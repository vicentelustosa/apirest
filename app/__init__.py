from flask import Flask
from marshmallow import ValidationError
from werkzeug.exceptions import NotFound
from http.client import HTTPException

from .config import Config
from .extensions import db, ma, migrate
from .routes.messages import messages_bp
from .routes.users import users_bp


def create_app():
    app = Flask(__name__)

    app.config.from_object(Config)

    db.init_app(app)
    migrate.init_app(app, db)
    ma.init_app(app)

    from .models import message, user  # noqa: F401

    app.register_blueprint(messages_bp, url_prefix="/messages")
    app.register_blueprint(users_bp, url_prefix="/users")

    @app.errorhandler(ValidationError)
    def handle_validation_error(err):
        return {"success": False, "errors": err.messages}, 400

    @app.errorhandler(NotFound)
    def handle_not_found(err):
        return {"success": False, "message": "Recurso nao encontrado"}, 404

    @app.errorhandler(404)
    def handle_404(err):
        return {"success": False, "message": "Rota nao encontrada"}, 404

    @app.errorhandler(Exception)
    def handle_generic_exception(e):
        # Passa o código de erro correto se for um HTTPException
        if isinstance(e, HTTPException):
            return e
        # Se for uma exceção inesperada (ex: bug no Python), retorna 500
        return {"success": False, "message": "Erro interno do servidor"}, 500
    
    return app
