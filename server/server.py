import os
from flask import Flask, request, redirect, url_for, session, render_template
from flask_sock import Sock
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

# create the Flask app and tell it where to find static files (JS, CSS)
# and HTML templates.
app = Flask(__name__, static_folder="static", static_url_path="")

# secret key is used to sign the session cookie so it can't be tampered with.
# read from an environment variable in production; fall back to a default for development.
app.secret_key = os.environ.get("SECRET_KEY", "quest-keyboard-fallback-secret-2026")

# attach flask-sock to the app so we can define WebSocket routes.
sock = Sock(app)

def init_db():
    # connect to (or create) the SQLite database file.
    con = sqlite3.connect("users.db")
    cur = con.cursor()
    # create the users table if it doesn't already exist.
    # each user has an auto-incrementing ID, a unique username, and a hashed password.
    # passwords are never stored in plain text.
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL
        )
    """)
    con.commit()
    con.close()

# run database setup once when the server starts.
init_db()

# both dicts are keyed by user_id.
# clients: maps each user to a list of their active WebSocket connections.
# last_message: maps each user to the last message they sent.
clients = {}
last_message = {}

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
                # hash the password before storing it.
                cur.execute(
                    "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                    (username, generate_password_hash(password))
                )
                con.commit()
                # fetch the new user's ID so we can log them in immediately.
                cur.execute("SELECT id FROM users WHERE username = ?", (username,))
                row = cur.fetchone()
                session["user_id"] = row[0]
                session["username"] = username
                return redirect(url_for("index"))
            except sqlite3.IntegrityError:
                # the UNIQUE constraint on username triggered (someone already has this name).
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
        # use the same error message whether the username or password is wrong.
        # separate messages would let someone probe which usernames exist.
        if row is None or not check_password_hash(row[1], password):
            error = "Invalid username or password."
        else:
            session["user_id"] = row[0]
            session["username"] = username
            return redirect(url_for("index"))
    return render_template("login.html", error=error)

@app.route("/logout")
def logout():
    # clear the session and send the user back to the login page.
    session.clear()
    return redirect(url_for("login"))

@app.route("/")
def index():
    if "user_id" not in session:
        return redirect(url_for("login"))
    # auto-detect the Quest browser by its user agent string and serve the receiver.
    # any other device (phone, laptop) gets the sender.
    user_agent = request.headers.get("User-Agent", "")
    if "OculusBrowser" in user_agent:
        return redirect(url_for("receiver"))
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
    # the flask session is only available during the HTTP handshake that upgrades
    # the connection to a WebSocket, so we capture user_id here before the loop starts.
    user_id = session.get("user_id")
    if user_id is None:
        ws.close()
        return

    # add this connection to the user's list, creating the list if it's their first connection.
    if user_id not in clients:
        clients[user_id] = []
    clients[user_id].append(ws)

    # send the most recent message immediately so a freshly loaded receiver isn't blank.
    if user_id in last_message:
        ws.send(last_message[user_id])

    try:
        while True:
            message = ws.receive()
            # none means the connection closed, exit the loop cleanly.
            if message is None:
                break
            last_message[user_id] = message
            # relay to all other connections belonging to the same user only.
            for client in list(clients[user_id]):
                if client is not ws:
                    try:
                        client.send(message)
                    except:
                        # if a send fails the client has disconnected — remove it.
                        clients[user_id].remove(client)
    finally:
        # always remove this connection when it ends, whether cleanly or due to an error.
        if ws in clients.get(user_id, []):
            clients[user_id].remove(ws)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)