"""
╔══════════════════════════════════════════════════════════╗
║   FARM EXPENSE AND HARVEST PROFIT ANALYZER               ║
║   Rice and Vegetable Farmers — Baras, Rizal              ║
║   CC 103 — Problem Set #3  (MySQL Edition)               ║
╚══════════════════════════════════════════════════════════╝

  HOW TO INSTALL MySQL CONNECTOR:
    pip install mysql-connector-python

  MAKE SURE farm_database.sql is already imported first!

  NEW FEATURES:
    - Type 0 or B at any screen to go back to main menu
    - Option 9: Delete a crop cycle or a specific expense
"""

import os
import sys
from datetime import datetime

# ── Try importing MySQL connector ──────────────────────────
try:
    import mysql.connector
    from mysql.connector import Error
except ImportError:
    print("\n  ✘ MySQL connector not found!")
    print("  Run this command first:")
    print("      pip install mysql-connector-python\n")
    sys.exit(1)


# ══════════════════════════════════════════════════════════
#  DATABASE CONNECTION SETTINGS
#  ← Change these to match your MySQL setup
# ══════════════════════════════════════════════════════════
DB_CONFIG = {
    "host":     "localhost",   # usually localhost
    "user":     "root",        # your MySQL username
    "password": "",            # your MySQL password
    "database": "farm_analyzer_db"
}


# ══════════════════════════════════════════════════════════
#  SPECIAL EXCEPTION — Used to go back to main menu
# ══════════════════════════════════════════════════════════

class GoBack(Exception):
    """Raised when user types 0 or B to return to main menu."""
    pass


# ══════════════════════════════════════════════════════════
#  CONNECTION HELPERS
# ══════════════════════════════════════════════════════════

def get_connection():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except Error as e:
        print(f"\n  ✘ Cannot connect to MySQL: {e}")
        print("  Check your DB_CONFIG settings at the top of this file.")
        sys.exit(1)

def run_query(sql, params=None, fetch=False):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(sql, params or ())
        if fetch:
            result = cursor.fetchall()
            return result
        else:
            conn.commit()
            return cursor.lastrowid
    except Error as e:
        print(f"\n  ✘ Query error: {e}")
        return None
    finally:
        cursor.close()
        conn.close()


# ══════════════════════════════════════════════════════════
#  UTILITIES
# ══════════════════════════════════════════════════════════

def cls():
    os.system("cls" if os.name == "nt" else "clear")

def sep(char="═", w=60):
    print(char * w)

def hdr(title):
    sep()
    print(f"  {title}")
    sep()

def back_hint():
    """Show the back-to-menu hint."""
    print("  (Type 0 or B anytime to go back to main menu)")
    sep("─")

def pause():
    input("\n  [Pindutin ang Enter / Press Enter to continue...]")

def peso(v):
    return f"₱{float(v):,.2f}" if v is not None else "₱0.00"

def pct(part, total):
    return f"{(float(part)/float(total)*100):.1f}%" if total else "0.0%"


# ══════════════════════════════════════════════════════════
#  INPUT HELPERS  (all support 0 / B to go back)
# ══════════════════════════════════════════════════════════

def check_back(raw):
    """If user typed 0 or b, raise GoBack to return to main menu."""
    if raw.strip().lower() in ("0", "b"):
        print("\n  ↩  Bumabalik sa main menu...")
        raise GoBack()

def get_float(prompt, mn=0):
    while True:
        raw = input(prompt)
        check_back(raw)
        try:
            v = float(raw)
            if v < mn:
                print(f"  ✘ Dapat ay {mn} o higit pa.")
            else:
                return v
        except ValueError:
            print("  ✘ Ilagay ang tamang numero.")

def get_int(prompt, mn=None, mx=None):
    while True:
        raw = input(prompt)
        check_back(raw)
        try:
            v = int(raw)
            if mn is not None and v < mn:
                print(f"  ✘ Minimum ay {mn}.")
            elif mx is not None and v > mx:
                print(f"  ✘ Maximum ay {mx}.")
            else:
                return v
        except ValueError:
            print("  ✘ Ilagay ang buong numero.")

