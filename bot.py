import os
import requests
import pandas as pd

# 1. Configurações de Ambiente (Secrets do GitHub)
token_telegram = os.getenv('TELEGRAM_TOKEN')
chat_id = os.getenv('CHAT_ID')

def enviar_telegram(mensagem):
    """Função para enviar alertas com log de erro detalhado"""
    if not token_telegram or not chat_id:
        print("❌ ERRO: Variáveis TELEGRAM_TOKEN ou CHAT_ID não encontradas!")
        print(f"Token presente: {'Sim' if token_telegram else 'Não'}")
        print(f"Chat ID presente: {'Sim' if chat_id else 'Não'}")
        return
    
    url = f"https://api.telegram.org/bot{token_telegram}/sendMessage"
    payload = {
        "chat_id": chat_id, 
        "text": mensagem, 
        "parse_mode": "Markdown"
    }
    
    try:
        response = requests.post(url, json=payload, timeout=15)
        if response.status_code == 200:
            print("✅ Mensagem enviada com sucesso para o Telegram!")
        else:
            print(f"❌ Erro do Telegram: {response.status_code} - {response.text}")
            print("DICA: Verifique se você já deu /start no seu bot e se o CHAT_ID está correto.")
    except Exception as e:
        print(f"❌ Erro de conexão ao tentar enviar para o Telegram: {e}")

def calcular_rsi(series, period=14):
    """Cálculo matemático nativo do RSI"""
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

try:
    print("🌐 Coletando dados públicos da Binance...")
    
    # Endpoint público que não bloqueia o GitHub
    url = "https://api1.binance.com/api/v3/klines"
    params = {"symbol": "BTCUSDT", "interval": "5m", "limit": "100"}
    
    response = requests.get(url, params=params, timeout=20)
    response.raise_for_status()
    klines = response.json()

    # 2. Processamento dos Dados
    df = pd.DataFrame(klines, columns=['time', 'open', 'high', 'low', 'close', 'vol', 'close_time', 'qav', 'num_trades', 'taker_base', 'taker_quote', 'ignore'])
    df['close'] = pd.to_numeric(df['close'])

    # 3. Cálculo dos Indicadores
    df['RSI'] = calcular_rsi(df['close'])
    df['EMA_9'] = df['close'].ewm(span=9, adjust=False).mean()
    df['EMA_21'] = df['close'].ewm(span=21, adjust=False).mean()

    ultimo_p = df['close'].iloc[-1]
    ultimo_rsi = df['RSI'].iloc[-1]
    ema_r = df['EMA_9'].iloc[-1]
    ema_l = df['EMA_21'].iloc[-1]

    # 4. Lógica de Sinal
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

    # 5. Formatação da Mensagem
    mensagem = (
        f"{cor} *RELATÓRIO BTC/USDT (5m)*\n\n"
        f"💰 *Preço:* `${ultimo_p:,.2f}`\n"
        f"📊 *RSI (14):* `{ultimo_rsi:.2f}`\n"
        f"⚡ *Sinal:* {status}\n\n"
        f"🕒 _Atualizado via GitHub Actions_"
    )

    print(f"📊 Análise concluída: Preço {ultimo_p} / RSI {ultimo_rsi:.2f}")
    enviar_telegram(mensagem)

except Exception as e:
    erro_msg = f"❌ *Erro Crítico no Bot*:\n`{str(e)}`"
    print(erro_msg)
    enviar_telegram(erro_msg)
