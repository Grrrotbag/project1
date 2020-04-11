#################
#### imports ####
#################
import os
import requests
from datetime import datetime

from flask import (
    Flask,
    session,
    render_template,
    request,
    flash,
    redirect,
    url_for,
    jsonify,
    abort,
)

# flask_session used to work when I first wrote this, but not any more. Removed to use session built in to flask.
# from flask_session import Session
from functools import wraps
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from werkzeug.security import check_password_hash, generate_password_hash
from models import *

################
#### config ####
################
app = Flask(__name__)

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
app.secret_key = "supersecret"
# The following line used to work when flask_session worked, but not any more. Commenting out seems to fix the issue.
# Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

################
#### login #####
################


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "logged_in" not in session:
            return redirect(url_for("login", next=request.url))
        return f(*args, **kwargs)

    return decorated_function


#####################
#### auth routes ####
#####################
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        error = None

        if not username:
            error = "Username is required."
        elif not password:
            error = "Password is required."
        elif (
            db.execute(
                "SELECT id FROM users WHERE username = :username",
                {"username": username},
            ).fetchone()
            is not None
        ):
            error = f"User {username} is already registered."

        if error is None:
            db.execute(
                "INSERT INTO users (username, password) VALUES (:username, :password)",
                {"username": username, "password": generate_password_hash(password)},
            )
            db.commit()
            flash(f"User {username} created.", "success")
            return redirect(url_for("login"))

        flash(error, "danger")

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        username_db = db.execute(
            "SELECT username FROM users WHERE username = :username",
            {"username": username},
        ).fetchone()
        if username_db is not None:
            password_db = db.execute(
                "SELECT password FROM users WHERE username = :username",
                {"username": username},
            ).fetchone()
            password_db = password_db[0]
            allowed = check_password_hash(password_db, password)
            if allowed is True:
                session["logged_in"] = True
                session["username"] = username
                flash(f"Logged in successfully. Welcome {username}.", "success")
                return redirect(url_for("books"))
            else:
                flash("Login failed.", "danger")
                return render_template("login.html")
        else:
            flash("no user with that name", "danger")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully.", "success")
    return redirect(url_for("login"))


#########################
#### standard routes ####
#########################

# This is the home page when logged in. It will have the complete list of books (probably paginated) and will have a search box at the top.
@app.route("/search", methods=["GET", "POST"])
@app.route("/books")
@app.route("/")
@login_required
def books():
    if request.method == "POST":
        query = request.form.get("search")
        books = db.execute(
            "SELECT * FROM books WHERE title ILIKE :query OR author ILIKE :query OR isbn LIKE :query OR year LIKE :query ORDER BY title",
            {"query": "%" + query + "%"},
        ).fetchall()
        if not books:
            flash("No books found. Please search again.", "danger")
            return redirect(url_for("books"))
        return render_template("books.html", books=books)
    else:
        # books = db.execute("SELECT * FROM books ORDER BY title").fetchall()
        books = []
        return render_template("books.html", books=books)


# Choosing a book will go to this detail view
@app.route("/books/<int:book_id>")
@login_required
def book(book_id):
    book = db.execute("SELECT * FROM books WHERE id = :id", {"id": book_id}).fetchone()
    gr_data = requests.get(
        "https://www.goodreads.com/book/review_counts.json",
        params={"key": "5hmm8TL0WdOEmWRajxg1w", "isbns": book.isbn},
    )
    goodreads = gr_data.json()
    # gbooks = requests.get("https://www.googleapis.com/books/v1/volumes?q=isbn:0142000655")
    reviews = db.execute(
        "SELECT * FROM reviews JOIN users ON users.id = reviews.user_id WHERE book_id = :book_id ORDER BY date_created DESC",
        {"book_id": book_id},
    ).fetchall()
    return render_template(
        "detail.html", book=book, goodreads=goodreads, reviews=reviews
    )


# the detail view will have a link to leave a review, leading to this URL
@app.route("/books/<int:book_id>/review", methods=["POST"])
@login_required
def review(book_id):
    book = db.execute("SELECT * FROM books WHERE id = :id", {"id": book_id}).fetchone()
    user = db.execute(
        "SELECT id, username FROM users WHERE username ILIKE :username",
        {"username": "%" + session["username"] + "%"},
    ).fetchone()
    review = request.form["review"]
    rating = request.form["rating"]
    # Check if user has already rated book
    pr = db.execute(
        "SELECT user_id FROM reviews WHERE user_id = :user_id", {"user_id": user.id}
    ).fetchall()
    if not pr:
        db.execute(
            'INSERT INTO reviews ("book_id", "user_id", "star_rating", "review_text") VALUES (:book_id, :user_id, :star_rating, :review_text)',
            {
                "book_id": book.id,
                "user_id": user.id,
                "star_rating": rating,
                "review_text": review,
            },
        )
        db.commit()
    else:
        flash("You have already reviewed this book.", "warning")
    return redirect(url_for("book", book_id=book.id))


#############
#### api ####
#############
@app.errorhandler(404)
def resource_not_found(e):
    return jsonify(error=str(e)), 404


@app.route("/api/<isbn>", methods=["GET"])
def book_api(isbn):
    """return details about a single book"""

    # make sure book exists
    book = db.execute(
        "SELECT * FROM books WHERE isbn = :isbn", {"isbn": isbn}
    ).fetchone()

    if book is None:
        abort(404, description="Book not found")

    gr_data = requests.get(
        "https://www.goodreads.com/book/review_counts.json",
        params={"key": "5hmm8TL0WdOEmWRajxg1w", "isbns": book.isbn},
    )
    goodreads = gr_data.json()

    return jsonify(
        {
            "title": book.title,
            "author": book.author,
            "year": book.year,
            "isbn": book.isbn,
            "review_count": goodreads["books"][0]["work_reviews_count"],
            "average_score": goodreads["books"][0]["average_rating"],
        }
    )
