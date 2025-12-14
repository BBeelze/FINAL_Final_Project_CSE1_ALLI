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

# === RESPONSE FORMATTER (JSON/XML) ===
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

# === JWT AUTH DECORATOR ===
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'x-access-token' in request.headers:
            token = request.headers['x-access-token']
        elif 'token' in session:
            token = session['token']

        if not token:
            if request.args.get('format') in ['json', 'xml']:
                return format_response({'message': 'Token is missing!'}, request.args.get('format')), 401
            else:
                return redirect(url_for('login'))

        try:
            jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
        except:
            if request.args.get('format') in ['json', 'xml']:
                return format_response({'message': 'Token is invalid!'}, request.args.get('format')), 401
            else:
                session.pop('token', None)
                return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

# === REGISTER ===
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        return render_template_string('''
        <!DOCTYPE html>
        <html>
        <head>
            <title>🏍️ Register • Motorcycle Hub</title>
            <style>
                body { font-family: 'Segoe UI', sans-serif; background: #121212; color: #e0e0e0; margin: 0; padding: 0; }
                .container {
                    max-width: 500px; margin: 60px auto; background: #1e1e1e;
                    padding: 30px; border-radius: 12px; box-shadow: 0 0 25px rgba(0,0,0,0.5);
                    border: 1px solid #333;
                }
                h2 {
                    text-align: center; color: #4CAF50; margin-bottom: 25px;
                    border-bottom: 2px solid #2a2a2a; padding-bottom: 10px;
                }
                input {
                    width: 100%; padding: 12px; margin: 10px 0;
                    border: 1px solid #444; border-radius: 6px;
                    background: #2a2a2a; color: #fff; box-sizing: border-box;
                }
                button {
                    width: 100%; padding: 12px; background: #4CAF50;
                    color: white; border: none; border-radius: 6px;
                    font-size: 16px; cursor: pointer; margin-top: 10px;
                }
                button:hover { background: #45a049; }
                a {
                    display: block; text-align: center; margin-top: 20px;
                    color: #4CAF50; text-decoration: none;
                }
                a:hover { text-decoration: underline; }
            </style>
        </head>
        <body>
            <div class="container">
                <h2>🏍️ Register</h2>
                <form method="POST">
                    <input type="text" name="username" placeholder="Username" required>
                    <input type="password" name="password" placeholder="Password" required>
                    <button type="submit">Create Account</button>
                </form>
                <a href="/login">← Already have an account?</a>
            </div>
        </body>
        </html>
        ''')

    username = request.form.get('username')
    password = request.form.get('password')
    if not username or not password:
        return '<h3 style="text-align:center;color:#f44336;">Error: Username and password required</h3><a href="/register" style="display:block;text-align:center;color:#4CAF50;">Try again</a>', 400

    hashed = hashlib.sha256(password.encode()).hexdigest()
    cur = mysql.connection.cursor()
    try:
        cur.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, hashed))
        mysql.connection.commit()
        cur.close()
        return '<h3 style="text-align:center;color:#4CAF50;">Registered successfully!</h3><a href="/login" style="display:block;text-align:center;color:#4CAF50;">Login now</a>'
    except Exception as e:
        cur.close()
        if "Duplicate entry" in str(e):
            return '<h3 style="text-align:center;color:#f44336;">Username already exists</h3><a href="/register" style="display:block;text-align:center;color:#4CAF50;">Try again</a>', 400
        return '<h3 style="text-align:center;color:#f44336;">Registration failed</h3><a href="/register" style="display:block;text-align:center;color:#4CAF50;">Try again</a>', 500

