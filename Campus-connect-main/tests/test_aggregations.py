import os

os.environ.setdefault("MONGO_MOCK", "true")

from data import aggregations, crud_users, crud_projects, crud_messages  # noqa: E402
from data.mongo_client import drop_all  # noqa: E402


def setup_function(_function):
    drop_all()


def test_top_skills_and_project_tags():
    crud_users.create_user({"django_user_id": 1, "skills": ["python", "docker"]})
    crud_users.create_user({"django_user_id": 2, "skills": ["python"]})

    crud_projects.create_project({"title": "P1", "owner_django_user_id": 1, "tags": ["AI", "ML"], "needed_skills": []})
    crud_projects.create_project({"title": "P2", "owner_django_user_id": 1, "tags": ["AI"], "needed_skills": []})

    top_skills = aggregations.top_skills(limit=2)
    assert top_skills[0]["skill"] == "python"
    assert top_skills[0]["count"] == 2

    top_tags = aggregations.top_project_tags(limit=1)
    assert top_tags[0]["tag"] == "AI"
    assert top_tags[0]["count"] == 2


def test_projects_by_status_and_activity():
    p1 = crud_projects.create_project({"title": "P1", "owner_django_user_id": 1, "status": "open", "needed_skills": []})
    p2 = crud_projects.create_project({"title": "P2", "owner_django_user_id": 1, "status": "done", "needed_skills": []})

    crud_messages.create_message(p1, from_user=1, text="Hola")
    crud_messages.create_message(p1, from_user=1, text="Hola2")
    crud_messages.create_message(p2, from_user=2, text="Adios")

    status_counts = aggregations.projects_by_status()
    status_by_code = {row["status"]: row["count"] for row in status_counts}
    assert status_by_code == {"open": 1, "done": 1}

    active_projects = aggregations.most_active_projects(limit=1)
    assert active_projects[0]["project_id"] == p1
    assert active_projects[0]["messages"] == 2

    active_users = aggregations.most_active_users(limit=1)
    assert active_users[0]["from_user"] == 1
    assert active_users[0]["messages"] == 2
