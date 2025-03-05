from flask import Flask, render_template, jsonify
from flask_socketio import SocketIO
import json
from datetime import datetime, timedelta
import threading
from collections import deque
import ccxt
import pandas as pd
import pandas_ta as ta

app = Flask(__name__)
socketio = SocketIO(app)

# Cache pour stocker les données (10 minutes)
signals_cache = deque(maxlen=600)  # 600 secondes = 10 minutes
pairs_data = {}

# Configuration Binance
exchange = ccxt.binance({
    'apiKey': 'Q64QJuS4Ro048O5ucBqFCInFvzDsI3nhKCZMXXCQkJ',
    'secret': 'YV8KJyOm2DTA5rmbaP463ia5CoWgxSbA2EU6EyHfn',
    'enableRateLimit': True
})

@app.route('/')
def index():
    return render_template('/index.html')

def analyze_crypto():
    while True:
        try:
            pairs = [p for p in exchange.load_markets().keys() if p.endswith('/USDT')]
            current_time = datetime.now()

            for pair in pairs:
                ohlcv = exchange.fetch_ohlcv(pair, '5m', limit=50)
                if not ohlcv:
                    continue

                df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                
                # Calcul des EMA
                ema6 = ta.ema(df['close'], length=6)
                ema12 = ta.ema(df['close'], length=12)
                ema20 = ta.ema(df['close'], length=20)

                if len(ema6) > 1 and len(ema12) > 1:
                    signal = {
                        'pair': pair,
                        'timestamp': current_time.strftime('%Y-%m-%d %H:%M:%S'),
                        'price': float(df['close'].iloc[-1]),  # Convertir en float standard
                        'ema6': float(ema6.iloc[-1]),         # Convertir en float standard
                        'ema12': float(ema12.iloc[-1]),       # Convertir en float standard
                        'ema20': float(ema20.iloc[-1]),       # Convertir en float standard
                        'volume': float(df['volume'].iloc[-1]),# Convertir en float standard
                        'signal': bool((ema6.iloc[-1] > ema12.iloc[-1] and  # Convertir en bool standard
                                     ema6.iloc[-2] < ema12.iloc[-2] and 
                                     ema12.iloc[-1] > ema20.iloc[-1]))
                    }

                    signals_cache.append(signal)
                    socketio.emit('update_data', signal)

            # Nettoyage des anciennes données
            cleanup_old_data()
            socketio.sleep(60)  # Mise à jour toutes les minutes

        except Exception as e:
            print(f"Erreur: {e}")
            socketio.sleep(60)

def cleanup_old_data():
    current_time = datetime.now()
    cutoff_time = current_time - timedelta(minutes=10)
    
    while signals_cache and datetime.strptime(signals_cache[0]['timestamp'], '%Y-%m-%d %H:%M:%S') < cutoff_time:
        signals_cache.popleft()

@socketio.on('connect')
def handle_connect():
    # Envoyer les données en cache au nouveau client
    for signal in signals_cache:
        socketio.emit('update_data', signal)

if __name__ == '__main__':
    # Démarrer l'analyse en arrière-plan
    thread = threading.Thread(target=analyze_crypto)
    thread.daemon = True
    thread.start()
    
    # Démarrer le serveur Flask
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)
