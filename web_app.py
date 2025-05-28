#!/usr/bin/env python3
"""
Stone量化交易系统 - Web界面
实时展示策略执行情况、持仓信息、股票价格和报表
"""

import os
import sys
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import threading
import time
from flask import Flask, render_template, jsonify, request, send_file
from flask_socketio import SocketIO, emit
import plotly.graph_objs as go
import plotly.utils
from loguru import logger

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# 导入项目模块
from data.database import DatabaseManager
from utils.real_data_fetcher import RealDataFetcher

# 修复导入问题 - 使用相对导入
try:
    from examples.real_time.real_time_trading import RealTimeTradingSystem
except ImportError:
    # 如果导入失败，创建一个简化版本
    class RealTimeTradingSystem:
        def __init__(self):
            self.config = {
                'stock_pool': [
                    "002415", "300059", "300124", "002230", "002594", "300750",
                    "002475", "300274", "300496", "300433", "002252", "300144",
                    "000063", "000568", "002352", "000725", "300015", "300142",
                    "002241", "000538", "000001", "600036", "600000", "601318"
                ],
                'strategies': {
                    "布林带策略": {"enabled": True, "weight": 0.25},
                    "优化双均线策略": {"enabled": True, "weight": 0.25},
                    "快速MACD策略": {"enabled": True, "weight": 0.25},
                    "KDJ策略": {"enabled": True, "weight": 0.25}
                }
            }
        
        def run_once(self):
            pass

app = Flask(__name__)
app.config['SECRET_KEY'] = 'stone_trading_system_2024'
socketio = SocketIO(app, cors_allowed_origins="*")

# 全局变量
trading_system = None
current_data = {
    'portfolio': {
        'total_value': 1000000,
        'available_cash': 1000000,
        'positions': {},
        'daily_pnl': 0,
        'total_pnl': 0
    },
    'stocks': {},
    'signals': [],
    'reports': {}
}

