import os
import re
import ast
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
    if file_path.endswith(('.ttf', '.bin', '.exe', '.dll')):
        return 0
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return sum(1 for _ in f)
    except:
        return 0

def extract_dependencies(file_path):
    """Trích xuất tất cả các import từ file Python sử dụng AST để đảm bảo chính xác."""
    deps = set()
    if not file_path.endswith('.py'):
        return deps
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            tree = ast.parse(f.read(), filename=file_path)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        deps.add(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        # Kết hợp module và names nếu cần chi tiết hơn, 
                        # nhưng ở đây lấy module path là đủ để thấy connection
                        deps.add(node.module)
    except Exception:
        # Fallback to regex if AST fails (e.g. syntax error in file)
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                matches = re.findall(r'^(?:from|import)\s+([\w\.]+)', content, re.MULTILINE)
                for m in matches:
                    deps.add(m)
        except:
            pass
    return deps

def generate_tree(startpath):
    """Tạo cây thư mục, thống kê file/lines và bản đồ dependency."""
    tree_lines = []
    total_files = 0
    total_loc = 0
    all_deps = {}

    for root, dirs, files in os.walk(startpath):
        dirs[:] = sorted([d for d in dirs if d not in EXCLUDE_DIRS])
        rel_root = os.path.relpath(root, startpath)
        
        if rel_root == ".":
            top_files = sorted([f for f in files if f.endswith(INCLUDE_EXTS) and f not in EXCLUDE_FILES])
            for f in top_files:
                loc = get_line_count(os.path.join(root, f))
                tree_lines.append(f"|-- {f} ({loc} lines)")
                total_files += 1
                total_loc += loc
            continue

        level = rel_root.count(os.sep)
        indent = "|   " * level
        tree_lines.append(f"{indent}|-- {os.path.basename(root)}/")
        
        sub_indent = "|   " * (level + 1)
        valid_files = sorted([f for f in files if f.endswith(INCLUDE_EXTS) and f not in EXCLUDE_FILES])
        
        for i, f in enumerate(valid_files):
            file_path = os.path.join(root, f)
            loc = get_line_count(file_path)
            total_files += 1
            total_loc += loc
            
            prefix = "\\-- " if i == len(valid_files) - 1 else "|-- "
            if loc > 0:
                tree_lines.append(f"{sub_indent}{prefix}{f} ({loc} lines)")
            else:
                tree_lines.append(f"{sub_indent}{prefix}{f} (binary/0 lines)")
            
            if f.endswith('.py'):
                f_deps = extract_dependencies(file_path)
                if f_deps:
                    rel_f_path = os.path.relpath(file_path, startpath)
                    all_deps[rel_f_path] = sorted(list(f_deps))

    return tree_lines, total_files, total_loc, all_deps

def update_memory_md():
    """Hàm chính: tạo báo cáo và ghi vào memory.md."""
    print("Generating tree and extracting all dependencies...")
    tree_lines, total_files, total_loc, dep_map = generate_tree(PROJECT_ROOT)
    
    old_content = ""
    if os.path.exists(MEMORY_MD_PATH):
        with open(MEMORY_MD_PATH, 'r', encoding='utf-8') as f:
            old_content = f.read()

    now = datetime.now().strftime("%Y-%m-%d")
    
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
    output.extend(tree_lines)
    output.extend(["```", ""])

    output.append("## Connections (Dependency Map)")
    output.append("")
    # Hiển thị tất cả connections từ tất cả các file Python
    for f_path, deps in sorted(dep_map.items()):
        output.append(f"- **{f_path}**")
        for d in deps:
            output.append(f"  - imports {d}")
    output.append("")

    output.append("## Session Summaries")
    output.append("")
    
    # Phase 4
    output.append("### 4. Industrial AI Agentic Refactoring (Completed)")
    output.append("- **UI**: Detailed diffs with context windows (+green/-red) in `_update_state.py`.")
    output.append("- **Architecture**: Standardized slash-commands (`/back`, `/exit`, `/accept`, etc.) via `command_parser.py`.")
    output.append("- **Security**: `core/sandbox/` executor with allowlist policy for Worker/Secretary.")
    output.append("- **Efficiency**: Lazy-loading `core.storage` exports via `__getattr__` to minimize import side-effects.")
    output.append("- **Robustness**: UTF-8 `errors=\"replace\"` in `safe_read.py\" for all TUI file viewing.")
    output.append("- **Roster**: Automated Worker roster in Leader prompts; `restore_worker` node for backup recovery.")
    output.append("")

    # Trích xuất các tóm tắt cũ
    summaries = re.findall(r'(### [1-3]\..+?)(?=### |\Z)', old_content, re.DOTALL)
    for s in summaries:
        output.append(s.strip())
        output.append("")

    with open(MEMORY_MD_PATH, 'w', encoding='utf-8') as f:
        f.write("\n".join(output))
    
    print(f"Success! Updated {MEMORY_MD_PATH}")
    print(f"Stats: {total_files} files | {total_loc} lines.")

if __name__ == "__main__":
    print("Redoing Codebase Index...")
    update_memory_md()
    print("Done.")