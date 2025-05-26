from flask import Flask, render_template, request, redirect, url_for, session, flash, request as flask_request
from models import db, User, Device, Role
from functools import wraps
from datetime import datetime
import logging, os, sys
import qrcode, uuid

# Logging konfigurieren
os.makedirs("logs", exist_ok=True)
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

# Flask App initialisieren
app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET', 'supersecret')

# Datenbank-Konfiguration
# Priorität: Render Postgres, fall back auf SQLite
database_url = os.getenv('DATABASE_URL')
if database_url:
    # Render liefert manchmal postgres:// statt postgresql://
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    logger.info("Using PostgreSQL: %s", database_url)
else:
    sqlite_path = os.path.join(os.getcwd(), 'namtaru.db')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{sqlite_path}'
    logger.info("Using SQLite fallback: %s", sqlite_path)

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# DB initialisieren
db.init_app(app)

# Initial-Seed nur, wenn DB leer
with app.app_context():
    db.create_all()
    if Role.query.count() == 0:
        logger.info("Seed-Datenbank initialisieren...")
        admin_role = Role(name="admin", can_delete_devices=True, can_manage_users=True, can_assign_roles=True)
        helpdesk_role = Role(name="helpdesk")
        db.session.add_all([admin_role, helpdesk_role])
        db.session.commit()
        
        admin_user = User(username="admin", role=admin_role)
        admin_user.set_password(os.getenv('ADMIN_PW', 'Milash91281288!'))
        helpdesk_user = User(username="helpdesk", role=helpdesk_role)
        helpdesk_user.set_password(os.getenv('HELPDESK_PW', 'helpdesk'))
        db.session.add_all([admin_user, helpdesk_user])
        db.session.commit()
        logger.info("Seed abgeschlossen.")

# Auth-Decorator
def login_required(role=None):
    def wrapper(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if 'user' not in session:
                return redirect(url_for('login'))
            if role:
                allowed = role if isinstance(role, (list, tuple)) else [role]
                if session.get('role') not in allowed:
                    flash("Keine Berechtigung", "warning")
                    return redirect(url_for('home'))
            return f(*args, **kwargs)
        return decorated
    return wrapper

# Routen
@app.route('/')
def index():
    return redirect(url_for('home'))

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        u = request.form['username']
        p = request.form['password']
        user = User.query.filter_by(username=u).first()
        if user and user.check_password(p):
            session['user'], session['role'] = user.username, user.role.name
            logger.info(f"Login: {u}")
            flash(f"Eingeloggt als {u}", "success")
            return redirect(url_for('home'))
        flash("Ungültiger Login", "danger")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash("Ausgeloggt", "info")
    return render_template('logout.html')

@app.route('/home')
@login_required()
def home():
    stats = {'devices': Device.query.count(), 'logins': 5}
    return render_template('home.html', user=session['user'], role=session['role'], **stats)

@app.route('/admin')
@login_required('admin')
def admin_panel():
    return render_template('admin.html', user=session['user'], role=session['role'])

@app.route('/devices')
@login_required()
def devices():
    return render_template('devices.html', devices=Device.query.all(), role=session['role'])

@app.route('/devices/delete/<int:id>', methods=['POST'])
@login_required('admin')
def delete_device(id):
    d = Device.query.get_or_404(id)
    db.session.delete(d)
    db.session.commit()
    flash("Gelöscht", "success")
    return redirect(url_for('devices'))

@app.route('/generate_qr')
@login_required(['admin','helpdesk'])
def generate_qr():
    t = str(uuid.uuid4())
    url = f"{flask_request.url_root}enroll?token={t}"
    os.makedirs('static/qrcodes', exist_ok=True)
    qrcode.make(url).save(f"static/qrcodes/{t}.png")
    return render_template('qr_preview.html', qr_path=f"qrcodes/{t}.png", token=t)

@app.route('/enroll')
def enroll():
    t = request.args.get('token')
    db.session.add(Device(name="Unbenanntes Gerät", enrollment_token=t, created_at=datetime.utcnow()))
    db.session.commit()
    flash("Registriert", "success")
    return redirect(url_for('devices'))

@app.errorhandler(500)
def error500(e):
    logger.exception("Interner Serverfehler")
    return render_template('500.html'), 500

if __name__=='__main__':
    app.run(debug=True, port=5000)
