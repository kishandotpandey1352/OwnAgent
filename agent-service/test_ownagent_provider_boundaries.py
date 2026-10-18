from pathlib import Path


AGENT_ROOT = (
    Path(__file__).parent
    / "app"
    / "agents"
)


FORBIDDEN_PROVIDER_IMPORTS = (
    "from openai ",
    "from openai import",
    "import openai",
    "from anthropic ",
    "from anthropic import",
    "import anthropic",
    "from langchain_openai ",
    "from langchain_openai import",
    "from langchain_anthropic ",
    "from langchain_anthropic import",
)


def test_agents_do_not_import_provider_sdks_directly():
    violations: list[str] = []

    for path in AGENT_ROOT.rglob("*.py"):
        source = path.read_text(
            encoding="utf-8"
        )

        for forbidden in FORBIDDEN_PROVIDER_IMPORTS:
            if forbidden in source:
                violations.append(
                    f"{path}: {forbidden}"
                )

    assert not violations, (
        "Agents must depend on the model gateway, "
        "not provider SDKs directly:\n"
        + "\n".join(violations)
    )

ANSWER_NODE = (
    Path(__file__).parent
    / "app"
    / "nodes"
    / "generate_answer.py"
)


def test_answer_node_does_not_import_provider_sdk_directly():
    source = ANSWER_NODE.read_text(
        encoding="utf-8"
    )

    violations = [
        forbidden
        for forbidden in FORBIDDEN_PROVIDER_IMPORTS
        if forbidden in source
    ]

    assert not violations, (
        "generate_answer.py must use ModelGateway "
        "instead of provider SDKs directly: "
        + ", ".join(violations)
    )