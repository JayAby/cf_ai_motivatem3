from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, session
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, logout_user, login_required
from extensions import db
from models import User
import hashlib
from datetime import datetime, timedelta
from itsdangerous import URLSafeTimedSerializer
import secrets, string, logging
import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail 

auth_bp = Blueprint("auth",__name__, url_prefix="/auth")
logger = logging.getLogger(__name__)

# Create and Store Code
def hash_code(code: str) -> str:
    return hashlib.sha256(code.encode()).hexdigest()

def send_email(to_email: str, subject: str, html_content: str) -> bool:
    """Send email via SendGrid API."""
    message = Mail(
        from_email=os.getenv("MAIL_DEFAULT_SENDER"),
        to_emails=to_email,
        subject=subject,
        html_content=html_content
    )
    try:
        sg = SendGridAPIClient(os.getenv("SENDGRID_API_KEY"))
        response = sg.send(message)
        logger.info(f"Email sent to {to_email}, status {response.status_code}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {e}")
        return False
    
def generate_verification_code(length=6) -> str:
    return "".join(secrets.choice(string.digits) for _ in range(length))

def generate_token(email: str):
    s = URLSafeTimedSerializer(current_app.secret_key)
    return s.dumps(email, salt="email-confirm")

def decode_token(token: str, max_age=3600):
    s = URLSafeTimedSerializer(current_app.secret_key)
    return s.loads(token, salt="email-confirm", max_age=max_age)


# Signup
@auth_bp.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        first_name = request.form.get("first_name", "").strip()
        last_name = request.form.get("last_name", "").strip() or None
        email = request.form.get("email","").strip().lower()
        password = request.form.get("password", "")

        # Check required fields
        if not first_name or not email or not password:
            flash("Please fill in all required fields.", "danger")
            return render_template("signup.html")

        # Check if user exists
        if User.query.filter_by(email=email).first():
            flash("User already exists! Please log in.", "danger")
            return redirect(url_for("auth.login"))
        
        # Hash password
        hashed_pw = generate_password_hash(password, method="pbkdf2:sha256")

        # Create user
        new_user = User(
            first_name=first_name,
            last_name=last_name,
            email=email, 
            password=hashed_pw,
            is_verified= False
        )
        db.session.add(new_user)
        db.session.commit()

        try:
            # Link token (time-limited)
            code = generate_verification_code()
            # Numeric code
            code_hash = hash_code(code)
            expiry = datetime.utcnow() + timedelta(hours=1)

            # Save hashed code and expiry to user
            new_user.verification_code_hash = code_hash
            new_user.code_expires_at = expiry
            db.session.commit()

            # Save session for verify page
            session["pending_user_id"] = new_user.id
            session["pending_user_email"] = new_user.email

            # Build verification link
            token = generate_token(new_user.email) 
            link = url_for("auth.verify_email", token=token, _external=True)
            # Send email with both link and code
            body = (
                f"Hi {first_name},<br><br>"
                f"Thanks for registering. You can verify your account in two ways:<br><br>"
                f"<a href='{link}'>Click this link</a> (expires in 1 hour)<br>"
                f"or enter this verification code into the app: <b>{code}</b><br><br>"
                f"If you didn't sign up, ignore this email.<br><br>"
                "-MotivateM3 Team"
            )

            if not send_email(email, "Confirm your MotivateM3 account", body):
                flash(f"Signup failed: could not send verification email.", "danger")
                db.session.delete(new_user)
                db.session.commit()
                return render_template("signup.html")
            
            flash("A verification email has been sent. Check your inbox or spam. \n" \
            "You can either click the link or enter the code here.", "info")
            return redirect(url_for("auth.verify_code"))
        
        except Exception as e:
            logger.error(f"Signup email send failed for {email}: {e}")
            db.session.delete(new_user)
            db.session.commit()
            flash("Signup failed. Try again later.", "danger")
            return render_template("signup.html")
          
    return render_template("signup.html")


# Verify by Link
@auth_bp.route("/verify/<token>")
def verify_email(token):
    try:
        email = decode_token(token)
    except Exception:
        flash("Confirmation link is either invalid or expired.", "danger")
        return redirect(url_for("auth.signup"))
    
    # Find user
    user = User.query.filter_by(email=email).first()
    if not user:
        flash("User not found.", "danger")
        return redirect(url_for("auth.signup"))
    
    if user.is_verified:
        flash("Your account is already verified. Please log in.", "info")
        return redirect(url_for("auth.login"))
    
    # Mark new user as verified
    user.is_verified = True
    user.verification_code_hash = None
    user.code_expires_at = None
    db.session.commit()

    flash("Your email has been verified! You can now log in.", "success")
    return redirect(url_for("auth.login", verified="success"))

