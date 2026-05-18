import json
from flask import current_app
from models import User, News, Category, Tag
from extensions import db
from app import app
from datetime import datetime


def serialize_user(user: User):
    return {
        "id": user.id,
        "username": user.username,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "email": user.email,
        "password_hash": user.password_hash,
        "created": user.created.isoformat() if user.created else None,
        "last_access": user.last_access.isoformat() if user.last_access else None,
    }

def serialize_category(cat: Category):
    return {
        "id": cat.id,
        "name": cat.name,
    }

def serialize_tag(tag: Tag):
    return {
        "id": tag.id,
        "name": tag.name,
    }

def serialize_news(news: News):
    return {
        "id": news.id,
        "title": news.title,
        "content": news.content,
        "created": news.created.isoformat() if news.created else None,
        "deleted": news.deleted.isoformat() if news.deleted else None,
        "user_id": news.user_id,
        "category_id": news.category_id,
        "tags": [tag.id for tag in news.tags]
    }

def save_all_to_json(filename="db_backup.json"):
    with app.app_context():
        data = {
            "users": [serialize_user(u) for u in User.query.all()],
            "categories": [serialize_category(c) for c in Category.query.all()],
            "tags": [serialize_tag(t) for t in Tag.query.all()],
            "news": [serialize_news(n) for n in News.query.all()],
        }
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    print(f"Данные сохранены в {filename}")

def load_all_from_json(filename="db_backup.json"):
    with app.app_context():
        with open(filename, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Очистить таблицы (опционально)
        db.session.query(News).delete()
        db.session.query(Tag).delete()
        db.session.query(Category).delete()
        db.session.query(User).delete()
        db.session.commit()

        # Восстановить пользователей
        for udata in data.get("users", []):
            created = udata.get("created")
            if created:
                created = datetime.fromisoformat(created)

            last_access = udata.get("last_access")
            if last_access:
                last_access = datetime.fromisoformat(last_access)

            user = User(
                id=udata["id"],
                username=udata["username"],
                first_name=udata.get("first_name"),
                last_name=udata.get("last_name"),
                email=udata["email"],
                password_hash=udata["password_hash"],
                created=created,
                last_access=last_access
            )
            db.session.add(user)
        db.session.commit()


        # Восстановить категории
        for cdata in data.get("categories", []):
            cat = Category(id=cdata["id"], name=cdata["name"])
            db.session.add(cat)
        db.session.commit()

        # Восстановить теги
        tags_map = {}
        for tdata in data.get("tags", []):
            tag = Tag(id=tdata["id"], name=tdata["name"])
            db.session.add(tag)
            tags_map[tag.id] = tag
        db.session.commit()

        # Восстановить новости (без тегов)
        news_map = {}
        for ndata in data.get("news", []):
            created = ndata.get("created")
            if created:
                created = datetime.fromisoformat(created)

            deleted = ndata.get("deleted")
            if deleted:
                deleted = datetime.fromisoformat(deleted)

            news = News(
                id=ndata["id"],
                title=ndata["title"],
                content=ndata["content"],
                created=created,
                deleted=deleted,
                user_id=ndata["user_id"],
                category_id=ndata["category_id"]
            )
            db.session.add(news)
            news_map[news.id] = (news, ndata.get("tags", []))
        db.session.commit()

        # Восстановить связи many-to-many (теги новостей)
        for news, tag_ids in news_map.values():
            for tag_id in tag_ids:
                tag = tags_map.get(tag_id)
                if tag:
                    news.tags.append(tag)
        db.session.commit()

    print(f"Данные загружены из {filename}")

# Пример использования:
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    # Сохранить все данные в json
    # save_all_to_json()

    # Или загрузить данные из json
    load_all_from_json()
