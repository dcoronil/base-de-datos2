from typing import Dict, Any, List, Optional
from bson import ObjectId
from data.mongo_client import projects_col


Project = Dict[str, Any]


def _oid(project_id: str) -> Optional[ObjectId]:
    try:
        return ObjectId(project_id)
    except Exception:
        return None


def _serialize(doc: Project) -> Optional[Project]:
    if not doc:
        return None
    d = dict(doc)
    d["id"] = str(d["_id"])
    d.pop("_id", None)
    return d


# ----------- CREATE -----------

def create_project(data: Project) -> str:
    """
    Inserta un proyecto en la colección `projects`.

    Ejemplo:
    {
        "title": "Finder IA para apuntes",
        "owner_django_user_id": 7,
        "tags": ["IA","NLP"],
        "needed_skills": ["python","nlp"],
        "description": "...",
        "status": "open"
    }
    """
    result = projects_col.insert_one(data)
    return str(result.inserted_id)


# ----------- READ -----------

def get_project_by_id(project_id: str) -> Optional[Project]:
    oid = _oid(project_id)
    if oid is None:
        return None
    doc = projects_col.find_one({"_id": oid})
    return _serialize(doc)


def list_projects(filter_query: Optional[Dict[str, Any]] = None,
                  limit: int = 50) -> List[Project]:
    if filter_query is None:
        filter_query = {}

    cursor = projects_col.find(filter_query).limit(limit)
    return [_serialize(d) for d in cursor]


def find_projects_by_skill(skill: str, limit: int = 50) -> List[Project]:
    cursor = projects_col.find({"needed_skills": skill}).limit(limit)
    return [_serialize(d) for d in cursor]


def search_projects_by_text(keyword: str, limit: int = 50) -> List[Project]:
    """
    Búsqueda sencilla por título o descripción.
    """
    cursor = projects_col.find({
        "$or": [
            {"title": {"$regex": keyword, "$options": "i"}},
            {"description": {"$regex": keyword, "$options": "i"}}
        ]
    }).limit(limit)
    return [_serialize(d) for d in cursor]


# ----------- UPDATE -----------

def update_project(project_id: str, updates: Dict[str, Any]) -> bool:
    oid = _oid(project_id)
    if oid is None:
        return False
    result = projects_col.update_one({"_id": oid}, {"$set": updates})
    return result.modified_count > 0


# ----------- DELETE -----------

def delete_project(project_id: str) -> bool:
    oid = _oid(project_id)
    if oid is None:
        return False
    result = projects_col.delete_one({"_id": oid})
    return result.deleted_count > 0
