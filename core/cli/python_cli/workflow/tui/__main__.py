from .monitor import run_workflow_list_view

if __name__ == "__main__":
    import sys
    project_root = sys.argv[1] if len(sys.argv) > 1 else "."
    run_workflow_list_view(project_root)
