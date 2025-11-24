"""Script utilitario para ejecutar pruebas o levantar Docker Compose dejando
traza en logs/execution_log.md.

Uso principal:
    python ejecutar.py                   # Ejecuta pytest y deja rastro en el log
    python ejecutar.py --pytest -q       # Reenvia argumentos adicionales a pytest
    python ejecutar.py --compose         # Levanta docker-compose en segundo plano
    python ejecutar.py --compose --build # Igual que anterior, forzando rebuild

El script garantiza que el archivo de log exista con su cabecera y anade
una fila por cada ejecucion, indicando resultado y comando usado.
"""

from __future__ import annotations

import argparse
import datetime as _dt
from pathlib import Path
import subprocess
import sys
from typing import Iterable, List, Optional


ROOT = Path(__file__).resolve().parent
LOG_PATH = ROOT / "logs" / "execution_log.md"
LOG_HEADER = (
    "# Execution Log\n\n"
    "| Timestamp (UTC) | Actor | Area | Type | Description | Command | Files | Result | Error | Next Steps |\n"
    "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n"
)

DEFAULT_ENV_CONTENT = """# Variables por defecto para docker-compose
DJANGO_SECRET_KEY=dev-secret-key
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=*
POSTGRES_DB=campus_auth
POSTGRES_USER=campus
POSTGRES_PASSWORD=campus
NEO4J_AUTH=neo4j/neo4j_password
"""


def _ensure_log_header() -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not LOG_PATH.exists():
        LOG_PATH.write_text(LOG_HEADER, encoding="utf-8")
        return

    content = LOG_PATH.read_text(encoding="utf-8")
    if "| Timestamp (UTC) | Actor | Area | Type | Description | Command | Files | Result | Error | Next Steps |" not in content:
        LOG_PATH.write_text(LOG_HEADER + content, encoding="utf-8")


def _append_log_row(
    *,
    area: str,
    type_: str,
    description: str,
    command: str,
    files: str,
    result: str,
    error: str = "-",
    next_steps: str = "None",
) -> None:
    timestamp = _dt.datetime.now(tz=_dt.timezone.utc).isoformat(timespec="seconds")
    sanitized_description = description.replace("|", "/")
    sanitized_command = command.replace("|", "/")
    sanitized_files = files.replace("|", "/") if files else "N/A"
    sanitized_error = error.replace("|", "/") if error else "-"
    sanitized_next_steps = next_steps.replace("|", "/") if next_steps else "None"

    row = (
        f"| {timestamp} | AI-Agent | {area} | {type_} | {sanitized_description} | "
        f"`{sanitized_command}` | {sanitized_files} | {result} | {sanitized_error} | {sanitized_next_steps} |\n"
    )
    with LOG_PATH.open("a", encoding="utf-8") as fh:
        fh.write(row)


def _ensure_env_file() -> Path:
    """Crea .env con valores por defecto si no existe para docker-compose."""
    env_path = ROOT / ".env"
    if not env_path.exists():
        env_path.write_text(DEFAULT_ENV_CONTENT, encoding="utf-8")
        print(f"[INFO] Archivo .env no encontrado, se genero con valores por defecto en {env_path}.")
    return env_path


def run_pytest(pytest_args: Iterable[str]) -> int:
    cmd: List[str] = [sys.executable, "-m", "pytest", *pytest_args]
    print(f"[INFO] Ejecutando pruebas: {' '.join(cmd)}")
    process = subprocess.run(cmd, cwd=ROOT)
    return process.returncode


