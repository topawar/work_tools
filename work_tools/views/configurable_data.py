"""可配置数据修改视图"""
import io
import logging
from django import forms
from django.shortcuts import render, get_object_or_404
from django.http import FileResponse
from django.core.cache import cache

from ..models import ConfigurableTable, ConfigurableField
from ..navigation import get_sidebar_groups
from ..config import get_config
from ..sql_merge import chunk_list, format_in, merge_by_key, to_literal
from ..logger_utils import log_view_input
from ..dropdown_utils import get_dropdown_options
from .base import parse_ops_remark, save_sql_file

try:
    import openpyxl
    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False

logger = logging.getLogger('work_tools.view')
sql_logger = logging.getLogger('work_tools.sql')


def get_table_config(table_code):
    """获取表配置（带缓存）"""
    cache_key = f'configurable_table_{table_code}'
    table = cache.get(cache_key)
    
    if table is None:
        table = ConfigurableTable.objects.filter(
            table_code=table_code,
            is_active=True
        ).first()
        if table:
            cache.set(cache_key, table, 30 * 60)
    
    return table


def get_fields_config(table_code, field_type=None):
    """获取字段配置（带缓存）"""
    cache_key = f'configurable_fields_{table_code}'
    fields = cache.get(cache_key)
    
    if fields is None:
        table = get_table_config(table_code)
        if not table:
            return []
        
        fields = {
            'update': list(ConfigurableField.objects.filter(
                table=table,
                field_type='update',
                is_active=True
            ).order_by('sort_order', 'field_name')),
            'query': list(ConfigurableField.objects.filter(
                table=table,
                field_type='query',
                is_active=True
            ).order_by('sort_order', 'field_name'))
        }
        cache.set(cache_key, fields, 30 * 60)
    
    if field_type:
        return fields.get(field_type, [])
    return fields


def create_form_field(field_config, is_update=False):
    """根据字段配置创建表单字段"""
    field_kwargs = {
        'label': field_config.display_name,
        'required': field_config.is_required if not is_update else False,
    }
    
    if field_config.default_value and not is_update:
        field_kwargs['initial'] = field_config.default_value
    
    if field_config.data_type == 'text':
        field_kwargs['max_length'] = field_config.max_length or 255
        field_kwargs['widget'] = forms.TextInput(attrs={'class': 'form-control'})
        return forms.CharField(**field_kwargs)
    elif field_config.data_type == 'number':
        field_kwargs['widget'] = forms.NumberInput(attrs={'class': 'form-control'})
        return forms.DecimalField(**field_kwargs)
    elif field_config.data_type == 'date':
        field_kwargs['widget'] = forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
        return forms.DateField(**field_kwargs)
    elif field_config.data_type == 'dropdown':
        # 下拉框类型：从配置分组加载选项
        if field_config.dropdown_group:
            choices = get_dropdown_options(
                field_config.dropdown_group.group_code,
                include_empty=not field_config.is_required,  # 必填字段不显示空选项
                empty_label='请选择'
            )
            field_kwargs['choices'] = choices
            field_kwargs['widget'] = forms.Select(attrs={'class': 'form-select'})
            logger.info(f"[动态表单] 下拉框字段 {field_config.field_name} 加载选项数: {len(choices)}")
        else:
            # 如果没有配置分组，降级为文本框
            logger.warning(f"[动态表单] 下拉框字段 {field_config.field_name} 未配置数据源分组，降级为文本框")
            field_kwargs['widget'] = forms.TextInput(attrs={'class': 'form-control'})
            return forms.CharField(**field_kwargs)
        return forms.ChoiceField(**field_kwargs)
    else:
        field_kwargs['widget'] = forms.TextInput(attrs={'class': 'form-control'})
        return forms.CharField(**field_kwargs)


