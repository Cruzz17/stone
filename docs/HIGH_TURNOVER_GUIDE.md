# 高换手率股票回测系统使用指南

## 系统概述

本系统专门用于拉取过去一个月换手率最高的股票，并对这些活跃股票进行量化策略回测，计算收益表现。

## 功能特性

### 1. 高换手率股票筛选
- 🔍 **自动筛选**: 从全市场A股中筛选换手率最高的股票
- 📊 **数据获取**: 支持AKShare真实数据和模拟数据两种模式
- 🎯 **灵活配置**: 可自定义统计天数和选股数量

### 2. 多策略回测
- 📈 **双均线策略**: 基于短期和长期移动平均线交叉
- 📉 **RSI策略**: 基于相对强弱指标的超买超卖判断
- 🌊 **MACD策略**: 基于MACD指标的趋势跟踪

### 3. 完整的回测分析
- 💰 **收益分析**: 总收益率、年化收益率、超额收益
- 📊 **风险评估**: 最大回撤、波动率、夏普比率
- 🎯 **交易分析**: 胜率、盈亏比、交易次数
- 📈 **图表展示**: 收益曲线、回撤分析、策略对比

## 文件说明

### 主要脚本

1. **`high_turnover_backtest.py`** - 完整版高换手率回测系统
   - 支持真实换手率数据获取
   - 完整的回测流程
   - 详细的结果分析和导出

2. **`quick_turnover_test.py`** - 快速测试版本
   - 使用预定义的活跃股票池
   - 快速验证系统功能
   - 简化的结果展示

### 核心模块

- **`backtest/backtest_engine.py`** - 回测引擎
- **`utils/real_data_fetcher.py`** - 数据获取器
- **`strategies/`** - 策略模块目录
- **`data/database.py`** - 数据库管理

## 使用方法

### 方法一：快速测试（推荐新手）

```bash
python quick_turnover_test.py
```

**特点：**
- 使用预定义的24只活跃股票
- 运行速度快，适合功能验证
- 包含完整的策略回测流程

### 方法二：完整回测

```bash
python high_turnover_backtest.py
```

**特点：**
- 真实获取换手率数据（需要AKShare）
- 支持自定义参数配置
- 完整的结果导出功能

### 方法三：自定义参数

```python
from high_turnover_backtest import HighTurnoverBacktest

# 创建回测系统
backtest_system = HighTurnoverBacktest()

# 自定义参数运行
backtest_system.run_complete_backtest(
    days=30,        # 统计换手率的天数
    top_n=100,      # 选择前100只股票
    strategy='all', # 测试所有策略
    data_days=90    # 下载90天历史数据
)
```

## 预定义股票池

快速测试版本使用以下活跃股票：

### 科技股
- 000858 (五粮液)
- 002415 (海康威视)
- 002594 (比亚迪)
- 300059 (东方财富)
- 300122 (智飞生物)
- 300124 (汇川技术)
- 300142 (沃森生物)
- 300274 (阳光电源)
- 300408 (三环集团)
- 300454 (深信服)

### 金融股
- 600000 (浦发银行)
- 600036 (招商银行)
- 601318 (中国平安)
- 601398 (工商银行)

### 消费股
- 600519 (贵州茅台)
- 000001 (平安银行)
- 000002 (万科A)

### 其他活跃股票
- 002230 (科大讯飞)
- 002241 (歌尔股份)
- 002304 (洋河股份)
- 002371 (北方华创)
- 002475 (立讯精密)
- 300015 (爱尔眼科)
- 300033 (同花顺)

## 策略配置

### 双均线策略
```python
{
    'short_window': 5,   # 短期均线周期
    'long_window': 20    # 长期均线周期
}
```

### RSI策略
```python
{
    'rsi_period': 14,    # RSI计算周期
    'oversold': 30,      # 超卖阈值
    'overbought': 70     # 超买阈值
}
```

### MACD策略
```python
{
    'fast_period': 12,   # 快速EMA周期
    'slow_period': 26,   # 慢速EMA周期
    'signal_period': 9   # 信号线周期
}
```

## 回测参数

