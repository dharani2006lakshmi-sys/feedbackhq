import os
import sqlite3
from functools import wraps
from flask import Flask, flash, g, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
# shortcut: static dev fallback secret key, set SECRET_KEY env var in production
app.secret_key = os.environ.get("SECRET_KEY", "feedbackhq-dev-secret")
_default_db = "/tmp/feedback.db" if os.environ.get("VERCEL") else os.path.join(app.root_path, "feedback.db")
DB_PATH = os.environ.get("FEEDBACK_DB", _default_db)


def get_db():
    if "db" not in g:
        if not os.path.exists(DB_PATH):
            init_db()
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = sqlite3.connect(DB_PATH)
    try:
        with db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL,
                    email TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'user'
                );
                CREATE TABLE IF NOT EXISTS feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    product TEXT NOT NULL,
                    rating INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 5),
                    comment TEXT NOT NULL,
                    date TEXT NOT NULL,
                    status TEXT NOT NULL,
                    FOREIGN KEY(user_id) REFERENCES users(id)
                );
                """
            )
            cols = {row[1] for row in db.execute("PRAGMA table_info(users)").fetchall()}
            if "role" not in cols:
                db.execute("ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'user'")

            admin = db.execute("SELECT id FROM users WHERE email = ?", ("admin@feedbackhq.com",)).fetchone()
            if admin is None:
                db.execute(
                    "INSERT INTO users (username, email, password_hash, role) VALUES (?, ?, ?, 'admin')",
                    ("Admin", "admin@feedbackhq.com", generate_password_hash("admin1234")),
                )

            demo_user = db.execute("SELECT id FROM users WHERE email = ?", ("user@feedbackhq.com",)).fetchone()
            if demo_user is None:
                cur = db.execute(
                    "INSERT INTO users (username, email, password_hash, role) VALUES (?, ?, ?, 'user')",
                    ("Demo User", "user@feedbackhq.com", generate_password_hash("user1234")),
                )
                demo_id = cur.lastrowid
                if db.execute("SELECT COUNT(*) FROM feedback").fetchone()[0] == 0:
                    db.executemany(
                        "INSERT INTO feedback (user_id, product, rating, comment, date, status) VALUES (?, ?, ?, ?, ?, ?)",
                        [
                            (demo_id, "Pro Dashboard v2", 5, "Clean dark UI and fast analytics.", "2026-11-10", "positive"),
                            (demo_id, "Mobile App", 4, "Smooth navigation, dark mode looks great.", "2026-11-09", "positive"),
                            (demo_id, "API Gateway", 3, "Solid uptime, docs could use more examples.", "2026-11-08", "neutral"),
                            (demo_id, "Checkout Flow", 2, "Coupon input took two tries to apply.", "2026-11-07", "negative"),
                        ],
                    )
    finally:
        db.close()


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            flash("Please sign in first.", "error")
            return redirect(url_for("login"))
        return view(*args, **kwargs)

    return wrapped


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            flash("Please sign in as admin.", "error")
            return redirect(url_for("admin_login"))
        if session.get("role") != "admin":
            flash("Admin access required.", "error")
            return redirect(url_for("submit"))
        return view(*args, **kwargs)

    return wrapped


def _home_for_role():
    return url_for("dashboard") if session.get("role") == "admin" else url_for("submit")


def _authenticate(expected_role, fail_endpoint, success_endpoint):
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    user = get_db().execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()

    if not user or not check_password_hash(user["password_hash"], password):
        flash("Invalid email or password.", "error")
        return redirect(fail_endpoint)

    if user["role"] != expected_role:
        portal = "Admin Login" if user["role"] == "admin" else "User Login"
        flash(f"Please use the {portal} page for this account.", "error")
        return redirect(fail_endpoint)

    session["user_id"] = user["id"]
    session["username"] = user["username"]
    session["role"] = user["role"]
    flash(f"Welcome back, {user['username']}!", "success")
    return redirect(success_endpoint)


@app.route("/")
def index():
    if "user_id" in session:
        return redirect(_home_for_role())
    return render_template("login.html", login_mode="user")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        if "user_id" in session:
            return redirect(_home_for_role())
        return render_template("login.html", login_mode="user")
    return _authenticate("user", url_for("login"), url_for("submit"))


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "GET":
        if session.get("role") == "admin":
            return redirect(url_for("dashboard"))
        return render_template("login.html", login_mode="admin")
    return _authenticate("admin", url_for("admin_login"), url_for("dashboard"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not username or not email or not password:
            flash("All fields are required.", "error")
            return render_template("register.html")

        db = get_db()
        try:
            db.execute(
                "INSERT INTO users (username, email, password_hash, role) VALUES (?, ?, ?, 'user')",
                (username, email, generate_password_hash(password)),
            )
            db.commit()
        except sqlite3.IntegrityError:
            flash("An account with that email already exists.", "error")
            return render_template("register.html")

        flash("Account created! Please sign in.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/dashboard")
@admin_required
def dashboard():
    db = get_db()
    stats = db.execute(
        """
        SELECT
            COUNT(*) AS total,
            COALESCE(ROUND(AVG(rating), 1), 0) AS avg_rating,
            SUM(CASE WHEN rating >= 4 THEN 1 ELSE 0 END) AS positive_count,
            SUM(CASE WHEN rating <= 2 THEN 1 ELSE 0 END) AS negative_count
        FROM feedback
        """
    ).fetchone()
    recent = db.execute(
        """
        SELECT f.*, u.username
        FROM feedback f
        JOIN users u ON u.id = f.user_id
        ORDER BY f.id DESC
        LIMIT 5
        """
    ).fetchall()
    return render_template(
        "dashboard.html",
        username=session.get("username", "User"),
        total=stats["total"],
        avg_rating=stats["avg_rating"],
        positive_count=stats["positive_count"] or 0,
        negative_count=stats["negative_count"] or 0,
        recent=recent,
    )


@app.route("/submit", methods=["GET", "POST"])
@login_required
def submit():
    if request.method == "POST":
        product = request.form.get("product", "").strip()
        comment = request.form.get("comment", "").strip()
        date = request.form.get("date", "").strip()
        try:
            rating = int(request.form.get("rating", "0"))
        except ValueError:
            rating = 0

        if not product or not comment or not date or not (1 <= rating <= 5):
            flash("Please complete all fields and select a rating (1–5).", "error")
            return render_template("submit.html")

        status = "positive" if rating >= 4 else ("negative" if rating <= 2 else "neutral")
        db = get_db()
        db.execute(
            "INSERT INTO feedback (user_id, product, rating, comment, date, status) VALUES (?, ?, ?, ?, ?, ?)",
            (session["user_id"], product, rating, comment, date, status),
        )
        db.commit()
        flash("Feedback submitted!", "success")
        return redirect(url_for("feedback"))

    return render_template("submit.html")


@app.route("/feedback")
@login_required
def feedback():
    db = get_db()
    if session.get("role") == "admin":
        rows = db.execute(
            """
            SELECT f.*, u.username
            FROM feedback f
            JOIN users u ON u.id = f.user_id
            ORDER BY f.id DESC
            """
        ).fetchall()
    else:
        rows = db.execute(
            """
            SELECT f.*, u.username
            FROM feedback f
            JOIN users u ON u.id = f.user_id
            WHERE f.user_id = ?
            ORDER BY f.id DESC
            """,
            (session["user_id"],),
        ).fetchall()
    return render_template("feedback.html", items=rows)


@app.route("/logout")
def logout():
    was_admin = session.get("role") == "admin"
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("admin_login" if was_admin else "login"))


init_db()

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True, use_reloader=False)
