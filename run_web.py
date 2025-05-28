#!/usr/bin/env python3
"""
Stone量化交易系统 - Web应用启动脚本
"""

import os
import sys
import webbrowser
import time
import threading
from pathlib import Path

def main():
    """启动Web应用"""
    # 获取项目根目录
    project_root = Path(__file__).parent
    
    print("🌐 Stone量化交易系统 - Web界面")
    print("=" * 60)
    print("正在启动Web服务器...")
    print("=" * 60)
    
    # 检查依赖
    try:
        import flask
        import flask_socketio
        import plotly
        print("✅ 依赖检查通过")
    except ImportError as e:
        print(f"❌ 缺少依赖: {e}")
        print("请运行: pip install flask flask-socketio plotly")
        return
    
    # 检查必要文件
    web_app_file = project_root / "web_app.py"
    if not web_app_file.exists():
        print(f"❌ Web应用文件不存在: {web_app_file}")
        return
    
    template_file = project_root / "templates" / "index.html"
    if not template_file.exists():
        print(f"❌ 模板文件不存在: {template_file}")
        return
    
    print("✅ 文件检查通过")
    
    # 显示访问信息
    print("\n📋 访问信息:")
    print("  本地访问: http://localhost:8081")
    print("  局域网访问: http://你的IP地址:8081")
    print("\n🎯 功能特性:")
    print("  • 实时股票价格监控")
    print("  • 策略信号实时推送")
    print("  • 持仓信息动态更新")
    print("  • 交互式图表展示")
    print("  • 策略表现分析")
    
    print("\n🔧 控制操作:")
    print("  • 开始/停止监控")
    print("  • 手动执行策略")
    print("  • 实时数据刷新")
    
    print("\n" + "=" * 60)
    
    # 询问是否自动打开浏览器
    auto_open = input("是否自动打开浏览器? (y/n, 默认y): ").lower().strip()
    if auto_open != 'n':
        # 延迟打开浏览器
        def open_browser():
            time.sleep(2)
            webbrowser.open('http://localhost:8081')
        
        browser_thread = threading.Thread(target=open_browser)
        browser_thread.daemon = True
        browser_thread.start()
    
    print("\n🚀 启动Web服务器...")
    print("按 Ctrl+C 停止服务器")
    print("-" * 60)
    
    try:
        # 启动Web应用
        os.chdir(str(project_root))
        os.system(f"{sys.executable} web_app.py")
        
    except KeyboardInterrupt:
        print("\n⏹️  服务器已停止")
    except Exception as e:
        print(f"❌ 启动失败: {e}")

if __name__ == "__main__":
    main() 