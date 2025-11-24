from typing import Dict, Any, List
import os

from neo4j import GraphDatabase  # Rodrigo debe tener esto en requirements.txt


NEO4J_URI = os.getenv("NEO4J_URI", "bolt://neo4j:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")


def get_driver():
    return GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))


# ---------- HELPERS GENÉRICOS ----------

def _run_write(query: str, params: Dict[str, Any] | None = None):
    if params is None:
        params = {}
    driver = get_driver()
    with driver.session() as session:
        session.run(query, **params)


# ---------- USERS ----------

def sync_user_to_neo4j(user: Dict[str, Any]):
    """
    Crea/actualiza un nodo (:Student) con sus relaciones básicas:
    - (:Student)-[:HAS_SKILL]->(:Skill)
    - (:Student)-[:TAKES]->(:Course)
    """
    query = """
    MERGE (s:Student {uid: $django_user_id})
    SET  s.name     = $name,
         s.degree   = $degree,
         s.semester = $semester,
         s.bio      = $bio

    WITH s
    UNWIND $skills AS sk
      MERGE (skill:Skill {name: sk})
      MERGE (s)-[:HAS_SKILL]->(skill)

    WITH s
    UNWIND $courses AS co
      MERGE (c:Course {code: co})
      MERGE (s)-[:TAKES]->(c)
    """

    params = {
        "django_user_id": user.get("django_user_id"),
        "name": user.get("name"),
        "degree": user.get("degree"),
        "semester": user.get("semester"),
        "bio": user.get("bio", ""),
        "skills": user.get("skills", []),
        "courses": user.get("courses", []),
    }
    _run_write(query, params)


# ---------- PROJECTS ----------

def sync_project_to_neo4j(project: Dict[str, Any]):
    """
    Crea/actualiza nodo (:Project) y relaciones con skills necesarias:
    - (:Project)-[:NEEDS]->(:Skill)
    """
    query = """
    MERGE (p:Project {pid: $pid})
    SET  p.title       = $title,
         p.status      = $status,
         p.description = $description

    WITH p
    UNWIND $needed_skills AS sk
      MERGE (skill:Skill {name: sk})
      MERGE (p)-[:NEEDS]->(skill)
    """

    params = {
        "pid": project.get("id") or str(project.get("_id", "")),
        "title": project.get("title"),
        "status": project.get("status", "open"),
        "description": project.get("description", ""),
        "needed_skills": project.get("needed_skills", []),
    }
    _run_write(query, params)


def link_owner_to_project(django_user_id: int, project_pid: str, role: str = "owner"):
    """
    Crea relación (:Student)-[:COLLABORATES_ON {role}]->(:Project)
    """
    query = """
    MATCH (s:Student {uid: $uid})
    MATCH (p:Project {pid: $pid})
    MERGE (s)-[r:COLLABORATES_ON]->(p)
    SET   r.role = $role
    """
    params = {
        "uid": django_user_id,
        "pid": project_pid,
        "role": role,
    }
    _run_write(query, params)
