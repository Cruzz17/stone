"""
配置加载器模块
用于加载和管理系统配置文件
"""

import yaml
import os
from typing import Dict, Any
from loguru import logger


class ConfigLoader:
    """配置加载器类"""
    
    def __init__(self, config_path: str = "config/config.yaml"):
        """
        初始化配置加载器
        
        Args:
            config_path: 配置文件路径
        """
        self.config_path = config_path
        self.config = {}
        self.load_config()
    
    def load_config(self) -> None:
        """加载配置文件"""
        try:
            if not os.path.exists(self.config_path):
                # 如果配置文件不存在，尝试复制示例配置
                example_path = "config/config.example.yaml"
                if os.path.exists(example_path):
                    import shutil
                    shutil.copy(example_path, self.config_path)
                    logger.info(f"已复制示例配置文件到 {self.config_path}")
                else:
                    raise FileNotFoundError(f"配置文件不存在: {self.config_path}")
            
            with open(self.config_path, 'r', encoding='utf-8') as file:
                self.config = yaml.safe_load(file)
            
            logger.info(f"配置文件加载成功: {self.config_path}")
            
        except Exception as e:
            logger.error(f"配置文件加载失败: {e}")
            raise
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置值
        
        Args:
            key: 配置键，支持点号分隔的嵌套键
            default: 默认值
            
        Returns:
            配置值
        """
        keys = key.split('.')
        value = self.config
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
    
    def set(self, key: str, value: Any) -> None:
        """
        设置配置值
        
        Args:
            key: 配置键
            value: 配置值
        """
        keys = key.split('.')
        config = self.config
        
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        config[keys[-1]] = value
    
    def save_config(self) -> None:
        """保存配置到文件"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as file:
                yaml.dump(self.config, file, default_flow_style=False, 
                         allow_unicode=True, indent=2)
            logger.info(f"配置文件保存成功: {self.config_path}")
        except Exception as e:
            logger.error(f"配置文件保存失败: {e}")
            raise
    
    def get_data_source_config(self) -> Dict[str, Any]:
        """获取数据源配置"""
        return self.get('data_sources', {})
    
    def get_trading_config(self) -> Dict[str, Any]:
        """获取交易配置"""
        return self.get('trading', {})
    
    def get_risk_config(self) -> Dict[str, Any]:
        """获取风险管理配置"""
        return self.get('risk_management', {})
    
    def get_strategy_config(self) -> Dict[str, Any]:
        """获取策略配置"""
        return self.get('strategies', {})
    
    def get_backtest_config(self) -> Dict[str, Any]:
        """获取回测配置"""
        return self.get('backtest', {})
    
    def get_web_config(self) -> Dict[str, Any]:
        """获取Web配置"""
        return self.get('web', {})
    
    def get_api_config(self) -> Dict[str, Any]:
        """获取API配置"""
        return self.get('api', {})
    
    def get_stock_pool_config(self) -> Dict[str, Any]:
        """获取股票池配置"""
        return self.get('stock_pool', {})


# 全局配置实例
config = ConfigLoader() 