import streamlit as st
import pandas as pd
import datetime
import os
import hashlib
import textwrap
import html
import io
import streamlit.components.v1 as components

st.set_page_config(page_title="PixelFinance", page_icon="💰", layout="centered")

# FULLSCREEN BUTTON - PIXELAPP STYLE
components.html(
    """
    <style>
        #fullscreenBtn {
            position: fixed; top: 12px; right: 16px; z-index: 999999;
            width: 34px; height: 34px; border: none; border-radius: 9px;
            background: transparent; color: #8b8f98; font-size: 20px;
            display: flex; align-items: center; justify-content: center;
            cursor: pointer; opacity: 0.65;
            transition: opacity 0.2s, background 0.2s, color 0.2s, transform 0.2s;
        }
        #fullscreenBtn:hover { opacity: 1; color: #b0b4bc; background: rgba(255,255,255,0.06); transform: scale(1.04); }
        #fullscreenBtn:active { transform: scale(0.94); }
        #fullscreenBtn.exit { transform: rotate(180deg); }
    </style>
    <button id="fullscreenBtn" title="Fullscreen">⛶</button>
    <script>
        const btn = document.getElementById("fullscreenBtn");
        function updateFullscreenIcon() {
            if (window.parent.document.fullscreenElement) { btn.classList.add("exit"); } 
            else { btn.classList.remove("exit"); }
        }
        btn.addEventListener("click", async () => {
            try {
                if (!window.parent.document.fullscreenElement) { await window.parent.document.documentElement.requestFullscreen(); } 
                else { await window.parent.document.exitFullscreen(); }
                updateFullscreenIcon();
            } catch (error) { console.log(error); }
        });
        window.parent.document.addEventListener("fullscreenchange", updateFullscreenIcon);
    </script>
    """, height=48,
)

st.markdown("""
<style>
    html, body, [data-testid="stAppViewContainer"] {
        background: linear-gradient(135deg, #090b0e 0%, #11151c 50%, #0d1117 100%) !important;
        background-attachment: fixed !important;
    }
    div.stSelectbox, div.stNumberInput, div.stTextInput, div.stRadio {
        background: rgba(255, 255, 255, 0.02) !important;
        border: 1px solid rgba(255, 255, 255, 0.06) !important;
        border-radius: 14px !important; padding: 10px 15px !important;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37) !important;
        backdrop-filter: blur(4px) !important; margin-bottom: 15px !important;
    }
    button[data-testid="stBaseButton-secondary"], button[data-testid="stBaseButton-primary"] {
        background: linear-gradient(135deg, #252932, #16191f) !important; color: #ffffff !important;
        border: 1px solid rgba(255, 255, 255, 0.05) !important; border-radius: 12px !important;
        box-shadow: 0 4px 15px rgba(0,0,0,0.4) !important; transition: all 0.25s ease !important; font-weight: 600 !important;
    }
    button[data-testid="stBaseButton-secondary"]:hover, button[data-testid="stBaseButton-primary"]:hover {
        background: linear-gradient(135deg, #2e343f, #1c2028) !important;
        transform: translateY(-1px) !important; box-shadow: 0 6px 20px rgba(0, 242, 254, 0.15) !important;
        border-color: rgba(0, 242, 254, 0.2) !important;
    }
    .tm-home-trips-title {
        color:#9aa1ad; font-size:11px; font-weight:800; text-transform: uppercase;
        margin:18px 0 9px 2px; padding-bottom:8px; border-bottom:1px solid rgba(255,255,255,0.08);
    }
    div[class*="st-key-month_card_"] button {
        min-height: 122px !important; padding: 16px 18px 30px 18px !important; border-radius: 18px !important;
        border: 1px solid rgba(255,255,255,.10) !important;
        background: linear-gradient(180deg, rgba(13,25,34,.96), rgba(8,15,21,.96)) !important;
        box-shadow: inset 0 1px 0 rgba(255,255,255,.04), 0 8px 22px rgba(0,0,0,.24) !important;
        text-align: left !important; justify-content: flex-start !important; align-items: flex-start !important;
    }
    div[class*="st-key-month_card_"] button:hover { transform: translateY(-2px) !important; border-color: rgba(0,242,254,.30) !important; }
    div[class*="st-key-month_card_"] button::after {
        content: ""; position: absolute; left: 18px; right: 18px; bottom: 11px; height: 5px;
        border-radius: 999px; background: linear-gradient(90deg, #4facfe, #00f2fe); opacity: .85;
    }
</style>
""", unsafe_allow_html=True)

