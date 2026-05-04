from flask import (
    Flask,
    render_template,
    redirect,
    url_for,
    flash,
)
from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    login_required,
    logout_user,
    current_user,
)
from forms import RegistrationForm, LoginForm
from utils import load_json, save_json
import os
from werkzeug.security import generate_password_hash, check_password_hash
import datetime


app = Flask(__name__)
app.config["SECRET_KEY"] = os.urandom(256)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

class User(UserMixin):
    def __init__(self, id, username, password_hash):
        self.id = id
        self.username = username
        self.password = password_hash


@login_manager.user_loader
def load_user(user_id):
    users_dct = load_json("data", "user.json")
    user_dct = users_dct.get(str(user_id))
    if user_dct is None:
        return None
    return User(str(user_id), user_dct['username'], user_dct['password'])


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        users_dct = load_json("data", "user.json")

        for key, user in users_dct.items():
            if user['username'] == username and check_password_hash(user['password'], password):
                user["last_login"] = datetime.datetime.now().isoformat()
                save_json("data", "user.json", users_dct)
                user_obj = User(key, username, user['password'])
                login_user(user_obj)
                flash(f'Добро пожаловать, {username}!', 'success')
                return redirect(url_for("index"))

        flash('Неверное имя пользователя или пароль', 'danger')
    return render_template("login.html", form=form)


@app.route("/hidden")
@login_required
def hidden():
    return f"Если вы можете прочитать эту надпись, значит вы авторизованный пользователь. Привет, {current_user.username}!"


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash('Вы вышли из системы', 'info')
    return redirect(url_for("index"))


@app.route("/register", methods=["GET", "POST"])
#@login_required
def register():

    form = RegistrationForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        users_dct = load_json("data", "user.json")

        for user in users_dct.values():
            if user['username'] == username:
                flash('Пользователь с таким именем уже существует', 'danger')
                return render_template("register.html", form=form)

        new_id = str(len(users_dct) + 1)
        new_user = {
            "username": username,
            "password": generate_password_hash(password),
            "created_at": datetime.datetime.now().isoformat(),
            "last_login": None,
            "is_admin": False
        }
        users_dct[new_id] = new_user
        save_json("data", "user.json", users_dct)
        if current_user.is_authenticated:
            flash(f'Пользователь {username} успешно создан', 'success')
            return redirect(url_for("index"))

        else:
            user_obj = User(new_id, username, new_user['password'])
            login_user(user_obj)
            flash(f'Добро пожаловать, {username}!', 'success')
            return redirect(url_for("index"))

    return render_template("register.html", form=form)


@app.route("/")
def index():
    users_dct = load_json("data", "user.json")
    return render_template("index.html", users=users_dct, current_user=current_user)


def create_admin():
    users_dct = load_json("data", "user.json")
    if not users_dct:
        admin_hash = generate_password_hash('Admin123!')
        users_dct['1'] = {
            "username": "admin",
            "password": admin_hash,
            'created_at': datetime.datetime.now().isoformat(),
            "last_login": None,
            "is_admin": True
        }
        save_json("data", "user.json", users_dct)

if __name__ == "__main__":
    create_admin()
    app.run(debug=True)