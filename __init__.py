# stockflow-backend/app/__init__.py

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from config import Config # Import the Config class

db = SQLAlchemy()

def create_app():
    """
    Creates and configures the Flask application.
    """
    app = Flask(__name__)
    app.config.from_object(Config) # Load configuration from Config class

    db.init_app(app) # Initialize SQLAlchemy with the Flask app

    # Import the Blueprint and register it with the app
    from app.routes import api_bp # Import the blueprint directly
    app.register_blueprint(api_bp) # Register the blueprint

    return app