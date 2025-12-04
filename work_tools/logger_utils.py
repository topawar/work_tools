import logging
import json
import functools
from datetime import datetime
from decimal import Decimal

logger = logging.getLogger('work_tools.view')
sql_logger = logging.getLogger('work_tools.sql')


def sanitize_for_json(obj):
    """将对象转换为JSON可序列化的格式"""
    if isinstance(obj, Decimal):
        return str(obj)
    elif isinstance(obj, (list, tuple)):
        return [sanitize_for_json(item) for item in obj]
    elif isinstance(obj, dict):
        return {k: sanitize_for_json(v) for k, v in obj.items()}
    else:
        return obj


def log_view_request(view_name):
    """视图函数日志装饰器"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(request, *args, **kwargs):
            logger.info("="*80)
            logger.info(f"{view_name} - 开始处理请求")
            logger.info(f"请求方法: {request.method}")
            logger.info(f"请求路径: {request.path}")

            try:
                result = func(request, *args, **kwargs)
                logger.info(f"{view_name} - 处理完成")
                logger.info("="*80)
                return result
            except Exception as e:
                logger.error(f"{view_name} - 处理异常: {str(e)}", exc_info=True)
                logger.info("="*80)
                raise
        return wrapper
    return decorator


def log_form_data(cd, is_batch=False):
    """记录表单数据"""
    mode = '批量导入' if is_batch else '单条记录'
    logger.info(f"处理模式: {mode}")
    logger.info(f"动态编号: {cd.get('dynamic_id')}")
    logger.info(f"操作备注: {cd.get('ops_remark')}")

    if is_batch:
        excel_file = cd.get('excel_file')
        if excel_file:
            logger.info(
                f"Excel文件: {excel_file.name}, 大小: {excel_file.size} bytes")
    else:
        logger.info(
            f"单条记录 - 方案:{cd.get('scheme_no')}, 询价:{cd.get('inquiry_no')}, 定标:{cd.get('result_no')}")

    # 记录单位信息
    if cd.get('new_drafting_name') or cd.get('new_drafting_id'):
        logger.info(
            f"新起草单位: 名称={cd.get('new_drafting_name')}, ID={cd.get('new_drafting_id')}")
    if cd.get('old_drafting_name') or cd.get('old_drafting_id'):
        logger.info(
            f"原起草单位: 名称={cd.get('old_drafting_name')}, ID={cd.get('old_drafting_id')}")
    if cd.get('new_party_name') or cd.get('new_party_id'):
        logger.info(
            f"新签约主体: 名称={cd.get('new_party_name')}, ID={cd.get('new_party_id')}")
    if cd.get('old_party_name') or cd.get('old_party_id'):
        logger.info(
            f"原签约主体: 名称={cd.get('old_party_name')}, ID={cd.get('old_party_id')}")


def log_records_processed(records, fail_rows=None):
    """记录处理的记录数"""
    logger.info(f"解析到 {len(records)} 条记录")

    if fail_rows:
        logger.warning(f"数据校验失败: {len(fail_rows)} 条")
        # 只记录前5条失败记录的详情
        for i, row in enumerate(fail_rows[:5]):
            logger.warning(
                f"失败记录 {i+1}: {json.dumps(row, ensure_ascii=False)}")

    # 记录前3条成功记录的关键信息
    for i, r in enumerate(records[:3]):
        logger.info(f"记录 {i+1}: 方案={r.get('scheme')}, 询价={r.get('inquiry')}, "
                    f"new_drafting_id={r.get('new_drafting_id')}, new_party_id={r.get('new_party_id')}")


def log_name_to_code_conversion(k_name, k_id, name, code, source):
    """记录名称到编号的转换"""
    if code:
        logger.info(
            f"字段转换成功: {k_name}='{name}' -> {k_id}='{code}' (来源:{source})")
    else:
        logger.warning(f"字段转换失败: {k_name}='{name}' 无法找到对应编号")


def log_sql_generation(cd, records, update_drafting, update_contract_party, sql_content, is_batch=False):
    """记录SQL生成信息"""
    mode = '批量导入' if is_batch else '单条记录'

    sql_logger.info("="*80)
    sql_logger.info(f"SQL生成 - 动态编号: {cd.get('dynamic_id')}")
    sql_logger.info(f"处理模式: {mode}")
    sql_logger.info(f"记录数: {len(records)}")
    sql_logger.info(f"更新起草单位: {update_drafting}")
    sql_logger.info(f"更新签约主体: {update_contract_party}")
    sql_logger.info(f"SQL长度: {len(sql_content)} 字符")

    # 记录SQL的前几行（用于快速检查）
    lines = sql_content.split('\n')
    sql_logger.info(f"SQL预览（前10行）:")
    for line in lines[:10]:
        sql_logger.info(f"  {line}")

    sql_logger.info("="*80)


def log_file_saved(filepath, filename):
    """记录文件保存信息"""
    logger.info(f"SQL文件已保存: {filepath}")
    logger.info(f"下载文件已准备: {filename}")


def log_view_input(view_name, cd, is_batch=None):
    """
    通用的视图输入参数记录

    Args:
        view_name: 视图名称
        cd: cleaned_data
        is_batch: 是否批量导入 (None 表示自动检测)
    """
    logger.info("="*80)
    logger.info(f"{view_name} - 开始处理")

    # 自动检测是否批量导入
    if is_batch is None:
        is_batch = bool(cd.get('excel_file'))

    mode = '批量导入' if is_batch else '单条记录'
    logger.info(f"处理模式: {mode}")

    # 记录所有非敏感字段
    input_data = {}
    for key, value in cd.items():
        if key == 'excel_file':
            if value:
                input_data[key] = {
                    'filename': value.name,
                    'size': value.size,
                    'content_type': value.content_type if hasattr(value, 'content_type') else 'unknown'
                }
        elif key not in ['csrfmiddlewaretoken']:
            input_data[key] = sanitize_for_json(value)

    logger.info(
        f"输入参数: {json.dumps(input_data, ensure_ascii=False, indent=2)}")
    logger.info("="*80)
