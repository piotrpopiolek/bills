"""Turn a storage URL the server can call into one the browser can open."""

from urllib.parse import urlsplit, urlunsplit


def browser_storage_url(signed_url: str, public_base: str | None) -> str:
    """Keep the path and token. Replace the host when the server uses an internal one."""
    if not signed_url or not public_base:
        return signed_url
    signed = urlsplit(signed_url)
    public = urlsplit(public_base)
    if not public.netloc:
        return signed_url
    scheme = public.scheme or signed.scheme
    return urlunsplit(
        (scheme, public.netloc, signed.path, signed.query, signed.fragment)
    )
