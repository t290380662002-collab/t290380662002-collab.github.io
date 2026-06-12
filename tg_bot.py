#!/usr/bin/env python3
"""
Agent 洗碼 Telegram Bot - GitHub Actions 輪詢版
每 5 分鐘自動執行，檢查新訊息並處理
"""

import json, os, requests
from datetime import datetime

TG_TOKEN = os.environ.get("TG_TOKEN", "8800485293:AAG_-ArhCRSEUsMmT4X_5gDLzxABVdQbx20")
TG_API = f"https://api.telegram.org/bot{TG_TOKEN}"
FB_DB = "https://anget1-default-rtdb.asia-southeast1.firebasedatabase.app/agentWashData"
FB_STATE = FB_DB.replace("agentWashData", "botState")

HOTELS = ["銀河", "倫敦人", "新濠天地", "永利皇宮", "上葡京"]
AGENTS = ["安", "Fifi", "Yuka", "H", "Ring", "韓國"]

# 場所 → 酒店對照
HALL_HOTEL_MAP = {
    "御匾會": "倫敦人",
    "御匾匯": "倫敦人",
    "勵盈1": "新濠天地",
    "勵盈2": "新濠天地",
    "金門1": "新濠天地",
    "金門8": "新濠天地",
    "永利會": "永利皇宮",
    "上葡京老佛爺": "上葡京",
    "上葡京西塔": "上葡京",
}

HOTEL_MAP = {
    "銀河": {
        "萬豪": [["JW01","萬豪大床",80,80],["JW01T","萬豪雙床",80,80],["JW06","萬豪一房一廳",200,200]],
        "麗思": [["RC01","麗思一房一廳",200,200]]
    },
    "倫敦人": {
        "名匯": [["RK","名匯普通房",60,60],["LS2","名匯一房一廳",150,150],["N2B","名匯兩房一廳",400,400]],
        "御園": [["CM1","御園一房一廳",150,150],["CK2","御園兩房一廳",400,400]],
        "酒店": [["KC","路易套房",60,60],["KS","溫莎套房",120,120],["TC","雙床",60,60]],
        "御匯": [["TC2","御匯兩房一廳",60,60],["TPS","御匯兩房一廳(雙床)",60,60]]
    },
    "新濠天地": {
        "摩珀斯": [["PK","摩珀斯豪華客房(大床)",80,80],["PT","摩珀斯豪華客房(雙床)",80,80],["CPK","摩珀斯行政豪華(大床)",100,100],["CPT","摩珀斯行政豪華(雙床)",100,100],["PS","摩珀斯豪華套房",120,120],["ES","摩珀斯尊尚套房",200,200],["S1","摩珀斯尊致套房",1000,1000]],
        "頤居": [["PK_N","頤居尊尚客房(大床)",80,80],["PQ","頤居尊尚雙床",80,80],["DS","頤居豪華套房",120,120],["PS_N","頤居尊尚套房",200,200],["V1","頤居套房",1000,1000]],
        "君悅": [["DLXK","君悅豪華客房(大床)",30,30],["DLX1","君悅豪華客房(雙床)",30,30],["GRSK","君悅套房(大床)",50,50]],
        "明星匯": [["CRK","明星匯經典(大床)",30,30],["CRT","明星匯經典雙床",30,30],["CDK","明星匯豪華(大床)",30,30]],
        "巨星匯": [["SDK","巨星匯尊貴(大床)",60,60],["SDT","巨星匯尊貴(雙床)",60,60],["SPS","巨星匯行政套房",200,200]],
        "映星匯": [["EDK","映星匯套房(大床)",60,60],["EDT","映星匯套房(雙床)",60,60],["EG1","映星匯悠然套房",100,100],["ES1","映星匯華麗套房",200,200]]
    },
    "永利皇宮": {
        "永利皇宮": [
            ["CRK","大床",160,250],
            ["CRT","雙床",180,270],
            ["LCRK","湖景大床",220,320],
            ["LCRT","湖景雙床",240,340],
            ["EXEC","行政套房",190,280],
            ["PRS","珀麗套",230,320],
            ["PRD","珀麗雙套",230,320],
            ["LPRS","湖景珀麗套",390,580],
            ["LPRX","湖景尊貴珀麗套",390,580]
        ]
    },
    "上葡京": {
        "老佛爺": [["LFK","上葡京老佛爺",0,0],["LFT","上葡京老佛爺雙床",0,0]],
        "西塔": [["XTK","上葡京西塔大床",0,0],["XTT","上葡京西塔雙床",0,0]]
    },
}


from datetime import datetime as dt_module

def is_weekend(date_str):
    """判斷是否週末（週五、週六）"""
    if not date_str: return False
    try:
        parts = date_str.split('/')
        m, d = int(parts[0]), int(parts[1])
        ref = dt_module(dt_module.now().year, m, d)
        return ref.weekday() in (4, 5)  # 週五=4, 週六=5
    except:
        return False


def fmt_wash(val):
    if val is None or val == 0: return "-"
    n = float(val)
    # 使用 round 避免浮點數精度問題，保留小數點後三位
    rounded = round(n * 1000) / 1000
    s = f"{rounded:.3f}"
    return s.rstrip("0").rstrip(".")


def fb_get(path):
    r = requests.get(f"{path}.json", timeout=10)
    return r.json() if r.status_code == 200 else None


def fb_put(data, path):
    r = requests.put(f"{path}.json", json=data, timeout=10)
    return r.status_code == 200


def tg_send(chat_id, text, keyboard=None, reply_kb=None):
    body = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    if keyboard: body["reply_markup"] = {"inline_keyboard": keyboard}
    if reply_kb: body["reply_markup"] = {"keyboard": reply_kb, "resize_keyboard": True}
    requests.post(f"{TG_API}/sendMessage", json=body, timeout=10)

