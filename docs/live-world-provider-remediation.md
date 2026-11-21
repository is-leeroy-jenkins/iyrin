# Live World Data — Provider Remediation and Validation Plan

## Scope and invariants

This change addresses the FIRMS, AIS Stream, Overpass Cameras, and Overpass Infrastructure
paths in the existing Live World Streamlit map. It preserves the current provider classes,
normalized entity fields, sidebar sections, metric labels, independent source refreshes,
and PyDeck point rendering. Credentials remain OS-environment-backed through `config.py`.

## Confirmed defects and implemented corrections

| Provider | Source defect | Change | Acceptance condition |
| --- | --- | --- | --- |
| FIRMS | Unexpected/invalid HTTP-successful CSV may be treated as data or fail during parsing | Require detection headers; distinguish valid empty CSV from malformed schema | Header-only response returns zero rows; wrong schema raises a provider error |
| FIRMS | Missing credential is discovered too late in the provider request path | Preflight `FIRMS_MAP_KEY` in `refresh_live_source()` | A missing key yields `Configuration Required` and retains previously loaded data |
| AIS | Three-second sample includes connection setup | Begin sampling only after subscription confirmation; expose a 5–60 second window, default 15 | Network setup no longer consumes collection time |
| AIS | Existing WebSocket transport does not negotiate message compression | Use `websockets.sync.client.connect` with permessage-deflate and verify negative compression acknowledgement | Compression-capable connection and explicit rejection of a negative acknowledgement |
| Cameras | Presence-based `webcam` Overpass selector conflicts with truthiness-based classifier | Match `webcam` and `contact:webcam` by key presence | A tagged feature with an empty webcam value is retained |
| Overpass shared | HTTP 200 may contain a `remark` that represents a query failure | Treat a nonempty `remark` as a provider error | Timeouts reported in JSON never appear as successful empty results |
| Overpass shared | Permanent HTTP exceptions lose `response.status_code` after conversion to a plain RuntimeError | Preserve `requests.HTTPError` and response | Status is recoverable by Live World source diagnostics |
| All sources | An empty normalized frame is labeled `Success` | Record and display `No Records` separately from `Success` and `Failed` | The UI distinguishes an empty sample from a failed request |

## Correctness and operating limits

- A valid zero-record response is not proof of provider failure. In particular, the configured
  map center, radius, source tags, observation period, and upstream traffic can legitimately
  produce empty results.
- OpenStreetMap is not a comprehensive registry of live CCTV streams or every facility.
  Infrastructure and camera layer coverage remains limited to the explicit OSM taxonomy.
  Expanding to additional providers or heuristically guessing OSM categories is not part of
  this targeted repair.
- Live AIS messages are event driven and cannot be guaranteed within a fixed window.
  Long-lived background streaming is a potential future architectural enhancement, not
  part of this request.
- The Overpass public endpoints remain subject to rate limits and server query budgets.
- Avoid exposing API keys in diagnostics or Streamlit session state.

## Regression coverage

- `tests/test_ais_stream_validation.py`: valid subscription acknowledgement, compressed
  subscription and input validation; missing confirmation.
- `tests/test_live_world_failure_modes.py`: HTTP 200 with an Overpass error remark,
  transient retries, permanent HTTP failure, AIS configuration.
- `tests/test_live_world_additional_provider_repairs.py`: FIRMS header-only datasets,
  invalid CSV schema, camera tag-existence matching.

## Release checklist

1. Install dependencies from `requirements-runtime.txt` or `requirements.txt`.
2. Run the existing Python test suite and inspect all failures before merge.
3. Start Streamlit with known valid environment credentials (without printing keys).
4. Test each source separately near a suitable location, varying radius and observation window.
5. Confirm `Success`, `No Records`, `Configuration Required`, and `Failed`
   reflect the actual provider outcomes.
6. Verify that pre-existing aircraft, military, satellite, earthquake, tracking, and
   map-layer functionality and UI layout remain intact.
7. Merge the single PR only after regression results and provider integration checks are accepted.
