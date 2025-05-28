#!/usr/bin/env python3
"""
KDJ策略
基于KDJ指标的交易策略
"""

import pandas as pd
import numpy as np
from typing import List
from loguru import logger

from .base_strategy import BaseStrategy, Signal


class KDJStrategy(BaseStrategy):
    """KDJ策略"""
    
    def __init__(self, config: dict = None):
        """
        初始化KDJ策略
        
        Args:
            config: 策略配置
                - k_period: K值计算周期 (默认9)
                - d_period: D值平滑周期 (默认3)
                - j_period: J值平滑周期 (默认3)
                - oversold: 超卖阈值 (默认20)
                - overbought: 超买阈值 (默认80)
        """
        default_config = {
            'k_period': 9,
            'd_period': 3,
            'j_period': 3,
            'oversold': 20,
            'overbought': 80
        }
        
        if config:
            default_config.update(config)
        
        super().__init__("KDJ策略", default_config)
    
    def generate_signals(self, data: pd.DataFrame, symbol: str) -> List[Signal]:
        """
        生成KDJ交易信号
        
        Args:
            data: 股票数据
            symbol: 股票代码
            
        Returns:
            信号列表
        """
        signals = []
        
        if len(data) < self.config['k_period'] + 10:
            logger.warning(f"{symbol}: 数据不足，无法计算KDJ")
            return signals
        
        try:
            # 计算KDJ指标
            data = self._calculate_kdj(data)
            
            # 生成信号
            for i in range(1, len(data)):
                current_row = data.iloc[i]
                prev_row = data.iloc[i-1]
                
                # 检查数据有效性
                if pd.isna(current_row['K']) or pd.isna(current_row['D']) or pd.isna(current_row['J']):
                    continue
                
                # 买入信号：KDJ金叉且在超卖区域
                if (prev_row['K'] <= prev_row['D'] and 
                    current_row['K'] > current_row['D'] and
                    current_row['K'] < self.config['oversold'] + 10):  # 超卖区域附近
                    
                    signal = Signal(
                        symbol=symbol,
                        timestamp=current_row.name,
                        signal_type='BUY',
                        price=current_row['close'],
                        quantity=0,  # 由回测引擎决定
                        reason=f"KDJ金叉买入，K:{current_row['K']:.1f}, D:{current_row['D']:.1f}, J:{current_row['J']:.1f}"
                    )
                    signals.append(signal)
                
                # 卖出信号：KDJ死叉且在超买区域
                elif (prev_row['K'] >= prev_row['D'] and 
                      current_row['K'] < current_row['D'] and
                      current_row['K'] > self.config['overbought'] - 10):  # 超买区域附近
                    
                    signal = Signal(
                        symbol=symbol,
                        timestamp=current_row.name,
                        signal_type='SELL',
                        price=current_row['close'],
                        quantity=0,  # 卖出全部持仓
                        reason=f"KDJ死叉卖出，K:{current_row['K']:.1f}, D:{current_row['D']:.1f}, J:{current_row['J']:.1f}"
                    )
                    signals.append(signal)
                
                # 强势买入信号：J值从超卖区域快速上升
                elif (prev_row['J'] < self.config['oversold'] and 
                      current_row['J'] > self.config['oversold'] and
                      current_row['J'] - prev_row['J'] > 5):  # J值快速上升
                    
                    signal = Signal(
                        symbol=symbol,
                        timestamp=current_row.name,
                        signal_type='BUY',
                        price=current_row['close'],
                        quantity=0,
                        reason=f"J值超卖反弹，J:{current_row['J']:.1f}"
                    )
                    signals.append(signal)
                
                # 强势卖出信号：J值从超买区域快速下降
                elif (prev_row['J'] > self.config['overbought'] and 
                      current_row['J'] < self.config['overbought'] and
                      prev_row['J'] - current_row['J'] > 5):  # J值快速下降
                    
                    signal = Signal(
                        symbol=symbol,
                        timestamp=current_row.name,
                        signal_type='SELL',
                        price=current_row['close'],
                        quantity=0,
                        reason=f"J值超买回落，J:{current_row['J']:.1f}"
                    )
                    signals.append(signal)
            
            logger.info(f"{symbol}: KDJ策略生成{len(signals)}个信号")
            return signals
            
        except Exception as e:
            logger.error(f"{symbol}: KDJ策略信号生成失败: {e}")
            return []
    
    def get_strategy_description(self) -> str:
        """获取策略描述"""
        return f"KDJ策略 - K周期:{self.config['k_period']}, D周期:{self.config['d_period']}, 超卖线:{self.config['oversold']}, 超买线:{self.config['overbought']}"
    
    def _calculate_kdj(self, data: pd.DataFrame) -> pd.DataFrame:
        """计算KDJ指标"""
        k_period = self.config['k_period']
        d_period = self.config['d_period']
        
        # 计算最高价和最低价的滚动窗口
        data['lowest_low'] = data['low'].rolling(window=k_period).min()
        data['highest_high'] = data['high'].rolling(window=k_period).max()
        
        # 计算RSV (Raw Stochastic Value)
        data['rsv'] = ((data['close'] - data['lowest_low']) / 
                       (data['highest_high'] - data['lowest_low']) * 100)
        
        # 计算K值 (使用指数移动平均)
        data['K'] = data['rsv'].ewm(alpha=1/d_period).mean()
        
        # 计算D值 (K值的指数移动平均)
        data['D'] = data['K'].ewm(alpha=1/d_period).mean()
        
        # 计算J值
        data['J'] = 3 * data['K'] - 2 * data['D']
        
        return data 