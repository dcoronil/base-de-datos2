import os

import os

os.environ.setdefault("MONGO_MOCK", "true")

from data import crud_projects  # noqa: E402
from data.mongo_client import drop_all  # noqa: E402


def setup_function(_function):
    drop_all()


def test_create_and_search_projects():
    project_id = crud_projects.create_project({
        "title": "Finder IA",
        "owner_django_user_id": 9,
        "tags": ["IA", "NLP"],
        "needed_skills": ["python", "nlp"],
        "description": "Motor de búsqueda",
        "status": "open",
    })

    stored = crud_projects.get_project_by_id(project_id)
    assert stored["title"] == "Finder IA"
    assert stored["id"] == project_id

    results = crud_projects.list_projects()
    assert len(results) == 1

    by_skill = crud_projects.find_projects_by_skill("python")
    assert len(by_skill) == 1
    assert by_skill[0]["id"] == project_id

    text_matches = crud_projects.search_projects_by_text("búsqueda")
    assert len(text_matches) == 1


def test_update_and_delete_project():
    project_id = crud_projects.create_project({
        "title": "App móvil",
        "owner_django_user_id": 3,
        "needed_skills": ["kotlin"],
        "description": "MVP inicial",
        "status": "open",
    })

    updated = crud_projects.update_project(project_id, {"status": "in_progress"})
    assert updated is True
    assert crud_projects.get_project_by_id(project_id)["status"] == "in_progress"

    deleted = crud_projects.delete_project(project_id)
    assert deleted is True
    assert crud_projects.get_project_by_id(project_id) is None
