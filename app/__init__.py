from flask import Flask, jsonify

from config import Config

from .extensions import cors, db, jwt, migrate


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    cors.init_app(app, resources={r"/api/*": {"origins": app.config["CORS_ORIGINS"]}})

    from . import models  # noqa: F401  (so migrations can see every table)
    from .routes import register_blueprints

    register_blueprints(app)

    @app.get("/api/health")
    def health():
        return jsonify({"status": "ok"})

    @app.errorhandler(404)
    def not_found(_error):
        return jsonify({"error": "Not found."}), 404

    @app.errorhandler(405)
    def method_not_allowed(_error):
        return jsonify({"error": "Method not allowed."}), 405

    @app.errorhandler(413)
    def too_large(_error):
        return jsonify({"error": "The file is too large. Use an image of 2 MB or less."}), 413

    @app.errorhandler(500)
    def server_error(_error):
        db.session.rollback()
        return jsonify({"error": "Something went wrong on the server."}), 500

    @jwt.unauthorized_loader
    def missing_token(_reason):
        return jsonify({"error": "Sign in to continue."}), 401

    @jwt.invalid_token_loader
    def invalid_token(_reason):
        return jsonify({"error": "Your session is not valid. Sign in again."}), 401

    @jwt.expired_token_loader
    def expired_token(_header, _payload):
        return jsonify({"error": "Your session has expired. Sign in again."}), 401

    return app
