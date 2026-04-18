# 🧠 Dự án: ai-team - Báo cáo Tình trạng Mã nguồn
**Ngày cập nhật:** 11/04/2026

**Ghi chú kỹ thuật:** `core/cli/workflow/runner_live.py` đã gộp vào `runner.py` — import duy nhất: `from core.cli.workflow.runner import run_agent_graph, resume_workflow, ...`.

## 📊 Tổng quan tiến độ
- **Tổng số file nguồn (.py):** ~62 file (bao gồm các module phụ trợ mới)
- **Đã hoàn thành (Có code):** ~48 file
- **Còn trống (0 bytes):** ~14 file
- **Tỷ lệ hoàn thành:** ~77% (Tăng từ 70% nhờ bổ sung hệ thống Config, Workflow và Utils mới)

## 📂 Chi tiết từng thư mục

### 🤖 1. Agents (Đại lý)
| Tên file | Trạng thái | Vai trò & Hàm chính |
| :--- | :--- | :--- |
| `base_agent.py` | ✅ Hoàn thành | Lớp cơ sở trừu tượng. Hàm: `brain`, `search_knowledge`, `save_knowledge`, `call_api`, `_estimate_cost`, `_check_budget`, `read_project_file`, `log_action`, `execute` |
| `ambassador.py` | ✅ Hoàn thành | Phân tích yêu cầu ban đầu. Hàm: `parse`, `parse_to_dict`, `get_tier_info`, `execute`, `format_output` |
| `expert.py` | ✅ Hoàn thành | Lập kế hoạch chuyên sâu. Hàm: `generate_context`, `validate_plan`, `_apply_revisions`, `execute` |
| `leader.py` | ✅ Hoàn thành | Điều phối và tạo ngữ cảnh. Gồm các lớp: `LeaderLow`, `LeaderMed`, `LeaderHigh`. Hàm: `generate_context`, `_build_prompt`, `execute` |
| `teamMap/_team_map.py`| ✅ Hoàn thành | Định nghĩa đồ thị LangGraph điều phối agents. Hàm: `route_entry`, `node_leader_generate`, `node_expert_solo`, `node_expert_coplan`, `get_graph` |
| `browser.py` | ❌ Còn trống | Dự kiến: Duyệt web và thu thập thông tin |
| `commander.py` | ❌ Còn trống | Dự kiến: Điều khiển và ra lệnh cấp cao |
| `final_reviewer.py`| ❌ Còn trống | Dự kiến: Kiểm duyệt kết quả cuối cùng |
| `fix_worker.py` | ❌ Còn trống | Dự kiến: Sửa lỗi mã nguồn tự động |
| `researcher.py` | ❌ Còn trống | Dự kiến: Nghiên cứu và tìm kiếm thông tin |
| `reviewer.py` | ❌ Còn trống | Dự kiến: Đánh giá mã nguồn hoặc kế hoạch |
| `secretary.py` | ❌ Còn trống | Dự kiến: Ghi chép và quản lý dữ liệu phụ trợ |
| `test_agent.py` | ❌ Còn trống | Dự kiến: Tự động tạo và chạy test |
| `tool_curator.py` | ❌ Còn trống | Dự kiến: Quản lý và lựa chọn công cụ (tool) |
| `worker.py` | ❌ Còn trống | Dự kiến: Thực hiện các tác vụ generic |

### 🧠 2. Core (Lõi hệ thống)
| Tên file | Trạng thái | Vai trò & Hàm chính |
| :--- | :--- | :--- |
| `dashboard.py` | ✅ Hoàn thành | Hiển thị thông số hệ thống. Hàm: `render_token_usage`, `show_dashboard` |
| `pipeline_state.py`| ✅ Hoàn thành | Quản lý trạng thái luồng. Hàm: `write_task_state_json`, `leader_generate_context` |
| `prompts.py` | ✅ Hoàn thành | Lưu trữ các mẫu prompt. Hàm: `build_leader_low/med/high_prompt`, `build_expert_solo/coplan_prompt` |
| `routing_map.py` | ✅ Hoàn thành | Bản đồ điều hướng giữa các Agent. Hàm: `pipeline_registry_key_for_tier`, `selected_leader_for_tier` |
| `orchestrator.py` | ❌ Còn trống | Dự kiến: Bộ điều phối luồng chính |
| `skills.py` | ❌ Còn trống | Dự kiến: Danh mục kỹ năng của Agents |

### 🖥️ 3. Core/CLI (Giao diện dòng lệnh)
| Tên file | Trạng thái | Vai trò & Hàm chính |
| :--- | :--- | :--- |
| `app.py` | ✅ Hoàn thành | Điểm vào chính của CLI. Hàm: `cli`, `start`, `check`, `status`, `info`, `workflow_cmd` |
| `ask_flow.py` | ✅ Hoàn thành | Chế độ chat trực tiếp. Hàm: `run_ask_mode`, `_handle_ask_show_command`, `_ask_model` |
| `change_flow.py` | ✅ Hoàn thành | Quy trình thay đổi/edit file. Hàm: `run_change_mode`, `_apply_diff` |
| `choice_lists.py` | ✅ Hoàn thành | Các danh sách lựa chọn cho menu UI |
| `context_flow.py` | ✅ Hoàn thành | Quản lý quy trình duyệt Context. Hàm: `show_context`, `confirm_context`, `ContextApp` |
| `palette.py` | ✅ Hoàn thành | Thành phần UI bảng màu lệnh (Command Palette) |
| `settings_flow.py`| ✅ Hoàn thành | Cấu hình cài đặt. Hàm: `show_settings` |
| `start_flow.py` | ✅ Hoàn thành | Khởi chạy workflow. Hàm: `run_start` |
| `state.py` | ✅ Hoàn thành | Lưu trữ trạng thái phiên CLI. Hàm: `load_cli_settings`, `save_context_state`, `log_system_action` |
| `ui.py` | ✅ Hoàn thành | Tiện ích giao diện: `clear_screen`, `print_header`, `print_divider` |

