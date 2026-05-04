import os
import requests
import pandas as pd

# 1. Configurações
token_telegram = os.getenv('TELEGRAM_TOKEN')
chat_id = os.getenv('CHAT_ID')

def enviar_telegram(mensagem):
    if not token_telegram or not chat_id: return
    url = f"https://api.telegram.org/bot{token_telegram}/sendMessage"
    payload = {"chat_id": chat_id, "text": mensagem, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload, timeout=10)
    except:
        pass

def calcular_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

try:
    # 2. Coleta de dados (Usando API pública para evitar bloqueio de região)
    url = "https://api1.binance.com/api/v3/klines"
    params = {"symbol": "BTCUSDT", "interval": "5m", "limit": "100"}
    
    response = requests.get(url, params=params, timeout=20)
    klines = response.json()

    # 3. Processamento
    df = pd.DataFrame(klines, columns=['time', 'open', 'high', 'low', 'close', 'vol', 'close_time', 'qav', 'num_trades', 'taker_base', 'taker_quote', 'ignore'])
    df['close'] = pd.to_numeric(df['close'])

    # 4. Indicadores
    df['RSI'] = calcular_rsi(df['close'])
    ultimo_p = df['close'].iloc[-1]
    ultimo_rsi = df['RSI'].iloc[-1]

    # 5. Mensagem
    status = "🔍 *NEUTRO*"
    if ultimo_rsi < 30: status = "🟢 *COMPRA (SOBREVENDIDO)*"
    elif ultimo_rsi > 70: status = "🔴 *VENDA (SOBRECOMPRADO)*"

    mensagem = (
        f"🤖 *BOT TRADER ALERT*\n\n"
        f"💰 *BTC:* `${ultimo_p:,.2f}`\n"
        f"📈 *RSI:* `{ultimo_rsi:.2f}`\n"
        f"⚡ *Sinal:* {status}"
    )

    enviar_telegram(mensagem)
    print("Sucesso! Alerta enviado.")

except Exception as e:
    print(f"Erro: {e}")
