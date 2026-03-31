import os, re, jwt, datetime
from functools import wraps
from flask import Flask, jsonify, request
from flask_cors import CORS
import mysql.connector
from mysql.connector import Error

try:
    from dotenv import load_dotenv
    load_dotenv()
except:
    pass

app = Flask(__name__)

# ── CORS ──
CORS(app,
     origins=["https://herambha1226.github.io",
               "http://localhost:5500",
               "http://127.0.0.1:5500"],
     allow_headers=["Content-Type","Authorization"],
     methods=["GET","POST","PUT","DELETE","OPTIONS"],
     supports_credentials=False)

SECRET_KEY     = os.getenv('SECRET_KEY',     'herambha_secret_key_2025_xyz')
ADMIN_USERNAME = os.getenv('ADMIN_USERNAME', 'herambha')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'herambha1107')

# ── DB CONFIG from MYSQLURL ──
def get_db_config():
    url = (os.getenv('MYSQLURL') or
           os.getenv('MYSQL_URL') or
           os.getenv('DATABASE_URL',''))
    if url.startswith('mysql://'):
        m = re.match(r'mysql://([^:]+):([^@]+)@([^:/]+):?(\d*)/(.+)', url)
        if m:
            return {
                'user':               m.group(1),
                'password':           m.group(2),
                'host':               m.group(3),
                'port':               int(m.group(4) or 3306),
                'database':           m.group(5),
                'autocommit':         True,
                'connection_timeout': 15,
                'ssl_disabled':       True
            }
    # fallback to individual vars
    return {
        'host':               os.getenv('MYSQLHOST',     'localhost'),
        'user':               os.getenv('MYSQLUSER',     'root'),
        'password':           os.getenv('MYSQLPASSWORD', ''),
        'database':           os.getenv('MYSQLDATABASE', 'railway'),
        'port':               int(os.getenv('MYSQLPORT') or 3306),
        'autocommit':         True,
        'connection_timeout': 15,
        'ssl_disabled':       True
    }

# ── DB HELPERS ──
def get_db():
    try:
        return mysql.connector.connect(**get_db_config())
    except Error as e:
        print(f"DB error: {e}")
        return None

def query(sql, params=(), fetchone=False, fetchall=False, commit=False):
    conn = get_db()
    if not conn:
        return None
    cur = None
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(sql, params)
        if fetchone:  return cur.fetchone()
        if fetchall:  return cur.fetchall()
        if commit:
            conn.commit()
            return cur.lastrowid
        return True
    except Error as e:
        print(f"Query error: {e}")
        return None
    finally:
        try:
            if cur:  cur.close()
            if conn and conn.is_connected(): conn.close()
        except: pass

# ── CREATE TABLES ──
def init_db():
    sqls = [
        """CREATE TABLE IF NOT EXISTS projects(
            id INT AUTO_INCREMENT PRIMARY KEY,
            title VARCHAR(255) NOT NULL,
            description TEXT, tech TEXT,
            image_url VARCHAR(500), project_link VARCHAR(500),
            emoji VARCHAR(20) DEFAULT '🤖',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""",
        """CREATE TABLE IF NOT EXISTS skill_categories(
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            sort_order INT DEFAULT 0)""",
        """CREATE TABLE IF NOT EXISTS skills(
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            category_id INT,
            FOREIGN KEY(category_id)
              REFERENCES skill_categories(id) ON DELETE CASCADE)""",
        """CREATE TABLE IF NOT EXISTS certifications(
            id INT AUTO_INCREMENT PRIMARY KEY,
            title VARCHAR(255) NOT NULL,
            issuer VARCHAR(255), type VARCHAR(50) DEFAULT 'Course',
            date_completed VARCHAR(50), credential_link VARCHAR(500),
            emoji VARCHAR(20), created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""",
        """CREATE TABLE IF NOT EXISTS messages(
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(255), email VARCHAR(255),
            subject VARCHAR(255), message TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"""
    ]
    for sql in sqls:
        query(sql, commit=True)
    print("✅ DB tables ready")

