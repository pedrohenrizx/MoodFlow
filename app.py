import os
import sqlite3
from functools import wraps

from flask import (
    Flask,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
    flash,
)
from werkzeug.security import check_password_hash, generate_password_hash


app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-key")
app.config["DATABASE"] = os.path.join(app.root_path, "moodflow.db")
app.config["DB_INITIALIZED"] = False

if app.config["SECRET_KEY"] == "dev-secret-key":
    if os.environ.get("FLASK_ENV") == "production" or os.environ.get("ENV") == "production":
        raise RuntimeError("SECRET_KEY must be set in production.")
    if not app.debug:
        app.logger.warning("Using development SECRET_KEY. Set SECRET_KEY in environment for production.")


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(exception):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = get_db()
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS moods (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            mood_level TEXT NOT NULL,
            emotions TEXT,
            intensity INTEGER,
            category TEXT,
            tags TEXT,
            notes TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );
        """
    )
    db.commit()


@app.before_request
def ensure_db():
    if not app.config.get("DB_INITIALIZED"):
        init_db()
        app.config["DB_INITIALIZED"] = True


def login_required(view):
    @wraps(view)
    def wrapped_view(**kwargs):
        if "user_id" not in session:
            flash("Entre para acessar o MoodFlow.")
            return redirect(url_for("login"))
        return view(**kwargs)

    return wrapped_view


def friendly_name(name, email):
    if name:
        return name
    if email and "@" in email:
        return email.split("@")[0]
    return ""


@app.route("/")
def landing():
    if session.get("user_id"):
        return redirect(url_for("dashboard"))
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if session.get("user_id"):
        return redirect(url_for("dashboard"))
    error = None
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        db = get_db()
        if not email or not password:
            error = "Preencha e-mail e senha."
        elif db.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone():
            error = "Este e-mail já está cadastrado."
        else:
            hashed = generate_password_hash(password)
            cur = db.execute(
                "INSERT INTO users (name, email, password) VALUES (?, ?, ?)",
                (name, email, hashed),
            )
            db.commit()
            session["user_id"] = cur.lastrowid
            session["user_name"] = friendly_name(name, email)
            return redirect(url_for("dashboard"))
    return render_template("register.html", error=error)


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("dashboard"))
    error = None
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        db = get_db()
        user = db.execute(
            "SELECT * FROM users WHERE email = ?", (email,)
        ).fetchone()
        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            session["user_name"] = friendly_name(user["name"], email)
            return redirect(url_for("dashboard"))
        error = "Credenciais inválidas. Tente novamente."
    return render_template("login.html", error=error)


@app.route("/logout")
def logout():
    session.clear()
    flash("Você saiu do MoodFlow. Volte quando quiser!")
    return redirect(url_for("landing"))


@app.route("/dashboard", methods=["GET", "POST"])
@login_required
def dashboard():
    db = get_db()
    if request.method == "POST":
        mood_level = request.form.get("mood_level")
        emotions = request.form.getlist("emotions")
        intensity = request.form.get("intensity")
        category = request.form.get("category")
        tags = request.form.get("tags", "").strip()
        notes = request.form.get("notes", "").strip()
        if mood_level:
            intensity_value = None
            if intensity and intensity.strip():
                try:
                    intensity_value = int(intensity)
                except ValueError:
                    app.logger.warning("Ignoring invalid intensity input: %s", intensity)
                    intensity_value = None
            emotions_text = ", ".join(emotions) if emotions else None
            db.execute(
                """
                INSERT INTO moods (user_id, mood_level, emotions, intensity, category, tags, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session["user_id"],
                    mood_level,
                    emotions_text,
                    intensity_value,
                    category,
                    tags,
                    notes,
                ),
            )
            db.commit()
            flash("Registro emocional salvo com sucesso!")
        return redirect(url_for("dashboard"))

    entries = db.execute(
        "SELECT * FROM moods WHERE user_id = ? ORDER BY created_at DESC LIMIT 12",
        (session["user_id"],),
    ).fetchall()
    most_recent = "Sem registros"
    if entries:
        most_recent = entries[0]["mood_level"]
    return render_template(
        "dashboard.html",
        entries=entries,
        most_recent=most_recent,
        user_name=session.get("user_name"),
    )


@app.route("/profile")
@login_required
def profile():
    db = get_db()
    user = db.execute(
        "SELECT id, name, email FROM users WHERE id = ?", (session["user_id"],)
    ).fetchone()
    total_entries = db.execute(
        "SELECT COUNT(*) as total FROM moods WHERE user_id = ?", (session["user_id"],)
    ).fetchone()["total"]
    latest = db.execute(
        "SELECT mood_level, created_at FROM moods WHERE user_id = ? ORDER BY created_at DESC LIMIT 1",
        (session["user_id"],),
    ).fetchone()
    return render_template(
        "profile.html",
        user=user,
        total_entries=total_entries,
        latest=latest,
    )


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")
