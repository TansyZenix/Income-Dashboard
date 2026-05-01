import json
import os
import webbrowser
from datetime import datetime, timedelta
from threading import Timer

from flask import Flask, redirect, render_template, request, url_for

app = Flask(__name__)
DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data.json")


def load_data():
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


SORT_FIELDS = {
    "id": "id",
    "completion_date": "completion_date",
    "expected_settlement_date": "expected_settlement_date",
    "amount": "amount",
    "fee": "fee",
}


@app.route("/")
def index():
    records = load_data()

    # ── 兼容旧数据：默认 fee = 0 ──
    for r in records:
        r.setdefault("fee", 0)

    # ── 区分未完成 / 已完成 ──
    incomplete = [r for r in records if not r.get("completed", True)]
    completed_records = [r for r in records if r.get("completed", True)]

    # ── 筛选（仅对已完成记录） ──
    filter_settled = request.args.get("filter_settled", "all")
    if filter_settled == "settled":
        completed_records = [r for r in completed_records if r["settled"]]
    elif filter_settled == "unsettled":
        completed_records = [r for r in completed_records if not r["settled"]]

    # ── 排序（仅对已完成记录） ──
    sort_by = request.args.get("sort_by", "id")
    sort_order = request.args.get("sort_order", "desc")

    if sort_by in SORT_FIELDS:
        key = SORT_FIELDS[sort_by]
        reverse = sort_order == "desc"
        # 金额按数字排序，其余按字符串
        if key in ("amount", "fee"):
            completed_records.sort(key=lambda r: r[key], reverse=reverse)
        else:
            completed_records.sort(key=lambda r: r[key], reverse=reverse)

    total = sum(r["amount"] - r["fee"] for r in completed_records)
    pending = sum(r["amount"] - r["fee"] for r in completed_records if not r["settled"])
    settled = sum(r["amount"] - r["fee"] for r in completed_records if r["settled"])
    in_progress_amount = sum(r["amount"] for r in incomplete)
    total_original = sum(r["amount"] for r in completed_records)
    return render_template(
        "index.html",
        records=completed_records,
        incomplete=incomplete,
        total=total,
        pending=pending,
        settled=settled,
        in_progress_amount=in_progress_amount,
        total_original=total_original,
        sort_by=sort_by,
        sort_order=sort_order,
        filter_settled=filter_settled,
    )


@app.route("/add", methods=["POST"])
def add():
    records = load_data()
    is_incomplete = "status_incomplete" in request.form
    new_record = {
        "id": request.form["id"],
        "type": request.form["type"],
        "path": request.form["path"],
        "completion_date": "",
        "expected_settlement_date": "",
        "amount": int(request.form["amount"]),
        "fee": 0,
        "completed": not is_incomplete,
        "settled": False,
    }
    if not is_incomplete:
        completion_date = request.form["completion_date"]
        new_record["completion_date"] = completion_date
        new_record["expected_settlement_date"] = (
            datetime.strptime(completion_date, "%Y-%m-%d") + timedelta(days=5)
        ).strftime("%Y-%m-%d")
    # 如果同编号存在则覆盖
    records = [r for r in records if r["id"] != new_record["id"]]
    records.append(new_record)
    save_data(records)
    return redirect(url_for("index"))


@app.route("/settle/<record_id>")
def settle(record_id):
    records = load_data()
    for r in records:
        if r["id"] == record_id:
            r["settled"] = not r["settled"]
            break
    save_data(records)
    return redirect(url_for("index"))


@app.route("/complete/<record_id>")
def complete(record_id):
    records = load_data()
    for r in records:
        if r["id"] == record_id:
            r["completed"] = True
            r["completion_date"] = datetime.now().strftime("%Y-%m-%d")
            r["expected_settlement_date"] = (
                datetime.now() + timedelta(days=5)
            ).strftime("%Y-%m-%d")
            break
    save_data(records)
    return redirect(url_for("index"))


@app.route("/uncomplete/<record_id>")
def uncomplete(record_id):
    records = load_data()
    for r in records:
        if r["id"] == record_id:
            r["completed"] = False
            r["completion_date"] = ""
            r["expected_settlement_date"] = ""
            r["settled"] = False
            break
    save_data(records)
    return redirect(url_for("index"))


@app.route("/update_fee", methods=["POST"])
def update_fee():
    records = load_data()
    record_id = request.form["id"]
    fee = int(request.form["fee"])
    for r in records:
        if r["id"] == record_id:
            r["fee"] = fee
            break
    save_data(records)
    return redirect(url_for("index"))


@app.route("/delete/<record_id>")
def delete(record_id):
    records = load_data()
    records = [r for r in records if r["id"] != record_id]
    save_data(records)
    return redirect(url_for("index"))


def open_browser():
    webbrowser.open("http://127.0.0.1:9000")


if __name__ == "__main__":
    Timer(1.5, open_browser).start()
    app.run(debug=False, port=9000)
