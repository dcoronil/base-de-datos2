"""Script utilitario para ejecutar pruebas y registrar resultados en logs/execution_log.md.

Uso principal:
    python ejecutar.py              # Ejecuta pytest y deja rastro en el log
    python ejecutar.py --pytest -q  # Reenvía argumentos adicionales a pytest

El script garantiza que el archivo de log exista con su cabecera y añade
una fila por cada ejecución, indicando resultado y comando usado.
"""

from __future__ import annotations

import argparse
import datetime as _dt
from pathlib import Path
import subprocess
import sys
from typing import Iterable, List


ROOT = Path(__file__).resolve().parent
LOG_PATH = ROOT / "logs" / "execution_log.md"
LOG_HEADER = (
    "# Execution Log\n\n"
    "| Timestamp (UTC) | Actor | Area | Type | Description | Command | Files | Result | Error | Next Steps |\n"
    "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n"
)


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


def run_pytest(pytest_args: Iterable[str]) -> int:
    cmd: List[str] = [sys.executable, "-m", "pytest", *pytest_args]
    print(f"[INFO] Ejecutando pruebas: {' '.join(cmd)}")
    process = subprocess.run(cmd, cwd=ROOT)
    return process.returncode


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Ejecuta pytest y registra resultados en logs/execution_log.md")
    parser.add_argument(
        "pytest_args",
        nargs=argparse.REMAINDER,
        help="Argumentos adicionales para pytest (se usan tras --).",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    _ensure_log_header()
    exit_code = run_pytest(args.pytest_args)

    if exit_code == 0:
        print("[INFO] Pytest finalizado con éxito.")
        _append_log_row(
            area="BACKEND_API",
            type_="INFO",
            description="Ejecución de suite de pruebas automatizadas vía ejecutar.py",
            command="python ejecutar.py" + (" " + " ".join(args.pytest_args) if args.pytest_args else ""),
            files="tests/*",
            result="SUCCESS",
            error="-",
            next_steps="Revisar nuevas advertencias en el output si existen.",
        )
    else:
        print(f"[ERROR] Pytest terminó con código {exit_code}.")
        _append_log_row(
            area="BACKEND_API",
            type_="ERROR",
            description="Fallo en la ejecución de pytest vía ejecutar.py",
            command="python ejecutar.py" + (" " + " ".join(args.pytest_args) if args.pytest_args else ""),
            files="tests/*",
            result="FAIL",
            error="Revisar salida de pytest para más detalles.",
            next_steps="Corregir pruebas fallidas y re-ejecutar ejecutar.py.",
        )

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
