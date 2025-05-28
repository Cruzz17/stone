#!/usr/bin/env python3
"""
策略回测器
使用历史数据对策略进行回测和参数优化
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

from datetime import datetime, timedelta
import itertools
from loguru import logger

from data.database import DatabaseManager
from strategies.double_ma_strategy import DoubleMaStrategy
from strategies.rsi_strategy import RSIStrategy
from strategies.macd_strategy import MACDStrategy
from backtest.backtest_engine import BacktestEngine

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False


class StrategyBacktester:
    """策略回测器"""
    
    def __init__(self):
        """初始化回测器"""
        self.db_manager = DatabaseManager()
        self.backtest_engine = BacktestEngine(initial_capital=100000)
        
        # 可用策略
        self.available_strategies = {
            'double_ma': DoubleMaStrategy,
            'rsi': RSIStrategy,
            'macd': MACDStrategy
        }
        
        logger.info("策略回测器初始化完成")
    
    def run_single_backtest(self, strategy_name: str, strategy_config: dict, 
                           symbol: str, start_date: str, end_date: str) -> dict:
        """
        运行单次回测
        
        Args:
            strategy_name: 策略名称
            strategy_config: 策略配置
            symbol: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            回测结果
        """
        try:
            # 获取历史数据
            data = self.db_manager.get_stock_data(symbol, start_date, end_date)
            
            if data.empty:
                logger.warning(f"没有找到 {symbol} 在 {start_date} 到 {end_date} 的数据")
                return {}
            
            # 创建策略实例
            if strategy_name not in self.available_strategies:
                raise ValueError(f"不支持的策略: {strategy_name}")
            
            strategy_class = self.available_strategies[strategy_name]
            strategy = strategy_class(strategy_config)
            
            # 运行回测
            results = self.backtest_engine.run_backtest(
                strategy=strategy,
                symbols=[symbol],
                start_date=start_date,
                end_date=end_date,
                data_fetcher=None,  # 直接使用数据库数据
                historical_data={symbol: data}
            )
            
            # 计算性能指标
            performance = self.calculate_performance_metrics(results, data)
            
            return {
                'strategy': strategy_name,
                'symbol': symbol,
                'config': strategy_config,
                'performance': performance,
                'trades': results.get('trades', []),
                'portfolio_history': results.get('portfolio_history', [])
            }
            
        except Exception as e:
            logger.error(f"回测失败: {e}")
            return {}
    
    def calculate_performance_metrics(self, backtest_results: dict, price_data: pd.DataFrame) -> dict:
        """计算性能指标"""
        try:
            portfolio_history = backtest_results.get('portfolio_history', [])
            
            if not portfolio_history:
                return {}
            
            # 转换为DataFrame
            df = pd.DataFrame(portfolio_history)
            
            if df.empty:
                return {}
            
            # 基本指标
            initial_value = df['total_value'].iloc[0]
            final_value = df['total_value'].iloc[-1]
            total_return = (final_value - initial_value) / initial_value
            
            # 计算日收益率
            df['daily_return'] = df['total_value'].pct_change().fillna(0)
            
            # 年化收益率
            trading_days = len(df)
            annual_return = (1 + total_return) ** (252 / trading_days) - 1
            
            # 波动率
            volatility = df['daily_return'].std() * np.sqrt(252)
            
            # 夏普比率（假设无风险利率为3%）
            risk_free_rate = 0.03
            sharpe_ratio = (annual_return - risk_free_rate) / volatility if volatility > 0 else 0
            
            # 最大回撤
            df['cummax'] = df['total_value'].cummax()
            df['drawdown'] = (df['total_value'] - df['cummax']) / df['cummax']
            max_drawdown = df['drawdown'].min()
            
            # 胜率
            trades = backtest_results.get('trades', [])
            if trades:
                profitable_trades = sum(1 for trade in trades if trade.get('pnl', 0) > 0)
                win_rate = profitable_trades / len(trades)
            else:
                win_rate = 0
            
            # 基准比较（买入持有策略）
            if not price_data.empty:
                benchmark_return = (price_data['close'].iloc[-1] - price_data['close'].iloc[0]) / price_data['close'].iloc[0]
                excess_return = total_return - benchmark_return
            else:
                benchmark_return = 0
                excess_return = 0
            
            return {
                'total_return': round(total_return * 100, 2),
                'annual_return': round(annual_return * 100, 2),
                'volatility': round(volatility * 100, 2),
                'sharpe_ratio': round(sharpe_ratio, 2),
                'max_drawdown': round(max_drawdown * 100, 2),
                'win_rate': round(win_rate * 100, 2),
                'total_trades': len(trades),
                'benchmark_return': round(benchmark_return * 100, 2),
                'excess_return': round(excess_return * 100, 2),
                'final_value': round(final_value, 2)
            }
            
        except Exception as e:
            logger.error(f"计算性能指标失败: {e}")
            return {}
    
    def optimize_strategy_parameters(self, strategy_name: str, symbol: str, 
                                   start_date: str, end_date: str, 
                                   param_ranges: dict) -> dict:
        """
        策略参数优化
        
        Args:
            strategy_name: 策略名称
            symbol: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            param_ranges: 参数范围字典
            
        Returns:
            优化结果
        """
        logger.info(f"开始优化 {strategy_name} 策略参数")
        
        # 生成参数组合
        param_names = list(param_ranges.keys())
        param_values = list(param_ranges.values())
        param_combinations = list(itertools.product(*param_values))
        
        logger.info(f"总共需要测试 {len(param_combinations)} 种参数组合")
        
        results = []
        
        for i, params in enumerate(param_combinations, 1):
            # 构建配置
            config = dict(zip(param_names, params))
            
            logger.info(f"进度: {i}/{len(param_combinations)} - 测试参数: {config}")
            
            # 运行回测
            result = self.run_single_backtest(
                strategy_name, config, symbol, start_date, end_date
            )
            
            if result and result.get('performance'):
                results.append({
                    'params': config,
                    'performance': result['performance']
                })
        
        if not results:
            logger.warning("没有有效的回测结果")
            return {}
        
        # 按夏普比率排序
        results.sort(key=lambda x: x['performance'].get('sharpe_ratio', -999), reverse=True)
        
        best_result = results[0]
        
        logger.info(f"最佳参数: {best_result['params']}")
        logger.info(f"最佳性能: 夏普比率={best_result['performance']['sharpe_ratio']}")
        
        return {
            'best_params': best_result['params'],
            'best_performance': best_result['performance'],
            'all_results': results[:10]  # 返回前10个结果
        }
    
    def compare_strategies(self, strategies_config: dict, symbol: str, 
                          start_date: str, end_date: str) -> dict:
        """
        比较多个策略
        
        Args:
            strategies_config: 策略配置字典
            symbol: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            比较结果
        """
        logger.info(f"开始比较策略在 {symbol} 上的表现")
        
        results = {}
        
        for strategy_name, config in strategies_config.items():
            logger.info(f"测试策略: {strategy_name}")
            
            result = self.run_single_backtest(
                strategy_name, config, symbol, start_date, end_date
            )
            
            if result:
                results[strategy_name] = result
        
        return results
    
    def plot_backtest_results(self, backtest_result: dict, save_path: str = None):
        """绘制回测结果图表"""
        try:
            portfolio_history = backtest_result.get('portfolio_history', [])
            
            if not portfolio_history:
                logger.warning("没有投资组合历史数据")
                return
            
            df = pd.DataFrame(portfolio_history)
            
            # 创建子图
            fig, axes = plt.subplots(2, 2, figsize=(15, 10))
            fig.suptitle(f"策略回测结果 - {backtest_result.get('symbol', 'Unknown')}", fontsize=16)
            
            # 1. 资产价值曲线
            axes[0, 0].plot(df.index, df['total_value'], label='策略收益', linewidth=2)
            axes[0, 0].axhline(y=df['total_value'].iloc[0], color='r', linestyle='--', alpha=0.7, label='初始资金')
            axes[0, 0].set_title('资产价值变化')
            axes[0, 0].set_ylabel('资产价值')
            axes[0, 0].legend()
            axes[0, 0].grid(True, alpha=0.3)
            
            # 2. 回撤曲线
            df['cummax'] = df['total_value'].cummax()
            df['drawdown'] = (df['total_value'] - df['cummax']) / df['cummax'] * 100
            axes[0, 1].fill_between(df.index, df['drawdown'], 0, alpha=0.3, color='red')
            axes[0, 1].plot(df.index, df['drawdown'], color='red', linewidth=1)
            axes[0, 1].set_title('回撤曲线')
            axes[0, 1].set_ylabel('回撤 (%)')
            axes[0, 1].grid(True, alpha=0.3)
            
            # 3. 现金和持仓价值
            axes[1, 0].plot(df.index, df['cash'], label='现金', alpha=0.7)
            axes[1, 0].plot(df.index, df['positions_value'], label='持仓价值', alpha=0.7)
            axes[1, 0].set_title('现金与持仓分布')
            axes[1, 0].set_ylabel('价值')
            axes[1, 0].legend()
            axes[1, 0].grid(True, alpha=0.3)
            
            # 4. 性能指标表
            performance = backtest_result.get('performance', {})
            metrics_text = f"""
