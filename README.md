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
├── 📄 主要文件
│   ├── app_enhanced_trading.py  # 增强版Web应用
│   ├── app_real_trading.py      # 基础版Web应用
│   ├── run_real_trading.py      # 命令行交易
│   ├── quick_start.py           # 快速测试
│   └── requirements.txt         # 依赖包
├── 📂 核心模块
│   ├── strategies/              # 交易策略
│   ├── trading/                 # 交易引擎
│   ├── backtest/               # 回测引擎
│   ├── utils/                  # 工具函数
│   ├── data/                   # 数据管理
│   └── config/                 # 配置文件
└── 📂 数据目录
    └── data/                   # 数据存储
```

## 🛠️ 开发指南

### 添加新策略

1. 继承 `BaseStrategy` 类
2. 实现 `generate_signals` 方法
3. 在配置文件中添加策略参数
4. 在策略管理器中注册策略

### 自定义数据源

1. 实现数据获取接口
2. 继承 `RealDataFetcher` 类
3. 添加数据源配置

## ⚠️ 风险提示

1. **本系统仅供学习和研究使用**
2. **实盘交易前请充分回测验证策略**
3. **量化交易存在亏损风险，请谨慎操作**
4. **建议先使用模拟交易熟悉系统**
5. **注意风险控制，合理配置仓位**

## 🤝 贡献

欢迎提交Issue和Pull Request来改进系统！

### 开发环境

```bash
# 克隆项目
git clone https://github.com/Cruzz17/stone.git
cd stone

# 安装依赖
pip install -r requirements.txt

# 运行测试
python quick_start.py
```

## 📄 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件

## 📞 联系方式

- 🐛 Issues: [GitHub Issues](https://github.com/Cruzz17/stone/issues)
- 📧 Email: 欢迎通过GitHub Issues联系

---

**⭐ 如果这个项目对你有帮助，请给个Star支持一下！**

## 🔗 相关链接

- [AKShare文档](https://akshare.akfamily.xyz/)
- [Tushare文档](https://tushare.pro/)
- [Dash文档](https://dash.plotly.com/)