# ── JWT ──
def make_token():
    return jwt.encode(
        {'admin': True,
         'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)},
        SECRET_KEY, algorithm='HS256')

def check_token(token):
    try:
        jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        return True
    except: return False

def admin_only(f):
    @wraps(f)
    def wrap(*a, **kw):
        auth = request.headers.get('Authorization','')
        token = auth.replace('Bearer ','').strip()
        if not token or not check_token(token):
            return jsonify({'error':'Unauthorized — please login first'}), 401
        return f(*a, **kw)
    return wrap

# ════════════════════════════════════════
#  ROUTES
# ════════════════════════════════════════

@app.route('/')
def index():
    return jsonify({'message':'Herambha Portfolio API ✅'})

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
        'message':  'Herambha Portfolio API'
    })

# ── AUTH ──
@app.route('/api/login', methods=['POST','OPTIONS'])
def login():
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    d = request.get_json(force=True, silent=True) or {}
    print(f"Login attempt: username={d.get('username')}")
    if (d.get('username','').strip() == ADMIN_USERNAME and
        d.get('password','').strip() == ADMIN_PASSWORD):
        token = make_token()
        print("Login success ✅")
        return jsonify({'success': True, 'token': token})
    print("Login failed ❌")
    return jsonify({'success': False, 'message': 'Wrong username or password'}), 401

@app.route('/api/logout', methods=['POST'])
def logout():
    return jsonify({'success': True})

# ── PROJECTS ──
@app.route('/api/projects', methods=['GET'])
def get_projects():
    rows = query('SELECT * FROM projects ORDER BY created_at DESC', fetchall=True) or []
    for r in rows:
        r['tech'] = r['tech'].split(',') if r.get('tech') else []
        if r.get('created_at'): r['created_at'] = str(r['created_at'])
    return jsonify(rows)

@app.route('/api/projects', methods=['POST'])
@admin_only
def add_project():
    d = request.get_json(force=True, silent=True) or {}
    rid = query(
        'INSERT INTO projects(title,description,tech,image_url,project_link,emoji)'
        ' VALUES(%s,%s,%s,%s,%s,%s)',
        (d.get('title',''), d.get('desc',''),
         ','.join(d.get('tech',[])),
         d.get('img',''), d.get('link',''), d.get('emoji','🤖')),
        commit=True)
    return jsonify({'success': True, 'id': rid})

@app.route('/api/projects/<int:pid>', methods=['PUT'])
@admin_only
def update_project(pid):
    d = request.get_json(force=True, silent=True) or {}
    query('UPDATE projects SET title=%s,description=%s,tech=%s,'
          'image_url=%s,project_link=%s,emoji=%s WHERE id=%s',
          (d.get('title',''), d.get('desc',''),
           ','.join(d.get('tech',[])),
           d.get('img',''), d.get('link',''), d.get('emoji','🤖'), pid),
          commit=True)
    return jsonify({'success': True})

@app.route('/api/projects/<int:pid>', methods=['DELETE'])
@admin_only
def delete_project(pid):
    query('DELETE FROM projects WHERE id=%s', (pid,), commit=True)
    return jsonify({'success': True})

# ── SKILLS ──
@app.route('/api/skills', methods=['GET'])
def get_skills():
    cats = query('SELECT * FROM skill_categories ORDER BY sort_order', fetchall=True) or []
    for c in cats:
        sk = query('SELECT name FROM skills WHERE category_id=%s ORDER BY id',
                   (c['id'],), fetchall=True) or []
        c['skills'] = [s['name'] for s in sk]
    return jsonify(cats)

@app.route('/api/skill-categories', methods=['POST'])
@admin_only
def add_skill_cat():
    d = request.get_json(force=True, silent=True) or {}
    rid = query(
        'INSERT INTO skill_categories(name,sort_order)'
        ' SELECT %s, IFNULL(MAX(sort_order),0)+1 FROM skill_categories',
        (d.get('name',''),), commit=True)
    return jsonify({'success': True, 'id': rid})

@app.route('/api/skill-categories/<int:cid>', methods=['PUT'])
@admin_only
def update_skill_cat(cid):
    d = request.get_json(force=True, silent=True) or {}
    query('UPDATE skill_categories SET name=%s WHERE id=%s',
          (d.get('name',''), cid), commit=True)
    return jsonify({'success': True})

