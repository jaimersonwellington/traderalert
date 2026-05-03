import os
import requests
import pandas as pd
import pandas_ta as ta
from binance.client import Client

# Configurações de Ambiente (Puxadas dos Secrets do GitHub)
api_key = os.getenv('BINANCE_KEY')
api_secret = os.getenv('BINANCE_SECRET')
token_telegram = os.getenv('TELEGRAM_TOKEN')
chat_id = os.getenv('CHAT_ID')

def enviar_telegram(mensagem):
    url = f"https://api.telegram.org/bot{token_telegram}/sendMessage"
    payload = {"chat_id": chat_id, "text": mensagem, "parse_mode": "Markdown"}
    requests.post(url, json=payload)

# 1. Conexão com a Binance
client = Client(api_key, api_secret)

# 2. Obter dados (Últimas 100 velas de 1 hora)
klines = client.get_historical_klines("BTCUSDT", Client.KLINE_INTERVAL_1HOUR, "100 hours ago UTC")
df = pd.DataFrame(klines, columns=['time', 'open', 'high', 'low', 'close', 'vol', 'close_time', 'qav', 'num_trades', 'taker_base', 'taker_quote', 'ignore'])
df['close'] = pd.to_numeric(df['close'])

# 3. Análise Técnica (RSI e Média Móvel de 20 períodos)
df['RSI'] = ta.rsi(df['close'], length=14)
df['EMA20'] = ta.ema(df['close'], length=20)

ultimo_fechamento = df['close'].iloc[-1]
ultimo_rsi = df['RSI'].iloc[-1]
ultima_ema = df['EMA20'].iloc[-1]

# 4. Lógica de Alerta (Exemplo: RSI abaixo de 30 ou Preço acima da Média)
status = "NEUTRO"
if ultimo_rsi < 35:
    status = "🚨 *SOBREVENDIDO (COMPRA)*"
elif ultimo_rsi > 65:
    status = "⚠️ *SOBRECOMPRADO (VENDA)*"

# Enviar alerta se houver algo relevante
mensagem_alerta = (
    f"📊 *Relatório BTC/USDT*\n\n"
    f"💰 Preço: ${ultimo_fechamento:,.2f}\n"
    f"📈 RSI: {ultimo_rsi:.2f}\n"
    f"📉 EMA20: ${ultima_ema:,.2f}\n\n"
    f"Sinal: {status}"
)

enviar_telegram(mensagem_alerta)
print("Análise executada e alerta enviado.")
