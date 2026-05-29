import ccxt
import pandas as pd
import pandas_ta as ta
import time

# ==========================================
# BORSAYA BAĞLANTI VE AYARLAR
# ==========================================
exchange = ccxt.binance({
    'apiKey': 'TESTNET_VEYA_GERCEK_API_KEY',
    'secret': 'TESTNET_VEYA_GERCEK_SECRET_KEY',
    'enableRateLimit': True,
})

# ÖNEMLİ: Gerçek parayla denemeden önce burayı True (Testnet) modunda bırakın.
exchange.set_sandbox_mode(True) 

SYMBOL = 'BTC/USDT'     # İşlem yapılacak çift
TIMEFRAME = '1m'        # Scalping için 1 dakikalık grafik
TRADE_AMOUNT = 0.001    # Her işlemde alınacak BTC miktarı
STOP_LOSS_PCT = 0.005   # %0.5 Zarar Kes (Fiyat aldığımız noktanın %0.5 altına düşerse stop ol)

# Pozisyon durumunu takip etmek için değişkenler
in_position = False
buy_price = 0.0

def get_signals():
    """Borsadan verileri çeker ve Bollinger / RSI indikatörlerini hesaplar"""
    try:
        # Son 100 mumu çek
        bars = exchange.fetch_ohlcv(SYMBOL, TIMEFRAME, limit=100)
        df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        # RSI Hesapla (Momentum için)
        df['RSI'] = ta.rsi(df['close'], length=14)
        
        # Bollinger Bantları (Dinamik Destek ve Direnç)
        bb = ta.bbands(df['close'], length=20, std=2)
        df['BB_lower'] = bb['BBL_20_2.0']  # ALT BANT = DESTEK
        df['BB_upper'] = bb['BBU_20_2.0']  # ÜST BANT = DİRENÇ
        
        return df.iloc[-1] # En güncel son satırı döndür
    except Exception as e:
        print(f"Veri çekme hatası: {e}")
        return None

# ==========================================
# ANA TİCARET DÖNGÜSÜ
# ==========================================
print(f"🚀 Binance Scalper Bot Başlatıldı ({SYMBOL} - {TIMEFRAME})")
if exchange.urls['api'] and 'testnet' in exchange.urls['api']:
    print("⚠️ DİKKAT: Bot şu anda TESTNET (Simülasyon) modunda çalışıyor.")

while True:
    data = get_signals()
    
    if data is not None:
        current_price = data['close']
        rsi = data['RSI']
        support = data['BB_lower']
        resistance = data['BB_upper']
        
        print(f"Fiyat: {current_price} | RSI: {rsi:.2f} | Destek (BB Alt): {support:.2f} | Direnç (BB Üst): {resistance:.2f}")
        
        # ----------------------------------------------------------
        # DURUM 1: POZİSYONDA DEĞİLİZ - ALIM SİNYALİ ARIYORUZ
        # ----------------------------------------------------------
        if not in_position:
            # ŞARTLAR: Fiyat desteğe değdi/altına indi VE RSI aşırı satımda (Momentum dönüyor)
            if current_price <= support and rsi < 35:
                print("\n🟢 ALIM SİNYALİ! Destek bölgesinde yüksek momentum tespit edildi.")
                try:
                    # Komisyon avantajı için LIMIT emir gönderiyoruz
                    order = exchange.create_limit_buy_order(SYMBOL, TRADE_AMOUNT, current_price)
                    print(f"Alım Emri Girildi. Fiyat: {current_price}, Miktar: {TRADE_AMOUNT}")
                    
                    buy_price = current_price
                    in_position = True
                except Exception as e:
                    print(f"Alım emri gönderilirken hata oluştu: {e}")
                    
        # ----------------------------------------------------------
        # DURUM 2: POZİSYONDAYIZ - SATIM VEYA STOP-LOSS ARIYORUZ
        # ----------------------------------------------------------
        else:
            stop_loss_level = buy_price * (1 - STOP_LOSS_PCT)
            print(f"-> Pozisyondayız. Alış: {buy_price} | Stop Seviyesi: {stop_loss_level:.2f}")
            
            # ŞART A: ZARAR KES (STOP LOSS) TETİKLENDİ Mİ?
            if current_price <= stop_loss_level:
                print("\n🔴 STOP LOSS! Piyasa terse döndü, zarar kesiliyor...")
                try:
                    order = exchange.create_market_sell_order(SYMBOL, TRADE_AMOUNT)
                    print("Zarar kes emri başarıyla uygulandı.")
                    in_position = False
                except Exception as e:
                    print(f"Stop emri gönderilirken hata oluştu: {e}")
            
            # ŞART B: DİRENÇTE HEDEFE ULAŞTIK MI? (KAR AL)
            elif current_price >= resistance or rsi > 65:
                print("\n🎯 KAR AL SİNYALİ! Fiyat dirence ulaştı.")
                try:
                    order = exchange.create_limit_sell_order(SYMBOL, TRADE_AMOUNT, current_price)
                    print(f"Satış Emri Girildi. Fiyat: {current_price}")
                    in_position = False
                except Exception as e:
                    print(f"Satış emri gönderilirken hata oluştu: {e}")

    # Scalping için döngü sıklığı (10 saniyede bir kontrol eder)
    time.sleep(10)
  
