from app import db
from passlib.hash import sha256_crypt


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nickname = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    post = db.relationship('Post', backref='user', lazy='dynamic')
    password = db.Column(db.String(128))

    def hash_password(self, password):
        self.password = sha256_crypt.encrypt(password)

    def verify_password(self, password):
        return sha256_crypt.verify(password, self.password)

    @classmethod
    def is_vaild(cls, username):
        user = User.query.filter_by(nickname=username).one()
        return user if user else False

    @property
    def is_authenticated(self):
        return True

    @property
    def is_active(self):
        return True

    @property
    def is_anonymous(self):
        return False

    def get_id(self):
        return str(self.id)

    def __repr__(self):
        return '<User {}>'.format(self.nickname)


class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.String(140))
    timestamp = db.Column(db.DateTime)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    def __repr__(self):
        return '<Post {}>'.format(self.body)