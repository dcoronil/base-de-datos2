from django.shortcuts import render
from django.utils import timezone
from pathlib import Path
import json
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from accounts.models import UserProfile

# Motor de recomendaciones existente
from .recommendations import recommend_projects, recommend_peers, recommend_skills

# Chat persistente sencillo por proyecto (archivos JSON)
CHAT_MESSAGES: dict[str, list[dict]] = {}
CHAT_LIMIT = 500
CHAT_DIR = Path(__file__).resolve().parent.parent / "data" / "chat_logs"
CHAT_DIR.mkdir(parents=True, exist_ok=True)


def _chat_path(project_id: str) -> Path:
    return CHAT_DIR / f"chat_{project_id}.json"


def _load_chat(project_id: str) -> list[dict]:
    path = _chat_path(project_id)
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []


def _save_chat(project_id: str, messages: list[dict]) -> None:
    path = _chat_path(project_id)
    try:
        path.write_text(json.dumps(messages[-CHAT_LIMIT:], ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


@api_view(["GET"])
@permission_classes([AllowAny])
def frontend_index(request):
    """Entrega la pagina principal del dashboard para el frontend sencillo."""
    return render(request, "index.html")


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
    Devuelve datos del dashboard en una sola llamada:
    - Proyectos sugeridos
    - Companeros sugeridos
    - Skills a aprender
    """
    user_id = request.user.id
    try:
        data = {
            "projects": recommend_projects(user_id),
            "peers": recommend_peers(user_id),
            "learning_path": recommend_skills(user_id),
        }
        return Response(data)
    except Exception as exc:  # noqa: BLE001
        print(f"Error en Neo4j: {exc}")
        return Response(
            {
                "projects": [],
                "peers": [],
                "learning_path": [],
                "error": str(exc),
            },
            status=500,
        )


def _get_profile(user):
    profile, _ = UserProfile.objects.get_or_create(user=user)
    return profile


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def skills(request):
    """
    GET: devuelve skills del usuario autenticado.
    POST: body {"skill": "..."} agrega skill si no existe.
    También devuelve/usa lista de proyectos del perfil.
    """
    profile = _get_profile(request.user)
    if request.method == "POST":
        payload = request.data or {}
        skill = (payload.get("skill") or "").strip()
        if not skill:
            return Response({"error": "skill requerida"}, status=400)
        skills = profile.skills or []
        if skill not in skills:
            skills.append(skill)
            profile.skills = skills
            profile.save()
        return Response({"skills": profile.skills, "projects": profile.projects})
    return Response({"skills": profile.skills, "projects": profile.projects})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def join_project(request):
    """
    Agrega al usuario autenticado a un proyecto (lista en UserProfile.projects).
    body: {project: "id"}
    """
    profile = _get_profile(request.user)
    payload = request.data or {}
    project_id = (payload.get("project") or "").strip()
    if not project_id:
        return Response({"error": "project requerido"}, status=400)
    projects = profile.projects or []
    if project_id not in projects:
        projects.append(project_id)
        profile.projects = projects
        profile.save()
    return Response({"projects": profile.projects})


@api_view(["GET", "POST"])
@permission_classes([AllowAny])
def chat_messages(request):
    """
    Chat minimo en memoria por proyecto (project param). GET devuelve los ultimos; POST agrega uno.
    """
    global CHAT_MESSAGES  # noqa: PLW0603

    project_id = request.query_params.get("project") or (request.data or {}).get("project") or "default"
    if project_id not in CHAT_MESSAGES:
        CHAT_MESSAGES[project_id] = _load_chat(project_id)

    if request.method == "POST":
        if not request.user or not request.user.is_authenticated:
            return Response({"error": "auth requerida para enviar"}, status=401)
        # verificar membresia
        profile = _get_profile(request.user)
        if project_id not in (profile.projects or []):
            return Response({"error": "No eres miembro de este proyecto"}, status=403)
        payload = request.data or {}
        sender = (payload.get("sender") or "anon")[:50]
        message = (payload.get("message") or "").strip()
        if not message:
            return Response({"error": "message requerido"}, status=400)

        entry = {
            "sender": sender,
            "message": message,
            "ts": timezone.now().isoformat(),
            "project": project_id,
        }
        CHAT_MESSAGES[project_id].append(entry)
        if len(CHAT_MESSAGES[project_id]) > CHAT_LIMIT:
            CHAT_MESSAGES[project_id] = CHAT_MESSAGES[project_id][-CHAT_LIMIT:]
        _save_chat(project_id, CHAT_MESSAGES[project_id])
        return Response(entry, status=201)

    return Response(list(CHAT_MESSAGES.get(project_id, [])))
