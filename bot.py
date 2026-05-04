import os
import requests
import pandas as pd
import numpy as np

# 1. Configurações e Funções Base
token_telegram = os.getenv('TELEGRAM_TOKEN')
chat_id = os.getenv('CHAT_ID')

def enviar_telegram(mensagem):
    if not token_telegram or not chat_id: return
    url = f"https://api.telegram.org/bot{token_telegram}/sendMessage"
    payload = {"chat_id": chat_id, "text": mensagem, "parse_mode": "Markdown"}
    try: requests.post(url, json=payload, timeout=10)
    except: pass

def obter_dados(symbol, interval, limit=200):
    endpoints = ["https://api.binance.us/api/v3/klines", "https://data-api.binance.vision/api/v3/klines"]
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
    return 100 - (100 / (1 + (gain / loss)))

try:
    print("🚀 Analisando Confluência 5min/60min...")
    df_5m = obter_dados("BTCUSDT", "5m", 300)   # Precisamos de 200+ para a EMA 200
    df_60m = obter_dados("BTCUSDT", "1h", 100)

    # --- PROCESSAMENTO 60 MINUTOS (MACRO) ---
    ma20_60m = df_60m['close'].rolling(window=20).mean().iloc[-1]
    topo_60m = df_60m['high'].max()  # Resistência máxima recente
    fundo_60m = df_60m['low'].min()  # Suporte máximo recente
    preco_60m = df_60m['close'].iloc[-1]

    # --- PROCESSAMENTO 5 MINUTOS (EXECUÇÃO) ---
    # Médias Móveis
    ema9_5m = df_5m['close'].ewm(span=9, adjust=False).mean()
    ema21_5m = df_5m['close'].ewm(span=21, adjust=False).mean()
    ma200_5m = df_5m['close'].rolling(window=200).mean()
    
    # Volume e RSI
    vol_media = df_5m['vol'].rolling(window=20).mean().iloc[-1]
    vol_atual = df_5m['vol'].iloc[-1]
    rsi_5m = calcular_rsi(df_5m['close']).iloc[-1]
    
    # Valores atuais para lógica
    p_atual = df_5m['close'].iloc[-1]
    p_low = df_5m['low'].iloc[-1]
    p_high = df_5m['high'].iloc[-1]
    m200 = ma200_5m.iloc[-1]
    
    # 1. Verificação de Toque na Média 200 (5min)
    # Definimos toque se o preço 'low' for menor que a média e o 'close' for maior (ou vice-versa)
    toucou_m200_compra = p_low <= m200 <= p_high and p_atual >= m200
    toucou_m200_venda = p_low <= m200 <= p_high and p_atual <= m200

    # 2. Cruzamento de Médias 9/21 (5min)
    cruzou_alta = ema9_5m.iloc[-1] > ema21_5m.iloc[-1] and ema9_5m.iloc[-2] <= ema21_5m.iloc[-2]
    cruzou_baixa = ema9_5m.iloc[-1] < ema21_5m.iloc[-1] and ema9_5m.iloc[-2] >= ema21_5m.iloc[-2]

    # 3. Lógica de Volume (Confirmar se há força)
    volume_confirmado = vol_atual > vol_media

    # --- CONDIÇÕES DE ALERTA ---
    
    # ALERTA DE COMPRA:
    # Preço tocou a MA200 (5m) + Perto do Fundo (60m) + Cruzamento 9/21 + Volume
    if (toucou_m200_compra or p_atual > m200) and cruzou_alta and volume_confirmado:
        msg = (
            f"🟢 **SINAL DE COMPRA CONFIRMADO** 🟢\n"
            f"🎯 *Ação:* Entrar na abertura do próximo candle\n\n"
            f"💰 Preço: `${p_atual:,.2f}`\n"
            f"📏 MA200(5m): `${m200:,.2f}`\n"
            f"📊 RSI: `{rsi_5m:.2f}`\n"
            f"🏗️ Macro(60m): Preço acima do Fundo `{fundo_60m:,.2f}`\n"
            f"🔥 Volume: `{(vol_atual/vol_media):.1f}x` acima da média"
        )
        enviar_telegram(msg)

    # ALERTA DE VENDA:
    # Preço tocou a MA200 (5m) + Perto do Topo (60m) + Cruzamento 9/21 + Volume
    elif (toucou_m200_venda or p_atual < m200) and cruzou_baixa and volume_confirmado:
        msg = (
            f"🔴 **SINAL DE VENDA CONFIRMADO** 🔴\n"
            f"🎯 *Ação:* Entrar na abertura do próximo candle\n\n"
            f"💰 Preço: `${p_atual:,.2f}`\n"
            f"📏 MA200(5m): `${m200:,.2f}`\n"
            f"📊 RSI: `{rsi_5m:.2f}`\n"
            f"🏗️ Macro(60m): Preço abaixo do Topo `{topo_60m:,.2f}`\n"
            f"🔥 Volume: `{(vol_atual/vol_media):.1f}x` acima da média"
        )
        enviar_telegram(msg)

    print(f"Check concluído. RSI: {rsi_5m:.2f} | P: {p_atual}")

except Exception as e:
    print(f"Erro: {e}")
