import os
import requests
import pandas as pd
import pandas_ta as ta
from binance.client import Client

# 1. Configurações de Ambiente (Puxadas dos Secrets do GitHub via main.yml)
api_key = os.getenv('BINANCE_KEY')
api_secret = os.getenv('BINANCE_SECRET')
token_telegram = os.getenv('TELEGRAM_TOKEN')
chat_id = os.getenv('CHAT_ID')

def enviar_telegram(mensagem):
    """Função para enviar alertas para o Telegram"""
    if not token_telegram or not chat_id:
        print("Erro: TELEGRAM_TOKEN ou CHAT_ID não configurados.")
        return
    
    url = f"https://api.telegram.org/bot{token_telegram}/sendMessage"
    payload = {
        "chat_id": chat_id, 
        "text": mensagem, 
        "parse_mode": "Markdown"
    }
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
    except Exception as e:
        print(f"Erro ao enviar Telegram: {e}")

# 2. Inicialização do Cliente Binance
client = Client(api_key, api_secret)

try:
    print("Iniciando análise técnica...")
    
    # 3. Obter dados (Últimas 100 velas de 5 minutos)
    klines = client.get_historical_klines("BTCUSDT", Client.KLINE_INTERVAL_5MINUTE, "12 hours ago UTC")
    
    if not klines:
        print("Erro: Não foi possível obter dados da Binance.")
        exit(1)

    # 4. Organização dos dados em um DataFrame
    df = pd.DataFrame(klines, columns=['time', 'open', 'high', 'low', 'close', 'vol', 'close_time', 'qav', 'num_trades', 'taker_base', 'taker_quote', 'ignore'])
    
    # Convertendo colunas essenciais para números
    df['close'] = pd.to_numeric(df['close'])
    df['high'] = pd.to_numeric(df['high'])
    df['low'] = pd.to_numeric(df['low'])

    # 5. Cálculo dos Indicadores Técnicos usando a extensão pandas_ta
    # Calculando RSI (14)
    df['RSI'] = df.ta.rsi(close='close', length=14)
    
    # Calculando Médias Móveis Exponenciais (EMA)
    df['EMA_RAPIDA'] = df.ta.ema(close='close', length=9)
    df['EMA_LENTA'] = df.ta.ema(close='close', length=21)

    # Pegando os valores da última linha (candle atual/recente)
    ultimo_fechamento = df['close'].iloc[-1]
    ultimo_rsi = df['RSI'].iloc[-1]
    ema_r = df['EMA_RAPIDA'].iloc[-1]
    ema_l = df['EMA_LENTA'].iloc[-1]

    # 6. Lógica de Interpretação
    status = "🔍 *AGUARDANDO*"
    cor_emoji = "⚪"

    # Se o RSI for menor que 30, está sobrevendido (oportunidade de compra)
    if ultimo_rsi < 30:
        status = "🚀 *OPORTUNIDADE: SOBREVENDIDO (COMPRA)*"
        cor_emoji = "🟢"
    # Se o RSI for maior que 70, está sobrecomprado (risco de queda)
    elif ultimo_rsi > 70:
        status = "⚠️ *ATENÇÃO: SOBRECOMPRADO (VENDA)*"
        cor_emoji = "🔴"
    # Cruzamento de Médias para tendência
    elif ema_r > ema_l:
        status = "📈 *TENDÊNCIA DE ALTA (BULLISH)*"
        cor_emoji = "🔹"
    else:
        status = "📉 *TENDÊNCIA DE BAIXA (BEARISH)*"
        cor_emoji = "🔸"

    # 7. Montagem e envio da mensagem
    mensagem_final = (
        f"{cor_emoji} *RELATÓRIO BTC/USDT (5m)*\n\n"
        f"💰 *Preço Atual:* `${ultimo_fechamento:,.2f}`\n"
        f"📊 *RSI (14):* `{ultimo_rsi:.2f}`\n"
        f"📉 *EMA (9/21):* `{ema_r:.2f}` / `{ema_l:.2f}`\n\n"
        f"⚡ *Sinal:* {status}\n\n"
        f"🕒 _Próxima verificação em 5 minutos._"
    )

    enviar_telegram(mensagem_final)
    print("Análise concluída e alerta enviado para o Telegram.")

except Exception as e:
    erro_msg = f"❌ *Erro no Bot de Trading*:\n`{str(e)}`"
    enviar_telegram(erro_msg)
    print(f"Erro detectado: {e}")
