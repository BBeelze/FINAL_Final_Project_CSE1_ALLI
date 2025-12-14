from flask import Flask, request, jsonify, make_response, render_template_string, session, redirect, url_for
from flask_mysqldb import MySQL
import jwt
import datetime
from functools import wraps
import xml.dom.minidom
from xml.etree.ElementTree import Element, SubElement, tostring
import hashlib
import os

app = Flask(__name__)
app.config.from_object('config.Config')
app.secret_key = os.environ.get('SECRET_KEY', 'motorcycle-secret-key-change-in-prod')

mysql = MySQL(app)

# === JWT AUTH DECORATOR (for API and HTML) ===
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        # Check header first (for API)
        if 'x-access-token' in request.headers:
            token = request.headers['x-access-token']
        # Fallback to session (for HTML)
        elif 'token' in session:
            token = session['token']

        if not token:
            if request.headers.get('Accept') and 'application/json' in request.headers.get('Accept'):
                return jsonify({'message': 'Token is missing!'}), 401
            else:
                return redirect(url_for('login'))

        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            current_user = data['user']
        except:
            if request.headers.get('Accept') and 'application/json' in request.headers.get('Accept'):
                return jsonify({'message': 'Token is invalid!'}), 401
            else:
                session.pop('token', None)
                return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

# === REGISTER (HTML + JSON) ===
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        return render_template_string('''
        <h2>Register</h2>
        <form method="POST">
            <p><input type="text" name="username" placeholder="Username" required></p>
            <p><input type="password" name="password" placeholder="Password" required></p>
            <p><button type="submit">Register</button></p>
            <a href="/login">Already have an account?</a>
        </form>
        ''')

    username = request.form.get('username')
    password = request.form.get('password')

    if not username or not password:
        return '<h3>Error: Username and password required</h3><a href="/register">Try again</a>', 400

    hashed = hashlib.sha256(password.encode()).hexdigest()
    cur = mysql.connection.cursor()
    try:
        cur.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, hashed))
        mysql.connection.commit()
        cur.close()
        return '<h3>Registered successfully!</h3><a href="/login">Login now</a>'
    except Exception as e:
        cur.close()
        if "Duplicate entry" in str(e):
            return '<h3>Username already exists</h3><a href="/register">Try again</a>', 400
        return '<h3>Registration failed</h3><a href="/register">Try again</a>', 500

# === LOGIN (HTML + JSON) ===
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template_string('''
        <h2>Login</h2>
        <form method="POST">
            <p><input type="text" name="username" placeholder="Username" required></p>
            <p><input type="password" name="password" placeholder="Password" required></p>
            <p><button type="submit">Login</button></p>
            <a href="/register">Don't have an account?</a>
        </form>
        ''')

    username = request.form.get('username')
    password = request.form.get('password')
    hashed = hashlib.sha256(password.encode()).hexdigest()

    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM users WHERE username = %s AND password = %s", (username, hashed))
    user = cur.fetchone()
    cur.close()

    if not user:
        return '<h3>Invalid credentials</h3><a href="/login">Try again</a>', 401

    token = jwt.encode({
        'user': username,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
    }, app.config['SECRET_KEY'], algorithm="HS256")

    session['token'] = token
    return redirect(url_for('list_motorcycles'))

# === LIST MOTORCYCLES (HTML view) ===
@app.route('/motorcycles')
@token_required
def list_motorcycles():
    search = request.args.get('search', '')
    cur = mysql.connection.cursor()
    if search:
        cur.execute("SELECT * FROM motorcycles WHERE make LIKE %s OR model LIKE %s OR color LIKE %s",
                    (f"%{search}%", f"%{search}%", f"%{search}%"))
    else:
        cur.execute("SELECT * FROM motorcycles")
    rows = cur.fetchall()
    cur.close()

    motorcycles = []
    for row in rows:
        motorcycles.append({
            'id': row[0],
            'make': row[1],
            'model': row[2],
            'year': row[3],
            'engine_cc': row[4],
            'color': row[5]
        })

    html = '''
    <h2>Motorcycles</h2>
    <form method="GET">
        <input type="text" name="search" placeholder="Search by make/model/color" value="{{search}}">
        <button type="submit">Search</button>
    </form>
    <p><a href="/motorcycles/new">Add New Motorcycle</a></p>
    <ul>
    {% for m in motorcycles %}
        <li>
            {{m.make}} {{m.model}} ({{m.year}}) - {{m.engine_cc}}cc, {{m.color}}
            | <a href="/motorcycles/{{m.id}}">View</a>
            | <a href="/motorcycles/{{m.id}}/edit">Edit</a>
            | <a href="/motorcycles/{{m.id}}/delete" onclick="return confirm('Delete?')">Delete</a>
        </li>
    {% endfor %}
    </ul>
    <p><a href="/">Home</a> | <a href="/logout">Logout</a></p>
    '''
    return render_template_string(html, motorcycles=motorcycles, search=search)

