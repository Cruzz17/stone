# 🚀 Stone - 沪A量化交易系统

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![GitHub stars](https://img.shields.io/github/stars/Cruzz17/stone.svg)](https://github.com/Cruzz17/stone/stargazers)

一个功能完整的沪A股票量化交易系统，支持策略配置、回测、实时交易和风险管理。

## ✨ 功能特性

- 📊 **多数据源支持**: 集成AKShare、Tushare等主流数据源
- 🎯 **策略框架**: 可扩展的量化策略框架，内置多种经典策略
- 📈 **回测系统**: 完整的历史数据回测和性能分析
- 🔄 **实时监控**: 实时行情监控和信号生成
- ⚠️ **风险管理**: 完善的风险控制和资金管理
- 🌐 **Web界面**: 直观的策略配置和监控界面
- 📊 **可视化**: 丰富的图表和分析工具

## 🏗️ 系统架构

```
Stone量化交易系统/
├── 📊 数据层 (utils/)
│   ├── real_data_fetcher.py    # 真实数据获取
│   ├── config_loader.py        # 配置管理
│   └── technical_indicators.py # 技术指标计算
├── 🧠 策略层 (strategies/)
│   ├── base_strategy.py        # 策略基类
│   ├── double_ma_strategy.py   # 双均线策略
│   ├── rsi_strategy.py         # RSI策略
│   ├── macd_strategy.py        # MACD策略
│   └── strategy_manager.py     # 策略管理器
├── 🔄 交易层 (trading/)
│   └── simulation_engine.py    # 模拟交易引擎
├── 📈 回测层 (backtest/)
│   └── backtest_engine.py      # 回测引擎
├── 🌐 界面层
│   ├── app_enhanced_trading.py # 增强版Web应用
│   ├── app_real_trading.py     # 实时交易Web应用
│   └── run_real_trading.py     # 命令行交易
├── 💾 数据层 (data/)
│   └── database.py             # 数据库管理
└── ⚙️ 配置层 (config/)
    └── config.yaml             # 系统配置
```

## 🚀 快速开始

### 1. 环境要求

- Python 3.8+
- 操作系统: Windows/macOS/Linux

### 2. 安装

```bash
# 克隆项目
git clone https://github.com/Cruzz17/stone.git
cd stone

# 安装依赖
pip install -r requirements.txt

# 快速测试系统
python quick_start.py
```

### 3. 运行系统

#### 方式一：Web界面（推荐）

```bash
# 启动增强版Web界面
python app_enhanced_trading.py

# 或启动基础版Web界面
python app_real_trading.py
```

然后在浏览器中访问 `http://localhost:8050`

#### 方式二：命令行模式

```bash
# 启动命令行交易
python run_real_trading.py
```

## 📊 内置策略

### 1. 双均线策略 (Double MA)
- **原理**: 基于短期和长期移动平均线的交叉信号
- **信号**: 金叉买入，死叉卖出
- **适用**: 趋势性市场

### 2. RSI策略
- **原理**: 基于相对强弱指标判断超买超卖
- **信号**: RSI < 30买入，RSI > 70卖出
- **适用**: 震荡市场

### 3. MACD策略
- **原理**: 基于MACD指标的趋势跟踪
- **信号**: MACD金叉买入，死叉卖出
- **适用**: 中长期趋势

## 🌐 Web界面功能

### 主要页面

1. **📊 实时监控**
   - 投资组合概览
   - 实时价格显示
   - 持仓详情

2. **⚙️ 策略管理**
   - 策略执行状态
   - 参数配置
   - 信号生成

3. **📈 交易记录**
   - 历史交易
   - 收益分析
   - 风险指标

## ⚙️ 配置说明

主配置文件：`config/config.yaml`

```yaml
# 交易配置
trading:
  initial_capital: 1000000      # 初始资金
  max_position_pct: 0.25        # 单只股票最大仓位
  max_total_position_pct: 0.90  # 总仓位上限

# 风险管理
risk_management:
  stop_loss: 0.08               # 止损比例
  take_profit: 0.15             # 止盈比例
  max_daily_loss: 0.05          # 日最大亏损

# 策略权重
strategies:
  double_ma:
    weight: 0.4
    short_period: 5
    long_period: 20
  rsi:
    weight: 0.3
    period: 14
    oversold: 30
    overbought: 70
  macd:
    weight: 0.3
    fast: 12
    slow: 26
    signal: 9
```

## 📈 使用示例

### 策略开发

```python
from strategies.base_strategy import BaseStrategy

class MyStrategy(BaseStrategy):
    def __init__(self, config):
        super().__init__("my_strategy", config)
    
    def generate_signals(self, data, symbol):
        # 实现你的策略逻辑
        signals = []
        # ... 策略代码 ...
        return signals
```

### 回测示例

```python
from trading.simulation_engine import RealSimulationEngine

# 初始化交易引擎
config = {...}  # 配置数据
engine = RealSimulationEngine(config)

# 启动模拟交易
engine.start_simulation()

# 获取性能报告
performance = engine.get_performance_summary()
```

## 📁 项目结构

```
stone/
├── README.md                 # 项目说明文档
├── requirements.txt          # 依赖包列表
├── LICENSE                   # 开源协议
├── .gitignore               # Git忽略文件
│
├── examples/                 # 示例和演示脚本
│   ├── high_turnover_backtest.py    # 完整版高换手率回测
│   ├── quick_turnover_test.py       # 快速测试版本
│   └── demo_high_turnover.py        # 交互式演示
│
├── docs/                     # 文档目录
│   ├── HIGH_TURNOVER_GUIDE.md       # 高换手率系统使用指南
│   └── SUMMARY.md                   # 项目总结
│
├── backtest/                 # 回测引擎
│   ├── __init__.py
│   └── backtest_engine.py    # 核心回测引擎
│
├── strategies/               # 交易策略
│   ├── __init__.py
│   ├── base_strategy.py      # 策略基类
│   ├── double_ma_strategy.py # 双均线策略
│   ├── rsi_strategy.py       # RSI策略
│   └── macd_strategy.py      # MACD策略
│
├── utils/                    # 工具模块
│   ├── __init__.py
│   ├── real_data_fetcher.py  # 数据获取器
│   └── indicators.py         # 技术指标计算
│
├── data/                     # 数据存储
│   ├── __init__.py
│   └── database.py           # 数据库管理
│
└── config/                   # 配置文件
    ├── __init__.py
    └── settings.py           # 系统配置
```

## 🚀 快速开始

### 环境要求
- Python 3.8+
- 推荐使用虚拟环境

### 安装依赖
```bash
pip install -r requirements.txt
```

### 快速体验高换手率回测系统

#### 1. 快速测试（推荐新手）
```bash
cd examples
python quick_turnover_test.py
```

#### 2. 交互式演示
```bash
cd examples
python demo_high_turnover.py
```

#### 3. 完整回测
```bash
cd examples
python high_turnover_backtest.py
```

### 基本使用示例

```python
from backtest.backtest_engine import BacktestEngine
from strategies.macd_strategy import MACDStrategy
from utils.real_data_fetcher import RealDataFetcher
from data.database import DatabaseManager

# 初始化组件
db_manager = DatabaseManager()
data_fetcher = RealDataFetcher(db_manager)
backtest_engine = BacktestEngine(initial_capital=1000000)

# 创建策略
strategy = MACDStrategy({
    'fast_period': 12,
    'slow_period': 26, 
    'signal_period': 9
})

# 运行回测
result = backtest_engine.run_backtest(
    strategy=strategy,
    symbols=['000001', '000002'],
    start_date='2024-01-01',
    end_date='2024-12-31'
)

# 查看结果
print(f"总收益率: {result['performance_metrics']['total_return']:.2%}")
```

## 📊 支持的策略

### 1. 双均线策略 (DoubleMaStrategy)
- **原理**: 基于短期和长期移动平均线的交叉信号
- **参数**: 短期周期(默认5)、长期周期(默认20)
- **适用**: 趋势性市场

### 2. RSI策略 (RSIStrategy)  
- **原理**: 基于相对强弱指标的超买超卖判断
- **参数**: RSI周期(默认14)、超卖阈值(默认30)、超买阈值(默认70)
- **适用**: 震荡市场

### 3. MACD策略 (MACDStrategy)
- **原理**: 基于MACD指标的趋势跟踪
- **参数**: 快速周期(默认12)、慢速周期(默认26)、信号周期(默认9)
- **适用**: 趋势确认和转折点识别

## 🎯 高换手率回测系统特色

### 智能选股
- 自动获取全市场A股换手率数据
- 筛选过去30天换手率最高的股票
- 支持自定义选股数量和统计周期

### 多维度分析
- **收益指标**: 总收益率、年化收益率、超额收益
- **风险指标**: 最大回撤、波动率、夏普比率  
- **交易指标**: 胜率、盈亏比、交易次数

### 预定义股票池
包含24只活跃股票，涵盖：
- 科技股：五粮液、海康威视、比亚迪等
- 金融股：招商银行、中国平安、工商银行等  
- 消费股：贵州茅台、万科A等
- 其他活跃股票：科大讯飞、立讯精密等

### 策略评价标准
- 🌟🌟🌟 优秀：年化收益>20%，夏普比率>1.5，回撤<5%
- 🌟🌟 良好：年化收益>10%，夏普比率>1.0，回撤<10%
- 🌟 一般：年化收益>5%，夏普比率>0.5，回撤<20%

## 📈 数据源

- **股票数据**: 支持多个数据源（tushare、akshare等）
- **技术指标**: 自动计算常用技术指标
- **实时数据**: 支持实时价格和成交量数据
- **历史数据**: 完整的历史K线数据

## 🔧 配置说明

### 回测参数
```python
BacktestEngine(
    initial_capital=1000000,    # 初始资金
    commission_rate=0.0003,     # 手续费率(万3)
    stamp_tax_rate=0.001,       # 印花税率(千1)
    min_trade_unit=100          # 最小交易单位
)
```

### 策略参数
```python
# MACD策略配置
MACDStrategy({
    'fast_period': 12,      # 快速EMA周期
    'slow_period': 26,      # 慢速EMA周期  
    'signal_period': 9      # 信号线周期
})
```

## 📚 文档

- [高换手率系统使用指南](docs/HIGH_TURNOVER_GUIDE.md) - 详细的使用说明和参数配置
- [项目总结](docs/SUMMARY.md) - 项目功能总结和使用建议

## 🤝 贡献

欢迎提交Issue和Pull Request来改进项目。

### 开发指南
1. Fork项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开Pull Request

## 📄 许可证

本项目采用MIT许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## ⚠️ 免责声明

本项目仅用于学习和研究目的，不构成投资建议。实际投资请谨慎决策，注意风险控制。

## 📞 联系方式

如有问题或建议，请通过以下方式联系：
- 提交Issue
- 发送邮件

---

**最后更新**: 2025-05-28  
**版本**: v2.0.0 - 新增高换手率回测系统

## 🔗 相关链接

- [AKShare文档](https://akshare.akfamily.xyz/)
- [Tushare文档](https://tushare.pro/)
- [Dash文档](https://dash.plotly.com/)
