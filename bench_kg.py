"""Flat RAG vs GraphRAG (Neo4j) on the two drug knowledge bases: accuracy, latency, tokens, USD.

    docker run -d --name neo4j-drug-kg -p 7474:7474 -p 7687:7687 -e NEO4J_AUTH=neo4j/password123 neo4j:5
    python bench_kg.py --check    # free: env + Neo4j + KG-1..KG-4 sanity check, no OpenAI calls
    python bench_kg.py            # needs OPENAI_API_KEY in .env
    python bench_kg.py --judge    # + LLM-as-judge score (metered separately, not counted in pipeline cost)

Writes ket_qua_benchmark_kg.txt (summary table + every answer).
"""

from __future__ import annotations

import argparse
import json
import os
import time
from importlib import import_module
from pathlib import Path

from dotenv import load_dotenv

PACKAGE = os.getenv("LAB_SOLUTION_PACKAGE", "src")
_m = import_module(PACKAGE)
graph_mod = import_module(f"{PACKAGE}.graph")
llm_mod = import_module(f"{PACKAGE}.llm")
Document, EmbeddingStore, KnowledgeBaseAgent, RecursiveChunker = (
    _m.Document, _m.EmbeddingStore, _m.KnowledgeBaseAgent, _m.RecursiveChunker)
Usage = llm_mod.Usage

JUDGE_PROMPT = """Chấm câu trả lời so với đáp án chuẩn. Trả về JSON {{"score": 0|1|2, "reason": "..."}}:
2 = đúng và đủ các ý chính, 1 = đúng một phần, 0 = sai hoặc không trả lời được.
Câu hỏi: {question}
Đáp án chuẩn: {gold}
Câu trả lời: {answer}"""

def chunk_docs(docs: list, chunk_size: int) -> list:
    chunker = RecursiveChunker(chunk_size=chunk_size)
    return [
        Document(id=f"{doc.id}#{i}", content=piece, metadata={**doc.metadata, "doc_id": doc.id})
        for doc in docs
        for i, piece in enumerate(chunker.chunk(doc.content))
    ]

def keyword_recall(answer: str, keywords: list[str]) -> float:
    return sum(k.lower() in answer.lower() for k in keywords) / len(keywords)

def metered(llm, fn):
    """Run fn(), return (result, Usage delta incl. wall-clock seconds)."""
    before, start = llm.usage, time.perf_counter()
    result = fn()
    delta = llm.usage - before
    delta.seconds = time.perf_counter() - start
    return result, delta

def fail(code: str, problem: str, fix: str) -> None:
    print(f"\n[LỖI {code}] {problem}\n  Cách sửa: {fix}\n  Tra bảng lỗi: LAB_GUIDE.md mục 'Xử lý lỗi'")
    raise SystemExit(1)

def ok(message: str) -> None:
    print(f"[OK] {message}")

def require_key() -> None:
    if not os.getenv("OPENAI_API_KEY", "").startswith("sk-"):
        fail("SETUP-1", "Chưa có OPENAI_API_KEY.",
             "copy .env.example thành .env, điền OPENAI_API_KEY=sk-... (không cần cho --check).")

def connect_graph():
    from neo4j.exceptions import AuthError, ServiceUnavailable

    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    try:
        return graph_mod.Neo4jGraph(uri, os.getenv("NEO4J_USER", "neo4j"), os.getenv("NEO4J_PASSWORD", "password123"))
    except ServiceUnavailable:
        fail("SETUP-2", f"Không kết nối được Neo4j tại {uri}.",
             "bật Docker Desktop, chạy `docker start neo4j-drug-kg` (lần đầu: lệnh docker run ở LAB_GUIDE.md Bước 0), "
             "đợi ~20 giây rồi chạy lại.")
    except AuthError:
        fail("SETUP-3", "Neo4j từ chối đăng nhập.",
             "NEO4J_USER/NEO4J_PASSWORD trong .env phải khớp NEO4J_AUTH lúc docker run (mặc định neo4j/password123).")

def load_corpus():
    law_docs = graph_mod.load_markdown_docs("data/drug_law")
    news_docs = graph_mod.load_markdown_docs("data/drug_news")
    if not law_docs or not news_docs:
        fail("DATA-1", "Thiếu dữ liệu trong data/drug_law hoặc data/drug_news.",
             "python scripts/crawl_drug_corpus.py --news-limit 20")
    return law_docs, news_docs

