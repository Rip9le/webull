
# Binance Exchange API Documentation

## 1. Purpose
This document provides details about the Binance Exchange API, including endpoints for public market data, account management, and order execution. It aims to guide developers in integrating Binance API into their projects.

---

## 2. API Endpoints Overview

| Category      | Endpoint                 | Method      | Description                          |
|---------------|--------------------------|-------------|--------------------------------------|
| Public Data   | `!ticker@arr` (WebSocket)| WebSocket   | Real-time market ticker data         |
| Account Data  | `/api/v3/account`        | REST        | Query account balances and details   |
| Order Execution | `/api/v3/order`        | REST        | Create and manage trading orders     |

---

## 3. API Details

### 3.1 Public Market Data: WebSocket
**Endpoint**: `wss://stream.binance.com:9443/ws`

#### Supported Subscriptions:
- **Single Pair Data**: `<symbol>@ticker` (e.g., `btcusdt@ticker`)
- **All Pairs Data**: `!ticker@arr`

#### Example Response:
```json
[
  {
      "e": "24hrTicker",  // 事件类型
      "E": 1672515782136, // 事件时间
      "s": "BNBBTC",      // 交易对
      "p": "0.0015",      // 24小时价格变化
      "P": "250.00",      // 24小时价格变化（百分比）
      "w": "0.0018",      // 平均价格
      "x": "0.0009",      // 整整24小时之前，向前数的最后一次成交价格
      "c": "0.0025",      // 最新成交价格
      "Q": "10",          // 最新成交交易的成交量
      "b": "0.0024",      // 目前最高买单价
      "B": "10",          // 目前最高买单价的挂单量
      "a": "0.0026",      // 目前最低卖单价
      "A": "100",         // 目前最低卖单价的挂单量
      "o": "0.0010",      // 整整24小时前，向后数的第一次成交价格
      "h": "0.0025",      // 24小时内最高成交价
      "l": "0.0010",      // 24小时内最低成交加
      "v": "10000",       // 24小时内成交量
      "q": "18",          // 24小时内成交额
      "O": 0,             // 统计开始时间
      "C": 1675216573749, // 统计结束时间
      "F": 0,             // 24小时内第一笔成交交易ID
      "L": 18150,         // 24小时内最后一笔成交交易ID
      "n": 18151          // 24小时内成交数
  }
]
```

#### Notes:
- **Heartbeat**: Binance sends a ping every 3 minutes to maintain the connection.
- **Usage Tip**: Validate fields before processing data to ensure message completeness.

---

### 3.2 Account Data: REST API
**Endpoint**: `https://api.binance.com/api/v3/account`

#### Request Parameters:
| Parameter    | Type   | Required | Description                 |
|--------------|--------|----------|-----------------------------|
| `timestamp`  | long   | Yes      | Request timestamp           |
| `signature`  | string | Yes      | HMAC SHA256 signature       |

#### Example Response:
```json
{
  "makerCommission": 15,
  "takerCommission": 15,
  "buyerCommission": 0,
  "sellerCommission": 0,
  "balances": [
    {
      "asset": "BTC",
      "free": "4723846.89208129",
      "locked": "0.00000000"
    },
    {
      "asset": "LTC",
      "free": "4763368.68006011",
      "locked": "0.00000000"
    }
  ]
}
```

#### Notes:
- **Signature**: Use HMAC SHA256 to generate the `signature` from the query string.
- **Balance Information**: `free` indicates available balance, and `locked` represents reserved funds.

---

### 3.3 Order Execution: REST API
**Endpoint**: `https://api.binance.com/api/v3/order`

#### Request Parameters:
| Parameter     | Type   | Required | Description                |
|---------------|--------|----------|----------------------------|
| `symbol`      | string | Yes      | Trading pair (e.g., BTCUSDT)|
| `side`        | string | Yes      | Order direction (BUY/SELL) |
| `type`        | string | Yes      | Order type (LIMIT/MARKET)  |
| `quantity`    | double | Yes      | Order quantity             |
| `price`       | double | Optional | Price for limit orders     |
| `timestamp`   | long   | Yes      | Request timestamp          |
| `signature`   | string | Yes      | HMAC SHA256 signature      |

#### Example Response:
```json
{
  "symbol": "BTCUSDT",
  "orderId": 28,
  "clientOrderId": "6gCrw2kRUAF9CvJDGP16IP",
  "transactTime": 1507725176595,
  "price": "0.1",
  "origQty": "1.0",
  "executedQty": "0.0",
  "status": "NEW",
  "timeInForce": "GTC",
  "type": "LIMIT",
  "side": "SELL"
}
```

#### Notes:
- **Order States**: Monitor the `status` field to track order progress.
- **Signature**: Required for authenticated requests.

---

## 4. General Considerations
- **API Rate Limits**: Ensure compliance with Binance rate limits to avoid IP bans.
- **Error Codes**: Refer to Binance API documentation for error code explanations.
- **Security**: Use HTTPS for all REST API requests to ensure data safety.

---

## 5. Future Enhancements
- Support for additional exchanges (e.g., Coinbase, Huobi).
- Periodic updates based on API changes.
- Integration with webhook notifications for significant events.
