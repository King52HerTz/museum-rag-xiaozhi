import unittest

from backend.indexing.document_loader import strip_indexing_boilerplate
from backend.rag import utils


class DocumentLoaderCleanupTests(unittest.TestCase):
    def test_repeated_conversion_metadata_is_removed(self):
        source = """智博导览 · 湖南博物院官方知识库    马王堆文物资料

官方知识库资料

利苍一家与西汉长沙国背景

Markdown 主资料转换版 · historical_context

资料范围

湖南博物院 · 长沙马王堆汉墓陈列

权威来源

湖南博物院官网 hnmuseum.com

整理日期

2026-08-29

使用边界

用于导览问答

资料标记：来源级别：official；页面整理日期：2026-08-29。

官方结论

利苍一家与三座墓葬有关。

第  页"""

        cleaned = strip_indexing_boilerplate(source)

        self.assertNotIn("智博导览 ·", cleaned)
        self.assertNotIn("整理日期", cleaned)
        self.assertNotIn("2026-08-29", cleaned)
        self.assertNotIn("用于导览问答", cleaned)
        self.assertIn("利苍一家与西汉长沙国背景", cleaned)
        self.assertIn("官方结论", cleaned)
        self.assertIn("利苍一家与三座墓葬有关", cleaned)

    def test_normal_museum_content_is_preserved(self):
        source = "展品概览\n\n辛追墓出土了大量重要文物。"

        self.assertEqual(source, strip_indexing_boilerplate(source))

    def test_retrieval_cleanup_changes_only_returned_copy(self):
        docs = [{"filename": "资料.docx", "text": "官方知识库资料\n\n正文内容"}]

        cleaned, changed = utils._clean_retrieval_context(docs)

        self.assertTrue(changed)
        self.assertEqual("正文内容", cleaned[0]["text"])
        self.assertIn("官方知识库资料", docs[0]["text"])


if __name__ == "__main__":
    unittest.main()
