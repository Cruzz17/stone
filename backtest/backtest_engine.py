"""
回测引擎
用于执行策略回测和性能分析
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import seaborn as sns
from loguru import logger

from strategies.base_strategy import BaseStrategy, Signal
from utils.real_data_fetcher import RealDataFetcher


class BacktestEngine:
    """回测引擎"""
    
    def __init__(self, 
                 initial_capital: float = 100000,
                 commission_rate: float = 0.0003,
                 stamp_tax_rate: float = 0.001,
                 min_trade_unit: int = 100):
        """
        初始化回测引擎
        
        Args:
            initial_capital: 初始资金
            commission_rate: 手续费率
            stamp_tax_rate: 印花税率
            min_trade_unit: 最小交易单位
        """
        self.initial_capital = initial_capital
        self.commission_rate = commission_rate
        self.stamp_tax_rate = stamp_tax_rate
        self.min_trade_unit = min_trade_unit
        
        # 回测状态
        self.current_capital = initial_capital
        self.positions = {}  # 持仓信息
        self.trades = []     # 交易记录
        self.daily_returns = []  # 每日收益
        self.portfolio_values = []  # 组合价值历史
        
        # 性能指标
        self.performance_metrics = {}
        
        logger.info(f"回测引擎初始化完成，初始资金: {initial_capital:,.2f}")
    
    def run_backtest(self, 
                    strategy: BaseStrategy,
                    symbols: List[str],
                    start_date: str,
                    end_date: str,
                    data_fetcher: Optional[RealDataFetcher] = None,
                    historical_data: Optional[Dict[str, pd.DataFrame]] = None,
                    benchmark: str = "000001.SH") -> Dict[str, Any]:
        """
        运行回测
        
        Args:
            strategy: 交易策略
            symbols: 股票代码列表
            start_date: 开始日期
            end_date: 结束日期
            data_fetcher: 数据获取器（可选）
            historical_data: 历史数据字典（可选）
            benchmark: 基准指数
            
        Returns:
            回测结果
        """
        logger.info(f"开始回测: {strategy.name}, 股票: {symbols}, 期间: {start_date} - {end_date}")
        
        # 重置回测状态
        self._reset_backtest()
        
        # 获取基准数据（如果有数据获取器的话）
        benchmark_data = pd.DataFrame()
        if data_fetcher:
            try:
                benchmark_data = data_fetcher.get_index_data(benchmark, start_date, end_date)
            except:
                logger.warning("无法获取基准数据，将使用空基准")
        
        # 为每个股票运行回测
        all_signals = []
        stock_data = {}
        
        for symbol in symbols:
            try:
                # 获取股票数据
                if historical_data and symbol in historical_data:
                    # 使用提供的历史数据
                    data = historical_data[symbol].copy()
                elif data_fetcher:
                    # 使用数据获取器
                    data = data_fetcher.get_stock_data(symbol, start_date, end_date)
                else:
                    logger.error(f"没有提供{symbol}的数据源")
                    continue
                
                if data.empty:
                    logger.warning(f"无法获取{symbol}的数据")
                    continue
                
                # 计算技术指标
                if data_fetcher:
                    data = data_fetcher.calculate_technical_indicators(data)
                else:
                    # 如果没有数据获取器，使用简单的技术指标计算
                    data = self._calculate_basic_indicators(data)
                
                stock_data[symbol] = data
                
                # 生成交易信号
                signals = strategy.generate_signals(data, symbol)
                all_signals.extend(signals)
                
                logger.info(f"{symbol}: 生成{len(signals)}个信号")
                
            except Exception as e:
                logger.error(f"处理{symbol}时出错: {e}")
                continue
        
        # 按时间排序信号
        all_signals.sort(key=lambda x: x.timestamp)
        
        # 执行交易
        self._execute_trades(all_signals, stock_data)
        
        # 计算每日组合价值
        self._calculate_daily_portfolio_values(stock_data, start_date, end_date)
        
        # 计算性能指标
        self._calculate_performance_metrics(benchmark_data)
        
        # 生成回测报告
        backtest_result = self._generate_backtest_report(strategy, symbols, start_date, end_date)
        
        logger.info(f"回测完成，总收益率: {self.performance_metrics.get('total_return', 0):.2%}")
        
        return backtest_result
    
    def _reset_backtest(self):
        """重置回测状态"""
        self.current_capital = self.initial_capital
        self.positions = {}
        self.trades = []
        self.daily_returns = []
        self.portfolio_values = []
        self.performance_metrics = {}
    
    def _execute_trades(self, signals: List[Signal], stock_data: Dict[str, pd.DataFrame]):
        """
        执行交易
        
        Args:
            signals: 交易信号列表
            stock_data: 股票数据字典
        """
        for signal in signals:
            try:
                self._execute_single_trade(signal, stock_data.get(signal.symbol))
            except Exception as e:
                logger.error(f"执行交易失败 {signal}: {e}")
    
    def _execute_single_trade(self, signal: Signal, stock_data: pd.DataFrame):
        """
        执行单笔交易
        
        Args:
            signal: 交易信号
            stock_data: 股票数据
        """
        symbol = signal.symbol
        
        # 初始化持仓
        if symbol not in self.positions:
            self.positions[symbol] = {
                'quantity': 0,
                'avg_price': 0,
                'total_cost': 0
            }
        
        position = self.positions[symbol]
        
        if signal.signal_type.lower() == 'buy':
            # 买入
            trade_amount = signal.price * signal.quantity
            commission = trade_amount * self.commission_rate
            total_cost = trade_amount + commission
            
            # 检查资金是否充足
            if total_cost > self.current_capital:
                # 调整买入数量
                available_amount = self.current_capital * 0.95  # 保留5%现金
                adjusted_quantity = int(available_amount / (signal.price * (1 + self.commission_rate)))
                adjusted_quantity = (adjusted_quantity // self.min_trade_unit) * self.min_trade_unit
                
                if adjusted_quantity < self.min_trade_unit:
                    logger.warning(f"资金不足，无法买入{symbol}")
                    return
                
                signal.quantity = adjusted_quantity
                trade_amount = signal.price * signal.quantity
                commission = trade_amount * self.commission_rate
                total_cost = trade_amount + commission
            
            # 更新持仓
            new_quantity = position['quantity'] + signal.quantity
            new_total_cost = position['total_cost'] + trade_amount
            position['quantity'] = new_quantity
            position['total_cost'] = new_total_cost
            position['avg_price'] = new_total_cost / new_quantity
            
            # 更新资金
            self.current_capital -= total_cost
            
            # 记录交易
            trade_record = {
                'timestamp': signal.timestamp,
                'symbol': symbol,
                'action': 'buy',
                'quantity': signal.quantity,
                'price': signal.price,
                'amount': trade_amount,
                'commission': commission,
                'total_cost': total_cost,
                'reason': signal.reason,
                'capital_after': self.current_capital
            }
            self.trades.append(trade_record)
            
        elif signal.signal_type.lower() == 'sell':
            # 卖出
            sell_quantity = min(signal.quantity, position['quantity'])
            if sell_quantity == 0:
                logger.warning(f"无持仓，无法卖出{symbol}")
                return
            
            trade_amount = signal.price * sell_quantity
            commission = trade_amount * self.commission_rate
            stamp_tax = trade_amount * self.stamp_tax_rate
            total_fees = commission + stamp_tax
            net_amount = trade_amount - total_fees
            
            # 计算盈亏
            cost_basis = position['avg_price'] * sell_quantity
            profit_loss = trade_amount - cost_basis - total_fees
            
            # 更新持仓
            position['quantity'] -= sell_quantity
            if position['quantity'] > 0:
                position['total_cost'] -= cost_basis
            else:
                position['total_cost'] = 0
                position['avg_price'] = 0
            
            # 更新资金
            self.current_capital += net_amount
            
            # 记录交易
            trade_record = {
                'timestamp': signal.timestamp,
                'symbol': symbol,
                'action': 'sell',
                'quantity': sell_quantity,
                'price': signal.price,
                'amount': trade_amount,
                'commission': commission,
                'stamp_tax': stamp_tax,
                'total_fees': total_fees,
                'net_amount': net_amount,
                'profit_loss': profit_loss,
                'reason': signal.reason,
                'capital_after': self.current_capital
            }
            self.trades.append(trade_record)
    
    def _calculate_daily_portfolio_values(self, stock_data: Dict[str, pd.DataFrame], 
                                        start_date: str, end_date: str):
        """
        计算每日组合价值
        
        Args:
            stock_data: 股票数据字典
            start_date: 开始日期
            end_date: 结束日期
        """
        # 获取所有交易日期
        all_dates = set()
        for data in stock_data.values():
            all_dates.update(data.index)
        
        trading_days = sorted(list(all_dates))
        trading_days = [d for d in trading_days if start_date <= d.strftime('%Y-%m-%d') <= end_date]
        
        portfolio_values = []
        daily_returns = []
        prev_value = self.initial_capital
        
        # 模拟每日持仓价值变化
        current_positions = {}
        current_cash = self.initial_capital
        
        for date in trading_days:
            # 处理当日交易
            daily_trades = [t for t in self.trades if t['timestamp'].date() == date.date()]
            
            for trade in daily_trades:
                symbol = trade['symbol']
                if symbol not in current_positions:
                    current_positions[symbol] = {'quantity': 0, 'avg_price': 0}
                
                if trade['action'] == 'buy':
                    # 更新持仓
                    old_quantity = current_positions[symbol]['quantity']
                    new_quantity = old_quantity + trade['quantity']
                    if new_quantity > 0:
                        current_positions[symbol]['avg_price'] = (
                            (old_quantity * current_positions[symbol]['avg_price'] + 
                             trade['quantity'] * trade['price']) / new_quantity
                        )
                    current_positions[symbol]['quantity'] = new_quantity
                    current_cash -= trade['total_cost']
                    
                elif trade['action'] == 'sell':
                    current_positions[symbol]['quantity'] -= trade['quantity']
                    current_cash += trade['net_amount']
            
            # 计算当日组合价值
            portfolio_value = current_cash
            
            for symbol, position in current_positions.items():
                if position['quantity'] > 0 and symbol in stock_data:
                    # 获取当日收盘价
                    symbol_data = stock_data[symbol]
                    if date in symbol_data.index:
                        current_price = symbol_data.loc[date, 'close']
                        portfolio_value += position['quantity'] * current_price
            
            portfolio_values.append({
                'date': date,
                'portfolio_value': portfolio_value,
                'cash': current_cash,
                'positions_value': portfolio_value - current_cash
            })
            
            # 计算日收益率
            daily_return = (portfolio_value - prev_value) / prev_value
            daily_returns.append(daily_return)
            prev_value = portfolio_value
        
        self.portfolio_values = portfolio_values
        self.daily_returns = daily_returns
    
    def _calculate_performance_metrics(self, benchmark_data: pd.DataFrame):
        """
        计算性能指标
        
        Args:
            benchmark_data: 基准数据
        """
        if not self.portfolio_values:
            return
        
        # 基本收益指标
        initial_value = self.initial_capital
        final_value = self.portfolio_values[-1]['portfolio_value']
        total_return = (final_value - initial_value) / initial_value
        
        # 年化收益率
        days = len(self.portfolio_values)
        annualized_return = (1 + total_return) ** (252 / days) - 1
        
        # 波动率
        returns_series = pd.Series(self.daily_returns)
        volatility = returns_series.std() * np.sqrt(252)
        
        # 夏普比率 (假设无风险利率为3%)
        risk_free_rate = 0.03
        sharpe_ratio = (annualized_return - risk_free_rate) / volatility if volatility > 0 else 0
        
        # 最大回撤
        portfolio_values = [pv['portfolio_value'] for pv in self.portfolio_values]
        peak = np.maximum.accumulate(portfolio_values)
        drawdown = (portfolio_values - peak) / peak
        max_drawdown = np.min(drawdown)
        
        # 胜率
        winning_trades = [t for t in self.trades if t.get('profit_loss', 0) > 0]
        total_trades = len([t for t in self.trades if 'profit_loss' in t])
        win_rate = len(winning_trades) / total_trades if total_trades > 0 else 0
        
        # 盈亏比
        avg_win = np.mean([t['profit_loss'] for t in winning_trades]) if winning_trades else 0
        losing_trades = [t for t in self.trades if t.get('profit_loss', 0) < 0]
        avg_loss = np.mean([abs(t['profit_loss']) for t in losing_trades]) if losing_trades else 0
        profit_loss_ratio = avg_win / avg_loss if avg_loss > 0 else 0
        
        # 基准比较
        benchmark_return = 0
        if not benchmark_data.empty:
            benchmark_start = benchmark_data.iloc[0]['close']
            benchmark_end = benchmark_data.iloc[-1]['close']
            benchmark_return = (benchmark_end - benchmark_start) / benchmark_start
        
        alpha = total_return - benchmark_return
        
        self.performance_metrics = {
            'total_return': total_return,
            'annualized_return': annualized_return,
            'volatility': volatility,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'win_rate': win_rate,
            'profit_loss_ratio': profit_loss_ratio,
            'total_trades': total_trades,
            'benchmark_return': benchmark_return,
            'alpha': alpha,
            'final_value': final_value
        }
    
    def _generate_backtest_report(self, strategy: BaseStrategy, symbols: List[str], 
                                start_date: str, end_date: str) -> Dict[str, Any]:
        """
        生成回测报告
        
        Args:
            strategy: 交易策略
            symbols: 股票代码列表
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            回测报告
        """
        return {
            'strategy_name': strategy.name,
            'symbols': symbols,
            'start_date': start_date,
            'end_date': end_date,
            'initial_capital': self.initial_capital,
            'final_capital': self.current_capital,
            'performance_metrics': self.performance_metrics,
            'trades': self.trades,
            'portfolio_values': self.portfolio_values,
            'daily_returns': self.daily_returns,
            'positions': self.positions
        }
    
    def plot_results(self, save_path: Optional[str] = None):
        """
        绘制回测结果图表
        
        Args:
            save_path: 保存路径
        """
        if not self.portfolio_values:
            logger.warning("没有回测数据可绘制")
            return
        
        # 创建图表
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        fig.suptitle('回测结果分析', fontsize=16)
        
        # 1. 组合价值曲线
        dates = [pv['date'] for pv in self.portfolio_values]
        values = [pv['portfolio_value'] for pv in self.portfolio_values]
        
        axes[0, 0].plot(dates, values, label='组合价值', linewidth=2)
        axes[0, 0].axhline(y=self.initial_capital, color='r', linestyle='--', label='初始资金')
        axes[0, 0].set_title('组合价值变化')
        axes[0, 0].set_ylabel('价值 (元)')
        axes[0, 0].legend()
        axes[0, 0].grid(True, alpha=0.3)
        
        # 2. 回撤曲线
        peak = np.maximum.accumulate(values)
        drawdown = (np.array(values) - peak) / peak * 100
        
        axes[0, 1].fill_between(dates, drawdown, 0, alpha=0.3, color='red')
        axes[0, 1].plot(dates, drawdown, color='red', linewidth=1)
        axes[0, 1].set_title('回撤曲线')
        axes[0, 1].set_ylabel('回撤 (%)')
        axes[0, 1].grid(True, alpha=0.3)
        
        # 3. 日收益率分布
        axes[1, 0].hist(self.daily_returns, bins=50, alpha=0.7, edgecolor='black')
        axes[1, 0].axvline(x=np.mean(self.daily_returns), color='r', linestyle='--', label='均值')
        axes[1, 0].set_title('日收益率分布')
        axes[1, 0].set_xlabel('日收益率')
        axes[1, 0].set_ylabel('频次')
        axes[1, 0].legend()
        axes[1, 0].grid(True, alpha=0.3)
        
        # 4. 月度收益热力图
        if len(self.daily_returns) > 30:
            returns_df = pd.DataFrame({
                'date': dates,
                'return': self.daily_returns
            })
            returns_df['year'] = returns_df['date'].dt.year
            returns_df['month'] = returns_df['date'].dt.month
            
            monthly_returns = returns_df.groupby(['year', 'month'])['return'].sum().unstack()
            
            if not monthly_returns.empty:
                sns.heatmap(monthly_returns, annot=True, fmt='.2%', cmap='RdYlGn', 
                           center=0, ax=axes[1, 1])
                axes[1, 1].set_title('月度收益热力图')
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            logger.info(f"图表已保存到: {save_path}")
        
        plt.show()
    
    def export_trades_to_csv(self, filepath: str):
        """
        导出交易记录到CSV
        
        Args:
            filepath: 文件路径
        """
        if not self.trades:
            logger.warning("没有交易记录可导出")
            return
        
        trades_df = pd.DataFrame(self.trades)
        trades_df.to_csv(filepath, index=False, encoding='utf-8-sig')
        logger.info(f"交易记录已导出到: {filepath}")
    
    def get_performance_summary(self) -> str:
        """
        获取性能摘要
        
        Returns:
            性能摘要字符串
        """
        if not self.performance_metrics:
            return "暂无回测数据"
        
        metrics = self.performance_metrics
        
        summary = f"""
        回测性能摘要
        ==================
        总收益率: {metrics['total_return']:.2%}
        年化收益率: {metrics['annualized_return']:.2%}
        波动率: {metrics['volatility']:.2%}
        夏普比率: {metrics['sharpe_ratio']:.2f}
        最大回撤: {metrics['max_drawdown']:.2%}
        胜率: {metrics['win_rate']:.2%}
        盈亏比: {metrics['profit_loss_ratio']:.2f}
        交易次数: {metrics['total_trades']}
        基准收益率: {metrics['benchmark_return']:.2%}
        超额收益(Alpha): {metrics['alpha']:.2%}
        最终资产: {metrics['final_value']:,.2f}
        """
        
        return summary
    
    def _calculate_basic_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """计算基本技术指标"""
        try:
            # 移动平均线
            data['ma5'] = data['close'].rolling(window=5).mean()
            data['ma10'] = data['close'].rolling(window=10).mean()
            data['ma20'] = data['close'].rolling(window=20).mean()
            data['ma60'] = data['close'].rolling(window=60).mean()
            
            # RSI
            delta = data['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            data['rsi'] = 100 - (100 / (1 + rs))
            
            # MACD
            exp1 = data['close'].ewm(span=12).mean()
            exp2 = data['close'].ewm(span=26).mean()
            data['macd'] = exp1 - exp2
            data['macd_signal'] = data['macd'].ewm(span=9).mean()
            data['macd_hist'] = data['macd'] - data['macd_signal']
            
            return data
        except Exception as e:
            logger.error(f"计算技术指标失败: {e}")
            return data 