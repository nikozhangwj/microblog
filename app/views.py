from app import app, db, lm, oid, socketio, emit
from flask import render_template, flash, redirect, session, url_for, request, g, jsonify, abort, make_response
from flask_login import login_user, logout_user, current_user, login_required
from flask_httpauth import HTTPBasicAuth
from flask_restful import Api, Resource, reqparse
from .forms import LoginForm
from .models import User, Post
import random

auth = HTTPBasicAuth()
api = Api(app)


@auth.error_handler
def unauthorized():
    return make_response(jsonify({'error': 'Unauthorized access'}), 403)


@auth.error_handler
def page_not_found():
    return make_response(jsonify({'error': 'Resource not found'}), 404)


tasks = [
    {
        'id': 1,
        'title': u'Buy groceries',
        'description': u'Milk, Cheese, Pizza, Fruit, Tylenol',
        'done': False
    },
    {
        'id': 2,
        'title': u'Learn Python',
        'description': u'Need to find a good Python tutorial on the web',
        'done': False
    }
]


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


@app.route('/xterm')
def show_terminal():
    return render_template('xt.html')


def make_public_task(task):
    new_task = {}
    for field in task:
        if field == 'id':
            # new_task['uri'] = url_for('TaskListAPI', task_id=task['id'], _external=True)
            new_task['uri'] = api.url_for(TaskListAPI, task_id=task['id'], _external=True)
        else:
            new_task[field] = task[field]
    return new_task


# TaskAPI
class TaskListAPI(Resource):

    def __init__(self):
        self.reqparse = reqparse.RequestParser()
        self.reqparse.add_argument('title', type=str, required=True,
                                   help='No task title provided', location='json')
        self.reqparse.add_argument('description', type=str, default="", location='json')
        super(TaskListAPI, self).__init__()

    def get(self):
        return {'tasks': [task for task in map(make_public_task, tasks)]}
        # return {'tasks': tasks}

    def post(self):
        if not request.json or 'title' not in request.json:
            abort(400)
        print(request)
        task = {
            'id': tasks[-1]['id'] + 1,
            'title': request.json['title'],
            'description': request.json.get('description', ""),
            'done': False
        }
        tasks.append(task)
        return {'task': task}, 201


class TaskAPI(Resource):

    def __init__(self):
        self.reqparse = reqparse.RequestParser()
        self.reqparse.add_argument('title', type=str, location='json')
        self.reqparse.add_argument('description', type=str, location='json')
        self.reqparse.add_argument('done', type=bool, location='json')
        super(TaskAPI, self).__init__()

    def get(self, id):
        task = [task for task in tasks if task['id'] == id]
        if not task:
            abort(404)
        return {'tasks': [task for task in map(make_public_task, task)]}

    def put(self, id):
        task = [task for task in tasks if task['id'] == id]
        if not task:
            abort(404)
        task[0]['title'] = request.json.get('title', task[0]['title'])
        task[0]['description'] = request.json.get('description', task[0]['description'])
        task[0]['done'] = request.json.get('done', task[0]['done'])
        task = [raw_task for raw_task in map(make_public_task, task)]
        return {'task': task}

    def delete(self, id):
        task = [task for task in tasks if task['id'] == id]
        if not task:
            abort(404)
        tasks.remove(task[0])
        return {'result': True}, 201


api.add_resource(TaskListAPI, '/todo/api/v1.0/tasks', endpoint='tasks')
api.add_resource(TaskAPI, '/todo/api/v1.0/tasks/<int:id>', endpoint='task')


# User API
class UserListAPI(Resource):

    decorators = [auth.login_required]

    def __init__(self):
        self.reqparse = reqparse.RequestParser()
        super(UserListAPI, self).__init__()

    def get(self):
        users = [
            {
                'username': users.nickname,
                'id': users.id,
                'post': [post.id for post in users.post.all()]
            }
            for users in User.query.all()
        ]
        app.logger.info("Get users from UserListAPI.")
        if not users:
            app.logger.error("Users does not exist.")
            abort(404)
        return {'users': users}

    def post(self):
        username = request.json.get('username')
        password = request.json.get('password')
        if username is None or password is None:
            abort(404)  # missing arguments
        if User.query.filter_by(nickname=username).first() is not None:
            abort(404)  # existing user
        user = User(nickname=username)
        user.hash_password(password)
        db.session.add(user)
        db.session.commit()
        return {'username': user.nickname}, 201, {'Location': api.url_for(UserAPI, id=user.id, _external=True)}


class UserAPI(Resource):

    decorators = [auth.login_required]

    def __init__(self):
        self.reqparse = reqparse.RequestParser()
        super(UserAPI, self).__init__()

    def get(self, id):
        user = User.query.get(id)
        if not user:
            abort(404)
        return {'username': user.nickname}

    def delete(self, id):
        user = User.query.get(id)
        if not user:
            abort(404)
        username = user.nickname
        db.session.delete(user)
        db.session.commit()
        return {'result': 'delete {} success.'.format(username)}


api.add_resource(UserListAPI, '/todo/api/v1.0/users', endpoint='users')
api.add_resource(UserAPI, '/todo/api/v1.0/users/<int:id>')


# PostAPI
class PostAPI(Resource):

    def __init__(self):
        self.reqparse = reqparse.RequestParser()
        super(PostAPI, self).__init__()

    def get(self, id):
        user = User.query.get(id)
        if not user:
            app.logger.error("User does not exist.")
            abort(404)
        post = [{'body': post.body, 'create_time': str(post.timestamp)} for post in user.post.all()]
        if not post:
            app.logger.error("Post does not exist.")
            return {'user': user.nickname, 'posts': 'user {} has no post yet.'.format(user.nickname)}
        return {'user': user.nickname, 'post': post}

    def post(self, id):
        user = User.query.get(id)
        if not user:
            abort(404)
        body = request.json.get('body')
        if Post.add_post(body=body, userid=user.id):
            return {'result': 'post success'}, 201, {'Location': api.url_for(PostAPI, id=user.id, _external=True)}
        else:
            abort(500)


api.add_resource(PostAPI, '/todo/api/v1.0/post/<int:id>', endpoint='post')


@app.route('/api/resource')
@auth.login_required
def get_resource():
    return jsonify({'data': 'Hello, {}!'.format(g.user.nickname)})


@auth.verify_password
def verify_password(username_or_token, password):
    user = User.verify_auth_token(username_or_token)
    if not user:
        user = User.query.filter_by(nickname=username_or_token).first()
        if not user or not user.verify_password(password):
            return False
    g.user = user
    return True


@app.route('/api/token')
@auth.login_required
def get_auth_token():
    expiration = app.config['TOKEN_EXPIRATION']
    token = g.user.generate_auth_token(expiration=expiration)
    app.logger.info("User {} get token from server, expiration {}.".format(g.user.nickname, expiration))
    return jsonify({'token': token.decode('ascii'), 'duration': expiration})


@socketio.on('connect', namespace='/test_conn')
def test_connect():
    while True:
        socketio.sleep(5)
        t = random_int_list(1, 100, 10)
        socketio.emit('server_response', {'data': t}, namespace='/test_conn')


def random_int_list(start, stop, length):
    start, stop = (int(start), int(stop)) if start <= stop else (int(stop), int(start))
    length = int(abs(length)) if length else 0
    random_list = []
    for i in range(length):
        random_list.append(random.randint(start, stop))
    return random_list


@app.route('/ws')
def blog_socket_route():
    return render_template('/ws.html')