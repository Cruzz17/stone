"""
RSI策略
基于相对强弱指标(RSI)进行交易
当RSI低于超卖线时买入，高于超买线时卖出
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Any
from datetime import datetime
from .base_strategy import BaseStrategy, Signal
from loguru import logger


class RSIStrategy(BaseStrategy):
    """RSI策略"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化RSI策略
        
        Args:
            config: 策略配置
        """
        super().__init__("RSI策略", config)
        
        # 使用更激进的参数
        self.rsi_period = config.get('rsi_period', 6)      # 改为6天
        self.oversold = config.get('oversold', 40)         # 改为40
        self.overbought = config.get('overbought', 60)     # 改为60
        
        # 验证参数
        if self.oversold >= self.overbought:
            raise ValueError("超卖线必须小于超买线")
        
        if not (0 < self.oversold < 50):
            raise ValueError("超卖线应在0-50之间")
            
        if not (50 < self.overbought < 100):
            raise ValueError("超买线应在50-100之间")
        
        logger.info(f"RSI策略初始化: 周期={self.rsi_period}, 超卖={self.oversold}, 超买={self.overbought}")
    
    def calculate_rsi(self, prices, period):
        """计算RSI指标"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
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
        if len(data) < self.rsi_period + 1:
            logger.warning(f"数据长度不足，需要至少{self.rsi_period + 1}条记录")
            return signals
        
        # 计算RSI
        data['rsi'] = self.calculate_rsi(data['close'], self.rsi_period)
        
        # 生成交易信号
        for i in range(self.rsi_period, len(data)):
            current_rsi = data['rsi'].iloc[i]
            
            # RSI超卖，买入信号
            if current_rsi < self.oversold:
                signal = Signal(
                    symbol=symbol,
                    signal_type='BUY',
                    price=data['close'].iloc[i],
                    quantity=1000,
                    timestamp=data.index[i]
                )
                signals.append(signal)
                
            # RSI超买，卖出信号
            elif current_rsi > self.overbought:
                signal = Signal(
                    symbol=symbol,
                    signal_type='SELL',
                    price=data['close'].iloc[i],
                    quantity=1000,
                    timestamp=data.index[i]
                )
                signals.append(signal)
        
        logger.info(f"RSI策略为{symbol}生成了{len(signals)}个信号")
        return signals
    
    def get_strategy_description(self) -> str:
        """
        获取策略描述
        
        Returns:
            策略描述字符串
        """
        return f"""
        RSI策略 (Relative Strength Index Strategy)
        
        策略原理:
        - 计算相对强弱指标RSI({self.rsi_period})
        - 当RSI从超卖区域({self.oversold})向上突破时买入
        - 当RSI从超买区域({self.overbought})向下突破时卖出
        - 极端超卖(RSI≤20)和极端超买(RSI≥80)时产生更强信号
        
        参数设置:
        - RSI计算周期: {self.rsi_period}天
        - 超卖线: {self.oversold}
        - 超买线: {self.overbought}
        
        适用场景:
        - 震荡市场
        - 短中期交易
        - 超跌反弹和超涨回调
        
        风险提示:
        - 在强趋势市场中可能产生过早的反向信号
        - 需要结合其他指标确认
        """
    
    def get_current_indicators(self, data: pd.DataFrame) -> Dict[str, float]:
        """
        获取当前技术指标值
        
        Args:
            data: 股票数据
            
        Returns:
            当前指标值
        """
        if len(data) < self.rsi_period + 1:
            return {}
        
        # 计算RSI
        data['rsi'] = self.calculate_rsi(data['close'], self.rsi_period)
        
        latest = data.iloc[-1]
        rsi = latest['rsi']
        
        # 判断RSI状态
        if rsi <= 20:
            rsi_status = 'extremely_oversold'
        elif rsi <= self.oversold:
            rsi_status = 'oversold'
        elif rsi >= 80:
            rsi_status = 'extremely_overbought'
        elif rsi >= self.overbought:
            rsi_status = 'overbought'
        else:
            rsi_status = 'neutral'
        
        return {
            'current_price': latest['close'],
            'rsi': rsi,
            'rsi_status': rsi_status,
            'oversold_line': self.oversold,
            'overbought_line': self.overbought,
            'signal_strength': self._get_signal_strength(rsi)
        }
    
    def _get_signal_strength(self, rsi: float) -> str:
        """
        获取信号强度
        
        Args:
            rsi: RSI值
            
        Returns:
            信号强度描述
        """
        if rsi <= 20 or rsi >= 80:
            return 'very_strong'
        elif rsi <= self.oversold or rsi >= self.overbought:
            return 'strong'
        elif 40 <= rsi <= 60:
            return 'neutral'
        else:
            return 'weak'
    
    def optimize_parameters(self, data: pd.DataFrame, symbol: str) -> Dict[str, Any]:
        """
        参数优化
        
        Args:
            data: 历史数据
            symbol: 股票代码
            
        Returns:
            优化后的参数
        """
        best_params = {
            'rsi_period': self.rsi_period,
            'oversold': self.oversold,
            'overbought': self.overbought
        }
        best_return = -float('inf')
        
        # 参数搜索范围
        period_range = range(5, 10)
        oversold_range = range(30, 50, 5)
        overbought_range = range(50, 70, 5)
        
        for period in period_range:
            for oversold in oversold_range:
                for overbought in overbought_range:
                    if oversold >= overbought:
                        continue
                    
                    # 临时修改参数
                    original_period = self.rsi_period
                    original_oversold = self.oversold
                    original_overbought = self.overbought
                    
                    self.rsi_period = period
                    self.oversold = oversold
                    self.overbought = overbought
                    
                    try:
                        # 生成信号并计算收益
                        signals = self.generate_signals(data, symbol)
                        total_return = self._calculate_strategy_return(data, signals)
                        
                        if total_return > best_return:
                            best_return = total_return
                            best_params = {
                                'rsi_period': period,
                                'oversold': oversold,
                                'overbought': overbought
                            }
                    
                    except Exception as e:
                        logger.warning(f"参数优化失败 period={period}, oversold={oversold}, overbought={overbought}: {e}")
                    
                    finally:
                        # 恢复原参数
                        self.rsi_period = original_period
                        self.oversold = original_oversold
                        self.overbought = original_overbought
        
        logger.info(f"RSI参数优化完成，最佳参数: {best_params}, 收益率: {best_return:.2%}")
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
            if signal.signal_type == 'BUY' and position == 0:
                position = capital / signal.price
                buy_price = signal.price
                capital = 0
            elif signal.signal_type == 'SELL' and position > 0:
                capital = position * signal.price
                trade_return = (signal.price - buy_price) / buy_price
                total_return += trade_return
                position = 0
        
        return total_return 