def get_str(prompt, default=None):
    raw = input(prompt).strip()
    check_back(raw)
    return raw if raw else default

def get_date(prompt="  Petsa (YYYY-MM-DD) [blank = ngayon]: "):
    raw = input(prompt).strip()
    check_back(raw)
    return raw if raw else datetime.today().strftime("%Y-%m-%d")

def get_yn(prompt):
    """Ask y/n — also supports 0/b to go back."""
    while True:
        raw = input(prompt).strip().lower()
        check_back(raw)
        if raw in ("y", "n"):
            return raw
        print("  ✘ Mag-type ng y o n lamang.")


# ══════════════════════════════════════════════════════════
#  PICK FROM DATABASE LISTS
# ══════════════════════════════════════════════════════════

def pick_crop():
    crops = run_query("SELECT * FROM crops ORDER BY crop_id", fetch=True)
    print("\n  ── MGA PANANIM / CROPS ─────────────────────────")
    for c in crops:
        print(f"    {c['crop_id']}. {c['crop_name'].title():<12}  {c['season_info']}")
        print(f"       Presyo: {c['price_guide']}")
    cid = get_int("  Pumili (ID): ", mn=1, mx=len(crops))
    chosen = next(c for c in crops if c["crop_id"] == cid)
    return chosen

def pick_expense_type():
    types = run_query("SELECT * FROM expense_types ORDER BY type_id", fetch=True)
    print("\n  Uri ng gastos:")
    for t in types:
        print(f"    {t['type_id']}. {t['type_name'].title()}")
    tid = get_int("  Pumili (ID): ", mn=1, mx=len(types))
    return next(t for t in types if t["type_id"] == tid)


PALAY_LEVELS = {
    "1": ("Di-pa-naproseso (raw paddy)",   12.0, 14.0),
    "2": ("Naproseso (processed)",         24.0, 24.0),
    "3": ("Gilingan (milled rice)",        32.5, 32.5),
}


# ══════════════════════════════════════════════════════════
#  CROP SEASON CALENDAR
# ══════════════════════════════════════════════════════════

def show_season_calendar():
    cls()
    hdr("CROP SEASON CALENDAR — BARAS, RIZAL")
    back_hint()
    crops = run_query("SELECT * FROM crops ORDER BY crop_id", fetch=True)
    print(f"\n  {'PANANIM':<14} {'PANAHON / SEASON':<35} {'GABAY SA PRESYO'}")
    sep("─")
    for c in crops:
        print(f"  {c['crop_name'].title():<14} {c['season_info']:<35} {c['price_guide']}")
    sep("─")
    print("\n  PALAY PRICE GUIDE:")
    print("    1. Di-pa-naproseso (raw paddy) : ₱12.00 – ₱14.00 / kg")
    print("    2. Naproseso (processed)       : ₱24.00 / kg")
    print("    3. Gilingan (milled rice)      : ₱32.50 / kg")
    pause()


# ══════════════════════════════════════════════════════════
#  ADD CROP CYCLE
# ══════════════════════════════════════════════════════════

