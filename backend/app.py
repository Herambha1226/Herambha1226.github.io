from flask import Flask, jsonify, request, session
from flask_cors import CORS
import mysql.connector
from mysql.connector import Error
import hashlib
import os
from datetime import datetime
from functools import wraps
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')

app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'None'
app.config['SESSION_COOKIE_HTTPONLY'] = True

CORS(
    app,
    supports_credentials=True,
    origins=[
        "https://herambha1226.github.io"
    ],
    allow_headers=["Content-Type"],
    methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"]
)

# ══════════════════════════════════════════════
#  DATABASE CONFIG  —  set your password below
# ══════════════════════════════════════════════
DB_CONFIG = {
    'host': os.getenv('MYSQLHOST'),
    'user': os.getenv('MYSQLUSER'),
    'password': os.getenv('MYSQLPASSWORD'),
    'database': os.getenv('MYSQLDATABASE'),
    'port': int(os.getenv('MYSQLPORT') or 23456),
    'autocommit': True
}


# ── Admin credentials (same as before) ──
ADMIN_USERNAME = os.getenv('ADMIN_USERNAME')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD')


# ══════════════════════════════════════════════
#  DB HELPER
# ══════════════════════════════════════════════
def get_db():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except Error as e:
        print(f"DB connection error: {e}")
        return None

def query(sql, params=(), fetchone=False, fetchall=False, commit=False):
    conn = get_db()
    if not conn:
        return None
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(sql, params)
        if fetchone:
            return cursor.fetchone()
        if fetchall:
            return cursor.fetchall()
        if commit:
            conn.commit()
            return cursor.lastrowid
    except Error as e:
        print(f"Query error: {e}")
        return None
    finally:
        cursor.close()
        conn.close()


# ══════════════════════════════════════════════
#  AUTH DECORATOR
# ══════════════════════════════════════════════
def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return jsonify({'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return decorated


# ══════════════════════════════════════════════
#  AUTH ROUTES
# ══════════════════════════════════════════════
@app.route('/api/login', methods=['POST'])
def login():
    data = request.json or {}
    username = data.get('username', '')
    password = data.get('password', '')
    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        session['admin_logged_in'] = True
        return jsonify({'success': True, 'message': 'Logged in successfully'})
    return jsonify({'success': False, 'message': 'Invalid credentials'}), 401

@app.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'success': True, 'message': 'Logged out'})

@app.route('/api/auth-check', methods=['GET'])
def auth_check():
    return jsonify({'logged_in': bool(session.get('admin_logged_in'))})


# ══════════════════════════════════════════════
#  PROJECTS  —  full CRUD
# ══════════════════════════════════════════════
@app.route('/api/projects', methods=['GET'])
def get_projects():
    rows = query('SELECT * FROM projects ORDER BY created_at DESC', fetchall=True)
    if rows is None:
        return jsonify([])
    for row in rows:
        # convert tech string back to list
        row['tech'] = row['tech'].split(',') if row['tech'] else []
        if row.get('created_at'):
            row['created_at'] = str(row['created_at'])
    return jsonify(rows)

@app.route('/api/projects', methods=['POST'])
@admin_required
def add_project():
    d = request.json or {}
    tech_str = ','.join(d.get('tech', []))
    rowid = query(
        'INSERT INTO projects (title, description, tech, image_url, project_link, emoji) VALUES (%s,%s,%s,%s,%s,%s)',
        (d.get('title',''), d.get('desc',''), tech_str, d.get('img',''), d.get('link',''), d.get('emoji','🤖')),
        commit=True
    )
    return jsonify({'success': True, 'id': rowid})

@app.route('/api/projects/<int:pid>', methods=['PUT'])
@admin_required
def update_project(pid):
    d = request.json or {}
    tech_str = ','.join(d.get('tech', []))
    query(
        'UPDATE projects SET title=%s, description=%s, tech=%s, image_url=%s, project_link=%s, emoji=%s WHERE id=%s',
        (d.get('title',''), d.get('desc',''), tech_str, d.get('img',''), d.get('link',''), d.get('emoji','🤖'), pid),
        commit=True
    )
    return jsonify({'success': True})

@app.route('/api/projects/<int:pid>', methods=['DELETE'])
@admin_required
def delete_project(pid):
    query('DELETE FROM projects WHERE id=%s', (pid,), commit=True)
    return jsonify({'success': True})


# ══════════════════════════════════════════════
#  SKILL CATEGORIES  —  full CRUD
# ══════════════════════════════════════════════
@app.route('/api/skills', methods=['GET'])
def get_skills():
    cats = query('SELECT * FROM skill_categories ORDER BY sort_order ASC', fetchall=True)
    if not cats:
        return jsonify([])
    for cat in cats:
        skills = query('SELECT * FROM skills WHERE category_id=%s ORDER BY id ASC', (cat['id'],), fetchall=True)
        cat['skills'] = [s['name'] for s in (skills or [])]
    return jsonify(cats)

