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

## Live World Service Classes

`realtime.py` exposes a session-owned `LiveWorld` composition root whose
collaborators encapsulate state, dependency ownership, and business behavior:

| Class | Responsibility |
|---|---|
| `LiveWorldValidation` | Required-argument validation |
| `LiveWorldState` | Streamlit session initialization, sidebar, and clearing |
| `LiveWorldGeometry` | Geographic bounds, coordinate checks, and distances |
| `LiveWorldProviders` | Aircraft, vessel, satellite, USGS, FIRMS, and Overpass acquisition |
| `LiveWorldEntities` | Row extraction and GeoEntity DataFrame normalization |
| `LiveWorldAnalytics` | Measurements, annotations, cross-layer analysis, and geofencing |
| `LiveWorldHistory` | Tracking, history, and replay |
| `LiveWorldRefresh` | Per-provider refresh isolation, status, and stale-data handling |
| `LiveWorldRendering` | PyDeck map rendering and display frame construction |

`LiveWorld` creates and owns one instance of each collaborating service per
Streamlit session, stored under `st.session_state['live_world_controller']`.
Stateful service operations use instance methods and retain a reference to that
session's state mapping; configured provider clients are initialized lazily and
owned by `LiveWorldProviders`. OpenSky OAuth tokens are therefore cached within
the user's session-owned provider instance, rather than on a global cached
resource. Overpass results retain the five-minute Streamlit data-cache behavior.

Only the stateless validation, geometry, and entity-serialization utilities
remain static methods. The previous module-level callable names remain thin
compatibility functions delegating to the active session's service instances.
Those compatibility functions do not constrain the internal class architecture.

NASA FIRMS credentials originate from `cfg.FIRMS_MAP_KEY` in its provider
constructor, where `config.py` resolves `FIRMS_MAP_KEY` or the legacy
`NASA_FIRMS_MAP_KEY` OS variable.

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
