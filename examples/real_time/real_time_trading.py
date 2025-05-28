#!/usr/bin/env python3
"""
实时交易策略执行系统
每日拉取最新数据，执行策略，生成报表
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
import schedule

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


class RealTimeTradingSystem:
    """实时交易策略执行系统"""
    
    def __init__(self, config_file: str = "config/trading_config.json"):
        """初始化实时交易系统"""
        self.project_root = project_root
        self.config_file = config_file
        self.config = self._load_config()
        
        # 初始化组件
        self.db_manager = DatabaseManager()
        self.data_fetcher = RealDataFetcher(self.db_manager)
        
        # 创建报表目录
        self.reports_dir = os.path.join(self.project_root, "reports")
        self.daily_reports_dir = os.path.join(self.reports_dir, "daily")
        self.strategy_reports_dir = os.path.join(self.reports_dir, "strategy")
        
        for dir_path in [self.reports_dir, self.daily_reports_dir, self.strategy_reports_dir]:
            os.makedirs(dir_path, exist_ok=True)
        
        # 初始化策略
        self.strategies = self._initialize_strategies()
        
        logger.info("实时交易系统初始化完成")
    
    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        config_path = os.path.join(self.project_root, self.config_file)
        
        # 默认配置
        default_config = {
            "stock_pool": [
                # 科技龙头
                "002415", "300059", "300124", "002230",
                # 新能源
                "002594", "300750", "002475", "300274",
                # 人工智能
                "300496", "300433", "002252", "300144",
                # 消费品牌
                "000063", "000568", "002352", "000725",
                # 医药生物
                "300015", "300142", "002241", "000538",
                # 金融银行
                "000001", "600036", "600000", "601318",
                # 地产建筑
                "000002", "600048", "000069", "600606",
                # 先进制造
                "002371", "002405", "300296", "300408",
                # 新材料
                "002555", "300251", "002714", "300454"
            ],
            "strategies": {
                "布林带策略": {"enabled": True, "weight": 0.25},
                "优化双均线策略": {"enabled": True, "weight": 0.25},
                "快速MACD策略": {"enabled": True, "weight": 0.25},
                "KDJ策略": {"enabled": True, "weight": 0.25}
            },
            "trading": {
                "initial_capital": 1000000,
                "commission_rate": 0.0003,
                "stamp_tax_rate": 0.001,
                "position_size_pct": 0.03
            },
            "schedule": {
                "data_update_time": "09:00",
                "strategy_run_time": "15:30",
                "report_time": "16:00"
            }
        }
        
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                # 合并默认配置
                for key, value in default_config.items():
                    if key not in config:
                        config[key] = value
            else:
                config = default_config
                # 创建配置目录和文件
                os.makedirs(os.path.dirname(config_path), exist_ok=True)
                with open(config_path, 'w', encoding='utf-8') as f:
                    json.dump(config, f, ensure_ascii=False, indent=2)
                logger.info(f"创建默认配置文件: {config_path}")
            
            return config
            
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
            return default_config
    
    def _initialize_strategies(self) -> Dict[str, Any]:
        """初始化策略"""
        strategies = {}
        
        # 单一策略
        strategies['布林带策略'] = BollingerStrategy({
            'period': 18,
            'std_dev': 2.2,
            'oversold_threshold': 0.15,
            'overbought_threshold': 0.85
        })
        
        strategies['优化双均线策略'] = DoubleMaStrategy({
            'short_window': 8,
            'long_window': 21
        })
        
        strategies['快速MACD策略'] = MACDStrategy({
            'fast_period': 10,
            'slow_period': 22,
            'signal_period': 8
        })
        
        strategies['KDJ策略'] = KDJStrategy({
            'k_period': 8,
            'd_period': 3,
            'oversold': 25,
            'overbought': 75
        })
        
        strategies['动态RSI策略'] = RSIStrategy({
            'rsi_period': 12,
            'oversold': 25,
            'overbought': 75
        })
        
        # 多策略组合
        enabled_strategies = {name: strategy for name, strategy in strategies.items() 
                            if self.config['strategies'].get(name, {}).get('enabled', False)}
        
        if len(enabled_strategies) > 1:
            # 创建组合策略
            strategy_weights = {}
            total_weight = sum(self.config['strategies'].get(name, {}).get('weight', 0) 
                             for name in enabled_strategies.keys())
            
            for name, strategy in enabled_strategies.items():
                weight = self.config['strategies'].get(name, {}).get('weight', 0)
                if total_weight > 0:
                    strategy_weights[strategy] = weight / total_weight
            
            if strategy_weights:
                strategies['智能组合策略'] = MultiStrategy(strategy_weights, {
                    'signal_threshold': 0.4,
                    'max_positions': 15,
                    'rebalance_frequency': 3
                })
        
        logger.info(f"初始化{len(strategies)}个策略")
        return strategies
    
    def update_daily_data(self) -> Dict[str, pd.DataFrame]:
        """更新当日数据"""
        logger.info("开始更新当日股票数据...")
        
        stock_pool = self.config['stock_pool']
        end_date = datetime.now()
        start_date = end_date - timedelta(days=60)  # 获取60天数据用于技术指标计算
        
        stock_data = {}
        success_count = 0
        
        for i, symbol in enumerate(stock_pool):
            try:
                data = self.data_fetcher.get_stock_data(
                    symbol,
                    start_date.strftime('%Y-%m-%d'),
                    end_date.strftime('%Y-%m-%d')
                )
                
                if not data.empty and len(data) >= 30:
                    # 计算技术指标
                    data = self.data_fetcher.calculate_technical_indicators(data)
                    stock_data[symbol] = data
                    success_count += 1
                    logger.debug(f"更新 {symbol}: {len(data)} 条数据")
                else:
                    logger.warning(f"股票 {symbol} 数据不足")
                
                # 限制请求频率
                time.sleep(0.1)
                
            except Exception as e:
                logger.error(f"更新 {symbol} 数据失败: {e}")
                continue
        
        logger.info(f"数据更新完成，成功更新{success_count}只股票")
        return stock_data
    
    def run_strategies(self, stock_data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """运行所有策略"""
        logger.info("开始执行策略分析...")
        
        strategy_results = {}
        today = datetime.now().strftime('%Y-%m-%d')
        
        for strategy_name, strategy in self.strategies.items():
            if not self.config['strategies'].get(strategy_name, {}).get('enabled', True):
                continue
            
            logger.info(f"执行策略: {strategy_name}")
            
            try:
                # 为每个策略创建独立的回测引擎
                engine = BacktestEngine(
                    initial_capital=self.config['trading']['initial_capital'],
                    commission_rate=self.config['trading']['commission_rate'],
                    stamp_tax_rate=self.config['trading']['stamp_tax_rate']
                )
                
                # 运行策略
                signals_summary = {}
                total_signals = 0
                
                for symbol, data in stock_data.items():
                    if len(data) < 30:
                        continue
                    
                    signals = strategy.generate_signals(data, symbol)
                    if signals:
                        # 只关注最新的信号
                        latest_signals = [s for s in signals if s.timestamp.date() == datetime.now().date()]
                        if latest_signals:
                            signals_summary[symbol] = {
                                'signals': len(latest_signals),
                                'latest_signal': latest_signals[-1].signal_type,
                                'price': latest_signals[-1].price,
                                'reason': latest_signals[-1].reason
                            }
                            total_signals += len(latest_signals)
                
                strategy_results[strategy_name] = {
                    'date': today,
                    'total_signals': total_signals,
                    'signals_by_stock': signals_summary,
                    'strategy_config': strategy.config,
                    'description': strategy.get_strategy_description()
                }
                
                logger.info(f"{strategy_name}: 生成{total_signals}个信号")
                
            except Exception as e:
                logger.error(f"策略 {strategy_name} 执行失败: {e}")
                continue
        
        return strategy_results
    
    def generate_daily_report(self, strategy_results: Dict[str, Any]) -> str:
        """生成每日报表"""
        today = datetime.now().strftime('%Y-%m-%d')
        report_file = os.path.join(self.daily_reports_dir, f"daily_report_{today}.json")
        
        # 创建报表数据
        report_data = {
            'date': today,
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'total_strategies': len(strategy_results),
                'total_signals': sum(result['total_signals'] for result in strategy_results.values()),
                'active_stocks': len(set().union(*[
                    result['signals_by_stock'].keys() 
                    for result in strategy_results.values()
                ]))
            },
            'strategies': strategy_results,
            'config': self.config
        }
        
        # 保存JSON报表
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)
        
        # 生成可读性报表
        readable_report = self._generate_readable_report(report_data)
        readable_file = os.path.join(self.daily_reports_dir, f"daily_report_{today}.txt")
        
        with open(readable_file, 'w', encoding='utf-8') as f:
            f.write(readable_report)
        
        logger.info(f"每日报表已生成: {report_file}")
        return report_file
    
    def _generate_readable_report(self, report_data: Dict[str, Any]) -> str:
        """生成可读性报表"""
        report = []
        report.append("=" * 80)
        report.append(f"📊 每日策略执行报表 - {report_data['date']}")
        report.append("=" * 80)
        report.append("")
        
        # 概要信息
        summary = report_data['summary']
        report.append("📈 执行概要:")
        report.append(f"  • 策略数量: {summary['total_strategies']}")
        report.append(f"  • 总信号数: {summary['total_signals']}")
        report.append(f"  • 活跃股票: {summary['active_stocks']}只")
        report.append("")
        
        # 策略详情
        report.append("🎯 策略执行详情:")
        report.append("-" * 60)
        
        for strategy_name, result in report_data['strategies'].items():
            report.append(f"\n📋 {strategy_name}")
            report.append(f"  描述: {result['description']}")
            report.append(f"  信号数量: {result['total_signals']}")
            
            if result['signals_by_stock']:
                report.append("  今日信号:")
                for symbol, signal_info in result['signals_by_stock'].items():
                    report.append(f"    {symbol}: {signal_info['latest_signal']} @ {signal_info['price']:.2f}")
                    report.append(f"      原因: {signal_info['reason']}")
            else:
                report.append("  今日无信号")
        
        report.append("")
        report.append("=" * 80)
        report.append(f"报表生成时间: {report_data['timestamp']}")
        report.append("=" * 80)
        
        return "\n".join(report)
    
    def generate_strategy_performance_report(self) -> str:
        """生成策略表现报表"""
        logger.info("生成策略表现报表...")
        
        # 读取历史报表数据
        performance_data = {}
        
        for filename in os.listdir(self.daily_reports_dir):
            if filename.startswith("daily_report_") and filename.endswith(".json"):
                try:
                    file_path = os.path.join(self.daily_reports_dir, filename)
                    with open(file_path, 'r', encoding='utf-8') as f:
                        daily_data = json.load(f)
                    
                    date = daily_data['date']
                    for strategy_name, result in daily_data['strategies'].items():
                        if strategy_name not in performance_data:
                            performance_data[strategy_name] = []
                        
                        performance_data[strategy_name].append({
                            'date': date,
                            'signals': result['total_signals'],
                            'active_stocks': len(result['signals_by_stock'])
                        })
                        
                except Exception as e:
                    logger.error(f"读取报表文件失败 {filename}: {e}")
                    continue
        
        # 生成表现报表
        today = datetime.now().strftime('%Y-%m-%d')
        performance_file = os.path.join(self.strategy_reports_dir, f"strategy_performance_{today}.json")
        
        summary_data = {}
        for strategy_name, daily_records in performance_data.items():
            if daily_records:
                df = pd.DataFrame(daily_records)
                summary_data[strategy_name] = {
                    'total_days': int(len(daily_records)),
                    'total_signals': int(df['signals'].sum()),
                    'avg_daily_signals': float(df['signals'].mean()),
                    'max_daily_signals': int(df['signals'].max()),
                    'signal_frequency': float((df['signals'] > 0).mean()),
                    'avg_active_stocks': float(df['active_stocks'].mean())
                }
        
        with open(performance_file, 'w', encoding='utf-8') as f:
            json.dump(summary_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"策略表现报表已生成: {performance_file}")
        return performance_file
    
    def run_daily_task(self):
        """执行每日任务"""
        logger.info("🚀 开始执行每日策略任务")
        
        try:
            # 1. 更新数据
            stock_data = self.update_daily_data()
            
            if not stock_data:
                logger.error("未获取到股票数据，任务终止")
                return
            
            # 2. 执行策略
            strategy_results = self.run_strategies(stock_data)
            
            # 3. 生成报表
            daily_report = self.generate_daily_report(strategy_results)
            performance_report = self.generate_strategy_performance_report()
            
            logger.info("✅ 每日策略任务执行完成")
            logger.info(f"📄 每日报表: {daily_report}")
            logger.info(f"📊 表现报表: {performance_report}")
            
        except Exception as e:
            logger.error(f"每日任务执行失败: {e}")
            raise
    
    def start_scheduler(self):
        """启动定时任务"""
        logger.info("启动实时交易系统定时任务...")
        
        # 设置定时任务
        schedule_config = self.config['schedule']
        
        # 每日数据更新
        schedule.every().day.at(schedule_config['data_update_time']).do(self.update_daily_data)
        
        # 每日策略执行
        schedule.every().day.at(schedule_config['strategy_run_time']).do(self.run_daily_task)
        
        # 每日报表生成
        schedule.every().day.at(schedule_config['report_time']).do(self.generate_strategy_performance_report)
        
        logger.info(f"定时任务已设置:")
        logger.info(f"  数据更新: 每日 {schedule_config['data_update_time']}")
        logger.info(f"  策略执行: 每日 {schedule_config['strategy_run_time']}")
        logger.info(f"  报表生成: 每日 {schedule_config['report_time']}")
        
        # 运行定时任务
        while True:
            schedule.run_pending()
            time.sleep(60)  # 每分钟检查一次
    
    def run_once(self):
        """立即执行一次任务（用于测试）"""
        logger.info("立即执行策略任务...")
        self.run_daily_task()


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="实时交易策略执行系统")
    parser.add_argument("--mode", choices=["once", "schedule"], default="once",
                       help="运行模式: once=立即执行一次, schedule=启动定时任务")
    parser.add_argument("--config", default="config/trading_config.json",
                       help="配置文件路径")
    
    args = parser.parse_args()
    
    # 创建系统实例
    trading_system = RealTimeTradingSystem(args.config)
    
    if args.mode == "once":
        # 立即执行一次
        trading_system.run_once()
    else:
        # 启动定时任务
        trading_system.start_scheduler()


if __name__ == "__main__":
    main() 