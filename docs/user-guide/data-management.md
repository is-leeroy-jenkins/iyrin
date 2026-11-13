# Data Management

Data Management provides local tabular and persistence workflows.

## Capabilities

- SQLite-backed application data.
- CSV and Excel import/export.
- DataFrame inspection and editing.
- SQL execution.
- Plotly visualization.
- Stored application datasets.
- Local cache implementations.

## Storage

| Component | Purpose |
|---|---|
| `stores/sqlite/` | SQLite persistence. |
| `stores/csv/` | CSV-backed storage. |
| `../../storage.py` | Memory and SQLite cache implementations. |
| `excel.py` | Spreadsheet integration. |
| `stores/vector.py` | Chroma and Pinecone vector storage. |
