#!/usr/bin/env python3
"""
快速高换手率股票回测测试
使用预定义的活跃股票池进行策略回测
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Any
from loguru import logger
import matplotlib.pyplot as plt

# 导入项目模块
from data.database import DatabaseManager
from utils.real_data_fetcher import RealDataFetcher
from backtest.backtest_engine import BacktestEngine
from strategies.double_ma_strategy import DoubleMaStrategy
from strategies.rsi_strategy import RSIStrategy
from strategies.macd_strategy import MACDStrategy

plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False


class QuickTurnoverTest:
    """快速高换手率股票回测"""
    
    def __init__(self):
        """初始化"""
        self.db_manager = DatabaseManager()
        self.data_fetcher = RealDataFetcher(self.db_manager)
        self.backtest_engine = BacktestEngine(
            initial_capital=1000000,  # 100万初始资金
            commission_rate=0.0003,   # 万3手续费
            stamp_tax_rate=0.001      # 千1印花税
        )
        
        # 预定义的高换手率股票池（活跃股票）
        self.active_stocks = [
            # 科技股
            '000858',  # 五粮液
            '002415',  # 海康威视
            '002594',  # 比亚迪
            '300059',  # 东方财富
            '300122',  # 智飞生物
            '300124',  # 汇川技术
            '300142',  # 沃森生物
            '300274',  # 阳光电源
            '300408',  # 三环集团
            '300454',  # 深信服
            
            # 银行股
            '600000',  # 浦发银行
            '600036',  # 招商银行
            '601318',  # 中国平安
            '601398',  # 工商银行
            
            # 消费股
            '600519',  # 贵州茅台
            '000001',  # 平安银行
            '000002',  # 万科A
            
            # 其他活跃股票
            '002230',  # 科大讯飞
            '002241',  # 歌尔股份
            '002304',  # 洋河股份
            '002371',  # 北方华创
            '002475',  # 立讯精密
            '300015',  # 爱尔眼科
            '300033',  # 同花顺
        ]
        
        logger.info(f"快速回测系统初始化完成，股票池: {len(self.active_stocks)}只")
    
    def download_data(self, days: int = 60) -> Dict[str, pd.DataFrame]:
        """下载股票数据"""
        logger.info(f"开始下载{len(self.active_stocks)}只股票的{days}天历史数据...")
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        stock_data = {}
        success_count = 0
        
        for i, symbol in enumerate(self.active_stocks):
            try:
                data = self.data_fetcher.get_stock_data(
                    symbol, 
                    start_date.strftime('%Y-%m-%d'),
                    end_date.strftime('%Y-%m-%d')
                )
                
                if not data.empty and len(data) >= 20:
                    # 计算技术指标
                    data = self.data_fetcher.calculate_technical_indicators(data)
                    stock_data[symbol] = data
                    success_count += 1
                    logger.info(f"✓ {symbol}: {len(data)} 条数据")
                else:
                    logger.warning(f"✗ {symbol}: 数据不足")
                
            except Exception as e:
                logger.error(f"✗ {symbol}: {e}")
                continue
        
        logger.info(f"数据下载完成，成功: {success_count}/{len(self.active_stocks)}")
        return stock_data
    
    def run_backtest(self, stock_data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """运行回测"""
        logger.info("开始策略回测...")
        
        # 定义策略
        strategies = {
            '双均线策略': DoubleMaStrategy({'short_window': 3, 'long_window': 8}),
            'RSI策略': RSIStrategy({'rsi_period': 6, 'oversold': 40, 'overbought': 60}),
            'MACD策略': MACDStrategy({'fast_period': 8, 'slow_period': 16, 'signal_period': 6})
        }
        
        # 计算回测期间
        all_dates = []
        for data in stock_data.values():
            all_dates.extend(data.index.tolist())
        
        start_date = min(all_dates).strftime('%Y-%m-%d')
        end_date = max(all_dates).strftime('%Y-%m-%d')
        symbols = list(stock_data.keys())
        
        logger.info(f"回测期间: {start_date} 至 {end_date}")
        logger.info(f"回测股票: {len(symbols)} 只")
        
        # 运行回测
        results = {}
        
        for strategy_name, strategy in strategies.items():
            logger.info(f"正在回测: {strategy_name}")
            
            try:
                # 修复参数传递
                result = self.backtest_engine.run_backtest(
                    strategy=strategy,
                    symbols=symbols,  # 使用symbols参数
                    start_date=start_date,
                    end_date=end_date,
                    historical_data=stock_data  # 使用historical_data参数
                )
                
                results[strategy_name] = result
                
                # 显示结果
                metrics = result['performance_metrics']
                logger.info(f"  总收益率: {metrics['total_return']:.2%}")
                logger.info(f"  年化收益率: {metrics['annualized_return']:.2%}")
                logger.info(f"  夏普比率: {metrics['sharpe_ratio']:.2f}")
                logger.info(f"  最大回撤: {metrics['max_drawdown']:.2%}")
                logger.info(f"  胜率: {metrics['win_rate']:.2%}")
                logger.info(f"  交易次数: {metrics['total_trades']}")
                
            except Exception as e:
                logger.error(f"策略 {strategy_name} 回测失败: {e}")
                continue
        
        return results
    
    def analyze_and_display(self, results: Dict[str, Any]):
        """分析并显示结果"""
        if not results:
            logger.warning("没有回测结果")
            return
        
        # 创建对比表
        comparison_data = []
        for strategy_name, result in results.items():
            metrics = result['performance_metrics']
            comparison_data.append({
                '策略': strategy_name,
                '总收益率': f"{metrics['total_return']:.2%}",
                '年化收益率': f"{metrics['annualized_return']:.2%}",
                '夏普比率': f"{metrics['sharpe_ratio']:.2f}",
                '最大回撤': f"{metrics['max_drawdown']:.2%}",
                '胜率': f"{metrics['win_rate']:.2%}",
                '交易次数': metrics['total_trades'],
                '最终资产': f"{metrics['final_value']:,.0f}元"
            })
        
        comparison_df = pd.DataFrame(comparison_data)
        
        print("\n" + "="*80)
        print("高换手率股票策略回测结果对比")
        print("="*80)
        print(comparison_df.to_string(index=False))
        print("="*80)
        
        # 找出最佳策略
        best_strategy = None
        best_return = -float('inf')
        
        for strategy_name, result in results.items():
            total_return = result['performance_metrics']['total_return']
            if total_return > best_return:
                best_return = total_return
                best_strategy = strategy_name
        
        if best_strategy:
            print(f"\n🏆 最佳策略: {best_strategy}")
            print(f"📈 总收益率: {best_return:.2%}")
            
            best_result = results[best_strategy]
            metrics = best_result['performance_metrics']
            
            print(f"\n📊 详细指标:")
            print(f"   年化收益率: {metrics['annualized_return']:.2%}")
            print(f"   波动率: {metrics['volatility']:.2%}")
            print(f"   夏普比率: {metrics['sharpe_ratio']:.2f}")
            print(f"   最大回撤: {metrics['max_drawdown']:.2%}")
            print(f"   胜率: {metrics['win_rate']:.2%}")
            print(f"   盈亏比: {metrics['profit_loss_ratio']:.2f}")
            print(f"   交易次数: {metrics['total_trades']}")
            print(f"   最终资产: {metrics['final_value']:,.0f}元")
            
            # 策略评价
            self._evaluate_strategy(metrics)
    
    def _evaluate_strategy(self, metrics: Dict):
        """评价策略表现"""
        print(f"\n🎯 策略评价:")
        
        # 收益率评价
        annual_return = metrics['annualized_return']
        if annual_return > 0.20:
            print("   收益率: 🌟🌟🌟 优秀 (>20%)")
        elif annual_return > 0.10:
            print("   收益率: 🌟🌟 良好 (10%-20%)")
        elif annual_return > 0.05:
            print("   收益率: 🌟 一般 (5%-10%)")
        else:
            print("   收益率: ❌ 较差 (<5%)")
        
        # 夏普比率评价
        sharpe = metrics['sharpe_ratio']
        if sharpe > 1.5:
            print("   风险调整收益: 🌟🌟🌟 优秀 (>1.5)")
        elif sharpe > 1.0:
            print("   风险调整收益: 🌟🌟 良好 (1.0-1.5)")
        elif sharpe > 0.5:
            print("   风险调整收益: 🌟 一般 (0.5-1.0)")
        else:
            print("   风险调整收益: ❌ 较差 (<0.5)")
        
        # 回撤评价
        max_dd = abs(metrics['max_drawdown'])
        if max_dd < 0.05:
            print("   风险控制: 🌟🌟🌟 优秀 (<5%)")
        elif max_dd < 0.10:
            print("   风险控制: 🌟🌟 良好 (5%-10%)")
        elif max_dd < 0.20:
            print("   风险控制: 🌟 一般 (10%-20%)")
        else:
            print("   风险控制: ❌ 较差 (>20%)")
        
        # 胜率评价
        win_rate = metrics['win_rate']
        if win_rate > 0.60:
            print("   交易胜率: 🌟🌟🌟 优秀 (>60%)")
        elif win_rate > 0.50:
            print("   交易胜率: 🌟🌟 良好 (50%-60%)")
        elif win_rate > 0.40:
            print("   交易胜率: 🌟 一般 (40%-50%)")
        else:
            print("   交易胜率: ❌ 较差 (<40%)")
    
    def plot_simple_results(self, results: Dict[str, Any]):
        """绘制简单的结果图表"""
        if not results:
            return
        
        # 创建简单的对比图
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
        
        strategies = list(results.keys())
        returns = [results[s]['performance_metrics']['total_return'] * 100 for s in strategies]
        sharpes = [results[s]['performance_metrics']['sharpe_ratio'] for s in strategies]
        
        # 收益率对比
        bars1 = ax1.bar(strategies, returns, alpha=0.7, color=['blue', 'green', 'orange'])
        ax1.set_title('策略总收益率对比')
        ax1.set_ylabel('收益率 (%)')
        ax1.tick_params(axis='x', rotation=45)
        ax1.grid(True, alpha=0.3)
        
        # 添加数值标签
        for bar, value in zip(bars1, returns):
            ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                    f'{value:.1f}%', ha='center', va='bottom')
        
        # 夏普比率对比
        bars2 = ax2.bar(strategies, sharpes, alpha=0.7, color=['red', 'purple', 'brown'])
        ax2.set_title('策略夏普比率对比')
        ax2.set_ylabel('夏普比率')
        ax2.tick_params(axis='x', rotation=45)
        ax2.grid(True, alpha=0.3)
        
        # 添加数值标签
        for bar, value in zip(bars2, sharpes):
            ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.02,
                    f'{value:.2f}', ha='center', va='bottom')
        
        plt.tight_layout()
        plt.show()
    
    def run_quick_test(self):
        """运行快速测试"""
        logger.info("🚀 开始快速高换手率股票回测测试")
        logger.info("="*60)
        
        try:
            # 1. 下载数据
            stock_data = self.download_data(60)
            
            if not stock_data:
                logger.error("❌ 没有获取到股票数据")
                return
            
            # 2. 运行回测
            results = self.run_backtest(stock_data)
            
            if not results:
                logger.error("❌ 回测失败")
                return
            
            # 3. 分析结果
            self.analyze_and_display(results)
            
            # 4. 绘制图表
            self.plot_simple_results(results)
            
            logger.info("✅ 快速回测完成！")
            
        except Exception as e:
            logger.error(f"❌ 回测过程出错: {e}")
            raise


def main():
    """主函数"""
    logger.info("🚀 开始高换手率股票策略回测...")
    
    # 初始化组件
    db_manager = DatabaseManager()
    data_fetcher = RealDataFetcher(db_manager)
    backtest_engine = BacktestEngine(initial_capital=1000000)
    
    # 使用更激进的策略参数
    strategies = {
        '双均线策略': DoubleMaStrategy({
            'short_window': 3,    # 3天短期均线
            'long_window': 8      # 8天长期均线
        }),
        'RSI策略': RSIStrategy({
            'rsi_period': 6,      # 6天RSI
            'oversold': 40,       # 40超卖线
            'overbought': 60      # 60超买线
        }),
        'MACD策略': MACDStrategy({
            'fast_period': 8,     # 8天快线
            'slow_period': 16,    # 16天慢线
            'signal_period': 6    # 6天信号线
        })
    }
    
    # 预定义的活跃股票池（24只）
    active_stocks = [
        '000858', '002415', '002594', '300059', '000001', '600036',
        '000002', '600000', '601318', '600519', '000166', '002352',
        '300750', '002475', '300015', '000725', '600276', '002230',
        '300142', '000063', '600031', '002304', '600887', '000876'
    ]
    
    # 获取数据时间范围（扩大到90天）
    end_date = datetime.now()
    start_date = end_date - timedelta(days=90)  # 增加到90天
    
    logger.info(f"📅 数据时间范围: {start_date.strftime('%Y-%m-%d')} 到 {end_date.strftime('%Y-%m-%d')}")
    logger.info(f"📊 股票池: {len(active_stocks)}只活跃股票")
    
    # 下载股票数据
    logger.info("📥 开始下载股票数据...")
    stock_data = {}
    
    for symbol in active_stocks:
        try:
            data = data_fetcher.get_stock_data(
                symbol, 
                start_date.strftime('%Y-%m-%d'),
                end_date.strftime('%Y-%m-%d')
            )
            
            if data is not None and len(data) > 20:  # 至少需要20天数据
                stock_data[symbol] = data
                logger.info(f"✅ {symbol}: {len(data)}条数据")
            else:
                logger.warning(f"⚠️ {symbol}: 数据不足")
                
        except Exception as e:
            logger.error(f"❌ {symbol}: 获取数据失败 - {e}")
    
    logger.info(f"📊 成功获取 {len(stock_data)} 只股票数据")
    
    # 运行回测
    results = {}
    symbols = list(stock_data.keys())  # 获取成功下载数据的股票列表
    
    for strategy_name, strategy in strategies.items():
        logger.info(f"🔄 运行策略: {strategy_name}")
        
        try:
            # 修复参数传递 - 使用正确的参数名
            result = backtest_engine.run_backtest(
                strategy=strategy,
                symbols=symbols,  # 使用symbols而不是stock_data
                start_date=start_date.strftime('%Y-%m-%d'),
                end_date=end_date.strftime('%Y-%m-%d'),
                historical_data=stock_data  # 使用historical_data参数
            )
            results[strategy_name] = result
            logger.info(f"✅ {strategy_name} 回测完成")
            
        except Exception as e:
            logger.error(f"❌ {strategy_name} 回测失败: {e}")
            results[strategy_name] = None
    
    # 显示结果
    display_results(results)
    
    logger.info("🎉 回测完成！")


def display_results(results):
    """显示回测结果"""
    if not results:
        logger.warning("没有回测结果")
        return
    
    # 创建对比表
    comparison_data = []
    for strategy_name, result in results.items():
        if result is None:
            continue
            
        metrics = result['performance_metrics']
        comparison_data.append({
            '策略': strategy_name,
            '总收益率': f"{metrics['total_return']:.2%}",
            '年化收益率': f"{metrics['annualized_return']:.2%}",
            '夏普比率': f"{metrics['sharpe_ratio']:.2f}",
            '最大回撤': f"{metrics['max_drawdown']:.2%}",
            '胜率': f"{metrics['win_rate']:.2%}",
            '交易次数': metrics['total_trades'],
            '最终资产': f"{metrics['final_value']:,.0f}元"
        })
    
    if not comparison_data:
        logger.warning("所有策略都回测失败")
        return
    
    comparison_df = pd.DataFrame(comparison_data)
    
    print("\n" + "="*80)
    print("高换手率股票策略回测结果对比")
    print("="*80)
    print(comparison_df.to_string(index=False))
    print("="*80)
    
    # 找出最佳策略
    best_strategy = None
    best_return = -float('inf')
    
    for strategy_name, result in results.items():
        if result is None:
            continue
            
        total_return = result['performance_metrics']['total_return']
        if total_return > best_return:
            best_return = total_return
            best_strategy = strategy_name
    
    if best_strategy:
        print(f"\n🏆 最佳策略: {best_strategy}")
        print(f"📈 总收益率: {best_return:.2%}")
        
        best_result = results[best_strategy]
        metrics = best_result['performance_metrics']
        
        print(f"\n📊 详细指标:")
        print(f"   年化收益率: {metrics['annualized_return']:.2%}")
        print(f"   波动率: {metrics['volatility']:.2%}")
        print(f"   夏普比率: {metrics['sharpe_ratio']:.2f}")
        print(f"   最大回撤: {metrics['max_drawdown']:.2%}")
        print(f"   胜率: {metrics['win_rate']:.2%}")
        print(f"   盈亏比: {metrics['profit_loss_ratio']:.2f}")
        print(f"   交易次数: {metrics['total_trades']}")
        print(f"   最终资产: {metrics['final_value']:,.0f}元")


if __name__ == "__main__":
    main() 