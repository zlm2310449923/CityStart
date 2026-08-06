def test_health(api):
    response = api.get("/health")
    assert response.status_code == 200
    assert response.json() == {
        "service": "residence-service",
        "status": "ok",
        "version": "1.0.0",
    }

