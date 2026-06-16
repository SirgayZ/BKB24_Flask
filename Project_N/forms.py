from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, FileField, TextAreaField, BooleanField, SelectMultipleField
from wtforms.validators import DataRequired, Length, Email, EqualTo, Optional, Regexp

class LoginForm(FlaskForm):
    username = StringField('Имя пользователя', validators=[DataRequired()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    submit = SubmitField('Войти')

class RegistrationForm(FlaskForm):
    username = StringField('Имя пользователя', validators=[DataRequired(), Length(min=3, max=80)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Пароль', validators=[DataRequired(), Length(min=8), Regexp('^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*(),.?":{}|<>]).+$')])
    password2 = PasswordField('Повторите пароль', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Зарегистрироваться')

class TrackForm(FlaskForm):
    title = StringField('Название трека', validators=[DataRequired()])
    artist = StringField('Исполнитель', validators=[DataRequired()])
    tags = StringField('Теги (через запятую)', validators=[Optional()], description='Например: рок, веселая, грустная, электроника')
    file = FileField('Аудио файл', validators=[DataRequired()])
    submit = SubmitField('Загрузить')

class PlaylistForm(FlaskForm):
    name = StringField('Название плейлиста', validators=[DataRequired(), Length(max=100)])
    description = TextAreaField('Описание', validators=[Optional(), Length(max=300)])
    is_public = BooleanField('Публичный плейлист (видят все пользователи)')
    submit = SubmitField('Создать плейлист')

class AddToPlaylistForm(FlaskForm):
    playlist_id = SelectMultipleField('Добавить в плейлисты', coerce=int, validators=[Optional()])
    submit = SubmitField('Добавить')