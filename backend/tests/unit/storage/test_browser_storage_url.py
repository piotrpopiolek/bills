from src.storage.urls import browser_storage_url


def test_signed_url_uses_the_browser_host() -> None:
    signed = (
        "http://host.docker.internal:54321/storage/v1/object/sign/bills/a.jpg?token=abc"
    )
    public = browser_storage_url(signed, "http://127.0.0.1:54321")
    assert public.startswith("http://127.0.0.1:54321/storage/v1/object/sign/bills/a.jpg")
    assert "token=abc" in public


def test_missing_public_host_leaves_the_signed_url() -> None:
    signed = "http://127.0.0.1:54321/storage/v1/object/sign/bills/a.jpg?token=abc"
    assert browser_storage_url(signed, None) == signed
