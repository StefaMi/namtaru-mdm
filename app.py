from flask import Flask, render_template, request, redirect, url_for, session, flash
from models import db, User
from functools import wraps
import logging

# Logging-Konfiguration
logging.basicConfig(filename='logs/app.log',
                    level=logging.DEBUG,
                    format='%(asctime)s %(levelname)s %(message)s')

app = Flask(__name__)
app.secret_key = "Milash91281288!"  # Für Sessions!

# 📦 SQLAlchemy-Konfiguration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///instance/namtaru.db'
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
            session['role'] = user.role
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

# 🚀 App starten
if __name__ == '__main__':
    app.run(debug=True, port=5000)