# Verify Code
@auth_bp.route("/verify-code", methods=["GET","POST"])
def verify_code():
    # Get the pending email from session
    email = session.get("pending_user_email")
    if not email:
        flash("No pending verification found. Please sign up first.", "danger")
        return redirect(url_for('auth.signup'))
    
    user = User.query.filter_by(email=email).first()
    if not user:
        flash("No account with the email found.", "danger")
        return redirect(url_for('auth.signup'))
    
    if user.is_verified:
        flash("Your account is already verified. Please log in.", "info")
        # Clear pending session
        session.pop("pending_user_email", None)
        session.pop("pending_user_id", None)
        return redirect(url_for("auth.login"))

    if request.method == "POST":
        code = request.form.get("code", "").strip()

        # Check expiry
        if not user.verification_code_hash or datetime.utcnow() > user.code_expires_at:
            flash("Code expired or not set.", "danger")
            return redirect(url_for("auth.signup"))
        
        # Check code hash
        if hash_code(code) == user.verification_code_hash:
            user.is_verified = True
            user.verification_code_hash = None
            user.code_expires_at = None
            db.session.commit()

            # Clear pending session
            session.pop("pending_user_email", None)
            session.pop("pending_user_id", None)

            flash("Verified! Please continue to Log in", "success")
            return redirect(url_for("auth.login", verified="success"))
        else:
            flash("Invalid verification code. Try again or request one", "danger")
            return redirect(url_for("auth.verify_code"))

    return render_template("verify_code.html", email=email)

# Resend Verification
@auth_bp.route("/resend_verification", methods=["POST"])
def resend_verification():
    pending_email = request.form.get("email") or session.get("pending_user_email")

    if not pending_email:
        flash("No pending verification found. Please log in or signup first.", "danger")
        return redirect(url_for("auth.signup"))

    user = User.query.filter_by(email=pending_email).first()
    if not user:
        flash("No account found with that email.", "danger")
        return redirect(url_for("auth.signup"))
    
    if user.is_verified:
        flash("Your account is already verified. Please log in.", "info")
        return redirect(url_for("auth.login"))
    
    # Generate new code + hash
    code = generate_verification_code()
    code_hash = hash_code(code)
    expiry = datetime.utcnow() + timedelta(hours=1)

    # Update DB
    user.verification_code_hash = code_hash
    user.code_expires_at = expiry
    db.session.commit()

    # Send email + new link
    token = generate_token(user.email)
    link = url_for("auth.verify_email", token=token, _external=True)
    body = (
        f"Hi {user.first_name},<br><br>"
        f"Here is your new verification link (valid for 1 hour): <a href='{link}'>Verify Email</a><br>"
        f"Or enter this code in the app: <b>{code}</b><br><br>"
        f"- MotivateM3 Team"
    )
    send_email(user.email, "Resend Verification - MotivateM3", body)

    # Save session to pre-fill email in verify-code page
    session["pending_user_email"] = user.email
    session["pending_user_id"] = user.id
    flash("A new verification email has been sent.", "success")
    return redirect(url_for("auth.login", show_code_modal="true"))

# Login
@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower() or session.get("pending_user_email")
        password = request.form.get("password", "").strip()
        
        if not email or not password:
            flash("Please enter both email and password. ", "danger")
            return render_template("login.html")

        # Find user
        user = User.query.filter_by(email=email).first()
        if not user:
            flash("No account found with that email.", "danger")
            return render_template("login.html")
        # Check password
        if not check_password_hash(user.password, password):
            flash("Incorrect password. Please try again.", "danger")
            return render_template("login.html")
        # Check is user is verified
        if  not user.is_verified:
            # Save pending user info to session
            session["pending_user_email"] = user.email
            session["pending_user_id"] = user.id
            flash("Please verify your email before logging in. Check your inbox or resend the code.", "warning")
            return redirect(url_for("auth.login", show_code_modal="true"))
        
        # If no issues, log in
        login_user(user)
        flash(f"Welcome back!, {user.first_name}!", "success")
        return redirect(url_for("motivation.home"))
    
    return render_template("login.html")

# Logout
@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))

# Edit Profiles
@auth_bp.route("/edit-profile", methods=["GET", "POST"])
@login_required
def edit_profile():
    pass