def add_crop_cycle():
    cls()
    hdr("BAGONG CROP CYCLE / NEW CROP CYCLE")
    back_hint()

    crop = pick_crop()
    season = get_str("\n  Pangalan ng season (hal. Wet 2025): ", default="Season 1")
    start_date = get_date("  Petsa ng pagtatanim (YYYY-MM-DD) [blank = ngayon]: ")

    cycle_id = run_query(
        "INSERT INTO crop_cycles (crop_id, season, start_date) VALUES (%s, %s, %s)",
        (crop["crop_id"], season, start_date)
    )
    print(f"\n  ✔ Crop cycle created! (ID #{cycle_id})")

    # Expenses
    print("\n  ── MGA GASTOS / EXPENSES ───────────────────────")
    while True:
        more = get_yn("  Magdagdag ng gastos? (y/n): ")
        if more != "y":
            break
        etype = pick_expense_type()
        amount = get_float("  Halaga (₱): ", mn=0.01)
        date = get_date()
        note = get_str("  Nota (optional): ", default="")
        is_log = 1 if etype["type_name"] == "lulan / transport to market" else 0
        run_query(
            "INSERT INTO expenses (cycle_id, type_id, amount, expense_date, note, is_logistics) VALUES (%s,%s,%s,%s,%s,%s)",
            (cycle_id, etype["type_id"], amount, date, note, is_log)
        )
        print(f"  ✔ Naidagdag: {etype['type_name'].title()} – {peso(amount)}")

    # Logistics
    print("\n  ── LOGISTIK / TRANSPORT COST ───────────────────")
    add_log = get_yn("  Magdagdag ng transport cost? (y/n): ")
    if add_log == "y":
        log_amount = get_float("  Transport cost (₱): ", mn=0)
        log_note = get_str("  Destinasyon / Note: ", default="")
        transport_type = run_query(
            "SELECT type_id FROM expense_types WHERE type_name = 'lulan / transport to market'",
            fetch=True
        )
        if transport_type:
            run_query(
                "INSERT INTO expenses (cycle_id, type_id, amount, expense_date, note, is_logistics) VALUES (%s,%s,%s,%s,%s,1)",
                (cycle_id, transport_type[0]["type_id"], log_amount, get_date(), log_note)
            )
            print(f"  ✔ Transport cost: {peso(log_amount)}")

    # Harvest
    print("\n  ── DETALYE NG ANI / HARVEST DETAILS ────────────")
    if get_yn("  I-input na ang detalye ng ani? (y/n): ") == "y":
        save_harvest(cycle_id, crop["crop_name"])

    print(f"\n  ✔ Tapos na! Crop cycle #{cycle_id} – {crop['crop_name'].title()}, {season}")
    pause()


def save_harvest(cycle_id, crop_name):
    yield_kg = get_float("  Kabuuang ani (kg): ", mn=0)

    if crop_name == "palay":
        print("\n  Antas ng proseso ng palay:")
        for k, (label, lo, hi) in PALAY_LEVELS.items():
            rng = f"₱{lo:.2f}" if lo == hi else f"₱{lo:.2f}–₱{hi:.2f}"
            print(f"    {k}. {label}  ({rng}/kg)")
        level = get_str("  Piliin (1/2/3): ", default="1")
        label, lo, hi = PALAY_LEVELS.get(level, PALAY_LEVELS["1"])
        price = get_float(f"  Presyo/kg (guide ₱{lo:.2f}–₱{hi:.2f}) ₱: ", mn=0)
        proc = label
    else:
        price = get_float("  Presyo bawat kilo (₱): ", mn=0)
        proc = None

    date = get_date("  Petsa ng ani: ")

    run_query("DELETE FROM harvests WHERE cycle_id = %s", (cycle_id,))
    run_query(
        "INSERT INTO harvests (cycle_id, yield_kg, price_per_kg, harvest_date, processing_level) VALUES (%s,%s,%s,%s,%s)",
        (cycle_id, yield_kg, price, date, proc)
    )
    print(f"  ✔ Harvest saved: {yield_kg} kg × {peso(price)}/kg = {peso(yield_kg * price)}")


# ══════════════════════════════════════════════════════════
#  ADD EXPENSE / UPDATE HARVEST
# ══════════════════════════════════════════════════════════

def add_expense_to_existing():
    cls(); hdr("DAGDAG NA GASTOS / ADD EXPENSE")
    back_hint()
    list_brief()
    cid = get_int("  ID ng cycle: ", mn=1)
    cycle = run_query(
        "SELECT cc.*, c.crop_name FROM crop_cycles cc JOIN crops c ON cc.crop_id=c.crop_id WHERE cc.cycle_id=%s",
        (cid,), fetch=True
    )
    if not cycle:
        print("  ✘ Hindi nahanap."); pause(); return
    cycle = cycle[0]
    print(f"\n  Crop: {cycle['crop_name'].title()} – {cycle['season']}")
    etype = pick_expense_type()
    amount = get_float("  Halaga (₱): ", mn=0.01)
    date = get_date()
    note = get_str("  Nota: ", default="")
    is_log = 1 if etype["type_name"] == "lulan / transport to market" else 0
    run_query(
        "INSERT INTO expenses (cycle_id, type_id, amount, expense_date, note, is_logistics) VALUES (%s,%s,%s,%s,%s,%s)",
        (cid, etype["type_id"], amount, date, note, is_log)
    )
    print(f"  ✔ Naidagdag: {etype['type_name'].title()} – {peso(amount)}")
    pause()


