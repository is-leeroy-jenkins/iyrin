# Realtime mode — Live World Data workspace

## Layout

Selecting **Realtime** in the application Mode radio displays a dedicated
two-column workspace, consistent with Geological, Weather, Astronomical, and
Public Health mode layouts:

- **Location header:** current global Location, Latitude, and Longitude.
- **Left (40%)**: separate expanders for **🌐 Live Layers**,
  **🎯 Tracking & Measurements**, **Additional Layers**, and
  **AI & Advanced Tools**. All pre-existing provider checkboxes, options,
  refresh/clear buttons, measurements/annotations, tracks, additional OSM
  layers, history, geofence and agent settings retain their session-state keys.
- **Right (60%)**: existing PyDeck Live World map, metrics, diagnostic
  messages, and a **read-only Live Entities `st.data_editor` directly below
  the map**. The existing detailed source/analysis/history tabs remain
  available beneath the editor.

The former **📡 Live Data** block was removed from the universal sidebar,
and the Live World map is no longer appended to unrelated application modes.
The mode is now present in `cfg.MODES`. `render_world_sidebar()` is retained
as the public control-rendering entrypoint and now renders inside the left
content column.

## Startup and refresh behavior

The right-hand column displays an empty, interactive basemap and an empty
entity editor if the Live Map is disabled, no source has been selected, or
the enabled sources have not yet returned records. This **does not** cause
network requests: selecting the appropriate source checkboxes and pressing
**Refresh** still controls provider fetches.

When a provider returns records, the map displays entity layers and the
read-only editor shows those same normalized entities. Individual source
results, measurements, tracking history, alerts, geofencing and historical
replay remain in the existing detailed tabs.

Source credentials and API implementations have not been moved or changed.
Provider requests continue to use configuration from `config.py`.

## Verification

Run the repository's existing GitHub Actions audit and
`tests/test_realtime_mode_layout.py`. The tests verify the Mode selection,
single control/map invocation, four expanders with unique widget keys, empty
basemap, and primary data editor placement.

Visual/interaction testing in Streamlit should confirm that selecting
**Realtime** shows only one copy of each widget, that provider Refresh
populates the right panel, and that switching modes does not render another
Live World map below unrelated content.
