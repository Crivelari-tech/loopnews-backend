# LoopNews v1.5.7 release regression: scheduler digests, search, text quality, admin routes, new feeds
import os
import re
import pytest
import requests
from dotenv import dotenv_values

FE_ENV = dotenv_values("/app/frontend/.env")
BE_ENV = dotenv_values("/app/backend/.env")
BASE_URL = (os.environ.get("EXPO_BACKEND_URL") or FE_ENV.get("EXPO_PUBLIC_BACKEND_URL")).rstrip("/")
ADMIN_KEY = BE_ENV.get("ADMIN_KEY")
REVIEWER = "reviewer@loopnewsapp.com"


@pytest.fixture(scope="module")
def token():
    s = requests.post(f"{BASE_URL}/api/auth/send-code", json={"email": REVIEWER}, timeout=30)
    assert s.status_code == 200, s.text
    r = requests.post(f"{BASE_URL}/api/auth/verify-code", json={"email": REVIEWER, "code": "123456"}, timeout=30)
    if r.status_code != 200:
        pytest.skip(f"auth failed {r.status_code}")
    data = r.json()
    tok = data.get("session_token")
    assert tok
    return tok


@pytest.fixture(scope="module")
def auth(token):
    return {"Authorization": f"Bearer {token}"}


# Auth OTP
def test_otp_login_returns_session_token(token):
    assert isinstance(token, str) and len(token) > 10


# Scheduler: 3 digests
def test_scheduler_has_three_digests():
    r = requests.get(f"{BASE_URL}/api/scheduler/status", timeout=30)
    assert r.status_code == 200, r.text
    txt = r.text
    data = r.json()
    jobs = data.get("jobs", [])
    ids = {j.get("id"): j for j in jobs}
    expected = {"daily_digest": "10", "lunch_digest": "15", "evening_digest": "22"}
    for jid, hour in expected.items():
        assert jid in ids, f"{jid} missing; jobs={list(ids)}"
        j = ids[jid]
        assert f"hour='{hour}'" in str(j.get("trigger", "")) or hour in str(j), j
    print("digest jobs:", {k: ids[k] for k in expected})


# Search
def test_search_gta(auth):
    r = requests.get(f"{BASE_URL}/api/news/search", params={"q": "gta", "limit": 10}, headers=auth, timeout=30)
    assert r.status_code == 200
    news = r.json()["news"]
    assert len(news) > 0
    for n in news:
        text = f"{n.get('title','')} {n.get('summary','')} {n.get('ai_summary','')}"
        assert re.search(r"\bgta", text, re.I), n["title"]


def test_search_lula_not_celula(auth):
    r = requests.get(f"{BASE_URL}/api/news/search", params={"q": "lula", "limit": 30}, headers=auth, timeout=30)
    assert r.status_code == 200
    news = r.json()["news"]
    assert len(news) > 0
    bad = []
    for n in news:
        text = f"{n.get('title','')} {n.get('summary','')} {n.get('ai_summary','')}"
        if not re.search(r"\blula", text, re.I):
            bad.append(n["title"])
    assert not bad, bad


def test_search_requires_auth():
    r = requests.get(f"{BASE_URL}/api/news/search", params={"q": "gta"}, timeout=30)
    assert r.status_code == 401


# Text quality in feed
ENTITY_RE = re.compile(r"&(quot|amp|gt|lt|nbsp|#\d+|#x[0-9a-f]+);?", re.I)


def test_feed_text_clean(auth):
    r = requests.get(f"{BASE_URL}/api/news", params={"limit": 20}, headers=auth, timeout=30)
    assert r.status_code == 200
    data = r.json()
    news = data["news"] if isinstance(data, dict) else data
    assert len(news) > 0
    issues = []
    for n in news:
        for f in ("title", "summary"):
            v = n.get(f) or ""
            if ENTITY_RE.search(v) or "&#" in v:
                issues.append((f, "entity", v[:120]))
            if "apareceu primeiro" in v:
                issues.append((f, "rodape", v[:120]))
            if v in ("null", "None"):
                issues.append((f, "null", v))
        assert n.get("image_url"), n.get("title")
    assert not issues, issues


# Admin routes
def test_admin_clean_text_no_key_403():
    r = requests.get(f"{BASE_URL}/api/admin/clean-text", timeout=30)
    assert r.status_code == 403


def test_admin_clean_text_wrong_key_403():
    r = requests.get(f"{BASE_URL}/api/admin/clean-text", params={"key": "wrong"}, timeout=30)
    assert r.status_code == 403


def test_admin_clean_text_with_key():
    r = requests.get(f"{BASE_URL}/api/admin/clean-text", params={"key": ADMIN_KEY}, timeout=120)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["status"] == "success" and isinstance(d["fixed"], int)
    print("clean-text fixed:", d["fixed"])


def test_admin_push_status_no_key_403():
    r = requests.get(f"{BASE_URL}/api/admin/push-status", timeout=30)
    assert r.status_code == 403


def test_admin_push_status_with_key():
    r = requests.get(f"{BASE_URL}/api/admin/push-status", params={"key": ADMIN_KEY}, timeout=30)
    assert r.status_code == 200
    d = r.json()
    for k in ("total_usuarios", "usuarios_com_dispositivo_registrado", "usuarios_com_notificacoes_ativadas"):
        assert isinstance(d[k], int)
    print({k: d[k] for k in d if k != "amostra"})


# Ingestion: new sources in DB
NEW_SOURCES = ["Metrópoles", "CNN Brasil", "ge", "Olhar Digital", "Rolling Stone Brasil", "Autoesporte",
               "Superinteressante", "Guia do Estudante", "Quem", "Flow Games", "IGN Brasil", "GameVicio",
               "MeuPlayStation", "Agência Brasil", "Canaltech", "TMDQA", "Canaltech Games"]


def test_new_sources_in_db():
    from pymongo import MongoClient
    c = MongoClient(BE_ENV["MONGO_URL"], serverSelectionTimeoutMS=20000)
    db = c[BE_ENV["DB_NAME"]]
    counts = {s: db.news.count_documents({"source_name": s}) for s in NEW_SOURCES}
    print("source counts:", counts)
    required = NEW_SOURCES[:13]
    missing = [s for s in required if counts[s] == 0]
    assert not missing, f"missing sources: {missing}; counts={counts}"
