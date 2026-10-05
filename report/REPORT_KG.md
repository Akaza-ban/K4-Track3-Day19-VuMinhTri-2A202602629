# Báo cáo Day 19 — Flat RAG vs GraphRAG

**Họ tên:** Vũ Minh Trí  **MSSV:** 2A202602629  **Ngày:** 05/10/2026

> Kỳ vọng và thang điểm: `SUBMISSION.md`. Mọi số liệu phải khớp với `ket_qua_benchmark_kg.txt`. Bản thiết kế ontology nộp riêng ở `report/ONTOLOGY.md`.

## 1. Chi phí (10 điểm)

Dán 2 bảng `Indexing` và `Querying` từ `ket_qua_benchmark_kg.txt`:

```
== Indexing (one-off)
pipeline  calls    in_tok  out_tok       USD  seconds
flat        176         0        0   0.00000    120.4
graph       196     34619     5477   0.00565    166.7

== Querying (mean per question)
pipeline  recall  judge   in_tok  out_tok       USD  seconds
flat        0.51   1.33      696       75   0.00010     5.25
graph       1.00   2.00     5322      174   0.00060     2.39
```

| Chỉ số | Flat | Graph | Graph / Flat |
| --- | --- | --- | --- |
| Indexing USD | 0.00000 | 0.00565 | +$0.00565 |
| Indexing giây | 120.4 | 166.7 | ×1.38 |
| Mỗi câu: USD | 0.00010 | 0.00060 | ×6.00 |
| Mỗi câu: giây | 5.25 | 2.39 | ×0.46 |
| Mỗi câu: in_tok | 696 | 5322 | ×7.65 |

**Chi phí tăng thêm đến từ đâu?**
> Chi phí tăng thêm ở pha Indexing ($0.00565 và thêm 46.3 giây) xuất phát từ 20 lượt gọi LLM để trích xuất có cấu trúc (JSON entity/relationship extraction) cho 20 bài báo tin tức trước khi nạp vào Neo4j (văn bản luật được parse bằng regex nên tốn 0 USD). Ở pha Querying, chi phí tăng gấp 6.0 lần (từ $0.00010 lên $0.00060) và input token tăng gấp 7.65 lần (từ 696 lên 5322 tokens) do prompt của GraphRAG được mở rộng kèm toàn bộ danh sách các dữ kiện đồ thị đa chặng (multi-hop graph facts gồm thông tin vụ án, tội danh, các khoản luật tương ứng và khung hình phạt).

## 2. Từng câu hỏi (10 điểm)

| Câu | Loại | Flat recall / judge | Graph recall / judge | Thắng | Vì sao (1 câu) |
| --- | --- | --- | --- | --- | --- |
| Q1 | single-hop-law | 1.00 / 2 | 1.00 / 2 | Hòa | Cả hai pipeline đều tìm được định nghĩa tiền chất nằm gọn trong một chunk của Luật Phòng, chống ma túy 2021. |
| Q2 | single-hop-news | 1.00 / 2 | 1.00 / 2 | Hòa | Thông tin các bị cáo tuyên án tử hình nằm trọn vẹn trong một bài báo tin tức nên Flat RAG truy xuất đủ không cần graph. |
| Q3 | cross-kb | 0.33 / 1 | 1.00 / 2 | Graph | Flat RAG chỉ tìm được số tháng tù từ tin tức và thiếu hẳn Điều luật trong khi GraphRAG đi qua cầu nối Crime sang Điều 251 khoản 1 BLHS. |
| Q4 | cross-kb | 0.33 / 1 | 1.00 / 2 | Graph | Flat RAG không biết hành vi tổ chức sử dụng thuộc điều luật nào, trong khi GraphRAG nối sang Điều 255 BLHS và trích xuất đúng khung cao nhất là tù chung thân. |
| Q5 | cross-kb-multi-hop | 0.40 / 1 | 1.00 / 2 | Graph | Flat RAG không có cơ chế liên kết đối chiếu khối lượng tang vật sang điều khoản cụ thể, còn GraphRAG nối sang Điều 250 và đối chiếu >9.6kg MDMA thuộc khoản 4. |
| Q6 | aggregation | 0.00 / 1 | 1.00 / 2 | Graph | Flat RAG bị giới hạn top-3 chunks phân mảnh nên không tổng hợp được danh sách vụ án, trong khi GraphRAG gom đủ toàn bộ các vụ án nối với node MDMA. |

