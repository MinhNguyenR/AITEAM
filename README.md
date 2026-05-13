# 🤖 AI Team 

**Version 6.0** | Enterprise-grade **Multi-Agent Orchestration Framework** designed for high-density systems engineering and massive context management.

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org)
[![Agents](https://img.shields.io/badge/Agents-42_Profiles_%285_Core_Implemented%29-orange)]()
[![Runtime](https://img.shields.io/badge/Engine-aiteamruntime_%28Event--Driven%29-brightgreen)]()
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Status: Development](https://img.shields.io/badge/Status-Phase_3_%2F_In_Progress-red)]()

---

## 📖 Overview

**AI Team** là một hệ thống điều phối Multi-Agent tự trị, tập trung vào việc thu hẹp khoảng cách giữa việc "chat với LLM" và "xây dựng phần mềm thực tế". Thay vì sử dụng một mô hình duy nhất, hệ thống phân rã bài toán thành các tác vụ chuyên biệt, được điều phối bởi một bộ máy vận hành (**aiteamruntime**) dựa trên sự kiện (event-driven).

### Tại sao lại là AI Team?

- 🏗️ **Leader-Coordinated DAG**: Mọi task được lập kế hoạch dưới dạng đồ thị (Directed Acyclic Graph) thông qua artifact `dag.json`, đảm bảo tính minh bạch và khả năng tái lập.
- 🛡️ **Resource Governance**: Hệ thống quản lý tài nguyên nghiêm ngặt với `LockManager` (priority-based) và `PathGuard` để bảo vệ workspace.
- ⚖️ **Tiered Reasoning**: Tự động định tuyến tác vụ qua 3 cấp độ (Low/Medium/High) để tối ưu hóa chi phí và độ trễ:
  - **Low**: `xiaomi/mimo-v2-flash` - Xử lý nhanh, chi phí cực thấp.
  - **Medium**: `deepseek/deepseek-v4-flash` - Cân bằng giữa suy luận và tốc độ.
  - **High**: `x-ai/grok-4.3` - Suy luận sâu cho kiến trúc hệ thống phức tạp.
- 🕹️ **Industrial TUI**: Giao diện dòng lệnh mật độ cao (Rich/Textual) với Command Palette và Dashboard theo dõi chi phí thời gian thực.

---

## 🕹️ Hệ thống Agent (Roster V6.0+)

Hệ thống định nghĩa 42 cấu hình Agent chuyên biệt, với các vai trò cốt lõi hiện đã đi vào vận hành:

| Agent | Tier | Role | Model |
|-------|------|------|-------|
| **Ambassador** | Entry | Phân loại và gác cổng task 
| **Leader High** | High | Lên kiến trúc và điều phối DAG 
| **Leader Low** | Low | Xử lý task nhỏ & hướng dẫn nhanh 
| **Worker** | Exec | Thực thi mã nguồn & viết file 
| **Secretary** | Support | Thao tác Terminal & môi trường 
| **Tool Curator**| Support | Chuẩn bị và kiểm định công cụ 

---

## ✨ Tính năng nổi bật

### 1. aiteamruntime (Event Engine)
Khác với các framework agentic thông thường, `aiteamruntime` giải quyết bài toán tranh chấp tài nguyên khi nhiều agent cùng làm việc:
- **LockManager**: Hỗ trợ `lock_timeout` và ưu tiên tác vụ.
- **Overseer & Self-Repair**: Tự động bắt lỗi Schema JSON và yêu cầu Agent sửa lỗi ngay lập tức.
- **Governor**: Chặn đứng các vòng lặp vô tận (Infinite loops) và kiểm soát độ sâu suy luận.

### 2. Trí nhớ dài hạn (Knowledge Store)
- Tích hợp **GraphRAG** và **SQLite Knowledge Store**.
- Agent truy vấn bối cảnh dự án thông qua biểu đồ tri thức để hiểu mối quan hệ giữa các module trước khi hành động.

### 3. Security & Ops
- **Budget Guard**: Giới hạn chi phí theo phiên (Session) và theo Task.
- **Safe Commit Path**: Mọi thay đổi file đều đi qua quy trình: Hydrate -> Base Hash Validation -> Syntax Check -> Backup -> Commit.
- **Audit Logs**: Lưu vết (Tracing) 100% tư duy và hành động của Agent phục vụ kiểm toán.

---

## 📦 Cài đặt

### Yêu cầu hệ thống
- Python 3.10+
- RAM: Tối thiểu 8GB (Khuyến nghị 16GB+)
- GPU: Tùy chọn (Tự động nhận diện CUDA)

### Các bước thiết lập
```bash
# 1. Clone repository
git clone https://github.com/MinhNguyenR/AITEAM.git
cd ai-team

# 2. Tạo môi trường ảo
python -m venv venv
source venv/bin/activate  # Linux/Mac
# Windows: venv\Scripts\activate

# 3. Cài đặt dependencies
pip install -e .

# 4. Cấu hình API Key
export OPENROUTER_API_KEY="sk-..."
```

---

## 🚀 Khởi chạy

```bash
# Chạy giao diện TUI chính
aiteam

# Chạy runtime server (cho tích hợp web)
aiteamruntime
```


---

## 📈 Trạng thái dự án

Hiện tại dự án đang ở **Phase 3**: Tập trung vào ổn định hóa Pipeline điều phối từ Ambassador -> Leader -> Workers.
- [x] Kiến trúc Event-Driven (Core Stable)
- [x] Hệ thống Registry & Tiered Models
- [x] Leader-Coordinated DAG Logic
- [x] LockManager & Resource Governance
- [/] Worker Optimization (Sửa lỗi & CodeGen)
- [ ] Automated Testing Suite (Partial)

---

## 🤝 Liên hệ & Đóng góp

Dự án được phát triển bởi **Nguyễn Đặng Tường Minh**. Mình rất mong nhận được góp ý về:
- Tối ưu hóa độ trễ (Latency) trong Multi-Agent.
- Quản lý State đa luồng.
- Cải thiện độ chính xác của DAG planning.

- **Github**: [MinhNguyenR/AITEAM](https://github.com/MinhNguyenR/AITEAM)
- **Portfolio**: [nguyendangtuongminh](https://portfolio-1-g7mc.onrender.com/)

---

*Last updated: May 13, 2026*
