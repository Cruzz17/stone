#!/usr/bin/env python3
"""
MACD策略
"""

import pandas as pd
import numpy as np
from typing import List
from loguru import logger

from .base_strategy import BaseStrategy, Signal


class MACDStrategy(BaseStrategy):
    """MACD策略"""

    def __init__(self, config: dict):
        """
        初始化MACD策略

        Args:
            config: 策略配置字典
        """
        super().__init__("MACD策略", config)
        
        # 从配置中获取参数
        self.fast_period = config.get('fast', 12)
        self.slow_period = config.get('slow', 26)
        self.signal_period = config.get('signal', 9)

        logger.info(f"MACD策略初始化: 快速={self.fast_period}, 慢速={self.slow_period}, 信号={self.signal_period}")

    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        计算MACD指标

        Args:
            data: 股票数据

        Returns:
            包含MACD指标的数据
        """
        try:
            df = data.copy()

            # 计算EMA
            ema_fast = df['close'].ewm(span=self.fast_period).mean()
            ema_slow = df['close'].ewm(span=self.slow_period).mean()

            # 计算MACD线
            df['macd'] = ema_fast - ema_slow

            # 计算信号线
            df['signal'] = df['macd'].ewm(span=self.signal_period).mean()

            # 计算柱状图
            df['histogram'] = df['macd'] - df['signal']

            return df

        except Exception as e:
            logger.error(f"计算MACD指标失败: {e}")
            return data

    def generate_signals(self, data: pd.DataFrame, symbol: str) -> List[Signal]:
        """
        生成交易信号

        Args:
            data: 股票数据
            symbol: 股票代码

        Returns:
            信号列表
        """
        signals = []

        try:
            if len(data) < max(self.slow_period, self.signal_period) + 10:
                return signals

            # 计算MACD指标
            df = self.calculate_indicators(data)

            # 生成信号
            for i in range(1, len(df)):
                current_macd = df.iloc[i]['macd']
                current_signal = df.iloc[i]['signal']
                current_hist = df.iloc[i]['histogram']

                prev_macd = df.iloc[i - 1]['macd']
                prev_signal = df.iloc[i - 1]['signal']
                prev_hist = df.iloc[i - 1]['histogram']

                signal_type = 'HOLD'
                strength = 0.0
                reason = ""

                # MACD金叉 - 买入信号
                if (prev_macd <= prev_signal and current_macd > current_signal and
                        current_macd < 0):  # 在零轴下方的金叉更可靠
                    signal_type = 'BUY'
                    strength = min(abs(current_macd - current_signal) / abs(current_macd) * 2, 1.0)
                    reason = "MACD金叉买入信号"

                # MACD死叉 - 卖出信号
                elif (prev_macd >= prev_signal and current_macd < current_signal and
                      current_macd > 0):  # 在零轴上方的死叉更可靠
                    signal_type = 'SELL'
                    strength = min(abs(current_macd - current_signal) / abs(current_macd) * 2, 1.0)
                    reason = "MACD死叉卖出信号"

                # 柱状图背离信号
                elif i >= 5:  # 需要足够的历史数据判断背离
                    # 价格创新高但MACD柱状图未创新高 - 顶背离
                    recent_prices = df.iloc[i - 4:i + 1]['close']
                    recent_hist = df.iloc[i - 4:i + 1]['histogram']

                    if (recent_prices.iloc[-1] == recent_prices.max() and
                            recent_hist.iloc[-1] < recent_hist.max() and
                            current_hist < 0):
                        signal_type = 'SELL'
                        strength = 0.6
                        reason = "MACD顶背离卖出信号"

                    # 价格创新低但MACD柱状图未创新低 - 底背离
                    elif (recent_prices.iloc[-1] == recent_prices.min() and
                          recent_hist.iloc[-1] > recent_hist.min() and
                          current_hist > 0):
                        signal_type = 'BUY'
                        strength = 0.6
                        reason = "MACD底背离买入信号"

                # 零轴穿越信号
                if signal_type == 'HOLD':
                    # MACD上穿零轴
                    if prev_macd <= 0 and current_macd > 0:
                        signal_type = 'BUY'
                        strength = 0.5
                        reason = "MACD上穿零轴买入信号"

                    # MACD下穿零轴
                    elif prev_macd >= 0 and current_macd < 0:
                        signal_type = 'SELL'
                        strength = 0.5
                        reason = "MACD下穿零轴卖出信号"

                if signal_type != 'HOLD' and strength > 0:
                    signal = Signal(
                        symbol=symbol,
                        signal_type=signal_type,
                        price=df.iloc[i]['close'],
                        quantity=100,  # 默认数量
                        timestamp=df.index[i] if hasattr(df.index[i], 'to_pydatetime') else pd.Timestamp.now(),
                        confidence=strength,
                        reason=reason
                    )
                    signals.append(signal)

            if signals:
                logger.info(f"MACD策略生成 {len(signals)} 个信号")

            return signals

        except Exception as e:
            logger.error(f"MACD策略生成信号失败: {e}")
            return []

    def optimize_parameters(self, data: pd.DataFrame,
                            fast_range: tuple = (8, 16),
                            slow_range: tuple = (20, 30),
                            signal_range: tuple = (6, 12)) -> dict:
        """
        参数优化

        Args:
            data: 历史数据
            fast_range: 快速周期范围
            slow_range: 慢速周期范围
            signal_range: 信号周期范围

        Returns:
            最优参数
        """
        try:
            best_params = {
                'fast_period': self.fast_period,
                'slow_period': self.slow_period,
                'signal_period': self.signal_period
            }
            best_score = 0

            for fast in range(fast_range[0], fast_range[1] + 1):
                for slow in range(slow_range[0], slow_range[1] + 1):
                    for signal in range(signal_range[0], signal_range[1] + 1):
                        if fast >= slow:  # 快速周期必须小于慢速周期
                            continue

                        # 临时设置参数
                        old_fast, old_slow, old_signal = self.fast_period, self.slow_period, self.signal_period
                        self.fast_period, self.slow_period, self.signal_period = fast, slow, signal

                        # 生成信号并评估
                        signals = self.generate_signals(data)
                        score = self._evaluate_signals(data, signals)

                        if score > best_score:
                            best_score = score
                            best_params = {
                                'fast_period': fast,
                                'slow_period': slow,
                                'signal_period': signal
                            }

                        # 恢复原参数
                        self.fast_period, self.slow_period, self.signal_period = old_fast, old_slow, old_signal

            logger.info(f"MACD策略最优参数: {best_params}, 得分: {best_score:.4f}")
            return best_params

        except Exception as e:
            logger.error(f"MACD策略参数优化失败: {e}")
            return {
                'fast_period': self.fast_period,
                'slow_period': self.slow_period,
                'signal_period': self.signal_period
            }

    def _evaluate_signals(self, data: pd.DataFrame, signals: List[Signal]) -> float:
        """
        评估信号质量

        Args:
            data: 历史数据
            signals: 信号列表

        Returns:
            评估得分
        """
        try:
            if not signals:
                return 0

            # 简单的信号评估：计算信号后的收益率
            total_return = 0
            signal_count = 0

            for signal in signals:
                # 找到信号对应的数据点
                signal_idx = None
                for i, row in data.iterrows():
                    if abs(row['close'] - signal.price) < 0.01:
                        signal_idx = i
                        break

                if signal_idx is not None and signal_idx < len(data) - 5:
                    # 计算信号后5天的收益率
                    entry_price = data.iloc[signal_idx]['close']
                    exit_price = data.iloc[min(signal_idx + 5, len(data) - 1)]['close']

                    if signal.signal_type == 'BUY':
                        return_rate = (exit_price - entry_price) / entry_price
                    else:  # SELL
                        return_rate = (entry_price - exit_price) / entry_price

                    total_return += return_rate * signal.strength
                    signal_count += 1

            return total_return / signal_count if signal_count > 0 else 0

        except Exception as e:
            logger.error(f"评估MACD信号失败: {e}")
            return 0

    def get_strategy_info(self) -> dict:
        """获取策略信息"""
        return {
            'name': self.name,
            'type': 'MACD',
            'parameters': {
                'fast_period': self.fast_period,
                'slow_period': self.slow_period,
                'signal_period': self.signal_period
            },
            'description': 'MACD指标策略，基于快慢EMA差值和信号线交叉生成交易信号'
        }

    def get_strategy_description(self) -> str:
        """
        获取策略描述
        
        Returns:
            策略描述字符串
        """
        return f"""
        MACD策略 (Moving Average Convergence Divergence Strategy)
        
        策略原理:
        - 计算快速EMA({self.fast_period})和慢速EMA({self.slow_period})的差值(MACD线)
        - 计算MACD线的{self.signal_period}期EMA作为信号线
        - 当MACD线上穿信号线时产生买入信号(金叉)
        - 当MACD线下穿信号线时产生卖出信号(死叉)
        - 识别价格与MACD的背离信号
        - 监控MACD零轴穿越信号
        
        参数设置:
        - 快速EMA周期: {self.fast_period}天
        - 慢速EMA周期: {self.slow_period}天  
        - 信号线周期: {self.signal_period}天
        
        信号类型:
        - 金叉/死叉信号(在零轴下方/上方更可靠)
        - 顶背离/底背离信号
        - 零轴穿越信号
        
        适用场景:
        - 趋势确认和转折点识别
        - 中短期交易
        - 与其他指标组合使用效果更佳
        
        风险提示:
        - 在震荡市场中可能产生较多假信号
        - 信号具有一定滞后性
        - 需要结合成交量和其他指标确认
        """