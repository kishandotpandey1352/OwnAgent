import json
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from app.core.config import settings


payload = json.dumps(
    {
        "q": "Ambac commission income 2025",
        "num": 5,
    }
).encode("utf-8")


request = Request(
    settings.serper_search_url,
    data=payload,
    method="POST",
    headers={
        "X-API-KEY": settings.serper_api_key or "",
        "Content-Type": "application/json",
        "Accept": "application/json",
    },
)


try:
    with urlopen(
        request,
        timeout=15,
    ) as response:
        print(
            response.status
        )

        print(
            response
            .read()
            .decode("utf-8")
        )

except HTTPError as error:
    print(
        "STATUS:",
        error.code,
    )

    print(
        "BODY:",
        error
        .read()
        .decode(
            "utf-8",
            errors="replace",
        ),
    )