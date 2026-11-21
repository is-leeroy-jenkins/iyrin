# Architecture

## Application Layers

| Layer | Modules | Responsibility |
|---|---|---|
| Streamlit UI | `app.py`, `realtime.py` | Modes, controls, session state, visualization, and interaction. |
| Geospatial gateway | `mapping.py` | Geocoding, places, distance, time zones, and map operations. |
| Data acquisition | `fetchers.py`, `sources.py`, `loaders.py` | Scientific APIs, Live World providers, web retrieval, documents, and cloud sources. |
| Processing | `processors.py`, `app.py`, `embedders.py` | Parsing, NLP, chunking, embeddings, and orchestration. |
| Persistence | `storage.py`, `history.py`, `stores/sqlite/`, `stores/csv/` | Cache state, Live World history, SQLite, Chroma, and Pinecone. |
| Agent interface | `tools.py` | Provider-neutral JSON-serializable Live World tools. |
| AI generation | `generators.py` | Multi-provider generation and analysis. |
| Configuration | `config.py` | Modes, provider metadata, constants, and credentials. |

## Live World Data Flow

```text
Provider
   │
   ▼
Provider-specific payload
   │
   ▼
GeoEntity normalization
   │
   ├──► Per-source status / stale-state tracking
   ├──► Combined entity frame
   ├──► PyDeck layers
   ├──► Tracking and trails
   ├──► Cross-layer analysis
   ├──► Geofencing
   ├──► Historical Replay
   └──► Agent Tools
```

## Document Processing Flow

```text
Source
  │
  ▼
LangChain Document
  │
  ▼
Recursive chunking
  │
  ▼
Embedding provider
  │
  ▼
Validated vectors
  │
  ├──► Chroma
  └──► Pinecone
```

## State Isolation

Processing state is isolated by mode/source prefix. Documents, chunks, embeddings, embedder state, vector-store state, signatures, and provider/model metadata are not shared accidentally across independent workflows.

## Reliability Boundary

Live World providers refresh independently. Provider failure can retain prior source data marked stale while later providers continue to refresh. Partial or stale refreshes are excluded from new Historical Replay snapshots.
