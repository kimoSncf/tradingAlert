import ccxt
import pandas as pd
import pandas_ta as ta
import time
import smtplib
from email.mime.text import MIMEText
from datetime import datetime

# Configuration
EMAIL_FROM = "scripttradingtn@gmail.com"
EMAIL_TO = "karim.dev59@gmail.com"
EMAIL_PASSWORD = "Karim321@"  # Mot de passe d'application Google
TIMEFRAME = '5m'
CHECK_INTERVAL = 60  # Intervalle de vérification en secondes
ALERT_COOLDOWN = 3600  # Délai minimum entre deux alertes pour une même paire

def get_all_usdt_pairs(exchange):
    """Récupère toutes les paires USDT disponibles"""
    try:
        markets = exchange.load_markets()
        usdt_pairs = [symbol for symbol in markets.keys() if symbol.endswith('/USDT')]
        return sorted(usdt_pairs)
    except Exception as e:
        print(f"❌ Erreur lors de la récupération des paires: {e}")
        return []

def calculate_indicators(closes):
    """Calcule les indicateurs techniques"""
    return {
        'ema6': ta.ema(closes, length=6),
        'ema12': ta.ema(closes, length=12),
        'ema20': ta.ema(closes, length=20)
    }

def check_ema_crossover(indicators):
    """Vérifie les conditions de croisement des EMA"""
    ema6, ema12, ema20 = indicators['ema6'], indicators['ema12'], indicators['ema20']
    
    if len(ema6) < 2 or len(ema12) < 2:
        return False
        
    return (ema6.iloc[-1] > ema12.iloc[-1] and
            ema6.iloc[-2] < ema12.iloc[-2] and
            ema12.iloc[-1] > ema20.iloc[-1])

def send_email_alert(pair, ema_values):
    """Envoie une alerte par email"""
    try:
        message = f"""
        🚨 Signal de trading détecté!

        Paire: {pair}
        Heure: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

        Indicateurs:
        - EMA6: {ema_values['ema6']:.2f}
        - EMA12: {ema_values['ema12']:.2f}
        - EMA20: {ema_values['ema20']:.2f}

        ⚡ Croisement EMA6 et EMA12 confirmé
        📈 EMA12 au-dessus de EMA20
        """

        msg = MIMEText(message)
        msg['Subject'] = f'Signal Trading - {pair}'
        msg['From'] = EMAIL_FROM
        msg['To'] = EMAIL_TO

        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(EMAIL_FROM, EMAIL_PASSWORD)
            server.send_message(msg)
            print(f"✅ Email envoyé pour {pair}")
            return True
    except Exception as e:
        print(f"❌ Erreur envoi email pour {pair}: {e}")
        return False

def analyze_pair(exchange, pair, last_signals):
    """Analyse une paire de trading"""
    try:
        # Vérifier le délai depuis la dernière alerte
        if time.time() - last_signals.get(pair, 0) < ALERT_COOLDOWN:
            return False

        # Récupération des données
        ohlcv = exchange.fetch_ohlcv(pair, TIMEFRAME, limit=50)
        if not ohlcv:
            return False

        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        indicators = calculate_indicators(df['close'])
        
        if check_ema_crossover(indicators):
            print(f"\n🚨 SIGNAL DÉTECTÉ pour {pair}")
            ema_values = {
                'ema6': indicators['ema6'].iloc[-1],
                'ema12': indicators['ema12'].iloc[-1],
                'ema20': indicators['ema20'].iloc[-1]
            }
            if send_email_alert(pair, ema_values):
                return True
    except Exception as e:
        print(f"❌ Erreur analyse {pair}: {e}")
    return False

def main():
    print("🔍 Démarrage de la surveillance des croisements EMA...")
    
    exchange = ccxt.binance({
        'apiKey': 'Q64QJuS4Ro048O5ucBqFCInkfxn8QaGJzkKZD7O8b3g2UFvzDsI3nhKCZMXXCQkJ',
        'secret': 'YV8KJyOm2DTA5rUmVlVl7inmLwmd3uLQr3lnBmbaP463ia5CoWgxSbA2EU6EyHfn',
        'enableRateLimit': True
    })

    last_signals = {}
    
    while True:
        try:
            current_time = datetime.now().strftime("%H:%M:%S")
            print(f"\n⏰ Vérification à {current_time}")
            
            pairs = get_all_usdt_pairs(exchange)
            print(f"📊 Surveillance de {len(pairs)} paires")

            for pair in pairs:
                if analyze_pair(exchange, pair, last_signals):
                    last_signals[pair] = time.time()

            print(f"\n💤 Attente de {CHECK_INTERVAL} secondes...")
            time.sleep(CHECK_INTERVAL)

        except KeyboardInterrupt:
            print("\n👋 Arrêt du programme par l'utilisateur")
            break
        except Exception as e:
            print(f"\n❌ Erreur générale: {e}")
            time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()