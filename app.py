# Этот код уже есть в шаблоне. Используйте его в своей работе, для отладки. В ответ добавлять этот код не нужно

import sys
import io
import contextlib
from itertools import cycle
import datetime
from flask import Flask, jsonify, request

status_lst = ["cancelled", "completed", "in_progress", "pending"]
priority_lst = ["high", "low", "medium"]


def get_task_list():
    f = io.StringIO()
    with contextlib.redirect_stdout(f):
        import this
    text = f.getvalue()
    status_cycle = cycle(status_lst)
    priority_cycle = cycle(priority_lst)
    tasks_lst = []
    num = 0
    for line in text.splitlines():
        if not line:
            continue
        num += 1
        tasks_lst.append({
            "id": num,
            "title": "Zen of Python",
            "description": line,
            "status": next(status_cycle),
            "priority": next(priority_cycle),
            "created_at": datetime.datetime.now().isoformat(),
            "updated_at": datetime.datetime.now().isoformat(),
            "deleted_at": None,
        })
    return tasks_lst


tasks_lst = get_task_list()

app = Flask(__name__)
def find_task(task_id):
    task_id = int(task_id)
    for task in tasks_lst:
        if task["id"] == task_id and task["deleted_at"] is None:
            return task
    return None

def normalize(d):
    if isinstance(d, dict):
        return {
            k: normalize(v)
            for k, v in d.items()
            if k not in ("created_at", "updated_at", "deleted_at")
        }
    if isinstance(d, list):
        return [normalize(i) for i in d]
    return d


def filter_tasks(tasks, query):
    if not query:
        return tasks
    query_lower = query.lower()
    return [task for task in tasks if query_lower in task["description"].lower()]


def sort_tasks(tasks, order):
    if order:
        if order[0] != "-":
            return sorted(tasks, key=lambda x: x[order])
        elif order[0] == "-":
            return sorted(tasks, key=lambda x: x[order[1:]], reverse = True)
        else:
            return tasks
    else:
        return tasks


@app.route("/api/v1/tasks", methods=["GET"])
def get_tasks_lst():
    query = request.args.get('query', '')
    order = request.args.get('order', '')
    offset = request.args.get('offset', 0, type=int)
    active_tasks = [task for task in tasks_lst if task["deleted_at"] is None]
    filtered_tasks = filter_tasks(active_tasks, query)
    sorted_tasks = sort_tasks(filtered_tasks, order)
    return jsonify({"tasks": sorted_tasks[offset:offset+10]}), 200


@app.route("/api/v1/tasks/<task_id>", methods=["GET"])
def get_tasks(task_id):
    task = find_task(task_id)
    if task is None:
        return jsonify({"error": "Задача не найдена"}), 404
    return jsonify(task), 200


@app.route("/api/v1/tasks", methods=["POST"])
def post_tasks():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Отсутствуют данные JSON"}), 400
    if "title" not in data:
        return jsonify({"error": "Пропущен обязательный параметр `title`"}), 400
    if "description" not in data:
        return jsonify({"error": "Пропущен обязательный параметр `description`"}), 400
    if tasks_lst:
        new_id = len(tasks_lst) + 1
    else:
        new_id = 1
    status = data.get("status", "pending")
    if status not in status_lst:
        return jsonify({"error": "Поле `status` невалидно"}), 400

    priority = data.get("priority", "medium")
    if priority not in priority_lst:
        return jsonify({"error": "Поле `priority` невалидно"}), 400

    new_task = {
        "id": new_id,
        "title": data["title"],
        "description": data["description"],
        "status": status,
        "priority": priority,
        "created_at": datetime.datetime.now().isoformat(),
        "updated_at": datetime.datetime.now().isoformat(),
        "deleted_at": None
    }

    tasks_lst.append(new_task)
    return jsonify(new_task), 201

@app.route("/api/v1/tasks/<task_id>", methods=["DELETE"])
def delete_tasks(task_id):
    task = find_task(task_id)
    if task is None:
        return jsonify({"error": "Задача не найдена"}), 404

    task["deleted_at"] = datetime.datetime.now().isoformat()
    task["status"] = "cancelled"
    return jsonify(task), 200


@app.route("/api/v1/tasks/<task_id>", methods=["PATCH"])
def patch_tasks(task_id):
    task = find_task(task_id)
    if task is None:
        return jsonify({"error": "Задача не найдена"}), 404

    data = request.get_json()
    if not data:
        return jsonify({"error": "Отсутствуют данные JSON"}), 400

    if "title" in data:
        task["title"] = data["title"]

    if "description" in data:
        task["description"] = data["description"]

    if "status" in data:
        if data["status"] not in status_lst:
            return jsonify({"error": "Поле `status` невалидно"}), 400
        task["status"] = data["status"]

    if "priority" in data:
        if data["priority"] not in priority_lst:
            return jsonify({"error": "Поле `priority` невалидно"}), 400
        task["priority"] = data["priority"]

    task["updated_at"] = datetime.datetime.now().isoformat()

    return jsonify(task), 200
