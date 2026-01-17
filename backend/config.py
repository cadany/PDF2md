"""
配置文件模块
集中管理应用的所有配置参数
"""

import os
import json
import logging
from typing import Any, Optional, Dict

# 配置日志记录器
logger = logging.getLogger(__name__)

# 全局配置实例
_config_instance: Optional['Config'] = None

def _find_default_config() -> Optional[str]:
    """查找默认配置文件"""
    # 查找当前目录下的配置文件，仅支持.conf格式
    possible_files = ['app.conf', 'config.conf']
    
    for filename in possible_files:
        if os.path.exists(filename):
            return filename
    
    return None

class Config:
    """配置类，管理所有应用配置"""
    
    # 默认配置 - 只保留实际使用的配置项
    DEFAULT_CONFIG = {
        # 服务器配置
        'server': {
            'host': '0.0.0.0',
            'port': 18080,
            'debug': False,
            'reload': False,
        },
        
        # 文件存储配置
        'storage': {
            'upload_dir': 'uploads',
        },
        
        # 安全配置
        'security': {
            'cors_origins': ["*"],
        }
    }
    
    def __init__(self, config_file: Optional[str] = None):
        """
        初始化配置
        
        Args:
            config_file: 配置文件路径，如果为None则使用默认配置
        """
        self._config = self.DEFAULT_CONFIG.copy()
        self.config_file = config_file
           
        # 如果指定了配置文件，则从文件加载
        if config_file and os.path.exists(config_file):
            self._load_from_file(config_file)

    def _load_from_file(self, config_file: str):
        """从配置文件加载配置"""
        try:
            if config_file.endswith('.conf'):
                self._load_from_conf(config_file)
            else:
                logger.warning(f"不支持的配置文件格式: {config_file}")
        except Exception as e:
            logger.error(f"配置文件加载失败: {e}")
    
    def _load_from_conf(self, config_file: str):
        """从key=value格式的配置文件加载配置"""
        config_dict = {}
        
        with open(config_file, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                
                # 跳过空行和注释
                if not line or line.startswith('#'):
                    continue
                
                # 解析key=value
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    
                    # 转换值类型
                    if value.lower() in ('true', 'false'):
                        value = value.lower() == 'true'
                    elif value.isdigit():
                        value = int(value)
                    elif value.replace('.', '').replace('-', '').isdigit() and value.count('.') <= 1 and value.count('-') <= 1:
                        # 检查是否是有效的数字（包含小数点和负号）
                        try:
                            value = float(value)
                            if value.is_integer():
                                value = int(value)
                        except ValueError:
                            pass  # 保持为字符串
                    elif ',' in value:
                        value = [v.strip() for v in value.split(',')]
                    
                    # 构建嵌套字典
                    keys = key.split('.')
                    current_dict = config_dict
                    
                    for k in keys[:-1]:
                        if k not in current_dict:
                            current_dict[k] = {}
                        current_dict = current_dict[k]
                    
                    current_dict[keys[-1]] = value
                else:
                    logger.warning(f"配置文件第{line_num}行格式错误: {line}")
        
        # 深度合并配置
        self._merge_config(self._config, config_dict)
        logger.info(f"配置文件加载成功: {config_file}")
    
    def _merge_config(self, base: Dict[str, Any], update: Dict[str, Any]):
        """深度合并配置字典"""
        for key, value in update.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._merge_config(base[key], value)
            else:
                base[key] = value
    
    def get(self, key: str, default=None) -> Any:
        """获取配置值"""
        keys = key.split('.')
        value = self._config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def set(self, key: str, value: Any):
        """设置配置值"""
        keys = key.split('.')
        config = self._config
        
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        config[keys[-1]] = value
    
    def save_to_file(self, config_file: Optional[str] = None):
        """保存配置到文件"""
        if config_file is None:
            config_file = self.config_file
        
        if config_file:
            try:
                with open(config_file, 'w', encoding='utf-8') as f:
                    json.dump(self._config, f, indent=2, ensure_ascii=False)
            except Exception as e:
                logger.error(f"保存配置文件失败: {e}")
    
    def get_server_config(self) -> Dict[str, Any]:
        """获取服务器配置"""
        return self._config.get('server', {})
    
    def __str__(self) -> str:
        """返回配置的字符串表示"""
        return json.dumps(self._config, indent=2, ensure_ascii=False)


# 全局配置实例
_config_instance: Optional[Config] = None


def get_config(config_file: Optional[str] = None) -> Config:
    """
    获取全局配置实例
    
    Args:
        config_file: 配置文件路径
        
    Returns:
        Config: 配置实例
    """
    global _config_instance
    
    if _config_instance is None:
        # 如果没有指定配置文件，自动查找默认配置文件
        if config_file is None:
            config_file = _find_default_config()
        _config_instance = Config(config_file)
    
    return _config_instance


def init_config(config_file: Optional[str] = None) -> Config:
    """
    初始化全局配置
    
    Args:
        config_file: 配置文件路径
        
    Returns:
        Config: 配置实例
    """
    global _config_instance
    _config_instance = Config(config_file)
    return _config_instance