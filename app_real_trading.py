#!/usr/bin/env python3
"""
真实交易数据Web应用
"""

import dash
from dash import dcc, html, Input, Output, dash_table
import plotly.graph_objs as go
import plotly.express as px
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import threading
import time
from loguru import logger

from utils.config_loader import config
from trading.simulation_engine import RealSimulationEngine
from data.database import DatabaseManager

# 初始化应用
app = dash.Dash(__name__)
app.title = "真实数据量化交易系统"

# 全局变量
trading_engine = None
db_manager = DatabaseManager()

def initialize_trading_engine():
    """初始化交易引擎"""
    global trading_engine
    try:
        config_data = config.config
        if config_data is None:
            config_data = {
                'trading': {'initial_capital': 100000},
                'position_management': {
                    'max_single_position': 0.25,
                    'max_total_position': 0.90,
                    'cash_reserve': 0.10
                },
                'risk_management': {
                    'stop_loss': 0.08,
                    'take_profit': 0.15
                },
                'strategies': {
                    'double_ma': {'weight': 0.4},
                    'rsi': {'weight': 0.3},
                    'macd': {'weight': 0.3}
                },
                'stock_pool': {
                    'default_stocks': ['000001', '000002', '600000', '600036', '000858']
                },
                'simulation': {
                    'signal_combination': 'weighted_average',
                    'min_signal_confidence': 0.6
                }
            }
        
        trading_engine = RealSimulationEngine(config_data)
        logger.info("交易引擎初始化成功")
        return True
    except Exception as e:
        logger.error(f"交易引擎初始化失败: {e}")
        return False

# 页面布局
app.layout = html.Div([
    html.H1("真实数据量化交易系统", style={'textAlign': 'center', 'marginBottom': 30}),
    
    # 控制面板
    html.Div([
        html.Button('启动交易', id='start-btn', n_clicks=0, 
                   style={'marginRight': 10, 'backgroundColor': '#28a745', 'color': 'white'}),
        html.Button('停止交易', id='stop-btn', n_clicks=0,
                   style={'marginRight': 10, 'backgroundColor': '#dc3545', 'color': 'white'}),
        html.Div(id='status-display', style={'display': 'inline-block', 'marginLeft': 20})
    ], style={'textAlign': 'center', 'marginBottom': 30}),
    
    # 实时状态
    html.Div([
        html.H3("实时状态"),
        html.Div(id='real-time-status')
    ], style={'marginBottom': 30}),
    
    # 投资组合概览
    html.Div([
        html.H3("投资组合概览"),
        html.Div(id='portfolio-overview')
    ], style={'marginBottom': 30}),
    
    # 最近交易信号
    html.Div([
        html.H3("最近交易信号"),
        html.Div(id='recent-signals')
    ], style={'marginBottom': 30}),
    
    # 最近交易记录
    html.Div([
        html.H3("最近交易记录"),
        html.Div(id='recent-trades')
    ], style={'marginBottom': 30}),
    
    # 自动刷新
    dcc.Interval(
        id='interval-component',
        interval=5*1000,  # 5秒刷新一次
        n_intervals=0
    )
])

@app.callback(
    Output('status-display', 'children'),
    [Input('start-btn', 'n_clicks'),
     Input('stop-btn', 'n_clicks')]
)
def control_trading(start_clicks, stop_clicks):
    """控制交易启停"""
    global trading_engine
    
    ctx = dash.callback_context
    if not ctx.triggered:
        return "系统就绪"
    
    button_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    if button_id == 'start-btn' and start_clicks > 0:
        if trading_engine is None:
            if not initialize_trading_engine():
                return "❌ 引擎初始化失败"
        
        try:
            if not trading_engine.is_running:
                trading_engine.start_simulation()
                return "✅ 交易已启动"
            else:
                return "⚠️ 交易已在运行"
        except Exception as e:
            return f"❌ 启动失败: {str(e)}"
    
    elif button_id == 'stop-btn' and stop_clicks > 0:
        if trading_engine and trading_engine.is_running:
            try:
                trading_engine.stop_simulation()
                return "⏹️ 交易已停止"
            except Exception as e:
                return f"❌ 停止失败: {str(e)}"
        else:
            return "⚠️ 交易未运行"
    
    return "系统就绪"

@app.callback(
    [Output('real-time-status', 'children'),
     Output('portfolio-overview', 'children'),
     Output('recent-signals', 'children'),
     Output('recent-trades', 'children')],
    [Input('interval-component', 'n_intervals')]
)
def update_dashboard(n):
    """更新仪表盘数据"""
    global trading_engine
    
    # 实时状态
    status_content = html.Div("交易引擎未启动")
    portfolio_content = html.Div("无数据")
    signals_content = html.Div("无数据")
    trades_content = html.Div("无数据")
    
    if trading_engine:
        try:
            # 获取当前状态
            current_status = trading_engine.get_current_status()
            
            if current_status:
                portfolio = current_status.get('portfolio_status')
                market = current_status.get('market_status', {})
                
                # 实时状态
                status_content = html.Div([
                    html.P(f"当前时间: {market.get('current_time', 'N/A')}"),
                    html.P(f"市场状态: {market.get('market_status', 'N/A')}"),
                    html.P(f"运行状态: {'运行中' if trading_engine.is_running else '已停止'}"),
                    html.P(f"总信号数: {current_status.get('total_signals', 0)}"),
                    html.P(f"总交易数: {current_status.get('total_trades', 0)}")
                ])
                
                # 投资组合概览
                if portfolio:
                    portfolio_content = html.Div([
                        html.P(f"总资产: ¥{portfolio.total_value:,.2f}"),
                        html.P(f"现金: ¥{portfolio.cash:,.2f}"),
                        html.P(f"市值: ¥{portfolio.market_value:,.2f}"),
                        html.P(f"总盈亏: ¥{portfolio.total_pnl:,.2f} ({portfolio.total_pnl_pct:+.2%})"),
                        html.P(f"持仓数: {portfolio.position_count}")
                    ])
            
            # 最近信号
            try:
                signals_df = trading_engine.get_recent_signals(limit=10)
                if not signals_df.empty:
                    signals_content = dash_table.DataTable(
                        data=signals_df.to_dict('records'),
                        columns=[{"name": i, "id": i} for i in signals_df.columns],
                        style_cell={'textAlign': 'left'},
                        style_data_conditional=[
                            {
                                'if': {'filter_query': '{signal_type} = BUY'},
                                'backgroundColor': '#d4edda',
                                'color': 'black',
                            },
                            {
                                'if': {'filter_query': '{signal_type} = SELL'},
                                'backgroundColor': '#f8d7da',
                                'color': 'black',
                            }
                        ]
                    )
            except Exception as e:
                signals_content = html.Div(f"信号数据获取失败: {str(e)}")
            
            # 最近交易
            try:
                trades_df = trading_engine.get_recent_trades(limit=10)
                if not trades_df.empty:
                    trades_content = dash_table.DataTable(
                        data=trades_df.to_dict('records'),
                        columns=[{"name": i, "id": i} for i in trades_df.columns],
                        style_cell={'textAlign': 'left'}
                    )
            except Exception as e:
                trades_content = html.Div(f"交易数据获取失败: {str(e)}")
                
        except Exception as e:
            status_content = html.Div(f"状态获取失败: {str(e)}")
    
    return status_content, portfolio_content, signals_content, trades_content

if __name__ == '__main__':
    logger.info("启动真实交易Web应用")
    app.run(debug=True, host='0.0.0.0', port=8051)
