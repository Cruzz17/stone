#!/usr/bin/env python3
"""
增强版真实数据量化交易Web应用
包含详细的持仓显示、实时价格和策略执行状态
"""

import dash
from dash import html, dcc, Input, Output, dash_table
import pandas as pd
from datetime import datetime
from loguru import logger
from trading.simulation_engine import RealSimulationEngine

# 初始化Dash应用
app = dash.Dash(__name__)
app.title = "量化交易系统 - 增强版"

# 全局变量
trading_engine = None


def initialize_trading_engine():
    """初始化交易引擎"""
    global trading_engine
    try:
        logger.info("初始化交易引擎...")

        # 配置数据
        config_data = {
            'trading': {
                'initial_capital': 1000000,
                'max_position_pct': 0.25,
                'max_total_position_pct': 0.90,
                'cash_reserve_pct': 0.10
            },
            'risk_management': {
                'stop_loss': 0.08,
                'take_profit': 0.15,
                'max_daily_loss': 0.05,
                'max_drawdown': 0.20
            },
            'strategies': {
                'double_ma': {'weight': 0.4, 'short_period': 5, 'long_period': 20},
                'rsi': {'weight': 0.3, 'period': 14, 'oversold': 30, 'overbought': 70},
                'macd': {'weight': 0.3, 'fast': 12, 'slow': 26, 'signal': 9}
            },
            'stock_pool': {
                'default_stocks': ['000001', '000002', '600000', '600036', '000858']
            },
            'simulation': {
                'signal_combination': 'weighted_average',
                'min_signal_confidence': 0.6,
                'update_frequency': 60
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
    html.H1("量化交易系统 - 增强版", style={'textAlign': 'center', 'marginBottom': 30}),

    # 控制面板
    html.Div([
        html.Button('启动交易', id='start-btn', n_clicks=0,
                    style={'marginRight': 10, 'backgroundColor': '#28a745', 'color': 'white', 'padding': '10px 20px'}),
        html.Button('停止交易', id='stop-btn', n_clicks=0,
                    style={'marginRight': 10, 'backgroundColor': '#dc3545', 'color': 'white', 'padding': '10px 20px'}),
        html.Button('刷新数据', id='refresh-btn', n_clicks=0,
                    style={'marginRight': 10, 'backgroundColor': '#007bff', 'color': 'white', 'padding': '10px 20px'}),
        html.Div(id='status-display',
                 style={'display': 'inline-block', 'marginLeft': 20, 'fontSize': '16px', 'fontWeight': 'bold'})
    ], style={'textAlign': 'center', 'marginBottom': 30}),

    # 主要内容区域
    html.Div([
        # 左侧列
        html.Div([
            # 实时状态
            html.Div([
                html.H3("实时状态", style={'color': '#333'}),
                html.Div(id='real-time-status',
                         style={'backgroundColor': '#f8f9fa', 'padding': '15px', 'borderRadius': '5px'})
            ], style={'marginBottom': 30}),

            # 投资组合概览
            html.Div([
                html.H3("投资组合概览", style={'color': '#333'}),
                html.Div(id='portfolio-overview',
                         style={'backgroundColor': '#f8f9fa', 'padding': '15px', 'borderRadius': '5px'})
            ], style={'marginBottom': 30}),

            # 实时价格
            html.Div([
                html.H3("实时价格", style={'color': '#333'}),
                html.Div(id='current-prices',
                         style={'backgroundColor': '#f8f9fa', 'padding': '15px', 'borderRadius': '5px'})
            ], style={'marginBottom': 30}),
        ], style={'width': '48%', 'display': 'inline-block', 'verticalAlign': 'top'}),

        # 右侧列
        html.Div([
            # 持仓详情
            html.Div([
                html.H3("持仓详情", style={'color': '#333'}),
                html.Div(id='positions-detail',
                         style={'backgroundColor': '#f8f9fa', 'padding': '15px', 'borderRadius': '5px'})
            ], style={'marginBottom': 30}),

            # 策略执行状态
            html.Div([
                html.H3("策略执行状态", style={'color': '#333'}),
                html.Div(id='strategy-status',
                         style={'backgroundColor': '#f8f9fa', 'padding': '15px', 'borderRadius': '5px'})
            ], style={'marginBottom': 30}),
        ], style={'width': '48%', 'display': 'inline-block', 'verticalAlign': 'top', 'marginLeft': '4%'}),
    ]),

    # 底部区域
    html.Div([
        # 最近交易信号
        html.Div([
            html.H3("最近交易信号", style={'color': '#333'}),
            html.Div(id='recent-signals')
        ], style={'marginBottom': 30}),

        # 最近交易记录
        html.Div([
            html.H3("最近交易记录", style={'color': '#333'}),
            html.Div(id='recent-trades')
        ], style={'marginBottom': 30}),
    ]),

    # 自动刷新
    dcc.Interval(
        id='interval-component',
        interval=5 * 1000,  # 5秒刷新一次
        n_intervals=0
    )
])


