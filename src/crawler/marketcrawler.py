import asyncio
import logging
import redis.asyncio as redis
import json
import websockets
from dotenv import load_dotenv
import os
import signal
import ssl

ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

# 加载环境变量
load_dotenv()

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 从环境变量中获取数据库配置
DB_CONFIG = {
    'user': os.getenv('POSTGRES_USER'),
    'password': os.getenv('POSTGRES_PASSWORD'),
    'database': os.getenv('POSTGRES_DB'),
    'host': os.getenv('POSTGRES_HOST'),
    'port': os.getenv('POSTGRES_PORT'),
}

# Binance WebSocket地址
WS_URL = 'wss://stream.binance.com:9443/ws/!ticker@arr'

# Redis 配置
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost')


# 数据校验函数
def validate_data(data):
    required_fields = [
        'e', 'E', 's', 'p', 'P', 'w', 'x', 'c', 'Q',
        'b', 'B', 'a', 'A', 'o', 'h', 'l', 'v', 'q',
        'O', 'C', 'F', 'L', 'n'
    ]
    for field in required_fields:
        if field not in data:
            raise ValueError(f"Missing field: {field}")

    # 验证字段类型
    if not isinstance(data['E'], int):
        raise TypeError(f"Invalid type for event_time: {data['E']}")
    if not isinstance(data['s'], str):
        raise TypeError(f"Invalid type for symbol: {data['s']}")

    # 验证数值字段
    numeric_fields = ['p', 'P', 'w', 'x', 'c', 'Q', 'b', 'B', 'a', 'A', 'o', 'h', 'l', 'v', 'q']
    for field in numeric_fields:
        if data[field] is not None and not isinstance(data[field], (int, float, str)):
            raise TypeError(f"Invalid type for {field}: {data[field]}")

    # 验证范围
    # if float(data['P']) < 0:
    #     raise ValueError(f"Price change percent cannot be negative: {data['P']}")

    return True  # 数据有效


# 保存数据到数据库
# async def save_to_db(pool, data):
#     try:
#         async with pool.acquire() as connection:
#             async with connection.transaction():
#                 await connection.execute('''
#                     INSERT INTO market_tickers (
#                         event_type, event_time, symbol, price_change, price_change_percent,
#                         weighted_avg_price, prev_close_price, last_price, last_qty,
#                         bid_price, bid_qty, ask_price, ask_qty, open_price, high_price,
#                         low_price, volume, quote_volume, open_time, close_time,
#                         first_trade_id, last_trade_id, trade_count
#                     ) VALUES (
#                         $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15,
#                         $16, $17, $18, $19, $20, $21, $22, $23
#                     )
#                 ''', (
#                     data.get('e'), data.get('E'), data.get('s'), data.get('p'),
#                     data.get('P'), data.get('w'), data.get('x'), data.get('c'),
#                     data.get('Q'), data.get('b'), data.get('B'), data.get('a'),
#                     data.get('A'), data.get('o'), data.get('h'), data.get('l'),
#                     data.get('v'), data.get('q'), data.get('O'), data.get('C'),
#                     data.get('F'), data.get('L'), data.get('n')
#                 ))
#     except asyncpg.PostgresError as e:
#         logging.error(f"Database error: {e}")
#     except KeyError as e:
#         logging.warning(f"Missing key in data: {e}")
#     except Exception as e:
#         logging.error(f"Unexpected error during data saving: {e}")


# 保存数据到 Redis
async def save_to_redis(redis_client, data):
    try:
        pipeline = redis_client.pipeline()

        # 存储所有币种的详细信息
        for item in data:
            symbol = item['s']
            pipeline.hset("market:details", symbol, json.dumps(item))

        # 更新涨跌榜前20
        pipeline.delete("market:top20")
        for item in sorted(data, key=lambda x: float(x['P']), reverse=True)[:20]:
            pipeline.zadd("market:top20", {item['s']: float(item['P'])})

        await pipeline.execute()
        logging.info("Successfully updated Redis with market details and top 20 data.")
    except Exception as e:
        logging.error(f"Error saving data to Redis: {e}")


async def handle_message(pool, redis_client, message):
    """
    处理 WebSocket 推送的消息，更新 Redis 和 PostgreSQL 数据。
    """
    try:
        data = json.loads(message)

        # 确保 data 是列表，统一处理逻辑
        if isinstance(data, dict):
            data = [data]  # 如果是单个字典，转换为列表

        # 遍历处理列表中的每个元素
        if isinstance(data, list):
            valid_data = [item for item in data if isinstance(item, dict) and validate_data(item)]
            await save_to_redis(redis_client, valid_data)
        else:
            logging.warning(f"Unexpected data type: {type(data)}")

    except json.JSONDecodeError as e:
        logging.error(f"Failed to decode JSON message: {e}")
    except Exception as e:
        logging.error(f"Error processing message: {e}")


async def connect_to_binance(pool, redis_client):
    """
    连接 Binance WebSocket 并处理消息。
    """
    while True:
        try:
            async with websockets.connect(WS_URL, ssl=ssl_context) as websocket:
                logging.info("Connected to Binance WebSocket.")
                async for message in websocket:
                    await handle_message(pool, redis_client, message)
        except websockets.exceptions.ConnectionClosedError as e:
            logging.error(f"WebSocket connection closed: {e}. Retrying in 5 seconds...")
            await asyncio.sleep(5)
        except (asyncio.TimeoutError, OSError) as e:
            logging.error(f"Network error: {e}. Retrying in 5 seconds...")
            await asyncio.sleep(5)
        except Exception as e:
            logging.error(f"Unexpected error during WebScoket connection: {e}")
            await asyncio.sleep(5)


async def cleanup_resources(pool, redis_client):
    logging.info("Cleaning up resources...")
    # if pool:
    #     await pool.close()
    if redis_client:
        await redis_client.close()


# 主函数
async def main():
    # 初始化数据库连接池和 Redis 客户端
    # pool = await asyncpg.create_pool(**DB_CONFIG)
    redis_client = redis.from_url(REDIS_URL)

    try:
        await connect_to_binance(pool, redis_client)
    except Exception as e:
        # 确保资源清理
        await cleanup_resources(pool, redis_client)
        logging.error(f"Failed to initialize: {e}")


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    pool, redis_client = None, None  # 初始化资源为 None

    try:
        # 处理终止信号
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, lambda: asyncio.ensure_future(cleanup_resources(pool, redis_client)))

        loop.run_until_complete(main())
    except Exception as e:
        logging.error(f"Fatal error: {e}")
    finally:
        loop.close()
