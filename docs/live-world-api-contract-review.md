# Live World Data: official API contract review

## Basis

This review compares the changes in PR #103 with authoritative provider and Python
client documentation. PR #104 is a follow-up stacked on top of PR #103 and should be
merged after the parent. It does not replace the parent remediation.

## Findings

| Contract | Documentation | Finding | Correction |
| --- | --- | --- | --- |
| AIS Stream subscription | https://www.aisstream.io/documentation | `SubscriptionConfirmation.Message.CompressionEnabled` indicates negotiated permessage-deflate; the previous implementation accepted a missing value | Require explicit `True` before collecting messages |
| AIS Stream sampling | https://www.aisstream.io/documentation | A subscription must be sent within three seconds; the server sends event-driven position messages; short samples may legitimately return zero | Retain post-confirmation observation window and configuration from PR #103 |
| Python websockets | https://websockets.readthedocs.io/en/14.2/reference/sync/client.html | `websockets.sync.client.connect` supports compression and `recv(timeout=...)` raises `TimeoutError` | Confirmed compatible; retain client, add negative acknowledgement tests |
| NASA FIRMS Area API | https://firms.modaps.eosdis.nasa.gov/api/area | Source, bounding-box order, day range, and optional date are correct | Retain existing URL and sensor settings |
| NASA FIRMS CSV | https://firms.modaps.eosdis.nasa.gov/content/academy/data_api/firms_api_use.html | Valid VIIRS CSV includes `latitude`, `longitude`, and `acq_date`; malformed nonempty content is not a valid empty dataset | Raise a provider error on nonempty unparsable CSV instead of reporting zero detections |
| OSM surveillance types | https://wiki.openstreetmap.org/wiki/Key:surveillance:type | `man_made=surveillance` can describe guards or other non-camera surveillance | Classify explicitly tagged camera/ALPR or `camera:type` as CCTV; exclude untyped or guard-only surveillance |
| Overpass QL | https://wiki.openstreetmap.org/wiki/Overpass_API/Overpass_QL | `nwr`, `around` (meters), and `out center` are supported | No syntax correction required |

## Tests

- Regression tests distinguish malformed nonempty FIRMS content from header-only
  valid zero-row CSV responses.
- Camera tests distinguish `surveillance:type=guard` from camera tags.
- AIS tests require affirmative compression acknowledgement and reject missing
  confirmation or unavailable compression.

## CI note

GitHub Actions for PR #103 recorded two failures in
`tests/test_live_world_credential_environment.py` concerning the existing
credentials form in `app.py`. These are unrelated to the four provider
changes and already existed in the parent branch. They require separate
credential-editor remediation and should not be concealed or reported as
passing provider tests.

## Verification limits

Static documentation review and mocked tests cannot prove that an external
provider delivered live records in the user's location, that API credentials
were configured, or that a public Overpass service was reachable. The
documented on-site integration checklist in
`docs/live-world-provider-remediation.md` remains necessary before release.