@app.route('/api/skill-categories', methods=['POST'])
@admin_required
def add_skill_category():
    d = request.json or {}
    rowid = query(
        'INSERT INTO skill_categories (name, sort_order) VALUES (%s, (SELECT IFNULL(MAX(sort_order),0)+1 FROM skill_categories sc2))',
        (d.get('name',''),), commit=True
    )
    return jsonify({'success': True, 'id': rowid})

@app.route('/api/skill-categories/<int:cid>', methods=['PUT'])
@admin_required
def update_skill_category(cid):
    d = request.json or {}
    query('UPDATE skill_categories SET name=%s WHERE id=%s', (d.get('name',''), cid), commit=True)
    return jsonify({'success': True})

@app.route('/api/skill-categories/<int:cid>', methods=['DELETE'])
@admin_required
def delete_skill_category(cid):
    query('DELETE FROM skills WHERE category_id=%s', (cid,), commit=True)
    query('DELETE FROM skill_categories WHERE id=%s', (cid,), commit=True)
    return jsonify({'success': True})

# ── Individual skills ──
@app.route('/api/skills/add', methods=['POST'])
@admin_required
def add_skill():
    d = request.json or {}
    names = [n.strip() for n in d.get('names', '').split(',') if n.strip()]
    cid = d.get('category_id')
    for name in names:
        exists = query('SELECT id FROM skills WHERE name=%s AND category_id=%s', (name, cid), fetchone=True)
        if not exists:
            query('INSERT INTO skills (name, category_id) VALUES (%s,%s)', (name, cid), commit=True)
    return jsonify({'success': True})

@app.route('/api/skills/delete', methods=['POST'])
@admin_required
def delete_skill():
    d = request.json or {}
    query('DELETE FROM skills WHERE name=%s AND category_id=%s', (d.get('name',''), d.get('category_id')), commit=True)
    return jsonify({'success': True})


# ══════════════════════════════════════════════
#  CERTIFICATIONS  —  full CRUD
# ══════════════════════════════════════════════
@app.route('/api/certs', methods=['GET'])
def get_certs():
    rows = query('SELECT * FROM certifications ORDER BY created_at DESC', fetchall=True)
    if rows is None:
        return jsonify([])
    for r in rows:
        if r.get('created_at'):
            r['created_at'] = str(r['created_at'])
    return jsonify(rows)

@app.route('/api/certs', methods=['POST'])
@admin_required
def add_cert():
    d = request.json or {}
    rowid = query(
        'INSERT INTO certifications (title, issuer, type, date_completed, credential_link, emoji) VALUES (%s,%s,%s,%s,%s,%s)',
        (d.get('title',''), d.get('issuer',''), d.get('type','Course'), d.get('date',''), d.get('link',''), d.get('emoji','')),
        commit=True
    )
    return jsonify({'success': True, 'id': rowid})

@app.route('/api/certs/<int:cid>', methods=['PUT'])
@admin_required
def update_cert(cid):
    d = request.json or {}
    query(
        'UPDATE certifications SET title=%s, issuer=%s, type=%s, date_completed=%s, credential_link=%s, emoji=%s WHERE id=%s',
        (d.get('title',''), d.get('issuer',''), d.get('type','Course'), d.get('date',''), d.get('link',''), d.get('emoji',''), cid),
        commit=True
    )
    return jsonify({'success': True})

@app.route('/api/certs/<int:cid>', methods=['DELETE'])
@admin_required
def delete_cert(cid):
    query('DELETE FROM certifications WHERE id=%s', (cid,), commit=True)
    return jsonify({'success': True})


# ══════════════════════════════════════════════
#  CONTACT MESSAGES  —  save & read
# ══════════════════════════════════════════════
@app.route('/api/messages', methods=['GET'])
@admin_required
def get_messages():
    rows = query('SELECT * FROM messages ORDER BY created_at DESC', fetchall=True)
    if rows is None:
        return jsonify([])
    for r in rows:
        if r.get('created_at'):
            r['created_at'] = str(r['created_at'])
    return jsonify(rows)

@app.route('/api/messages', methods=['POST'])
def save_message():
    d = request.json or {}
    query(
        'INSERT INTO messages (name, email, subject, message) VALUES (%s,%s,%s,%s)',
        (d.get('name',''), d.get('email',''), d.get('subject',''), d.get('message','')),
        commit=True
    )
    return jsonify({'success': True})

@app.route('/api/messages/<int:mid>', methods=['DELETE'])
@admin_required
def delete_message(mid):
    query('DELETE FROM messages WHERE id=%s', (mid,), commit=True)
    return jsonify({'success': True})

@app.route('/api/messages/clear', methods=['DELETE'])
@admin_required
def clear_messages():
    query('DELETE FROM messages', commit=True)
    return jsonify({'success': True})

@app.route('/api/messages/count', methods=['GET'])
@admin_required
def message_count():
    row = query('SELECT COUNT(*) as count FROM messages', fetchone=True)
    return jsonify({'count': row['count'] if row else 0})


# ══════════════════════════════════════════════
#  HEALTH CHECK
# ══════════════════════════════════════════════
@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'message': 'Herambha Portfolio API running'})


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(debug=False, host='0.0.0.0', port=port)
