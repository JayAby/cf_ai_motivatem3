from flask import Blueprint, render_template, request, redirect, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, logout_user, login_required
from models import db, User

auth_bp = Blueprint("auth",__name__)

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
            flash("Please fill in all required fields.", "error")
            return redirect(url_for("auth.signup"))

        # Check if user exists
        if User.query.filter_by(email=email).first():
            flash("User already exists!", "error")
            return redirect(url_for("auth.signup"))
        
        # Hash password
        hashed_pw = generate_password_hash(password, method="pbkdf2:sha256")
  
        # Create user
        new_user = User(
            first_name=first_name,
            last_name=last_name,
            email=email, 
            password=hashed_pw
        )
        db.session.add(new_user)
        db.session.commit()

        # Auto Login
        login_user(new_user)
        flash(f"Welcome, {new_user.first_name}! to MotivateM3")
        return redirect(url_for("motivation.home"))

        # Login Manually
        # flash("Account created! Please log in.", "success")
        # return redirect(url_for("auth.login"))
    
    return render_template("signup.html")

# Login
@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "").strip()

        user = User.query.filter_by(email=email).first()

        if not user or not check_password_hash(user.password, password):
            flash("Invalid email or password", "error")
            return redirect(url_for("auth.login"))
        
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