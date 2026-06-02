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

HOTELS = ["銀河", "倫敦人", "新濠天地"]
AGENTS = ["安", "Fifi", "Yuka", "H", "Ring", "韓國"]

HOTEL_MAP = {
    "銀河": {
        "萬豪": [["JW01","萬豪大床",80],["JW01T","萬豪雙床",80],["JW06","萬豪一房一廳",200]],
        "麗思": [["RC01","麗思一房一廳",200]]
    },
    "倫敦人": {
        "名匯": [["RK","名匯普通房",60],["LS2","名匯一房一廳",120],["N2B","名匯兩房一廳",400]],
        "御園": [["CM1","御園一房一廳",150],["CK2","御園兩房一廳",400]],
        "倫敦人酒店": [["KC","倫敦人酒店小套",60],["KS","倫敦人酒店大套",120],["DBKD2","倫敦人酒店兩房一廳",400]]
    },
    "新濠天地": {
        "摩珀斯": [["PK","摩珀斯豪華客房(大床)",80],["PT","摩珀斯豪華客房(雙床)",80],["CPK","摩珀斯行政豪華(大床)",100],["CPT","摩珀斯行政豪華(雙床)",100],["PS","摩珀斯豪華套房",120],["ES","摩珀斯尊尚套房",200],["S1","摩珀斯尊致套房",1000]],
        "頤居": [["PK_N","頤居尊尚客房(大床)",80],["PQ","頤居尊尚雙床",80],["DS","頤居豪華套房",120],["PS_N","頤居尊尚套房",200],["V1","頤居套房",1000]],
        "君悅": [["DLXK","君悅豪華客房(大床)",30],["DLX1","君悅豪華客房(雙床)",30],["GRSK","君悅套房(大床)",50]],
        "明星匯": [["CRK","明星匯經典(大床)",30],["CRT","明星匯經典雙床",30],["CDK","明星匯豪華(大床)",30]],
        "巨星匯": [["SDK","巨星匯尊貴(大床)",60],["SDT","巨星匯尊貴(雙床)",60],["SPS","巨星匯行政套房",200]],
        "映星匯": [["EDK","映星匯套房(大床)",60],["EDT","映星匯套房(雙床)",60],["EG1","映星匯悠然套房",100],["ES1","映星匯華麗套房",200]]
    },
}


def fmt_wash(val):
    if val is None or val == 0: return "-"
    s = f"{float(val):.2f}"; return s.rstrip("0").rstrip(".")


def fb_get(path):
    r = requests.get(f"{path}.json", timeout=10)
    return r.json() if r.status_code == 200 else None


def fb_put(data, path):
    r = requests.put(f"{path}.json", json=data, timeout=10)
    return r.status_code == 200


def tg_send(chat_id, text, keyboard=None):
    body = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    if keyboard: body["reply_markup"] = {"inline_keyboard": keyboard}
    requests.post(f"{TG_API}/sendMessage", json=body, timeout=10)


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
    requests.put(f"{FB_STATE}/_lastUpdateId.json", json=uid, timeout=10)


# ===== 指令處理 =====

def cmd_start(chat_id):
    tg_send(chat_id, (
        "🤖 *Agent 洗碼統計機器人*\n\n即時同步網頁數據\n\n"
        "📌 *指令：*\n"
        "/status — 各 Agent 洗碼總覽\n"
        "/room — 新增拿房\n"
        "/wash — 新增洗碼\n"
        "/list — 近期記錄\n"
        "/commission — 碼糧明細\n"
        "/fund — 公積金\n"
        "/delete — 刪除記錄"
    ))


def cmd_status(chat_id):
    data = get_data()
    agents = data.get("agents", {})
    if not agents: return tg_send(chat_id, "📋 尚無數據")

    lines = ["📊 *Agent 洗碼統計總覽*\n"]
    for name, ad in agents.items():
        if name == "房間總計": continue
        lines.append(f"👤 *{name}*")
        tr = tw = tm = 0; hl = []
        for hotel in HOTELS:
            h = ad.get(hotel, {})
            r, l, w = h.get("rooms",0), h.get("rolling",0), h.get("washed",0)
            if r or l or w:
                d = w - l; ds = f"+{fmt_wash(d)}" if d > 0 else fmt_wash(d)
                hl.append(f"  {hotel}: {r}晚 | 轉碼{fmt_wash(l)}萬 | 洗碼{fmt_wash(w)}萬 | 差異{ds}萬")
                tr += l; tw += w; tm += r
        if hl:
            lines.extend(hl)
            td = tw - tr; tds = f"+{fmt_wash(td)}" if td > 0 else fmt_wash(td)
            lines.append(f"  ➡️ 合計: {tm}晚 | 差異{tds}萬")
        else:
            lines.append("  尚無記錄")
        lines.append("")
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
    data = get_data()
    records = data.get("records",[])
    if not records: return tg_send(chat_id, "📋 尚無記錄")
    recent = records[-20:]
    lines = ["📋 *近期記錄*\n"]
    for r in reversed(recent):
        icon = "✅" if r.get("status")=="done" else "⏳"
        lines.append(f"{icon} {r.get('date','')} | {r.get('agent','')} | {r.get('hotel','')}·{r.get('area','')} | {r.get('code','')} | 轉碼{fmt_wash(r.get('total_req',0))}萬 | 洗碼{fmt_wash(r.get('washed',0))}萬")
    tg_send(chat_id, "\n".join(lines))