KATEGORII = ["Храна и пазар за дома", "Месечни сметки", "Данъци", "Кола и мотор", "Развлечения и пътуване", "Зареждане на Револют", "Плащане по Кредитна карта"]
DATA_FILE = "finance_data_2026.csv"
SETTINGS_FILE = "finance_months_2026.csv"
BUDGETS_FILE = "finance_budgets_2026.csv"

# В DATA_FILE пазим и тип на транзакцията (expense / income)
for f, cols in [(DATA_FILE, ["month_id", "date", "amount", "category", "description", "payment_method", "tx_type"]), 
                (SETTINGS_FILE, ["month_id", "start_date", "month_finished", "initial_total", "initial_cash", "initial_debit", "initial_revolut"]),
                (BUDGETS_FILE, ["month_id", "category", "budget"])]:
    if not os.path.exists(f): pd.DataFrame(columns=cols).to_csv(f, index=False, encoding="utf-8")
def get_emoji(cat):
    m = {"Храна и пазар за дома": "🛒", "Месечни сметки": "🔌", "Данъци": "📜", "Кола и мотор": "🏍️", "Развлечения и пътуване": "✈️", "Зареждане на Револют": "🔄", "Плащане по Кредитна карта": "🚨"}
    return m.get(cat, "🪙")

def get_month_data(m_id):
    try: return pd.read_csv(DATA_FILE, encoding="utf-8")[lambda d: d["month_id"] == m_id].copy()
    except: return pd.DataFrame(columns=["month_id", "date", "amount", "category", "description", "payment_method", "tx_type"])

def get_month_settings(m_id):
    try:
        df = pd.read_csv(SETTINGS_FILE, encoding="utf-8")
        f = df[df["month_id"] == m_id]
        if not f.empty:
            res = f.iloc.to_dict()
            return {
                "month_id": m_id, "start_date": str(res.get("start_date", "")), "month_finished": str(res.get("month_finished", "Не")),
                "initial_total": float(res.get("initial_total", 0.0) or 0.0), "initial_cash": float(res.get("initial_cash", 0.0) or 0.0),
                "initial_debit": float(res.get("initial_debit", 0.0) or 0.0), "initial_revolut": float(res.get("initial_revolut", 0.0) or 0.0)
            }
    except: pass
    return {"month_id": m_id, "start_date": "", "month_finished": "Не", "initial_total": 0.0, "initial_cash": 0.0, "initial_debit": 0.0, "initial_revolut": 0.0}

def save_month_settings(m_id, s_date, finished, total, cash, debit, revolut):
    df = pd.read_csv(SETTINGS_FILE, encoding="utf-8")[lambda d: d["month_id"] != m_id]
    new_row = pd.DataFrame([{"month_id": m_id, "start_date": s_date, "month_finished": finished, "initial_total": float(total or 0), "initial_cash": float(cash or 0), "initial_debit": float(debit or 0), "initial_revolut": float(revolut or 0)}])
    pd.concat([df, new_row], ignore_index=True).to_csv(SETTINGS_FILE, index=False, encoding="utf-8")

def add_transaction(m_id, amt, cat, desc, method, tx_type="expense"):
    df = pd.read_csv(DATA_FILE, encoding="utf-8")
    row = {"month_id": m_id, "date": datetime.datetime.now().strftime("%d.%m %H:%M"), "amount": float(amt), "category": cat, "description": desc if desc else "Без описание", "payment_method": method, "tx_type": tx_type}
    pd.concat([df, pd.DataFrame([row])], ignore_index=True).to_csv(DATA_FILE, index=False, encoding="utf-8")

def get_category_budgets(m_id):
    res = {cat: 0.0 for cat in KATEGORII}
    try:
        df = pd.read_csv(BUDGETS_FILE, encoding="utf-8")
        rows = df[df["month_id"] == m_id]
        for _, r in rows.iterrows():
            if r["category"] in res: res[r["category"]] = float(r["budget"])
    except: pass
    return res

