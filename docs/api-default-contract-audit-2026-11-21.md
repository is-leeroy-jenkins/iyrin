# External API request-default audit — 2026-11-21

## Scope and method

A source-level inventory of the Python modules used by Iyrin, including the request-bearing
provider classes in `fetchers.py`, `sources.py`, `generators.py` and `mapping.py`, and
SDK-adjacent call sites in loaders, processors, storage, tools, app and realtime.
The direct-request inventory below enumerates `93` explicit `requests.*`
calls and `17` syntactically visible SDK client calls found in the inspected
modules. Calls made inside third-party libraries or by dynamically assembled wrappers
may not appear in this count. A source-code audit cannot prove a credentialed live endpoint
accepts a request or that a remote dataset exists.

**Result labels:** "Documentation cross-checked" means the linked authoritative
documentation was consulted for the relevant provider and representative defaults.
"Source-inventoried" means code and dispatch defaults were enumerated, but individual
endpoint/model parameter combinations have not all been independently verified.
Do not treat the second label as an assurance of compatibility.

## Confirmed defects and corrective actions

| ID | Source | Confirmed defect | Corrective action | Regression |
| --- | --- | --- | --- | --- |
| C01 | `app.py` → `realtime.py` | Missing session location defaults to `(0.0, 0.0)`; local providers receive this as a usable location | Refuse geographic refresh for aircraft, military, vessels, infrastructure, cameras, map layers and local FIRMS; retain stale data and report `Location Required`. Permit global satellites, earthquakes and worldwide FIRMS | Missing-location dispatch test |
| C02 | `sources.py:AisStreamLive.fetch_positions` | Clamping longitude loses coverage at the ±180° meridian | Split across two valid AIS north-west/south-east bounding boxes | Positive and negative antimeridian subscription tests |
| C03 | `sources.py:OpenSkyLive.fetch_states` | Single clamped bbox loses coverage at date line | Issue two valid WGS84 `lamin/lomin/lamax/lomax` requests; deduplicate state vectors by ICAO24 | Two-request OpenSky test |
| C04 | `realtime.py:fetch_fires` | Local FIRMS bbox is clipped at date line | Split into two `west,south,east,north` Area API requests and merge detection records | Both date-line FIRMS tests |
| C05 | `fetchers.py:Firms.fetch` | Default `mode='area'` combined with `source=''` cannot satisfy mandatory `SOURCE` | Set `source='VIIRS_NOAA21_NRT'`, which NASA documents | Default-source AST test |
| C06 | `fetchers.py:NearbyObjects.fetch`, `app.py` | Default close-approach dispatch used empty dates and raised before making its default request | Use JPL CAD's documented `date-min=now` and `date-max=+60`; mirror in UI | CAD default-argument test |
| C07 | `fetchers.py:NearbyObjects`, `app.py` | JPL NHATS integer enum filters `dv`/`h` were sent as floats (`6.0`/`26.0`); UI permitted values outside documented sets | Integer defaults and provider-defined allowed values for dv, dur, stay, launch, h, occ; constrain UI | NHATS default and contract tests |

## Other defaults checked against official provider references

