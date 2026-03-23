import os
from flask import Flask, request, redirect, url_for, session, render_template
from flask_sock import Sock
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__, static_folder="static", static_url_path="")
app.secret_key = os.environ.get("SECRET_KEY", "quest-keyboard-fallback-secret-2026")
sock = Sock(app)

def init_db():
    con = sqlite3.connect("users.db")
    cur = con.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL
        )
    """)
    con.commit()
    con.close()

init_db()

clients = []
last_message = None

@app.route("/register", methods=["GET", "POST"])
def register():
    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        confirm = request.form.get("confirm", "").strip()
        if not username or not password:
            error = "Username and password are required."
        elif password != confirm:
            error = "Passwords do not match."
        else:
            con = sqlite3.connect("users.db")
            cur = con.cursor()
            try:
                cur.execute(
                    "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                    (username, generate_password_hash(password))
                )
                con.commit()
                cur.execute("SELECT id FROM users WHERE username = ?", (username,))
                row = cur.fetchone()
                session["user_id"] = row[0]
                session["username"] = username
                return redirect(url_for("index"))
            except sqlite3.IntegrityError:
                error = "Username already taken."
            finally:
                con.close()
    return render_template("register.html", error=error)

@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        con = sqlite3.connect("users.db")
        cur = con.cursor()
        cur.execute("SELECT id, password_hash FROM users WHERE username = ?", (username,))
        row = cur.fetchone()
        con.close()
        if row is None or not check_password_hash(row[1], password):
            error = "Invalid username or password."
        else:
            session["user_id"] = row[0]
            session["username"] = username
            return redirect(url_for("index"))
    return render_template("login.html", error=error)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/")
def index():
    if "user_id" not in session:
        return redirect(url_for("login"))
    user_agent = request.headers.get("User-Agent", "")
    if "OculusBrowser" in user_agent:
        return app.send_static_file("receiver.html")
    return render_template("sender.html")

@app.route("/sender")
def sender():
    if "user_id" not in session:
        return redirect(url_for("login"))
    return render_template("sender.html")

@app.route("/receiver")
def receiver():
    if "user_id" not in session:
        return redirect(url_for("login"))
    return render_template("receiver.html")

@sock.route("/ws")
def websocket(ws):
    global last_message
    clients.append(ws)

    if last_message is not None:
        ws.send(last_message)

    try:
        while True:
            message = ws.receive()
            if message is None:
                break
            last_message = message
            for client in list(clients):
                if client is not ws:
                    try:
                        client.send(message)
                    except:
                        clients.remove(client)
    finally:
        if ws in clients:
            clients.remove(ws)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)