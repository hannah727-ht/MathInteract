

import io

from PIL import Image as PILImage

from app.routers import images
from tests.conftest import sign_up


def image_bytes(fmt="PNG", size=(40, 30)) -> bytes:
    buf = io.BytesIO()
    PILImage.new("RGB", size, (249, 115, 22)).save(buf, fmt)
    return buf.getvalue()


def upload(client, data=None, name="diagram.png"):
    return client.post("/api/images", files={"file": (name, image_bytes() if data is None else data, "image/png")})


def test_upload_and_view(client):
    sign_up(client)
    res = upload(client)
    assert res.status_code == 201
    item = res.json()
    assert (item["width"], item["height"]) == (40, 30) and item["url"] == f"/api/images/{item['id']}"
    file = client.get(item["url"])
    assert file.status_code == 200 and file.headers["content-type"] == "image/png"
    assert file.headers["x-content-type-options"] == "nosniff"


def test_jpeg_and_webp(client):
    sign_up(client)
    for fmt, ctype in (("JPEG", "image/jpeg"), ("WEBP", "image/webp")):
        item = upload(client, image_bytes(fmt), name="x.bin").json()
        assert client.get(item["url"]).headers["content-type"] == ctype


def test_upload_needs_login(client):
    assert upload(client).status_code == 401


def test_rejects_non_images_and_other_formats(client):
    sign_up(client)
    assert upload(client, b"%PDF-1.4 not an image").status_code == 415
    assert upload(client, image_bytes("GIF")).status_code == 415
    assert upload(client, image_bytes()[:60]).status_code == 415
    assert upload(client, b"").status_code == 422


def test_size_limits(client, monkeypatch):
    sign_up(client)
    monkeypatch.setattr(images, "MAX_IMAGE_BYTES", 100)
    assert upload(client).status_code == 413
    monkeypatch.setattr(images, "MAX_IMAGE_BYTES", 5 * 1024 * 1024)
    monkeypatch.setattr(images, "MAX_PIXELS", 1000)
    assert upload(client).status_code == 413


def test_missing_image(client):
    assert client.get("/api/images/999").status_code == 404
