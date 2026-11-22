# Mapping Tools: Static Maps / Street / Satellites tabs

## Changes

- Preserve the existing Mapping Tools → Static Maps input controls, Generate Map
  button, success message, and generated static map URL.
- Display the generated map at full content-column width using Streamlit's
  `st.image(width='stretch')`.
- Request `scale=2` for sharper imagery while preserving Google Maps Static
  API's maximum supported base `size` of 640×640; remove the unsupported
  `800x600` option.
- Keep the static image in **Static Maps** and add **Street** and **Satellites** to the\n  top-level Mapping Tools tab bar, immediately to the right of Static Maps.
- **Street:** Embed an interactive, location-based Google Street View panorama
  using the documented Maps Embed API `streetview` iframe mode. Available
  imagery depends on Street View coverage.
- **Satellites:** Render Google Maps' interactive photorealistic **3D Maps** viewer
  by default using `<gmp-map-3d>` and `mode="SATELLITE"`, with a camera
  range of 3000 meters, tilt 65 degrees, and heading 0 degrees. Offer a
  selectable **2D Satellite** fallback via the existing Google Maps Embed API
  `view` mode with `maptype=satellite`. Retain **Open Google Earth** as
  an external link; Google Earth itself cannot be embedded.
- Use the latitude and longitude saved with the most recently generated static
  map, falling back to the validated global coordinate getters if necessary.
- Reuse the existing OS-backed `cfg.GOOGLEMAPS_API_KEY` (also used by
  `mapping.StaticMap`). No new credential entry or provider is introduced.

## Deployment requirements

Enable **Maps JavaScript API** for the 3D satellite viewer and **Maps Embed
API** for Street View and the 2D fallback on the Google Cloud project that
owns the existing Google Maps key. Keep billing enabled and verify 3D Maps
billing and quotas independently of Maps Embed API. The Maps JavaScript API
key is loaded by the user's browser, just like the existing Google Maps embeds.
If the key is HTTP-referrer-restricted, allow the deployed Streamlit app's origin
and test the component's iframe referrer behavior. Embedded Street View may show
imagery at a nearby road rather than at the exact coordinate.

Photorealistic 3D buildings are only available where Google provides 3D mesh
coverage. 3D Maps requires suitable browser hardware acceleration and WebGL.
Select **2D Satellite** if the browser or graphics hardware cannot render 3D.

The Satellites tab is a satellite-map substitute, **not** the Google Earth web app
inside an iframe. Google explicitly states that Earth has no embed or client API.

## Official documentation

- [Google Maps Static size and scale](https://developers.google.com/maps/documentation/maps-static/start)
- [Google Maps Embed API Street View mode](https://developers.google.com/maps/documentation/embed/embedding-map)
- [Google Maps Embed API setup](https://developers.google.com/maps/documentation/embed/quickstart)
- [Google 3D Maps overview](https://developers.google.com/maps/documentation/javascript/3d/overview)
- [Google 3D Maps setup](https://developers.google.com/maps/documentation/javascript/3d/get-started)
- [Google 3D Maps browser support](https://developers.google.com/maps/documentation/javascript/3d/support)
- [Google Earth embedding limitations](https://developers.google.com/maps/documentation/earth/quick-reference)

## Regression checks

Run `tests/test_static_map_embed_tabs.py` and the existing project audit.
Verify that the Static Maps, Street and Satellites tabs show the most recently generated
coordinates, that Street View displays a panorama when coverage exists, and
that **3D Satellite** renders using Maps JavaScript API, that **2D Satellite**
remains selectable and that both work with a browser-accessible API key.