def check() -> int:
    """Free self-check (no OpenAI call) so students find setup/TODO problems before spending money."""
    law_docs, news_docs = load_corpus()
    ok(f"Dữ liệu: {len(law_docs)} điều luật, {len(news_docs)} bài báo")
    articles = [graph_mod.parse_law_article(doc) for doc in law_docs]
    a251 = next((a for a in articles if a["id"] == "Điều 251 BLHS"), None)
    if not a251 or a251["crime"] != "mua bán trái phép chất ma túy" or len(a251["clauses"]) < 4:
        fail("KG-2", "parse_law_article chưa đúng với Điều 251 BLHS (crime hoặc số khoản sai).",
             "pytest tests/test_graph.py -k ParseLawArticle -v")
    ok("KG-2 parse_law_article: Điều 251 có crime + đủ khoản")
    crimes = [a["crime"] for a in articles if a["crime"]]
    if graph_mod.link_crime("Tội mua bán trái phép chất ma tuý", crimes) != "mua bán trái phép chất ma túy":
        fail("KG-1", "link_crime không map được biến thể chính tả 'ma tuý' về tội trong luật.",
             "pytest tests/test_graph.py -k LinkCrime -v")
    ok("KG-1 link_crime")

    graph = connect_graph()
    ok("Neo4j kết nối được")
    graph.reset()
    for article in articles:
        graph.add_law_article(article)
    fixture = {"name": "[check] Vụ Lê Minh Thành", "summary": "Mua bán MDMA.",
               "charges": ["mua bán trái phép chất ma túy"], "substances": [{"name": "MDMA", "amount": "5 viên"}],
               "people": [{"name": "Lê Minh Thành", "role": "bị cáo", "charge": "", "sentence": "36 tháng tù"}]}
    graph.add_news_case(fixture, Document("check", "", {}))
    facts = graph.context("Lê Minh Thành bị xử theo điều nào?", [])
    clause_facts = [f for f in facts if f.startswith("[Điều 251 BLHS")]
    if not any("khoản 1:" in f for f in clause_facts) or not any("MDMA" in f for f in clause_facts):
        fail("KG-4", "Neo4jGraph.context không đi được Person -> Case -> Crime -> Article -> Clause.",
             "thử Cypher trong Neo4j Browser (LAB_GUIDE.md Bước 5); cần có khoản 1 và khoản nhắc MDMA của Điều 251.")
    ok(f"KG-4 hop xuyên KB: {len(clause_facts)} khoản của Điều 251 lấy được từ 'Lê Minh Thành'")

    store = EmbeddingStore(collection_name="check", embedding_fn=_m._mock_embed)
    store.add_documents([Document("check", "Lê Minh Thành bị tuyên 36 tháng tù.", {"doc_id": "check"})])
    prompt = graph_mod.GraphRAGAgent(store=store, graph=graph, llm_fn=lambda p: p).answer("Lê Minh Thành?", top_k=1)
    if "Điều 251 BLHS" not in prompt or "36 tháng" not in prompt:
        fail("KG-3", "GraphRAGAgent.answer chưa đưa cả dữ kiện graph và đoạn văn bản vào prompt.",
             "pytest tests/test_graph.py -k GraphRAGAgent -v")
    ok("KG-3 GraphRAGAgent.answer")
    graph.reset()
    graph.close()

    load_dotenv(override=False)
    if os.getenv("OPENAI_API_KEY", "").startswith("sk-"):
        ok("OPENAI_API_KEY có trong .env -> chạy: python bench_kg.py --judge")
    else:
        print("[CHÚ Ý SETUP-1] Chưa có OPENAI_API_KEY trong .env -> cần trước khi chạy benchmark thật.")
    return 0

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument("--chunk-size", type=int, default=800)
    parser.add_argument("--judge", action="store_true")
    parser.add_argument("--out", default="ket_qua_benchmark_kg.txt")
    parser.add_argument("--check", action="store_true", help="free self-check, no OpenAI calls")
    args = parser.parse_args()
    load_dotenv(override=False)
    if args.check:
        return check()

    require_key()
    law_docs, news_docs = load_corpus()
    connect_graph().close()  # fail fast before paying for embeddings
    llm = llm_mod.MeteredOpenAI()
    chunks = chunk_docs(law_docs + news_docs, args.chunk_size)
    questions = json.loads(Path("data/benchmark_kg.json").read_text(encoding="utf-8"))

    # --- Indexing. Flat RAG = embed chunks. GraphRAG = the same vector index + KG build.
    store = EmbeddingStore(collection_name="drug_kb", embedding_fn=llm.embed)
    _, flat_index = metered(llm, lambda: store.add_documents(chunks))

    graph = connect_graph()

    def build_graph() -> None:
        graph.reset()
        articles = [graph_mod.parse_law_article(doc) for doc in law_docs]
        for article in articles:
            graph.add_law_article(article)
        crimes = [a["crime"] for a in articles if a["crime"]]
        for doc in news_docs:
            for case in graph_mod.extract_news_cases(doc, lambda p: llm.chat(p, json_mode=True), crimes):
                graph.add_news_case(case, doc)

    _, kg_build = metered(llm, build_graph)
    graph_index = flat_index + kg_build

    # --- Querying.
    flat_agent = KnowledgeBaseAgent(store=store, llm_fn=llm.chat)
    graph_agent = graph_mod.GraphRAGAgent(store=store, graph=graph, llm_fn=llm.chat)
    rows = []
    for q in questions:
        for name, agent in (("flat", flat_agent), ("graph", graph_agent)):
            answer, usage = metered(llm, lambda: agent.answer(q["question"], top_k=args.top_k))
            row = {"id": q["id"], "type": q["type"], "pipeline": name, "answer": answer, "usage": usage,
                   "recall": keyword_recall(answer, q["must_include"])}
            if args.judge:
                verdict = llm.chat(JUDGE_PROMPT.format(question=q["question"], gold=q["gold"], answer=answer), json_mode=True)
                row["judge"] = json.loads(verdict).get("score", 0)
            rows.append(row)
            print(f"{q['id']} {name:5} recall={row['recall']:.2f} {usage.seconds:.2f}s ${usage.usd:.5f}")
    stats = graph.stats()
    graph.close()

    # --- Report.
    lines = [f"Chat model: {llm.chat_model} | Embedding: {llm.embedding_model} | top_k={args.top_k} "
             f"| chunk_size={args.chunk_size} | chunks={len(chunks)} | KG: {stats['nodes']} nodes / {stats['relationships']} rels", ""]
    lines.append("== Indexing (one-off)")
    lines.append(f"{'pipeline':8} {'calls':>6} {'in_tok':>9} {'out_tok':>8} {'USD':>9} {'seconds':>8}")
    for name, u in (("flat", flat_index), ("graph", graph_index)):
        lines.append(f"{name:8} {u.calls:>6} {u.input_tokens:>9} {u.output_tokens:>8} {u.usd:>9.5f} {u.seconds:>8.1f}")
    lines += ["", "== Querying (mean per question)"]
    lines.append(f"{'pipeline':8} {'recall':>7} {'judge':>6} {'in_tok':>8} {'out_tok':>8} {'USD':>9} {'seconds':>8}")
    for name in ("flat", "graph"):
        mine = [r for r in rows if r["pipeline"] == name]
        n = len(mine)
        total = sum((r["usage"] for r in mine), Usage())
        judge = f"{sum(r.get('judge', 0) for r in mine) / n:.2f}" if args.judge else "-"
        lines.append(f"{name:8} {sum(r['recall'] for r in mine) / n:>7.2f} {judge:>6} {total.input_tokens / n:>8.0f} "
                     f"{total.output_tokens / n:>8.0f} {total.usd / n:>9.5f} {total.seconds / n:>8.2f}")
    lines += ["", "== Per question"]
    for r in rows:
        lines.append(f"--- {r['id']} [{r['type']}] {r['pipeline']} recall={r['recall']:.2f}"
                     f"{' judge=' + str(r['judge']) if 'judge' in r else ''} {r['usage'].seconds:.2f}s")
        lines.append(r["answer"].strip())
    Path(args.out).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines[: lines.index("== Per question")]))
    print(f"Saved {args.out}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
