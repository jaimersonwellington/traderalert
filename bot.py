import os
import requests
import pandas as pd

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

# 2. Lista de Endpoints para contornar o Erro 451
# Se o primeiro der erro de região, o bot tenta os próximos da lista
endpoints = [
    "https://api.binance.us/api/v3/klines",   # Focado em servidores nos EUA
    "https://api.binance.com/api/v3/klines",  # Internacional
    "https://data-api.binance.vision/api/v3/klines", # Dados públicos (mais resistente)
    "https://api2.binance.com/api/v3/klines"  # Backup
]

klines = None
print("Iniciando busca de dados...")

for url in endpoints:
    try:
        print(f"Tentando conexão com: {url}")
        params = {"symbol": "BTCUSDT", "interval": "5m", "limit": "100"}
        response = requests.get(url, params=params, timeout=15)
        
        if response.status_code == 200:
            klines = response.json()
            print(f"✅ Conectado com sucesso via: {url}")
            break
        else:
            print(f"⚠️ Erro {response.status_code} em {url}")
    except Exception as e:
        print(f"❌ Falha de conexão em {url}: {e}")

try:
    if klines is None:
        raise Exception("Todos os endpoints da Binance falharam devido a restrições geográficas.")

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
        f"🤖 *BOT TRADER (Multi-Region)*\n\n"
        f"💰 *BTC:* `${ultimo_p:,.2f}`\n"
        f"📈 *RSI:* `{ultimo_rsi:.2f}`\n"
        f"⚡ *Sinal:* {status}"
    )

    enviar_telegram(mensagem)
    print("Sucesso! Relatório enviado.")

except Exception as e:
    erro_final = f"❌ *Erro de Localização*: A Binance bloqueou todos os servidores de nuvem testados.\n`{str(e)}`"
    print(erro_final)
    enviar_telegram(erro_final)
