import asyncio
import logging

from redis.asyncio import Redis
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler

# Redis 配置
REDIS_URL = "redis://localhost"

# 初始化 Redis 客户端
redis_client = Redis.from_url(REDIS_URL)

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 格式化工具
def format_price(price):
    return f"{float(price):.4f}"  # 4 decimal places

def format_percent(percent):
    return f"{float(percent):.2f}%"  # 2 decimal places

# 从 Redis 获取涨跌榜前 20 和跌幅榜前 20 数据
async def get_rank_from_redis():
    try:
        gainers = await redis_client.zrevrange("market:top_gainers", 0, 9)
        losers = await redis_client.zrange("market:top_losers", 0, 9)

        keyboard = []
        gainers_details = []
        for symbol in gainers:
            symbol_str = symbol.decode()
            details = await redis_client.hgetall(f"market:top_gainers:{symbol_str}")
            details = {key.decode(): value.decode() for key, value in details.items()}
            gainers_details.append({"symbol": symbol_str, **details})
            keyboard.append([InlineKeyboardButton(f"More {symbol_str}", callback_data=f"more_{symbol_str}")])

        losers_details = []
        for symbol in losers:
            symbol_str = symbol.decode()
            details = await redis_client.hgetall(f"market:top_losers:{symbol_str}")
            details = {key.decode(): value.decode() for key, value in details.items()}
            losers_details.append({"symbol": symbol_str, **details})
            keyboard.append([InlineKeyboardButton(f"More {symbol_str}", callback_data=f"more_{symbol_str}")])

        # Format headers
        message = "📈 *Top 10 Gainers*\n\n"
        for item in gainers_details:
            message += f"`{item['symbol']:<12} {format_percent(item['change_percent']):>8}`\n"

        message += "\n📉 *Top 10 Losers*\n\n"
        for item in losers_details:
            message += f"`{item['symbol']:<12} {format_percent(item['change_percent']):>8}`\n"

        reply_markup = InlineKeyboardMarkup(keyboard)
        return message, reply_markup
    except Exception as e:
        logging.error(f"Failed to read data from Redis: {e}")
        return "An error occurred while fetching data.", None

# 处理 More 按钮点击
async def handle_more(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("more start...")
    query = update.callback_query
    await query.answer()

    symbol = query.data.split("_")[1]
    print(f"Handling more details for {symbol}...")
    try:
        # 从 Redis 获取详细信息
        details = await redis_client.hgetall(f"market:details:{symbol}")
        print(details)
        if not details:
            escaped_symbol = escape_markdown_v2(symbol)
            await query.edit_message_text(
                f"Details for `{escaped_symbol}` not found.", parse_mode="MarkdownV2"
            )
            return

        # 转换 Redis 数据
        details = {key.decode(): value.decode() for key, value in details.items()}
        print(details)
        message = (
            f"*Details for {escape_markdown_v2(symbol)}*\n"
            f"Latest Price: `{escape_markdown_v2(details['c'])}`\n"
            f"Change%: `{escape_markdown_v2(details['P'])}`\n"
            f"Volume: `{escape_markdown_v2(details.get('v', 'N/A'))}`\n"
        )

        # 编辑原消息
        await query.edit_message_text(message, parse_mode="MarkdownV2")
    except Exception as e:
        logging.error(f"Error handling more details for {symbol}: {e}")
        await query.edit_message_text(
            "An error occurred while fetching details. Please try again later.",
            parse_mode="MarkdownV2"
        )


def escape_markdown_v2(text: str) -> str:
    """
    Escapes special characters for Telegram MarkdownV2.
    """
    special_chars = r"_*[]()~`>#+-=|{}.!"
    for char in special_chars:
        text = text.replace(char, f"\\{char}")
    return text


# Telegram Bot 命令处理函数
async def rank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data, markup = await get_rank_from_redis()
    try:
        await update.message.reply_text(data, reply_markup=markup, parse_mode="MarkdownV2")
    except Exception as e:
        logging.error(f"Error sending rank message: {e}")
        await update.message.reply_text(f"Error sending message: {e}")

# 主函数
def main():
    # 全局异常处理
    def handle_uncaught_exceptions(loop, context):
        message = context.get("exception", context["message"])
        logging.error(f"Unhandled exception: {message}")

    loop = asyncio.get_event_loop()
    loop.set_exception_handler(handle_uncaught_exceptions)

    app = ApplicationBuilder().token("7175969511:AAF9JLQU6L27tyyBvajeHDv0sU14usUVwUE").build()
    app.add_handler(CommandHandler("rank", rank))
    app.add_handler(CallbackQueryHandler(handle_more, pattern="more_"))

    logging.info("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