def create_dynamic_form(table_code):
    """根据配置动态创建表单类"""
    update_fields = get_fields_config(table_code, 'update')
    query_fields = get_fields_config(table_code, 'query')
    
    logger.info(f"[动态表单] 表编码: {table_code}, 查询字段数: {len(query_fields)}, 修改字段数: {len(update_fields)}")
    
    # 构建字段字典
    form_fields = {
        'dynamic_id': forms.CharField(
            label='编号',
            max_length=100,
            required=False,
            widget=forms.TextInput(attrs={'placeholder': '用于SQL文件命名', 'class': 'form-control'})
        ),
        'ops_remark': forms.CharField(
            label='操作备注',
            required=False,
            widget=forms.TextInput(attrs={'placeholder': '支持ONES链接格式：#69054 修改数据', 'class': 'form-control'})
        ),
        'excel_file': forms.FileField(
            label='批量导入Excel',
            required=False,
            help_text='上传Excel文件进行批量修改',
            widget=forms.FileInput(attrs={'class': 'form-control'})
        ),
    }
    
    # 添加查询字段
    for field_config in query_fields:
        field_name = f'query_{field_config.field_name}'
        form_fields[field_name] = create_form_field(field_config, is_update=False)
        logger.info(f"[动态表单] 添加查询字段: {field_name}")
    
    # 添加修改字段
    for field_config in update_fields:
        field_name = f'update_{field_config.field_name}'
        form_fields[field_name] = create_form_field(field_config, is_update=True)
        logger.info(f"[动态表单] 添加修改字段: {field_name}")
    
    # 添加原值字段（用于回退SQL）
    for field_config in update_fields:
        field_name = f'orig_{field_config.field_name}'
        # 原值字段都是非必填
        orig_field_config_copy = type('obj', (object,), {
            'field_name': field_config.field_name,
            'display_name': f'原{field_config.display_name}',
            'data_type': field_config.data_type,
            'max_length': field_config.max_length,
            'is_required': False,
            'default_value': '',
            'dropdown_group': field_config.dropdown_group if hasattr(field_config, 'dropdown_group') else None
        })()
        form_fields[field_name] = create_form_field(orig_field_config_copy, is_update=True)
        logger.info(f"[动态表单] 添加原值字段: {field_name}")
    
    # 使用type()动态创建表单类
    DynamicForm = type('DynamicForm', (forms.Form,), form_fields)
    
    logger.info(f"[动态表单] 创建完成，总字段数: {len(DynamicForm.base_fields)}")
    logger.info(f"[动态表单] 字段列表: {list(DynamicForm.base_fields.keys())}")
    
    return DynamicForm


def parse_excel(file, table_code):
    """解析Excel文件，提取修改数据"""
    if not OPENPYXL_AVAILABLE:
        raise ValueError("缺少 openpyxl，无法解析 Excel")
    
    update_fields = get_fields_config(table_code, 'update')
    query_fields = get_fields_config(table_code, 'query')
    
    wb = openpyxl.load_workbook(file)
    ws = wb.active
    
    # 读取表头（第一行或第二行）
    headers = [cell.value for cell in ws[1]]
    
    # 创建字段名到列索引的映射（忽略大小写）
    def build_column_map(headers, fields_config):
        col_map = {}
        headers_upper = [str(h).upper() if h else '' for h in headers]
        
        for field_cfg in fields_config:
            # 优先匹配字段数据库名
            field_name_upper = field_cfg.field_name.upper()
            if field_name_upper in headers_upper:
                col_map[field_cfg.field_name] = headers_upper.index(field_name_upper)
            # 其次匹配显示名称
            elif field_cfg.display_name in headers:
                col_map[field_cfg.field_name] = headers.index(field_cfg.display_name)
        
        return col_map
    
    query_col_map = build_column_map(headers, query_fields)
    update_col_map = build_column_map(headers, update_fields)
    
    # 检查是否包含所有必需的查询字段
    required_query_fields = [f for f in query_fields if f.is_required]
    missing_fields = [f.field_name for f in required_query_fields if f.field_name not in query_col_map]
    if missing_fields:
        raise ValueError(f"Excel缺少必需的查询字段列: {', '.join(missing_fields)}")
    
    # 检查是否至少包含一个修改字段
    if not update_col_map:
        raise ValueError("Excel必须包含至少一个修改字段列")
    
    # 构建原值列映射（用于回退SQL）
    orig_col_map = {}
    for field_name in update_col_map.keys():
        orig_field_name = f'orig_{field_name}'
        orig_field_name_upper = orig_field_name.upper()
        if orig_field_name_upper in [str(h).upper() if h else '' for h in headers]:
            orig_col_map[field_name] = [str(h).upper() if h else '' for h in headers].index(orig_field_name_upper)
    
    # 提取数据记录
    records = []
    for row_idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
        if not row or all(cell is None or str(cell).strip() == '' for cell in row):
            continue
        
        record = {'query': {}, 'update': {}, 'orig': {}}
        
        # 提取查询字段值
        for field_name, col_idx in query_col_map.items():
            value = row[col_idx]
            if value is not None:
                record['query'][field_name] = str(value).strip()
        
        # 提取修改字段值
        for field_name, col_idx in update_col_map.items():
            value = row[col_idx]
            if value is not None and str(value).strip() != '':
                record['update'][field_name] = str(value).strip()
        
        # 提取原值
        for field_name, col_idx in orig_col_map.items():
            value = row[col_idx]
            if value is not None and str(value).strip() != '':
                record['orig'][field_name] = str(value).strip()
        
        # 验证查询字段完整性
        if len(record['query']) != len(query_col_map):
            logger.warning(f"[Excel解析] 第{row_idx}行查询字段不完整，跳过")
            continue
        
        # 至少有一个修改字段有值
        if record['update']:
            records.append(record)
    
    if not records:
        raise ValueError("Excel中没有有效的数据记录")
    
    logger.info(f"[Excel解析] 成功解析{len(records)}条记录")
    return records


