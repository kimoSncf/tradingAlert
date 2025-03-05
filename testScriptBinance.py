import ccxt
import pandas as pd
from datetime import datetime

def test_api_binance():
    print("🔍 Test de connexion à l'API Binance...")
    
    # Configuration de l'API
    exchange = ccxt.binance({
        'apiKey': 'Q64QJuS4Ro048O5ucBqFCInkfxn8QaGJzkKZD7O8b3g2UFvzDsI3nhKCZMXXCQkJ',
        'secret': 'YV8KJyOm2DTA5rUmVlVl7inmLwmd3uLQr3lnBmbaP463ia5CoWgxSbA2EU6EyHfn',
    })

    try:
        # Test 1: Vérification de la connexion
        print("\n✨ Test 1: Vérification de la connexion au serveur")
        exchange.load_markets()
        print("✅ Connexion réussie!")

        # Test 2: Récupération du prix actuel de BTC/USDT
        print("\n✨ Test 2: Prix actuel de BTC/USDT")
        ticker = exchange.fetch_ticker('BTC/USDT')
        print(f"✅ Prix BTC/USDT: {ticker['last']} USDT")

        # Test 3: Récupération des dernières bougies
        print("\n✨ Test 3: Dernières bougies BTC/USDT (5m)")
        ohlcv = exchange.fetch_ohlcv('BTC/USDT', '5m', limit=5)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        print("\nDernières bougies:")
        print(df)

        # Test 4: Récupération du carnet d'ordres
        print("\n✨ Test 4: Carnet d'ordres BTC/USDT")
        orderbook = exchange.fetch_order_book('BTC/USDT', limit=5)
        print("\nMeilleurs prix d'achat:")
        for price, volume in orderbook['bids'][:3]:
            print(f"Prix: {price}, Volume: {volume}")
        print("\nMeilleurs prix de vente:")
        for price, volume in orderbook['asks'][:3]:
            print(f"Prix: {price}, Volume: {volume}")

        print("\n✅ Tous les tests ont réussi!")

    except Exception as e:
        print(f"\n❌ Erreur lors du test: {str(e)}")

if __name__ == "__main__":
    test_api_binance()