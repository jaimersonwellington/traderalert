import os
import requests
import pandas as pd
from binance.client import Client

# 1. Configurações de Ambiente
api_key = os.getenv('BINANCE_KEY')
api_secret = os.getenv('BINANCE_SECRET')
token_telegram = os.getenv('TELEGRAM_TOKEN')
chat_id = os.getenv('CHAT_ID')

def enviar_telegram(mensagem):
    if not token_telegram or not chat_id: return
    url = f"https://api.telegram.org/bot{token_telegram}/sendMessage"
    payload = {"chat_id": chat_id, "text": mensagem, "parse_mode": "Markdown"}
    try: requests.post(url, json=payload, timeout=10)
    except: pass

def calcular_rsi(series, period=14):
    """Calcula o RSI manualmente sem bibliotecas externas"""
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

# 2. Inicialização
client = Client(api_key, api_secret)

try:
    print("Iniciando análise...")
    # 3. Coleta de dados
    klines = client.get_historical_klines("BTCUSDT", Client.KLINE_INTERVAL_5MINUTE, "12 hours ago UTC")
    df = pd.DataFrame(klines, columns=['time', 'open', 'high', 'low', 'close', 'vol', 'close_time', 'qav', 'num_trades', 'taker_base', 'taker_quote', 'ignore'])
    df['close'] = pd.to_numeric(df['close'])

    # 4. Cálculo dos Indicadores (Nativo)
    df['RSI'] = calcular_rsi(df['close'])
    df['EMA_9'] = df['close'].ewm(span=9, adjust=False).mean()
    df['EMA_21'] = df['close'].ewm(span=21, adjust=False).mean()

    ultimo_fechamento = df['close'].iloc[-1]
    ultimo_rsi = df['RSI'].iloc[-1]
    ema_r = df['EMA_9'].iloc[-1]
    ema_l = df['EMA_21'].iloc[-1]

    # 5. Lógica de Sinal
    status = "🔍 *AGUARDANDO*"
    if ultimo_rsi < 30: status = "🚀 *SOBREVENDIDO (COMPRA)*"
    elif ultimo_rsi > 70: status = "⚠️ *SOBRECOMPRADO (VENDA)*"
    elif ema_r > ema_l: status = "📈 *TENDÊNCIA DE ALTA*"
    else: status = "📉 *TENDÊNCIA DE BAIXA*"

    mensagem = (
        f"📊 *RELATÓRIO BTC/USDT (5m)*\n\n"
        f"💰 *Preço:* `${ultimo_fechamento:,.2f}`\n"
        f"📈 *RSI:* `{ultimo_rsi:.2f}`\n"
        f"⚡ *Sinal:* {status}"
    )

    enviar_telegram(mensagem)
    print("Sucesso!")

except Exception as e:
    print(f"Erro: {e}")
    enviar_telegram(f"❌ Erro no bot: {str(e)}")
