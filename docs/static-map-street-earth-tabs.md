# Mapping Tools: Map / Street / Earth tabs

## Changes

- Preserve the existing Mapping Tools → Static Maps input controls, Generate Map
  button, success message, and generated static map URL.
- Display the generated map at full content-column width using Streamlit's
  `st.image(width='stretch')`.
- Request `scale=2` for sharper imagery while preserving Google Maps Static
  API's maximum supported base `size` of 640×640; remove the unsupported
  `800x600` option.
- Display the result in a **Map** tab alongside **Street** and **Earth** tabs.
- **Street:** Embed an interactive, location-based Google Street View panorama
  using the documented Maps Embed API `streetview` iframe mode. Available
  imagery depends on Street View coverage.
- **Earth:** Google Earth does **not** support official iframe embedding.
  Use the documented Google Maps Embed API `view` mode with
  `maptype=satellite`, and provide an **Open Google Earth** external link.
- Use the latitude and longitude saved with the most recently generated static
  map, falling back to the validated global coordinate getters if necessary.
- Reuse the existing OS-backed `cfg.GOOGLEMAPS_API_KEY` (also used by
  `mapping.StaticMap`). No new credential entry or provider is introduced.

## Deployment requirements

Enable **Maps Embed API** on the Google Cloud project that owns the existing
Google Maps key. Keep billing enabled. The Maps Embed API currently has no
per-request charge, but an API key and project billing configuration remain
required. If the key is HTTP-referrer-restricted, allow the deployed application's
public origin. Embedded Street View may show imagery at a nearby road rather
than the exact coordinate.

The Earth tab is a satellite-map substitute, **not** the Google Earth web app
inside an iframe. Google explicitly states that Earth has no embed or client API.

## Official documentation

- [Google Maps Static size and scale](https://developers.google.com/maps/documentation/maps-static/start)
- [Google Maps Embed API Street View mode](https://developers.google.com/maps/documentation/embed/embedding-map)
- [Google Maps Embed API setup](https://developers.google.com/maps/documentation/embed/quickstart)
- [Google Earth embedding limitations](https://developers.google.com/maps/documentation/earth/quick-reference)

## Regression checks

Run `tests/test_static_map_embed_tabs.py` and the existing project audit.
Verify that the Map, Street and Earth tabs show the most recently generated
coordinates, that Street View displays a panorama when coverage exists, and
that satellite imagery uses a browser-accessible API key.