def process_nullable_fields(records, update_fields_config):
    """处理可为空字段，为空值生成空字符串"""
    # 构建字段名到配置的映射
    field_map = {f.field_name: f for f in update_fields_config}
    
    for record in records:
        # 检查每个可为空的修改字段
        for field_name, field_config in field_map.items():
            if field_config.is_nullable and field_name not in record['update']:
                # 字段可为空且用户未填写，添加空字符串
                record['update'][field_name] = ''
    
    return records


def generate_dynamic_filename(records, update_fields_config):
    """生成动态文件名: 收集实际修改字段的sql_file_name并用顿号连接"""
    # 构建字段名到配置的映射
    field_map = {f.field_name: f for f in update_fields_config}
    
    # 收集所有记录中实际修改的字段
    modified_fields = set()
    for record in records:
        modified_fields.update(record['update'].keys())
    
    # 收集这些字段的sql_file_name
    file_name_parts = []
    for field_name in sorted(modified_fields):  # 排序保证一致性
        if field_name in field_map:
            field_config = field_map[field_name]
            if field_config.sql_file_name:  # 只收集配置了文件名的字段
                file_name_parts.append(field_config.sql_file_name)
    
    # 用中文顿号连接
    if file_name_parts:
        return '、'.join(file_name_parts)
    else:
        # 如果没有配置文件名，返回默认值
        return '数据修改'