### 🌊 4. Core/CLI/Workflow (Giám sát luồng)
| Tên file | Trạng thái | Vai trò & Hàm chính |
| :--- | :--- | :--- |
| `monitor.py` | ✅ Hoàn thành | TUI giám sát luồng (Textual). Hàm: `WorkflowMonitorApp`, `_refresh_views` |
| `runner.py` | ✅ Hoàn thành | Chạy đồ thị Agent. Hàm: `run_agent_graph`, `spawn_workflow_monitor` |
| `session.py` | ✅ Hoàn thành | Đồng bộ trạng thái UI & Workflow. Gồm `WorkflowSession` quản lý realtime status |
| `activity_log.py` | ✅ Hoàn thành | Quản lý log hoạt động của workflow. Hàm: `append_workflow_activity`, `get_workflow_activity` |
| `checkpointer.py` | ✅ Hoàn thành | Bộ lưu vết/checkpoint cho LangGraph. `AITeamCheckpointer` |
| `display_policy.py`| ✅ Hoàn thành | Chính sách hiển thị thông tin log lên UI |
| `list_view.py` | ✅ Hoàn thành | Component danh sách hiển thị các bước workflow |

### ⚙️ 5. Core/Config (Cấu hình hệ thống)
| Tên file | Trạng thái | Vai trò & Hàm chính |
| :--- | :--- | :--- |
| `constants.py` | ✅ Hoàn thành | Định nghĩa các hằng số hệ thống (VERSION, CACHE_DIR, etc.) |
| `hardware.py` | ✅ Hoàn thành | Tự động phát hiện phần cứng (VRAM/CUDA). Hàm: `get_vram_info`, `is_cuda_available` |
| `pricing.py` | ✅ Hoàn thành | Quản lý giá model OpenRouter. Lớp `PricingManager` |
| `registry.py` | ✅ Hoàn thành | Đăng ký các Model & Agent Worker. `ModelRegistry` |
| `service.py` | ✅ Hoàn thành | Trung tâm điều phối dịch vụ. Hàm: `ServiceProvider`, `get_model_for_tier` |
| `settings.py` | ✅ Hoàn thành | Xử lý cài đặt người dùng (JSON/Env). `AI_TEAM_SETTINGS` |

### 🗄️ 6. Core/Storage (Lưu trữ dữ liệu)
| Tên file | Trạng thái | Vai trò & Hàm chính |
| :--- | :--- | :--- |
| `ask_chat_store.py`| ✅ Hoàn thành | Lưu trữ chat SQLite. Hàm: `create_conversation`, `append_message`, `ConversationStore` |
| `knowledge_store.py`| ✅ Hoàn thành | Kho tri thức (Compressed Brain). Hàm: `store`, `retrieve`, `smart_search`, `KnowledgeStore` |

### 🛠️ 7. Utils (Tiện ích)
| Tên file | Trạng thái | Vai trò & Hàm chính |
| :--- | :--- | :--- |
| `ask_history.py` | ✅ Hoàn thành | Quản lý lịch sử chat. Hàm: `load_store`, `create_chat`, `append_message` |
| `env_guard.py` | ✅ Hoàn thành | Kiểm tra môi trường & bảo mật. Hàm: `run_startup_checks`, `redact_for_display` |
| `tracker.py` | ✅ Hoàn thành | Theo dõi chi phí & token OpenRouter. Hàm: `fetch_wallet`, `compute_cost_usd`, `get_dashboard_summary` |
| `delta_brief.py` | ✅ Hoàn thành | Hợp đồng artifact pipeline. Lớp `DeltaBrief`, hàm `build_state_payload` |
| `file_manager.py` | ✅ Hoàn thành | Quản lý file/cache sandbox. Hàm: `get_cache_root`, `path_under_cache`, `ensure_run_dir` |
| `activity_badges.py`| ✅ Hoàn thành | Tiện ích hiển thị huy hiệu (badges) trên UI TUI |
| `budget_guard.py` | ✅ Hoàn thành | Bảo vệ ngân sách (Budget guard) tránh chi tiêu vượt mức |
| `logger.py` | ✅ Hoàn thành | Hệ thống logging sự kiện workflow. Hàm: `workflow_event`, `system_event` |
| `free_model_finder.py`| ❌ Còn trống | Dự kiến: Tự động tìm model miễn phí |

## 📝 Ghi chú Memory
Dự án **ai-team** đã có sự tiến bộ lớn so với báo cáo trước:
1. **Kiến trúc Config & Hardware:** Đã tách bạch rõ ràng cấu hình phần cứng, giá cả và đăng ký model, giúp hệ thống linh hoạt hơn.
2. **Hệ thống Workflow Monitor:** Đã hoàn thiện bộ TUI giám sát luồng với `monitor.py`, `activity_log.py` và `session.py` hỗ trợ real-time.
3. **Quản lý thay đổi:** Thêm `change_flow.py` hỗ trợ áp dụng code edits.
4. **Tiện ích mở rộng:** Bổ sung `budget_guard`, `activity_badges` và `logger` chuyên dụng cho workflow.

**Cần tập trung tiếp theo:**
- Hiện thực hóa các Agent trống (`browser`, `researcher`, `fix_worker`).
- Xây dựng `orchestrator` để kết nối logic lõi thay vì gọi gián tiếp.
- Hoàn thiện `free_model_finder.py` để tối ưu chi phí cho các tác vụ đơn giản.
- Mở rộng `skills.py` để định nghĩa khả năng của từng agent một cách rõ ràng.
