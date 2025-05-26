from flask import Flask, render_template, request, redirect, url_for, session, flash
from models import db, User, Device, Role
from functools import wraps
from datetime import datetime
import logging
import qrcode
import uuid
import os
import sys

# Sicherstellen, dass der logs-Ordner existiert
os.makedirs("logs", exist_ok=True)

# Logging-Konfiguration
log_formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] %(message)s')
file_handler = logging.FileHandler('logs/app.log')
file_handler.setFormatter(log_formatter)
file_handler.setLevel(logging.DEBUG)

stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setFormatter(log_formatter)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.addHandler(file_handler)
logger.addHandler(stream_handler)

app = Flask(__name__)
app.secret_key = "Milash91281288!"  # Für Sessions!

# Session-Konfiguration für HTTPS-Umgebungen (Render)
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# SQLAlchemy-Konfiguration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///namtaru.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# DB initialisieren
db.init_app(app)

# Wenn Datenbank nicht existiert, automatisch anlegen (nur beim ersten Start)
with app.app_context():
    if not os.path.exists("namtaru.db"):
        db.create_all()
        logger.info("SQLite-Datenbank wurde auf dem Server neu erstellt.")

        # Beispielrollen und Benutzer hinzufügen
        admin_role = Role(name="admin", can_delete_devices=True, can_manage_users=True, can_assign_roles=True)
        support_role = Role(name="support", can_delete_devices=True)
        db.session.add_all([admin_role, support_role])
        db.session.commit()

        admin_user = User(username="admin", role=admin_role)
        admin_user.set_password("demo1234")
        support_user = User(username="support", role=support_role)
        support_user.set_password("demo1234")
        db.session.add_all([admin_user, support_user])
        db.session.commit()

        demo_device = Device(name="iPhone 13", platform="iOS", status="Aktiv", user=support_user)
        db.session.add(demo_device)
        db.session.commit()



# Login-Route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            session['user'] = user.username
            session['role'] = user.role.name if user.role else 'user'
            logger.info(f"Login erfolgreich: {user.username} ({session['role']})")
            logger.info(f"Session gesetzt: {session}")
            flash(f"Eingeloggt als {user.username}", "success")
            return redirect(url_for('home'))
        else:
            logger.warning(f"Login fehlgeschlagen für Benutzer: {username}")
            flash("Ungültiger Benutzer oder Passwort", "danger")

    return render_template('login.html')

# Logout
@app.route('/logout')
def logout():
    user = session.get('user')
    session.clear()
    logger.info(f"Logout: {user}")
    flash("Erfolgreich ausgeloggt", "info")
    return render_template('logout.html')

# Login-Check + Rollen-Check
def login_required(role=None):
    def wrapper(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if 'user' not in session:
                return redirect(url_for('login'))
            if role and session.get('role') != role:
                logger.warning(f"Zugriffsversuch ohne Berechtigung durch: {session.get('user')} (Rolle: {session.get('role')})")
                flash("Keine Berechtigung für diese Aktion", "warning")
                return redirect(url_for('home'))
            return f(*args, **kwargs)
        return decorated
    return wrapper

# Home (geschützt)
@app.route('/home')
@login_required()
def home():
    logger.info(f"Aktive Session beim Home-Zugriff: {session}")
    user = session.get('user')
    role = session.get('role')
    device_count = Device.query.count()
    recent_logins = 5  # Platzhalter für spätere dynamische Berechnung

    return render_template(
        'home.html',
        user=user,
        role=role,
        device_count=device_count,
        recent_logins=recent_logins
    )

# Admin Panel
@app.route('/admin')
@login_required(role='admin')
def admin_panel():
    return render_template('admin.html', user=session.get('user'), role=session.get('role'))

# Geräte anzeigen
@app.route('/devices')
@login_required()
def devices():
    all_devices = Device.query.all()
    return render_template('devices.html', devices=all_devices, role=session.get('role'))

# Gerät löschen
@app.route('/devices/delete/<int:device_id>', methods=['POST'])
@login_required()
def delete_device(device_id):
    user = User.query.filter_by(username=session.get('user')).first()

    if user and user.role:
        logger.info(f"{user.username} löscht Gerät-ID: {device_id} (Rolle: {user.role.name})")

    device = Device.query.get_or_404(device_id)
    db.session.delete(device)
    db.session.commit()
    flash(f"Gerät '{device.name}' wurde gelöscht", "success")
    return redirect(url_for('devices'))

# QR-Code erstellen
@app.route("/generate_qr")
@login_required(role='admin')
def generate_qr():
    token = str(uuid.uuid4())
    url = f"https://namtaru-mdm.onrender.com/enroll?token={token}"

    os.makedirs("static/qrcodes", exist_ok=True)
    img = qrcode.make(url)
    path = f"static/qrcodes/{token}.png"
    img.save(path)

    logger.info(f"QR-Code erstellt für Enrollment-Token: {token}")
    return render_template("qr_preview.html", qr_path=path, token=token)

# Enrollment-Route
@app.route("/enroll")
def enroll():
    token = request.args.get("token")

    new_device = Device(
        name="Unbenanntes Gerät",
        enrollment_token=token,
        platform="unbekannt",
        type="unbekannt",
        created_at=datetime.utcnow()
    )
    db.session.add(new_device)
    db.session.commit()

    logger.info(f"Neues Gerät registriert mit Token: {token}")
    flash("Gerät erfolgreich registriert!", "success")
    return redirect(url_for('devices'))



# App starten
if __name__ == '__main__':
    app.run(debug=True, port=5000)
