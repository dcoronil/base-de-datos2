from typing import List, Dict, Any
from data.mongo_client import users_col, projects_col, messages_col


# --------- SKILLS / TAGS ---------

def top_skills(limit: int = 10) -> List[Dict[str, Any]]:
    """
    Devuelve las skills más frecuentes entre los usuarios.
    [{ "skill": "python", "count": 15 }, ...]
    """
    pipeline = [
        {"$unwind": "$skills"},
        {"$group": {"_id": "$skills", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": limit},
        {"$project": {"_id": 0, "skill": "$_id", "count": 1}},
    ]
    return list(users_col.aggregate(pipeline))


def top_project_tags(limit: int = 10) -> List[Dict[str, Any]]:
    """
    Tags más usados en proyectos.
    [{ "tag": "IA", "count": 7 }, ...]
    """
    pipeline = [
        {"$unwind": "$tags"},
        {"$group": {"_id": "$tags", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": limit},
        {"$project": {"_id": 0, "tag": "$_id", "count": 1}},
    ]
    return list(projects_col.aggregate(pipeline))


# --------- PROYECTOS ---------

def projects_by_status() -> List[Dict[str, Any]]:
    """
    Número de proyectos por estado (open / in_progress / done).
    """
    pipeline = [
        {"$group": {"_id": "$status", "count": {"$sum": 1}}},
        {"$project": {"_id": 0, "status": "$_id", "count": 1}},
    ]
    return list(projects_col.aggregate(pipeline))


# --------- ACTIVIDAD / MENSAJES ---------

def most_active_projects(limit: int = 10) -> List[Dict[str, Any]]:
    """
    Proyectos con más mensajes de chat.
    [{ "project_id": "...", "messages": 23 }, ...]
    """
    pipeline = [
        {"$group": {"_id": "$project_id", "messages": {"$sum": 1}}},
        {"$sort": {"messages": -1}},
        {"$limit": limit},
        {"$project": {"_id": 0, "project_id": "$_id", "messages": 1}},
    ]
    return list(messages_col.aggregate(pipeline))


def most_active_users(limit: int = 10) -> List[Dict[str, Any]]:
    """
    Usuarios que más escriben (por from_user).
    [{ "from_user": 42, "messages": 30 }, ...]
    """
    pipeline = [
        {"$group": {"_id": "$from_user", "messages": {"$sum": 1}}},
        {"$sort": {"messages": -1}},
        {"$limit": limit},
        {"$project": {"_id": 0, "from_user": "$_id", "messages": 1}},
    ]
    return list(messages_col.aggregate(pipeline))
