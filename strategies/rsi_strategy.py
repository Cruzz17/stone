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
        super().__init__("rsi", config)
        
        # 策略参数
        self.period = config.get('period', 14)
        self.oversold = config.get('oversold', 30)
        self.overbought = config.get('overbought', 70)
        
        # 验证参数
        if self.oversold >= self.overbought:
            raise ValueError("超卖线必须小于超买线")
        
        if not (0 < self.oversold < 50):
            raise ValueError("超卖线应在0-50之间")
            
        if not (50 < self.overbought < 100):
            raise ValueError("超买线应在50-100之间")
        
        logger.info(f"RSI策略初始化: 周期={self.period}, 超卖={self.oversold}, 超买={self.overbought}")
    
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
        if len(data) < self.period + 1:
            logger.warning(f"数据长度不足，需要至少{self.period + 1}条记录")
            return signals
        
        # 计算RSI
        data = data.copy()
        data['rsi'] = self._calculate_rsi(data['close'], self.period)
        data['rsi_prev'] = data['rsi'].shift(1)
        
        # 去除NaN值
        data = data.dropna()
        
        if data.empty:
            return signals
        
        # 获取当前持仓
        current_position = self.get_current_position(symbol)
        
        # 遍历数据生成信号
        for i, (date, row) in enumerate(data.iterrows()):
            current_price = row['close']
            rsi = row['rsi']
            rsi_prev = row['rsi_prev']
            
            # RSI从超卖区域向上突破
            if rsi > self.oversold and rsi_prev <= self.oversold:
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
                        confidence=self._calculate_signal_confidence(row, 'buy'),
                        reason=f"RSI超卖反弹买入: RSI={rsi:.2f} > {self.oversold}"
                    )
                    signals.append(signal)
                    
                    # 更新持仓
                    self.update_position(symbol, signal)
                    current_position = self.get_current_position(symbol)
            
            # RSI从超买区域向下突破
            elif rsi < self.overbought and rsi_prev >= self.overbought:
                # 卖出信号
                if current_position['quantity'] > 0:  # 当前有持仓
                    signal = Signal(
                        symbol=symbol,
                        signal_type='sell',
                        price=current_price,
                        quantity=current_position['quantity'],  # 全部卖出
                        timestamp=date,
                        confidence=self._calculate_signal_confidence(row, 'sell'),
                        reason=f"RSI超买回调卖出: RSI={rsi:.2f} < {self.overbought}"
                    )
                    signals.append(signal)
                    
                    # 更新持仓
                    self.update_position(symbol, signal)
                    current_position = self.get_current_position(symbol)
            
            # 极端超卖/超买信号（更强的信号）
            elif rsi <= 20 and current_position['quantity'] == 0:
                # 极端超卖买入
                quantity = self.calculate_position_size(
                    symbol, current_price, 100000
                )
                
                signal = Signal(
                    symbol=symbol,
                    signal_type='buy',
                    price=current_price,
                    quantity=quantity,
                    timestamp=date,
                    confidence=min(1.0, self._calculate_signal_confidence(row, 'buy') * 1.2),
                    reason=f"RSI极端超卖买入: RSI={rsi:.2f} <= 20"
                )
                signals.append(signal)
                
                # 更新持仓
                self.update_position(symbol, signal)
                current_position = self.get_current_position(symbol)
                
            elif rsi >= 80 and current_position['quantity'] > 0:
                # 极端超买卖出
                signal = Signal(
                    symbol=symbol,
                    signal_type='sell',
                    price=current_price,
                    quantity=current_position['quantity'],
                    timestamp=date,
                    confidence=min(1.0, self._calculate_signal_confidence(row, 'sell') * 1.2),
                    reason=f"RSI极端超买卖出: RSI={rsi:.2f} >= 80"
                )
                signals.append(signal)
                
                # 更新持仓
                self.update_position(symbol, signal)
                current_position = self.get_current_position(symbol)
        
        logger.info(f"RSI策略为{symbol}生成了{len(signals)}个信号")
        return signals
    
    def _calculate_rsi(self, prices: pd.Series, period: int) -> pd.Series:
        """
        计算RSI指标
        
        Args:
            prices: 价格序列
            period: 计算周期
            
        Returns:
            RSI序列
        """
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def _calculate_signal_confidence(self, row: pd.Series, signal_type: str) -> float:
        """
        计算信号置信度
        
        Args:
            row: 当前行数据
            signal_type: 信号类型
            
        Returns:
            信号置信度 (0-1)
        """
        rsi = row['rsi']
        
        if signal_type == 'buy':
            # 买入信号：RSI越低，置信度越高
            if rsi <= 20:
                confidence = 1.0
            elif rsi <= self.oversold:
                confidence = 0.8
            else:
                confidence = max(0.1, (self.oversold - rsi) / self.oversold + 0.5)
        else:  # sell
            # 卖出信号：RSI越高，置信度越高
            if rsi >= 80:
                confidence = 1.0
            elif rsi >= self.overbought:
                confidence = 0.8
            else:
                confidence = max(0.1, (rsi - self.overbought) / (100 - self.overbought) + 0.5)
        
        # 考虑成交量因素
        if 'volume' in row and 'volume_ma' in row:
            volume_ratio = row['volume'] / row['volume_ma'] if row['volume_ma'] > 0 else 1
            volume_factor = min(1.2, max(0.8, volume_ratio))
            confidence *= volume_factor
        
        return max(0.1, min(1.0, confidence))
    
    def get_strategy_description(self) -> str:
        """
        获取策略描述
        
        Returns:
            策略描述字符串
        """
        return f"""
        RSI策略 (Relative Strength Index Strategy)
        
        策略原理:
        - 计算相对强弱指标RSI({self.period})
        - 当RSI从超卖区域({self.oversold})向上突破时买入
        - 当RSI从超买区域({self.overbought})向下突破时卖出
        - 极端超卖(RSI≤20)和极端超买(RSI≥80)时产生更强信号
        
        参数设置:
        - RSI计算周期: {self.period}天
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
        if len(data) < self.period + 1:
            return {}
        
        # 计算RSI
        data = data.copy()
        data['rsi'] = self._calculate_rsi(data['close'], self.period)
        
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
            'period': self.period,
            'oversold': self.oversold,
            'overbought': self.overbought
        }
        best_return = -float('inf')
        
        # 参数搜索范围
        period_range = range(10, 25)
        oversold_range = range(20, 40, 5)
        overbought_range = range(60, 85, 5)
        
        for period in period_range:
            for oversold in oversold_range:
                for overbought in overbought_range:
                    if oversold >= overbought:
                        continue
                    
                    # 临时修改参数
                    original_period = self.period
                    original_oversold = self.oversold
                    original_overbought = self.overbought
                    
                    self.period = period
                    self.oversold = oversold
                    self.overbought = overbought
                    
                    try:
                        # 生成信号并计算收益
                        signals = self.generate_signals(data, symbol)
                        total_return = self._calculate_strategy_return(data, signals)
                        
                        if total_return > best_return:
                            best_return = total_return
                            best_params = {
                                'period': period,
                                'oversold': oversold,
                                'overbought': overbought
                            }
                    
                    except Exception as e:
                        logger.warning(f"参数优化失败 period={period}, oversold={oversold}, overbought={overbought}: {e}")
                    
                    finally:
                        # 恢复原参数
                        self.period = original_period
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