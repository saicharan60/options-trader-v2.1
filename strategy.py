def ema(values, period):
    if len(values) < period: return None
    result = sum(values[:period]) / period
    alpha = 2 / (period + 1)
    for v in values[period:]: result = alpha * v + (1-alpha) * result
    return result

def rsi(closes, period=14):
    if len(closes) <= period: return None
    changes = [b-a for a,b in zip(closes[-period-1:-1], closes[-period:])]
    up = sum(max(x,0) for x in changes) / period
    down = sum(max(-x,0) for x in changes) / period
    return 100.0 if down == 0 else 100 - 100/(1 + up/down)

def analyse_candles(payload):
    candles = payload.get("candles", []) if isinstance(payload, dict) else payload
    if len(candles) < 25:
        return {"direction":"NEUTRAL","score":0,"confidence":0,"reason":f"Only {len(candles)} candles"}
    rows = sorted(candles, key=lambda x:x[0])
    try:
        op=[float(x[1]) for x in rows]; hi=[float(x[2]) for x in rows]
        lo=[float(x[3]) for x in rows]; cl=[float(x[4]) for x in rows]
        vol=[float(x[5] or 0) for x in rows]
    except (ValueError,TypeError,IndexError):
        return {"direction":"NEUTRAL","score":0,"confidence":0,"reason":"Unexpected candle format"}
    e9,e21,rv=ema(cl,9),ema(cl,21),rsi(cl)
    if e9 is None or e21 is None or rv is None:
        return {"direction":"NEUTRAL","score":0,"confidence":0,"reason":"Insufficient candle history"}
    score,reasons=0,[]
    if e9>e21: score+=20; reasons.append("EMA9 > EMA21")
    elif e9<e21: score-=20; reasons.append("EMA9 < EMA21")
    typ=[(h+l+c)/3 for h,l,c in zip(hi,lo,cl)]
    tv=sum(vol); vwap=sum(p*v for p,v in zip(typ,vol))/tv if tv else cl[-1]
    if cl[-1]>vwap: score+=20; reasons.append("price above candle VWAP")
    elif cl[-1]<vwap: score-=20; reasons.append("price below candle VWAP")
    if rv>=55: score+=15; reasons.append(f"RSI {rv:.1f} bullish")
    elif rv<=45: score-=15; reasons.append(f"RSI {rv:.1f} bearish")
    av=sum(vol[-21:-1])/max(1,len(vol[-21:-1]))
    if av and vol[-1]>1.2*av:
        if cl[-1]>op[-1]: score+=15; reasons.append("bullish volume expansion")
        elif cl[-1]<op[-1]: score-=15; reasons.append("bearish volume expansion")
    if cl[-1]>max(hi[-11:-1]): score+=20; reasons.append("10-candle breakout")
    elif cl[-1]<min(lo[-11:-1]): score-=20; reasons.append("10-candle breakdown")
    direction="BULLISH" if score>=50 else "BEARISH" if score<=-50 else "NEUTRAL"
    return {"direction":direction,"score":score,"confidence":min(100,abs(score)),
            "price":cl[-1],"rsi":rv,"vwap":vwap,"reason":"; ".join(reasons) or "No strong signal"}

def enrich_option(row, leg, opt_type, spot):
    md=leg.get("market_data") or {}; g=leg.get("option_greeks") or {}
    ltp=float(md.get("ltp") or 0); bid=float(md.get("bid_price") or 0); ask=float(md.get("ask_price") or 0)
    mid=(bid+ask)/2 if bid>0 and ask>0 else 0
    spread=((ask-bid)/mid*100) if mid and ask>=bid else 999
    strike=float(row.get("strike_price") or 0)
    return {"type":opt_type,"strike":strike,"key":leg.get("instrument_key",""),"ltp":ltp,"bid":bid,
            "ask":ask,"spread":spread,"oi":float(md.get("oi") or 0),"prev_oi":float(md.get("prev_oi") or 0),
            "volume":float(md.get("volume") or 0),"delta":g.get("delta"),"iv":g.get("iv"),
            "distance":abs(strike-spot)/spot*100 if spot else 999}