def update_harvest():
    cls(); hdr("I-UPDATE ANG ANI / UPDATE HARVEST")
    back_hint()
    list_brief()
    cid = get_int("  ID ng cycle: ", mn=1)
    cycle = run_query(
        "SELECT cc.*, c.crop_name FROM crop_cycles cc JOIN crops c ON cc.crop_id=c.crop_id WHERE cc.cycle_id=%s",
        (cid,), fetch=True
    )
    if not cycle:
        print("  ✘ Hindi nahanap."); pause(); return
    cycle = cycle[0]
    print(f"\n  Crop: {cycle['crop_name'].title()} – {cycle['season']}")
    save_harvest(cid, cycle["crop_name"])
    pause()


# ══════════════════════════════════════════════════════════
#  DELETE — Option 9
# ══════════════════════════════════════════════════════════

def delete_records():
    cls()
    hdr("BURAHIN / DELETE RECORDS")
    back_hint()
    print("  Ano ang gusto mong burahin?")
    print("  1. Burahin ang isang CROP CYCLE (kasama lahat ng gastos at ani nito)")
    print("  2. Burahin ang isang EXPENSE sa isang cycle")
    sep("─")

    choice = get_int("  Pumili (1 o 2): ", mn=1, mx=2)

    if choice == 1:
        _delete_crop_cycle()
    else:
        _delete_expense()


def _delete_crop_cycle():
    cls()
    hdr("BURAHIN ANG CROP CYCLE")
    back_hint()
    list_brief()

    cid = get_int("  ID ng cycle na gusto mong burahin: ", mn=1)

    # Verify cycle exists
    cycle = run_query(
        "SELECT cc.*, c.crop_name FROM crop_cycles cc JOIN crops c ON cc.crop_id=c.crop_id WHERE cc.cycle_id=%s",
        (cid,), fetch=True
    )
    if not cycle:
        print("\n  ✘ Walang cycle na may ID na iyan.")
        pause()
        return
    cycle = cycle[0]

    # Show what will be deleted
    expense_count = run_query(
        "SELECT COUNT(*) as cnt FROM expenses WHERE cycle_id=%s", (cid,), fetch=True
    )
    has_harvest = run_query(
        "SELECT COUNT(*) as cnt FROM harvests WHERE cycle_id=%s", (cid,), fetch=True
    )
    exp_cnt = expense_count[0]["cnt"] if expense_count else 0
    harv_cnt = has_harvest[0]["cnt"] if has_harvest else 0

    print(f"\n  ⚠  BABALA! Mabubura ang sumusunod:")
    print(f"     Crop Cycle  : {cycle['crop_name'].title()} — {cycle['season']} (ID #{cid})")
    print(f"     Mga Gastos  : {exp_cnt} expense record(s)")
    print(f"     Harvest     : {'Meron' if harv_cnt else 'Wala'}")
    sep("─")

    confirm = get_yn("  Sigurado ka bang gusto mong burahin ito? (y/n): ")
    if confirm != "y":
        print("\n  ✘ Hindi binura. Bumabalik sa menu...")
        pause()
        return

    # Delete — expenses and harvests auto-deleted via ON DELETE CASCADE
    run_query("DELETE FROM crop_cycles WHERE cycle_id = %s", (cid,))
    print(f"\n  ✔ Na-delete na ang crop cycle #{cid} ({cycle['crop_name'].title()}, {cycle['season']})")
    print(f"     kasama ang {exp_cnt} expense(s) at harvest data nito.")
    pause()


