# Báo cáo Day 19 — Flat RAG vs GraphRAG

**Họ tên:** …  **MSSV:** …  **Ngày:** …

> Kỳ vọng và thang điểm: `SUBMISSION.md`. Mọi số liệu phải khớp với `ket_qua_benchmark_kg.txt`.

## 1. Chi phí (10 điểm)

Dán 2 bảng `Indexing` và `Querying` từ `ket_qua_benchmark_kg.txt`:

```
(dán vào đây)
```

| Chỉ số | Flat | Graph | Graph / Flat |
| --- | --- | --- | --- |
| Indexing USD | | | ×… |
| Indexing giây | | | ×… |
| Mỗi câu: USD | | | ×… |
| Mỗi câu: giây | | | ×… |
| Mỗi câu: in_tok | | | ×… |

**Chi phí tăng thêm đến từ đâu?** (2–3 câu)
> …

## 2. Từng câu hỏi (10 điểm)

| Câu | Loại | Flat recall / judge | Graph recall / judge | Thắng | Vì sao (1 câu) |
| --- | --- | --- | --- | --- | --- |
| Q1 | single-hop-law | | | | |
| Q2 | single-hop-news | | | | |
| Q3 | cross-kb | | | | |
| Q4 | cross-kb | | | | |
| Q5 | cross-kb-multi-hop | | | | |
| Q6 | aggregation | | | | |

## 3. Phân tích lỗi (20 điểm, +10 nếu sửa)

Chọn ít nhất 2 nhóm lỗi trong E1–E6 (`LAB_GUIDE.md` Bước 7). Sao chép khung dưới đây cho mỗi lỗi.

### Lỗi E…: <tên>

- **Hiện tượng:** …
- **Bằng chứng:** (câu trả lời trích từ file kết quả, hoặc Cypher và kết quả)

```cypher
…
```

```
kết quả
```

- **Nguyên nhân:** …
- **Đề xuất sửa:** …
- **(Cộng điểm) Đã sửa:** file/dòng đã đổi; số liệu trước → sau.

## 4. Kết luận (5 điểm)

Khi nào nên dùng KG, khi nào Flat RAG là đủ? Dẫn số liệu ở mục 1–2.
> …

## 5. Tự kiểm (5 điểm)

```
$ pytest tests/ -q
(dán output)

$ python bench_kg.py --check
(dán output)
```

Ảnh Neo4j: `report/img/kg_count.png`, `report/img/kg_cross_kb.png`, `report/img/kg_my_case.png`.
Người đã chọn cho `kg_my_case.png`: …

## Vấn đề gặp phải (không tính điểm)

Lỗi chưa giải quyết được: lệnh đã chạy, toàn bộ thông báo lỗi, những gì đã thử.
> …