# === LOGOUT ===
@app.route('/logout')
def logout():
    session.pop('token', None)
    return redirect(url_for('login'))

# === API ENDPOINTS (pure JSON/XML) ===

@app.route('/api/motorcycles', methods=['GET', 'POST'])
@token_required
def api_motorcycles():
    if request.method == 'POST':
        data = request.get_json()
        required = ['make', 'model', 'year', 'engine_cc', 'color']
        if not all(k in data for k in required):
            return jsonify({'error': 'Missing fields'}), 400
        try:
            year = int(data['year']); cc = int(data['engine_cc'])
        except:
            return jsonify({'error': 'Year and CC must be integers'}), 400

        cur = mysql.connection.cursor()
        try:
            cur.execute("""
                INSERT INTO motorcycles (make, model, year, engine_cc, color)
                VALUES (%s, %s, %s, %s, %s)
            """, (data['make'], data['model'], year, cc, data['color']))
            mysql.connection.commit()
            cur.close()
            return jsonify({'message': 'Motorcycle added!'}), 201
        except Exception as e:
            return jsonify({'error': str(e)}), 400

    # GET all (API version)
    fmt = request.args.get('format', 'json')
    search = request.args.get('search', None)
    cur = mysql.connection.cursor()
    if search:
        cur.execute("SELECT * FROM motorcycles WHERE make LIKE %s OR model LIKE %s OR color LIKE %s",
                    (f"%{search}%", f"%{search}%", f"%{search}%"))
    else:
        cur.execute("SELECT * FROM motorcycles")
    rows = cur.fetchall()
    cur.close()

    motorcycles = []
    for row in rows:
        motorcycles.append({
            'id': row[0],
            'make': row[1],
            'model': row[2],
            'year': row[3],
            'engine_cc': row[4],
            'color': row[5]
        })
    return format_response(motorcycles, fmt)

@app.route('/api/motorcycles/<int:id>', methods=['GET', 'PUT', 'DELETE'])
@token_required
def api_motorcycle(id):
    fmt = request.args.get('format', 'json')
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM motorcycles WHERE id = %s", (id,))
    row = cur.fetchone()
    if not row:
        cur.close()
        return jsonify({'error': 'Not found'}), 404

    if request.method == 'GET':
        mc = {'id': row[0], 'make': row[1], 'model': row[2], 'year': row[3], 'engine_cc': row[4], 'color': row[5]}
        cur.close()
        return format_response(mc, fmt)

    elif request.method == 'PUT':
        data = request.get_json()
        required = ['make', 'model', 'year', 'engine_cc', 'color']
        if not all(k in data for k in required):
            return jsonify({'error': 'Missing fields'}), 400
        try:
            year = int(data['year']); cc = int(data['engine_cc'])
        except:
            return jsonify({'error': 'Year and CC must be integers'}), 400
        cur.execute("""
            UPDATE motorcycles SET make=%s, model=%s, year=%s, engine_cc=%s, color=%s WHERE id=%s
        """, (data['make'], data['model'], year, cc, data['color'], id))
        mysql.connection.commit()
        cur.close()
        return jsonify({'message': 'Updated'})

    elif request.method == 'DELETE':
        cur.execute("DELETE FROM motorcycles WHERE id = %s", (id,))
        mysql.connection.commit()
        cur.close()
        return jsonify({'message': 'Deleted'})

# === RESPONSE FORMATTER (for API only) ===
def format_response(data, fmt='json'):
    if fmt.lower() == 'xml':
        root = Element('response')
        if isinstance(data, list):
            for item in data:
                mc_elem = SubElement(root, 'motorcycle')
                for key, val in item.items():
                    SubElement(mc_elem, key).text = str(val)
        else:
            for key, val in data.items():
                SubElement(root, key).text = str(val)
        rough = tostring(root, 'utf-8')
        reparsed = xml.dom.minidom.parseString(rough)
        xml_str = reparsed.toprettyxml(indent="  ")
        resp = make_response(xml_str)
        resp.headers['Content-Type'] = 'application/xml'
        return resp
    else:
        return jsonify(data)

# === HOME ===
@app.route('/')
def index():
    if 'token' in session:
        return '<h2>Welcome!</h2><p><a href="/motorcycles">View Motorcycles</a></p><p><a href="/logout">Logout</a></p>'
    else:
        return '<h2>Motorcycle App</h2><p><a href="/login">Login</a> or <a href="/register">Register</a></p>'

if __name__ == '__main__':
    app.run(debug=True)