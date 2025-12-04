import json
import os
from django.conf import settings

DEFAULT = {
    'MERGE_MAX_IN_SIZE': 500,
    'MERGE_MODULES': {
        'price': True,
        'item': True,
        'unit': True,
        'budget': True,
        'gov': True,
        'importance': True,
        'enddate': True,
        'erp': True,
        'price_type': True,
    }
}

def _path():
    base = getattr(settings, 'BASE_DIR', os.getcwd())
    cfg_dir = os.path.join(base, 'config')
    os.makedirs(cfg_dir, exist_ok=True)
    return os.path.join(cfg_dir, 'app_config.json')

def get_config():
    p = _path()
    if os.path.exists(p):
        try:
            with open(p, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return {**DEFAULT, **data}
        except Exception:
            return DEFAULT.copy()
    return DEFAULT.copy()

def set_config(cfg):
    data = {**DEFAULT, **(cfg or {})}
    p = _path()
    with open(p, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return data
