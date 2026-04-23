# Standalone GraphRAG

A repository-root GraphRAG index that is independent from the project code.

## Commands

```bash
python -m graphrag_standalone --root . rebuild
python -m graphrag_standalone --root . search "sqlite fts"
python -m graphrag_standalone --root . search-files "indexer"
python -m graphrag_standalone --root . search-modules "core storage"
python -m graphrag_standalone --root . search-symbols "GraphRAGStandalone"
python -m graphrag_standalone --root . find-usage "build_project_map"
python -m graphrag_standalone --root . tree --depth 3
python -m graphrag_standalone --root . summary --output PROJECT_SUMMARY.md
python -m graphrag_standalone --root . project-map --output PROJECT_MAP.md
python -m graphrag_standalone --root . inspect
```

## Storage

The index lives in `./.graphrag/graphrag.sqlite` under the repository root.

## Outputs

- `PROJECT_MAP.md` — generated architecture summary and project map at repo root
- `PROJECT_SUMMARY.md` — optional summary export
