import os
import re
from datetime import datetime

# --- Cấu hình ---
# Đường dẫn gốc của dự án (đường dẫn tuyệt đối trên Windows)
PROJECT_ROOT = r"d:\Profolio\Programming Language\Python\AI\ML\DL\Research\AI Agentic\ai-team"
# Đường dẫn tới file memory.md sẽ được cập nhật
MEMORY_MD_PATH = os.path.join(PROJECT_ROOT, "docs", "notes", "memory.md")

# Các thư mục cần loại trừ khi duyệt cây thư mục
EXCLUDE_DIRS = {
    '.git', 'venv', '.venv', 'node_modules', '__pycache__', 
    '.pytest_cache', '.idea', '.vscode', 'aiteam.egg-info', 
    'build', 'dist', '.ruff_cache', '.claude'
}
# Các file cụ thể cần loại trừ
EXCLUDE_FILES = {'.DS_Store', '.env', '.coverage', 'package-lock.json'}
# Các phần mở rộng file cần bao gồm trong thống kê
INCLUDE_EXTS = ('.py', '.md', '.txt', '.yml', '.yaml', '.json', '.toml', '.ttf')

# --- Logic ---

def get_line_count(file_path):
    """Đếm số dòng trong file, trả về 0 cho file nhị phân hoặc lỗi."""
    # Bỏ qua các loại file nhị phân phổ biến
    if file_path.endswith(('.ttf', '.bin', '.exe', '.dll')):
        return 0
    try:
        # Mở file với encoding UTF-8, bỏ qua lỗi giải mã
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return sum(1 for _ in f)  # Đếm số dòng
    except:
        return 0  # Trả về 0 nếu có lỗi (ví dụ: quyền truy cập)

def extract_dependencies(file_path):
    """Trích xuất các dependency cấp cao nhất từ file Python (chỉ core, agents, utils)."""
    deps = set()
    # Chỉ xử lý file Python
    if not file_path.endswith('.py'):
        return deps
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            # Tìm các dòng import/from bằng regex (bắt đầu dòng)
            matches = re.findall(r'^(?:from|import)\s+([\w\.]+)', content, re.MULTILINE)
            for m in matches:
                # Lấy gói gốc (phần trước dấu chấm đầu tiên)
                root_pkg = m.split('.')[0]
                # Chỉ quan tâm đến các gói nội bộ cụ thể
                if root_pkg in ('core', 'agents', 'utils'):
                    deps.add(root_pkg)
    except:
        pass  # Bỏ qua lỗi đọc file
    return deps

def generate_tree(startpath):
    """Tạo cây thư mục, thống kê file/lines và bản đồ dependency."""
    tree_lines = []  # Lưu các dòng mô tả cây thư mục
    total_files = 0  # Tổng số file đã đếm
    total_loc = 0    # Tổng số lines of code
    all_deps = {}    # Bản đồ dependency: {relative_path: [deps]}

    # Duyệt cây thư mục theo thứ tự nhất quán (sắp xếp)
    for root, dirs, files in os.walk(startpath):
        # Loại trừ thư mục không cần thiết và sắp xếp
        dirs[:] = sorted([d for d in dirs if d not in EXCLUDE_DIRS])
        rel_root = os.path.relpath(root, startpath)  # Đường dẫn tương đối từ startpath
        
        # Xử lý thư mục gốc (level 0)
        if rel_root == ".":
            top_files = sorted([f for f in files if f.endswith(INCLUDE_EXTS) and f not in EXCLUDE_FILES])
            for f in top_files:
                loc = get_line_count(os.path.join(root, f))
                tree_lines.append(f"|-- {f} ({loc} lines)")  # Định dạng cây
                total_files += 1
                total_loc += loc
            continue  # Chuyển sang thư mục con

        # Tính mức độ lồng nhau để thụt lề
        level = rel_root.count(os.sep)
        indent = "|   " * level
        tree_lines.append(f"{indent}|-- {os.path.basename(root)}/")  # Thêm thư mục vào cây
        
        sub_indent = "|   " * (level + 1)  # Thụt lề cho file con
        valid_files = sorted([f for f in files if f.endswith(INCLUDE_EXTS) and f not in EXCLUDE_FILES])
        
        for i, f in enumerate(valid_files):
            file_path = os.path.join(root, f)
            loc = get_line_count(file_path)
            total_files += 1
            total_loc += loc
            
            # Xác định prefix: "\\-- " cho file cuối cùng, "|-- " cho các file còn lại
            prefix = "\\-- " if i == len(valid_files) - 1 else "|-- "
            if loc > 0:
                tree_lines.append(f"{sub_indent}{prefix}{f} ({loc} lines)")  # File có mã nguồn
            else:
                # File nhị phân hoặc rỗng
                tree_lines.append(f"{sub_indent}{prefix}{f} (binary/0 lines)")
            
            # Trích xuất dependency cho file Python
            if f.endswith('.py'):
                f_deps = extract_dependencies(file_path)
                if f_deps:
                    rel_f_path = os.path.relpath(file_path, startpath)
                    all_deps[rel_f_path] = sorted(list(f_deps))  # Lưu bản đồ dependency

    return tree_lines, total_files, total_loc, all_deps

