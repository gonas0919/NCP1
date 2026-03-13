import os
import time

import psycopg
from flask import Flask, flash, g, redirect, render_template, request, session, url_for
from psycopg import errors
from psycopg.rows import dict_row
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "change-me-in-production")
app.config["DATABASE_URL"] = os.environ.get(
    "DATABASE_URL",
    "postgresql://appuser:apppassword@db:5432/appdb",
)
app.config["DB_INIT_RETRIES"] = int(os.environ.get("DB_INIT_RETRIES", "20"))
app.config["DB_INIT_DELAY_SECONDS"] = float(os.environ.get("DB_INIT_DELAY_SECONDS", "1.5"))


def get_db():
    if "db" not in g:
        g.db = psycopg.connect(app.config["DATABASE_URL"], row_factory=dict_row)
    return g.db


@app.teardown_appcontext
def close_db(_exception):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id BIGSERIAL PRIMARY KEY,
                username VARCHAR(64) NOT NULL UNIQUE,
                email VARCHAR(255) NOT NULL UNIQUE,
                password_hash VARCHAR(255) NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
    db.commit()


def initialize_database_with_retry():
    last_error = None
    for attempt in range(1, app.config["DB_INIT_RETRIES"] + 1):
        try:
            with app.app_context():
                init_db()
            return
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            app.logger.warning(
                "DB init failed (%s/%s): %s",
                attempt,
                app.config["DB_INIT_RETRIES"],
                exc,
            )
            time.sleep(app.config["DB_INIT_DELAY_SECONDS"])

    raise RuntimeError("Unable to initialize database after retries") from last_error


def find_current_user():
    user_id = session.get("user_id")
    if user_id is None:
        return None

    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            "SELECT id, username, email, created_at FROM users WHERE id = %s",
            (user_id,),
        )
        return cur.fetchone()


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
                with db.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO users (username, email, password_hash)
                        VALUES (%s, %s, %s)
                        """,
                        (username, email, generate_password_hash(password)),
                    )
                db.commit()
            except errors.UniqueViolation:
                db.rollback()
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
        with db.cursor() as cur:
            cur.execute(
                """
                SELECT id, username, email, password_hash
                FROM users
                WHERE username = %s OR email = %s
                """,
                (identity, identity),
            )
            user = cur.fetchone()

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


initialize_database_with_retry()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
