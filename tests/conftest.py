import pytest
import requests


@pytest.fixture(autouse=True)
def forbid_live_api(monkeypatch):
    def blocked(*args, **kwargs):
        raise AssertionError("Chamadas HTTP reais são proibidas nos testes")

    monkeypatch.setattr(requests.sessions.Session, "request", blocked)