def _delete_expense():
    cls()
    hdr("BURAHIN ANG EXPENSE")
    back_hint()
    list_brief()

    cid = get_int("  ID ng cycle: ", mn=1)

    # Verify cycle exists
    cycle = run_query(
        "SELECT cc.*, c.crop_name FROM crop_cycles cc JOIN crops c ON cc.crop_id=c.crop_id WHERE cc.cycle_id=%s",
        (cid,), fetch=True
    )
    if not cycle:
        print("\n  ✘ Walang cycle na may ID na iyan.")
        pause()
        return
    cycle = cycle[0]

    # List expenses for that cycle
    expenses = run_query(
        """SELECT e.expense_id, e.expense_date, et.type_name, e.amount, e.note
           FROM expenses e
           JOIN expense_types et ON e.type_id = et.type_id
           WHERE e.cycle_id = %s
           ORDER BY e.expense_date""",
        (cid,), fetch=True
    )

    if not expenses:
        print(f"\n  Walang expenses ang cycle na ito ({cycle['crop_name'].title()}, {cycle['season']}).")
        pause()
        return

    print(f"\n  Mga Gastos ng {cycle['crop_name'].title()} — {cycle['season']}:")
    sep("─")
    print(f"  {'EXP ID':<8} {'Petsa':<12} {'Uri':<30} {'Halaga':>10}  Nota")
    sep("─")
    for e in expenses:
        print(f"  {e['expense_id']:<8} {str(e['expense_date']):<12} {e['type_name'].title():<30} {peso(e['amount']):>10}  {e['note'] or ''}")
    sep("─")

    eid = get_int("  Expense ID na gusto mong burahin: ", mn=1)

    # Verify expense belongs to this cycle
    target = next((e for e in expenses if e["expense_id"] == eid), None)
    if not target:
        print("\n  ✘ Hindi nahanap ang expense na iyan sa cycle na ito.")
        pause()
        return

    print(f"\n  ⚠  BABALA! Mabubura ang:")
    print(f"     {str(target['expense_date'])}  {target['type_name'].title()}  {peso(target['amount'])}  {target['note'] or ''}")
    sep("─")

    confirm = get_yn("  Sigurado ka bang gusto mong burahin ito? (y/n): ")
    if confirm != "y":
        print("\n  ✘ Hindi binura. Bumabalik sa menu...")
        pause()
        return

    run_query("DELETE FROM expenses WHERE expense_id = %s", (eid,))
    print(f"\n  ✔ Na-delete na ang expense ID #{eid}.")
    pause()


# ══════════════════════════════════════════════════════════
#  REPORTS
# ══════════════════════════════════════════════════════════

def list_brief():
    rows = run_query(
        "SELECT cycle_id, crop_name, season, total_expenses, yield_kg FROM view_cycle_summary ORDER BY cycle_id",
        fetch=True
    )
    print()
    print(f"  {'ID':<4} {'Pananim':<12} {'Season':<16} {'Gastos':>12} {'Ani':>10}")
    sep("─")
    for r in rows:
        ani = f"{float(r['yield_kg']):.1f} kg" if r["yield_kg"] else "—"
        print(f"  {r['cycle_id']:<4} {r['crop_name'].title():<12} {r['season']:<16} {peso(r['total_expenses']):>12} {ani:>10}")
    print()


