from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from itsdangerous import URLSafeTimedSerializer

db = SQLAlchemy()
login_manager = LoginManager()
s = None