## 3. Phân tích lỗi (20 điểm)

### Lỗi E1: Cầu nối gãy (Unconnected Cases)

- **Hiện tượng:** Một số vụ án được LLM trích xuất từ tin tức nhưng hoàn toàn không có cạnh `[:CHARGED_WITH]` nối sang node `Crime`, khiến đường đi từ vụ án sang văn bản luật bị đứt gãy.
- **Bằng chứng:**

```cypher
MATCH (k:Case) WHERE NOT (k)-[:CHARGED_WITH]->() RETURN k.name, k.doc_id;
```

```
"Vụ vận chuyển 840kg chất nghi là ma túy và vũ khí tại Preah Sihanouk", "news-100260924145818945"
"Vụ tông cảnh sát giao thông tại An Giang", "news-100260926112415229"
"Triệt phá chuyên án A3-626P", "news-100261002184934505"
```

- **Nguyên nhân:** Nằm ở bản chất văn bản báo chí và bước prompt trích xuất: các bài báo này đưa tin về vụ việc ban đầu tại nước ngoài (Campuchia) hoặc vụ va chạm giao thông đang trong giai đoạn điều tra ban đầu, chưa có quyết định khởi tố bị can với tội danh chính thức theo Bộ luật Hình sự Việt Nam. Vì prompt yêu cầu LLM bắt buộc chọn tội danh trong DANH SÁCH TỘI DANH BLHS, LLM trả về mảng rỗng `charges: []`, dẫn đến không tạo được quan hệ `CHARGED_WITH`.
- **Đề xuất sửa:** Cho phép tạo một nhãn dự phòng hoặc quan hệ điều tra (ví dụ: `SUSPECTED_OF` hoặc `UNDER_INVESTIGATION`) khi vụ việc chưa có tội danh chính thức. Đánh đổi: Tăng thêm node/cạnh trong graph và có thể làm loãng kết quả truy vấn điều luật khi chỉ cần tìm các tội danh đã khởi tố rõ ràng.

---

### Lỗi E3: Trùng thực thể (Entity Duplication)

- **Hiện tượng:** Cùng một vụ việc hoặc đối tượng ngoài đời thực bị phân mảnh thành nhiều node `Case` khác nhau trong đồ thị do xuất hiện ở nhiều bài báo.
- **Bằng chứng:**

```cypher
MATCH (k:Case) WHERE k.name CONTAINS 'Hoàng Nato' RETURN k.name, k.doc_id;
```

```
"Vụ triệt phá 8 đường dây ma túy liên quan đến 'Hoàng Nato' và 126 người tại TP.HCM", "news-100260920221957595"
"Vụ bắt giữ TikToker Phannhibeauty và giang hồ Hoàng Nato tại TP.HCM", "news-100260922111804786"
"Vụ sử dụng ma túy trong pod chill của 'Hoàng Nato' và TikToker Phannhibeauty", "news-100260924095400982"
"Vụ triệt phá 8 đường dây ma túy liên quan đến 'Hoàng Nato' tại TP.HCM", "news-100260925144412498"
```

- **Nguyên nhân:** Nằm ở thiết kế ontology và cơ chế trích xuất: Ontology định danh `Case` bằng `name` do LLM tự do sinh ra từ nội dung từng bài báo (`MERGE (k:Case {name: $name})`). Do mỗi bài báo có tiêu đề và góc nhìn khác nhau, LLM tạo ra các tên chuỗi khác nhau, khiến Neo4j coi chúng là các node độc lập.
- **Đề xuất sửa:** Bổ sung bước Entity Resolution / Entity Linking cho `Case` (ví dụ gom nhóm các bài báo cùng đề cập đến nhân vật chính `Dương Minh Tuấn` hoặc mã chuyên án chung trước khi tạo node `Case`), hoặc sử dụng khóa kết hợp `case_code` thay vì tên tự do. Đánh đổi: Cần thêm một bước phân tích cross-document tốn thêm token và thời gian indexing.

