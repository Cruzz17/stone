#!/usr/bin/env python3
"""
仓位管理器
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from loguru import logger


@dataclass
class Position:
    """持仓信息"""
    symbol: str
    shares: int
    avg_cost: float
    current_price: float
    market_value: float
    unrealized_pnl: float
    unrealized_pnl_pct: float
    entry_date: datetime
    last_update: datetime


@dataclass
class PortfolioStatus:
    """投资组合状态"""
    total_value: float
    cash: float
    market_value: float
    total_pnl: float
    total_pnl_pct: float
    position_count: int
    positions: List[Position]
    last_update: datetime


class PositionManager:
    """仓位管理器"""

    def __init__(self, config: dict):
        """初始化仓位管理器"""
        self.config = config
        self.initial_capital = config.get('trading', {}).get('initial_capital', 100000)
        self.max_position_pct = config.get('position_management', {}).get('max_single_position', 0.25)
        self.max_total_position = config.get('position_management', {}).get('max_total_position', 0.90)
        self.cash_reserve = config.get('position_management', {}).get('cash_reserve', 0.10)
        self.stop_loss_pct = config.get('risk_management', {}).get('stop_loss', 0.08)
        self.take_profit_pct = config.get('risk_management', {}).get('take_profit', 0.15)
        self.cash = self.initial_capital
        self.positions = {}
        self.transaction_cost = 0.001
        logger.info(f"仓位管理器初始化完成，初始资金: ¥{self.initial_capital:,.2f}")

    def calculate_position_size(self, symbol: str, signal_strength: float, current_price: float) -> int:
        """计算建仓数量"""
        try:
            if symbol in self.positions:
                return 0
            available_cash = self.cash * (1 - self.cash_reserve)
            base_position_value = available_cash * self.max_position_pct * signal_strength
            current_market_value = sum(pos.market_value for pos in self.positions.values())
            total_value = self.cash + current_market_value
            current_position_pct = current_market_value / total_value
            if current_position_pct >= self.max_total_position:
                return 0
            remaining_capacity = (self.max_total_position - current_position_pct) * total_value
            position_value = min(base_position_value, remaining_capacity)
            shares = int(position_value / (current_price * (1 + self.transaction_cost)))
            required_cash = shares * current_price * (1 + self.transaction_cost)
            if required_cash > available_cash:
                shares = int(available_cash / (current_price * (1 + self.transaction_cost)))
            return max(0, shares)
        except Exception as e:
            logger.error(f"计算 {symbol} 仓位大小失败: {e}")
            return 0

    def get_portfolio_status(self, current_prices: Dict[str, float] = None) -> PortfolioStatus:
        """获取投资组合状态"""
        try:
            market_value = sum(pos.market_value for pos in self.positions.values())
            total_value = self.cash + market_value
            total_pnl = total_value - self.initial_capital
            total_pnl_pct = total_pnl / self.initial_capital if self.initial_capital > 0 else 0
            return PortfolioStatus(
                total_value=total_value,
                cash=self.cash,
                market_value=market_value,
                total_pnl=total_pnl,
                total_pnl_pct=total_pnl_pct,
                position_count=len(self.positions),
                positions=list(self.positions.values()),
                last_update=datetime.now()
            )
        except Exception as e:
            logger.error(f"获取投资组合状态失败: {e}")
            return PortfolioStatus(
                total_value=self.cash,
                cash=self.cash,
                market_value=0,
                total_pnl=self.cash - self.initial_capital,
                total_pnl_pct=(self.cash - self.initial_capital) / self.initial_capital,
                position_count=0,
                positions=[],
                last_update=datetime.now()
            )

    def buy_stock(self, symbol: str, shares: int, price: float) -> bool:
        """买入股票"""
        try:
            total_cost = shares * price * (1 + self.transaction_cost)
            
            if total_cost > self.cash:
                logger.warning(f"现金不足，无法买入 {symbol}")
                return False
            
            if symbol in self.positions:
                old_position = self.positions[symbol]
                total_shares = old_position.shares + shares
                total_cost_basis = old_position.avg_cost * old_position.shares + shares * price
                new_avg_cost = total_cost_basis / total_shares
                
                self.positions[symbol] = Position(
                    symbol=symbol,
                    shares=total_shares,
                    avg_cost=new_avg_cost,
                    current_price=price,
                    market_value=total_shares * price,
                    unrealized_pnl=(price - new_avg_cost) * total_shares,
                    unrealized_pnl_pct=(price - new_avg_cost) / new_avg_cost,
                    entry_date=old_position.entry_date,
                    last_update=datetime.now()
                )
            else:
                self.positions[symbol] = Position(
                    symbol=symbol,
                    shares=shares,
                    avg_cost=price,
                    current_price=price,
                    market_value=shares * price,
                    unrealized_pnl=0,
                    unrealized_pnl_pct=0,
                    entry_date=datetime.now(),
                    last_update=datetime.now()
                )
            
            self.cash -= total_cost
            logger.info(f"买入成功: {symbol} {shares}股 @ ¥{price:.2f}")
            return True
            
        except Exception as e:
            logger.error(f"买入 {symbol} 失败: {e}")
            return False
    
    def sell_stock(self, symbol: str, shares: int, price: float) -> bool:
        """卖出股票"""
        try:
            if symbol not in self.positions:
                logger.warning(f"无持仓，无法卖出 {symbol}")
                return False
            
            position = self.positions[symbol]
            if shares > position.shares:
                shares = position.shares
            
            gross_income = shares * price
            commission = gross_income * 0.0003
            stamp_tax = gross_income * 0.001
            net_income = gross_income - commission - stamp_tax
            
            remaining_shares = position.shares - shares
            if remaining_shares > 0:
                self.positions[symbol] = Position(
                    symbol=symbol,
                    shares=remaining_shares,
                    avg_cost=position.avg_cost,
                    current_price=price,
                    market_value=remaining_shares * price,
                    unrealized_pnl=(price - position.avg_cost) * remaining_shares,
                    unrealized_pnl_pct=(price - position.avg_cost) / position.avg_cost,
                    entry_date=position.entry_date,
                    last_update=datetime.now()
                )
            else:
                del self.positions[symbol]
            
            self.cash += net_income
            logger.info(f"卖出成功: {symbol} {shares}股 @ ¥{price:.2f}")
            return True
            
        except Exception as e:
            logger.error(f"卖出 {symbol} 失败: {e}")
            return False
    
    def get_position_summary(self, current_prices: Dict[str, float] = None) -> pd.DataFrame:
        """获取持仓汇总"""
        try:
            if not self.positions:
                return pd.DataFrame()
            
            if current_prices:
                self.update_positions(current_prices)
            
            data = []
            for position in self.positions.values():
                data.append({
                    'symbol': position.symbol,
                    'shares': position.shares,
                    'avg_price': position.avg_cost,
                    'current_price': position.current_price,
                    'market_value': position.market_value,
                    'unrealized_pnl': position.unrealized_pnl,
                    'unrealized_pnl_pct': position.unrealized_pnl_pct,
                    'entry_date': position.entry_date.strftime('%Y-%m-%d'),
                    'last_update': position.last_update.strftime('%Y-%m-%d %H:%M:%S')
                })
            
            return pd.DataFrame(data)
            
        except Exception as e:
            logger.error(f"获取持仓汇总失败: {e}")
            return pd.DataFrame()
    
    def update_positions(self, current_prices: Dict[str, float]):
        """更新持仓价格"""
        try:
            for symbol, position in self.positions.items():
                if symbol in current_prices:
                    current_price = current_prices[symbol]
                    market_value = position.shares * current_price
                    unrealized_pnl = (current_price - position.avg_cost) * position.shares
                    unrealized_pnl_pct = (current_price - position.avg_cost) / position.avg_cost
                    
                    self.positions[symbol] = Position(
                        symbol=symbol,
                        shares=position.shares,
                        avg_cost=position.avg_cost,
                        current_price=current_price,
                        market_value=market_value,
                        unrealized_pnl=unrealized_pnl,
                        unrealized_pnl_pct=unrealized_pnl_pct,
                        entry_date=position.entry_date,
                        last_update=datetime.now()
                    )
        except Exception as e:
            logger.error(f"更新持仓价格失败: {e}")
    
    def check_risk_control(self, current_prices: Dict[str, float]) -> List[Tuple[str, str, int]]:
        """检查风险控制"""
        risk_actions = []
        
        try:
            for symbol, position in self.positions.items():
                if symbol in current_prices:
                    current_price = current_prices[symbol]
                    pnl_pct = (current_price - position.avg_cost) / position.avg_cost
                    
                    if pnl_pct <= -self.stop_loss_pct:
                        risk_actions.append((symbol, 'sell', position.shares))
                        logger.warning(f"触发止损: {symbol} 亏损 {pnl_pct:.2%}")
                    
                    elif pnl_pct >= self.take_profit_pct:
                        sell_shares = position.shares // 2
                        if sell_shares > 0:
                            risk_actions.append((symbol, 'sell', sell_shares))
                            logger.info(f"触发止盈: {symbol} 盈利 {pnl_pct:.2%}")
            
            return risk_actions
            
        except Exception as e:
            logger.error(f"风险控制检查失败: {e}")
            return []

    def get_position_summary(self, current_prices=None):
        return pd.DataFrame()
