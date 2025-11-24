from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

# Importamos tu nuevo motor de recomendaciones
from .recommendations import recommend_projects, recommend_peers, recommend_skills

@api_view(["GET"])
@permission_classes([AllowAny])
def health(request):
    return Response({"status": "ok"})

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me(request):
    user = request.user
    return Response({"id": user.id, "username": user.username})

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def dashboard_recommendations(request):
    """
    Devuelve todo lo necesario para el Dashboard en una sola llamada:
    - Proyectos sugeridos
    - Compañeros sugeridos
    - Skills a aprender
    """
    # Obtenemos el ID numérico de Django (que es el uid en Neo4j)
    user_id = request.user.id
    
    try:
        data = {
            "projects": recommend_projects(user_id),
            "peers": recommend_peers(user_id),
            "learning_path": recommend_skills(user_id)
        }
        return Response(data)
    except Exception as e:
        # En caso de error (ej. Neo4j apagado), devolvemos listas vacías para no romper el front
        print(f"Error en Neo4j: {e}") 
        return Response({
            "projects": [], 
            "peers": [], 
            "learning_path": [], 
            "error": str(e)
        }, status=500)
