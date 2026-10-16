from __future__ import annotations

import ipaddress
import socket

from dataclasses import dataclass

from urllib.parse import (
    urljoin,
    urlparse,
)

import httpx

from app.core.config import settings


class WebFetchError(
    RuntimeError
):
    pass


REDIRECT_STATUS_CODES = {
    301,
    302,
    303,
    307,
    308,
}


@dataclass
class RawFetchedResource:
    requested_url: str

    final_url: str

    status_code: int

    content_kind: str

    media_type: str

    content: bytes


# ---------------------------------------------------------
# URL / SSRF protection
# ---------------------------------------------------------


def _validate_public_url(
    url: str,
) -> None:
    parsed = urlparse(
        url
    )

    if parsed.scheme not in {
        "http",
        "https",
    }:
        raise WebFetchError(
            "Only http and https URLs "
            "may be fetched."
        )

    if (
        parsed.username
        or parsed.password
    ):
        raise WebFetchError(
            "URLs containing credentials "
            "are not allowed."
        )

    hostname = (
        parsed.hostname
        or ""
    ).strip().lower().rstrip(".")

    if not hostname:
        raise WebFetchError(
            "URL does not contain a "
            "valid hostname."
        )

    if (
        hostname == "localhost"
        or hostname.endswith(
            ".localhost"
        )
        or hostname.endswith(
            ".local"
        )
    ):
        raise WebFetchError(
            "Local hostnames are not "
            "allowed."
        )

    try:
        port = parsed.port

    except ValueError as error:
        raise WebFetchError(
            "URL contains an invalid port."
        ) from error

    if parsed.scheme == "http":
        allowed_ports = {
            None,
            80,
        }

    else:
        allowed_ports = {
            None,
            443,
        }

    if port not in allowed_ports:
        raise WebFetchError(
            "Non-standard network ports "
            "are not allowed."
        )

    effective_port = (
        port
        or (
            443
            if parsed.scheme == "https"
            else 80
        )
    )

    # -----------------------------------------------------
    # Literal IP
    # -----------------------------------------------------

    try:
        direct_ip = (
            ipaddress.ip_address(
                hostname
            )
        )

    except ValueError:
        direct_ip = None

    if direct_ip is not None:
        if not direct_ip.is_global:
            raise WebFetchError(
                "Private, local, reserved, "
                "or non-global IP addresses "
                "are not allowed."
            )

        return

    # -----------------------------------------------------
    # DNS hostname
    # -----------------------------------------------------

    try:
        results = (
            socket.getaddrinfo(
                hostname,
                effective_port,
                type=socket.SOCK_STREAM,
            )
        )

    except socket.gaierror as error:
        raise WebFetchError(
            (
                "Unable to resolve "
                f"hostname: {hostname}"
            )
        ) from error

    if not results:
        raise WebFetchError(
            "Hostname did not resolve."
        )

    resolved_addresses: set[str] = set()

    for result in results:
        sockaddr = result[4]

        if not sockaddr:
            continue

        resolved_addresses.add(
            str(
                sockaddr[0]
            )
        )

    if not resolved_addresses:
        raise WebFetchError(
            "Hostname produced no usable "
            "IP addresses."
        )

    for address in (
        resolved_addresses
    ):
        try:
            resolved_ip = (
                ipaddress.ip_address(
                    address
                )
            )

        except ValueError:
            raise WebFetchError(
                (
                    "Hostname resolved to "
                    "an invalid IP address."
                )
            )

        if not resolved_ip.is_global:
            raise WebFetchError(
                (
                    "Hostname resolved to a "
                    "private, local, reserved, "
                    "or non-global address."
                )
            )


# ---------------------------------------------------------
# Response classification
# ---------------------------------------------------------


def _classify_content(
    *,
    content_type: str,
    url: str,
) -> tuple[
    str,
    int,
]:
    media_type = (
        content_type
        .split(
            ";",
            1,
        )[0]
        .strip()
        .lower()
    )

    if media_type in {
        "text/html",
        "application/xhtml+xml",
    }:
        return (
            "html",
            settings
            .web_fetch_max_html_bytes,
        )

    if media_type in {
        "text/plain",
    }:
        return (
            "text",
            settings
            .web_fetch_max_html_bytes,
        )

    if media_type == "application/pdf":
        return (
            "pdf",
            settings
            .web_fetch_max_pdf_bytes,
        )

    # Some document CDNs return PDFs as generic binary
    # content even when the URL clearly ends in .pdf.
    if (
        media_type
        in {
            "application/octet-stream",
            "binary/octet-stream",
        }
        and urlparse(
            url
        ).path.lower().endswith(
            ".pdf"
        )
    ):
        return (
            "pdf",
            settings
            .web_fetch_max_pdf_bytes,
        )

    raise WebFetchError(
        (
            "Unsupported response "
            f"content type: "
            f"{media_type or 'unknown'}"
        )
    )


