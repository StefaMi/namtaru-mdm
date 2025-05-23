from flask import Flask, render_template, request, redirect, url_for, session, flash
from models import db, User
from functools import wraps
from datetime import datetime
import logging
from models import Device
import qrcode
import uuid
import os
import logging

# 🔐 Sicherstellen, dass der logs-Ordner existiert
os.makedirs("logs", exist_ok=True)


# Logging-Konfiguration
logging.basicConfig(filename='logs/app.log',
                    level=logging.DEBUG,
                    format='%(asctime)s %(levelname)s %(message)s')

app = Flask(__name__)
app.secret_key = "Milash91281288!"  # Für Sessions!

# 📦 SQLAlchemy-Konfiguration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///namtaru.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# 🔐 Login-Route (Datenbankbasiert)
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            session['user'] = user.username
            session['role'] = user.role.name
            flash(f"Eingeloggt als {user.username}", "success")
            return redirect(url_for('home'))
        else:
            flash("Ungültiger Benutzer oder Passwort", "danger")

    return render_template('login.html')

# 🔓 Logout
@app.route('/logout')
def logout():
    session.clear()
    flash("Erfolgreich ausgeloggt", "info")
    return render_template('logout.html')

# 🛡️ Login-Check + Rollen-Check
def login_required(role=None):
    def wrapper(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if 'user' not in session:
                return redirect(url_for('login'))
            if role and session.get('role') != role:
                flash("Keine Berechtigung für diese Aktion", "warning")
                return redirect(url_for('home'))
            return f(*args, **kwargs)
        return decorated
    return wrapper

# 🏠 Home (geschützt)
@app.route('/')
@login_required()
def home():
    return render_template('home.html', user=session['user'], role=session['role'])

# 🛠️ Admin Panel (nur für Admins)
@app.route('/admin')
@login_required(role='admin')
def admin_panel():
    return render_template('admin.html', user=session['user'], role=session['role'])

#   Device hinzufügen
@app.route('/devices')
@login_required()
def devices():
    # Alle Geräte holen
    all_devices = Device.query.all()
    return render_template('devices.html', devices=all_devices, role=session['role'])

# 🗑️ Device löschen
@app.route('/devices/delete/<int:device_id>', methods=['POST'])
@login_required()
def delete_device(device_id):
    user = User.query.filter_by(username=session['user']).first()

    # DEBUG-Ausgabe
    print("User:", user.username)
    print("Rolle:", user.role.name)
    print("Darf löschen?", user.role.can_delete_devices)


    device = Device.query.get_or_404(device_id)
    db.session.delete(device)
    db.session.commit()
    flash(f"Gerät '{device.name}' wurde gelöscht", "success")
    return redirect(url_for('devices'))



# QR-Code erstellung
@app.route("/generate_qr")
@login_required(role='admin')
def generate_qr():
    token = str(uuid.uuid4())
    url = f"https://namtaru-mdm.onrender.com/enroll?token={token}"
    
    os.makedirs("static/qrcodes", exist_ok=True)
    img = qrcode.make(url)
    path = f"static/qrcodes/{token}.png"
    img.save(path)

    return render_template("qr_preview.html" , qr_path=path, token=token)

@app.route("/enroll")
def enroll():
    token = request.args.get("token")

    # Optional: Token validieren (später)
    new_device = Device(
        name="Unbenanntes Gerät",
        enrollment_token=token,
        created_at=datetime.utcnow()
    )
    db.session.add(new_device)
    db.session.commit()

    flash("Gerät erfolgreich registriert!", "success")
    return redirect(url_for('devices'))

# 🚀 App starten
if __name__ == '__main__':
    app.run(debug=True, port=5000)
