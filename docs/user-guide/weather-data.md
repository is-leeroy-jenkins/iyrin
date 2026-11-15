# Weather Data

Weather Data is a standalone application mode for meteorological and marine observations, forecasts, and historical climate retrieval. It appears directly in **Map Data → Pipelines**, alongside Astronomical Data.

## Sources

- Google Weather
- OpenWeather
- Historical Weather
- NOAA Climate Data
- NOAA Tides & Currents

## Workflow

1. Select **Weather Data** from the Pipelines radio control.
2. Review the active location and latitude/longitude metrics.
3. Expand a weather source, configure its existing inputs, and run the retrieval.
4. Inspect results in the **Loaded** document pane and use the existing processing controls for chunking, embeddings, or storage when appropriate.

Provider credentials, existing widget keys, request arguments, and the `weather_*` session-state namespace remain unchanged by this mode split.
