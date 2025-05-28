#!/usr/bin/env python3
"""
实时数据获取模块
从真实数据源获取股票数据
"""

import akshare as ak
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from loguru import logger
import time
import threading
from data.database import DatabaseManager

class RealDataFetcher:
    """实时数据获取器"""
    
    def __init__(self, db_manager: DatabaseManager):
        """
        初始化实时数据获取器
        
        Args:
            db_manager: 数据库管理器
        """
        self.db_manager = db_manager
        self.is_running = False
        self.update_thread = None
        self.stock_pool = []
        self.current_prices = {}
        self.last_update_time = None
        
        logger.info("实时数据获取器初始化完成")
    
    def set_stock_pool(self, symbols: List[str]):
        """设置股票池"""
        self.stock_pool = symbols
        logger.info(f"设置股票池: {symbols}")
    
    def get_stock_basic_data(self, symbol: str, period: str = "daily", count: int = 100) -> pd.DataFrame:
        """
        获取股票基础数据
        
        Args:
            symbol: 股票代码
            period: 数据周期 (daily, weekly, monthly)
            count: 获取数量
            
        Returns:
            股票数据DataFrame
        """
        try:
            # 转换股票代码格式
            if symbol.endswith('.SZ'):
                ak_symbol = symbol.replace('.SZ', '')
            elif symbol.endswith('.SH'):
                ak_symbol = symbol.replace('.SH', '')
            else:
                ak_symbol = symbol
            
            # 获取历史数据
            if period == "daily":
                data = ak.stock_zh_a_hist(symbol=ak_symbol, period="daily", adjust="qfq")
            else:
                data = ak.stock_zh_a_hist(symbol=ak_symbol, period=period, adjust="qfq")
            
            if data is not None and not data.empty:
                # 重命名列
                data.columns = ['date', 'open', 'close', 'high', 'low', 'volume', 'amount', 'amplitude', 'pct_change', 'change', 'turnover']
                
                # 选择需要的列
                data = data[['date', 'open', 'high', 'low', 'close', 'volume', 'amount']]
                
                # 设置索引
                data['date'] = pd.to_datetime(data['date'])
                data.set_index('date', inplace=True)
                
                # 数据类型转换
                for col in ['open', 'high', 'low', 'close', 'volume', 'amount']:
                    data[col] = pd.to_numeric(data[col], errors='coerce')
                
                # 取最近count条数据
                data = data.tail(count)
                
                # 保存到数据库
                self.db_manager.save_stock_data(symbol, data)
                
                logger.info(f"获取 {symbol} 数据成功: {len(data)} 条")
                return data
            else:
                logger.warning(f"获取 {symbol} 数据为空")
                return pd.DataFrame()
                
        except Exception as e:
            logger.error(f"获取 {symbol} 数据失败: {e}")
            # 从数据库获取历史数据作为备用
            return self.db_manager.get_stock_data(symbol, limit=count)
    
    def get_real_time_price(self, symbol: str) -> float:
        """
        获取实时价格
        
        Args:
            symbol: 股票代码
            
        Returns:
            实时价格
        """
        try:
            # 转换股票代码格式
            if symbol.endswith('.SZ'):
                ak_symbol = symbol.replace('.SZ', '')
            elif symbol.endswith('.SH'):
                ak_symbol = symbol.replace('.SH', '')
            else:
                ak_symbol = symbol
            
            # 获取实时数据
            data = ak.stock_zh_a_spot_em()
            
            if data is not None and not data.empty:
                # 查找对应股票
                stock_data = data[data['代码'] == ak_symbol]
                
                if not stock_data.empty:
                    price = float(stock_data.iloc[0]['最新价'])
                    self.current_prices[symbol] = price
                    return price
            
            # 如果实时数据获取失败，使用最新的历史数据
            historical_data = self.get_stock_basic_data(symbol, count=1)
            if not historical_data.empty:
                price = float(historical_data.iloc[-1]['close'])
                self.current_prices[symbol] = price
                return price
            
            return 0.0
            
        except Exception as e:
            logger.error(f"获取 {symbol} 实时价格失败: {e}")
            return self.current_prices.get(symbol, 0.0)
    
    def get_market_status(self) -> Dict[str, bool]:
        """
        获取市场状态
        
        Returns:
            市场状态字典
        """
        now = datetime.now()
        current_time = now.time()
        is_weekday = now.weekday() < 5
        
        # 交易时间段
        morning_start = datetime.strptime("09:30", "%H:%M").time()
        morning_end = datetime.strptime("11:30", "%H:%M").time()
        afternoon_start = datetime.strptime("13:00", "%H:%M").time()
        afternoon_end = datetime.strptime("15:00", "%H:%M").time()
        
        in_morning = morning_start <= current_time <= morning_end
        in_afternoon = afternoon_start <= current_time <= afternoon_end
        
        is_trading_time = is_weekday and (in_morning or in_afternoon)
        
        return {
            'is_trading_time': is_trading_time,
            'is_weekday': is_weekday,
            'in_morning_session': in_morning,
            'in_afternoon_session': in_afternoon,
            'current_time': current_time.strftime("%H:%M:%S")
        }
    
    def update_all_prices(self):
        """更新所有股票的实时价格"""
        if not self.stock_pool:
            return
        
        logger.info("开始更新实时价格...")
        
        for symbol in self.stock_pool:
            try:
                price = self.get_real_time_price(symbol)
                if price > 0:
                    logger.debug(f"{symbol}: ¥{price:.2f}")
                time.sleep(0.5)  # 避免请求过于频繁
                
            except Exception as e:
                logger.error(f"更新 {symbol} 价格失败: {e}")
        
        self.last_update_time = datetime.now()
        logger.info(f"价格更新完成，共 {len(self.current_prices)} 只股票")
    
    def start_real_time_update(self, interval: int = 30):
        """
        启动实时数据更新
        
        Args:
            interval: 更新间隔(秒)
        """
        if self.is_running:
            logger.warning("实时数据更新已在运行中")
            return
        
        self.is_running = True
        
        def update_loop():
            while self.is_running:
                try:
                    market_status = self.get_market_status()
                    
                    # 只在交易时间或测试时更新
                    if market_status['is_trading_time'] or True:  # 测试时总是更新
                        self.update_all_prices()
                    else:
                        logger.debug("非交易时间，跳过价格更新")
                    
                    time.sleep(interval)
                    
                except Exception as e:
                    logger.error(f"实时数据更新异常: {e}")
                    time.sleep(5)
        
        self.update_thread = threading.Thread(target=update_loop, daemon=True)
        self.update_thread.start()
        
        logger.info(f"实时数据更新已启动，更新间隔: {interval}秒")
    
    def stop_real_time_update(self):
        """停止实时数据更新"""
        self.is_running = False
        if self.update_thread:
            self.update_thread.join(timeout=5)
        
        logger.info("实时数据更新已停止")
    
    def get_current_prices(self) -> Dict[str, float]:
        """获取当前价格字典"""
        return self.current_prices.copy()
    
    def refresh_historical_data(self, days: int = 60):
        """
        刷新历史数据
        
        Args:
            days: 获取天数
        """
        logger.info(f"开始刷新历史数据，获取最近 {days} 天数据...")
        
        for symbol in self.stock_pool:
            try:
                data = self.get_stock_basic_data(symbol, count=days)
                if not data.empty:
                    logger.info(f"刷新 {symbol} 历史数据: {len(data)} 条")
                else:
                    logger.warning(f"刷新 {symbol} 历史数据失败")
                
                time.sleep(1)  # 避免请求过于频繁
                
            except Exception as e:
                logger.error(f"刷新 {symbol} 历史数据异常: {e}")
        
        logger.info("历史数据刷新完成")