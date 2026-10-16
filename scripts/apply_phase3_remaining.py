from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN = ROOT / "agent-service" / "app" / "main.py"
CONFIG = ROOT / "agent-service" / "app" / "core" / "config.py"


def add_main_routers() -> None:
    if not MAIN.exists():
        raise SystemExit(f"Missing {MAIN}; run this script from the repository root.")
    text = MAIN.read_text(encoding="utf-8")
    imports = [
        "from app.routers.multi_agent_runtime import router as multi_agent_runtime_router",
        "from app.routers.governance import router as governance_router",
        "from app.routers.automation import router as automation_router",
    ]
    for line in imports:
        if line not in text:
            marker = "from fastapi import FastAPI"
            pos = text.find("\n", text.find(marker)) + 1
            text = text[:pos] + line + "\n" + text[pos:]

    includes = [
        "app.include_router(multi_agent_runtime_router)",
        "app.include_router(governance_router)",
        "app.include_router(automation_router)",
    ]
    for line in includes:
        if line not in text:
            text = text.rstrip() + "\n" + line + "\n"
    MAIN.write_text(text, encoding="utf-8")


def add_feature_flags() -> None:
    if not CONFIG.exists():
        raise SystemExit(f"Missing {CONFIG}; Phase 3I-A config must exist first.")
    text = CONFIG.read_text(encoding="utf-8")
    flags = [
        ("evidence_review_enabled", "True"),
        ("compliance_blocking_enabled", "False"),
        ("automation_enabled", "False"),
    ]
    missing = [(name, value) for name, value in flags if f"{name}:" not in text]
    if not missing:
        return

    marker = "settings = Settings()"
    if marker not in text:
        raise SystemExit("Could not locate 'settings = Settings()' in app/core/config.py")
    insertion = "\n    # Phase 3I-H / 3J / 3K rollout flags\n" + "".join(
        f"    {name}: bool = {value}\n" for name, value in missing
    ) + "\n"
    text = text.replace(marker, insertion + marker, 1)
    CONFIG.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    add_main_routers()
    add_feature_flags()
    print("Applied Phase 3 remaining router wiring and rollout flags.")
    print("MULTI_AGENT_ENABLED and AUTOMATION_ENABLED remain off until you explicitly enable them.")