def summary_report():
    cls(); hdr("SUMMARY REPORT")
    back_hint()
    list_brief()
    cid = get_int("  ID ng cycle: ", mn=1)

    row = run_query("SELECT * FROM view_cycle_summary WHERE cycle_id = %s", (cid,), fetch=True)
    if not row:
        print("  ✘ Hindi nahanap."); pause(); return
    r = row[0]

    expenses = run_query(
        """SELECT e.expense_date, et.type_name, e.amount, e.note, e.is_logistics
           FROM expenses e
           JOIN expense_types et ON e.type_id = et.type_id
           WHERE e.cycle_id = %s
           ORDER BY e.expense_date""",
        (cid,), fetch=True
    )
    breakdown = run_query(
        "SELECT * FROM view_expense_breakdown WHERE cycle_id = %s ORDER BY type_total DESC",
        (cid,), fetch=True
    )

    cls()
    sep()
    print("  FARM SUMMARY REPORT — BARAS, RIZAL")
    print(f"  Pananim  : {r['crop_name'].title()}")
    print(f"  Season   : {r['season']}")
    print(f"  Simula   : {r['start_date']}")
    sep("─")

    print("\n  MGA GASTOS / EXPENSES")
    sep("─")
    if expenses:
        for e in expenses:
            tag = " [logistics]" if e["is_logistics"] else ""
            label = e["type_name"].title() + tag
            print(f"  {e['expense_date']}  {label:<38} {peso(e['amount']):>10}  {e['note'] or ''}")
    else:
        print("  (walang gastos na naitala)")
    sep("─")
    print(f"  {'KABUUANG GASTOS / TOTAL EXPENSES':<42} {peso(r['total_expenses']):>10}")
    if r["logistics_cost"]:
        print(f"    └ Logistics                              {peso(r['logistics_cost']):>10}")

    if breakdown:
        print("\n  DISTRIBUSYON NG GASTOS / EXPENSE BREAKDOWN")
        sep("─")
        BAR_W = 20
        for b in breakdown:
            bars = int(float(b["percentage"]) / 100 * BAR_W)
            print(f"  {b['type_name'].title():<36} {'█'*bars:<20} {b['percentage']:>5}%  {peso(b['type_total']):>10}")

    print("\n  ANI / HARVEST")
    sep("─")
    if r["yield_kg"]:
        net = float(r["net_profit_loss"])
        arrow = "▲" if net >= 0 else "▼"
        if r["processing_level"]:
            print(f"  Antas ng proseso : {r['processing_level']}")
        print(f"  Petsa ng ani     : {r['harvest_date']}")
        print(f"  Kabuuang ani     : {float(r['yield_kg']):,.2f} kg")
        print(f"  Presyo/kg        : {peso(r['price_per_kg'])}")
        sep("─")
        print(f"  {'KABUUANG KITA / TOTAL REVENUE':<42} {peso(r['revenue']):>10}")
        print(f"  {'KABUUANG GASTOS / TOTAL EXPENSES':<42} {peso(r['total_expenses']):>10}")
        sep("─")
        print(f"  {r['status']:<42} {arrow} {peso(abs(net)):>8}")
        te = float(r["total_expenses"])
        if te > 0:
            roi = net / te * 100
            print(f"  {'ROI':<42} {roi:>+.1f}%")
    else:
        print("  (hindi pa naitala ang ani)")

    sep()
    print("\n  (I-print ang screen na ito para sa dokumentasyon)")
    pause()


def all_cycles_overview():
    cls(); hdr("LAHAT NG CROP CYCLE — OVERVIEW")
    back_hint()
    rows = run_query("SELECT * FROM view_cycle_summary ORDER BY cycle_id", fetch=True)
    if not rows:
        print("  Walang rekord."); pause(); return

    print(f"  {'ID':<4} {'Pananim':<12} {'Season':<14} {'Kita':>12} {'Gastos':>12} {'Net':>12}")
    sep("─")
    for r in rows:
        rev_s = peso(r["revenue"]) if r["revenue"] else "—"
        net = float(r["net_profit_loss"])
        net_s = ("+" if net >= 0 else "") + peso(abs(net)) if r["revenue"] else "—"
        print(f"  {r['cycle_id']:<4} {r['crop_name'].title():<12} {r['season']:<14} {rev_s:>12} {peso(r['total_expenses']):>12} {net_s:>12}")

    sep("─")
    t_rev = sum(float(r["revenue"]) for r in rows if r["revenue"])
    t_exp = sum(float(r["total_expenses"]) for r in rows)
    t_net = t_rev - t_exp
    status = "TUBO" if t_net >= 0 else "LUGI"
    print(f"  {'GRAND TOTAL':<30} {peso(t_rev):>12} {peso(t_exp):>12} {peso(t_net):>12}")
    print(f"\n  Overall: {status} ng {peso(abs(t_net))}")
    sep()
    pause()


