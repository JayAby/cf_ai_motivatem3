from flask import Flask, redirect, url_for, abort, render_template
from dotenv import load_dotenv
from flask_login import current_user, login_required
from extensions import db, login_manager, mail
from models import User
from blueprints.motivation import motivation_bp
from blueprints.auth_routes import auth_bp
from itsdangerous import URLSafeTimedSerializer
import os

# Load .env
load_dotenv(override=True)

# Create app factory
def create_app():
    app = Flask(__name__)

    # Secret Key
    app.secret_key = os.getenv("SECRET_KEY", "fallbacksecret")

    # Database setup
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///motivatem3.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    db.init_app(app)

    # Mail Config
    app.config['MAIL_SERVER'] = 'smtp.sendgrid.net'
    app.config['MAIL_PORT'] = 587
    app.config['MAIL_USE_TLS'] = True
    app.config['MAIL_USERNAME'] = 'apikey'
    app.config['MAIL_PASSWORD'] = os.getenv('SENDGRID_API_KEY')
    app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER')

    # Initialise extensions
    mail.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"

    # Token Serializer
    s = URLSafeTimedSerializer(app.secret_key)

    # Register blueprints
    app.register_blueprint(motivation_bp)
    app.register_blueprint(auth_bp)

    # Test email route
    @app.route("/test-email")
    def test_email():
        from flask_mail import Message
        msg = Message("Test from MotivateM3", recipients=["joelabiola04@gmail.com"])
        msg.body = "This is a test email sent via SendGrid!"
        try:
            mail.send(msg)
            return "Email sent successfully!"
        except Exception as e:
            return f"Error: {str(e)}"

    # Default route
    @app.route("/")
    def index():
        return redirect(url_for("auth.login"))

    # Admin dashboard
    @app.route("/admin")
    @login_required
    def admin_dashboard():
        if not current_user.is_admin:
            abort(403)
            return redirect(url_for("motivation.home"))

        users = User.query.all()
        return render_template("admin.html", users=users)

    return app

# User loader
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Only used if running locally
if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        db.create_all()
    app.run(debug=True)
