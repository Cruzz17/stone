"""
双均线策略
当短期均线上穿长期均线时买入，下穿时卖出
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Any
from datetime import datetime
from .base_strategy import BaseStrategy, Signal
from loguru import logger


class DoubleMaStrategy(BaseStrategy):
    """双均线策略"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化双均线策略
        
        Args:
            config: 策略配置
        """
        super().__init__("双均线策略", config)
        
        # 使用更激进的参数
        self.short_window = config.get('short_window', 3)  # 改为3天
        self.long_window = config.get('long_window', 8)    # 改为8天
        
        # 验证参数
        if self.short_window >= self.long_window:
            raise ValueError("短期均线周期必须小于长期均线周期")
        
        logger.info(f"双均线策略初始化: 短期={self.short_window}, 长期={self.long_window}")
    
    def generate_signals(self, data: pd.DataFrame, symbol: str) -> List[Signal]:
        """
        生成交易信号
        
        Args:
            data: 股票数据
            symbol: 股票代码
            
        Returns:
            交易信号列表
        """
        signals = []
        
        if len(data) < self.long_window:
            return signals
            
        # 计算移动平均线
        data['ma_short'] = data['close'].rolling(window=self.short_window).mean()
        data['ma_long'] = data['close'].rolling(window=self.long_window).mean()
        
        # 生成交易信号
        for i in range(self.long_window, len(data)):
            current_short = data['ma_short'].iloc[i]
            current_long = data['ma_long'].iloc[i]
            prev_short = data['ma_short'].iloc[i-1]
            prev_long = data['ma_long'].iloc[i-1]
            
            # 金叉：短期均线上穿长期均线
            if prev_short <= prev_long and current_short > current_long:
                signal = Signal(
                    symbol=symbol,
                    signal_type='BUY',
                    price=data['close'].iloc[i],
                    quantity=1000,  # 固定数量
                    timestamp=data.index[i]
                )
                signals.append(signal)
                
            # 死叉：短期均线下穿长期均线  
            elif prev_short >= prev_long and current_short < current_long:
                signal = Signal(
                    symbol=symbol,
                    signal_type='SELL',
                    price=data['close'].iloc[i],
                    quantity=1000,
                    timestamp=data.index[i]
                )
                signals.append(signal)
                
        return signals
    
    def _calculate_signal_confidence(self, row: pd.Series) -> float:
        """
        计算信号置信度
        
        Args:
            row: 当前行数据
            
        Returns:
            信号置信度 (0-1)
        """
        # 基于均线差值的绝对值计算置信度
        ma_diff_abs = abs(row['ma_diff'])
        ma_short = row[f'ma_{self.short_window}']
        
        # 差值越大，置信度越高
        confidence = min(1.0, ma_diff_abs / (ma_short * 0.02))  # 2%作为基准
        
        # 考虑成交量因素
        if 'volume' in row and 'volume_ma' in row:
            volume_ratio = row['volume'] / row['volume_ma'] if row['volume_ma'] > 0 else 1
            volume_factor = min(1.2, max(0.8, volume_ratio))  # 成交量放大提高置信度
            confidence *= volume_factor
        
        return max(0.1, min(1.0, confidence))
    
    def get_strategy_description(self) -> str:
        """
        获取策略描述
        
        Returns:
            策略描述字符串
        """
        return f"""
        双均线策略 (Double Moving Average Strategy)
        
        策略原理:
        - 计算短期移动平均线 (MA{self.short_window}) 和长期移动平均线 (MA{self.long_window})
        - 当短期均线上穿长期均线时产生买入信号 (金叉)
        - 当短期均线下穿长期均线时产生卖出信号 (死叉)
        
        参数设置:
        - 短期均线周期: {self.short_window}天
        - 长期均线周期: {self.long_window}天
        
        适用场景:
        - 趋势性较强的市场
        - 中长期投资
        
        风险提示:
        - 在震荡市场中可能产生较多假信号
        - 信号具有滞后性
        """
    
    def get_current_indicators(self, data: pd.DataFrame) -> Dict[str, float]:
        """
        获取当前技术指标值
        
        Args:
            data: 股票数据
            
        Returns:
            当前指标值
        """
        if len(data) < self.long_window:
            return {}
        
        # 计算移动平均线
        data = data.copy()
        data[f'ma_{self.short_window}'] = data['close'].rolling(window=self.short_window).mean()
        data[f'ma_{self.long_window}'] = data['close'].rolling(window=self.long_window).mean()
        
        latest = data.iloc[-1]
        
        return {
            'current_price': latest['close'],
            f'ma_{self.short_window}': latest[f'ma_{self.short_window}'],
            f'ma_{self.long_window}': latest[f'ma_{self.long_window}'],
            'ma_diff': latest[f'ma_{self.short_window}'] - latest[f'ma_{self.long_window}'],
            'trend': 'bullish' if latest[f'ma_{self.short_window}'] > latest[f'ma_{self.long_window}'] else 'bearish'
        }
    
    def optimize_parameters(self, data: pd.DataFrame, symbol: str) -> Dict[str, Any]:
        """
        参数优化
        
        Args:
            data: 历史数据
            symbol: 股票代码
            
        Returns:
            优化后的参数
        """
        best_params = {'short_window': self.short_window, 'long_window': self.long_window}
        best_return = -float('inf')
        
        # 参数搜索范围
        short_range = range(3, 15)
        long_range = range(15, 60)
        
        for short in short_range:
            for long in long_range:
                if short >= long:
                    continue
                
                # 临时修改参数
                original_short = self.short_window
                original_long = self.long_window
                
                self.short_window = short
                self.long_window = long
                
                try:
                    # 生成信号并计算收益
                    signals = self.generate_signals(data, symbol)
                    total_return = self._calculate_strategy_return(data, signals)
                    
                    if total_return > best_return:
                        best_return = total_return
                        best_params = {'short_window': short, 'long_window': long}
                
                except Exception as e:
                    logger.warning(f"参数优化失败 short={short}, long={long}: {e}")
                
                finally:
                    # 恢复原参数
                    self.short_window = original_short
                    self.long_window = original_long
        
        logger.info(f"参数优化完成，最佳参数: {best_params}, 收益率: {best_return:.2%}")
        return best_params
    
    def _calculate_strategy_return(self, data: pd.DataFrame, signals: List[Signal]) -> float:
        """
        计算策略收益率
        
        Args:
            data: 历史数据
            signals: 交易信号
            
        Returns:
            总收益率
        """
        if not signals:
            return 0.0
        
        capital = 100000  # 初始资金
        position = 0
        buy_price = 0
        total_return = 0
        
        for signal in signals:
            if signal.signal_type == 'buy' and position == 0:
                position = capital / signal.price
                buy_price = signal.price
                capital = 0
            elif signal.signal_type == 'sell' and position > 0:
                capital = position * signal.price
                trade_return = (signal.price - buy_price) / buy_price
                total_return += trade_return
                position = 0
        
        return total_return 