总收益率: {performance.get('total_return', 0):.2f}%
年化收益率: {performance.get('annual_return', 0):.2f}%
波动率: {performance.get('volatility', 0):.2f}%
夏普比率: {performance.get('sharpe_ratio', 0):.2f}
最大回撤: {performance.get('max_drawdown', 0):.2f}%
胜率: {performance.get('win_rate', 0):.2f}%
交易次数: {performance.get('total_trades', 0)}
超额收益: {performance.get('excess_return', 0):.2f}%
            """
            axes[1, 1].text(0.1, 0.5, metrics_text, transform=axes[1, 1].transAxes, 
                           fontsize=12, verticalalignment='center',
                           bbox=dict(boxstyle="round,pad=0.3", facecolor="lightgray", alpha=0.5))
            axes[1, 1].set_title('性能指标')
            axes[1, 1].axis('off')
            
            plt.tight_layout()
            
            if save_path:
                plt.savefig(save_path, dpi=300, bbox_inches='tight')
                logger.info(f"图表已保存到: {save_path}")
            
            plt.show()
            
        except Exception as e:
            logger.error(f"绘制图表失败: {e}")
    
    def generate_report(self, backtest_result: dict) -> str:
        """生成回测报告"""
        try:
            strategy = backtest_result.get('strategy', 'Unknown')
            symbol = backtest_result.get('symbol', 'Unknown')
            performance = backtest_result.get('performance', {})
            config = backtest_result.get('config', {})
            
            report = f"""