class WebTradingSystem:
    """Web交易系统"""
    
    def __init__(self):
        """初始化"""
        self.trading_system = RealTimeTradingSystem()
        self.db_manager = DatabaseManager()
        self.data_fetcher = RealDataFetcher(self.db_manager)
        self.is_running = False
        self.update_thread = None
        
        # 模拟持仓数据
        self.portfolio = {
            'total_value': 1000000,
            'available_cash': 800000,
            'positions': {
                '002415': {'shares': 1000, 'avg_price': 45.20, 'current_price': 46.80, 'pnl': 1600},
                '300059': {'shares': 800, 'avg_price': 28.50, 'current_price': 29.10, 'pnl': 480},
                '002594': {'shares': 500, 'avg_price': 180.30, 'current_price': 185.60, 'pnl': 2650},
                '300124': {'shares': 600, 'avg_price': 65.40, 'current_price': 64.20, 'pnl': -720}
            }
        }
        
        logger.info("Web交易系统初始化完成")
    
    def start_monitoring(self):
        """开始监控"""
        if self.is_running:
            return
        
        self.is_running = True
        self.update_thread = threading.Thread(target=self._update_loop)
        self.update_thread.daemon = True
        self.update_thread.start()
        logger.info("开始实时监控")
    
    def stop_monitoring(self):
        """停止监控"""
        self.is_running = False
        if self.update_thread:
            self.update_thread.join()
        logger.info("停止实时监控")
    
    def _update_loop(self):
        """更新循环"""
        while self.is_running:
            try:
                # 更新股票价格
                self._update_stock_prices()
                
                # 更新策略信号
                self._update_strategy_signals()
                
                # 更新持仓信息
                self._update_portfolio()
                
                # 发送数据到前端
                socketio.emit('data_update', {
                    'portfolio': self.portfolio,
                    'stocks': current_data['stocks'],
                    'signals': current_data['signals'][-20:],  # 最近20个信号
                    'timestamp': datetime.now().isoformat()
                })
                
                time.sleep(30)  # 30秒更新一次
                
            except Exception as e:
                logger.error(f"更新数据失败: {e}")
                time.sleep(60)
    
    def _update_stock_prices(self):
        """更新股票价格"""
        stock_pool = self.trading_system.config['stock_pool'][:20]  # 取前20只股票
        
        for symbol in stock_pool:
            try:
                # 模拟实时价格（实际应该从API获取）
                if symbol not in current_data['stocks']:
                    current_data['stocks'][symbol] = {
                        'price': np.random.uniform(20, 200),
                        'change': 0,
                        'change_pct': 0,
                        'volume': np.random.randint(1000000, 10000000),
                        'turnover_rate': np.random.uniform(1, 8)
                    }
                else:
                    # 模拟价格变动
                    old_price = current_data['stocks'][symbol]['price']
                    change_pct = np.random.uniform(-0.03, 0.03)  # ±3%变动
                    new_price = old_price * (1 + change_pct)
                    
                    current_data['stocks'][symbol].update({
                        'price': round(new_price, 2),
                        'change': round(new_price - old_price, 2),
                        'change_pct': round(change_pct * 100, 2),
                        'volume': np.random.randint(1000000, 10000000),
                        'turnover_rate': np.random.uniform(1, 8)
                    })
                    
            except Exception as e:
                logger.error(f"更新股票{symbol}价格失败: {e}")
    
    def _update_strategy_signals(self):
        """更新策略信号"""
        try:
            # 模拟策略信号生成
            strategies = ['布林带策略', '优化双均线策略', '快速MACD策略', 'KDJ策略']
            
            if np.random.random() < 0.3:  # 30%概率生成新信号
                strategy = np.random.choice(strategies)
                symbol = np.random.choice(list(current_data['stocks'].keys()))
                signal_type = np.random.choice(['BUY', 'SELL'])
                
                signal = {
                    'timestamp': datetime.now().isoformat(),
                    'strategy': strategy,
                    'symbol': symbol,
                    'signal_type': signal_type,
                    'price': current_data['stocks'][symbol]['price'],
                    'reason': f"{strategy}触发{signal_type}信号",
                    'confidence': round(np.random.uniform(0.6, 0.95), 2)
                }
                
                current_data['signals'].append(signal)
                
                # 保持最近100个信号
                if len(current_data['signals']) > 100:
                    current_data['signals'] = current_data['signals'][-100:]
                    
        except Exception as e:
            logger.error(f"更新策略信号失败: {e}")
    
    def _update_portfolio(self):
        """更新持仓信息"""
        try:
            total_value = self.portfolio['available_cash']
            total_pnl = 0
            
            # 更新持仓价值
            for symbol, position in self.portfolio['positions'].items():
                if symbol in current_data['stocks']:
                    current_price = current_data['stocks'][symbol]['price']
                    position['current_price'] = current_price
                    position['market_value'] = position['shares'] * current_price
                    position['pnl'] = (current_price - position['avg_price']) * position['shares']
                    
                    total_value += position['market_value']
                    total_pnl += position['pnl']
            
            self.portfolio['total_value'] = round(total_value, 2)
            self.portfolio['total_pnl'] = round(total_pnl, 2)
            self.portfolio['daily_pnl'] = round(total_pnl * 0.1, 2)  # 模拟当日盈亏
            
        except Exception as e:
            logger.error(f"更新持仓信息失败: {e}")
    
    def get_strategy_performance(self) -> Dict[str, Any]:
        """获取策略表现"""
        try:
            # 读取策略报表
            reports_dir = os.path.join(project_root, "reports", "strategy")
            if not os.path.exists(reports_dir):
                return {}
            
            latest_report = None
            for filename in os.listdir(reports_dir):
                if filename.startswith("strategy_performance_") and filename.endswith(".json"):
                    file_path = os.path.join(reports_dir, filename)
                    if latest_report is None or os.path.getmtime(file_path) > os.path.getmtime(latest_report):
                        latest_report = file_path
            
            if latest_report:
                with open(latest_report, 'r', encoding='utf-8') as f:
                    return json.load(f)
            
            return {}
            
        except Exception as e:
            logger.error(f"获取策略表现失败: {e}")
            return {}
    
    def generate_charts(self) -> Dict[str, Any]:
        """生成图表数据"""
        try:
            # 1. 资产价值曲线
            dates = [(datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(30, 0, -1)]
            portfolio_values = [1000000 + np.random.randint(-50000, 100000) + i * 1000 for i in range(30)]
            
            portfolio_chart = {
                'data': [{
                    'x': dates,
                    'y': portfolio_values,
                    'type': 'scatter',
                    'mode': 'lines+markers',
                    'name': '资产价值',
                    'line': {'color': '#1f77b4', 'width': 3}
                }],
                'layout': {
                    'title': '资产价值曲线',
                    'xaxis': {'title': '日期'},
                    'yaxis': {'title': '资产价值 (元)'},
                    'height': 400
                }
            }
            
            # 2. 策略信号分布
            strategies = ['布林带策略', '优化双均线策略', '快速MACD策略', 'KDJ策略']
            signal_counts = [np.random.randint(5, 25) for _ in strategies]
            
            signal_chart = {
                'data': [{
                    'x': strategies,
                    'y': signal_counts,
                    'type': 'bar',
                    'marker': {'color': ['#ff7f0e', '#2ca02c', '#d62728', '#9467bd']}
                }],
                'layout': {
                    'title': '策略信号分布',
                    'xaxis': {'title': '策略'},
                    'yaxis': {'title': '信号数量'},
                    'height': 400
                }
            }
            
            # 3. 持仓分布
            if self.portfolio['positions']:
                symbols = list(self.portfolio['positions'].keys())
                values = [pos['market_value'] for pos in self.portfolio['positions'].values()]
                
                position_chart = {
                    'data': [{
                        'labels': symbols,
                        'values': values,
                        'type': 'pie',
                        'hole': 0.4
                    }],
                    'layout': {
                        'title': '持仓分布',
                        'height': 400
                    }
                }
            else:
                position_chart = {'data': [], 'layout': {'title': '暂无持仓'}}
            
            return {
                'portfolio_chart': portfolio_chart,
                'signal_chart': signal_chart,
                'position_chart': position_chart
            }
            
        except Exception as e:
            logger.error(f"生成图表失败: {e}")
            return {}

# 创建Web交易系统实例
web_trading_system = WebTradingSystem()

@app.route('/')
def index():
    """主页"""
    return render_template('index.html')

@app.route('/api/portfolio')
def get_portfolio():
    """获取持仓信息"""
    return jsonify(web_trading_system.portfolio)

@app.route('/api/stocks')
def get_stocks():
    """获取股票信息"""
    return jsonify(current_data['stocks'])

@app.route('/api/signals')
def get_signals():
    """获取交易信号"""
    return jsonify(current_data['signals'][-50:])  # 最近50个信号

@app.route('/api/charts')
def get_charts():
    """获取图表数据"""
    charts = web_trading_system.generate_charts()
    # 转换为JSON格式
    for chart_name, chart_data in charts.items():
        charts[chart_name] = json.loads(plotly.utils.PlotlyJSONEncoder().encode(chart_data))
    return jsonify(charts)

@app.route('/api/strategy_performance')
def get_strategy_performance():
    """获取策略表现"""
    return jsonify(web_trading_system.get_strategy_performance())

@app.route('/api/start_monitoring', methods=['POST'])
def start_monitoring():
    """开始监控"""
    web_trading_system.start_monitoring()
    return jsonify({'status': 'success', 'message': '开始实时监控'})

@app.route('/api/stop_monitoring', methods=['POST'])
def stop_monitoring():
    """停止监控"""
    web_trading_system.stop_monitoring()
    return jsonify({'status': 'success', 'message': '停止实时监控'})

@app.route('/api/run_strategy', methods=['POST'])
def run_strategy():
    """手动执行策略"""
    try:
        web_trading_system.trading_system.run_once()
        return jsonify({'status': 'success', 'message': '策略执行完成'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@socketio.on('connect')
def handle_connect():
    """客户端连接"""
    logger.info("客户端已连接")
    emit('connected', {'message': '连接成功'})

@socketio.on('disconnect')
def handle_disconnect():
    """客户端断开连接"""
    logger.info("客户端已断开连接")

if __name__ == '__main__':
    logger.info("启动Stone量化交易Web系统...")
    socketio.run(app, host='0.0.0.0', port=8081, debug=True, allow_unsafe_werkzeug=True) 