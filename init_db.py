from app import app
from models import db, User, Role
from models import Device

with app.app_context():
    db.drop_all()
    db.create_all()

    # Rollen anlegen
    admin_role = Role(
        name="admin",
        can_delete_devices=True,
        can_manage_users=True,
        can_assign_roles=True
    )

    support_role = Role(
        name="support",
        can_delete_devices=True  # Support darf Geräte löschen ✅
    )

    db.session.add_all([admin_role, support_role])
    db.session.commit()

    # Benutzer mit Rollen anlegen
    admin = User(username="admin", role=admin_role)
    admin.set_password("Milash91281288!")

    support = User(username="support", role=support_role)
    support.set_password("supportpass")

    db.session.add_all([admin, support])
    db.session.commit()

    test_device = Device(
    name="iPhone 13",
    type="Smartphone",
    platform="iOS",
    status="Aktiv",
    user=support  # Gerät gehört Support-User
    )

    db.session.add(test_device)
    db.session.commit()