def test_vercel_entrypoint_exposes_wsgi_app():
    from api.index import app

    assert callable(app)
    assert hasattr(app, "wsgi_app")
