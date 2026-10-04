# Submission — Day 19 Knowledge Graph

## 1. Nộp gì

Repo GitHub **cá nhân**, đặt tên `K4-DAY19-HoVaTen-MSSV`. Nộp link repo lên vlearn.

```
K4-DAY19-HoVaTen-MSSV/
├── src/graph.py                 ← đã hoàn thành KG-1..KG-4
├── ket_qua_benchmark_kg.txt     ← output của: python bench_kg.py --judge
└── report/
    ├── REPORT_KG.md             ← điền theo template có sẵn
    └── img/
        ├── kg_count.png         ← truy vấn Q-A (LAB_GUIDE 7.1)
        ├── kg_cross_kb.png      ← truy vấn Q-B (LAB_GUIDE 7.1)
        └── kg_my_case.png       ← truy vấn Q-D với người bạn tự chọn
```

**Không** được có trong repo: `.env`, API key ở bất kỳ file nào, `.venv/`.

## 2. Kỳ vọng đầu ra

### Code

| Lệnh | Kỳ vọng |
| --- | --- |
| `pytest tests/ -q` | `50 passed` (41 base + 9 graph) |
| `python bench_kg.py --check` | 7 dòng `[OK]`, không có `[LỖI …]` |

### Benchmark (`ket_qua_benchmark_kg.txt`)

- Chạy **với** `--judge`, đủ 3 phần: `Indexing`, `Querying`, `Per question`.
- File **sinh ra từ code của bạn**: số node/rel ở dòng đầu, số chunk, số liệu phải khớp với báo cáo.
- Kỳ vọng định tính: trên các câu `cross-kb`, GraphRAG có `recall` cao hơn Flat RAG. Không đạt thì vẫn nộp, nhưng báo cáo phải giải thích vì sao.

### Báo cáo (`report/REPORT_KG.md`)

| Mục | Kỳ vọng tối thiểu | Bài tốt thường có thêm |
| --- | --- | --- |
| 1. Chi phí | 2 bảng copy từ file kết quả; tỉ lệ Graph/Flat cho indexing và mỗi câu hỏi | Tách được chi phí tăng thêm đến từ đâu (trích xuất? prompt dài hơn?), ước tính điểm hòa vốn theo số câu hỏi |
| 2. Từng câu | Bảng Q1–Q6: recall, judge, bên thắng, 1 câu lý do | Liên hệ "loại câu hỏi" với "bên thắng" thành một quy luật |
| 3. Phân tích lỗi | ≥ 2 nhóm lỗi trong E1–E6, mỗi lỗi đủ 4 phần: hiện tượng, bằng chứng, nguyên nhân, đề xuất sửa | Sửa thật và có số liệu trước/sau; chỉ ra lỗi nằm ở bước nào của pipeline |
| 4. Kết luận | Khi nào nên dùng KG, khi nào Flat RAG đủ, dẫn số liệu của mình | Nêu điều kiện cụ thể (loại dữ liệu, loại câu hỏi, số lượng câu hỏi) |
| 5. Tự kiểm | Dán output `pytest` và `--check` | |

**Bằng chứng** nghĩa là người chấm đọc vào kiểm chứng được: trích nguyên văn câu trả lời (ghi rõ câu Qx, pipeline nào), hoặc Cypher kèm kết quả trả về. Câu như "graph có vẻ bị trùng node" mà không kèm truy vấn thì **không** tính là bằng chứng.

## 3. Thang điểm (100)

| # | Hạng mục | Điểm | Cách chấm |
| --- | --- | --- | --- |
| 1 | KG-1, KG-2, KG-3 | 15 | `pytest tests/test_graph.py`: 9 test, mỗi test fail trừ 2 điểm (tối thiểu 0) |
| 2 | KG-4 | 15 | `--check` đủ 7 `[OK]` → 10. Câu trả lời `cross-kb` của GraphRAG có nêu số Điều luật → +5 |
| 3 | Base không bị phá | 5 | `pytest tests/test_base.py` → `41 passed` |
| 4 | File benchmark hợp lệ | 10 | Đủ 3 phần, có `judge`, khớp số liệu báo cáo |
| 5 | Báo cáo mục 1: Chi phí | 10 | |
| 6 | Báo cáo mục 2: Từng câu | 10 | |
| 7 | Báo cáo mục 3: Phân tích lỗi | 20 | 10 điểm/lỗi, tối đa 2 lỗi. Thiếu bằng chứng: tối đa 3/10 cho lỗi đó |
| 8 | Báo cáo mục 4: Kết luận | 5 | Có dẫn số liệu → đủ điểm; chỉ nêu cảm tính → tối đa 2 |
| 9 | 3 ảnh Neo4j | 5 | Đúng quy cách ở LAB_GUIDE Bước 7: thấy ô truy vấn và Results overview, kết quả giống dạng ảnh mẫu trong LAB_GUIDE 7.1. Thiếu hoặc sai mỗi ảnh trừ 2 điểm |
| 10 | Báo cáo mục 5: Tự kiểm | 5 | Output khớp với repo khi người chấm chạy lại |
| + | **Điểm cộng**: sửa lỗi thật, có số liệu trước/sau | +10 | Tổng không vượt 100 |

### Trừ điểm và điểm liệt

| Vi phạm | Hậu quả |
| --- | --- |
| Commit `.env` hoặc API key (kể cả đã xóa ở commit sau, vì vẫn còn trong lịch sử git) | **−20** và phải thu hồi key ngay |
| Số liệu trong báo cáo không khớp `ket_qua_benchmark_kg.txt`, hoặc không có file này | Mục 1, 2, 4 của báo cáo = **0** |
| File benchmark không sinh từ code trong repo (sửa tay, chép của người khác) | Mục 4 và mục 1, 2, 4 của báo cáo = **0** |
| Sửa test hoặc `bench_kg.py --check` để test pass | Hạng mục 1–3 = **0** |
| Báo cáo giống bài khác | Cả hai bài = **0** phần báo cáo |

## 4. Checklist trước khi nộp

```bash
pytest tests/ -q                   # 50 passed
python bench_kg.py --check         # 7 [OK]
python bench_kg.py --judge         # sinh lại ket_qua_benchmark_kg.txt từ code cuối cùng
git status                         # .env KHÔNG được xuất hiện
git log --all -p | grep "sk-"      # PHẢI không ra gì
```

- [ ] `src/graph.py` không còn `raise NotImplementedError`
- [ ] `ket_qua_benchmark_kg.txt` có cột `judge` khác `-`
- [ ] `report/REPORT_KG.md` đủ 5 mục, số liệu khớp file kết quả
- [ ] Phân tích ít nhất 2 lỗi, mỗi lỗi có bằng chứng
- [ ] Có 3 ảnh trong `report/img/`, mỗi ảnh thấy được ô truy vấn
- [ ] Repo tên `K4-DAY19-HoVaTen-MSSV`, đã push, link đã nộp lên vlearn
- [ ] Đã tắt Neo4j nếu không dùng nữa: `docker stop neo4j-drug-kg`
