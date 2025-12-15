""" 
项目轮次模块
包含项目轮次修改的所有视图函数和SQL生成逻辑
"""
import io
import os
import logging
from django.shortcuts import render
from django.http import FileResponse
from ..forms import ProjectRoundForm
from ..navigation import get_sidebar_groups
from ..config import get_config
from ..sql_merge import chunk_list, format_in, merge_by_key
from ..logger_utils import log_view_input
from .base import parse_ops_remark, save_sql_file
from ..validation_utils import (
    validate_required,
    generate_validation_failure_excel,
    get_temp_filename_from_path
)

try:
    import openpyxl
    from openpyxl.styles import Font, Alignment, PatternFill
    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False

logger = logging.getLogger('work_tools.view')
sql_logger = logging.getLogger('work_tools.sql')


def parse_project_round_excel(file):
    """解析Excel文件,提取项目轮次数据"""
    if not OPENPYXL_AVAILABLE:
        raise ValueError("缺少 openpyxl，无法解析 Excel")

    wb = openpyxl.load_workbook(file)
    ws = wb.active
    headers = [cell.value for cell in ws[1]]
    idx = {str(h): i for i, h in enumerate(headers)}

    def pick(alts):
        for a in alts:
            if a in idx:
                return idx[a]
        return None

    scheme_idx = pick(['采购方案编号', 'PURCHASE_SCHEME_NO', 'purchase_scheme_no'])
    prev_inq_idx = pick(['上轮询价单编号', 'PREV_INQ_ID', 'prev_inq_id'])
    prev_scheme_idx = pick(['上轮采购方案编号', 'PREV_PURCHASE_SCHEME_NO', 'prev_purchase_scheme_no'])
    round_idx = pick(['物理轮次', 'ROUND_NUMBER', 'round_number'])
    
    orig_prev_inq_idx = pick(['原上轮询价单编号', 'orig_prev_inq_id'])
    orig_prev_scheme_idx = pick(['原上轮采购方案编号', 'orig_prev_purchase_scheme_no'])
    orig_round_idx = pick(['原物理轮次', 'orig_round_number'])

    if scheme_idx is None:
        raise ValueError("Excel 缺少必要列：采购方案编号")

    records = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        if not row:
            continue
        scheme_no = row[scheme_idx]
        if scheme_no is None:
            continue

        rec = {
            'purchase_scheme_no': str(scheme_no).strip(),
        }

        # 新值
        if prev_inq_idx is not None and row[prev_inq_idx]:
            rec['prev_inq_id'] = str(row[prev_inq_idx]).strip()
        if prev_scheme_idx is not None and row[prev_scheme_idx]:
            rec['prev_purchase_scheme_no'] = str(row[prev_scheme_idx]).strip()
        if round_idx is not None and row[round_idx]:
            rec['round_number'] = str(row[round_idx]).strip()

        # 原值(用于回退)
        if orig_prev_inq_idx is not None and row[orig_prev_inq_idx]:
            rec['orig_prev_inq_id'] = str(row[orig_prev_inq_idx]).strip()
        if orig_prev_scheme_idx is not None and row[orig_prev_scheme_idx]:
            rec['orig_prev_purchase_scheme_no'] = str(row[orig_prev_scheme_idx]).strip()
        if orig_round_idx is not None and row[orig_round_idx]:
            rec['orig_round_number'] = str(row[orig_round_idx]).strip()

        records.append(rec)

    if not records:
        raise ValueError("Excel 中没有有效的行数据")

    logger.info(f"[项目轮次] Excel解析完成, 记录数={len(records)}")
    return records


def validate_project_round_records(records):
    """校验项目轮次记录"""
    results = []
    passed_count = 0
    failed_count = 0
    
    for idx, record in enumerate(records):
        row_number = idx + 2  # 跳过表头
        errors = []
        
        # 三个字段都必填:采购方案编号、物理轮次、原物理轮次
        error = validate_required(record.get('purchase_scheme_no'), '采购方案编号')
        if error:
            errors.append(error)
        
        error = validate_required(record.get('round_number'), '物理轮次')
        if error:
            errors.append(error)
        
        error = validate_required(record.get('orig_round_number'), '原物理轮次')
        if error:
            errors.append(error)
        
        # 记录结果
        if errors:
            results.append({
                'row_number': row_number,
                'valid': False,
                'errors': errors
            })
            failed_count += 1
        else:
            results.append({
                'row_number': row_number,
                'valid': True,
                'errors': []
            })
            passed_count += 1
    
    return {
        'valid': failed_count == 0,
        'total': len(records),
        'passed': passed_count,
        'failed': failed_count,
        'results': results
    }