@app.route('/api/skill-categories/<int:cid>', methods=['DELETE'])
@admin_only
def delete_skill_cat(cid):
    query('DELETE FROM skills WHERE category_id=%s', (cid,), commit=True)
    query('DELETE FROM skill_categories WHERE id=%s', (cid,), commit=True)
    return jsonify({'success': True})

@app.route('/api/skills/add', methods=['POST'])
@admin_only
def add_skill():
    d = request.get_json(force=True, silent=True) or {}
    cid = d.get('category_id')
    for name in [n.strip() for n in d.get('names','').split(',') if n.strip()]:
        if not query('SELECT id FROM skills WHERE name=%s AND category_id=%s',
                     (name, cid), fetchone=True):
            query('INSERT INTO skills(name,category_id) VALUES(%s,%s)',
                  (name, cid), commit=True)
    return jsonify({'success': True})

@app.route('/api/skills/delete', methods=['POST'])
@admin_only
def delete_skill():
    d = request.get_json(force=True, silent=True) or {}
    query('DELETE FROM skills WHERE name=%s AND category_id=%s',
          (d.get('name',''), d.get('category_id')), commit=True)
    return jsonify({'success': True})

# ── CERTS ──
@app.route('/api/certs', methods=['GET'])
def get_certs():
    rows = query('SELECT * FROM certifications ORDER BY created_at DESC', fetchall=True) or []
    for r in rows:
        if r.get('created_at'): r['created_at'] = str(r['created_at'])
    return jsonify(rows)

@app.route('/api/certs', methods=['POST'])
@admin_only
def add_cert():
    d = request.get_json(force=True, silent=True) or {}
    rid = query(
        'INSERT INTO certifications(title,issuer,type,date_completed,credential_link,emoji)'
        ' VALUES(%s,%s,%s,%s,%s,%s)',
        (d.get('title',''), d.get('issuer',''), d.get('type','Course'),
         d.get('date',''), d.get('link',''), d.get('emoji','')),
        commit=True)
    return jsonify({'success': True, 'id': rid})

@app.route('/api/certs/<int:cid>', methods=['PUT'])
@admin_only
def update_cert(cid):
    d = request.get_json(force=True, silent=True) or {}
    query('UPDATE certifications SET title=%s,issuer=%s,type=%s,'
          'date_completed=%s,credential_link=%s,emoji=%s WHERE id=%s',
          (d.get('title',''), d.get('issuer',''), d.get('type','Course'),
           d.get('date',''), d.get('link',''), d.get('emoji',''), cid),
          commit=True)
    return jsonify({'success': True})

@app.route('/api/certs/<int:cid>', methods=['DELETE'])
@admin_only
def delete_cert(cid):
    query('DELETE FROM certifications WHERE id=%s', (cid,), commit=True)
    return jsonify({'success': True})

# ── MESSAGES ──
@app.route('/api/messages', methods=['POST'])
def save_message():
    d = request.get_json(force=True, silent=True) or {}
    query('INSERT INTO messages(name,email,subject,message) VALUES(%s,%s,%s,%s)',
          (d.get('name',''), d.get('email',''),
           d.get('subject',''), d.get('message','')), commit=True)
    return jsonify({'success': True})

@app.route('/api/messages', methods=['GET'])
@admin_only
def get_messages():
    rows = query('SELECT * FROM messages ORDER BY created_at DESC', fetchall=True) or []
    for r in rows:
        if r.get('created_at'): r['created_at'] = str(r['created_at'])
    return jsonify(rows)

@app.route('/api/messages/<int:mid>', methods=['DELETE'])
@admin_only
def delete_message(mid):
    query('DELETE FROM messages WHERE id=%s', (mid,), commit=True)
    return jsonify({'success': True})

@app.route('/api/messages/clear', methods=['DELETE'])
@admin_only
def clear_messages():
    query('DELETE FROM messages', commit=True)
    return jsonify({'success': True})

@app.route('/api/messages/count', methods=['GET'])
@admin_only
def msg_count():
    row = query('SELECT COUNT(*) as c FROM messages', fetchone=True)
    return jsonify({'count': row['c'] if row else 0})

# ════════════════════════════════════════
#  START
# ════════════════════════════════════════
init_db()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)