# === LOGIN ===
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template_string('''
        <!DOCTYPE html>
        <html>
        <head>
            <title>🏍️ Login • Motorcycle Hub</title>
            <style>
                body { font-family: 'Segoe UI', sans-serif; background: #121212; color: #e0e0e0; margin: 0; padding: 0; }
                .container {
                    max-width: 500px; margin: 60px auto; background: #1e1e1e;
                    padding: 30px; border-radius: 12px; box-shadow: 0 0 25px rgba(0,0,0,0.5);
                    border: 1px solid #333;
                }
                h2 {
                    text-align: center; color: #4CAF50; margin-bottom: 25px;
                    border-bottom: 2px solid #2a2a2a; padding-bottom: 10px;
                }
                input {
                    width: 100%; padding: 12px; margin: 10px 0;
                    border: 1px solid #444; border-radius: 6px;
                    background: #2a2a2a; color: #fff; box-sizing: border-box;
                }
                button {
                    width: 100%; padding: 12px; background: #4CAF50;
                    color: white; border: none; border-radius: 6px;
                    font-size: 16px; cursor: pointer; margin-top: 10px;
                }
                button:hover { background: #45a049; }
                a {
                    display: block; text-align: center; margin-top: 20px;
                    color: #4CAF50; text-decoration: none;
                }
                a:hover { text-decoration: underline; }
            </style>
        </head>
        <body>
            <div class="container">
                <h2>🏍️ Login</h2>
                <form method="POST">
                    <input type="text" name="username" placeholder="Username" required>
                    <input type="password" name="password" placeholder="Password" required>
                    <button type="submit">Sign In</button>
                </form>
                <a href="/register">← Don't have an account?</a>
            </div>
        </body>
        </html>
        ''')

    username = request.form.get('username')
    password = request.form.get('password')
    hashed = hashlib.sha256(password.encode()).hexdigest()

    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM users WHERE username = %s AND password = %s", (username, hashed))
    user = cur.fetchone()
    cur.close()

    if not user:
        return '<h3 style="text-align:center;color:#f44336;">Invalid credentials</h3><a href="/login" style="display:block;text-align:center;color:#4CAF50;">Try again</a>', 401

    token = jwt.encode({
        'user': username,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
    }, app.config['SECRET_KEY'], algorithm="HS256")
    session['token'] = token
    return redirect(url_for('list_motorcycles'))

# === LOGOUT ===
@app.route('/logout')
def logout():
    session.pop('token', None)
    return redirect(url_for('login'))

# === CREATE MOTORCYCLE ===
@app.route('/motorcycles/new', methods=['GET', 'POST'])
@token_required
def create_motorcycle():
    if request.method == 'GET':
        return render_template_string('''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Add Motorcycle • Motorcycle Hub</title>
            <style>
                body { font-family: 'Segoe UI', sans-serif; background: #121212; color: #e0e0e0; padding: 20px; }
                .container {
                    max-width: 600px; margin: 40px auto; background: #1e1e1e;
                    padding: 30px; border-radius: 12px; box-shadow: 0 0 25px rgba(0,0,0,0.5);
                    border: 1px solid #333;
                }
                h2 {
                    color: #4CAF50; margin-bottom: 20px;
                    border-bottom: 1px solid #333; padding-bottom: 8px;
                }
                input {
                    width: 100%; padding: 10px; margin: 12px 0;
                    border: 1px solid #444; border-radius: 6px;
                    background: #2a2a2a; color: #fff;
                }
                button {
                    width: 100%; padding: 12px; background: #4CAF50;
                    color: white; border: none; border-radius: 6px;
                    font-size: 16px; cursor: pointer; margin-top: 15px;
                }
                button:hover { background: #45a049; }
                a {
                    display: inline-block; margin-top: 15px;
                    color: #4CAF50; text-decoration: none;
                }
                a:hover { text-decoration: underline; }
            </style>
        </head>
        <body>
            <div class="container">
                <h2>➕ Add New Motorcycle</h2>
                <form method="POST">
                    <input name="make" placeholder="Make (e.g., Yamaha)" required>
                    <input name="model" placeholder="Model (e.g., R1)" required>
                    <input name="year" type="number" placeholder="Year (e.g., 2023)" required>
                    <input name="engine_cc" type="number" placeholder="Engine (cc)" required>
                    <input name="color" placeholder="Color" required>
                    <button type="submit">Add Motorcycle</button>
                </form>
                <a href="/motorcycles">← Cancel</a>
            </div>
        </body>
        </html>
        ''')

    data = {
        'make': request.form['make'],
        'model': request.form['model'],
        'year': request.form['year'],
        'engine_cc': request.form['engine_cc'],
        'color': request.form['color']
    }

    try:
        year = int(data['year']); cc = int(data['engine_cc'])
    except:
        return '<h3 style="color:#f44336;">Error: Year and Engine must be numbers</h3><a href="/motorcycles/new" style="color:#4CAF50;">Try again</a>', 400

    cur = mysql.connection.cursor()
    try:
        cur.execute("""
            INSERT INTO motorcycles (make, model, year, engine_cc, color)
            VALUES (%s, %s, %s, %s, %s)
        """, (data['make'], data['model'], year, cc, data['color']))
        mysql.connection.commit()
        cur.close()
        return redirect(url_for('list_motorcycles'))
    except Exception as e:
        cur.close()
        return f'<h3 style="color:#f44336;">Error: {str(e)}</h3><a href="/motorcycles/new" style="color:#4CAF50;">Try again</a>', 400