def generate_sql(table_config, records, ops_remark=None, db_config_ids=None):
    """
    生成SQL语句 - 支持SQL合并策略
    records: [{'query': {...}, 'update': {...}, 'orig': {...}}, ...]
    db_config_ids: 选中的数据库配置id列表
    """
    cfg = get_config()
    table_name = table_config.table_name
    table_code = table_config.table_code
    
    # 获取数据库配置
    from ..models import DatabaseConfig
    if db_config_ids:
        db_configs = DatabaseConfig.objects.filter(id__in=db_config_ids, is_active=True).order_by('sort_order')
    else:
        db_configs = DatabaseConfig.objects.filter(is_active=True).order_by('sort_order')
    
    sql = []
    sql.append("1、执行语句")
    
    sql_logger.info(
        f"[SQL生成] 开始生成可配置表SQL, 表={table_name}, 记录数={len(records)}, "
        f"配置启用={cfg.get('MERGE_MODULES', {}).get(table_code, True)}"
    )
    
    # 检查是否启用SQL合并策略
    merge_enabled = cfg.get('MERGE_MODULES', {}).get(table_code, True)
    
    if merge_enabled:
        # 启用SQL合并策略: 按修改字段值分组
        def key_fn(r):
            # 构建修改字段的值元组作为分组键
            return tuple(sorted(r['update'].items()))
        
        groups = merge_by_key(records, key_fn)
        sql_logger.info(f"[SQL合并] 分组结果: {len(groups)}个分组")
        
        for key, recs in groups.items():
            update_dict = dict(key)
            
            # 构建查询条件列表
            query_conditions = [r['query'] for r in recs]
            
            # 如果所有记录的查询条件完全相同,使用IN查询
            # 否则使用OR条件组合
            if len(query_conditions) == 1:
                # 单条记录
                where_clause = ' AND '.join([f"{k}={to_literal(v)}" for k, v in query_conditions[0].items()])
            else:
                # 多条记录,尝试提取公共字段做IN查询
                # 简化处理:假设第一个查询字段是主键,用它做IN查询
                first_query_field = list(query_conditions[0].keys())[0]
                id_values = [qc[first_query_field] for qc in query_conditions if first_query_field in qc]
                
                # 其他查询字段作为AND条件
                other_conditions = {k: v for k, v in query_conditions[0].items() if k != first_query_field}
                
                for chunk in chunk_list(id_values, int(cfg.get('MERGE_MAX_IN_SIZE', 500))):
                    inlist = format_in(chunk)
                    where_parts = [f"{first_query_field} IN ({inlist})"]
                    for k, v in other_conditions.items():
                        where_parts.append(f"{k}={to_literal(v)}")
                    where_clause = ' AND '.join(where_parts)
                    
                    # 构建 SET子句
                    set_parts = [f"{k}={to_literal(v)}" for k, v in update_dict.items()]
                    if ops_remark:
                        set_parts.append(f"OPS_REMARK={to_literal(ops_remark)}")
                    set_clause = ', '.join(set_parts)
                    
                    stmt = f"UPDATE {table_name} SET {set_clause} WHERE {where_clause};"
                    sql.append(stmt)
                    sql_logger.info(f"[SQL合并] 生成IN查询: {len(chunk)}条记录")
                continue
            
            # 单条或相同条件的记录
            set_parts = [f"{k}={to_literal(v)}" for k, v in update_dict.items()]
            if ops_remark:
                set_parts.append(f"OPS_REMARK={to_literal(ops_remark)}")
            set_clause = ', '.join(set_parts)
            
            stmt = f"UPDATE {table_name} SET {set_clause} WHERE {where_clause};"
            sql.append(stmt)
    else:
        # 未启用合并策略: 逐条生成SQL
        sql_logger.info("[SQL合并] 合并策略已禁用, 逐条生成SQL")
        for r in records:
            set_parts = [f"{k}={to_literal(v)}" for k, v in r['update'].items()]
            if ops_remark:
                set_parts.append(f"OPS_REMARK={to_literal(ops_remark)}")
            set_clause = ', '.join(set_parts)
            
            where_parts = [f"{k}={to_literal(v)}" for k, v in r['query'].items()]
            where_clause = ' AND '.join(where_parts)
            
            stmt = f"UPDATE {table_name} SET {set_clause} WHERE {where_clause};"
            sql.append(stmt)
    
    # 生成回退语句
    sql.append("2、回退语句")
    has_rollback = any(r['orig'] for r in records)
    
    if has_rollback:
        if merge_enabled:
            # 按原值分组生成回退SQL
            def rb_key(r):
                return tuple(sorted(r['orig'].items())) if r['orig'] else None
            
            groups = merge_by_key([r for r in records if r['orig']], rb_key)
            
            for key, recs in groups.items():
                if key is None:
                    continue
                
                orig_dict = dict(key)
                query_conditions = [r['query'] for r in recs]
                
                if len(query_conditions) == 1:
                    where_clause = ' AND '.join([f"{k}={to_literal(v)}" for k, v in query_conditions[0].items()])
                    
                    set_parts = [f"{k}={to_literal(v)}" for k, v in orig_dict.items()]
                    set_parts.append("OPS_REMARK=''")
                    set_clause = ', '.join(set_parts)
                    
                    stmt = f"UPDATE {table_name} SET {set_clause} WHERE {where_clause};"
                    sql.append(stmt)
                else:
                    first_query_field = list(query_conditions[0].keys())[0]
                    id_values = [qc[first_query_field] for qc in query_conditions if first_query_field in qc]
                    other_conditions = {k: v for k, v in query_conditions[0].items() if k != first_query_field}
                    
                    for chunk in chunk_list(id_values, int(cfg.get('MERGE_MAX_IN_SIZE', 500))):
                        inlist = format_in(chunk)
                        where_parts = [f"{first_query_field} IN ({inlist})"]
                        for k, v in other_conditions.items():
                            where_parts.append(f"{k}={to_literal(v)}")
                        where_clause = ' AND '.join(where_parts)
                        
                        set_parts = [f"{k}={to_literal(v)}" for k, v in orig_dict.items()]
                        set_parts.append("OPS_REMARK=''")
                        set_clause = ', '.join(set_parts)
                        
                        stmt = f"UPDATE {table_name} SET {set_clause} WHERE {where_clause};"
                        sql.append(stmt)
        else:
            for r in records:
                if not r['orig']:
                    continue
                
                set_parts = [f"{k}={to_literal(v)}" for k, v in r['orig'].items()]
                set_parts.append("OPS_REMARK=''")
                set_clause = ', '.join(set_parts)
                
                where_parts = [f"{k}={to_literal(v)}" for k, v in r['query'].items()]
                where_clause = ' AND '.join(where_parts)
                
                stmt = f"UPDATE {table_name} SET {set_clause} WHERE {where_clause};"
                sql.append(stmt)
    
    # 生成数据库配置信息
    sql.append("3.数据库")
    if db_configs.exists():
        for db_config in db_configs:
            sql.append(f"ip：{db_config.db_host}")
            sql.append(f"库名：{db_config.db_name}")
    else:
        # 默认配置
        sql.append("ip：192.168.11.71")
        sql.append("库名：cnnc_ph")
    
    sql_logger.info(f"[SQL生成] SQL生成完成, 总行数={len(sql)}")
    return "\n".join(sql)


