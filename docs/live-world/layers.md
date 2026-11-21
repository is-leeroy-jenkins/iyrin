# Operational Layers

| Layer | Provider / Function |
|---|---|
| Aircraft | OpenSky Network live state vectors. |
| Military Aircraft | ADSB.lol military-tagged aircraft. |
| Satellites | CelesTrak OMM data propagated with SGP4. |
| Vessels | AIS Stream WebSocket positions. |
| Earthquakes | USGS earthquake feeds. |
| Fires | NASA FIRMS active-fire detections. |
| Infrastructure | OpenStreetMap/Overpass infrastructure. |
| Cameras | OpenStreetMap/Overpass CCTV and webcams. |
| Map Features | Transit, bike share, emergency services, healthcare, EV charging, communications, and launch sites. |

## Provider Hardening

Infrastructure, Cameras, and Map Features share Overpass behavior with identifying headers, bounded retry, and fallback endpoint support.

OpenSky uses the `OPENSKY_CLIENT_ID` and `OPENSKY_API_CLIENT_SECRET` OS environment variables through `config.py`. AIS Stream uses `AISSTREAM_API_KEY`. Live World provider credentials are not supplied through sidebar controls; restart the application after changing OS environment variables.

FIRMS identities use stable source/date/time/coordinate values rather than provider row ordering.
