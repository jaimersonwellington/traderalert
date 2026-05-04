import os
import requests
import pandas as pd

# 1. Configurações vindas do main.yml
token_telegram = os.getenv('TELEGRAM_TOKEN')
chat_id = os.getenv('CHAT_ID')

def enviar_telegram(mensagem):
    """Envia mensagem e mostra no log do GitHub se deu certo ou errado"""
    if not token_telegram or not chat_id:
        print("❌ Erro: Variáveis do Telegram não encontradas!")
        return
    
    url = f"https://api.telegram.org/bot{token_telegram}/sendMessage"
    payload = {"chat_id": chat_id, "text": mensagem, "parse_mode": "Markdown"}
    
    try:
        response = requests.post(url, json=payload, timeout=15)
        if response.status_code == 200:
            print("✅ Sucesso: Mensagem enviada ao Telegram.")
        else:
            print(f"❌ Erro Telegram: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Erro de conexão: {e}")

def calcular_rsi(series, period=14):
    """Cálculo manual do RSI para evitar erros de biblioteca"""
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

# Lista de servidores da Binance (sistema de backup)
endpoints = [
    "https://api.binance.us/api/v3/klines",
    "https://data-api.binance.vision/api/v3/klines",
    "https://api1.binance.com/api/v3/klines"
]

try:
    print("🌐 Iniciando coleta de dados...")
    klines = None
    for url in endpoints:
        try:
            params = {"symbol": "BTCUSDT", "interval": "5m", "limit": "100"}
            res = requests.get(url, params=params, timeout=10)
            if res.status_code == 200:
                klines = res.json()
                print(f"🔗 Conectado via: {url}")
                break
        except:
            continue

    if klines is None:
        raise Exception("Não foi possível conectar a nenhum servidor da Binance.")

    # 2. Processamento
    df = pd.DataFrame(klines, columns=['time', 'open', 'high', 'low', 'close', 'vol', 'close_time', 'qav', 'num_trades', 'taker_base', 'taker_quote', 'ignore'])
    df['close'] = pd.to_numeric(df['close'])

    # 3. Indicadores
    df['RSI'] = calcular_rsi(df['close'])
    df['EMA_9'] = df['close'].ewm(span=9, adjust=False).mean()
    df['EMA_21'] = df['close'].ewm(span=21, adjust=False).mean()

    ultimo_p = df['close'].iloc[-1]
    ultimo_rsi = df['RSI'].iloc[-1]
    ema_r = df['EMA_9'].iloc[-1]
    ema_l = df['EMA_21'].iloc[-1]

    # 4. Estratégia de Sinal
    status = "🔍 *NEUTRO*"
    cor = "⚪"
    
    if ultimo_rsi < 30:
        status = "🚀 *COMPRA (SOBREVENDIDO)*"
        cor = "🟢"
    elif ultimo_rsi > 70:
        status = "⚠️ *VENDA (SOBRECOMPRADO)*"
        cor = "🔴"
    elif ema_r > ema_l:
        status = "📈 *TENDÊNCIA DE ALTA*"
        cor = "🔹"
    else:
        status = "📉 *TENDÊNCIA DE BAIXA*"
        cor = "🔸"

    # 5. Mensagem Final
    mensagem = (
        f"{cor} *RELATÓRIO BTC/USDT (5m)*\n\n"
        f"💰 *Preço:* `${ultimo_p:,.2f}`\n"
        f"📊 *RSI (14):* `{ultimo_rsi:.2f}`\n"
        f"⚡ *Sinal:* {status}\n\n"
        f"🕒 _Próxima verificação em 5 min._"
    )

    enviar_telegram(mensagem)

except Exception as e:
    print(f"❌ Erro fatal: {e}")
    enviar_telegram(f"⚠️ *Erro no Bot:* {str(e)}")
