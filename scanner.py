import csv, time
from datetime import datetime
from pathlib import Path
from config import *
from upstox_api import UpstoxClient, UpstoxAPIError
from strategy import analyse_candles, enrich_option

CSV_FILE=Path("signals.csv")
FIELDS=["timestamp","underlying","spot","direction","confidence","expiry","option_type","strike","instrument_key",
        "ltp","bid","ask","spread_pct","oi","prev_oi","volume","delta","iv","entry","stop_loss","target_1","target_2","reason"]

def log(row):
    exists=CSV_FILE.exists()
    with CSV_FILE.open("a",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=FIELDS,extrasaction="ignore")
        if not exists: w.writeheader()
        w.writerow(row)

def list_data(payload,*keys):
    if isinstance(payload,list): return payload
    if isinstance(payload,dict):
        for k in keys:
            if isinstance(payload.get(k),list): return payload[k]
    return []

def resolve_stocks(api):
    resolved=[]
    print("\\nResolving stock underlyings...")
    for symbol in STOCKS[:MAX_STOCKS]:
        try:
            candidates=list_data(api.instrument_search(symbol),"instruments","items")
            matches=[]
            for item in candidates:
                sym=str(item.get("trading_symbol") or item.get("tradingSymbol") or "").upper()
                key=item.get("instrument_key") or item.get("instrumentKey")
                if key and sym==symbol: matches.append(key)
            if matches:
                resolved.append((symbol,matches[0],"STOCK")); print(f"  {symbol}: {matches[0]}")
            else: print(f"  {symbol}: not resolved; candidates={len(candidates)}")
        except UpstoxAPIError as e: print(f"  {symbol}: SEARCH ERROR: {e}")
    return resolved

def nearest_expiry(contracts):
    today=datetime.now().date().isoformat()
    dates=sorted({str(x.get("expiry")) for x in contracts if x.get("expiry") and str(x.get("expiry"))>=today})
    return dates[0] if dates else None

def scan_one(api,name,key,kind):
    print(f"\\n{'='*68}\\n{name} [{kind}]")
    try:
        candles=api.candles(key,CANDLE_INTERVAL_MINUTES)
        signal=analyse_candles(candles)
        spot=float(signal.get("price") or 0)
        print(f"Signal={signal['direction']} score={signal['score']} confidence={signal['confidence']}%")
        print(f"Reason: {signal['reason']}")
        if spot<=0: print("SKIP: no valid spot from candle API"); return
        if signal["direction"]=="NEUTRAL" or signal["confidence"]<MIN_CONFIDENCE:
            print("No directional signal; no option selected on this scan."); return
        contracts=list_data(api.option_contracts(key),"contracts","items")
        print(f"Option contracts API returned {len(contracts)} contracts")
        expiry=nearest_expiry(contracts)
        if not expiry: print("NO OPTIONS: no upcoming expiry in contract response"); return
        chain=list_data(api.option_chain(key,expiry),"option_chain","items")
        if not chain: print(f"NO OPTIONS: empty chain for expiry {expiry}"); return
        chain_spot=next((float(x.get("underlying_spot_price") or 0) for x in chain if x.get("underlying_spot_price")),spot)
        spot=chain_spot or spot
        typ="CE" if signal["direction"]=="BULLISH" else "PE"
        candidates=[]
        for row in chain:
            leg=row.get("call_options") if typ=="CE" else row.get("put_options")
            if leg and leg.get("instrument_key"): candidates.append(enrich_option(row,leg,typ,spot))
        candidates.sort(key=lambda x:x["distance"])
        near=candidates[:2*STRIKES_EACH_SIDE+1]
        print(f"Expiry={expiry}; spot={spot:.2f}; chain strikes={len(chain)}; {typ} contracts={len(candidates)}")
        eligible=[x for x in near if x["ltp"]>=MIN_OPTION_LTP and x["volume"]>0 and x["oi"]>0 and
                  x["bid"]>0 and x["ask"]>0 and x["spread"]<=MAX_SPREAD_PERCENT]
        if not eligible:
            print("No option passed liquidity filters. Near-ATM diagnostics:")
            for x in near[:7]:
                print(f"  {typ} {x['strike']:g} LTP={x['ltp']:.2f} bid={x['bid']:.2f} ask={x['ask']:.2f} "
                      f"spread={x['spread']:.2f}% OI={x['oi']:.0f} Vol={x['volume']:.0f}")
            print(f"Filters: LTP>={MIN_OPTION_LTP}, OI/volume>0, bid/ask>0, spread<={MAX_SPREAD_PERCENT}%")
            return
        chosen=max(eligible,key=lambda x:(-x["distance"],min(x["volume"],1e7)/1e7,min(x["oi"],1e7)/1e7,-x["spread"]))
        entry=round(chosen["ask"] or chosen["ltp"],2); sl=round(entry*.90,2); t1=round(entry*1.15,2); t2=round(entry*1.25,2)
        print("-"*68)
        print(f"SELECTED: {name} {chosen['strike']:g} {typ} | {chosen['key']}")
        print(f"LTP ₹{chosen['ltp']:.2f} | bid ₹{chosen['bid']:.2f} | ask ₹{chosen['ask']:.2f} | spread {chosen['spread']:.2f}%")
        print(f"OI={chosen['oi']:.0f} prevOI={chosen['prev_oi']:.0f} volume={chosen['volume']:.0f} delta={chosen['delta']} IV={chosen['iv']}")
        print(f"Entry reference ₹{entry:.2f} | SL ₹{sl:.2f} | T1 ₹{t1:.2f} | T2 ₹{t2:.2f}")
        print("PAPER SIGNAL ONLY — NO ORDER PLACED")
        log({"timestamp":datetime.now().astimezone().isoformat(),"underlying":name,"spot":spot,"direction":signal["direction"],
             "confidence":signal["confidence"],"expiry":expiry,"option_type":typ,"strike":chosen["strike"],
             "instrument_key":chosen["key"],"ltp":chosen["ltp"],"bid":chosen["bid"],"ask":chosen["ask"],
             "spread_pct":chosen["spread"],"oi":chosen["oi"],"prev_oi":chosen["prev_oi"],"volume":chosen["volume"],
             "delta":chosen["delta"],"iv":chosen["iv"],"entry":entry,"stop_loss":sl,"target_1":t1,"target_2":t2,
             "reason":signal["reason"]})
        print(f"Logged to {CSV_FILE.resolve()}")
    except UpstoxAPIError as e: print(f"API ERROR: {e}")
    except Exception as e: print(f"UNEXPECTED ERROR: {type(e).__name__}: {e}")

def main():
    if TRADING_MODE!="PAPER": raise SystemExit("Signals-only build. Set TRADING_MODE=PAPER; no orders are placed.")
    try: api=UpstoxClient(TOKEN)
    except UpstoxAPIError as e: raise SystemExit(str(e))
    print("UPSTOX OPTIONS SCANNER V2.1 | SIGNALS ONLY | NO ORDERS")
    stocks=resolve_stocks(api)
    underlyings=[(n,k,"INDEX") for n,k in INDEXES]+stocks
    print("\\nConfigured scan targets:")
    for n,k,t in underlyings: print(f"  {n} [{t}] -> {k}")
    while True:
        print(f"\\nScan started {datetime.now().astimezone().isoformat(timespec='seconds')}")
        for n,k,t in underlyings: scan_one(api,n,k,t)
        print(f"\\nScan complete; next scan in {SCAN_SECONDS}s. Ctrl+C to stop.")
        time.sleep(SCAN_SECONDS)

if __name__=="__main__": main()