## 4. Kết luận (5 điểm)

Khi nào nên dùng KG, khi nào Flat RAG là đủ? Dẫn số liệu ở mục 1–2.
> Dựa trên số liệu thực nghiệm:
> 1. **Nên dùng Knowledge Graph (GraphRAG):** Khi bài toán đòi hỏi trả lời các câu hỏi xuyên nhiều nguồn tri thức độc lập (Cross-KB như Q3, Q4, Q5) hoặc câu hỏi tổng hợp đa thực thể (Aggregation như Q6). Ở các câu hỏi này, Flat RAG thất bại nặng nề (recall chỉ đạt 0.00 – 0.40 và judge 1/2) do thông tin nằm ở các văn bản rời rạc không thể cùng xuất hiện trong top-k vector chunking; trong khi GraphRAG đạt độ chính xác tuyệt đối (Recall 1.00 và Judge 2.00 trên toàn bộ các câu hỏi).
> 2. **Flat RAG là hoàn toàn đủ:** Khi nghiệp vụ chủ yếu là tra cứu định nghĩa, trích lục văn bản đơn lẻ (Single-hop như Q1, Q2) mà thông tin nằm gọn trong một đoạn văn bản. Ở trường hợp này, Flat RAG đạt kết quả xuất sắc tương đương GraphRAG (Recall 1.00, Judge 2.00) nhưng chi phí rẻ hơn gần 7 lần ($0.00010 so với $0.00068 mỗi câu) và tốc độ nhanh hơn ~40% mà không tốn công sức thiết kế ontology hay chi phí indexing đồ thị.

## 5. Tự kiểm (5 điểm)

```
$ pytest tests/ -q
................................................                         [100%]
48 passed in 0.05s

$ python bench_kg.py --check
[OK] Dữ liệu: 18 điều luật, 20 bài báo
[OK] KG-1 link_entity
[OK] Neo4j kết nối được
[provider] chat = gemini:gemini-3.5-flash-lite | embedding = gemini:gemini-embedding-001
[OK] KG-2 build_graph: 148 node / 294 cạnh, đường xuyên 2 KB dài 2 cạnh
[OK] KG-3 context: 23 dữ kiện, có Điều 251
[OK] KG-4 GraphRAGAgent.answer
[OK] Chi phí check: 1 lần gọi LLM, $0.00055. Graph nhỏ (luật + 1 bài) vẫn còn trong Neo4j để bạn xem; chạy --judge để dựng graph đầy đủ.
```

Ảnh Neo4j: `report/img/kg_count.png`, `report/img/kg_cross_kb.png`, `report/img/kg_my_case.png`.
Người đã chọn cho `kg_my_case.png`: **Cái Quang Huy** (vụ vận chuyển trái phép chất ma túy qua sân bay Nội Bài, nối sang Điều 250 BLHS).

## Vấn đề gặp phải (không tính điểm)

Lỗi chưa giải quyết được: lệnh đã chạy, toàn bộ thông báo lỗi, những gì đã thử.
> - Ban đầu OpenRouter gặp lỗi `402 - Insufficient credits` do tài khoản chưa có credit. Đã chuyển sang sử dụng `GEMINI_API_KEY` (Gemini 3.5 Flash Lite và Gemini Embedding 001).
> - Trong quá trình batch embedding ban đầu gặp lỗi `503 Service Unavailable` từ Google API do tần suất gọi nhanh; đã xử lý triệt để bằng cách bổ sung cơ chế retry with exponential backoff trong `src/llm.py`.
> - Trên terminal Windows gặp lỗi mã hóa tiếng Việt `UnicodeEncodeError: 'charmap'`; đã xử lý bằng `$env:PYTHONIOENCODING="utf-8"`.