@app.callback(
    Output('status-display', 'children'),
    [Input('start-btn', 'n_clicks'),
     Input('stop-btn', 'n_clicks'),
     Input('refresh-btn', 'n_clicks')]
)
def control_trading(start_clicks, stop_clicks, refresh_clicks):
    """控制交易启停和刷新"""
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

    elif button_id == 'refresh-btn' and refresh_clicks > 0:
        return "🔄 数据已刷新"

    return "系统就绪"


@app.callback(
    [Output('real-time-status', 'children'),
     Output('portfolio-overview', 'children'),
     Output('positions-detail', 'children'),
     Output('current-prices', 'children'),
     Output('strategy-status', 'children'),
     Output('recent-signals', 'children'),
     Output('recent-trades', 'children')],
    [Input('interval-component', 'n_intervals'),
     Input('refresh-btn', 'n_clicks')]
)
def update_dashboard(n, refresh_clicks):
    """更新仪表盘数据"""
    global trading_engine

    # 默认内容
    status_content = html.Div("交易引擎未启动")
    portfolio_content = html.Div("无数据")
    positions_content = html.Div("无持仓")
    prices_content = html.Div("无数据")
    strategy_content = html.Div("策略未运行")
    signals_content = html.Div("无数据")
    trades_content = html.Div("无数据")

    if trading_engine:
        try:
            # 获取当前状态
            current_status = trading_engine.get_current_status()

            if current_status:
                portfolio = current_status.get('portfolio_status')
                market = current_status.get('market_status', {})
                current_prices = current_status.get('current_prices', {})

                # 实时状态
                status_content = html.Div([
                    html.P(f"📅 当前时间: {market.get('current_time', 'N/A')}", style={'margin': '5px 0'}),
                    html.P(f"📈 市场状态: {market.get('market_status', 'N/A')}", style={'margin': '5px 0'}),
                    html.P(f"🔄 运行状态: {'运行中' if trading_engine.is_running else '已停止'}", style={'margin': '5px 0'}),
                    html.P(f"📊 总信号数: {current_status.get('total_signals', 0)}", style={'margin': '5px 0'}),
                    html.P(f"💰 总交易数: {current_status.get('total_trades', 0)}", style={'margin': '5px 0'}),
                    html.P(f"🕐 最后更新: {current_status.get('last_update_time', 'N/A')}", style={'margin': '5px 0'})
                ])

                # 投资组合概览
                if portfolio:
                    portfolio_content = html.Div([
                        html.P(f"💼 总资产: ¥{portfolio.total_value:,.2f}",
                               style={'margin': '5px 0', 'fontSize': '16px', 'fontWeight': 'bold'}),
                        html.P(f"💵 现金: ¥{portfolio.cash:,.2f}", style={'margin': '5px 0'}),
                        html.P(f"📈 市值: ¥{portfolio.market_value:,.2f}", style={'margin': '5px 0'}),
                        html.P(f"📊 总盈亏: ¥{portfolio.total_pnl:,.2f} ({portfolio.total_pnl_pct:+.2%})",
                               style={'margin': '5px 0', 'color': 'green' if portfolio.total_pnl >= 0 else 'red',
                                      'fontWeight': 'bold'}),
                        html.P(f"🏢 持仓数: {portfolio.position_count}", style={'margin': '5px 0'})
                    ])

                # 实时价格
                if current_prices:
                    price_data = []
                    for symbol, price in current_prices.items():
                        price_data.append({
                            '股票代码': symbol,
                            '当前价格': f"¥{price:.2f}",
                            '更新时间': datetime.now().strftime('%H:%M:%S')
                        })

                    if price_data:
                        prices_content = dash_table.DataTable(
                            data=price_data,
                            columns=[{"name": i, "id": i} for i in price_data[0].keys()],
                            style_cell={'textAlign': 'center', 'fontSize': '14px'},
                            style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'},
                            style_data={'backgroundColor': 'rgb(248, 249, 250)'}
                        )

                # 策略执行状态
                strategy_content = html.Div([
                    html.P("📈 双均线策略: 权重 40%", style={'margin': '5px 0'}),
                    html.P("📊 RSI策略: 权重 30%", style={'margin': '5px 0'}),
                    html.P("📉 MACD策略: 权重 30%", style={'margin': '5px 0'}),
                    html.P(f"🎯 信号组合方式: 加权平均", style={'margin': '5px 0'}),
                    html.P(f"⚡ 最小信号置信度: 60%", style={'margin': '5px 0'}),
                    html.P(f"🔄 更新频率: 60秒", style={'margin': '5px 0'})
                ])

            # 持仓详情
            try:
                positions_df = trading_engine.get_position_summary()
                if not positions_df.empty:
                    # 格式化持仓数据
                    positions_display = positions_df.copy()

                    # 重命名列
                    column_mapping = {
                        'symbol': '股票代码',
                        'shares': '持股数量',
                        'avg_price': '成本价',
                        'current_price': '当前价',
                        'market_value': '市值',
                        'unrealized_pnl': '浮动盈亏',
                        'unrealized_pnl_pct': '盈亏比例'
                    }

                    for old_col, new_col in column_mapping.items():
                        if old_col in positions_display.columns:
                            positions_display = positions_display.rename(columns={old_col: new_col})

                    # 格式化数值
                    for col in ['成本价', '当前价', '市值', '浮动盈亏']:
                        if col in positions_display.columns:
                            positions_display[col] = positions_display[col].apply(lambda x: f"¥{x:.2f}")

                    if '盈亏比例' in positions_display.columns:
                        positions_display['盈亏比例'] = positions_display['盈亏比例'].apply(lambda x: f"{x:+.2%}")

                    positions_content = dash_table.DataTable(
                        data=positions_display.to_dict('records'),
                        columns=[{"name": i, "id": i} for i in positions_display.columns],
                        style_cell={'textAlign': 'center', 'fontSize': '14px'},
                        style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'},
                        style_data_conditional=[
                            {
                                'if': {'filter_query': '{盈亏比例} contains +'},
                                'backgroundColor': '#d4edda',
                                'color': 'black',
                            },
                            {
                                'if': {'filter_query': '{盈亏比例} contains -'},
                                'backgroundColor': '#f8d7da',
                                'color': 'black',
                            }
                        ]
                    )
                else:
                    positions_content = html.Div("📭 暂无持仓", style={'textAlign': 'center', 'color': '#666'})
            except Exception as e:
                positions_content = html.Div(f"❌ 持仓数据获取失败: {str(e)}")

            # 最近信号
            try:
                signals_df = trading_engine.get_recent_signals(limit=10)
                if not signals_df.empty:
                    signals_content = dash_table.DataTable(
                        data=signals_df.to_dict('records'),
                        columns=[{"name": i, "id": i} for i in signals_df.columns],
                        style_cell={'textAlign': 'left', 'fontSize': '14px'},
                        style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'},
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
                else:
                    signals_content = html.Div("📭 暂无交易信号", style={'textAlign': 'center', 'color': '#666'})
            except Exception as e:
                signals_content = html.Div(f"❌ 信号数据获取失败: {str(e)}")

            # 最近交易
            try:
                trades_df = trading_engine.get_recent_trades(limit=10)
                if not trades_df.empty:
                    trades_content = dash_table.DataTable(
                        data=trades_df.to_dict('records'),
                        columns=[{"name": i, "id": i} for i in trades_df.columns],
                        style_cell={'textAlign': 'left', 'fontSize': '14px'},
                        style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'},
                        style_data_conditional=[
                            {
                                'if': {'filter_query': '{action} = BUY'},
                                'backgroundColor': '#d4edda',
                                'color': 'black',
                            },
                            {
                                'if': {'filter_query': '{action} = SELL'},
                                'backgroundColor': '#f8d7da',
                                'color': 'black',
                            }
                        ]
                    )
                else:
                    trades_content = html.Div("📭 暂无交易记录", style={'textAlign': 'center', 'color': '#666'})
            except Exception as e:
                trades_content = html.Div(f"❌ 交易数据获取失败: {str(e)}")

        except Exception as e:
            status_content = html.Div(f"❌ 状态获取失败: {str(e)}")

    return status_content, portfolio_content, positions_content, prices_content, strategy_content, signals_content, trades_content


if __name__ == '__main__':
    logger.info("启动增强版真实交易Web应用")
    app.run(debug=True, host='0.0.0.0', port=8052)