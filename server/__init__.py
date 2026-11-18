from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager
from flask_marshmallow import Marshmallow

from config import Config

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()
bcrypt = Bcrypt()
jwt = JWTManager()
ma = Marshmallow()


def create_app():
    app = Flask(__name__)

    # Load configuration
    app.config.from_object(Config)

    # Initialize extensions with Flask
    db.init_app(app)
    migrate.init_app(app, db)
    bcrypt.init_app(app)
    jwt.init_app(app)
    ma.init_app(app)

    from server.routes.docs import bp as docs_bp, URL_PREFIX as docs_prefix

    app.register_blueprint(docs_bp, url_prefix=docs_prefix)

    from server.routes.auth import bp as auth_bp, URL_PREFIX as auth_prefix

    app.register_blueprint(auth_bp, url_prefix=auth_prefix)
    return app
