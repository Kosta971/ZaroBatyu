from flask import Flask, request, redirect, url_for, session, jsonify, render_template_string from flask_sqlalchemy import SQLAlchemy from flask_socketio import SocketIO, emit from werkzeug.security import generate_password_hash, check_password_hash import requests import os

app = Flask(name) app.secret_key = os.environ.get('SECRET_KEY', 'your_secret_key') app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db' db = SQLAlchemy(app) socketio = SocketIO(app, cors_allowed_origins="*")

class User(db.Model): id = db.Column(db.Integer, primary_key=True) username = db.Column(db.String(150), unique=True, nullable=False) password = db.Column(db.String(150), nullable=False)

@app.before_first_request def create_tables(): db.create_all()

login_html = '''

<h2>Login</h2>
<form method="POST">
    <input type="text" name="username" placeholder="Username" required><br>
    <input type="password" name="password" placeholder="Password" required><br>
    <button type="submit">Login</button>
</form>
<p>Don't have an account? <a href="/register">Register here</a></p>
'''register_html = '''

<h2>Register</h2>
<form method="POST">
    <input type="text" name="username" placeholder="Username" required><br>
    <input type="password" name="password" placeholder="Password" required><br>
    <button type="submit">Register</button>
</form>
<p>Already have an account? <a href="/login">Login here</a></p>
'''dashboard_html = '''

<h1>Welcome, {{ username }}!</h1>
<ul>
    <li><a href="/chat">Chat</a></li>
    <li><a href="/exchange">Crypto Exchange</a></li>
    <li><a href="/payment">Donate</a></li>
    <li><a href="/logout">Logout</a></li>
</ul>
'''chat_html = '''

<h2>Chat Room</h2>
<div id="messages"></div>
<input id="message" placeholder="Type a message...">
<button onclick="sendMessage()">Send</button>
<script src="https://cdn.socket.io/4.6.1/socket.io.min.js"></script>
<script>
const socket = io();
const messages = document.getElementById("messages");
socket.on("receive_message", data => {
    const msg = document.createElement("div");
    msg.textContent = `${data.username}: ${data.message}`;
    messages.appendChild(msg);
});
function sendMessage() {
    const input = document.getElementById("message");
    const text = input.value;
    if (text.trim() !== '') {
        socket.emit("send_message", { message: text });
        input.value = '';
    }
}
</script>
'''exchange_html = '''

<h2>Current Crypto Prices</h2>
<button onclick="loadRates()">Load Prices</button>
<div id="prices"></div>
<script>
function loadRates() {
    fetch("/exchange-rate")
        .then(res => res.json())
        .then(data => {
            document.getElementById("prices").innerHTML = `BTC: $${data.bitcoin.usd}<br>ETH: $${data.ethereum.usd}`;
        });
}
</script>
'''payment_html = '''

<h2>Donate</h2>
<button onclick="createPayment()">Donate 10 USD in BTC</button>
<pre id="result"></pre>
<script>
function createPayment() {
    fetch("/create-payment")
        .then(res => res.json())
        .then(data => {
            document.getElementById("result").textContent = JSON.stringify(data, null, 2);
        });
}
</script>
'''@app.route('/') def index(): if 'user_id' in session: return render_template_string(dashboard_html, username=session.get('username')) return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST']) def register(): if request.method == 'POST': username = request.form['username'] password = generate_password_hash(request.form['password']) if User.query.filter_by(username=username).first(): return 'User exists!' db.session.add(User(username=username, password=password)) db.session.commit() return redirect(url_for('login')) return render_template_string(register_html)

@app.route('/login', methods=['GET', 'POST']) def login(): if request.method == 'POST': user = User.query.filter_by(username=request.form['username']).first() if user and check_password_hash(user.password, request.form['password']): session['user_id'] = user.id session['username'] = user.username return redirect(url_for('index')) return 'Invalid credentials!' return render_template_string(login_html)

@app.route('/logout') def logout(): session.clear() return redirect(url_for('login'))

@app.route('/chat') def chat(): if 'user_id' not in session: return redirect(url_for('login')) return render_template_string(chat_html)

@socketio.on('send_message') def handle_send(data): emit('receive_message', {'username': session['username'], 'message': data['message']}, broadcast=True)

@app.route('/exchange') def exchange(): return render_template_string(exchange_html)

@app.route('/exchange-rate') def exchange_rate(): res = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum&vs_currencies=usd").json() return jsonify(res)

@app.route('/payment') def payment(): return render_template_string(payment_html)

@app.route('/create-payment') def create_payment(): api_key = os.environ.get('NOWPAYMENTS_API_KEY', 'your_nowpayments_api_key') payload = { "price_amount": 10, "price_currency": "usd", "pay_currency": "btc", "ipn_callback_url": "https://yourdomain.com/callback", } headers = { "x-api-key": api_key, "Content-Type": "application/json" } r = requests.post("https://api.nowpayments.io/v1/payment", json=payload, headers=headers) return r.json()

if name == "main": socketio.run(app, host='0.0.0.0', port=int(os.environ.get("PORT", 5000)), debug=True)

