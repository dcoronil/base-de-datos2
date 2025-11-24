import os

try:
    from neo4j import GraphDatabase  # type: ignore
except Exception:  # pragma: no cover - fallback para entornos sin driver
    class GraphDatabase:  # type: ignore
        @staticmethod
        def driver(*_args, **_kwargs):
            raise ImportError("El paquete neo4j no está instalado")

# Configuración basada en tu docker-compose.yml
# Usamos "neo4j" como host porque dentro de la red docker se llaman por nombre de servicio
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://neo4j:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
# OJO: En tu docker-compose la contraseña es 'neo4j_password'
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "neo4j_password")

def get_driver():
    return GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

def recommend_projects(user_id):
    """
    1. Proyectos para mí: Busca proyectos que necesiten skills que el estudiante tiene.
    Excluye proyectos en los que ya colabora.
    """
    query = """
    MATCH (s:Student {uid: $user_id})-[:HAS_SKILL]->(sk:Skill)<-[:NEEDS]-(p:Project)
    WHERE NOT (s)-[:COLLABORATES_ON]->(p)
    RETURN p.pid AS project_id, p.title AS title, count(sk) AS matching_skills
    ORDER BY matching_skills DESC
    LIMIT 5
    """
    driver = get_driver()
    with driver.session() as session:
        result = session.run(query, user_id=user_id)
        return [
            {"id": r["project_id"], "title": r["title"], "matches": r["matching_skills"]} 
            for r in result
        ]

def recommend_peers(user_id):
    """
    2. Estudiantes afines: Busca otros estudiantes que compartan Skills o Cursos (TAKES).
    """
    query = """
    MATCH (me:Student {uid: $user_id})-[:HAS_SKILL|TAKES]->(common)<-[:HAS_SKILL|TAKES]-(peer:Student)
    WHERE me <> peer
    RETURN peer.uid AS peer_id, peer.name AS name, count(common) AS similarity
    ORDER BY similarity DESC
    LIMIT 5
    """
    driver = get_driver()
    with driver.session() as session:
        result = session.run(query, user_id=user_id)
        return [
            {"id": r["peer_id"], "name": r["name"], "similarity": r["similarity"]} 
            for r in result
        ]

def recommend_skills(user_id):
    """
    3. Gap Analysis: Sugiere skills que piden muchos proyectos pero que el usuario NO tiene.
    """
    query = """
    MATCH (p:Project)-[:NEEDS]->(sk:Skill)
    WHERE NOT (:Student {uid: $user_id})-[:HAS_SKILL]->(sk)
    RETURN sk.name AS skill, count(p) AS demand
    ORDER BY demand DESC
    LIMIT 5
    """
    driver = get_driver()
    with driver.session() as session:
        result = session.run(query, user_id=user_id)
        return [
            {"skill": r["skill"], "demand": r["demand"]} 
            for r in result
        ]
