#!/usr/bin/env python3
"""
Stone量化交易系统 - 快速开始
"""

import sys
import os
from datetime import datetime, timedelta

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# 导入项目模块
from data.database import DatabaseManager
from utils.real_data_fetcher import RealDataFetcher
from backtest.backtest_engine import BacktestEngine
from strategies.double_ma_strategy import DoubleMaStrategy

def main():
    """主函数"""
    print("🚀 欢迎使用Stone量化交易系统！")
    print("=" * 50)
    
    print("\n📋 可用功能:")
    print("1. 🔥 高换手率股票回测系统")
    print("2. 📊 策略回测引擎")
    print("3. 📈 技术指标计算")
    
    print("\n🎯 推荐开始方式:")
    print("1. 快速测试高换手率系统:")
    print("   cd examples && python quick_turnover_test.py")
    
    print("\n2. 交互式演示:")
    print("   cd examples && python demo_high_turnover.py")
    
    print("\n3. 完整回测:")
    print("   cd examples && python high_turnover_backtest.py")
    
    print("\n📚 文档:")
    print("- README.md - 项目总览")
    print("- docs/HIGH_TURNOVER_GUIDE.md - 详细使用指南")
    print("- docs/SUMMARY.md - 项目总结")
    
    print("\n" + "=" * 50)
    print("开始您的量化交易之旅吧！🎉")

if __name__ == "__main__":
    main() 