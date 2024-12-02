# WB requirements

## 项目目标
1. 爬取主流交易所(CEX and DEX)行情数据, 并筛选出涨跌榜。
2. 每日定期推送或用户主动请求时，通过Telegram Bot展示涨跌榜信息
3. 实现数字货币市场的各种信号监控，并推送给用户
4. 通过用户的账户交易记录，生成数据分析报告和改进建议

## 当前进展
### **项目版本**
v0.1.0 - 开发中
### **版本功能**
1. 通过Binance Websocket接口获取行情数据，并存入redis和postgres
2. 计算当前24小时的涨跌榜前20并储存在redis中
3. 每日推送一条24小时涨跌榜前20的消息给所有用户
4. 当用户通过telegram bot主动请求时，也展示当前的24小时涨跌榜前20
### **具体需求**
docs/crawlerreqs.md

## 文件目录说明
my_project/
├── README.md                 # 项目简介
├── src/                      # 源代码目录
│   ├── bg/                   # 后台项目文件夹
│   ├── crawler               # 交易所爬虫项目文件夹
│   └── tgbot                 # telegram bot项目文件夹
├── tests/                    # 测试代码
├── docs/                     # 文档目录
│   └── crawlerreqs.md        # 爬虫需求文档
└── logs/                     # 日志目录（应被忽略）
    └── app.log
