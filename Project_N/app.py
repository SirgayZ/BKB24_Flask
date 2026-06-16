from flask import Flask, render_template, make_response, request, flash, redirect, url_for, send_from_directory, abort
from flask_login import login_user, logout_user, current_user, login_required, LoginManager, UserMixin
from extensions import db, login_manager
from datetime import datetime
from models import User, Track, Tag, Playlist, favorites, playlist_tracks
import os
from forms import LoginForm, RegistrationForm, TrackForm, PlaylistForm, AddToPlaylistForm
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import func, desc

app = Flask(__name__)
app.config["SECRET_KEY"] = os.urandom(67)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///music.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'uploads')
ALLOWED_EXTENSIONS = {'.mp3', '.wav', '.ogg', '.m4a'}

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

db.init_app(app)
login_manager.init_app(app)
login_manager.login_view = "login_page"

@app.route('/toggle-theme')
def toggle_theme():
    current_theme = request.cookies.get('theme', 'light')
    new_theme = 'dark' if current_theme == 'light' else 'light'
    response = make_response(redirect(request.referrer or '/'))
    response.set_cookie('theme', new_theme, max_age = 365*24*60*60)
    return response


@app.context_processor
def inject_theme():
    return {'theme': request.cookies.get('theme', 'light')}


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def allowed_file(filename):
    ext = os.path.splitext(filename)[1].lower()
    return ext in ALLOWED_EXTENSIONS


def process_tags(tag_string):
    if not tag_string:
        return []

    tag_names = [t.strip().lower() for t in tag_string.split(',') if t.strip()]
    tags = []

    for tag_name in tag_names:
        tag = Tag.query.filter_by(name=tag_name).first()
        if not tag:
            tag = Tag(name=tag_name)
            db.session.add(tag)
        tags.append(tag)

    return tags


@app.route('/login', methods=['GET'])
def login_page():
    form = LoginForm()
    theme = request.cookies.get('theme', 'light')
    return render_template('login.html',theme =theme, form=form)


