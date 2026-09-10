import unittest

from scripts.evaluate_retrieval import evaluate_cases, normalize_document_name, rank_gold_document


class RetrievalEvaluatorTests(unittest.TestCase):
    def test_normalize_document_name_ignores_extension(self):
        self.assertEqual("03_利苍一家", normalize_document_name("03_利苍一家.md"))
        self.assertEqual("03_利苍一家", normalize_document_name("03_利苍一家.docx"))

    def test_rank_gold_document_returns_one_based_rank(self):
        rank = rank_gold_document(
            [
                {"filename": "其他资料.docx"},
                {"filename": "03_利苍一家.docx"},
            ],
            [{"canonical_name": "03_利苍一家.md"}],
        )

        self.assertEqual(2, rank)

    def test_evaluate_cases_reports_recall_and_mrr(self):
        cases = [
            {
                "id": "hit",
                "question": "问题一",
                "gold_documents": [{"canonical_name": "A.md"}],
            },
            {
                "id": "miss",
                "question": "问题二",
                "gold_documents": [{"canonical_name": "B.md"}],
            },
            {"id": "no-gold", "question": "问题三", "gold_documents": []},
        ]

        def retrieve(question):
            if question == "问题一":
                return {"docs": [{"filename": "X.docx"}, {"filename": "A.docx"}]}
            return {"docs": [{"filename": "X.docx"}]}

        report = evaluate_cases(cases, retrieve)

        self.assertEqual(2, report["evaluated_cases"])
        self.assertEqual(0.5, report["document_recall"])
        self.assertEqual(0.25, report["mrr"])
        self.assertEqual(1, report["miss_count"])


if __name__ == "__main__":
    unittest.main()
