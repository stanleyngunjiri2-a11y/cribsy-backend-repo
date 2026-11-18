from app import create_app
from app.extensions import db

app = create_app()

with app.app_context():
    try:
        db.create_all()
        app.config["DATABASE_READY"] = True
    except Exception as error:
        app.config["DATABASE_READY"] = False
        app.logger.exception("Database schema initialization failed: %s", error)
