# Báo cáo kết quả thử nghiệm Hệ thống Memory cho AI Agent

## 1. Kết quả Benchmark

### 1.1. Standard Benchmark (Độ nhớ qua nhiều hội thoại bình thường)
| Agent Name | Agent Tokens Only | Prompt Tokens Processed | Cross-Session Recall | Response Quality | Memory Growth (bytes) | Compactions |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Baseline Agent** | 1446 | 13893 | 7.14% | 7.14% | 0 | 0 |
| **Advanced Agent** | 2671 | 21858 | 100.00% | 100.00% | 244 | 10 |

### 1.2. Long-Context Stress Benchmark (Hội thoại dài vượt ngưỡng)
| Agent Name | Agent Tokens Only | Prompt Tokens Processed | Cross-Session Recall | Response Quality | Memory Growth (bytes) | Compactions |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Baseline Agent** | 242 | 21850 | 0.00% | 0.00% | 0 | 0 |
| **Advanced Agent** | 469 | 9686 | 100.00% | 100.00% | 165 | 28 |

---

## 2. Phân tích kết quả chi tiết (Result Analysis)

### 2.1. Khả năng ghi nhớ thông tin (Cross-Session Recall)
* **Baseline Agent**: Đạt tỷ lệ recall rất thấp (**7.14%** ở hội thoại thường và **0.00%** ở hội thoại dài). Do Baseline chỉ lưu trữ short-term memory nội trong thread đó, nên khi bắt đầu một session hoặc thread mới, nó hoàn toàn quên hết các thông tin cá nhân của người dùng trước đó.
* **Advanced Agent**: Đạt tỷ lệ recall tuyệt đối (**100.00%**) ở cả 2 bài test. Nhờ lớp **Persistent Memory** (`User.md`), các thông tin quan trọng được trích xuất và ghi lại bền vững trên đĩa cứng. Khi có luồng chat mới, agent tải thông tin này vào prompt để phục hồi trí nhớ tức thì.

### 2.2. Trade-off về Token ở hội thoại ngắn (Standard Benchmark)
* Ở hội thoại ngắn, **Advanced Agent** tiêu tốn nhiều prompt tokens hơn (**21858** so với **13893** của Baseline).
* **Nguyên nhân**: Advanced Agent luôn phải gánh thêm chi phí tải thông tin profile từ file `User.md` cũng như các tóm tắt (summary) cũ vào ngữ cảnh ở mỗi đầu lượt chat mới, ngay cả khi hội thoại chưa dài.

### 2.3. Lợi thế vượt trội của Compact Memory ở hội thoại dài (Stress Benchmark)
* Trong Stress Benchmark, tổng lượng prompt tokens của **Advanced Agent** giảm sâu xuống chỉ còn **9686** tokens (so với **21850** của Baseline - giảm hơn **55.7%**).
* **Nguyên nhân**: Lớp **Compact Memory** hoạt động hiệu quả bằng cách nén (compaction) các tin nhắn cũ hơn thành dạng summary khi tổng số tokens vượt quá ngưỡng thiết lập, thực hiện tổng cộng 28 lần nén. Việc nén này giữ cho độ dài lịch sử chat không bị phình to tuyến tính, tối ưu hóa mạnh mẽ chi phí prompt tokens xử lý cho LLM.

### 2.4. Sự tăng trưởng file memory & Rủi ro tiềm ẩn
* **Tăng trưởng file**: Bộ nhớ của Advanced Agent tăng thêm **244 bytes** (Standard) và **165 bytes** (Stress). Tốc độ tăng này khá chậm và ổn định vì chỉ lưu trữ các thực thể / facts dạng key-value đã được chắt lọc kỹ.
* **Rủi ro đi kèm**:
    1. *Lưu thông tin sai lệch*: Nếu người dùng nói đùa hoặc đưa ra thông tin giả định, hệ thống trích xuất kém có thể lưu nhầm vào profile dài hạn.
  2. *Mất chi tiết (Lossy compression)*: Quá trình compact summary có thể làm mất các sắc thái, chi tiết nhỏ hoặc ngữ cảnh cụ thể của hội thoại cũ.
  3. *Phình to lâu dài*: Profile vẫn có thể tăng kích thước vô hạn nếu không có cơ chế dọn dẹp hoặc phai nhạt trí nhớ (memory decay) cho các thông tin đã lỗi thời.

---

## 3. Các Tính Năng Nâng Cao Được Triển Khai (Bonus Features)

### 3.1. Confidence Threshold (Ngưỡng tin cậy trích xuất)
* **Giải quyết vấn đề**: Tránh việc tự động ghi nhận thông tin thiếu độ tin cậy (ví dụ: câu hỏi ngược của người dùng, trò đùa, phủ định hoặc thông tin giả định).
* **Cơ chế hoạt động**: Hàm `extract_profile_updates` trong `memory_store.py` chủ động bỏ qua các lượt thoại có tính chất nghi vấn và chỉ trích xuất các facts kèm theo trọng số tin cậy (Confidence). Chỉ có các thực thể đạt độ tin cậy từ `0.7` trở lên mới được lưu vào bộ nhớ lâu dài.
* **Cải thiện**: Giữ cho profile `User.md` cực kỳ tinh gọn, tránh phình to và hạn chế kéo theo prompt tokens không cần thiết.
* **Rủi ro**: Có thể bỏ sót thông tin thực tế nếu câu nói của người dùng quá lắt léo và bị thuật toán đánh giá dưới ngưỡng `0.7`.

### 3.2. Conflict Handling (Xử lý xung đột thông tin)
* **Giải quyết vấn đề**: Khi người dùng đính chính hoặc thay đổi thông tin (ví dụ: chuyển từ Huế vào Đà Nẵng), agent cần cập nhật thông tin mới nhất và loại bỏ thông tin cũ lỗi thời để tránh mâu thuẫn dữ liệu.
* **Cơ chế hoạt động**: Profile được quản lý dưới dạng cấu trúc Key-Value trong file `User.md` thông qua phương thức `upsert_fact`. Khi nhận diện được khóa trùng lắp (ví dụ: `location`), giá trị mới sẽ tự động ghi đè và xóa bỏ giá trị cũ.
* **Cải thiện**: Giữ cho độ chính xác phản hồi (Cross-Session Recall) đạt mức tối đa 100%, ngăn ngừa việc LLM nhận được thông tin mâu thuẫn trong prompt context.
* **Rủi ro**: Nếu quá trình trích xuất phân loại nhầm thực thể mới vào một Key sẵn có, thông tin đúng cũ sẽ bị ghi đè ngoài ý muốn.
