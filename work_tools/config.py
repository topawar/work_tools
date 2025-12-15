import json
import os
import logging
from django.conf import settings

logger = logging.getLogger('work_tools.config')

DEFAULT = {
    'MERGE_MAX_IN_SIZE': 500,
    'MERGE_MODULES': {
        # 合同模块
        'price': True,
        'item': True,
        'use_list': True,
        'budget': True,
        'enddate': True,
        'appr_state': True,
        'contract_terminate': True,
        'sourcing_terminate': True,
        'creator': True,  # 合同创建人修改
        # 计划-寻源模块
        'unit': True,
        'gov': True,
        'importance': True,
        'price_type': True,
        'erp': True,
        'project_round': True,
        'executor': True,  # 订单执行人修改
        'plan_date': True,  # 需求计划日期修改
    },
    # SQL文件输出配置
    'SQL_OUTPUT_BASE_PATH': './temp_files/sql_output',  # 相对路径，运行时解析为绝对路径
    'SQL_OUTPUT_MODE': 'hierarchical',  # 'flat' 或 'hierarchical'
    'SQL_OUTPUT_DATE_FORMAT': '%Y%m/%d',  # 日期子目录格式
    # 临时文件清理配置
    'TEMP_FILE_CLEANUP_ENABLED': True,
    'TEMP_FILE_RETENTION_HOURS': 24,
}


def _get_runtime_base_dir():
    """获取运行时的基础目录，支持打包后的exe和源码运行"""
    import sys
    if getattr(sys, 'frozen', False):
        # 打包后，exe所在目录
        base_dir = os.path.dirname(sys.executable)
        logger.debug(f"[路径解析] 打包环境，基础目录: {base_dir}")
        return base_dir
    else:
        # 源码运行，使用Django的BASE_DIR
        base_dir = getattr(settings, 'BASE_DIR', os.getcwd())
        logger.debug(f"[路径解析] 源码环境，基础目录: {base_dir}")
        return base_dir


def _path():
    base = _get_runtime_base_dir()
    cfg_dir = os.path.join(base, 'config')
    os.makedirs(cfg_dir, exist_ok=True)
    return os.path.join(cfg_dir, 'app_config.json')


def validate_config(cfg):
    """验证配置的完整性和正确性
    
    Args:
        cfg: 配置字典
    
    Returns:
        dict: {'valid': bool, 'errors': list, 'warnings': list}
    """
    errors = []
    warnings = []
    
    # 检查必需的顶级键
    required_keys = ['MERGE_MAX_IN_SIZE', 'MERGE_MODULES', 'SQL_OUTPUT_BASE_PATH', 
                     'SQL_OUTPUT_MODE', 'SQL_OUTPUT_DATE_FORMAT',
                     'TEMP_FILE_CLEANUP_ENABLED', 'TEMP_FILE_RETENTION_HOURS']
    
    for key in required_keys:
        if key not in cfg:
            errors.append(f"缺少必需配置项: {key}")
    
    # 检查MERGE_MODULES完整性
    if 'MERGE_MODULES' in cfg:
        default_modules = set(DEFAULT['MERGE_MODULES'].keys())
        config_modules = set(cfg['MERGE_MODULES'].keys())
        missing_modules = default_modules - config_modules
        
        if missing_modules:
            warnings.append(f"MERGE_MODULES缺少模块: {missing_modules}")
        
        # 检查模块值类型
        for mod_name, mod_val in cfg['MERGE_MODULES'].items():
            if not isinstance(mod_val, bool):
                errors.append(f"MERGE_MODULES.{mod_name} 值类型错误，应为bool")
    
    # 检查值类型
    if 'MERGE_MAX_IN_SIZE' in cfg and not isinstance(cfg['MERGE_MAX_IN_SIZE'], int):
        errors.append("MERGE_MAX_IN_SIZE 应为整数")
    
    if 'TEMP_FILE_RETENTION_HOURS' in cfg and not isinstance(cfg['TEMP_FILE_RETENTION_HOURS'], int):
        errors.append("TEMP_FILE_RETENTION_HOURS 应为整数")
    
    return {
        'valid': len(errors) == 0,
        'errors': errors,
        'warnings': warnings
    }