# === LIST MOTORCYCLES ===
@app.route('/motorcycles', methods=['GET'])
@token_required
def list_motorcycles():
    search = request.args.get('search', '')
    fmt = request.args.get('format', 'html')

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

    if fmt in ['json', 'xml']:
        return format_response(motorcycles, fmt)

    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head>
        <title>🏍️ Motorcycle Hub</title>
        <style>
            body { font-family: 'Segoe UI', sans-serif; background: #121212; color: #e0e0e0; padding: 20px; }
            .container {
                max-width: 900px; margin: auto; background: #1e1e1e;
                padding: 25px; border-radius: 12px; box-shadow: 0 0 25px rgba(0,0,0,0.5);
                border: 1px solid #333;
            }
            h2 { color: #4CAF50; margin-bottom: 20px; }
            .controls { text-align: center; margin: 15px 0; }
            .controls a { margin: 0 10px; color: #4CAF50; text-decoration: none; }
            .controls a:hover { text-decoration: underline; }
            form { text-align: center; margin: 20px 0; }
            input[type="text"] {
                padding: 10px; width: 300px; border: 1px solid #444;
                border-radius: 6px; background: #2a2a2a; color: #fff;
            }
            button {
                padding: 10px 20px; background: #4CAF50; color: white;
                border: none; border-radius: 6px; cursor: pointer;
            }
            ul { list-style: none; padding: 0; }
            li {
                padding: 15px; margin: 12px 0; background: #252525;
                border-left: 4px solid #4CAF50; border-radius: 6px;
            }
            .actions a {
                margin-right: 12px; color: #4CAF50; text-decoration: none;
                font-weight: bold;
            }
            .actions a:hover { text-decoration: underline; }
            .nav { margin-top: 25px; text-align: center; }
            .nav a {
                margin: 0 10px; color: #4CAF50; text-decoration: none;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h2>🏍️ Motorcycle Inventory</h2>
            <div class="controls">
                <a href="/motorcycles?format=json">[JSON]</a>
                <a href="/motorcycles?format=xml">[XML]</a>
            </div>
            <form method="GET">
                <input type="text" name="search" placeholder="Search by make, model, or color..." value="{{search}}">
                <button type="submit">Search</button>
            </form>
            <p><a href="/motorcycles/new" style="color:#4CAF50;">➕ Add New Motorcycle</a></p>
            <ul>
            {% for m in motorcycles %}
                <li>
                    <strong>{{m.make}} {{m.model}}</strong><br>
                    <em>{{m.year}} • {{m.engine_cc}}cc • {{m.color}}</em><br>
                    <div class="actions">
                        <a href="/motorcycles/{{m.id}}">View</a>
                        <a href="/motorcycles/{{m.id}}?format=json">JSON</a>
                        <a href="/motorcycles/{{m.id}}?format=xml">XML</a>
                        <a href="/motorcycles/{{m.id}}/edit">Edit</a>
                        <a href="/motorcycles/{{m.id}}/delete" onclick="return confirm('Remove this motorcycle?')">Delete</a>
                    </div>
                </li>
            {% endfor %}
            </ul>
            <div class="nav">
                <a href="/">Home</a> | <a href="/logout">Logout</a>
            </div>
        </div>
    </body>
    </html>
    ''', motorcycles=motorcycles, search=search)

# === VIEW MOTORCYCLE ===
@app.route('/motorcycles/<int:id>', methods=['GET', 'POST', 'DELETE'])
@token_required
def motorcycle_detail(id):
    if request.method == 'POST' and 'delete' in request.form:
        request.method = 'DELETE'

    fmt = request.args.get('format', 'html')
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM motorcycles WHERE id = %s", (id,))
    row = cur.fetchone()
    if not row:
        cur.close()
        if fmt in ['json', 'xml']:
            return format_response({'error': 'Not found'}, fmt), 404
        else:
            return '<h3 style="color:#f44336;">Motorcycle not found</h3><a href="/motorcycles" style="color:#4CAF50;">Back</a>', 404

    mc = {
        'id': row[0],
        'make': row[1],
        'model': row[2],
        'year': row[3],
        'engine_cc': row[4],
        'color': row[5]
    }

    if request.method == 'GET':
        if fmt in ['json', 'xml']:
            cur.close()
            return format_response(mc, fmt)
        else:
            html = '''
            <!DOCTYPE html>
            <html>
            <head>
                <title>🏍️ {{mc.make}} {{mc.model}}</title>
                <style>
                    body { font-family: 'Segoe UI', sans-serif; background: #121212; color: #e0e0e0; padding: 20px; }
                    .container {
                        max-width: 600px; margin: 40px auto; background: #1e1e1e;
                        padding: 30px; border-radius: 12px; box-shadow: 0 0 25px rgba(0,0,0,0.5);
                        border: 1px solid #333;
                    }
                    h2 { color: #4CAF50; margin-bottom: 20px; }
                    p { margin: 10px 0; font-size: 16px; }
                    strong { color: #4CAF50; }
                    .btn {
                        display: inline-block; padding: 10px 20px; margin: 5px;
                        background: #4CAF50; color: white; text-decoration: none;
                        border-radius: 6px;
                    }
                    .btn:hover { background: #45a049; }
                    .delete-btn {
                        background: #f44336;
                    }
                    .delete-btn:hover {
                        background: #d32f2f;
                    }
                    form { display: inline; }
                    button {
                        padding: 10px 20px; background: #f44336; color: white;
                        border: none; border-radius: 6px; cursor: pointer;
                    }
                    button:hover { background: #d32f2f; }
                </style>
            </head>
            <body>
                <div class="container">
                    <h2>🏍️ {{mc.make}} {{mc.model}}</h2>
                    <p><strong>Year:</strong> {{mc.year}}</p>
                    <p><strong>Engine:</strong> {{mc.engine_cc}}cc</p>
                    <p><strong>Color:</strong> {{mc.color}}</p>
                    <div>
                        <a href="/motorcycles/{{mc.id}}/edit" class="btn">✏️ Edit</a>
                        <form method="POST" onsubmit="return confirm('Delete this motorcycle?')" style="display:inline">
                            <input type="hidden" name="delete" value="1">
                            <button type="submit">🗑️ Delete</button>
                        </form>
                        <a href="/motorcycles" class="btn">← Back</a>
                    </div>
                </div>
            </body>
            </html>
            '''
            cur.close()
            return render_template_string(html, mc=mc)

    # Handle POST (Update)
    elif request.method == 'POST':
        if 'delete' not in request.form:
            data = {
                'make': request.form['make'],
                'model': request.form['model'],
                'year': request.form['year'],
                'engine_cc': request.form['engine_cc'],
                'color': request.form['color']
            }
            try:
                year = int(data['year']); cc = int(data['engine_cc'])
            except:
                return '<h3 style="color:#f44336;">Error: Year and Engine must be integers</h3><a href="/motorcycles/{{id}}/edit" style="color:#4CAF50;">Try again</a>', 400

            cur.execute("""
                UPDATE motorcycles SET make=%s, model=%s, year=%s, engine_cc=%s, color=%s WHERE id=%s
            """, (data['make'], data['model'], year, cc, data['color'], id))
            mysql.connection.commit()
            cur.close()
            return redirect(url_for('motorcycle_detail', id=id))

    # Handle DELETE
    if request.method == 'DELETE':
        cur.execute("DELETE FROM motorcycles WHERE id = %s", (id,))
        mysql.connection.commit()
        cur.close()
        if fmt in ['json', 'xml']:
            return format_response({'message': 'Deleted'}, fmt)
        else:
            return redirect(url_for('list_motorcycles'))

# === EDIT FORM ===
@app.route('/motorcycles/<int:id>/edit', methods=['GET', 'POST'])
@token_required
def edit_motorcycle(id):
    if request.method == 'GET':
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM motorcycles WHERE id = %s", (id,))
        row = cur.fetchone()
        cur.close()
        if not row:
            return '<h3 style="color:#f44336;">Not found</h3><a href="/motorcycles" style="color:#4CAF50;">Back</a>', 404
        mc = {
            'id': row[0],
            'make': row[1],
            'model': row[2],
            'year': row[3],
            'engine_cc': row[4],
            'color': row[5]
        }
        html = '''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Edit Motorcycle • Motorcycle Hub</title>
            <style>
                body { font-family: 'Segoe UI', sans-serif; background: #121212; color: #e0e0e0; padding: 20px; }
                .container {
                    max-width: 600px; margin: 40px auto; background: #1e1e1e;
                    padding: 30px; border-radius: 12px; box-shadow: 0 0 25px rgba(0,0,0,0.5);
                    border: 1px solid #333;
                }
                h2 {
                    color: #4CAF50; margin-bottom: 20px;
                    border-bottom: 1px solid #333; padding-bottom: 8px;
                }
                input {
                    width: 100%; padding: 10px; margin: 12px 0;
                    border: 1px solid #444; border-radius: 6px;
                    background: #2a2a2a; color: #fff;
                }
                button {
                    width: 100%; padding: 12px; background: #4CAF50;
                    color: white; border: none; border-radius: 6px;
                    font-size: 16px; cursor: pointer; margin-top: 15px;
                }
                button:hover { background: #45a049; }
                a {
                    display: inline-block; margin-top: 15px;
                    color: #4CAF50; text-decoration: none;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <h2>✏️ Edit Motorcycle</h2>
                <form method="POST" action="/motorcycles/{{mc.id}}">
                    <input name="make" value="{{mc.make}}" required>
                    <input name="model" value="{{mc.model}}" required>
                    <input name="year" type="number" value="{{mc.year}}" required>
                    <input name="engine_cc" type="number" value="{{mc.engine_cc}}" required>
                    <input name="color" value="{{mc.color}}" required>
                    <button type="submit">Save Changes</button>
                </form>
                <a href="/motorcycles/{{mc.id}}">← Cancel</a>
            </div>
        </body>
        </html>
        '''
        return render_template_string(html, mc=mc)

# === HOME ===
@app.route('/')
def index():
    if 'token' in session:
        return '''
        <!DOCTYPE html>
        <html>
        <head>
            <title>🏍️ Motorcycle Hub</title>
            <style>
                body { font-family: 'Segoe UI', sans-serif; background: #121212; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; color: #e0e0e0; }
                .box {
                    text-align: center; background: #1e1e1e; padding: 40px;
                    border-radius: 15px; box-shadow: 0 0 30px rgba(0,0,0,0.6);
                    border: 1px solid #333; max-width: 500px;
                }
                h1 { color: #4CAF50; font-size: 2.2em; margin-bottom: 30px; }
                .btn {
                    display: block; width: 220px; margin: 12px auto;
                    padding: 14px; background: #4CAF50; color: white;
                    text-decoration: none; border-radius: 8px; font-size: 18px;
                }
                .btn:hover { background: #45a049; }
            </style>
        </head>
        <body>
            <div class="box">
                <h1>🏍️ Welcome to Motorcycle Hub</h1>
                <a href="/motorcycles" class="btn">Manage Motorcycles</a>
                <a href="/logout" class="btn">Logout</a>
            </div>
        </body>
        </html>
        '''
    else:
        return '''
        <!DOCTYPE html>
        <html>
        <head>
            <title>🏍️ Motorcycle Hub</title>
            <style>
                body { font-family: 'Segoe UI', sans-serif; background: #121212; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; color: #e0e0e0; }
                .box {
                    text-align: center; background: #1e1e1e; padding: 40px;
                    border-radius: 15px; box-shadow: 0 0 30px rgba(0,0,0,0.6);
                    border: 1px solid #333; max-width: 500px;
                }
                h1 { color: #4CAF50; font-size: 2.2em; margin-bottom: 30px; }
                .btn {
                    display: block; width: 220px; margin: 12px auto;
                    padding: 14px; background: #4CAF50; color: white;
                    text-decoration: none; border-radius: 8px; font-size: 18px;
                }
                .btn:hover { background: #45a049; }
            </style>
        </head>
        <body>
            <div class="box">
                <h1>🏍️ Motorcycle Management System</h1>
                <a href="/login" class="btn">Login</a>
                <a href="/register" class="btn">Register</a>
            </div>
        </body>
        </html>
        '''

if __name__ == '__main__':
    app.run(debug=True)