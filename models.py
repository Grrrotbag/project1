from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String, nullable=False, unique=True)
    password = db.Column(db.String, nullable=False)
    reviews = db.relationship('Review', backref='review', lazy=True)

    def __repr__(self):
        return '<User %r>' % self.username


class Book(db.Model):
    __tablename__ = "books"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String, nullable=False)
    author = db.Column(db.String, nullable=False)
    isbn = db.Column(db.String, nullable=False)
    year = db.Column(db.String, nullable=False)
    reviews = db.relationship('Review', backref='review', lazy=True)

    def __repr__(self):
        return '<Book %r>' % self.title


class Review(db.Model):
    __tablename__ = "reviews"
    id = db.Column(db.Integer, primary_key=True)
    book_id = db.Column(db.Integer, db.ForeignKey("books.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    star_rating = db.Column(db.Integer, nullable=False)
    review_text = db.Column(db.Text, nullable=True)
    date_created = db.Column(db.DateTime, nullable=False, default=datetime.now())

    def __repr__(self):
        return '<Review %r>' % self.book_id