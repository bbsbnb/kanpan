# AI智能看盘系统 - MVP

## 快速开始

```bash
cd ai-stock-trader
pip install -r requirements.txt
python main.py --code 600519
```

## 项目结构

```
ai-stock-trader/
├── main.py              # 入口
├── config.yaml          # 配置
├── requirements.txt     # 依赖
├── data/                # 缓存数据
│   └── cache.py         # 本地缓存
├── agents/              # Agent模块
│   ├── base.py          # Agent基类
│   ├── analyst.py       # 分析师Agent
│   ├── researcher.py    # 研究员Agent
│   ├── trader.py        # 交易员Agent
│   ├── risk_manager.py  # 风控Agent
│   └── portfolio_mgr.py # 投资经理Agent
├── indicators/          # 技术指标
│   ├── ta_engine.py     # 指标计算引擎
│   └── signals.py       # 信号生成
├── news/                # 舆情数据
│   └── sentiment.py     # 情绪分析
└── utils/               # 工具
    └── logger.py        # 日志
```

## MVP功能清单

- [x] AKShare行情数据接入
- [x] 技术指标计算（MA/MACD/RSI/KDJ/布林带）
- [x] 分析师Agent自动生成技术分析报告
- [ ] 研究员Agent舆情分析（后续）
- [ ] 交易员Agent信号生成（后续）
- [ ] 风控Agent规则引擎（后续）
- [ ] Web看板（后续）
