from flask import Flask, jsonify, request, make_response
from flask_mysqldb import MySQL
import jwt
import datetime
from functools import wraps
import xml.dom.minidom
from xml.etree.ElementTree import Element, SubElement, tostring

app = Flask(__name__)
app.config.from_object('config.Config')

mysql = MySQL(app)
app.config['SECRET_KEY'] = 'motorcycle-secret-key-change-in-prod'

# === JWT AUTH DECORATOR ===
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('x-access-token')
        if not token:
            return jsonify({'message': 'Token is missing!'}), 401
        try:
            jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token expired!'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'message': 'Token is invalid!'}), 401
        return f(*args, **kwargs)
    return decorated

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

# === LOGIN (GET TOKEN) ===
@app.route('/login', methods=['POST'])
def login():
    token = jwt.encode({
        'user': 'rider',
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
    }, app.config['SECRET_KEY'], algorithm="HS256")
    return jsonify({'token': token})

# === CREATE ===
@app.route('/motorcycles', methods=['POST'])
@token_required
def create_motorcycle():
    data = request.get_json()
    required = ['make', 'model', 'year', 'engine_cc', 'color']
    if not all(k in data for k in required):
        return jsonify({'error': 'Missing required fields'}), 400
    try:
        year = int(data['year'])
        cc = int(data['engine_cc'])
    except (ValueError, TypeError):
        return jsonify({'error': 'Year and engine_cc must be integers'}), 400

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

# === READ ALL + SEARCH ===
@app.route('/motorcycles', methods=['GET'])
@token_required
def get_motorcycles():
    fmt = request.args.get('format', 'json')
    search = request.args.get('search', None)

    cur = mysql.connection.cursor()
    if search:
        query = """
            SELECT * FROM motorcycles
            WHERE make LIKE %s OR model LIKE %s OR color LIKE %s
        """
        like = f"%{search}%"
        cur.execute(query, (like, like, like))
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

# === READ ONE ===
@app.route('/motorcycles/<int:id>', methods=['GET'])
@token_required
def get_motorcycle(id):
    fmt = request.args.get('format', 'json')
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM motorcycles WHERE id = %s", (id,))
    row = cur.fetchone()
    cur.close()
    if not row:
        return jsonify({'error': 'Motorcycle not found'}), 404
    mc = {
        'id': row[0],
        'make': row[1],
        'model': row[2],
        'year': row[3],
        'engine_cc': row[4],
        'color': row[5]
    }
    return format_response(mc, fmt)

# === UPDATE ===
@app.route('/motorcycles/<int:id>', methods=['PUT'])
@token_required
def update_motorcycle(id):
    data = request.get_json()
    required = ['make', 'model', 'year', 'engine_cc', 'color']
    if not all(k in data for k in required):
        return jsonify({'error': 'Missing fields'}), 400
    try:
        year = int(data['year'])
        cc = int(data['engine_cc'])
    except:
        return jsonify({'error': 'Year and CC must be integers'}), 400

    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM motorcycles WHERE id = %s", (id,))
    if not cur.fetchone():
        cur.close()
        return jsonify({'error': 'Not found'}), 404

    cur.execute("""
        UPDATE motorcycles
        SET make=%s, model=%s, year=%s, engine_cc=%s, color=%s
        WHERE id=%s
    """, (data['make'], data['model'], year, cc, data['color'], id))
    mysql.connection.commit()
    cur.close()
    return jsonify({'message': 'Motorcycle updated!'})

# === DELETE ===
@app.route('/motorcycles/<int:id>', methods=['DELETE'])
@token_required
def delete_motorcycle(id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM motorcycles WHERE id = %s", (id,))
    if not cur.fetchone():
        cur.close()
        return jsonify({'error': 'Not found'}), 404
    cur.execute("DELETE FROM motorcycles WHERE id = %s", (id,))
    mysql.connection.commit()
    cur.close()
    return jsonify({'message': 'Motorcycle deleted!'})

if __name__ == '__main__':
    app.run(debug=True)