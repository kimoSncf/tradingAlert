from flask import Flask, render_template, jsonify
from flask_socketio import SocketIO
import ccxt
import pandas as pd
import pandas_ta as ta
import time
from datetime import datetime, timedelta
import threading
from collections import deque
import smtplib
from email.mime.text import MIMEText

# Configuration de l'application Flask
app = Flask(__name__)
socketio = SocketIO(app)

# Constantes
CRYPTOS = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'XRP/USDT', 'ADA/USDT', 'SOL/USDT', 'DOT/USDT']
TIMEFRAME = '5m'
ALERT_EMAIL = 'scripttradingtn@gmail.com'
ALERT_INTERVAL = 3600  # 1 heure entre les alertes

# Stockage des données
signals_cache = deque(maxlen=600)  # 10 minutes de données
last_alerts = {crypto: 0 for crypto in CRYPTOS}

# Configuration Binance
exchange = ccxt.binance({
    'apiKey': 'Q64QJuS4Ro048O5ucBqFCInkfxnhKCZMXXCQkJ',
    'secret': 'YV8KJyOm2DTA5LQr3lnBmbaP463ia5CoWgxSbA2EU6EyHfn',
    'enableRateLimit': True
})

def send_email_alert(crypto, message):
    """Envoie une alerte par email."""
    msg = MIMEText(message)
    msg['Subject'] = f'Alerte Achat: {crypto} - Conditions réunies'
    msg['From'] = ALERT_EMAIL
    msg['To'] = ALERT_EMAIL

    try:
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(ALERT_EMAIL, 'Karim321@')
            server.send_message(msg)
            print(f"Email envoyé pour {crypto}")
    except Exception as e:
        print(f"Erreur d'envoi d'email: {e}")

def calculate_indicators(df):
    """Calcule tous les indicateurs techniques."""
    closes = df['close']
    
    return {
        'ema6': ta.ema(closes, length=6),
        'ema12': ta.ema(closes, length=12),
        'ema20': ta.ema(closes, length=20),
        'rsi6': ta.rsi(closes, length=6),
        'rsi12': ta.rsi(closes, length=12),
        'rsi24': ta.rsi(closes, length=24)
    }

def check_conditions(indicators, current_price):
    """Vérifie toutes les conditions de trading."""
    ema_crossover = (
        indicators['ema6'].iloc[-1] > indicators['ema12'].iloc[-1] and
        indicators['ema6'].iloc[-2] < indicators['ema12'].iloc[-2] and
        indicators['ema12'].iloc[-1] > indicators['ema20'].iloc[-1]
    )

    price_above_ema = (
        current_price > indicators['ema6'].iloc[-1] and
        current_price > indicators['ema12'].iloc[-1] and
        current_price > indicators['ema20'].iloc[-1]
    )

    rsi_conditions = (
        30 <= indicators['rsi6'].iloc[-1] <= 40 and
        indicators['rsi6'].iloc[-2] < 30 and
        indicators['rsi12'].iloc[-1] > 50 and
        indicators['rsi12'].iloc[-2] <= 50 and
        indicators['rsi24'].iloc[-1] > 50
    )

    return bool(ema_crossover and price_above_ema and rsi_conditions)

@app.route('/')
def index():
    return render_template('index.html')

def analyze_crypto():
    """Fonction principale d'analyse des cryptomonnaies."""
    while True:
        try:
            current_time = datetime.now()
            unix_time = time.time()

            for pair in CRYPTOS:
                try:
                    # Récupération des données
                    ohlcv = exchange.fetch_ohlcv(pair, TIMEFRAME, limit=50)
                    if not ohlcv:
                        continue

                    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                    current_price = float(df['close'].iloc[-1])
                    
                    # Calcul des indicateurs
                    indicators = calculate_indicators(df)
                    
                    # Création du signal
                    signal = {
                        'pair': pair,
                        'timestamp': current_time.strftime('%Y-%m-%d %H:%M:%S'),
                        'price': current_price,
                        'ema6': float(indicators['ema6'].iloc[-1]),
                        'ema12': float(indicators['ema12'].iloc[-1]),
                        'ema20': float(indicators['ema20'].iloc[-1]),
                        'rsi6': float(indicators['rsi6'].iloc[-1]),
                        'rsi12': float(indicators['rsi12'].iloc[-1]),
                        'rsi24': float(indicators['rsi24'].iloc[-1]),
                        'volume': float(df['volume'].iloc[-1])
                    }
                    
                    # Vérification des conditions
                    signal['signal'] = check_conditions(indicators, current_price)

                    # Gestion des signaux et alertes
                    signals_cache.append(signal)
                    socketio.emit('update_data', signal)

                    if signal['signal'] and (unix_time - last_alerts[pair] >= ALERT_INTERVAL):
                        message = f"""
                        🚨 Toutes les conditions d'achat sont réunies pour {pair} 🚨
                        - EMA6 > EMA12 > EMA20
                        - Prix > EMA6/12/20
                        - RSI6: Survente -> 30-40
                        - RSI12 > 50 (croisement)
                        - RSI24 > 50
                        """
                        send_email_alert(pair, message)
                        last_alerts[pair] = unix_time

                except Exception as e:
                    print(f"Erreur pour {pair}: {e}")
                    continue

            # Nettoyage et pause
            cleanup_old_data()
            socketio.sleep(60)

        except Exception as e:
            print(f"Erreur générale: {e}")
            socketio.sleep(60)

def cleanup_old_data():
    """Nettoie les anciennes données du cache."""
    current_time = datetime.now()
    cutoff_time = current_time - timedelta(minutes=10)
    
    while signals_cache and datetime.strptime(signals_cache[0]['timestamp'], '%Y-%m-%d %H:%M:%S') < cutoff_time:
        signals_cache.popleft()

@socketio.on('connect')
def handle_connect():
    """Gère la connexion d'un nouveau client."""
    for signal in signals_cache:
        socketio.emit('update_data', signal)

if __name__ == '__main__':
    thread = threading.Thread(target=analyze_crypto)
    thread.daemon = True
    thread.start()
    
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)
