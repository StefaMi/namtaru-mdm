from flask import Flask, render_template, request, redirect, url_for, session, flash
from models import db, User
from functools import wraps
import logging



logging.basicConfig(filename='logs/app.log',
                    level=logging.DEBUG,
                    format='%(asctime)s %(levelname)s %(message)s')
app = Flask(__name__)
app.secret_key = "Milash91281288!"  # für Sessions!

# SQLAlchemy-Konfiguration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///namtaru.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# Logging-Konfiguration
logging.basicConfig(filename='logs/app.log',
                    level=logging.DEBUG,
                    format='%(asctime)s %(levelname)s %(message)s')



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

# 3. Logout‑Route
@app.route('/logout')
def logout():
    session.clear()
    flash("Erfolgreich ausgeloggt", "info")
    return render_template('logout.html')

# 4. Decorator für geschützte Routen
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

# 5. Beispiel Home‑Route (geschützt für alle eingeloggten)
@app.route('/')
@login_required()  

def home():
    return render_template('home.html', user=session['user'], role=session['role'])

# 6. Beispiel Admin‑Route (nur role='admin')
@app.route('/admin')
@login_required(role='admin')
def admin_panel():
    return "<h1>Admin-Panel</h1>"

if __name__ == '__main__':
    app.run(debug=True, port=5000)