def update_memory_md():
    """Hàm chính: tạo báo cáo và ghi vào memory.md."""
    print("Generating tree...")
    # Tạo cây thư mục, thống kê và bản đồ dependency
    tree_lines, total_files, total_loc, dep_map = generate_tree(PROJECT_ROOT)
    
    # Đọc nội dung cũ để giữ lại phần lịch sử (Session Summaries)
    old_content = ""
    if os.path.exists(MEMORY_MD_PATH):
        with open(MEMORY_MD_PATH, 'r', encoding='utf-8') as f:
            old_content = f.read()

    now = datetime.now().strftime("%Y-%m-%d")  # Ngày hiện tại
    
    # Xây dựng nội dung output
    output = [
        "# Codebase Memory",
        "",
        f"**Last Updated:** {now}",
        f"**Total Files:** {total_files}",
        f"**Total Lines of Code:** {total_loc}",
        "",
        "## Structure",
        "```text"
    ]
    output.extend(tree_lines)  # Thêm cây thư mục
    output.extend(["```", ""])  # Đóng khối mã

    output.append("## Connections (Dependency Map)")
    output.append("")
    # Chỉ tập trung vào các thư mục quan trọng để hiển thị dependency
    interesting_folders = ('core/cli', 'agents', 'core/orchestration')
    for f_path, deps in sorted(dep_map.items()):
        if any(f_path.startswith(folder) for folder in interesting_folders):
            output.append(f"- **{f_path}**")
            for d in deps:
                output.append(f"  - imports {d}")  # Mỗi dependency trên một dòng
    output.append("")

    output.append("## Session Summaries")
    output.append("")
    
    # Thêm tómắt phiên làm việc mới nhất (Phase 4)
    output.append("### 4. Industrial AI Agentic Refactoring (Completed)")
    output.append("- **UI**: Detailed diffs with context windows (+green/-red) in `_update_state.py`.")
    output.append("- **Architecture**: Standardized slash-commands (`/back`, `/exit`, `/accept`, etc.) via `command_parser.py`.")
    output.append("- **Security**: `core/sandbox/` executor with allowlist policy for Worker/Secretary.")
    output.append("- **Efficiency**: Lazy-loading `core.storage` exports via `__getattr__` to minimize import side-effects.")
    output.append("- **Robustness**: UTF-8 `errors=\"replace\"` in `safe_read.py\" for all TUI file viewing.")
    output.append("- **Roster**: Automated Worker roster in Leader prompts; `restore_worker` node for backup recovery.")
    output.append("")

    # Trích xuất và giữ lại các tómắt phiên cũ (từ Phase 1-3)
    summaries = re.findall(r'(### [1-3]\..+?)(?=### |\Z)', old_content, re.DOTALL)
    for s in summaries:
        output.append(s.strip())
        output.append("")

    # Ghi nội dung mới vào file memory.md
    with open(MEMORY_MD_PATH, 'w', encoding='utf-8') as f:
        f.write("\n".join(output))
    
    print(f"Success! Updated {MEMORY_MD_PATH}")
    print(f"Stats: {total_files} files | {total_loc} lines.")

if __name__ == "__main__":
    print("Redoing Codebase Index...")
    update_memory_md()
    print("Done.")