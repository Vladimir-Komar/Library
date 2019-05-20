from app import app, db
from app.models import User, Post, Owner, Book


@app.shell_context_processor
def make_shell_context():
    return {'db': db, 'User': User, 'Post': Post, 'Owner': Owner, 'Book': Book}
