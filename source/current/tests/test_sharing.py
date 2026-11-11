
def csrf(client):
    with client.session_transaction() as session:
        return session["csrf_token"]


def login(client, email):
    client.post("/auth/dev-login", data={"email": email, "name": email.split("@")[0]})
    return csrf(client)


def accept_terms(client, token):
    client.post("/account/settings/terms", data={"csrf_token": token, "accept": "on"})


def test_owner_can_share_and_admin_can_comment_without_editing_text(client):
    owner_token = login(client, "owner@example.test")
    accept_terms(client, owner_token)
    created = client.post("/projects", data={"csrf_token": owner_token, "project_type": "case"})
    project_id = created.headers["Location"].rsplit("/", 1)[-1]
    shared = client.post(f"/projects/{project_id}/sharing", data={"csrf_token": owner_token, "allow_admin_view": "on", "allow_admin_comments": "on"})
    assert shared.status_code == 302
    client.application.config["ADMIN_EMAILS"] = {"admin@example.test"}
    admin_token = login(client, "admin@example.test")
    accept_terms(client, admin_token)
    listing = client.get("/admin/projects")
    assert listing.status_code == 200
    assert project_id in listing.get_data(as_text=True)
    detail = client.get(f"/admin/projects/{project_id}")
    assert detail.status_code == 200
    comment = client.post(f"/admin/projects/{project_id}/comments", data={"csrf_token": admin_token, "body": "Confira a fundamentação."})
    assert comment.status_code == 302
    owner_token = login(client, "owner@example.test")
    editor = client.get(f"/projects/{project_id}")
    assert "Confira a fundamentação." in editor.get_data(as_text=True)


def test_non_admin_cannot_list_shared_projects(client):
    token = login(client, "student@example.test")
    accept_terms(client, token)
    assert client.get("/admin/projects").status_code == 403
