

from app.config import settings
from app.db import SessionLocal
from app.models import Resource
from tests.conftest import sign_up, sign_up_admin

PDF = b"%PDF-1.4\n% a tiny test file\n%%EOF\n"


def upload(client, content=PDF, filename="2024 AMC 10A.pdf", **fields):
    data = {"section": "us", "contest": "amc10", "kind": "problems", "year": "2024", "title": "", **fields}
    return client.post("/api/resources", data=data, files={"file": (filename, content, "application/pdf")})


def stored_files():
    folder = settings.upload_dir / "resources"
    return list(folder.iterdir()) if folder.exists() else []




def test_catalog(client):
    data = client.get("/api/catalog").json()
    assert list(data["sections"]) == ["us", "canada", "ib", "ossd"]
    canada = [c["key"] for c in data["sections"]["canada"]["contests"]]
    assert "comc" in canada and "ctmc" not in canada
    assert data["kinds"][0] == {"key": "problems", "name": "Problems"}


def test_list_empty_and_unknown(client):
    assert client.get("/api/resources?section=ib").json() == []
    assert client.get("/api/resources?section=mars").status_code == 404
    assert client.get("/api/resources?section=us&contest=euclid").status_code == 404
    assert client.get("/api/resources").status_code == 422




def test_admin_upload_then_list_and_open(client):
    sign_up_admin(client)
    res = upload(client)
    assert res.status_code == 201, res.text
    item = res.json()
    assert item["title"] == "2024 AMC 10A"
    assert item["contest_name"] == "AMC 10" and item["file_type"] == "PDF" and item["size"] == len(PDF)

    listed = client.get("/api/resources?section=us&contest=amc10").json()
    assert [r["id"] for r in listed] == [item["id"]]

    file = client.get(item["href"])
    assert file.status_code == 200 and file.content == PDF
    assert file.headers["content-type"] == "application/pdf"
    assert file.headers["content-disposition"].startswith("inline")
    assert file.headers["x-content-type-options"] == "nosniff"


    assert [f.suffix for f in stored_files()] == [".pdf"] and "AMC" not in stored_files()[0].name


def test_word_files_download_instead_of_opening(client):
    sign_up_admin(client)
    item = upload(client, content=b"PK\x03\x04rest-of-docx", filename="notes.docx", section="ossd", contest="mhf4u", kind="notes", year="").json()
    assert item["year"] is None
    file = client.get(item["href"])
    assert file.headers["content-disposition"].startswith("attachment")


def test_list_order_year_then_type(client):
    sign_up_admin(client)
    upload(client, title="B 2023 solutions", year="2023", kind="solutions")
    upload(client, title="C undated", year="")
    upload(client, title="A 2023 problems", year="2023", kind="problems")
    upload(client, title="D 2024", year="2024", kind="solutions")
    titles = [r["title"] for r in client.get("/api/resources?section=us").json()]
    assert titles == ["D 2024", "A 2023 problems", "B 2023 solutions", "C undated"]


def test_upload_needs_admin(client):
    assert upload(client).status_code == 401
    sign_up(client, username="student")
    assert upload(client).status_code == 403
    assert stored_files() == []


def test_upload_rejects_bad_input(client):
    sign_up_admin(client)
    assert upload(client, contest="euclid").status_code == 422
    assert upload(client, kind="homework").status_code == 422
    assert upload(client, year="24").status_code == 422
    assert upload(client, year="2999").status_code == 422
    assert upload(client, filename="virus.exe").status_code == 415
    assert upload(client, content=b"MZ not really a pdf").status_code == 415
    assert upload(client, content=b"").status_code == 422
    assert upload(client, content=b"%PDF-" + b"0" * (1024 * 1024)).status_code == 413
    assert stored_files() == []
    assert client.get("/api/resources?section=us").json() == []




def test_admin_delete(client):
    sign_up_admin(client)
    item = upload(client).json()
    assert client.delete(f"/api/resources/{item['id']}").status_code == 200
    assert client.get(item["href"]).status_code == 404
    assert stored_files() == []
    assert client.delete(f"/api/resources/{item['id']}").status_code == 404


def test_delete_needs_admin(client):
    sign_up_admin(client)
    item = upload(client).json()
    client.post("/api/auth/logout")
    assert client.delete(f"/api/resources/{item['id']}").status_code == 401
    sign_up(client, username="student")
    assert client.delete(f"/api/resources/{item['id']}").status_code == 403


def test_scraped_links_cannot_be_deleted(client):
    with SessionLocal() as db:
        db.add(Resource(section="us", contest="amc10", year=2024, title="2024 AMC 10A Problems", kind="problems",
                        source="aops", url="https://artofproblemsolving.com/wiki/index.php/2024_AMC_10A_Problems"))
        db.commit()
    item = client.get("/api/resources?section=us").json()[0]
    assert item["href"].startswith("https://artofproblemsolving.com/") and item["file_type"] == "Link"
    sign_up_admin(client)
    assert client.delete(f"/api/resources/{item['id']}").status_code == 400




def test_recent_newest_first(client):
    sign_up_admin(client)
    upload(client, title="first")
    upload(client, title="second", section="canada", contest="euclid")
    recent = client.get("/api/resources/recent?limit=5").json()
    assert [r["title"] for r in recent] == ["second", "first"]
    assert recent[0]["section_name"] == "Canada Competitions"
