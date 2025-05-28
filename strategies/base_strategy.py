"""
策略基类
定义所有量化策略的通用接口和方法
"""

from abc import ABC, abstractmethod
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from loguru import logger


class Signal:
    """交易信号类"""
    
    def __init__(self, 
                 symbol: str,
                 signal_type: str,  # 'buy', 'sell', 'hold'
                 price: float,
                 quantity: int,
                 timestamp: datetime,
                 confidence: float = 1.0,
                 reason: str = ""):
        """
        初始化交易信号
        
        Args:
            symbol: 股票代码
            signal_type: 信号类型
            price: 价格
            quantity: 数量
            timestamp: 时间戳
            confidence: 信号置信度 (0-1)
            reason: 信号原因
        """
        self.symbol = symbol
        self.signal_type = signal_type
        self.price = price
        self.quantity = quantity
        self.timestamp = timestamp
        self.confidence = confidence
        self.reason = reason
    
    def __repr__(self):
        return f"Signal({self.signal_type} {self.symbol} {self.quantity}@{self.price})"


class BaseStrategy(ABC):
    """策略基类"""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        """
        初始化策略
        
        Args:
            name: 策略名称
            config: 策略配置
        """
        self.name = name
        self.config = config
        self.positions = {}  # 持仓信息
        self.signals = []    # 信号历史
        self.performance_metrics = {}  # 绩效指标
        
    @abstractmethod
    def generate_signals(self, data: pd.DataFrame, symbol: str) -> List[Signal]:
        """
        生成交易信号
        
        Args:
            data: 股票数据
            symbol: 股票代码
            
        Returns:
            交易信号列表
        """
        pass
    
    @abstractmethod
    def get_strategy_description(self) -> str:
        """
        获取策略描述
        
        Returns:
            策略描述字符串
        """
        pass
    
    def validate_data(self, data: pd.DataFrame) -> bool:
        """
        验证数据有效性
        
        Args:
            data: 股票数据
            
        Returns:
            数据是否有效
        """
        if data.empty:
            logger.warning(f"策略{self.name}: 数据为空")
            return False
        
        required_columns = ['open', 'high', 'low', 'close', 'volume']
        missing_columns = [col for col in required_columns if col not in data.columns]
        
        if missing_columns:
            logger.warning(f"策略{self.name}: 缺少必要列 {missing_columns}")
            return False
        
        # 检查数据质量
        if data[required_columns].isnull().any().any():
            logger.warning(f"策略{self.name}: 数据包含空值")
            return False
        
        return True
    
    def calculate_position_size(self, 
                              symbol: str, 
                              price: float, 
                              available_capital: float,
                              risk_level: float = 0.02) -> int:
        """
        计算仓位大小
        
        Args:
            symbol: 股票代码
            price: 当前价格
            available_capital: 可用资金
            risk_level: 风险水平
            
        Returns:
            建议仓位大小
        """
        # 基于风险水平计算仓位
        max_risk_amount = available_capital * risk_level
        
        # 基于价格计算最大可买数量
        max_quantity = int(available_capital * 0.2 / price)  # 最多使用20%资金
        
        # 确保是100的整数倍（A股最小交易单位）
        quantity = (max_quantity // 100) * 100
        
        return max(100, quantity)  # 至少买100股
    
    def update_position(self, symbol: str, signal: Signal):
        """
        更新持仓信息
        
        Args:
            symbol: 股票代码
            signal: 交易信号
        """
        if symbol not in self.positions:
            self.positions[symbol] = {
                'quantity': 0,
                'avg_price': 0,
                'total_cost': 0,
                'last_update': signal.timestamp
            }
        
        position = self.positions[symbol]
        
        if signal.signal_type == 'buy':
            # 买入
            new_quantity = position['quantity'] + signal.quantity
            new_cost = position['total_cost'] + signal.price * signal.quantity
            position['quantity'] = new_quantity
            position['total_cost'] = new_cost
            position['avg_price'] = new_cost / new_quantity if new_quantity > 0 else 0
            
        elif signal.signal_type == 'sell':
            # 卖出
            sell_quantity = min(signal.quantity, position['quantity'])
            if sell_quantity > 0:
                position['quantity'] -= sell_quantity
                # 按比例减少总成本
                if position['quantity'] > 0:
                    position['total_cost'] *= (position['quantity'] / (position['quantity'] + sell_quantity))
                else:
                    position['total_cost'] = 0
                    position['avg_price'] = 0
        
        position['last_update'] = signal.timestamp
    
    def get_current_position(self, symbol: str) -> Dict:
        """
        获取当前持仓
        
        Args:
            symbol: 股票代码
            
        Returns:
            持仓信息
        """
        return self.positions.get(symbol, {
            'quantity': 0,
            'avg_price': 0,
            'total_cost': 0,
            'last_update': None
        })
    
    def calculate_unrealized_pnl(self, symbol: str, current_price: float) -> float:
        """
        计算未实现盈亏
        
        Args:
            symbol: 股票代码
            current_price: 当前价格
            
        Returns:
            未实现盈亏
        """
        position = self.get_current_position(symbol)
        if position['quantity'] == 0:
            return 0.0
        
        current_value = position['quantity'] * current_price
        unrealized_pnl = current_value - position['total_cost']
        
        return unrealized_pnl
    
    def get_performance_summary(self) -> Dict:
        """
        获取策略绩效摘要
        
        Returns:
            绩效摘要
        """
        return {
            'strategy_name': self.name,
            'total_signals': len(self.signals),
            'buy_signals': len([s for s in self.signals if s.signal_type == 'buy']),
            'sell_signals': len([s for s in self.signals if s.signal_type == 'sell']),
            'active_positions': len([p for p in self.positions.values() if p['quantity'] > 0]),
            'performance_metrics': self.performance_metrics
        }
    
    def reset(self):
        """重置策略状态"""
        self.positions = {}
        self.signals = []
        self.performance_metrics = {}
        logger.info(f"策略{self.name}状态已重置")
    
    def save_signals_to_file(self, filepath: str):
        """
        保存信号到文件
        
        Args:
            filepath: 文件路径
        """
        try:
            signals_data = []
            for signal in self.signals:
                signals_data.append({
                    'timestamp': signal.timestamp,
                    'symbol': signal.symbol,
                    'signal_type': signal.signal_type,
                    'price': signal.price,
                    'quantity': signal.quantity,
                    'confidence': signal.confidence,
                    'reason': signal.reason
                })
            
            df = pd.DataFrame(signals_data)
            df.to_csv(filepath, index=False)
            logger.info(f"策略{self.name}信号已保存到 {filepath}")
            
        except Exception as e:
            logger.error(f"保存信号失败: {e}")
    
    def load_signals_from_file(self, filepath: str):
        """
        从文件加载信号
        
        Args:
            filepath: 文件路径
        """
        try:
            df = pd.read_csv(filepath)
            self.signals = []
            
            for _, row in df.iterrows():
                signal = Signal(
                    symbol=row['symbol'],
                    signal_type=row['signal_type'],
                    price=row['price'],
                    quantity=row['quantity'],
                    timestamp=pd.to_datetime(row['timestamp']),
                    confidence=row.get('confidence', 1.0),
                    reason=row.get('reason', '')
                )
                self.signals.append(signal)
            
            logger.info(f"策略{self.name}从 {filepath} 加载了 {len(self.signals)} 个信号")
            
        except Exception as e:
            logger.error(f"加载信号失败: {e}")


class StrategyManager:
    """策略管理器"""
    
    def __init__(self):
        """初始化策略管理器"""
        self.strategies = {}
        self.active_strategies = []
    
    def register_strategy(self, strategy: BaseStrategy):
        """
        注册策略
        
        Args:
            strategy: 策略实例
        """
        self.strategies[strategy.name] = strategy
        logger.info(f"策略 {strategy.name} 已注册")
    
    def activate_strategy(self, strategy_name: str):
        """
        激活策略
        
        Args:
            strategy_name: 策略名称
        """
        if strategy_name in self.strategies:
            if strategy_name not in self.active_strategies:
                self.active_strategies.append(strategy_name)
                logger.info(f"策略 {strategy_name} 已激活")
        else:
            logger.error(f"策略 {strategy_name} 未注册")
    
    def deactivate_strategy(self, strategy_name: str):
        """
        停用策略
        
        Args:
            strategy_name: 策略名称
        """
        if strategy_name in self.active_strategies:
            self.active_strategies.remove(strategy_name)
            logger.info(f"策略 {strategy_name} 已停用")
    
    def get_active_strategies(self) -> List[BaseStrategy]:
        """
        获取活跃策略列表
        
        Returns:
            活跃策略列表
        """
        return [self.strategies[name] for name in self.active_strategies 
                if name in self.strategies]
    
    def generate_all_signals(self, data: pd.DataFrame, symbol: str) -> List[Signal]:
        """
        生成所有活跃策略的信号
        
        Args:
            data: 股票数据
            symbol: 股票代码
            
        Returns:
            所有信号列表
        """
        all_signals = []
        
        for strategy in self.get_active_strategies():
            try:
                signals = strategy.generate_signals(data, symbol)
                all_signals.extend(signals)
                strategy.signals.extend(signals)
            except Exception as e:
                logger.error(f"策略 {strategy.name} 生成信号失败: {e}")
        
        return all_signals 