MAIN_KB = [
    [{"text": "📊 總覽"}, {"text": "📝 拿房"}, {"text": "💰 洗碼"}],
    [{"text": "📋 代理紀錄"}, {"text": "💵 碼糧"}, {"text": "🏛️ 公積金"}],
    [{"text": "🗑️ 刪除"}, {"text": "❓ 幫助"}]
]


def tg_answer(cid, text=""):
    requests.post(f"{TG_API}/answerCallbackQuery", json={"callback_query_id": cid, "text": text}, timeout=10)


def get_data():
    return fb_get(FB_DB) or {"agents":{},"records":[],"commission_rates":[]}


def save_data(data):
    data["last_update"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    fb_put(data, FB_DB)


def get_state(chat_id):
    return fb_get(f"{FB_STATE}/{chat_id}")


def set_state(chat_id, state):
    fb_put(state, f"{FB_STATE}/{chat_id}")


def clear_state(chat_id):
    requests.delete(f"{FB_STATE}/{chat_id}.json", timeout=10)


def get_last_update():
    r = requests.get(f"{FB_STATE}/_lastUpdateId.json", timeout=10)
    return int(r.json()) if r.status_code == 200 and r.json() else 0


def set_last_update(uid):
    try:
        r = requests.put(f"{FB_STATE}/_lastUpdateId.json", json=uid, timeout=10)
        if r.status_code not in (200, 204):
            print(f"⚠️ 保存 offset 失敗: {r.status_code}")
    except Exception as e:
        print(f"⚠️ 保存 offset 失敗: {e}")


# ===== 自動解析文字格式 =====

import re

def auto_parse(text, chat_id):
    """自動解析格式（支援全形：和半形:）：
    代理：XXX / Agent：XXX
    場所：XXX
    佣金：X.X%
    
    日期:X/X
    客：XXX
    洗碼：XXX
    """
    # 支援 "代理" 或 "Agent"/"Anget" 開頭
    has_agent = "代理" in text or "Agent" in text or "agent" in text or "Anget" in text or "anget" in text
    if not has_agent or "場所" not in text:
        return False  # 不符合格式

    # 標準化：全形冒號 → 半形
    text = text.replace("：", ":")

    lines = text.strip().split("\n")
    agent = None; hall = None; commission = None
    records = []
    current = {}

    for line in lines:
        line = line.strip()
        if not line: continue

        # 標頭行（支援代理或Agent）
        if line.startswith("代理:") or line.startswith("Agent:") or line.startswith("agent:") or line.startswith("Anget:") or line.startswith("anget:"):
            agent = line.split(":")[-1].strip()
            # 大小寫不敏感比對
            agent_lower = agent.lower()
            matched = next((a for a in AGENTS if a.lower() == agent_lower), None)
            if matched:
                agent = matched
            else:
                agent = "韓國"
        elif line.startswith("場所:"):
            hall = line.split("場所:")[-1].strip()
        elif line.startswith("佣金:"):
            c = line.split("佣金:")[-1].strip().replace("%","")
            try: commission = float(c)
            except: commission = 1.2
        elif line.startswith("日期:"):
            if current: records.append(current)
            current = {"date": line.split("日期:")[-1].strip()}
        elif line.startswith("客:"):
            current["customer"] = line.split("客:")[-1].strip()
        elif line.startswith("洗碼:"):
            try:
                current["wash"] = float(line.split("洗碼:")[-1].strip())
            except:
                current["wash"] = 0
    if current: records.append(current)

    if not records:
        return False

    # 場所 → 酒店
    hotel = HALL_HOTEL_MAP.get(hall, "其他")

    data = get_data()
    added = 0
    for rec in records:
        data.setdefault("records", []).append({
            "id": f"w{int(datetime.now().timestamp()*1000)}_{added}",
            "date": rec.get("date", "?"),
            "agent": agent,
            "hotel": hotel,
            "area": "(獨立洗碼)",
            "code": "-",
            "name": rec.get("customer", "?")[:20],
            "req": 0,
            "nights": 0,
            "total_req": 0,
            "washed": rec.get("wash", 0),
            "hall": hall or "",
            "commission_taken": False,
            "taken_amount": None,
            "status": "done",
            "isWashFree": True
        })
        added += 1

    data["last_update"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    save_data(data)

    # 回報
    lines = [f"✅ *自動解析完成！*\n👤 {agent} | 🏛️ {hall or '?'} | 🏨 {hotel}\n"]
    total = 0
    for i, rec in enumerate(records):
        w = rec.get("wash", 0); total += w
        lines.append(f"{i+1}. {rec.get('date','?')} | {rec.get('customer','?')[:15]} | 洗碼 {fmt_wash(w)}萬")
    lines.append(f"\n📊 共 {added} 筆 | 總洗碼 {fmt_wash(total)}萬")
    tg_send(chat_id, "\n".join(lines))
    return True


def parse_one_room_block(block):
    """解析單筆房間訂單區塊，成功回傳 record dict 否則回傳 error str"""
    text = block.replace("：", ":").replace("（", "(").replace("）", ")")
    lines = [l.strip() for l in text.strip().split("\n") if l.strip()]
    if len(lines) < 4:
        return "格式不完整（至少需 4 行）"

    # 必須有四關鍵字
    has_checkin = any("入住:" in l for l in lines)
    has_checkout = any("退房:" in l for l in lines)
    has_hotel = any("酒店:" in l for l in lines)
    has_room = any("房型:" in l for l in lines)
    if not (has_checkin and has_checkout and has_hotel and has_room):
        return "缺少 入住/退房/酒店/房型 關鍵字"

    guest = lines[0].strip()
    checkin = ""; checkout = ""; hotel_raw = ""; code_raw = ""
    rooms_count = 1; confirmation = ""

    for line in lines:
        if line.startswith("入住:"):
            checkin = line.split(":",1)[-1].strip().rstrip("(").strip()
        elif line.startswith("退房:"):
            checkout = line.split(":",1)[-1].strip().rstrip("(").strip()
        elif line.startswith("酒店:"):
            hotel_raw = line.split(":",1)[-1].strip()
        elif line.startswith("房型:"):
            raw = line.split(":",1)[-1].strip()
            code_raw = raw.replace("🚬","").replace("🚭","").strip()
        elif line.startswith("件數:"):
            try: rooms_count = int(line.split(":",1)[-1].strip())
            except: pass
        elif line.startswith("確認號:"):
            confirmation = line.split(":",1)[-1].strip()

    if not checkin or not checkout or not hotel_raw or not code_raw:
        return "入住/退房/酒店/房型 不可為空"

    # 計算晚數
    try:
        ci_parts = checkin.split("/"); co_parts = checkout.split("/")
        ci_m, ci_d = int(ci_parts[0]), int(ci_parts[1])
        co_m, co_d = int(co_parts[0]), int(co_parts[1])
        from datetime import date
        ci = date(2026, ci_m, ci_d)
        co = date(2026, co_m, co_d)
        nights = (co - ci).days
        if nights <= 0 or nights > 31:
            return f"晚數異常: {nights}晚"
    except:
        return f"日期格式錯誤: {checkin}→{checkout}"

    # 匹配酒店
    hotel = None
    for h_name in ["倫敦人","銀河","新濠天地","永利皇宮","上葡京"]:
        if h_name in hotel_raw:
            hotel = h_name
            break
    if not hotel:
        AREA_TO_HOTEL = {"御園":"倫敦人","名匯":"倫敦人","御匯":"倫敦人","酒店":"倫敦人"}
        hotel = AREA_TO_HOTEL.get(hotel_raw)
    if not hotel:
        return f"無法識別酒店: {hotel_raw}"

    # 搜尋 code
    search_code = code_raw.upper()
    area = None; room_name = None; req_wd = 0; req_we = 0
    if hotel in HOTEL_MAP:
        for a_name, rooms in HOTEL_MAP[hotel].items():
            for r in rooms:
                if r[0].upper() == search_code:
                    area = a_name; room_name = r[1]; req_wd = r[2]; req_we = r[3]
                    break
            if area: break
    if not area:
        return f"找不到房型 {code_raw}（酒店: {hotel}）"

    req = req_we if is_weekend(checkin) else req_wd
    total_req = req * nights

    return {
        "guest": guest, "checkin": checkin, "checkout": checkout,
        "hotel": hotel, "area": area, "code": search_code, "name": room_name,
        "req": req, "nights": nights, "total_req": total_req,
        "rooms": rooms_count, "confirmation": confirmation,
        "is_weekend": is_weekend(checkin)
    }


def auto_parse_room_booking(text, chat_id):
    """自動解析房間訂單（支援多筆，以空行分隔）
    未指定代理 → 歸入「韓國」
    """
    text = text.replace("：", ":").replace("（", "(").replace("）", ")")

    # 拆分成多個區塊（以空行分隔）
    blocks = [b.strip() for b in text.split("\n\n") if b.strip()]
    # 如果單一區塊內有明顯的兩個住客名（兩個連續的姓名行），再拆分
    final_blocks = []
    for b in blocks:
        lines = [l for l in b.split("\n") if l.strip()]
        # 找第一個「入住:」的位置
        split_points = []
        for i, l in enumerate(lines):
            if l.startswith("入住:") and i > 0:
                split_points.append(i)
        if split_points:
            # 從第二個入住行開始拆分
            prev = 0
            for sp in split_points:
                final_blocks.append("\n".join(lines[prev:sp]))
                prev = sp
            final_blocks.append("\n".join(lines[prev:]))
        else:
            final_blocks.append(b)

    if not final_blocks:
        return False

    # 檢查第一個區塊格式
    first = final_blocks[0].replace("：",":")
    has_keys = all(k in first for k in ["入住:","退房:","酒店:","房型:"])
    if not has_keys:
        return False

    results = []
    errors = []
    for block in final_blocks:
        r = parse_one_room_block(block)
        if isinstance(r, str):
            errors.append(f"❌ {block.split(chr(10))[0][:20]}... — {r}")
        else:
            results.append(r)

    if not results:
        if errors:
            tg_send(chat_id, "❌ 解析失敗：\n" + "\n".join(errors[:5]))
        return False

    # 寫入 Firebase
    data = get_data()
    for rec in results:
        new_id = f"r{int(datetime.now().timestamp()*1000)}_{results.index(rec)}"
        obj = {
            "id": new_id,
            "date": rec["checkin"],
            "checkout": rec["checkout"],
            "agent": "韓國",
            "hotel": rec["hotel"],
            "area": rec["area"],
            "code": rec["code"],
            "name": rec["name"],
            "req": rec["req"],
            "nights": rec["nights"],
            "total_req": rec["total_req"],
            "washed": 0,
            "hall": "",
            "commission_taken": False,
            "taken_amount": None,
            "status": "pending",
            "guest": rec["guest"],
            "rooms": rec["rooms"]
        }
        if rec.get("confirmation"):
            obj["confirmation"] = rec["confirmation"]
        data.setdefault("records", []).append(obj)

    data["last_update"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    save_data(data)

    # 回報
    total_nights = sum(r["nights"] for r in results)
    total_req = sum(r["total_req"] for r in results)
    lines = [f"✅ *批量訂房解析完成！*\n📊 {len(results)} 筆 | {total_nights} 晚 | *{total_req} 萬*\n"]
    for i, rec in enumerate(results):
        wl = "週末" if rec["is_weekend"] else "平日"
        lines.append(f"{i+1}. {rec['guest']} | {rec['checkin']}→{rec['checkout']} {rec['nights']}晚 | {rec['hotel']}·{rec['area']} {rec['code']} | {wl} {rec['total_req']}萬")
    if errors:
        lines.append(f"\n⚠️ {len(errors)} 筆錯誤：")
        lines.extend(errors[:5])
    lines.append("\n🌐 網頁已即時同步")
    tg_send(chat_id, "\n".join(lines), reply_kb=MAIN_KB)
    return True


# ===== 指令處理 =====

def cmd_start(chat_id):
    tg_send(chat_id, (
        "🤖 *Agent 洗碼統計機器人*\n\n即時同步網頁數據\n\n"
        "📌 *指令：*\n"
        "/status — 各 Agent 洗碼總覽\n"
        "/room — 新增拿房\n"
        "/wash — 新增洗碼\n"
        "/list — 代理紀錄（選Agent+時間看獨立洗碼）\n"
        "/commission — 碼糧明細\n"
        "/fund — 公積金\n"
        "/delete — 刪除記錄"
    ), reply_kb=MAIN_KB)


def cmd_status(chat_id):
    data = get_data()
    agents = data.get("agents", {})
    records = data.get("records", [])
    if not agents: return tg_send(chat_id, "📋 尚無數據")

    # 從 records 重新計算各 Agent 匯總（與網頁版一致）
    calc = {}
    for name in agents:
        if name == "房間總計": continue
        calc[name] = {}
        for h in HOTELS:
            calc[name][h] = {"rooms":0, "rolling":0, "washed":0}

    for rec in records:
        name = rec.get("agent","")
        hotel = rec.get("hotel","")
        if name in calc and hotel in calc[name]:
            calc[name][hotel]["rooms"] += rec.get("nights", 0) or 0
            calc[name][hotel]["rolling"] += rec.get("total_req", 0) or 0
            if rec.get("washed"):
                calc[name][hotel]["washed"] = round(calc[name][hotel]["washed"] + float(rec.get("washed", 0) or 0), 2)

    lines = ["📊 *Agent 洗碼統計總覽*\n"]
    grand = {}
    for h in HOTELS:
        grand[h] = {"rooms":0, "rolling":0, "washed":0}

    for name, ad in calc.items():
        lines.append(f"👤 *{name}*")
        tr = tw = tm = 0; hl = []
        for hotel in HOTELS:
            h = ad.get(hotel, {})
            r, l, w = h.get("rooms",0), h.get("rolling",0), h.get("washed",0)
            if r or l or w:
                d = w - l; ds = f"+{fmt_wash(d)}" if d > 0 else fmt_wash(d)
                hl.append(f"  {hotel}: {r}晚 | 轉碼{fmt_wash(l)}萬 | 洗碼{fmt_wash(w)}萬 | 差異{ds}萬")
                tr += l; tw += w; tm += r
                grand[hotel]["rooms"] += r
                grand[hotel]["rolling"] += l
                grand[hotel]["washed"] += w
        if hl:
            lines.extend(hl)
            td = tw - tr; tds = f"+{fmt_wash(td)}" if td > 0 else fmt_wash(td)
            lines.append(f"  ➡️ 合計: {tm}晚 | 差異{tds}萬")
        else:
            lines.append("  尚無記錄")
        lines.append("")

    # 房間總計
    gt = {"rooms":0, "rolling":0, "washed":0}
    has_data = False
    total_lines = []
    for hotel in HOTELS:
        r = grand[hotel]["rooms"]; l = grand[hotel]["rolling"]; w = grand[hotel]["washed"]
        if r or l or w:
            has_data = True
            total_lines.append(f"  {hotel}: {r}晚 | 轉碼{fmt_wash(l)}萬 | 洗碼{fmt_wash(w)}萬")
            gt["rooms"] += r; gt["rolling"] += l; gt["washed"] = round(gt["washed"] + w, 2)

    if has_data:
        lines.append("🏨 *房間總計*")
        lines.extend(total_lines)
        lines.append(f"  ➡️ 合計: {gt['rooms']}晚 | 轉碼{fmt_wash(gt['rolling'])}萬 | 洗碼{fmt_wash(gt['washed'])}萬")

    tg_send(chat_id, "\n".join(lines))


def cmd_room(chat_id):
    set_state(chat_id, {"step":"room_agent"})
    tg_send(chat_id, "📝 新增拿房記錄\n\n請選擇 Agent：",
            [[{"text":a,"callback_data":f"ra:{a}"}] for a in AGENTS])


def cmd_wash(chat_id):
    set_state(chat_id, {"step":"wash_agent"})
    tg_send(chat_id, "💰 新增洗碼記錄\n\n請選擇 Agent：",
            [[{"text":a,"callback_data":f"wa:{a}"}] for a in AGENTS])


def cmd_list(chat_id):
    """代理紀錄：選擇 Agent → 選擇時間 → 顯示獨立洗碼"""
    tg_send(chat_id, "📋 代理紀錄\n\n請選擇 Agent：",
            [[{"text": a, "callback_data": f"la:{a}"}] for a in AGENTS])

# 時間篩選輔助函數
def filter_records_by_period(records, period):
    """period: month / lastmonth / year / all"""
    if period == 'all': return records
    now = datetime.now()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    filtered = []
    for r in records:
        try:
            parts = r.get('date', '').split('/')
            if len(parts) < 2: continue
            m, d = int(parts[0]), int(parts[1])
            rd = datetime(now.year, m, d)
            if rd > today: rd = rd.replace(year=rd.year - 1)
        except:
            continue
        if period == 'month':
            if rd.year == now.year and rd.month == now.month: filtered.append(r)
        elif period == 'lastmonth':
            lm = now.month - 1 if now.month > 1 else 12
            ly = now.year if now.month > 1 else now.year - 1
            if rd.year == ly and rd.month == lm: filtered.append(r)
        elif period == 'year':
            if rd.year == now.year: filtered.append(r)
    return filtered


def cmd_commission(chat_id):
    data = get_data()
    records, rates = data.get("records",[]), data.get("commission_rates",[])
    if not records: return tg_send(chat_id, "💰 尚無碼糧數據")

    # 排序函數：按日期 M/D
    def sort_date(r):
        try: d = r.get("date","").split("/"); return (int(d[0]), int(d[1]))
        except: return (0,0)

    lines = ["💰 *碼糧明細（按日期）*\n"]
    for agent in AGENTS:
        ar = sorted([r for r in records if r.get("agent")==agent and r.get("washed")], key=sort_date)
        if not ar: continue
        tc = tt = 0; lines.append(f"👤 *{agent}*")
        for r in ar:
            hall = r.get("hall","")
            rate = next((x["rate"] for x in rates if x["name"]==hall), 0)
            w = float(r.get("washed",0))
            c = w * 10000 * (rate/100) if rate else 0; tc += c
            tk = float(r.get("taken_amount",0)) if r.get("commission_taken") else 0; tt += tk
            cs = f"{c:,.0f}" if c else "-"
            lines.append(f"  {r.get('date','')} | {r.get('hotel','')}·{r.get('area','')} | {r.get('code','')} | 洗碼{fmt_wash(w)}萬 | {hall} {rate}% | 碼糧{cs}")
        p = tc - tt
        lines.append(f"  ➡️ 應得 {tc:,.0f} | 已取 {tt:,.0f} | 未取 {p:,.0f}\n")
    tg_send(chat_id, "\n".join(lines))


def cmd_fund(chat_id):
    data = get_data()
    records = data.get("records",[])
    lines = ["🏛️ *公積金（新濠天地 · 勵盈1 × 0.01%）*\n"]
    total = 0; taken = 0
    fund_rows = []
    for r in records:
        if r.get("hotel")=="新濠天地" and r.get("hall")=="勵盈1" and r.get("washed"):
            f = float(r["washed"]) * 10000 * 0.0001
            is_taken = r.get("fund_taken", False)
            fund_rows.append({"rec": r, "agent": r.get("agent",""), "fund": f, "taken": is_taken})
            total += f
            if is_taken: taken += f
    pending = total - taken

    kb = []
    for item in fund_rows:
        r = item["rec"]; agent = item["agent"]; f = item["fund"]; is_taken = item["taken"]
        status = "✅已提取" if is_taken else "⏳未提取"
        lines.append(f"{status} 👤 {agent} | {r.get('date','')} | 洗碼{fmt_wash(r['washed'])}萬 | 公積金 {f:,.0f}")
        if not is_taken:
            kb.append([{"text": f"💰 提取 {agent} {r.get('date','')}", "callback_data": f"fund:{r.get('id','')}"}])

    lines.append(f"\n➡️ 公積金總計: *{total:,.0f}*")
    lines.append(f"✅ 已提取：{taken:,.0f} | ⏳ 未提取：{pending:,.0f}")

    if kb:
        tg_send(chat_id, "\n".join(lines), keyboard=kb)
    else:
        tg_send(chat_id, "\n".join(lines))


def cmd_delete(chat_id):
    data = get_data()
    records = data.get("records",[])
    if not records: return tg_send(chat_id, "📋 尚無記錄")
    recent = records[-10:]
    kb = [[{"text":f"{r.get('date','')} | {r.get('agent','')} | {r.get('hotel','')}·{r.get('area','')} | {r.get('code','')}","callback_data":f"del:{r.get('id','')}"}] for r in reversed(recent)]
    kb.append([{"text":"❌ 取消","callback_data":"del:cancel"}])
    tg_send(chat_id, "🗑️ 選擇要刪除的記錄：", kb)


# ===== Callback 處理 =====

def handle_callback(chat_id, data_str, cid):
    tg_answer(cid)

    if data_str.startswith("ra:"):
        agent = data_str[3:]
        set_state(chat_id, {"step":"room_hotel","agent":agent})
        tg_send(chat_id, f"✅ Agent: {agent}\n\n請選擇酒店：", [[{"text":h,"callback_data":f"rh:{h}"}] for h in HOTELS])

    elif data_str.startswith("la:"):
        agent = data_str[3:]
        # 代理紀錄流程：選擇時間範圍
        tg_send(chat_id, f"✅ Agent: {agent}\n\n請選擇時間範圍：",
                [[{"text":"本月","callback_data":f"lt:{agent}:month"},
                  {"text":"上月","callback_data":f"lt:{agent}:lastmonth"}],
                 [{"text":"本年","callback_data":f"lt:{agent}:year"},
                  {"text":"全部","callback_data":f"lt:{agent}:all"}]])

    elif data_str.startswith("lt:"):
        parts = data_str[3:].split(":")
        agent, period = parts[0], parts[1] if len(parts) > 1 else 'month'
        period_names = {"month":"本月","lastmonth":"上月","year":"本年","all":"全部"}
        data = get_data()
        records = [r for r in data.get("records",[]) if r.get("agent")==agent and r.get("area")=="(獨立洗碼)" and r.get("washed")]
        records = filter_records_by_period(records, period)
        if not records:
            tg_send(chat_id, f"📋 {agent} · {period_names.get(period, period)}\n\n尚無獨立洗碼記錄", reply_kb=MAIN_KB)
            return
        def sort_date(r):
            try: d=r.get("date","").split("/"); return (int(d[0]),int(d[1]))
            except: return (0,0)
        records.sort(key=sort_date)
        lines = [f"📋 *{agent} · {period_names.get(period, period)} 獨立洗碼*\n"]
        total = 0
        for r in records:
            w = float(r.get("washed",0)); total += w
            lines.append(f"  {r.get('date','')} | {r.get('hotel','')} | {r.get('hall','')} | {r.get('name','?')[:15]} | 洗碼{fmt_wash(w)}萬")
        lines.append(f"\n➡️ 共 {len(records)} 筆 | 總洗碼 {fmt_wash(total)}萬")
        tg_send(chat_id, "\n".join(lines), reply_kb=MAIN_KB)

    elif data_str.startswith("rh:"):
        hotel = data_str[3:]; state = get_state(chat_id); state["step"]="room_area"; state["hotel"]=hotel
        set_state(chat_id, state)
        tg_send(chat_id, f"✅ 酒店: {hotel}\n\n請選擇區域：", [[{"text":a,"callback_data":f"rarea:{a}"}] for a in HOTEL_MAP.get(hotel,{})])

    elif data_str.startswith("rarea:"):
        area = data_str[6:]; state = get_state(chat_id); state["step"]="room_code"; state["area"]=area
        set_state(chat_id, state)
        codes = HOTEL_MAP.get(state["hotel"],{}).get(area,[])
        kb = []
        for c, n, rw, re in codes:
            label = f"{c} {n} (平日{rw}萬{'/週末'+str(re)+'萬' if re!=rw else ''})"
            kb.append([{"text": label, "callback_data": f"rc:{c}:{n}:{rw}:{re}"}])
        tg_send(chat_id, f"✅ 區域: {area}\n\n請選擇房型：", kb)

    elif data_str.startswith("rc:"):
        parts = data_str[3:].split(":"); code, name, req_wd, req_we = parts[0], parts[1], int(parts[2]), int(parts[3])
        state = get_state(chat_id); state.update(step="room_date",code=code,name=name,req_wd=req_wd,req_we=req_we)
        set_state(chat_id, state)
        if req_wd != req_we:
            tg_send(chat_id, f"✅ 房型: {code} {name} (平日{req_wd}萬 / 週末{req_we}萬)\n\n請輸入日期（M/D，例如 6/5）：\n📅 週五/週六自動用週末需求")
        else:
            tg_send(chat_id, f"✅ 房型: {code} {name} ({req_wd}萬)\n\n請輸入日期（M/D，例如 6/5）：")

    elif data_str.startswith("wa:"):
        agent = data_str[3:]
        set_state(chat_id, {"step":"wash_hotel","agent":agent})
        tg_send(chat_id, f"✅ Agent: {agent}\n\n請選擇酒店：", [[{"text":h,"callback_data":f"wh:{h}"}] for h in HOTELS])

    elif data_str.startswith("wh:"):
        hotel = data_str[3:]; state = get_state(chat_id); state["step"]="wash_target"; state["hotel"]=hotel
        set_state(chat_id, state)
        data = get_data()
        pending = [r for r in data.get("records",[]) if r.get("agent")==state["agent"] and r.get("hotel")==hotel and r.get("status")=="pending"]
        kb = [[{"text":f"{r.get('date','')} | {r.get('area','')}·{r.get('code','')} | 轉碼{r.get('total_req',0)}萬","callback_data":f"wt:{r.get('id','')}"}] for r in pending]
        kb.append([{"text":"📝 獨立洗碼","callback_data":"wt:free"}])
        tg_send(chat_id, f"✅ 酒店: {hotel}\n\n選擇對應的拿房記錄：", kb)

    elif data_str.startswith("wt:"):
        target = data_str[3:]; state = get_state(chat_id); state["step"]="wash_amt"; state["washTarget"]=target
        set_state(chat_id, state)
        tg_send(chat_id, "請輸入洗碼量（萬，可含小數，例如 153.23）：")

    elif data_str.startswith("whall:"):
        hall = data_str[6:]; state = get_state(chat_id); state["step"]="wash_date"; state["hall"]=hall
        set_state(chat_id, state)
        tg_send(chat_id, "請輸入日期（M/D），或輸入 skip 跳過：")

    elif data_str.startswith("fund:"):
        rid = data_str[5:]
        data = get_data()
        if rid == "all":
            changed = 0
            for r in data.get("records",[]):
                if r.get("hotel")=="新濠天地" and r.get("hall")=="勵盈1" and r.get("washed") and not r.get("fund_taken"):
                    r["fund_taken"] = True
                    changed += 1
            save_data(data)
            tg_send(chat_id, f"✅ 已一鍵提取 {changed} 筆公積金！\n\n🌐 網頁已即時同步")
        else:
            for r in data.get("records",[]):
                if r.get("id")==rid:
                    r["fund_taken"] = True
                    break
            save_data(data)
            tg_send(chat_id, "✅ 已標記為「已提取」！\n\n🌐 網頁已即時同步")
        cmd_fund(chat_id)  # 刷新顯示

    elif data_str.startswith("del:"):
        rid = data_str[4:]
        if rid == "cancel": return tg_send(chat_id, "❌ 已取消")
        data = get_data(); records = data.get("records",[])
        idx = next((i for i,r in enumerate(records) if r.get("id")==rid), -1)
        if idx == -1: return tg_send(chat_id, "❌ 找不到此記錄")
        target = records.pop(idx); save_data(data)
        tg_send(chat_id, f"✅ 已刪除：\n{target.get('date','')} | {target.get('agent','')} | {target.get('hotel','')}·{target.get('area','')} | {target.get('code','')}\n\n🌐 網頁已即時同步", reply_kb=MAIN_KB)


# ===== 文字處理 =====

def handle_text(chat_id, text):
    state = get_state(chat_id)
    if not state: return

    if state.get("step") == "room_date":
        state["date"] = text; state["step"] = "room_nights"
        set_state(chat_id, state)
        tg_send(chat_id, f"✅ 日期: {text}\n\n請輸入晚數（例如 3）：")

    elif state.get("step") == "room_nights":
        try: nights = int(text)
        except: return tg_send(chat_id, "❌ 請輸入數字")
        s = state
        req = s["req_we"] if is_weekend(s["date"]) else s["req_wd"]
        rec = {"id":f"r{int(datetime.now().timestamp()*1000)}","date":s["date"],"agent":s["agent"],"hotel":s["hotel"],"area":s["area"],"code":s["code"],"name":s["name"],"req":req,"nights":nights,"total_req":req*nights,"washed":0,"hall":"","commission_taken":False,"taken_amount":None,"status":"pending"}
        data = get_data(); data.setdefault("records",[]).append(rec); save_data(data); clear_state(chat_id)
        week_label = "週末" if is_weekend(s["date"]) else "平日"
        tg_send(chat_id, f"✅ *拿房記錄已新增！*\n\n👤 {s['agent']} | 📅 {s['date']} ({week_label})\n🏨 {s['hotel']}·{s['area']} | {s['code']} {s['name']}\n轉碼需求 {req}萬 × {nights}晚 = {req*nights}萬\n\n🌐 網頁已即時同步", reply_kb=MAIN_KB)

    elif state.get("step") == "wash_amt":
        try: amt = float(text)
        except: return tg_send(chat_id, "❌ 請輸入數字")
        state["washAmt"] = amt; state["step"] = "wash_hall"
        set_state(chat_id, state)
        data = get_data(); rates = data.get("commission_rates",[])
        kb = [[{"text":f"{r['name']} ({r['rate']}%)","callback_data":f"whall:{r['name']}"}] for r in rates]
        kb.append([{"text":"不選","callback_data":"whall:"}])
        tg_send(chat_id, f"✅ 洗碼量: {fmt_wash(amt)}萬\n\n請選擇貴賓廳：", kb)

    elif state.get("step") == "wash_date":
        ds = "" if text.lower()=="skip" else text
        s = state; data = get_data()
        if s["washTarget"] == "free":
            data.setdefault("records",[]).append({"id":f"w{int(datetime.now().timestamp()*1000)}","date":ds,"agent":s["agent"],"hotel":s["hotel"],"area":"(獨立洗碼)","code":"-","name":"獨立洗碼","req":0,"nights":0,"total_req":0,"washed":s["washAmt"],"hall":s.get("hall",""),"commission_taken":False,"taken_amount":None,"status":"done","isWashFree":True})
        else:
            for r in data.get("records",[]):
                if r.get("id")==s["washTarget"]: r["washed"]=s["washAmt"]; r["status"]="done"; break
        save_data(data); clear_state(chat_id)
        tg_send(chat_id, f"✅ *洗碼記錄已新增！*\n\n👤 {s['agent']} | 🏨 {s['hotel']}\n💰 洗碼 {fmt_wash(s['washAmt'])}萬 | 🏛️ {s.get('hall','未選')}\n\n🌐 網頁已即時同步", reply_kb=MAIN_KB)


# ===== 主流程 =====

def main():
    # 啟動時驗證 Token
    try:
        vr = requests.get(f"{TG_API}/getMe", timeout=10)
        if vr.status_code == 200 and vr.json().get("ok"):
            bot_info = vr.json()["result"]
            print(f"✅ Bot 上線: @{bot_info['username']} ({bot_info['first_name']})")
        else:
            print(f"❌ Bot Token 無效: {vr.status_code} {vr.text[:200]}")
            return
    except Exception as e:
        print(f"❌ 無法連接 Telegram: {e}")
        return

    print("⏳ 檢查 Telegram 訊息...")

    offset = get_last_update() + 1
    try:
        r = requests.get(f"{TG_API}/getUpdates", params={"offset": offset, "timeout": 0}, timeout=10)
    except Exception as e:
        print(f"❌ 網絡錯誤: {e}")
        return

    if r.status_code == 409:
        print("⚠️ 409 衝突：另一個實例正在執行，跳過本次輪詢")
        return

    if r.status_code != 200:
        print(f"❌ Telegram API 錯誤: {r.status_code} {r.text[:200]}")
        return

    updates = r.json().get("result", [])
    if not updates:
        print("  無新訊息")
        return

    print(f"  📬 收到 {len(updates)} 則新訊息")

    for up in updates:
        uid = up["update_id"]
        set_last_update(uid)

        msg = up.get("message") or up.get("edited_message")
        cb = up.get("callback_query")

        if msg:
            chat_id = msg["chat"]["id"]
            text = (msg.get("text") or "").strip()
            print(f"    💬 chat={chat_id} text={text[:50]}")

            if text == "/start": cmd_start(chat_id)
            elif text == "/status" or text == "📊 總覽": cmd_status(chat_id)
            elif text == "/room" or text == "📝 拿房": cmd_room(chat_id)
            elif text == "/wash" or text == "💰 洗碼": cmd_wash(chat_id)
            elif text == "/list" or text == "📋 代理紀錄" or text == "📋 記錄": cmd_list(chat_id)
            elif text == "/commission" or text == "💵 碼糧": cmd_commission(chat_id)
            elif text == "/fund" or text == "🏛️ 公積金": cmd_fund(chat_id)
            elif text == "/delete" or text == "🗑️ 刪除": cmd_delete(chat_id)
            elif text == "/help" or text == "❓ 幫助": cmd_start(chat_id)
            elif text.startswith("/"): tg_send(chat_id, "❓ 未知指令，/start 查看可用指令")
            else: 
                if not auto_parse(text, chat_id):
                    handle_text(chat_id, text)

        elif cb:
            chat_id = cb["message"]["chat"]["id"]
            data_str = cb["data"]
            cid = cb["id"]
            print(f"    🔘 chat={chat_id} data={data_str}")
            handle_callback(chat_id, data_str, cid)

    print("✅ 處理完成")


if __name__ == "__main__":
    # 印出版本資訊方便偵錯
    try:
        import subprocess
        commit = subprocess.check_output(["git","log","--oneline","-1"], cwd="/workspace/ghpages", stderr=subprocess.DEVNULL).decode().strip()
    except:
        commit = "unknown"
    print(f"📦 啟動 | commit: {commit} | deploy: 2026-06-09 22:39")

    # 檢查是否為持續運行模式（Render 或 GitHub Actions 長輪詢）
    LONGPOLL_MODE = os.environ.get("RENDER", "0") == "1" or os.environ.get("LONGPOLL", "0") == "1"

    if LONGPOLL_MODE:
        # Render 模式：持續長輪詢
        print("🚀 Render 模式：持續運行")

        # 啟動 dummy HTTP 服務器（Render Web Service 需要綁定端口）
        import threading
        from http.server import HTTPServer, BaseHTTPRequestHandler
        class DummyHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(b'Bot is running')
            def log_message(self, format, *args):
                pass  # 關閉 log
        def start_server():
            port = int(os.environ.get('PORT', 8080))
            server = HTTPServer(('0.0.0.0', port), DummyHandler)
            server.serve_forever()
        threading.Thread(target=start_server, daemon=True).start()
        print(f"🌐 HTTP 服務器已啟動於端口 {os.environ.get('PORT', 8080)}")

        # 先驗證 Token
        try:
            vr = requests.get(f"{TG_API}/getMe", timeout=10)
            if vr.status_code == 200 and vr.json().get("ok"):
                bot_info = vr.json()["result"]
                print(f"✅ Bot 上線: @{bot_info['username']} ({bot_info['first_name']})")
            else:
                print(f"❌ Bot Token 無效: {vr.status_code} {vr.text[:200]}")
                exit(1)
        except Exception as e:
            print(f"❌ 無法連接 Telegram: {e}")
            exit(1)

        # 清掉舊的 webhook（避免 409 錯誤）
        requests.get(f"{TG_API}/deleteWebhook", timeout=10)
        print("🧹 已清除 webhook")

        while True:
            offset = get_last_update() + 1
            try:
                r = requests.get(f"{TG_API}/getUpdates", params={"offset": offset, "timeout": 30}, timeout=35)
            except Exception as e:
                print(f"⚠️ 網絡錯誤: {e}，5秒後重試...")
                import time; time.sleep(5)
                continue

            if r.status_code == 409:
                print("⚠️ 409 衝突，5秒後重試...")
                import time; time.sleep(5)
                continue

            if r.status_code != 200:
                print(f"❌ Telegram API 錯誤: {r.status_code} {r.text[:200]}，5秒後重試...")
                import time; time.sleep(5)
                continue

            updates = r.json().get("result", [])
            if updates:
                print(f"  📬 收到 {len(updates)} 則新訊息")
                for up in updates:
                    uid = up["update_id"]
                    set_last_update(uid)
                    msg = up.get("message") or up.get("edited_message")
                    cb = up.get("callback_query")
                    if msg:
                        chat_id = msg["chat"]["id"]
                        text = (msg.get("text") or "").strip()
                        print(f"    💬 chat={chat_id} text={text[:50]}")
                        if text == "/start": cmd_start(chat_id)
                        elif text == "/status" or text == "📊 總覽": cmd_status(chat_id)
                        elif text == "/room" or text == "📝 拿房": cmd_room(chat_id)
                        elif text == "/wash" or text == "💰 洗碼": cmd_wash(chat_id)
                        elif text == "/list" or text == "📋 代理紀錄" or text == "📋 記錄": cmd_list(chat_id)
                        elif text == "/commission" or text == "💵 碼糧": cmd_commission(chat_id)
                        elif text == "/fund" or text == "🏛️ 公積金": cmd_fund(chat_id)
                        elif text == "/delete" or text == "🗑️ 刪除": cmd_delete(chat_id)
                        elif text == "/help" or text == "❓ 幫助": cmd_start(chat_id)
                        elif text.startswith("/"): tg_send(chat_id, "❓ 未知指令，/start 查看可用指令")
                        else: 
                            if not auto_parse(text, chat_id):
                                if not auto_parse_room_booking(text, chat_id):
                                    handle_text(chat_id, text)
                    elif cb:
                        chat_id = cb["message"]["chat"]["id"]
                        data_str = cb["data"]
                        cid = cb["id"]
                        print(f"    🔘 chat={chat_id} data={data_str}")
                        handle_callback(chat_id, data_str, cid)
            # 處理完立即繼續輪詢，不等待
    else:
        # 本地 / GitHub Actions 模式：跑一次就結束
        main()
