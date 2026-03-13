import os
import sqlite3
from pathlib import Path

from flask import Flask, flash, g, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "change-me-in-production")
app.config["DATABASE_PATH"] = os.environ.get("DATABASE_PATH", str(Path("data") / "app.db"))


def get_db():
    if "db" not in g:
        db_path = Path(app.config["DATABASE_PATH"])
        db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        g.db = conn
    return g.db


@app.teardown_appcontext
def close_db(_exception):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = get_db()
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    db.commit()


def find_current_user():
    user_id = session.get("user_id")
    if user_id is None:
        return None
    db = get_db()
    return db.execute(
        "SELECT id, username, email, created_at FROM users WHERE id = ?",
        (user_id,),
    ).fetchone()


@app.context_processor
def inject_user():
    return {"current_user": find_current_user()}


@app.route("/")
def home():
    user = find_current_user()
    if user is None:
        return redirect(url_for("login"))
    return render_template("index.html", user=user)


@app.route("/register", methods=["GET", "POST"])
def register():
    if find_current_user() is not None:
        return redirect(url_for("home"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if len(username) < 3:
            flash("아이디는 3자 이상으로 입력해 주세요.", "error")
        elif "@" not in email or "." not in email:
            flash("유효한 이메일 형식을 입력해 주세요.", "error")
        elif len(password) < 8:
            flash("비밀번호는 8자 이상으로 설정해 주세요.", "error")
        elif password != confirm_password:
            flash("비밀번호 확인이 일치하지 않습니다.", "error")
        else:
            db = get_db()
            try:
                db.execute(
                    "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
                    (username, email, generate_password_hash(password)),
                )
                db.commit()
            except sqlite3.IntegrityError:
                flash("이미 사용 중인 아이디 또는 이메일입니다.", "error")
            else:
                flash("회원가입이 완료되었습니다. 로그인해 주세요.", "success")
                return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if find_current_user() is not None:
        return redirect(url_for("home"))

    if request.method == "POST":
        identity = request.form.get("identity", "").strip().lower()
        password = request.form.get("password", "")
        db = get_db()
        user = db.execute(
            "SELECT id, username, email, password_hash FROM users WHERE username = ? OR email = ?",
            (identity, identity),
        ).fetchone()

        if user is None or not check_password_hash(user["password_hash"], password):
            flash("아이디(또는 이메일) / 비밀번호가 올바르지 않습니다.", "error")
        else:
            session.clear()
            session["user_id"] = user["id"]
            flash(f"{user['username']}님, 로그인되었습니다.", "success")
            return redirect(url_for("home"))

    return render_template("login.html")


@app.post("/logout")
def logout():
    session.clear()
    flash("로그아웃되었습니다.", "info")
    return redirect(url_for("login"))


@app.route("/health")
def health():
    return {"status": "ok"}, 200


with app.app_context():
    init_db()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
