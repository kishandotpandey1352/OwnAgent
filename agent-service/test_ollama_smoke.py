from app.models.contracts import (
    ModelMessage,
    ModelMessageRole,
    ModelRequest,
)
from app.models.runtime import get_model_gateway


gateway = get_model_gateway()

request = ModelRequest(
    messages=[
        ModelMessage(
            role=ModelMessageRole.user,
            content=(
                "Explain what a local AI model is "
                "in two short sentences."
            ),
        )
    ]
)

for chunk in gateway.stream(
    provider_id="ollama-local",
    request=request,
):
    print(
        chunk.delta,
        end="",
        flush=True,
    )

print()