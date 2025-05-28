#!/usr/bin/env python3
"""
回测系统启动脚本
"""

import os
import sys
import subprocess
from pathlib import Path

def main():
    """启动回测系统"""
    # 获取项目根目录
    project_root = Path(__file__).parent
    
    print("🎯 Stone量化交易回测系统")
    print("=" * 50)
    print("请选择回测类型:")
    print("1. 最大收益回测 (推荐)")
    print("2. 高换手率回测")
    print("3. 快速测试")
    print("4. 演示回测")
    print("=" * 50)
    
    choice = input("请输入选择 (1-4): ").strip()
    
    script_map = {
        "1": "examples/backtest/max_profit_backtest.py",
        "2": "examples/backtest/high_turnover_backtest.py", 
        "3": "examples/backtest/quick_turnover_test.py",
        "4": "examples/backtest/demo_high_turnover.py"
    }
    
    if choice not in script_map:
        print("❌ 无效选择")
        return
    
    script_path = project_root / script_map[choice]
    
    if not script_path.exists():
        print(f"❌ 回测脚本不存在: {script_path}")
        return
    
    script_names = {
        "1": "最大收益回测",
        "2": "高换手率回测",
        "3": "快速测试",
        "4": "演示回测"
    }
    
    print(f"\n🚀 启动{script_names[choice]}...")
    print(f"📁 项目目录: {project_root}")
    print(f"📄 执行脚本: {script_path}")
    print("-" * 60)
    
    try:
        # 执行回测脚本
        subprocess.run([sys.executable, str(script_path)], cwd=str(project_root))
    except KeyboardInterrupt:
        print("\n⏹️  用户中断，回测停止")
    except Exception as e:
        print(f"❌ 回测运行出错: {e}")

if __name__ == "__main__":
    main() 