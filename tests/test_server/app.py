"""VRCPost mock server.

A Flask application that mimics the VRCPost UI and behavior
for local development and testing.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from pathlib import Path

from flask import (
    Flask,
    jsonify,
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
    url_for,
)
from werkzeug.utils import secure_filename

app = Flask(
    __name__,
    template_folder=str(Path(__file__).parent / "templates"),
    static_folder=str(Path(__file__).parent / "static"),
)
app.secret_key = "test-server-secret-key-for-development"

# Upload destination for images
UPLOAD_DIR = Path(__file__).parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

# In-memory data store
posts_db: list[dict] = []
stories_db: list[dict] = []
scheduled_posts_db: list[dict] = []
users_db: dict[str, dict] = {
    "test@example.com": {
        "id": "test-user-001",
        "email": "test@example.com",
        "name": "Test User",
        "username": "test_user",
        "avatar": None,
    }
}


@app.route("/")
def index():
    """Root -> redirect to home."""
    return redirect(url_for("home"))


@app.route("/home")
def home():
    """Home page (timeline)."""
    user = session.get("user")
    return render_template(
        "home.html",
        user=user,
        posts=reversed(posts_db),
        stories=stories_db,
    )


@app.route("/login", methods=["GET", "POST"])
def login():
    """Login page."""
    if request.method == "POST":
        email = request.form.get("email", "")
        # For testing: any email can log in
        if email:
            if email not in users_db:
                users_db[email] = {
                    "id": str(uuid.uuid4())[:8],
                    "email": email,
                    "name": email.split("@")[0],
                    "username": email.split("@")[0],
                    "avatar": None,
                }
            session["user"] = users_db[email]
            return redirect(url_for("home"))
    return render_template("login.html")


@app.route("/login/google")
def login_google():
    """Google OAuth mock (auto-login for testing)."""
    email = "google_user@example.com"
    if email not in users_db:
        users_db[email] = {
            "id": str(uuid.uuid4())[:8],
            "email": email,
            "name": "Google User",
            "username": "google_user",
            "avatar": None,
        }
    session["user"] = users_db[email]
    return redirect(url_for("home"))


@app.route("/logout")
def logout():
    """Logout."""
    session.pop("user", None)
    return redirect(url_for("home"))


@app.route("/post", methods=["POST"])
def create_post():
    """Create a post."""
    user = session.get("user")
    if not user:
        return jsonify({"error": "Not logged in"}), 401

    text = request.form.get("text", "")
    scheduled_at = request.form.get("scheduled_at", "")

    # Image upload
    image_urls = []
    files = request.files.getlist("images")
    for f in files:
        if f and f.filename:
            filename = f"{str(uuid.uuid4())[:8]}_{secure_filename(f.filename)}"
            filepath = UPLOAD_DIR / filename
            f.save(str(filepath))
            image_urls.append(f"/uploads/{filename}")

    post_data = {
        "id": str(uuid.uuid4())[:8],
        "user": user,
        "text": text,
        "images": image_urls,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "likes": 0,
        "scheduled_at": scheduled_at if scheduled_at else None,
    }

    if scheduled_at:
        scheduled_posts_db.append(post_data)
    else:
        posts_db.append(post_data)

    if request.headers.get("Accept") == "application/json":
        return jsonify({"success": True, "post": post_data})

    return redirect(url_for("home"))


@app.route("/story", methods=["POST"])
def create_story():
    """Create a story."""
    user = session.get("user")
    if not user:
        return jsonify({"error": "Not logged in"}), 401

    text = request.form.get("text", "")

    # Image upload
    image_url = None
    f = request.files.get("image")
    if f and f.filename:
        filename = f"{str(uuid.uuid4())[:8]}_{secure_filename(f.filename)}"
        filepath = UPLOAD_DIR / filename
        f.save(str(filepath))
        image_url = f"/uploads/{filename}"

    story_data = {
        "id": str(uuid.uuid4())[:8],
        "user": user,
        "image": image_url,
        "text": text,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
    stories_db.append(story_data)

    if request.headers.get("Accept") == "application/json":
        return jsonify({"success": True, "story": story_data})

    return redirect(url_for("home"))


@app.route("/uploads/<filename>")
def uploaded_file(filename):
    """Serve uploaded files."""
    return send_from_directory(str(UPLOAD_DIR), filename)


@app.route("/api/posts")
def api_posts():
    """Posts list API (for testing)."""
    return jsonify({"posts": posts_db})


@app.route("/api/stories")
def api_stories():
    """Stories list API (for testing)."""
    return jsonify({"stories": stories_db})


@app.route("/api/scheduled")
def api_scheduled():
    """Scheduled posts list API (for testing)."""
    return jsonify({"scheduled": scheduled_posts_db})


@app.route("/search")
def search():
    """Search page."""
    q = request.args.get("q", "")
    results = [p for p in posts_db if q.lower() in p.get("text", "").lower()]
    return render_template("home.html", user=session.get("user"), posts=results, stories=[])


@app.route("/gallery")
def gallery():
    """Gallery page."""
    return render_template(
        "home.html", user=session.get("user"), posts=posts_db, stories=stories_db
    )


def run_server(host: str = "127.0.0.1", port: int = 5000, debug: bool = True) -> None:
    """Start the test server."""
    print(f"Starting test server: http://{host}:{port}")
    app.run(host=host, port=port, debug=debug)


if __name__ == "__main__":
    run_server()
