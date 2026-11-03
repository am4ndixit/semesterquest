import os, tempfile

TEST_HOME=tempfile.mkdtemp(prefix="semester-quest-tests-")
os.environ["SQ_DATA_DIR"]=os.path.join(TEST_HOME,"data")
os.environ["SQ_UPLOAD_DIR"]=os.path.join(TEST_HOME,"uploads")
os.environ["DATABASE_URL"]="sqlite:///"+os.path.join(TEST_HOME,"test.db")
os.environ["DEV_SHOW_CODE"]="1"
os.environ["SQ_SECRET_KEY"]="test-secret-not-for-production"

import pytest
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c

def login(client, email="e26b07f0007@adypu.edu.in", password="password123"):
    started=client.post("/api/auth/start",json={"email":email,"password":password})
    assert started.status_code==200, started.text
    verified=client.post("/api/auth/verify",json={"email":email,"code":started.json()["dev_code"]})
    assert verified.status_code==200, verified.text
    return {"Authorization":"Bearer "+verified.json()["token"]}

@pytest.fixture
def auth(client):
    return login(client)
