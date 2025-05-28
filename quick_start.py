#!/usr/bin/env python3
"""
快速启动脚本 - 测试量化交易系统
"""

import sys
import os
from loguru import logger


def test_imports():
    """测试所有核心模块导入"""
    try:
        logger.info("测试模块导入...")

        # 测试配置加载
        from utils.config_loader import ConfigLoader
        logger.info("✅ 配置加载模块导入成功")

        # 测试数据获取
        from utils.real_data_fetcher import RealDataFetcher
        logger.info("✅ 真实数据获取模块导入成功")

        # 测试策略模块
        from strategies.double_ma_strategy import DoubleMaStrategy
        from strategies.rsi_strategy import RSIStrategy
        from strategies.macd_strategy import MACDStrategy
        logger.info("✅ 策略模块导入成功")

        # 测试交易引擎
        from trading.simulation_engine import RealSimulationEngine
        logger.info("✅ 交易引擎导入成功")

        # 测试数据库
        from data.database import DatabaseManager
        logger.info("✅ 数据库模块导入成功")

        return True

    except Exception as e:
        logger.error(f"❌ 模块导入失败: {e}")
        return False


def test_config():
    """测试配置文件"""
    try:
        logger.info("测试配置文件...")
        from utils.config_loader import ConfigLoader

        config_loader = ConfigLoader('config/config.yaml')
        config = config_loader.config

        logger.info(f"✅ 配置加载成功，初始资金: {config.get('trading', {}).get('initial_capital', 'N/A')}")
        return True

    except Exception as e:
        logger.error(f"❌ 配置测试失败: {e}")
        return False


def test_database():
    """测试数据库连接"""
    try:
        logger.info("测试数据库连接...")
        from data.database import DatabaseManager

        db = DatabaseManager()
        # DatabaseManager在初始化时会自动调用_init_database()

        logger.info("✅ 数据库连接成功")
        return True

    except Exception as e:
        logger.error(f"❌ 数据库测试失败: {e}")
        return False


def main():
    """主函数"""
    logger.info("🚀 开始系统测试...")

    # 测试导入
    if not test_imports():
        logger.error("❌ 导入测试失败，请检查依赖")
        return False

    # 测试配置
    if not test_config():
        logger.error("❌ 配置测试失败，请检查配置文件")
        return False

    # 测试数据库
    if not test_database():
        logger.error("❌ 数据库测试失败")
        return False

    logger.info("🎉 所有测试通过！系统准备就绪")
    logger.info("💡 使用以下命令启动系统:")
    logger.info("   python run_real_trading.py  # 启动命令行交易")
    logger.info("   python app_real_trading.py  # 启动Web界面")

    return True


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)