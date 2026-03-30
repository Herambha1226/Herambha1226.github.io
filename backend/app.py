import os
import re
import jwt
import datetime
from functools import wraps
from flask import Flask, jsonify, request
from flask_cors import CORS
import mysql.connector
from mysql.connector import Error

# ── load .env locally (ignored on Railway) ──
try:
    from dotenv import load_dotenv
    load_dotenv()
except:
    pass

app = Flask(__name__)

CORS(app,
     origins=["https://herambha1226.github.io"],
     allow_headers=["Content-Type", "Authorization"],
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"]
)

SECRET_KEY     = os.getenv('SECRET_KEY',     'herambha_secret_2025')
ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'herambha')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'herambha1107')

# ══════════════════════════════════════════════
#  DB CONFIG
# ══════════════════════════════════════════════
def get_db_config():
    url = os.getenv('MYSQLURL') or os.getenv('MYSQL_URL') or os.getenv('DATABASE_URL','')
    if url and url.startswith('mysql://'):
        m = re.match(r'mysql://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)', url)
        if m:
            return {
                'user':               m.group(1),
                'password':           m.group(2),
                'host':               m.group(3),
                'port':               int(m.group(4)),
                'database':           m.group(5),
                'autocommit':         True,
                'connection_timeout': 10,
                'ssl_disabled':       True
            }
    return {
        'host':               os.getenv('MYSQLHOST',     'localhost'),
        'user':               os.getenv('MYSQLUSER',     'root'),
        'password':           os.getenv('MYSQLPASSWORD', ''),
        'database':           os.getenv('MYSQLDATABASE', 'railway'),
        'port':               int(os.getenv('MYSQLPORT') or 3306),
        'autocommit':         True,
        'connection_timeout': 10,
        'ssl_disabled':       True
    }

def get_db():
    try:
        cfg = get_db_config()
        return mysql.connector.connect(**cfg)
    except Error as e:
        print(f"DB error: {e}")
        return None

def query(sql, params=(), fetchone=False, fetchall=False, commit=False):
    conn = get_db()
    if not conn:
        return None
    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(sql, params)
        if fetchone:  return cursor.fetchone()
        if fetchall:  return cursor.fetchall()
        if commit:
            conn.commit()
            return cursor.lastrowid
        return True
    except Error as e:
        print(f"Query error: {e}")
        return None
    finally:
        try:
            if cursor: cursor.close()
            if conn and conn.is_connected(): conn.close()
        except: pass

def init_db():
    try:
        query("""CREATE TABLE IF NOT EXISTS projects (
            id INT AUTO_INCREMENT PRIMARY KEY,
            title VARCHAR(255) NOT NULL,
            description TEXT, tech TEXT,
            image_url VARCHAR(500), project_link VARCHAR(500),
            emoji VARCHAR(10) DEFAULT '🤖',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""", commit=True)
        query("""CREATE TABLE IF NOT EXISTS skill_categories (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(255) NOT NULL, sort_order INT DEFAULT 0
        )""", commit=True)
        query("""CREATE TABLE IF NOT EXISTS skills (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100) NOT NULL, category_id INT,
            FOREIGN KEY (category_id) REFERENCES skill_categories(id) ON DELETE CASCADE
        )""", commit=True)
        query("""CREATE TABLE IF NOT EXISTS certifications (
            id INT AUTO_INCREMENT PRIMARY KEY,
            title VARCHAR(255) NOT NULL, issuer VARCHAR(255),
            type VARCHAR(50) DEFAULT 'Course', date_completed VARCHAR(50),
            credential_link VARCHAR(500), emoji VARCHAR(10),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""", commit=True)
        query("""CREATE TABLE IF NOT EXISTS messages (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(255), email VARCHAR(255),
            subject VARCHAR(255), message TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""", commit=True)
        print("✅ Tables ready!")
    except Exception as e:
        print(f"⚠️ init_db error: {e}")

