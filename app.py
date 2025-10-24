from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
import os
import json
import cv2
import numpy as np
from datetime import datetime
import base64
import re

# CONFIG
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'root',
    'database': 'atm_app'
}
UPLOAD_FACES_DIR = 'faces'
MODEL_PATH = os.path.join(UPLOAD_FACES_DIR, 'trainer.yml')
CASCADE_PATH = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'

app = Flask(__name__)
app.secret_key = 'replace_with_secure_secret'

# ensure face dir exists
os.makedirs(UPLOAD_FACES_DIR, exist_ok=True)

# Helper to get DB connection
def get_db():
    return mysql.connector.connect(**DB_CONFIG)

# ----------------- Admin -----------------
@app.route('/admin/login', methods=['GET','POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == 'admin' and password == 'admin123':
            session['admin'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            return render_template('admin_login.html', error='Invalid credentials')
    return render_template('admin_login.html')

@app.route('/admin')
def admin_dashboard():
    if not session.get('admin'):
        return redirect(url_for('admin_login'))
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT account_number, type, amount, timestamp FROM transactions ORDER BY timestamp DESC LIMIT 200')
    txs = cursor.fetchall()
    cursor.execute('SELECT cash_available FROM atm_machine WHERE id=1')
    cash = cursor.fetchone()[0]
    conn.close()
    return render_template('admin_dashboard.html', transactions=txs, cash=cash)

@app.route('/admin/refill', methods=['POST'])
def admin_refill():
    if not session.get('admin'):
        return jsonify({'success': False, 'error':'Not authorized'})
    amount = float(request.form.get('amount', 0))
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('UPDATE atm_machine SET cash_available = cash_available + %s WHERE id=1', (amount,))
    conn.commit()
    conn.close()
    return redirect(url_for('admin_dashboard'))

# ----------------- User Registration -----------------
@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        acc = request.form.get('account_number')
        pwd = request.form.get('password')
        initial_deposit = request.form.get('initial_deposit')

        # Validation
        if not re.fullmatch(r'\d{10}', acc):
            flash("Account number must be exactly 10 digits")
            return redirect(url_for('register'))
        if len(pwd) < 8 or not re.search(r"[A-Z]", pwd) or not re.search(r"[a-z]", pwd) or not re.search(r"[0-9]", pwd):
            flash("Password must be at least 8 chars, include uppercase, lowercase, and number")
            return redirect(url_for('register'))
        try:
            initial_deposit = float(initial_deposit)
            if initial_deposit < 5000:
                flash("Initial deposit must be at least ₹5000")
                return redirect(url_for('register'))
        except:
            flash("Invalid deposit amount")
            return redirect(url_for('register'))

        pwd_hash = generate_password_hash(pwd)
        conn = get_db()
        cursor = conn.cursor()
        try:
            cursor.execute(
                'INSERT INTO users (name, account_number, password_hash, balance) VALUES (%s,%s,%s,%s)',
                (name, acc, pwd_hash, initial_deposit)
            )
            conn.commit()
            conn.close()
            flash("Registered successfully! Now you can register your face.")
            return redirect(url_for('login'))
        except mysql.connector.IntegrityError:
            conn.close()
            flash("Account already exists")
            return redirect(url_for('register'))

    return render_template('register.html')

# ----------------- Face Registration -----------------
@app.route('/register_face', methods=['POST'])
def register_face():
    payload = request.get_json()
    acc = payload.get('account_number')
    images = payload.get('images', [])
    if not acc or not images:
        return jsonify({'success': False, 'error':'Missing data'})
    
    acc_dir = os.path.join(UPLOAD_FACES_DIR, acc)
    os.makedirs(acc_dir, exist_ok=True)

    for idx, b64 in enumerate(images):
        header, data = b64.split(',',1)
        img_data = base64.b64decode(data)
        with open(os.path.join(acc_dir, f'{idx}.jpg'), 'wb') as f:
            f.write(img_data)

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET face_registered=1 WHERE account_number=%s', (acc,))
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'message':'Face images saved. Run training to update model.'})

# ----------------- Login -----------------
@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        acc = request.form.get('account_number')
        pwd = request.form.get('password')
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute('SELECT password_hash FROM users WHERE account_number=%s', (acc,))
        row = cursor.fetchone()
        conn.close()
        if row and check_password_hash(row[0], pwd):
            session['account_number'] = acc
            return redirect(url_for('dashboard'))
        flash("Invalid credentials")
        return redirect(url_for('login'))
    return render_template('login.html')

# ----------------- Face Login -----------------
@app.route('/face_login', methods=['POST'])
def face_login():
    payload = request.get_json()
    b64 = payload.get('image')
    if not b64:
        return jsonify({'success': False, 'error':'No image'})
    nparr = np.frombuffer(base64.b64decode(b64.split(',')[1]), np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    faces = cv2.CascadeClassifier(CASCADE_PATH).detectMultiScale(gray, 1.2, 5)
    if len(faces) == 0:
        return jsonify({'success': False, 'error':'No face detected'})

    recognizer = cv2.face.LBPHFaceRecognizer_create()
    if not os.path.exists(MODEL_PATH):
        return jsonify({'success': False, 'error':'Model not trained'})
    recognizer.read(MODEL_PATH)

    labels_path = os.path.join(UPLOAD_FACES_DIR, 'labels.json')
    if not os.path.exists(labels_path):
        return jsonify({'success': False, 'error':'No labels mapping'})
    labels = json.load(open(labels_path))

    for (x,y,w,h) in faces:
        roi = gray[y:y+h, x:x+w]
        label, confidence = recognizer.predict(cv2.resize(roi, (200,200)))
        if str(label) in labels and confidence < 80:
            session['account_number'] = labels[str(label)]
            return jsonify({'success': True, 'account_number': labels[str(label)]})
    return jsonify({'success': False, 'error':'No match'})

# ----------------- Dashboard -----------------
@app.route('/dashboard')
def dashboard():
    acc = session.get('account_number')
    if not acc:
        return redirect(url_for('login'))
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT name, balance FROM users WHERE account_number=%s', (acc,))
    row = cursor.fetchone()
    name, bal = row if row else ('Unknown', 0)
    cursor.execute('SELECT type, amount, timestamp FROM transactions WHERE account_number=%s ORDER BY timestamp DESC LIMIT 50', (acc,))
    txs = cursor.fetchall()
    conn.close()
    return render_template('dashboard.html', name=name, balance=bal, transactions=txs, account_number=acc)

# ----------------- Deposit/Withdraw -----------------
@app.route('/deposit', methods=['POST'])
def deposit():
    acc = session.get('account_number')
    if not acc:
        return jsonify({'success': False, 'error':'Not logged in'})
    amount = float(request.form.get('amount',0))
    if amount <= 0:
        return jsonify({'success': False, 'error':'Invalid amount'})
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET balance = balance + %s WHERE account_number=%s', (amount, acc))
    cursor.execute('INSERT INTO transactions (account_number, type, amount) VALUES (%s,%s,%s)', (acc,'deposit', amount))
    conn.commit()
    conn.close()
    return redirect(url_for('dashboard'))

@app.route('/withdraw', methods=['POST'])
def withdraw():
    acc = session.get('account_number')
    if not acc:
        return jsonify({'success': False, 'error':'Not logged in'})
    amount = float(request.form.get('amount',0))
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT balance FROM users WHERE account_number=%s', (acc,))
    bal = float(cursor.fetchone()[0])
    cursor.execute('SELECT cash_available FROM atm_machine WHERE id=1')
    atm_cash = float(cursor.fetchone()[0])
    if amount <= 0 or amount > bal:
        conn.close()
        return jsonify({'success': False, 'error':'Insufficient account funds'})
    if amount > atm_cash:
        conn.close()
        return jsonify({'success': False, 'error':'ATM has insufficient cash'})
    cursor.execute('UPDATE users SET balance = balance - %s WHERE account_number=%s', (amount, acc))
    cursor.execute('UPDATE atm_machine SET cash_available = cash_available - %s WHERE id=1', (amount,))
    cursor.execute('INSERT INTO transactions (account_number, type, amount) VALUES (%s,%s,%s)', (acc,'withdraw', amount))
    conn.commit()
    conn.close()
    return redirect(url_for('dashboard'))

@app.route('/')
def home():
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
