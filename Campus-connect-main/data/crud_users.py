from typing import Dict, Any, List, Optional

from bson import ObjectId
from data.mongo_client import users_col


UserDict = Dict[str, Any]


def _to_object_id(user_id: str) -> Optional[ObjectId]:
    """
    Convierte un string a ObjectId de forma segura.
    Devuelve None si el id no es válido.
    """
    try:
        return ObjectId(user_id)
    except Exception:
        return None


def _serialize_user(doc: UserDict) -> Optional[UserDict]:
    """
    Pasa de documento MongoDB a dict listo para API/plantillas.
    Cambia _id -> id (string).
    """
    if not doc:
        return None
    doc = dict(doc)  # copia
    doc["id"] = str(doc["_id"])
    doc.pop("_id", None)
    return doc


# ---------- CREATE ----------

def create_user(data: UserDict) -> str:
    """
    Inserta un nuevo usuario en la colección `users`.

    Ejemplo de data:
    {
        "django_user_id": 42,
        "name": "Ana Ruiz",
        "degree": "ISW",
        "semester": 5,
        "skills": ["python", "django", "docker"],
        "interests": ["IA", "backend"],
        "courses": ["ABD", "IS", "DS"],
        "bio": "Busco equipo para hackathon",
        "links": {"github": "...", "linkedin": "..."},
    }
    """
    result = users_col.insert_one(data)
    return str(result.inserted_id)


# ---------- READ ----------

def get_user_by_id(user_id: str) -> Optional[UserDict]:
    """
    Devuelve un usuario por su _id (string) o None si no existe.
    """
    oid = _to_object_id(user_id)
    if oid is None:
        return None
    doc = users_col.find_one({"_id": oid})
    return _serialize_user(doc)


def get_user_by_django_id(django_user_id: int) -> Optional[UserDict]:
    """
    Devuelve un usuario por su django_user_id.
    """
    doc = users_col.find_one({"django_user_id": django_user_id})
    return _serialize_user(doc)


def list_users(filter_query: Optional[Dict[str, Any]] = None,
               limit: int = 50) -> List[UserDict]:
    """
    Lista usuarios con un filtro opcional.

    Ejemplos:
      list_users()  -> todos (hasta `limit`)
      list_users({"degree": "ISW"})
      list_users({"skills": "python"})
    """
    if filter_query is None:
        filter_query = {}

    cursor = users_col.find(filter_query).limit(limit)
    return [_serialize_user(doc) for doc in cursor]


def find_users_by_skill(skill: str, limit: int = 50) -> List[UserDict]:
    """
    Devuelve usuarios que tengan una skill concreta.
    """
    cursor = users_col.find({"skills": skill}).limit(limit)
    return [_serialize_user(doc) for doc in cursor]


# ---------- UPDATE ----------

def update_user(user_id: str, updates: Dict[str, Any]) -> bool:
    """
    Actualiza un usuario por _id. Devuelve True si ha modificado algo.
    """
    oid = _to_object_id(user_id)
    if oid is None:
        return False

    result = users_col.update_one({"_id": oid}, {"$set": updates})
    return result.modified_count > 0


# ---------- DELETE ----------

def delete_user(user_id: str) -> bool:
    """
    Elimina físicamente un usuario por _id.
    (Si preferís borrado lógico, aquí se haría un $set {"active": False})
    """
    oid = _to_object_id(user_id)
    if oid is None:
        return False

    result = users_col.delete_one({"_id": oid})
    return result.deleted_count > 0
