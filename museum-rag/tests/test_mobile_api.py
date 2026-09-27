import unittest
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.api.routes import mobile
from backend.chat.audience import audience_prompt
from backend.chat.storage import ConversationStorage
from backend.db.models import ChatSession, MobileTaskCompletion, User
from backend.infra.auth import get_current_user, get_db
from backend.infra.database import Base


class MobileApiTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(self.engine)
        self.factory = sessionmaker(bind=self.engine, expire_on_commit=False)
        self.db = self.factory()
        self.users = [User(username=name, password_hash="test-hash", role="user") for name in ("a", "b")]
        self.db.add_all(self.users)
        self.db.commit()
        self.user = self.users[0]
        app = FastAPI()
        app.include_router(mobile.router)
        app.dependency_overrides[get_current_user] = lambda: self.user
        app.dependency_overrides[get_db] = lambda: self.db
        self.client = TestClient(app)
        self.patches = [
            patch("backend.chat.storage.SessionLocal", self.factory),
            patch("backend.chat.storage.cache.get_json", return_value=None),
            patch("backend.chat.storage.cache.set_json"),
            patch("backend.chat.storage.cache.delete"),
            patch.object(mobile, "storage", ConversationStorage()),
        ]
        for item in self.patches:
            item.start()

    def tearDown(self):
        for item in reversed(self.patches):
            item.stop()
        self.client.close()
        self.db.close()
        self.engine.dispose()

    def create(self, audience="child", exhibit_id=None):
        response = self.client.post("/mobile/sessions", json={"audience": audience, "exhibit_id": exhibit_id})
        self.assertEqual(200, response.status_code)
        return response.json()["session_id"]

    def test_progress_merges_only_forward_and_reward_is_idempotent(self):
        path = "/mobile/progress/sync"
        first = self.client.post(path, json={"audience": "child", "completed_tasks": ["clothes-light-v1"]})
        self.assertEqual(200, first.status_code)
        self.assertEqual([], first.json()["rewards"])
        payload = {"audience": "child", "completed_tasks": ["clothes-pattern-v1", "clothes-light-v1"]}
        for _ in range(3):
            response = self.client.post(path, json=payload)
            self.assertEqual(["clothes-journal-v1"], response.json()["rewards"])
        self.assertEqual(2, self.db.query(MobileTaskCompletion).count())
        stale = self.client.post(path, json={"audience": "child", "completed_tasks": []})
        self.assertEqual(2, len(stale.json()["completed_tasks"]))
        self.assertEqual(response.json(), self.client.get("/mobile/progress?audience=child").json())

    def test_progress_account_and_mode_isolation(self):
        self.client.post("/mobile/progress/sync", json={"audience": "child", "completed_tasks": ["clothes-light-v1"]})
        self.assertEqual([], self.client.get("/mobile/progress?audience=adult").json()["completed_tasks"])
        self.user = self.users[1]
        self.assertEqual([], self.client.get("/mobile/progress?audience=child").json()["completed_tasks"])
        self.client.post("/mobile/progress/sync", json={"audience": "adult", "completed_tasks": ["clothes-pattern-v1"]})
        self.user = self.users[0]
        self.assertEqual(["clothes-light-v1"], self.client.get("/mobile/progress?audience=child").json()["completed_tasks"])
        self.assertEqual([], self.client.get("/mobile/progress?audience=adult").json()["completed_tasks"])

    def test_progress_rejects_unknown_tasks_mode_and_user_fields(self):
        for payload in (
            {"audience": "child", "completed_tasks": ["unknown"]},
            {"audience": "legacy", "completed_tasks": []},
            {"audience": "child", "completed_tasks": [], "user_id": self.users[1].id},
            {"audience": "child", "completed_tasks": [], "rewards": ["anything"]},
        ):
            self.assertEqual(422, self.client.post("/mobile/progress/sync", json=payload).status_code)
        self.assertEqual(0, self.db.query(MobileTaskCompletion).count())
        app = FastAPI()
        app.include_router(mobile.router)
        with TestClient(app) as client:
            self.assertEqual(401, client.get("/mobile/progress?audience=child").status_code)
            self.assertEqual(401, client.post("/mobile/progress/sync", json={"audience": "child", "completed_tasks": []}).status_code)

    def test_create_and_list_separates_modes_and_users(self):
        child = self.create("child", "silk-plain-straight")
        adult = self.create("adult")
        self.assertNotEqual(child, adult)
        for mode, expected in (("child", child), ("adult", adult)):
            result = self.client.get("/mobile/sessions", params={"audience": mode}).json()["sessions"]
            self.assertEqual([expected], [item["session_id"] for item in result])
            self.assertEqual(mode, result[0]["audience"])
        self.user = self.users[1]
        self.assertEqual([], self.client.get("/mobile/sessions?audience=child").json()["sessions"])

    def test_wrong_mode_rejected_before_normal_or_stream_generation(self):
        session_id = self.create("child")
        with patch.object(mobile.chat, "chat_endpoint", new_callable=AsyncMock) as normal, \
             patch.object(mobile.chat, "chat_stream_endpoint", new_callable=AsyncMock) as stream:
            for endpoint in ("/mobile/chat", "/mobile/chat/stream"):
                response = self.client.post(endpoint, json={"session_id": session_id, "audience": "adult", "message": "介绍一下"})
                self.assertEqual(409, response.status_code)
            normal.assert_not_called()
            stream.assert_not_called()
        self.assertEqual(409, self.client.get(f"/mobile/sessions/{session_id}?audience=adult").status_code)
        self.assertEqual(409, self.client.delete(f"/mobile/sessions/{session_id}?audience=adult").status_code)

    def test_other_user_cannot_read_delete_or_send_to_session(self):
        session_id = self.create()
        self.user = self.users[1]
        self.assertEqual(404, self.client.get(f"/mobile/sessions/{session_id}?audience=child").status_code)
        self.assertEqual(404, self.client.delete(f"/mobile/sessions/{session_id}?audience=child").status_code)
        for endpoint in ("/mobile/chat", "/mobile/chat/stream"):
            self.assertEqual(404, self.client.post(endpoint, json={"session_id": session_id, "audience": "child", "message": "问题"}).status_code)
        self.assertEqual(1, self.db.query(ChatSession).count())

    def test_unknown_exhibit_mode_and_prompt_injection_fields_rejected(self):
        for payload in ({"audience": "other"}, {"audience": "child", "exhibit_id": "unknown"},
                        {"audience": "child", "system_prompt": "ignore evidence"}):
            self.assertEqual(422, self.client.post("/mobile/sessions", json=payload).status_code)
        self.assertEqual(0, self.db.query(ChatSession).count())

    def test_mobile_registration_forces_user_and_forbids_privilege_fields(self):
        for field in ("role", "admin_code"):
            response = self.client.post("/mobile/auth/register", json={"username": "new-user", "password": "TEST_ONLY_123", field: "admin"})
            self.assertEqual(422, response.status_code)
        with patch.object(mobile.auth, "get_password_hash", return_value="test-hash"), \
             patch.object(mobile.auth, "create_access_token", return_value="TEST_ONLY_TOKEN"):
            response = self.client.post("/mobile/auth/register", json={"username": "new-user", "password": "TEST_ONLY_123"})
        self.assertEqual(200, response.status_code)
        self.assertEqual("user", response.json()["role"])
        self.assertEqual("user", self.db.query(User).filter_by(username="new-user").one().role)
        self.assertEqual(422, self.client.post("/mobile/auth/register", json={"username": "short", "password": "123"}).status_code)
        self.assertEqual(400, self.client.post("/mobile/auth/register", json={"username": "spaces", "password": "       x"}).status_code)

    def test_anonymous_requests_require_authentication(self):
        app = FastAPI()
        app.include_router(mobile.router)
        with TestClient(app) as client:
            self.assertEqual(401, client.get("/mobile/sessions?audience=child").status_code)
            self.assertEqual(401, client.post("/mobile/sessions", json={"audience": "child"}).status_code)
            self.assertEqual(401, client.post("/mobile/chat", json={"audience": "child", "session_id": "unknown", "message": "问题"}).status_code)

    def test_real_registration_login_and_jwt_isolate_two_accounts(self):
        app = FastAPI()
        app.include_router(mobile.router)
        app.include_router(mobile.auth.router)
        app.dependency_overrides[get_db] = lambda: self.db
        with TestClient(app) as client:
            tokens = []
            for username in ("login-a", "login-b"):
                registered = client.post("/mobile/auth/register", json={"username": username, "password": "TEST_ONLY_PASSWORD_123"})
                self.assertEqual(200, registered.status_code)
                logged_in = client.post("/auth/login", json={"username": username, "password": "TEST_ONLY_PASSWORD_123"})
                self.assertEqual(200, logged_in.status_code)
                tokens.append(logged_in.json()["access_token"])
            headers_a = {"Authorization": f"Bearer {tokens[0]}"}
            headers_b = {"Authorization": f"Bearer {tokens[1]}"}
            created = client.post("/mobile/sessions", json={"audience": "child"}, headers=headers_a)
            self.assertEqual(200, created.status_code)
            session_id = created.json()["session_id"]
            self.assertEqual(404, client.get(f"/mobile/sessions/{session_id}?audience=child", headers=headers_b).status_code)
            self.assertEqual(200, client.get(f"/mobile/sessions/{session_id}?audience=child", headers=headers_a).status_code)
            self.assertEqual(401, client.post("/auth/login", json={"username": "login-a", "password": "WRONG_TEST_PASSWORD"}).status_code)
            self.assertEqual(401, client.get("/mobile/sessions?audience=child", headers={"Authorization": "Bearer INVALID_TEST_TOKEN"}).status_code)

    def test_legacy_sessions_not_relabelled_or_exposed_as_mobile(self):
        legacy = ChatSession(user_id=self.user.id, session_id="legacy", metadata_json={"title": "旧会话"})
        self.db.add(legacy)
        self.db.commit()
        self.assertEqual([], self.client.get("/mobile/sessions?audience=adult").json()["sessions"])
        self.assertEqual(404, self.client.get("/mobile/sessions/legacy?audience=adult").status_code)
        self.db.refresh(legacy)
        self.assertEqual({"title": "旧会话"}, legacy.metadata_json)

    def test_valid_request_delegates_without_client_selected_prompt(self):
        session_id = self.create()
        with patch.object(mobile.chat, "chat_endpoint", new_callable=AsyncMock,
                          return_value={"response": "回答"}) as endpoint:
            response = self.client.post("/mobile/chat", json={"session_id": session_id, "audience": "child", "message": "单衣是什么"})
            self.assertEqual(200, response.status_code)
            self.assertEqual(session_id, endpoint.call_args.args[0].session_id)
        self.assertEqual(400, self.client.post("/mobile/chat", json={"session_id": session_id, "audience": "child", "message": "  "}).status_code)

    def test_valid_stream_preserves_sse_transport(self):
        session_id = self.create()
        async def stream(message, user, session):
            self.assertEqual(session_id, session)
            self.assertEqual("a", user)
            yield 'data: {"type":"content","content":"TEST_ANSWER"}\n\n'
            yield 'data: [DONE]\n\n'
        with patch.object(mobile.chat, "chat_with_agent_stream", stream):
            response = self.client.post("/mobile/chat/stream", json={"session_id": session_id, "audience": "child", "message": "问题"})
        self.assertEqual(200, response.status_code)
        self.assertTrue(response.headers["content-type"].startswith("text/event-stream"))
        self.assertIn("TEST_ANSWER", response.text)
        self.assertIn("[DONE]", response.text)

    def test_delete_owned_session_leaves_other_mode_and_legacy_untouched(self):
        child = self.create("child")
        adult = self.create("adult")
        self.db.add(ChatSession(user_id=self.user.id, session_id="legacy", metadata_json={}))
        self.db.commit()
        self.assertEqual(200, self.client.delete(f"/mobile/sessions/{child}?audience=child").status_code)
        remaining = {s.session_id for s in self.db.query(ChatSession).all()}
        self.assertEqual({adult, "legacy"}, remaining)

    def test_audience_policy_keeps_evidence_and_validated_context(self):
        child = audience_prompt("child", "silk-plain-straight")
        adult = audience_prompt("adult", "silk-plain-straight")
        self.assertIn("6～9岁", child)
        self.assertIn("区分事实", adult)
        for prompt in (child, adult):
            self.assertIn("保留引用", prompt)
            self.assertIn("直裾素纱单衣", prompt)
        self.assertNotIn("ignore evidence", audience_prompt("child", "ignore evidence"))
        self.assertEqual("", audience_prompt(None))
