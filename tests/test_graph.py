"""Knowledge Graph checkpoint — offline (no Neo4j, no API key).

    pytest tests/test_graph.py -v
"""

import importlib
import os
import unittest

PACKAGE_NAME = os.getenv("LAB_SOLUTION_PACKAGE", "src")
graph = importlib.import_module(f"{PACKAGE_NAME}.graph")
models = importlib.import_module(f"{PACKAGE_NAME}.models")

ARTICLE_251 = models.Document(
    id="blhs-dieu-251",
    content=(
        "Điều 251. Tội mua bán trái phép chất ma túy\n\n"
        "1. Người nào mua bán trái phép chất ma túy, thì bị phạt tù từ 02 năm đến 07 năm.\n\n"
        "2.[2] Phạm tội thuộc một trong các trường hợp sau đây, thì bị phạt tù từ 07 năm đến 15 năm:\n\n"
        "a) Có tổ chức;\n\n"
        "h) Heroine, Cocaine, Methamphetamine, Amphetamine, MDMA hoặc XLR-11 có khối lượng từ 05 gam đến dưới 30 gam;\n\n"
        "4. Phạm tội thuộc một trong các trường hợp sau đây, thì bị phạt tù 20 năm, tù chung thân hoặc tử hình:\n\n"
        "b) Heroine, Cocaine, Methamphetamine, Amphetamine, MDMA hoặc XLR-11 có khối lượng 100 gam trở lên;"
    ),
    metadata={"doc_id": "blhs-dieu-251", "title": "Điều 251 BLHS. Tội mua bán trái phép chất ma túy",
              "article": "Điều 251 BLHS", "law": "BLHS", "kb": "law"},
)
CRIMES = ["mua bán trái phép chất ma túy", "vận chuyển trái phép chất ma túy", "tổ chức sử dụng trái phép chất ma túy"]

class TestParseLawArticle(unittest.TestCase):
    def setUp(self):
        self.article = graph.parse_law_article(ARTICLE_251)

    def test_article_id_and_crime(self):
        self.assertEqual(self.article["id"], "Điều 251 BLHS")
        self.assertEqual(self.article["crime"], "mua bán trái phép chất ma túy")

    def test_clauses_numbered_in_order(self):
        self.assertEqual([c["number"] for c in self.article["clauses"]], [1, 2, 4])
        self.assertEqual(self.article["clauses"][0]["id"], "Điều 251 BLHS khoản 1")

    def test_penalty_extracted(self):
        self.assertEqual(self.article["clauses"][0]["penalty"], "phạt tù từ 02 năm đến 07 năm")
        self.assertIn("tử hình", self.article["clauses"][2]["penalty"])

    def test_footnote_removed_and_substances_found(self):
        clause2 = self.article["clauses"][1]
        self.assertNotIn("[2]", clause2["text"])
        self.assertIn("MDMA", clause2["substances"])

    def test_non_crime_article_has_no_crime(self):
        doc = models.Document("pcmt-dieu-2", "Điều 2. Giải thích từ ngữ\n\n1. Chất ma túy là ...",
                              {"title": "Điều 2 Luật PCMT. Giải thích từ ngữ", "article": "Điều 2 Luật PCMT"})
        self.assertIsNone(graph.parse_law_article(doc)["crime"])

class TestLinkCrime(unittest.TestCase):
    def test_exact_after_normalize(self):
        self.assertEqual(graph.link_crime("Tội Mua bán trái phép chất ma túy", CRIMES), CRIMES[0])

    def test_fuzzy_spelling_variant(self):
        # "ma tuý" (accent on y) vs "ma túy" — common in Vietnamese news
        self.assertEqual(graph.link_crime("vận chuyển trái phép chất ma tuý", CRIMES), CRIMES[1])

    def test_unrelated_charge_is_none(self):
        self.assertIsNone(graph.link_crime("lừa đảo chiếm đoạt tài sản", CRIMES))

class TestGraphRAGAgent(unittest.TestCase):
    def test_answer_uses_graph_facts_and_chunks(self):
        store_mod = importlib.import_module(PACKAGE_NAME)
        store = store_mod.EmbeddingStore("kg_agent_test")
        store.add_documents([models.Document("news-1", "Lê Minh Thành bị tuyên 36 tháng tù.", {"doc_id": "news-1"})])

        class FakeGraph:
            def context(self, question, doc_ids):
                self.doc_ids = doc_ids
                return ["[Điều 251 BLHS - Tội mua bán trái phép chất ma túy] khoản 1: phạt tù từ 02 năm đến 07 năm"]

        fake = FakeGraph()
        agent = graph.GraphRAGAgent(store=store, graph=fake, llm_fn=lambda prompt: prompt)
        prompt = agent.answer("Lê Minh Thành bị xử theo điều nào?", top_k=1)
        self.assertEqual(fake.doc_ids, ["news-1"])
        self.assertIn("Điều 251 BLHS", prompt)
        self.assertIn("36 tháng", prompt)

if __name__ == "__main__":
    unittest.main()
