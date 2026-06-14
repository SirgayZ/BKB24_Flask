from extensions import db
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from datetime import datetime

track_tags = db.Table('track_tags',
                      db.Column('track_id', db.Integer, db.ForeignKey('tracks.id'), primary_key=True),
                      db.Column('tag_id', db.Integer, db.ForeignKey('tags.id'), primary_key=True)
                      )

favorites = db.Table('favorites',
                     db.Column('user_id', db.Integer, db.ForeignKey('users.id'), primary_key=True),
                     db.Column('track_id', db.Integer, db.ForeignKey('tracks.id'), primary_key=True),
                     db.Column('created_at', db.DateTime, default=datetime.utcnow)
                     )

playlist_tracks = db.Table('playlist_tracks',
                           db.Column('playlist_id', db.Integer, db.ForeignKey('playlists.id'), primary_key=True),
                           db.Column('track_id', db.Integer, db.ForeignKey('tracks.id'), primary_key=True),
                           db.Column('added_at', db.DateTime, default=datetime.utcnow)
                           )


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    tracks = db.relationship('Track', backref='user', lazy=True, cascade='all, delete-orphan')
    playlists = db.relationship('Playlist', backref='owner', lazy=True, cascade='all, delete-orphan')

    favorite_tracks = db.relationship('Track', secondary=favorites, lazy='subquery', backref=db.backref('favorited_by', lazy=True))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def is_favorite(self, track_id):
        return db.session.query(favorites).filter_by(
            user_id=self.id, track_id=track_id
        ).first() is not None


class Track(db.Model):
    __tablename__ = 'tracks'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    artist = db.Column(db.String(200), nullable=False)
    filename = db.Column(db.String(200), nullable=False)
    original_filename = db.Column(db.String(200), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False)
    deleted_at = db.Column(db.DateTime, nullable=True)
    plays_count = db.Column(db.Integer, default=0)
    tags = db.relationship('Tag', secondary=track_tags, lazy='subquery', backref=db.backref('tracks', lazy=True))

class Tag(db.Model):
    __tablename__ = 'tags'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Tag {self.name}>'

class Playlist(db.Model):
    __tablename__ = 'playlists'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(300))
    is_public = db.Column(db.Boolean, default=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    tracks = db.relationship('Track', secondary=playlist_tracks, lazy='subquery', backref=db.backref('playlists', lazy=True))

    def __repr__(self):
        return f'<Playlist {self.name}>'