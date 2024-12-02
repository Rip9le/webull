import requests
import psycopg2
import redis
import json
import time
import logging
from datetime import datetime, timezone, timedelta
from apscheduler.schedulers.background import BackgroundScheduler

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("marketcrawler.log"),  # 日志写入文件
        logging.StreamHandler()  # 控制台输出日志
    ]
)

# PostgreSQL 配置
DB_CONFIG = {
    "database": "longbull",
    "user": "mando",
    "password": "U4AXRLDQuVau7MGEKKbU",
    "host": "localhost",
    "port": "5432"
}

# Redis 配置
REDIS_HOST = "localhost"
REDIS_PORT = 6379
REDIS_DB = 0

# Redis 连接
redis_client = redis.StrictRedis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)


# 检查数据库中是否有当天数据
def has_today_data():
    try:
        url = "https://api.binance.com/api/v3/time"
        response = requests.get(url)
        if response.status_code != 200:
            raise Exception("Failed to fetch Binance server time")

        server_time = response.json()['serverTime'] / 1000  # 转换为秒
        server_date = datetime.fromtimestamp(server_time, tz=timezone.utc).date()  # 转为 UTC 日期

        # 连接 PostgreSQL 数据库
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        # 查询当天数据是否存在
        cursor.execute("""SELECT COUNT(*) FROM price_data_history 
            WHERE DATE(close_time) = %s""", (server_date,))
        count = cursor.fetchone()[0]

        cursor.close()
        conn.close()

        return count > 0
    except Exception as e:
        logging.error(f"Error checking today's data: {e}")
        return False


# 获取 Binance API 数据
def fetch_binance_data():
    try:
        url = "https://api.binance.com/api/v3/ticker/24hr"
        response = requests.get(url)
        if response.status_code == 200:
            logging.info("Binance data fetched successfully.")
            return response.json()
        else:
            logging.error(f"Failed to fetch Binance data: {response.status_code}")
            return None
    except Exception as e:
        logging.error(f"Error fetching Binance data: {e}")
        return None

# 取数据库中的最新数据
def get_existing_latest_close_times():
    """
    获取数据库中每个 symbol 对应的最新 close_time。
    返回字典 {symbol: close_time}
    """
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()

    # 查询每个 symbol 的最新 close_time
    cursor.execute("""
        SELECT DISTINCT ON (symbol) symbol, close_time
        FROM price_data_history
        ORDER BY symbol, close_time DESC
    """)
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    # 组织为字典形式 {symbol: close_time}
    existing_data = {symbol: close_time for symbol, close_time in rows}
    return existing_data

# 保存数据到 PostgreSQL
def save_to_postgresql(data):
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        for item in data:
            cursor.execute("""
                INSERT INTO price_data_history (symbol, price_change, price_change_percent, last_price, high_price, 
                                                    low_price, volume, quote_volume, open_time, close_time)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, to_timestamp(%s / 1000), to_timestamp(%s / 1000))
                ON CONFLICT (symbol, close_time) DO NOTHING;
            """, (
                item['symbol'],
                float(item['priceChange']),
                float(item['priceChangePercent']),
                float(item['lastPrice']),
                float(item['highPrice']),
                float(item['lowPrice']),
                float(item['volume']),
                float(item['quoteVolume']),
                item['openTime'],
                item['closeTime']
            ))

        conn.commit()
        cursor.close()
        conn.close()
        logging.info("Data saved to PostgreSQL successfully.")
    except Exception as e:
        logging.error(f"Error saving data to PostgreSQL: {e}")


# 计算涨跌幅前 20 的币种
def calculate_top_gainers_and_losers(data):
    try:
        sorted_data = sorted(data, key=lambda x: float(x['priceChangePercent']), reverse=True)
        top_gainers = sorted_data[:20]

        sorted_data = sorted(data, key=lambda x: float(x['priceChangePercent']))
        top_losers = sorted_data[:20]

        logging.info("Top gainers and losers calculated successfully.")
        return top_gainers, top_losers
    except Exception as e:
        logging.error(f"Error calculating top gainers and losers: {e}")
        return [], []


# 保存结果到 Redis
def save_to_redis(key, data):
    try:
        redis_client.set(key, json.dumps(data), ex=86400)  # 缓存 24 小时
        logging.info(f"{key} saved to Redis successfully.")
    except Exception as e:
        logging.error(f"Error saving {key} to Redis: {e}")


# 动态调整频率的检测新数据逻辑
def fetch_data_at_midnight():
    interval = 300  # 初始检测间隔 5 分钟
    while True:
        now = datetime.now(timezone.utc)
        remaining_minutes = (60 - now.minute) + (23 - now.hour) * 60

        # 缩短检测间隔在凌晨前后
        if remaining_minutes <= 10:
            interval = 60  # 1 分钟检测一次
        elif remaining_minutes <= 30:
            interval = 180  # 3 分钟检测一次

        # 检测新数据是否可用
        if is_new_day_data_available():
            logging.info("New day data available. Fetching now...")
            data = fetch_binance_data()
            if data:
                save_to_postgresql(data)
                top_gainers, top_losers = calculate_top_gainers_and_losers(data)
                save_to_redis("top_gainers", top_gainers)
                save_to_redis("top_losers", top_losers)
            break
        else:
            logging.info(f"New data not available. Retrying in {interval} seconds.")
            time.sleep(interval)


# 检测 API 数据是否更新到新一天
def is_new_day_data_available():
    try:
        url = "https://api.binance.com/api/v3/ticker/24hr"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            if len(data) > 0:
                close_time = data[0]['closeTime'] / 1000
                close_date = datetime.fromtimestamp(close_time, tz=timezone.utc).date()
                current_date = datetime.now(timezone.utc).date()
                return close_date == current_date
        return False
    except Exception as e:
        logging.error(f"Error checking new day data: {e}")
        return False


# 定时任务逻辑
def main_task():
    if not has_today_data():
        logging.info("No data for today. Checking for new data...")
        fetch_data_at_midnight()
    else:
        logging.info("Today's data already exists.")


# 主程序入口
if __name__ == "__main__":
    scheduler = BackgroundScheduler()
    scheduler.add_job(main_task, 'cron', hour=0, minute=0)  # 每天凌晨 0 点执行
    scheduler.start()

    logging.info("Scheduler is running. Press Ctrl+C to exit.")

    # 程序启动时立即检查并触发主任务
    main_task()

    try:
        while True:
            pass
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