def expense_vs_income_analysis():
    rows = run_query("SELECT * FROM view_income_vs_expense ORDER BY net DESC", fetch=True)
    harvested = [r for r in rows if r["total_revenue"]]
    if not harvested:
        print("\n  Walang crop cycle na may ani pa."); pause(); return

    cls(); hdr("EXPENSE VS. INCOME ANALYSIS")
    back_hint()
    print(f"\n  {'Pananim':<12} {'Season':<14} {'Gastos':>12} {'Kita':>12} {'Net':>12} {'ROI':>8}")
    sep("─")
    for r in harvested:
        net = float(r["net"])
        roi = float(r["roi_percent"]) if r["roi_percent"] else 0
        print(f"  {r['crop_name'].title():<12} {r['season']:<14} {peso(r['total_expenses']):>12} {peso(r['total_revenue']):>12} {peso(net):>12} {roi:>+.1f}%")

    sep("─")
    t_exp = sum(float(r["total_expenses"]) for r in harvested)
    t_rev = sum(float(r["total_revenue"]) for r in harvested)
    t_net = t_rev - t_exp
    t_roi = (t_net / t_exp * 100) if t_exp else 0
    print(f"  {'TOTAL':<26} {peso(t_exp):>12} {peso(t_rev):>12} {peso(t_net):>12} {t_roi:>+.1f}%")

    print("\n  KITA vs GASTOS (bar):")
    sep("─")
    max_val = max(max(float(r["total_expenses"]), float(r["total_revenue"])) for r in harvested)
    BAR_W = 28
    for r in harvested:
        te = float(r["total_expenses"])
        rv = float(r["total_revenue"])
        eb = int((te / max_val) * BAR_W)
        rb = int((rv / max_val) * BAR_W)
        print(f"  {r['crop_name'].title()} {r['season']}")
        print(f"    Gastos : {'█'*eb} {peso(te)}")
        print(f"    Kita   : {'░'*rb} {peso(rv)}")
    sep()
    pause()


# ══════════════════════════════════════════════════════════
#  MAIN MENU
# ══════════════════════════════════════════════════════════

def main():
    print("\n  Connecting to MySQL database...")
    conn = get_connection()
    conn.close()
    print("  ✔ Connected to farm_analyzer_db!\n")

    while True:
        cls()
        hdr("FARM EXPENSE & HARVEST PROFIT ANALYZER")
        print("  Para sa mga Magsasaka ng Baras, Rizal")
        print("  CC 103 — Problem Set #3  |  MySQL Edition")
        sep("─")
        print("  1. Bagong crop cycle (gastos + ani)")
        print("  2. Dagdag na gastos sa existing cycle")
        print("  3. I-update ang detalye ng ani")
        print("  4. Summary report (per cycle)")
        print("  5. Lahat ng cycle — overview")
        print("  6. Expense vs. Income analysis")
        print("  7. Listahan ng lahat ng cycle")
        print("  8. Crop season calendar")
        print("  9. Burahin / Delete (cycle o expense)")
        print("  0. Lumabas / Exit")
        sep("─")
        print("  💡 TIP: Sa kahit anong screen, mag-type ng 0 o B para")
        print("          bumalik sa main menu nang hindi mag-re-restart.")
        sep("─")

        choice = input("  Pumili: ").strip()

        try:
            if choice == "1":
                add_crop_cycle()
            elif choice == "2":
                add_expense_to_existing()
            elif choice == "3":
                update_harvest()
            elif choice == "4":
                summary_report()
            elif choice == "5":
                all_cycles_overview()
            elif choice == "6":
                expense_vs_income_analysis()
            elif choice == "7":
                cls(); hdr("LAHAT NG CROP CYCLE")
                back_hint()
                list_brief()
                pause()
            elif choice == "8":
                show_season_calendar()
            elif choice == "9":
                delete_records()
            elif choice == "0":
                print("\n  Salamat! Maligayang pagsasaka! 🌾\n")
                break
            else:
                print("  ✘ Hindi wastong pagpipilian. Pumili ng 0–9.")
                pause()

        except GoBack:
            # User typed 0 or B somewhere inside a function
            # Just loop back to show the main menu again
            pass

if __name__ == "__main__":
    main()