def save_category_budgets(m_id, budgets):
    df = pd.read_csv(BUDGETS_FILE, encoding="utf-8")[lambda d: d["month_id"] != m_id]
    rows = [{"month_id": m_id, "category": k, "budget": float(v)} for k, v in budgets.items() if float(v) > 0]
    if rows: df = pd.concat([df, pd.DataFrame(rows)], ignore_index=True)
    df.to_csv(BUDGETS_FILE, index=False, encoding="utf-8")

if "current_month" not in st.session_state: st.session_state["current_month"] = None
if "form_version" not in st.session_state: st.session_state["form_version"] = 0

if st.session_state["current_month"] is None:
    st.markdown("""<div style='text-align: center;'><h1 style='font-family: "Segoe UI"; font-weight: 900; font-size: 46px; background: linear-gradient(135deg, #00f2fe, #4facfe, #ff4b4b); -webkit-background-clip: text; -webkit-text-fill-color: transparent;'>💰 PixelFinance</h1><p style='font-family: "Segoe UI"; font-size: 16px; color: #ffd700; font-weight: 500; margin-top: -8px; margin-bottom: 30px;'>Budget Manager</p></div>""", unsafe_allow_html=True)

    @st.dialog("Стартиране на нов отчетен месец")
    def create_month_modal():
        m_name = st.selectbox("Избери Месец:", ["Януари", "Февруари", "Март", "Април", "Май", "Юни", "Юли", "Август", "Септември", "Октомври", "Ноември", "Декември"])
        m_year = st.selectbox("Година:", ["2026", "2027"])
        target_id = f"{m_name}_{m_year}"
        st.markdown("<small style='color: #00f2fe; font-weight: bold;'>С какви пари стартираш приложението?</small>", unsafe_allow_html=True)
        cash = st.number_input("💵 Стартов Кеш / В брой (EUR):", min_value=0.0, step=20.0)
        debit = st.number_input("💳 Стартов баланс в Дебитна Карта (EUR):", min_value=0.0, step=50.0)
        revolut = st.number_input("🔄 Стартов баланс в Револют (EUR):", min_value=0.0, step=50.0)
        total_start = cash + debit + revolut
        if st.button("✔️ Създай и Отвори", use_container_width=True, type="primary"):
            save_month_settings(target_id, datetime.datetime.now().strftime("%d.%m.%Y"), "Не", total_start, cash, debit, revolut)
            st.session_state["current_month"] = target_id
            st.rerun()

    if st.button(" Нов Месечен Бюджет", use_container_width=True, key="new_month_btn", type="primary"): create_month_modal()

    try: existing_months = list(pd.read_csv(SETTINGS_FILE)["month_id"].dropna().unique())
    except: existing_months = []
    existing_months = sorted(existing_months, key=lambda mid: 1 if get_month_settings(mid).get("month_finished") == "Да" else 0)

    if existing_months:
        st.markdown("<div class='tm-home-trips-title'>Избери отчетен период</div>", unsafe_allow_html=True)
        for _m_id in existing_months:
            _stg = get_month_settings(_m_id)
            _df_m = get_month_data(_m_id)
            _finished = _stg.get("month_finished") == "Да"
            _status_dot = "🔴 Затворен" if _finished else "🟢 Активен разчет"
            
            _df_exp = _df_m[_df_m["tx_type"] == "expense"] if not _df_m.empty and "tx_type" in _df_m.columns else _df_m
            _df_inc = _df_m[_df_m["tx_type"] == "income"] if not _df_m.empty and "tx_type" in _df_m.columns else pd.DataFrame()
            
            _added_income = float(_df_inc["amount"].sum()) if not _df_inc.empty else 0.0
            _total_funds = float(_stg.get("initial_total", 0)) + _added_income
            _spent = float(_df_exp[~_df_exp["category"].isin(["Зареждане на Револют", "Плащане по Кредитна карта"])]["amount"].sum()) if not _df_exp.empty else 0.0
            
            _pct = max(0.0, min(100.0, (_spent / _total_funds) * 100.0)) if _total_funds > 0 else 0.0
            _bar_gradient = f"linear-gradient(90deg, #4facfe 0%, #00f2fe {_pct:.1f}%, rgba(255,255,255,0.12) {_pct:.1f}%, rgba(255,255,255,0.12) 100%)"
            _safe_key = hashlib.sha256(_m_id.encode("utf-8")).hexdigest()[:16]
            _button_key = f"month_card_{_safe_key}"
            st.markdown(f"<style>.st-key-{_button_key} button {{ background: {_bar_gradient} bottom / 100% 12px no-repeat, linear-gradient(135deg,rgba(255,255,255,.035),rgba(255,255,255,.012)) !important; width: 100% !important; height: auto !important; display: block !important; text-align: left !important; }}</style>", unsafe_allow_html=True)
            _label = f"📅 **{_m_id.replace('_', ' ')}**\n{_status_dot}\nЧисти разходи: €{_spent:,.2f} / Разполагаем капитал: €{_total_funds:,.2f}"
            if st.button(_label, key=_button_key, use_container_width=True): st.session_state["current_month"] = _m_id; st.rerun()