# ---------------------------------------------------------
# Safe network fetch
# ---------------------------------------------------------


def fetch_public_resource(
    url: str,
) -> RawFetchedResource:
    if not (
        settings.web_fetch_enabled
    ):
        raise WebFetchError(
            "Web source fetching is "
            "disabled."
        )

    requested_url = url
    current_url = url

    seen_urls: set[str] = set()

    timeout = httpx.Timeout(
        settings
        .web_fetch_timeout_seconds
    )

    headers = {
        "User-Agent":
            settings
            .web_fetch_user_agent,

        "Accept":
            (
                "text/html,"
                "application/xhtml+xml,"
                "text/plain,"
                "application/pdf;"
                "q=0.9,*/*;q=0.1"
            ),
    }

    # trust_env=False prevents environment proxy settings
    # from silently changing the outbound route.
    with httpx.Client(
        timeout=timeout,
        follow_redirects=False,
        trust_env=False,
        headers=headers,
    ) as client:

        for redirect_index in range(
            settings
            .web_fetch_max_redirects
            + 1
        ):
            _validate_public_url(
                current_url
            )

            if current_url in seen_urls:
                raise WebFetchError(
                    "Redirect loop detected."
                )

            seen_urls.add(
                current_url
            )

            try:
                with client.stream(
                    "GET",
                    current_url,
                ) as response:

                    # -------------------------------------
                    # Redirect
                    # -------------------------------------

                    if (
                        response.status_code
                        in REDIRECT_STATUS_CODES
                    ):
                        if (
                            redirect_index
                            >= settings
                            .web_fetch_max_redirects
                        ):
                            raise WebFetchError(
                                (
                                    "Maximum redirect "
                                    "count exceeded."
                                )
                            )

                        location = (
                            response.headers.get(
                                "location"
                            )
                        )

                        if not location:
                            raise WebFetchError(
                                (
                                    "Redirect response "
                                    "did not provide a "
                                    "Location header."
                                )
                            )

                        next_url = urljoin(
                            current_url,
                            location,
                        )

                        # The next target will be
                        # independently SSRF checked.
                        _validate_public_url(
                            next_url
                        )

                        current_url = (
                            next_url
                        )

                        continue

                    # -------------------------------------
                    # HTTP status
                    # -------------------------------------

                    if not (
                        200
                        <= response.status_code
                        < 300
                    ):
                        raise WebFetchError(
                            (
                                "Remote source returned "
                                f"HTTP "
                                f"{response.status_code}."
                            )
                        )

                    content_type = (
                        response.headers.get(
                            "content-type",
                            "",
                        )
                    )

                    (
                        content_kind,
                        max_bytes,
                    ) = _classify_content(
                        content_type=(
                            content_type
                        ),
                        url=current_url,
                    )

                    # -------------------------------------
                    # Content-Length pre-check
                    # -------------------------------------

                    content_length_value = (
                        response.headers.get(
                            "content-length"
                        )
                    )

                    if content_length_value:
                        try:
                            declared_length = int(
                                content_length_value
                            )

                        except ValueError:
                            declared_length = None

                        if (
                            declared_length
                            is not None
                            and declared_length
                            > max_bytes
                        ):
                            raise WebFetchError(
                                (
                                    "Remote source "
                                    "exceeds configured "
                                    "size limit."
                                )
                            )

                    # -------------------------------------
                    # Stream with actual byte cap
                    # -------------------------------------

                    chunks: list[bytes] = []

                    total_bytes = 0

                    for chunk in (
                        response.iter_bytes()
                    ):
                        total_bytes += len(
                            chunk
                        )

                        if total_bytes > max_bytes:
                            raise WebFetchError(
                                (
                                    "Downloaded source "
                                    "exceeded configured "
                                    "size limit."
                                )
                            )

                        chunks.append(
                            chunk
                        )

                    content = b"".join(
                        chunks
                    )

                    if not content:
                        raise WebFetchError(
                            "Remote source was empty."
                        )

                    media_type = (
                        content_type
                        .split(
                            ";",
                            1,
                        )[0]
                        .strip()
                        .lower()
                    )

                    return RawFetchedResource(
                        requested_url=(
                            requested_url
                        ),
                        final_url=(
                            current_url
                        ),
                        status_code=(
                            response.status_code
                        ),
                        content_kind=(
                            content_kind
                        ),
                        media_type=(
                            media_type
                        ),
                        content=content,
                    )

            except httpx.TimeoutException as error:
                raise WebFetchError(
                    (
                        "Timed out while "
                        "fetching web source."
                    )
                ) from error

            except httpx.RequestError as error:
                raise WebFetchError(
                    (
                        "Network error while "
                        "fetching web source: "
                        f"{error}"
                    )
                ) from error

    raise WebFetchError(
        "Unable to fetch web source."
    )