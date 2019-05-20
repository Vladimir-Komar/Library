from flask import render_template, flash, redirect, url_for, request
from flask_login import login_user, logout_user, current_user, login_required
from werkzeug.urls import url_parse
from app import app, db
from app.forms import LoginForm, RegistrationForm, LibraryForm, EditProfileForm, PostForm
from app.models import User, Owner, Book, Post
from datetime import datetime


@app.before_request
def before_request():
    if current_user.is_authenticated:
        current_user.last_seen = datetime.utcnow()
        db.session.commit()


@app.route('/', methods=['GET', 'POST'])
@app.route('/index', methods=['GET', 'POST'])
@login_required
def index():
    form = PostForm()
    if form.validate_on_submit():
        post = Post(body=form.post.data, author=current_user)
        db.session.add(post)
        db.session.commit()
        flash('Your post is now live!')
        return redirect(url_for('index'))
    posts = current_user.followed_posts().all()
    return render_template("index.html", title='Home Page', form=form,
                           posts=posts)


@app.route('/explore')
@login_required
def explore():
    posts = Post.query.order_by(Post.timestamp.desc()).all()
    return render_template('index.html', title='Explore', posts=posts)


@app.route('/user/<username>')
@login_required
def user(username):
    user = User.query.filter_by(username=username).first_or_404()
    posts = [
        {'author': user, 'body': 'Test is post #1'},
        {'author': user, 'body': 'Test post #2'}
    ]
    return render_template('user.html', user=user, posts=posts)


@app.route('/owner/<ownername>')
@login_required
def owner(ownername):
    owner = Owner.query.filter_by(ownername=ownername).first_or_404()
    posts = [
        {'author': owner, 'body': 'Test is post #1'},
        {'author': owner, 'body': 'Test post #2'}
    ]
    return render_template('owner.html', owner=owner, posts=posts)


@app.route('/follow/<username>')
@login_required
def follow(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('User {} not found.'.format(username))
        return redirect(url_for('index'))
    if user == current_user:
        flash('You cannot follow yourself!')
        return redirect(url_for('user', username=username))
    current_user.follow(user)
    db.session.commit()
    flash('You are following {}!'.format(username))
    return redirect(url_for('user', username=username))


@app.route('/unfollow/<username>')
@login_required
def unfollow(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('User {} not found.'.format(username))
        return redirect(url_for('index'))
    if user == current_user:
        flash('You cannot unfollow yourself!')
        return redirect(url_for('user', username=username))
    current_user.unfollow(user)
    db.session.commit()
    flash('You are not following {}.'.format(username))
    return redirect(url_for('user', username=username))

# показ всех авторов
@app.route('/author')
@login_required
def author():
    q = request.args.get('q')
    if q:
        books = Book.query.filter(Book.bookname.contains(q)).all()
        ollname = Owner.query.filter(Owner.ownername.contains(q) | Owner.body.contains(q)).all()
    else:
        ollname = Owner.query.all()
        books = Book.query.all()
    return render_template('author.html', owners=ollname, books=books)


# delete owner
@app.route('/delete/<slug>')
@login_required
def delete(slug):
    owners = Owner.query.filter(Owner.slug==slug).first()
    db.session.delete(owners)
    db.session.commit()
    flash('Автора больше нет!')
    return redirect(url_for('library'))


@app.route('/bookdel/<slug>, <bookname>')
@login_required
def bookdel(slug, bookname):
    owners = Owner.query.filter(Owner.slug == slug).first()
    booknames = Book.query.filter(Book.bookname == bookname).first()
    owners.subscriptions.remove(booknames)
    db.session.commit()
    flash('"{}" has been removed'.format(bookname))
    books = owners.subscriptions
    return render_template('author_detail.html', owner=owners, books=books)


# http://localhost/Mark-Tven
@app.route('/<slug>')
@login_required
def author_detail(slug):
    owners = Owner.query.filter(Owner.slug==slug).first()
    books = owners.subscriptions
    return render_template('author_detail.html', owner=owners, books=books)


@app.route('/library/', methods=['GET', 'POST'])
@login_required
def library():
    form = LibraryForm()
    if form.validate_on_submit():
        ownername=form.ownername.data
        bookname=form.bookname.data
        body = form.body.data
        k = Owner.query.filter(Owner.ownername == ownername).first()
        r = Book.query.filter(Book.bookname == bookname).first()

        # если автор не в базе добавим автора
        if not k:
            a = Owner(ownername=ownername, body=body)
            db.session.add(a)
            db.session.commit()
            flash('{} successfully added'.format(ownername))

        # если книга не в базе - добавим только книгу
        if not r:
            c = Book(bookname=bookname)
            db.session.add(c)
            db.session.commit()
            flash('"{}" successfully added to the base of books'.format(bookname))

        k = Owner.query.filter(Owner.ownername == ownername).first()
        r = Book.query.filter(Book.bookname == bookname).first()
        all_book = k.subscriptions
        result = 1
        for book in all_book:
            if book == r:
                flash('{} already has "{}"'.format(ownername, bookname))
                result = 2
        if result == 1:
            flash('"{}" successfully added to {}'.format(bookname, ownername))
            k.subscriptions.append(r)
        db.session.commit()
        return redirect('/library')

    # pagination page
    page = request.args.get('page')
    if page and page.isdigit():
        page = int(page)
    else:
        page = 1
    # all owner list
    ollname = Owner.query.order_by(Owner.created.desc())
    pages = ollname.paginate(page=page, per_page=10)

    return render_template('library.html', title='library', form=form, user=user, pages=pages)


# Автор хочет добавить книгу к себе
@app.route('/add_book/<ownername>')
@login_required
def madebook(ownername):
    book = Book(bookname=form.bookname.data)
    owner = Owner.query.filter_by(ownername=ownername).first()
    if book is None:
        flash('Owner {} not found.'.format(ownername))
        return redirect(url_for('library'))
    owner.madebook(book)
    db.session.commit()
    flash('You are add book to list of owner {}!'.format(ownername))
    return redirect(url_for('library2', ownername=ownername))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password')
            return redirect(url_for('login'))
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('index')
        return redirect(next_page)
    return render_template('login.html', title='Sign In', form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Congratulations, you are now a registered user!')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)


@app.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm()
    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.about_me = form.about_me.data
        db.session.commit()
        flash('Your changes have been saved.')
        return redirect(url_for('edit_profile'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.about_me.data = current_user.about_me
    return render_template('edit_profile.html', title='Edit Profile',
                           form=form)


@app.route('/lib', methods=['GET', 'POST'])
@login_required
def lib():
    form = LibraryForm()
    if form.validate_on_submit():
        a = Owner(ownername=form.ownername.data, body=form.body.data)
        c = Book(bookname=form.bookname.data)
        db.session.add(a)
        db.session.add(c)
        a.subscriptions.append(c)
        db.session.commit()
        flash('Library requested for author {}, book name={}'.format(
            form.ownername.data, form.bookname.data))
        return redirect('/index')
    return render_template('library.html', title='library', form=form)

