"""
Session-lifecycle API tests (remediation brief P0-4).

Against the audited HEAD there is no DELETE route, so
`test_delete_session_makes_reads_404` fails (404 route missing / data persists).
"""
import io

from api.app import app


def _upload(client, csv_bytes):
    return client.post(
        "/upload",
        data={"file": (io.BytesIO(csv_bytes), "x.csv")},
        content_type="multipart/form-data",
    )


def test_delete_session_makes_reads_404():
    client = app.test_client()
    csv = (
        b"Date,Description,Amount\n"
        b"2024-01-01,A,-100\n2024-01-02,B,-50\n2024-01-03,C,-30\n"
    )
    r = _upload(client, csv)
    assert r.status_code == 200
    sid = r.get_json()["session_id"]

    # Session exists -> a read succeeds.
    assert client.get("/subscriptions", headers={"X-Session-Id": sid}).status_code == 200
    # Delete is idempotent and returns 204.
    assert client.delete(f"/session/{sid}").status_code == 204
    # Its data is now unreachable.
    assert client.get("/subscriptions", headers={"X-Session-Id": sid}).status_code == 404


def test_delete_invalid_uuid_rejected():
    client = app.test_client()
    assert client.delete("/session/not-a-uuid").status_code == 400
