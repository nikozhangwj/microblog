from app import app, db, lm, oid
from flask import render_template, flash, redirect, session, url_for, request, g
from flask_login import login_user, logout_user, current_user, login_required
from .forms import LoginForm
from .models import User


@app.route('/')
@app.route('/index')
@login_required
def index():
    user = g.user
    posts = [  # fake array of posts
        {
            'author': {'nickname': 'John'},
            'body': 'Beautiful day in Portland!'
        },
        {
            'author': {'nickname': 'Susan'},
            'body': 'The Avengers movie was so cool!'
        }
    ]

    return render_template(
        'index.html',
        # title='Home',
        user=user,
        posts=posts
    )


@app.route('/login', methods=['GET', 'POST'])
def login():
    if g.user is not None and g.user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        print(form.nickname.data, form.password.data, str(form.remember_me.data))
        if not User.is_vaild(username=form.nickname.data):
            return redirect(url_for('login'))
        user = User.query.filter_by(nickname=form.nickname.data).one()
        if user.verify_password(form.password.data):
            login_user(user)
            session['remember_me'] = str(form.remember_me.data)
            return redirect(url_for('index'))
        else:
            return redirect(url_for('login'))

    return render_template(
        'login.html',
        title='sign in',
        form=form,
        providers=app.config['OPENID_PROVIDERS']
    )


@app.before_request
def before_request():
    g.user = current_user


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))


@lm.user_loader
def load_user(ID):
    return User.query.get(int(ID))


@app.route('/user/<nickname>')
@login_required
def user(nickname):
    user = User.query.filter_by(nickname=nickname).first()
    if user == None:
        flash('User ' + nickname + ' not found.')
        return redirect(url_for('index'))
    posts = [
        {'author': user, 'body': 'Test post #1'},
        {'author': user, 'body': 'Test post #2'}
    ]
    return render_template(
        'user.html',
        user=user,
        posts=posts
    )


@app.route('/echart')
@login_required
def show_chart():
    return render_template('render.html')