def download_template(request, table_code):
    """下载Excel模板"""
    if not OPENPYXL_AVAILABLE:
        return render(request, 'error.html', {'error': '服务器缺少 openpyxl 库'})
    
    table_config = get_table_config(table_code)
    if not table_config:
        return render(request, 'error.html', {'error': '表配置不存在或已禁用'})
    
    update_fields = get_fields_config(table_code, 'update')
    query_fields = get_fields_config(table_code, 'query')
    
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = table_config.display_name
    
    # 构建表头
    headers = []
    field_names = []
    
    # 查询字段列
    for field in query_fields:
        headers.append(field.display_name)
        field_names.append(field.field_name)
    
    # 修改字段列
    for field in update_fields:
        headers.append(field.display_name)
        field_names.append(field.field_name)
    
    # 原值列
    for field in update_fields:
        headers.append(f'原{field.display_name}')
        field_names.append(f'orig_{field.field_name}')
    
    ws.append(headers)
    ws.append(field_names)
    ws.append(['示例值'] * len(headers))
    
    bio = io.BytesIO()
    wb.save(bio)
    bio.seek(0)
    
    filename = f'{table_config.table_code}_template.xlsx'
    response = FileResponse(bio, as_attachment=True, filename=filename)
    response['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    return response


def configurable_data_view(request, table_code):
    """可配置数据修改视图"""
    table_config = get_table_config(table_code)
    if not table_config:
        return render(request, 'error.html', {
            'error': '表配置不存在或已禁用',
            'sidebar_groups': get_sidebar_groups(),
        })
    
    # 首先获取字段配置用于创建表单
    update_fields_data = get_fields_config(table_code, 'update')
    query_fields_data = get_fields_config(table_code, 'query')
    
    FormClass = create_dynamic_form(table_code)
    saved_file = None
    
    if request.method == 'POST':
        form = FormClass(request.POST, request.FILES)
        if form.is_valid():
            cd = form.cleaned_data
            log_view_input(f"可配置数据修改-{table_config.display_name}", cd)
            
            ops_remark = parse_ops_remark(cd.get('ops_remark', ''))
            
            # 从表配置中获取数据库配置
            db_config_ids = [str(db.id) for db in table_config.database_configs.filter(is_active=True)]
            logger.info(f"[可配置数据修改] 使用数据库配置: {db_config_ids}")
            
            if cd.get('excel_file'):
                # Excel批量导入模式
                try:
                    records = parse_excel(cd['excel_file'], table_code)
                    # 处理空值字段
                    records = process_nullable_fields(records, update_fields_data)
                    sql_content = generate_sql(table_config, records, ops_remark, db_config_ids)
                except Exception as e:
                    logger.error(f"[可配置数据修改] Excel解析失败: {e}")
                    form.add_error('excel_file', f'Excel解析失败: {str(e)}')
                else:
                    # 生成动态文件名
                    file_prefix = generate_dynamic_filename(records, update_fields_data)
                    saved_file = save_sql_file(
                        sql_content,
                        file_prefix,
                        cd.get('dynamic_id')
                    )
            else:
                # 单条修改模式
                record = {'query': {}, 'update': {}, 'orig': {}}
                
                # 提取查询字段值
                for field in query_fields_data:
                    field_key = f'query_{field.field_name}'
                    if field_key in cd and cd[field_key]:
                        record['query'][field.field_name] = cd[field_key]
                
                # 提取修改字段值
                for field in update_fields_data:
                    field_key = f'update_{field.field_name}'
                    value = cd.get(field_key)
                    # 处理空值: 如果字段可为空且值为空，也要生成SQL
                    if value is not None and str(value).strip() != '':
                        record['update'][field.field_name] = str(value).strip()
                    elif field.is_nullable and (value is None or str(value).strip() == ''):
                        # 字段可为空且用户未填写，生成空字符串SQL
                        record['update'][field.field_name] = ''
                
                # 提取原值字段（用于回退SQL）
                for field in update_fields_data:
                    field_key = f'orig_{field.field_name}'
                    if field_key in cd and cd[field_key]:
                        record['orig'][field.field_name] = cd[field_key]
                
                # 验证: 所有查询字段必须填写
                if len(record['query']) != len(query_fields_data):
                    form.add_error(None, '所有查询条件字段必须填写')
                elif not record['update']:
                    form.add_error(None, '至少填写一个修改字段')
                else:
                    sql_content = generate_sql(table_config, [record], ops_remark, db_config_ids)
                    # 生成动态文件名
                    file_prefix = generate_dynamic_filename([record], update_fields_data)
                    saved_file = save_sql_file(
                        sql_content,
                        file_prefix,
                        cd.get('dynamic_id')
                    )
    else:
        form = FormClass()
    
    # 为字段配置添加form_field属性用于模板渲染
    # 重新获取字段配置，确保是新的对象
    update_fields = list(update_fields_data)
    query_fields = list(query_fields_data)
    orig_fields = []  # 原值字段列表
    
    for field in query_fields:
        field.field_key = f'query_{field.field_name}'
        if field.field_key in form.fields:
            field.form_field = form[field.field_key]
        else:
            logger.error(f"[可配置数据修改] 表单中找不到字段: {field.field_key}")
            
    for field in update_fields:
        field.field_key = f'update_{field.field_name}'
        if field.field_key in form.fields:
            field.form_field = form[field.field_key]
        else:
            logger.error(f"[可配置数据修改] 表单中找不到字段: {field.field_key}")
    
    # 为原值字段创建虚拟配置对象
    for field in update_fields_data:
        orig_field = type('obj', (object,), {
            'field_name': field.field_name,
            'display_name': f'原{field.display_name}',
            'field_key': f'orig_{field.field_name}',
        })()
        if orig_field.field_key in form.fields:
            orig_field.form_field = form[orig_field.field_key]
            orig_fields.append(orig_field)
        else:
            logger.error(f"[可配置数据修改] 表单中找不到字段: {orig_field.field_key}")
    
    return render(request, 'configurable_data.html', {
        'form': form,
        'table_config': table_config,
        'update_fields': update_fields,
        'query_fields': query_fields,
        'orig_fields': orig_fields,
        'saved_file': saved_file,
        'active_menu': f'configurable_data_{table_code}',
        'sidebar_groups': get_sidebar_groups(),
    })


__all__ = [
    'get_table_config',
    'get_fields_config',
    'configurable_data_view',
    'download_template',
]
