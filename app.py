import os
from flask import Flask, render_template, request, send_file
import sqlite3, uuid, io, qrcode, datetime, base64

app = Flask(__name__)
DB = os.path.join(os.path.dirname(__file__), 'attendance.db')

def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS tokens (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    token TEXT UNIQUE,
                    created_at TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS attendance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_id TEXT,
                    token TEXT,
                    marked_at TEXT)''')
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/faculty', methods=['GET','POST'])
def faculty():
    if request.method == 'POST':
        token = str(uuid.uuid4())[:8]
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute('INSERT INTO tokens (token, created_at) VALUES (?,?)', (token, datetime.datetime.utcnow().isoformat()))
        conn.commit()
        conn.close()

        img_io = io.BytesIO()
        img = qrcode.make(token)
        img.save(img_io, 'PNG')
        img_io.seek(0)
        b64 = base64.b64encode(img_io.read()).decode('ascii')

        return render_template('faculty.html', token=token, qr=b64)

    return render_template('faculty.html', token=None, qr=None)

@app.route('/student', methods=['GET','POST'])
def student():
    message = None

    if request.method == 'POST':
        student_id = request.form.get('student_id','').strip()
        token = request.form.get('token','').strip()

        if not student_id or not token:
            message = 'Please provide both Student ID and Token.'
        else:
            conn = sqlite3.connect(DB)
            c = conn.cursor()
            c.execute('SELECT id FROM tokens WHERE token=?', (token,))
            row = c.fetchone()

            if not row:
                message = 'Invalid or expired token.'
            else:
                c.execute('SELECT id FROM attendance WHERE student_id=? AND token=?', (student_id, token))
                if c.fetchone():
                    message = 'Attendance already marked for this student for this token.'
                else:
                    c.execute('INSERT INTO attendance (student_id, token, marked_at) VALUES (?,?,?)',
                              (student_id, token, datetime.datetime.utcnow().isoformat()))
                    conn.commit()
                    message = 'Attendance marked successfully.'
            conn.close()

    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('SELECT token, created_at FROM tokens ORDER BY id DESC LIMIT 5')
    tokens = c.fetchall()
    c.execute('SELECT student_id, token, marked_at FROM attendance ORDER BY id DESC LIMIT 10')
    marks = c.fetchall()
    conn.close()

    return render_template('student.html', message=message, tokens=tokens, marks=marks)

@app.route('/admin')
def admin():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('SELECT student_id, token, marked_at FROM attendance ORDER BY id DESC')
    marks = c.fetchall()
    conn.close()
    return render_template('admin.html', marks=marks)

@app.route('/download_db')
def download_db():
    return send_file(DB, as_attachment=True, download_name='attendance.db')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
