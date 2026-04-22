from app import create_app


def _component_ids(component):
    current_id = getattr(component, "id", None)
    if current_id is not None:
        yield current_id

    children = getattr(component, "children", None)
    if children is None:
        return
    if not isinstance(children, (list, tuple)):
        children = [children]

    for child in children:
        yield from _component_ids(child)


def test_gemini_api_key_is_not_collected_in_the_ui():
    app = create_app()
    ids = set(_component_ids(app.layout))

    assert "gemini-key" not in ids
    assert "gemini-polish" not in ids
    assert "gemini-status" in ids
