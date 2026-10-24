###### iyrin

![](https://github.com/is-leeroy-jenkins/iyr/blob/main/resources/images/iyrin-project.png)

<p align="left">
  <a href="#core-capabilities">Core Capabilities</a>
  &nbsp;&bull;&nbsp;
  <a href="#application-modes">Application Modes</a>
  &nbsp;&bull;&nbsp;
  <a href="#live-world-data">Live World</a>
  &nbsp;&bull;&nbsp;
  <a href="#ai--ml-functionality">AI / ML</a>
  &nbsp;&bull;&nbsp;
  <a href="#scientific--operational-data-sources">Data Sources</a>
  &nbsp;&bull;&nbsp;
  <a href="resources/installation.md">Installation</a>
  &nbsp;&bull;&nbsp;
  <a href="#configuration">Configuration</a>
  &nbsp;&bull;&nbsp;
  <a href="#project-structure">Project Structure</a>
  &nbsp;&bull;&nbsp;
  <a href="#requirements">Requirements</a>
  &nbsp;&bull;&nbsp;
  <a href="#license">License</a>
</p>

___

[![Documentation](https://img.shields.io/badge/docs-GitHub%20Pages-0078FC?style=for-the-badge&logo=github)](https://is-leeroy-jenkins.github.io/Iyrin/)


Iyrin is a Streamlit-based geospatial, scientific-data, document-processing, and agentic-analysis application. It combines mapping services, environmental and scientific APIs, live-world operational data, document chunking, embeddings, vector storage, geospatial analytics, and provider-neutral tool interfaces in a single application.

<a id="core-capabilities"></a>

## ✨ Core Capabilities

| Capability             | Functionality                                                                                                                                                      |
|------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| 🧭 Mapping Tools       | Geocoding, distance and travel-time calculations, coordinate-based time-zone resolution, and static map generation in one workflow. |
| 🗺️ Interactive Mapping | Interactive geospatial visualization using PyDeck and configurable map styles.                                                                                     |
| 🌐 Site Crawling       | Web retrieval and crawling for text/document acquisition.                                                                                                          |
| 🌦️ Weather             | Current, forecast, historical, and climate-oriented weather retrieval.                                                                                             |
| 🌱 Environmental       | Air quality, UV, environmental records, active-fire, water, and natural-event data.                                                                                |
| 🌎 Geological          | Earthquake, water, terrain, and geospatial science data.                                                                                                           |
| 🔭 Astronomical        | Astronomical catalogs, solar/space-weather data, satellite data, and astronomy tooling.                                                                            |
| 🌌 Celestial Mapping   | Star-map and celestial visualization functionality.                                                                                                                |
| 📄 Data Upload         | File ingestion and processing for supported structured and document formats.                                                                                       |
| 🗄️ Data Management     | Local application data and persistence workflows.                                                                                                                  |
| 🧠 AI/ML Processing    | Chunking, embeddings, vector stores, retrieval-ready document preparation, and agent-callable geospatial tools.                                                    |
| 🌐 Live World Data     | Aircraft, military aircraft, satellites, vessels, fires, earthquakes, infrastructure, cameras, map layers, tracking, geofencing, replay, and cross-layer analysis. |



Live World Data extends Iyrin with a normalized operational geospatial layer built around the `GeoEntity` contract. Heterogeneous providers are converted into a common schema containing entity identity, type, name, latitude, longitude, altitude, heading, speed, timestamp, source, and provider-specific metadata.

<a id="application-modes"></a>

### 🕹️ Application Modes

| Mode | Purpose | Major Components |
|------|---------|------------------|
| **Mapping Tools** | Resolve locations and perform direct geospatial utility operations. | Geocoding, place lookup, distance and travel-time calculations, coordinate-based time zones, and static maps. |
| **Interactive Map** | Explore interactive geographic and operational data on a shared map surface. | PyDeck mapping, configurable map styles, Live World layers, tracking, measurements, cross-layer analysis, geofencing, replay, and Agent Tools. |
| **Site Crawler** | Retrieve and inspect web content from individual pages or recursive crawls. | HTTP/web retrieval, Crawl4AI, BeautifulSoup extraction, links, text, HTML, and document preparation. |
| **Document Data** | Load document-oriented and public information sources for inspection and processing. | Text and document loaders, arXiv, Wikipedia, GitHub, cloud files, corpora, chunking, embeddings, and vector storage. |
| **Geoscience Data** | Retrieve geographic, weather, climate, environmental, water, fire, and earth-science information. | Google Weather, Open-Meteo, NOAA, EPA, NASA, USGS, OpenSky, mapping, and environmental APIs. |
| **Astronomical Data** | Query astronomical catalogs, orbital data, solar/space-weather sources, and related scientific services. | Astroquery, SIMBAD, CelesTrak, near-Earth objects, satellite data, space weather, and U.S. Naval Observatory data. |
| **Celestial Map** | Render and interact with star and sky visualizations. | Star charts, coordinate/object charts, configurable rendering controls, and What's Up Tonight interactions. |
| **Public Health** | Retrieve demographic, population, biomedical, and public-health data. | U.S. Census, CDC Socrata, CDC WONDER, HHS, WHO, United Nations, PubMed, World Population, and Open City Data. |
| **Artificial Intelligence** | Generate or analyze content with multiple AI providers and reusable AI processing workflows. | OpenAI, Gemini, Grok/xAI, Claude, Mistral, embeddings, vector-ready context, and provider credentials. |
| **File Upload** | Upload supported local files for preview, extraction, and downstream processing. | CSV, Excel, PDF, Word, PowerPoint, Markdown, HTML, JSON, XML, text, chunking, embeddings, and vector storage. |
| **Data Management** | Manage local application data and tabular persistence workflows. | SQLite, CSV/Excel-backed data, dataframe inspection, SQL execution, visualization, import/export, and stored application datasets. |

<a id="live-world-data"></a>

### Live Layers

| Layer                         | Source / Functionality                                                                                                                  |
|-------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------|
| ✈️ Aircraft                   | OpenSky Network live state vectors with configurable geographic radius and airborne filtering.                                          |
| 🛩️ Military Aircraft          | ADSB.lol military-tagged aircraft with local nautical-mile filtering.                                                                   |
| 🛰️ Satellites                 | CelesTrak OMM orbital data propagated with SGP4 and converted to Earth-fixed positions.                                                 |
| 🚢 Vessels & Ships            | AIS Stream WebSocket position messages with bounded collection and geographic filtering.                                                |
| 📈 Earthquakes                | USGS earthquake feeds with magnitude filtering and normalized event locations.                                                          |
| 🔥 Fires                      | NASA FIRMS active-fire detections from VIIRS, MODIS, and Landsat sources.                                                               |
| 📡 Infrastructure             | OpenStreetMap/Overpass infrastructure features including airports, ports, power plants, dams, data centers, and military installations. |
| 📷 CCTV / Web Cameras         | OpenStreetMap/Overpass surveillance-camera and webcam locations.                                                                        |
| 🗺️ Additional Map Layers      | Public transit, bike share, emergency services, healthcare, EV charging, communications, and launch sites.                              |
| 🎯 Tracking & Trails          | Selected moving-entity tracking with persisted in-session path history and optional map following.                                      |
| 📏 Measurements & Annotations | Great-circle distance, bearing, custom points, entity-to-entity measurements, and map annotations.                                      |

### Live World Reliability

The Live World execution path is designed to keep independent providers operational even when one source fails or becomes unavailable.

- Independent refresh execution for the nine provider-backed Live World sources.
- Per-source status, last-attempt, last-success, error, and stale-data state.
- Previous provider data is retained and explicitly marked stale when a refresh fails.
- Provider failures do not stop later enabled providers from refreshing.
- Partial or stale refreshes are not persisted as new Historical Replay snapshots.
- Shared Overpass client behavior for Infrastructure, Cameras, and Map Features, including identifying headers, bounded retry, and fallback endpoints.
- OpenSky OAuth client-credential configuration with backward-compatible legacy environment aliases.
- Bounded Historical Replay persistence with configurable retention and per-source row limits.
- State-fingerprint deduplication for Earthquakes, Fires, Infrastructure, Cameras, and Map Features while moving entities continue to persist for trajectory replay.
- Historical replay limits select the newest records through the chosen snapshot and return them chronologically.
- Agent Tools and Historical Replay are rendered on the active Live World UI path with provider diagnostics and callable-tool inventory.


## 🏛️ Data                                                                                                                                                                                

| Dataset                                                                                                                                                                                 | Records | Description                                                                                                                                 |
| --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------: | ------------------------------------------------------------------------------------------------------------------------------------------- |
| [![Hugging Face Bucket](https://img.shields.io/badge/Hugging%20Face-UAP%20Reports-FFD21E?logo=huggingface\&logoColor=000000)](https://huggingface.co/buckets/leeroy-jankins/UAP)        | 128,975 | UAP sightings reported to the National UFO Reporting Center (NUFORC) from 1906 to 2021 by country, state, city, and geographic coordinates. |
| [![Hugging Face Bucket](https://img.shields.io/badge/Hugging%20Face-EPA%20Sites-FFD21E?logo=huggingface\&logoColor=000000)](https://huggingface.co/buckets/leeroy-jankins/UAP)          |   4,478 | Pollution sites with active EPA remediations or removals by country, state, city, and geographic coordinates.                               |
| [![Hugging Face Bucket](https://img.shields.io/badge/Hugging%20Face-Nuclear%20Facilities-FFD21E?logo=huggingface\&logoColor=000000)](https://huggingface.co/buckets/leeroy-jankins/UAP) |     378 | IAEA nuclear power facilities by country, state, city, and geographic coordinates.                                                          |
| [![Hugging Face Bucket](https://img.shields.io/badge/Hugging%20Face-Airports-FFD21E?logo=huggingface\&logoColor=000000)](https://huggingface.co/buckets/leeroy-jankins/UAP)             |  20,142 | Airports by country, state, city, and geographic coordinates.                                                                               |

### Cross-Layer Spatial Analysis

- Configurable origin from current location, custom point, or loaded entity.
- Radius-based search across normalized entity types.
- Great-circle distance and bearing calculations.
- Nearest-entity and nearest-by-type analysis.
- Cross-layer results without re-fetching provider data when only analysis parameters change.
- Map highlighting for entities inside the active analysis radius.

### Geofencing

- Configurable circular geofence origin and radius.
- Entity-type filtering across operational Live World layers.
- Current inside/outside membership calculation.
- Entry and exit transition events tied to explicit Live World refreshes.
- Baseline initialization without false entry events.
- Bounded event history and dedicated geofence result tables.

### Historical Replay & Persistence

- SQLite persistence of normalized Live World refreshes.
- Configurable retention period.
- Replay windows from one hour through all retained observations.
- Entity-type filtering and bounded replay record counts.
- Snapshot selection from persisted observation timestamps.
- Historical moving-entity paths for aircraft, military aircraft, satellites, and vessels.
- Historical position overlays for static and moving entities.

<a id="ai--ml-functionality"></a>

## 🧠 AI / ML Functionality

### Document-to-Vector Pipeline

Iyrin converts supported API results, crawled web content, and loaded document text into LangChain `Document` objects. The processing pipeline is designed for retrieval-augmented generation, semantic search, downstream agent context, and ML feature preparation.

```text
Source / API Result
        │
        ▼
LangChain Document
        │
        ▼
Recursive Text Chunking
        │
        ▼
Embedding Model
        │
        ▼
Embedding Vectors
        │
        ├──────────────► Chroma
        │
        └──────────────► Pinecone
```

### Chunking & Token-Oriented Preparation

- `RecursiveCharacterTextSplitter` document segmentation.
- Configurable chunk size and overlap.
- Stable chunk identifiers written to document metadata.
- Processing-state isolation by application mode/source.
- Automatic invalidation of downstream embeddings when chunk settings change.
- Loaded-document, chunk, and embedding inspection tabs.

### Embedding Providers

| Provider             | Supported Models / Mode                                                             |
|----------------------|-------------------------------------------------------------------------------------|
| OpenAI               | `text-embedding-3-small`, `text-embedding-3-large`                                  |
| Google Generative AI | `gemini-embedding-2-preview`                                                        |
| Mistral AI           | `mistral-embed`                                                                     |
| Hugging Face         | `sentence-transformers/all-MiniLM-L6-v2`, `sentence-transformers/all-mpnet-base-v2` |
| Local GGUF           | Local embedding-capable GGUF models through `llama-cpp-python`                      |

### Embedding Validation

- One vector per document chunk.
- Consistent embedding dimensionality across a batch.
- Finite numeric-value validation.
- Provider/model tracking in Streamlit session state.
- Local GGUF model-file validation before model loading.

### Vector Storage

| Backend  | Functionality                                                                |
|----------|------------------------------------------------------------------------------|
| Chroma   | Local persistent vector collections with configurable persistence directory. |
| Pinecone | Remote vector indexes with optional namespaces.                              |

Vectorized content is prepared for semantic retrieval, RAG pipelines, contextual search, and agent grounding.

### Agentic Tool Surface

`tools.py` exposes provider-neutral, JSON-serializable geospatial functions suitable for tool-calling 
integrations. The tool layer operates against normalized Live World session state rather 
than provider-specific payload formats.

Supported tool-oriented operations include:

- Live World operational status.
- Entity listing by normalized type.
- Entity search by identifier or name.
- Coordinate-to-entity nearest-neighbor queries.
- Great-circle distance calculations.
- Bearing calculations.
- Cross-layer geospatial context suitable for downstream agent reasoning.
- Provider refresh status and stale/error diagnostics.
- Cross-Layer Analysis, Geofencing, Tracking, and Historical Replay status.
- Bounded retrieval of persisted Historical Replay observations.
- Full normalized entity-type parity, including Infrastructure, Camera, and Map Feature.

The tool surface is intentionally decoupled from any single agent SDK. Provider registration can be performed by an external agent framework without changing the underlying Iyrin geospatial implementation.

### Geospatial Intelligence for AI/ML

The normalized `GeoEntity` model provides a consistent analytical feature surface across aircraft, military aircraft, satellites, vessels, earthquakes, fires, infrastructure, cameras, and additional map features.

Available features include:

- latitude and longitude;
- altitude/depth where applicable;
- heading;
- speed;
- observation timestamp;
- source identity;
- entity type;
- provider metadata;
- derived distance;
- derived bearing;
- geofence membership;
- entry/exit transitions;
- historical position sequences;
- tracking trails;
- cross-layer proximity relationships.

These features support downstream clustering, anomaly detection, classification, trajectory analysis, spatial-temporal modeling, semantic retrieval, and agentic decision-support workflows. Iyrin provides the data normalization, embedding, vectorization, spatial-analysis, persistence, and tool interfaces required for these workflows; supervised model training is not performed automatically by the application.

<a id="scientific--operational-data-sources"></a>

## 🔬 Scientific & Operational Data Sources

### Weather & Climate

- Google Weather
- Open-Meteo
- Historical Weather
- NOAA Climate Data
- NOAA Tides & Currents

### Environmental

- EPA AirNow
- OpenAQ
- PurpleAir
- EPA Envirofacts
- EPA UV Index
- NASA FIRMS
- NASA EONET
- USGS Water Data

### Geological & Geospatial

- USGS Earthquakes
- USGS National Map
- Global imagery and geospatial services

### Astronomical & Space

- Astropy / Astroquery
- Open Astronomy Catalog
- NASA scientific data sources
- CelesTrak satellite orbital data
- Space-weather services
- Naval Observatory data
- Celestial/star-map services

### Live Operational Sources

- OpenSky Network
- ADSB.lol
- AIS Stream
- CelesTrak
- OpenStreetMap Overpass
- NASA FIRMS
- USGS Earthquakes

## 🗺️ Additional Map Layers

OpenStreetMap/Overpass map-feature retrieval supports:

- 🚇 Public Transit
- 🚲 Bike Share
- 🚨 Emergency Services
- 🏥 Healthcare
- 🔌 EV Charging
- 📡 Communications
- 🚀 Launch Sites

Additional map features are normalized as `Map Feature` entities and participate in the same Cross-Layer Analysis, Geofencing, Historical Replay, SQLite persistence, and map-rendering paths used by the other Live World layers.

<a id="installation"></a>

## 📦 Installation

```powershell
 git clone https://github.com/is-leeroy-jenkins/iyrin.git
 cd iyrin
 python -m venv .venv
 .\.venv\Scripts\Activate.ps1
 python -m pip install --upgrade pip
 pip install -r requirements.txt
```

The runtime manifest includes the dependencies needed for the existing AWS S3, Google Cloud Storage, Google Speech-to-Text, and PowerPoint document loaders. To enable the optional Crawl4AI integration when installing from PyPI, use `pip install "iyrin-py[crawl]"`. Crawl4AI is not required for the requests-based crawler fallback; enhanced crawling may require additional browser setup and SDK compatibility testing.

## 🚀 Run

```powershell
streamlit run app.py
```


<a id="configuration"></a>

## ⚙️ Configuration 

Iyrin reads provider credentials from environment variables where required. Legacy `OPENSKY_API_CLIENT_ID`, `OPENSKY_API_CREDENTIALS`, and `NASA_FIRMS_MAP_KEY` names remain accepted as compatibility aliases.

| Environment Variable      | Service                          |
|---------------------------|----------------------------------|
| `GOOGLE_API_KEY`          | Google APIs                      |
| `GOOGLEMAPS_API_KEY`      | Google Maps                      |
| `GOOGLE_WEATHER_API_KEY`  | Google Weather                   |
| `OPENAI_API_KEY`           | OpenAI                           |
| `GEMINI_API_KEY`           | Google Gemini                    |
| `XAI_API_KEY`              | Grok / xAI                       |
| `CLAUDE_API_KEY`           | Anthropic Claude                 |
| `MISTRAL_API_KEY`          | Mistral AI                       |
| `NASA_API_KEY`            | NASA APIs                        |
| `NASA_EARTHDATA_TOKEN`    | NASA Earthdata                   |
| `FIRMS_MAP_KEY`           | NASA FIRMS                       |
| `AIRNOW_API_KEY`          | EPA AirNow                       |
| `OPENAQ_API_KEY`          | OpenAQ                           |
| `PURPLEAIR_API_KEY`       | PurpleAir                        |
| `OPENSKY_CLIENT_ID`          | OpenSky OAuth client ID          |
| `OPENSKY_API_CLIENT_SECRET` | OpenSky OAuth client secret       |
| `AISSTREAM_API_KEY`       | AIS Stream                       |
| `PINECONE_API_KEY`        | Pinecone vector storage          |

## 🔑 API 

- [Science APIs](https://github.com/is-leeroy-jenkins/iyr/blob/main/resources/setup/API-Setup.md) 
- [OpenAI](https://github.com/is-leeroy-jenkins/iyr/blob/main/resources/setup/environments.md) 
- [Gemini AI](https://github.com/is-leeroy-jenkins/iyr/blob/main/resources/setup/gemini.md) 
- [Grok AI](https://github.com/is-leeroy-jenkins/iyr/blob/main/resources/setup/xai.md) 
- [Mistral AI](https://github.com/is-leeroy-jenkins/iyr/blob/main/resources/setup/mistral.md) 
- [Claude AI](https://github.com/is-leeroy-jenkins/iyr/blob/main/resources/setup/claude.md) 

<a id="project-structure"></a>

## 📂 Project Structure

```text
iyr/
├── app.py                  Streamlit application
├── config.py               Application configuration and API metadata
├── world.py                Live World UI, normalization, analysis, rendering, and state
├── sources.py              Live operational provider clients
├── history.py              Live World SQLite persistence and replay
├── tools.py                Provider-neutral agent/tool-calling functions
├── pipelines.py           Chunking, embedding, and vector-storage workflows
├── embedders.py            Embedding providers and local GGUF embeddings
├── fetchers.py             Scientific, environmental, weather, and web providers
├── maps.py                 Mapping gateway
├── geocode.py              Geocoding
├── distances.py            Distance Matrix functionality
├── timezones.py            Time-zone resolution
├── staticmaps.py           Static map generation
├── places.py               Place lookup
├── excel.py                Spreadsheet integration
├── caches.py               Cache implementations
├── stores/
│   ├── vector.py           Chroma and Pinecone vector-store wrappers
│   ├── sqlite/             SQLite application persistence
│   └── csv/                CSV-backed storage
└── resources/              Images and application assets
```

## ⚙️ Processing Architecture

```text
Scientific / Operational APIs
            │
            ├──────────────► Streamlit UI
            │
            ├──────────────► Pandas DataFrames
            │
            ├──────────────► GeoEntity normalization
            │                       │
            │                       ├────────► PyDeck rendering
            │                       ├────────► Tracking / trails
            │                       ├────────► Cross-layer analysis
            │                       ├────────► Geofencing
            │                       ├────────► Historical persistence
            │                       └────────► Agent tools
            │
            └──────────────► LangChain Documents
                                    │
                                    ├────────► Chunking
                                    ├────────► Embeddings
                                    └────────► Chroma / Pinecone
```

## 💡 Use Cases

- Live operational geospatial monitoring.
- Aircraft, vessel, and satellite situational awareness.
- Wildfire and earthquake monitoring.
- Infrastructure and public-camera mapping.
- Emergency-service and healthcare proximity analysis.
- Cross-domain geospatial intelligence.
- Geofence event detection.
- Historical movement replay.
- Environmental and scientific research workflows.
- Semantic indexing of scientific/API results.
- Retrieval-augmented generation preparation.
- Agent grounding with normalized geospatial context.
- Local/private embedding workflows using GGUF models.
- Vector-search dataset creation with Chroma or Pinecone.
- Spreadsheet and reporting enrichment.

<a id="requirements"></a>

## 📦 Requirements

The table below reflects the requirements implied by the active imports, loaders, fetchers, and UI
surface in `app.py`. Some provider-specific loaders/fetchers may require additional credentials or
cloud SDKs depending on deployment.

| Requirement              | Import / Package Name                 | Purpose                                                               | Required By                                             |
| ------------------------ | ------------------------------------- | --------------------------------------------------------------------- | ------------------------------------------------------- |
| Python                   | `python>=3.10`                        | Runtime for modern typing syntax and Streamlit application execution. | Entire application.                                     |
| Streamlit                | `streamlit`                           | Web application framework.                                            | UI, sidebar, modes, expanders, controls, session state. |
| Altair                   | `altair`                              | Declarative charting support.                                         | Visualization and chart-compatible workflows.           |
| Pandas                   | `pandas`                              | Dataframes, Excel ingestion, SQL result rendering, tabular previews.  | Loaders, Data Management, result tables.                |
| NumPy                    | `numpy`                               | Numeric arrays and vector calculations.                               | Text/vector utilities and analysis helpers.             |
| Plotly                   | `plotly`                              | Interactive charts and visualizations.                                | Data Management visualization engine.                   |
| BeautifulSoup            | `beautifulsoup4`                      | HTML parsing and link/text extraction.                                | Scraping mode and HTML preview helpers.                 |
| Requests                 | `requests`                            | HTTP request support.                                                 | Web fetchers and API wrappers.                          |
| Crawl4AI                 | `crawl4ai`                            | JavaScript-capable or enhanced crawling support.                      | Web crawling workflows.                                 |
| LangChain Core           | `langchain-core`                      | `Document` object model for loaded/retrieved records.                 | Loaders and retrieval result handling.                  |
| LXML                     | `lxml`                                | XML parsing and XPath operations.                                     | XML Loader.                                             |
| NLTK                     | `nltk`                                | Tokenization, stopwords, WordNet, corpora, text metrics.              | Loading metrics and Corpora Loader.                     |
| TextStat                 | `textstat`                            | Optional readability metrics.                                         | Readability panel.                                      |
| Astroquery               | `astroquery`                          | Astronomical service access, including SIMBAD.                        | Astronomical mode.                                      |
| SQLite                   | `sqlite3`                             | Local database storage and SQL execution.                             | Data Management and local stores.                       |
| OpenPyXL                 | `openpyxl`                            | Excel `.xlsx` read/write engine.                                      | Excel Loader and Data Management import.                |
| Python PPTX              | `python-pptx`                         | PowerPoint text extraction support.                                   | PowerPoint Loader.                                      |
| PyMuPDF                  | `PyMuPDF`                             | PDF extraction support where used by PDF loader internals.            | PDF Loader.                                             |
| Unstructured             | `unstructured`                        | Optional document extraction for complex files.                       | PDF/XML/document loader implementations.                |
| Python DOCX / Docx2Txt   | `python-docx` / `docx2txt`            | Word document extraction support.                                     | WordLoader.                                             |
| Boto3                    | `boto3`                               | AWS S3 file and bucket access.                                        | AWS S3 File and AWS S3 Bucket loaders.                  |
| Google API Client        | `google-api-python-client`            | Google Drive and Google API access.                                   | Google Drive and cloud workflows.                       |
| Google Auth              | `google-auth`, `google-auth-oauthlib` | Google credentials and OAuth flows.                                   | Google Drive, Google Cloud, Google Speech-to-Text.      |
| Google Cloud Storage     | `google-cloud-storage`                | Google Cloud bucket/file access.                                      | Google Cloud File and Google Cloud Bucket loaders.      |
| Google Cloud Speech      | `google-cloud-speech`                 | Speech-to-text transcription.                                         | Google Speech-to-Text loader.                           |
| ArXiv                    | `arxiv`                               | arXiv search and document retrieval.                                  | ArXiv Loader and Retrieval mode.                        |
| Streamlit Runtime Extras | `watchdog`                            | Optional local development file watching.                             | Local Streamlit development.                            |
| Environment Variables    | `python-dotenv`                       | Optional `.env` loading for API keys.                                 | Local configuration.                                    |
| Typing Extensions        | `typing-extensions`                   | Backported typing support where needed.                               | Compatibility support.                                  |

<a id="license"></a>

## 📜 License

Iyrin is available under the MIT License: [LICENSE.txt](https://github.com/is-leeroy-jenkins/iyr/blob/main/LICENSE.txt).

## 🙏 Acknowledgements

- [God's Eye View](https://github.com/bilawalsidhu/gods-eye-view) — architectural and functional inspiration for Iyrin's Live World Data capabilities.
