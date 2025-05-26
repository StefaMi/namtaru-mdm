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

# SQLAlchemy-Konfiguration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///namtaru.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# DB initialisieren
db.init_app(app)

# Datenbank & Initial-Seed
with app.app_context():
    db_path = os.path.join(os.getcwd(), 'namtaru.db')
    if not os.path.isfile(db_path):
        db.create_all()
        logger.info("SQLite-Datenbank wurde auf dem Server neu erstellt.")

        # Rollen anlegen
        admin_role = Role(
            name="admin",
            can_delete_devices=True,
            can_manage_users=True,
            can_assign_roles=True
        )
        helpdesk_role = Role(
            name="helpdesk"  # Standardrechte: nur Ansicht
        )
        db.session.add_all([admin_role, helpdesk_role])
        db.session.commit()

        # Benutzer anlegen
        admin_user = User(username="admin", role=admin_role)
        admin_user.set_password("Milash91281288!")
        helpdesk_user = User(username="helpdesk", role=helpdesk_role)
        helpdesk_user.set_password("helpdesk")
        db.session.add_all([admin_user, helpdesk_user])
        db.session.commit()

# Routen
@app.route('/')
def index():
    return redirect(url_for('home'))

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
            flash(f"Eingeloggt als {user.username}", "success")
            return redirect(url_for('home'))
        else:
            logger.warning(f"Login fehlgeschlagen für Benutzer: {username}")
            flash("Ungültiger Benutzer oder Passwort", "danger")
    return render_template('login.html')

@app.route('/logout')
def logout():
    user = session.get('user')
    session.clear()
    logger.info(f"Logout: {user}")
    flash("Erfolgreich ausgeloggt", "info")
    return render_template('logout.html')

# Decorator für Login + Rollen
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

@app.route('/home')
@login_required()
def home():
    user = session.get('user')
    role = session.get('role')
    device_count = Device.query.count()
    recent_logins = 5  # Platzhalter
    return render_template(
        'home.html', user=user, role=role,
        device_count=device_count, recent_logins=recent_logins
    )

@app.route('/admin')
@login_required(role='admin')
def admin_panel():
    return render_template('admin.html', user=session.get('user'), role=session.get('role'))

@app.route('/devices')
@login_required()
def devices():
    all_devices = Device.query.all()
    return render_template('devices.html', devices=all_devices, role=session.get('role'))

@app.route('/devices/delete/<int:device_id>', methods=['POST'])
@login_required(role='admin')
def delete_device(device_id):
    device = Device.query.get_or_404(device_id)
    db.session.delete(device)
    db.session.commit()
    flash(f"Gerät '{device.name}' wurde gelöscht", "success")
    return redirect(url_for('devices'))

@app.route('/generate_qr')
@login_required(role='admin, helpdesk')
def generate_qr():
    token = str(uuid.uuid4())
    url = f"https://namtaru-mdm.onrender.com/enroll?token={token}"
    os.makedirs('static/qrcodes', exist_ok=True)
    img = qrcode.make(url)
    path = f"static/qrcodes/{token}.png"
    img.save(path)
    return render_template('qr_preview.html', qr_path=path, token=token)

@app.route('/enroll')
def enroll():
    token = request.args.get('token')
    new_device = Device(
        name="Unbenanntes Gerät",
        enrollment_token=token,
        created_at=datetime.utcnow()
    )
    db.session.add(new_device)
    db.session.commit()
    flash("Gerät erfolgreich registriert!", "success")
    return redirect(url_for('devices'))

# Fehlerhandler
@app.errorhandler(500)
def internal_error(error):
    logger.exception("Interner Serverfehler")
    return render_template('500.html'), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
