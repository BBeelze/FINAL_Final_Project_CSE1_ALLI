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

# === LOGIN ===
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

# === LOGOUT ===
@app.route('/logout')
def logout():
    session.pop('token', None)
    return redirect(url_for('login'))

# === CREATE MOTORCYCLE (HTML FORM + JSON POST) ===
@app.route('/motorcycles/new', methods=['GET', 'POST'])
@token_required
def create_motorcycle():
    if request.method == 'GET':
        return render_template_string('''
        <h2>Add New Motorcycle</h2>
        <form method="POST">
            <p><input name="make" placeholder="Make (e.g., Yamaha)" required></p>
            <p><input name="model" placeholder="Model (e.g., R1)" required></p>
            <p><input name="year" type="number" placeholder="Year" required></p>
            <p><input name="engine_cc" type="number" placeholder="Engine (cc)" required></p>
            <p><input name="color" placeholder="Color" required></p>
            <p><button type="submit">Add Motorcycle</button></p>
            <a href="/motorcycles">Cancel</a>
        </form>
        ''')

    # Handle HTML form submission
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
        return '<h3>Error: Year and Engine must be numbers</h3><a href="/motorcycles/new">Try again</a>', 400

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
        return f'<h3>Error: {str(e)}</h3><a href="/motorcycles/new">Try again</a>', 400

# === READ ALL + SEARCH (supports ?format=json/xml) ===
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

    # HTML view
    html = '''
    <h2>Motorcycles</h2>
    <p><a href="/motorcycles?format=json">JSON</a> | <a href="/motorcycles?format=xml">XML</a></p>
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
            | <a href="/motorcycles/{{m.id}}?format=json">JSON</a>
            | <a href="/motorcycles/{{m.id}}?format=xml">XML</a>
            | <a href="/motorcycles/{{m.id}}/edit">Edit</a>
            | <a href="/motorcycles/{{m.id}}/delete" onclick="return confirm('Delete?')">Delete</a>
        </li>
    {% endfor %}
    </ul>
    <p><a href="/">Home</a> | <a href="/logout">Logout</a></p>
    '''
    return render_template_string(html, motorcycles=motorcycles, search=search)

# === READ ONE, UPDATE, DELETE (supports ?format=json/xml) ===
@app.route('/motorcycles/<int:id>', methods=['GET', 'POST', 'DELETE'])
@token_required
def motorcycle_detail(id):
    # For DELETE, we allow POST workaround since HTML doesn't support DELETE
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
            return '<h3>Motorcycle not found</h3><a href="/motorcycles">Back</a>', 404

    mc = {
        'id': row[0],
        'make': row[1],
        'model': row[2],
        'year': row[3],
        'engine_cc': row[4],
        'color': row[5]
    }

    # === GET: View ===
    if request.method == 'GET':
        if fmt in ['json', 'xml']:
            cur.close()
            return format_response(mc, fmt)
        else:
            html = '''
            <h2>{{mc.make}} {{mc.model}}</h2>
            <p><strong>Year:</strong> {{mc.year}}</p>
            <p><strong>Engine:</strong> {{mc.engine_cc}}cc</p>
            <p><strong>Color:</strong> {{mc.color}}</p>
            <p>
                <a href="/motorcycles/{{mc.id}}/edit">Edit</a> |
                <form method="POST" style="display:inline" onsubmit="return confirm('Delete?')">
                    <input type="hidden" name="delete" value="1">
                    <button type="submit">Delete</button>
                </form> |
                <a href="/motorcycles">Back to list</a>
            </p>
            '''
            cur.close()
            return render_template_string(html, mc=mc)

    # === POST: Update ===
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
                return '<h3>Error: Year and Engine must be integers</h3><a href="/motorcycles/{{id}}/edit">Try again</a>', 400

            cur.execute("""
                UPDATE motorcycles SET make=%s, model=%s, year=%s, engine_cc=%s, color=%s WHERE id=%s
            """, (data['make'], data['model'], year, cc, data['color'], id))
            mysql.connection.commit()
            cur.close()
            return redirect(url_for('motorcycle_detail', id=id))

    # === DELETE ===
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
            return '<h3>Not found</h3><a href="/motorcycles">Back</a>', 404
        mc = {
            'id': row[0],
            'make': row[1],
            'model': row[2],
            'year': row[3],
            'engine_cc': row[4],
            'color': row[5]
        }
        html = '''
        <h2>Edit Motorcycle</h2>
        <form method="POST" action="/motorcycles/{{mc.id}}">
            <p><input name="make" value="{{mc.make}}" required></p>
            <p><input name="model" value="{{mc.model}}" required></p>
            <p><input name="year" type="number" value="{{mc.year}}" required></p>
            <p><input name="engine_cc" type="number" value="{{mc.engine_cc}}" required></p>
            <p><input name="color" value="{{mc.color}}" required></p>
            <p><button type="submit">Save Changes</button></p>
            <a href="/motorcycles/{{mc.id}}">Cancel</a>
        </form>
        '''
        return render_template_string(html, mc=mc)

# === HOME ===
@app.route('/')
def index():
    if 'token' in session:
        return '<h2>Welcome!</h2><p><a href="/motorcycles">View Motorcycles</a></p><p><a href="/logout">Logout</a></p>'
    else:
        return '<h2>Motorcycle App</h2><p><a href="/login">Login</a> or <a href="/register">Register</a></p>'

if __name__ == '__main__':
    app.run(debug=True)