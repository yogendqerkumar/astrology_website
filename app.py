from flask import Flask, request, jsonify, render_template, send_from_directory, make_response
import sqlite3
import os
import json
from datetime import datetime
import uuid

app = Flask(__name__, template_folder='templates', static_folder='static')

# Manual CORS support
@app.after_request
def add_cors(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    response.headers['Access-Control-Allow-Methods'] = 'GET,POST,OPTIONS'
    return response

@app.before_request
def handle_options():
    if request.method == 'OPTIONS':
        r = make_response()
        r.headers['Access-Control-Allow-Origin'] = '*'
        r.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        r.headers['Access-Control-Allow-Methods'] = 'GET,POST,OPTIONS'
        return r

DB_PATH = 'astro_ayur.db'

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Users / Visitors table
    c.execute('''CREATE TABLE IF NOT EXISTS visitors (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        phone TEXT,
        password_hash TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')

    # Consultations (Doctor / Medicine chat)
    c.execute('''CREATE TABLE IF NOT EXISTS consultations (
        id TEXT PRIMARY KEY,
        visitor_name TEXT NOT NULL,
        visitor_email TEXT NOT NULL,
        visitor_phone TEXT,
        query TEXT NOT NULL,
        query_type TEXT NOT NULL,  -- 'medicine', 'astrology', 'appointment'
        status TEXT DEFAULT 'pending',  -- pending, replied, closed
        doctor_reply TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        replied_at TEXT
    )''')

    # Appointments table
    c.execute('''CREATE TABLE IF NOT EXISTS appointments (
        id TEXT PRIMARY KEY,
        visitor_name TEXT NOT NULL,
        visitor_email TEXT NOT NULL,
        visitor_phone TEXT NOT NULL,
        appointment_date TEXT NOT NULL,
        appointment_time TEXT NOT NULL,
        reason TEXT,
        status TEXT DEFAULT 'pending',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')

    # Astrology queries
    c.execute('''CREATE TABLE IF NOT EXISTS astrology_queries (
        id TEXT PRIMARY KEY,
        visitor_name TEXT NOT NULL,
        visitor_email TEXT NOT NULL,
        visitor_phone TEXT,
        birth_date TEXT,
        birth_time TEXT,
        birth_place TEXT,
        query TEXT NOT NULL,
        problem_area TEXT,  -- health, career, marriage, finance
        status TEXT DEFAULT 'pending',
        astrologer_reply TEXT,
        recommended_stone TEXT,
        recommended_remedy TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        replied_at TEXT
    )''')

    # Messages (chat messages within a consultation)
    c.execute('''CREATE TABLE IF NOT EXISTS messages (
        id TEXT PRIMARY KEY,
        consultation_id TEXT NOT NULL,
        sender TEXT NOT NULL,  -- 'visitor' or 'doctor'
        message TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (consultation_id) REFERENCES consultations(id)
    )''')

    conn.commit()
    conn.close()
    print("✅ Database initialized successfully.")

# ─── ROUTES ───────────────────────────────────────────────────────────────────

@app.route('/')
def home():
    return render_template('index.html')

# ── SIGN UP ──
@app.route('/api/signup', methods=['POST'])
def signup():
    data = request.get_json()
    name = data.get('name', '').strip()
    email = data.get('email', '').strip().lower()
    phone = data.get('phone', '').strip()

    if not name or not email:
        return jsonify({'success': False, 'message': 'नाम और ईमेल आवश्यक है।'}), 400

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        visitor_id = str(uuid.uuid4())
        c.execute('INSERT INTO visitors (id, name, email, phone) VALUES (?, ?, ?, ?)',
                  (visitor_id, name, email, phone))
        conn.commit()
        return jsonify({'success': True, 'message': 'स्वागत है! आपका पंजीकरण सफल रहा।', 'visitor_id': visitor_id})
    except sqlite3.IntegrityError:
        return jsonify({'success': False, 'message': 'यह ईमेल पहले से पंजीकृत है।'}), 409
    finally:
        conn.close()

# ── MEDICINE CONSULTATION ──
@app.route('/api/consult/medicine', methods=['POST'])
def medicine_consult():
    data = request.get_json()
    required = ['name', 'email', 'query']
    if not all(data.get(f) for f in required):
        return jsonify({'success': False, 'message': 'कृपया सभी आवश्यक जानकारी भरें।'}), 400

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    consult_id = str(uuid.uuid4())
    c.execute('''INSERT INTO consultations (id, visitor_name, visitor_email, visitor_phone, query, query_type)
                 VALUES (?, ?, ?, ?, ?, 'medicine')''',
              (consult_id, data['name'], data['email'], data.get('phone', ''), data['query']))
    
    # Add first message
    msg_id = str(uuid.uuid4())
    c.execute('INSERT INTO messages (id, consultation_id, sender, message) VALUES (?, ?, ?, ?)',
              (msg_id, consult_id, 'visitor', data['query']))
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'message': 'आपकी जिज्ञासा दर्ज हो गई। वैद्यजी शीघ्र उत्तर देंगे।', 'consultation_id': consult_id})

# ── ASTROLOGY QUERY ──
@app.route('/api/consult/astrology', methods=['POST'])
def astrology_query():
    data = request.get_json()
    required = ['name', 'email', 'query']
    if not all(data.get(f) for f in required):
        return jsonify({'success': False, 'message': 'कृपया सभी आवश्यक जानकारी भरें।'}), 400

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    query_id = str(uuid.uuid4())
    c.execute('''INSERT INTO astrology_queries 
                 (id, visitor_name, visitor_email, visitor_phone, birth_date, birth_time, birth_place, query, problem_area)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
              (query_id, data['name'], data['email'], data.get('phone', ''),
               data.get('birth_date', ''), data.get('birth_time', ''),
               data.get('birth_place', ''), data['query'], data.get('problem_area', 'general')))
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'message': 'आपकी कुंडली जिज्ञासा दर्ज हो गई। ज्योतिषाचार्य शीघ्र उत्तर देंगे।', 'query_id': query_id})

# ── BOOK APPOINTMENT ──
@app.route('/api/appointment', methods=['POST'])
def book_appointment():
    data = request.get_json()
    required = ['name', 'email', 'phone', 'date', 'time']
    if not all(data.get(f) for f in required):
        return jsonify({'success': False, 'message': 'कृपया सभी आवश्यक जानकारी भरें।'}), 400

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    appt_id = str(uuid.uuid4())
    c.execute('''INSERT INTO appointments 
                 (id, visitor_name, visitor_email, visitor_phone, appointment_date, appointment_time, reason)
                 VALUES (?, ?, ?, ?, ?, ?, ?)''',
              (appt_id, data['name'], data['email'], data['phone'],
               data['date'], data['time'], data.get('reason', '')))
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'message': 'आपका अपॉइंटमेंट सफलतापूर्वक बुक हो गया।', 'appointment_id': appt_id})

# ── GET MESSAGES FOR CONSULTATION ──
@app.route('/api/consult/<consult_id>/messages', methods=['GET'])
def get_messages(consult_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT sender, message, created_at FROM messages WHERE consultation_id = ? ORDER BY created_at', (consult_id,))
    rows = c.fetchall()
    conn.close()
    messages = [{'sender': r[0], 'message': r[1], 'time': r[2]} for r in rows]
    return jsonify({'success': True, 'messages': messages})

# ── SEND MESSAGE ──
@app.route('/api/consult/<consult_id>/send', methods=['POST'])
def send_message(consult_id):
    data = request.get_json()
    msg = data.get('message', '').strip()
    sender = data.get('sender', 'visitor')
    if not msg:
        return jsonify({'success': False, 'message': 'संदेश खाली नहीं हो सकता।'}), 400

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    msg_id = str(uuid.uuid4())
    c.execute('INSERT INTO messages (id, consultation_id, sender, message) VALUES (?, ?, ?, ?)',
              (msg_id, consult_id, sender, msg))
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'message': 'संदेश भेजा गया।'})

# ── ADMIN: ALL CONSULTATIONS ──
@app.route('/api/admin/consultations', methods=['GET'])
def all_consultations():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT id, visitor_name, visitor_email, visitor_phone, query, query_type, status, created_at FROM consultations ORDER BY created_at DESC')
    rows = c.fetchall()
    conn.close()
    result = [{'id': r[0], 'name': r[1], 'email': r[2], 'phone': r[3], 'query': r[4], 'type': r[5], 'status': r[6], 'time': r[7]} for r in rows]
    return jsonify({'success': True, 'consultations': result})

# ── ADMIN: ALL APPOINTMENTS ──
@app.route('/api/admin/appointments', methods=['GET'])
def all_appointments():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT * FROM appointments ORDER BY appointment_date DESC')
    rows = c.fetchall()
    conn.close()
    keys = ['id', 'name', 'email', 'phone', 'date', 'time', 'reason', 'status', 'created_at']
    result = [dict(zip(keys, r)) for r in rows]
    return jsonify({'success': True, 'appointments': result})

# ── ADMIN: ALL ASTROLOGY QUERIES ──
@app.route('/api/admin/astrology', methods=['GET'])
def all_astrology():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT id, visitor_name, visitor_email, query, problem_area, status, created_at FROM astrology_queries ORDER BY created_at DESC')
    rows = c.fetchall()
    conn.close()
    result = [{'id': r[0], 'name': r[1], 'email': r[2], 'query': r[3], 'area': r[4], 'status': r[5], 'time': r[6]} for r in rows]
    return jsonify({'success': True, 'queries': result})

# ── STATS ──
@app.route('/api/stats', methods=['GET'])
def stats():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM visitors')
    visitors = c.fetchone()[0]
    c.execute('SELECT COUNT(*) FROM consultations')
    consultations = c.fetchone()[0]
    c.execute('SELECT COUNT(*) FROM appointments')
    appointments = c.fetchone()[0]
    c.execute('SELECT COUNT(*) FROM astrology_queries')
    astro = c.fetchone()[0]
    conn.close()
    return jsonify({'visitors': visitors, 'consultations': consultations, 'appointments': appointments, 'astrology': astro})

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)
