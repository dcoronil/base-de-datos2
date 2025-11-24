from typing import Dict, Any, List, Optional
from bson import ObjectId
from data.mongo_client import messages_col


Message = Dict[str, Any]


def _oid(mid: str) -> Optional[ObjectId]:
    try:
        return ObjectId(mid)
    except Exception:
        return None


def _serialize(doc: Message) -> Optional[Message]:
    if not doc:
        return None
    d = dict(doc)
    d["id"] = str(d["_id"])
    d.pop("_id", None)
    return d


# ----------- CREATE -----------

def create_message(project_id: str, from_user: int, text: str) -> str:
    """
    Crea un mensaje nuevo dentro de un proyecto.
    """
    doc = {
        "project_id": project_id,
        "from_user": from_user,
        "text": text,
        "ts": None  # se llena en el backend si queréis timestamp real
    }
    result = messages_col.insert_one(doc)
    return str(result.inserted_id)


# ----------- READ -----------

def get_message_by_id(message_id: str) -> Optional[Message]:
    oid = _oid(message_id)
    if oid is None:
        return None
    doc = messages_col.find_one({"_id": oid})
    return _serialize(doc)


def list_messages_by_project(project_id: str,
                             limit: int = 100) -> List[Message]:
    cursor = messages_col.find({"project_id": project_id}) \
                         .sort("ts", 1) \
                         .limit(limit)
    return [_serialize(d) for d in cursor]


# ----------- DELETE -----------

def delete_message(message_id: str) -> bool:
    oid = _oid(message_id)
    if oid is None:
        return False
    result = messages_col.delete_one({"_id": oid})
    return result.deleted_count > 0
