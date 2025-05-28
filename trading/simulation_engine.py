#!/usr/bin/env python3
"""
基于真实数据的模拟交易引擎
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import time
import threading
from loguru import logger

from data.database import DatabaseManager
from utils.real_data_fetcher import RealDataFetcher
from utils.position_manager import PositionManager
from strategies.strategy_manager import StrategyManager


class RealSimulationEngine:
    """基于真实数据的模拟交易引擎"""

    def __init__(self, config: dict):
        """
        初始化模拟交易引擎

        Args:
            config: 配置字典
        """
        self.config = config
        self.stock_pool = config.get('stock_pool', {}).get('default_stocks', [])

        # 初始化组件
        self.db_manager = DatabaseManager()
        self.data_fetcher = RealDataFetcher(self.db_manager)
        self.position_manager = PositionManager(config)
        self.strategy_manager = StrategyManager(config)

        # 设置股票池
        self.data_fetcher.set_stock_pool(self.stock_pool)

        # 运行状态
        self.is_running = False
        self.trading_thread = None

        # 交易统计
        self.total_signals = 0
        self.total_trades = 0
        self.last_portfolio_snapshot = None

        logger.info("真实数据模拟交易引擎初始化完成")

    def initialize_data(self):
        """初始化历史数据"""
        logger.info("正在初始化历史数据...")

        # 刷新历史数据
        self.data_fetcher.refresh_historical_data(days=100)

        # 启动实时数据更新
        self.data_fetcher.start_real_time_update(interval=30)

        logger.info("历史数据初始化完成")

    def start_simulation(self):
        """启动模拟交易"""
        if self.is_running:
            logger.warning("模拟交易已在运行中")
            return

        # 初始化数据
        self.initialize_data()

        self.is_running = True
        logger.info("🚀 启动真实数据模拟交易引擎")

        # 启动交易主循环
        self.trading_thread = threading.Thread(target=self._trading_loop, daemon=True)
        self.trading_thread.start()

        logger.info("模拟交易引擎已启动")

    def stop_simulation(self):
        """停止模拟交易"""
        self.is_running = False

        # 停止实时数据更新
        self.data_fetcher.stop_real_time_update()

        if self.trading_thread:
            self.trading_thread.join(timeout=10)

        logger.info("⏹️ 模拟交易引擎已停止")

    def _trading_loop(self):
        """交易主循环"""
        while self.is_running:
            try:
                # 检查市场状态
                market_status = self.data_fetcher.get_market_status()

                # 在交易时间或测试模式下执行交易逻辑
                if market_status['is_trading_time'] or True:  # 测试时总是执行

                    # 1. 获取最新数据
                    current_prices = self.data_fetcher.get_current_prices()

                    if current_prices:
                        # 2. 生成交易信号
                        signals = self._generate_trading_signals()

                        # 3. 执行交易
                        if signals:
                            self._execute_trades(signals, current_prices)

                        # 4. 风险控制
                        self._risk_control(current_prices)

                        # 5. 更新持仓
                        self._update_positions(current_prices)

                        # 6. 保存投资组合快照
                        self._save_portfolio_snapshot(current_prices)

                # 等待下次循环
                time.sleep(60)  # 1分钟执行一次

            except Exception as e:
                logger.error(f"交易循环异常: {e}")
                time.sleep(10)

    def _generate_trading_signals(self):
        """生成交易信号"""
        try:
            # 获取所有股票的历史数据
            stock_data = {}

            for symbol in self.stock_pool:
                data = self.db_manager.get_stock_data(symbol, limit=100)
                if not data.empty:
                    stock_data[symbol] = data

            if not stock_data:
                return []

            # 使用策略管理器生成信号
            signals = self.strategy_manager.generate_combined_signals(stock_data)

            # 保存信号到数据库
            for signal in signals:
                self.db_manager.save_signal(
                    symbol=signal.symbol,
                    signal_type=signal.signal_type,
                    strength=signal.combined_strength,
                    price=self.data_fetcher.current_prices.get(signal.symbol, 0),
                    strategy='combined',
                    reason=f"组合信号，置信度: {signal.confidence:.2f}"
                )

            self.total_signals += len(signals)

            if signals:
                logger.info(f"生成 {len(signals)} 个交易信号")

            return signals

        except Exception as e:
            logger.error(f"生成交易信号异常: {e}")
            return []

    def _execute_trades(self, signals, current_prices):
        """执行交易"""
        try:
            for signal in signals:
                symbol = signal.symbol
                signal_type = signal.signal_type
                strength = signal.combined_strength

                if symbol not in current_prices:
                    continue

                price = current_prices[symbol]

                if signal_type == 'BUY':
                    self._execute_buy_order(symbol, strength, price, signal)
                elif signal_type == 'SELL':
                    self._execute_sell_order(symbol, strength, price, signal)

        except Exception as e:
            logger.error(f"执行交易异常: {e}")

    def _execute_buy_order(self, symbol, strength, price, signal):
        """执行买入订单"""
        try:
            # 计算建仓数量
            shares = self.position_manager.calculate_position_size(
                symbol=symbol,
                signal_strength=strength,
                current_price=price
            )

            if shares > 0:
                # 执行买入
                success = self.position_manager.buy_stock(symbol, shares, price)

                if success:
                    # 保存交易记录
                    commission = shares * price * 0.0003
                    self.db_manager.save_trade(
                        symbol=symbol,
                        action='BUY',
                        shares=shares,
                        price=price,
                        amount=shares * price,
                        commission=commission,
                        strategy='combined'
                    )

                    self.total_trades += 1
                    logger.info(f"✅ 买入: {symbol} {shares}股 @ ¥{price:.2f}")

        except Exception as e:
            logger.error(f"执行买入订单异常: {e}")

    def _execute_sell_order(self, symbol, strength, price, signal):
        """执行卖出订单"""
        try:
            if symbol not in self.position_manager.positions:
                return

            position = self.position_manager.positions[symbol]

            # 计算卖出数量
            sell_ratio = min(1.0, strength)
            shares_to_sell = int(position.shares * sell_ratio)
            shares_to_sell = (shares_to_sell // 100) * 100  # 整手

            if shares_to_sell > 0:
                # 执行卖出
                success = self.position_manager.sell_stock(symbol, shares_to_sell, price)

                if success:
                    # 保存交易记录
                    commission = shares_to_sell * price * 0.0003
                    stamp_tax = shares_to_sell * price * 0.001

                    self.db_manager.save_trade(
                        symbol=symbol,
                        action='SELL',
                        shares=shares_to_sell,
                        price=price,
                        amount=shares_to_sell * price,
                        commission=commission + stamp_tax,
                        strategy='combined'
                    )

                    self.total_trades += 1
                    logger.info(f"✅ 卖出: {symbol} {shares_to_sell}股 @ ¥{price:.2f}")

        except Exception as e:
            logger.error(f"执行卖出订单异常: {e}")

    def _risk_control(self, current_prices):
        """风险控制"""
        try:
            risk_actions = self.position_manager.check_risk_control(current_prices)

            for symbol, action, shares in risk_actions:
                if action == 'sell' and symbol in current_prices:
                    price = current_prices[symbol]
                    success = self.position_manager.sell_stock(symbol, shares, price)

                    if success:
                        # 保存风控交易记录
                        commission = shares * price * 0.0013  # 包含印花税

                        self.db_manager.save_trade(
                            symbol=symbol,
                            action='SELL',
                            shares=shares,
                            price=price,
                            amount=shares * price,
                            commission=commission,
                            strategy='risk_control'
                        )

                        logger.warning(f"🛡️ 风控卖出: {symbol} {shares}股 @ ¥{price:.2f}")

        except Exception as e:
            logger.error(f"风险控制异常: {e}")

    def _update_positions(self, current_prices):
        """更新持仓记录"""
        try:
            for symbol, position in self.position_manager.positions.items():
                if symbol in current_prices:
                    current_price = current_prices[symbol]
                    self.db_manager.update_position(
                        symbol=symbol,
                        shares=position.shares,
                        avg_price=position.avg_price,
                        current_price=current_price
                    )

        except Exception as e:
            logger.error(f"更新持仓记录异常: {e}")

    def _save_portfolio_snapshot(self, current_prices):
        """保存投资组合快照"""
        try:
            portfolio_status = self.position_manager.get_portfolio_status(current_prices)

            self.db_manager.save_portfolio_snapshot(
                total_value=portfolio_status.total_value,
                cash=portfolio_status.cash,
                positions_value=portfolio_status.market_value,
                total_pnl=portfolio_status.total_pnl,
                total_pnl_pct=portfolio_status.total_pnl_pct,
                position_count=portfolio_status.position_count
            )

            self.last_portfolio_snapshot = portfolio_status

        except Exception as e:
            logger.error(f"保存投资组合快照异常: {e}")

    def get_current_status(self) -> Dict:
        """获取当前状态"""
        try:
            current_prices = self.data_fetcher.get_current_prices()
            portfolio_status = self.position_manager.get_portfolio_status(current_prices)
            market_status = self.data_fetcher.get_market_status()

            return {
                'is_running': self.is_running,
                'market_status': market_status,
                'portfolio_status': portfolio_status,
                'current_prices': current_prices,
                'total_signals': self.total_signals,
                'total_trades': self.total_trades,
                'last_update_time': self.data_fetcher.last_update_time,
                'stock_pool': self.stock_pool
            }

        except Exception as e:
            logger.error(f"获取当前状态异常: {e}")
            return {}

    def get_portfolio_history(self, days: int = 30) -> pd.DataFrame:
        """获取投资组合历史"""
        return self.db_manager.get_portfolio_history(days)

    def get_recent_signals(self, limit: int = 50) -> pd.DataFrame:
        """获取最近信号"""
        return self.db_manager.get_recent_signals(limit)

    def get_recent_trades(self, limit: int = 50) -> pd.DataFrame:
        """获取最近交易"""
        return self.db_manager.get_recent_trades(limit)

    def get_position_summary(self) -> pd.DataFrame:
        """获取持仓汇总"""
        current_prices = self.data_fetcher.get_current_prices()
        return self.position_manager.get_position_summary(current_prices)