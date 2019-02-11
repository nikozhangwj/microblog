from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import os
from flask_login import LoginManager
from flask_openid import OpenID
from config import basedir, LOG_DIR
import logging
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config.from_object('config')
db = SQLAlchemy(app)

lm = LoginManager()
lm.init_app(app)
lm.login_view = 'login'
oid = OpenID(app, os.path.join(basedir, 'tmp'))

socketio = SocketIO(app)
socketio.init_app(app)

logging.basicConfig(filename=LOG_DIR, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

from app import views, models