else:
    month_id = st.session_state["current_month"]
    c_s = get_month_settings(month_id)
    is_month_finished = c_s.get("month_finished") == "Да"
    initial_total, initial_cash, initial_debit, initial_revolut = float(c_s.get("initial_total", 0.0)), float(c_s.get("initial_cash", 0.0)), float(c_s.get("initial_debit", 0.0)), float(c_s.get("initial_revolut", 0.0))

    st.markdown(f"<div style='text-align: center; margin-bottom: 20px;'><h2 style='color: #00f2fe;'>📊 Разчет: {month_id.replace('_', ' ')}</h2></div>", unsafe_allow_html=True)
    if st.button("🔙 НАЗАД КЪМ ГЛАВНО МЕНЮ", use_container_width=True): st.session_state["current_month"] = None; st.rerun()

    st.markdown("---")
    v_id = st.session_state["form_version"]
    
    # 🌟 ИЗБОР МЕЖДУ РАЗХОД И ПРИХОД
    tx_mode = st.radio("Тип операция:", ["📉 Нов Разход", "💰 Нов Приход / Заплата"], horizontal=True, key=f"mode_{v_id}")
    
    col1, col2 = st.columns(2)
    with col1: s_input = st.number_input("Сума (EUR)", value=None, placeholder="Въведете сума...", format="%.2f", key=f"su_{v_id}")
    with col2: o_input = st.text_input("Описание / Основание", placeholder="Напишете детайли...", key=f"op_{v_id}")

    ekran_za_kategorii = st.empty()
    if o_input.strip() and s_input and s_input > 0:
        with ekran_za_kategorii.container():
            if tx_mode == "📉 Нов Разход":
                st.markdown("<div style='text-align: center;'><h3 style='color: #00f2fe;'>🎯 НАЧИН НА ПЛАЩАНЕ И КАТЕГОРИЯ</h3></div>", unsafe_allow_html=True)
                method = st.radio("С какво платихте?", ["💵 Кеш", "💳 Дебитна карта", "🚨 Кредитна карта", "🔄 Револют"], horizontal=True, key=f"mth_{v_id}")
                grid = st.columns(3)
                for i, kat in enumerate(KATEGORII):
                    with grid[i % 3]:
                        if st.button(f"{get_emoji(kat)} {kat}", use_container_width=True, key=f"cat_btn_{i}", disabled=is_month_finished):
                            add_transaction(month_id, s_input, kat, o_input.strip(), method, "expense")
                            st.session_state["form_version"] += 1; st.rerun()
            else:
                st.markdown("<div style='text-align: center;'><h3 style='color: #49dc72;'>💰 КЪДЕ ДА СЕ НАЧИСЛИ ПРИХОДЪТ?</h3></div>", unsafe_allow_html=True)
                target_wallet = st.radio("Избери портфейл за пристигане на парите:", ["💵 Кеш", "💳 Дебитна карта", "🔄 Револют"], horizontal=True, key=f"wallet_in_{v_id}")
                if st.button("💾 Запиши Прихода", use_container_width=True, type="primary", disabled=is_month_finished):
                    add_transaction(month_id, s_input, "Входящ Приход", o_input.strip(), target_wallet, "income")
                    st.session_state["form_version"] += 1; st.rerun()
                    
            if st.button("❌ ОТКАЗ", use_container_width=True): st.session_state["form_version"] += 1; st.rerun()
            st.stop()

    col_m1, col_m2 = st.columns(2)
    with col_m1:
        if not is_month_finished:
            if st.button("🏁 Приключи Месечния Период", use_container_width=True): save_month_settings(month_id, c_s.get("start_date"), "Да", initial_total, initial_cash, initial_debit, initial_revolut); st.rerun()
        else:
            if st.button("🔓 Отключи за Редакция", use_container_width=True): save_month_settings(month_id, c_s.get("start_date"), "Не", initial_total, initial_cash, initial_debit, initial_revolut); st.rerun()
    with col_m2:
        if st.button("🎯 Настрой лимити по категории", use_container_width=True, disabled=is_month_finished):
            @st.dialog("Лимити за месеца")
            def set_limits_modal():
                current_budgets = get_category_budgets(month_id); new_budgets = {}
                for cat in KATEGORII: new_budgets[cat] = st.number_input(f"{get_emoji(cat)} {cat} (EUR):", min_value=0.0, value=current_budgets.get(cat, 0.0))
                if st.button("💾 Запази Лимитите", use_container_width=True, type="primary"): save_category_budgets(month_id, new_budgets); st.rerun()
            set_limits_modal()

    # Счетоводна логика за Разходи, Трансфери и Добавени Приходи
    df_m = get_month_data(month_id)
    cash_out, debit_out, credit_out, revolut_out = 0.0, 0.0, 0.0, 0.0
    cash_in, debit_in, revolut_in, credit_in = 0.0, 0.0, 0.0, 0.0
    
    if not df_m.empty:
        # Сигурност за стари записи, в които липсва колона tx_type
        if "tx_type" not in df_m.columns: df_m["tx_type"] = "expense"
        
        for _, row in df_m.iterrows():
            amt = float(row["amount"])
            method = row["payment_method"]
            cat = row["category"]
            t_type = str(row["tx_type"])
            
            if t_type == "income":
                if method == "💵 Кеш": cash_in += amt
                elif method == "💳 Дебитна карта": debit_in += amt
                elif method == "🔄 Револют": revolut_in += amt
            else:
                if method == "💵 Кеш": cash_out += amt
                elif method == "💳 Дебитна карта": debit_out += amt
                elif method == "🚨 Кредитна карта": credit_out += amt
                elif method == "🔄 Револют": revolut_out += amt
                if cat == "Зареждане на Револют": revolut_in += amt
                elif cat == "Плащане по Кредитна карта": credit_in += amt

    final_cash = initial_cash - cash_out + cash_in
    final_debit = initial_debit - debit_out + debit_in
    final_credit = credit_out - credit_in
    final_revolut = initial_revolut - revolut_out + revolut_in
    current_live_total = initial_total + cash_in + debit_in + revolut_in

    st.markdown("### 🏦 Наличности по портфейли в реално време")
    st.markdown(f"<div style='display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 8px; margin-bottom: 20px;'><div style='background: rgba(0,0,0,0.2); border: 1px solid rgba(255,255,255,0.06); padding: 10px 5px; border-radius: 12px; text-align: center;'><div style='font-size: 9px; color: #8f98a3;'>💵 КЕШ</div><div style='font-size: 14px; color: #ffd43b; font-weight: 900; margin-top: 5px;'>€{final_cash:.2f}</div></div><div style='background: rgba(0,0,0,0.2); border: 1px solid rgba(255,255,255,0.06); padding: 10px 5px; border-radius: 12px; text-align: center;'><div style='font-size: 9px; color: #8f98a3;'>💳 ДЕБИТНА</div><div style='font-size: 14px; color: #49dc72; font-weight: 900; margin-top: 5px;'>€{final_debit:.2f}</div></div><div style='background: rgba(0,0,0,0.2); border: 1px solid rgba(255,255,255,0.06); padding: 10px 5px; border-radius: 12px; text-align: center;'><div style='font-size: 9px; color: #8f98a3;'>🚨 КРЕДИТНА ДЪЛГ</div><div style='font-size: 14px; color: #ff4b4b; font-weight: 900; margin-top: 5px;'>€{final_credit:.2f}</div></div><div style='background: rgba(0,0,0,0.2); border: 1px solid rgba(255,255,255,0.06); padding: 10px 5px; border-radius: 12px; text-align: center;'><div style='font-size: 9px; color: #8f98a3;'>🔄 РЕВОЛЮТ</div><div style='font-size: 14px; color: #00d9ff; font-weight: 900; margin-top: 5px;'>€{final_revolut:.2f}</div></div></div>", unsafe_allow_html=True)

    category_budgets = get_category_budgets(month_id); stat_grid = st.columns(2)
    df_only_expenses = df_m[df_m["tx_type"] == "expense"] if not df_m.empty and "tx_type" in df_m.columns else df_m
    for idx, kat in enumerate(KATEGORII):
        with stat_grid[idx % 2]:
            cat_spent = float(df_only_expenses[df_only_expenses["category"] == kat]["amount"].sum()) if not df_only_expenses.empty else 0.0
            limit = category_budgets.get(kat, 0.0)
            pct_of_funds = (cat_spent / current_live_total * 100) if current_live_total > 0 else 0.0
            st.markdown(f'<div style="background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.08); padding: 14px; border-radius: 14px; margin-bottom: 12px;"><div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;"><span style="font-weight: bold; font-size: 13px;">{get_emoji(kat)} {kat}</span><span style="font-weight: bold; color: #ff4b4b; font-size: 14px;">€{cat_spent:.2f}</span></div><div style="background: rgba(0, 0, 0, 0.4); height: 12px; border-radius: 20px; padding: 2px; position: relative; overflow: hidden; margin-top: 4px;"><div style="width: {min(100.0, pct_of_funds)}%; height: 100%; background: linear-gradient(90deg, #4facfe 0%, #00f2fe 100%); border-radius: 20px;"></div></div><div style="font-size: 10px; color: #888; margin-top: 4px; display: flex; justify-content: space-between;"><span>Дял: {pct_of_funds:.1f}%</span><span>Лимит: {f"€{limit:.2f}" if limit > 0 else "Няма"}</span></div></div>', unsafe_allow_html=True)

    st.markdown("---"); st.markdown("### 📜 Хронология на транзакциите")
    if not df_m.empty:
        for idx in reversed(df_m.index.tolist()):
            r = df_m.loc[idx]
            col_rec, col_del = st.columns([0.88, 0.12])
            is_inc = str(r.get("tx_type", "expense")) == "income"
            sign = "+" if is_inc else "-"
            amt_color = "#49dc72" if is_inc else "#ff4b4b"
            with col_rec: st.markdown(f'<div style="background: rgba(255,255,255,0.02); padding: 12px; border-radius: 12px; border: 1px solid rgba(255,255,255,0.05); margin-bottom: 6px; display: flex; justify-content: space-between; align-items: center;"><div><span style="font-weight:bold;">{get_emoji(r["category"]) if not is_inc else "💰"} {r["category"]}</span> <small style="color:#aaa;">({r["payment_method"]})</small><br><small style="color: #666;">📅 {r["date"]} — {r["description"]}</small></div><div style="color: {amt_color}; font-weight: bold; font-size: 16px;">{sign}€{r["amount"]:.2f}</div></div>', unsafe_allow_html=True)
            with col_del:
                
                if st.button("🗑️", key=f"del_{idx}", disabled=is_month_finished, use_container_width=True):
                    pd.read_csv(DATA_FILE, encoding="utf-8").drop(idx).to_csv(DATA_FILE, index=False, encoding="utf-8")
                    st.rerun()
    else: 
        st.info("Все още няма записани транзакции за този месец.")

    st.markdown("", unsafe_allow_html=True)
    if st.button("🚨 ИЗТРИЙ ЦЕЛИЯ ТОЗИ МЕСЕЦ", type="primary", use_container_width=True):
        pd.read_csv(DATA_FILE, encoding="utf-8")[lambda d: d["month_id"] != month_id].to_csv(DATA_FILE, index=False, encoding="utf-8")
        pd.read_csv(SETTINGS_FILE, encoding="utf-8")[lambda d: d["month_id"] != month_id].to_csv(SETTINGS_FILE, index=False, encoding="utf-8")
        pd.read_csv(BUDGETS_FILE, encoding="utf-8")[lambda d: d["month_id"] != month_id].to_csv(BUDGETS_FILE, index=False, encoding="utf-8")
        st.session_state["current_month"] = None
        st.rerun()
