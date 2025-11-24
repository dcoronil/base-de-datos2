import os

os.environ.setdefault("MONGO_MOCK", "true")

from data import crud_users  # noqa: E402
from data.mongo_client import drop_all, users_col  # noqa: E402


def setup_function(_function):
    drop_all()


def test_create_and_get_user_roundtrip():
    user_payload = {
        "django_user_id": 1,
        "name": "Ana Ruiz",
        "degree": "ISW",
        "semester": 5,
        "skills": ["python", "django"],
        "interests": ["IA"],
        "courses": ["ABD", "IS"],
        "bio": "Busco equipo",
        "links": {"github": "ana"},
    }

    user_id = crud_users.create_user(user_payload)
    stored = crud_users.get_user_by_id(user_id)

    assert stored is not None
    assert stored["name"] == "Ana Ruiz"
    assert stored["id"] == user_id
    assert set(stored["skills"]) == {"python", "django"}


def test_get_user_by_django_id_and_update():
    user_id = crud_users.create_user({
        "django_user_id": 7,
        "name": "Luis",
        "degree": "II",
        "semester": 3,
        "skills": ["java"],
        "courses": [],
    })

    fetched = crud_users.get_user_by_django_id(7)
    assert fetched["id"] == user_id

    updated = crud_users.update_user(user_id, {"semester": 4, "skills": ["java", "spring"]})
    assert updated is True
    refreshed = crud_users.get_user_by_id(user_id)
    assert refreshed["semester"] == 4
    assert set(refreshed["skills"]) == {"java", "spring"}


def test_list_and_delete_users():
    ids = [
        crud_users.create_user({"django_user_id": i, "name": f"User{i}", "degree": "IS", "skills": ["python"]})
        for i in range(3)
    ]

    results = crud_users.list_users()
    assert len(results) == 3

    filtered = crud_users.find_users_by_skill("python")
    assert len(filtered) == 3

    # delete first user
    deleted = crud_users.delete_user(ids[0])
    assert deleted is True
    assert crud_users.get_user_by_id(ids[0]) is None

    remaining = crud_users.list_users()
    assert len(remaining) == 2
    assert {u["django_user_id"] for u in remaining} == {1, 2}