def get_module_names():
    """获取所有MERGE_MODULES模块名称列表
    
    Returns:
        list: 模块名称列表
    """
    return list(DEFAULT['MERGE_MODULES'].keys())


def _resolve_path(path):
    """解析路径，支持相对路径和绝对路径
    
    Args:
        path: 路径字符串，可以是相对路径（如 ./temp_files）或绝对路径
    
    Returns:
        解析后的绝对路径
    """
    if not path:
        return path
    
    # 如果是绝对路径，直接返回
    if os.path.isabs(path):
        logger.debug(f"[路径解析] 绝对路径: {path}")
        return path
    
    # 相对路径，基于运行时基础目录解析
    base_dir = _get_runtime_base_dir()
    resolved = os.path.normpath(os.path.join(base_dir, path))
    logger.debug(f"[路径解析] 相对路径 '{path}' 解析为: {resolved}")
    return resolved


def get_config():
    """获取配置，从文件读取并与DEFAULT合并，确保配置完整性"""
    p = _path()
    if os.path.exists(p):
        try:
            with open(p, 'r', encoding='utf-8') as f:
                data = json.load(f)
            # 合并配置：DEFAULT提供基础，data覆盖DEFAULT
            merged = {**DEFAULT, **data}
            
            # 确保MERGE_MODULES包含所有DEFAULT中的模块
            if 'MERGE_MODULES' in merged:
                merged['MERGE_MODULES'] = {**DEFAULT['MERGE_MODULES'], **merged.get('MERGE_MODULES', {})}
            
            # 解析SQL输出路径为绝对路径
            if 'SQL_OUTPUT_BASE_PATH' in merged:
                merged['SQL_OUTPUT_BASE_PATH'] = _resolve_path(merged['SQL_OUTPUT_BASE_PATH'])
            
            logger.debug(f"[配置加载] 从文件加载配置: {p}")
            return merged
        except Exception as e:
            logger.error(f"[配置加载] 读取配置文件失败: {e}, 使用默认配置")
            config = DEFAULT.copy()
            config['SQL_OUTPUT_BASE_PATH'] = _resolve_path(config['SQL_OUTPUT_BASE_PATH'])
            return config
    logger.debug(f"[配置加载] 配置文件不存在，使用默认配置")
    config = DEFAULT.copy()
    config['SQL_OUTPUT_BASE_PATH'] = _resolve_path(config['SQL_OUTPUT_BASE_PATH'])
    return config


def set_config(cfg):
    """保存配置到文件
    
    Args:
        cfg: 完整的配置字典（应该已经包含所有必需的配置项）
    
    Returns:
        保存的配置字典
    """
    if not cfg:
        logger.warning("[配置保存] 传入空配置，使用默认配置")
        cfg = DEFAULT.copy()
    
    # 验证配置完整性
    validation_result = validate_config(cfg)
    if not validation_result['valid']:
        logger.error(f"[配置保存] 配置验证失败: {validation_result['errors']}")
        # 补全缺失的配置项
        for key in DEFAULT:
            if key not in cfg:
                cfg[key] = DEFAULT[key]
                logger.warning(f"[配置保存] 补全缺失配置项: {key}")
    
    p = _path()
    
    # 保存前日志
    logger.info(f"[配置保存] 准备保存配置到: {p}")
    logger.debug(f"[配置保存] 配置内容: {cfg}")
    
    try:
        # 原子性写入：先写临时文件，成功后重命名
        temp_path = p + '.tmp'
        with open(temp_path, 'w', encoding='utf-8') as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
        
        # 重命名为正式文件
        if os.path.exists(p):
            os.replace(temp_path, p)
        else:
            os.rename(temp_path, p)
        
        logger.info(f"[配置保存] 配置保存成功")
        
        # 保存后验证
        saved_cfg = get_config()
        if saved_cfg.get('MERGE_MODULES') != cfg.get('MERGE_MODULES'):
            logger.error(f"[配置保存] 验证失败：保存的配置与预期不一致")
        else:
            logger.debug(f"[配置保存] 验证成功：配置已正确保存")
        
        return cfg
    except Exception as e:
        logger.error(f"[配置保存] 保存失败: {e}", exc_info=True)
        # 清理临时文件
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except:
                pass
        raise