# ══════════════════════════════════════════════
#  JWT
# ══════════════════════════════════════════════
def generate_token():
    return jwt.encode(
        {'admin': True, 'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)},
        SECRET_KEY, algorithm='HS256'
    )

def verify_token(token):
    try:
        jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        return True
    except: return False

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization','').replace('Bearer ','')
        if not token or not verify_token(token):
            return jsonify({'error':'Unauthorized'}), 401
        return f(*args, **kwargs)
    return decorated

# ══════════════════════════════════════════════
#  ROUTES
# ══════════════════════════════════════════════

# ── Health ──
@app.route('/api/health')
def health():
    db = get_db()
    ok = db is not None
    if db:
        try: db.close()
        except: pass
    return jsonify({
        'status':   'ok' if ok else 'db_error',
        'database': 'connected ✅' if ok else 'not connected ❌',
        'message':  'Herambha Portfolio API running'
    })

# ── Auth ──
@app.route('/api/login', methods=['POST'])
def login():
    d = request.json or {}
    if d.get('username') == ADMIN_USERNAME and d.get('password') == ADMIN_PASSWORD:
        return jsonify({'success': True, 'token': generate_token()})
    return jsonify({'success': False, 'message': 'Invalid credentials'}), 401

@app.route('/api/logout', methods=['POST'])
def logout():
    return jsonify({'success': True})

# ── Projects ──
@app.route('/api/projects', methods=['GET'])
def get_projects():
    rows = query('SELECT * FROM projects ORDER BY created_at DESC', fetchall=True)
    if not rows: return jsonify([])
    for r in rows:
        r['tech'] = r['tech'].split(',') if r['tech'] else []
        if r.get('created_at'): r['created_at'] = str(r['created_at'])
    return jsonify(rows)

@app.route('/api/projects', methods=['POST'])
@admin_required
def add_project():
    d = request.json or {}
    rid = query(
        'INSERT INTO projects (title,description,tech,image_url,project_link,emoji) VALUES (%s,%s,%s,%s,%s,%s)',
        (d.get('title',''), d.get('desc',''), ','.join(d.get('tech',[])),
         d.get('img',''), d.get('link',''), d.get('emoji','🤖')), commit=True
    )
    return jsonify({'success': True, 'id': rid})

@app.route('/api/projects/<int:pid>', methods=['PUT'])
@admin_required
def update_project(pid):
    d = request.json or {}
    query(
        'UPDATE projects SET title=%s,description=%s,tech=%s,image_url=%s,project_link=%s,emoji=%s WHERE id=%s',
        (d.get('title',''), d.get('desc',''), ','.join(d.get('tech',[])),
         d.get('img',''), d.get('link',''), d.get('emoji','🤖'), pid), commit=True
    )
    return jsonify({'success': True})

@app.route('/api/projects/<int:pid>', methods=['DELETE'])
@admin_required
def delete_project(pid):
    query('DELETE FROM projects WHERE id=%s', (pid,), commit=True)
    return jsonify({'success': True})

# ── Skills ──
@app.route('/api/skills', methods=['GET'])
def get_skills():
    cats = query('SELECT * FROM skill_categories ORDER BY sort_order', fetchall=True)
    if not cats: return jsonify([])
    for c in cats:
        skills = query('SELECT * FROM skills WHERE category_id=%s ORDER BY id', (c['id'],), fetchall=True)
        c['skills'] = [s['name'] for s in (skills or [])]
    return jsonify(cats)

@app.route('/api/skill-categories', methods=['POST'])
@admin_required
def add_skill_cat():
    d = request.json or {}
    rid = query(
        'INSERT INTO skill_categories (name,sort_order) SELECT %s,IFNULL(MAX(sort_order),0)+1 FROM skill_categories',
        (d.get('name',''),), commit=True
    )
    return jsonify({'success': True, 'id': rid})

@app.route('/api/skill-categories/<int:cid>', methods=['PUT'])
@admin_required
def update_skill_cat(cid):
    d = request.json or {}
    query('UPDATE skill_categories SET name=%s WHERE id=%s', (d.get('name',''), cid), commit=True)
    return jsonify({'success': True})

@app.route('/api/skill-categories/<int:cid>', methods=['DELETE'])
@admin_required
def delete_skill_cat(cid):
    query('DELETE FROM skills WHERE category_id=%s', (cid,), commit=True)
    query('DELETE FROM skill_categories WHERE id=%s', (cid,), commit=True)
    return jsonify({'success': True})

@app.route('/api/skills/add', methods=['POST'])
@admin_required
def add_skill():
    d = request.json or {}
    cid = d.get('category_id')
    for name in [n.strip() for n in d.get('names','').split(',') if n.strip()]:
        if not query('SELECT id FROM skills WHERE name=%s AND category_id=%s', (name,cid), fetchone=True):
            query('INSERT INTO skills (name,category_id) VALUES (%s,%s)', (name,cid), commit=True)
    return jsonify({'success': True})

@app.route('/api/skills/delete', methods=['POST'])
@admin_required
def delete_skill():
    d = request.json or {}
    query('DELETE FROM skills WHERE name=%s AND category_id=%s', (d.get('name',''), d.get('category_id')), commit=True)
    return jsonify({'success': True})

# ── Certifications ──
@app.route('/api/certs', methods=['GET'])
def get_certs():
    rows = query('SELECT * FROM certifications ORDER BY created_at DESC', fetchall=True)
    if not rows: return jsonify([])
    for r in rows:
        if r.get('created_at'): r['created_at'] = str(r['created_at'])
    return jsonify(rows)

@app.route('/api/certs', methods=['POST'])
@admin_required
def add_cert():
    d = request.json or {}
    rid = query(
        'INSERT INTO certifications (title,issuer,type,date_completed,credential_link,emoji) VALUES (%s,%s,%s,%s,%s,%s)',
        (d.get('title',''), d.get('issuer',''), d.get('type','Course'),
         d.get('date',''), d.get('link',''), d.get('emoji','')), commit=True
    )
    return jsonify({'success': True, 'id': rid})

@app.route('/api/certs/<int:cid>', methods=['PUT'])
@admin_required
def update_cert(cid):
    d = request.json or {}
    query(
        'UPDATE certifications SET title=%s,issuer=%s,type=%s,date_completed=%s,credential_link=%s,emoji=%s WHERE id=%s',
        (d.get('title',''), d.get('issuer',''), d.get('type','Course'),
         d.get('date',''), d.get('link',''), d.get('emoji',''), cid), commit=True
    )
    return jsonify({'success': True})

@app.route('/api/certs/<int:cid>', methods=['DELETE'])
@admin_required
def delete_cert(cid):
    query('DELETE FROM certifications WHERE id=%s', (cid,), commit=True)
    return jsonify({'success': True})

# ── Messages ──
@app.route('/api/messages', methods=['GET'])
@admin_required
def get_messages():
    rows = query('SELECT * FROM messages ORDER BY created_at DESC', fetchall=True)
    if not rows: return jsonify([])
    for r in rows:
        if r.get('created_at'): r['created_at'] = str(r['created_at'])
    return jsonify(rows)

@app.route('/api/messages', methods=['POST'])
def save_message():
    d = request.json or {}
    query('INSERT INTO messages (name,email,subject,message) VALUES (%s,%s,%s,%s)',
          (d.get('name',''), d.get('email',''), d.get('subject',''), d.get('message','')), commit=True)
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
#  STARTUP
# ══════════════════════════════════════════════
init_db()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(debug=False, host='0.0.0.0', port=port)