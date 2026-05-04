from flask import Flask, render_template, request, flash, redirect, url_for, send_from_directory
import os
import mimetypes
import uuid
import hashlib
import json
from datetime import datetime
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = os.urandom(67)

root = os.path.dirname(os.path.realpath(__file__))
UPLOAD_FOLDER = os.path.join(root, 'uploads')
METADATA_FILE = os.path.join(root, 'file_metadata.json')
EXTENSIONS = {'.txt', '.pdf', '.png', '.jpg', '.jpeg', '.gif'}

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def load_metadata():
    if os.path.exists(METADATA_FILE):
        with open(METADATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def save_metadata(metadata):
    with open(METADATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)


def ext_check(filename):
    ext = os.path.splitext(filename)[1].lower()
    if ext not in EXTENSIONS:
        return False, f"Неподдерживаемое расширение файла: {ext}"
    return True, "OK"

def calculate_md5_hash(file):
    md5_hash = hashlib.md5()
    file.seek(0)
    for chunk in iter(lambda: file.read(4096), b''):
        md5_hash.update(chunk)
    file.seek(0)
    return md5_hash.hexdigest()


def duplicate_check(file_md5, metadata):
    for file_info in metadata:
        if file_info.get('md5') == file_md5:
            return True, file_info
    return False, None


@app.route('/', methods=['GET', 'POST'])
def upload_file():
    metadata = load_metadata()

    if request.method == 'POST':
        if 'file' not in request.files:
            flash('Файла нет', 'error')
            return redirect(url_for('upload_file'))

        file = request.files['file']
        if file.filename == '':
            flash('Файл не выбран', 'error')
            return redirect(url_for('upload_file'))

        filename = secure_filename(file.filename)

        allowed, error_msg = ext_check(filename)
        if not allowed:
            flash(error_msg, 'error')
            return redirect(url_for('upload_file'))

        file_md5 = calculate_md5_hash(file)
        is_duplicate, duplicate_info = duplicate_check(file_md5, metadata)
        if is_duplicate:
            flash(f'Такой файл уже загружен {duplicate_info["file_path"]}', 'error')
            return redirect(url_for('upload_file'))

        file_uuid = str(uuid.uuid4()).replace('-', '')
        ext = os.path.splitext(filename)[1].lower()

        subdir1 = file_uuid[:2]
        subdir2 = file_uuid[2:4]
        save_dir = os.path.join(UPLOAD_FOLDER, subdir1, subdir2)
        os.makedirs(save_dir, exist_ok=True)

        save_path = os.path.join(save_dir, file_uuid + ext)
        file.save(save_path)

        relative_path = os.path.join('uploads', subdir1, subdir2, file_uuid + ext)

        file_metadata = {
            'id': file_uuid,
            'name': filename,
            'original_name': file.filename,
            'uuid_filename': file_uuid,
            'upload_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'extension': ext,
            'md5': file_md5,
            'file_size': os.path.getsize(save_path),
            'file_path': relative_path
        }

        metadata.append(file_metadata)
        save_metadata(metadata)

        flash(f'Файл "{filename}" успешно загружен', 'success')
        return redirect(url_for('upload_file'))

    return render_template('upload.html', files=metadata)

@app.route("/uploads/<path:filename>")
def uploads_folder(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    app.run(debug=True)