from app import app
from models import db, User

with app.app_context():
    db.create_all()
    admin = User(username="admin", role="admin")
    admin.set_password("Milash91281288!")
    support = User(username="support", role="support")
    support.set_password("supportpass")
    db.session.add(admin)
    db.session.add(support)
    db.session.commit()