📊 策略回测报告
{'='*50}

📈 基本信息:
  策略名称: {strategy}
  股票代码: {symbol}
  策略配置: {config}

💰 收益指标:
  总收益率: {performance.get('total_return', 0):.2f}%
  年化收益率: {performance.get('annual_return', 0):.2f}%
  基准收益率: {performance.get('benchmark_return', 0):.2f}%
  超额收益: {performance.get('excess_return', 0):.2f}%

⚠️ 风险指标:
  波动率: {performance.get('volatility', 0):.2f}%
  最大回撤: {performance.get('max_drawdown', 0):.2f}%
  夏普比率: {performance.get('sharpe_ratio', 0):.2f}

📊 交易统计:
  总交易次数: {performance.get('total_trades', 0)}
  胜率: {performance.get('win_rate', 0):.2f}%
  最终资产: {performance.get('final_value', 0):.2f}

📝 策略评价:
"""
            
            # 添加策略评价
            sharpe = performance.get('sharpe_ratio', 0)
            max_dd = performance.get('max_drawdown', 0)
            
            if sharpe > 1.5:
                report += "  ✅ 夏普比率优秀，风险调整后收益良好\n"
            elif sharpe > 1.0:
                report += "  ✅ 夏普比率良好\n"
            elif sharpe > 0.5:
                report += "  ⚠️ 夏普比率一般，需要优化\n"
            else:
                report += "  ❌ 夏普比率较差，建议重新设计策略\n"
            
            if abs(max_dd) < 5:
                report += "  ✅ 回撤控制良好\n"
            elif abs(max_dd) < 10:
                report += "  ⚠️ 回撤适中\n"
            else:
                report += "  ❌ 回撤较大，风险较高\n"
            
            return report
            
        except Exception as e:
            logger.error(f"生成报告失败: {e}")
            return "报告生成失败"


def main():
    """主函数 - 提供交互式回测界面"""
    backtester = StrategyBacktester()
    
    print("📊 策略回测器")
    print("=" * 50)
    
    while True:
        print("\n请选择操作:")
        print("1. 单策略回测")
        print("2. 策略参数优化")
        print("3. 多策略比较")
        print("4. 退出")
        
        choice = input("\n请输入选择 (1-4): ").strip()
        
        if choice == '1':
            # 单策略回测
            print("\n可用策略: double_ma, rsi, macd")
            strategy_name = input("请输入策略名称: ").strip()
            symbol = input("请输入股票代码 (如: 000001): ").strip()
            months = input("请输入回测月数 (默认6个月): ").strip() or "6"
            
            try:
                months = int(months)
                end_date = datetime.now()
                start_date = end_date - timedelta(days=months * 30)
                
                # 默认配置
                default_configs = {
                    'double_ma': {'short_period': 5, 'long_period': 20},
                    'rsi': {'period': 14, 'oversold': 30, 'overbought': 70},
                    'macd': {'fast': 12, 'slow': 26, 'signal': 9}
                }
                
                config = default_configs.get(strategy_name, {})
                
                result = backtester.run_single_backtest(
                    strategy_name, config, symbol,
                    start_date.strftime('%Y-%m-%d'),
                    end_date.strftime('%Y-%m-%d')
                )
                
                if result:
                    print(backtester.generate_report(result))
                    
                    plot_choice = input("\n是否绘制图表? (y/n): ").strip().lower()
                    if plot_choice == 'y':
                        backtester.plot_backtest_results(result)
                else:
                    print("❌ 回测失败")
                    
            except ValueError:
                print("❌ 输入格式错误")
        
        elif choice == '2':
            # 参数优化
            print("\n可用策略: double_ma, rsi, macd")
            strategy_name = input("请输入策略名称: ").strip()
            symbol = input("请输入股票代码 (如: 000001): ").strip()
            months = input("请输入回测月数 (默认6个月): ").strip() or "6"
            
            try:
                months = int(months)
                end_date = datetime.now()
                start_date = end_date - timedelta(days=months * 30)
                
                # 参数范围
                param_ranges = {
                    'double_ma': {
                        'short_period': [3, 5, 7, 10],
                        'long_period': [15, 20, 25, 30]
                    },
                    'rsi': {
                        'period': [10, 14, 18, 22],
                        'oversold': [20, 25, 30, 35],
                        'overbought': [65, 70, 75, 80]
                    },
                    'macd': {
                        'fast': [8, 12, 16],
                        'slow': [20, 26, 32],
                        'signal': [6, 9, 12]
                    }
                }
                
                if strategy_name in param_ranges:
                    result = backtester.optimize_strategy_parameters(
                        strategy_name, symbol,
                        start_date.strftime('%Y-%m-%d'),
                        end_date.strftime('%Y-%m-%d'),
                        param_ranges[strategy_name]
                    )
                    
                    if result:
                        print(f"\n🎯 最佳参数: {result['best_params']}")
                        print(f"📊 最佳性能: {result['best_performance']}")
                    else:
                        print("❌ 参数优化失败")
                else:
                    print("❌ 不支持的策略")
                    
            except ValueError:
                print("❌ 输入格式错误")
        
        elif choice == '3':
            # 多策略比较
            symbol = input("请输入股票代码 (如: 000001): ").strip()
            months = input("请输入回测月数 (默认6个月): ").strip() or "6"
            
            try:
                months = int(months)
                end_date = datetime.now()
                start_date = end_date - timedelta(days=months * 30)
                
                strategies_config = {
                    'double_ma': {'short_period': 5, 'long_period': 20},
                    'rsi': {'period': 14, 'oversold': 30, 'overbought': 70},
                    'macd': {'fast': 12, 'slow': 26, 'signal': 9}
                }
                
                results = backtester.compare_strategies(
                    strategies_config, symbol,
                    start_date.strftime('%Y-%m-%d'),
                    end_date.strftime('%Y-%m-%d')
                )
                
                if results:
                    print("\n📊 策略比较结果:")
                    print("-" * 80)
                    print(f"{'策略':<12} {'总收益%':<10} {'年化收益%':<12} {'夏普比率':<10} {'最大回撤%':<12} {'胜率%':<8}")
                    print("-" * 80)
                    
                    for strategy_name, result in results.items():
                        perf = result.get('performance', {})
                        print(f"{strategy_name:<12} {perf.get('total_return', 0):<10.2f} "
                              f"{perf.get('annual_return', 0):<12.2f} {perf.get('sharpe_ratio', 0):<10.2f} "
                              f"{perf.get('max_drawdown', 0):<12.2f} {perf.get('win_rate', 0):<8.2f}")
                else:
                    print("❌ 策略比较失败")
                    
            except ValueError:
                print("❌ 输入格式错误")
        
        elif choice == '4':
            print("👋 再见！")
            break
        
        else:
            print("❌ 无效选择，请重新输入")


if __name__ == '__main__':
    main() 