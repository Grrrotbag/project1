# This file is where we will import the csv data into the database
import csv
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

# Check environment variable is set
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
# postgres://gyumfyvcqyxxbw:940db23022f6a68a48d6fadb85b7535ce61d07f9976435c5a8693455986c5c4a@ec2-54-247-98-162.eu-west-1.compute.amazonaws.com:5432/d701s522dl15cj
db = scoped_session(sessionmaker(bind=engine))

def main():
    # This now works, but only if all the column data types are set as text. I believe csv is stored as text.
    f = open('config/books.csv')
    reader = csv.reader(f)
    for isbn, title, author, year in reader:
        db.execute("INSERT INTO books (isbn, title, author, year) VALUES (:isbn, :title, :author, :year)",
                {"isbn": isbn, "title": title, "author": author, "year": year})
        print(f"Added {title} by {author}, isbn {isbn} released {year} to the database.")
    db.commit()

if __name__ == "__main__":
    main()