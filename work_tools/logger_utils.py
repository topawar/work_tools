"""日志工具模块 - 简化版本,直接写入日志文件"""
import logging
import json
import functools
from datetime import datetime
from decimal import Decimal

# 使用简化的日志器名称
logger = logging.getLogger('app.view')
sql_logger = logging.getLogger('app.sql')


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


def log_view_input(view_name, cd, is_batch=None):
    """
    通用的视图输入参数记录

    Args:
        view_name: 视图名称
        cd: cleaned_data
        is_batch: 是否批量导入 (None 表示自动检测)
    """
    try:
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
            elif key not in ['csrfmiddlewaretoken', 'password']:
                input_data[key] = sanitize_for_json(value)

        logger.info(
            f"输入参数: {json.dumps(input_data, ensure_ascii=False, indent=2)}")
        logger.info("="*80)

        # 强制刷新日志
        for handler in logger.handlers:
            handler.flush()

    except Exception as e:
        logger.error(f"记录视图输入失败: {e}", exc_info=True)
        print(f"[日志错误] 记录视图输入失败: {e}")


def log_sql_generation(cd, records, update_drafting, update_contract_party, sql_content, is_batch=False):
    """记录SQL生成信息"""
    try:
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

        # 强制刷新日志
        for handler in sql_logger.handlers:
            handler.flush()

    except Exception as e:
        sql_logger.error(f"记录SQL生成失败: {e}", exc_info=True)
        print(f"[日志错误] 记录SQL生成失败: {e}")


def log_excel_parse_result(records):
    """
    记录Excel解析结果的详细信息

    Args:
        records: 解析后的记录列表
    """
    try:
        logger.info(f"Excel解析完成: 总记录数={len(records)}")

        if not records:
            logger.warning("Excel文件中没有有效数据")
            return

        # 记录前5条完整数据
        logger.info("前5条记录详情:")
        for i, rec in enumerate(records[:5], 1):
            logger.info(f"  记录{i}: {json.dumps(rec, ensure_ascii=False)}")

        # 统计各字段的填写情况
        field_stats = {}
        for rec in records:
            for key, value in rec.items():
                if value:
                    field_stats[key] = field_stats.get(key, 0) + 1

        logger.info("字段统计(非空数量):")
        for field, count in sorted(field_stats.items()):
            logger.info(
                f"  {field}: {count}/{len(records)} ({count*100//len(records)}%)")

        # 强制刷新日志
        for handler in logger.handlers:
            handler.flush()

    except Exception as e:
        logger.error(f"记录Excel解析结果失败: {e}", exc_info=True)
        print(f"[日志错误] 记录Excel解析结果失败: {e}")


def log_view_request(view_name):
    """视图函数日志装饰器"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(request, *args, **kwargs):
            try:
                logger.info("="*80)
                logger.info(f"{view_name} - 开始处理请求")
                logger.info(f"请求方法: {request.method}")
                logger.info(f"请求路径: {request.path}")

                # 强制刷新日志
                for handler in logger.handlers:
                    handler.flush()

                result = func(request, *args, **kwargs)

                logger.info(f"{view_name} - 处理完成")
                logger.info("="*80)

                # 强制刷新日志
                for handler in logger.handlers:
                    handler.flush()

                return result

            except Exception as e:
                logger.error(f"{view_name} - 处理异常: {str(e)}", exc_info=True)

                # 强制刷新日志
                for handler in logger.handlers:
                    handler.flush()

                logger.info("="*80)
                raise
        return wrapper
    return decorator
