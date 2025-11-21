# dashboard.py
from flask import Flask, render_template, send_file, request, abort, jsonify
import sqlite3, hashlib, csv, os, io, time
from datetime import datetime, timedelta, date

DB = "results.db"  # path to your sqlite DB
app = Flask(__name__, template_folder="templates")

def sha256_hexdigest(s: str) -> str:
    return hashlib.sha256((s or "").encode("utf-8")).hexdigest()

def mask_email(e: str) -> str:
    if not e:
        return ""
    e = e.strip()
    if "@" not in e:
        return e[0] + "****"
    local, domain = e.split("@", 1)
    if len(local) <= 1:
        local_masked = local + "****"
    else:
        local_masked = local[0] + "****"
    return f"{local_masked}@{domain}"

def mask_password(p: str) -> str:
    if not p:
        return ""
    return "•" * 8

def fetch_rows(limit=1000):
    if not os.path.exists(DB):
        return []
    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    try:
        cur.execute("SELECT id, email, password, ts, campaign FROM submissions ORDER BY id DESC LIMIT ?", (limit,))
    except sqlite3.OperationalError:
        cur.execute("SELECT id, email, password, ts FROM submissions ORDER BY id DESC LIMIT ?", (limit,))
    rows = cur.fetchall()
    conn.close()
    return rows

@app.route("/")
def index():
    limit = int(request.args.get("limit", 500))
    raw_rows = fetch_rows(limit=limit)
    display = []
    for r in raw_rows:
        if len(r) == 5:
            rid, email, password, ts, campaign = r
        else:
            rid, email, password, ts = r
            campaign = ""
        email_hash = sha256_hexdigest(email or "")
        pwd_hash = sha256_hexdigest((email or "") + "::" + (password or ""))
        display.append({
            "id": rid,
            "email_masked": mask_email(email),
            "email_hash": email_hash[:16],
            "password_masked": mask_password(password),
            "pwd_hash": pwd_hash[:16],
            "ts": datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S") if ts else "",
            "campaign": campaign or ""
        })
    return render_template("dashboard.html", rows=display, total=len(display))

@app.route("/data.json")
def data_json():
    # Returns aggregated data for charts:
    # - submission counts per day for last N days
    # - counts per campaign
    days = int(request.args.get("days", 30))
    # fetch more rows to ensure coverage
    raw = fetch_rows(limit=10000)

    # build by-day buckets for last `days` days
    today = date.today()
    day_counts = {}
    for i in range(days):
        d = today - timedelta(days=(days-1-i))
        day_counts[d.strftime("%Y-%m-%d")] = 0

    # campaigns counts
    campaign_counts = {}

    for r in raw:
        if len(r) == 5:
            _id, email, pwd, ts, campaign = r
        else:
            _id, email, pwd, ts = r
            campaign = ""
        if ts:
            try:
                d = datetime.fromtimestamp(int(ts)).date().strftime("%Y-%m-%d")
            except Exception:
                d = ""
            if d in day_counts:
                day_counts[d] += 1
        # campaigns aggregation
        key = campaign or "unknown"
        campaign_counts[key] = campaign_counts.get(key, 0) + 1

    return jsonify({
        "by_day": {
            "labels": list(day_counts.keys()),
            "counts": list(day_counts.values())
        },
        "by_campaign": {
            "labels": list(campaign_counts.keys()),
            "counts": list(campaign_counts.values())
        }
    })

@app.route("/export_anonymized.csv")
def export_anonymized():
    raw_rows = fetch_rows(limit=10000)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id","email_sha256","pwd_sha256","ts","campaign"])
    for r in raw_rows:
        if len(r) == 5:
            rid, email, password, ts, campaign = r
        else:
            rid, email, password, ts = r
            campaign = ""
        email_hash = sha256_hexdigest(email or "")
        pwd_hash = sha256_hexdigest((email or "") + "::" + (password or ""))
        writer.writerow([rid, email_hash, pwd_hash, ts, campaign])
    output.seek(0)
    buf = io.BytesIO(output.getvalue().encode("utf-8"))
    filename = f"results_anonymized_{int(time.time())}.csv"
    return send_file(buf, mimetype="text/csv", as_attachment=True, download_name=filename)

@app.route("/raw")
def raw_view():
    key = request.args.get("key","")
    if key != "showraw_localonly":
        abort(403)
    rows = fetch_rows(limit=2000)
    # convert timestamps for readability
    out = []
    for r in rows:
        if len(r) == 5:
            rid, email, pwd, ts, campaign = r
        else:
            rid, email, pwd, ts = r
            campaign = ""
        out.append([rid, email, pwd, datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S") if ts else "", campaign])
    return {"rows": out}

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5001, debug=False)
