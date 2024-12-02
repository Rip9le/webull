from flask import Flask, render_template, request
import psycopg2
from config import DB_CONFIG

app = Flask(__name__)

def query_data(symbol):
    """
    查询指定时间段内的数据。
    """
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT symbol, price_change, price_change_percent, last_price,
               high_price, low_price, volume, quote_volume, data_time
        FROM ticker_data_full
        WHERE symbol = %s
        ORDER BY data_time, symbol
    """, (symbol,))

    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    return rows

@app.route('/', methods=['GET', 'POST'])
def index():
    """
    首页：查询数据。
    """
    data = []
    if request.method == 'POST':
        # start_time = request.form['start_time']
        # end_time = request.form['end_time']
        symbol = request.form['symbol']
        data = query_data(symbol.upper())

    return render_template('index.html', data=data)

if __name__ == '__main__':
    app.run(debug=True)

