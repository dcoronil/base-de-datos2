"""
Cliente MongoDB configurable con soporte para modo "mock" en tests.

- Utiliza variables de entorno estándar para host/puerto/bd.
- Permite activar un cliente en memoria usando ``MONGO_MOCK=true`` para pruebas
  sin depender de un servicio externo.
"""

import copy
import os
import re
from typing import Any, Dict, Iterable, List, Optional

from bson import ObjectId

MONGO_HOST = os.getenv("MONGO_HOST", "mongo")
MONGO_PORT = int(os.getenv("MONGO_PORT", 27017))
MONGO_DB = os.getenv("MONGO_DB", "campus_connect")
USE_MOCK = os.getenv("MONGO_MOCK", "false").lower() == "true"

if USE_MOCK:

    class _InsertResult:
        def __init__(self, inserted_id: ObjectId):
            self.inserted_id = inserted_id

    class _UpdateResult:
        def __init__(self, modified_count: int):
            self.modified_count = modified_count

    class _DeleteResult:
        def __init__(self, deleted_count: int):
            self.deleted_count = deleted_count

    class _MockCursor:
        def __init__(self, docs: List[Dict[str, Any]]):
            self._docs = docs

        def limit(self, limit: int):
            self._docs = self._docs[:limit]
            return self

        def sort(self, field: str, direction: int):
            reverse = direction < 0
            self._docs = sorted(self._docs, key=lambda d: d.get(field), reverse=reverse)
            return self

        def __iter__(self):
            return iter(self._docs)

    class _MockCollection:
        def __init__(self):
            self._docs: List[Dict[str, Any]] = []

        def _match(self, doc: Dict[str, Any], query: Dict[str, Any]) -> bool:
            if not query:
                return True

            for key, value in query.items():
                if key == "$or":
                    if any(self._match(doc, clause) for clause in value):
                        return True
                    return False

                if isinstance(value, dict) and "$regex" in value:
                    pattern = value["$regex"]
                    flags = re.IGNORECASE if value.get("$options") == "i" else 0
                    if not re.search(pattern, str(doc.get(key, "")), flags):
                        return False
                    continue

                doc_value = doc.get(key)
                if isinstance(doc_value, list):
                    if value not in doc_value:
                        return False
                else:
                    if doc_value != value:
                        return False
            return True

        def find_one(self, query: Optional[Dict[str, Any]] = None):
            query = query or {}
            for doc in self._docs:
                if self._match(doc, query):
                    return copy.deepcopy(doc)
            return None

        def find(self, query: Optional[Dict[str, Any]] = None):
            query = query or {}
            filtered = [copy.deepcopy(doc) for doc in self._docs if self._match(doc, query)]
            return _MockCursor(filtered)

        def insert_one(self, doc: Dict[str, Any]):
            new_doc = copy.deepcopy(doc)
            new_doc.setdefault("_id", ObjectId())
            self._docs.append(new_doc)
            return _InsertResult(new_doc["_id"])

        def update_one(self, query: Dict[str, Any], update: Dict[str, Any]):
            modified = 0
            for doc in self._docs:
                if self._match(doc, query):
                    if "$set" in update:
                        doc.update(update["$set"])
                    modified += 1
                    break
            return _UpdateResult(modified)

        def delete_one(self, query: Dict[str, Any]):
            for idx, doc in enumerate(self._docs):
                if self._match(doc, query):
                    del self._docs[idx]
                    return _DeleteResult(1)
            return _DeleteResult(0)

        def create_index(self, *_args, **_kwargs):  # pragma: no cover - noop en mock
            return None

        def drop(self):
            self._docs.clear()

        def aggregate(self, pipeline: Iterable[Dict[str, Any]]):
            docs: List[Dict[str, Any]] = [copy.deepcopy(d) for d in self._docs]
            for stage in pipeline:
                if "$unwind" in stage:
                    field = stage["$unwind"].lstrip("$")
                    unwound: List[Dict[str, Any]] = []
                    for doc in docs:
                        values = doc.get(field, [])
                        if not isinstance(values, list):
                            values = [values]
                        for val in values:
                            new_doc = copy.deepcopy(doc)
                            new_doc[field] = val
                            unwound.append(new_doc)
                    docs = unwound
                elif "$group" in stage:
                    group = stage["$group"]
                    key_field = str(group.get("_id", "")).lstrip("$")
                    accumulators = {k: v for k, v in group.items() if k != "_id"}
                    grouped: Dict[Any, Dict[str, Any]] = {}
                    for doc in docs:
                        key = doc.get(key_field)
                        bucket = grouped.setdefault(key, {k: 0 for k in accumulators})
                        for acc_key, acc_val in accumulators.items():
                            if "$sum" in acc_val:
                                bucket[acc_key] += acc_val.get("$sum", 0)
                    docs = [
                        {"_id": key, **values}
                        for key, values in grouped.items()
                    ]
                elif "$sort" in stage:
                    sort_spec = stage["$sort"]
                    field = next(iter(sort_spec.keys()))
                    reverse = sort_spec[field] < 0
                    docs = sorted(docs, key=lambda d: d.get(field, 0), reverse=reverse)
                elif "$limit" in stage:
                    docs = docs[: stage["$limit"]]
                elif "$project" in stage:
                    projection = stage["$project"]
                    projected: List[Dict[str, Any]] = []
                    for doc in docs:
                        new_doc: Dict[str, Any] = {}
                        for out_field, expr in projection.items():
                            if out_field == "_id":
                                continue
                            if isinstance(expr, str) and expr.startswith("$"):
                                new_doc[out_field] = doc.get(expr[1:])
                            elif expr == 1:
                                new_doc[out_field] = doc.get(out_field)
                            else:
                                new_doc[out_field] = expr if not isinstance(expr, dict) else doc.get(out_field)
                        projected.append(new_doc)
                    docs = projected
            return docs

    class _MockDatabase:
        def __init__(self):
            self._collections: Dict[str, _MockCollection] = {}

        def __getitem__(self, name: str) -> _MockCollection:
            return self._collections.setdefault(name, _MockCollection())

    class MongoClient:  # type: ignore[misc]
        def __init__(self, *_args, **_kwargs):
            self._dbs: Dict[str, _MockDatabase] = {}

        def __getitem__(self, name: str) -> _MockDatabase:
            return self._dbs.setdefault(name, _MockDatabase())

        @property
        def admin(self):
            return self

        def command(self, *_args, **_kwargs):
            return {"ok": 1}

else:  # pragma: no cover - path usado en runtime real
    from pymongo import MongoClient


def _build_client() -> "MongoClient":
    """Crea la instancia de cliente (real o simulada)."""

    uri = os.getenv("MONGO_URI")
    if uri:
        return MongoClient(uri)
    return MongoClient(f"mongodb://{MONGO_HOST}:{MONGO_PORT}/")


# Cliente global
client = _build_client()

# Selección de base de datos
db = client[MONGO_DB]

# Colecciones principales
users_col = db["users"]
projects_col = db["projects"]
messages_col = db["messages"]


def test_connection():
    try:
        client.admin.command("ping")
        return True
    except Exception as e:  # pragma: no cover - logging auxiliar
        print("Error connecting to MongoDB:", e)
        return False


def drop_all():
    """Elimina todas las colecciones (útil en tests con mock)."""

    users_col.drop()
    projects_col.drop()
    messages_col.drop()