def generate_project_round_sql_bulk(records, ops_remark=None):
    """
    生成批量项目轮次修改SQL - 支持SQL合并策略
    """
    cfg = get_config()
    sql = []
    sql.append("1、执行语句")

    sql_logger.info(
        f"[SQL合并] 开始生成项目轮次SQL, 记录数={len(records)}, 配置启用={cfg.get('MERGE_MODULES', {}).get('project_round', True)}")

    # 项目轮次不适合合并,因为每条记录的SET字段可能不同
    # 逐条生成SQL
    sql_logger.info("[SQL合并] 项目轮次使用逐条生成模式")
    
    for r in records:
        scheme_no = r.get('purchase_scheme_no')
        if not scheme_no:
            continue

        # 构建SET子句
        set_parts = []
        if r.get('prev_inq_id') is not None:
            prev_inq = r['prev_inq_id'].strip()
            set_parts.append(f"PREV_INQ_ID = '{prev_inq}'")
        if r.get('prev_purchase_scheme_no') is not None:
            prev_scheme = r['prev_purchase_scheme_no'].strip()
            set_parts.append(f"PREV_PURCHASE_SCHEME_NO = '{prev_scheme}'")
        if r.get('round_number') is not None:
            round_num = r['round_number'].strip()
            set_parts.append(f"ROUND_NUMBER = '{round_num}'")

        if set_parts:
            set_clause = ', '.join(set_parts)
            stmt = f"UPDATE cnnc_pr.tprfa01 SET {set_clause} WHERE PURCHASE_SCHEME_NO = '{scheme_no}';"
            sql.append(stmt)

    # 生成回退语句
    sql.append("")
    sql.append("2、回退语句")

    for r in records:
        scheme_no = r.get('purchase_scheme_no')
        if not scheme_no:
            continue

        # 构建回退SET子句
        set_parts = []
        if r.get('orig_prev_inq_id') is not None:
            orig_inq = r['orig_prev_inq_id'].strip()
            set_parts.append(f"PREV_INQ_ID = '{orig_inq}'")
        elif r.get('prev_inq_id') is not None:
            # 如果没有原值,回退为空格
            set_parts.append("PREV_INQ_ID = ' '")

        if r.get('orig_prev_purchase_scheme_no') is not None:
            orig_scheme = r['orig_prev_purchase_scheme_no'].strip()
            set_parts.append(f"PREV_PURCHASE_SCHEME_NO = '{orig_scheme}'")
        elif r.get('prev_purchase_scheme_no') is not None:
            set_parts.append("PREV_PURCHASE_SCHEME_NO = ''")

        if r.get('orig_round_number') is not None:
            orig_round = r['orig_round_number'].strip()
            set_parts.append(f"ROUND_NUMBER = '{orig_round}'")
        elif r.get('round_number') is not None:
            set_parts.append("ROUND_NUMBER = '1'")

        if set_parts:
            set_clause = ', '.join(set_parts)
            stmt = f"UPDATE cnnc_pr.tprfa01 SET {set_clause} WHERE PURCHASE_SCHEME_NO = '{scheme_no}';"
            sql.append(stmt)

    return sql