@app.route('/login', methods=['POST'])
def login():
    theme = request.cookies.get('theme', 'light')
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            flash('Вы вошли в систему', 'success')
            return redirect(request.args.get('next') or url_for('index'))
        else:
            flash('Неверный логин или пароль', 'danger')
    return redirect(url_for('login_page'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    theme = request.cookies.get('theme', 'light')
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    form = RegistrationForm()
    if form.validate_on_submit():
        existing_user = User.query.filter_by(username=form.username.data).first()
        if existing_user:
            flash('Имя пользователя уже занято', 'danger')
            return render_template('register.html', theme=theme, form=form)

        existing_email = User.query.filter_by(email=form.email.data).first()
        if existing_email:
            flash('Email уже зарегистрирован', 'danger')
            return render_template('register.html', theme=theme, form=form)

        user = User(
            username=form.username.data,
            email=form.email.data
        )
        user.set_password(form.password.data)

        db.session.add(user)
        db.session.commit()

        login_user(user)
        flash(f'Добро пожаловать, {form.username.data}!', 'success')
        return redirect(url_for("index"))

    return render_template('register.html', theme=theme, form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы вышли из системы', 'info')
    return redirect(url_for('index'))


@app.route("/")
def index():
    theme = request.cookies.get('theme', 'light')
    tag_name = request.args.get('tag')

    query = Track.query.filter(Track.deleted_at.is_(None))

    if tag_name:
        tag = Tag.query.filter_by(name=tag_name.lower()).first()
        if tag:
            query = query.filter(Track.tags.contains(tag))

    tracks = query.order_by(Track.created_at.desc()).all()
    all_tags = Tag.query.all()
    popular_tags = Tag.query.join(Track.tags).group_by(Tag.id).order_by(func.count(Track.id).desc()).limit(10).all()

    return render_template("index.html", theme=theme, tracks=tracks, tags=all_tags, popular_tags=popular_tags, selected_tag=tag_name)


@app.route("/my-music")
@login_required
def my_music():
    theme = request.cookies.get('theme', 'light')
    tracks = Track.query.filter_by(user_id=current_user.id, deleted_at=None).order_by(Track.created_at.desc()).all()
    return render_template("my_music.html", tracks=tracks, theme=theme)


@app.route("/favorites")
@login_required
def favorites_page():
    theme = request.cookies.get('theme', 'light')
    tracks = current_user.favorite_tracks
    return render_template("favorites.html", theme=theme, tracks=tracks)


@app.route("/favorite/<int:track_id>/toggle")
@login_required
def toggle_favorite(track_id):
    track = Track.query.get_or_404(track_id)

    if current_user.is_favorite(track_id):
        current_user.favorite_tracks.remove(track)
        flash(f'Трек "{track.title}" удален из избранного', 'info')
    else:
        current_user.favorite_tracks.append(track)
        flash(f'Трек "{track.title}" добавлен в избранное', 'success')

    db.session.commit()
    return redirect(request.referrer or url_for('index'))


@app.route("/track/upload", methods=["GET", "POST"])
@login_required
def upload_track():

    form = TrackForm()
    theme = request.cookies.get('theme', 'light')
    if form.validate_on_submit():
        if 'file' not in request.files:
            flash('Файл не выбран', 'danger')
            return redirect(request.url)

        file = request.files['file']
        if file.filename == '':
            flash('Файл не выбран', 'danger')
            return redirect(request.url)

        if not allowed_file(file.filename):
            flash('Неподдерживаемый формат. Разрешены: mp3, wav, ogg, m4a', 'danger')
            return redirect(request.url)

        filename = secure_filename(file.filename)
        name_parts = os.path.splitext(filename)
        unique_filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{name_parts[0]}{name_parts[1]}"

        file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(file_path)

        track = Track(
            title=form.title.data,
            artist=form.artist.data,
            filename=unique_filename,
            original_filename=filename,
            user_id=current_user.id,
            created_at=datetime.utcnow()
        )

        tags = process_tags(form.tags.data)
        track.tags = tags

        db.session.add(track)
        db.session.commit()

        flash(f'Трек "{form.title.data}" успешно загружен', 'success')
        return redirect(url_for('index'))

    return render_template("upload.html", form=form, theme=theme)


@app.route("/track/delete/<int:track_id>")
@login_required
def delete_track(track_id):
    track = Track.query.get_or_404(track_id)

    if not current_user.is_admin and track.user_id != current_user.id:
        flash('У вас нет прав на удаление этого трека', 'danger')
        return redirect(url_for('index'))

    track.deleted_at = datetime.utcnow()
    db.session.commit()

    flash(f'Трек "{track.title}" удален', 'success')
    return redirect(request.referrer or url_for('index'))


@app.route("/track/<int:track_id>/increment-play")
def increment_play(track_id):
    track = Track.query.get_or_404(track_id)
    track.plays_count += 1
    db.session.commit()
    return '', 204


@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
@app.route("/playlists")
def playlists_page():
    public_playlists = Playlist.query.filter_by(is_public=True).order_by(Playlist.created_at.desc()).all()
    theme = request.cookies.get('theme', 'light')
    my_playlists = []
    if current_user.is_authenticated:
        my_playlists = Playlist.query.filter_by(user_id=current_user.id, is_public=False).order_by(
            Playlist.created_at.desc()).all()

    return render_template("playlists.html", theme=theme, public_playlists=public_playlists, my_playlists=my_playlists)


@app.route("/playlist/create", methods=["GET", "POST"])
@login_required
def create_playlist():
    theme = request.cookies.get('theme', 'light')
    form = PlaylistForm()
    if form.validate_on_submit():
        playlist = Playlist(
            name=form.name.data,
            description=form.description.data,
            is_public=form.is_public.data,
            user_id=current_user.id
        )
        db.session.add(playlist)
        db.session.commit()
        flash(f'Плейлист "{playlist.name}" создан!', 'success')
        return redirect(url_for('playlists_page'))

    return render_template("playlist_form.html", theme=theme, form=form, title="Создать плейлист")


@app.route("/playlist/<int:playlist_id>")
def view_playlist(playlist_id):
    playlist = Playlist.query.get_or_404(playlist_id)
    theme = request.cookies.get('theme', 'light')

    if not playlist.is_public and (not current_user.is_authenticated or current_user.id != playlist.user_id):
        abort(403)

    return render_template("playlist_detail.html", theme=theme, playlist=playlist)


@app.route("/playlist/<int:playlist_id>/add-track/<int:track_id>")
@login_required
def add_to_playlist(playlist_id, track_id):
    playlist = Playlist.query.get_or_404(playlist_id)
    track = Track.query.get_or_404(track_id)

    if playlist.user_id != current_user.id:
        flash('У вас нет прав для изменения этого плейлиста', 'danger')
        return redirect(url_for('index'))

    if track in playlist.tracks:
        flash(f'Трек "{track.title}" уже в плейлисте "{playlist.name}"', 'warning')
    else:
        playlist.tracks.append(track)
        db.session.commit()
        flash(f'Трек "{track.title}" добавлен в плейлист "{playlist.name}"', 'success')

    return redirect(request.referrer or url_for('view_playlist', playlist_id=playlist_id))


@app.route("/playlist/<int:playlist_id>/remove-track/<int:track_id>")
@login_required
def remove_from_playlist(playlist_id, track_id):
    playlist = Playlist.query.get_or_404(playlist_id)
    track = Track.query.get_or_404(track_id)

    if playlist.user_id != current_user.id:
        flash('У вас нет прав для изменения этого плейлиста', 'danger')
        return redirect(url_for('index'))

    if track in playlist.tracks:
        playlist.tracks.remove(track)
        db.session.commit()
        flash(f'Трек "{track.title}" удален из плейлиста "{playlist.name}"', 'success')

    return redirect(url_for('view_playlist', playlist_id=playlist_id))


@app.route("/playlist/<int:playlist_id>/delete")
@login_required
def delete_playlist(playlist_id):
    playlist = Playlist.query.get_or_404(playlist_id)

    if playlist.user_id != current_user.id and not current_user.is_admin:
        flash('У вас нет прав для удаления этого плейлиста', 'danger')
        return redirect(url_for('playlists_page'))

    db.session.delete(playlist)
    db.session.commit()
    flash(f'Плейлист "{playlist.name}" удален', 'success')
    return redirect(url_for('playlists_page'))


@app.route("/tags")
def tags_page():
    tags = Tag.query.all()
    return render_template("tags.html", tags=tags)


def create_admin():
    admin = User.query.filter_by(username='admin').first()
    if not admin:
        admin = User(
            username='admin',
            email='admin@example.com',
            is_admin=True,
            created_at=datetime.utcnow()
        )
        admin.set_password('Admin123!')
        db.session.add(admin)
        db.session.commit()
        print('Администратор создан (логин: admin, пароль: Admin123!)')


with app.app_context():
    db.create_all()
    create_admin()

if __name__ == "__main__":
    app.run(debug=True)