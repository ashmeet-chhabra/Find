import io
from PIL import Image


def get_valid_image_bytes():
    """Generate a 1x1 valid PNG for testing."""
    img = Image.new("RGB", (1, 1), color="red")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


class TestUploadSuccess:
    """Successful upload response shape."""

    def test_single_image(self, client):
        response = client.post(
            "/api/upload",
            files=[("files", ("photo.png", get_valid_image_bytes(), "image/png"))],
        )

        assert response.status_code == 200
        body = response.json()
        assert "results" in body
        assert "total" in body
        assert body["total"] == 1

        result = body["results"][0]
        assert result["filename"] == "photo.png"
        assert result["status"] == "uploaded"
        assert "media_id" in result
        assert "job_id" in result

    def test_duplicate_returns_duplicate_status(self, client):
        data = get_valid_image_bytes()
        first = client.post(
            "/api/upload",
            files=[("files", ("a.png", data, "image/png"))],
        )
        assert first.status_code == 200
        response = client.post(
            "/api/upload",
            files=[("files", ("a.png", data, "image/png"))],
        )
        assert response.status_code == 200
        assert response.json()["results"][0]["status"] == "duplicate"


class TestUploadInvalid:
    """Invalid upload behavior."""

    def test_non_image_rejected(self, client):
        response = client.post(
            "/api/upload",
            files=[("files", ("readme.txt", b"hello", "text/plain"))],
        )
        assert response.status_code == 400

    def test_corrupted_image_rejected(self, client):
        """Even if mime is image/png, invalid bytes should be rejected."""
        response = client.post(
            "/api/upload",
            files=[("files", ("corrupted.png", b"not-a-real-image", "image/png"))],
        )
        assert response.status_code == 400
        assert "corrupted" in response.json()["detail"].lower()

    def test_missing_files_returns_422(self, client):
        response = client.post("/api/upload")
        assert response.status_code == 422
