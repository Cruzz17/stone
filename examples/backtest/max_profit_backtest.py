#!/usr/bin/env python3
"""
最大收益回测系统
支持板块配置、多策略组合和全面的技术指标策略
"""

import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import time
import json
from loguru import logger
import matplotlib.pyplot as plt
import seaborn as sns

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

# 导入项目模块
from data.database import DatabaseManager
from utils.real_data_fetcher import RealDataFetcher
from backtest.backtest_engine import BacktestEngine

# 导入所有策略
from strategies.double_ma_strategy import DoubleMaStrategy
from strategies.rsi_strategy import RSIStrategy
from strategies.macd_strategy import MACDStrategy
from strategies.bollinger_strategy import BollingerStrategy
from strategies.kdj_strategy import KDJStrategy
from strategies.multi_strategy import MultiStrategy

try:
    import akshare as ak
    AKSHARE_AVAILABLE = True
except ImportError:
    AKSHARE_AVAILABLE = False
    logger.warning("AKShare未安装，将使用模拟数据")

plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False


class MaxProfitBacktest:
    """最大收益回测系统"""
    
    def __init__(self):
        """初始化回测系统"""
        self.db_manager = DatabaseManager()
        self.data_fetcher = RealDataFetcher(self.db_manager)
        self.backtest_engine = BacktestEngine(
            initial_capital=1000000,  # 100万初始资金
            commission_rate=0.0003,   # 万3手续费
            stamp_tax_rate=0.001      # 千1印花税
        )
        
        self.selected_stocks = []
        self.backtest_results = {}
        self.sector_config = self._load_default_sectors()
        
        logger.info("最大收益回测系统初始化完成")
    
    def _load_default_sectors(self) -> Dict[str, Dict]:
        """加载默认板块配置"""
        return {
            # 科技成长板块 (40% - 高成长潜力)
            '科技龙头': {
                'stocks': ['002415', '300059', '300124', '002230', '300142', '300015'],
                'weight': 0.15,
                'description': '科技龙头企业，创新能力强'
            },
            '新能源': {
                'stocks': ['002594', '300750', '002475', '300274', '300316', '002304'],
                'weight': 0.15,
                'description': '新能源产业链，政策支持强'
            },
            '人工智能': {
                'stocks': ['300496', '300433', '002252', '300144', '000069', '000338'],
                'weight': 0.10,
                'description': '人工智能概念，未来趋势'
            },
            
            # 消费医药板块 (25% - 稳定增长)
            '消费品牌': {
                'stocks': ['000063', '000568', '002352', '000725', '600276', '000876'],
                'weight': 0.15,
                'description': '消费品牌，需求稳定'
            },
            '医药生物': {
                'stocks': ['300015', '300142', '002241', '000538', '300347', '002558'],
                'weight': 0.10,
                'description': '医药生物，刚性需求'
            },
            
            # 金融地产板块 (20% - 价值支撑)
            '金融银行': {
                'stocks': ['000001', '600036', '600000', '601318', '000002', '600016'],
                'weight': 0.15,
                'description': '金融银行，价值稳定'
            },
            '地产建筑': {
                'stocks': ['000002', '600048', '000069', '600606', '002142', '600895'],
                'weight': 0.05,
                'description': '地产建筑，周期性机会'
            },
            
            # 制造业板块 (15% - 周期性机会)
            '先进制造': {
                'stocks': ['002371', '002405', '300296', '300408', '002493', '000425'],
                'weight': 0.10,
                'description': '先进制造业，产业升级'
            },
            '新材料': {
                'stocks': ['002555', '300251', '002714', '300454', '000100', '000157'],
                'weight': 0.05,
                'description': '新材料产业，技术突破'
            }
        }
    
    def configure_sectors(self, sector_config: Dict[str, Dict] = None, 
                         custom_weights: Dict[str, float] = None):
        """
        配置板块和权重
        
        Args:
            sector_config: 板块配置字典
            custom_weights: 自定义权重 {板块名: 权重}
        """
        if sector_config:
            self.sector_config = sector_config
        
        if custom_weights:
            # 更新权重
            total_weight = sum(custom_weights.values())
            if abs(total_weight - 1.0) > 0.01:
                logger.warning(f"权重总和为{total_weight:.2f}，将自动归一化")
                custom_weights = {k: v/total_weight for k, v in custom_weights.items()}
            
            for sector_name, weight in custom_weights.items():
                if sector_name in self.sector_config:
                    self.sector_config[sector_name]['weight'] = weight
        
        logger.info("板块配置更新:")
        for sector_name, config in self.sector_config.items():
            logger.info(f"  {sector_name}: {config['weight']:.1%} - {config['description']}")
    
    def select_stocks_by_sectors(self, max_stocks_per_sector: int = 5) -> List[str]:
        """
        按板块选择股票
        
        Args:
            max_stocks_per_sector: 每个板块最大股票数
            
        Returns:
            选中的股票列表
        """
        selected_stocks = []
        
        logger.info("按板块选择股票:")
        
        for sector_name, config in self.sector_config.items():
            sector_stocks = config['stocks'][:max_stocks_per_sector]
            selected_stocks.extend(sector_stocks)
            
            logger.info(f"  {sector_name}: {len(sector_stocks)}只股票 (权重: {config['weight']:.1%})")
            for stock in sector_stocks:
                logger.debug(f"    {stock}")
        
        # 去重
        selected_stocks = list(set(selected_stocks))
        
        logger.info(f"总计选择{len(selected_stocks)}只股票")
        self.selected_stocks = selected_stocks
        return selected_stocks
    
    def download_stock_data(self, days: int = 365) -> Dict[str, pd.DataFrame]:
        """
        下载股票历史数据
        
        Args:
            days: 下载天数（默认一年365天）
            
        Returns:
            股票数据字典
        """
        if not self.selected_stocks:
            self.select_stocks_by_sectors()
        
        logger.info(f"开始下载{len(self.selected_stocks)}只股票的{days}天历史数据...")
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        stock_data = {}
        success_count = 0
        
        for i, symbol in enumerate(self.selected_stocks):
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
                
                # 显示进度
                if (i + 1) % 10 == 0:
                    logger.info(f"数据下载进度: {i + 1}/{len(self.selected_stocks)}")
                
                # 限制请求频率
                time.sleep(0.1)
                
            except Exception as e:
                logger.error(f"下载 {symbol} 数据失败: {e}")
                continue
        
        logger.info(f"数据下载完成，成功下载{success_count}只股票数据")
        return stock_data
    
    def create_optimized_strategies(self) -> Dict[str, Any]:
        """创建优化的策略组合"""
        strategies = {
            # 单一策略
            '优化双均线策略': DoubleMaStrategy({
                'short_window': 8,    # 8日短期均线
                'long_window': 21     # 21日长期均线
            }),
            
            '动态RSI策略': RSIStrategy({
                'rsi_period': 12,     # 12日RSI
                'oversold': 25,       # 25超卖线
                'overbought': 75      # 75超买线
            }),
            
            '快速MACD策略': MACDStrategy({
                'fast_period': 10,    # 10日快线
                'slow_period': 22,    # 22日慢线
                'signal_period': 8    # 8日信号线
            }),
            
            '布林带策略': BollingerStrategy({
                'period': 18,         # 18日布林带
                'std_dev': 2.2,       # 2.2倍标准差
                'oversold_threshold': 0.15,   # 超卖阈值
                'overbought_threshold': 0.85  # 超买阈值
            }),
            
            'KDJ策略': KDJStrategy({
                'k_period': 8,        # 8日K值
                'd_period': 3,        # 3日D值平滑
                'oversold': 25,       # 25超卖线
                'overbought': 75      # 75超买线
            })
        }
        
        # 多策略组合
        # 成长型组合 (适合科技股)
        growth_strategies = {
            strategies['快速MACD策略']: 0.4,
            strategies['动态RSI策略']: 0.3,
            strategies['KDJ策略']: 0.3
        }
        
        strategies['成长型组合'] = MultiStrategy(growth_strategies, {
            'signal_threshold': 0.5,
            'max_positions': 15,
            'rebalance_frequency': 3
        })
        
        # 稳健型组合 (适合价值股)
        stable_strategies = {
            strategies['优化双均线策略']: 0.4,
            strategies['布林带策略']: 0.35,
            strategies['动态RSI策略']: 0.25
        }
        
        strategies['稳健型组合'] = MultiStrategy(stable_strategies, {
            'signal_threshold': 0.6,
            'max_positions': 12,
            'rebalance_frequency': 5
        })
        
        # 激进型组合 (适合高波动股)
        aggressive_strategies = {
            strategies['KDJ策略']: 0.35,
            strategies['快速MACD策略']: 0.35,
            strategies['布林带策略']: 0.3
        }
        
        strategies['激进型组合'] = MultiStrategy(aggressive_strategies, {
            'signal_threshold': 0.4,
            'max_positions': 20,
            'rebalance_frequency': 2
        })
        
        # 全能型组合 (平衡所有策略)
        balanced_strategies = {
            strategies['优化双均线策略']: 0.25,
            strategies['动态RSI策略']: 0.25,
            strategies['快速MACD策略']: 0.20,
            strategies['布林带策略']: 0.15,
            strategies['KDJ策略']: 0.15
        }
        
        strategies['全能型组合'] = MultiStrategy(balanced_strategies, {
            'signal_threshold': 0.55,
            'max_positions': 15,
            'rebalance_frequency': 4
        })
        
        logger.info(f"创建了{len(strategies)}个优化策略")
        return strategies
    
    def run_strategy_backtest(self, stock_data: Dict[str, pd.DataFrame], 
                            strategy_names: List[str] = None) -> Dict[str, Any]:
        """
        运行策略回测
        
        Args:
            stock_data: 股票数据字典
            strategy_names: 要测试的策略名称列表
            
        Returns:
            回测结果
        """
        logger.info(f"开始运行最大收益策略回测，股票数量: {len(stock_data)}")
        
        # 创建所有策略
        all_strategies = self.create_optimized_strategies()
        
        # 选择要测试的策略
        if strategy_names:
            strategies = {name: strategy for name, strategy in all_strategies.items() 
                         if name in strategy_names}
        else:
            strategies = all_strategies
        
        # 计算回测期间
        all_dates = []
        for data in stock_data.values():
            all_dates.extend(data.index.tolist())
        
        if not all_dates:
            logger.error("没有可用的股票数据")
            return {}
        
        start_date = min(all_dates).strftime('%Y-%m-%d')
        end_date = max(all_dates).strftime('%Y-%m-%d')
        symbols = list(stock_data.keys())
        
        logger.info(f"回测期间: {start_date} 至 {end_date}")
        logger.info(f"回测股票: {len(symbols)} 只")
        
        # 运行回测
        results = {}
        
        for strategy_name, strategy in strategies.items():
            logger.info(f"🔄 正在回测策略: {strategy_name}")
            
            try:
                # 创建独立的回测引擎
                engine = BacktestEngine(
                    initial_capital=1000000,
                    commission_rate=0.0003,
                    stamp_tax_rate=0.001,
                    min_trade_unit=100
                )
                
                result = engine.run_backtest(
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
                logger.error(f"❌ 策略 {strategy_name} 回测失败: {e}")
                continue
        
        self.backtest_results = results
        return results
    
    def analyze_results(self) -> pd.DataFrame:
        """分析回测结果"""
        if not self.backtest_results:
            logger.warning("没有回测结果可分析")
            return pd.DataFrame()
        
        # 创建结果对比表
        comparison_data = []
        
        for strategy_name, result in self.backtest_results.items():
            metrics = result['performance_metrics']
            comparison_data.append({
                '策略名称': strategy_name,
                '总收益率': f"{metrics['total_return']:.2%}",
                '年化收益率': f"{metrics['annualized_return']:.2%}",
                '波动率': f"{metrics['volatility']:.2%}",
                '夏普比率': f"{metrics['sharpe_ratio']:.2f}",
                '最大回撤': f"{metrics['max_drawdown']:.2%}",
                '胜率': f"{metrics['win_rate']:.2%}",
                '盈亏比': f"{metrics['profit_loss_ratio']:.2f}",
                '交易次数': metrics['total_trades'],
                '最终资产': f"{metrics['final_value']:,.0f}元",
                '收益排名': 0  # 稍后计算
            })
        
        comparison_df = pd.DataFrame(comparison_data)
        
        # 计算收益排名
        comparison_df['收益率_数值'] = comparison_df['总收益率'].str.rstrip('%').astype(float)
        comparison_df['收益排名'] = comparison_df['收益率_数值'].rank(ascending=False, method='min').astype(int)
        comparison_df = comparison_df.drop('收益率_数值', axis=1)
        
        # 按收益率排序
        comparison_df = comparison_df.sort_values('收益排名')
        
        logger.info("\n🏆 最大收益策略回测结果排行榜:")
        logger.info("=" * 120)
        print(comparison_df.to_string(index=False))
        
        # 显示最佳策略
        if not comparison_df.empty:
            best_strategy = comparison_df.iloc[0]
            logger.info(f"\n🥇 最佳策略: {best_strategy['策略名称']}")
            logger.info(f"   总收益率: {best_strategy['总收益率']}")
            logger.info(f"   年化收益率: {best_strategy['年化收益率']}")
            logger.info(f"   夏普比率: {best_strategy['夏普比率']}")
            logger.info(f"   最大回撤: {best_strategy['最大回撤']}")
        
        return comparison_df
    
    def run_complete_backtest(self, 
                            days: int = 365,
                            max_stocks_per_sector: int = 5,
                            strategy_names: List[str] = None,
                            custom_sector_weights: Dict[str, float] = None):
        """
        运行完整的最大收益回测流程
        
        Args:
            days: 数据天数
            max_stocks_per_sector: 每个板块最大股票数
            strategy_names: 要测试的策略名称列表
            custom_sector_weights: 自定义板块权重
        """
        logger.info("=" * 80)
        logger.info("🚀 开始最大收益策略回测系统")
        logger.info(f"📅 数据周期: {days}天 (约{days//30}个月)")
        logger.info("=" * 80)
        
        try:
            # 1. 配置板块
            logger.info("步骤1: 配置投资板块")
            if custom_sector_weights:
                self.configure_sectors(custom_weights=custom_sector_weights)
            
            # 2. 选择股票
            logger.info("步骤2: 按板块选择股票")
            self.select_stocks_by_sectors(max_stocks_per_sector)
            
            # 3. 下载数据
            logger.info("步骤3: 下载历史数据")
            stock_data = self.download_stock_data(days)
            
            if not stock_data:
                logger.error("未获取到股票数据，退出")
                return
            
            # 4. 运行策略回测
            logger.info("步骤4: 运行策略回测")
            results = self.run_strategy_backtest(stock_data, strategy_names)
            
            if not results:
                logger.error("回测失败，退出")
                return
            
            # 5. 分析结果
            logger.info("步骤5: 分析回测结果")
            self.analyze_results()
            
            logger.info("=" * 80)
            logger.info("🎉 最大收益策略回测完成！")
            logger.info("=" * 80)
            
        except Exception as e:
            logger.error(f"回测过程中出现错误: {e}")
            raise


def main():
    """主函数"""
    # 创建最大收益回测系统
    backtest_system = MaxProfitBacktest()
    
    # 自定义板块权重 (可选)
    custom_weights = {
        '科技龙头': 0.20,    # 加大科技权重
        '新能源': 0.20,      # 加大新能源权重
        '人工智能': 0.15,    # 加大AI权重
        '消费品牌': 0.15,    # 保持消费权重
        '医药生物': 0.10,    # 保持医药权重
        '金融银行': 0.10,    # 减少金融权重
        '地产建筑': 0.05,    # 减少地产权重
        '先进制造': 0.05     # 减少制造权重
    }
    
    # 运行完整回测
    backtest_system.run_complete_backtest(
        days=180,                    # 使用半年历史数据
        max_stocks_per_sector=4,     # 每个板块最多4只股票
        strategy_names=None,         # 测试所有策略
        custom_sector_weights=custom_weights  # 使用自定义权重
    )


if __name__ == "__main__":
    main() 