from html.parser import HTMLParser


class FormMarkupParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.forms = []
        self._open_forms = []

    def handle_starttag(self, tag, attrs):
        if tag != "form":
            return
        attributes = dict(attrs)
        form = {"attributes": attributes, "parent": self._open_forms[-1] if self._open_forms else None}
        self.forms.append(form)
        self._open_forms.append(form)

    def handle_endtag(self, tag):
        if tag == "form" and self._open_forms:
            self._open_forms.pop()


def csrf(client):
    with client.session_transaction() as session:
        return session["csrf_token"]


def login(client):
    response = client.post("/auth/dev-login", data={"email": "markup@example.test", "name": "Markup"})
    assert response.status_code == 302
    accepted = client.post("/account/settings/terms", data={"csrf_token": csrf(client), "accept": "on"})
    assert accepted.status_code == 302


def test_editor_has_no_nested_forms_and_sharing_is_sibling_form(client):
    login(client)
    created = client.post("/projects", data={"csrf_token": csrf(client), "project_type": "case"})
    editor = client.get(created.headers["Location"])
    assert editor.status_code == 200

    parser = FormMarkupParser()
    body = editor.get_data(as_text=True)
    parser.feed(body)

    assert len(parser.forms) == 2
    assert all(form["parent"] is None for form in parser.forms)

    editor_form = next(form for form in parser.forms if "data-project-editor" in form["attributes"])
    sharing_form = next(form for form in parser.forms if "data-sharing-form" in form["attributes"])
    assert editor_form["parent"] is None
    assert sharing_form["parent"] is None
    assert sharing_form["attributes"]["method"] == "post"
    assert body.find('id="project-sharing"') < body.find("data-project-editor")
    assert 'data-reload-editor' in body
    assert 'aria-live="polite"' in body
