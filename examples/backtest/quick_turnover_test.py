#!/usr/bin/env python3
"""
高换手率股票策略回测 - 快速测试版（优化版）
使用预定义的优质股票池进行快速验证
"""

import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from loguru import logger
from typing import Dict, List, Any
import time

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

# 导入项目模块
from data.database import DatabaseManager
from utils.real_data_fetcher import RealDataFetcher
from backtest.backtest_engine import BacktestEngine
from strategies.double_ma_strategy import DoubleMaStrategy
from strategies.rsi_strategy import RSIStrategy
from strategies.macd_strategy import MACDStrategy

class QuickTurnoverTest:
    """快速换手率测试系统（优化版）"""
    
    def __init__(self):
        """初始化"""
        self.db_manager = DatabaseManager()
        self.data_fetcher = RealDataFetcher(self.db_manager)
        self.backtest_engine = BacktestEngine(
            initial_capital=1000000,    # 100万初始资金
            commission_rate=0.0003,     # 万3手续费
            stamp_tax_rate=0.001,       # 千1印花税
            min_trade_unit=100          # 最小交易单位
        )
        self.test_results = {}
    
    def get_optimized_test_stocks(self) -> List[str]:
        """
        获取优化的测试股票池
        按板块均衡配置，兼顾稳定性和活跃度
        """
        # 优化的股票池 - 按板块分类
        stock_pool = {
            # 大盘蓝筹股（30% - 稳定基础）
            '金融蓝筹': ['000001', '600036', '600000', '601318', '000002', '600016'],
            '央企龙头': ['600519', '000858', '601857', '600887', '601398'],
            
            # 科技成长股（40% - 成长动力）
            '科技龙头': ['002415', '300059', '300124', '002230', '300142'],
            '新能源车': ['002594', '300750', '002475', '300274', '002304'],
            '人工智能': ['300496', '300433', '002252', '300144', '000069'],
            
            # 消费医药股（20% - 防御配置）
            '消费品牌': ['000063', '000568', '002352', '000725', '600276'],
            '医药生物': ['300015', '002241', '000538', '300347', '002558'],
            
            # 制造业（10% - 周期平衡）
            '先进制造': ['002371', '002405', '300296', '300408', '002493']
        }
        
        # 按权重选择股票
        selected_stocks = []
        weights = {
            '金融蓝筹': 6,      # 6只
            '央企龙头': 5,      # 5只
            '科技龙头': 5,      # 5只
            '新能源车': 5,      # 5只
            '人工智能': 5,      # 5只
            '消费品牌': 4,      # 4只
            '医药生物': 4,      # 4只
            '先进制造': 4       # 4只
        }
        
        for sector, count in weights.items():
            if sector in stock_pool:
                sector_stocks = stock_pool[sector][:count]
                selected_stocks.extend(sector_stocks)
        
        logger.info(f"优化测试股票池构成（共{len(selected_stocks)}只）:")
        for sector, count in weights.items():
            logger.info(f"  {sector}: {count}只")
        
        return selected_stocks
    
    def download_test_data(self, days: int = 180) -> Dict[str, pd.DataFrame]:
        """
        下载测试数据
        
        Args:
            days: 下载天数（默认半年180天）
            
        Returns:
            股票数据字典
        """
        test_stocks = self.get_optimized_test_stocks()
        logger.info(f"开始下载{len(test_stocks)}只股票的{days}天历史数据...")
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        stock_data = {}
        success_count = 0
        
        for symbol in test_stocks:
            try:
                data = self.data_fetcher.get_stock_data(
                    symbol, 
                    start_date.strftime('%Y-%m-%d'),
                    end_date.strftime('%Y-%m-%d')
                )
                
                if not data.empty and len(data) >= 60:  # 至少60个交易日
                    # 计算技术指标
                    data = self.data_fetcher.calculate_technical_indicators(data)
                    stock_data[symbol] = data
                    success_count += 1
                    logger.debug(f"成功下载 {symbol}: {len(data)} 条数据")
                else:
                    logger.warning(f"股票 {symbol} 数据不足，跳过")
                
            except Exception as e:
                logger.error(f"下载 {symbol} 数据失败: {e}")
                continue
        
        logger.info(f"数据下载完成，成功下载{success_count}只股票数据")
        return stock_data
    
    def create_optimized_strategies(self) -> Dict[str, Any]:
        """创建优化的策略"""
        strategies = {
            '稳健双均线策略': DoubleMaStrategy({
                'short_window': 10,   # 10日短期均线（更稳定）
                'long_window': 30     # 30日长期均线（趋势确认）
            }),
            
            '经典RSI策略': RSIStrategy({
                'rsi_period': 14,     # 标准14日RSI
                'oversold': 30,       # 30超卖线（经典参数）
                'overbought': 70      # 70超买线（经典参数）
            }),
            
            '标准MACD策略': MACDStrategy({
                'fast_period': 12,    # 标准12日快线
                'slow_period': 26,    # 标准26日慢线
                'signal_period': 9    # 标准9日信号线
            })
        }
        
        logger.info("创建优化策略:")
        for name, strategy in strategies.items():
            logger.info(f"  {name}: {strategy.config}")
        
        return strategies
    
    def run_strategy_tests(self, stock_data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """运行策略测试"""
        logger.info(f"开始运行优化策略测试，股票数量: {len(stock_data)}")
        
        strategies = self.create_optimized_strategies()
        
        # 计算回测期间
        all_dates = []
        for data in stock_data.values():
            all_dates.extend(data.index.tolist())
        
        start_date = min(all_dates).strftime('%Y-%m-%d')
        end_date = max(all_dates).strftime('%Y-%m-%d')
        symbols = list(stock_data.keys())
        
        logger.info(f"回测期间: {start_date} 至 {end_date}")
        logger.info(f"回测股票: {len(symbols)} 只")
        
        results = {}
        
        for strategy_name, strategy in strategies.items():
            logger.info(f"🔄 运行策略: {strategy_name}")
            
            try:
                result = self.backtest_engine.run_backtest(
                    strategy=strategy,
                    symbols=symbols,
                    start_date=start_date,
                    end_date=end_date,
                    historical_data=stock_data
                )
                
                results[strategy_name] = result
                
                # 显示策略结果
                metrics = result['performance_metrics']
                logger.info(f"✅ {strategy_name} 回测完成:")
                logger.info(f"  总收益率: {metrics['total_return']:.2%}")
                logger.info(f"  年化收益率: {metrics['annualized_return']:.2%}")
                logger.info(f"  夏普比率: {metrics['sharpe_ratio']:.2f}")
                logger.info(f"  最大回撤: {metrics['max_drawdown']:.2%}")
                logger.info(f"  胜率: {metrics['win_rate']:.2%}")
                logger.info(f"  交易次数: {metrics['total_trades']}")
                
            except Exception as e:
                logger.error(f"❌ {strategy_name} 回测失败: {e}")
                continue
        
        self.test_results = results
        return results
    
    def analyze_test_results(self) -> pd.DataFrame:
        """分析测试结果"""
        if not self.test_results:
            logger.warning("没有可分析的结果")
            return pd.DataFrame()
        
        logger.info("📊 分析测试结果...")
        
        # 创建结果对比表
        comparison_data = []
        
        for strategy_name, result in self.test_results.items():
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
        
        # 显示结果
        logger.info("优化策略回测结果对比")
        logger.info("=" * 100)
        print(comparison_df.to_string(index=False))
        
        # 找出最佳策略
        best_strategy = None
        best_return = -float('inf')
        
        for strategy_name, result in self.test_results.items():
            total_return = result['performance_metrics']['total_return']
            if total_return > best_return:
                best_return = total_return
                best_strategy = strategy_name
        
        if best_strategy:
            logger.info(f"🏆 最佳策略: {best_strategy} (收益率: {best_return:.2%})")
        
        return comparison_df
    
    def export_test_results(self):
        """导出测试结果"""
        if not self.test_results:
            logger.warning("没有可导出的结果")
            return
        
        try:
            # 导出结果对比表
            comparison_df = self.analyze_test_results()
            results_file = f"quick_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            comparison_df.to_csv(results_file, index=False, encoding='utf-8-sig')
            logger.info(f"测试结果已导出到: {results_file}")
            
            # 导出详细数据
            for strategy_name, result in self.test_results.items():
                if 'trades' in result and not result['trades'].empty:
                    trades_file = f"trades_{strategy_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                    result['trades'].to_csv(trades_file, index=False, encoding='utf-8-sig')
                    logger.info(f"{strategy_name} 交易记录已导出到: {trades_file}")
            
        except Exception as e:
            logger.error(f"导出结果失败: {e}")
    
    def run_quick_test(self, data_days: int = 180):
        """
        运行快速测试
        
        Args:
            data_days: 数据天数（默认半年180天）
        """
        logger.info("🚀 开始优化版快速换手率策略测试")
        logger.info("=" * 60)
        logger.info(f"数据周期: {data_days}天 (约{data_days//30}个月)")
        logger.info("=" * 60)
        
        try:
            # 1. 下载测试数据
            logger.info("步骤1: 下载优化测试数据")
            stock_data = self.download_test_data(data_days)
            
            if not stock_data:
                logger.error("未获取到股票数据，退出")
                return
            
            # 2. 运行策略测试
            logger.info("步骤2: 运行优化策略测试")
            results = self.run_strategy_tests(stock_data)
            
            if not results:
                logger.error("策略测试失败，退出")
                return
            
            # 3. 分析结果
            logger.info("步骤3: 分析测试结果")
            self.analyze_test_results()
            
            # 4. 导出结果
            logger.info("步骤4: 导出测试结果")
            self.export_test_results()
            
            logger.info("=" * 60)
            logger.info("🎉 优化版快速测试完成！")
            logger.info("=" * 60)
            
        except Exception as e:
            logger.error(f"快速测试过程中出现错误: {e}")
            raise


def main():
    """主函数"""
    # 创建快速测试系统
    test_system = QuickTurnoverTest()
    
    # 运行优化的快速测试
    test_system.run_quick_test(
        data_days=180  # 使用半年历史数据
    )


if __name__ == "__main__":
    main() 