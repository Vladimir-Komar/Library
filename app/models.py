from datetime import datetime
from app import db, login
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from hashlib import md5

import re


@login.user_loader
def load_user(id):
    return User.query.get(int(id))


followers = db.Table('followers',
    db.Column('follower_id', db.Integer, db.ForeignKey('user.id')),
    db.Column('followed_id', db.Integer, db.ForeignKey('user.id'))
)


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password_hash = db.Column(db.String(128))
    posts = db.relationship('Post', backref='author', lazy='dynamic')
    about_me = db.Column(db.String(140))
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)

    followed = db.relationship(
        'User', secondary=followers,
        primaryjoin=(followers.c.follower_id == id),
        secondaryjoin=(followers.c.followed_id == id),
        backref=db.backref('followers', lazy='dynamic'), lazy='dynamic')

    def __repr__(self):
        return '<User {}>'.format(self.username)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def avatar(self, size):
        digest = md5(self.email.lower().encode('utf-8')).hexdigest()
        return 'https://www.gravatar.com/avatar/{}?d=identicon&s={}'.format(
            digest, size)

    def follow(self, user):
        if not self.is_following(user):
            self.followed.append(user)

    def unfollow(self, user):
        if self.is_following(user):
            self.followed.remove(user)

    def is_following(self, user):
        return self.followed.filter(
            followers.c.followed_id == user.id).count() > 0

    def followed_posts(self):
        followed = Post.query.join(
            followers, (followers.c.followed_id == Post.user_id)).filter(
            followers.c.follower_id == self.id)
        own = Post.query.filter_by(user_id=self.id)
        return followed.union(own).order_by(Post.timestamp.desc())


class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.String(140))
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    def __repr__(self):
        return '<Post {}>'.format(self.body)


association_table = db.Table('association_table',
    db.Column('owner_id', db.Integer, db.ForeignKey('owner.owner_id')),
    db.Column('book_id', db.Integer, db.ForeignKey('book.book_id'))
)


def slugify(s):
    pattern = r'[^\w+]'
    return re.sub(pattern, '-', s)


class Owner(db.Model):
    owner_id = db.Column(db.Integer, primary_key=True)
    ownername = db.Column(db.String(64))
    slug = db.Column(db.String(140), unique=True)
    body = db.Column(db.Text)
    created = db.Column(db.DateTime, default=datetime.utcnow)

    subscriptions = db.relationship('Book', secondary=association_table, backref=db.backref('subscribers', lazy='dynamic'))

    def __init__(self, *args, **kwargs):
        super(Owner, self).__init__(*args, **kwargs)
        self.generate_slug()

    def generate_slug(self):
        if self.ownername:
            self.slug = slugify(self.ownername)

    def __repr__(self):
        return '<Owner owner_id: {}, ownername: {}>'.format(self.owner_id, self.ownername)

    def madebook(self, owner):
        if not self.is_foll(owner):
            self.subscriptions.append(owner)

    def unmadebook(self, owner):
        if self.is_foll(owner):
            self.subscriptions.remove(owner)

    def is_foll(self, owner):
        return self.subscriptions.filter(
            association_table.c.book_id == owner.owner_id).count() > 0

    # Список всех книг конкретного автора, автор передается в self
    def all_owner_book(self):
        return Book.query.join(
            association_table, (association_table.c.book_id == Book.book_id)).filter(
                association_table.c.owner_id == self.owner_id)


class Book(db.Model):
    book_id = db.Column(db.Integer, primary_key=True)
    bookname = db.Column(db.String(140))

    def __repr__(self):
        return '<Book {}>'.format(self.bookname)