def cmd_commission(chat_id):
    data = get_data()
    records, rates = data.get("records",[]), data.get("commission_rates",[])
    if not records: return tg_send(chat_id, "💰 尚無碼糧數據")

    lines = ["💰 *碼糧明細*\n"]
    for agent in AGENTS:
        ar = [r for r in records if r.get("agent")==agent and r.get("washed")]
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
    total = 0
    for agent in AGENTS:
        for r in records:
            if r.get("agent")==agent and r.get("hotel")=="新濠天地" and r.get("hall")=="勵盈1" and r.get("washed"):
                f = float(r["washed"]) * 10000 * 0.0001; total += f
                lines.append(f"👤 {agent} | 洗碼{fmt_wash(r['washed'])}萬 | 公積金 {f:,.0f}")
    lines.append(f"\n➡️ 公積金總計: *{total:,.0f}*")
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

    elif data_str.startswith("rh:"):
        hotel = data_str[3:]; state = get_state(chat_id); state["step"]="room_area"; state["hotel"]=hotel
        set_state(chat_id, state)
        tg_send(chat_id, f"✅ 酒店: {hotel}\n\n請選擇區域：", [[{"text":a,"callback_data":f"rarea:{a}"}] for a in HOTEL_MAP.get(hotel,{})])

    elif data_str.startswith("rarea:"):
        area = data_str[6:]; state = get_state(chat_id); state["step"]="room_code"; state["area"]=area
        set_state(chat_id, state)
        codes = HOTEL_MAP.get(state["hotel"],{}).get(area,[])
        tg_send(chat_id, f"✅ 區域: {area}\n\n請選擇房型：", [[{"text":f"{c} {n} ({r}萬)","callback_data":f"rc:{c}:{n}:{r}"}] for c,n,r in codes])

    elif data_str.startswith("rc:"):
        parts = data_str[3:].split(":"); code, name, req = parts[0], parts[1], int(parts[2])
        state = get_state(chat_id); state.update(step="room_date",code=code,name=name,req=req)
        set_state(chat_id, state)
        tg_send(chat_id, f"✅ 房型: {code} {name} ({req}萬)\n\n請輸入日期（M/D，例如 6/5）：")

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

    elif data_str.startswith("del:"):
        rid = data_str[4:]
        if rid == "cancel": return tg_send(chat_id, "❌ 已取消")
        data = get_data(); records = data.get("records",[])
        idx = next((i for i,r in enumerate(records) if r.get("id")==rid), -1)
        if idx == -1: return tg_send(chat_id, "❌ 找不到此記錄")
        target = records.pop(idx); save_data(data)
        tg_send(chat_id, f"✅ 已刪除：\n{target.get('date','')} | {target.get('agent','')} | {target.get('hotel','')}·{target.get('area','')} | {target.get('code','')}\n\n🌐 網頁已即時同步")


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
        rec = {"id":f"r{int(datetime.now().timestamp()*1000)}","date":s["date"],"agent":s["agent"],"hotel":s["hotel"],"area":s["area"],"code":s["code"],"name":s["name"],"req":s["req"],"nights":nights,"total_req":s["req"]*nights,"washed":0,"hall":"","commission_taken":False,"taken_amount":None,"status":"pending"}
        data = get_data(); data.setdefault("records",[]).append(rec); save_data(data); clear_state(chat_id)
        tg_send(chat_id, f"✅ *拿房記錄已新增！*\n\n👤 {s['agent']} | 📅 {s['date']}\n🏨 {s['hotel']}·{s['area']} | {s['code']} {s['name']}\n轉碼需求 {s['req']*nights}萬 | {nights}晚\n\n🌐 網頁已即時同步")

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
        tg_send(chat_id, f"✅ *洗碼記錄已新增！*\n\n👤 {s['agent']} | 🏨 {s['hotel']}\n💰 洗碼 {fmt_wash(s['washAmt'])}萬 | 🏛️ {s.get('hall','未選')}\n\n🌐 網頁已即時同步")


# ===== 主流程 =====

def main():
    print("⏳ 檢查 Telegram 訊息...")

    offset = get_last_update() + 1
    try:
        r = requests.get(f"{TG_API}/getUpdates", params={"offset": offset, "timeout": 30}, timeout=35)
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
            elif text == "/status": cmd_status(chat_id)
            elif text == "/room": cmd_room(chat_id)
            elif text == "/wash": cmd_wash(chat_id)
            elif text == "/list": cmd_list(chat_id)
            elif text == "/commission": cmd_commission(chat_id)
            elif text == "/fund": cmd_fund(chat_id)
            elif text == "/delete": cmd_delete(chat_id)
            elif text.startswith("/"): tg_send(chat_id, "❓ 未知指令，/start 查看可用指令")
            else: handle_text(chat_id, text)

        elif cb:
            chat_id = cb["message"]["chat"]["id"]
            data_str = cb["data"]
            cid = cb["id"]
            print(f"    🔘 chat={chat_id} data={data_str}")
            handle_callback(chat_id, data_str, cid)

    print("✅ 處理完成")


if __name__ == "__main__":
    main()
