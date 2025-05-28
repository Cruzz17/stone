#!/usr/bin/env python3
"""
多策略组合
实现多个策略的组合和权重分配
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Any
from loguru import logger

from .base_strategy import BaseStrategy, Signal


class MultiStrategy(BaseStrategy):
    """多策略组合"""
    
    def __init__(self, strategies: Dict[BaseStrategy, float], config: dict = None):
        """
        初始化多策略组合
        
        Args:
            strategies: 策略字典 {策略实例: 权重}
            config: 策略配置
                - signal_threshold: 信号阈值 (默认0.6)
                - max_positions: 最大持仓数 (默认10)
                - rebalance_frequency: 再平衡频率天数 (默认5)
        """
        default_config = {
            'signal_threshold': 0.6,  # 信号强度阈值
            'max_positions': 10,      # 最大持仓数
            'rebalance_frequency': 5  # 再平衡频率
        }
        
        if config:
            default_config.update(config)
        
        super().__init__("多策略组合", default_config)
        
        # 验证权重总和
        total_weight = sum(strategies.values())
        if abs(total_weight - 1.0) > 0.01:
            logger.warning(f"策略权重总和为{total_weight:.2f}，将自动归一化")
            # 归一化权重
            self.strategies = {strategy: weight/total_weight for strategy, weight in strategies.items()}
        else:
            self.strategies = strategies
        
        logger.info(f"多策略组合初始化，包含{len(self.strategies)}个策略")
        for strategy, weight in self.strategies.items():
            logger.info(f"  {strategy.name}: {weight:.2%}")
    
    def generate_signals(self, data: pd.DataFrame, symbol: str) -> List[Signal]:
        """
        生成多策略组合信号
        
        Args:
            data: 股票数据
            symbol: 股票代码
            
        Returns:
            信号列表
        """
        try:
            # 收集所有策略的信号
            all_strategy_signals = {}
            
            for strategy, weight in self.strategies.items():
                try:
                    signals = strategy.generate_signals(data.copy(), symbol)
                    all_strategy_signals[strategy.name] = {
                        'signals': signals,
                        'weight': weight
                    }
                    logger.debug(f"{symbol}: {strategy.name}生成{len(signals)}个信号")
                except Exception as e:
                    logger.error(f"{symbol}: {strategy.name}信号生成失败: {e}")
                    continue
            
            # 合成最终信号
            combined_signals = self._combine_signals(all_strategy_signals, data, symbol)
            
            logger.info(f"{symbol}: 多策略组合生成{len(combined_signals)}个信号")
            return combined_signals
            
        except Exception as e:
            logger.error(f"{symbol}: 多策略组合信号生成失败: {e}")
            return []
    
    def _combine_signals(self, strategy_signals: Dict[str, Dict], 
                        data: pd.DataFrame, symbol: str) -> List[Signal]:
        """
        合成策略信号
        
        Args:
            strategy_signals: 各策略信号字典
            data: 股票数据
            symbol: 股票代码
            
        Returns:
            合成信号列表
        """
        combined_signals = []
        
        # 创建时间序列信号强度表
        signal_strength = {}
        
        # 遍历所有策略信号
        for strategy_name, strategy_data in strategy_signals.items():
            signals = strategy_data['signals']
            weight = strategy_data['weight']
            
            for signal in signals:
                timestamp = signal.timestamp
                
                if timestamp not in signal_strength:
                    signal_strength[timestamp] = {
                        'buy_strength': 0,
                        'sell_strength': 0,
                        'price': signal.price,
                        'reasons': []
                    }
                
                # 累加信号强度
                if signal.signal_type.upper() == 'BUY':
                    signal_strength[timestamp]['buy_strength'] += weight
                    signal_strength[timestamp]['reasons'].append(f"{strategy_name}买入({weight:.1%})")
                elif signal.signal_type.upper() == 'SELL':
                    signal_strength[timestamp]['sell_strength'] += weight
                    signal_strength[timestamp]['reasons'].append(f"{strategy_name}卖出({weight:.1%})")
        
        # 生成合成信号
        for timestamp, strength_data in signal_strength.items():
            buy_strength = strength_data['buy_strength']
            sell_strength = strength_data['sell_strength']
            net_strength = buy_strength - sell_strength
            
            # 判断信号类型和强度
            if abs(net_strength) >= self.config['signal_threshold']:
                if net_strength > 0:
                    # 买入信号
                    signal = Signal(
                        symbol=symbol,
                        timestamp=timestamp,
                        signal_type='BUY',
                        price=strength_data['price'],
                        quantity=0,
                        reason=f"多策略买入(强度:{net_strength:.2f}) - " + "; ".join(strength_data['reasons'])
                    )
                    combined_signals.append(signal)
                else:
                    # 卖出信号
                    signal = Signal(
                        symbol=symbol,
                        timestamp=timestamp,
                        signal_type='SELL',
                        price=strength_data['price'],
                        quantity=0,
                        reason=f"多策略卖出(强度:{abs(net_strength):.2f}) - " + "; ".join(strength_data['reasons'])
                    )
                    combined_signals.append(signal)
        
        # 按时间排序
        combined_signals.sort(key=lambda x: x.timestamp)
        
        # 信号过滤和优化
        filtered_signals = self._filter_signals(combined_signals, data)
        
        return filtered_signals
    
    def _filter_signals(self, signals: List[Signal], data: pd.DataFrame) -> List[Signal]:
        """
        过滤和优化信号
        
        Args:
            signals: 原始信号列表
            data: 股票数据
            
        Returns:
            过滤后的信号列表
        """
        if not signals:
            return signals
        
        filtered_signals = []
        last_signal_type = None
        last_signal_time = None
        
        for signal in signals:
            # 避免连续相同类型信号
            if (last_signal_type == signal.signal_type and 
                last_signal_time and 
                (signal.timestamp - last_signal_time).days < self.config['rebalance_frequency']):
                continue
            
            # 添加技术确认
            if self._technical_confirmation(signal, data):
                filtered_signals.append(signal)
                last_signal_type = signal.signal_type
                last_signal_time = signal.timestamp
        
        return filtered_signals
    
    def _technical_confirmation(self, signal: Signal, data: pd.DataFrame) -> bool:
        """
        技术确认信号有效性
        
        Args:
            signal: 交易信号
            data: 股票数据
            
        Returns:
            是否确认信号
        """
        try:
            # 找到信号对应的数据行
            signal_date = signal.timestamp.date()
            data_dates = [d.date() for d in data.index]
            
            if signal_date not in data_dates:
                return True  # 如果找不到对应日期，默认确认
            
            signal_idx = data_dates.index(signal_date)
            
            if signal_idx < 5:  # 数据不足
                return True
            
            current_data = data.iloc[signal_idx]
            
            # 基本技术确认
            if signal.signal_type.upper() == 'BUY':
                # 买入确认：价格不在近期高点，有上涨空间
                recent_high = data.iloc[signal_idx-5:signal_idx+1]['high'].max()
                if current_data['close'] > recent_high * 0.95:  # 接近近期高点
                    return False
                
                # 成交量确认（如果有成交量数据）
                if 'volume' in data.columns:
                    avg_volume = data.iloc[signal_idx-5:signal_idx]['volume'].mean()
                    if current_data['volume'] < avg_volume * 0.8:  # 成交量不足
                        return False
            
            elif signal.signal_type.upper() == 'SELL':
                # 卖出确认：价格不在近期低点
                recent_low = data.iloc[signal_idx-5:signal_idx+1]['low'].min()
                if current_data['close'] < recent_low * 1.05:  # 接近近期低点
                    return False
            
            return True
            
        except Exception as e:
            logger.debug(f"技术确认失败: {e}")
            return True  # 默认确认
    
    def get_strategy_description(self) -> str:
        """获取策略描述"""
        strategy_names = [strategy.name for strategy in self.strategies.keys()]
        return f"多策略组合 - 包含策略: {', '.join(strategy_names)}, 信号阈值: {self.config['signal_threshold']}"
    
    def get_strategy_performance(self) -> Dict[str, Any]:
        """
        获取各策略表现统计
        
        Returns:
            策略表现字典
        """
        performance = {}
        
        for strategy, weight in self.strategies.items():
            performance[strategy.name] = {
                'weight': weight,
                'config': strategy.config,
                'description': f"{strategy.name} (权重: {weight:.1%})"
            }
        
        return performance
    
    def update_weights(self, new_weights: Dict[str, float]):
        """
        更新策略权重
        
        Args:
            new_weights: 新权重字典 {策略名称: 权重}
        """
        # 根据策略名称更新权重
        updated_strategies = {}
        
        for strategy, old_weight in self.strategies.items():
            strategy_name = strategy.name
            if strategy_name in new_weights:
                updated_strategies[strategy] = new_weights[strategy_name]
                logger.info(f"更新{strategy_name}权重: {old_weight:.2%} -> {new_weights[strategy_name]:.2%}")
            else:
                updated_strategies[strategy] = old_weight
        
        # 归一化权重
        total_weight = sum(updated_strategies.values())
        if total_weight > 0:
            self.strategies = {strategy: weight/total_weight 
                             for strategy, weight in updated_strategies.items()}
        
        logger.info("策略权重更新完成")
        for strategy, weight in self.strategies.items():
            logger.info(f"  {strategy.name}: {weight:.2%}") 