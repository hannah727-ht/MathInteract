

from tests.conftest import sign_up, sign_up_admin
from tests.test_images import upload as upload_image


def log_out(client):
    client.post("/api/auth/logout")


def log_in(client, name):
    assert client.post("/api/auth/login", json={"username": name, "password": "password123"}).status_code == 200


def ask(client, title="How do I factor $x^2 - 5x + 6$?", body="I tried $(x-1)(x-6)$.", topic="ossd", **extra):
    return client.post("/api/questions", json={"title": title, "body": body, "topic": topic, **extra})


def answer(client, question_id, body="Try $(x-2)(x-3)$.", **extra):
    return client.post(f"/api/questions/{question_id}/answers", json={"body": body, **extra})




def test_ask_and_read(client):
    sign_up(client, username="amy")
    img = upload_image(client).json()
    res = ask(client, image_ids=[img["id"]])
    assert res.status_code == 201
    q = res.json()
    assert q["topic"] == "ossd" and q["user"]["username"] == "amy" and q["answer_count"] == 0
    assert q["solved"] is False and q["answers"] == [] and len(q["images"]) == 1

    log_out(client)
    assert client.get(f"/api/questions/{q['id']}").json()["title"] == "How do I factor $x^2 - 5x + 6$?"
    listed = client.get("/api/questions").json()
    assert listed["total"] == 1 and listed["questions"][0]["id"] == q["id"]
    assert [t["key"] for t in listed["topics"]] == ["general", "us", "canada", "ib", "ossd"]


def test_ask_needs_login_and_valid_input(client):
    assert ask(client).status_code == 401
    sign_up(client)
    assert ask(client, title=" ").status_code == 422
    assert ask(client, body="").status_code == 422
    assert ask(client, topic="chemistry").status_code == 422
    assert ask(client, title="x" * 201).status_code == 422
    assert ask(client, image_ids=[999]).status_code == 422
    assert client.get("/api/questions/999").status_code == 404


def test_list_newest_first_with_pages(client):
    sign_up(client)
    for i in range(25):
        ask(client, title=f"Question {i}")
    first = client.get("/api/questions").json()
    assert (first["total"], first["pages"], len(first["questions"])) == (25, 2, 20)
    assert first["questions"][0]["title"] == "Question 24"
    second = client.get("/api/questions?page=2").json()
    assert [q["title"] for q in second["questions"]] == [f"Question {i}" for i in range(4, -1, -1)]
    assert len(client.get("/api/questions?limit=5").json()["questions"]) == 5


def test_topic_filter_and_search(client):
    sign_up(client)
    ask(client, title="AIME 2024 #5", body="Counting problem", topic="us")
    ask(client, title="Euclid tips", body="How to prepare for the Euclid contest?", topic="canada")
    ask(client, title="Vectors", body="MCV4U dot product question", topic="ossd")
    ask(client, title="100% sure?", body="Is 0.999... = 1", topic="general")

    titles = lambda query: [q["title"] for q in client.get(f"/api/questions{query}").json()["questions"]]
    assert titles("?topic=canada") == ["Euclid tips"]
    assert titles("?q=euclid") == ["Euclid tips"]
    assert titles("?q=dot%20product") == ["Vectors"]
    assert titles("?q=%25") == ["100% sure?"]
    assert titles("?q=euclid&topic=us") == []
    assert client.get("/api/questions?topic=chemistry").status_code == 422




def test_answer_and_accept(client):
    sign_up(client, username="amy")
    q = ask(client).json()
    log_out(client)

    assert answer(client, q["id"]).status_code == 401
    sign_up(client, username="bob")
    a1 = answer(client, q["id"], body="Use the quadratic formula.").json()
    a2 = answer(client, q["id"], body="Try $(x-2)(x-3)$.").json()
    assert a2["user"]["username"] == "bob" and a2["accepted"] is False


    assert client.post(f"/api/questions/{q['id']}/accept", json={"answer_id": a2["id"]}).status_code == 403
    log_out(client)
    log_in(client, "amy")
    res = client.post(f"/api/questions/{q['id']}/accept", json={"answer_id": a2["id"]})
    assert res.status_code == 200
    detail = res.json()
    assert detail["solved"] is True and detail["accepted_answer_id"] == a2["id"]
    assert [a["id"] for a in detail["answers"]] == [a2["id"], a1["id"]]
    assert detail["answers"][0]["accepted"] is True
    assert client.get("/api/questions").json()["questions"][0]["solved"] is True


    assert client.post(f"/api/questions/{q['id']}/accept", json={"answer_id": a1["id"]}).json()["accepted_answer_id"] == a1["id"]
    assert client.post(f"/api/questions/{q['id']}/accept", json={"answer_id": None}).json()["solved"] is False


def test_accept_must_be_an_answer_of_this_question(client):
    sign_up(client, username="amy")
    q1 = ask(client).json()
    q2 = ask(client, title="Another").json()
    other = answer(client, q2["id"]).json()
    assert client.post(f"/api/questions/{q1['id']}/accept", json={"answer_id": other["id"]}).status_code == 422
    assert client.post("/api/questions/999/accept", json={"answer_id": None}).status_code == 404


def test_answer_validation(client):
    sign_up(client)
    q = ask(client).json()
    assert answer(client, q["id"], body="   ").status_code == 422
    assert answer(client, q["id"], body="x" * 20_001).status_code == 422
    assert answer(client, 999).status_code == 404




def test_edit_own_posts_only(client):
    sign_up(client, username="amy")
    q = ask(client).json()
    a = answer(client, q["id"]).json()
    res = client.put(f"/api/questions/{q['id']}", json={"title": "Factoring help", "body": "Edited", "topic": "general"})
    assert res.status_code == 200 and res.json()["title"] == "Factoring help" and res.json()["edited"] is True
    res = client.put(f"/api/answers/{a['id']}", json={"body": "Edited answer"})
    assert res.status_code == 200 and res.json()["edited"] is True

    log_out(client)
    sign_up(client, username="bob")
    assert client.put(f"/api/questions/{q['id']}", json={"title": "x", "body": "y", "topic": "general"}).status_code == 403
    assert client.put(f"/api/answers/{a['id']}", json={"body": "hacked"}).status_code == 403
    assert client.put("/api/answers/999", json={"body": "x"}).status_code == 404


def test_admin_deletes_answers_and_questions(client):
    sign_up(client, username="amy")
    q = ask(client).json()
    a = answer(client, q["id"]).json()
    client.post(f"/api/questions/{q['id']}/accept", json={"answer_id": a["id"]})
    assert client.delete(f"/api/answers/{a['id']}").status_code == 403
    assert client.delete(f"/api/questions/{q['id']}").status_code == 403
    log_out(client)

    sign_up_admin(client)
    assert client.delete(f"/api/answers/{a['id']}").status_code == 200
    detail = client.get(f"/api/questions/{q['id']}").json()
    assert detail["answers"] == [] and detail["solved"] is False

    answer(client, q["id"])
    assert client.delete(f"/api/questions/{q['id']}").status_code == 200
    assert client.get(f"/api/questions/{q['id']}").status_code == 404
    assert client.delete(f"/api/questions/{q['id']}").status_code == 404
