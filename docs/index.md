# Iyrin

![Iyrin](https://raw.githubusercontent.com/is-leeroy-jenkins/Iyrin/main/resources/images/iyrin-project.png)

Iyrin is a Streamlit application for geospatial analysis, scientific and public data retrieval, Live World operational intelligence, document processing, embeddings, vector storage, and multi-provider artificial intelligence.

<div class="grid cards" markdown>

-   **🧭 Geospatial Analysis**

    Geocoding, places, distance and travel-time calculations, time zones, static maps, and interactive PyDeck visualization.

-   **🌐 Live World**

    Aircraft, military aircraft, satellites, vessels, earthquakes, fires, infrastructure, cameras, additional map features, tracking, geofencing, and replay.

-   **🧠 AI / ML Processing**

    Document chunking, embedding generation, Chroma and Pinecone persistence, retrieval-ready state, and agent-callable geospatial tools.

-   **🔬 Scientific Data**

    Weather, climate, environmental, geological, astronomical, demographic, biomedical, and public-health sources.

</div>

## Application Modes

| Mode | Primary Function |
|---|---|
| Mapping Tools | Direct geospatial utilities and map-service operations. |
| Interactive Map | Interactive mapping and Live World visualization. |
| Site Crawler | Page retrieval, crawling, and web-content extraction. |
| Document Data | Document/public-source ingestion and processing. |
| Weather Data | Weather forecasts, climate, historical observations, and tides. |
| Environmental Data | Air quality, UV, environmental facilities, fires, and natural events. |
| Geological Data | Earthquakes, water monitoring, topographic data, and geoscience catalogs. |
| Astronomical Data | Catalog, orbital, satellite, and space-weather data. |
| Celestial Map | Star/sky charting and observation-oriented visualization. |
| Public Health | Demographic, population, biomedical, and health sources. |
| Artificial Intelligence | Multi-provider AI generation and analysis. |
| File Upload | Local file ingestion, preview, and processing. |
| Data Management | Local persistence, SQL, tables, import/export, and visualization. |

## Processing Model

```text
Scientific / Operational APIs
            │
            ├──────────────► Streamlit UI
            │
            ├──────────────► Pandas DataFrames
            │
            ├──────────────► GeoEntity normalization
            │                       ├────────► PyDeck rendering
            │                       ├────────► Tracking / trails
            │                       ├────────► Cross-layer analysis
            │                       ├────────► Geofencing
            │                       ├────────► Historical persistence
            │                       └────────► Agent tools
            │
            └──────────────► LangChain Documents
                                    ├────────► Chunking
                                    ├────────► Embeddings
                                    └────────► Chroma / Pinecone
```

[Get Started](getting-started.md){ .md-button .md-button--primary }
[Architecture](architecture.md){ .md-button }
