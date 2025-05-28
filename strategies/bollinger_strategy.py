#!/usr/bin/env python3
"""
布林带策略
基于布林带指标的交易策略
"""

import pandas as pd
import numpy as np
from typing import List
from loguru import logger

from .base_strategy import BaseStrategy, Signal


class BollingerStrategy(BaseStrategy):
    """布林带策略"""
    
    def __init__(self, config: dict = None):
        """
        初始化布林带策略
        
        Args:
            config: 策略配置
                - period: 布林带周期 (默认20)
                - std_dev: 标准差倍数 (默认2)
                - oversold_threshold: 超卖阈值 (默认0.1)
                - overbought_threshold: 超买阈值 (默认0.9)
        """
        default_config = {
            'period': 20,
            'std_dev': 2.0,
            'oversold_threshold': 0.1,
            'overbought_threshold': 0.9
        }
        
        if config:
            default_config.update(config)
        
        super().__init__("布林带策略", default_config)
    
    def generate_signals(self, data: pd.DataFrame, symbol: str) -> List[Signal]:
        """
        生成布林带交易信号
        
        Args:
            data: 股票数据
            symbol: 股票代码
            
        Returns:
            信号列表
        """
        signals = []
        
        if len(data) < self.config['period'] + 10:
            logger.warning(f"{symbol}: 数据不足，无法计算布林带")
            return signals
        
        try:
            # 计算布林带
            data = self._calculate_bollinger_bands(data)
            
            # 计算布林带位置 (0-1之间)
            data['bb_position'] = (data['close'] - data['bb_lower']) / (data['bb_upper'] - data['bb_lower'])
            
            # 生成信号
            for i in range(1, len(data)):
                current_row = data.iloc[i]
                prev_row = data.iloc[i-1]
                
                # 买入信号：价格从下轨反弹
                if (prev_row['bb_position'] <= self.config['oversold_threshold'] and 
                    current_row['bb_position'] > self.config['oversold_threshold'] and
                    current_row['close'] > prev_row['close']):
                    
                    signal = Signal(
                        symbol=symbol,
                        timestamp=current_row.name,
                        signal_type='BUY',
                        price=current_row['close'],
                        quantity=0,  # 由回测引擎决定
                        reason=f"布林带超卖反弹，位置: {current_row['bb_position']:.2f}"
                    )
                    signals.append(signal)
                
                # 卖出信号：价格从上轨回落
                elif (prev_row['bb_position'] >= self.config['overbought_threshold'] and 
                      current_row['bb_position'] < self.config['overbought_threshold'] and
                      current_row['close'] < prev_row['close']):
                    
                    signal = Signal(
                        symbol=symbol,
                        timestamp=current_row.name,
                        signal_type='SELL',
                        price=current_row['close'],
                        quantity=0,  # 卖出全部持仓
                        reason=f"布林带超买回落，位置: {current_row['bb_position']:.2f}"
                    )
                    signals.append(signal)
            
            logger.info(f"{symbol}: 布林带策略生成{len(signals)}个信号")
            return signals
            
        except Exception as e:
            logger.error(f"{symbol}: 布林带策略信号生成失败: {e}")
            return []
    
    def get_strategy_description(self) -> str:
        """获取策略描述"""
        return f"布林带策略 - 周期:{self.config['period']}, 标准差:{self.config['std_dev']}, 超卖阈值:{self.config['oversold_threshold']}, 超买阈值:{self.config['overbought_threshold']}"
    
    def _calculate_bollinger_bands(self, data: pd.DataFrame) -> pd.DataFrame:
        """计算布林带指标"""
        period = self.config['period']
        std_dev = self.config['std_dev']
        
        # 中轨（移动平均线）
        data['bb_middle'] = data['close'].rolling(window=period).mean()
        
        # 标准差
        data['bb_std'] = data['close'].rolling(window=period).std()
        
        # 上轨和下轨
        data['bb_upper'] = data['bb_middle'] + (data['bb_std'] * std_dev)
        data['bb_lower'] = data['bb_middle'] - (data['bb_std'] * std_dev)
        
        return data 