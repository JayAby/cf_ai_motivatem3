from flask import Flask, abort, render_template, request, flash, redirect, url_for
from dotenv import load_dotenv
from flask_login import LoginManager, current_user, login_required
from flask_sqlalchemy import SQLAlchemy
from models import db, User
from motivation import motivation_bp
from auth import auth_bp
import os

# Load .env and override any system/global variables
load_dotenv(override=True)

# Create app
app = Flask(__name__)
# Get Secret Key 
app.secret_key = os.getenv("SECRET_KEY", "fallbacksecret")

# Database setup
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///motivatem3.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.init_app(app)

# Login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "auth.login" # Redirect if not logged in

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Register blueprint
app.register_blueprint(motivation_bp)
app.register_blueprint(auth_bp)

# Default route -> Login
@app.route("/")
def index():
    return redirect(url_for("auth.login"))

@app.route("/admin")
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        abort(403)
        return redirect(url_for("motivation.home"))
    
    users = User.query.all()
    return render_template("admin.html", users=users)

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)