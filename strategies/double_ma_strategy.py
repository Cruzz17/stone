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
        super().__init__("double_ma", config)
        
        # 策略参数
        self.short_window = config.get('short_window', 5)
        self.long_window = config.get('long_window', 20)
        
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
        
        # 验证数据
        if not self.validate_data(data):
            return signals
        
        # 数据长度检查
        if len(data) < self.long_window:
            logger.warning(f"数据长度不足，需要至少{self.long_window}条记录")
            return signals
        
        # 计算移动平均线
        data = data.copy()
        data[f'ma_{self.short_window}'] = data['close'].rolling(window=self.short_window).mean()
        data[f'ma_{self.long_window}'] = data['close'].rolling(window=self.long_window).mean()
        
        # 计算金叉死叉信号
        data['ma_diff'] = data[f'ma_{self.short_window}'] - data[f'ma_{self.long_window}']
        data['ma_diff_prev'] = data['ma_diff'].shift(1)
        
        # 去除NaN值
        data = data.dropna()
        
        if data.empty:
            return signals
        
        # 获取当前持仓
        current_position = self.get_current_position(symbol)
        
        # 遍历数据生成信号
        for i, (date, row) in enumerate(data.iterrows()):
            current_price = row['close']
            ma_diff = row['ma_diff']
            ma_diff_prev = row['ma_diff_prev']
            
            # 金叉信号（短期均线上穿长期均线）
            if ma_diff > 0 and ma_diff_prev <= 0:
                # 买入信号
                if current_position['quantity'] == 0:  # 当前无持仓
                    quantity = self.calculate_position_size(
                        symbol, current_price, 100000  # 假设可用资金10万
                    )
                    
                    signal = Signal(
                        symbol=symbol,
                        signal_type='buy',
                        price=current_price,
                        quantity=quantity,
                        timestamp=date,
                        confidence=self._calculate_signal_confidence(row),
                        reason=f"金叉买入: MA{self.short_window}({row[f'ma_{self.short_window}']:.2f}) > MA{self.long_window}({row[f'ma_{self.long_window}']:.2f})"
                    )
                    signals.append(signal)
                    
                    # 更新持仓
                    self.update_position(symbol, signal)
                    current_position = self.get_current_position(symbol)
            
            # 死叉信号（短期均线下穿长期均线）
            elif ma_diff < 0 and ma_diff_prev >= 0:
                # 卖出信号
                if current_position['quantity'] > 0:  # 当前有持仓
                    signal = Signal(
                        symbol=symbol,
                        signal_type='sell',
                        price=current_price,
                        quantity=current_position['quantity'],  # 全部卖出
                        timestamp=date,
                        confidence=self._calculate_signal_confidence(row),
                        reason=f"死叉卖出: MA{self.short_window}({row[f'ma_{self.short_window}']:.2f}) < MA{self.long_window}({row[f'ma_{self.long_window}']:.2f})"
                    )
                    signals.append(signal)
                    
                    # 更新持仓
                    self.update_position(symbol, signal)
                    current_position = self.get_current_position(symbol)
        
        logger.info(f"双均线策略为{symbol}生成了{len(signals)}个信号")
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