def run_docker_compose(*, build: bool) -> subprocess.CompletedProcess[str]:
    compose_file = ROOT / "docker" / "docker-compose.yml"
    base_cmd = ["-f", str(compose_file), "up", "-d"]
    if build:
        base_cmd.append("--build")

    # Intento 1: docker compose
    cmd_compose = ["docker", "compose", *base_cmd]
    print(f"[INFO] Levantando Docker Compose: {' '.join(cmd_compose)}")
    result = subprocess.run(
        cmd_compose,
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode == 0:
        return result

    # Intento 2: docker-compose (CLI antiguo)
    cmd_legacy = ["docker-compose", *base_cmd]
    print(f"[WARN] docker compose fallo, probando docker-compose: {' '.join(cmd_legacy)}")
    return subprocess.run(
        cmd_legacy,
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def _parse_compose_ps_json(raw: str) -> Optional[list]:
    """Intenta extraer JSON valido de la salida de docker compose ps."""
    if not raw:
        return None
    try:
        import json

        start = raw.find("[")
        end = raw.rfind("]")
        if start != -1 and end != -1 and end > start:
            snippet = raw[start : end + 1]
            return json.loads(snippet)
    except Exception:
        return None
    return None


def check_docker_compose() -> tuple[bool, str]:
    """Verifica que los servicios esten arriba usando docker compose ps."""
    compose_file = ROOT / "docker" / "docker-compose.yml"

    # Primero intentamos con salida JSON (compose v2)
    cmd_json = [
        "docker",
        "compose",
        "-f",
        str(compose_file),
        "ps",
        "--format",
        "json",
    ]
    result_json = subprocess.run(
        cmd_json,
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result_json.returncode == 0 and result_json.stdout.strip():
        services = _parse_compose_ps_json(result_json.stdout)
        if services is not None:
            not_up = [
                svc.get("Service") or svc.get("Name") or "?"
                for svc in services
                if str(svc.get("State") or "").lower() not in ("running", "up")
            ]
            if not not_up:
                return True, "Todos los servicios reportan estado running/up."
            return False, f"Servicios no arriba: {', '.join(not_up)}."
        # Si no pudimos parsear, seguimos al modo texto sin interrumpir

    # Fallback: salida de texto plano
    cmd_plain = [
        "docker",
        "compose",
        "-f",
        str(compose_file),
        "ps",
    ]
    result_plain = subprocess.run(
        cmd_plain,
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    output = (result_plain.stdout or result_plain.stderr or "").lower()
    if result_plain.returncode == 0 and "up" in output:
        return True, "Salida de docker compose ps contiene 'Up'."

    error_text = (result_plain.stderr or result_plain.stdout or "Sin salida de error").strip()
    return False, f"docker compose ps fallo o no muestra servicios 'Up': {error_text}"


def main(argv: Optional[Iterable[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Ejecuta pytest o docker-compose y registra resultados en logs/execution_log.md"
    )
    parser.add_argument(
        "--compose",
        action="store_true",
        help="Levanta docker-compose con el archivo docker/docker-compose.yml",
    )
    parser.add_argument(
        "--build",
        action="store_true",
        help="Reconstruye imagenes al levantar docker-compose (solo si se usa --compose).",
    )
    parser.add_argument(
        "pytest_args",
        nargs=argparse.REMAINDER,
        help="Argumentos adicionales para pytest (se usan tras --).",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    _ensure_log_header()

    if args.compose:
        env_path = _ensure_env_file()
        result = run_docker_compose(build=args.build)
        command_str = "docker compose -f docker/docker-compose.yml up -d"
        if args.build:
            command_str += " --build"

        if result.returncode == 0:
            print("[INFO] Docker Compose levantado con exito. Verificando estado de servicios...")
            ok, check_msg = check_docker_compose()
            if ok:
                _append_log_row(
                    area="INFRA",
                    type_="INFO",
                    description="Levantado docker-compose via ejecutar.py (verificado)",
                    command=command_str,
                    files="docker/docker-compose.yml",
                    result="SUCCESS",
                    error="-",
                    next_steps="Validar que los servicios respondan en los puertos expuestos.",
                )
                return 0

            print(f"[ERROR] Verificacion de docker-compose: {check_msg}")
            _append_log_row(
                area="INFRA",
                type_="ERROR",
                description="Docker-compose arriba pero verificacion indica fallos.",
                command=command_str + " && docker compose ps",
                files="docker/docker-compose.yml",
                result="FAIL",
                error=check_msg[:4000],
                next_steps="Revisar logs de servicios y volver a levantar docker-compose.",
            )
            return 1

        stderr_msg = (result.stderr or "").strip()
        stdout_msg = (result.stdout or "").strip()
        combined_msg = (stderr_msg + "\n" + stdout_msg).strip() or "Sin salida de error"

        print(f"[ERROR] Docker Compose fallo con codigo {result.returncode}.")
        if stderr_msg:
            print(stderr_msg)
        if stdout_msg:
            print(stdout_msg)

        _append_log_row(
            area="INFRA",
            type_="ERROR",
            description="Fallo al levantar docker-compose via ejecutar.py",
            command=command_str,
            files="docker/docker-compose.yml",
            result="FAIL",
            error=combined_msg[:4000],
            next_steps="Revisar docker compose y los logs de cada servicio.",
        )
        return result.returncode

    exit_code = run_pytest(args.pytest_args)

    command_str = "python ejecutar.py" + (" " + " ".join(args.pytest_args) if args.pytest_args else "")
    if exit_code == 0:
        print("[INFO] Pytest finalizado con exito.")
        _append_log_row(
            area="BACKEND_API",
            type_="INFO",
            description="Ejecucion de suite de pruebas automatizadas via ejecutar.py",
            command=command_str,
            files="tests/*",
            result="SUCCESS",
            error="-",
            next_steps="Revisar nuevas advertencias en el output si existen.",
        )
    else:
        print(f"[ERROR] Pytest termino con codigo {exit_code}.")
        _append_log_row(
            area="BACKEND_API",
            type_="ERROR",
            description="Fallo en la ejecucion de pytest via ejecutar.py",
            command=command_str,
            files="tests/*",
            result="FAIL",
            error="Revisar salida de pytest para mas detalles.",
            next_steps="Corregir pruebas fallidas y re-ejecutar ejecutar.py.",
        )

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