### 交易成本设置
- **初始资金**: 1,000,000元（100万）
- **手续费率**: 0.0003（万分之3）
- **印花税率**: 0.001（千分之1）
- **最小交易单位**: 100股

### 数据设置
- **默认数据天数**: 60天
- **最小数据要求**: 20个交易日
- **技术指标计算**: 自动计算MA、RSI、MACD等

## 结果分析

### 性能指标

1. **收益指标**
   - 总收益率：整个回测期间的总收益
   - 年化收益率：按年计算的收益率
   - 超额收益(Alpha)：相对基准的超额收益

2. **风险指标**
   - 最大回撤：最大的资产下跌幅度
   - 波动率：收益率的标准差
   - 夏普比率：风险调整后的收益

3. **交易指标**
   - 胜率：盈利交易占总交易的比例
   - 盈亏比：平均盈利与平均亏损的比值
   - 交易次数：总的买卖交易次数

### 策略评价标准

#### 优秀策略 🌟🌟🌟
- 年化收益率 > 20%
- 夏普比率 > 1.5
- 最大回撤 < 5%
- 胜率 > 60%

#### 良好策略 🌟🌟
- 年化收益率 > 10%
- 夏普比率 > 1.0
- 最大回撤 < 10%
- 胜率 > 50%

#### 一般策略 🌟
- 年化收益率 > 5%
- 夏普比率 > 0.5
- 最大回撤 < 20%
- 胜率 > 40%

## 输出文件

运行完整回测后，系统会在`backtest_results/`目录下生成：

1. **策略对比结果**: `strategy_comparison_YYYYMMDD_HHMMSS.csv`
2. **交易记录**: `{策略名称}_trades_YYYYMMDD_HHMMSS.csv`
3. **股票列表**: `high_turnover_stocks_YYYYMMDD_HHMMSS.csv`
4. **图表文件**: 收益曲线、回撤分析等图表

## 注意事项

### 数据依赖
- 真实数据需要安装AKShare：`pip install akshare`
- 无AKShare时自动使用模拟数据
- 模拟数据仅用于功能测试，不代表真实市场表现

### 性能考虑
- 获取真实换手率数据较耗时，建议先用快速测试版本
- 股票数量越多，回测时间越长
- 建议首次使用时选择较少的股票数量

### 策略限制
- 当前策略相对简单，实际投资需要更复杂的风控
- 回测结果不代表未来表现
- 建议结合多种策略和风险管理

## 扩展功能

### 添加新策略
1. 在`strategies/`目录下创建新策略文件
2. 继承`BaseStrategy`类
3. 实现`generate_signals`方法
4. 在回测脚本中添加策略配置

### 自定义股票池
```python
# 修改quick_turnover_test.py中的active_stocks列表
self.active_stocks = [
    '000001',  # 平安银行
    '000002',  # 万科A
    # 添加更多股票代码...
]
```

### 参数优化
系统支持策略参数优化，可以自动寻找最佳参数组合：

```python
# 在策略类中实现optimize_parameters方法
best_params = strategy.optimize_parameters(data, symbol)
```

## 常见问题

### Q: 为什么所有策略收益率都是0%？
A: 可能的原因：
1. 数据时间范围太短，策略没有触发交易信号
2. 策略参数设置过于严格
3. 股票价格波动不足以触发策略条件

### Q: 如何提高策略表现？
A: 建议：
1. 调整策略参数，如均线周期、RSI阈值等
2. 增加数据时间范围
3. 结合多个策略进行组合投资
4. 添加止损止盈机制

### Q: 真实数据获取失败怎么办？
A: 解决方案：
1. 检查网络连接
2. 确认AKShare版本是否最新
3. 使用快速测试版本的模拟数据
4. 减少请求频率，避免被限制

## 技术支持

如遇到问题，请检查：
1. Python环境和依赖包是否正确安装
2. 数据库文件是否正常创建
3. 日志输出中的错误信息
4. 策略参数配置是否合理

---

**免责声明**: 本系统仅用于学习和研究目的，不构成投资建议。实际投资请谨慎决策，注意风险控制。 