def project_round_view(request):
    """项目轮次视图"""
    saved_file = None
    validation_failure = None  # 新增

    if request.method == 'POST':
        form = ProjectRoundForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                cd = form.cleaned_data
                ops_remark = parse_ops_remark(cd.get('ops_remark', ''))
                dynamic_id = cd.get('dynamic_id', '')

                # 记录视图输入
                log_view_input('project_round', cd)

                logger.info(
                    f"[项目轮次] 开始处理, dynamic_id={dynamic_id}, ops_remark={ops_remark}")

                # 解析数据
                excel_file = cd.get('excel_file')
                if excel_file:
                    records = parse_project_round_excel(excel_file)
                    logger.info(f"[项目轮次] Excel模式, 记录数={len(records)}")
                    
                    # 执行数据校验
                    validation_result = validate_project_round_records(records)
                    
                    if not validation_result['valid']:
                        # 校验失败,生成失败文件
                        temp_file = generate_validation_failure_excel(
                            cd['excel_file'],
                            validation_result,
                            'project_round'
                        )
                        
                        if temp_file:
                            validation_failure = {
                                'total': validation_result['total'],
                                'passed': validation_result['passed'],
                                'failed': validation_result['failed'],
                                'filename': get_temp_filename_from_path(temp_file)
                            }
                        
                        return render(request, 'project_round.html', {
                            'form': form,
                            'validation_failure': validation_failure,
                            'active_menu': 'project_round',
                            'sidebar_groups': get_sidebar_groups(),
                        })
                else:
                    # 单条记录
                    rec = {
                        'purchase_scheme_no': cd.get('purchase_scheme_no'),
                    }
                    if cd.get('prev_inq_id'):
                        rec['prev_inq_id'] = cd.get('prev_inq_id')
                    if cd.get('prev_purchase_scheme_no'):
                        rec['prev_purchase_scheme_no'] = cd.get('prev_purchase_scheme_no')
                    if cd.get('round_number'):
                        rec['round_number'] = cd.get('round_number')
                    
                    # 原值
                    if cd.get('orig_prev_inq_id'):
                        rec['orig_prev_inq_id'] = cd.get('orig_prev_inq_id')
                    if cd.get('orig_prev_purchase_scheme_no'):
                        rec['orig_prev_purchase_scheme_no'] = cd.get('orig_prev_purchase_scheme_no')
                    if cd.get('orig_round_number'):
                        rec['orig_round_number'] = cd.get('orig_round_number')
                    
                    records = [rec]
                    logger.info(
                        f"[项目轮次] 单条模式, scheme_no={rec['purchase_scheme_no']}")

                # 生成SQL
                sql_lines = generate_project_round_sql_bulk(records, ops_remark)
                logger.info(f"[项目轮次] SQL生成完成, 行数={len(sql_lines)}")

                # 保存SQL文件
                sql_content = '\n'.join(sql_lines)
                saved_file = save_sql_file(
                    sql_content, prefix='项目轮次', dynamic_id=dynamic_id)
                logger.info(f"[项目轮次] SQL文件已保存: {saved_file}")

            except Exception as e:
                logger.error(f"[项目轮次] 处理失败: {e}", exc_info=True)
                form.add_error(None, f"生成SQL失败: {str(e)}")
    else:
        form = ProjectRoundForm()

    return render(request, 'project_round.html', {
        'form': form,
        'saved_file': saved_file,
        'validation_failure': validation_failure,
        'active_menu': 'project_round',
        'sidebar_groups': get_sidebar_groups(),
    })


def download_project_round_template(request):
    """下载项目轮次Excel模板"""
    if not OPENPYXL_AVAILABLE:
        return FileResponse(
            io.BytesIO(b"openpyxl not installed"),
            as_attachment=True,
            filename="error.txt"
        )

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "项目轮次"

    # 设置表头
    headers = ["采购方案编号", "上轮询价单编号", "上轮采购方案编号", "物理轮次", 
               "原上轮询价单编号", "原上轮采购方案编号", "原物理轮次"]
    header_fill = PatternFill(start_color="4472C4",
                              end_color="4472C4", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF")

    for col_num, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col_num)
        cell.value = header
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal='center', vertical='center')

    # 设置列宽
    ws.column_dimensions['A'].width = 25
    ws.column_dimensions['B'].width = 25
    ws.column_dimensions['C'].width = 25
    ws.column_dimensions['D'].width = 15
    ws.column_dimensions['E'].width = 25
    ws.column_dimensions['F'].width = 25
    ws.column_dimensions['G'].width = 15

    # 添加示例数据
    example_data = [
        ["CNEC-CGFA-25-23960", "CNEC-XJD-25-21442", "CNEC-CGFA-25-22304", "3", " ", "", "1"],
        ["CNEC-CGFA-25-23961", "CNEC-XJD-25-21443", "CNEC-CGFA-25-22305", "3", " ", "", "1"],
    ]

    for row_num, row_data in enumerate(example_data, 2):
        for col_num, value in enumerate(row_data, 1):
            cell = ws.cell(row=row_num, column=col_num)
            cell.value = value
            cell.alignment = Alignment(horizontal='left', vertical='center')

    bio = io.BytesIO()
    wb.save(bio)
    bio.seek(0)

    response = FileResponse(bio, as_attachment=True,
                            filename='project_round_template.xlsx')
    response['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    return response


__all__ = [
    'project_round_view',
    'download_project_round_template',
]
