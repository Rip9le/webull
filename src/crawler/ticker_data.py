import schedule
import time
import psycopg2
import requests
from datetime import datetime, timedelta
from config import DB_CONFIG, BINANCE_API_URL

def fetch_and_store_full_data():
    """
    拉取 Binance /api/v3/ticker/24hr 全量数据并存储到数据库。
    """
    response = requests.get(BINANCE_API_URL)
    if response.status_code != 200:
        print(f"Failed to fetch Binance data: {response.status_code}")
        return

    data = response.json()
    data_time = datetime.utcnow().replace(minute=0, second=0, microsecond=0)  # 当前小时整点时间

    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()

    for item in data:
        cursor.execute("""
            INSERT INTO ticker_data_full (
                symbol, price_change, price_change_percent, weighted_avg_price,
                last_price, last_qty, bid_price, bid_qty, ask_price, ask_qty,
                open_price, high_price, low_price, volume, quote_volume,
                open_time, close_time, first_id, last_id, count, data_time
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, to_timestamp(%s / 1000), to_timestamp(%s / 1000), %s, %s, %s, %s)
            ON CONFLICT (symbol, data_time) DO NOTHING
        """, (
            item['symbol'], float(item['priceChange']), float(item['priceChangePercent']), float(item['weightedAvgPrice']),
            float(item['lastPrice']), float(item['lastQty']), float(item['bidPrice']), float(item['bidQty']),
            float(item['askPrice']), float(item['askQty']), float(item['openPrice']), float(item['highPrice']),
            float(item['lowPrice']), float(item['volume']), float(item['quoteVolume']),
            item['openTime'], item['closeTime'], item['firstId'], item['lastId'], item['count'], data_time
        ))

    conn.commit()
    cursor.close()
    conn.close()

    print(f"Full data stored successfully for {data_time}.")

# 每小时整点运行
schedule.every().hour.at(":00").do(fetch_and_store_full_data)
while True:
    schedule.run_pending()
    time.sleep(1)