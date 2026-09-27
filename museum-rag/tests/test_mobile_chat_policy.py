import unittest
from unittest.mock import Mock, patch

from backend.chat import runtime, service
from backend.chat.request_context import ChatRequestContext
from tests.test_chat_hitl_resume import FakeStorage, FakeSyncAgent, FakeStreamAgent


class MobileChatPolicyTests(unittest.IsolatedAsyncioTestCase):
    def test_agent_receives_server_side_mode_and_artifact_policy(self):
        for audience in ("child", "adult", None):
            ctx = ChatRequestContext.for_sync(user_id="a", session_id="s")
            ctx.audience = audience
            ctx.exhibit_id = "silk-plain-straight"
            with patch.object(runtime, "create_agent") as create:
                runtime.create_agent_for_request(ctx)
            prompt = create.call_args.kwargs["system_prompt"]
            self.assertIn("search_knowledge_base", prompt)
            if audience:
                self.assertIn("直裾素纱单衣", prompt)
                self.assertIn("保留引用", prompt)
            else:
                self.assertEqual(runtime.SYSTEM_PROMPT, prompt)

    def test_sync_context_uses_persisted_mode(self):
        storage = FakeStorage(metadata={"audience": "child", "exhibit_id": "silk-plain-straight"})
        contexts = []
        def make_agent(ctx):
            contexts.append(ctx)
            return FakeSyncAgent(ctx)
        with patch.object(service, "storage", storage), \
             patch.object(service, "create_agent_for_request", make_agent), \
             patch.object(service, "generate_session_title", return_value="问题"):
            service.chat_with_agent("介绍它", "a", "s")
        self.assertEqual("child", contexts[0].audience)
        self.assertEqual("silk-plain-straight", contexts[0].exhibit_id)
        self.assertEqual("child", storage.metadata["audience"])

    async def test_stream_context_uses_persisted_mode(self):
        storage = FakeStorage(metadata={"audience": "adult"})
        contexts = []
        def make_agent(ctx):
            contexts.append(ctx)
            return FakeStreamAgent(ctx, chunks=["回答"])
        with patch.object(service, "storage", storage), \
             patch.object(service, "create_agent_for_request", make_agent), \
             patch.object(service, "generate_session_title", return_value="问题"):
            chunks = [chunk async for chunk in service.chat_with_agent_stream("介绍它", "a", "s")]
        self.assertTrue(chunks)
        self.assertEqual("adult", contexts[0].audience)
        self.assertEqual("adult", storage.metadata["audience"])

    def test_hitl_direct_answer_preserves_child_policy(self):
        ctx = ChatRequestContext.for_sync(user_id="a", session_id="s")
        ctx.audience = "child"
        ctx.exhibit_id = "silk-plain-straight"
        docs = [{"filename": "guide", "text": "片段"}]
        messages = service._build_resume_answer_messages({"original_question": "介绍它"}, "单衣", docs, ctx)
        self.assertIn("6～9岁", messages[0].content)
        self.assertIn("MUST cite", messages[0].content)
        model = Mock()
        model.invoke.return_value.content = "回答"
        with patch.object(service, "model", model):
            service._answer_resumed_rag_sync({"original_question": "介绍它"}, "单衣", {"docs": docs}, ctx)
        self.assertIn("6～9岁", model.invoke.call_args.args[0][0].content)
