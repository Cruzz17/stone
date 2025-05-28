#!/usr/bin/env python3
"""
策略管理器
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from dataclasses import dataclass
from loguru import logger

from .base_strategy import BaseStrategy, Signal
from .double_ma_strategy import DoubleMaStrategy
from .rsi_strategy import RSIStrategy
from .macd_strategy import MACDStrategy


@dataclass
class CombinedSignal:
    """组合信号"""
    symbol: str
    signal_type: str  # 'BUY', 'SELL', 'HOLD'
    combined_strength: float  # 组合信号强度 (0-1)
    confidence: float  # 置信度 (0-1)
    individual_signals: List[Signal]  # 各个策略的信号
    strategy_weights: Dict[str, float]  # 策略权重


class StrategyManager:
    """策略管理器"""

    def __init__(self, config: dict):
        """
        初始化策略管理器

        Args:
            config: 配置字典
        """
        self.config = config
        self.strategies = {}

        # 策略权重配置
        strategy_config = config.get('strategies', {})
        self.strategy_weights = {
            'double_ma': strategy_config.get('double_ma', {}).get('weight', 0.4),
            'rsi': strategy_config.get('rsi', {}).get('weight', 0.3),
            'macd': strategy_config.get('macd', {}).get('weight', 0.3)
        }

        # 信号合成配置
        self.signal_combination = config.get('simulation', {}).get('signal_combination', 'weighted_average')
        self.min_confidence = config.get('simulation', {}).get('min_signal_confidence', 0.6)

        # 初始化策略
        self._initialize_strategies()

        logger.info(f"策略管理器初始化完成，策略权重: {self.strategy_weights}")

    def _initialize_strategies(self):
        """初始化所有策略"""
        try:
            # 双均线策略
            if self.strategy_weights.get('double_ma', 0) > 0:
                ma_config = self.config.get('strategies', {}).get('double_ma', {})
                self.strategies['double_ma'] = DoubleMaStrategy(ma_config)
            # RSI策略
            if self.strategy_weights.get('rsi', 0) > 0:
                rsi_config = self.config.get('strategies', {}).get('rsi', {})
                self.strategies['rsi'] = RSIStrategy(rsi_config)


            # MACD策略
            if self.strategy_weights.get('macd', 0) > 0:
                macd_config = self.config.get('strategies', {}).get('macd', {})
                self.strategies['macd'] = MACDStrategy(macd_config)


            logger.info(f"已初始化 {len(self.strategies)} 个策略")

        except Exception as e:
            logger.error(f"初始化策略失败: {e}")

    def generate_combined_signals(self, stock_data: Dict[str, pd.DataFrame]) -> List[CombinedSignal]:
        """
        生成组合信号

        Args:
            stock_data: 股票数据字典 {symbol: DataFrame}

        Returns:
            组合信号列表
        """
        combined_signals = []

        try:
            for symbol, data in stock_data.items():
                if data.empty or len(data) < 30:  # 确保有足够的数据
                    continue

                # 收集各策略信号
                individual_signals = []

                for strategy_name, strategy in self.strategies.items():
                    try:
                        signals = strategy.generate_signals(data)
                        if signals:
                            # 取最新信号
                            latest_signal = signals[-1]
                            latest_signal.strategy_name = strategy_name
                            individual_signals.append(latest_signal)
                    except Exception as e:
                        logger.error(f"策略 {strategy_name} 生成 {symbol} 信号失败: {e}")

                if not individual_signals:
                    continue

                # 合成信号
                combined_signal = self._combine_signals(symbol, individual_signals)

                if combined_signal and combined_signal.confidence >= self.min_confidence:
                    combined_signals.append(combined_signal)

        except Exception as e:
            logger.error(f"生成组合信号失败: {e}")

        return combined_signals

    def _combine_signals(self, symbol: str, signals: List[Signal]) -> Optional[CombinedSignal]:
        """
        合成多个策略信号

        Args:
            symbol: 股票代码
            signals: 策略信号列表

        Returns:
            组合信号
        """
        try:
            if not signals:
                return None

            if self.signal_combination == 'weighted_average':
                return self._weighted_average_combination(symbol, signals)
            elif self.signal_combination == 'majority_vote':
                return self._majority_vote_combination(symbol, signals)
            elif self.signal_combination == 'unanimous':
                return self._unanimous_combination(symbol, signals)
            else:
                return self._weighted_average_combination(symbol, signals)

        except Exception as e:
            logger.error(f"合成 {symbol} 信号失败: {e}")
            return None

    def _weighted_average_combination(self, symbol: str, signals: List[Signal]) -> Optional[CombinedSignal]:
        """加权平均合成"""
        try:
            buy_weight = 0
            sell_weight = 0
            total_weight = 0

            for signal in signals:
                strategy_name = getattr(signal, 'strategy_name', 'unknown')
                weight = self.strategy_weights.get(strategy_name, 0)

                if weight <= 0:
                    continue

                if signal.signal_type == 'BUY':
                    buy_weight += weight * signal.strength
                elif signal.signal_type == 'SELL':
                    sell_weight += weight * signal.strength

                total_weight += weight

            if total_weight == 0:
                return None

            # 计算最终信号
            net_signal = (buy_weight - sell_weight) / total_weight

            if net_signal > 0.1:
                signal_type = 'BUY'
                strength = min(net_signal, 1.0)
            elif net_signal < -0.1:
                signal_type = 'SELL'
                strength = min(abs(net_signal), 1.0)
            else:
                signal_type = 'HOLD'
                strength = 0.0

            # 计算置信度
            confidence = min(abs(net_signal) * 2, 1.0)

            return CombinedSignal(
                symbol=symbol,
                signal_type=signal_type,
                combined_strength=strength,
                confidence=confidence,
                individual_signals=signals,
                strategy_weights=self.strategy_weights
            )

        except Exception as e:
            logger.error(f"加权平均合成 {symbol} 信号失败: {e}")
            return None

    def _majority_vote_combination(self, symbol: str, signals: List[Signal]) -> Optional[CombinedSignal]:
        """多数投票合成"""
        try:
            buy_votes = 0
            sell_votes = 0
            hold_votes = 0

            for signal in signals:
                if signal.signal_type == 'BUY':
                    buy_votes += 1
                elif signal.signal_type == 'SELL':
                    sell_votes += 1
                else:
                    hold_votes += 1

            total_votes = len(signals)

            if buy_votes > sell_votes and buy_votes > hold_votes:
                signal_type = 'BUY'
                strength = buy_votes / total_votes
            elif sell_votes > buy_votes and sell_votes > hold_votes:
                signal_type = 'SELL'
                strength = sell_votes / total_votes
            else:
                signal_type = 'HOLD'
                strength = 0.0

            confidence = max(buy_votes, sell_votes, hold_votes) / total_votes

            return CombinedSignal(
                symbol=symbol,
                signal_type=signal_type,
                combined_strength=strength,
                confidence=confidence,
                individual_signals=signals,
                strategy_weights=self.strategy_weights
            )

        except Exception as e:
            logger.error(f"多数投票合成 {symbol} 信号失败: {e}")
            return None

    def _unanimous_combination(self, symbol: str, signals: List[Signal]) -> Optional[CombinedSignal]:
        """一致性合成"""
        try:
            if not signals:
                return None

            first_signal_type = signals[0].signal_type

            # 检查是否所有信号一致
            for signal in signals:
                if signal.signal_type != first_signal_type:
                    return CombinedSignal(
                        symbol=symbol,
                        signal_type='HOLD',
                        combined_strength=0.0,
                        confidence=0.0,
                        individual_signals=signals,
                        strategy_weights=self.strategy_weights
                    )

            # 所有信号一致
            avg_strength = np.mean([s.strength for s in signals])

            return CombinedSignal(
                symbol=symbol,
                signal_type=first_signal_type,
                combined_strength=avg_strength,
                confidence=1.0,  # 一致性信号置信度最高
                individual_signals=signals,
                strategy_weights=self.strategy_weights
            )

        except Exception as e:
            logger.error(f"一致性合成 {symbol} 信号失败: {e}")
            return None

    def update_strategy_weights(self, new_weights: Dict[str, float]):
        """更新策略权重"""
        try:
            # 归一化权重
            total_weight = sum(new_weights.values())
            if total_weight > 0:
                self.strategy_weights = {k: v / total_weight for k, v in new_weights.items()}
                logger.info(f"策略权重已更新: {self.strategy_weights}")
            else:
                logger.warning("权重总和为0，保持原权重")

        except Exception as e:
            logger.error(f"更新策略权重失败: {e}")

    def get_strategy_performance(self, symbol: str, data: pd.DataFrame) -> Dict[str, Dict]:
        """获取各策略表现"""
        performance = {}

        try:
            for strategy_name, strategy in self.strategies.items():
                try:
                    signals = strategy.generate_signals(data)
                    if signals:
                        # 简单的表现评估
                        buy_signals = [s for s in signals if s.signal_type == 'BUY']
                        sell_signals = [s for s in signals if s.signal_type == 'SELL']

                        performance[strategy_name] = {
                            'total_signals': len(signals),
                            'buy_signals': len(buy_signals),
                            'sell_signals': len(sell_signals),
                            'avg_strength': np.mean([s.strength for s in signals]) if signals else 0,
                            'weight': self.strategy_weights.get(strategy_name, 0)
                        }
                except Exception as e:
                    logger.error(f"评估策略 {strategy_name} 表现失败: {e}")
                    performance[strategy_name] = {
                        'error': str(e),
                        'weight': self.strategy_weights.get(strategy_name, 0)
                    }

        except Exception as e:
            logger.error(f"获取策略表现失败: {e}")

        return performance

    def get_active_strategies(self) -> List[str]:
        """获取活跃策略列表"""
        return list(self.strategies.keys())

    def get_strategy_config(self) -> Dict:
        """获取策略配置"""
        return {
            'weights': self.strategy_weights,
            'combination_method': self.signal_combination,
            'min_confidence': self.min_confidence,
            'active_strategies': self.get_active_strategies()
        }