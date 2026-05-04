import os
import requests
import pandas as pd
from binance.client import Client

# 1. Configurações de Ambiente
token_telegram = os.getenv('TELEGRAM_TOKEN')
chat_id = os.getenv('CHAT_ID')

def enviar_telegram(mensagem):
    if not token_telegram or not chat_id: return
    url = f"https://api.telegram.org/bot{token_telegram}/sendMessage"
    payload = {"chat_id": chat_id, "text": mensagem, "parse_mode": "Markdown"}
    try: requests.post(url, json=payload, timeout=10)
    except: pass

def calcular_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

# 2. Inicialização sem "Ping" para evitar bloqueio regional do GitHub
# Usamos o cliente apenas para estruturar a URL, mas pegamos dados públicos
client = Client("", "") # Não precisamos de chaves para ler dados públicos

try:
    print("Coletando dados públicos da Binance...")
    
    # Usando o endpoint direto da API REST via requests (mais resistente a bloqueios de biblioteca)
    url = "https://api.binance.com/api/v3/klines"
    params = {
        "symbol": "BTCUSDT",
        "interval": "5m",
        "limit": "100"
    }
    
    response = requests.get(url, params=params, timeout=20)
    if response.status_code != 200:
        # Se a principal falhar, tenta o endpoint alternativo (vision)
        url = "https://api1.binance.com/api/v3/klines"
        response = requests.get(url, params=params, timeout=20)

    klines = response.json()
    
    if not isinstance(klines, list):
        raise Exception(f"Erro na API: {response.text}")

    # 3. Processamento
    df = pd.DataFrame(klines, columns=['time', 'open', 'high', 'low', 'close', 'vol', 'close_time', 'qav', 'num_trades', 'taker_base', 'taker_quote', 'ignore'])
    df['close'] = pd.to_numeric(df['close'])

    # 4. Indicadores
    df['RSI'] = calcular_rsi(df['close'])
    df['EMA_9'] = df['close'].ewm(span=9, adjust=False).mean()
    df['EMA_21'] = df['close'].ewm(span=21, adjust=False).mean()

    ultimo_fechamento = df['close'].iloc[-1]
    ultimo_rsi = df['RSI'].iloc[-1]
    ema_r = df['EMA_9'].iloc[-1]
    ema_l = df['EMA_21'].iloc[-1]

    # 5. Lógica
    status = "🔍 *NEUTRO*"
    if ultimo_rsi < 30: status = "🚀 *SOBREVENDIDO (COMPRA)*"
    elif ultimo_rsi > 70: status = "⚠️ *SOBRECOMPRADO (VENDA)*"
    elif ema_r > ema_l: status = "📈 *TENDÊNCIA ALTA*"
    else: status = "📉 *TENDÊNCIA BAIXA*"

    mensagem = (
        f"📊 *BITCOIN REPORT (GitHub Cloud)*\n\n"
        f"💰 *Preço:* `${ultimo_fechamento:,.2f}`\n"
        f"📈 *RSI:* `{ultimo_rsi:.2f}`\n"
        f"⚡ *Sinal:* {status}"
    )

    enviar_telegram(mensagem)
    print("Sucesso! Mensagem enviada.")

except Exception as e:
    print(f"Erro: {e}")
    # Envia o erro pro telegram para você monitorar
    # enviar_telegram(f"❌ Erro de Localização/Conexão: {str(e)}")
