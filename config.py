# stockflow-backend/config.py

import os

class Config:
    """Base configuration for the Flask application."""
    # Use an in-memory SQLite for development/testing.
    # For production, replace with a persistent database like PostgreSQL or MySQL.
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///inventory.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False # Suppresses a warning, set to True for debugging modification tracking
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'a_very_secret_key_for_development_only'