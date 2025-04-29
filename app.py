from flask import Flask, render_template, request, redirect, url_for, session, flash
from functools import wraps
import logging
logging.basicConfig(filename='logs/app.log',
                    level=logging.DEBUG,
                    format='%(asctime)s %(levelname)s %(message)s')
app = Flask(__name__)
app.secret_key = "Milash91281288!"  # für Sessions!

# 1. User‑Daten (vorerst hard‑coded)
users = {
    "admin":   {"password": "Milash91281288!",   "role": "admin"},
    "support": {"password": "supportpass", "role": "support"}
}

# 2. Login‑Route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = request.form['username']
        pwd  = request.form['password']
        if user in users and users[user]['password'] == pwd:
            session['user'] = user
            session['role'] = users[user]['role']
            flash(f"Eingeloggt als {user}", "success")
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
