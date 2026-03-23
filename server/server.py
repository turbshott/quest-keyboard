import os
from flask import Flask
from flask_sock import Sock

app = Flask(__name__, static_folder="../client", static_url_path="")
sock = Sock(app)

clients = []
last_message = None

@app.route("/")
def index():
    return app.send_static_file("sender.html")

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