#!/usr/bin/env python3
"""
高换手率股票策略回测
拉取过去一个月换手率最高的100只股票，进行策略回测
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Any
import time
from loguru import logger
import matplotlib.pyplot as plt
import seaborn as sns

# 导入项目模块
from data.database import DatabaseManager
from utils.real_data_fetcher import RealDataFetcher
from backtest.backtest_engine import BacktestEngine
from strategies.double_ma_strategy import DoubleMaStrategy
from strategies.rsi_strategy import RSIStrategy
from strategies.macd_strategy import MACDStrategy

try:
    import akshare as ak
    AKSHARE_AVAILABLE = True
except ImportError:
    AKSHARE_AVAILABLE = False
    logger.warning("AKShare未安装，将使用模拟数据")

plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False


class HighTurnoverBacktest:
    """高换手率股票回测系统"""
    
    def __init__(self):
        """初始化回测系统"""
        self.db_manager = DatabaseManager()
        self.data_fetcher = RealDataFetcher(self.db_manager)
        self.backtest_engine = BacktestEngine(
            initial_capital=1000000,  # 100万初始资金
            commission_rate=0.0003,   # 万3手续费
            stamp_tax_rate=0.001      # 千1印花税
        )
        
        self.high_turnover_stocks = []
        self.backtest_results = {}
        
        logger.info("高换手率股票回测系统初始化完成")
    
    def get_high_turnover_stocks(self, days: int = 30, top_n: int = 100) -> List[str]:
        """
        获取过去一个月换手率最高的股票
        
        Args:
            days: 统计天数
            top_n: 取前N只股票
            
        Returns:
            股票代码列表
        """
        logger.info(f"开始获取过去{days}天换手率最高的{top_n}只股票...")
        
        if not AKSHARE_AVAILABLE:
            logger.warning("AKShare不可用，使用模拟股票池")
            return self._get_mock_high_turnover_stocks(top_n)
        
        try:
            # 获取所有A股基本信息
            stock_info = ak.stock_info_a_code_name()
            logger.info(f"获取到{len(stock_info)}只A股信息")
            
            # 计算换手率
            turnover_data = []
            
            for idx, row in stock_info.iterrows():
                stock_code = row['code']
                stock_name = row['name']
                
                try:
                    # 获取个股资金流向数据（包含换手率）
                    end_date = datetime.now()
                    start_date = end_date - timedelta(days=days)
                    
                    # 获取股票基本信息
                    stock_individual_info = ak.stock_individual_info_em(symbol=stock_code)
                    
                    if not stock_individual_info.empty:
                        # 查找换手率信息
                        turnover_row = stock_individual_info[stock_individual_info['item'] == '换手率']
                        if not turnover_row.empty:
                            turnover_rate = turnover_row.iloc[0]['value']
                            try:
                                turnover_rate = float(turnover_rate.replace('%', ''))
                                turnover_data.append({
                                    'code': stock_code,
                                    'name': stock_name,
                                    'turnover_rate': turnover_rate
                                })
                            except:
                                continue
                    
                    # 限制请求频率
                    time.sleep(0.1)
                    
                    # 每处理100只股票显示进度
                    if (idx + 1) % 100 == 0:
                        logger.info(f"已处理 {idx + 1}/{len(stock_info)} 只股票")
                    
                    # 为了演示，只处理前500只股票
                    if idx >= 500:
                        break
                        
                except Exception as e:
                    logger.debug(f"获取{stock_code}换手率失败: {e}")
                    continue
            
            # 按换手率排序
            turnover_df = pd.DataFrame(turnover_data)
            if turnover_df.empty:
                logger.warning("未获取到换手率数据，使用模拟数据")
                return self._get_mock_high_turnover_stocks(top_n)
            
            turnover_df = turnover_df.sort_values('turnover_rate', ascending=False)
            top_stocks = turnover_df.head(top_n)
            
            logger.info(f"换手率最高的{top_n}只股票:")
            for _, row in top_stocks.head(10).iterrows():
                logger.info(f"  {row['code']} {row['name']}: {row['turnover_rate']:.2f}%")
            
            self.high_turnover_stocks = top_stocks['code'].tolist()
            return self.high_turnover_stocks
            
        except Exception as e:
            logger.error(f"获取高换手率股票失败: {e}")
            return self._get_mock_high_turnover_stocks(top_n)
    
    def _get_mock_high_turnover_stocks(self, top_n: int) -> List[str]:
        """获取模拟的高换手率股票"""
        # 使用一些活跃的股票作为示例
        mock_stocks = [
            '000001', '000002', '000858', '002415', '002594', '002714', '300059',
            '300122', '300124', '300142', '300144', '300251', '300274', '300296',
            '300316', '300347', '300408', '300433', '300454', '300496',
            '600000', '600036', '600519', '600887', '601318', '601398', '601857',
            '002230', '002241', '002252', '002304', '002352', '002371', '002405',
            '002456', '002475', '002493', '002508', '002555', '002558',
            '000063', '000069', '000100', '000157', '000166', '000338', '000425',
            '000503', '000538', '000568', '000623', '000651', '000703', '000725',
            '000768', '000776', '000783', '000792', '000839', '000876',
            '300003', '300015', '300017', '300027', '300033', '300070', '300072',
            '300073', '300104', '300113', '300136', '300146', '300168', '300182',
            '300207', '300226', '300253', '300271', '300285', '300315',
            '600009', '600010', '600015', '600028', '600030', '600031', '600048',
            '600050', '600061', '600066', '600085', '600089', '600104', '600111',
            '600115', '600118', '600150', '600161', '600170', '600177'
        ]
        
        # 随机选择并模拟换手率
        selected_stocks = mock_stocks[:min(top_n, len(mock_stocks))]
        logger.info(f"使用模拟高换手率股票池: {len(selected_stocks)}只股票")
        
        self.high_turnover_stocks = selected_stocks
        return selected_stocks
    
    def download_stock_data(self, days: int = 60) -> Dict[str, pd.DataFrame]:
        """
        下载股票历史数据
        
        Args:
            days: 下载天数
            
        Returns:
            股票数据字典
        """
        logger.info(f"开始下载{len(self.high_turnover_stocks)}只股票的{days}天历史数据...")
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        stock_data = {}
        success_count = 0
        
        for i, symbol in enumerate(self.high_turnover_stocks):
            try:
                data = self.data_fetcher.get_stock_data(
                    symbol, 
                    start_date.strftime('%Y-%m-%d'),
                    end_date.strftime('%Y-%m-%d')
                )
                
                if not data.empty and len(data) >= 20:  # 至少20个交易日
                    # 计算技术指标
                    data = self.data_fetcher.calculate_technical_indicators(data)
                    stock_data[symbol] = data
                    success_count += 1
                    logger.debug(f"成功下载 {symbol}: {len(data)} 条数据")
                else:
                    logger.warning(f"股票 {symbol} 数据不足，跳过")
                
                # 显示进度
                if (i + 1) % 10 == 0:
                    logger.info(f"数据下载进度: {i + 1}/{len(self.high_turnover_stocks)}")
                
                # 限制请求频率
                time.sleep(0.1)
                
            except Exception as e:
                logger.error(f"下载 {symbol} 数据失败: {e}")
                continue
        
        logger.info(f"数据下载完成，成功下载{success_count}只股票数据")
        return stock_data
    
    def run_strategy_backtest(self, stock_data: Dict[str, pd.DataFrame], 
                            strategy_name: str = 'all') -> Dict[str, Any]:
        """
        运行策略回测
        
        Args:
            stock_data: 股票数据字典
            strategy_name: 策略名称 ('double_ma', 'rsi', 'macd', 'all')
            
        Returns:
            回测结果
        """
        logger.info(f"开始运行策略回测，股票数量: {len(stock_data)}")
        
        # 定义策略
        strategies = {}
        
        if strategy_name in ['double_ma', 'all']:
            strategies['双均线策略'] = DoubleMaStrategy({'short_window': 5, 'long_window': 20})
        
        if strategy_name in ['rsi', 'all']:
            strategies['RSI策略'] = RSIStrategy({'rsi_period': 14, 'oversold': 30, 'overbought': 70})
        
        if strategy_name in ['macd', 'all']:
            strategies['MACD策略'] = MACDStrategy({'fast_period': 12, 'slow_period': 26, 'signal_period': 9})
        
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
            logger.info(f"正在回测策略: {strategy_name}")
            
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
                logger.info(f"{strategy_name} 回测完成:")
                logger.info(f"  总收益率: {metrics['total_return']:.2%}")
                logger.info(f"  年化收益率: {metrics['annualized_return']:.2%}")
                logger.info(f"  夏普比率: {metrics['sharpe_ratio']:.2f}")
                logger.info(f"  最大回撤: {metrics['max_drawdown']:.2%}")
                logger.info(f"  胜率: {metrics['win_rate']:.2%}")
                logger.info(f"  交易次数: {metrics['total_trades']}")
                
            except Exception as e:
                logger.error(f"策略 {strategy_name} 回测失败: {e}")
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
                '最终资产': f"{metrics['final_value']:,.0f}"
            })
        
        comparison_df = pd.DataFrame(comparison_data)
        
        logger.info("\n策略回测结果对比:")
        logger.info("\n" + comparison_df.to_string(index=False))
        
        return comparison_df
    
    def plot_results(self, save_path: str = None):
        """绘制回测结果图表"""
        if not self.backtest_results:
            logger.warning("没有回测结果可绘制")
            return
        
        # 创建图表
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        fig.suptitle('高换手率股票策略回测结果', fontsize=16)
        
        # 1. 策略收益对比
        strategy_names = []
        total_returns = []
        annualized_returns = []
        sharpe_ratios = []
        max_drawdowns = []
        
        for strategy_name, result in self.backtest_results.items():
            metrics = result['performance_metrics']
            strategy_names.append(strategy_name)
            total_returns.append(metrics['total_return'] * 100)
            annualized_returns.append(metrics['annualized_return'] * 100)
            sharpe_ratios.append(metrics['sharpe_ratio'])
            max_drawdowns.append(abs(metrics['max_drawdown']) * 100)
        
        # 收益率对比
        x = np.arange(len(strategy_names))
        width = 0.35
        
        axes[0, 0].bar(x - width/2, total_returns, width, label='总收益率', alpha=0.8)
        axes[0, 0].bar(x + width/2, annualized_returns, width, label='年化收益率', alpha=0.8)
        axes[0, 0].set_title('策略收益率对比')
        axes[0, 0].set_ylabel('收益率 (%)')
        axes[0, 0].set_xticks(x)
        axes[0, 0].set_xticklabels(strategy_names, rotation=45)
        axes[0, 0].legend()
        axes[0, 0].grid(True, alpha=0.3)
        
        # 风险指标对比
        axes[0, 1].bar(strategy_names, sharpe_ratios, alpha=0.8, color='green')
        axes[0, 1].set_title('夏普比率对比')
        axes[0, 1].set_ylabel('夏普比率')
        axes[0, 1].tick_params(axis='x', rotation=45)
        axes[0, 1].grid(True, alpha=0.3)
        
        # 最大回撤对比
        axes[1, 0].bar(strategy_names, max_drawdowns, alpha=0.8, color='red')
        axes[1, 0].set_title('最大回撤对比')
        axes[1, 0].set_ylabel('最大回撤 (%)')
        axes[1, 0].tick_params(axis='x', rotation=45)
        axes[1, 0].grid(True, alpha=0.3)
        
        # 资产价值曲线对比
        for strategy_name, result in self.backtest_results.items():
            portfolio_values = result['portfolio_values']
            if portfolio_values:
                dates = [pv['date'] for pv in portfolio_values]
                values = [pv['portfolio_value'] for pv in portfolio_values]
                axes[1, 1].plot(dates, values, label=strategy_name, linewidth=2)
        
        axes[1, 1].axhline(y=1000000, color='black', linestyle='--', alpha=0.5, label='初始资金')
        axes[1, 1].set_title('资产价值曲线')
        axes[1, 1].set_ylabel('资产价值 (元)')
        axes[1, 1].legend()
        axes[1, 1].grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            logger.info(f"图表已保存到: {save_path}")
        
        plt.show()
    
    def export_results(self, output_dir: str = "backtest_results"):
        """导出回测结果"""
        import os
        
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # 导出策略对比结果
        comparison_df = self.analyze_results()
        if not comparison_df.empty:
            comparison_file = f"{output_dir}/strategy_comparison_{timestamp}.csv"
            comparison_df.to_csv(comparison_file, index=False, encoding='utf-8-sig')
            logger.info(f"策略对比结果已导出到: {comparison_file}")
        
        # 导出详细交易记录
        for strategy_name, result in self.backtest_results.items():
            if result['trades']:
                trades_df = pd.DataFrame(result['trades'])
                trades_file = f"{output_dir}/{strategy_name}_trades_{timestamp}.csv"
                trades_df.to_csv(trades_file, index=False, encoding='utf-8-sig')
                logger.info(f"{strategy_name} 交易记录已导出到: {trades_file}")
        
        # 导出高换手率股票列表
        if self.high_turnover_stocks:
            stocks_df = pd.DataFrame({'股票代码': self.high_turnover_stocks})
            stocks_file = f"{output_dir}/high_turnover_stocks_{timestamp}.csv"
            stocks_df.to_csv(stocks_file, index=False, encoding='utf-8-sig')
            logger.info(f"高换手率股票列表已导出到: {stocks_file}")
    
    def run_complete_backtest(self, days: int = 30, top_n: int = 100, 
                            strategy: str = 'all', data_days: int = 60):
        """
        运行完整的回测流程
        
        Args:
            days: 统计换手率的天数
            top_n: 选择前N只高换手率股票
            strategy: 策略名称
            data_days: 下载数据的天数
        """
        logger.info("=" * 60)
        logger.info("开始高换手率股票策略回测")
        logger.info("=" * 60)
        
        try:
            # 1. 获取高换手率股票
            logger.info("步骤1: 获取高换手率股票")
            high_turnover_stocks = self.get_high_turnover_stocks(days, top_n)
            
            if not high_turnover_stocks:
                logger.error("未获取到高换手率股票，退出")
                return
            
            # 2. 下载股票数据
            logger.info("步骤2: 下载股票历史数据")
            stock_data = self.download_stock_data(data_days)
            
            if not stock_data:
                logger.error("未获取到股票数据，退出")
                return
            
            # 3. 运行策略回测
            logger.info("步骤3: 运行策略回测")
            results = self.run_strategy_backtest(stock_data, strategy)
            
            if not results:
                logger.error("回测失败，退出")
                return
            
            # 4. 分析结果
            logger.info("步骤4: 分析回测结果")
            self.analyze_results()
            
            # 5. 绘制图表
            logger.info("步骤5: 绘制结果图表")
            self.plot_results()
            
            # 6. 导出结果
            logger.info("步骤6: 导出回测结果")
            self.export_results()
            
            logger.info("=" * 60)
            logger.info("高换手率股票策略回测完成！")
            logger.info("=" * 60)
            
        except Exception as e:
            logger.error(f"回测过程中出现错误: {e}")
            raise


def main():
    """主函数"""
    # 创建回测系统
    backtest_system = HighTurnoverBacktest()
    
    # 运行完整回测
    backtest_system.run_complete_backtest(
        days=30,        # 统计过去30天的换手率
        top_n=50,       # 选择前50只股票（减少数量以提高速度）
        strategy='all', # 测试所有策略
        data_days=60    # 下载60天的历史数据
    )


if __name__ == "__main__":
    main() 