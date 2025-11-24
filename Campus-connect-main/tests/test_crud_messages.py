import os

os.environ.setdefault("MONGO_MOCK", "true")

from data import crud_messages  # noqa: E402
from data.mongo_client import drop_all  # noqa: E402


def setup_function(_function):
    drop_all()


def test_create_and_list_messages_ordered():
    m1 = crud_messages.create_message("p1", from_user=1, text="Hola")
    m2 = crud_messages.create_message("p1", from_user=2, text="Qué tal")

    # agregar timestamps para ordenar deterministamente
    crud_messages.messages_col.update_one({"_id": crud_messages._oid(m1)}, {"$set": {"ts": 1}})
    crud_messages.messages_col.update_one({"_id": crud_messages._oid(m2)}, {"$set": {"ts": 2}})

    messages = crud_messages.list_messages_by_project("p1")
    assert [m["id"] for m in messages] == [m1, m2]
    assert messages[0]["text"] == "Hola"
    assert messages[1]["from_user"] == 2


def test_delete_message():
    mid = crud_messages.create_message("p9", from_user=4, text="Ping")
    assert crud_messages.get_message_by_id(mid)["text"] == "Ping"

    deleted = crud_messages.delete_message(mid)
    assert deleted is True
    assert crud_messages.get_message_by_id(mid) is None