| Provider / method | Application default | Official contract conclusion |
| --- | --- | --- |
| AIS Stream | `APIKey`, `BoundingBoxes`, position message filters, 15s sample | Required fields present; API uses latitude-longitude corner pairs and event-driven messages. [Docs](https://www.aisstream.io/documentation/) |
| OpenSky states/all | `radius_degrees=2.0` | Four bbox parameters use decimal-degree WGS84 bounds; a 2° radius is a client search preference. [Docs](https://openskynetwork.github.io/opensky-api/rest.html) |
| FIRMS Area | `VIIRS_NOAA21_NRT`, `world` or local bbox, `day_range=1` | Supported source; `DAY_RANGE` is 1–5; bounding order west,south,east,north. [Docs](https://firms.modaps.eosdis.nasa.gov/api/area) |
| FIRMS data availability | `sensor='ALL'` | `ALL` is an allowed sensor. [Docs](https://firms.modaps.eosdis.nasa.gov/api/data_availability) |
| JPL CAD | `now`, `+60`, `10LD`, `Earth`, `date`, `limit=20` | Relative date tokens, distance unit, body and sort all documented. [Docs](https://ssd-api.jpl.nasa.gov/doc/cad.html) |
| JPL NHATS | `dv=6`, `dur=360`, `stay=8`, `launch='2020-2045'`, `h=26`, `occ=7` | All allowed documented integer/enum values. [Docs](https://ssd-api.jpl.nasa.gov/doc/nhats.html) |
| NASA EONET v3 | `status='open'`, `limit=20`, `days=30` | All supported query values and filters. [Docs](https://eonet.gsfc.nasa.gov/docs/v3) |
| Google Search | `results=10`, `start=1`, `safe='off'` | Results 1–10, start 1-based, safe=off supported. [Docs](https://developers.google.com/custom-search/v1/reference/rest/v1/cse/list) |
| Google Directions | `mode='driving'` | Documented default travel mode. [Docs](https://developers.google.com/maps/documentation/directions/get-directions) |
| Google Weather | `unitsSystem=METRIC`, `languageCode=en`, `hours=24`, `days=5` | Hours 1–240; days 1–10; METRIC and en supported. Note hours over 24 may require pagination to return all records. [Docs](https://developers.google.com/maps/documentation/weather/reference/rest) |
| The News API | `endpoint='all'`, `language='en'`, `limit=10`, `include_similar=True` | Published supported endpoint, language, limit and similarity flag. [Docs](https://www.thenewsapi.com/documentation) |
| Open-Meteo | `zone='auto'` | `timezone=auto` is supported. [Docs](https://open-meteo.com/en/docs) |
| NOAA CO-OPS | `datum='MLLW'`, `units='metric'`, `time_zone='gmt'`, `interval='hilo'` | Valid for applicable tidal products; specific station and dates remain mandatory caller inputs. [Docs](https://api.tidesandcurrents.noaa.gov/api/prod/) |
| Census ACS | `year='2022'`, `dataset='acs/acs5'`, `fields='NAME,B01001_001E'` | The dataset and variable names exist; API key/permissions depend on current endpoint policy. [Docs](https://api.census.gov/data/2022/acs/acs5/variables.html) |
| Overpass | `around:radius_meters,latitude,longitude` | Radius is in meters; coordinates are latitude then longitude. [Docs](https://wiki.openstreetmap.org/wiki/Overpass_API/Overpass_QL) |
| Anthropic Claude | `claude-sonnet-4-6` | Supported active model at review. [Docs](https://docs.anthropic.com/en/docs/about-claude/model-deprecations) |
| Mistral | `mistral-large-latest` | Supported model alias; provider tracks latest alias versions. [Docs](https://docs.mistral.ai/models/mistral-large-latest) |

**Argument sentinel policy:** An empty ZIP code, station ID, model prompt or geographic
selector is not inherently a valid API default. Existing `throw_if` guards in the
underlying mandatory-argument methods reject these before sending an outbound request.
The audit does not invent a ZIP code, station identifier or coordinates to make every
optional dispatcher signature callable without user input.

## Client and entrypoint inventory

The table includes all provider wrapper classes found in the primary request modules,
including the constructor/dispatcher entrypoint where available. A source-inventoried
entry is **not** a claim that every combination of caller arguments has been checked.

| Module | Provider class | Primary API entrypoint / signature | Review | Documentation |
| --- | --- | --- | --- | --- |
| `fetchers.py` | `Fetcher` | `188: def fetch( self, query: str, url:str, time: int=10 ) -> Result \| None:` | Source-inventoried | Provider-specific documentation not located |
| `fetchers.py` | `WebFetcher` | `275: def fetch( self, url: str, time: int=10 ) -> List[ Document ]:` | Source-inventoried | Provider-specific documentation not located |
| `fetchers.py` | `WebCrawler` | `852: def fetch( self, url: str, time: int=10 ) -> Result \| None:` | Source-inventoried | Provider-specific documentation not located |
| `fetchers.py` | `ArXiv` | `1004: def fetch( self, question: str, max_documents: Optional[ int ]=None, full_documents: Optional[ bool ]=None, include_metadata: Optional[ bool ]=None ) -> List[ Document ] \| None:` | Source-inventoried | [Reference](https://info.arxiv.org/help/api/) |
| `fetchers.py` | `GoogleDrive` | `1153: def fetch( self, question: str, folder_id: str='root', results: int=10, template: str='gdrive-query', mime_type: Optional[ str ]=None, mode: str='documents' ) -> List[ Document ] \| None:` | Source-inventoried | [Reference](https://developers.google.com/workspace/drive/api/reference/rest/v3) |
| `fetchers.py` | `Wikipedia` | `1301: def fetch( self, question: str, language: Optional[ str ]=None, max_documents: Optional[ int ]=None, include_metadata: Optional[ bool ]=None ) -> List[ Document ] \| None:` | Source-inventoried | [Reference](https://www.mediawiki.org/wiki/API:Main_page) |
| `fetchers.py` | `TheNews` | `1437: def fetch( self, endpoint: str='all', query: str='', language: str='en', categories: str='', exclude_categories: str='', locale: str='', domains: str='', exclude_domains: str='', source_ids: str='', exclude_source_ids: str='', published_after: str='', published_before: str='', pu` | Documentation cross-checked | [Reference](https://www.thenewsapi.com/documentation) |
| `fetchers.py` | `GoogleSearch` | `1712: def fetch( self, keywords: str, results: int=10, start: int=1, exact_terms: str='', exclude_terms: str='', file_type: str='', date_restrict: str='', gl: str='', lr: str='', safe: str='off', search_type: str='', site_search: str='', site_search_filter: str='', sort: str='', img_si` | Documentation cross-checked | [Reference](https://developers.google.com/custom-search/v1/reference/rest/v1/cse/list) |
| `fetchers.py` | `GoogleMaps` | `2073: def request_directions( self, origin: str, destination: str, mode: str='driving' ) -> str \| None:` | Documentation cross-checked | [Reference](https://developers.google.com/maps/documentation/directions/get-directions) |
| `fetchers.py` | `GoogleWeather` | `2343: def request( self, path: str, params: Dict[ str, Any ], time: int=10 ) -> Dict[ str, Any ] \| None:` | Documentation cross-checked | [Reference](https://developers.google.com/maps/documentation/weather/reference/rest) |
| `fetchers.py` | `NavalObservatory` | `2776: def fetch( self, mode: str='celnav', date_value: str='', time_value: str='', latitude: float=0.0, longitude: float=0.0, location_label: str='', time: int=20 ) -> Dict[ str, Any ] \| None:` | Source-inventoried | [Reference](https://aa.usno.navy.mil/data/api) |
| `fetchers.py` | `SatelliteCenter` | `3066: def fetch( self, mode: str='observatories', query: str='', start_time: str='', end_time: str='', coordinate_systems: str='gse', resolution_factor: int=1, time: int=20 ) -> Dict[ str, Any ] \| None:` | Source-inventoried | [Reference](https://sscweb.gsfc.nasa.gov/WebServices/) |
| `fetchers.py` | `EarthObservatory` | `3461: def fetch( self, mode: str='events', status: str='open', category: str='', source: str='', limit: int=20, days: int=30, start_date: str='', end_date: str='', time: int=20 ) -> Dict[ str, Any ]:` | Documentation cross-checked | [Reference](https://eonet.gsfc.nasa.gov/docs/v3) |
| `fetchers.py` | `GlobalImagery` | `3665: def fetch_map_services( self ) -> Image.Image:` | Source-inventoried | [Reference](https://nasa-gibs.github.io/gibs-api-docs/) |
| `fetchers.py` | `NearbyObjects` | `4255: def fetch( self, mode: str='close_approaches', start_date: str='now', end_date: str='+60', query: str='', query_type: str='sstr', dist_max: str='10LD', body: str='Earth', sort: str='date', limit: int=20, dv: int=6, dur: int=360, stay: int=8, launch: str='2020-2045', h: int=26,` | Documentation cross-checked | [Reference](https://ssd-api.jpl.nasa.gov/doc/cad.html) |
| `fetchers.py` | `OpenScience` | `4760: def fetch( self, mode: str='dataset', query: str='', accession: str='', format_value: str='json', time: int=20 ) -> Dict[ str, Any ] \| None:` | Source-inventoried | [Reference](https://visualization.osdr.nasa.gov/biodata/api) |
| `fetchers.py` | `SpaceWeather` | `5122: def fetch( self, mode: str='cme', start_date: str='', end_date: str='', time: int=20, location: str='ALL', catalog: str='ALL', notification_type: str='all', most_accurate_only: bool=True, complete_entry_only: bool=True, speed: int=0, half_angle: int=0, keyword: str='',` | Documentation cross-checked | [Reference](https://api.nasa.gov/) |
| `fetchers.py` | `AstroCatalog` | `5604: def fetch( self, mode: str='object_query', query: str='', quantity: str='', attributes: str='', arguments: str='', ra: str='', dec: str='', radius: int=2, data_format: str='json', time: int=20 ) -> Any:` | Source-inventoried | [Reference](https://api.astrocats.space/) |
| `fetchers.py` | `AstroQuery` | `5967: def fetch( self, mode: str='object_search', query: str='', ra: str='', dec: str='', radius: float=0.5, radius_unit: str='deg', row_limit: int=100 ) -> Dict[ str, Any ] \| None:` | Source-inventoried | [Reference](https://astroquery.readthedocs.io/en/latest/) |
| `fetchers.py` | `StarMap` | `6527: def fetch( self, mode: str='object_link', query: str='', ra: float=0.0,` | Source-inventoried | [Reference](https://www.sky-map.org/) |
| `fetchers.py` | `GovData` | `7095: def fetch( self, mode: str='search', query: str='', page_size: int=10, offset_mark: str='*', sort_field: str='score', sort_order: str='DESC', package_id: str='', collection: str='', start_date: str='', time: int=20 ) -> Dict[ str, Any ] \| None:` | Source-inventoried | [Reference](https://api.govinfo.gov/docs/) |
| `fetchers.py` | `StarChart` | `7793: def fetch( self, mode: str='object_chart', query: str='', ra: float=0.0, dec: float=0.0, zoom: int=5, image_source: str='DSS2', box_color: str='yellow', show_box: bool=True, show_grid: bool=True, show_lines: bool=True, show_boundaries: bool=True,` | Source-inventoried | [Reference](https://www.sky-map.org/) |
| `fetchers.py` | `Congress` | `8846: def fetch( self, mode: str='congresses', congress: int=0, bill_type: str='', bill_number: int=0, law_type: str='', law_number: int=0, report_type: str='', report_number: int=0, offset: int=0, limit: int=20, sort: str='updateDate+desc', from_date_time: str='',` | Documentation cross-checked | [Reference](https://github.com/LibraryOfCongress/api.congress.gov) |
| `fetchers.py` | `InternetArchive` | `9274: def fetch( self, keywords: str, fields: List[ str ] \| None = None, rows: int=10, page: int=1, sort: str='downloads desc', media_type: str='', collection: str='', time: int=20 ) -> Dict[ str, Any ] \| None:` | Source-inventoried | [Reference](https://archive.org/developers/search.html) |
| `fetchers.py` | `OpenWeather` | `9961: def fetch( self, location: str, mode: str='current', zone: str='auto', forecast_days: int=7, past_days: int=0, count: int=10 ) -> Dict[ str, Any ] \| None:` | Documentation cross-checked | [Reference](https://open-meteo.com/en/docs) |
| `fetchers.py` | `HistoricalWeather` | `10474: def fetch( self, location: str, date: dt.date, zone: str='auto', count: int=10 ) -> Dict[ str, Any ] \| None:` | Source-inventoried | [Reference](https://open-meteo.com/en/docs/historical-weather-api) |
| `fetchers.py` | `Grokipedia` | `10918: def fetch( self, mode: str='search', query: str='', page: str='', limit: int=12, offset: int=0, include_content: bool=True ) -> Dict[ str, Any ] \| None:` | Source-inventoried | [Reference](https://grokipedia.com/) |
| `fetchers.py` | `GoogleGeocoding` | `11445: def fetch( self, mode: str='forward', query: str='', latitude: float=0.0, longitude: float=0.0, place_id: str='', language: str='en', region: str='', result_type: str='', location_type: str='', time: int=10, api_key: Optional[ str ] = None ) -> Dict[ str, Any ] \| None:` | Documentation cross-checked | [Reference](https://developers.google.com/maps/documentation/geocoding/requests-geocoding) |
| `fetchers.py` | `CensusData` | `12011: def fetch( self, mode: str='variables', year: str='2022', dataset: str='acs/acs5', fields: str='NAME,B01001_001E', geography_for: str='state:*', geography_in: str='', predicates: str='', time: int=20 ) -> Dict[ str, Any ] \| None:` | Documentation cross-checked | [Reference](https://api.census.gov/data/2022/acs/acs5/variables.html) |
| `fetchers.py` | `Socrata` | `12498: def fetch( self, mode: str='rows', domain: str='data.cdc.gov', dataset_id: str='', select: str='', where: str='', order: str='', group: str='', limit: int=25, offset: int=0, time: int=20 ) -> Dict[ str, Any ] \| None:` | Source-inventoried | [Reference](https://dev.socrata.com/docs/queries/) |
| `fetchers.py` | `HealthData` | `12989: def fetch( self, mode: str='rows', domain: str='healthdata.gov', dataset_id: str='', select: str='', where: str='', order: str='', group: str='', limit: int=25, offset: int=0, time: int=20 ) -> Dict[ str, Any ] \| None:` | Source-inventoried | [Reference](https://dev.socrata.com/docs/queries/) |
| `fetchers.py` | `GlobalHealthData` | `13396: def fetch( self, mode: str='indicator_registry', query_path: str='', fmt: str='json', time: int=20 ) -> Dict[ str, Any ] \| None:` | Source-inventoried | [Reference](https://www.who.int/data/gho/info/gho-odata-api) |
| `fetchers.py` | `UnitedNations` | `13738: def fetch( self, mode: str='datasets', query_path: str='', time: int=20 ) -> Dict[ str, Any ] \| None:` | Source-inventoried | [Reference](https://unstats.un.org/sdgapi/swagger/) |
| `fetchers.py` | `WorldPopulation` | `14156: def fetch( self, mode: str='catalog', query: str='', asset_path: str='', page: int=1, page_size: int=25, time: int=20 ) -> Dict[ str, Any ] \| None:` | Source-inventoried | [Reference](https://www.worldpop.org/) |
| `fetchers.py` | `Wonder` | `14568: def fetch( self, mode: str='metadata_template', dataset_id: str='D76', request_xml: str='', time: int=20 ) -> Dict[ str, Any ] \| None:` | Source-inventoried | [Reference](https://wonder.cdc.gov/) |
| `fetchers.py` | `USGSEarthquakes` | `15184: def fetch( self, mode: str='feed', feed: str='all_day.geojson', start_date: str='', end_date: str='', min_magnitude: float=1.0, max_magnitude: float=10.0, limit: int=25, order_by: str='time', event_type: str='earthquake', latitude: float \| None = None, longitude: float \| None =` | Source-inventoried | [Reference](https://earthquake.usgs.gov/earthquakes/feed/v1.0/geojson.php) |
| `fetchers.py` | `USGSWaterData` | `16149: def fetch( self, mode: str='monitoring-locations', monitoring_location_id: str='', state_code: str='', county_code: str='', site_type: str='', parameter_code: str='', limit: int=25, time: int=20 ) -> Dict[ str, Any ] \| None:` | Source-inventoried | [Reference](https://api.waterdata.usgs.gov/) |
| `fetchers.py` | `USGSTheNationalMap` | `16822: def fetch( self, mode: str='products', dataset: str='', q: str='', bbox: str='', prod_formats: str='', max_items: int=25, offset: int=0, time: int=20 ) -> Dict[ str, Any ] \| None:` | Source-inventoried | [Reference](https://tnmaccess.nationalmap.gov/) |
| `fetchers.py` | `USGSScienceBase` | `17486: def fetch( self, mode: str='items', q: str='', item_id: str='', max_items: int=25, offset: int=0, fields: str='', time: int=20 ) -> Dict[ str, Any ] \| None:` | Source-inventoried | [Reference](https://www.sciencebase.gov/catalog/) |
| `fetchers.py` | `AirNow` | `18195: def fetch( self, mode: str='current-zip', zip_code: str='', latitude: float \| None = None, longitude: float \| None = None, date: str='', distance: int=25, time: int=20 ) -> Dict[ str, Any ] \| None:` | Source-inventoried | [Reference](https://docs.airnowapi.org/) |
| `fetchers.py` | `ClimateData` | `18824: def fetch( self, mode: str='datasets', keyword: str='', dataset: str='', start_date: str='', end_date: str='', stations: str='', data_types: str='', limit: int=25, offset: int=0, time: int=20 ) -> Dict[ str, Any ] \| None:` | Source-inventoried | [Reference](https://www.ncei.noaa.gov/support/access-data-service-api-user-documentation) |
| `fetchers.py` | `EoNet` | `19447: def fetch( self, mode: str='events', source: str='', category: str='', status: str='open', limit: int=25, days: int=30, start_date: str='', end_date: str='', bbox: str='', time: int=20 ) -> Dict[ str, Any ] \| None:` | Documentation cross-checked | [Reference](https://eonet.gsfc.nasa.gov/docs/v3) |
| `fetchers.py` | `EnviroFacts` | `19999: def fetch( self, table_name: str='TRI_FACILITY', state_code: str='', facility_name: str='', limit: int=25, time: int=20 ) -> Dict[ str, Any ] \| None:` | Source-inventoried | [Reference](https://www.epa.gov/enviro/envirofacts-data-service-api) |
| `fetchers.py` | `TidesAndCurrents` | `20666: def fetch( self, mode: str='water-level', station_id: str='', begin_date: str='', end_date: str='', datum: str='MLLW', units: str='metric', time_zone: str='gmt', interval: str='hilo', time: int=20 ) -> Dict[ str, Any ] \| None:` | Documentation cross-checked | [Reference](https://api.tidesandcurrents.noaa.gov/api/prod/) |
| `fetchers.py` | `UvIndex` | `21310: def fetch( self, mode: str='daily-zip', zip_code: str='', city: str='', state: str='', time: int=20 ) -> Dict[ str, Any ] \| None:` | Source-inventoried | [Reference](https://www.epa.gov/sunsafety/uv-index-api) |
| `fetchers.py` | `PurpleAir` | `21988: def fetch( self, mode: str='sensors', sensor_index: Optional[ int ]=None, nwlng: float \| None = None, nwlat: float \| None = None, selng: float \| None = None, selat: float \| None = None, location_type: int=0, max_age: int=0, modified_since: int=0, time: int=20 ) -> Dict[ str, ` | Source-inventoried | [Reference](https://api.purpleair.com/) |
| `fetchers.py` | `OpenAQ` | `22654: def fetch( self, mode: str='locations', location_id: Optional[ int ]=None, country_id: Optional[ int ]=None, coordinates: str='', radius: int=25000, providers_id: str='', parameters_id: str='', limit: int=25, page: int=1, time: int=20 ) -> Dict[ str, Any ] \| None:` | Source-inventoried | [Reference](https://docs.openaq.org/) |
| `fetchers.py` | `Firms` | `23242: def fetch( self, mode: str='area', source: str='VIIRS_NOAA21_NRT', area_coordinates: str='world', day_range: int=1, date: str='', sensor: str='ALL', time: int=20 ) -> Dict[ str, Any ] \| None:` | Documentation cross-checked | [Reference](https://firms.modaps.eosdis.nasa.gov/api/area) |
| `fetchers.py` | `OpenSky` | `23806: def fetch( self, mode: str='states_bbox', icao24: str='', airport: str='', begin: Optional[ int ]=None, end: Optional[ int ]=None, time_value: Optional[ int ]=None, lamin: float \| None = None, lomin: float \| None = None, lamax: float \| None = None, lomax: float \| None = None,` | Documentation cross-checked | [Reference](https://openskynetwork.github.io/opensky-api/rest.html) |
| `sources.py` | `OpenSkyLive` | `169: def fetch_states( self, latitude: float, longitude: float, radius_degrees: float=2.0 ) -> Dict[ str, Any ]:` | Documentation cross-checked | [Reference](https://openskynetwork.github.io/opensky-api/rest.html) |
| `sources.py` | `AdsbLolMilitary` | `293: def fetch_military( self, latitude: float, longitude: float, radius_nm: float=250.0 ) -> Dict[ str, Any ]:` | Source-inventoried | [Reference](https://api.adsb.lol/) |
| `sources.py` | `AisStreamLive` | `388: def fetch_positions( self, latitude: float, longitude: float, radius_degrees: float=2.0, max_messages: int=100, duration_seconds: float=3.0 ) -> List[ Dict[ str, Any ] ]:` | Documentation cross-checked | [Reference](https://www.aisstream.io/documentation/) |
| `sources.py` | `CelesTrakLive` | `580: def fetch_group( self, group: str, limit: int=250 ) -> List[ Dict[ str, Any ] ]:` | Source-inventoried | [Reference](https://celestrak.org/NORAD/documentation/gp-data-formats.php) |
| `sources.py` | `OverpassClient` | `728: def execute( self, query: str ) -> Dict[ str, Any ]:` | Documentation cross-checked | [Reference](https://wiki.openstreetmap.org/wiki/Overpass_API/Overpass_QL) |
| `sources.py` | `OverpassInfrastructure` | `859: def fetch_infrastructure( self, latitude: float, longitude: float, radius_km: float, categories: List[ str ], max_results: int ) -> Dict[ str, Any ]:` | Documentation cross-checked | [Reference](https://wiki.openstreetmap.org/wiki/Overpass_API/Overpass_QL) |
| `sources.py` | `OverpassCameras` | `1010: def fetch_cameras( self, latitude: float, longitude: float, radius_km: float, categories: List[ str ], max_results: int ) -> Dict[ str, Any ]:` | Documentation cross-checked | [Reference](https://wiki.openstreetmap.org/wiki/Overpass_API/Overpass_QL) |
| `sources.py` | `OverpassMapLayers` | `1174: def fetch_features( self, latitude: float, longitude: float, radius_km: float, categories: List[ str ], max_results: int ) -> Dict[ str, Any ]:` | Documentation cross-checked | [Reference](https://wiki.openstreetmap.org/wiki/Overpass_API/Overpass_QL) |
| `generators.py` | `Grok` | `771: def fetch( self, query: str, model: str='grok-4-fast-reasoning', temperature: float=0.7, max_tokens: int=2048, top_p: float=1.0, seed: int \| None=None, system: str=None, response_format: str=None, reasoning_effort: str=None, web_search: bool=False, search_domains: Any=None, stop` | Source-inventoried | [Reference](https://docs.x.ai/developers/models) |
| `generators.py` | `Gemini` | `1575: def fetch( self, prompt: str, model: str='gemini-2.5-flash', temperature: float=0.7, max_tokens: int=2048, top_p: float=1.0, top_k: int \| None=None, candidate_count: int=1, seed: int \| None=None, system: str=None, response_format: str=None, stop_sequences: Any=None,` | Source-inventoried | [Reference](https://ai.google.dev/gemini-api/docs/models) |
| `generators.py` | `Claude` | `2009: def fetch( self, query: str, model: str='claude-sonnet-4-6', temperature: float=0.7, max_tokens: int=2048, top_p: float=1.0, top_k: int \| None=None, system: str=None, stop_sequences: List[ str ]=None, thinking: bool=False, thinking_budget: int \| None=None, web_search: bool=Fals` | Documentation cross-checked | [Reference](https://docs.anthropic.com/en/docs/about-claude/models) |
| `generators.py` | `Mistral` | `2366: def fetch( self, query: str, model: str='mistral-large-latest', temperature: float=0.7, max_tokens: int=1024, top_p: float=1.0, seed: int \| None=None, safe_mode: bool=False, system: str=None ) -> str \| None:` | Documentation cross-checked | [Reference](https://docs.mistral.ai/models/) |
| `generators.py` | `Chat` | `2985: def fetch( self, prompt: str, model: str='gpt-5-mini', temperature: float=0.7, max_tokens: int=1024, top_p: float=1.0, seed: int \| None=None, system: str=None, response_format: str \| Dict[ str, Any ] = None, reasoning_effort: str=None, web_search: bool=False, search_domains: An` | Source-inventoried | [Reference](https://platform.openai.com/docs/models) |
| `mapping.py` | `Map` | `249: def request( self, endpoint: str, params: Dict[ str, str ] ) -> Dict \| None:` | Source-inventoried | [Reference](https://developers.google.com/maps/documentation/maps-static/start) |
| `mapping.py` | `Geocoder` | Indirect/constructor-only | Source-inventoried | [Reference](https://developers.google.com/maps/documentation/geocoding/requests-geocoding) |
| `mapping.py` | `Place` | Indirect/constructor-only | Source-inventoried | [Reference](https://developers.google.com/maps/documentation/places/web-service/search-text) |
| `mapping.py` | `Timezone` | `1534: def lookup( self, lat: float, lng: float ) -> Dict \| None:` | Source-inventoried | [Reference](https://developers.google.com/maps/documentation/timezone/requests-timezone) |

## Direct HTTP and SDK call-site inventory

This enumerates explicit outgoing operations by source location. Some wrappers issue
multiple requests per logical operation (pagination, retry, split geographic bounds).

| Module | Line | Owning class | Outbound call expression (abbreviated) |
| --- | ---: | --- | --- |
| `fetchers.py` | 375 | `WebFetcher` | `self.response = requests.get( self.uri, timeout=10 )` |
| `fetchers.py` | 409 | `WebFetcher` | `self.response = requests.get( self.uri, timeout=10 )` |
| `fetchers.py` | 444 | `WebFetcher` | `self.response = requests.get( self.uri, timeout=10 )` |
| `fetchers.py` | 486 | `WebFetcher` | `self.response = requests.get( self.uri, timeout=10 )` |
| `fetchers.py` | 520 | `WebFetcher` | `self.response = requests.get( self.uri, timeout=10 )` |
| `fetchers.py` | 555 | `WebFetcher` | `self.response = requests.get( self.uri, timeout=10 )` |
| `fetchers.py` | 589 | `WebFetcher` | `self.response = requests.get( self.uri, timeout=10 )` |
| `fetchers.py` | 623 | `WebFetcher` | `self.response = requests.get( self.uri, timeout=10 )` |
| `fetchers.py` | 657 | `WebFetcher` | `self.response = requests.get( self.uri, timeout=10 )` |
| `fetchers.py` | 691 | `WebFetcher` | `self.response = requests.get( self.uri, timeout=10 )` |
| `fetchers.py` | 905 | `WebCrawler` | `response = requests.get( self.raw_url, headers=self.headers, timeout=self.timeout )` |
| `fetchers.py` | 1613 | `TheNews` | `self.response = requests.get( url=request_url, params=self.params, headers=self.headers,` |
| `fetchers.py` | 1843 | `GoogleSearch` | `self.response = requests.get( url=self.url, params=self.params, headers=self.headers,` |
| `fetchers.py` | 1951 | `GoogleMaps` | `self.response = requests.get( url=self.url, params=self.params, headers=self.headers,` |
| `fetchers.py` | 2006 | `GoogleMaps` | `self.response = requests.get( url=self.url, params=self.params,` |
| `fetchers.py` | 2060 | `GoogleMaps` | `self.response = requests.post( url=self.url, params=self.params,` |
| `fetchers.py` | 2111 | `GoogleMaps` | `self.response = requests.get( url=self.url, params=self.params,` |
| `fetchers.py` | 2380 | `GoogleWeather` | `self.response = requests.get( url=request_url, params=request_params,` |
| `fetchers.py` | 2760 | `NavalObservatory` | `self.response = requests.get( url=self.url, params=self.params,` |
| `fetchers.py` | 3051 | `SatelliteCenter` | `self.response = requests.get( url=request_url, params=self.params, headers=self.headers,` |
| `fetchers.py` | 3310 | `EarthObservatory` | `self.response = requests.get( url=self.url, params=self.params, headers=self.headers,` |
| `fetchers.py` | 3355 | `EarthObservatory` | `self.response = requests.get( url=self.url, params=self.params, headers=self.headers,` |
| `fetchers.py` | 3394 | `EarthObservatory` | `self.response = requests.get( url=self.url, params=self.params, headers=self.headers,` |
| `fetchers.py` | 3440 | `EarthObservatory` | `self.response = requests.get( url=self.url, params=self.params, headers=self.headers,` |
| `fetchers.py` | 3733 | `GlobalImagery` | `self.response = requests.get( self.url, params=self.params,` |
| `fetchers.py` | 3950 | `NearbyObjects` | `self.response = requests.get( url=self.url, params=self.params, headers=self.headers,` |
| `fetchers.py` | 4029 | `NearbyObjects` | `self.response = requests.get( url=self.url, params=self.params, headers=self.headers,` |
| `fetchers.py` | 4105 | `NearbyObjects` | `self.response = requests.get( url=self.url, params=self.params, headers=self.headers,` |
| `fetchers.py` | 4180 | `NearbyObjects` | `self.response = requests.get( url=self.url, params=self.params,` |
| `fetchers.py` | 4235 | `NearbyObjects` | `self.response = requests.get( url=self.url, params=self.params, headers=self.headers,` |
| `fetchers.py` | 4596 | `OpenScience` | `self.response = requests.get( url=self.url, params=self.params, headers=self.headers,` |
| `fetchers.py` | 4638 | `OpenScience` | `self.response = requests.get( url=self.url, params=self.params, headers=self.headers,` |
| `fetchers.py` | 4683 | `OpenScience` | `self.response = requests.get( url=self.url, params=self.params, headers=self.headers,` |
| `fetchers.py` | 4734 | `OpenScience` | `self.response = requests.get(` |
| `fetchers.py` | 5092 | `SpaceWeather` | `self.response = requests.get(` |
| `fetchers.py` | 5468 | `AstroCatalog` | `self.response = requests.get(` |
| `fetchers.py` | 6274 | `StarMap` | `self.response = requests.get(` |
| `fetchers.py` | 6380 | `StarMap` | `self.response = requests.get(` |
| `fetchers.py` | 6489 | `StarMap` | `self.response = requests.get(` |
| `fetchers.py` | 6948 | `GovData` | `self.response = requests.post(` |
| `fetchers.py` | 7003 | `GovData` | `self.response = requests.get( url=self.url, params=self.params, headers=self.headers,` |
| `fetchers.py` | 7068 | `GovData` | `self.response = requests.get(` |
| `fetchers.py` | 7478 | `StarChart` | `self.response = requests.get(` |
| `fetchers.py` | 8382 | `Congress` | `self.response = requests.get(` |
| `fetchers.py` | 8465 | `Congress` | `self.response = requests.get(` |
| `fetchers.py` | 8535 | `Congress` | `self.response = requests.get(` |
| `fetchers.py` | 8605 | `Congress` | `self.response = requests.get(` |
| `fetchers.py` | 8674 | `Congress` | `self.response = requests.get(` |
| `fetchers.py` | 8751 | `Congress` | `self.response = requests.get(` |
| `fetchers.py` | 8820 | `Congress` | `self.response = requests.get(` |
| `fetchers.py` | 9339 | `InternetArchive` | `self.response = requests.get(` |
| `fetchers.py` | 9671 | `OpenWeather` | `self.response = requests.get(` |
| `fetchers.py` | 9757 | `OpenWeather` | `self.response = requests.get(` |
| `fetchers.py` | 9843 | `OpenWeather` | `self.response = requests.get(` |
| `fetchers.py` | 9929 | `OpenWeather` | `self.response = requests.get(` |
| `fetchers.py` | 10351 | `HistoricalWeather` | `self.response = requests.get(` |
| `fetchers.py` | 10442 | `HistoricalWeather` | `self.response = requests.get(` |
| `fetchers.py` | 10838 | `Grokipedia` | `_results = self.client.search(` |
| `fetchers.py` | 10894 | `Grokipedia` | `_result = self.client.get_page(` |
| `fetchers.py` | 11222 | `GoogleGeocoding` | `self.response = requests.get(` |
| `fetchers.py` | 11897 | `CensusData` | `self.response = requests.get(` |
| `fetchers.py` | 11983 | `CensusData` | `self.response = requests.get(` |
| `fetchers.py` | 12371 | `Socrata` | `self.response = requests.get(` |
| `fetchers.py` | 12470 | `Socrata` | `self.response = requests.get(` |
| `fetchers.py` | 12862 | `HealthData` | `self.response = requests.get(` |
| `fetchers.py` | 12961 | `HealthData` | `self.response = requests.get(` |
| `fetchers.py` | 13294 | `GlobalHealthData` | `self.response = requests.get(` |
| `fetchers.py` | 13363 | `GlobalHealthData` | `self.response = requests.get(` |
| `fetchers.py` | 13646 | `UnitedNations` | `self.response = requests.get(` |
| `fetchers.py` | 13705 | `UnitedNations` | `self.response = requests.get(` |
| `fetchers.py` | 13996 | `WorldPopulation` | `self.response = requests.get(` |
| `fetchers.py` | 14063 | `WorldPopulation` | `self.response = requests.get(` |
| `fetchers.py` | 14123 | `WorldPopulation` | `self.response = requests.get(` |
| `fetchers.py` | 14537 | `Wonder` | `self.response = requests.post(` |
| `fetchers.py` | 15027 | `USGSEarthquakes` | `self.response = requests.get(` |
| `fetchers.py` | 15145 | `USGSEarthquakes` | `self.response = requests.get(` |
| `fetchers.py` | 15558 | `USGSWaterData` | `self.response = requests.get(` |
| `fetchers.py` | 16446 | `USGSTheNationalMap` | `self.response = requests.get(` |
| `fetchers.py` | 17094 | `USGSScienceBase` | `self.response = requests.get(` |
| `fetchers.py` | 17797 | `AirNow` | `self.response = requests.get(` |
| `fetchers.py` | 18496 | `ClimateData` | `self.response = requests.get(` |
| `fetchers.py` | 19107 | `EoNet` | `self.response = requests.get(` |
| `fetchers.py` | 19782 | `EnviroFacts` | `self.response = requests.get(` |
| `fetchers.py` | 20255 | `TidesAndCurrents` | `self.response = requests.get(` |
| `fetchers.py` | 20943 | `UvIndex` | `self.response = requests.get(` |
| `fetchers.py` | 21643 | `PurpleAir` | `self.response = requests.get(` |
| `fetchers.py` | 22317 | `OpenAQ` | `self.response = requests.get(` |
| `fetchers.py` | 22959 | `Firms` | `self.response = requests.get(` |
| `fetchers.py` | 23501 | `OpenSky` | `response = requests.post(` |
| `fetchers.py` | 23587 | `OpenSky` | `self.response = requests.get(` |
| `sources.py` | 144 | `OpenSkyLive` | `self.response = requests.post( self.token_url, data=self.token_data,` |
| `sources.py` | 228 | `OpenSkyLive` | `self.response = requests.get( self.states_url, params=self.params,` |
| `sources.py` | 319 | `AdsbLolMilitary` | `self.response = requests.get( self.request_url, timeout=self.timeout )` |
| `sources.py` | 603 | `CelesTrakLive` | `self.response = requests.get( self.url, params=self.params, timeout=self.timeout )` |
| `sources.py` | 759 | `OverpassClient` | `self.response = requests.post( self.url,` |
| `generators.py` | 1649 | `Gemini` | `self.response = self.client.models.generate_content( **self.params )` |
| `generators.py` | 2109 | `Claude` | `self.response = self.client.messages.create( **self.params )` |
| `generators.py` | 2416 | `Mistral` | `self.response = self.client.chat.complete( **self.params )` |
| `generators.py` | 3086 | `Chat` | `self.response = self.client.responses.create( **self.request )` |
| `generators.py` | 3177 | `Chat` | `self.response = self.client.images.generate( model='gpt-image-1',` |
| `generators.py` | 3240 | `Chat` | `self.response = self.client.responses.create( model=self.model, input=self.input )` |
| `generators.py` | 3276 | `Chat` | `uploaded = self.client.files.create( file=stream, purpose='assistants' )` |
| `generators.py` | 3293 | `Chat` | `self.response = self.client.responses.create( model=self.model, input=self.messages )` |
| `generators.py` | 3376 | `Chat` | `self.response = self.client.responses.create( **self.request )` |
| `mapping.py` | 1327 | `Place` | `self.details = self.maps.request( 'place/details/json', self.request ).get( 'result', { } )` |
| `mapping.py` | 1375 | `Place` | `self.search = self.maps.request( 'place/textsearch/json', self.params )` |
| `mapping.py` | 1388 | `Place` | `self.details = self.maps.request( 'place/details/json', self.request ).get( 'result', { } )` |
| `mapping.py` | 1425 | `Place` | `self.search = self.maps.request( 'place/textsearch/json', self.params )` |
| `mapping.py` | 1561 | `Timezone` | `self.data = self.maps.request( 'timezone/json', { 'location': f'{self.latitude},{self.longitude}',` |
| `embedders.py` | 196 | `LocalEmbeddings` | `self.response = self.client.create_embedding( self.texts )` |

## Merge and provider validation

1. Run the complete repository test suite with the project's standard CI environment.
2. Verify zero-location refresh reports Location Required for each local layer, while
   satellites, earthquakes and FIRMS World mode remain callable.
3. Verify normal and date-line AIS, OpenSky and FIRMS request parameters using the
   captured outbound request structure; never log API keys.
4. Verify FIRMS data availability and API key privileges, OpenSky OAuth/rate limits,
   and AIS subscription status in a credentialed integration environment.
5. Distinguish empty geographic samples from rejected requests; do not infer that
   empty public OSM results imply there are no objects in the physical world.
6. Record any provider contract not confirmed in a live integration as **unverified**;
   do not promote source-level assumptions to successful API validation.
