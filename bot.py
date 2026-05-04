import os
import requests
import pandas as pd
import numpy as np

# 1. Configurações de Ambiente
token_telegram = os.getenv('TELEGRAM_TOKEN')
chat_id = os.getenv('CHAT_ID')

def enviar_telegram(mensagem):
    if not token_telegram or not chat_id: return
    url = f"https://api.telegram.org/bot{token_telegram}/sendMessage"
    payload = {"chat_id": chat_id, "text": mensagem, "parse_mode": "Markdown"}
    try: requests.post(url, json=payload, timeout=10)
    except: pass

def obter_dados(symbol, interval, limit=300):
    endpoints = [
        "https://api.binance.us/api/v3/klines",
        "https://data-api.binance.vision/api/v3/klines",
        "https://api1.binance.com/api/v3/klines"
    ]
    for url in endpoints:
        try:
            params = {"symbol": symbol, "interval": interval, "limit": limit}
            res = requests.get(url, params=params, timeout=10)
            if res.status_code == 200:
                df = pd.DataFrame(res.json(), columns=['time', 'open', 'high', 'low', 'close', 'vol', 'close_time', 'qav', 'num_trades', 'taker_base', 'taker_quote', 'ignore'])
                df[['open', 'high', 'low', 'close', 'vol']] = df[['open', 'high', 'low', 'close', 'vol']].apply(pd.to_numeric)
                return df
        except: continue
    return None

def calcular_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

try:
    print("🚀 Iniciando Análise de Confluência Avançada...")
    
    # Coleta de dados (300 candles para garantir médias longas)
    df_5m = obter_dados("BTCUSDT", "5m", 300)
    df_60m = obter_dados("BTCUSDT", "1h", 100)

    if df_5m is None or df_60m is None:
        raise Exception("Erro ao obter dados da API.")

    # --- INDICADORES 60 MINUTOS (MACRO) ---
    # Topos e Fundos (Usando os últimos 20 candles de 1h como referência de região)
    resistencia_60m = df_60m['high'].rolling(window=20).max().iloc[-1]
    suporte_60m = df_60m['low'].rolling(window=20).min().iloc[-1]
    ma20_60m = df_60m['close'].rolling(window=20).mean().iloc[-1]
    tendencia_alta_60m = df_60m['close'].iloc[-1] > ma20_60m

    # --- INDICADORES 5 MINUTOS (EXECUÇÃO) ---
    # Médias Móveis
    ema9 = df_5m['close'].ewm(span=9, adjust=False).mean()
    ema21 = df_5m['close'].ewm(span=21, adjust=False).mean()
    ma200 = df_5m['close'].rolling(window=200).mean()
    
    # RSI e Volume
    rsi = calcular_rsi(df_5m['close'])
    vol_media = df_5m['vol'].rolling(window=20).mean()
    
    # Valores atuais para lógica de gatilho
    c = df_5m['close'].iloc[-1]
    l = df_5m['low'].iloc[-1]
    h = df_5m['high'].iloc[-1]
    v = df_5m['vol'].iloc[-1]
    m200_atual = ma200.iloc[-1]
    
    # --- LÓGICA DE CONFLUÊNCIA ---

    # 1. Verificação de Proximidade/Toque na MA200 (Margem de 0.05% para garantir detecção)
    perto_m200 = abs(c - m200_atual) / m200_atual < 0.0005
    toca_m200 = l <= m200_atual <= h
    
    # 2. Cruzamento de Médias 9/21 (Detecta a virada no candle atual ou anterior)
    cruzamento_alta = (ema9.iloc[-1] > ema21.iloc[-1]) and (ema9.iloc[-2] <= ema21.iloc[-2])
    cruzamento_baixa = (ema9.iloc[-1] < ema21.iloc[-1]) and (ema9.iloc[-2] >= ema21.iloc[-2])

    # 3. Filtro de Volume (Volume acima da média)
    volume_ok = v > vol_media.iloc[-1]

    # --- DISPARO DE ALERTAS ---

    # CONDIÇÃO COMPRA: 
    # Toque/Perto da MA200 (5m) + Cruzamento 9/21 (5m) + Acima do Suporte (60m) + Tendência 60m Alta + Volume
    if (toca_m200 or perto_m200) and cruzamento_alta and v > suporte_60m and tendencia_alta_60m and volume_ok:
        msg = (
            "✅ **SINAL DE COMPRA: CONFLUÊNCIA TOTAL** 🚀\n"
            "🎯 *Entrada:* Abertura do próximo candle\n\n"
            f"💰 Preço Atual: `${c:,.2f}`\n"
            f"📏 MA200 (5m): `${m200_atual:,.2f}`\n"
            f"📊 RSI (5m): `{rsi.iloc[-1]:.2f}`\n"
            f"🏗️ Macro (60m): Acima da MA20 e Suporte\n"
            f"🔥 Volume: Confirmado (Acima da média)"
        )
        enviar_telegram(msg)
        print("Sinal de Compra enviado!")

    # CONDIÇÃO VENDA:
    # Toque/Perto da MA200 (5m) + Cruzamento 9/21 (5m) + Abaixo da Resistência (60m) + Tendência 60m Baixa + Volume
    elif (toca_m200 or perto_m200) and cruzamento_baixa and v < resistencia_60m and not tendencia_alta_60m and volume_ok:
        msg = (
            "🔴 **SINAL DE VENDA: CONFLUÊNCIA TOTAL** 🔴\n"
            "🎯 *Entrada:* Abertura do próximo candle\n\n"
            f"💰 Preço Atual: `${c:,.2f}`\n"
            f"📏 MA200 (5m): `${m200_atual:,.2f}`\n"
            f"📊 RSI (5m): `{rsi.iloc[-1]:.2f}`\n"
            f"🏗️ Macro (60m): Abaixo da MA20 e Resistência\n"
            f"🔥 Volume: Confirmado (Acima da média)"
        )
        enviar_telegram(msg)
        print("Sinal de Venda enviado!")

    else:
        print(f"Monitorando... P:{c:.2f} | MA200:{m200_atual:.2f} | RSI:{rsi.iloc[-1]:.2f}")

except Exception as e:
    print(f"❌ Erro na execução: {e}")
