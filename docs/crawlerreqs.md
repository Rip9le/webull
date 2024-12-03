# 交易所爬虫
## 需求
1. 通过各个交易所的API获取行情数据
2. 根据行情的时间维度，定期将数据存入数据库
3. 将获取到的数据进行计算，筛选出涨跌榜并存入redis

## 进展
1. 实现Binance交易所的行情数据爬取

## Binance Wesocket接口说明
URL1: https://developers.binance.com/docs/zh-CN/binance-spot-api-docs/web-socket-streams
URL2: https://developers.binance.com/docs/zh-CN/binance-spot-api-docs/web-socket-api/public-websocket-api-for-binance-2024-10-17
URL3: https://developers.binance.com/docs/zh-CN/binance-spot-api-docs/web-socket-api/public-api-requests

## 任务
1. 通过Binance Websocket获取行情数据
2. 每次从Binance Websocket获取到数据后，计算出新的涨跌榜前20存入redis
3. Binance webscoket的数据是实时推送，设计一个时间维度，将数据存入postgres数据库 // 暂时不实现
4. 要考虑到程序会长时间运行，数据库的数据量会很大，需要考虑数据的清理和备份
5. Binance websocket接口具有 有效期、链接限制、心跳检测等特性，需要处理这些异常情况

## 问题

## 下阶段计划
1. 配合Telegram Bot项目进行数据展示




