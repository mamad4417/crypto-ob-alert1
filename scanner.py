import asyncio, os, time
from datetime import datetime, timezone
import aiohttp
from order_block import detect_new_order_blocks

COINS_URL="https://api.coingecko.com/api/v3/coins/markets"
EXCHANGE_URL="https://api.binance.com/api/v3/exchangeInfo"
KLINES_URL="https://api.binance.com/api/v3/klines"
TG_URL="https://api.telegram.org/bot{}/sendMessage"

TOP_N=int(os.getenv("TOP_N","250"))
SENS=int(os.getenv("SENSITIVITY","28"))
GAP=int(os.getenv("OB_GAP_BARS","5"))
TOKEN=os.environ["TELEGRAM_BOT_TOKEN"]
CHAT=os.environ["TELEGRAM_CHAT_ID"]

async def get_json(session,url,params=None):
    for attempt in range(4):
        try:
            async with session.get(url,params=params,timeout=30) as r:
                if r.status in (429,418):
                    await asyncio.sleep(2**attempt); continue
                r.raise_for_status()
                return await r.json()
        except Exception:
            if attempt == 3: raise
            await asyncio.sleep(2**attempt)

async def top_coins(session):
    return (await get_json(session,COINS_URL,{
        "vs_currency":"usd","order":"market_cap_desc","per_page":250,
        "page":1,"sparkline":"false"}))[:TOP_N]

async def binance_symbols(session):
    data=await get_json(session,EXCHANGE_URL)
    return {x["symbol"] for x in data["symbols"]
            if x["status"]=="TRADING" and x["quoteAsset"]=="USDT"
            and x.get("isSpotTradingAllowed",False)}

async def klines(session,symbol,interval):
    data=await get_json(session,KLINES_URL,{"symbol":symbol,"interval":interval,"limit":30})
    now=int(time.time()*1000)
    return [{"open_time":int(x[0]),"open":float(x[1]),"high":float(x[2]),
             "low":float(x[3]),"close":float(x[4])}
            for x in data if int(x[6]) <= now]

async def send_telegram(session,text):
    async with session.post(TG_URL.format(TOKEN),
                            json={"chat_id":CHAT,"text":text},timeout=20) as r:
        r.raise_for_status()

def should_scan(interval):
    now=datetime.now(timezone.utc)
    if interval=="4h": return True
    if interval=="1d": return now.hour in (0,1)
    if interval=="1w": return now.weekday()==0 and now.hour in (0,1)
    return False

async def process(session,coin,pair,interval,label,sem):
    async with sem:
        try:
            rows=await klines(session,pair,interval)
            for ob in detect_new_order_blocks(rows,SENS,GAP):
                dt=datetime.fromtimestamp(ob["created_open_time"]/1000,timezone.utc)
                icon="🟢" if ob["side"]=="BULLISH" else "🔴"
                text=(f"{icon} NEW {ob['side']} ORDER BLOCK\n\n"
                      f"Coin: {coin['name']} ({coin['symbol'].upper()})\n"
                      f"Market Cap Rank: #{coin.get('market_cap_rank','?')}\n"
                      f"Pair: {pair}\nTimeframe: {label}\n\n"
                      f"OB High: {ob['high']:g}\nOB Low: {ob['low']:g}\n"
                      f"Candle Open: {dt:%Y-%m-%d %H:%M UTC}")
                await send_telegram(session,text)
                print(text)
        except Exception as e:
            print("ERROR",pair,interval,repr(e))

async def main():
    timeout=aiohttp.ClientTimeout(total=45)
    async with aiohttp.ClientSession(timeout=timeout,
                                     connector=aiohttp.TCPConnector(limit=30)) as session:
        coins=await top_coins(session)
        valid=await binance_symbols(session)
        tasks=[]; sem=asyncio.Semaphore(20)
        for coin in coins:
            pair=coin["symbol"].upper()+"USDT"
            if pair not in valid: continue
            for interval,label in (("4h","4H"),("1d","1D"),("1w","1W")):
                if should_scan(interval):
                    tasks.append(process(session,coin,pair,interval,label,sem))
        print(f"Scanning {len(tasks)} checks.")
        await asyncio.gather(*tasks)

if __name__=="__main__":
    asyncio.run(main())
