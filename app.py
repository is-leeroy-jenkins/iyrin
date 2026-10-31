'''
******************************************************************************************
 Assembly:                iyr
 Filename:                app.py
 Author:                  Terry D. Eppler (framework) / Assistant (Streamlit UI)
 Created:                 12-27-2025
******************************************************************************************

Purpose:
    Streamlit application exposing iyr geospatial functionality:
        - Geocoding
        - Places Text Search fallback
        - Distance Matrix
        - Static Maps
        - Time Zone lookup
        - Excel / CSV enrichment
    - Flat project layout (no package directory)
    - Maps.__init__(api_key, qps)
    - Places.text_to_location(...) is the ONLY Places lookup method
    - Cache is injected ONLY into services that support it
******************************************************************************************
'''

from __future__ import annotations

from bs4 import BeautifulSoup
from collections import deque, Counter
from exceptions import NotFound
import html as html_lib
import inspect
import json
import os
import tempfile
from typing import Optional
import matplotlib
import pandas as pd
import plotly.graph_objects as go
import pydeck as pdk
import streamlit as st
import streamlit.components.v1 as components
from streamlit_js_eval import get_geolocation
import sqlite3
import re
import datetime as dt
from typing import Optional
import time
from urllib.parse import urljoin, urlparse
from pathlib import Path
import config as cfg
from maps import Maps
from typing import Any, Optional, Dict, List, Tuple
from geocode import Geocoder
from places import Place
from distances import DistanceMatrix
from timezones import Timezone
from staticmaps import StaticMap
from excel import Excel
from caches import InMemoryCache, SQLiteCache
from langchain_core.documents import Document
from lxml import etree
from pipelines import (PdfParser, clear_if_active, clear_loader_documents, promote_loader_documents,
                       initialize_loading_state, sync_mode_document,
                        rebuild_raw_text_from_documents, render_document_processing_actions,
                        render_document_processing_controls, render_document_processing_inputs,
                        render_loading_tabs, render_mode_document_tabs, initialize_mode_document_state,
                        render_source_processing_controls, reset_document_processing_controls,
                        render_web_document_processing)
from world import render_live_world_map, render_live_world_sidebar
from loaders import (TextLoader, CsvLoader, PdfLoader, ExcelLoader, MarkdownLoader,
	HtmlLoader, JsonLoader, WikiLoader, GithubLoader, WebLoader, ArXivLoader,
	XmlLoader, PubMedSearchLoader, OpenCityLoader,
	AwsFileLoader, OneDriveDocLoader, GoogleCloudFileLoader, GoogleSpeechToTextLoader,
	GoogleBucketLoader, AwsBucketLoader, EmailLoader, SpfxLoader, WebCrawler as LoaderWebCrawler)
from generators import Chat, Claude, Gemini, Grok, Mistral
from upload_documents import load_uploaded_document
from fetchers import (GoogleWeather, OpenWeather, HistoricalWeather, ClimateData, TidesAndCurrents,
                      AirNow, UvIndex, OpenAQ, PurpleAir, EnviroFacts, Firms, EoNet,
                      USGSEarthquakes, USGSWaterData, USGSTheNationalMap, GlobalImagery,
                      NavalObservatory, SatelliteCenter, SpaceWeather, AstroCatalog, AstroQuery,
                      StarMap, StarChart, WebFetcher, EarthObservatory, NearbyObjects, OpenScience,
                      USGSScienceBase, CensusData, Socrata, HealthData, GlobalHealthData,
                      UnitedNations, WorldPopulation, Wonder)

# ---------------------------------------------------------------------
# SESSION STATE INITIALIZATION
# ---------------------------------------------------------------------

if 'source' not in st.session_state:
	st.session_state[ 'source' ] = ''

if 'df_source' not in st.session_state:
	st.session_state[ 'df_source' ] = pd.DataFrame( )

if 'df_frame' not in st.session_state:
	st.session_state[ 'df_frame' ] = pd.DataFrame( )

if 'df_default' not in st.session_state:
	st.session_state[ 'df_default' ] = pd.DataFrame( )

if 'df_original' not in st.session_state:
	st.session_state[ 'df_original' ] = pd.DataFrame( )

if 'df_raw' not in st.session_state:
	st.session_state[ 'df_raw' ] = pd.DataFrame( )

if 'df_dataset' not in st.session_state:
	st.session_state[ 'df_dataset' ] = pd.DataFrame( )

if 'active_dataset_name' not in st.session_state:
	st.session_state[ 'active_dataset_name' ] = cfg.DEFAULT_DATA

if 'df_reports_geocode_preview' not in st.session_state:
	st.session_state[ 'df_reports_geocode_preview' ] = pd.DataFrame( )

if 'df_geocoding_map_results' not in st.session_state:
	st.session_state[ 'df_geocoding_map_results' ] = pd.DataFrame( )

if 'pipeline_log' not in st.session_state:
	st.session_state[ 'pipeline_log' ] = [ ]

# ------- Mappy State

if 'mode' not in st.session_state:
	st.session_state[ 'mode' ] = 'Mapping Tools'

if 'previous_mode' not in st.session_state:
	st.session_state[ 'previous_mode' ] = ''

if 'timezone' not in st.session_state:
	st.session_state[ 'timezone' ] = dt.timezone

if 'distances' not in st.session_state:
	st.session_state[ 'distances' ] = None

if 'geocoder' not in st.session_state:
	st.session_state[ 'geocoder' ] = None

if 'places' not in st.session_state:
	st.session_state[ 'places' ] = None

if 'static_maps' not in st.session_state:
	st.session_state[ 'static_maps' ] = None

if 'qps' not in st.session_state:
	st.session_state[ 'qps' ] = 10

# ------------ Location State

if 'coordinates' not in st.session_state:
	st.session_state[ 'coordinates' ] = ( )

if 'latitude' not in st.session_state:
	st.session_state[ 'latitude' ] = 0.0

if 'longitude' not in st.session_state:
	st.session_state[ 'longitude' ] = 0.0

if 'location' not in st.session_state:
	st.session_state[ 'location' ] = ''

if 'country' not in st.session_state:
	st.session_state[ 'country' ] = ''

if 'state' not in st.session_state:
	st.session_state[ 'state' ] = ''

if 'city' not in st.session_state:
	st.session_state[ 'city' ] = ''

if 'zipcode' not in st.session_state:
	st.session_state[ 'zipcode' ] = ''

if 'description' not in st.session_state:
	st.session_state[ 'description' ] = ''

if 'origin' not in st.session_state:
	st.session_state[ 'origin' ] = ''

if 'destination' not in st.session_state:
	st.session_state[ 'destination' ] = ''

if 'radius' not in st.session_state:
	st.session_state[ 'radius' ] = 25.0

if 'zoom' not in st.session_state:
	st.session_state[ 'zoom' ] = 8

if 'map_size' not in st.session_state:
	st.session_state[ 'map_size' ] = '600x400'

if 'year' not in st.session_state:
	st.session_state[ 'year' ] = dt.datetime.now( ).year

if 'month' not in st.session_state:
	st.session_state[ 'month' ] = dt.datetime.now( ).month

if 'day' not in st.session_state:
	st.session_state[ 'day' ] = dt.datetime.now( ).day

if 'calendar_date' not in st.session_state:
	st.session_state[ 'calendar_date' ] = dt.date.today( )
	
if 'browser_geolocation' not in st.session_state:
	st.session_state[ 'browser_geolocation' ] = None

if 'browser_geolocation_loaded' not in st.session_state:
	st.session_state[ 'browser_geolocation_loaded' ] = False

if 'browser_geolocation_enabled' not in st.session_state:
	st.session_state[ 'browser_geolocation_enabled' ] = True

if 'browser_geolocation_reverse_geocoded' not in st.session_state:
	st.session_state[ 'browser_geolocation_reverse_geocoded' ] = False

if 'browser_geolocation_error' not in st.session_state:
	st.session_state[ 'browser_geolocation_error' ] = ''

if 'browser_geolocation_permission_denied' not in st.session_state:
	st.session_state[ 'browser_geolocation_permission_denied' ] = False

if 'geocoded_location' not in st.session_state:
	st.session_state[ 'geocoded_location' ] = ''

if 'geocoded_latitude' not in st.session_state:
	st.session_state[ 'geocoded_latitude' ] = 0.0

if 'geocoded_longitude' not in st.session_state:
	st.session_state[ 'geocoded_longitude' ] = 0.0

if 'active_location_source' not in st.session_state:
	st.session_state[ 'active_location_source' ] = ''

if 'browser_location_signature' not in st.session_state:
	st.session_state[ 'browser_location_signature' ] = ''
	
# ------- API Key State

if 'google_api_key' not in st.session_state:
	st.session_state[ 'google_api_key' ] = ''

if 'google_cse_id' not in st.session_state:
	st.session_state[ 'google_cse_id' ] = ''

if 'googlemaps_api_key' not in st.session_state:
	st.session_state[ 'googlemaps_api_key' ] = ''

if 'geocoding_api_key' not in st.session_state:
	st.session_state[ 'geocoding_api_key' ] = ''

if 'google_cloud_project_id' not in st.session_state:
	st.session_state[ 'google_cloud_project_id' ] = ''

if 'google_cloud_location' not in st.session_state:
	st.session_state[ 'google_cloud_location' ] = ''

if 'google_weather_api_key' not in st.session_state:
	st.session_state[ 'google_weather_api_key' ] = ''

if 'govinfo_api_key' not in st.session_state:
	st.session_state[ 'govinfo_api_key' ] = ''

if 'nasa_api_key' not in st.session_state:
	st.session_state[ 'nasa_api_key' ] = ''

if 'airnow_api_key' not in st.session_state:
	st.session_state[ 'airnow_api_key' ] = ''

if 'openaq_api_key' not in st.session_state:
	st.session_state[ 'openaq_api_key' ] = ''

if 'nasa_earthdata_token' not in st.session_state:
	st.session_state[ 'nasa_earthdata_token' ] = ''

if 'opensky_api_client_id' not in st.session_state:
	st.session_state[ 'opensky_api_client_id' ] = ''

if 'firms_map_key' not in st.session_state:
	st.session_state[ 'firms_map_key' ] = ''

if 'opensky_api_credentials' not in st.session_state:
	st.session_state[ 'opensky_api_credentials' ] = ''

if 'purpleair_api_key' not in st.session_state:
	st.session_state[ 'purpleair_api_key' ] = ''

if st.session_state.google_api_key == '':
	default = cfg.GOOGLE_API_KEY
	if default:
		st.session_state.google_api_key = default
		os.environ[ 'GOOGLE_API_KEY' ] = default

if st.session_state.google_cse_id == '':
	default = cfg.GOOGLE_CSE_ID
	if default:
		st.session_state.google_cse_id = default
		os.environ[ 'GOOGLE_CSE_ID' ] = default

if st.session_state.googlemaps_api_key == '':
	default = cfg.GOOGLEMAPS_API_KEY
	if default:
		st.session_state.googlemaps_api_key = default
		os.environ[ 'GOOGLEMAPS_API_KEY' ] = default

if st.session_state.geocoding_api_key == '':
	default = cfg.GEOCODING_API_KEY
	if default:
		st.session_state.geocoding_api_key = default
		os.environ[ 'GEOCODING_API_KEY' ] = default

if st.session_state.google_cloud_project_id == '':
	default = cfg.GOOGLE_CLOUD_PROJECT_ID
	if default:
		st.session_state.google_cloud_project_id = default
		os.environ[ 'GOOGLE_CLOUD_PROJECT_ID' ] = default

if st.session_state.google_cloud_location == '':
	default = cfg.GOOGLE_CLOUD_LOCATION
	if default:
		st.session_state.google_cloud_location = default
		os.environ[ 'GOOGLE_CLOUD_LOCATION' ] = default

if st.session_state.google_weather_api_key == '':
	default = cfg.GOOGLE_WEATHER_API_KEY
	if default:
		st.session_state.google_weather_api_key = default
		os.environ[ 'GOOGLE_WEATHER_API_KEY' ] = default

if st.session_state.govinfo_api_key == '':
	default = cfg.GOVINFO_API_KEY
	if default:
		st.session_state.govinfo_api_key = default
		os.environ[ 'GOVINFO_API_KEY' ] = default

if st.session_state.nasa_api_key == '':
	default = cfg.NASA_API_KEY
	if default:
		st.session_state.nasa_api_key = default
		os.environ[ 'NASA_API_KEY' ] = default

if st.session_state.airnow_api_key == '':
	default = cfg.AIRNOW_API_KEY
	if default:
		st.session_state.airnow_api_key = default
		os.environ[ 'AIRNOW_API_KEY' ] = default

if st.session_state.openaq_api_key == '':
	default = cfg.OPENAQ_API_KEY
	if default:
		st.session_state.openaq_api_key = default
		os.environ[ 'OPENAQ_API_KEY' ] = default

if st.session_state.nasa_earthdata_token == '':
	default = cfg.NASA_EARTHDATA_TOKEN
	if default:
		st.session_state.nasa_earthdata_token = default
		os.environ[ 'NASA_EARTHDATA_TOKEN' ] = default

if st.session_state.opensky_api_client_id == '':
	default = cfg.OPENSKY_CLIENT_ID
	if default:
		st.session_state.opensky_api_client_id = default
		os.environ[ 'OPENSKY_API_CLIENT_ID' ] = default

if st.session_state.firms_map_key == '':
	default = cfg.FIRMS_MAP_KEY
	if default:
		st.session_state.firms_map_key = default
		os.environ[ 'FIRMS_MAP_KEY' ] = default

if st.session_state.opensky_api_credentials == '':
	default = cfg.OPENSKY_API_CREDENTIALS
	if default:
		st.session_state.opensky_api_credentials = default
		os.environ[ 'OPENSKY_API_CREDENTIALS' ] = default

if st.session_state.purpleair_api_key == '':
	default = getattr( cfg, 'PURPLEAIR_API_KEY', '' )
	if default:
		st.session_state.purpleair_api_key = default
		os.environ[ 'PURPLEAIR_API_KEY' ] = default

initialize_loading_state( )

# ---------------------------------------------------------------------
# UTILITIES
# ---------------------------------------------------------------------

def throw_if( name: str, value: object ) -> None:
	"""Throw if.

	Purpose:
	    Validates that a required argument contains a usable value so failures occur
	    before provider, filesystem, or parsing work begins.

	Args:
	    name (str): Argument name included in validation error messages.
	    value (object): Candidate value to validate or normalize.

	Returns:
	    None: This method updates instance state or validates input and does not return a value.

	Raises:
	    ValueError: Raised when the method cannot satisfy its documented value requirement.
	"""
	if value is None:
		raise ValueError( f'Argument "{name}" cannot be empty!' )
	
	if isinstance( value, str ) and (not value.strip( )):
		raise ValueError( f'Argument "{name}" cannot be empty!' )
	
	if isinstance( value, (list, tuple, dict, set) ) and len( value ) == 0:
		raise ValueError( f'Argument "{name}" cannot be empty!' )

def render_result_metadata( result: Dict[ str, Any ] ) -> None:
	"""
		Purpose:
		--------
		Render common metadata returned by an API fetcher.

		Parameters:
		-----------
		result (Dict[str, Any]): Structured fetcher result.

		Returns:
		--------
		None
	"""
	throw_if( 'result', result )
	metadata = { key: result.get( key ) for key in [ 'source', 'mode', 'status', 'url' ]
		if result.get( key ) not in [ None, '' ] }
	if metadata:
		st.caption( ' | '.join( f'{key.title( )}: {value}' for key, value in metadata.items( ) ) )

def render_summary_kv( title: str, values: Dict[ str, Any ] ) -> None:
	"""
		Purpose:
		--------
		Render a two-column key/value summary table.

		Parameters:
		-----------
		title (str): Markdown heading displayed above the summary.
		values (Dict[str, Any]): Summary values to display.

		Returns:
		--------
		None
	"""
	throw_if( 'title', title )
	throw_if( 'values', values )
	st.markdown( title )
	rows = [ { 'Field': key, 'Value': value } for key, value in values.items( ) ]
	st.data_editor( pd.DataFrame( rows ), use_container_width=True, hide_index=True, disabled=True )

def render_rows_table( title: str, rows: List[ Dict[ str, Any ] ] ) -> None:
	"""
		Purpose:
		--------
		Render structured API rows in a read-only data editor.

		Parameters:
		-----------
		title (str): Markdown heading displayed above the rows.
		rows (List[Dict[str, Any]]): Records to display.

		Returns:
		--------
		None
	"""
	throw_if( 'title', title )
	st.markdown( title )
	if rows:
		st.data_editor( pd.DataFrame( rows ), use_container_width=True, hide_index=True,
			disabled=True )
	else:
		st.info( 'No rows returned.' )

def render_fallback_raw( result: Dict[ str, Any ] ) -> None:
	"""
		Purpose:
		--------
		Expose the complete structured API response for inspection.

		Parameters:
		-----------
		result (Dict[str, Any]): Structured fetcher result.

		Returns:
		--------
		None
	"""
	throw_if( 'result', result )
	with st.expander( 'Raw Response', expanded=False ):
		st.json( result )

def render_html_preview( title: str, html_text: str ) -> None:
	"""
		Purpose:
		--------
		Render returned HTML content in an isolated Streamlit component.

		Parameters:
		-----------
		title (str): Markdown heading displayed above the preview.
		html_text (str): HTML payload to render.

		Returns:
		--------
		None
	"""
	throw_if( 'title', title )
	throw_if( 'html_text', html_text )
	st.markdown( title )
	components.html( html_text, height=500, scrolling=True )

def render_xml_preview( title: str, xml_text: str ) -> None:
	"""
		Purpose:
		--------
		Pretty-print returned XML content.

		Parameters:
		-----------
		title (str): Markdown heading displayed above the preview.
		xml_text (str): XML payload to display.

		Returns:
		--------
		None
	"""
	throw_if( 'title', title )
	throw_if( 'xml_text', xml_text )
	st.markdown( title )
	try:
		root = etree.fromstring( xml_text.encode( 'utf-8' ) )
		formatted = etree.tostring( root, pretty_print=True, encoding='unicode' )
	except Exception:
		formatted = xml_text
	st.code( formatted, language='xml' )

def style_subheaders( ) -> None:
	"""
	
		Purpose:
		_________
		Sets the style of subheaders in the main UI
		
	"""
	st.markdown(
		"""
		<style>
		div[data-testid="stMarkdownContainer"] h2,
		div[data-testid="stMarkdownContainer"] h3,
		div[data-testid="stChatMessage"] div[data-testid="stMarkdownContainer"] h2,
		div[data-testid="stChatMessage"] div[data-testid="stMarkdownContainer"] h3 {
			color: rgb(0, 120, 252) !important;
		}
		</style>
		""",
		unsafe_allow_html=True, )

def init_state( key: str, value: Any ) -> None:
	"""
		
		Purpose:
		--------
		Initialize a Streamlit session-state key only when the key is not already present.
	
		Parameters:
		-----------
		key (str): Session-state key to initialize.
		value (Any): Default value assigned only when the key is absent.
	
		Returns:
		--------
		None
		
	"""
	if key not in st.session_state:
		st.session_state[ key ] = value

def init_env_state( key: str, config_name: str, env_name: str ) -> None:
	"""
		
		Purpose:
		--------
		Initialize a session-state API/configuration key from config.py and mirror the value to
		os.environ when a configured value exists.
	
		Parameters:
		-----------
		key (str): Session-state key to initialize.
		config_name (str): Attribute name to read from config.py.
		env_name (str): Environment variable name to assign.
	
		Returns:
		--------
		None
		
	"""
	init_state( key, '' )
	if st.session_state.get( key, '' ) == '':
		default = getattr( cfg, config_name, '' )
		if default:
			st.session_state[ key ] = default
			os.environ[ env_name ] = default

def normalize( obj ):
	if obj is None or isinstance( obj, (str, int, float, bool) ):
		return obj
	
	if isinstance( obj, dict ):
		return { k: normalize( v ) for k, v in obj.items( ) }
	
	if isinstance( obj, (list, tuple, set) ):
		return [ normalize( v ) for v in obj ]
	if hasattr( obj, "model_dump" ):
		try:
			return obj.model_dump( )
		except Exception:
			return str( obj )
	return str( obj )

def blue_divider( ) -> None:
	st.markdown( cfg.BLUE_DIVIDER, unsafe_allow_html=True )

def log_step( msg: str ) -> None:
	st.session_state.pipeline_log.append( msg )

# ------------- CELESTIAL MAP UTILITY

def render_celestial_map( asset_root: str = 'assets/starmap', height: int = 1400,
		latitude: Optional[ float ] = None, longitude: Optional[ float ] = None,
		location: Optional[ str ] = None, zoom: Optional[ int ] = None ) -> None:
	"""
	
		Purpose:
		--------
		Render the browser-based Celestial Map application inside Streamlit as a
		self-contained HTML component. The function preserves the existing HTML, CSS,
		JavaScript, D3, Leaflet, Pickr, star-map rendering, location picker, star detail
		panel, animation controls, and image-export behavior while loading local JSON data
		from the configured asset folder and passing iyr's observer location into the
		embedded JavaScript application.

		Parameters:
		-----------
		asset_root (str): Root folder containing index.html, style.css, js/main.js,
			js/modules/*.js, and data/*.json.
		height (int): Component iframe height in pixels.
		latitude (Optional[float]): Observer latitude supplied by iyr Location State or
			manual Celestial Map controls.
		longitude (Optional[float]): Observer longitude supplied by iyr Location State or
			manual Celestial Map controls.
		location (Optional[str]): Human-readable observer location label.
		zoom (Optional[int]): Initial Leaflet location-picker zoom level.

		Returns:
		--------
		None
		
	"""
	try:
		root = Path( asset_root )
		index_path = root / 'index.html'
		style_path = root / 'style.css'
		data_paths = { 'constellations': root / 'data' / 'constellations.json',
				'lines': root / 'data' / 'constellations.lines.json',
				'stars': root / 'data' / 'stars.6.json',
				'dsos': root / 'data' / 'dsos.bright.json',
				'starnames': root / 'data' / 'starnames.json',
				'planets': root / 'data' / 'planets.json',
				'mw': root / 'data' / 'mw.json',
				'constellationBorders': root / 'data' / 'constellations.borders.json',
				'dsonames': root / 'data' / 'dsonames.json', }
		
		module_paths = [
				root / 'js' / 'modules' / 'CelestialMath.js',
				root / 'js' / 'modules' / 'StarData.js',
				root / 'js' / 'modules' / 'MapRenderer.js',
				root / 'js' / 'modules' / 'LocationPicker.js',
				root / 'js' / 'modules' / 'UIController.js',
				root / 'js' / 'modules' / 'StarDetailsPanel.js',
				root / 'js' / 'modules' / 'ImageExporter.js',
				root / 'js' / 'main.js', ]
		
		required_paths = [ index_path, style_path, *data_paths.values( ), *module_paths ]
		missing_paths = [ str( path ) for path in required_paths if not path.exists( ) ]
		
		if missing_paths:
			st.error( 'Celestial Map assets are missing.' )
			st.code( '\n'.join( missing_paths ) )
			return
		
		html = index_path.read_text( encoding='utf-8' )
		css = style_path.read_text( encoding='utf-8' )
		
		local_data: Dict[ str, object ] = { }
		for key, path in data_paths.items( ):
			local_data[ key ] = json.loads( path.read_text( encoding='utf-8' ) )
		
		if has_valid_coordinates( latitude, longitude ):
			default_latitude = float( latitude )
			default_longitude = float( longitude )
		else:
			default_latitude = get_global_latitude_default( )
			default_longitude = get_global_longitude_default( )
		
		if location is not None and str( location ).strip( ):
			default_location = str( location ).strip( )
		else:
			default_location = get_global_location_default( )
		
		default_zoom = int( zoom if zoom is not None else st.session_state.get( 'zoom', 8 ) or 8 )
		
		default_payload = { 'latitude': default_latitude, 'longitude': default_longitude,
				'location': default_location, 'zoom': default_zoom, }
		
		html = html.replace( '<link rel="stylesheet" href="style.css">',
			f'<style>\n{css}\n</style>' )
		
		for relative_path in [ 'js/modules/CelestialMath.js', 'js/modules/StarData.js',
				'js/modules/MapRenderer.js', 'js/modules/LocationPicker.js',
				'js/modules/UIController.js', 'js/modules/StarDetailsPanel.js',
				'js/modules/ImageExporter.js', 'js/main.js', ]:
			html = re.sub(
				rf'\s*<script\s+src="{re.escape( relative_path )}"></script>',
				'',
				html,
				flags=re.IGNORECASE )
		
		data_script = (
				'<script>\n'
				'window.StarMapApp = window.StarMapApp || {};\n'
				f'window.StarMapApp.LOCAL_DATA = {json.dumps( local_data )};\n'
				f'window.StarMapApp.DEFAULT_LOCATION = {json.dumps( default_payload )};\n'
				'</script>' )
		
		inline_scripts = [ data_script ]
		
		for path in module_paths:
			source = path.read_text( encoding='utf-8' )
			
			if path.name == 'main.js':
				source = source.replace(
					"this.locationPicker = new LocationPicker('locationPicker', {\n"
					"                onLocationChange: (lat, lon) => this.handleLocationChange(lat, lon)\n"
					"            });",
					"const defaultLocation = window.StarMapApp.DEFAULT_LOCATION || {};\n"
					"            this.locationPicker = new LocationPicker('locationPicker', {\n"
					"                initialLat: defaultLocation.latitude,\n"
					"                initialLon: defaultLocation.longitude,\n"
					"                onLocationChange: (lat, lon) => this.handleLocationChange(lat, lon)\n"
					"            });" )
				
				source = source.replace(
					"this.selectedCoords = { lat: 30.0444, lon: 31.2357 };",
					"this.selectedCoords = {\n"
					"                lat: Number(defaultLocation.latitude || 30.0444),\n"
					"                lon: Number(defaultLocation.longitude || 31.2357)\n"
					"            };" )
				
				source = source.replace(
					"this.locationPicker.setView(this.selectedCoords.lat, this.selectedCoords.lon);",
					"this.locationPicker.setView(\n"
					"                    this.selectedCoords.lat,\n"
					"                    this.selectedCoords.lon,\n"
					"                    Number(defaultLocation.zoom || 8)\n"
					"                );\n"
					"                this.ui.updateLocationDisplay(\n"
					"                    this.selectedCoords.lat,\n"
					"                    this.selectedCoords.lon\n"
					"                );" )
			
			inline_scripts.append( f'<script>\n{source}\n</script>' )
		
		local_data_override = """
		<script>
		(function () {
		    window.StarMapApp = window.StarMapApp || {};
		
		    if (!window.StarMapApp.StarData || !window.StarMapApp.LOCAL_DATA) {
		        return;
		    }
		
		    window.StarMapApp.StarData.prototype.load = async function () {
		        this.data = window.StarMapApp.LOCAL_DATA;
		        return this.data;
		    };
		})();
		</script>
		"""
		
		inline_scripts.append( local_data_override )
		html = html.replace( '</body>', '\n'.join( inline_scripts ) + '\n</body>' )
		
		components.html( html, height=int( height ), scrolling=True )
	
	except Exception as ex:
		st.error( f'Celestial Map failed to render: {ex}' )
		
# ------------- LOCATION STATE UTILITIES

def has_valid_coordinates( latitude: object, longitude: object ) -> bool:
	"""
	
		Purpose:
		--------
		Determine whether latitude and longitude values represent usable coordinates.

		Parameters:
		-----------
		latitude (object): Latitude value to validate.
		longitude (object): Longitude value to validate.

		Returns:
		--------
		bool: True when both values are numeric, within valid geographic ranges, and not
			the placeholder coordinate pair (0, 0).
		
	"""
	try:
		lat_value = float( latitude )
		lon_value = float( longitude )
	except Exception:
		return False
	
	if not (-90.0 <= lat_value <= 90.0):
		return False
	
	if not (-180.0 <= lon_value <= 180.0):
		return False
	
	if lat_value == 0.0 and lon_value == 0.0:
		return False
	
	return True

def has_valid_global_coordinates( ) -> bool:
	"""
	
		Purpose:
		--------
		Determine whether the global Location State contains usable coordinates.

		Parameters:
		-----------
		None

		Returns:
		--------
		bool: True when global latitude and longitude are usable.
		
	"""
	return has_valid_coordinates(
		st.session_state.get( 'latitude', None ),
		st.session_state.get( 'longitude', None ) )

def set_coordinates( latitude: object, longitude: object ) -> None:
	"""
	
		Purpose:
		--------
		Update global latitude, longitude, and coordinates state together.

		Parameters:
		-----------
		latitude (object): Latitude value.
		longitude (object): Longitude value.

		Returns:
		--------
		None
		
	"""
	if not has_valid_coordinates( latitude, longitude ):
		return
	
	lat_value = float( latitude )
	lon_value = float( longitude )
	st.session_state[ 'latitude' ] = lat_value
	st.session_state[ 'longitude' ] = lon_value
	st.session_state[ 'coordinates' ] = (lat_value, lon_value)

def get_location_state( ) -> Dict[ str, object ]:
	"""
	
		Purpose:
		--------
		Return the canonical global Location State values.

		Parameters:
		-----------
		None

		Returns:
		--------
		Dict[str, object]: Dictionary containing global geospatial state values.
		
	"""
	return {
			'coordinates': st.session_state.get( 'coordinates', ( ) ),
			'latitude': st.session_state.get( 'latitude', 0.0 ),
			'longitude': st.session_state.get( 'longitude', 0.0 ),
			'location': st.session_state.get( 'location', '' ),
			'country': st.session_state.get( 'country', '' ),
			'state': st.session_state.get( 'state', '' ),
			'city': st.session_state.get( 'city', '' ),
			'zipcode': st.session_state.get( 'zipcode', '' ),
			'description': st.session_state.get( 'description', '' ),
			'origin': st.session_state.get( 'origin', '' ),
			'destination': st.session_state.get( 'destination', '' ),
			'radius': st.session_state.get( 'radius', 25.0 ),
			'zoom': st.session_state.get( 'zoom', 8 ),
			'map_size': st.session_state.get( 'map_size', '600x400' ),
			'year': st.session_state.get( 'year', dt.datetime.now( ).year ),
			'month': st.session_state.get( 'month', dt.datetime.now( ).month ),
			'day': st.session_state.get( 'day', dt.datetime.now( ).day ),
			'calendar_date': st.session_state.get( 'calendar_date', dt.date.today( ) ),
	}

def set_location_state( location: Optional[ str ] = None, city: Optional[ str ] = None,
		state: Optional[ str ] = None, country: Optional[ str ] = None,
		zipcode: Optional[ str ] = None, description: Optional[ str ] = None,
		latitude: Optional[ float ] = None, longitude: Optional[ float ] = None ) -> None:
	"""
	
		Purpose:
		--------
		Update global Location State values without touching unrelated state keys.

		Parameters:
		-----------
		location (Optional[str]): Freeform location string.
		city (Optional[str]): City value.
		state (Optional[str]): State, province, or region value.
		country (Optional[str]): Country value.
		zipcode (Optional[str]): ZIP or postal code value.
		description (Optional[str]): Description for the current location.
		latitude (Optional[float]): Latitude value.
		longitude (Optional[float]): Longitude value.

		Returns:
		--------
		None
		
	"""
	if location is not None:
		st.session_state[ 'location' ] = str( location ).strip( )
	
	if city is not None:
		st.session_state[ 'city' ] = str( city ).strip( )
	
	if state is not None:
		st.session_state[ 'state' ] = str( state ).strip( )
	
	if country is not None:
		st.session_state[ 'country' ] = str( country ).strip( )
	
	if zipcode is not None:
		st.session_state[ 'zipcode' ] = str( zipcode ).strip( )
	
	if description is not None:
		st.session_state[ 'description' ] = str( description ).strip( )
	
	if latitude is not None and longitude is not None:
		set_coordinates( latitude, longitude )

def compose_location_from_state( ) -> str:
	"""
	
		Purpose:
		--------
		Compose a geocoding query from the canonical global Location State.

		Parameters:
		-----------
		None

		Returns:
		--------
		str: Freeform location query.
		
	"""
	location = str( st.session_state.get( 'location', '' ) ).strip( )
	if location:
		return location
	
	parts = [ ]
	
	for key in [ 'city', 'state', 'zipcode', 'country' ]:
		value = st.session_state.get( key, '' )
		text = str( value ).strip( )
		
		if text and text.lower( ) not in [ 'nan', 'none', 'null' ]:
			parts.append( text )
	
	return ', '.join( parts )

def resolve_table_name( requested: str, tables: List[ str ] ) -> Optional[ str ]:
	"""
	
		Purpose:
		--------
		Resolve a requested SQLite table name using case-insensitive matching.

		Parameters:
		-----------
		requested (str): Requested table name.
		tables (List[str]): Available table names.

		Returns:
		--------
		Optional[str]: Actual table name when found; otherwise None.
		
	"""
	if not requested or not tables:
		return None
	
	for table in tables:
		if table == requested:
			return table
	
	requested_lower = requested.lower( )
	for table in tables:
		if str( table ).lower( ) == requested_lower:
			return table
	
	return None

def get_global_location_default( fallback: str = '' ) -> str:
	"""
	
		Purpose:
		--------
		Return the best available global location text for location-based controls.

		Parameters:
		-----------
		fallback (str): Fallback location text used when global Location State has no
			usable location value.

		Returns:
		--------
		str: Location text suitable for geospatial query controls.
		
	"""
	location = compose_location_from_state( )
	if location:
		return location
	
	return fallback

def get_global_zipcode_default( fallback: str = '20001' ) -> str:
	"""
	
		Purpose:
		--------
		Return the best available global ZIP or postal code value.

		Parameters:
		-----------
		fallback (str): Fallback ZIP or postal code.

		Returns:
		--------
		str: ZIP or postal code value.
		
	"""
	zipcode = str( st.session_state.get( 'zipcode', '' ) ).strip( )
	if zipcode:
		return zipcode
	
	return fallback

def get_global_latitude_default( fallback: float = 0.0 ) -> float:
	"""
	
		Purpose:
		--------
		Return the best available global latitude value.

		Parameters:
		-----------
		fallback (float): Fallback latitude.

		Returns:
		--------
		float: Latitude value.
		
	"""
	if has_valid_global_coordinates( ):
		return float( st.session_state.get( 'latitude', fallback ) )
	
	return float( fallback )

def get_global_longitude_default( fallback: float = 0.0 ) -> float:
	"""
	
		Purpose:
		--------
		Return the best available global longitude value.

		Parameters:
		-----------
		fallback (float): Fallback longitude.

		Returns:
		--------
		float: Longitude value.
		
	"""
	if has_valid_global_coordinates( ):
		return float( st.session_state.get( 'longitude', fallback ) )
	
	return float( fallback )

def set_global_coordinates_from_result( latitude: object, longitude: object,
		location: Optional[ str ]=None, description: Optional[ str ]=None ) -> None:
	"""
	
		Purpose:
		--------
		Update global Location State from a service result when valid coordinates exist.

		Parameters:
		-----------
		latitude (object): Latitude value returned by a service or derived from controls.
		longitude (object): Longitude value returned by a service or derived from controls.
		location (Optional[str]): Optional location text to save globally.
		description (Optional[str]): Optional description of the source result.

		Returns:
		--------
		None
		
	"""
	if not has_valid_coordinates( latitude, longitude ):
		return
	
	set_location_state( location=location, description=description, latitude=float( latitude ),
		longitude=float( longitude ) )

def create_bounding_box_from_center( latitude: object, longitude: object,
		delta: float=0.125 ) -> Dict[ str, float ]:
	"""
	
		Purpose:
		--------
		Create a simple bounding box around a center latitude and longitude.

		Parameters:
		-----------
		latitude (object): Center latitude.
		longitude (object): Center longitude.
		delta (float): Decimal-degree offset used to build the box.

		Returns:
		--------
		Dict[str, float]: Bounding box values with west, south, east, north, northwest,
			and southeast coordinate keys.
		
	"""
	lat_value = get_global_latitude_default( )
	lng_value = get_global_longitude_default( )
	if has_valid_coordinates( latitude, longitude ):
		lat_value = float( latitude )
		lng_value = float( longitude )
	
	return { 'west': lng_value - float( delta ), 'south': lat_value - float( delta ),
			'east': lng_value + float( delta ), 'north': lat_value + float( delta ),
			'nw_lng': lng_value - float( delta ), 'nw_lat': lat_value + float( delta ),
			'se_lng': lng_value + float( delta ), 'se_lat': lat_value - float( delta ),
			'center_lat': lat_value, 'center_lng': lng_value, }

# ------------- BROWSER GEOLOCATION UTILITIES

def get_geolocation_error_message( error_code: object, error_message: object ) -> str:
	"""
	
		Purpose:
		--------
		Convert a browser geolocation error code into a readable application message.

		Parameters:
		-----------
		error_code (object): Browser geolocation error code.
		error_message (object): Browser geolocation error message.

		Returns:
		--------
		str: User-facing error message.
		
	"""
	try:
		code = int( error_code )
	except Exception:
		code = -1
	
	message = str( error_message or '' ).strip( )
	if code == 0:
		return f'Browser does not support geolocation. {message}'.strip( )
	
	if code == 1:
		return f'Browser location permission was denied. {message}'.strip( )
	
	if code == 2:
		return f'Browser position is unavailable. {message}'.strip( )
	
	if code == 3:
		return f'Browser location request timed out. {message}'.strip( )
	
	if message:
		return message
	
	return 'Browser geolocation failed.'

def update_location_state_from_browser_geolocation( geo: Dict[ str, object ] ) -> bool:
	"""
	
		Purpose:
		--------
		Update global Location State from a browser geolocation payload.

		Parameters:
		-----------
		geo (Dict[str, object]): Geolocation payload returned by streamlit-js-eval.

		Returns:
		--------
		bool: True when global coordinates were updated.
		
	"""
	try:
		if not geo:
			return False
		
		if 'error' in geo:
			error = geo.get( 'error', { } )
			error_code = None
			error_message = ''
			if isinstance( error, dict ):
				error_code = error.get( 'code', None )
				error_message = error.get( 'message', '' )
			
			st.session_state[ 'browser_geolocation_error' ] = get_geolocation_error_message(
				error_code, error_message )
			
			if error_code == 1:
				st.session_state[ 'browser_geolocation_permission_denied' ] = True
			
			st.session_state[ 'browser_geolocation_loaded' ] = False
			return False
		
		coords = geo.get( 'coords', { } )
		
		if not coords:
			st.session_state[ 'browser_geolocation_error' ] = (
					'Browser geolocation did not return coordinates.')
			return False
		
		latitude = coords.get( 'latitude', None )
		longitude = coords.get( 'longitude', None )
		accuracy = coords.get( 'accuracy', None )
		
		if not has_valid_coordinates( latitude, longitude ):
			st.session_state[ 'browser_geolocation_error' ] = (
					'Browser geolocation returned invalid coordinates.')
			return False
		
		set_location_state(
			description=f'Browser geolocation. Accuracy: {accuracy} meters.',
			latitude=float( latitude ),
			longitude=float( longitude ) )
		st.session_state[ 'active_location_source' ] = 'browser'
		
		st.session_state[ 'browser_geolocation' ] = geo
		st.session_state[ 'browser_geolocation_loaded' ] = True
		st.session_state[ 'browser_geolocation_permission_denied' ] = False
		st.session_state[ 'browser_geolocation_error' ] = ''
		
		return True
	
	except Exception as ex:
		st.session_state[ 'browser_geolocation_error' ] = str( ex )
		return False

def bootstrap_browser_geolocation( geocoder: Geocoder ) -> None:
	"""
	
		Purpose:
		--------
		Request browser geolocation and keep the canonical global Location State synchronized
		with the browser coordinates before location-dependent modes render.

		Parameters:
		-----------
		geocoder (Geocoder): Existing geocoder instance used to reverse geocode browser coordinates.

		Returns:
		--------
		None
		
	"""
	try:
		if not st.session_state.get( 'browser_geolocation_enabled', True ):
			return
		
		if st.session_state.get( 'browser_geolocation_permission_denied', False ):
			return
		
		browser_loaded = bool( st.session_state.get( 'browser_geolocation_loaded', False ) )
		geo_payload = st.session_state.get( 'browser_geolocation', None ) if browser_loaded else get_geolocation( )
		
		if not geo_payload:
			return
		
		state_changed = False
		if not browser_loaded:
			if not update_location_state_from_browser_geolocation( geo_payload ):
				return
			state_changed = True
		
		coords = geo_payload.get( 'coords', { } ) if isinstance( geo_payload, dict ) else { }
		latitude = coords.get( 'latitude', None )
		longitude = coords.get( 'longitude', None )
		if not has_valid_coordinates( latitude, longitude ):
			return
		
		latitude = float( latitude )
		longitude = float( longitude )
		signature = f'{latitude:.6f},{longitude:.6f}'
		resolved_signature = str( st.session_state.get( 'browser_location_signature', '' ) or '' )
		location_text = str( st.session_state.get( 'location', '' ) or '' ).strip( )
		active_source = str( st.session_state.get( 'active_location_source', '' ) or '' ).strip( )
		needs_resolution = (resolved_signature != signature or not location_text or active_source != 'browser')
		if needs_resolution:
			try:
				result = geocoder.reverse( latitude, longitude ) if geocoder is not None else { }
				result = result or { }
				locality = str( result.get( 'locality', '' ) or '' ).strip( )
				region = str( result.get( 'admin_level_1', '' ) or '' ).strip( )
				location_parts = [ part for part in [ locality, region ] if part ]
				location_text = ', '.join( location_parts )
				if not location_text:
					location_text = str( result.get( 'formatted_address', '' ) or '' ).strip( )
				if not location_text:
					location_text = f'{latitude:.6f}, {longitude:.6f}'
				set_location_state( location=location_text, city=locality, state=region,
					country=str( result.get( 'country_code', '' ) or '' ).strip( ),
					zipcode=str( result.get( 'postal_code', '' ) or '' ).strip( ),
					description='Browser geolocation resolved by reverse geocoding.',
					latitude=latitude, longitude=longitude )
			except Exception:
				set_location_state( location=f'{latitude:.6f}, {longitude:.6f}',
					city='', state='', country='', zipcode='',
					description='Browser geolocation coordinates.',
					latitude=latitude, longitude=longitude )
			
			st.session_state[ 'browser_location_signature' ] = signature
			st.session_state[ 'browser_geolocation_reverse_geocoded' ] = True
			state_changed = True
		else:
			set_coordinates( latitude, longitude )
		
		st.session_state[ 'browser_geolocation' ] = geo_payload
		st.session_state[ 'browser_geolocation_loaded' ] = True
		st.session_state[ 'browser_geolocation_permission_denied' ] = False
		st.session_state[ 'browser_geolocation_error' ] = ''
		st.session_state[ 'active_location_source' ] = 'browser'
		if state_changed:
			st.rerun( )
	
	except Exception as ex:
		st.session_state[ 'browser_geolocation_error' ] = str( ex )

def ensure_active_location_state( ) -> None:
	"""
	
		Purpose:
		--------
		Apply the active-location priority: browser location first and the most recent
		Geocoding result second. Leave location state empty when neither source is available.
	
		Returns:
		--------
		None
		
	"""
	browser_enabled = bool( st.session_state.get( 'browser_geolocation_enabled', True ) )
	browser_loaded = bool( st.session_state.get( 'browser_geolocation_loaded', False ) )
	browser_geo = st.session_state.get( 'browser_geolocation', None )
	if browser_enabled and browser_loaded and isinstance( browser_geo, dict ):
		coords = browser_geo.get( 'coords', { } ) or { }
		browser_latitude = coords.get( 'latitude', None )
		browser_longitude = coords.get( 'longitude', None )
		if has_valid_coordinates( browser_latitude, browser_longitude ):
			browser_latitude = float( browser_latitude )
			browser_longitude = float( browser_longitude )
			location_text = str( st.session_state.get( 'location', '' ) or '' ).strip( )
			if not location_text or st.session_state.get( 'active_location_source', '' ) != 'browser':
				location_text = f'{browser_latitude:.6f}, {browser_longitude:.6f}'
				set_location_state(
					location=location_text, city='', state='', country='', zipcode='',
					description='Browser geolocation coordinates.',
					latitude=browser_latitude, longitude=browser_longitude )
			else:
				set_coordinates( browser_latitude, browser_longitude )
			st.session_state[ 'active_location_source' ] = 'browser'
			return
	
	geocoded_latitude = st.session_state.get( 'geocoded_latitude', 0.0 )
	geocoded_longitude = st.session_state.get( 'geocoded_longitude', 0.0 )
	if has_valid_coordinates( geocoded_latitude, geocoded_longitude ):
		location_text = str( st.session_state.get( 'geocoded_location', '' ) or '' ).strip( )
		if not location_text:
			location_text = f'{float( geocoded_latitude ):.6f}, {float( geocoded_longitude ):.6f}'
		set_location_state(
			location=location_text, city='', state='', country='', zipcode='',
			description='Geocoding mode location fallback.',
			latitude=float( geocoded_latitude ),
			longitude=float( geocoded_longitude ) )
		st.session_state[ 'active_location_source' ] = 'geocoding'
		return
	
	set_location_state( location='', city='', state='', country='', zipcode='', description='' )
	st.session_state[ 'coordinates' ] = ( )
	st.session_state[ 'latitude' ] = 0.0
	st.session_state[ 'longitude' ] = 0.0
	st.session_state[ 'active_location_source' ] = ''

# ------------- VISUALIZATION UTILITIES

def create_reports_map( df: pd.DataFrame, df_overlay: Optional[ pd.DataFrame ]=None,
		use_user_location: bool=True, key_prefix: str='reports_map', source_name: str='' ) -> None:
	"""
	
		Purpose:
		--------
		Render an interactive PyDeck map for records containing Latitude and Longitude fields.
		The map title, filters, tooltip fields, and mapped-record table adapt to known source schemas.

		Parameters:
		-----------
		df (pd.DataFrame): Source DataFrame containing geospatial records.
		df_overlay (Optional[pd.DataFrame]): Optional geocoded records rendered above the base layer.
		use_user_location (bool): Use the global/user location as a fallback map point.
		key_prefix (str): Unique Streamlit widget key prefix for this map instance.
		source_name (str): Active database table or custom dataset name displayed as the map header.

		Returns:
		--------
		None
		
	"""
	try:
		active_source = str( source_name or st.session_state.get( 'active_dataset_name', '' )
			or cfg.DEFAULT_DATA ).strip( )
		st.subheader( active_source )
		
		profiles: Dict[ str, Dict[ str, List[ str ] ] ] = {
			'UAP Sightings': {
				'filters': [ 'Year', 'Country', 'State', 'Shape' ],
				'tooltip': [ 'CalendarDate', 'City', 'State', 'Country', 'Latitude', 'Longitude',
				             'Shape', 'Summary' ],
				'display': [ 'Year', 'Month', 'Day', 'CalendarDate', 'City', 'State', 'Country',
				             'Latitude', 'Longitude', 'Shape', 'Summary' ],
			},
			'Nuclear Sites': {
				'filters': [ 'Name', 'Capacity', 'City', 'State' ],
				'tooltip': [ 'Name', 'Capacity', 'City', 'State', 'Latitude', 'Longitude' ],
				'display': [ 'Name', 'Capacity', 'City', 'State', 'Latitude', 'Longitude' ],
			},
			'Airports': {
				'filters': [ 'Name', 'Identifier', 'Elevation', 'City', 'State' ],
				'tooltip': [ 'Name', 'Identifier', 'Elevation', 'City', 'State', 'Latitude', 'Longitude' ],
				'display': [ 'Name', 'Identifier', 'Elevation', 'City', 'State', 'Latitude', 'Longitude' ],
			},
			'EPA Sites': {
				'filters': [ 'Name', 'City', 'State' ],
				'tooltip': [ 'Name', 'City', 'State', 'Latitude', 'Longitude' ],
				'display': [ 'Name', 'City', 'State', 'Latitude', 'Longitude' ],
			},
		}
		profile = profiles.get( active_source, { } )
		df_source = pd.DataFrame( ) if df is None else df.copy( )
		df_overlay_source = pd.DataFrame( ) if df_overlay is None else df_overlay.copy( )
		required_cols = [ 'Latitude', 'Longitude' ]
		
		if not df_source.empty:
			missing_cols = [ col for col in required_cols if col not in df_source.columns ]
			if missing_cols:
				st.warning( f'Map requires missing column(s): {", ".join( missing_cols )}' )
				return
		
		if not df_overlay_source.empty:
			overlay_missing_cols = [ col for col in required_cols
				if col not in df_overlay_source.columns ]
			if overlay_missing_cols:
				df_overlay_source = pd.DataFrame( )
		
		total_count = len( df_source )
		df_base_map = pd.DataFrame( )
		if not df_source.empty:
			df_source[ 'Latitude' ] = pd.to_numeric( df_source[ 'Latitude' ], errors='coerce' )
			df_source[ 'Longitude' ] = pd.to_numeric( df_source[ 'Longitude' ], errors='coerce' )
			base_mask = (df_source[ 'Latitude' ].notna( )
			             & df_source[ 'Longitude' ].notna( )
			             & df_source[ 'Latitude' ].between( -90.0, 90.0 )
			             & df_source[ 'Longitude' ].between( -180.0, 180.0 )
			             & ~((df_source[ 'Latitude' ] == 0.0)
			                 & (df_source[ 'Longitude' ] == 0.0)))
			df_base_map = df_source.loc[ base_mask ].copy( )
		
		mapped_count = len( df_base_map )
		missing_count = total_count - mapped_count
		df_overlay_map = pd.DataFrame( )
		if not df_overlay_source.empty:
			df_overlay_source[ 'Latitude' ] = pd.to_numeric(
				df_overlay_source[ 'Latitude' ], errors='coerce' )
			df_overlay_source[ 'Longitude' ] = pd.to_numeric(
				df_overlay_source[ 'Longitude' ], errors='coerce' )
			overlay_mask = (df_overlay_source[ 'Latitude' ].notna( )
			                & df_overlay_source[ 'Longitude' ].notna( )
			                & df_overlay_source[ 'Latitude' ].between( -90.0, 90.0 )
			                & df_overlay_source[ 'Longitude' ].between( -180.0, 180.0 )
			                & ~((df_overlay_source[ 'Latitude' ] == 0.0)
			                    & (df_overlay_source[ 'Longitude' ] == 0.0)))
			df_overlay_map = df_overlay_source.loc[ overlay_mask ].copy( )
		
		df_user_map = pd.DataFrame( )
		if use_user_location and df_base_map.empty and df_overlay_map.empty:
			user_latitude = st.session_state.get( 'latitude', None )
			user_longitude = st.session_state.get( 'longitude', None )
			if has_valid_coordinates( user_latitude, user_longitude ):
				user_location = compose_location_from_state( )
				user_description = st.session_state.get( 'description', '' )
				if not user_location:
					user_location = (f'{float( user_latitude ):.4f},'
					                 f'{float( user_longitude ):.4f}')
				df_user_map = pd.DataFrame( [ {
					'CalendarDate': dt.datetime.now( ).strftime( '%Y-%m-%d %H:%M:%S' ),
					'City': user_location,
					'State': '',
					'Country': '',
					'Latitude': float( user_latitude ),
					'Longitude': float( user_longitude ),
					'Shape': 'User Location',
					'Summary': user_description or 'Current user location fallback.',
				} ] )
		
		metric_c1, metric_c2, metric_c3, metric_c4 = st.columns( 4, border=True )
		metric_c1.metric( 'Total Records', f'{total_count:,}' )
		metric_c2.metric( 'Mapped Records', f'{mapped_count:,}' )
		metric_c3.metric( 'Missing / Invalid Coordinates', f'{missing_count:,}' )
		metric_c4.metric( 'Overlay / User Records',
			f'{len( df_overlay_map ) + len( df_user_map ):,}' )
		
		if df_base_map.empty and df_overlay_map.empty and df_user_map.empty:
			st.info( 'No usable base, overlay, or user-location coordinates are available.' )
			return
		
		filter_fields = [ col for col in profile.get( 'filters',
			[ 'Year', 'Country', 'State', 'Shape' ] ) if col in df_base_map.columns ]
		if not df_base_map.empty and filter_fields:
			for row_start in range( 0, len( filter_fields ), 2 ):
				filter_columns = st.columns( 2, border=True )
				for offset, field in enumerate( filter_fields[ row_start: row_start + 2 ] ):
					with filter_columns[ offset ]:
						options = sorted( [ str( value ) for value in
							df_base_map[ field ].dropna( ).unique( ) ] )
						field_key = re.sub( r'[^0-9a-zA-Z_]+', '_', field.lower( ) )
						selected_values = st.multiselect( field, options,
							key=f'{key_prefix}_{field_key}' )
						if selected_values:
							df_base_map = df_base_map[
								df_base_map[ field ].astype( str ).isin( selected_values ) ]
		
		if df_base_map.empty and df_overlay_map.empty and df_user_map.empty:
			st.info( 'No mapped records match the selected filters.' )
			return
		
		map_style_options = {
			'Carto Positron': 'https://basemaps.cartocdn.com/gl/positron-gl-style/style.json',
			'Carto Dark Matter': 'https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json',
			'Carto Voyager': 'https://basemaps.cartocdn.com/gl/voyager-gl-style/style.json',
			'Dark': 'dark', 'Light': 'light', 'Road': 'road', 'Satellite': 'satellite',
			'Dark - No Labels': 'dark_no_labels', 'Light - No Labels': 'light_no_labels',
			'Streamlit Theme': None,
		}
		control_c1, control_c2, control_c3, control_c4 = st.columns(
			[ 0.20, 0.20, 0.30, 0.30 ], border=True )
		with control_c1:
			zoom_level = st.slider( 'Initial Zoom', min_value=0, max_value=50, step=1,
				value=5, key=f'{key_prefix}_zoom' )
		with control_c2:
			point_radius = st.slider( 'Point Radius', min_value=1, max_value=50, value=1,
				step=5, key=f'{key_prefix}_radius' )
		with control_c3:
			selected_map_style = st.selectbox( 'Map Style', list( map_style_options.keys( ) ),
				index=1, key=f'{key_prefix}_style' )
			map_style = map_style_options[ selected_map_style ]
		with control_c4:
			if len( df_base_map ) > 100:
				max_records = st.slider( 'Maximum Records', min_value=100,
					max_value=len( df_base_map ), value=min( 2500, len( df_base_map ) ),
					step=500, key=f'{key_prefix}_limit' )
				df_base_map = df_base_map.head( max_records )
			elif not df_base_map.empty:
				st.caption( f'Displaying all {len( df_base_map ):,} mapped base records.' )
			elif not df_overlay_map.empty:
				st.caption( f'Displaying {len( df_overlay_map ):,} overlay record(s).' )
			else:
				st.caption( 'Displaying current user/global location fallback.' )
		
		tooltip_fields = profile.get( 'tooltip', [ 'City', 'State', 'Country',
			'Latitude', 'Longitude', 'Shape', 'Summary' ] )
		for df_target in [ df_base_map, df_overlay_map, df_user_map ]:
			if df_target.empty:
				continue
			for col in tooltip_fields:
				if col not in df_target.columns:
					df_target[ col ] = ''
			df_target[ 'Position' ] = df_target.apply(
				lambda row: [ float( row[ 'Longitude' ] ), float( row[ 'Latitude' ] ) ], axis=1 )
		
		if not df_base_map.empty:
			df_view = df_base_map
		elif not df_overlay_map.empty:
			df_view = df_overlay_map
		else:
			df_view = df_user_map
		
		view_state = pdk.ViewState( latitude=float( df_view[ 'Latitude' ].median( ) ),
			longitude=float( df_view[ 'Longitude' ].median( ) ), zoom=zoom_level, pitch=0 )
		layers = [ ]
		if not df_base_map.empty:
			layers.append( pdk.Layer( 'ScatterplotLayer', data=df_base_map,
				get_position='Position', get_radius=point_radius,
				get_fill_color=[ 0, 120, 252, 160 ], get_line_color=[ 255, 255, 255, 180 ],
				line_width_min_pixels=1, radius_min_pixels=4, radius_max_pixels=24,
				filled=True, stroked=True, pickable=True ) )
		if not df_overlay_map.empty:
			layers.append( pdk.Layer( 'ScatterplotLayer', data=df_overlay_map,
				get_position='Position', get_radius=max( point_radius * 2, 20000 ),
				get_fill_color=[ 255, 80, 0, 220 ], get_line_color=[ 255, 255, 255, 255 ],
				line_width_min_pixels=2, radius_min_pixels=8, radius_max_pixels=40,
				filled=True, stroked=True, pickable=True ) )
		if not df_user_map.empty:
			layers.append( pdk.Layer( 'ScatterplotLayer', data=df_user_map,
				get_position='Position', get_radius=max( point_radius * 2, 20000 ),
				get_fill_color=[ 0, 180, 80, 230 ], get_line_color=[ 255, 255, 255, 255 ],
				line_width_min_pixels=2, radius_min_pixels=10, radius_max_pixels=42,
				filled=True, stroked=True, pickable=True ) )
		
		labels = { 'CalendarDate': 'Date' }
		tooltip_lines = [ ]
		for field in tooltip_fields:
			label = labels.get( field, field )
			if field == 'Summary':
				tooltip_lines.append(
					'<b>Summary:</b><div style="max-width:320px;white-space:normal;overflow-wrap:anywhere;">{Summary}</div>' )
			else:
				tooltip_lines.append( f'<b>{label}:</b> {{{field}}}<br/>' )
		tooltip = {
			'html': ''.join( tooltip_lines ),
			'style': { 'backgroundColor': 'rgba(0, 0, 0, 0.85)', 'color': 'white',
				'fontSize': '12px' }, }
		blue_divider( )
		deck = pdk.Deck( layers=layers, initial_view_state=view_state,
			map_style=map_style, tooltip=tooltip )
		st.pydeck_chart( deck, use_container_width=True )
		
		show_table = st.checkbox( 'Show mapped records table', value=False,
			key=f'{key_prefix}_show_table' )
		if show_table:
			if df_base_map.empty:
				if not df_user_map.empty:
					st.info( 'No base mapped records are available.' )
					st.data_editor( df_user_map, key=f'{key_prefix}_user_location_table',
						use_container_width=True, disabled=True )
				else:
					st.info( 'No base mapped records are available to display.' )
			else:
				display_cols = [ col for col in profile.get( 'display', list( df_base_map.columns ) )
					if col in df_base_map.columns and col != 'Position' ]
				st.data_editor( df_base_map[ display_cols ], key=f'{key_prefix}_table',
					use_container_width=True, disabled=True )
	
	except Exception as e:
		st.error( f'Interactive map failed: {e}' )

# ------------ GIS MAPPING UTILITIES

def compose_location_query( city: object, state: object, country: object ) -> str:
	"""
	
		Purpose:
		--------
		Compose a clean geocoding query from city, state, and country values.

		Parameters:
		-----------
		city (object): City value from the source row.
		state (object): State, province, region, or equivalent value from the source row.
		country (object): Country value from the source row.

		Returns:
		--------
		str: Comma-delimited location query.
		
	"""
	parts = [ ]
	
	for value in [ city, state, country ]:
		if value is None:
			continue
		
		text = str( value ).strip( )
		if text and text.lower( ) not in [ 'nan', 'none', 'null' ]:
			parts.append( text )
	
	return ', '.join( parts )

def get_value_by_path( obj: object, path: List[ object ] ) -> object:
	"""
	
		Purpose:
		--------
		Read a nested value from dictionaries, lists, tuples, or simple objects using a
		specified lookup path.

		Parameters:
		-----------
		obj (object): Source object to inspect.
		path (List[object]): Lookup path containing dictionary keys, object attributes,
			or integer sequence indexes.

		Returns:
		--------
		object: Resolved value or None.
		
	"""
	current = obj
	
	for key in path:
		if current is None:
			return None
		
		if isinstance( current, dict ):
			current = current.get( key )
			continue
		
		if isinstance( current, (list, tuple) ) and isinstance( key, int ):
			if 0 <= key < len( current ):
				current = current[ key ]
				continue
			return None
		
		if hasattr( current, str( key ) ):
			current = getattr( current, str( key ) )
			continue
		
		return None
	
	return current

def extract_coordinates( result: object ) -> Tuple[ Optional[ float ], Optional[ float ] ]:
	"""
	
		Purpose:
		--------
		Extract latitude and longitude from common geocoding and places response shapes.

		Parameters:
		-----------
		result (object): Geocoder or Places response object.

		Returns:
		--------
		Tuple[Optional[float], Optional[float]]: Latitude and longitude when available.
		
	"""
	if result is None:
		return None, None
	
	lat_paths = [ [ 'lat' ], [ 'latitude' ], [ 'location', 'lat' ], [ 'location', 'latitude' ],
			[ 'geometry', 'location', 'lat' ], [ 'geometry', 'location', 'latitude' ],
			[ 'result', 'geometry', 'location', 'lat' ],
			[ 'results', 0, 'geometry', 'location', 'lat' ],
			[ 'candidates', 0, 'geometry', 'location', 'lat' ], ]
	
	lon_paths = [
			[ 'lng' ],
			[ 'lon' ],
			[ 'longitude' ],
			[ 'location', 'lng' ],
			[ 'location', 'lon' ],
			[ 'location', 'longitude' ],
			[ 'geometry', 'location', 'lng' ],
			[ 'geometry', 'location', 'lon' ],
			[ 'geometry', 'location', 'longitude' ],
			[ 'result', 'geometry', 'location', 'lng' ],
			[ 'results', 0, 'geometry', 'location', 'lng' ],
			[ 'candidates', 0, 'geometry', 'location', 'lng' ],
	]
	
	lat_value = None
	lon_value = None
	for path in lat_paths:
		lat_value = get_value_by_path( result, path )
		if lat_value is not None:
			break
	
	for path in lon_paths:
		lon_value = get_value_by_path( result, path )
		if lon_value is not None:
			break
	
	try:
		latitude = float( lat_value ) if lat_value is not None else None
		longitude = float( lon_value ) if lon_value is not None else None
	except Exception:
		return None, None
	
	if not has_valid_coordinates( latitude, longitude ):
		return None, None
	
	return latitude, longitude

def count_missing_report_coordinate_rows( table_name: str ) -> int:
	"""
	
		Purpose:
		--------
		Count rows in a Reports-like table with missing, invalid, or placeholder
		coordinates.

		Parameters:
		-----------
		table_name (str): SQLite table name to inspect.

		Returns:
		--------
		int: Count of rows requiring coordinate enrichment.
		
	"""
	try:
		throw_if( 'table_name', table_name )
		query = f"""
			SELECT COUNT(*) AS RowCount
			FROM "{table_name}"
			WHERE (
			          Latitude IS NULL
			          OR Longitude IS NULL
			          OR Latitude < -90
			          OR Latitude > 90
			          OR Longitude < -180
			          OR Longitude > 180
			          OR (Latitude = 0 AND Longitude = 0)
			      )
			  AND City IS NOT NULL
			  AND TRIM(City) <> ''
			  AND Country IS NOT NULL
			  AND TRIM(Country) <> '';
		"""
		with create_connection( ) as conn:
			row = conn.execute( query ).fetchone( )
			return int( row[ 0 ] or 0 )
	
	except Exception as e:
		st.error( f'Unable to count missing coordinate rows: {e}' )
		return 0

def read_missing_report_locations( table_name: str, limit: Optional[ int ] = None ) -> pd.DataFrame:
	"""
	
		Purpose:
		--------
		Read distinct City, State, and Country combinations from a Reports-like table
		where coordinates are missing, invalid, or placeholder values.

		Parameters:
		-----------
		table_name (str): SQLite table name to inspect.
		limit (Optional[int]): Optional maximum number of distinct locations to return.

		Returns:
		--------
		pd.DataFrame: Distinct location records requiring geocoding.
		
	"""
	try:
		throw_if( 'table_name', table_name )
		query = f"""
			SELECT
			    TRIM(City) AS City,
			    TRIM(COALESCE(State, '')) AS State,
			    TRIM(Country) AS Country,
			    COUNT(*) AS RowCount
			FROM "{table_name}"
			WHERE (
			          Latitude IS NULL
			          OR Longitude IS NULL
			          OR Latitude < -90
			          OR Latitude > 90
			          OR Longitude < -180
			          OR Longitude > 180
			          OR (Latitude = 0 AND Longitude = 0)
			      )
			  AND City IS NOT NULL
			  AND TRIM(City) <> ''
			  AND Country IS NOT NULL
			  AND TRIM(Country) <> ''
			GROUP BY TRIM(City), TRIM(COALESCE(State, '')), TRIM(Country)
			ORDER BY RowCount DESC, City, State, Country
		"""
		if limit:
			query += f' LIMIT {int( limit )}'
		
		with create_connection( ) as conn:
			return pd.read_sql_query( query, conn )
	
	except Exception as e:
		st.error( f'Unable to read missing report locations: {e}' )
		return pd.DataFrame( )

def preview_report_coordinate_updates( table_name: str, geocoder: Geocoder, places: Place,
		use_places: bool = True, limit: Optional[ int ]=None ) -> pd.DataFrame:
	"""
	
		Purpose:
		--------
		Geocode distinct missing City, State, and Country combinations and return a
		dry-run preview without updating SQLite.

		Parameters:
		-----------
		table_name (str): SQLite table name to inspect.
		geocoder (Geocoder): Existing Geocoder service instance.
		places (Place): Existing Places service instance.
		use_places (bool): Use Places fallback when Geocoder lookup fails.
		limit (Optional[int]): Optional maximum number of distinct locations to process.

		Returns:
		--------
		pd.DataFrame: Preview of proposed coordinate updates.
		
	"""
	try:
		throw_if( 'table_name', table_name )
		throw_if( 'geocoder', geocoder )
		
		df_locations = read_missing_report_locations( table_name, limit )
		
		if df_locations.empty:
			return pd.DataFrame( )
		
		records: List[ Dict[ str, object ] ] = [ ]
		
		for row in df_locations.itertuples( index=False ):
			query = compose_location_query( row.City, row.State, row.Country )
			
			record = {
					'City': row.City,
					'State': row.State,
					'Country': row.Country,
					'Query': query,
					'RowCount': row.RowCount,
					'Latitude': None,
					'Longitude': None,
					'Source': '',
					'Status': '',
					'Message': '',
			}
			
			if not query:
				record[ 'Status' ] = 'Skipped'
				record[ 'Message' ] = 'Location query could not be composed.'
				records.append( record )
				continue
			
			try:
				result = geocoder.freeform( query )
				latitude, longitude = extract_coordinates( result )
				
				if latitude is None or longitude is None:
					raise NotFound( 'No usable coordinates returned by Geocoder.' )
				
				record[ 'Latitude' ] = latitude
				record[ 'Longitude' ] = longitude
				record[ 'Source' ] = 'Geocoder'
				record[ 'Status' ] = 'Matched'
				record[ 'Message' ] = 'Resolved by Geocoder.'
			
			except NotFound as e:
				if use_places and places is not None:
					try:
						result = places.text_to_location( query )
						latitude, longitude = extract_coordinates( result )
						
						if latitude is None or longitude is None:
							record[ 'Source' ] = 'Places'
							record[ 'Status' ] = 'Failed'
							record[ 'Message' ] = 'No usable coordinates returned by Places.'
						else:
							record[ 'Latitude' ] = latitude
							record[ 'Longitude' ] = longitude
							record[ 'Source' ] = 'Places'
							record[ 'Status' ] = 'Matched'
							record[ 'Message' ] = 'Resolved by Places fallback.'
					
					except Exception as ex:
						record[ 'Source' ] = 'Places'
						record[ 'Status' ] = 'Failed'
						record[ 'Message' ] = str( ex )
				else:
					record[ 'Source' ] = 'Geocoder'
					record[ 'Status' ] = 'Failed'
					record[ 'Message' ] = str( e )
			
			except Exception as e:
				record[ 'Source' ] = 'Geocoder'
				record[ 'Status' ] = 'Failed'
				record[ 'Message' ] = str( e )
			
			records.append( record )
		
		return pd.DataFrame( records )
	
	except Exception as e:
		st.error( f'Unable to preview coordinate updates: {e}' )
		return pd.DataFrame( )

def apply_report_coordinate_updates( table_name: str, df_updates: pd.DataFrame ) -> int:
	"""
	
		Purpose:
		--------
		Apply matched latitude and longitude values to all missing-coordinate rows in a
		Reports-like table that share the same City, State, and Country values.

		Parameters:
		-----------
		table_name (str): SQLite table name to update.
		df_updates (pd.DataFrame): Preview DataFrame containing matched coordinates.

		Returns:
		--------
		int: Number of SQLite rows updated.
		
	"""
	try:
		throw_if( 'table_name', table_name )
		
		if df_updates is None or df_updates.empty:
			return 0
		
		required_cols = [ 'City', 'State', 'Country', 'Latitude', 'Longitude', 'Status' ]
		missing_cols = [ col for col in required_cols if col not in df_updates.columns ]
		
		if missing_cols:
			raise ValueError( f'Missing update column(s): {", ".join( missing_cols )}' )
		
		df_apply = df_updates.copy( )
		df_apply = df_apply[ df_apply[ 'Status' ].astype( str ).str.lower( ) == 'matched' ]
		df_apply[ 'Latitude' ] = pd.to_numeric( df_apply[ 'Latitude' ], errors='coerce' )
		df_apply[ 'Longitude' ] = pd.to_numeric( df_apply[ 'Longitude' ], errors='coerce' )
		
		valid_mask = (
				df_apply[ 'Latitude' ].notna( )
				& df_apply[ 'Longitude' ].notna( )
				& df_apply[ 'Latitude' ].between( -90.0, 90.0 )
				& df_apply[ 'Longitude' ].between( -180.0, 180.0 )
				& ~(
				(df_apply[ 'Latitude' ] == 0.0)
				& (df_apply[ 'Longitude' ] == 0.0)
		)
		)
		
		df_apply = df_apply.loc[ valid_mask ].copy( )
		
		if df_apply.empty:
			return 0
		
		updated_count = 0
		with create_connection( ) as conn:
			cursor = conn.cursor( )
			cursor.execute( 'BEGIN' )
			for row in df_apply.itertuples( index=False ):
				cursor.execute(
					f"""
					UPDATE "{table_name}"
					SET Latitude = ?,
					    Longitude = ?
					WHERE (
					          Latitude IS NULL
					          OR Longitude IS NULL
					          OR Latitude < -90
					          OR Latitude > 90
					          OR Longitude < -180
					          OR Longitude > 180
					          OR (Latitude = 0 AND Longitude = 0)
					      )
					  AND TRIM(City) = ?
					  AND TRIM(COALESCE(State, '')) = ?
					  AND TRIM(Country) = ?;
					""",
					(
							float( row.Latitude ),
							float( row.Longitude ),
							str( row.City ).strip( ),
							str( row.State ).strip( ),
							str( row.Country ).strip( ),
					) )
				
				updated_count += int( cursor.rowcount or 0 )
			
			conn.commit( )
		
		return updated_count
	
	except Exception as e:
		st.error( f'Unable to apply coordinate updates: {e}' )
		return 0

def append_geocoding_map_result( query: str, source: str, result: object ) -> None:
	"""
	
		Purpose:
		--------
		Append a resolved geocoding result to the temporary Geocoding Mode map overlay and
		update the global Location State with the resolved coordinates.

		Parameters:
		-----------
		query (str): User-entered location query.
		source (str): Source label such as Geocoder or Places.
		result (object): Raw geocoding response object.

		Returns:
		--------
		None
		
	"""
	try:
		throw_if( 'query', query )
		throw_if( 'source', source )
		
		latitude, longitude = extract_coordinates( result )
		
		if latitude is None or longitude is None:
			st.warning( 'The geocoding result did not contain usable coordinates for the map.' )
			return
		
		resolved_location = query
		if isinstance( result, dict ):
			resolved_location = str( result.get( 'formatted_address', '' ) or query ).strip( )
		st.session_state[ 'geocoded_location' ] = resolved_location
		st.session_state[ 'geocoded_latitude' ] = float( latitude )
		st.session_state[ 'geocoded_longitude' ] = float( longitude )
		
		if not (st.session_state.get( 'browser_geolocation_enabled', True )
				and st.session_state.get( 'browser_geolocation_loaded', False )):
			set_location_state(
				location=resolved_location, city='', state='', country='', zipcode='',
				description=f'{source} result for {query}',
				latitude=latitude,
				longitude=longitude )
			st.session_state[ 'active_location_source' ] = 'geocoding'
		
		df_new = pd.DataFrame(
			[
					{
							'ID': f'GEOCODED-{int( time.time( ) )}',
							'CalendarDate': dt.datetime.now( ).strftime( '%Y-%m-%d %H:%M:%S' ),
							'City': query,
							'State': '',
							'Country': '',
							'Latitude': latitude,
							'Longitude': longitude,
							'Shape': 'Geocoded Result',
							'Summary': f'{source} result for {query}',
							'Source': source,
							'Query': query,
					}
			]
		)
		
		df_current = st.session_state.get( 'df_geocoding_map_results', pd.DataFrame( ) )
		
		if df_current is None or df_current.empty:
			st.session_state[ 'df_geocoding_map_results' ] = df_new
		else:
			st.session_state[ 'df_geocoding_map_results' ] = pd.concat(
				[ df_current, df_new ],
				ignore_index=True )
	
	except Exception as e:
		st.error( f'Unable to append geocoding result to map: {e}' )
		
# ------------ DATABASE UTILITIES

def initialize_database( ) -> None:
	"""
		Purpose:
		--------
		Ensure required SQLite tables exist and that the Prompts table contains the
		columns required by the prompt utilities and Prompt Engineering mode.

		Parameters:
		-----------
		None

		Returns:
		--------
		None
	"""
	Path( 'stores/sqlite' ).mkdir( parents=True, exist_ok=True )
	with sqlite3.connect( cfg.DB_PATH ) as conn:
		conn.execute(
			"""
            CREATE TABLE IF NOT EXISTS chat_history
            (
                id
                INTEGER
                PRIMARY
                KEY
                AUTOINCREMENT,
                role
                TEXT,
                content
                TEXT
            )
			"""
		)
		
		conn.execute(
			"""
            CREATE TABLE IF NOT EXISTS embeddings
            (
                id
                INTEGER
                PRIMARY
                KEY
                AUTOINCREMENT,
                chunk
                TEXT,
                vector
                BLOB
            )
			"""
		)
		
		conn.execute(
			"""
            CREATE TABLE IF NOT EXISTS Prompts
            (
                PromptsId
                INTEGER
                NOT
                NULL
                PRIMARY
                KEY
                AUTOINCREMENT,
                Caption
                TEXT,
                Name
                TEXT
            (
                80
            ),
                Text TEXT,
                Version TEXT
            (
                80
            ),
                ID TEXT
            (
                80
            )
                )
			"""
		)
		
		prompt_columns = [ row[ 1 ] for row in
		                   conn.execute( 'PRAGMA table_info("Prompts");' ).fetchall( ) ]
		
		if 'Caption' not in prompt_columns:
			conn.execute( 'ALTER TABLE "Prompts" ADD COLUMN "Caption" TEXT;' )
		
		conn.commit( )

# Initialize the writable database before the application reads its tables.
initialize_database( )

def create_connection( ) -> sqlite3.Connection:
	return sqlite3.connect( cfg.DB_PATH )

def list_tables( ) -> List[ str ]:
	with create_connection( ) as conn:
		_query = "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;"
		rows = conn.execute( _query ).fetchall( )
		return [ r[ 0 ] for r in rows ]

def create_schema( table: str ) -> List[ Tuple ]:
	with create_connection( ) as conn:
		return conn.execute( f'PRAGMA table_info("{table}");' ).fetchall( )

def read_table( table: str, limit: int = None, offset: int = 0 ) -> pd.DataFrame:
	"""
	
		Purpose:
		--------
		Read a SQLite table into a pandas DataFrame using a normalized scalar-only path.
	
		Parameters:
		-----------
		table : str
			Table name.
		limit : int = None
			Optional row limit.
		offset : int = 0
			Optional row offset.
	
		Returns:
		--------
		pd.DataFrame
			DataFrame of plain Python scalar values.
	
	"""
	if not table:
		return pd.DataFrame( )
	
	query = f'SELECT * FROM "{table}"'
	if limit:
		query += f' LIMIT {int( limit )} OFFSET {int( offset )}'
	
	with create_connection( ) as conn:
		cur = conn.cursor( )
		cur.execute( query )
		
		raw_columns = [ d[ 0 ] for d in (cur.description or [ ]) ]
		rows = cur.fetchall( )
	
	seen: Dict[ str, int ] = { }
	columns: List[ str ] = [ ]
	
	for col in raw_columns:
		name = str( col )
		if name not in seen:
			seen[ name ] = 0
			columns.append( name )
		else:
			seen[ name ] += 1
			columns.append( f'{name}_{seen[ name ]}' )
	
	def _scalarize( value: Any ) -> Any:
		if value is None or isinstance( value, (str, int, float, bool) ):
			return value
		
		if isinstance( value, bytes ):
			try:
				return value.decode( 'utf-8' )
			except Exception:
				return value.hex( )
		
		if isinstance( value, (list, tuple, set, dict) ):
			try:
				return str( normalize( value ) )
			except Exception:
				return str( value )
		
		if hasattr( value, 'model_dump' ):
			try:
				return str( value.model_dump( ) )
			except Exception:
				return str( value )
		
		return str( value )
	
	normalized_rows: List[ Dict[ str, Any ] ] = [ ]
	for row in rows:
		record: Dict[ str, Any ] = { }
		for idx, col in enumerate( columns ):
			record[ col ] = _scalarize( row[ idx ] )
		normalized_rows.append( record )
	
	return pd.DataFrame( normalized_rows, columns=columns )

def render_table( df: pd.DataFrame ) -> None:
	"""
	
		Purpose:
		--------
		Render a DataFrame safely in Streamlit. Use the normal interactive dataframe
		first, and fall back to HTML rendering if Streamlit/PyArrow serialization fails.
	
		Parameters:
		-----------
		df : pd.DataFrame
			The DataFrame to render.
	
		Returns:
		--------
		None
	
	"""
	if df is None:
		st.info( 'No data available.' )
		return
	
	try:
		st.data_editor( df, use_container_width=True )
		return
	except Exception:
		pass
	
	fallback_df = df.copy( )
	fallback_df = fallback_df.where( pd.notnull( fallback_df ), '' )
	
	for col in fallback_df.columns:
		fallback_df[ col ] = fallback_df[ col ].map(
			lambda x: x if isinstance( x, (str, int, float, bool) ) or x == '' else str( x ) )
	
	st.markdown( fallback_df.to_html( index=False, escape=True ), unsafe_allow_html=True )

def make_display_safe( df: pd.DataFrame ) -> pd.DataFrame:
	display_df = df.copy( )
	for col in display_df.columns:
		display_df[ col ] = display_df[ col ].map( lambda x: '' if x is None else str( x ) )
	
	return display_df

def drop_table( table: str ) -> None:
	"""
		Purpose:
		--------
		Safely drop a table if it exists.
	
		Parameters:
		-----------
		table : str
			Table name.
	"""
	if not table:
		return
	
	with create_connection( ) as conn:
		conn.execute( f'DROP TABLE IF EXISTS "{table}";' )
		conn.commit( )

def create_index( table: str, column: str ) -> None:
	"""
		Purpose:
		--------
		Create a safe SQLite index on a specified table column.
	
		Handles:
			- Spaces in column names
			- Special characters
			- Reserved words
			- Duplicate index names
			- Validation against actual table schema
	
		Parameters:
		-----------
		table : str
			Table name.
		column : str
			Column name to index.
	"""
	if not table or not column:
		return
	
	# ------------------------------------------------------------------
	# Validate table exists
	# ------------------------------------------------------------------
	tables = list_tables( )
	if table not in tables:
		raise ValueError( 'Invalid table name.' )
	
	# ------------------------------------------------------------------
	# Validate column exists
	# ------------------------------------------------------------------
	schema = create_schema( table )
	valid_columns = [ col[ 1 ] for col in schema ]
	
	if column not in valid_columns:
		raise ValueError( 'Invalid column name.' )
	
	# ------------------------------------------------------------------
	# Sanitize index name (identifier only)
	# ------------------------------------------------------------------
	safe_index_name = re.sub( r"[^0-9a-zA-Z_]+", "_", f"idx_{table}_{column}" )
	
	# ------------------------------------------------------------------
	# Create index safely (quote identifiers)
	# ------------------------------------------------------------------
	sql = f'CREATE INDEX IF NOT EXISTS "{safe_index_name}" ON "{table}"("{column}");'
	
	with create_connection( ) as conn:
		conn.execute( sql )
		conn.commit( )

def apply_filters( df: pd.DataFrame ) -> pd.DataFrame:
	st.subheader( 'Advanced Filters' )
	conditions = [ ]
	col1, col2, col3 = st.columns( 3 )
	column = col1.selectbox( 'Column', df.columns )
	operator = col2.selectbox( 'Operator', [ '=', '!=', '>', '<', '>=', '<=', 'contains' ] )
	value = col3.text_input( 'Value' )
	if value:
		if operator == '=':
			df = df[ df[ column ] == value ]
		elif operator == '!=':
			df = df[ df[ column ] != value ]
		elif operator == '>':
			df = df[ df[ column ].astype( float ) > float( value ) ]
		elif operator == '<':
			df = df[ df[ column ].astype( float ) < float( value ) ]
		elif operator == '>=':
			df = df[ df[ column ].astype( float ) >= float( value ) ]
		elif operator == '<=':
			df = df[ df[ column ].astype( float ) <= float( value ) ]
		elif operator == 'contains':
			df = df[ df[ column ].astype( str ).str.contains( value ) ]
	
	return df

def create_aggregation( df: pd.DataFrame ):
	st.subheader( 'Aggregation Engine' )
	
	numeric_cols = df.select_dtypes( include=[ 'number' ] ).columns.tolist( )
	
	if not numeric_cols:
		st.info( 'No numeric columns available.' )
		return
	
	col = st.selectbox( 'Column', numeric_cols )
	agg = st.selectbox( 'Aggregation', [ 'COUNT', 'SUM', 'AVG', 'MIN', 'MAX', 'MEDIAN' ] )
	
	if agg == 'COUNT':
		result = df[ col ].count( )
	elif agg == 'SUM':
		result = df[ col ].sum( )
	elif agg == 'AVG':
		result = df[ col ].mean( )
	elif agg == 'MIN':
		result = df[ col ].min( )
	elif agg == 'MAX':
		result = df[ col ].max( )
	elif agg == 'MEDIAN':
		result = df[ col ].median( )
	
	st.metric( 'Result', result )

def create_visualization( df: pd.DataFrame ) -> None:
	"""
	
		Purpose:
		--------
		Render data visualizations without passing pandas objects directly into
		Plotly/Narwhals.
		
		Parameters:
		-----------
		df : pd.DataFrame
			The input DataFrame.
		
		Returns:
		--------
		None
		
	"""
	
	blue_divider( )
	st.markdown( '##### Visualization Engine' )
	if df is None or df.empty:
		st.info( 'No data available.' )
		return
	
	df_plot = df.copy( )
	for col in df_plot.columns:
		if df_plot[ col ].dtype == object:
			df_plot[ col ] = df_plot[ col ].map( lambda x: '' if x is None else str( x ) )
	
	numeric_cols: List[ str ] = [ ]
	for col in df_plot.columns:
		series_num = pd.to_numeric( df_plot[ col ], errors='coerce' )
		if series_num.notna( ).any( ):
			numeric_cols.append( col )
	
	categorical_cols: List[ str ] = [ col for col in df_plot.columns if col not in numeric_cols ]
	chart = st.selectbox( 'Chart Type',
		[ 'Histogram', 'Bar', 'Line', 'Scatter', 'Box', 'Pie', 'Correlation' ] )
	
	if chart == 'Histogram':
		if not numeric_cols:
			st.info( 'No numeric columns available.' )
			return
		
		col = st.selectbox( 'Column', numeric_cols )
		values = pd.to_numeric( df_plot[ col ], errors='coerce' ).dropna( ).tolist( )
		fig = go.Figure( data=[ go.Histogram( x=values ) ] )
		fig.update_layout( xaxis_title=col, yaxis_title='Count' )
		st.plotly_chart( fig, use_container_width=True )
	
	elif chart == 'Bar':
		if not numeric_cols:
			st.info( 'No numeric columns available.' )
			return
		
		x = st.selectbox( 'X', df_plot.columns )
		y = st.selectbox( 'Y', numeric_cols )
		x_values = df_plot[ x ].astype( str ).tolist( )
		y_values = pd.to_numeric( df_plot[ y ], errors='coerce' ).fillna( 0 ).tolist( )
		fig = go.Figure( data=[ go.Bar( x=x_values, y=y_values ) ] )
		fig.update_layout( xaxis_title=x, yaxis_title=y )
		st.plotly_chart( fig, use_container_width=True )
	
	elif chart == 'Line':
		if not numeric_cols:
			st.info( 'No numeric columns available.' )
			return
		
		x = st.selectbox( 'X', df_plot.columns )
		y = st.selectbox( 'Y', numeric_cols )
		x_values = df_plot[ x ].astype( str ).tolist( )
		y_values = pd.to_numeric( df_plot[ y ], errors='coerce' ).fillna( 0 ).tolist( )
		fig = go.Figure( data=[ go.Scatter( x=x_values, y=y_values, mode='lines' ) ] )
		fig.update_layout( xaxis_title=x, yaxis_title=y )
		st.plotly_chart( fig, use_container_width=True )
	
	elif chart == 'Scatter':
		if len( numeric_cols ) < 2:
			st.info( 'At least two numeric columns are required.' )
			return
		
		x = st.selectbox( 'X', numeric_cols, key='viz_scatter_x' )
		y = st.selectbox( 'Y', numeric_cols, key='viz_scatter_y' )
		x_series = pd.to_numeric( df_plot[ x ], errors='coerce' )
		y_series = pd.to_numeric( df_plot[ y ], errors='coerce' )
		mask = x_series.notna( ) & y_series.notna( )
		x_values = x_series[ mask ].tolist( )
		y_values = y_series[ mask ].tolist( )
		fig = go.Figure( data=[ go.Scatter( x=x_values, y=y_values, mode='markers' ) ] )
		fig.update_layout( xaxis_title=x, yaxis_title=y )
		st.plotly_chart( fig, use_container_width=True )
	
	elif chart == 'Box':
		if not numeric_cols:
			st.info( 'No numeric columns available.' )
			return
		
		col = st.selectbox( 'Column', numeric_cols, key='viz_box_col' )
		values = pd.to_numeric( df_plot[ col ], errors='coerce' ).dropna( ).tolist( )
		fig = go.Figure( data=[ go.Box( y=values, name=col ) ] )
		fig.update_layout( yaxis_title=col )
		st.plotly_chart( fig, use_container_width=True )
	
	elif chart == 'Pie':
		if not categorical_cols:
			st.info( 'No categorical columns available.' )
			return
		
		col = st.selectbox( 'Category Column', categorical_cols )
		counts = df_plot[ col ].astype( str ).value_counts( )
		fig = go.Figure( data=[ go.Pie( labels=counts.index.tolist( ),
			values=counts.values.tolist( ) ) ] )
		st.plotly_chart( fig, use_container_width=True )
	
	elif chart == 'Correlation':
		if len( numeric_cols ) < 2:
			st.info( 'At least two numeric columns are required.' )
			return
		
		corr_df = pd.DataFrame( )
		for col in numeric_cols:
			corr_df[ col ] = pd.to_numeric( df_plot[ col ], errors='coerce' )
		
		corr = corr_df.corr( )
		fig = go.Figure( data=[ go.Heatmap( z=corr.values.tolist( ), x=corr.columns.tolist( ),
				y=corr.index.tolist( ) ) ] )
		st.plotly_chart( fig, use_container_width=True )

def convert_dataframe( table_name: str, df: pd.DataFrame ):
	columns = [ ]
	for col in df.columns:
		sql_type = get_sqlite_type( df[ col ].dtype )
		safe_col = col.replace( ' ', '_' )
		columns.append( f'{safe_col} {sql_type}' )
	
	create_stmt = f'CREATE TABLE IF NOT EXISTS {table_name} ({", ".join( columns )});'
	with create_connection( ) as conn:
		conn.execute( create_stmt )
		conn.commit( )

def insert_data( table_name: str, df: pd.DataFrame ):
	df = df.copy( )
	df.columns = [ c.replace( ' ', '_' ) for c in df.columns ]
	placeholders = ', '.join( [ '?' ] * len( df.columns ) )
	stmt = f'INSERT INTO {table_name} VALUES ({placeholders});'
	with create_connection( ) as conn:
		conn.executemany( stmt, df.values.tolist( ) )
		conn.commit( )

def get_sqlite_type( dtype ) -> str:
	"""
		Purpose:
		--------
		Map a pandas dtype to an appropriate SQLite column type.
	
		Parameters:
		-----------
		dtype : pandas dtype
			The dtype of a pandas Series.
	
		Returns:
		--------
		str
			SQLite column type.
	"""
	dtype_str = str( dtype ).lower( )
	
	# ------------------------------------------------------------------
	# Integer Types (including nullable Int64)
	# ------------------------------------------------------------------
	if 'int' in dtype_str:
		return 'INTEGER'
	
	# ------------------------------------------------------------------
	# Float Types
	# ------------------------------------------------------------------
	if 'float' in dtype_str:
		return 'REAL'
	
	# ------------------------------------------------------------------
	# Boolean
	# ------------------------------------------------------------------
	if 'bool' in dtype_str:
		return 'INTEGER'
	
	# ------------------------------------------------------------------
	# Datetime
	# ------------------------------------------------------------------
	if 'datetime' in dtype_str:
		return 'TEXT'
	
	# ------------------------------------------------------------------
	# Categorical
	# ------------------------------------------------------------------
	if 'category' in dtype_str:
		return 'TEXT'
	
	# ------------------------------------------------------------------
	# Default fallback
	# ------------------------------------------------------------------
	return 'TEXT'

def create_custom_table( table_name: str, columns: list ) -> None:
	"""
		Purpose:
		--------
		Create a custom SQLite table from column definitions.
	
		Parameters:
		-----------
		table_name : str
			Name of table.
	
		columns : list of dict
			[
				{
					"name": str,
					"type": str,
					"not_null": bool,
					"primary_key": bool,
					"auto_increment": bool
				}
			]
	"""
	if not table_name:
		raise ValueError( 'Table name required.' )
	
	# Validate identifier
	if not re.match( r"^[A-Za-z_][A-Za-z0-9_]*$", table_name ):
		raise ValueError( 'Invalid table name.' )
	
	col_defs = [ ]
	
	for col in columns:
		col_name = col[ 'name' ]
		col_type = col[ 'type' ].upper( )
		
		if not re.match( r"^[A-Za-z_][A-Za-z0-9_]*$", col_name ):
			raise ValueError( f"Invalid column name: {col_name}" )
		
		definition = f'"{col_name}" {col_type}'
		
		if col[ 'primary_key' ]:
			definition += ' PRIMARY KEY'
			if col[ 'auto_increment' ] and col_type == 'INTEGER':
				definition += ' AUTOINCREMENT'
		
		if col[ "not_null" ]:
			definition += " NOT NULL"
		
		col_defs.append( definition )
	
	sql = f'CREATE TABLE IF NOT EXISTS "{table_name}" ({", ".join( col_defs )});'
	
	with create_connection( ) as conn:
		conn.execute( sql )
		conn.commit( )

def is_safe_query( query: str ) -> bool:
	"""
	
		Purpose:
		--------
		Determine whether a SQL query is read-only and safe to execute.
	
		Allows:
			SELECT
			WITH (CTE returning SELECT)
			EXPLAIN SELECT
			PRAGMA (read-only)
	
		Blocks:
			INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, ATTACH,
			DETACH, VACUUM, REPLACE, TRIGGER, and multiple statements.
			
	"""
	if not query or not isinstance( query, str ):
		return False
	
	q = query.strip( ).lower( )
	
	# ------------------------------------------------------------------
	# Block multiple statements
	# ------------------------------------------------------------------
	if ';' in q[ :-1 ]:
		return False
	
	# ------------------------------------------------------------------
	# Remove SQL comments
	# ------------------------------------------------------------------
	q = re.sub( r"--.*?$", "", q, flags=re.MULTILINE )
	q = re.sub( r"/\*.*?\*/", "", q, flags=re.DOTALL )
	q = q.strip( )
	
	# ------------------------------------------------------------------
	# Allowed starting keywords
	# ------------------------------------------------------------------
	allowed_starts = ('select', 'with', 'explain', 'pragma')
	if not q.startswith( allowed_starts ):
		return False
	
	# ------------------------------------------------------------------
	# Block dangerous keywords anywhere
	# ------------------------------------------------------------------
	blocked_keywords = ('insert ', 'update ', 'delete ', 'drop ', 'alter ',
	                    'create ', 'attach ', 'detach ', 'vacuum ', 'replace ', 'trigger ')
	
	for keyword in blocked_keywords:
		if keyword in q:
			return False
	
	return True

def create_identifier( name: str ) -> str:
	"""
	
		Purpose:
		--------
		Sanitize a string into a safe SQLite identifier.
	
		- Replaces invalid characters with underscores
		- Ensures it starts with a letter or underscore
		- Prevents empty names
		
	"""
	if not name or not isinstance( name, str ):
		raise ValueError( 'Invalid Identifier.' )
	
	safe = re.sub( r'[^0-9a-zA-Z_]', '_', name.strip( ) )
	if not re.match( r'^[A-Za-z_]', safe ):
		safe = f'_{safe}'
	
	if not safe:
		raise ValueError( 'Invalid identifier after sanitization.' )
	
	return safe

def get_indexes( table: str ):
	with create_connection( ) as conn:
		rows = conn.execute( f'PRAGMA index_list("{table}");' ).fetchall( )
		return rows

def add_column( table: str, column: str, col_type: str ):
	column = create_identifier( column )
	col_type = col_type.upper( )
	
	with create_connection( ) as conn:
		conn.execute(
			f'ALTER TABLE "{table}" ADD COLUMN "{column}" {col_type};' )
		conn.commit( )

def rename_column( table_name: str, old_name: str, new_name: str ) -> None:
	"""
	
		Purpose:
		--------
		Rename a column within an existing SQLite table. Attempts native ALTER TABLE rename
		first; if it fails, falls back to a schema-safe rebuild preserving column order, data,
		and indexes.

		Parameters:
		-----------
		table_name : str
			Table containing the column.

		old_name : str
			Existing column name.

		new_name : str
			New column name.

		Returns:
		--------
		None
		
	"""
	if not table_name or not old_name or not new_name:
		return
	
	with create_connection( ) as conn:
		try:
			conn.execute(
				f'ALTER TABLE "{table_name}" RENAME COLUMN "{old_name}" TO "{new_name}";'
			)
			conn.commit( )
			return
		except Exception:
			pass
		
		row = conn.execute(
			"""
            SELECT sql
            FROM sqlite_master
            WHERE type ='table' AND name =?
			""",
			(table_name,)
		).fetchone( )
		
		if not row or not row[ 0 ]:
			raise ValueError( "Table definition not found." )
		
		create_sql = row[ 0 ]
		
		indexes = conn.execute(
			"""
            SELECT sql
            FROM sqlite_master
            WHERE type ='index' AND tbl_name=? AND sql IS NOT NULL
			""",
			(table_name,)
		).fetchall( )
		
		schema = conn.execute( f'PRAGMA table_info("{table_name}");' ).fetchall( )
		cols = [ r[ 1 ] for r in schema ]
		if old_name not in cols:
			raise ValueError( "Column not found." )
		
		mapped_cols = [ (new_name if c == old_name else c) for c in cols ]
		
		temp_table = f"{table_name}__rebuild_temp"
		
		col_defs: List[ str ] = [ ]
		pk_cols = [ r for r in schema if int( r[ 5 ] or 0 ) > 0 ]
		single_pk = len( pk_cols ) == 1
		
		for row in schema:
			col_name = row[ 1 ]
			col_type = row[ 2 ] or ''
			not_null = int( row[ 3 ] or 0 )
			default_value = row[ 4 ]
			pk = int( row[ 5 ] or 0 )
			
			out_name = new_name if col_name == old_name else col_name
			col_def = f'"{out_name}" {col_type}'.strip( )
			
			if not_null:
				col_def += ' NOT NULL'
			
			if default_value is not None:
				col_def += f' DEFAULT {default_value}'
			
			if single_pk and pk == 1:
				col_def += ' PRIMARY KEY'
			
			col_defs.append( col_def )
		
		new_create_sql = f'CREATE TABLE "{temp_table}" ({", ".join( col_defs )});'
		
		old_select = ", ".join( [ f'"{c}"' for c in cols ] )
		new_insert = ", ".join( [ f'"{c}"' for c in mapped_cols ] )
		
		conn.execute( "BEGIN" )
		conn.execute( new_create_sql )
		conn.execute(
			f'INSERT INTO "{temp_table}" ({new_insert}) SELECT {old_select} FROM "{table_name}";'
		)
		
		conn.execute( f'DROP TABLE "{table_name}";' )
		conn.execute( f'ALTER TABLE "{temp_table}" RENAME TO "{table_name}";' )
		
		for idx in indexes:
			idx_sql = idx[ 0 ]
			if idx_sql:
				idx_sql = idx_sql.replace( f'"{old_name}"', f'"{new_name}"' )
				conn.execute( idx_sql )
		
		conn.commit( )

def create_profile_table( table: str ):
	df = read_table( table )
	profile_rows = [ ]
	total_rows = len( df )
	for col in df.columns:
		series = df[ col ]
		null_count = series.isna( ).sum( )
		distinct_count = series.nunique( dropna=True )
		row = \
			{
					'column': col, 'dtype': str( series.dtype ),
					'null_%': round( (null_count / total_rows) * 100, 2 ) if total_rows else 0,
					'distinct_%': round( (
							                     distinct_count / total_rows) * 100,
						2 ) if total_rows else 0,
			}
		
		if pd.api.types.is_numeric_dtype( series ):
			row[ 'min' ] = series.min( )
			row[ 'max' ] = series.max( )
			row[ 'mean' ] = series.mean( )
		else:
			row[ 'min' ] = None
			row[ 'max' ] = None
			row[ 'mean' ] = None
		
		profile_rows.append( row )
	
	return pd.DataFrame( profile_rows )

def drop_column( table: str, column: str ):
	if not table or not column:
		raise ValueError( 'Table and column required.' )
	
	with create_connection( ) as conn:
		# ------------------------------------------------------------
		# Fetch original CREATE TABLE statement
		# ------------------------------------------------------------
		row = conn.execute(
			"""
            SELECT sql
            FROM sqlite_master
            WHERE type ='table' AND name =?
			""",
			(table,)
		).fetchone( )
		
		if not row or not row[ 0 ]:
			raise ValueError( 'Table definition not found.' )
		
		create_sql = row[ 0 ]
		
		# ------------------------------------------------------------
		# Extract column definitions
		# ------------------------------------------------------------
		open_paren = create_sql.find( "(" )
		close_paren = create_sql.rfind( ")" )
		
		if open_paren == -1 or close_paren == -1:
			raise ValueError( "Malformed CREATE TABLE statement." )
		
		inner = create_sql[ open_paren + 1: close_paren ]
		
		column_defs = [ c.strip( ) for c in inner.split( "," ) ]
		
		# Remove target column
		new_defs = [ ]
		for col_def in column_defs:
			col_name = col_def.split( )[ 0 ].strip( '"' )
			if col_name != column:
				new_defs.append( col_def )
		
		if len( new_defs ) == len( column_defs ):
			raise ValueError( "Column not found." )
		
		# ------------------------------------------------------------
		# Build new CREATE TABLE statement
		# ------------------------------------------------------------
		temp_table = f"{table}_rebuild_temp"
		
		new_create_sql = (
				f'CREATE TABLE "{temp_table}" ('
				+ ", ".join( new_defs )
				+ ");"
		)
		
		# ------------------------------------------------------------
		# Begin transaction
		# ------------------------------------------------------------
		conn.execute( "BEGIN" )
		
		conn.execute( new_create_sql )
		
		remaining_cols = [
				c.split( )[ 0 ].strip( '"' )
				for c in new_defs
		]
		
		col_list = ", ".join( [ f'"{c}"' for c in remaining_cols ] )
		
		conn.execute(
			f'INSERT INTO "{temp_table}" ({col_list}) '
			f'SELECT {col_list} FROM "{table}";'
		)
		
		# Preserve indexes
		indexes = conn.execute(
			"""
            SELECT sql
            FROM sqlite_master
            WHERE type ='index' AND tbl_name=? AND sql IS NOT NULL
			""",
			(table,)
		).fetchall( )
		
		conn.execute( f'DROP TABLE "{table}";' )
		conn.execute(
			f'ALTER TABLE "{temp_table}" RENAME TO "{table}";'
		)
		
		# Recreate indexes
		for idx in indexes:
			idx_sql = idx[ 0 ]
			if column not in idx_sql:
				conn.execute( idx_sql )
		
		conn.commit( )

def rename_table( old_name: str, new_name: str ) -> None:
	"""
	
		Purpose:
		--------
		Rename an existing SQLite table. Attempts native ALTER TABLE rename first; if it fails,
		falls back to a schema-safe rebuild using the original CREATE TABLE statement and
		preserves indexes.

		Parameters:
		-----------
		old_name : str
			Existing table name.

		new_name : str
			New table name.

		Returns:
		--------
		None
		
	"""
	if not old_name or not new_name:
		return
	
	with create_connection( ) as conn:
		try:
			conn.execute( f'ALTER TABLE "{old_name}" RENAME TO "{new_name}";' )
			conn.commit( )
			return
		except Exception:
			pass
		
		row = conn.execute(
			"""
            SELECT sql
            FROM sqlite_master
            WHERE type ='table' AND name =?
			""",
			(old_name,)
		).fetchone( )
		
		if not row or not row[ 0 ]:
			raise ValueError( "Table definition not found." )
		
		create_sql = row[ 0 ]
		
		indexes = conn.execute(
			"""
            SELECT sql
            FROM sqlite_master
            WHERE type ='index' AND tbl_name=? AND sql IS NOT NULL
			""",
			(old_name,)
		).fetchall( )
		
		open_paren = create_sql.find( "(" )
		if open_paren == -1:
			raise ValueError( "Malformed CREATE TABLE statement." )
		
		temp_name = f"{new_name}__rebuild_temp"
		
		conn.execute( "BEGIN" )
		conn.execute( f'CREATE TABLE "{temp_name}" {create_sql[ open_paren: ]}' )
		
		cols = [ r[ 1 ] for r in conn.execute( f'PRAGMA table_info("{old_name}");' ).fetchall( ) ]
		col_list = ", ".join( [ f'"{c}"' for c in cols ] )
		
		conn.execute(
			f'INSERT INTO "{temp_name}" ({col_list}) SELECT {col_list} FROM "{old_name}";'
		)
		
		conn.execute( f'DROP TABLE "{old_name}";' )
		conn.execute( f'ALTER TABLE "{temp_name}" RENAME TO "{new_name}";' )
		
		for idx in indexes:
			idx_sql = idx[ 0 ]
			if idx_sql:
				idx_sql = idx_sql.replace( f'ON "{old_name}"', f'ON "{new_name}"' )
				conn.execute( idx_sql )
		
		conn.commit( )

# ------------- GEN AI

def _model_selector( key_prefix: str, label: str, options: list[ str ], default_model: str ) -> str:
	base_options = options[ : ]
	if "Custom..." not in base_options:
		base_options.append( "Custom..." )
	
	idx_default = base_options.index( default_model ) if default_model in base_options else 0
	selected = st.selectbox( label=label, options=base_options, index=idx_default,
		key=f"{key_prefix}_model_select", )
	
	if selected == "Custom...":
		return st.text_input( "Custom Model", value=default_model,
			key=f"{key_prefix}_model_custom", )
	
	return selected

def invoke_provider( provider: object, prompt: str, parameters: Dict[ str, object ] ) -> object:
	"""
		Purpose:
		--------
		Invoke a provider's text-generation method using only parameters declared by the
		provider method signature.

		Parameters:
		-----------
		provider (object): Provider wrapper instance.
		prompt (str): Prompt submitted to the provider.
		parameters (Dict[str, object]): Candidate provider parameters.

		Returns:
		--------
		object: Provider response.
	"""
	throw_if( 'provider', provider )
	throw_if( 'prompt', prompt )
	throw_if( 'parameters', parameters )
	method = getattr( provider, 'generate_text', None )
	if not callable( method ):
		raise TypeError( 'Provider does not expose generate_text( ).' )

	signature = inspect.signature( method )
	accepted = { name for name, parameter in signature.parameters.items( )
		if parameter.kind in ( inspect.Parameter.POSITIONAL_OR_KEYWORD,
			inspect.Parameter.KEYWORD_ONLY ) }
	first_parameter = next( iter( signature.parameters ), '' )
	accepted.discard( first_parameter )
	filtered = { key: value for key, value in parameters.items( ) if key in accepted }
	return method( prompt, **filtered )

# ------------- DATASET UTILITIES

def has_loaded_dataset( df_frame: object ) -> bool:
	"""
		Purpose:
		--------
		Determine whether an object is a valid loaded dataframe.

		Parameters:
		-----------
		df_frame ( object ): Candidate dataframe object.

		Returns:
		--------
		bool:
			True when the object is a non-empty dataframe with at least one column.
	"""
	return ( isinstance( df_frame, pd.DataFrame )
			and not df_frame.empty
			and len( df_frame.columns ) > 0 )

def get_loaded_dataset( ) -> pd.DataFrame | None:
	"""
		Purpose:
		--------
		Return the currently loaded dataset from session state when valid.

		Parameters:
		-----------
		None

		Returns:
		--------
		pd.DataFrame | None:
			Copy of the loaded dataset, or None when no valid dataset exists.
	"""
	df_frame = st.session_state.get( 'df_dataset', None )
	if not has_loaded_dataset( df_frame ):
		return None
	
	return df_frame.copy( )

def store_loaded_dataset( df_dataset: pd.DataFrame, df_original: pd.DataFrame | None=None ) -> None:
	"""
		Purpose:
		--------
		Persist a successfully loaded dataset to session state.

		Parameters:
		-----------
		df_dataset ( pd.DataFrame ): Loaded dataset.
		df_original ( pd.DataFrame | None ): Optional original copy.

		Returns:
		--------
		None
	"""
	if not has_loaded_dataset( df_dataset ):
		return
	
	df_source = df_dataset.copy( )
	df_base = df_original.copy( ) if isinstance( df_original, pd.DataFrame ) else df_source.copy( )
	st.session_state[ 'df_raw' ] = df_source.copy( )
	st.session_state[ 'df_original' ] = df_base.copy( )
	st.session_state[ 'df_dataset' ] = df_source.copy( )
	
# ---------------------------------------------------------------------
# PAGE CONFIGURATION
# ---------------------------------------------------------------------
st.set_page_config(  page_title='iyr', layout='wide', page_icon=cfg.FAVICON,
    initial_sidebar_state='expanded', )

style_subheaders( )

# ==============================================================================
# SIDEBAR
# ==============================================================================
st.logo( cfg.LOGO, size='Large' )

with st.sidebar:
	# ------- Map Mode
	blue_divider( )
	st.markdown( '#### 🛰️ GIS Data' )
	with st.expander( label='Pipelines', expanded=True ):
		mode = st.radio( label='Mode', options=cfg.MODES, label_visibility='collapsed' )
		if mode:
			st.session_state[ 'mode' ] = mode
		else:
			st.session_state[ 'mode' ] = 'Mapping Tools'
			
		previous_mode = st.session_state.get( 'previous_mode', None )
		if previous_mode != mode:
			st.session_state[ 'previous_mode' ] = mode
			st.rerun( )
		
	# ------- Data
	blue_divider( )
	st.markdown( '#### 🏛️ Static Data' )
	with st.expander( label='Source', expanded=False ):
		st.caption( 'Sources' )
		source = st.selectbox( label='Select', options=[ 'Default', 'Database', 'External' ],
			key='source_selectbox' )
		
		uploaded = st.file_uploader( label='Upload Spreadsheet', type=[ 'xlsx', 'xls', 'csv' ],
			key='source_uploader' )
		df_default = pd.DataFrame( )
		df_original: pd.DataFrame | None = None
		dataset_signature = None
		db_path = Path( cfg.DB_PATH )
		db_version = db_path.stat( ).st_mtime_ns if db_path.exists( ) else None

		if source in ( 'Default', 'Database' ):
			try:
				with sqlite3.connect( cfg.DB_PATH ) as connection:
					df_tables = pd.read_sql_query( """
                                               SELECT name
                                               FROM sqlite_master
                                               WHERE type = 'table'
                                                 AND name NOT LIKE 'sqlite_%'
                                               ORDER BY name; """, connection )
					table_options = df_tables[ 'name' ].tolist( )
					selected_table = cfg.DEFAULT_DATA if source == 'Default' else None
					if source == 'Database':
						if table_options:
							selected_table = st.selectbox( label='Select Database Table',
								options=table_options, key='database_table_selectbox' )
						else:
							st.warning( 'No tables were found in the database.' )
					elif selected_table not in table_options:
						st.warning( f'Default dataset "{cfg.DEFAULT_DATA}" is not installed. '
							'Choose Database or External to load an available dataset.' )
						st.session_state[ 'active_dataset_name' ] = ''
						selected_table = None

					if selected_table:
						dataset_signature = (source, str( db_path.resolve( ) ),
							selected_table, db_version)
						if st.session_state.get( '_sidebar_dataset_signature' ) != dataset_signature:
							df_default = pd.read_sql_query( f'SELECT * FROM "{selected_table}"',
								connection )
							df_original = df_default.copy( )
						if source == 'Database':
							st.session_state[ 'map_mode_table' ] = selected_table
						st.session_state[ 'active_dataset_name' ] = selected_table
			except Exception as ex:
				st.error( f'Error loading database data: {ex}' )

		elif source == 'External':
			if uploaded is not None:
				import hashlib
				file_signature = hashlib.sha256( uploaded.getvalue( ) ).hexdigest( )
				dataset_signature = (source, uploaded.name, file_signature)
				if st.session_state.get( '_sidebar_dataset_signature' ) != dataset_signature:
					if uploaded.name.lower( ).endswith( ('.xlsx', '.xls') ):
						df_default = pd.read_excel( uploaded )
					else:
						df_default = pd.read_csv( uploaded )
					df_original = df_default.copy( )
				st.session_state[ 'active_dataset_name' ] = uploaded.name
			else:
				st.info( 'Upload a spreadsheet to load data.' )

		if dataset_signature is not None and has_loaded_dataset( df_default ):
			store_loaded_dataset( df_default, df_original )
			st.session_state[ '_sidebar_dataset_signature' ] = dataset_signature
			log_step( f'Loaded dataset: {st.session_state[ "active_dataset_name" ]}' )

	# ------- Live World Data
	st.markdown( '#### 📡 Live Data' )
	render_live_world_sidebar( )
	
	# -------- Settings
	blue_divider( )
	st.markdown( '#### 🎚️ Configuration' )
	
	# ------- User Location
	with st.expander( label='Location',  expanded=False ):
		st.checkbox( 'Use browser location on load',
			value=st.session_state.get( 'browser_geolocation_enabled', True ),
			key='browser_geolocation_enabled' )
		
		if st.session_state.get( 'browser_geolocation_loaded', False ):
			st.success( 'Browser location loaded.' )
			st.write( f"Latitude: {float( st.session_state.get( 'latitude', 0.0 ) ):.6f}" )
			st.write( f"Longitude: {float( st.session_state.get( 'longitude', 0.0 ) ):.6f}" )
		
		elif st.session_state.get( 'browser_geolocation_permission_denied', False ):
			st.warning( 'Browser location permission was denied.' )
		
		else:
			st.info( 'Browser location has not been loaded yet.' )
		
		error = st.session_state.get( 'browser_geolocation_error', '' )
		if error:
			st.warning( error )
		
		if st.button( 'Reset', key='browser_geolocation_reset', width='stretch' ):
			st.session_state[ 'browser_geolocation' ] = None
			st.session_state[ 'browser_geolocation_loaded' ] = False
			st.session_state[ 'browser_geolocation_reverse_geocoded' ] = False
			st.session_state[ 'browser_geolocation_error' ] = ''
			st.session_state[ 'browser_geolocation_permission_denied' ] = False
			st.rerun( )
	
	# ------- Query
	with st.expander( label='Frequency', expanded=False ):
		qps = st.slider( 'Queries Per Second', min_value=1, max_value=50, value=10, )
	
	# ------- Cache
	with st.expander( label='Persistence',  expanded=False ):
		cache_backend = st.selectbox( 'Select', options=[ 'none', 'memory', 'sqlite' ],
			key='cache_backend' )
		cache: Optional[ object ] = None
		if cache_backend == 'memory':
			cache = InMemoryCache( )
		elif cache_backend == 'sqlite':
			cache_path = st.text_input( 'SQLite Cache Path', value='mappy_cache.db', )
			cache = SQLiteCache( cache_path )
	
	# ------- Security
	blue_divider( )
	st.markdown( '#### 🔒 Credentials' )
	with st.expander( label='API', expanded=False ):
		init_env_state( 'openai_api_key', 'OPENAI_API_KEY', 'OPENAI_API_KEY' )
		init_env_state( 'gemini_api_key', 'GEMINI_API_KEY', 'GEMINI_API_KEY' )
		init_env_state( 'xai_api_key', 'XAI_API_KEY', 'XAI_API_KEY' )
		init_env_state( 'claude_api_key', 'CLAUDE_API_KEY', 'CLAUDE_API_KEY' )
		init_env_state( 'mistral_api_key', 'MISTRAL_API_KEY', 'MISTRAL_API_KEY' )
		openai_key = st.text_input( 'OpenAI API Key', type='password',
			value=st.session_state.openai_api_key or '', help='Overrides OPENAI_API_KEY.' )
		if openai_key:
			st.session_state.openai_api_key = openai_key
			os.environ[ 'OPENAI_API_KEY' ] = openai_key
			cfg.OPENAI_API_KEY = openai_key

		gemini_key = st.text_input( 'Gemini API Key', type='password',
			value=st.session_state.gemini_api_key or '', help='Overrides GEMINI_API_KEY.' )
		if gemini_key:
			st.session_state.gemini_api_key = gemini_key
			os.environ[ 'GEMINI_API_KEY' ] = gemini_key
			cfg.GEMINI_API_KEY = gemini_key

		xai_key = st.text_input( 'Grok / xAI API Key', type='password',
			value=st.session_state.xai_api_key or '', help='Overrides XAI_API_KEY.' )
		if xai_key:
			st.session_state.xai_api_key = xai_key
			os.environ[ 'XAI_API_KEY' ] = xai_key
			cfg.XAI_API_KEY = xai_key

		claude_key = st.text_input( 'Claude API Key', type='password',
			value=st.session_state.claude_api_key or '', help='Overrides CLAUDE_API_KEY' )
		if claude_key:
			st.session_state.claude_api_key = claude_key
			os.environ[ 'CLAUDE_API_KEY' ] = claude_key
			cfg.CLAUDE_API_KEY = claude_key

		mistral_key = st.text_input( 'Mistral API Key', type='password',
			value=st.session_state.mistral_api_key or '', help='Overrides MISTRAL_API_KEY.' )
		if mistral_key:
			st.session_state.mistral_api_key = mistral_key
			os.environ[ 'MISTRAL_API_KEY' ] = mistral_key
			cfg.MISTRAL_API_KEY = mistral_key

		google_key = st.text_input( 'Google API Key', type='password',
			value=st.session_state.google_api_key or '', help='Overrides GOOGLE_API_KEY.' )
		
		if google_key:
			st.session_state.google_api_key = google_key
			os.environ[ 'GOOGLE_API_KEY' ] = google_key
			cfg.GOOGLE_API_KEY = google_key
		
		googlemaps_key = st.text_input( 'Google Maps API Key', type='password',
			value=st.session_state.googlemaps_api_key or '', help='Overrides GOOGLEMAPS_API_KEY.' )
		
		if googlemaps_key:
			st.session_state.googlemaps_api_key = googlemaps_key
			os.environ[ 'GOOGLEMAPS_API_KEY' ] = googlemaps_key
			cfg.GOOGLEMAPS_API_KEY = googlemaps_key
		
		googleweather_key = st.text_input( 'Google Weather API Key', type='password',
			value=st.session_state.google_weather_api_key or '',
			help='Overrides GOOGLE_WEATHER_API_KEY.' )
		
		if googleweather_key:
			st.session_state.google_weather_api_key = googleweather_key
			os.environ[ 'GOOGLE_WEATHER_API_KEY' ] = googleweather_key
		
		geocoding_key = st.text_input( 'Geocoding API Key', type='password',
			value=st.session_state.geocoding_api_key or '',
			help='Overrides GEOCODING_API_KEY.' )
		
		if geocoding_key:
			st.session_state.geocoding_api_key = geocoding_key
			os.environ[ 'GEOCODING_API_KEY' ] = geocoding_key
		
		google_cse_id = st.text_input( 'Google Custom Search ID', type='password',
			value=st.session_state.google_cse_id or '', help='Overrides GOOGLE_CSE_ID.' )
		
		if google_cse_id:
			st.session_state.google_cse_id = google_cse_id
			os.environ[ 'GOOGLE_CSE_ID' ] = google_cse_id
		
		govinfo_key = st.text_input( 'Gov Info API', type='password',
			value=st.session_state.govinfo_api_key or '',
			help='Overrides GOVINFO_API_KEY from config.py for this session only.' )
		
		if govinfo_key:
			st.session_state.govinfo_api_key = govinfo_key
			os.environ[ 'GOVINFO_API_KEY' ] = govinfo_key
		
		airnow_key = st.text_input( 'Air Quality Now', type='password',
			value=st.session_state.airnow_api_key or '',
			help='Overrides AIRNOW_API_KEY from config.py for this session only.' )
		
		if airnow_key:
			st.session_state.airnow_api_key = airnow_key
			os.environ[ 'AIRNOW_API_KEY' ] = airnow_key
		
		nasa_key = st.text_input( 'NASA API Key', type='password',
			value=st.session_state.nasa_api_key or '',
			help='Overrides NASA_API_KEY from config.py for this session only.' )
		
		if nasa_key:
			st.session_state.nasa_api_key = nasa_key
			os.environ[ 'NASA_API_KEY' ] = nasa_key
		
		nasa_token = st.text_input( 'NASA Earth Data', type='password',
			value=st.session_state.nasa_earthdata_token or '',
			help='Overrides NASA_EARTHDATA_TOKEN from config.py for this session only.' )
		
		if nasa_token:
			st.session_state.nasa_earthdata_token = nasa_token
			os.environ[ 'NASA_EARTHDATA_TOKEN' ] = nasa_token
		
		openaq_key = st.text_input( 'Open Air Quality', type='password',
			value=st.session_state.openaq_api_key or '',
			help='Overrides OPENAQ_API_KEY from config.py for this session only.' )
		
		if openaq_key:
			st.session_state.openaq_api_key = openaq_key
			os.environ[ 'OPENAQ_API_KEY' ] = openaq_key
		
		opensky_client = st.text_input( 'Open Sky Client ID', type='password',
			value=st.session_state.opensky_api_client_id or '',
			help='Overrides OPENSKY_API_CLIENT_ID from config.py for this session only.' )
		
		if opensky_client:
			st.session_state.opensky_api_client_id = opensky_client
			os.environ[ 'OPENSKY_API_CLIENT_ID' ] = opensky_client
		
		firms_key = st.text_input( 'FIRMS Map Client', type='password',
			value=st.session_state.firms_map_key or '',
			help='Overrides FIRMS_MAP_KEY from config.py for this session only.' )
		
		if firms_key:
			st.session_state.firms_map_key = firms_key
			os.environ[ 'FIRMS_MAP_KEY' ] = firms_key
		
		opensky_credentials = st.text_input( 'Open Sky Credentials', type='password',
			value=st.session_state.opensky_api_credentials or '',
			help='Overrides OPENSKY_API_CREDENTIALS from config.py for this session only.' )
		
		if opensky_credentials:
			st.session_state.opensky_api_credentials = opensky_credentials
			os.environ[ 'OPENSKY_API_CREDENTIALS' ] = opensky_credentials
			
		purpleair_key = st.text_input( 'Purple Air API', type='password',
			value=st.session_state.purpleair_api_key or '',
			help='Overrides Purple Air API from config.py for this session only.' )
		
		if purpleair_key:
			st.session_state.purpleair_api_key = purpleair_key
			os.environ[ 'PURPLEAIR_API_KEY' ] = purpleair_key
	
	maps = Maps( qps=qps, )
	distances = DistanceMatrix( maps )
	timezone = Timezone( maps )
	geocoder = Geocoder( maps, cache=cache )
	places = Place( maps, cache=cache )
	static_maps = StaticMap( )
	
# ------------------------------------------------------------------------------
# BROWSER GEOLOCATION BOOTSTRAP
# ------------------------------------------------------------------------------
bootstrap_browser_geolocation( geocoder )
ensure_active_location_state( )

# ==============================================================================
# Mapping Tools
# ==============================================================================
if mode == 'Mapping Tools':
	geocoding_tab, distances_tab, timezones_tab, static_maps_tab = \
		st.tabs( [ 'Geocoding', 'Distances', 'Time Zones', 'Static Maps' ] )

	with geocoding_tab:
		left, center, right = st.columns( [ 0.025, 0.95, 0.025 ] )
		with center:
			st.subheader( 'Geocoding' )
			st.divider( )

			geo_c1, geo_c2 = st.columns( [ 0.60, 0.40 ], border=True, gap='small' )
			with geo_c2:
				st.caption( '' )
				geosub_c1, geosub_c2 = st.columns( 2 )
				with geosub_c1:
					use_places = st.checkbox( 'Use Places fallback', value=True,
						key='geocoding_fallback' )

				with geosub_c2:
					if st.button( label='Clear Map Results', icon='💫', width='stretch',
							key='clear_map_results' ):
						st.session_state[ 'df_geocoding_map_results' ] = pd.DataFrame( )
						st.rerun( )

			with geo_c1:
				if st.session_state.pop( 'clear_geocoding_location_input', False ):
					st.session_state[ 'geocoding_location_input' ] = ''

				if 'geocoding_location_input' not in st.session_state:
					st.session_state[ 'geocoding_location_input' ] = get_global_location_default( )

				query = st.text_input( 'Enter Address or Location', key='geocoding_location_input' )
				btn_c1, btn_c2 = st.columns( 2 )
				with btn_c1:
					if st.button( 'Resolve Location', width='stretch', icon='📍' ):
						if not query:
							st.warning( 'Enter a Location.' )
						else:
							try:
								result = geocoder.freeform( query )
								append_geocoding_map_result( query, 'Geocoder', result )
								st.json( result )
							except NotFound:
								if use_places:
									try:
										st.warning( 'Geocoding failed.' )
										result = places.text_to_location( query )
										append_geocoding_map_result( query, 'Places', result )
										st.json( result )
									except Exception as e:
										st.error( str( e ) )
								else:
									st.warning( 'Geocoding failed and Places fallback is disabled.' )
							except Exception as e:
								st.error( str( e ) )

				with btn_c2:
					if st.button( label='Clear Location', width='stretch', icon='🧹' ):
						st.session_state[ 'clear_geocoding_location_input' ] = True
						st.rerun( )

			st.divider( )

	with distances_tab:
		left, center, right = st.columns( [ 0.025, 0.95, 0.025 ] )
		with center:
			st.subheader( 'Distance Matrix' )
			st.divider( )
			global_location = get_global_location_default( )
			location_state = get_location_state( )
			current_location = compose_location_from_state( )
			status_c1, status_c2, status_c3 = st.columns( 3, border=True )
			status_c1.metric( 'Location', current_location if current_location else global_location )
			status_c2.metric( 'Latitude', f'{float( location_state[ "latitude" ] ):.4f}' )
			status_c3.metric( 'Longitude', f'{float( location_state[ "longitude" ] ):.4f}' )
			blue_divider( )
			dist_c1, dist_c2 = st.columns( [ 0.50, 0.50 ], border=True )
			with dist_c1:
				use_global_origin = st.checkbox( 'Use User-Location as Origin',
					value=bool( current_location ), key='distance_use_global_origin' )

				if use_global_origin:
					origin = current_location
					st.text_input( 'Origin', value=origin,
						key='distance_origin_display', disabled=True )
				else:
					origin_default = st.session_state.get( 'origin', '' ) or current_location
					origin = st.text_input( 'Origin', value=origin_default,
						key='distance_origin_input' )

			with dist_c2:
				use_global_destination = st.checkbox( 'Use User-Location as Destination', value=False,
					key='distance_use_global_destination' )

				if use_global_destination:
					destination = current_location
					st.text_input( 'Destination', value=destination,
						key='distance_destination_display', disabled=True )
				else:
					destination_default = st.session_state.get( 'destination', '' )
					destination = st.text_input( 'Destination', value=destination_default,
						key='distance_destination_input' )

			ctl_c1, ctl_c2, ctl_c3 = st.columns( [ 0.30, 0.30, 0.40 ], border=True )
			with ctl_c1:
				travel_mode = st.selectbox( 'Travel Mode',
					[ 'driving', 'walking', 'bicycling', 'transit' ], key='travel_key' )

			with ctl_c2:
				update_global_route = st.checkbox( 'Save Route to Global State', value=True,
					key='distance_save_route_state' )

			with ctl_c3:
				run_distance = st.button( 'Calculate Distance', key='distance_calculate', icon='📐',
					width='stretch' )

			if run_distance:
				if not origin or not destination:
					st.warning( 'Provide both origin and destination.' )
				else:
					try:
						if update_global_route:
							st.session_state[ 'origin' ] = str( origin ).strip( )
							st.session_state[ 'destination' ] = str( destination ).strip( )

						summary = distances.summary( origin, destination, mode=travel_mode )
						st.session_state[ 'distance_last_result' ] = summary or { }
						st.success( 'Distance Matrix request completed.' )

					except Exception as ex:
						st.error( f'Distance Matrix request failed: {ex}' )

			result = st.session_state.get( 'distance_last_result', { } )
			if result:
				blue_divider( )
				st.markdown( '##### Distance Result' )
				st.data_editor( pd.DataFrame( [ result ] ), key='distance_result_table',
					use_container_width=True, disabled=True )
				st.json( result )

	with timezones_tab:
		left, center, right = st.columns( [ 0.025, 0.95, 0.025 ] )
		with center:
			st.subheader( 'Time Zone Lookup' )
			st.divider( )
			global_location = get_global_location_default( )
			location_state = get_location_state( )
			has_global_coords = has_valid_global_coordinates( )
			status_c1, status_c2, status_c3 = st.columns( 3, border=True )
			status_c1.metric( 'Location', compose_location_from_state( ) or global_location )
			status_c2.metric( 'Latitude', f'{float( location_state[ "latitude" ] ):.4f}' )
			status_c3.metric( 'Longitude', f'{float( location_state[ "longitude" ] ):.4f}' )
			blue_divider( )
			tz_c1, tz_c2 = st.columns( [ 0.50, 0.50 ], border=True )
			with tz_c1:
				use_global_coordinates = st.checkbox( 'User Location', value=has_global_coords,
					key='timezone_use_global_coordinates' )

				if use_global_coordinates:
					lat_tz = float( location_state[ 'latitude' ] )
					lng_tz = float( location_state[ 'longitude' ] )
					coord_c1, coord_c2 = st.columns( 2 )
					with coord_c1:
						st.number_input( 'Latitude', value=lat_tz, format='%.6f',
							key='timezone_global_latitude_display', disabled=True )

					with coord_c2:
						st.number_input( 'Longitude', value=lng_tz, format='%.6f',
							key='timezone_global_longitude_display', disabled=True )

				else:
					manual_default_lat = (
							float( location_state[ 'latitude' ] ) if has_global_coords else 0.0)

					manual_default_lng = (
							float( location_state[ 'longitude' ] ) if has_global_coords else 0.0)

					coord_c1, coord_c2 = st.columns( 2 )
					with coord_c1:
						lat_tz = st.number_input( 'Latitude', value=manual_default_lat, format='%.6f',
							key='timezone_manual_latitude' )

					with coord_c2:
						lng_tz = st.number_input( 'Longitude', value=manual_default_lng, format='%.6f',
							key='timezone_manual_longitude' )

			with tz_c2:
				save_coordinates = st.checkbox( 'Save Coordinates to Global State', value=True,
					key='timezone_save_coordinates' )

				run_timezone = st.button( 'Lookup Time Zone', key='timezone_lookup', icon='🔍',
					width='content' )

			if run_timezone:
				if use_global_coordinates and not has_global_coords:
					st.warning( 'Global coordinates are not set' )
				elif not has_valid_coordinates( lat_tz, lng_tz ):
					st.warning( 'Provide valid coordinates before looking up a time zone.' )
				else:
					try:
						if save_coordinates:
							set_coordinates( lat_tz, lng_tz )

						result = timezone.lookup( float( lat_tz ), float( lng_tz ) )
						st.session_state[ 'timezone_last_result' ] = result or { }
						st.session_state[ 'timezone_last_latitude' ] = float( lat_tz )
						st.session_state[ 'timezone_last_longitude' ] = float( lng_tz )
						st.success( 'Time zone lookup completed.' )

					except Exception as ex:
						st.error( f'Time zone lookup failed: {ex}' )

			result = st.session_state.get( 'timezone_last_result', { } )
			if result:
				blue_divider( )
				st.markdown( '##### Time Zone Result' )
				lat_c, lng_c = st.columns( 2 )
				with lat_c:
					st.metric( 'Latitude',
						f'{float( st.session_state.get( "timezone_last_latitude", 0.0 ) ):.6f}' )
				with lng_c:
					st.metric( 'Longitude',
						f'{float( st.session_state.get( "timezone_last_longitude", 0.0 ) ):.6f}' )

				st.json( result )

	with static_maps_tab:
		left, center, right = st.columns( [ 0.025, 0.95, 0.025 ] )
		with center:
			st.subheader( 'Static Map' )
			st.divider( )
			global_location = get_global_location_default( )
			location_state = get_location_state( )
			has_global_coords = has_valid_global_coordinates( )
			status_c1, status_c2, status_c3 = st.columns( 3, border=True )
			status_c1.metric( 'Location', compose_location_from_state( ) or global_location )
			status_c2.metric( 'Latitude', f'{float( location_state[ "latitude" ] ):.4f}' )
			status_c3.metric( 'Longitude', f'{float( location_state[ "longitude" ] ):.4f}' )
			blue_divider( )
			map_c1, map_c2 = st.columns( [ 0.50, 0.50 ], border=True )
			with map_c1:
				use_global_coordinates = st.checkbox( 'Use User-Location', value=has_global_coords,
					key='maps_use_global_coordinates' )

				if use_global_coordinates:
					lat = float( location_state[ 'latitude' ] )
					lng = float( location_state[ 'longitude' ] )

					coord_c1, coord_c2 = st.columns( 2 )
					with coord_c1:
						st.number_input( 'Latitude', value=lat, format='%.4f',
							key='maps_global_latitude_display', disabled=True )

					with coord_c2:
						st.number_input( 'Longitude', value=lng, format='%.4f',
							key='maps_global_longitude_display', disabled=True )

				else:
					manual_default_lat = (
						float( location_state[ 'latitude' ] ) if has_global_coords else 0.0)

					manual_default_lng = (
						float( location_state[ 'longitude' ] ) if has_global_coords else 0.0)

					coord_c1, coord_c2 = st.columns( 2 )
					with coord_c1:
						lat = st.number_input( 'Latitude', value=manual_default_lat, format='%.4f',
							key='maps_manual_latitude' )

					with coord_c2:
						lng = st.number_input( 'Longitude', value=manual_default_lng, format='%.4f',
							key='maps_manual_longitude' )

			with map_c2:
				zoom_default = int( st.session_state.get( 'zoom', 8 ) or 8 )
				size_default = str( st.session_state.get( 'map_size', '600x400' ) or '600x400' )
				size_options = [ '400x400', '600x400', '800x600' ]

				if size_default not in size_options:
					size_default = '600x400'

				zoom = st.slider( 'Zoom', min_value=1, max_value=20, value=zoom_default,
					key='maps_zoom' )

				size = st.selectbox( 'Image Size', size_options,
					index=size_options.index( size_default ), key='maps_size' )

				save_coordinates = st.checkbox( 'Save Coordinates to Global State', value=True,
					key='maps_save_coordinates' )

			if st.button( 'Generate Map', icon='🗺️', key='maps_generate', width='content' ):
				if use_global_coordinates and not has_global_coords:
					st.warning( 'User coordinates are not set.' )
				elif not has_valid_coordinates( lat, lng ):
					st.warning( 'Provide valid coordinates before generating a map.' )
				else:
					try:
						if save_coordinates:
							set_coordinates( lat, lng )
							st.session_state[ 'zoom' ] = int( zoom )
							st.session_state[ 'map_size' ] = str( size )

						url = static_maps.pin( lat=float( lat ), lng=float( lng ), zoom=int( zoom ),
							size=str( size ) )

						st.session_state[ 'maps_last_url' ] = url
						st.session_state[ 'maps_last_latitude' ] = float( lat )
						st.session_state[ 'maps_last_longitude' ] = float( lng )
						st.success( 'Static map generated.' )
					except Exception as ex:
						st.error( f'Static map generation failed: {ex}' )

			map_url = st.session_state.get( 'maps_last_url', '' )
			if map_url:
				blue_divider( )
				st.markdown( '##### Static Map Result' )
				st.image( map_url )
				st.code( map_url )

# ==============================================================================
# MAP MODE
# ==============================================================================
elif mode == 'Interactive Map':
	left, center, right = st.columns( [ 0.025, 0.95, 0.025 ] )
	with center:
		st.subheader( 'Interactive Map' )
		st.divider( )
		tables = list_tables( )
		if not tables:
			st.info( 'No tables available.' )
		else:
			default_table = resolve_table_name( cfg.DEFAULT_DATA, tables )
			if default_table is None:
				default_table = tables[ 0 ]
			
			default_index = tables.index( default_table )
			control_c1, control_c2, control_c3 = st.columns( [ 0.35, 0.35, 0.30 ], border=True )
			with control_c1:
				table = st.selectbox( 'Table', tables, index=default_index,
					key='map_mode_table' )
			
			with control_c2:
				include_overlay = st.checkbox( 'Show Geocoded Overlay', value=True,
					key='map_mode_show_overlay' )
			
			with control_c3:
				refresh_map = st.button( label='Refresh Map', key='map_mode_refresh', icon='🔄',
					width='stretch' )
				
				if refresh_map:
					st.rerun( )
			
			df_map_source = read_table( table )
			df_overlay = pd.DataFrame( )
			
			if include_overlay:
				df_overlay = st.session_state.get( 'df_geocoding_map_results',
					pd.DataFrame( ) )
			
			create_reports_map( df_map_source, df_overlay=df_overlay, source_name=table )
			if include_overlay and df_overlay is not None and not df_overlay.empty:
				with st.expander( 'Geocoded Overlay Records', expanded=False ):
					st.data_editor( df_overlay, key='map_mode_overlay_records',
						use_container_width=True, disabled=True )

# =============================================================================
# DOCUMENT LOADING MODE
# =============================================================================
if mode == 'Local Data':
	tokens = st.session_state[ 'tokens' ]
	documents = st.session_state[ 'documents' ]
	raw_text = st.session_state[ 'raw_text' ]
	st.subheader( '📤 Document Loading' )
	st.divider( )
	
	# ----------- LEFT COLUMN - LOADERS
	document_loaders_column, document_results_column = st.columns( [ 0.4, 0.6 ],
		gap='xxsmall', border=True )
	with document_loaders_column:
		_loader_msg = st.session_state.pop( '_loader_status', None )
		if isinstance( _loader_msg, str ) and _loader_msg.strip( ):
			st.success( _loader_msg )
		
		with st.expander( label='Local Documents', expanded=True ):
			
			# ------ Expander Text Loader
			with st.expander( label='Text Loader', icon='📝', expanded=False ):
				st.caption( 'API', help=cfg.TEXT_LOADER )
				files = st.file_uploader( 'Upload Text File(s)', type=[ 'txt', 'text', 'log' ],
					accept_multiple_files=True, key='txt_upload' )
				
				st.divider( )
				render_document_processing_inputs( 'TextLoader', 'txt' )
				
				# ------------------------------------------------------------------
				# Buttons: Load / Clear / Save
				# ------------------------------------------------------------------
				st.divider( )
				col_load, col_clear, col_save = st.columns( 3 )
				load_txt = col_load.button( label='Load', key='txt_load', icon='📤',
					width='stretch' )
				
				clear_txt = col_clear.button( label='Clear', key='txt_clear', icon='🧹',
					width='stretch' )
				
				can_save = (st.session_state.get( 'active_loader' ) == 'TextLoader' and isinstance(
					st.session_state.get( 'raw_text' ), str ) and st.session_state.get(
					'raw_text' ).strip( ))
				
				if can_save:
					col_save.download_button( label='Save', data=st.session_state.get( 'raw_text' ),
						file_name='text_loader_output.txt', mime='text/plain', key='txt_save',
						icon='💾', width='stretch' )
				else:
					col_save.button( label='Save', key='txt_save_disabled', disabled=True, icon='💾',
						width='stretch' )
				
				# ------------------------------------------------------------------
				# Clear
				# ------------------------------------------------------------------
				if clear_txt:
					reset_document_processing_controls( 'txt' )
					clear_if_active( 'TextLoader' )
					st.info( 'Text Loader state cleared.' )
					st.rerun( )
				
				# ------------------------------------------------------------------
				# Load
				# ------------------------------------------------------------------
				if load_txt and files:
					documents: list[ Document ] = [ ]
					with tempfile.TemporaryDirectory( ) as tmp:
						for uploaded_file in files:
							path = os.path.join( tmp, uploaded_file.name )
							
							with open( path, 'wb' ) as handle:
								handle.write( uploaded_file.read( ) )
							
							loader = TextLoader( )
							loaded = loader.load( path ) or [ ]
							for document in loaded:
								if not isinstance( getattr( document, 'metadata', None ), dict ):
									document.metadata = { }
								
								document.metadata[ 'loader' ] = 'TextLoader'
								document.metadata.setdefault( 'source', uploaded_file.name )
							
							documents.extend( loaded )
					
					st.session_state.documents = documents
					st.session_state.raw_documents = list( documents )
					st.session_state.raw_text = "\n\n".join( d.page_content for d in documents if
					                                         hasattr( d, 'page_content' ) \
					                                         and isinstance( d.page_content,
						                                         str ) and d.page_content.strip( ) )
					
					st.session_state.active_loader = 'TextLoader'
					st.success( f'Loaded {len( documents )} text document(s).' )
				
				render_document_processing_actions( 'TextLoader', 'txt' )
			
			# ------ Expander CSV Loader
			with st.expander( label='CSV Loader', icon='📑', expanded=False ):
				st.caption( 'API', help=cfg.CSV_LOADER )
				csv_file = st.file_uploader( label='Upload CSV', type=[ 'csv' ], key='csv_upload' )
				st.divider( )
				csv_c1, csv_c2 = st.columns( 2 )
				with csv_c1:
					delimiter = st.text_input( 'Delimiter', value=',', key='csv_delim', )
				with csv_c2:
					quotechar = st.text_input( 'Quote Character', value="", key='csv_quote', )
				
				render_document_processing_inputs( 'CsvLoader', 'csv' )
				
				# --------------------------------------------------
				# Buttons: Load / Clear / Save
				# --------------------------------------------------
				col_load, col_clear, col_save = st.columns( 3 )
				load_csv = col_load.button( 'Load', key='csv_load', icon='📤', width='stretch' )
				clear_csv = col_clear.button( 'Clear', key='csv_clear', icon='🧹', width='stretch' )
				can_save = (st.session_state.get( 'active_loader' ) == 'CsvLoader' and isinstance(
					st.session_state.get( 'raw_text' ), str ) and st.session_state.get(
					'raw_text' ).strip( ))
				
				if can_save:
					col_save.download_button( 'Save', data=st.session_state.get( 'raw_text' ),
						file_name='csv_loader_output.txt', mime='text/plain', key='csv_save',
						icon='💾', width='stretch' )
				else:
					col_save.button( 'Save', key='csv_save_disabled', disabled=True, icon='💾',
						width='stretch' )
				
				# --------------------------------------------------
				# Clear
				# --------------------------------------------------
				if clear_csv:
					reset_document_processing_controls( 'csv' )
					clear_if_active( 'CsvLoader' )
					st.session_state.raw_text = rebuild_raw_text_from_documents( )
					st.session_state[ '_loader_status' ] = 'CSV Loader state cleared.'
				
				# --------------------------------------------------
				# Load
				# --------------------------------------------------
				if load_csv and csv_file:
					with tempfile.TemporaryDirectory( ) as tmp:
						path = os.path.join( tmp, csv_file.name )
						with open( path, 'wb' ) as f:
							f.write( csv_file.read( ) )
						
						loader = CsvLoader( )
						documents = loader.load( path, columns=None, delimiter=delimiter,
							quotechar=quotechar, ) or [ ]
					
					st.session_state.documents = documents
					st.session_state.raw_documents = list( documents )
					st.session_state.raw_text = "\n\n".join( d.page_content for d in documents if
					                                         hasattr( d,
						                                         'page_content' ) and isinstance(
						                                         d.page_content,
						                                         str ) and d.page_content.strip( ) )
					st.session_state.processed_text = None
					st.session_state.active_loader = 'CsvLoader'
					
					st.session_state[
						'_loader_status' ] = f'Loaded {len( documents )} CSV document(s).'
				
				# ----------------------------
				# ---- XML Loader
				# ----------------------------
				render_document_processing_actions( 'CsvLoader', 'csv' )
			
			# ------- Expander PDF Loader
			with st.expander( label='PDF Loader', icon='📕', expanded=False ):
				st.caption( 'API', help=cfg.PDF_LOADER )
				pdf = st.file_uploader( 'Upload PDF', type=[ 'pdf' ], key='pdf_upload', )
				
				st.divider( )
				
				pdf_c1, pdf_c2 = st.columns( 2, border=True )
				with pdf_c1:
					mode = st.selectbox( 'Mode', [ 'single', 'page' ], key='pdf_mode' )
				
				with pdf_c2:
					extract = st.selectbox( 'Extract', [ 'plain', 'layout' ], key='pdf_extract',
						help='Used only when legacy extraction is enabled.' )
				
				img_c1, img_c2 = st.columns( 2 )
				with img_c1:
					include = st.checkbox( 'Include Images', value=False, key='pdf_include',
						help='Used only when legacy extraction is enabled.' )
				
				with img_c2:
					fmt = st.selectbox( 'Format', [ 'markdown-img', 'html-img', 'text-img' ],
						key='pdf_fmt', help='Used only when legacy extraction is enabled.' )
				
				geo_c1, geo_c2 = st.columns( 2 )
				with geo_c1:
					use_geometry = st.checkbox( 'Use Geometry Extraction', value=True,
						key='pdf_use_geometry', help='Uses PyMuPDF block coordinates' )
				
				with geo_c2:
					use_legacy_pdf_loader = st.checkbox( 'Use Legacy PdfLoader', value=False,
						key='pdf_use_legacy_loader', help='Falls back to the existing PdfLoader' )
				
				band_left, band_right = st.columns( 2, border=True )
				with band_left:
					header_band = st.slider( 'Header Band', min_value=0, max_value=30, value=8,
						step=1, key='pdf_header_band',
						help='Percentage of page height classified as the top candidate header' )
				
				with band_right:
					footer_band = st.slider( 'Footer Band', min_value=0, max_value=30, value=8,
						step=1, key='pdf_footer_band',
						help='Percentage of page height classified as the bottom candidate footer.' )
				
				preserve_page_breaks = st.checkbox( 'Preserve Page Breaks', value=False,
					key='pdf_preserve_page_breaks',
					help='Adds explicit page-break markers between extracted pages.' )
				
				render_document_processing_inputs( 'PdfLoader', 'pdf' )
				
				st.divider( )
				# --------------------------------------------------
				# Buttons: Load / Clear / Save
				# --------------------------------------------------
				col_load, col_clear, col_save = st.columns( 3 )
				load_pdf = col_load.button( 'Load', key='pdf_load', icon='📤', width='stretch' )
				clear_pdf = col_clear.button( 'Clear', key='pdf_clear', icon='🧹', width='stretch' )
				save_pdf = col_save.empty( )
				
				# --------------------------------------------------
				# Clear
				# --------------------------------------------------
				if clear_pdf:
					reset_document_processing_controls( 'pdf' )
					clear_if_active( 'PdfLoader' )
					st.session_state.pdf_pages = None
					st.session_state[ '_loader_status' ] = 'PDF Loader state cleared.'
				
				# --------------------------------------------------
				# Load
				# --------------------------------------------------
				if load_pdf and pdf:
					with tempfile.TemporaryDirectory( ) as tmp:
						path = os.path.join( tmp, pdf.name )
						
						with open( path, 'wb' ) as f:
							f.write( pdf.read( ) )
						
						if use_geometry and not use_legacy_pdf_loader:
							parser = PdfParser( )
							pdf_pages = parser.extract_pages( path=path,
								header_ratio=float( header_band ) / 100.0,
								footer_ratio=float( footer_band ) / 100.0 ) or [ ]
							
							raw_text = parser.rebuild_pages( pages=pdf_pages,
								preserve_page_breaks=preserve_page_breaks ) or ''
							
							documents = [ Document( page_content=raw_text,
								metadata={ 'loader': 'PdfLoader', 'source': pdf.name,
										'extract': 'geometry', 'header_band': int( header_band ),
										'footer_band': int( footer_band ),
										'preserve_page_breaks': preserve_page_breaks, } ) ]
							
							st.session_state.pdf_pages = pdf_pages
						else:
							loader = PdfLoader( )
							documents = loader.load( path, mode=mode, extract=extract,
								include=include, format=fmt ) or [ ]
							
							for document in documents:
								if not isinstance( getattr( document, 'metadata', None ), dict ):
									document.metadata = { }
								
								document.metadata[ 'loader' ] = 'PdfLoader'
								document.metadata.setdefault( 'source', pdf.name )
								document.metadata.setdefault( 'extract', 'legacy' )
							
							raw_text = '\n\n'.join( d.page_content for d in documents if
							                        hasattr( d, 'page_content' ) and isinstance(
								                        d.page_content,
								                        str ) and d.page_content.strip( ) )
							
							st.session_state.pdf_pages = None
					
					st.session_state.documents = documents
					st.session_state.raw_documents = list( documents )
					st.session_state.raw_text = raw_text
					st.session_state.processed_text = None
					st.session_state.displayed_text = ''
					st.session_state.processed_text_display = ''
					st.session_state.lines = None
					st.session_state.chunked_documents = None
					st.session_state.df_chunks = None
					st.session_state.active_loader = 'PdfLoader'
					
					st.session_state[
						'_loader_status' ] = f'Loaded {len( documents )} PDF document(s).'
				
				# --------------------------------------------------
				# Save
				# --------------------------------------------------
				can_save = (st.session_state.get( 'active_loader' ) == 'PdfLoader' and isinstance(
					st.session_state.get( 'raw_text' ), str ) and st.session_state.get(
					'raw_text' ).strip( ))
				
				if can_save:
					save_pdf.download_button( 'Save', data=st.session_state.get( 'raw_text' ),
						file_name='pdf_loader_output.txt', mime='text/plain', key='pdf_save',
						icon='💾', width='stretch' )
				else:
					save_pdf.button( 'Save', key='pdf_save_disabled', disabled=True, icon='💾',
						width='stretch' )
				
				render_document_processing_actions( 'PdfLoader', 'pdf' )
			
			# ------- Expander Excel Loader
			with st.expander( label='Excel Loader', icon='📊', expanded=False ):
				st.caption( 'API', help=cfg.EXCEL_LOADER )
				excel_file = st.file_uploader( 'Upload Excel file', type=[ 'xlsx', 'xls' ],
					key='excel_upload' )
				
				load_mode = st.selectbox( 'Load Mode', [ 'Tabular', 'Unstructured Document' ],
					index=0, key='excel_load_mode',)
				
				sheet_name = st.text_input( 'Sheet name (leave blank for all sheets)',
					key='excel_sheet' )
				
				table_prefix = st.text_input( 'table prefix', value='excel',
					help='Each sheet will be written as <prefix>_<sheetname>',
					key='excel_table_prefix' )
				
				unstructured_mode = st.selectbox( 'Document Mode', [ 'single', 'elements' ],
					index=0, key='excel_unstructured_mode',
					help='Used only with "Unstructured Documents".' )
				
				render_document_processing_inputs( 'ExcelLoader', 'excel' )
				
				# --------------------------------------------------
				# Buttons: Load / Clear / Save
				# --------------------------------------------------
				col_load, col_clear, col_save = st.columns( 3 )
				load_excel = col_load.button( 'Load', key='excel_load', icon='📤', width='stretch' )
				clear_excel = col_clear.button( 'Clear', key='excel_clear', icon='🧹',
					width='stretch' )
				can_save = (st.session_state.get( 'active_loader' ) == 'ExcelLoader' and isinstance(
					st.session_state.get( 'raw_text' ), str ) and st.session_state.get(
					'raw_text' ).strip( ))
				
				if can_save:
					col_save.download_button( 'Save', data=st.session_state.get( 'raw_text' ),
						file_name='excel_loader_output.txt', mime='text/plain', key='excel_save',
						icon='💾', width='stretch' )
				else:
					col_save.button( 'Save', key='excel_save_disabled', disabled=True, icon='💾',
						width='stretch' )
				
				# --------------------------------------------------
				# Clear (remove only ExcelLoader documents)
				# --------------------------------------------------
				if clear_excel and st.session_state.get( 'documents' ):
					reset_document_processing_controls( 'excel' )
					st.session_state.documents = [ d for d in st.session_state.documents if
					                               d.metadata.get( 'loader' ) != 'ExcelLoader' ]
					
					st.session_state.raw_documents = [ d for d in st.session_state.documents if
					                                   isinstance( getattr( d, 'metadata', None ),
						                                   dict ) ] if st.session_state.documents else [ ]
					
					st.session_state.raw_text = ('\n\n'.join(
						d.page_content for d in st.session_state.documents if
						isinstance( d.page_content,
							str ) and d.page_content.strip( ) ) if st.session_state.documents else None)
					
					st.session_state.processed_text = None
					st.session_state.active_loader = None
					st.info( "ExcelLoader documents removed." )
				
				# --------------------------------------------------
				# Load
				# --------------------------------------------------
				if load_excel and excel_file:
					with tempfile.TemporaryDirectory( ) as tmp:
						excel_path = os.path.join( tmp, excel_file.name )
						with open( excel_path, 'wb' ) as f:
							f.write( excel_file.read( ) )
						
						documents = [ ]
						if load_mode == 'Tabular + SQLite':
							sqlite_path = os.path.join( 'stores', 'sqlite', 'data.db' )
							os.makedirs( os.path.dirname( sqlite_path ), exist_ok=True )
							if sheet_name.strip( ):
								dfs = { sheet_name: pd.read_excel( excel_path,
									sheet_name=sheet_name, ) }
							else:
								dfs = pd.read_excel( excel_path, sheet_name=None, )
							
							conn = sqlite3.connect( sqlite_path )
							try:
								for sheet, df in dfs.items( ):
									if df.empty:
										continue
									table_name = f'{table_prefix}_{sheet}'.replace( ' ',
										'_' ).lower( )
									df.to_sql( table_name, conn, if_exists='replace', index=False, )
									text = df.to_csv( index=False )
									documents.append( Document( page_content=text,
										metadata={ 'loader': 'ExcelLoader',
												'source': excel_file.name, 'sheet': sheet,
												'table': table_name, 'sqlite_db': sqlite_path,
												'load_mode': 'Tabular + SQLite', }, ) )
							finally:
								conn.close( )
						
						else:
							loader = ExcelLoader( )
							documents = loader.load( excel_path, mode=unstructured_mode,
								has_headers=True ) or [ ]
							
							for document in documents:
								if not isinstance( getattr( document, 'metadata', None ), dict ):
									document.metadata = { }
								
								document.metadata[ 'loader' ] = 'ExcelLoader'
								document.metadata.setdefault( 'source', excel_file.name )
								document.metadata[ 'load_mode' ] = 'Unstructured Document'
								document.metadata[ 'document_mode' ] = unstructured_mode
					
					if documents:
						existing_documents = st.session_state.get( 'documents' )
						if isinstance( existing_documents, list ) and existing_documents:
							st.session_state.documents.extend( documents )
						else:
							st.session_state.documents = list( documents )
						
						st.session_state.raw_documents = list( st.session_state.documents )
						st.session_state.raw_text = "\n\n".join(
							d.page_content for d in st.session_state.documents if
							isinstance( d.page_content, str ) and d.page_content.strip( ) )
						
						st.session_state.processed_text = None
						st.session_state.active_loader = 'ExcelLoader'
						
						if load_mode == 'Tabular + SQLite':
							st.success(
								f'Loaded {len( documents )} sheet(s) and stored in SQLite.' )
						else:
							st.success(
								f'Loaded {len( documents )} Excel {unstructured_mode!r} mode.' )
					else:
						if load_mode == 'Tabular + SQLite':
							st.warning( 'No data loaded (empty sheets or invalid selection).' )
						else:
							st.warning( 'No Excel document content was loaded.' )
				
				# ----------------------------
				# ------ Expander Markdown Loader
				# ----------------------------
				render_document_processing_actions( 'ExcelLoader', 'excel' )
			
			# ------- Expander Markdown Loader
			with st.expander( label='Markdown Loader', icon='🧾', expanded=False ):
				st.caption( 'API', help=cfg.MARKDOWN_LOADER )
				md = st.file_uploader( 'Upload Markdown', type=[ 'md', 'markdown' ],
					key='md_upload' )
				
				mode = st.selectbox( 'Mode', [ 'single', 'elements' ], index=0, key='md_mode',
					help='Use "single" for one combined document or "elements" for multiple.' )
				
				render_document_processing_inputs( 'MarkdownLoader', 'md' )
				
				# --------------------------------------------------
				# Buttons: Load / Clear / Save
				# --------------------------------------------------
				col_load, col_clear, col_save = st.columns( 3 )
				load_md = col_load.button( 'Load', key='md_load', icon='📤', width='stretch' )
				clear_md = col_clear.button( 'Clear', key='md_clear', icon='🧹', width='stretch' )
				can_save = (st.session_state.get( 'active_loader' ) == 'MarkdownLoader' \
				            and isinstance( st.session_state.get( 'raw_text' ), str ) \
				            and st.session_state.get( 'raw_text' ).strip( ))
				
				if can_save:
					col_save.download_button( 'Save', data=st.session_state.get( 'raw_text' ),
						file_name='markdown_loader_output.txt', mime='text/plain', key='md_save',
						icon='💾', width='stretch' )
				else:
					col_save.button( 'Save', key='md_save_disabled', disabled=True, icon='💾',
						width='stretch' )
				
				# --------------------------------------------------
				# Clear
				# --------------------------------------------------
				if clear_md:
					reset_document_processing_controls( 'md' )
					clear_if_active( 'MarkdownLoader' )
					st.info( "Markdown Loader state cleared." )
				
				# --------------------------------------------------
				# Load
				# --------------------------------------------------
				if load_md and md:
					with tempfile.TemporaryDirectory( ) as tmp:
						path = os.path.join( tmp, md.name )
						with open( path, 'wb' ) as f:
							f.write( md.read( ) )
						
						loader = MarkdownLoader( )
						documents = loader.load( path, mode=mode ) or [ ]
					
					st.session_state.documents = documents
					st.session_state.raw_documents = list( documents )
					st.session_state.raw_text = '\n\n'.join( d.page_content for d in documents if
					                                         hasattr( d, 'page_content' ) \
					                                         and isinstance( d.page_content, str ) \
					                                         and d.page_content.strip( ) )
					
					st.session_state.active_loader = 'MarkdownLoader'
					st.success( f'Loaded {len( documents )} Markdown document(s).' )
				
				# ----------------------------
				# ---- Expander HTML Loader
				# ----------------------------
				render_document_processing_actions( 'MarkdownLoader', 'md' )
			
			# ------- Expander HTML Loader
			with st.expander( label='HTML Loader', icon='🌐', expanded=False ):
				st.caption( 'API', help=cfg.HTML_LOADER )
				html = st.file_uploader( 'Upload HTML', type=[ 'html', 'htm' ], key='html_upload' )
				render_document_processing_inputs( 'HtmlLoader', 'html' )
				
				# --------------------------------------------------
				# Buttons: Load / Clear / Save (same row, same style)
				# --------------------------------------------------
				col_load, col_clear, col_save = st.columns( 3 )
				load_html = col_load.button( 'Load', key='html_load', icon='📤', width='stretch' )
				clear_html = col_clear.button( 'Clear', key='html_clear', icon='🧹',
					width='stretch' )
				
				can_save = (st.session_state.get( 'active_loader' ) == 'HtmlLoader' and isinstance(
					st.session_state.get( 'raw_text' ), str ) \
				            and st.session_state.get( 'raw_text' ).strip( ) )
				
				if can_save:
					col_save.download_button( 'Save', data=st.session_state.get( 'raw_text' ),
						file_name='html_loader_output.txt', mime='text/plain', key='html_save',
						icon='💾', width='stretch' )
				else:
					col_save.button( 'Save', key='html_save_disabled', disabled=True, icon='💾',
						width='stretch' )
				
				# --------------------------------------------------
				# Clear
				# --------------------------------------------------
				if clear_html:
					reset_document_processing_controls( 'html' )
					clear_if_active( 'HtmlLoader' )
					st.info( 'HTML Loader state cleared.' )
				
				# --------------------------------------------------
				# Load
				# --------------------------------------------------
				if load_html and html:
					with tempfile.TemporaryDirectory( ) as tmp:
						path = os.path.join( tmp, html.name )
						with open( path, 'wb' ) as f:
							f.write( html.read( ) )
						
						loader = HtmlLoader( )
						documents = loader.load( path )
					
					st.session_state.documents = documents
					st.session_state.raw_documents = list( documents )
					st.session_state.raw_text = '\n\n'.join( d.page_content for d in documents )
					st.session_state.active_loader = 'HtmlLoader'
					st.success( f'Loaded {len( documents )} HTML document(s).' )
				
				# ----------------------------
				# --------- Expander JSON Loader
				# ----------------------------
				render_document_processing_actions( 'HtmlLoader', 'html' )
			
			# ------- Expander JSON Loader
			with st.expander( label='JSON Loader', icon='🧩', expanded=False ):
				st.caption( 'API', help=cfg.JSON_LOADER )
				js = st.file_uploader( 'Upload JSON', type=[ 'json', 'jsonl' ], key='json_upload', )
				jq_schema = st.text_input( 'jq Schema', value='.', key='json_jq_schema',
					help='Examples: ., .[], .messages[], .content' )
				
				content_key = st.text_input( 'Content Key (optional)', value='',
					key='json_content_key',
					help='Use when jq_schema returns objects page_content.' )
				
				is_lines = st.checkbox( 'JSON Lines', value=False, key='json_lines', )
				is_text = st.checkbox( 'Extracted content is already text', value=True,
					key='json_text_content',
					help='Turn this off when jq_schema/content_key selects structured values' )
				
				render_document_processing_inputs( 'JsonLoader', 'json' )
				
				# --------------------------------------------------
				# Buttons: Load / Clear / Save
				# --------------------------------------------------
				col_load, col_clear, col_save = st.columns( 3 )
				load_json = col_load.button( 'Load', key='json_load', icon='📤', width='stretch' )
				clear_json = col_clear.button( 'Clear', key='json_clear', icon='🧹',
					width='stretch' )
				
				can_save = (st.session_state.get( 'active_loader' ) == 'JsonLoader' and isinstance(
					st.session_state.get( 'raw_text' ), str ) and st.session_state.get(
					'raw_text' ).strip( ))
				
				if can_save:
					col_save.download_button( 'Save', data=st.session_state.get( 'raw_text' ),
						file_name='json_loader_output.txt', mime='text/plain', key='json_save',
						icon='💾', width='stretch' )
				else:
					col_save.button( 'Save', key='json_save_disabled', disabled=True, icon='💾',
						width='stretch' )
				
				# --------------------------------------------------
				# Clear
				# --------------------------------------------------
				if clear_json:
					reset_document_processing_controls( 'json' )
					clear_if_active( 'JsonLoader' )
					st.info( 'JSON Loader state cleared.' )
				
				# --------------------------------------------------
				# Load
				# --------------------------------------------------
				if load_json and js:
					with tempfile.TemporaryDirectory( ) as tmp:
						path = os.path.join( tmp, js.name )
						with open( path, 'wb' ) as f:
							f.write( js.read( ) )
						
						loader = JsonLoader( )
						documents = loader.load( path, jq_schema=jq_schema, content_key=content_key,
							is_text=is_text, is_lines=is_lines, ) or [ ]
					
					st.session_state.documents = documents
					st.session_state.raw_documents = list( documents )
					st.session_state.raw_text = "\n\n".join( d.page_content for d in documents if
					                                         hasattr( d, 'page_content' ) \
					                                         and isinstance( d.page_content, str ) \
					                                         and d.page_content.strip( ) )
					st.session_state.active_loader = "JsonLoader"
					st.success( f"Loaded {len( documents )} JSON document(s)." )
				
				render_document_processing_actions( 'JsonLoader', 'json' )
		
		with st.expander( label='Web Documents', expanded=False ):
			
			# ------- Expander ArXiv Loader
			with st.expander( label='ArXiv Loader', icon='🧠', expanded=False ):
				st.caption( 'API', help=cfg.ARXIV_LOADER )
				arxiv_query = st.text_input( 'Query', placeholder='e.g., transformer OR llm',
					key='arxiv_query', )
				
				arxiv_max_chars = st.number_input( 'Max characters per document', min_value=250,
					max_value=100000, value=1000, step=250, key='arxiv_max_chars',
					help='Maximum characters read', )
				
				col_fetch, col_clear, col_save = st.columns( 3 )
				arxiv_fetch = col_fetch.button( 'Load', key='arxiv_fetch', icon='📤',
					width='stretch' )
				arxiv_clear = col_clear.button( 'Clear', key='arxiv_clear', icon='🧹',
					width='stretch' )
				can_save = (st.session_state.get( 'active_loader' ) == 'ArXivLoader' and isinstance(
					st.session_state.get( 'raw_text' ), str ) and st.session_state.get(
					'raw_text' ).strip( ))
				
				if can_save:
					col_save.download_button( 'Save', data=st.session_state.get( 'raw_text' ),
						file_name='arxiv_loader_output.txt', mime='text/plain', key='arxiv_save',
						icon='💾', width='stretch' )
				else:
					col_save.button( 'Save', key='arxiv_save_disabled', disabled=True, icon='💾',
						width='stretch' )
				
				if arxiv_clear and st.session_state.get( 'documents' ):
					st.session_state.documents = [ d for d in st.session_state.documents if
					                               d.metadata.get( 'loader' ) != 'ArXivLoader' ]
					st.session_state.raw_text = rebuild_raw_text_from_documents( )
					st.session_state[ '_loader_status' ] = 'ArXivLoader documents removed.'
				
				if arxiv_fetch and arxiv_query:
					loader = ArXivLoader( )
					documents = loader.load( arxiv_query, max_chars=int( arxiv_max_chars ), ) or [ ]
					
					for d in documents:
						d.metadata[ 'loader' ] = 'ArXivLoader'
						d.metadata[ 'source' ] = arxiv_query
					
					if documents:
						if st.session_state.get( 'documents' ):
							st.session_state.documents.extend( documents )
						else:
							st.session_state.documents = documents
							st.session_state.raw_documents = list( documents )
						
						st.session_state.raw_text = rebuild_raw_text_from_documents( )
						st.session_state.active_loader = 'ArXivLoader'
						
						st.session_state[
							'_loader_status' ] = f'Fetched {len( documents )} document(s).'
				
				render_document_processing_controls( 'ArXivLoader', 'loader_arxiv_loader' )
			
			# ------- Expander Wikipedia Loader
			with st.expander( label='Wikipedia Loader', icon='📚', expanded=False ):
				st.caption( 'API', help=cfg.WIKIPEDIA_LOADER )
				wiki_query = st.text_input( 'Query',
					placeholder='e.g., Natural language processing', key='wiki_query', )
				
				wiki_max_docs = st.number_input( 'Max documents', min_value=1, max_value=250,
					value=25, step=1, key='wiki_max_docs',
					help='Maximum number of documents loaded', )
				
				wiki_max_chars = st.number_input( 'Max characters per document', min_value=250,
					max_value=100000, value=4000, step=250, key='wiki_max_chars',
					help='Upper limit on the number of characters', )
				
				col_fetch, col_clear, col_save = st.columns( 3 )
				wiki_fetch = col_fetch.button( 'Load', key='wiki_fetch', icon='📤', width='stretch' )
				wiki_clear = col_clear.button( 'Clear', key='wiki_clear', icon='🧹',
					width='stretch' )
				
				can_save = (st.session_state.get( 'active_loader' ) == 'WikiLoader' and isinstance(
					st.session_state.get( 'raw_text' ), str ) and st.session_state.get(
					'raw_text' ).strip( ))
				
				if can_save:
					col_save.download_button( 'Save', data=st.session_state.get( 'raw_text' ),
						file_name='wiki_loader_output.txt', mime='text/plain', key='wiki_save',
						icon='💾', width='stretch' )
				else:
					col_save.button( 'Save', key='wiki_save_disabled', disabled=True, icon='💾',
						width='stretch' )
				
				if wiki_clear and st.session_state.get( 'documents' ):
					st.session_state.documents = [ d for d in st.session_state.documents if
					                               d.metadata.get( 'loader' ) != 'WikiLoader' ]
					st.session_state.raw_text = rebuild_raw_text_from_documents( )
					st.session_state[ '_loader_status' ] = 'WikiLoader documents removed.'
				
				if wiki_fetch and wiki_query:
					loader = WikiLoader( )
					documents = loader.load( wiki_query, max_docs=int( wiki_max_docs ),
						max_chars=int( wiki_max_chars ), ) or [ ]
					
					for d in documents:
						d.metadata[ 'loader' ] = 'WikiLoader'
						d.metadata[ 'source' ] = wiki_query
					
					if documents:
						if st.session_state.get( 'documents' ):
							st.session_state.documents.extend( documents )
						else:
							st.session_state.documents = documents
							st.session_state.raw_documents = list( documents )
						
						st.session_state.raw_text = rebuild_raw_text_from_documents( )
						st.session_state.active_loader = 'WikiLoader'
						
						st.session_state[ '_loader_status' ] = (
								f'Fetched {len( documents )} Wikipedia document(s).')
				
				render_document_processing_controls( 'WikiLoader', 'loader_wikipedia_loader' )
			
			# ------- Expander GitHub Loader
			with st.expander( label='GitHub Loader', icon='🐙', expanded=False ):
				st.caption( 'API', help=cfg.GITHUB_LOADER )
				gh_url = st.text_input( 'GitHub API URL', placeholder='https://api.github.com',
					value='https://api.github.com', key='gh_url',
					help='GitHub REST API base URL.', )
				
				gh_repo = st.text_input( 'Repo (owner/name)', placeholder='openai/openai-python',
					key='gh_repo', help='Name of the repository.', )
				
				gh_branch = st.text_input( 'Branch', placeholder='main', value='main',
					key='gh_branch', help='The branch of the repository.', )
				
				gh_filetype = st.text_input( 'File type filter', value='.md', key='gh_filetype',
					help='Filtering by file type. Example: .py, .md, .txt', )
				
				gh_access_token = st.text_input( 'GitHub Access Token (optional)', value="",
					type='password', key='gh_access_token', help='Optional personal access token.' )
				
				col_fetch, col_clear, col_save = st.columns( 3 )
				gh_fetch = col_fetch.button( 'Load', key='gh_fetch', icon='📤', width='stretch' )
				gh_clear = col_clear.button( "Clear", key="gh_clear", icon='🧹', width='stretch' )
				
				can_save = (
						st.session_state.get( 'active_loader' ) == 'GithubLoader' and isinstance(
					st.session_state.get( 'raw_text' ), str ) and st.session_state.get(
					'raw_text' ).strip( ))
				
				if can_save:
					col_save.download_button( 'Save', data=st.session_state.get( 'raw_text' ),
						file_name='github_loader_output.txt', mime='text/plain', key='gh_save',
						icon='💾', width='stretch' )
				else:
					col_save.button( 'Save', key='gh_save_disabled', disabled=True, icon='💾',
						width='stretch' )
				
				if gh_clear and st.session_state.get( 'documents' ):
					st.session_state.documents = [ d for d in st.session_state.documents if
					                               d.metadata.get( 'loader' ) != 'GithubLoader' ]
					st.session_state.raw_text = rebuild_raw_text_from_documents( )
					st.session_state[ '_loader_status' ] = 'GithubLoader documents removed.'
				
				if gh_fetch and gh_repo and gh_branch:
					loader = GithubLoader( )
					documents = loader.load( gh_url, gh_repo, gh_branch, gh_filetype,
						gh_access_token, ) or [ ]
					
					for d in documents:
						if not isinstance( getattr( d, 'metadata', None ), dict ):
							d.metadata = { }
						d.metadata[ 'loader' ] = 'GithubLoader'
						d.metadata[ 'source' ] = f'{gh_repo}@{gh_branch}'
					
					if documents:
						if st.session_state.get( 'documents' ):
							st.session_state.documents.extend( documents )
						else:
							st.session_state.documents = documents
							st.session_state.raw_documents = list( documents )
						
						st.session_state.raw_text = rebuild_raw_text_from_documents( )
						st.session_state.active_loader = 'GithubLoader'
						
						st.session_state[
							'_loader_status' ] = f'Fetched {len( documents )} GitHub document(s).'
				
				render_document_processing_controls( 'GithubLoader', 'loader_github_loader' )
			
			# ------- Expander Web Loader
			with st.expander( label='Web Loader', icon='🌐', expanded=False ):
				st.caption( 'API', help=cfg.WEB_LOADER )
				urls = st.text_area( 'Enter one URL per line',
					placeholder="https://example.com\nhttps://another.com", key='web_urls', )
				
				web_timeout = st.number_input( 'Timeout (seconds)', min_value=1, max_value=120,
					value=10, step=1, key='web_timeout', )
				
				web_ignore = st.checkbox( 'Continue On Failure', value=True, key='web_ignore',
					help='Keep loading remaining URLs if one page fails.' )
				
				col_fetch, col_clear, col_save = st.columns( 3 )
				load_web = col_fetch.button( 'Load', key='web_fetch', icon='📤', width='stretch' )
				clear_web = col_clear.button( "Clear", key="web_clear", icon='🧹', width='stretch' )
				can_save = (st.session_state.get( 'active_loader' ) == 'WebLoader' and isinstance(
					st.session_state.get( 'raw_text' ), str ) and st.session_state.get(
					'raw_text' ).strip( ))
				
				if can_save:
					col_save.download_button( 'Save', data=st.session_state.get( 'raw_text' ),
						file_name='web_loader_output.txt', mime='text/plain', key='web_save',
						icon='💾', width='stretch' )
				else:
					col_save.button( 'Save', key='web_save_disabled', disabled=True, icon='💾',
						width='stretch' )
				
				if clear_web and st.session_state.get( 'documents' ):
					st.session_state.documents = [ d for d in st.session_state.documents if
					                               d.metadata.get( 'loader' ) != 'WebLoader' ]
					st.session_state.raw_text = rebuild_raw_text_from_documents( )
					st.session_state[ '_loader_status' ] = 'WebLoader documents removed.'
				
				if load_web and urls.strip( ):
					loader = WebLoader( recursive=False )
					new_docs = [ ]
					for url in [ u.strip( ) for u in urls.splitlines( ) if u.strip( ) ]:
						documents = loader.load( urls=url, timeout=int( web_timeout ),
							ignore=bool( web_ignore ), progress=True ) or [ ]
						
						for d in documents:
							if not isinstance( getattr( d, 'metadata', None ), dict ):
								d.metadata = { }
							d.metadata[ 'loader' ] = 'WebLoader'
							d.metadata[ 'source' ] = url
						
						new_docs.extend( documents )
					
					if new_docs:
						if st.session_state.get( 'documents' ):
							st.session_state.documents.extend( new_docs )
						else:
							st.session_state.documents = new_docs
							st.session_state.raw_documents = list( new_docs )
						
						st.session_state.raw_text = rebuild_raw_text_from_documents( )
						st.session_state.active_loader = 'WebLoader'
						st.session_state[
							'_loader_status' ] = f'Fetched {len( new_docs )} web document(s).'
				
				render_document_processing_controls( 'WebLoader', 'loader_web_loader' )
			
			# ------- Expander Web Crawler
			with st.expander( label='Web Crawler', icon='🕷️', expanded=False ):
				st.caption( 'API', help=cfg.WEB_CRAWLER )
				start_url = st.text_input( 'Start URL', placeholder='https://example.com',
					key='crawl_start_url', )
				
				max_depth = st.number_input( 'Max crawl depth', min_value=1, max_value=5, value=2,
					step=1, key='crawl_depth', )
				
				crawl_timeout = st.number_input( 'Timeout (seconds)', min_value=1, max_value=120,
					value=10, step=1, key='crawl_timeout', )
				
				stay_on_domain = st.checkbox( 'Stay on starting domain', value=True,
					key='crawl_domain_lock', )
				
				col_run, col_clear, col_save = st.columns( 3 )
				run_crawl = col_run.button( 'Load', key='crawl_run', icon='🏃', width='stretch' )
				clear_crawl = col_clear.button( 'Clear', key='crawl_clear', icon='🧹',
					width='stretch' )
				
				can_save = (st.session_state.get( 'active_loader' ) == 'WebCrawler' and isinstance(
					st.session_state.get( 'raw_text' ), str ) and st.session_state.get(
					'raw_text' ).strip( ))
				
				if can_save:
					col_save.download_button( 'Save', data=st.session_state.get( 'raw_text' ),
						file_name='web_crawler_output.txt', mime='text/plain', key='crawl_save',
						icon='💾', width='stretch' )
				else:
					col_save.button( 'Save', key='crawl_save_disabled', disabled=True, icon='💾',
						width='stretch' )
				
				if clear_crawl:
					clear_if_active( 'WebCrawler' )
					st.session_state.raw_text = rebuild_raw_text_from_documents( )
					st.session_state[ '_loader_status' ] = 'Web Crawler state cleared.'
				
				if run_crawl and isinstance( start_url, str ) and start_url.strip( ):
					loader = LoaderWebCrawler( url=start_url.strip( ), recursive=True,
						max_depth=int( max_depth ), prevent_outside=bool( stay_on_domain ),
						timeout=int( crawl_timeout ), ignore=True, progress=True, )
					
					documents = loader.load( urls=start_url.strip( ), depth=int( max_depth ),
						timeout=int( crawl_timeout ), ignore=True, progress=True,
						prevent_outside=bool( stay_on_domain ), ) or [ ]
					
					for document in documents:
						if not isinstance( getattr( document, 'metadata', None ), dict ):
							document.metadata = { }
						
						document.metadata[ 'loader' ] = 'WebCrawler'
						document.metadata.setdefault( 'source', start_url.strip( ) )
						document.metadata.setdefault( 'max_depth', int( max_depth ) )
						document.metadata.setdefault( 'timeout', int( crawl_timeout ) )
						document.metadata.setdefault( 'prevent_outside', bool( stay_on_domain ) )
					
					st.session_state.documents = documents
					st.session_state.raw_documents = list( documents )
					st.session_state.raw_text = '\n\n'.join( d.page_content for d in documents if
					                                         hasattr( d,
						                                         'page_content' ) and isinstance(
						                                         d.page_content,
						                                         str ) and d.page_content.strip( ) )
					st.session_state.processed_text = None
					st.session_state.lines = None
					st.session_state.chunked_documents = None
					st.session_state.df_chunks = None
					st.session_state.active_loader = 'WebCrawler'
					st.session_state[
						'_loader_status' ] = f'Crawled {len( documents )} document(s).'
				
				render_document_processing_controls( 'WebCrawler', 'loader_web_crawler' )
			
			# ------- Expander Email Loader
			with st.expander( label='E-mail Loader', icon='📧', expanded=False ):
				st.caption( 'API', help=cfg.EMAIL_LOADER )
				email_file = st.file_uploader( 'Upload Email File', type=[ 'eml' ],
					key='email_upload', )
				
				email_mode = st.selectbox( 'Mode', options=[ 'elements', 'single' ], index=0,
					key='email_mode', )
				
				email_attachments = st.checkbox( 'Process Attachments', value=False,
					key='email_attachments', )
				
				# --------------------------------------------------
				# Buttons: Load / Clear / Save
				# --------------------------------------------------
				col_load, col_clear, col_save = st.columns( 3 )
				load_email = col_load.button( 'Load', key='email_load', icon='📤', width='stretch' )
				clear_email = col_clear.button( 'Clear', key='email_clear', icon='🧹',
					width='stretch' )
				
				can_save = (st.session_state.get( 'active_loader' ) == 'EmailLoader' and isinstance(
					st.session_state.get( 'raw_text' ), str ) and st.session_state.get(
					'raw_text' ).strip( ))
				
				if can_save:
					col_save.download_button( 'Save', data=st.session_state.get( 'raw_text' ),
						file_name='email_loader_output.txt', mime='text/plain', key='email_save',
						icon='💾', width='stretch' )
				else:
					col_save.button( 'Save', key='email_save_disabled', disabled=True, icon='💾',
						width='stretch' )
				
				# --------------------------------------------------
				# Clear
				# --------------------------------------------------
				if clear_email:
					clear_if_active( 'EmailLoader' )
					st.session_state.raw_text = rebuild_raw_text_from_documents( )
					st.session_state[ '_loader_status' ] = 'Email Loader state cleared.'
				
				# --------------------------------------------------
				# Load
				# --------------------------------------------------
				if load_email and email_file:
					with tempfile.TemporaryDirectory( ) as tmp:
						path = os.path.join( tmp, email_file.name )
						with open( path, 'wb' ) as f:
							f.write( email_file.read( ) )
						
						loader = EmailLoader( )
						documents = loader.load( path=path, mode=email_mode,
							attachments=email_attachments, ) or [ ]
					
					for document in documents:
						if not isinstance( getattr( document, 'metadata', None ), dict ):
							document.metadata = { }
						
						document.metadata[ 'loader' ] = 'EmailLoader'
						document.metadata.setdefault( 'source', email_file.name )
						document.metadata.setdefault( 'mode', email_mode )
						document.metadata.setdefault( 'attachments', email_attachments )
					
					st.session_state.documents = documents
					st.session_state.raw_documents = list( documents )
					st.session_state.raw_text = '\n\n'.join( d.page_content for d in documents if
					                                         hasattr( d,
						                                         'page_content' ) and isinstance(
						                                         d.page_content,
						                                         str ) and d.page_content.strip( ) )
					
					st.session_state.processed_text = None
					st.session_state.lines = None
					st.session_state.chunked_documents = None
					st.session_state.df_chunks = None
					st.session_state.active_loader = 'EmailLoader'
					st.session_state[
						'_loader_status' ] = f'Loaded {len( documents )} email document(s).'
				
				render_document_processing_controls( 'EmailLoader', 'loader_e_mail_loader' )
			
			# ------- Expander PubMed Loader
			with st.expander( label='Pub Med Loader', icon='🧬', expanded=False ):
				st.caption( 'API', help=cfg.PUBMED_LOADER )
				pubmed_query = st.text_input( 'PubMed Query', value='', key='pubmed_query',
					placeholder='e.g. transformer models biomedical NLP', )
				
				pubmed_max_docs = st.number_input( 'Maximum Documents', min_value=1, value=5,
					step=1, key='pubmed_max_docs', )
				
				# --------------------------------------------------
				# Buttons: Load / Clear / Save
				# --------------------------------------------------
				col_load, col_clear, col_save = st.columns( 3 )
				load_pubmed = col_load.button( 'Load', key='pubmed_load', icon='📥',
					width='stretch' )
				clear_pubmed = col_clear.button( 'Clear', key='pubmed_clear', icon='🧹',
					width='stretch' )
				
				can_save = (st.session_state.get(
					'active_loader' ) == 'PubMedSearchLoader' and isinstance(
					st.session_state.get( 'raw_text' ), str ) and st.session_state.get(
					'raw_text' ).strip( ))
				
				if can_save:
					col_save.download_button( 'Save', data=st.session_state.get( 'raw_text' ),
						file_name='pubmed_loader_output.txt', mime='text/plain', key='pubmed_save',
						icon='💾', width='stretch' )
				else:
					col_save.button( 'Save', key='pubmed_save_disabled', disabled=True, icon='💾',
						width='stretch' )
				
				# --------------------------------------------------
				# Clear
				# --------------------------------------------------
				if clear_pubmed:
					clear_if_active( 'PubMedSearchLoader' )
					st.session_state.raw_text = rebuild_raw_text_from_documents( )
					st.session_state[ '_loader_status' ] = 'PubMed Loader state cleared.'
				
				# --------------------------------------------------
				# Load
				# --------------------------------------------------
				if load_pubmed and isinstance( pubmed_query, str ) and pubmed_query.strip( ):
					loader = PubMedSearchLoader( )
					documents = loader.load( query=pubmed_query.strip( ),
						max_docs=int( pubmed_max_docs ), ) or [ ]
					
					for document in documents:
						if not isinstance( getattr( document, 'metadata', None ), dict ):
							document.metadata = { }
						
						document.metadata[ 'loader' ] = 'PubMedSearchLoader'
						document.metadata.setdefault( 'query', pubmed_query.strip( ) )
						document.metadata.setdefault( 'max_docs', int( pubmed_max_docs ) )
					
					st.session_state.documents = documents
					st.session_state.raw_documents = list( documents )
					st.session_state.raw_text = '\n\n'.join( d.page_content for d in documents if
					                                         hasattr( d, 'page_content' ) \
					                                         and isinstance( d.page_content, str ) \
					                                         and d.page_content.strip( ) )
					st.session_state.processed_text = None
					st.session_state.lines = None
					st.session_state.chunked_documents = None
					st.session_state.df_chunks = None
					st.session_state.active_loader = 'PubMedSearchLoader'
					st.session_state[ '_loader_status' ] = \
						f'Loaded {len( documents )} PubMed document(s).'
				
				render_document_processing_controls( 'PubMedSearchLoader', 'loader_pub_med_loader' )
			
			# ------- Expander Open City Loader
			with st.expander( label='Open City Loader', icon='🏙️', expanded=False ):
				st.caption( 'API', help=cfg.OPEN_CITY_DATA_LOADER )
				open_city_id = st.text_input( 'City Domain', value='', key='open_city_id',
					placeholder='e.g. data.sfgov.org',
					help='City domain identifier for the Socrata-backed portal.', icon='💾',
					width='stretch' )
				
				open_city_dataset_id = st.text_input( 'Dataset ID', value='',
					key='open_city_dataset_id', placeholder='e.g. vw6y-z8j6',
					help='Dataset identifier from the city portal.', icon='💾', width='stretch' )
				
				open_city_limit = st.number_input( 'Maximum Records', min_value=1, value=100,
					step=1, key='open_city_limit', )
				
				# --------------------------------------------------
				# Buttons: Load / Clear / Save
				# --------------------------------------------------
				col_load, col_clear, col_save = st.columns( 3 )
				load_open_city = col_load.button( 'Load', key='open_city_load', icon='📥',
					width='stretch' )
				clear_open_city = col_clear.button( 'Clear', key='open_city_clear', icon='🧹',
					width='stretch' )
				
				can_save = (
						st.session_state.get( 'active_loader' ) == 'OpenCityLoader' and isinstance(
					st.session_state.get( 'raw_text' ), str ) and st.session_state.get(
					'raw_text' ).strip( ))
				
				if can_save:
					col_save.download_button( 'Save', data=st.session_state.get( 'raw_text' ),
						file_name='open_city_loader_output.txt', mime='text/plain',
						key='open_city_save', icon='💾', width='stretch' )
				else:
					col_save.button( 'Save', key='open_city_save_disabled', disabled=True, icon='💾',
						width='stretch' )
				
				# --------------------------------------------------
				# Clear
				# --------------------------------------------------
				if clear_open_city:
					clear_if_active( 'OpenCityLoader' )
					st.session_state.raw_text = rebuild_raw_text_from_documents( )
					st.session_state[ '_loader_status' ] = 'Open City Loader state cleared.'
				
				# --------------------------------------------------
				# Load
				# --------------------------------------------------
				if (load_open_city and isinstance( open_city_id,
						str ) and open_city_id.strip( ) and isinstance( open_city_dataset_id,
					str ) and open_city_dataset_id.strip( )):
					loader = OpenCityLoader( )
					documents = loader.load( city_id=open_city_id.strip( ),
						dataset_id=open_city_dataset_id.strip( ),
						limit=int( open_city_limit ), ) or [ ]
					
					for document in documents:
						if not isinstance( getattr( document, 'metadata', None ), dict ):
							document.metadata = { }
						
						document.metadata[ 'loader' ] = 'OpenCityLoader'
						document.metadata.setdefault( 'city_id', open_city_id.strip( ) )
						document.metadata.setdefault( 'dataset_id', open_city_dataset_id.strip( ) )
						document.metadata.setdefault( 'limit', int( open_city_limit ) )
					
					st.session_state.documents = documents
					st.session_state.raw_documents = list( documents )
					st.session_state.raw_text = '\n\n'.join( d.page_content for d in documents if
					                                         hasattr( d, 'page_content' ) \
					                                         and isinstance( d.page_content, str )
					                                         and d.page_content.strip( ) )
					st.session_state.processed_text = None
					st.session_state.lines = None
					st.session_state.chunked_documents = None
					st.session_state.df_chunks = None
					st.session_state.active_loader = 'OpenCityLoader'
					st.session_state[ '_loader_status' ] = \
						f'Loaded {len( documents )} Open City document(s).'
				
				render_document_processing_controls( 'OpenCityLoader', 'loader_open_city_loader' )
		
		with st.expander( label='Cloud Documents', expanded=False ):
			
			# ------- Expander OneDrive Loader
			with st.expander( label='OneDrive Loader', icon='🟦', expanded=False ):
				st.caption( 'API', help=cfg.ONEDRIVE_LOADER )
				onedrive_drive_id = st.text_input( 'Drive ID', value='', key='onedrive_drive_id',
					placeholder='OneDrive drive identifier', )
				
				onedrive_folder_path = st.text_input( 'Folder Path', value='',
					key='onedrive_folder_path', placeholder='Optional folder path within the drive',
					help='Leave blank to load the drive target directly.', )
				
				# --------------------------------------------------
				# Buttons: Load / Clear / Save
				# --------------------------------------------------
				col_load, col_clear, col_save = st.columns( 3 )
				load_onedrive = col_load.button( 'Load', key='onedrive_load', icon='📤',
					width='stretch' )
				clear_onedrive = col_clear.button( 'Clear', key='onedrive_clear', icon='🧹',
					width='stretch' )
				
				can_save = (st.session_state.get(
					'active_loader' ) == 'OneDriveDocLoader' and isinstance(
					st.session_state.get( 'raw_text' ), str ) and st.session_state.get(
					'raw_text' ).strip( ))
				
				if can_save:
					col_save.download_button( 'Save', data=st.session_state.get( 'raw_text' ),
						file_name='onedrive_loader_output.txt', mime='text/plain',
						key='onedrive_save', icon='💾', width='stretch' )
				else:
					col_save.button( 'Save', key='onedrive_save_disabled', disabled=True, icon='💾',
						width='stretch' )
				
				# --------------------------------------------------
				# Clear
				# --------------------------------------------------
				if clear_onedrive:
					clear_if_active( 'OneDriveDocLoader' )
					st.session_state.raw_text = rebuild_raw_text_from_documents( )
					st.session_state[ '_loader_status' ] = 'OneDrive Loader state cleared.'
				
				# --------------------------------------------------
				# Load
				# --------------------------------------------------
				if (load_onedrive and isinstance( onedrive_drive_id,
						str ) and onedrive_drive_id.strip( )):
					loader = OneDriveDocLoader( )
					documents = loader.load( drive_id=onedrive_drive_id.strip( ),
						folder_path=onedrive_folder_path.strip( ) or None, object_ids=None,
						auth_with_token=False ) or [ ]
					
					for document in documents:
						if not isinstance( getattr( document, 'metadata', None ), dict ):
							document.metadata = { }
						
						document.metadata[ 'loader' ] = 'OneDriveDocLoader'
						document.metadata.setdefault( 'drive_id', onedrive_drive_id.strip( ) )
						document.metadata.setdefault( 'folder_path',
							onedrive_folder_path.strip( ) or None, )
						
						if onedrive_folder_path.strip( ):
							document.metadata.setdefault( 'source',
								f"{onedrive_drive_id.strip( )}:{onedrive_folder_path.strip( )}" )
						else:
							document.metadata.setdefault( 'source', onedrive_drive_id.strip( ), )
					
					st.session_state.documents = documents
					st.session_state.raw_documents = list( documents )
					st.session_state.raw_text = '\n\n'.join( d.page_content for d in documents if
					                                         hasattr( d,
						                                         'page_content' ) and isinstance(
						                                         d.page_content,
						                                         str ) and d.page_content.strip( ) )
					st.session_state.processed_text = None
					st.session_state.lines = None
					st.session_state.chunked_documents = None
					st.session_state.df_chunks = None
					st.session_state.active_loader = 'OneDriveDocLoader'
					st.session_state[
						'_loader_status' ] = f'Loaded {len( documents )} OneDrive document(s).'
				
				render_document_processing_controls( 'OneDriveDocLoader', 'loader_onedrive_loader' )
			
			# ------- Expander Google Cloud File Loader
			with st.expander( label='Google Cloud File Loader', icon='☁️', expanded=False ):
				st.caption( 'API', help=cfg.WEB_CRAWLER )
				gcs_project_name = st.text_input( 'Project Name', value='',
					key='gcs_file_project_name', placeholder='e.g. my-gcp-project', )
				
				gcs_bucket = st.text_input( 'Bucket', value='', key='gcs_file_bucket',
					placeholder='e.g. my-bucket', )
				
				gcs_blob = st.text_input( 'Blob', value='', key='gcs_file_blob',
					placeholder='e.g. documents/report.pdf', )
				
				# ---------------- Buttons: Load / Clear / Save
				col_load, col_clear, col_save = st.columns( 3 )
				load_gcs_file = col_load.button( 'Load', key='gcs_file_load', icon='📤',
					width='stretch' )
				clear_gcs_file = col_clear.button( 'Clear', key='gcs_file_clear', icon='🧹',
					width='stretch' )
				can_save = (st.session_state.get(
					'active_loader' ) == 'GoogleCloudFileLoader' and isinstance(
					st.session_state.get( 'raw_text' ), str ) and st.session_state.get(
					'raw_text' ).strip( ))
				
				if can_save:
					col_save.download_button( 'Save', data=st.session_state.get( 'raw_text' ),
						file_name='google_cloud_file_loader_output.txt', mime='text/plain',
						key='gcs_file_save', icon='💾', width='stretch' )
				else:
					col_save.button( 'Save', key='gcs_file_save_disabled', disabled=True, icon='💾',
						width='stretch' )
				
				# --------------------------------------------------
				# Clear
				# --------------------------------------------------
				if clear_gcs_file:
					clear_if_active( 'GoogleCloudFileLoader' )
					st.session_state.raw_text = rebuild_raw_text_from_documents( )
					st.session_state[ '_loader_status' ] = ('Google Cloud File Loader state '
					                                        'cleared.')
				
				# --------------------------------------------------
				# Load
				# --------------------------------------------------
				if (load_gcs_file and isinstance( gcs_project_name,
						str ) and gcs_project_name.strip( ) and isinstance( gcs_bucket,
					str ) and gcs_bucket.strip( ) and isinstance( gcs_blob,
					str ) and gcs_blob.strip( )):
					loader = GoogleCloudFileLoader( )
					documents = loader.load( project_name=gcs_project_name.strip( ),
						bucket=gcs_bucket.strip( ), blob=gcs_blob.strip( ), ) or [ ]
					
					for document in documents:
						if not isinstance( getattr( document, 'metadata', None ), dict ):
							document.metadata = { }
						
						document.metadata[ 'loader' ] = 'GoogleCloudFileLoader'
						document.metadata.setdefault( 'project_name', gcs_project_name.strip( ) )
						document.metadata.setdefault( 'bucket', gcs_bucket.strip( ) )
						document.metadata.setdefault( 'blob', gcs_blob.strip( ) )
						document.metadata.setdefault( 'source',
							f"gs://{gcs_bucket.strip( )}/{gcs_blob.strip( )}" )
					
					st.session_state.documents = documents
					st.session_state.raw_documents = list( documents )
					st.session_state.raw_text = '\n\n'.join( d.page_content for d in documents if
					                                         hasattr( d,
						                                         'page_content' ) and isinstance(
						                                         d.page_content,
						                                         str ) and d.page_content.strip( ) )
					st.session_state.processed_text = None
					st.session_state.lines = None
					st.session_state.chunked_documents = None
					st.session_state.df_chunks = None
					st.session_state.active_loader = 'GoogleCloudFileLoader'
					st.session_state[ '_loader_status' ] = (
							f'Loaded {len( documents )} Google Cloud file '
							f'document(s).')
				
				render_document_processing_controls( 'GoogleCloudFileLoader',
					'loader_google_cloud_file_loader' )
			
			# ------- Expander AWS File Loader
			with st.expander( label='AWS File Loader', icon='🪣', expanded=False ):
				st.caption( 'API', help=cfg.AWS_S3FILE_LOADER )
				aws_file_bucket = st.text_input( 'Bucket', value='', key='aws_file_bucket',
					placeholder='e.g. my-s3-bucket', )
				
				aws_file_key = st.text_input( 'Object Key', value='', key='aws_file_key',
					placeholder='e.g. documents/report.pdf', )
				
				aws_file_region = st.text_input( 'Region Name', value='', key='aws_file_region',
					placeholder='e.g. us-east-1', )
				
				aws_file_api_version = st.text_input( 'API Version', value='',
					key='aws_file_api_version', placeholder='Optional', )
				
				aws_file_use_ssl = st.checkbox( 'Use SSL', value=True, key='aws_file_use_ssl', )
				aws_file_verify = st.text_input( 'Verify', value='', key='aws_file_verify',
					placeholder='Optional path or True / False',
					help='Leave blank for default behavior, or provide a CA bundle path.', )
				
				aws_file_endpoint_url = st.text_input( 'Endpoint URL', value='',
					key='aws_file_endpoint_url', placeholder='Optional custom endpoint', )
				
				# --------------------------------------------------
				# Buttons: Load / Clear / Save
				# --------------------------------------------------
				col_load, col_clear, col_save = st.columns( 3 )
				load_aws_file = col_load.button( label='Load', key='aws_file_load', icon='📤',
					width='stretch' )
				clear_aws_file = col_clear.button( label='Clear', key='aws_file_clear', icon='🧹',
					width='stretch' )
				can_save = (st.session_state.get(
					'active_loader' ) == 'AwsFileLoader' and isinstance(
					st.session_state.get( 'raw_text' ), str ) and st.session_state.get(
					'raw_text' ).strip( ))
				
				if can_save:
					col_save.download_button( 'Save', data=st.session_state.get( 'raw_text' ),
						file_name='aws_file_loader_output.txt', mime='text/plain',
						key='aws_file_save', icon='📥', width='stretch' )
				else:
					col_save.button( 'Save', key='aws_file_save_disabled', disabled=True, icon='💾',
						width='stretch' )
				
				# --------------------------------------------------
				# Clear
				# --------------------------------------------------
				if clear_aws_file:
					clear_if_active( 'AwsFileLoader' )
					st.session_state.raw_text = rebuild_raw_text_from_documents( )
					st.session_state[ '_loader_status' ] = 'AWS File Loader state cleared.'
				
				# --------------------------------------------------
				# Load
				# --------------------------------------------------
				if (load_aws_file and isinstance( aws_file_bucket,
						str ) and aws_file_bucket.strip( ) and isinstance( aws_file_key,
					str ) and aws_file_key.strip( )):
					verify_value: str | bool | None = None
					if isinstance( aws_file_verify, str ) and aws_file_verify.strip( ):
						verify_text = aws_file_verify.strip( )
						if verify_text.lower( ) == 'true':
							verify_value = True
						elif verify_text.lower( ) == 'false':
							verify_value = False
						else:
							verify_value = verify_text
					
					loader = AwsFileLoader( )
					documents = loader.load( bucket=aws_file_bucket.strip( ),
						key=aws_file_key.strip( ), region_name=aws_file_region.strip( ) or None,
						api_version=aws_file_api_version.strip( ) or None,
						use_ssl=bool( aws_file_use_ssl ), verify=verify_value,
						endpoint_url=aws_file_endpoint_url.strip( ) or None, ) or [ ]
					
					for document in documents:
						if not isinstance( getattr( document, 'metadata', None ), dict ):
							document.metadata = { }
						
						document.metadata[ 'loader' ] = 'AwsFileLoader'
						document.metadata.setdefault( 'bucket', aws_file_bucket.strip( ) )
						document.metadata.setdefault( 'key', aws_file_key.strip( ) )
						document.metadata.setdefault( 'region_name',
							aws_file_region.strip( ) or None )
						document.metadata.setdefault( 'api_version',
							aws_file_api_version.strip( ) or None )
						document.metadata.setdefault( 'use_ssl', bool( aws_file_use_ssl ) )
						document.metadata.setdefault( 'verify', verify_value )
						document.metadata.setdefault( 'endpoint_url',
							aws_file_endpoint_url.strip( ) or None )
						document.metadata.setdefault( 'source',
							f"s3://{aws_file_bucket.strip( )}/{aws_file_key.strip( )}" )
					
					st.session_state.documents = documents
					st.session_state.raw_documents = list( documents )
					st.session_state.raw_text = '\n\n'.join( d.page_content for d in documents if
					                                         hasattr( d,
						                                         'page_content' ) and isinstance(
						                                         d.page_content,
						                                         str ) and d.page_content.strip( ) )
					st.session_state.processed_text = None
					st.session_state.lines = None
					st.session_state.chunked_documents = None
					st.session_state.df_chunks = None
					st.session_state.active_loader = 'AwsFileLoader'
					st.session_state[
						'_loader_status' ] = f'Loaded {len( documents )} AWS file document(s).'
				
				render_document_processing_controls( 'AwsFileLoader', 'loader_aws_file_loader' )
			
			# ------- Expander Google Bucket Loader
			with st.expander( label='Google Bucket Loader', icon='🗂️', expanded=False ):
				gcs_bucket_project_name = st.text_input( 'Project Name', value='',
					key='gcs_bucket_project_name', placeholder='e.g. my-gcp-project', )
				
				gcs_bucket_name = st.text_input( 'Bucket', value='', key='gcs_bucket_name',
					placeholder='e.g. my-bucket', )
				
				gcs_bucket_prefix = st.text_input( 'Prefix', value='', key='gcs_bucket_prefix',
					placeholder='Optional folder / object prefix', )
				
				gcs_bucket_continue_on_failure = st.checkbox( 'Continue On Failure', value=False,
					key='gcs_bucket_continue_on_failure', )
				
				# --------------------------------------------------
				# Buttons: Load / Clear / Save
				# --------------------------------------------------
				col_load, col_clear, col_save = st.columns( 3 )
				load_gcs_bucket = col_load.button( 'Load', key='gcs_bucket_load', icon='📥',
					width='stretch' )
				clear_gcs_bucket = col_clear.button( 'Clear', key='gcs_bucket_clear', icon='🧹',
					width='stretch' )
				can_save = (st.session_state.get( 'active_loader' ) == 'GoogleBucketLoader' \
				            and isinstance( st.session_state.get( 'raw_text' ), str ) \
				            and st.session_state.get( 'raw_text' ).strip( ))
				
				if can_save:
					col_save.download_button( 'Save', data=st.session_state.get( 'raw_text' ),
						file_name='google_bucket_loader_output.txt', mime='text/plain',
						key='gcs_bucket_save', icon='💾', width='stretch' )
				else:
					col_save.button( 'Save', key='gcs_bucket_save_disabled', disabled=True,
						icon='💾', width='stretch' )
				
				# --------------------------------------------------
				# Clear
				# --------------------------------------------------
				if clear_gcs_bucket:
					clear_if_active( 'GoogleBucketLoader' )
					st.session_state.raw_text = rebuild_raw_text_from_documents( )
					st.session_state[ '_loader_status' ] = 'Google Bucket Loader state cleared.'
				
				# --------------------------------------------------
				# Load
				# --------------------------------------------------
				if (load_gcs_bucket and isinstance( gcs_bucket_project_name,
						str ) and gcs_bucket_project_name.strip( ) and isinstance( gcs_bucket_name,
					str ) and gcs_bucket_name.strip( )):
					loader = GoogleBucketLoader( )
					documents = loader.load( project_name=gcs_bucket_project_name.strip( ),
						bucket=gcs_bucket_name.strip( ), prefix=gcs_bucket_prefix.strip( ) or None,
						continue_on_failure=bool( gcs_bucket_continue_on_failure ), ) or [ ]
					
					for document in documents:
						if not isinstance( getattr( document, 'metadata', None ), dict ):
							document.metadata = { }
						
						document.metadata[ 'loader' ] = 'GoogleBucketLoader'
						document.metadata.setdefault( 'project_name',
							gcs_bucket_project_name.strip( ), )
						
						document.metadata.setdefault( 'bucket', gcs_bucket_name.strip( ), )
						document.metadata.setdefault( 'prefix',
							gcs_bucket_prefix.strip( ) or None, )
						document.metadata.setdefault( 'continue_on_failure',
							bool( gcs_bucket_continue_on_failure ), )
						
						if gcs_bucket_prefix.strip( ):
							document.metadata.setdefault( 'source',
								f'gs://{gcs_bucket_name.strip( )}/{gcs_bucket_prefix.strip( )}' )
						else:
							document.metadata.setdefault( 'source',
								f'gs://{gcs_bucket_name.strip( )}' )
					
					st.session_state.documents = documents
					st.session_state.raw_documents = list( documents )
					st.session_state.raw_text = '\n\n'.join( d.page_content for d in documents if
					                                         hasattr( d, 'page_content' ) \
					                                         and isinstance(  d.page_content, str ) \
					                                         and d.page_content.strip( ))
					st.session_state.processed_text = None
					st.session_state.lines = None
					st.session_state.chunked_documents = None
					st.session_state.df_chunks = None
					st.session_state.active_loader = 'GoogleBucketLoader'
					st.session_state[ '_loader_status' ] = \
						f'Loaded {len( documents )} Google bucket document(s).'
				
				render_document_processing_controls( 'GoogleBucketLoader',
					'loader_google_bucket_loader' )
			
			# ------- Expander AWS Bucket Loader
			with st.expander( label='AWS Bucket Loader', icon='🗃️', expanded=False ):
				aws_bucket_name = st.text_input( 'Bucket', value='', key='aws_bucket_name',
					placeholder='e.g. my-s3-bucket', )
				
				aws_bucket_prefix = st.text_input( 'Prefix', value='', key='aws_bucket_prefix',
					placeholder='Optional folder / object prefix', )
				
				aws_bucket_region = st.text_input( 'Region Name', value='', key='aws_bucket_region',
					placeholder='e.g. us-east-1', )
				
				aws_bucket_api_version = st.text_input( 'API Version', value='',
					key='aws_bucket_api_version', placeholder='Optional', )
				
				aws_bucket_use_ssl = st.checkbox( 'Use SSL', value=True, key='aws_bucket_use_ssl', )
				
				aws_bucket_verify = st.text_input( 'Verify', value='', key='aws_bucket_verify',
					placeholder='Optional path or True / False',
					help='Leave blank for default behavior, or provide a CA bundle path.', )
				
				aws_bucket_endpoint_url = st.text_input( 'Endpoint URL', value='',
					key='aws_bucket_endpoint_url', placeholder='Optional custom endpoint', )
				
				# --------------------------------------------------
				# Buttons: Load / Clear / Save
				# --------------------------------------------------
				col_load, col_clear, col_save = st.columns( 3 )
				load_aws_bucket = col_load.button( 'Load', key='aws_bucket_load', icon='📤',
					width='stretch' )
				
				clear_aws_bucket = col_clear.button( 'Clear', key='aws_bucket_clear', icon='🧹',
					width='stretch' )
				
				can_save = st.session_state.get(
					'active_loader' ) == 'AwsBucketLoader' and isinstance(
					st.session_state.get( 'raw_text' ), str ) and st.session_state.get(
					'raw_text' ).strip( )
				
				if can_save:
					col_save.download_button( 'Save', data=st.session_state.get( 'raw_text' ),
						file_name='aws_bucket_loader_output.txt', mime='text/plain',
						key='aws_bucket_save', icon='💾', width='stretch' )
				else:
					col_save.button( 'Save', key='aws_bucket_save_disabled', disabled=True,
						icon='💾', width='stretch' )
				
				# --------------------------------------------------
				# Clear
				# --------------------------------------------------
				if clear_aws_bucket:
					clear_if_active( 'AwsBucketLoader' )
					st.session_state.raw_text = rebuild_raw_text_from_documents( )
					st.session_state[ '_loader_status' ] = 'AWS Bucket Loader state cleared.'
				
				# --------------------------------------------------
				# Load
				# --------------------------------------------------
				if (load_aws_bucket and isinstance( aws_bucket_name,
						str ) and aws_bucket_name.strip( )):
					verify_value: str = None
					
					if isinstance( aws_bucket_verify, str ) and aws_bucket_verify.strip( ):
						verify_text = aws_bucket_verify.strip( )
						if verify_text.lower( ) == 'true':
							verify_value = True
						elif verify_text.lower( ) == 'false':
							verify_value = False
						else:
							verify_value = verify_text
					
					loader = AwsBucketLoader( )
					documents = loader.load( bucket=aws_bucket_name.strip( ),
						prefix=aws_bucket_prefix.strip( ),
						region_name=aws_bucket_region.strip( ) or None,
						api_version=aws_bucket_api_version.strip( ) or None,
						use_ssl=bool( aws_bucket_use_ssl ), verify=verify_value,
						endpoint_url=aws_bucket_endpoint_url.strip( ) or None, ) or [ ]
					
					for document in documents:
						if not isinstance( getattr( document, 'metadata', None ), dict ):
							document.metadata = { }
						
						document.metadata[ 'loader' ] = 'AwsBucketLoader'
						document.metadata.setdefault( 'bucket', aws_bucket_name.strip( ) )
						document.metadata.setdefault( 'prefix', aws_bucket_prefix.strip( ) )
						document.metadata.setdefault( 'region_name',
							aws_bucket_region.strip( ) or None )
						
						document.metadata.setdefault( 'api_version',
							aws_bucket_api_version.strip( ) or None )
						
						document.metadata.setdefault( 'use_ssl', bool( aws_bucket_use_ssl ) )
						document.metadata.setdefault( 'verify', verify_value )
						document.metadata.setdefault( 'endpoint_url',
							aws_bucket_endpoint_url.strip( ) or None )
						
						if aws_bucket_prefix.strip( ):
							document.metadata.setdefault( 'source',
								f's3://{aws_bucket_name.strip( )}/{aws_bucket_prefix.strip( )}' )
						else:
							document.metadata.setdefault( 'source',
								f's3://{aws_bucket_name.strip( )}' )
					
					st.session_state.documents = documents
					st.session_state.raw_documents = list( documents )
					st.session_state.raw_text = '\n\n'.join( d.page_content for d in documents if
					                                         hasattr( d,
						                                         'page_content' ) and isinstance(
						                                         d.page_content,
						                                         str ) and d.page_content.strip( ) )
					st.session_state.processed_text = None
					st.session_state.lines = None
					st.session_state.chunked_documents = None
					st.session_state.df_chunks = None
					st.session_state.active_loader = 'AwsBucketLoader'
					st.session_state[
						'_loader_status' ] = f'Loaded {len( documents )} AWS bucket document(s).'
				
				render_document_processing_controls( 'AwsBucketLoader', 'loader_aws_bucket_loader' )
			
			# ------- Expander SharePoint Loader
			with st.expander( label='SharePoint Loader', icon='🟩', expanded=False ):
				spfx_library_id = st.text_input( 'Library ID', value='', key='spfx_library_id',
					placeholder='SharePoint document library identifier', )
				
				spfx_folder_id = st.text_input( 'Folder ID', value='', key='spfx_folder_id',
					placeholder='Optional folder identifier within the library',
					help='Leave blank to load the library directly.', )
				
				# --------------------------------------------------
				# Buttons: Load / Clear / Save
				# --------------------------------------------------
				col_load, col_clear, col_save = st.columns( 3 )
				load_spfx = col_load.button( 'Load', key='spfx_load', icon='📤', width='stretch' )
				clear_spfx = col_clear.button( 'Clear', key='spfx_clear', icon='🧹',
					width='stretch' )
				
				can_save = (st.session_state.get( 'active_loader' ) == 'SpfxLoader' and isinstance(
					st.session_state.get( 'raw_text' ), str ) and st.session_state.get(
					'raw_text' ).strip( ))
				
				if can_save:
					col_save.download_button( 'Save', data=st.session_state.get( 'raw_text' ),
						file_name='sharepoint_loader_output.txt', mime='text/plain',
						key='spfx_save', icon='💾', width='stretch' )
				else:
					col_save.button( 'Save', key='spfx_save_disabled', disabled=True, icon='💾',
						width='stretch' )
				
				# --------------------------------------------------
				# Clear
				# --------------------------------------------------
				if clear_spfx:
					clear_if_active( 'SpfxLoader' )
					st.session_state.raw_text = rebuild_raw_text_from_documents( )
					st.session_state[ '_loader_status' ] = 'SharePoint Loader state cleared.'
				
				# --------------------------------------------------
				# Load
				# --------------------------------------------------
				if (load_spfx and isinstance( spfx_library_id, str ) and spfx_library_id.strip( )):
					loader = SpfxLoader( )
					if isinstance( spfx_folder_id, str ) and spfx_folder_id.strip( ):
						documents = loader.load_folder( library_id=spfx_library_id.strip( ),
							folder_id=spfx_folder_id.strip( ), ) or [ ]
					else:
						documents = loader.load( library_id=spfx_library_id.strip( ), ) or [ ]
					
					for document in documents:
						if not isinstance( getattr( document, 'metadata', None ), dict ):
							document.metadata = { }
						
						document.metadata[ 'loader' ] = 'SpfxLoader'
						document.metadata.setdefault( 'library_id', spfx_library_id.strip( ) )
						document.metadata.setdefault( 'folder_id',
							spfx_folder_id.strip( ) or None, )
						
						if spfx_folder_id.strip( ):
							document.metadata.setdefault( 'source',
								f'{spfx_library_id.strip( )}:{spfx_folder_id.strip( )}' )
						else:
							document.metadata.setdefault( 'source', spfx_library_id.strip( ), )
					
					st.session_state.documents = documents
					st.session_state.raw_documents = list( documents )
					st.session_state.raw_text = '\n\n'.join( d.page_content for d in documents if
					                                         hasattr( d, 'page_content' ) \
					                                         and isinstance( d.page_content,  str ) \
					                                         and d.page_content.strip( ) )
					st.session_state.processed_text = None
					st.session_state.lines = None
					st.session_state.chunked_documents = None
					st.session_state.df_chunks = None
					st.session_state.active_loader = 'SpfxLoader'
					st.session_state[ '_loader_status' ] = \
						f'Loaded {len( documents )} SharePoint document(s).'
				
				render_document_processing_controls( 'SpfxLoader', 'loader_sharepoint_loader' )
	
	# ----------- RIGHT COLUMN — DOCUMENT RENDERING
	with document_results_column:
		render_loading_tabs( )

# ==============================================================================
# GEOSCIENCE DATA MODE
# ==============================================================================
elif mode == 'Geoscience Data':
	with st.expander( 'Geoscience Data', expanded=True ):
		
		# ----------- Weather Expander
		with st.expander( 'Weather', expanded=True ):
			left, center, right = st.columns( [ 0.025, 0.95, 0.025 ] )
			with center:
				st.subheader( 'Weather Data' )
				st.divider( )
				global_location = get_global_location_default( )
				global_latitude = get_global_latitude_default( )
				global_longitude = get_global_longitude_default( )
				location_c1, location_c2, location_c3 = st.columns( 3, border=True )
				location_c1.metric( 'Location', global_location )
				location_c2.metric( 'Latitude', f'{float( global_latitude ):.4f}' )
				location_c3.metric( 'Longitude', f'{float( global_longitude ):.4f}' )
				
				blue_divider( )
				weather_c1, weather_c2 = st.columns( [ 0.40, 0.60 ], border=True, gap='xsmall' )
				with weather_c1:
					
					# --------- GOOGLE WEATHER
					with st.expander( '🌦️ Google Weather', expanded=True ):
						st.badge( label='About API', color='blue', help=cfg.GOOGLE_WEATHER )
						google_address = st.text_input( 'Address or Location', value=global_location,
							key='weather_google_address' )
						
						google_product = st.selectbox( 'Product',
							options=[ 'Current Conditions', 'Hourly Forecast', 'Daily Forecast', 'Alerts' ],
							key='weather_google_product' )
						
						google_units = st.selectbox( 'Units System', options=[ 'METRIC', 'IMPERIAL' ],
							key='weather_google_units' )
						
						google_language = st.text_input( 'Language Code', value='en',
							key='weather_google_language' )
						
						if google_product == 'Hourly Forecast':
							google_hours = st.number_input( 'Hours', min_value=1, max_value=240,
								value=24, step=1, key='weather_google_hours' )
						else:
							google_hours = 24
						
						if google_product == 'Daily Forecast':
							google_days = st.number_input( 'Days', min_value=1, max_value=10, value=5,
								step=1, key='weather_google_days' )
						else:
							google_days = 5
						
						google_timeout = st.number_input( 'Timeout', min_value=1, max_value=60,
							value=10, step=1, key='weather_google_timeout' )
						
						google_btn_c1, google_btn_c2 = st.columns( 2 )
						with google_btn_c1:
							if st.button( label='Run', icon='🏃', key='weather_google_run',
									use_container_width=True ):
								if not google_address:
									st.warning( 'Enter an address or location.' )
								else:
									try:
										weather = GoogleWeather( )
										
										if google_product == 'Current Conditions':
											result = weather.fetch_current( address=google_address,
												units_system=google_units, language_code=google_language,
												time=int( google_timeout ) )
										
										elif google_product == 'Hourly Forecast':
											result = weather.fetch_hourly_forecast( address=google_address,
												hours=int( google_hours ), units_system=google_units,
												language_code=google_language, time=int( google_timeout ) )
										
										elif google_product == 'Daily Forecast':
											result = weather.fetch_daily_forecast( address=google_address,
												days=int( google_days ), units_system=google_units,
												language_code=google_language, time=int( google_timeout ) )
										
										else:
											result = weather.fetch_alerts( address=google_address,
												language_code=google_language, time=int( google_timeout ) )
										
										weather_latitude = getattr( weather, 'latitude', None )
										weather_longitude = getattr( weather, 'longitude', None )
										
										st.session_state[ 'weather_last_source' ] = 'Google Weather'
										st.session_state[ 'weather_last_result' ] = result or { }
										st.session_state[ 'weather_last_latitude' ] = weather_latitude
										st.session_state[ 'weather_last_longitude' ] = weather_longitude
										
										set_global_coordinates_from_result(
											weather_latitude,
											weather_longitude,
											location=google_address,
											description='Google Weather result' )
										
										st.success( 'Google Weather request completed.' )
									
									except Exception as ex:
										st.error( f'Google Weather request failed: {ex}' )
						
						with google_btn_c2:
							if st.button( label='Clear', icon='🧹', key='weather_google_clear',
									use_container_width=True ):
								if st.session_state.get( 'weather_last_source' ) == 'Google Weather':
									initialize_mode_document_state( 'weather' )
									for key, value in {
										'weather_documents': [ ], 'weather_chunks': [ ],
										'weather_embeddings': [ ], 'weather_embedder': None,
										'weather_vector_store': None,
										'weather_document_signature': '',
										'weather_chunk_size_used': 0,
										'weather_chunk_overlap_used': 0,
										'weather_embedding_provider_used': '',
										'weather_embedding_model_used': '',
										'weather_embedding_model_path_used': '',
									}.items( ):
										st.session_state[ key ] = value
									st.session_state[ 'weather_last_source' ] = ''
									st.session_state[ 'weather_last_result' ] = { }
									st.session_state[ 'weather_last_latitude' ] = None
									st.session_state[ 'weather_last_longitude' ] = None
					
						st.divider( )
						render_source_processing_controls( 'weather', 'weather_last_result',
							'weather_last_source', 'Google Weather', 'weather_google_weather' )
				
					# --------- OPENWEATHER / OPEN-METEO\
					with st.expander( '🌤️ OpenWeather / Open-Meteo', expanded=False ):
						st.badge( label='About API', color='blue', help=cfg.OPEN_WEATHER )
						open_location = st.text_input( 'Location', value=global_location,
							key='weather_open_location' )
						
						open_mode = st.selectbox( 'Mode', options=[ 'current', 'hourly', 'daily' ],
							key='weather_open_mode' )
						
						open_zone = st.text_input( 'Timezone',
							value='auto',
							key='weather_open_zone' )
						
						open_forecast_days = st.number_input( 'Forecast Days', min_value=1,
							max_value=16, value=7, step=1,
							key='weather_open_forecast_days' )
						
						open_past_days = st.number_input( 'Past Days', min_value=0, max_value=92,
							value=0, step=1, key='weather_open_past_days' )
						
						open_count = st.number_input( 'Geocoding Result Count', min_value=1, max_value=100,
							value=10, step=1, key='weather_open_count' )
						
						open_btn_c1, open_btn_c2 = st.columns( 2 )
						with open_btn_c1:
							if st.button( label='Run', icon='🏃', key='weather_open_run',
									use_container_width=True ):
								if not open_location:
									st.warning( 'Enter a location.' )
								else:
									try:
										weather = OpenWeather( )
										
										result = weather.fetch( location=open_location, mode=open_mode,
											zone=open_zone, forecast_days=int( open_forecast_days ),
											past_days=int( open_past_days ),
											count=int( open_count ) )
										
										weather_latitude = getattr( weather, 'latitude', None )
										weather_longitude = getattr( weather, 'longitude', None )
										
										st.session_state[
											'weather_last_source' ] = 'OpenWeather / Open-Meteo'
										st.session_state[ 'weather_last_result' ] = result or { }
										st.session_state[ 'weather_last_latitude' ] = weather_latitude
										st.session_state[ 'weather_last_longitude' ] = weather_longitude
										
										set_global_coordinates_from_result( weather_latitude,
											weather_longitude, location=open_location,
											description='OpenWeather / Open-Meteo result' )
										
										st.success( 'OpenWeather request completed.' )
									
									except Exception as ex:
										st.error( f'OpenWeather request failed: {ex}' )
						
						with open_btn_c2:
							if st.button( label='Clear', icon='🧹', key='weather_open_clear',
									use_container_width=True ):
								st.session_state[ 'weather_last_source' ] = ''
								st.session_state[ 'weather_last_result' ] = { }
								st.session_state[ 'weather_last_latitude' ] = None
								st.session_state[ 'weather_last_longitude' ] = None
					
						st.divider( )
						render_source_processing_controls( 'weather', 'weather_last_result',
							'weather_last_source', 'OpenWeather / Open-Meteo',
							'weather_openweather_open_meteo' )
						
					# --------- HISTORICAL WEATHER
					with st.expander( '🕰️ Historical Weather', expanded=False ):
						st.badge( label='About API', color='blue', help=cfg.HISTORICAL_WEATHER )
						historical_location = st.text_input( 'Location', value=global_location,
							key='weather_historical_location' )
						
						historical_date = st.date_input( 'Historical Date',
							value=dt.date.today( ) - dt.timedelta( days=7 ),
							key='weather_historical_date' )
						
						historical_zone = st.text_input( 'Timezone', value='auto',
							key='weather_historical_zone' )
						
						historical_count = st.number_input( 'Geocoding Result Count', min_value=1,
							max_value=100, value=10, step=1, key='weather_historical_count' )
						
						historical_btn_c1, historical_btn_c2 = st.columns( 2 )
						with historical_btn_c1:
							if st.button( label='Run', icon='🏃', key='weather_historical_run',
									use_container_width=True ):
								if not historical_location:
									st.warning( 'Enter a location.' )
								else:
									try:
										weather = HistoricalWeather( )
										
										result = weather.fetch( location=historical_location,
											date=historical_date, zone=historical_zone,
											count=int( historical_count ) )
										
										weather_latitude = getattr( weather, 'latitude', None )
										weather_longitude = getattr( weather, 'longitude', None )
										
										st.session_state[ 'weather_last_source' ] = 'Historical Weather'
										st.session_state[ 'weather_last_result' ] = result or { }
										st.session_state[ 'weather_last_latitude' ] = weather_latitude
										st.session_state[ 'weather_last_longitude' ] = weather_longitude
										
										set_global_coordinates_from_result( weather_latitude,
											weather_longitude, location=historical_location,
											description='Historical Weather result' )
										
										st.success( 'Historical Weather request completed.' )
									
									except Exception as ex:
										st.error( f'Historical Weather request failed: {ex}' )
						
						with historical_btn_c2:
							if st.button( label='Clear', icon='🧹', key='weather_historical_clear',
									use_container_width=True ):
								st.session_state[ 'weather_last_source' ] = ''
								st.session_state[ 'weather_last_result' ] = { }
								st.session_state[ 'weather_last_latitude' ] = None
								st.session_state[ 'weather_last_longitude' ] = None
					
						st.divider( )
						render_source_processing_controls( 'weather', 'weather_last_result',
							'weather_last_source', 'Historical Weather', 'weather_historical_weather' )
						
					# --------- CLIMATE DATA
					with st.expander( '🌡️ Climate Data', expanded=False ):
						st.badge( label='About API', color='blue', help=cfg.NOAA_CLIMATE_DATA )
						climate_mode = st.selectbox( 'Mode',
							options=[ 'datasets', 'data' ],
							key='weather_climate_mode' )
						
						climate_timeout = st.number_input( 'Timeout', min_value=1, max_value=60, value=20,
							step=1, key='weather_climate_timeout' )
						
						if climate_mode == 'datasets':
							climate_keyword = st.text_input( 'Keyword', value='daily',
								key='weather_climate_keyword' )
							
							climate_start_date_value = st.date_input( 'Start Date',
								value=dt.date.today( ) - dt.timedelta( days=365 ),
								key='weather_climate_dataset_start_date' )
							
							climate_end_date_value = st.date_input( 'End Date', value=dt.date.today( ),
								key='weather_climate_dataset_end_date' )
							
							climate_limit = st.number_input( 'Limit', min_value=1, max_value=1000,
								value=25,
								step=1, key='weather_climate_dataset_limit' )
							
							climate_offset = st.number_input( 'Offset', min_value=0, max_value=100000,
								value=0, step=1, key='weather_climate_dataset_offset' )
							
							climate_dataset = ''
							climate_stations = ''
							climate_data_types = ''
						
						else:
							climate_dataset = st.text_input( 'Dataset', value='daily-summaries',
								help='Example: daily-summaries', key='weather_climate_dataset' )
							
							climate_data_c1, climate_data_c2 = st.columns( 2 )
							with climate_data_c1:
								climate_start_date_value = st.date_input( 'Start Date',
									value=dt.date.today( ) - dt.timedelta( days=30 ),
									key='weather_climate_data_start_date' )
							
							with climate_data_c2:
								climate_end_date_value = st.date_input( 'End Date', value=dt.date.today( ),
									key='weather_climate_data_end_date' )
							
							climate_stations = st.text_input( 'Stations', value='',
								help='Optional comma-separated station identifiers.',
								key='weather_climate_stations' )
							
							climate_data_types = st.text_input( 'Data Types', value='',
								help='Optional comma-separated data type identifiers.',
								key='weather_climate_data_types' )
							
							climate_limit = st.number_input( 'Limit', min_value=1, max_value=1000,
								value=25,
								step=1, key='weather_climate_data_limit' )
							
							climate_offset = 0
							climate_keyword = ''
						
						climate_btn_c1, climate_btn_c2 = st.columns( 2 )
						with climate_btn_c1:
							if st.button( label='Run', icon='🏃', key='weather_climate_run',
									use_container_width=True ):
								try:
									service = ClimateData( )
									
									if climate_mode == 'datasets':
										result = service.fetch_datasets( keyword=climate_keyword,
											start_date=climate_start_date_value.isoformat( ),
											end_date=climate_end_date_value.isoformat( ),
											limit=int( climate_limit ), offset=int( climate_offset ),
											time=int( climate_timeout ) )
									
									else:
										if not climate_dataset:
											st.warning( 'Enter a dataset identifier.' )
											result = None
										else:
											result = service.fetch_data( dataset=climate_dataset,
												start_date=climate_start_date_value.isoformat( ),
												end_date=climate_end_date_value.isoformat( ),
												stations=climate_stations, data_types=climate_data_types,
												limit=int( climate_limit ), time=int( climate_timeout ) )
									
									if result is not None:
										st.session_state[ 'weather_last_source' ] = 'Climate Data'
										st.session_state[ 'weather_last_result' ] = result or { }
										st.session_state[ 'weather_last_latitude' ] = None
										st.session_state[ 'weather_last_longitude' ] = None
										st.success( 'Climate Data request completed.' )
								
								except Exception as ex:
									st.error( f'Climate Data request failed: {ex}' )
						
						with climate_btn_c2:
							if st.button( label='Clear', icon='🧹', key='weather_climate_clear',
									use_container_width=True ):
								
								st.session_state[ 'weather_last_source' ] = ''
								st.session_state[ 'weather_last_result' ] = { }
								st.session_state[ 'weather_last_latitude' ] = None
								st.session_state[ 'weather_last_longitude' ] = None
					
						st.divider( )
						render_source_processing_controls( 'weather', 'weather_last_result',
							'weather_last_source', 'Climate Data', 'weather_climate_data' )
					
					# --------- TIDES AND CURRENTS
					with st.expander( '🌊 Tides & Currents', expanded=False ):
						st.badge( label='About API', color='blue', help=cfg.NOAA_TIDES_CURRENTS )
						tides_mode = st.selectbox( 'Mode',
							options=[ 'station', 'water-level', 'tide-predictions' ],
							key='weather_tides_mode' )
						
						tides_station_id = st.text_input( 'Station ID', value='8594900',
							help='Example NOAA station: 8594900', key='weather_tides_station_id' )
						
						tides_timeout = st.number_input( 'Timeout', min_value=1, max_value=60, value=20,
							step=1, key='weather_tides_timeout' )
						
						if tides_mode == 'station':
							tides_begin_date = ''
							tides_end_date = ''
							tides_datum = 'MLLW'
							tides_units = 'metric'
							tides_time_zone = 'gmt'
							tides_interval = 'hilo'
						
						else:
							tides_date_c1, tides_date_c2 = st.columns( 2 )
							with tides_date_c1:
								tides_begin = st.date_input( 'Begin Date',
									value=dt.date.today( ) - dt.timedelta( days=1 ),
									key='weather_tides_begin_date' )
							
							with tides_date_c2:
								tides_end = st.date_input( 'End Date', value=dt.date.today( ),
									key='weather_tides_end_date' )
							
							tides_begin_date = tides_begin.strftime( '%Y%m%d' )
							tides_end_date = tides_end.strftime( '%Y%m%d' )
							
							tides_datum = st.selectbox(
								'Datum',
								options=[ 'MLLW', 'MLW', 'MSL', 'MHW', 'MHHW', 'NAVD' ],
								key='weather_tides_datum' )
							
							tides_units = st.selectbox( 'Units', options=[ 'metric', 'english' ],
								key='weather_tides_units' )
							
							tides_time_zone = st.selectbox( 'Time Zone',
								options=[ 'gmt', 'lst', 'lst_ldt' ], key='weather_tides_time_zone' )
							
							if tides_mode == 'tide-predictions':
								tides_interval = st.selectbox( 'Interval', options=[ 'hilo', 'h' ],
									key='weather_tides_interval' )
							else:
								tides_interval = 'hilo'
						
						tides_btn_c1, tides_btn_c2 = st.columns( 2 )
						with tides_btn_c1:
							if st.button( label='Run', icon='🏃', key='weather_tides_run',
									use_container_width=True ):
								try:
									service = TidesAndCurrents( )
									
									result = service.fetch( mode=tides_mode, station_id=tides_station_id,
										begin_date=tides_begin_date, end_date=tides_end_date,
										datum=tides_datum, units=tides_units, time_zone=tides_time_zone,
										interval=tides_interval, time=int( tides_timeout ) )
									
									st.session_state[ 'weather_last_source' ] = 'Tides & Currents'
									st.session_state[ 'weather_last_result' ] = result or { }
									st.session_state[ 'weather_last_latitude' ] = None
									st.session_state[ 'weather_last_longitude' ] = None
									st.success( 'Tides & Currents request completed.' )
								
								except Exception as ex:
									st.error( f'Tides & Currents request failed: {ex}' )
						
						with tides_btn_c2:
							if st.button( label='Clear', icon='🧹', key='weather_tides_clear',
									use_container_width=True ):
								st.session_state[ 'weather_last_source' ] = ''
								st.session_state[ 'weather_last_result' ] = { }
								st.session_state[ 'weather_last_latitude' ] = None
								st.session_state[ 'weather_last_longitude' ] = None
				
						st.divider( )
						render_source_processing_controls( 'weather', 'weather_last_result',
							'weather_last_source', 'Tides & Currents', 'weather_tides_currents' )
						
				with weather_c2:
					render_mode_document_tabs( 'weather', '📄 Loaded' )
		
		# ----------- Environmental Expander
		with st.expander( 'Environmental', expanded=False ):
			left, center, right = st.columns( [ 0.025, 0.95, 0.025 ] )
			with center:
				st.subheader( 'Environmental Data' )
				st.divider( )
				global_location = get_global_location_default( )
				global_zipcode = get_global_zipcode_default( )
				global_latitude = get_global_latitude_default( )
				global_longitude = get_global_longitude_default( )
				global_box = create_bounding_box_from_center( global_latitude, global_longitude )
				location_c1, location_c2, location_c3, location_c4 = st.columns( 4, border=True )
				location_c1.metric( 'Location', global_location )
				location_c2.metric( 'ZIP Code', global_zipcode )
				location_c3.metric( 'Latitude', f'{float( global_latitude ):.4f}' )
				location_c4.metric( 'Longitude', f'{float( global_longitude ):.4f}' )
				
				blue_divider( )
				enviro_c1, enviro_c2 = st.columns( [ 0.40, 0.60 ], border=True, gap='xsmall' )
				with enviro_c1:
					
					# --------- AIRNOW AIR QUALITY
					with st.expander( '🌫️ AirNow Air Quality', expanded=True ):
						st.caption( 'API', help=cfg.AIR_NOW )
						airnow_mode = st.selectbox( 'Mode',
							options=[ 'Current by ZIP', 'Current by Coordinates', 'Forecast by ZIP',
									'Forecast by Coordinates' ], key='env_airnow_mode' )
						
						airnow_distance = st.number_input( 'Distance', min_value=0, max_value=250,
							value=25, step=1, key='input_env_airnow_distance' )
						
						airnow_timeout = st.number_input( 'Timeout', min_value=1, max_value=60,
							value=20, step=1, key='input_env_airnow_timeout' )
						
						if 'ZIP' in airnow_mode:
							airnow_zip = st.text_input( 'ZIP Code', value=global_zipcode,
								key='input_env_airnow_zip' )
							
							airnow_latitude = None
							airnow_longitude = None
						
						else:
							airnow_zip = ''
							
							airnow_coord_c1, airnow_coord_c2 = st.columns( 2 )
							
							with airnow_coord_c1:
								airnow_latitude = st.number_input(
									'Latitude',
									value=float( global_latitude ),
									format='%.6f',
									key='input_env_airnow_latitude' )
							
							with airnow_coord_c2:
								airnow_longitude = st.number_input(
									'Longitude',
									value=float( global_longitude ),
									format='%.6f',
									key='input_env_airnow_longitude' )
						
						if 'Forecast' in airnow_mode:
							airnow_date = st.date_input(
								'Forecast Date',
								value=dt.date.today( ),
								key='input_env_airnow_date' )
						else:
							airnow_date = None
						
						airnow_btn_c1, airnow_btn_c2 = st.columns( 2 )
						
						with airnow_btn_c1:
							if st.button( label='Run', icon='🏃', key='input_env_airnow_run',
									use_container_width=True ):
								try:
									service = AirNow( )
									result = None
									
									if airnow_mode == 'Current by ZIP':
										if not airnow_zip:
											st.warning( 'Enter a ZIP code.' )
										else:
											result = service.fetch_current_zip(
												zip_code=airnow_zip,
												distance=int( airnow_distance ),
												time=int( airnow_timeout ) )
									
									elif airnow_mode == 'Current by Coordinates':
										if not has_valid_coordinates( airnow_latitude, airnow_longitude ):
											st.warning( 'Provide valid coordinates.' )
										else:
											result = service.fetch_current_latlon(
												latitude=float( airnow_latitude ),
												longitude=float( airnow_longitude ),
												distance=int( airnow_distance ),
												time=int( airnow_timeout ) )
									
									elif airnow_mode == 'Forecast by ZIP':
										if not airnow_zip:
											st.warning( 'Enter a ZIP code.' )
										else:
											result = service.fetch_forecast_zip(
												zip_code=airnow_zip,
												date=airnow_date.isoformat( ),
												distance=int( airnow_distance ),
												time=int( airnow_timeout ) )
									
									else:
										if not has_valid_coordinates( airnow_latitude, airnow_longitude ):
											st.warning( 'Provide valid coordinates.' )
										else:
											result = service.fetch_forecast_latlon(
												latitude=float( airnow_latitude ),
												longitude=float( airnow_longitude ),
												date=airnow_date.isoformat( ),
												distance=int( airnow_distance ),
												time=int( airnow_timeout ) )
									
									if result is not None:
										st.session_state[ 'env_last_source' ] = 'AirNow'
										st.session_state[ 'env_last_result' ] = result or { }
										st.session_state[ 'env_last_latitude' ] = airnow_latitude
										st.session_state[ 'env_last_longitude' ] = airnow_longitude
										
										set_global_coordinates_from_result(
											airnow_latitude,
											airnow_longitude,
											location=global_location,
											description='AirNow coordinate result' )
										
										if airnow_zip:
											st.session_state[ 'zipcode' ] = str( airnow_zip ).strip( )
										
										st.success( 'AirNow request completed.' )
								
								except Exception as ex:
									st.error( f'AirNow request failed: {ex}' )
						
						with airnow_btn_c2:
							if st.button( label='Clear', icon='🧹', key='env_airnow_clear',
									use_container_width=True ):
								st.session_state[ 'env_last_source' ] = ''
								st.session_state[ 'env_last_result' ] = { }
								st.session_state[ 'env_last_latitude' ] = None
								st.session_state[ 'env_last_longitude' ] = None
					
						st.divider( )
						render_source_processing_controls( 'env', 'env_last_result', 'env_last_source', 'AirNow', 'env_airnow' )
					
					# --------- UV INDEX
					with st.expander( '☀️ UV Index', expanded=False ):
						st.badge( label='About API', color='blue', help=cfg.AIR_NOW )
						uv_mode = st.selectbox(
							'Mode',
							options=[
									'Daily by ZIP',
									'Daily by City / State',
									'Hourly by ZIP',
									'Hourly by City / State'
							],
							key='env_uv_mode' )
						
						uv_timeout = st.number_input(
							'Timeout',
							min_value=1,
							max_value=60,
							value=20,
							step=1,
							key='env_uv_timeout' )
						
						if 'ZIP' in uv_mode:
							uv_zip = st.text_input(
								'ZIP Code',
								value='20001',
								key='env_uv_zip' )
							
							uv_city = ''
							uv_state = ''
						
						else:
							uv_zip = ''
							uv_city = st.text_input(
								'City',
								value='Washington',
								key='env_uv_city' )
							
							uv_state = st.text_input(
								'State',
								value='DC',
								key='env_uv_state' )
						
						uv_btn_c1, uv_btn_c2 = st.columns( 2 )
						
						with uv_btn_c1:
							if st.button( label='Run', icon='🏃', key='env_uv_run',
									use_container_width=True ):
								try:
									service = UvIndex( )
									
									if uv_mode == 'Daily by ZIP':
										if not uv_zip:
											st.warning( 'Enter a ZIP code.' )
											result = None
										else:
											result = service.fetch_daily_zip(
												zip_code=uv_zip,
												time=int( uv_timeout ) )
									
									elif uv_mode == 'Daily by City / State':
										if not uv_city or not uv_state:
											st.warning( 'Enter both city and state.' )
											result = None
										else:
											result = service.fetch_daily_city_state(
												city=uv_city,
												state=uv_state,
												time=int( uv_timeout ) )
									
									elif uv_mode == 'Hourly by ZIP':
										if not uv_zip:
											st.warning( 'Enter a ZIP code.' )
											result = None
										else:
											result = service.fetch_hourly_zip(
												zip_code=uv_zip,
												time=int( uv_timeout ) )
									
									else:
										if not uv_city or not uv_state:
											st.warning( 'Enter both city and state.' )
											result = None
										else:
											result = service.fetch_hourly_city_state(
												city=uv_city,
												state=uv_state,
												time=int( uv_timeout ) )
									
									if result is not None:
										st.session_state[ 'env_last_source' ] = 'UV Index'
										st.session_state[ 'env_last_result' ] = result or { }
										st.session_state[ 'env_last_latitude' ] = None
										st.session_state[ 'env_last_longitude' ] = None
										st.success( 'UV Index request completed.' )
								
								except Exception as ex:
									st.error( f'UV Index request failed: {ex}' )
						
						with uv_btn_c2:
							if st.button( label='Clear', icon='🧹', key='env_uv_clear',
									use_container_width=True ):
								st.session_state[ 'env_last_source' ] = ''
								st.session_state[ 'env_last_result' ] = { }
								st.session_state[ 'env_last_latitude' ] = None
								st.session_state[ 'env_last_longitude' ] = None
					
						st.divider( )
						render_source_processing_controls( 'env', 'env_last_result', 'env_last_source', 'UV Index', 'env_uv_index' )
					
					# --------- OPENAQ
					with st.expander( '🧪 OpenAQ', expanded=False ):
						st.badge( label='About API', color='blue', help=cfg.OPEN_AQ )
						openaq_mode = st.selectbox( 'Mode',
							options=[ 'Locations', 'Latest Measurements' ], key='sb_openaq_mode' )
						
						openaq_timeout = st.number_input( 'Timeout', min_value=1, max_value=60,
							value=20, step=1, key='ib_env_openaq_timeout' )
						
						if openaq_mode == 'Locations':
							openaq_country_id = st.number_input( 'Country ID', min_value=0,
								value=0, step=1, key='in_env_openaq_country_id' )
							
							openaq_coordinates = st.text_input( 'Coordinates',
								value=f'{global_latitude:.6f},{global_longitude:.6f}',
								help='OpenAQ expects a latitude,longitude string.',
								key='env_openaq_coordinates' )
							
							openaq_radius = st.number_input( 'Radius', min_value=1,
								max_value=100000, value=25000, step=1000, key='env_openaq_radius' )
							
							openaq_providers_id = st.text_input( 'Providers ID',
								value='', key='env_openaq_providers_id' )
							
							openaq_parameters_id = st.text_input( 'Parameters ID', value='',
								key='env_openaq_parameters_id' )
							
							openaq_limit = st.number_input( 'Limit', min_value=1, max_value=1000,
								value=25, step=1, key='env_openaq_limit' )
							
							openaq_page = st.number_input( 'Page', min_value=1, max_value=10000,
								value=1, step=1, key='env_openaq_page' )
							
							openaq_location_id = None
						
						else:
							openaq_country_id = 0
							openaq_coordinates = ''
							openaq_radius = 25000
							openaq_providers_id = ''
							openaq_parameters_id = ''
							openaq_limit = 25
							openaq_page = 1
							
							openaq_location_id = st.number_input( 'Location ID', min_value=1,
								value=1, step=1, key='env_openaq_location_id' )
						
						openaq_btn_c1, openaq_btn_c2 = st.columns( 2 )
						with openaq_btn_c1:
							if st.button( label='Run', icon='🏃', key='env_openaq_run',
									use_container_width=True ):
								try:
									service = OpenAQ( )
									if openaq_mode == 'Locations':
										country_id_value = None
										if int( openaq_country_id ) > 0:
											country_id_value = int( openaq_country_id )
										
										result = service.fetch_locations(
											country_id=country_id_value,
											coordinates=openaq_coordinates,
											radius=int( openaq_radius ),
											providers_id=openaq_providers_id,
											parameters_id=openaq_parameters_id,
											limit=int( openaq_limit ),
											page=int( openaq_page ),
											time=int( openaq_timeout ) )
										
										lat_value = None
										lng_value = None
										
										try:
											parts = [ p.strip( ) for p in openaq_coordinates.split( ',' ) ]
											if len( parts ) == 2:
												lat_value = float( parts[ 0 ] )
												lng_value = float( parts[ 1 ] )
										except Exception:
											lat_value = None
											lng_value = None
									
									else:
										result = service.fetch_latest(
											location_id=int( openaq_location_id ),
											time=int( openaq_timeout ) )
										
										lat_value = None
										lng_value = None
									
									st.session_state[ 'env_last_source' ] = 'OpenAQ'
									st.session_state[ 'env_last_result' ] = result or { }
									st.session_state[ 'env_last_latitude' ] = lat_value
									st.session_state[ 'env_last_longitude' ] = lng_value
									
									set_global_coordinates_from_result( lat_value, lng_value,
										location=global_location, description='OpenAQ result' )
									
									st.success( 'OpenAQ request completed.' )
								
								except Exception as ex:
									st.error( f'OpenAQ request failed: {ex}' )
						
						with openaq_btn_c2:
							if st.button( label='Clear', icon='🧹', key='env_openaq_clear',
									use_container_width=True ):
								st.session_state[ 'env_last_source' ] = ''
								st.session_state[ 'env_last_result' ] = { }
								st.session_state[ 'env_last_latitude' ] = None
								st.session_state[ 'env_last_longitude' ] = None
					
						st.divider( )
						render_source_processing_controls( 'env', 'env_last_result',
							'env_last_source', 'OpenAQ', 'env_openaq' )
					
					# --------- PURPLEAIR SENSORS
					with st.expander( '🟣 PurpleAir Sensors', expanded=False ):
						st.badge( label='About API', color='blue', help=cfg.PURPLE_AIR )
						purple_mode = st.selectbox( 'Mode',
							options=[ 'Sensors by Bounding Box', 'Single Sensor' ],
							key='env_purple_mode' )
						
						purple_timeout = st.number_input( 'Timeout', min_value=1,
							max_value=60, value=20, step=1,
							key='env_purple_timeout' )
						
						if purple_mode == 'Sensors by Bounding Box':
							st.caption( 'Centered on the global latitude and longitude.' )
							purple_box_c1, purple_box_c2 = st.columns( 2 )
							with purple_box_c1:
								purple_nwlng = st.number_input( 'NW Longitude',
									value=float( global_box[ 'nw_lng' ] ),
									format='%.6f', key='env_purple_nwlng' )
								
								purple_nwlat = st.number_input( 'NW Latitude',
									value=float( global_box[ 'nw_lat' ] ),
									format='%.6f', key='env_purple_nwlat' )
							
							with purple_box_c2:
								purple_selng = st.number_input( 'SE Longitude',
									value=float( global_box[ 'se_lng' ] ),
									format='%.6f', key='env_purple_selng' )
								
								purple_selat = st.number_input( 'SE Latitude',
									value=float( global_box[ 'se_lat' ] ),
									format='%.6f', key='env_purple_selat' )
							
							purple_location_type = st.number_input( 'Location Type',
								min_value=0, max_value=1, value=0,
								step=1, help='Public outdoor sensors are commonly 0.',
								key='env_purple_location_type' )
							
							purple_max_age = st.number_input( 'Max Age', min_value=0,
								max_value=10080, value=0, step=10,
								help='Maximum sensor age in minutes. 0 keeps the default behavior.',
								key='env_purple_max_age' )
							
							purple_modified_since = st.number_input( 'Modified Since',
								min_value=0, max_value=4102444800,
								value=0, step=1,
								help='UNIX timestamp filter. 0 disables the filter.',
								key='env_purple_modified_since' )
							
							purple_sensor_index = 0
							purple_center_latitude = (float( purple_nwlat ) + float( purple_selat )) / 2.0
							purple_center_longitude = (float( purple_nwlng ) + float( purple_selng )) / 2.0
						
						else:
							purple_nwlng = 0.0
							purple_nwlat = 0.0
							purple_selng = 0.0
							purple_selat = 0.0
							purple_location_type = 0
							purple_max_age = 0
							purple_modified_since = 0
							purple_center_latitude = None
							purple_center_longitude = None
							
							purple_sensor_index = st.number_input( 'Sensor Index', min_value=1,
								value=1, step=1, key='env_purple_sensor_index' )
						
						purple_btn_c1, purple_btn_c2 = st.columns( 2 )
						with purple_btn_c1:
							if st.button( label='Run', icon='🏃', key='env_purple_run',
									use_container_width=True ):
								try:
									service = PurpleAir( )
									if purple_mode == 'Sensors by Bounding Box':
										result = service.fetch_sensors(
											nwlng=float( purple_nwlng ),
											nwlat=float( purple_nwlat ),
											selng=float( purple_selng ),
											selat=float( purple_selat ),
											location_type=int( purple_location_type ),
											max_age=int( purple_max_age ),
											modified_since=int( purple_modified_since ),
											time=int( purple_timeout ) )
									
									else:
										result = service.fetch_sensor(
											sensor_index=int( purple_sensor_index ),
											time=int( purple_timeout ) )
									
									st.session_state[ 'env_last_source' ] = 'PurpleAir'
									st.session_state[ 'env_last_result' ] = result or { }
									st.session_state[ 'env_last_latitude' ] = purple_center_latitude
									st.session_state[ 'env_last_longitude' ] = purple_center_longitude
									
									set_global_coordinates_from_result( purple_center_latitude,
										purple_center_longitude, location=global_location,
										description='PurpleAir bounding-box center' )
									
									st.success( 'PurpleAir request completed.' )
								
								except Exception as ex:
									st.error( f'PurpleAir request failed: {ex}' )
						
						with purple_btn_c2:
							if st.button( label='Clear', icon='🧹', key='env_purple_clear',
									use_container_width=True ):
								st.session_state[ 'env_last_source' ] = ''
								st.session_state[ 'env_last_result' ] = { }
								st.session_state[ 'env_last_latitude' ] = None
								st.session_state[ 'env_last_longitude' ] = None
					
						st.divider( )
						render_source_processing_controls( 'env', 'env_last_result',
							'env_last_source', 'PurpleAir', 'env_purpleair' )
					
					# --------- ENVIROFACTS
					with st.expander( '🏭 EPA EnviroFacts Facilities', expanded=False ):
						st.badge( label='About API', color='blue', help=cfg.EPA_ENVIROFACTS )
						envirofacts_table = st.selectbox( 'Table',
							options=[ 'TRI_FACILITY', 'TRI_RELEASE', 'EF_W_EMISSIONS_SOURCE_GHG' ],
							key='env_envirofacts_table' )
						
						envirofacts_state = st.text_input( 'State Code', value='',
							help='Optional two-letter state filter.', key='env_envirofacts_state' )
						
						envirofacts_facility = st.text_input( 'Facility Name', value='',
							help='Optional facility-name prefix filter.', key='env_envirofacts_facility' )
						
						envirofacts_limit = st.number_input( 'Limit', min_value=1, max_value=500, value=25,
							step=1, key='env_envirofacts_limit' )
						
						envirofacts_timeout = st.number_input( 'Timeout', min_value=1, max_value=60,
							value=20, step=1, key='env_envirofacts_timeout' )
						
						envirofacts_btn_c1, envirofacts_btn_c2 = st.columns( 2 )
						
						with envirofacts_btn_c1:
							if st.button( label='Run', icon='🏃', key='env_envirofacts_run',
									use_container_width=True ):
								try:
									service = EnviroFacts( )
									result = service.fetch(
										table_name=envirofacts_table,
										state_code=envirofacts_state,
										facility_name=envirofacts_facility,
										limit=int( envirofacts_limit ),
										time=int( envirofacts_timeout ) )
									
									st.session_state[ 'env_last_source' ] = 'EnviroFacts'
									st.session_state[ 'env_last_result' ] = result or { }
									st.session_state[ 'env_last_latitude' ] = None
									st.session_state[ 'env_last_longitude' ] = None
									st.success( 'EnviroFacts request completed.' )
								
								except Exception as ex:
									st.error( f'EnviroFacts request failed: {ex}' )
						
						with envirofacts_btn_c2:
							if st.button( label='Clear', icon='🧹', key='env_envirofacts_clear',
									use_container_width=True ):
								st.session_state[ 'env_last_source' ] = ''
								st.session_state[ 'env_last_result' ] = { }
								st.session_state[ 'env_last_latitude' ] = None
								st.session_state[ 'env_last_longitude' ] = None
					
						st.divider( )
						render_source_processing_controls( 'env', 'env_last_result', 'env_last_source', 'EnviroFacts', 'env_envirofacts' )
					
					# --------- FIRMS FIRE / THERMAL ANOMALIES
					with st.expander( '🔥 NASA FIRMS', expanded=False ):
						st.badge( label='About API', color='blue', help=cfg.NASA_FIRMS )
						firms_source = st.selectbox( 'Source',
							options=[ 'MODIS_NRT', 'MODIS_SP', 'VIIRS_SNPP_NRT', 'VIIRS_SNPP_SP',
									'VIIRS_NOAA20_NRT', 'VIIRS_NOAA20_SP', 'VIIRS_NOAA21_NRT',
									'LANDSAT_NRT' ], key='env_firms_source' )
						
						firms_area_mode = st.selectbox( 'Area Mode', options=[ 'World', 'Bounding Box' ],
							key='env_firms_area_mode' )
						
						firms_day_range = st.number_input( 'Day Range', min_value=1, max_value=5, value=1,
							step=1, key='env_firms_day_range' )
						
						firms_use_date = st.checkbox( 'Use Start Date', value=False,
							key='env_firms_use_date' )
						
						if firms_use_date:
							firms_date_value = st.date_input( 'Date', value=dt.date.today( ),
								key='env_firms_date' )
							firms_date = firms_date_value.isoformat( )
						else:
							firms_date = ''
						
						firms_timeout = st.number_input( 'Timeout', min_value=1, max_value=60, value=20,
							step=1, key='env_firms_timeout' )
						
						if firms_area_mode == 'World':
							firms_area_coordinates = 'world'
							firms_center_latitude = None
							firms_center_longitude = None
							
							st.info(
								'World mode does not update global latitude and longitude because it '
								'does not represent a single geographic center.' )
						
						else:
							st.caption(
								'Bounding box defaults are centered on the global latitude and longitude.' )
							
							firms_box_c1, firms_box_c2 = st.columns( 2 )
							
							with firms_box_c1:
								firms_west = st.number_input( 'West',
									value=float( global_box[ 'west' ] ),
									format='%.6f', key='env_firms_west' )
								
								firms_south = st.number_input( 'South',
									value=float( global_box[ 'south' ] ),
									format='%.6f', key='env_firms_south' )
							
							with firms_box_c2:
								firms_east = st.number_input( 'East',
									value=float( global_box[ 'east' ] ),
									format='%.6f', key='env_firms_east' )
								
								firms_north = st.number_input( 'North',
									value=float( global_box[ 'north' ] ),
									format='%.6f', key='env_firms_north' )
							
							firms_area_coordinates = (
									f'{float( firms_west )},{float( firms_south )},'
									f'{float( firms_east )},{float( firms_north )}'
							)
							
							firms_center_latitude = (float( firms_south ) + float( firms_north )) / 2.0
							firms_center_longitude = (float( firms_west ) + float( firms_east )) / 2.0
						
						firms_btn_c1, firms_btn_c2 = st.columns( 2 )
						with firms_btn_c1:
							if st.button( label='Run', icon='🏃', key='btn_env_firms_run',
									use_container_width=True ):
								try:
									service = Firms( )
									result = service.fetch_area( source=firms_source,
										area_coordinates=firms_area_coordinates,
										day_range=int( firms_day_range ),
										date=firms_date, time=int( firms_timeout ) )
									
									st.session_state[ 'env_last_source' ] = 'FIRMS'
									st.session_state[ 'env_last_result' ] = result or { }
									st.session_state[ 'env_last_latitude' ] = firms_center_latitude
									st.session_state[ 'env_last_longitude' ] = firms_center_longitude
									set_global_coordinates_from_result( firms_center_latitude,
										firms_center_longitude, location=global_location,
										description='FIRMS bounding-box center' )
									
									st.success( 'FIRMS request completed.' )
								
								except Exception as ex:
									st.error( f'FIRMS request failed: {ex}' )
						
						with firms_btn_c2:
							if st.button( label='Clear', icon='🧹', key='btn_env_firms_clear',
									use_container_width=True ):
								st.session_state[ 'env_last_source' ] = ''
								st.session_state[ 'env_last_result' ] = { }
								st.session_state[ 'env_last_latitude' ] = None
								st.session_state[ 'env_last_longitude' ] = None
					
						st.divider( )
						render_source_processing_controls( 'env', 'env_last_result',
							'env_last_source', 'FIRMS', 'env_firms' )
					
					# --------- EONET NATURAL EVENTS
					with st.expander( '🌎 NASA Earth Observatory Natural Events', expanded=False ):
						st.badge( label='About API', color='blue', help=cfg.NASA_EONET )
						eonet_mode = st.selectbox( 'Mode', options=[ 'events', 'categories' ],
							key='env_eonet_mode' )
						
						eonet_timeout = st.number_input( 'Timeout', min_value=1, max_value=60, value=20,
							step=1, key='env_eonet_timeout' )
						
						if eonet_mode == 'events':
							eonet_source = st.text_input( 'Source', value='',
								help='Optional EONET source identifier or comma-separated identifiers.',
								key='env_eonet_source' )
							
							eonet_category = st.text_input( 'Category', value='',
								help='Optional EONET category identifier or comma-separated identifiers.',
								key='env_eonet_category' )
							
							eonet_status = st.selectbox( 'Status', options=[ 'open', 'closed', 'all' ],
								key='env_eonet_status' )
							
							eonet_limit = st.number_input( 'Limit', min_value=1, max_value=500, value=25,
								step=1, key='env_eonet_limit' )
							
							eonet_days = st.number_input( 'Days', min_value=1, max_value=3650, value=30,
								step=1, key='env_eonet_days' )
							
							eonet_use_dates = st.checkbox( 'Use Start / End Dates', value=False,
								key='env_eonet_use_dates' )
							
							if eonet_use_dates:
								eonet_date_c1, eonet_date_c2 = st.columns( 2 )
								
								with eonet_date_c1:
									eonet_start_value = st.date_input( 'Start Date',
										value=dt.date.today( ) - dt.timedelta( days=30 ),
										key='env_eonet_start_date' )
								
								with eonet_date_c2:
									eonet_end_value = st.date_input( 'End Date', value=dt.date.today( ),
										key='env_eonet_end_date' )
								
								eonet_start_date = eonet_start_value.isoformat( )
								eonet_end_date = eonet_end_value.isoformat( )
							
							else:
								eonet_start_date = ''
								eonet_end_date = ''
							
							eonet_use_bbox = st.checkbox( 'Use Bounding Box', value=False,
								key='env_eonet_use_bbox' )
							
							if eonet_use_bbox:
								st.caption( 'Defaults are on the global latitude and longitude.' )
								eonet_box_c1, eonet_box_c2 = st.columns( 2 )
								with eonet_box_c1:
									eonet_min_lon = st.number_input( 'Min Longitude',
										value=float( global_box[ 'west' ] ),
										format='%.6f', key='env_eonet_min_lon' )
									
									eonet_max_lat = st.number_input( 'Max Latitude',
										value=float( global_box[ 'north' ] ),
										format='%.6f', key='env_eonet_max_lat' )
								
								with eonet_box_c2:
									eonet_max_lon = st.number_input( 'Max Longitude',
										value=float( global_box[ 'east' ] ),
										format='%.6f', key='env_eonet_max_lon' )
									
									eonet_min_lat = st.number_input( 'Min Latitude',
										value=float( global_box[ 'south' ] ),
										format='%.6f', key='env_eonet_min_lat' )
								
								eonet_bbox = ( f'{float( eonet_min_lon )},{float( eonet_max_lat )},'
										f'{float( eonet_max_lon )},{float( eonet_min_lat )}' )
								
								eonet_center_latitude = ( float( eonet_min_lat ) + float(
									                        eonet_max_lat ) ) / 2.0
								
								eonet_center_longitude = ( float( eonet_min_lon ) + float(
									                         eonet_max_lon ) ) / 2.0
							
							else:
								eonet_bbox = ''
								eonet_center_latitude = None
								eonet_center_longitude = None
						
						else:
							eonet_source = ''
							eonet_category = ''
							eonet_status = 'open'
							eonet_limit = 25
							eonet_days = 30
							eonet_start_date = ''
							eonet_end_date = ''
							eonet_bbox = ''
							eonet_center_latitude = None
							eonet_center_longitude = None
						
						eonet_btn_c1, eonet_btn_c2 = st.columns( 2 )
						with eonet_btn_c1:
							if st.button( label='Run', icon='🏃', key='env_eonet_run',
									use_container_width=True ):
								try:
									service = EoNet( )
									result = service.fetch( mode=eonet_mode, source=eonet_source,
										category=eonet_category, status=eonet_status,
										limit=int( eonet_limit ), days=int( eonet_days ),
										start_date=eonet_start_date, end_date=eonet_end_date,
										bbox=eonet_bbox, time=int( eonet_timeout ) )
									
									st.session_state[ 'env_last_source' ] = 'EONET'
									st.session_state[ 'env_last_result' ] = result or { }
									st.session_state[ 'env_last_latitude' ] = eonet_center_latitude
									st.session_state[ 'env_last_longitude' ] = eonet_center_longitude
									
									set_global_coordinates_from_result( eonet_center_latitude,
										eonet_center_longitude, location=global_location,
										description='EONET bounding-box center' )
									
									st.success( 'EONET request completed.' )
								
								except Exception as ex:
									st.error( f'EONET request failed: {ex}' )
						
						with eonet_btn_c2:
							if st.button( label='Clear', icon='🧹', key='env_eonet_clear',
									use_container_width=True ):
								st.session_state[ 'env_last_source' ] = ''
								st.session_state[ 'env_last_result' ] = { }
								st.session_state[ 'env_last_latitude' ] = None
								st.session_state[ 'env_last_longitude' ] = None
				
						st.divider( )
						render_source_processing_controls( 'env', 'env_last_result',
							'env_last_source', 'EONET', 'env_eonet' )
				
				with enviro_c2:
					render_mode_document_tabs( 'env', '📄 Loaded' )
		
		# ----------- Geological Expander
		with st.expander( 'Geological', expanded=False ):
			left, center, right = st.columns( [ 0.025, 0.95, 0.025 ] )
			with center:
				st.subheader( 'Geological Data' )
				st.divider( )
				global_location = get_global_location_default( )
				global_latitude = get_global_latitude_default( )
				global_longitude = get_global_longitude_default( )
				global_box = create_bounding_box_from_center( global_latitude, global_longitude )
				location_c1, location_c2, location_c3 = st.columns( 3, border=True )
				location_c1.metric( 'Location', global_location )
				location_c2.metric( 'Latitude', f'{float( global_latitude ):.4f}' )
				location_c3.metric( 'Longitude', f'{float( global_longitude ):.4f}' )
				blue_divider( )
				geo_c1, geo_c2 = st.columns( [ 0.40, 0.60 ], border=True, gap='xsmall' )
				with geo_c1:
					
					# --------- USGS EARTHQUAKES
					with st.expander( '🌎 USGS Earthquakes', expanded=True ):
						st.badge( label='About API', color='blue', help=cfg.USGS_EARTHQUAKES )
						quake_mode = st.selectbox( 'Mode', options=[ 'feed', 'search' ],
							key='geo_quake_mode' )
						
						quake_timeout = st.number_input( 'Timeout', min_value=1, max_value=60,
							value=20, step=1, key='geo_quake_timeout' )
						
						if quake_mode == 'feed':
							quake_feed = st.selectbox( 'Feed',
								options=[ 'all_hour.geojson', 'all_day.geojson', 'all_week.geojson',
										'all_month.geojson', '1.0_hour.geojson', '1.0_day.geojson',
										'1.0_week.geojson', '1.0_month.geojson', '2.5_hour.geojson',
										'2.5_day.geojson', '2.5_week.geojson', '2.5_month.geojson',
										'4.5_hour.geojson', '4.5_day.geojson', '4.5_week.geojson',
										'4.5_month.geojson', 'significant_hour.geojson',
										'significant_day.geojson', 'significant_week.geojson',
										'significant_month.geojson' ], key='geo_quake_feed' )
							
							quake_start_date = ''
							quake_end_date = ''
							quake_min_magnitude = 1.0
							quake_max_magnitude = 10.0
							quake_limit = 25
							quake_order_by = 'time'
							quake_event_type = 'earthquake'
							quake_use_location = False
							quake_latitude = None
							quake_longitude = None
							quake_radius = None
						
						else:
							quake_feed = 'all_day.geojson'
							search_c1, search_c2 = st.columns( 2 )
							
							with search_c1:
								quake_start = st.date_input( 'Start Date',
									value=dt.date.today( ) - dt.timedelta( days=7 ),
									key='geo_quake_start_date' )
							
							with search_c2:
								quake_end = st.date_input( 'End Date', value=dt.date.today( ),
									key='geo_quake_end_date' )
							
							quake_start_date = quake_start.isoformat( )
							quake_end_date = quake_end.isoformat( )
							
							mag_c1, mag_c2 = st.columns( 2 )
							with mag_c1:
								quake_min_magnitude = st.number_input( 'Minimum Magnitude', min_value=0.0,
									max_value=10.0, value=1.0, step=0.1,
									format='%.1f', key='geo_quake_min_magnitude' )
							
							with mag_c2:
								quake_max_magnitude = st.number_input( 'Maximum Magnitude', min_value=0.0,
									max_value=10.0, value=10.0, step=0.1,
									format='%.1f', key='geo_quake_max_magnitude' )
							
							quake_limit = st.number_input( 'Limit', min_value=1, max_value=20000, value=25,
								step=1, key='geo_quake_limit' )
							
							quake_order_by = st.selectbox( 'Order By',
								options=[ 'time', 'time-asc', 'magnitude', 'magnitude-asc' ],
								key='geo_quake_order_by' )
							
							quake_event_type = st.text_input( 'Event Type', value='earthquake',
								key='geo_quake_event_type' )
							
							quake_use_location = st.checkbox( 'Use Location Radius Filter',
								value=False, key='geo_quake_use_location' )
							
							if quake_use_location:
								loc_c1, loc_c2 = st.columns( 2 )
								
								with loc_c1:
									quake_latitude = st.number_input( 'Latitude',
										value=float( global_latitude ), format='%.6f',
										key='geo_quake_latitude' )
								
								with loc_c2:
									quake_longitude = st.number_input( 'Longitude',
										value=float( global_longitude ), format='%.6f',
										key='geo_quake_longitude' )
								
								quake_radius = st.number_input( 'Maximum Radius KM', min_value=1.0,
									max_value=20000.0,
									value=float( st.session_state.get( 'radius', 500.0 ) or 500.0 ),
									step=10.0, format='%.1f', key='geo_quake_radius' )
							
							else:
								quake_latitude = None
								quake_longitude = None
								quake_radius = None
						
						quake_btn_c1, quake_btn_c2 = st.columns( 2 )
						with quake_btn_c1:
							if st.button( label='Run', icon='🏃', key='geo_quake_run',
									use_container_width=True ):
								try:
									service = USGSEarthquakes( )
									result = service.fetch( mode=quake_mode, feed=quake_feed,
										start_date=quake_start_date, end_date=quake_end_date,
										min_magnitude=float( quake_min_magnitude ),
										max_magnitude=float( quake_max_magnitude ),
										limit=int( quake_limit ), order_by=quake_order_by,
										event_type=quake_event_type, latitude=quake_latitude,
										longitude=quake_longitude, max_radius_km=quake_radius,
										time=int( quake_timeout ) )
									
									st.session_state[ 'geo_last_source' ] = 'USGS Earthquakes'
									st.session_state[ 'geo_last_result' ] = result or { }
									st.session_state[ 'geo_last_latitude' ] = quake_latitude
									st.session_state[ 'geo_last_longitude' ] = quake_longitude
									
									if quake_radius is not None:
										st.session_state[ 'radius' ] = float( quake_radius )
									
									set_global_coordinates_from_result( quake_latitude, quake_longitude,
										location=global_location,
										description='USGS Earthquake search center' )
									
									st.success( 'USGS Earthquake request completed.' )
								
								except Exception as ex:
									st.error( f'USGS Earthquake request failed: {ex}' )
						
						with quake_btn_c2:
							if st.button( label='Clear', icon='🧹', key='geo_quake_clear',
									use_container_width=True ):
								st.session_state[ 'geo_last_source' ] = ''
								st.session_state[ 'geo_last_result' ] = { }
								st.session_state[ 'geo_last_latitude' ] = None
								st.session_state[ 'geo_last_longitude' ] = None
								st.session_state[ 'geo_last_image_path' ] = ''
					
						st.divider( )
						render_source_processing_controls( 'geo', 'geo_last_result', 'geo_last_source',
							'USGS Earthquakes', 'geo_usgs_earthquakes' )
						
					# --------- GLOBAL IMAGERY
					with st.expander( '🛰️ Global Imagery', expanded=False ):
						st.badge( label='About API', color='blue', help=cfg.NASA_GLOBAL_IMAGERY )
						st.caption( 'Uses the original GlobalImagery fetcher. The current fetch_map_services() '
							'writes the default NASA GIBS image to python-examples.' )
						
						imagery_product = st.selectbox( 'Product',
							options=[ 'NASA GIBS EPSG:4326 Default Map Service' ],
							key='geo_imagery_product' )
						
						imagery_btn_c1, imagery_btn_c2 = st.columns( 2 )
						with imagery_btn_c1:
							if st.button( label='Run', icon='🏃', key='geo_imagery_run',
									use_container_width=True ):
								
								try:
									Path( 'python-examples' ).mkdir( parents=True, exist_ok=True )
									service = GlobalImagery( )
									result = service.fetch_map_services( )
									
									image_path = ( 'python-examples/'
											'MODIS_Terra_CorrectedReflectance_TrueColor.png' )
									
									st.session_state[ 'geo_last_source' ] = 'Global Imagery'
									st.session_state[ 'geo_last_result' ] = { 'mode': 'fetch_map_services',
											'product': imagery_product, 'image_path': image_path,
											'result': str( result ) }
									
									st.session_state[ 'geo_last_latitude' ] = None
									st.session_state[ 'geo_last_longitude' ] = None
									st.session_state[ 'geo_last_image_path' ] = image_path
									st.success( 'Global Imagery request completed.' )
								
								except Exception as ex:
									st.error( f'Global Imagery request failed: {ex}' )
						
						with imagery_btn_c2:
							if st.button( label='Clear', icon='🧹', key='geo_imagery_clear',
									use_container_width=True ):
								st.session_state[ 'geo_last_source' ] = ''
								st.session_state[ 'geo_last_result' ] = { }
								st.session_state[ 'geo_last_latitude' ] = None
								st.session_state[ 'geo_last_longitude' ] = None
								st.session_state[ 'geo_last_image_path' ] = ''
					
						st.divider( )
						render_source_processing_controls( 'geo', 'geo_last_result', 'geo_last_source',
							'Global Imagery', 'geo_global_imagery' )
					
					# --------- USGS WATER DATA
					with st.expander( '💧 USGS Water Data', expanded=False ):
						st.badge( label='About API', color='blue', help=cfg.USGS_WATER )
						water_mode = st.selectbox( 'Mode',
							options=[ 'monitoring-locations', 'time-series-metadata', 'latest-continuous',
									'latest-daily' ], key='geo_water_mode' )
						
						water_timeout = st.number_input( 'Timeout', min_value=1, max_value=60, value=20,
							step=1, key='geo_water_timeout' )
						
						water_limit = st.number_input( 'Limit', min_value=1, max_value=1000, value=25,
							step=1, key='geo_water_limit' )
						
						if water_mode == 'monitoring-locations':
							water_monitoring_location_id = st.text_input( 'Monitoring Location ID',
								value='', help='Optional. Example: USGS-01491000',
								key='geo_water_monitoring_location_id' )
							
							water_state_code = st.text_input( 'State Code', value='',
								help='Optional state filter.', key='geo_water_state_code' )
							
							water_county_code = st.text_input( 'County Code', value='',
								help='Optional county filter.', key='geo_water_county_code' )
							
							water_site_type = st.text_input( 'Site Type', value='',
								help='Optional site type filter.', key='geo_water_site_type' )
							
							water_parameter_code = ''
						
						else:
							water_monitoring_location_id = st.text_input( 'Monitoring Location ID',
								value='USGS-01491000', help='Example: USGS-01491000',
								key='geo_water_monitoring_location_id_value' )
							
							water_parameter_code = st.text_input( 'Parameter Code', value='',
								help='Optional USGS parameter code.', key='geo_water_parameter_code' )
							
							water_state_code = ''
							water_county_code = ''
							water_site_type = ''
						
						water_btn_c1, water_btn_c2 = st.columns( 2 )
						with water_btn_c1:
							if st.button( label='Run', icon='🏃', key='geo_water_run',
									use_container_width=True ):
								try:
									service = USGSWaterData( )
									result = service.fetch(
										mode=water_mode,
										monitoring_location_id=water_monitoring_location_id,
										state_code=water_state_code,
										county_code=water_county_code,
										site_type=water_site_type,
										parameter_code=water_parameter_code,
										limit=int( water_limit ),
										time=int( water_timeout ) )
									
									st.session_state[ 'geo_last_source' ] = 'USGS Water Data'
									st.session_state[ 'geo_last_result' ] = result or { }
									st.session_state[ 'geo_last_latitude' ] = None
									st.session_state[ 'geo_last_longitude' ] = None
									st.session_state[ 'geo_last_image_path' ] = ''
									st.success( 'USGS Water Data request completed.' )
								
								except Exception as ex:
									st.error( f'USGS Water Data request failed: {ex}' )
						
						with water_btn_c2:
							if st.button( label='Clear', icon='🧹', key='geo_water_clear',
									use_container_width=True ):
								st.session_state[ 'geo_last_source' ] = ''
								st.session_state[ 'geo_last_result' ] = { }
								st.session_state[ 'geo_last_latitude' ] = None
								st.session_state[ 'geo_last_longitude' ] = None
								st.session_state[ 'geo_last_image_path' ] = ''
					
						st.divider( )
						render_source_processing_controls( 'geo', 'geo_last_result', 'geo_last_source', 'USGS Water Data', 'geo_usgs_water_data' )
					
					# --------- USGS THE NATIONAL MAP
					with st.expander( '🗺️ USGS The National Map', expanded=False ):
						st.badge( label='About API', color='blue', help=cfg.USGS_NATIONAL_MAP )
						tnm_mode = st.selectbox( 'Mode', options=[ 'datasets', 'products' ],
							key='geo_tnm_mode' )
						
						tnm_timeout = st.number_input( 'Timeout', min_value=1, max_value=60, value=20,
							step=1, key='geo_tnm_timeout' )
						
						if tnm_mode == 'datasets':
							tnm_dataset = ''
							tnm_query = ''
							tnm_bbox = ''
							tnm_prod_formats = ''
							tnm_max_items = 25
							tnm_offset = 0
							tnm_center_latitude = None
							tnm_center_longitude = None
							
							st.caption( 'Datasets mode lists does not use global coordinates.' )
						
						else:
							tnm_dataset = st.text_input( 'Dataset', value='',
								help='Optional TNM dataset filter.', key='geo_tnm_dataset' )
							
							tnm_query = st.text_input( 'Search Query', value='',
								help='Optional free-text product search.', key='geo_tnm_query' )
							
							tnm_prod_formats = st.text_input( 'Product Formats', value='',
								help='Optional format filter such as GeoTIFF, IMG, LAS, or LAZ.',
								key='geo_tnm_prod_formats' )
							
							tnm_use_bbox = st.checkbox( 'Use Bounding Box', value=False,
								key='geo_tnm_use_bbox' )
							
							if tnm_use_bbox:
								st.caption(
									'Bounding box defaults are centered on the global latitude and '
									'longitude.' )
								
								tnm_box_c1, tnm_box_c2 = st.columns( 2 )
								with tnm_box_c1:
									tnm_min_x = st.number_input( 'Min X / West Longitude',
										value=float( global_box[ 'west' ] ), format='%.6f',
										key='geo_tnm_min_x' )
									
									tnm_min_y = st.number_input( 'Min Y / South Latitude',
										value=float( global_box[ 'south' ] ), format='%.6f',
										key='geo_tnm_min_y' )
								
								with tnm_box_c2:
									tnm_max_x = st.number_input( 'Max X / East Longitude',
										value=float( global_box[ 'east' ] ), format='%.6f',
										key='geo_tnm_max_x' )
									
									tnm_max_y = st.number_input( 'Max Y / North Latitude',
										value=float( global_box[ 'north' ] ), format='%.6f',
										key='geo_tnm_max_y' )
								
								tnm_bbox = (f'{float( tnm_min_x )},{float( tnm_min_y )},'
								            f'{float( tnm_max_x )},{float( tnm_max_y )}')
								
								tnm_center_latitude = (float( tnm_min_y ) + float( tnm_max_y )) / 2.0
								tnm_center_longitude = (float( tnm_min_x ) + float( tnm_max_x )) / 2.0
							
							else:
								tnm_bbox = ''
								tnm_center_latitude = None
								tnm_center_longitude = None
							
							tnm_max_items = st.number_input( 'Max Items', min_value=1, max_value=1000,
								value=25, step=1, key='geo_tnm_max_items' )
							
							tnm_offset = st.number_input( 'Offset', min_value=0, max_value=100000, value=0,
								step=1, key='geo_tnm_offset' )
						
						tnm_btn_c1, tnm_btn_c2 = st.columns( 2 )
						with tnm_btn_c1:
							if st.button( label='Run', icon='🏃', key='geo_tnm_run',
									use_container_width=True ):
								
								try:
									service = USGSTheNationalMap( )
									result = service.fetch( mode=tnm_mode, dataset=tnm_dataset, q=tnm_query,
										bbox=tnm_bbox, prod_formats=tnm_prod_formats,
										max_items=int( tnm_max_items ), offset=int( tnm_offset ),
										time=int( tnm_timeout ) )
									
									st.session_state[ 'geo_last_source' ] = 'USGS The National Map'
									st.session_state[ 'geo_last_result' ] = result or { }
									st.session_state[ 'geo_last_latitude' ] = tnm_center_latitude
									st.session_state[ 'geo_last_longitude' ] = tnm_center_longitude
									st.session_state[ 'geo_last_image_path' ] = ''
									
									set_global_coordinates_from_result( tnm_center_latitude,
										tnm_center_longitude, location=global_location,
										description='USGS The National Map bounding-box center' )
									
									st.success( 'USGS The National Map request completed.' )
								
								except Exception as ex:
									st.error( f'USGS The National Map request failed: {ex}' )
						
						with tnm_btn_c2:
							if st.button( label='Clear', icon='🧹', key='geo_tnm_clear',
									use_container_width=True ):
								st.session_state[ 'geo_last_source' ] = ''
								st.session_state[ 'geo_last_result' ] = { }
								st.session_state[ 'geo_last_latitude' ] = None
								st.session_state[ 'geo_last_longitude' ] = None
								st.session_state[ 'geo_last_image_path' ] = ''
				
						st.divider( )
						render_source_processing_controls( 'geo', 'geo_last_result', 'geo_last_source',
							'USGS The National Map', 'geo_usgs_the_national_map' )
				
					# --------- USGS SCIENCEBASE
					with st.expander( '🧭 USGS ScienceBase', expanded=False ):
						sciencebase_mode = st.selectbox( 'Mode', options=[ 'items', 'item' ],
							key='geo_sciencebase_mode' )
						sciencebase_timeout = st.slider( 'Timeout', min_value=1, max_value=60, value=20,
							key='geo_sciencebase_timeout' )
						sciencebase_query = ''
						sciencebase_item_id = ''
						sciencebase_max_items = 25
						sciencebase_offset = 0
						sciencebase_fields = ''
						if sciencebase_mode == 'items':
							sciencebase_c1, sciencebase_c2 = st.columns( 2 )
							with sciencebase_c1:
								sciencebase_query = st.text_input( 'Query', key='geo_sciencebase_query' )
								sciencebase_max_items = st.slider( 'Maximum Items', min_value=1,
									max_value=500, value=25, key='geo_sciencebase_max_items' )
							with sciencebase_c2:
								sciencebase_fields = st.text_input( 'Fields',
									placeholder='Optional comma-separated fields', key='geo_sciencebase_fields' )
								sciencebase_offset = st.number_input( 'Offset', min_value=0, value=0, step=1,
									key='geo_sciencebase_offset' )
						else:
							sciencebase_item_id = st.text_input( 'Item ID', key='geo_sciencebase_item_id' )
						sciencebase_btn_c1, sciencebase_btn_c2 = st.columns( 2 )
						with sciencebase_btn_c1:
							if st.button( label='Run', icon='🏃', key='geo_sciencebase_run',
									use_container_width=True ):
								try:
									service = USGSScienceBase( )
									result = service.fetch( mode=sciencebase_mode, q=sciencebase_query,
										item_id=sciencebase_item_id, max_items=int( sciencebase_max_items ),
										offset=int( sciencebase_offset ), fields=sciencebase_fields,
										time=int( sciencebase_timeout ) )
									st.session_state[ 'geo_last_source' ] = 'USGS ScienceBase'
									st.session_state[ 'geo_last_result' ] = result or { }
									st.session_state[ 'geo_last_latitude' ] = None
									st.session_state[ 'geo_last_longitude' ] = None
									st.session_state[ 'geo_last_image_path' ] = ''
									st.success( 'USGS ScienceBase request completed.' )
								except Exception as ex:
									st.error( f'USGS ScienceBase request failed: {ex}' )
						with sciencebase_btn_c2:
							if st.button( label='Clear', icon='🧹', key='geo_sciencebase_clear',
									use_container_width=True ):
								st.session_state[ 'geo_last_source' ] = ''
								st.session_state[ 'geo_last_result' ] = { }
								st.session_state[ 'geo_last_latitude' ] = None
								st.session_state[ 'geo_last_longitude' ] = None
								st.session_state[ 'geo_last_image_path' ] = ''
						st.divider( )
						render_source_processing_controls( 'geo', 'geo_last_result', 'geo_last_source',
							'USGS ScienceBase', 'geo_usgs_sciencebase' )
				with geo_c2:
					render_mode_document_tabs( 'geo', '📄 Loaded' )

# ==============================================================================
# ASTRONOMICAL MODE
# ==============================================================================
elif mode == 'Astronomical Data':
	left, center, right = st.columns( [ 0.025, 0.95, 0.025 ] )
	with center:
		st.subheader( 'Astronomical Data' )
		st.divider( )
		global_location = get_global_location_default( )
		global_latitude = get_global_latitude_default( )
		global_longitude = get_global_longitude_default( )
		location_c1, location_c2, location_c3 = st.columns( 3, border=True )
		location_c1.metric( 'Observer Location', global_location )
		location_c2.metric( 'Observer Latitude', f'{float( global_latitude ):.4f}' )
		location_c3.metric( 'Observer Longitude', f'{float( global_longitude ):.4f}' )
		blue_divider( )
		astro_c1, astro_c2 = st.columns( [ 0.40, 0.60 ], border=True, gap='xsmall' )
		with astro_c1:
			
			# --------- NAVAL OBSERVATORY
			with st.expander( '🧭 Naval Observatory', expanded=True ):
				st.badge( label='About API', color='blue', help=cfg.US_NAVAL_OBSERVATORY )
				naval_date = st.date_input( 'Date', value=dt.date.today( ),
					key='astro_naval_date' )
				
				naval_time_value = st.text_input( 'Time', value='12:00:00',
					help='Use HH:MM, HH:MM:SS, or HH:MM:SS.S format.',
					key='astro_naval_time_value' )
				
				naval_c1, naval_c2 = st.columns( 2 )
				with naval_c1:
					naval_latitude = st.number_input( 'Observer Latitude',
						value=float( global_latitude ), format='%.6f', key='astro_naval_latitude' )
				
				with naval_c2:
					naval_longitude = st.number_input( 'Observer Longitude',
						value=float( global_longitude ), format='%.6f',
						key='astro_naval_longitude' )
				
				naval_location_label = st.text_input( 'Location Label', value=global_location,
					key='astro_naval_location_label' )
				
				naval_timeout = st.number_input( 'Timeout', min_value=1, max_value=60, value=20,
					step=1, key='astro_naval_timeout' )
				
				naval_btn_c1, naval_btn_c2 = st.columns( 2 )
				with naval_btn_c1:
					if st.button( label='Run', icon='🏃', key='astro_naval_run',
							use_container_width=True ):
						if not has_valid_coordinates( naval_latitude, naval_longitude ):
							st.warning( 'Provide valid observer latitude and longitude.' )
						else:
							try:
								service = NavalObservatory( )
								
								result = service.fetch( mode='celnav',
									date_value=naval_date.isoformat( ),
									time_value=naval_time_value,
									latitude=float( naval_latitude ),
									longitude=float( naval_longitude ),
									location_label=naval_location_label,
									time=int( naval_timeout ) )
								
								st.session_state[ 'astro_last_source' ] = 'Naval Observatory'
								st.session_state[ 'astro_last_result' ] = result or { }
								st.session_state[ 'astro_last_latitude' ] = float( naval_latitude )
								st.session_state[ 'astro_last_longitude' ] = float(
									naval_longitude )
								st.session_state[ 'astro_last_url' ] = ''
								
								set_global_coordinates_from_result( naval_latitude,
									naval_longitude, location=naval_location_label,
									description='Naval Observatory observer location' )
								
								st.success( 'Naval Observatory request completed.' )
							
							except Exception as ex:
								st.error( f'Naval Observatory request failed: {ex}' )
				
				with naval_btn_c2:
					if st.button( label='Clear', icon='🧹', key='astro_naval_clear',
							use_container_width=True ):
						st.session_state[ 'astro_last_source' ] = ''
						st.session_state[ 'astro_last_result' ] = { }
						st.session_state[ 'astro_last_latitude' ] = None
						st.session_state[ 'astro_last_longitude' ] = None
						st.session_state[ 'astro_last_url' ] = ''
			
				st.divider( )
				render_source_processing_controls( 'astro', 'astro_last_result',
					'astro_last_source', 'Naval Observatory', 'astro_naval_observatory' )
			
			# --------- SPACE WEATHER
			with st.expander( '☀️ Space Weather', expanded=False ):
				st.badge( label='About API', color='blue', help=cfg.SPACE_WEATHER )
				space_mode = st.selectbox( 'Mode',
					options=[ 'cme', 'cme_analysis', 'gst', 'ips', 'flr', 'sep', 'mpc', 'rbe',
					          'hss', 'wsa_enlil', 'notifications' ], key='astro_space_mode' )
				
				space_date_c1, space_date_c2 = st.columns( 2 )
				with space_date_c1:
					space_start = st.date_input( 'Start Date',
						value=dt.date.today( ) - dt.timedelta( days=7 ),
						key='astro_space_start_date' )
				
				with space_date_c2:
					space_end = st.date_input( 'End Date', value=dt.date.today( ),
						key='astro_space_end_date' )
				
				space_location = st.text_input( 'Location', value='ALL',
					key='astro_space_location' )
				
				space_catalog = st.text_input( 'Catalog', value='ALL', key='astro_space_catalog' )
				
				space_notification_type = st.text_input( 'Notification Type', value='all',
					key='astro_space_notification_type' )
				
				space_c1, space_c2 = st.columns( 2 )
				with space_c1:
					space_most_accurate_only = st.checkbox( 'Most Accurate Only', value=True,
						key='astro_space_most_accurate_only' )
					
					space_complete_entry_only = st.checkbox( 'Complete Entry Only', value=True,
						key='astro_space_complete_entry_only' )
				
				with space_c2:
					space_speed = st.number_input( 'Speed', min_value=0, max_value=5000, value=0,
						step=10, key='astro_space_speed' )
					
					space_half_angle = st.number_input( 'Half Angle', min_value=0, max_value=360,
						value=0, step=1, key='astro_space_half_angle' )
				
				space_keyword = st.text_input( 'Keyword', value='', key='astro_space_keyword' )
				space_timeout = st.number_input( 'Timeout', min_value=1, max_value=60, value=20,
					step=1, key='astro_space_timeout' )
				
				space_btn_c1, space_btn_c2 = st.columns( 2 )
				with space_btn_c1:
					if st.button( label='Run', icon='🏃', key='astro_space_run',
							use_container_width=True ):
						try:
							service = SpaceWeather( )
							result = service.fetch( mode=space_mode,
								start_date=space_start.isoformat( ),
								end_date=space_end.isoformat( ), time=int( space_timeout ),
								location=space_location, catalog=space_catalog,
								notification_type=space_notification_type,
								most_accurate_only=bool( space_most_accurate_only ),
								complete_entry_only=bool( space_complete_entry_only ),
								speed=int( space_speed ), half_angle=int( space_half_angle ),
								keyword=space_keyword,
								api_key=getattr( cfg, 'NASA_API_KEY', None ) )
							
							st.session_state[ 'astro_last_source' ] = 'Space Weather'
							st.session_state[ 'astro_last_result' ] = result or { }
							st.session_state[ 'astro_last_latitude' ] = None
							st.session_state[ 'astro_last_longitude' ] = None
							st.session_state[ 'astro_last_url' ] = ''
							st.success( 'Space Weather request completed.' )
						
						except Exception as ex:
							st.error( f'Space Weather request failed: {ex}' )
				
				with space_btn_c2:
					if st.button( label='Clear', icon='🧹', key='astro_space_clear',
							use_container_width=True ):
						
						st.session_state[ 'astro_last_source' ] = ''
						st.session_state[ 'astro_last_result' ] = { }
						st.session_state[ 'astro_last_latitude' ] = None
						st.session_state[ 'astro_last_longitude' ] = None
						st.session_state[ 'astro_last_url' ] = ''
			
				st.divider( )
				render_source_processing_controls( 'astro', 'astro_last_result',
					'astro_last_source', 'Space Weather', 'astro_space_weather' )
				
			# --------- STAR CHART
			with st.expander( '✨ Star Chart', expanded=False ):
				st.caption( 'API', help=cfg.STAR_CHART )
				chart_mode = st.selectbox( 'Mode',
					options=[ 'Object Chart', 'Coordinate Chart', 'Static Chart' ],
					key='astro_chart_mode' )
				
				chart_zoom = st.number_input( 'Zoom', min_value=1, max_value=20,
					value=5, step=1, key='astro_chart_zoom' )
				
				chart_image_source = st.text_input( 'Image Source', value='DSS2',
					key='astro_chart_image_source' )
				
				if chart_mode == 'Object Chart':
					chart_object_name = st.text_input( 'Object Name', value='M31',
						key='astro_chart_object_name' )
					
					chart_ra = 0.0
					chart_dec = 0.0
				
				else:
					chart_object_name = ''
					coord_c1, coord_c2 = st.columns( 2 )
					with coord_c1:
						chart_ra = st.number_input( 'Right Ascension', value=10.6847083,
							format='%.7f', key='astro_chart_ra' )
					
					with coord_c2:
						chart_dec = st.number_input( 'Declination', value=41.2687500,
							format='%.7f', key='astro_chart_dec' )
				
				chart_box_color = st.selectbox( 'Box Color',
					options=[ 'yellow', 'red', 'green', 'blue', 'white' ],
					key='astro_chart_box_color' )
				
				chart_options_c1, chart_options_c2 = st.columns( 2 )
				with chart_options_c1:
					chart_show_box = st.checkbox( 'Show Box', value=True,
						key='astro_chart_show_box' )
					
					chart_show_grid = st.checkbox( 'Show Grid', value=True,
						key='astro_chart_show_grid' )
				
				with chart_options_c2:
					chart_show_lines = st.checkbox( 'Show Lines', value=True,
						key='astro_chart_show_lines' )
					
					chart_show_boundaries = st.checkbox( 'Show Boundaries', value=True,
						key='astro_chart_show_boundaries' )
				
				if chart_mode == 'Static Chart':
					static_c1, static_c2 = st.columns( 2 )
					with static_c1:
						chart_width = st.number_input( 'Width', min_value=250, max_value=2500,
							value=900, step=50, key='astro_chart_width' )
						
						chart_magnitude = st.number_input( 'Magnitude', min_value=0.0,
							max_value=20.0, value=7.5, step=0.1, format='%.1f',
							key='astro_chart_magnitude' )
					
					with static_c2:
						chart_height = st.number_input( 'Height', min_value=250, max_value=2500,
							value=450, step=50, key='astro_chart_height' )
						
						chart_show_const_names = st.checkbox(
							'Show Constellation Names',
							value=False,
							key='astro_chart_show_const_names' )
				
				else:
					chart_width = 900
					chart_height = 450
					chart_magnitude = 7.5
					chart_show_const_names = False
				
				chart_timeout = st.number_input( 'Timeout', min_value=1, max_value=60, value=20,
					step=1, key='astro_chart_timeout' )
				
				chart_btn_c1, chart_btn_c2 = st.columns( 2 )
				with chart_btn_c1:
					if st.button( label='Run', icon='🏃', key='astro_chart_run',
							use_container_width=True ):
						try:
							service = StarChart( )
							
							if chart_mode == 'Object Chart':
								if not chart_object_name:
									st.warning( 'Enter an object name.' )
									result = None
								else:
									result = service.fetch_object_chart( name=chart_object_name,
										zoom=int( chart_zoom ), box_color=chart_box_color,
										show_box=bool( chart_show_box ),
										image_source=chart_image_source,
										time=int( chart_timeout ) )
							
							elif chart_mode == 'Coordinate Chart':
								result = service.fetch_coordinate_chart( ra=float( chart_ra ),
									dec=float( chart_dec ), zoom=int( chart_zoom ),
									box_color=chart_box_color, show_box=bool( chart_show_box ),
									show_grid=bool( chart_show_grid ),
									show_lines=bool( chart_show_lines ),
									show_boundaries=bool( chart_show_boundaries ),
									image_source=chart_image_source )
							
							else:
								result = service.fetch_static_chart( ra=float( chart_ra ),
									dec=float( chart_dec ), zoom=int( chart_zoom ),
									image_source=chart_image_source,
									show_grid=bool( chart_show_grid ),
									show_lines=bool( chart_show_lines ),
									show_boundaries=bool( chart_show_boundaries ),
									show_const_names=bool( chart_show_const_names ),
									width=int( chart_width ), height=int( chart_height ),
									magnitude=float( chart_magnitude ) )
							
							if result is not None:
								result_url = ''
								if isinstance( result, dict ):
									result_url = ( result.get( 'chart_url', '' )
											or result.get( 'image_url', '' )
											or result.get( 'static_chart_url', '' )
											or result.get( 'preferred_image_url', '' )
											or result.get( 'snapshot_page_url', '' ) )
								
								st.session_state[ 'astro_last_source' ] = 'Star Chart'
								st.session_state[ 'astro_last_result' ] = result or { }
								st.session_state[ 'astro_last_latitude' ] = None
								st.session_state[ 'astro_last_longitude' ] = None
								st.session_state[ 'astro_last_url' ] = result_url
								st.success( 'Star Chart request completed.' )
						
						except Exception as ex:
							st.error( f'Star Chart request failed: {ex}' )
				
				with chart_btn_c2:
					if st.button( label='Clear', icon='🧹', key='astro_chart_clear',
							use_container_width=True ):
						st.session_state[ 'astro_last_source' ] = ''
						st.session_state[ 'astro_last_result' ] = { }
						st.session_state[ 'astro_last_latitude' ] = None
						st.session_state[ 'astro_last_longitude' ] = None
						st.session_state[ 'astro_last_url' ] = ''
			
				st.divider( )
				render_source_processing_controls( 'astro', 'astro_last_result',
					'astro_last_source', 'Star Chart', 'astro_star_chart' )
			
			# --------- SATELLITE CENTER
			with st.expander( '🛰️ Satellite Center', expanded=False ):
				st.caption( 'API', help=cfg.SATELLITE_CENTER )
				satellite_mode = st.selectbox( 'Mode',
					options=[ 'observatories', 'ground_stations', 'locations' ],
					key='astro_satellite_mode' )
				
				satellite_timeout = st.number_input( 'Timeout', min_value=1, max_value=60,
					value=20, step=1, key='astro_satellite_timeout' )
				
				if satellite_mode == 'locations':
					satellite_query = st.text_input( 'Observatories', value='iss',
						help='Comma-separated observatory identifiers such as iss or mms1,mms2.',
						key='astro_satellite_query' )
					
					satellite_start_date = st.date_input( 'Start Date',
						value=dt.date.today( ) - dt.timedelta( days=1 ),
						key='astro_satellite_start_date' )
					
					satellite_start_time = st.text_input( 'Start Time', value='00:00:00Z',
						help='Use UTC time ending in Z.', key='astro_satellite_start_time' )
					
					satellite_end_date = st.date_input( 'End Date', value=dt.date.today( ),
						key='astro_satellite_end_date' )
					
					satellite_end_time = st.text_input( 'End Time', value='00:00:00Z',
						help='Use UTC time ending in Z.',
						key='astro_satellite_end_time' )
					
					satellite_coordinate_systems = st.text_input( 'Coordinate Systems', value='gse',
						help='Comma-separated coordinate systems such as gse, geo, or gsm.',
						key='astro_satellite_coordinate_systems' )
					
					satellite_resolution_factor = st.number_input( 'Resolution Factor',
						min_value=1, max_value=10000, value=1, step=1,
						key='astro_satellite_resolution_factor' )
				
				else:
					satellite_query = ''
					satellite_start_date = dt.date.today( )
					satellite_start_time = ''
					satellite_end_date = dt.date.today( )
					satellite_end_time = ''
					satellite_coordinate_systems = 'gse'
					satellite_resolution_factor = 1
				
				satellite_btn_c1, satellite_btn_c2 = st.columns( 2 )
				with satellite_btn_c1:
					if st.button( label='Run', icon='🏃', key='astro_satellite_run',
							use_container_width=True ):
						try:
							service = SatelliteCenter( )
							
							if satellite_mode == 'locations':
								start_value = f'{satellite_start_date.isoformat( )}T{satellite_start_time}'
								end_value = f'{satellite_end_date.isoformat( )}T{satellite_end_time}'
							else:
								start_value = ''
								end_value = ''
							
							result = service.fetch( mode=satellite_mode, query=satellite_query,
								start_time=start_value, end_time=end_value,
								coordinate_systems=satellite_coordinate_systems,
								resolution_factor=int( satellite_resolution_factor ),
								time=int( satellite_timeout ) )
							
							st.session_state[ 'astro_last_source' ] = 'Satellite Center'
							st.session_state[ 'astro_last_result' ] = normalize( result ) or { }
							st.session_state[ 'astro_last_latitude' ] = None
							st.session_state[ 'astro_last_longitude' ] = None
							st.session_state[ 'astro_last_url' ] = ''
							st.success( 'Satellite Center request completed.' )
						
						except Exception as ex:
							st.error( f'Satellite Center request failed: {ex}' )
				
				with satellite_btn_c2:
					if st.button( label='Clear', icon='🧹', key='astro_satellite_clear',
							use_container_width=True ):
						
						st.session_state[ 'astro_last_source' ] = ''
						st.session_state[ 'astro_last_result' ] = { }
						st.session_state[ 'astro_last_latitude' ] = None
						st.session_state[ 'astro_last_longitude' ] = None
						st.session_state[ 'astro_last_url' ] = ''
			
				st.divider( )
				render_source_processing_controls( 'astro', 'astro_last_result', 'astro_last_source',
					'Satellite Center', 'astro_satellite_center' )
			
			# --------- ASTRO CATALOG
			with st.expander( '🔭 Astro Catalog', expanded=False ):
				st.caption( 'API', help=cfg.ASTRONOMY_CATALOG )
				catalog_mode = st.selectbox( 'Mode', options=[ 'object_query', 'cone_search' ],
					key='astro_catalog_mode' )
				
				catalog_quantity = st.text_input( 'Quantity', value='',
					help='Optional Open Astronomy Catalog quantity path segment.',
					key='astro_catalog_quantity' )
				
				catalog_attributes = st.text_input( 'Attributes', value='',
					help='Optional comma-separated attribute path segments.',
					key='astro_catalog_attributes' )
				
				catalog_arguments = st.text_area( 'Arguments', value='',
					help='Optional comma-separated or newline-separated key=value arguments.',
					key='astro_catalog_arguments' )
				
				catalog_data_format = st.selectbox( 'Data Format', options=[ 'json', 'csv' ],
					key='astro_catalog_data_format' )
				
				catalog_timeout = st.number_input( 'Timeout', min_value=1, max_value=60, value=20,
					step=1, key='astro_catalog_timeout' )
				
				if catalog_mode == 'object_query':
					catalog_query = st.text_input( 'Object Name', value='SN2011fe',
						key='astro_catalog_query' )
					
					catalog_ra = ''
					catalog_dec = ''
					catalog_radius = 2
				
				else:
					catalog_query = ''
					catalog_ra = st.text_input( 'Right Ascension', value='10:00:00',
						key='astro_catalog_ra' )
					
					catalog_dec = st.text_input( 'Declination', value='+10:00:00',
						key='astro_catalog_dec' )
					
					catalog_radius = st.number_input( 'Radius', min_value=1, max_value=360,
						value=2, step=1, key='astro_catalog_radius' )
				
				catalog_btn_c1, catalog_btn_c2 = st.columns( 2 )
				with catalog_btn_c1:
					if st.button( label='Run', icon='🏃', key='astro_catalog_run',
							use_container_width=True ):
						try:
							service = AstroCatalog( )
							result = service.fetch( mode=catalog_mode, query=catalog_query,
								quantity=catalog_quantity, attributes=catalog_attributes,
								arguments=catalog_arguments, ra=catalog_ra, dec=catalog_dec,
								radius=int( catalog_radius ), data_format=catalog_data_format,
								time=int( catalog_timeout ) )
							
							st.session_state[ 'astro_last_source' ] = 'Astro Catalog'
							st.session_state[ 'astro_last_result' ] = normalize( result ) or { }
							st.session_state[ 'astro_last_latitude' ] = None
							st.session_state[ 'astro_last_longitude' ] = None
							st.session_state[ 'astro_last_url' ] = ''
							st.success( 'Astro Catalog request completed.' )
						
						except Exception as ex:
							st.error( f'Astro Catalog request failed: {ex}' )
				
				with catalog_btn_c2:
					if st.button( label='Clear', icon='🧹', key='astro_catalog_clear',
							use_container_width=True ):
						st.session_state[ 'astro_last_source' ] = ''
						st.session_state[ 'astro_last_result' ] = { }
						st.session_state[ 'astro_last_latitude' ] = None
						st.session_state[ 'astro_last_longitude' ] = None
						st.session_state[ 'astro_last_url' ] = ''
			
				st.divider( )
				render_source_processing_controls( 'astro', 'astro_last_result', 'astro_last_source',
					'Astro Catalog', 'astro_astro_catalog' )
			
			# --------- ASTROQUERY / SIMBAD
			with st.expander( '🌌 AstroQuery / SIMBAD', expanded=False ):
				st.caption( 'API', help=cfg.ASTRO_QUERY )
				astroquery_mode = st.selectbox( 'Mode',
					options=[ 'object_search', 'object_ids', 'region_search' ],
					key='astro_astroquery_mode' )
				
				astroquery_row_limit = st.number_input( 'Row Limit', min_value=1, max_value=10000,
					value=100, step=1, key='astro_astroquery_row_limit' )
				
				if astroquery_mode in [ 'object_search', 'object_ids' ]:
					astroquery_query = st.text_input( 'Object Name', value='M31',
						key='astro_astroquery_query' )
					
					astroquery_ra = ''
					astroquery_dec = ''
					astroquery_radius = 0.5
					astroquery_radius_unit = 'deg'
				
				else:
					astroquery_query = ''
					astroquery_ra = st.text_input( 'Right Ascension', value='10.6847083',
						key='astro_astroquery_ra' )
					
					astroquery_dec = st.text_input( 'Declination', value='41.2687500',
						key='astro_astroquery_dec' )
					
					astroquery_radius = st.number_input( 'Radius', min_value=0.001,
						max_value=180.0,
						value=0.5, step=0.1, format='%.3f', key='astro_astroquery_radius' )
					
					astroquery_radius_unit = st.selectbox( 'Radius Unit',
						options=[ 'deg', 'arcmin', 'arcsec' ], key='astro_astroquery_radius_unit' )
				
				astroquery_btn_c1, astroquery_btn_c2 = st.columns( 2 )
				with astroquery_btn_c1:
					if st.button( label='Run', icon='🏃', key='astro_astroquery_run',
							use_container_width=True ):
						try:
							service = AstroQuery( )
							result = service.fetch(
								mode=astroquery_mode,
								query=astroquery_query,
								ra=astroquery_ra,
								dec=astroquery_dec,
								radius=float( astroquery_radius ),
								radius_unit=astroquery_radius_unit,
								row_limit=int( astroquery_row_limit ) )
							
							st.session_state[ 'astro_last_source' ] = 'AstroQuery / SIMBAD'
							st.session_state[ 'astro_last_result' ] = normalize( result ) or { }
							st.session_state[ 'astro_last_latitude' ] = None
							st.session_state[ 'astro_last_longitude' ] = None
							st.session_state[ 'astro_last_url' ] = ''
							st.success( 'AstroQuery request completed.' )
						
						except Exception as ex:
							st.error( f'AstroQuery request failed: {ex}' )
				
				with astroquery_btn_c2:
					if st.button( label='Clear', icon='🧹', key='astro_astroquery_clear',
							use_container_width=True ):
						st.session_state[ 'astro_last_source' ] = ''
						st.session_state[ 'astro_last_result' ] = { }
						st.session_state[ 'astro_last_latitude' ] = None
						st.session_state[ 'astro_last_longitude' ] = None
						st.session_state[ 'astro_last_url' ] = ''
			
				st.divider( )
				render_source_processing_controls( 'astro', 'astro_last_result', 'astro_last_source',
					'AstroQuery / SIMBAD', 'astro_astroquery_simbad' )
			
			# --------- STAR MAP
			with st.expander( '🗺️ Star Map', expanded=False ):
				st.caption( 'API', help=cfg.STAR_MAP )
				starmap_mode = st.selectbox( 'Mode',
					options=[ 'object_link', 'coordinate_link', 'snapshot' ],
					key='astro_starmap_mode' )
				
				starmap_zoom = st.number_input( 'Zoom', min_value=1, max_value=20,
					value=5, step=1, key='astro_starmap_zoom' )
				
				starmap_image_source = st.text_input( 'Image Source', value='DSS2',
					key='astro_starmap_image_source' )
				
				starmap_box_color = st.selectbox( 'Box Color',
					options=[ 'yellow', 'red', 'green', 'blue', 'white' ],
					key='astro_starmap_box_color' )
				
				if starmap_mode == 'object_link':
					starmap_query = st.text_input( 'Object Name', value='M31',
						key='astro_starmap_query' )
					
					starmap_ra = 0.0
					starmap_dec = 0.0
				
				else:
					starmap_query = ''
					starmap_coord_c1, starmap_coord_c2 = st.columns( 2 )
					with starmap_coord_c1:
						starmap_ra = st.number_input( 'Right Ascension', value=10.6847083,
							format='%.7f', key='astro_starmap_ra' )
					
					with starmap_coord_c2:
						starmap_dec = st.number_input( 'Declination', value=41.2687500,
							format='%.7f', key='astro_starmap_dec' )
				
				starmap_options_c1, starmap_options_c2 = st.columns( 2 )
				with starmap_options_c1:
					starmap_show_box = st.checkbox( 'Show Box', value=True,
						key='astro_starmap_show_box' )
					
					starmap_show_grid = st.checkbox( 'Show Grid', value=True,
						key='astro_starmap_show_grid' )
				
				with starmap_options_c2:
					starmap_show_lines = st.checkbox( 'Show Lines', value=True,
						key='astro_starmap_show_lines' )
					
					starmap_show_boundaries = st.checkbox( 'Show Boundaries', value=True,
						key='astro_starmap_show_boundaries' )
				
				starmap_show_const_names = st.checkbox( 'Show Constellation Names', value=False,
					key='astro_starmap_show_const_names' )
				
				starmap_timeout = st.number_input( 'Timeout', min_value=1, max_value=60,
					value=20, step=1, key='astro_starmap_timeout' )
				
				starmap_btn_c1, starmap_btn_c2 = st.columns( 2 )
				
				with starmap_btn_c1:
					if st.button( label='Run', icon='🏃', key='astro_starmap_run',
							use_container_width=True ):
						try:
							service = StarMap( )
							result = service.fetch( mode=starmap_mode, query=starmap_query,
								ra=float( starmap_ra ), dec=float( starmap_dec ),
								zoom=int( starmap_zoom ), image_source=starmap_image_source,
								box_color=starmap_box_color, show_box=bool( starmap_show_box ),
								show_grid=bool( starmap_show_grid ),
								show_lines=bool( starmap_show_lines ),
								show_boundaries=bool( starmap_show_boundaries ),
								show_const_names=bool( starmap_show_const_names ),
								time=int( starmap_timeout ) )
							
							result_url = ''
							if isinstance( result, dict ):
								result_url = ( result.get( 'preferred_image_url', '' )
										or result.get( 'snapshot_page_url', '' )
										or result.get( 'object_page_url', '' )
										or result.get( 'coordinate_page_url', '' )
										or result.get( 'url', '' ) )
							
							st.session_state[ 'astro_last_source' ] = 'Star Map'
							st.session_state[ 'astro_last_result' ] = normalize( result ) or { }
							st.session_state[ 'astro_last_latitude' ] = None
							st.session_state[ 'astro_last_longitude' ] = None
							st.session_state[ 'astro_last_url' ] = result_url
							st.success( 'Star Map request completed.' )
						
						except Exception as ex:
							st.error( f'Star Map request failed: {ex}' )
				
				with starmap_btn_c2:
					if st.button( label='Clear', icon='🧹', key='astro_starmap_clear',
							use_container_width=True ):
						st.session_state[ 'astro_last_source' ] = ''
						st.session_state[ 'astro_last_result' ] = { }
						st.session_state[ 'astro_last_latitude' ] = None
						st.session_state[ 'astro_last_longitude' ] = None
						st.session_state[ 'astro_last_url' ] = ''
		
				st.divider( )
				render_source_processing_controls( 'astro', 'astro_last_result',
					'astro_last_source', 'Star Map', 'astro_star_map' )
				
			# --------- JPL NEARBY OBJECTS
			with st.expander( '☄️ JPL Nearby Objects', expanded=False ):
				st.caption( 'API', help=cfg.NASA_EONET )
				nearby_mode = st.selectbox( 'Mode',
					options=[ 'close_approaches', 'object_lookup', 'nhats_summary', 'nhats_object',
					          'fireballs' ], key='astro_nearby_mode' )
				nearby_timeout = st.slider( 'Timeout', min_value=1, max_value=60, value=20,
					key='astro_nearby_timeout' )
				nearby_start_date = ''
				nearby_end_date = ''
				nearby_query = ''
				nearby_query_type = 'sstr'
				nearby_dist_max = '10LD'
				nearby_body = 'Earth'
				nearby_sort = 'date'
				nearby_limit = 20
				nearby_dv = 6.0
				nearby_dur = 360
				nearby_stay = 8
				nearby_launch = '2020-2045'
				nearby_h = 26.0
				nearby_occ = 7
				nearby_include_physical = True
				nearby_include_close = True
				nearby_include_discovery = True
				nearby_ca_body = 'Earth'
				if nearby_mode == 'close_approaches':
					nearby_c1, nearby_c2 = st.columns( 2 )
					with nearby_c1:
						nearby_start_date = st.text_input( 'Start Date', placeholder='YYYY-MM-DD',
							key='astro_nearby_start_date' )
						nearby_dist_max = st.text_input( 'Maximum Distance', value='10LD',
							key='astro_nearby_dist_max' )
						nearby_sort = st.selectbox( 'Sort', [ 'date', 'dist' ],
							key='astro_nearby_sort' )
					with nearby_c2:
						nearby_end_date = st.text_input( 'End Date', placeholder='YYYY-MM-DD',
							key='astro_nearby_end_date' )
						nearby_body = st.selectbox( 'Body', [ 'Earth', 'Moon', 'Mars', 'Juptr' ],
							key='astro_nearby_body' )
						nearby_limit = st.slider( 'Maximum Records', min_value=1, max_value=500,
							value=20, key='astro_nearby_limit' )
				elif nearby_mode == 'object_lookup':
					nearby_query = st.text_input( 'Object', value='Apophis',
						key='astro_nearby_query' )
					nearby_query_type = st.selectbox( 'Query Type', [ 'sstr', 'spk', 'des' ],
						key='astro_nearby_query_type' )
					nearby_opt_c1, nearby_opt_c2 = st.columns( 2 )
					with nearby_opt_c1:
						nearby_include_physical = st.checkbox( 'Physical Parameters', value=True,
							key='astro_nearby_physical' )
						nearby_include_close = st.checkbox( 'Close Approaches', value=True,
							key='astro_nearby_close' )
					with nearby_opt_c2:
						nearby_include_discovery = st.checkbox( 'Discovery Data', value=True,
							key='astro_nearby_discovery' )
						nearby_ca_body = st.selectbox( 'Approach Body', [ 'Earth', 'Moon', 'Mars' ],
							key='astro_nearby_ca_body' )
				elif nearby_mode in [ 'nhats_summary', 'nhats_object' ]:
					if nearby_mode == 'nhats_object':
						nearby_query = st.text_input( 'Designation', key='astro_nearby_designation' )
					nhats_c1, nhats_c2 = st.columns( 2 )
					with nhats_c1:
						nearby_dv = st.number_input( 'Maximum ΔV', min_value=0.0, value=6.0,
							step=0.1, key='astro_nearby_dv' )
						nearby_stay = st.number_input( 'Minimum Stay', min_value=0, value=8,
							step=1, key='astro_nearby_stay' )
						nearby_h = st.number_input( 'Maximum H', min_value=0.0, value=26.0,
							step=0.1, key='astro_nearby_h' )
					with nhats_c2:
						nearby_dur = st.number_input( 'Maximum Duration', min_value=1, value=360,
							step=1, key='astro_nearby_dur' )
						nearby_launch = st.text_input( 'Launch Window', value='2020-2045',
							key='astro_nearby_launch' )
						nearby_occ = st.number_input( 'Minimum Opportunities', min_value=1, value=7,
							step=1, key='astro_nearby_occ' )
				else:
					nearby_start_date = st.text_input( 'Minimum Date', placeholder='YYYY-MM-DD',
						key='astro_nearby_fireball_date' )
					nearby_limit = st.slider( 'Maximum Records', min_value=1, max_value=500,
						value=20, key='astro_nearby_fireball_limit' )
				nearby_btn_c1, nearby_btn_c2 = st.columns( 2 )
				with nearby_btn_c1:
					if st.button( label='Run', icon='🏃', key='astro_nearby_run',
							use_container_width=True ):
						try:
							service = NearbyObjects( )
							result = service.fetch( mode=nearby_mode, start_date=nearby_start_date,
								end_date=nearby_end_date, query=nearby_query,
								query_type=nearby_query_type, dist_max=nearby_dist_max,
								body=nearby_body, sort=nearby_sort, limit=int( nearby_limit ),
								dv=float( nearby_dv ), dur=int( nearby_dur ), stay=int( nearby_stay ),
								launch=nearby_launch, h=float( nearby_h ), occ=int( nearby_occ ),
								include_physical=bool( nearby_include_physical ),
								include_close_approaches=bool( nearby_include_close ),
								ca_body=nearby_ca_body, include_discovery=bool( nearby_include_discovery ),
								time=int( nearby_timeout ) )
							st.session_state[ 'astro_last_source' ] = 'JPL Nearby Objects'
							st.session_state[ 'astro_last_result' ] = normalize( result ) or { }
							st.session_state[ 'astro_last_latitude' ] = None
							st.session_state[ 'astro_last_longitude' ] = None
							st.session_state[ 'astro_last_url' ] = ''
							st.success( 'JPL Nearby Objects request completed.' )
						except Exception as ex:
							st.error( f'JPL Nearby Objects request failed: {ex}' )
				with nearby_btn_c2:
					if st.button( label='Clear', icon='🧹', key='astro_nearby_clear',
							use_container_width=True ):
						st.session_state[ 'astro_last_source' ] = ''
						st.session_state[ 'astro_last_result' ] = { }
						st.session_state[ 'astro_last_latitude' ] = None
						st.session_state[ 'astro_last_longitude' ] = None
						st.session_state[ 'astro_last_url' ] = ''
				st.divider( )
				render_source_processing_controls( 'astro', 'astro_last_result',
					'astro_last_source', 'JPL Nearby Objects', 'astro_nearby_objects' )

			# --------- NASA OPEN SCIENCE DATA REPOSITORY
			with st.expander( '🧬 NASA Open Science Data', expanded=False ):
				st.caption( 'API', help=cfg.NASA_OPEN_SCIENCE )
				open_science_mode = st.selectbox( 'Mode',
					options=[ 'dataset', 'metadata', 'assays', 'data' ],
					key='astro_open_science_mode' )
				open_science_timeout = st.slider( 'Timeout', min_value=1, max_value=60, value=20,
					key='astro_open_science_timeout' )
				open_science_query = ''
				open_science_accession = ''
				open_science_format = 'json'
				if open_science_mode == 'dataset':
					open_science_accession = st.text_input( 'OSDR Accession', value='OSD-48',
						key='astro_open_science_accession' )
				else:
					open_science_c1, open_science_c2 = st.columns( 2 )
					with open_science_c1:
						open_science_query = st.text_input( 'Query',
							key='astro_open_science_query' )
					with open_science_c2:
						open_science_format = st.selectbox( 'Format',
							options=[ 'json', 'csv', 'tsv', 'browser' ],
							key='astro_open_science_format' )
				open_science_btn_c1, open_science_btn_c2 = st.columns( 2 )
				with open_science_btn_c1:
					if st.button( label='Run', icon='🏃', key='astro_open_science_run',
							use_container_width=True ):
						try:
							service = OpenScience( )
							result = service.fetch( mode=open_science_mode, query=open_science_query,
								accession=open_science_accession, format_value=open_science_format,
								time=int( open_science_timeout ) )
							st.session_state[ 'astro_last_source' ] = 'NASA Open Science Data'
							st.session_state[ 'astro_last_result' ] = normalize( result ) or { }
							st.session_state[ 'astro_last_latitude' ] = None
							st.session_state[ 'astro_last_longitude' ] = None
							st.session_state[ 'astro_last_url' ] = ''
							st.success( 'NASA Open Science Data request completed.' )
						except Exception as ex:
							st.error( f'NASA Open Science Data request failed: {ex}' )
				with open_science_btn_c2:
					if st.button( label='Clear', icon='🧹', key='astro_open_science_clear',
							use_container_width=True ):
						st.session_state[ 'astro_last_source' ] = ''
						st.session_state[ 'astro_last_result' ] = { }
						st.session_state[ 'astro_last_latitude' ] = None
						st.session_state[ 'astro_last_longitude' ] = None
						st.session_state[ 'astro_last_url' ] = ''
				st.divider( )
				render_source_processing_controls( 'astro', 'astro_last_result',
					'astro_last_source', 'NASA Open Science Data', 'astro_open_science' )
		
		with astro_c2:
			render_mode_document_tabs( 'astro', '📄 Loaded' )
			
# ==============================================================================
# CELESTIAL MAP MODE
# ==============================================================================
elif mode == 'Celestial Map':
	left, center, right = st.columns( [ 0.025, 0.95, 0.025 ] )
	with center:
		st.subheader( 'Celestial Map' )
		st.divider( )
		global_location = get_global_location_default( )
		location_state = get_location_state( )
		has_global_coords = has_valid_global_coordinates( )
		status_c1, status_c2, status_c3 = st.columns( 3, border=True )
		status_c1.metric( 'Location', compose_location_from_state( ) or global_location )
		status_c2.metric( 'Latitude', f'{float( location_state[ "latitude" ] ):.4f}' )
		status_c3.metric( 'Longitude', f'{float( location_state[ "longitude" ] ):.4f}' )
		blue_divider( )
		control_c1, control_c2 = st.columns( [ 0.50, 0.50 ], border=True )
		with control_c1:
			use_global_coordinates = st.checkbox( 'Use User-Location',
				value=has_global_coords, key='celestial_use_global_coordinates' )
			
			if use_global_coordinates:
				celestial_latitude = float( location_state[ 'latitude' ] )
				celestial_longitude = float( location_state[ 'longitude' ] )
				coord_c1, coord_c2 = st.columns( 2 )
				with coord_c1:
					st.number_input( 'Latitude', value=celestial_latitude, format='%.6f',
						key='celestial_global_latitude_display', disabled=True )
				
				with coord_c2:
					st.number_input( 'Longitude', value=celestial_longitude, format='%.6f',
						key='celestial_global_longitude_display', disabled=True )
			
			else:
				manual_default_latitude = ( float( location_state[ 'latitude' ] )
						if has_global_coords
						else get_global_latitude_default( ) )
				
				manual_default_longitude = (
						float( location_state[ 'longitude' ] )
						if has_global_coords
						else get_global_longitude_default( ) )
				
				coord_c1, coord_c2 = st.columns( 2 )
				with coord_c1:
					celestial_latitude = st.number_input( 'Latitude',
						value=manual_default_latitude,
						format='%.6f', key='celestial_manual_latitude' )
				
				with coord_c2:
					celestial_longitude = st.number_input( 'Longitude',
						value=manual_default_longitude, format='%.6f',
						key='celestial_manual_longitude' )
		
		with control_c2:
			celestial_location = st.text_input( 'Location Label',
				value=compose_location_from_state( ) or global_location,
				key='celestial_location_label' )
			
			celestial_zoom = st.slider( 'Location Picker Zoom', min_value=1, max_value=18,
				value=int( st.session_state.get( 'zoom', 8 ) or 8 ),
				key='celestial_location_picker_zoom' )
			
			save_coordinates = st.checkbox( 'Save Coordinates to Global State', value=True,
				key='celestial_save_coordinates' )
		
		if not has_valid_coordinates( celestial_latitude, celestial_longitude ):
			st.warning( 'Provide valid coordinates before rendering the Celestial Map.' )
			st.stop( )
		
		if save_coordinates:
			set_location_state( location=celestial_location,
				description='Celestial Map observer location',
				latitude=float( celestial_latitude ), longitude=float( celestial_longitude ) )
			st.session_state[ 'zoom' ] = int( celestial_zoom )
		
		blue_divider( )
		render_celestial_map( asset_root='assets/starmap', height=1400,
			latitude=float( celestial_latitude ), longitude=float( celestial_longitude ),
			location=celestial_location, zoom=int( celestial_zoom ) )
		
# ==============================================================================
# DEMOGRAPHIC MODE
# ==============================================================================
elif mode == 'Public Health':
	st.subheader( f'🩺 Population & Public Health' )
	st.divider( )
	demographic_location = get_global_location_default( )
	demographic_state = get_location_state( )
	demo_c1, demo_c2, demo_c3 = st.columns( 3, border=True )
	demo_c1.metric( 'Location', demographic_location )
	demo_c2.metric( 'Latitude', f'{float( demographic_state[ "latitude" ] ):.4f}' )
	demo_c3.metric( 'Longitude', f'{float( demographic_state[ "longitude" ] ):.4f}' )
	blue_divider( )
	left, right = st.columns( [ 0.4, 0.6 ], gap='xxsmall', border=True )
	if 'demographic_active_source' not in st.session_state:
		st.session_state[ 'demographic_active_source' ] = ''
	
	with left:
		
		# ---- Expander U.S. Census Bureau
		with st.expander( label='U.S. Census Bureau (ACS)', icon='📊', expanded=False ):
			CENSUS_MODES = [ 'variables', 'data' ]
			st.caption( 'API', help=cfg.CENSUS_DATA )
			
			def _clear_census_state( ) -> None:
				st.session_state[ 'census_clear_request' ] = True
			
			def _validate_census_year( value: object ) -> str:
				text = str( value or '' ).strip( )
				if not re.fullmatch( r'\d{4}', text ):
					raise ValueError( 'Year must be a four-digit Census API vintage year.' )
				
				return text
			
			def _validate_census_dataset( value: object ) -> str:
				text = str( value or '' ).strip( ).strip( '/' )
				if not text:
					raise ValueError( 'Dataset is required.' )
				
				if not re.fullmatch( r'[A-Za-z0-9_\-/]+', text ):
					raise ValueError( 'Dataset may only contain letters, numbers, underscores, '
					                  'hyphens, '
					                  'and forward slashes.' )
				
				return text
			
			def _validate_census_fields( value: object ) -> str:
				text = str( value or '' ).strip( )
				
				if not text:
					raise ValueError( 'Fields are required for Census data mode.' )
				
				fields = [ item.strip( ) for item in text.split( ',' ) if item.strip( ) ]
				
				if not fields:
					raise ValueError( 'Fields are required for Census data mode.' )
				
				for field in fields:
					if not re.fullmatch( r'[A-Za-z0-9_]+', field ):
						raise ValueError( f'Invalid Census field name: {field}' )
				
				return ','.join( fields )
			
			def _validate_census_geography_clause( name: str,
			                                       value: object, required: bool = False ) -> str:
				text = str( value or '' ).strip( )
				
				if not text:
					if required:
						raise ValueError( f'{name} is required.' )
					return ''
				
				if ':' not in text:
					raise ValueError( f'{name} must use Census geography syntax such as state:*.' )
				
				return text
			
			if 'census_results' not in st.session_state:
				st.session_state[ 'census_results' ] = { }
			
			if 'census_clear_request' not in st.session_state:
				st.session_state[ 'census_clear_request' ] = False
			
			if st.session_state.get( 'census_mode', 'variables' ) not in CENSUS_MODES:
				st.session_state[ 'census_mode' ] = 'variables'
			
			if 'census_year' not in st.session_state:
				st.session_state[ 'census_year' ] = '2022'
			
			if 'census_dataset' not in st.session_state:
				st.session_state[ 'census_dataset' ] = 'acs/acs5'
			
			if 'census_fields' not in st.session_state:
				st.session_state[ 'census_fields' ] = 'NAME,B01001_001E'
			
			if 'census_for' not in st.session_state:
				st.session_state[ 'census_for' ] = 'state:*'
			
			if 'census_in' not in st.session_state:
				st.session_state[ 'census_in' ] = ''
			
			if 'census_predicates' not in st.session_state:
				st.session_state[ 'census_predicates' ] = ''
			
			if 'census_timeout' not in st.session_state:
				st.session_state[ 'census_timeout' ] = 20
			
			if st.session_state.get( 'census_clear_request', False ):
				st.session_state[ 'census_mode' ] = 'variables'
				st.session_state[ 'census_year' ] = '2022'
				st.session_state[ 'census_dataset' ] = 'acs/acs5'
				st.session_state[ 'census_fields' ] = 'NAME,B01001_001E'
				st.session_state[ 'census_for' ] = 'state:*'
				st.session_state[ 'census_in' ] = ''
				st.session_state[ 'census_predicates' ] = ''
				st.session_state[ 'census_timeout' ] = 20
				st.session_state[ 'census_results' ] = { }
				st.session_state[ 'census_clear_request' ] = False
			
			census_mode = st.selectbox( 'Mode', options=CENSUS_MODES,
				index=CENSUS_MODES.index( st.session_state.get( 'census_mode', 'variables' ) ),
				key='census_mode', help=('variables = dataset variable metadata; '
				                         'data = tabular Census query using get/for/in.') )
			
			census_year = st.text_input( 'Year',
				value=st.session_state.get( 'census_year', '2022' ), key='census_year',
				placeholder='2022' )
			
			census_dataset = st.text_input( 'Dataset',
				value=st.session_state.get( 'census_dataset', 'acs/acs5' ), key='census_dataset',
				placeholder='acs/acs5' )
			
			census_fields = st.text_area( 'Fields (get)',
				value=st.session_state.get( 'census_fields', 'NAME,B01001_001E' ), height=90,
				key='census_fields', placeholder='NAME,B01001_001E',
				disabled=(census_mode != 'data') )
			
			c1, c2 = st.columns( 2 )
			with c1:
				census_for = st.text_input( 'For',
					value=st.session_state.get( 'census_for', 'state:*' ), key='census_for',
					placeholder='state:*', disabled=(census_mode != 'data') )
			
			with c2:
				census_in = st.text_input( 'In', value=st.session_state.get( 'census_in', '' ),
					key='census_in', placeholder='state:24', disabled=(census_mode != 'data') )
			
			census_predicates = st.text_area( 'Predicates',
				value=st.session_state.get( 'census_predicates', '' ), height=90,
				key='census_predicates', placeholder='SEX=1\nAGE=15',
				disabled=(census_mode != 'data'),
				help='Optional newline-delimited key=value filters.' )
			
			census_timeout = st.number_input( 'Timeout', min_value=1, max_value=120,
				value=int( st.session_state.get( 'census_timeout', 20 ) ), step=1,
				key='census_timeout' )
			
			st.caption( 'Examples: dataset = acs/acs5, fields = NAME,B01001_001E, '
			            'for = state:*' )
			
			b1, b2 = st.columns( 2 )
			with b1:
				census_submit = st.button( 'Submit', key='census_submit', width='stretch' )
			
			with b2:
				st.button( 'Clear', key='census_clear', on_click=_clear_census_state,
					width='stretch' )
			
			if census_submit:
				st.session_state[ 'demographic_active_source' ] = 'u_s_census_bureau'
			
			render_source_processing_controls( 'demographic', 'census_results', 
				'demographic_active_source', 'u_s_census_bureau', 'api_u_s_census_bureau' )
		
		# ---- Expander CDC Open Data Portal
		with st.expander( label='CDC Open Data', icon='🩺', expanded=False ):
			st.caption( 'API', help=cfg.CDC_SOCRATA )
			SOCRATA_MODES = [ 'rows', 'metadata' ]
			SOCRATA_CDC_DOMAINS = [ 'data.cdc.gov', 'chronicdata.cdc.gov' ]
			
			def _clear_socrata_state( ) -> None:
				st.session_state[ 'socrata_clear_request' ] = True
			
			def _validate_socrata_dataset_id( value: object ) -> str:
				text = str( value or '' ).strip( ).replace( '.json', '' ).strip( '/' )
				
				if not text:
					raise ValueError( 'Dataset ID is required.' )
				
				if not re.fullmatch( r'[a-zA-Z0-9]{4}-[a-zA-Z0-9]{4}', text ):
					raise ValueError( 'Dataset ID must use the Socrata four-by-four format, '
					                  'such as q8xq-ygsk.' )
				
				return text.lower( )
			
			if 'socrata_results' not in st.session_state:
				st.session_state[ 'socrata_results' ] = { }
			
			if 'socrata_clear_request' not in st.session_state:
				st.session_state[ 'socrata_clear_request' ] = False
			
			if st.session_state.get( 'socrata_mode', 'rows' ) not in SOCRATA_MODES:
				st.session_state[ 'socrata_mode' ] = 'rows'
			
			if st.session_state.get( 'socrata_domain', 'data.cdc.gov' ) not in SOCRATA_CDC_DOMAINS:
				st.session_state[ 'socrata_domain' ] = 'data.cdc.gov'
			
			if 'socrata_dataset_id' not in st.session_state:
				st.session_state[ 'socrata_dataset_id' ] = 'q8xq-ygsk'
			
			if 'socrata_select' not in st.session_state:
				st.session_state[ 'socrata_select' ] = ''
			
			if 'socrata_where' not in st.session_state:
				st.session_state[ 'socrata_where' ] = ''
			
			if 'socrata_order' not in st.session_state:
				st.session_state[ 'socrata_order' ] = ''
			
			if 'socrata_group' not in st.session_state:
				st.session_state[ 'socrata_group' ] = ''
			
			if 'socrata_limit' not in st.session_state:
				st.session_state[ 'socrata_limit' ] = 25
			
			if 'socrata_offset' not in st.session_state:
				st.session_state[ 'socrata_offset' ] = 0
			
			if 'socrata_timeout' not in st.session_state:
				st.session_state[ 'socrata_timeout' ] = 20
			
			if st.session_state.get( 'socrata_clear_request', False ):
				st.session_state[ 'socrata_mode' ] = 'rows'
				st.session_state[ 'socrata_domain' ] = 'data.cdc.gov'
				st.session_state[ 'socrata_dataset_id' ] = 'q8xq-ygsk'
				st.session_state[ 'socrata_select' ] = ''
				st.session_state[ 'socrata_where' ] = ''
				st.session_state[ 'socrata_order' ] = ''
				st.session_state[ 'socrata_group' ] = ''
				st.session_state[ 'socrata_limit' ] = 25
				st.session_state[ 'socrata_offset' ] = 0
				st.session_state[ 'socrata_timeout' ] = 20
				st.session_state[ 'socrata_results' ] = { }
				st.session_state[ 'socrata_clear_request' ] = False
			
			socrata_mode = st.selectbox( 'Mode', options=SOCRATA_MODES,
				index=SOCRATA_MODES.index( st.session_state.get( 'socrata_mode', 'rows' ) ),
				key='socrata_mode', help='rows = '
				                         'query '
				                         'dataset rows; metadata = inspect dataset metadata.' )
			
			socrata_domain = st.selectbox( 'Domain', options=SOCRATA_CDC_DOMAINS,
				index=SOCRATA_CDC_DOMAINS.index(
					st.session_state.get( 'socrata_domain', 'data.cdc.gov' ) ),
				key='socrata_domain', help='CDC Socrata portal domain.' )
			
			socrata_dataset_id = st.text_input( 'Dataset ID',
				value=st.session_state.get( 'socrata_dataset_id', 'q8xq-ygsk' ),
				key='socrata_dataset_id', placeholder='q8xq-ygsk' )
			
			socrata_select = st.text_area( 'Select',
				value=st.session_state.get( 'socrata_select', '' ), height=80, key='socrata_select',
				placeholder='locationname,datavaluetype,'
				            'datavalue', disabled=(socrata_mode != 'rows') )
			
			socrata_where = st.text_area( 'Where',
				value=st.session_state.get( 'socrata_where', '' ), height=100, key='socrata_where',
				placeholder="year = '2020'", disabled=(socrata_mode != 'rows') )
			
			c1, c2 = st.columns( 2 )
			with c1:
				socrata_order = st.text_input( 'Order',
					value=st.session_state.get( 'socrata_order', '' ), key='socrata_order',
					placeholder='locationname ASC', disabled=(socrata_mode != 'rows') )
			
			with c2:
				socrata_group = st.text_input( 'Group',
					value=st.session_state.get( 'socrata_group', '' ), key='socrata_group',
					placeholder='locationname', disabled=(socrata_mode != 'rows') )
			
			c3, c4, c5 = st.columns( 3 )
			with c3:
				socrata_limit = st.number_input( 'Limit', min_value=1, max_value=50000,
					value=int( st.session_state.get( 'socrata_limit', 25 ) ), step=1,
					key='socrata_limit', disabled=(socrata_mode != 'rows'),
					help='Socrata SODA 2.0 endpoints allow $limit '
					     'values up to 50,000.' )
			
			with c4:
				socrata_offset = st.number_input( 'Offset', min_value=0, max_value=1000000,
					value=int( st.session_state.get( 'socrata_offset', 0 ) ), step=1,
					key='socrata_offset', disabled=(socrata_mode != 'rows') )
			
			with c5:
				socrata_timeout = st.number_input( 'Timeout', min_value=1, max_value=120,
					value=int( st.session_state.get( 'socrata_timeout', 20 ) ), step=1,
					key='socrata_timeout' )
			
			st.caption( 'Example dataset: q8xq-ygsk on data.cdc.gov. '
			            'Use SoQL clauses for select, where, order, and group.' )
			
			b1, b2 = st.columns( 2 )
			with b1:
				socrata_submit = st.button( 'Submit', key='socrata_submit', width='stretch' )
			
			with b2:
				st.button( 'Clear', key='socrata_clear', on_click=_clear_socrata_state,
					width='stretch' )
			
			if socrata_submit:
				st.session_state[ 'demographic_active_source' ] = 'cdc_socrata'
			
			render_source_processing_controls( 'demographic', 'socrata_results',
				'demographic_active_source', 'cdc_socrata', 'api_cdc_socrata' )
		
		# ---- Expander US Health Data
		with st.expander( label='U.S. Health', icon='🏥', expanded=False ):
			st.caption( 'API', help=cfg.US_HEALTH_DATA )
			HEALTHDATA_MODES = [ 'rows', 'metadata' ]
			HEALTHDATA_DOMAINS = [ 'healthdata.gov' ]
			
			def _clear_healthdata_state( ) -> None:
				st.session_state[ 'healthdata_clear_request' ] = True
			
			def _validate_healthdata_dataset_id( value: object ) -> str:
				text = str( value or '' ).strip( ).replace( '.json', '' ).strip( '/' )
				
				if not text:
					raise ValueError( 'Dataset ID is required.' )
				
				if not re.fullmatch( r'[a-zA-Z0-9]{4}-[a-zA-Z0-9]{4}', text ):
					raise ValueError( 'Dataset ID must use the Socrata four-by-four format, '
					                  'such as abcd-1234.' )
				
				return text.lower( )
			
			if 'healthdata_results' not in st.session_state:
				st.session_state[ 'healthdata_results' ] = { }
			
			if 'healthdata_clear_request' not in st.session_state:
				st.session_state[ 'healthdata_clear_request' ] = False
			
			if st.session_state.get( 'healthdata_mode', 'rows' ) not in HEALTHDATA_MODES:
				st.session_state[ 'healthdata_mode' ] = 'rows'
			
			if st.session_state.get( 'healthdata_domain',
					'healthdata.gov' ) not in HEALTHDATA_DOMAINS:
				st.session_state[ 'healthdata_domain' ] = 'healthdata.gov'
			
			if 'healthdata_dataset_id' not in st.session_state:
				st.session_state[ 'healthdata_dataset_id' ] = ''
			
			if 'healthdata_select' not in st.session_state:
				st.session_state[ 'healthdata_select' ] = ''
			
			if 'healthdata_where' not in st.session_state:
				st.session_state[ 'healthdata_where' ] = ''
			
			if 'healthdata_order' not in st.session_state:
				st.session_state[ 'healthdata_order' ] = ''
			
			if 'healthdata_group' not in st.session_state:
				st.session_state[ 'healthdata_group' ] = ''
			
			if 'healthdata_limit' not in st.session_state:
				st.session_state[ 'healthdata_limit' ] = 25
			
			if 'healthdata_offset' not in st.session_state:
				st.session_state[ 'healthdata_offset' ] = 0
			
			if 'healthdata_timeout' not in st.session_state:
				st.session_state[ 'healthdata_timeout' ] = 20
			
			if st.session_state.get( 'healthdata_clear_request', False ):
				st.session_state[ 'healthdata_mode' ] = 'rows'
				st.session_state[ 'healthdata_domain' ] = 'healthdata.gov'
				st.session_state[ 'healthdata_dataset_id' ] = ''
				st.session_state[ 'healthdata_select' ] = ''
				st.session_state[ 'healthdata_where' ] = ''
				st.session_state[ 'healthdata_order' ] = ''
				st.session_state[ 'healthdata_group' ] = ''
				st.session_state[ 'healthdata_limit' ] = 25
				st.session_state[ 'healthdata_offset' ] = 0
				st.session_state[ 'healthdata_timeout' ] = 20
				st.session_state[ 'healthdata_results' ] = { }
				st.session_state[ 'healthdata_clear_request' ] = False
			
			healthdata_mode = st.selectbox( 'Mode', options=HEALTHDATA_MODES,
				index=HEALTHDATA_MODES.index( st.session_state.get( 'healthdata_mode', 'rows' ) ),
				key='healthdata_mode', help='rows = query dataset rows; metadata = inspect dataset '
				                            'metadata.' )
			
			healthdata_domain = st.selectbox( 'Domain', options=HEALTHDATA_DOMAINS,
				index=HEALTHDATA_DOMAINS.index(
					st.session_state.get( 'healthdata_domain', 'healthdata.gov' ) ),
				key='healthdata_domain', help='HealthData.gov Socrata '
				                              'portal domain.' )
			
			healthdata_dataset_id = st.text_input( 'Dataset ID',
				value=st.session_state.get( 'healthdata_dataset_id', '' ),
				key='healthdata_dataset_id', placeholder='abcd-1234' )
			
			healthdata_select = st.text_area( 'Select',
				value=st.session_state.get( 'healthdata_select', '' ), height=80,
				key='healthdata_select', placeholder='column1,column2',
				disabled=(healthdata_mode != 'rows') )
			
			healthdata_where = st.text_area( 'Where',
				value=st.session_state.get( 'healthdata_where', '' ), height=100,
				key='healthdata_where', placeholder="year = '2024'", disabled=(healthdata_mode != 'rows') )
			
			c1, c2 = st.columns( 2 )
			with c1:
				healthdata_order = st.text_input( 'Order',
					value=st.session_state.get( 'healthdata_order', '' ), key='healthdata_order',
					placeholder='column1 ASC', disabled=(healthdata_mode != 'rows') )
			
			with c2:
				healthdata_group = st.text_input( 'Group',
					value=st.session_state.get( 'healthdata_group', '' ), key='healthdata_group',
					placeholder='column1', disabled=(healthdata_mode != 'rows') )
			
			c3, c4, c5 = st.columns( 3 )
			with c3:
				healthdata_limit = st.number_input( 'Limit', min_value=1, max_value=50000,
					value=int( st.session_state.get( 'healthdata_limit', 25 ) ), step=1,
					key='healthdata_limit', disabled=(healthdata_mode != 'rows'),
					help='Socrata SODA 2.0 endpoints allow $limit values up to 50,000.' )
			
			with c4:
				healthdata_offset = st.number_input( 'Offset', min_value=0, max_value=1000000,
					value=int( st.session_state.get( 'healthdata_offset', 0 ) ), step=1,
					key='healthdata_offset', disabled=(healthdata_mode != 'rows') )
			
			with c5:
				healthdata_timeout = st.number_input( 'Timeout', min_value=1, max_value=120,
					value=int( st.session_state.get( 'healthdata_timeout', 20 ) ), step=1,
					key='healthdata_timeout' )
			
			st.caption( 'HealthData.gov exposes open API access through Socrata. '
			            'Use SoQL-style clauses for select, where, order, and group.' )
			
			b1, b2 = st.columns( 2 )
			with b1:
				healthdata_submit = st.button( 'Submit', key='healthdata_submit', width='stretch' )
			
			with b2:
				st.button( label='Clear', key='healthdata_clear', on_click=_clear_healthdata_state,
					width='stretch' )
			
			if healthdata_submit:
				st.session_state[ 'demographic_active_source' ] = 'u_s_health'
			
			render_source_processing_controls( 'demographic', 'healthdata_results',
				'demographic_active_source', 'u_s_health', 'api_u_s_health' )
		
		# ---- Expander WHO Global Health
		with st.expander( label='WHO Global', icon='🌍', expanded=False ):
			st.caption( 'API', help=cfg.WHO_DATA )
			WHO_MODES = [ 'indicator_registry', 'athena' ]
			WHO_QUERY_PRESETS = [ 'Indicator', 'Dimension', 'DIMENSION/COUNTRY/DimensionValues',
			                      'DIMENSION/REGION', 'WHOSIS_000001', 'Custom...' ]
			
			WHO_FORMATS = [ 'json', 'xml', 'csv', 'csv&profile=text', 'csv&profile=verbose' ]
			
			def _clear_who_state( ) -> None:
				st.session_state[ 'who_clear_request' ] = True
			
			def _validate_who_query_path( value: object ) -> str:
				text = str( value or '' ).strip( ).lstrip( '/' )
				
				if not text:
					raise ValueError( 'Query Path is required for WHO Athena mode.' )
				
				if text.startswith( 'http://' ) or text.startswith( 'https://' ):
					raise ValueError( 'Query Path must be a path segment only, not a full URL.' )
				
				if '..' in text:
					raise ValueError( 'Query Path cannot contain parent-directory markers.' )
				
				if not re.fullmatch( r"[A-Za-z0-9_\-/$(),.'% =]+(?:\?.*)?", text ):
					raise ValueError( 'Query Path contains unsupported characters for this '
					                  'request.' )
				
				return text
			
			if 'who_results' not in st.session_state:
				st.session_state[ 'who_results' ] = { }
			
			if 'who_clear_request' not in st.session_state:
				st.session_state[ 'who_clear_request' ] = False
			
			if st.session_state.get( 'who_mode', 'indicator_registry' ) not in WHO_MODES:
				st.session_state[ 'who_mode' ] = 'indicator_registry'
			
			if 'who_query_path' not in st.session_state:
				st.session_state[ 'who_query_path' ] = ''
			
			if st.session_state.get( 'who_query_path', '' ) in WHO_QUERY_PRESETS:
				default_who_query_choice = st.session_state.get( 'who_query_path', 'Indicator' )
			elif str( st.session_state.get( 'who_query_path', '' ) ).strip( ):
				default_who_query_choice = 'Custom...'
			else:
				default_who_query_choice = 'Indicator'
			
			if 'who_query_choice' not in st.session_state:
				st.session_state[ 'who_query_choice' ] = default_who_query_choice
			
			if st.session_state.get( 'who_query_choice', 'Indicator' ) not in WHO_QUERY_PRESETS:
				st.session_state[ 'who_query_choice' ] = default_who_query_choice
			
			if 'who_custom_query_path' not in st.session_state:
				st.session_state[ 'who_custom_query_path' ] = (
						'' if default_who_query_choice != 'Custom...' else st.session_state.get(
							'who_query_path', '' ))
			
			if st.session_state.get( 'who_format', 'json' ) not in WHO_FORMATS:
				st.session_state[ 'who_format' ] = 'json'
			
			if 'who_timeout' not in st.session_state:
				st.session_state[ 'who_timeout' ] = 20
			
			if st.session_state.get( 'who_clear_request', False ):
				st.session_state[ 'who_mode' ] = 'indicator_registry'
				st.session_state[ 'who_query_path' ] = ''
				st.session_state[ 'who_query_choice' ] = 'Indicator'
				st.session_state[ 'who_custom_query_path' ] = ''
				st.session_state[ 'who_format' ] = 'json'
				st.session_state[ 'who_timeout' ] = 20
				st.session_state[ 'who_results' ] = { }
				st.session_state[ 'who_clear_request' ] = False
			
			who_mode = st.selectbox( 'Mode', options=WHO_MODES,
				index=WHO_MODES.index( st.session_state.get( 'who_mode', 'indicator_registry' ) ),
				key='who_mode', help=('indicator_registry = WHO metadata landing content; '
				                      'athena = configurable WHO GHO query path.') )
			
			who_query_choice = st.selectbox( 'Query Path Preset', options=WHO_QUERY_PRESETS,
				index=WHO_QUERY_PRESETS.index(
					st.session_state.get( 'who_query_choice', 'Indicator' ) ),
				key='who_query_choice', disabled=(who_mode != 'athena'),
				help='Common WHO GHO OData query paths.' )
			
			who_custom_query_path = st.text_area( 'Custom Query Path',
				value=st.session_state.get( 'who_custom_query_path', '' ), height=100,
				key='who_custom_query_path', placeholder="WHOSIS_000001?$filter=Dim1 eq 'MLE'",
				disabled=(who_mode != 'athena' or who_query_choice != 'Custom...'),
				help='Path appended '
				     'after the WHO '
				     'GHO API base '
				     'endpoint.' )
			
			who_format = st.selectbox( 'Format', options=WHO_FORMATS,
				index=WHO_FORMATS.index( st.session_state.get( 'who_format', 'json' ) ),
				key='who_format', disabled=(who_mode != 'athena') )
			
			who_timeout = st.number_input( 'Timeout', min_value=1, max_value=120,
				value=int( st.session_state.get( 'who_timeout', 20 ) ), step=1, key='who_timeout' )
			
			st.caption( 'WHO supports GHO OData paths such as Indicator, Dimension, '
			            'DIMENSION/COUNTRY/DimensionValues, and direct indicator-code '
			            'queries.' )
			
			b1, b2 = st.columns( 2 )
			with b1:
				who_submit = st.button( 'Submit', key='who_submit', width='stretch' )
			
			with b2:
				st.button( 'Clear', key='who_clear', on_click=_clear_who_state, width='stretch' )
			
			if who_submit:
				st.session_state[ 'demographic_active_source' ] = 'who_global'
			
			render_source_processing_controls( 'demographic', 'who_results',
				'demographic_active_source', 'who_global', 'api_who_global' )
		
		# ---- Expander United Nations Data
		with st.expander( label='United Nations', icon='🇺🇳', expanded=False ):
			st.caption( 'API', help=cfg.UN_DATA )
			UN_MODES = [ 'datasets', 'sdmx_query' ]
			UN_QUERY_PRESETS = [ 'dataflow', 'datastructure', 'codelist', 'conceptscheme',
			                     'dataflow/all/all/latest', 'datastructure/all/all/latest',
			                     'codelist/all/all/latest', 'conceptscheme/all/all/latest',
			                     'Custom...' ]
			
			def _clear_un_state( ) -> None:
				st.session_state[ 'un_clear_request' ] = True
			
			def _validate_un_query_path( value: object ) -> str:
				text = str( value or '' ).strip( ).lstrip( '/' )
				
				if not text:
					raise ValueError( 'Query Path is required for sdmx_query mode.' )
				
				if text.startswith( 'http://' ) or text.startswith( 'https://' ):
					raise ValueError( 'Query Path must be a path segment only, not a full URL.' )
				
				if '..' in text:
					raise ValueError( 'Query Path cannot contain parent-directory markers.' )
				
				if not re.fullmatch( r'[A-Za-z0-9_\-./(),:*?=&%]+', text ):
					raise ValueError( 'Query Path contains unsupported characters for a UNdata '
					                  'REST request.' )
				
				return text
			
			if 'un_results' not in st.session_state:
				st.session_state[ 'un_results' ] = { }
			
			if 'un_clear_request' not in st.session_state:
				st.session_state[ 'un_clear_request' ] = False
			
			if st.session_state.get( 'un_mode', 'datasets' ) not in UN_MODES:
				st.session_state[ 'un_mode' ] = 'datasets'
			
			if 'un_query_path' not in st.session_state:
				st.session_state[ 'un_query_path' ] = ''
			
			if st.session_state.get( 'un_query_path', '' ) in UN_QUERY_PRESETS:
				default_un_query_choice = st.session_state.get( 'un_query_path', 'dataflow' )
			elif str( st.session_state.get( 'un_query_path', '' ) ).strip( ):
				default_un_query_choice = 'Custom...'
			else:
				default_un_query_choice = 'dataflow'
			
			if 'un_query_choice' not in st.session_state:
				st.session_state[ 'un_query_choice' ] = default_un_query_choice
			
			if st.session_state.get( 'un_query_choice', 'dataflow' ) not in UN_QUERY_PRESETS:
				st.session_state[ 'un_query_choice' ] = default_un_query_choice
			
			if 'un_custom_query_path' not in st.session_state:
				st.session_state[ 'un_custom_query_path' ] = (
						'' if default_un_query_choice != 'Custom...' else st.session_state.get(
							'un_query_path', '' ))
			
			if 'un_timeout' not in st.session_state:
				st.session_state[ 'un_timeout' ] = 20
			
			if st.session_state.get( 'un_clear_request', False ):
				st.session_state[ 'un_mode' ] = 'datasets'
				st.session_state[ 'un_query_path' ] = ''
				st.session_state[ 'un_query_choice' ] = 'dataflow'
				st.session_state[ 'un_custom_query_path' ] = ''
				st.session_state[ 'un_timeout' ] = 20
				st.session_state[ 'un_results' ] = { }
				st.session_state[ 'un_clear_request' ] = False
			
			un_mode = st.selectbox( 'Mode', options=UN_MODES,
				index=UN_MODES.index( st.session_state.get( 'un_mode', 'datasets' ) ),
				key='un_mode', help=('datasets = UNdata dataset catalog landing content; '
				                     'sdmx_query = direct REST SDMX query path.') )
			
			un_query_choice = st.selectbox( 'Query Path Preset', options=UN_QUERY_PRESETS,
				index=UN_QUERY_PRESETS.index(
					st.session_state.get( 'un_query_choice', 'dataflow' ) ), key='un_query_choice',
				disabled=(un_mode != 'sdmx_query'), help='Common UNdata SDMX REST artifact paths.' )
			
			un_custom_query_path = st.text_area( 'Custom Query Path',
				value=st.session_state.get( 'un_custom_query_path', '' ), height=120,
				key='un_custom_query_path', placeholder='data/DF_SDG_GLH/..SI_POV_DAY1...........?',
				disabled=(un_mode != 'sdmx_query' or un_query_choice != 'Custom...'), help='Path '
				                                                                           'appended '
				                                                                           'after '
				                                                                           'https://data.un.org/WS/rest/' )
			
			un_timeout = st.number_input( 'Timeout', min_value=1, max_value=120,
				value=int( st.session_state.get( 'un_timeout', 20 ) ), step=1, key='un_timeout' )
			
			st.caption( 'UNdata exposes SDMX REST artifacts such as dataflow, datastructure, '
			            'codelist, and conceptscheme. Use Custom for dataset-specific paths.' )
			
			b1, b2 = st.columns( 2 )
			with b1:
				un_submit = st.button( 'Submit', key='un_submit', width='stretch' )
			
			with b2:
				st.button( 'Clear', key='un_clear', on_click=_clear_un_state, width='stretch' )
			
			if un_submit:
				st.session_state[ 'demographic_active_source' ] = 'united_nations'
			
			render_source_processing_controls( 'demographic', 'un_results', 'demographic_active_source', 'united_nations', 'api_united_nations' )
		
		# ---- Expander World Population
		with st.expander( label='World Population', icon='👥', expanded=False ):
			st.caption( 'API', help=cfg.WORLD_POP_DATA )
			WORLDPOP_MODES = [ 'catalog', 'search', 'raster_metadata' ]
			WORLDPOP_ASSET_PRESETS = [ 'data/pop', 'data/pop/wpgp', 'data/pop/wpgp?iso3=GHA',
			                           'data/pop/wpgp?iso3=AUS', 'data/pop/wpgp?iso3=USA',
			                           'data/pop/wpgp?iso3=GBR', 'data/pop/wpgp?iso3=NGA',
			                           'data/pop/wpgp?iso3=KEN', 'data/pop/wpgp?iso3=IND',
			                           'data/pop/wpgp?iso3=BRA', 'Custom...' ]
			
			def _clear_worldpop_state( ) -> None:
				st.session_state[ 'worldpop_clear_request' ] = True
			
			def _validate_worldpop_query( value: object ) -> str:
				text = str( value or '' ).strip( )
				
				if not text:
					raise ValueError( 'Query is required for World Population search mode.' )
				
				return text
			
			def _validate_worldpop_asset_path( value: object ) -> str:
				text = str( value or '' ).strip( ).lstrip( '/' )
				
				if not text:
					raise ValueError( 'Asset Path is required for raster_metadata mode.' )
				
				if text.startswith( 'http://' ) or text.startswith( 'https://' ):
					raise ValueError( 'Asset Path must be a path segment only, not a full URL.' )
				
				if '..' in text:
					raise ValueError( 'Asset Path cannot contain parent-directory markers.' )
				
				if not re.fullmatch( r'[A-Za-z0-9_\-./?=&%]+', text ):
					raise ValueError( 'Asset Path contains unsupported characters for a WorldPop '
					                  'request.' )
				
				return text
			
			if 'worldpop_results' not in st.session_state:
				st.session_state[ 'worldpop_results' ] = { }
			
			if 'worldpop_clear_request' not in st.session_state:
				st.session_state[ 'worldpop_clear_request' ] = False
			
			if st.session_state.get( 'worldpop_mode', 'catalog' ) not in WORLDPOP_MODES:
				st.session_state[ 'worldpop_mode' ] = 'catalog'
			
			if 'worldpop_query' not in st.session_state:
				st.session_state[ 'worldpop_query' ] = ''
			
			if 'worldpop_asset_path' not in st.session_state:
				st.session_state[ 'worldpop_asset_path' ] = ''
			
			if st.session_state.get( 'worldpop_asset_path', '' ) in WORLDPOP_ASSET_PRESETS:
				default_asset_choice = st.session_state.get( 'worldpop_asset_path',
					'data/pop/wpgp?iso3=GHA' )
			elif str( st.session_state.get( 'worldpop_asset_path', '' ) ).strip( ):
				default_asset_choice = 'Custom...'
			else:
				default_asset_choice = 'data/pop/wpgp?iso3=GHA'
			
			if 'worldpop_asset_choice' not in st.session_state:
				st.session_state[ 'worldpop_asset_choice' ] = default_asset_choice
			
			if st.session_state.get( 'worldpop_asset_choice',
					'data/pop/wpgp?iso3=GHA' ) not in WORLDPOP_ASSET_PRESETS:
				st.session_state[ 'worldpop_asset_choice' ] = default_asset_choice
			
			if 'worldpop_custom_asset_path' not in st.session_state:
				st.session_state[ 'worldpop_custom_asset_path' ] = (
						'' if default_asset_choice != 'Custom...' else st.session_state.get(
							'worldpop_asset_path', '' ))
			
			if 'worldpop_page' not in st.session_state:
				st.session_state[ 'worldpop_page' ] = 1
			
			if 'worldpop_page_size' not in st.session_state:
				st.session_state[ 'worldpop_page_size' ] = 25
			
			if 'worldpop_timeout' not in st.session_state:
				st.session_state[ 'worldpop_timeout' ] = 20
			
			if st.session_state.get( 'worldpop_clear_request', False ):
				st.session_state[ 'worldpop_mode' ] = 'catalog'
				st.session_state[ 'worldpop_query' ] = ''
				st.session_state[ 'worldpop_asset_path' ] = ''
				st.session_state[ 'worldpop_asset_choice' ] = 'data/pop/wpgp?iso3=GHA'
				st.session_state[ 'worldpop_custom_asset_path' ] = ''
				st.session_state[ 'worldpop_page' ] = 1
				st.session_state[ 'worldpop_page_size' ] = 25
				st.session_state[ 'worldpop_timeout' ] = 20
				st.session_state[ 'worldpop_results' ] = { }
				st.session_state[ 'worldpop_clear_request' ] = False
			
			worldpop_mode = st.selectbox( 'Mode', options=WORLDPOP_MODES,
				index=WORLDPOP_MODES.index( st.session_state.get( 'worldpop_mode', 'catalog' ) ),
				key='worldpop_mode', help=('catalog = API landing content; '
				                           'search = catalog-style search; '
				                           'raster_metadata = direct asset or metadata path.') )
			
			worldpop_query = st.text_area( 'Query',
				value=st.session_state.get( 'worldpop_query', '' ), height=90, key='worldpop_query',
				placeholder='population Ghana 2020', disabled=(worldpop_mode != 'search') )
			
			worldpop_asset_choice = st.selectbox( 'Asset Path Preset',
				options=WORLDPOP_ASSET_PRESETS, index=WORLDPOP_ASSET_PRESETS.index(
					st.session_state.get( 'worldpop_asset_choice', 'data/pop/wpgp?iso3=GHA' ) ),
				key='worldpop_asset_choice', disabled=(worldpop_mode != 'raster_metadata'),
				help='Common WorldPop API metadata paths. '
				     'Use Custom for another path.' )
			
			worldpop_custom_asset_path = st.text_area( 'Custom Asset Path',
				value=st.session_state.get( 'worldpop_custom_asset_path', '' ), height=100,
				key='worldpop_custom_asset_path', placeholder='data/pop/wpgp?iso3=GHA', disabled=(
						worldpop_mode != 'raster_metadata' or worldpop_asset_choice != 'Custom...') )
			
			c1, c2, c3 = st.columns( 3 )
			with c1:
				worldpop_page = st.number_input( 'Page', min_value=1, max_value=100000,
					value=int( st.session_state.get( 'worldpop_page', 1 ) ), step=1,
					key='worldpop_page', disabled=(worldpop_mode != 'search') )
			
			with c2:
				worldpop_page_size = st.number_input( 'Page Size', min_value=1, max_value=500,
					value=int( st.session_state.get( 'worldpop_page_size', 25 ) ), step=1,
					key='worldpop_page_size', disabled=(worldpop_mode != 'search') )
			
			with c3:
				worldpop_timeout = st.number_input( 'Timeout', min_value=1, max_value=120,
					value=int( st.session_state.get( 'worldpop_timeout', 20 ) ), step=1,
					key='worldpop_timeout' )
			
			st.caption( 'WorldPop exposes API access to population and demographic datasets. '
			            'Raster metadata mode appends a selected path to the current wrapper '
			            'base URL.' )
			
			b1, b2 = st.columns( 2 )
			with b1:
				worldpop_submit = st.button( 'Submit', key='worldpop_submit', width='stretch' )
			
			with b2:
				st.button( 'Clear', key='worldpop_clear', on_click=_clear_worldpop_state,
					width='stretch' )
			
			if worldpop_submit:
				st.session_state[ 'demographic_active_source' ] = 'world_population'
			
			render_source_processing_controls( 'demographic', 'worldpop_results',
				'demographic_active_source', 'world_population', 'api_world_population' )
		
		# ---- Expander CDC WONDER
		with st.expander( label='CDC Wonder', icon='🧬', expanded=False ):
			st.caption( 'API', help=cfg.CDC_WONDER )
			WONDER_MODES = [ 'metadata_template', 'query_xml' ]
			WONDER_DATASETS = [ 'D76', 'D140', 'D176', 'D158', 'D159', 'D160', 'D161', 'D162',
			                    'D163', 'D164', 'D165', 'D166', 'D167', 'D168', 'D169', 'D170',
			                    'D171', 'D172', 'D173', 'D174', 'D175', 'Other' ]
			
			def _clear_wonder_state( ) -> None:
				st.session_state[ 'wonder_clear_request' ] = True
			
			def _validate_wonder_dataset_id( value: object ) -> str:
				text = str( value or '' ).strip( ).upper( )
				
				if not text:
					raise ValueError( 'CDC WONDER Dataset ID is required.' )
				
				if not re.fullmatch( r'D\d{1,4}', text ):
					raise ValueError( 'CDC WONDER Dataset ID must use the format D followed by '
					                  'digits, '
					                  'such as D76.' )
				
				return text
			
			def _validate_wonder_xml( value: object ) -> str:
				text = str( value or '' ).strip( )
				
				if not text:
					raise ValueError( 'Request XML is required for query_xml mode.' )
				
				if '<request-parameters>' not in text and '<query-parameters>' not in text:
					raise ValueError( 'Request XML should contain CDC WONDER request/query '
					                  'parameters.' )
				
				return text
			
			if 'wonder_results' not in st.session_state:
				st.session_state[ 'wonder_results' ] = { }
			
			if 'wonder_clear_request' not in st.session_state:
				st.session_state[ 'wonder_clear_request' ] = False
			
			if st.session_state.get( 'wonder_mode', 'metadata_template' ) not in WONDER_MODES:
				st.session_state[ 'wonder_mode' ] = 'metadata_template'
			
			if 'wonder_dataset_id' not in st.session_state:
				st.session_state[ 'wonder_dataset_id' ] = 'D76'
			
			if st.session_state.get( 'wonder_dataset_id', 'D76' ) in WONDER_DATASETS:
				default_dataset_choice = st.session_state.get( 'wonder_dataset_id', 'D76' )
			else:
				default_dataset_choice = 'Other'
			
			if 'wonder_dataset_choice' not in st.session_state:
				st.session_state[ 'wonder_dataset_choice' ] = default_dataset_choice
			
			if st.session_state.get( 'wonder_dataset_choice', 'D76' ) not in WONDER_DATASETS:
				st.session_state[ 'wonder_dataset_choice' ] = default_dataset_choice
			
			if 'wonder_custom_dataset_id' not in st.session_state:
				st.session_state[ 'wonder_custom_dataset_id' ] = (
						'' if default_dataset_choice != 'Other' else st.session_state.get(
							'wonder_dataset_id', '' ))
			
			if 'wonder_request_xml' not in st.session_state:
				st.session_state[ 'wonder_request_xml' ] = ''
			
			if 'wonder_timeout' not in st.session_state:
				st.session_state[ 'wonder_timeout' ] = 20
			
			if st.session_state.get( 'wonder_clear_request', False ):
				st.session_state[ 'wonder_mode' ] = 'metadata_template'
				st.session_state[ 'wonder_dataset_id' ] = 'D76'
				st.session_state[ 'wonder_dataset_choice' ] = 'D76'
				st.session_state[ 'wonder_custom_dataset_id' ] = ''
				st.session_state[ 'wonder_request_xml' ] = ''
				st.session_state[ 'wonder_timeout' ] = 20
				st.session_state[ 'wonder_results' ] = { }
				st.session_state[ 'wonder_clear_request' ] = False
			
			wonder_mode = st.selectbox( 'Mode', options=WONDER_MODES, index=WONDER_MODES.index(
				st.session_state.get( 'wonder_mode', 'metadata_template' ) ), key='wonder_mode',
				help=('metadata_template = build a starter XML request; '
				      'query_xml = submit a raw XML request to CDC WONDER.') )
			
			wonder_dataset_choice = st.selectbox( 'Dataset ID', options=WONDER_DATASETS,
				index=WONDER_DATASETS.index(
					st.session_state.get( 'wonder_dataset_choice', 'D76' ) ),
				key='wonder_dataset_choice', help='Common CDC WONDER database '
				                                  'identifiers. Use Other for newer'
				                                  ' IDs.' )
			
			wonder_custom_dataset_id = st.text_input( 'Custom Dataset ID',
				value=st.session_state.get( 'wonder_custom_dataset_id', '' ),
				key='wonder_custom_dataset_id', placeholder='D76',
				disabled=(wonder_dataset_choice != 'Other') )
			
			wonder_request_xml = st.text_area( 'Request XML',
				value=st.session_state.get( 'wonder_request_xml', '' ), height=240,
				key='wonder_request_xml',
				placeholder='<request-parameters>...</request-parameters>',
				disabled=(wonder_mode != 'query_xml') )
			
			wonder_timeout = st.number_input( 'Timeout', min_value=1, max_value=120,
				value=int( st.session_state.get( 'wonder_timeout', 20 ) ), step=1,
				key='wonder_timeout' )
			
			st.caption( 'CDC WONDER requires POST requests with request_xml and acceptance '
			            'of data-use restrictions. The wrapper submits '
			            'accept_datause_restrictions=true.' )
			
			b1, b2 = st.columns( 2 )
			with b1:
				wonder_submit = st.button( 'Submit', key='wonder_submit', width='stretch' )
			
			with b2:
				st.button( 'Clear', key='wonder_clear', on_click=_clear_wonder_state,
					width='stretch' )
			
			if wonder_submit:
				st.session_state[ 'demographic_active_source' ] = 'cdc_wonder'
			
			render_source_processing_controls( 'demographic', 'wonder_results',
				'demographic_active_source', 'cdc_wonder', 'api_cdc_wonder' )
		
		# ---- Expander Pub Med
		with st.expander( label='Pub Med Search', icon='🏥', expanded=False ):
			st.caption( 'API', help=cfg.PUB_MED_SEARCH_LOADER )
			def _clear_pubmed_state( ) -> None:
				st.session_state[ 'pubmed_clear_request' ] = True
			
			if 'pubmed_results' not in st.session_state:
				st.session_state[ 'pubmed_results' ] = { }
			
			if 'pubmed_clear_request' not in st.session_state:
				st.session_state[ 'pubmed_clear_request' ] = False
			
			if 'pubmed_query' not in st.session_state:
				st.session_state[ 'pubmed_query' ] = ''
			
			if 'pubmed_max_docs' not in st.session_state:
				st.session_state[ 'pubmed_max_docs' ] = 5
			
			if st.session_state.get( 'pubmed_clear_request', False ):
				st.session_state[ 'pubmed_results' ] = { }
				st.session_state[ 'pubmed_query' ] = ''
				st.session_state[ 'pubmed_max_docs' ] = 5
				st.session_state[ 'pubmed_clear_request' ] = False
			
			pubmed_query = st.text_input( 'PubMed Query',
				value=st.session_state.get( 'pubmed_query', '' ), key='pubmed_query',
				placeholder='Example: machine learning '
				            'cancer diagnosis' )
			
			pubmed_max_docs = st.number_input( 'Max Documents', min_value=1, max_value=100,
				value=int( st.session_state.get( 'pubmed_max_docs', 5 ) ), step=1,
				key='pubmed_max_docs' )
			
			st.caption( 'PubMed search uses the LangChain PubMedSearchLoader and promotes '
			            'returned documents into the shared loader state for downstream use.' )
			
			b1, b2, b3 = st.columns( 3 )
			with b1:
				pubmed_submit = st.button( 'Submit', key='pubmed_submit', use_container_width=True )
			
			with b2:
				pubmed_clear = st.button( 'Clear', key='pubmed_clear', on_click=_clear_pubmed_state,
					use_container_width=True )
			
			with b3:
				can_save = (st.session_state.get(
					'active_loader' ) == 'PubMedSearchLoader' and isinstance(
					st.session_state.get( 'raw_text' ), str ) and st.session_state.get(
					'raw_text' ).strip( ))
				
				if can_save:
					st.download_button( 'Save', data=st.session_state.get( 'raw_text' ),
						file_name='pubmed_loader_output.txt', mime='text/plain', key='pubmed_save',
						width='stretch' )
				else:
					st.button( 'Save', key='pubmed_save_disabled', disabled=True, width='stretch' )
			
			if pubmed_submit:
				st.session_state[ 'demographic_active_source' ] = 'pub_med_search'
			
			render_source_processing_controls( 'demographic', 'pubmed_results',
				'demographic_active_source', 'pub_med_search', 'api_pub_med_search' )
		
		# ---- Expander Open City
		with st.expander( label='Open City Data', icon='🏙️', expanded=False ):
			st.caption( 'API', help=cfg.OPEN_CITY_DATA_LOADER )
			OPEN_CITY_DOMAINS = [ 'data.sfgov.org', 'data.cityofnewyork.us',
			                      'data.cityofchicago.org', 'data.lacity.org', 'data.seattle.gov',
			                      'data.austintexas.gov', 'data.cincinnati-oh.gov',
			                      'data.baltimorecity.gov', 'data.cityofboston.gov',
			                      'data.nashville.gov', 'Other' ]
			
			def _clear_open_city_state( ) -> None:
				st.session_state[ 'open_city_clear_request' ] = True
			
			def _validate_open_city_domain( value: object ) -> str:
				text = str( value or '' ).strip( ).lower( )
				text = text.replace( 'https://', '' ).replace( 'http://', '' )
				text = text.strip( '/' )
				
				if not text:
					raise ValueError( 'City ID is required.' )
				
				if '/' in text:
					raise ValueError( 'City ID must be a domain only, not a URL path.' )
				
				if not re.fullmatch( r'[a-z0-9][a-z0-9.-]+\.[a-z]{2,}', text ):
					raise ValueError( 'City ID must be a valid Socrata portal domain, such as '
					                  'data.sfgov.org.' )
				
				return text
			
			def _validate_open_city_dataset_id( value: object ) -> str:
				text = str( value or '' ).strip( ).replace( '.json', '' ).strip( '/' )
				
				if not text:
					raise ValueError( 'Dataset ID is required.' )
				
				if not re.fullmatch( r'[a-zA-Z0-9]{4}-[a-zA-Z0-9]{4}', text ):
					raise ValueError( 'Dataset ID must use the Socrata four-by-four format, '
					                  'such as vw6y-z8j6.' )
				
				return text.lower( )
			
			if 'open_city_results' not in st.session_state:
				st.session_state[ 'open_city_results' ] = { }
			
			if 'open_city_clear_request' not in st.session_state:
				st.session_state[ 'open_city_clear_request' ] = False
			
			if 'open_city_id' not in st.session_state:
				st.session_state[ 'open_city_id' ] = 'data.sfgov.org'
			
			if st.session_state.get( 'open_city_id', 'data.sfgov.org' ) in OPEN_CITY_DOMAINS:
				default_open_city_choice = st.session_state.get( 'open_city_id', 'data.sfgov.org' )
			else:
				default_open_city_choice = 'Other'
			
			if 'open_city_choice' not in st.session_state:
				st.session_state[ 'open_city_choice' ] = default_open_city_choice
			
			if st.session_state.get( 'open_city_choice',
					'data.sfgov.org' ) not in OPEN_CITY_DOMAINS:
				st.session_state[ 'open_city_choice' ] = default_open_city_choice
			
			if 'open_city_custom_id' not in st.session_state:
				st.session_state[ 'open_city_custom_id' ] = (
						'' if default_open_city_choice != 'Other' else st.session_state.get(
							'open_city_id', '' ))
			
			if 'open_city_dataset_id' not in st.session_state:
				st.session_state[ 'open_city_dataset_id' ] = ''
			
			if 'open_city_limit' not in st.session_state:
				st.session_state[ 'open_city_limit' ] = 100
			
			if st.session_state.get( 'open_city_clear_request', False ):
				st.session_state[ 'open_city_results' ] = { }
				st.session_state[ 'open_city_id' ] = 'data.sfgov.org'
				st.session_state[ 'open_city_choice' ] = 'data.sfgov.org'
				st.session_state[ 'open_city_custom_id' ] = ''
				st.session_state[ 'open_city_dataset_id' ] = ''
				st.session_state[ 'open_city_limit' ] = 100
				st.session_state[ 'open_city_clear_request' ] = False
			
			open_city_choice = st.selectbox( 'City ID', options=OPEN_CITY_DOMAINS,
				index=OPEN_CITY_DOMAINS.index(
					st.session_state.get( 'open_city_choice', 'data.sfgov.org' ) ),
				key='open_city_choice', help='Common Socrata open-data '
				                             'city domains. Use Other '
				                             'for a custom portal.' )
			
			open_city_custom_id = st.text_input( 'Custom City ID',
				value=st.session_state.get( 'open_city_custom_id', '' ), key='open_city_custom_id',
				disabled=(open_city_choice != 'Other'), placeholder='data.example.gov' )
			
			dataset_id = st.text_input( 'Dataset ID',
				value=st.session_state.get( 'open_city_dataset_id', '' ),
				key='open_city_dataset_id', placeholder='vw6y-z8j6' )
			
			limit = st.number_input( 'Limit', min_value=1, max_value=5000,
				value=int( st.session_state.get( 'open_city_limit', 100 ) ), step=10,
				key='open_city_limit' )
			
			st.caption( 'Open City Data uses LangChain OpenCityDataLoader backed by Socrata. '
			            'Use the API tab on the city dataset page to find the dataset ID.' )
			
			b1, b2, b3 = st.columns( 3 )
			with b1:
				open_city_submit = st.button( 'Submit', key='open_city_submit', width='stretch' )
			
			with b2:
				open_city_clear = st.button( 'Clear', key='open_city_clear',
					on_click=_clear_open_city_state, width='stretch' )
			
			with b3:
				can_save = (
						st.session_state.get( 'active_loader' ) == 'OpenCityLoader' and isinstance(
					st.session_state.get( 'raw_text' ), str ) and st.session_state.get(
					'raw_text' ).strip( ))
				
				if can_save:
					st.download_button( 'Save', data=st.session_state.get( 'raw_text' ),
						file_name='open_city_loader_output.txt', mime='text/plain',
						key='open_city_save', width='stretch' )
				else:
					st.button( 'Save', key='open_city_save_disabled', disabled=True,
						width='stretch' )
			
			if open_city_submit:
				st.session_state[ 'demographic_active_source' ] = 'open_city_data'
			
			render_source_processing_controls( 'demographic', 'open_city_results',
				'demographic_active_source', 'open_city_data', 'api_open_city_data' )
	
	with right:
		active_source = st.session_state.get( 'demographic_active_source', '' )
		display_names: Dict[ str, str ] = { 'u_s_census_bureau': 'U.S. Census Bureau',
		                                    'cdc_socrata': 'CDC Socrata',
		                                    'u_s_health': 'U.S. Health', 'who_global': 'WHO Global',
		                                    'united_nations': 'United Nations',
		                                    'world_population': 'World Population',
		                                    'cdc_wonder': 'CDC Wonder',
		                                    'pub_med_search': 'Pub Med Search',
		                                    'open_city_data': 'Open City Data', }
		if active_source:
			st.caption( f"Active Source: {display_names.get( active_source, active_source )}" )
		
		# -------- U.S. Census Bureau
		if active_source == 'u_s_census_bureau':
			st.markdown( '##### U.S. Census Bureau' )
			result = st.session_state.get( 'census_results', { } )
			if census_submit:
				try:
					clean_year = _validate_census_year( census_year )
					clean_dataset = _validate_census_dataset( census_dataset )
					if census_mode == 'data':
						clean_fields = _validate_census_fields( census_fields )
						clean_for = _validate_census_geography_clause( name='For', value=census_for,
							required=True )
						clean_in = _validate_census_geography_clause( name='In', value=census_in,
							required=False )
					else:
						clean_fields = str( census_fields or '' ).strip( )
						clean_for = str( census_for or '' ).strip( )
						clean_in = str( census_in or '' ).strip( )
					
					f = CensusData( )
					result = f.fetch( mode=str( census_mode ), year=clean_year,
						dataset=clean_dataset, fields=clean_fields, geography_for=clean_for,
						geography_in=clean_in, predicates=str( census_predicates or '' ).strip( ),
						time=int( census_timeout ) )
					
					st.session_state[ 'census_results' ] = result or { }
					st.rerun( )
				
				except Exception as exc:
					st.error( 'Census request failed.' )
					st.exception( exc )
			
			if not result:
				st.text( 'No results.' )
			else:
				render_result_metadata( result )
				if result.get( 'mode', '' ) == 'variables':
					payload = result.get( 'data', { } ) if isinstance( result, dict ) else { }
					variables = payload.get( 'variables', { } ) if isinstance( payload,
						dict ) else { }
					
					rows: List[ Dict[ str, Any ] ] = [ ]
					if isinstance( variables, dict ):
						for name, meta in variables.items( ):
							if isinstance( meta, dict ):
								rows.append( { 'Name': name, 'Label': meta.get( 'label', '' ),
								               'Concept': meta.get( 'concept', '' ),
								               'PredicateType': meta.get( 'predicateType', '' ),
								               'Group': meta.get( 'group', '' ),
								               'Limit': meta.get( 'limit', '' ), } )
					
					render_summary_kv( '#### Summary',
						{ 'Year': census_year, 'Dataset': census_dataset,
						  'VariableCount': len( rows ), } )
					render_rows_table( '#### Variables', rows )
				
				elif result.get( 'mode', '' ) == 'data':
					payload = result.get( 'data', { } ) if isinstance( result, dict ) else { }
					rows = payload.get( 'rows', [ ] ) if isinstance( payload, dict ) else [ ]
					render_summary_kv( '#### Summary',
						{ 'Year': census_year, 'Dataset': census_dataset, 'Fields': census_fields,
						  'For': census_for, 'In': census_in,
						  'RowCount': len( rows ) if isinstance( rows, list ) else 0, } )
					render_rows_table( '#### Data Rows',
						rows if isinstance( rows, list ) else [ ] )
				
				render_fallback_raw( result )
		
		# -------- CDC SOCRATA
		elif active_source == 'cdc_socrata':
			st.markdown( '##### CDC Socrata' )
			result = st.session_state.get( 'socrata_results', { } )
			if socrata_submit:
				try:
					clean_dataset_id = _validate_socrata_dataset_id( socrata_dataset_id )
					f = Socrata( )
					result = f.fetch( mode=str( socrata_mode ), domain=str( socrata_domain ),
						dataset_id=clean_dataset_id, select=str( socrata_select ),
						where=str( socrata_where ), order=str( socrata_order ),
						group=str( socrata_group ), limit=int( socrata_limit ),
						offset=int( socrata_offset ), time=int( socrata_timeout ) )
					st.session_state[ 'socrata_results' ] = result or { }
					st.rerun( )
				except Exception as exc:
					st.error( 'CDC Socrata request failed.' )
					st.exception( exc )
			
			if not result:
				st.text( 'No results.' )
			else:
				render_result_metadata( result )
				if result.get( 'mode', '' ) == 'metadata':
					payload = result.get( 'data', { } )
					render_summary_kv( '#### Summary', { 'Name': payload.get( 'name', '' ),
							'Description': payload.get( 'description', '' ),
							'RowsUpdatedAt': payload.get( 'rowsUpdatedAt', '' ),
							'ViewType': payload.get( 'viewType', '' ),
							'Columns': len( payload.get( 'columns', [ ] ) ) } )
					rows: List[ Dict[ str, Any ] ] = [ ]
					columns_payload = payload.get( 'columns', [ ] ) if isinstance( payload,
						dict ) else [ ]
					for item in columns_payload:
						if isinstance( item, dict ):
							rows.append( { 'Name': item.get( 'name', '' ),
							               'FieldName': item.get( 'fieldName', '' ),
							               'DataType': item.get( 'dataTypeName', '' ),
							               'Description': item.get( 'description', '' ), } )
					
					render_rows_table( '#### Columns', rows )
				
				elif result.get( 'mode', '' ) == 'rows':
					rows = result.get( 'data', [ ] ) if isinstance( result, dict ) else [ ]
					
					render_summary_kv( '#### Summary',
						{ 'Domain': socrata_domain, 'DatasetId': socrata_dataset_id,
						  'Limit': int( socrata_limit ), 'Offset': int( socrata_offset ),
						  'RowCount': len( rows ) if isinstance( rows, list ) else 0, } )
					render_rows_table( '#### Rows', rows if isinstance( rows, list ) else [ ] )
				
				render_fallback_raw( result )
		
		# -------- US Health Data
		elif active_source == 'u_s_health':
			st.markdown( '##### U.S. Health' )
			result = st.session_state.get( 'healthdata_results', { } )
			
			if healthdata_submit:
				try:
					clean_dataset_id = _validate_healthdata_dataset_id( healthdata_dataset_id )
					
					f = HealthData( )
					result = f.fetch( mode=str( healthdata_mode ), domain=str( healthdata_domain ),
						dataset_id=clean_dataset_id, select=str( healthdata_select ),
						where=str( healthdata_where ), order=str( healthdata_order ),
						group=str( healthdata_group ), limit=int( healthdata_limit ),
						offset=int( healthdata_offset ), time=int( healthdata_timeout ) )
					
					st.session_state[ 'healthdata_results' ] = result or { }
					st.rerun( )
				
				except Exception as exc:
					st.error( 'HealthData request failed.' )
					st.exception( exc )
			
			if not result:
				st.text( 'No results.' )
			else:
				render_result_metadata( result )
				
				if result.get( 'mode', '' ) == 'metadata':
					payload = result.get( 'data', { } ) if isinstance( result, dict ) else { }
					
					render_summary_kv( '#### Summary', { 'Name': payload.get( 'name', '' ) if isinstance( payload, dict ) else '',
								'Description': payload.get( 'description', '' ) if isinstance(
									payload, dict ) else '',
								'RowsUpdatedAt': payload.get( 'rowsUpdatedAt', '' ) if isinstance(
									payload, dict ) else '',
								'ViewType': payload.get( 'viewType', '' ) if isinstance( payload,
									dict ) else '',
								'Columns': len( payload.get( 'columns', [ ] ) ) if isinstance(
									payload, dict ) else 0, } )
					
					rows: List[ Dict[ str, Any ] ] = [ ]
					columns_payload = payload.get( 'columns', [ ] ) if isinstance( payload,
						dict ) else [ ]
					for item in columns_payload:
						if isinstance( item, dict ):
							rows.append( { 'Name': item.get( 'name', '' ),
							               'FieldName': item.get( 'fieldName', '' ),
							               'DataType': item.get( 'dataTypeName', '' ),
							               'Description': item.get( 'description', '' ), } )
					
					render_rows_table( '#### Columns', rows )
				
				elif result.get( 'mode', '' ) == 'rows':
					rows = result.get( 'data', [ ] ) if isinstance( result, dict ) else [ ]
					
					render_summary_kv( '#### Summary', { 'Domain': healthdata_domain, 'DatasetId': healthdata_dataset_id,
						  'Limit': int( healthdata_limit ), 'Offset': int( healthdata_offset ),
						  'RowCount': len( rows ) if isinstance( rows, list ) else 0, } )
					render_rows_table( '#### Rows', rows if isinstance( rows, list ) else [ ] )
				
				render_fallback_raw( result )
		
		# -------- WHO Global Health
		elif active_source == 'who_global':
			st.markdown( '##### WHO Global' )
			result = st.session_state.get( 'who_results', { } )
			
			if who_submit:
				try:
					if who_mode == 'athena':
						selected_query_path = (
								who_custom_query_path if who_query_choice == 'Custom...' else who_query_choice)
						clean_query_path = _validate_who_query_path( selected_query_path )
					else:
						clean_query_path = ''
					
					f = GlobalHealthData( )
					result = f.fetch( mode=str( who_mode ), query_path=clean_query_path,
						fmt=str( who_format ), time=int( who_timeout ) )
					
					st.session_state[ 'who_query_path' ] = clean_query_path
					st.session_state[ 'who_results' ] = result or { }
					st.rerun( )
				
				except Exception as exc:
					st.error( 'WHO Global Health request failed.' )
					st.exception( exc )
			
			if not result:
				st.text( 'No results.' )
			else:
				render_result_metadata( result )
				
				if result.get( 'mode', '' ) == 'indicator_registry':
					payload = result.get( 'data', { } ) if isinstance( result, dict ) else { }
					
					render_summary_kv( '#### Summary', { 'Mode': result.get( 'mode', '' ),
					                                      'HasHtml': (isinstance( payload,
						                                      dict ) and bool(
						                                      payload.get( 'html', '' ) )), } )
					
					if isinstance( payload, dict ) and payload.get( 'html', '' ):
						render_html_preview( '#### Indicator Registry Preview',
							str( payload.get( 'html', '' ) ) )
					else:
						st.json( payload )
				
				elif result.get( 'mode', '' ) == 'athena':
					payload = result.get( 'data', { } ) if isinstance( result, dict ) else { }
					
					if isinstance( payload, dict ) and isinstance( payload.get( 'value', [ ] ),
							list ):
						rows = payload.get( 'value', [ ] )
						render_summary_kv( '#### Summary',
							{ 'QueryPath': st.session_state.get( 'who_query_path', '' ),
									'Format': who_format, 'ResultCount': len( rows ), } )
						render_rows_table( '#### Athena Results', rows )
					elif isinstance( payload, dict ) and payload.get( 'text', '' ):
						render_summary_kv( '#### Summary',
							{ 'QueryPath': st.session_state.get( 'who_query_path', '' ),
									'Format': who_format, 'HasText': True, } )
						st.markdown( '#### Response' )
						st.code( str( payload.get( 'text', '' ) )[ :8000 ] )
					else:
						st.json( payload )
				
				render_fallback_raw( result )
		
		# -------- United Nations Data
		elif active_source == 'united_nations':
			st.markdown( '##### United Nations' )
			result = st.session_state.get( 'un_results', { } )
			
			if un_submit:
				try:
					if un_mode == 'sdmx_query':
						selected_query_path = (
								un_custom_query_path if un_query_choice == 'Custom...' else un_query_choice)
						clean_query_path = _validate_un_query_path( selected_query_path )
					else:
						clean_query_path = ''
					
					f = UnitedNations( )
					result = f.fetch( mode=str( un_mode ), query_path=clean_query_path,
						time=int( un_timeout ) )
					
					st.session_state[ 'un_query_path' ] = clean_query_path
					st.session_state[ 'un_results' ] = result or { }
					st.rerun( )
				
				except Exception as exc:
					st.error( 'United Nations request failed.' )
					st.exception( exc )
			
			if not result:
				st.text( 'No results.' )
			else:
				render_result_metadata( result )
				
				if result.get( 'mode', '' ) == 'datasets':
					payload = result.get( 'data', { } ) if isinstance( result, dict ) else { }
					
					render_summary_kv( '#### Summary', { 'Mode': result.get( 'mode', '' ),
					                                      'HasHtml': (isinstance( payload,
						                                      dict ) and bool(
						                                      payload.get( 'html', '' ) )), } )
					
					if isinstance( payload, dict ) and payload.get( 'html', '' ):
						render_html_preview( '#### Dataset Catalog Preview',
							str( payload.get( 'html', '' ) ) )
					else:
						st.json( payload )
				
				elif result.get( 'mode', '' ) == 'sdmx_query':
					payload = result.get( 'data', { } ) if isinstance( result, dict ) else { }
					
					render_summary_kv( '#### Summary', { 'Mode': result.get( 'mode', '' ),
					                                      'QueryPath': st.session_state.get(
						                                      'un_query_path', '' ),
					                                      'TextPayload': (isinstance( payload,
						                                      dict ) and bool(
						                                      payload.get( 'text', '' ) )),
					                                      'JsonPayload': isinstance( payload,
						                                      (dict, list) ), } )
					
					if isinstance( payload, dict ) and payload.get( 'text', '' ):
						st.markdown( '#### Query Response' )
						st.code( str( payload.get( 'text', '' ) )[ :8000 ] )
					elif isinstance( payload, dict ) and payload.get( 'html', '' ):
						render_html_preview( '#### Query Response',
							str( payload.get( 'html', '' ) ) )
					else:
						st.json( payload )
				
				render_fallback_raw( result )
		
		# -------- World Population
		elif active_source == 'world_population':
			st.markdown( '##### World Population' )
			result = st.session_state.get( 'worldpop_results', { } )
			if worldpop_submit:
				try:
					if worldpop_mode == 'search':
						clean_query = _validate_worldpop_query( worldpop_query )
						clean_asset_path = ''
					elif worldpop_mode == 'raster_metadata':
						selected_asset_path = (
								worldpop_custom_asset_path if worldpop_asset_choice == 'Custom...' else worldpop_asset_choice)
						clean_asset_path = _validate_worldpop_asset_path( selected_asset_path )
						clean_query = ''
					else:
						clean_query = ''
						clean_asset_path = ''
					
					f = WorldPopulation( )
					result = f.fetch( mode=str( worldpop_mode ), query=clean_query,
						asset_path=clean_asset_path, page=int( worldpop_page ),
						page_size=int( worldpop_page_size ), time=int( worldpop_timeout ) )
					
					st.session_state[ 'worldpop_query' ] = clean_query
					st.session_state[ 'worldpop_asset_path' ] = clean_asset_path
					st.session_state[ 'worldpop_results' ] = result or { }
					st.rerun( )
				
				except Exception as exc:
					st.error( 'World Population request failed.' )
					st.exception( exc )
			
			if not result:
				st.text( 'No results.' )
			else:
				render_result_metadata( result )
				if result.get( 'mode', '' ) == 'catalog':
					payload = result.get( 'data', { } ) if isinstance( result, dict ) else { }
					
					render_summary_kv( '#### Summary', { 'Mode': result.get( 'mode', '' ),
					                                      'HasHtml': (isinstance( payload,
						                                      dict ) and bool(
						                                      payload.get( 'html', '' ) )), } )
					
					if isinstance( payload, dict ) and payload.get( 'html', '' ):
						render_html_preview( '#### Catalog Preview',
							str( payload.get( 'html', '' ) ) )
					else:
						st.json( payload )
				
				elif result.get( 'mode', '' ) == 'search':
					payload = result.get( 'data', { } ) if isinstance( result, dict ) else { }
					
					if isinstance( payload, dict ) and isinstance( payload.get( 'results', [ ] ),
							list ):
						rows = payload.get( 'results', [ ] )
						render_summary_kv( '#### Summary', { 'Query': st.session_state.get( 'worldpop_query', '' ),
									'Page': worldpop_page, 'PageSize': worldpop_page_size,
									'ResultCount': len( rows ), } )
						render_rows_table( '#### Search Results', rows )
					else:
						st.json( payload )
				
				elif result.get( 'mode', '' ) == 'raster_metadata':
					payload = result.get( 'data', { } ) if isinstance( result, dict ) else { }
					
					render_summary_kv( '#### Summary',
						{ 'AssetPath': st.session_state.get( 'worldpop_asset_path', '' ),
								'HasText': (isinstance( payload, dict ) and bool(
									payload.get( 'text', '' ) )), } )
					
					if isinstance( payload, dict ) and payload.get( 'text', '' ):
						st.markdown( '#### Metadata Response' )
						st.code( str( payload.get( 'text', '' ) )[ :8000 ] )
					else:
						st.json( payload )
				
				render_fallback_raw( result )
		
		# -------- CDC WONDER
		elif active_source == 'cdc_wonder':
			st.markdown( '##### CDC Wonder' )
			result = st.session_state.get( 'wonder_results', { } )
			if wonder_submit:
				try:
					selected_dataset_id = (
							wonder_custom_dataset_id if wonder_dataset_choice == 'Other' else wonder_dataset_choice)
					clean_dataset_id = _validate_wonder_dataset_id( selected_dataset_id )
					
					if wonder_mode == 'query_xml':
						clean_request_xml = _validate_wonder_xml( wonder_request_xml )
					else:
						clean_request_xml = str( wonder_request_xml or '' ).strip( )
					
					f = Wonder( )
					result = f.fetch( mode=str( wonder_mode ), dataset_id=clean_dataset_id,
						request_xml=clean_request_xml, time=int( wonder_timeout ) )
					
					st.session_state[ 'wonder_dataset_id' ] = clean_dataset_id
					st.session_state[ 'wonder_results' ] = result or { }
					
					if (wonder_mode == 'metadata_template' and isinstance( result,
						dict ) and isinstance( result.get( 'data', { } ), dict )):
						template_xml = result.get( 'data', { } ).get( 'request_xml', '' )
						st.session_state[ 'wonder_request_xml' ] = template_xml
					
					st.rerun( )
				
				except Exception as exc:
					st.error( 'CDC WONDER request failed.' )
					st.exception( exc )
			
			if not result:
				st.text( 'No results.' )
			else:
				render_result_metadata( result )
				
				if result.get( 'mode', '' ) == 'metadata_template':
					payload = result.get( 'data', { } ) if isinstance( result, dict ) else { }
					
					if isinstance( payload, dict ):
						render_summary_kv( '#### Template Summary',
							{ 'DatasetId': payload.get( 'dataset_id', '' ),
									'Notes': payload.get( 'notes', '' ), } )
						
						template_xml = str( payload.get( 'request_xml', '' ) )
						if template_xml:
							render_xml_preview( '#### Starter XML', template_xml )
						else:
							st.info( 'No starter XML returned.' )
				
				elif result.get( 'mode', '' ) == 'query_xml':
					payload = result.get( 'data', { } ) if isinstance( result, dict ) else { }
					
					if isinstance( payload, dict ):
						xml_text = str( payload.get( 'xml', '' ) )
						
						render_summary_kv( '#### Response Summary',
							{ 'DatasetId': st.session_state.get( 'wonder_dataset_id', '' ),
									'Characters': len( xml_text ),
									'HasXml': bool( xml_text.strip( ) ), } )
						
						render_xml_preview( '#### XML Response', xml_text )
					else:
						st.info( 'No XML response returned.' )
				
				render_fallback_raw( result )
		
		# -------- Pub Med
		elif active_source == 'pub_med_search':
			st.markdown( '##### Pub Med Search' )
			if pubmed_clear:
				remaining = clear_loader_documents( 'PubMedSearchLoader' )
				st.info( f'PubMed Loader state cleared. Remaining documents: {remaining}.' )
			
			if pubmed_submit:
				if not pubmed_query or not pubmed_query.strip( ):
					st.info( 'Enter a PubMed query.' )
				else:
					try:
						loader = PubMedSearchLoader( )
						documents = loader.load( query=pubmed_query.strip( ),
							max_docs=int( pubmed_max_docs ) ) or [ ]
						
						count = promote_loader_documents( documents, 'PubMedSearchLoader' )
						
						items: list[ dict[ str, Any ] ] = [ ]
						
						for i, doc in enumerate( documents, start=1 ):
							metadata = (doc.metadata if isinstance( getattr( doc, 'metadata', { } ),
								dict ) else { })
							content = str( getattr( doc, 'page_content', '' ) or '' )
							
							items.append( { 'Index': i, 'Title': (
									metadata.get( 'Title' ) or metadata.get( 'title' ) or ''),
							                'Published': (
									                metadata.get( 'Published' ) or metadata.get(
								                'published' ) or ''), 'Copyright': (
											metadata.get( 'Copyright Information' ) or metadata.get(
										'copyright' ) or ''), 'Summary': content,
							                'Metadata': metadata, } )
						
						st.session_state[ 'pubmed_results' ] = { 'mode': 'pubmed',
						                                         'query': pubmed_query.strip( ),
						                                         'max_docs': int( pubmed_max_docs ),
						                                         'count': count, 'items': items, }
						
						st.success( f'Loaded {count} PubMed document(s).' )
					
					except Exception as exc:
						st.error( 'PubMed request failed.' )
						st.exception( exc )
			
			result = st.session_state.get( 'pubmed_results', { } )
			
			if not result:
				st.text( 'No results.' )
			else:
				render_summary_kv( '#### Summary',
					{ 'Mode': result.get( 'mode', '' ), 'Query': result.get( 'query', '' ),
					  'MaxDocs': result.get( 'max_docs', 0 ),
					  'Returned': result.get( 'count', 0 ), } )
				
				items = result.get( 'items', [ ] ) if isinstance( result, dict ) else [ ]
				
				if items:
					table_rows = [
							{ 'Index': item.get( 'Index', '' ), 'Title': item.get( 'Title', '' ),
							  'Published': item.get( 'Published', '' ), } for item in items ]
					df_pubmed = pd.DataFrame( table_rows )
					st.markdown( '#### Results' )
					st.data_editor( df_pubmed, use_container_width=True, hide_index=True )
					first = items[ 0 ]
					render_summary_kv( '#### First Result', { 'Title': first.get( 'Title', '' ),
					                                           'Published': first.get( 'Published',
						                                           '' ),
					                                           'Copyright': first.get( 'Copyright',
						                                           '' ), } )
					
					st.markdown( '#### Abstract Preview' )
					st.code( str( first.get( 'Summary', '' ) )[ :8000 ] )
					
					with st.expander( 'Records', expanded=False ):
						for item in items:
							record_label = str( item.get( 'Title', '' ) or f"Record "
							                                               f"{item.get( 'Index', '' )}" )
							with st.expander( f"Record {item.get( 'Index', '' )}: {record_label}",
									expanded=False ):
								st.markdown( f"**Published:** {item.get( 'Published', '' )}" )
								st.markdown( f"**Copyright:** {item.get( 'Copyright', '' )}" )
								st.markdown( '##### Summary' )
								st.code( str( item.get( 'Summary', '' ) )[ :8000 ] )
								
								metadata = item.get( 'Metadata', { } )
								if metadata:
									with st.expander( 'Metadata', expanded=False ):
										st.json( metadata )
				else:
					st.info( 'No PubMed records returned.' )
				
				render_fallback_raw( result )
		
		# -------- Open City
		elif active_source == 'open_city_data':
			st.markdown( '##### Open City Data' )
			if open_city_clear:
				remaining = clear_loader_documents( 'OpenCityLoader' )
				st.info( f'Open City Data Loader state cleared. Remaining documents: '
				         f'{remaining}.' )
			
			if open_city_submit:
				try:
					selected_city_id = (
							open_city_custom_id if open_city_choice == 'Other' else open_city_choice)
					clean_city_id = _validate_open_city_domain( selected_city_id )
					clean_dataset_id = _validate_open_city_dataset_id( dataset_id )
					
					loader = OpenCityLoader( )
					documents = loader.load( city_id=clean_city_id, dataset_id=clean_dataset_id,
						limit=int( limit ) ) or [ ]
					
					count = promote_loader_documents( documents, 'OpenCityLoader' )
					
					items: list[ dict[ str, Any ] ] = [ ]
					for i, doc in enumerate( documents, start=1 ):
						metadata = (doc.metadata if isinstance( getattr( doc, 'metadata', { } ),
							dict ) else { })
						content = str( getattr( doc, 'page_content', '' ) or '' )
						items.append(
							{ 'Index': i, 'Source': metadata.get( 'source', '' ), 'Row': content,
							  'Metadata': metadata, } )
					
					st.session_state[ 'open_city_id' ] = clean_city_id
					st.session_state[ 'open_city_results' ] = { 'mode': 'open_city',
					                                            'city_id': clean_city_id,
					                                            'dataset_id': clean_dataset_id,
					                                            'limit': int( limit ),
					                                            'count': count, 'items': items, }
					
					st.success( f'Loaded {count} Open City document(s).' )
				
				except Exception as exc:
					st.error( 'Open City request failed.' )
					st.exception( exc )
			
			result = st.session_state.get( 'open_city_results', { } )
			
			if not result:
				st.text( 'No results.' )
			else:
				render_summary_kv( '#### Summary',
					{ 'Mode': result.get( 'mode', '' ), 'CityId': result.get( 'city_id', '' ),
					  'DatasetId': result.get( 'dataset_id', '' ),
					  'Limit': result.get( 'limit', 0 ), 'Returned': result.get( 'count', 0 ), } )
				
				items = result.get( 'items', [ ] ) if isinstance( result, dict ) else [ ]
				
				if items:
					table_rows = [
							{ 'Index': item.get( 'Index', '' ), 'Source': item.get( 'Source', '' ),
							  'Preview': str( item.get( 'Row', '' ) )[ :200 ], } for item in items ]
					
					df_open_city = pd.DataFrame( table_rows )
					
					st.markdown( '#### Results' )
					st.data_editor( df_open_city, use_container_width=True, hide_index=True )
					
					first = items[ 0 ]
					st.markdown( '#### First Row Preview' )
					st.code( str( first.get( 'Row', '' ) )[ :8000 ] )
					
					with st.expander( 'Records', expanded=False ):
						for item in items:
							with st.expander( f"Record {item.get( 'Index', '' )}", expanded=False ):
								st.markdown( f"**Source:** {item.get( 'Source', '' )}" )
								st.markdown( '##### Row' )
								st.code( str( item.get( 'Row', '' ) )[ :8000 ] )
								
								metadata = item.get( 'Metadata', { } )
								if metadata:
									with st.expander( 'Metadata', expanded=False ):
										st.json( metadata )
				else:
					st.info( 'No city records returned.' )
				
				render_fallback_raw( result )
		
		demographic_result_keys = { 'u_s_census_bureau': 'census_results',
				'cdc_socrata': 'socrata_results', 'u_s_health': 'healthdata_results',
				'who_global': 'who_results', 'united_nations': 'un_results',
				'world_population': 'worldpop_results', 'cdc_wonder': 'wonder_results',
				'pub_med_search': 'pubmed_results', 'open_city_data': 'open_city_results', }
		if active_source in demographic_result_keys:
			sync_mode_document( 'demographic', demographic_result_keys[ active_source ],
				'demographic_active_source' )
		render_mode_document_tabs( 'demographic', '📄 Loaded' )
		
# ==============================================================================
# TEXT GENERATION MODE
# ==============================================================================
elif mode == 'Artificial Intelligence':
	st.subheader( '🧠  Generative AI' )
	st.divider( )
	
	# ---------- Generation Result State
	if 'generation_documents' not in st.session_state:
		st.session_state[ 'generation_documents' ] = [ ]
	
	if 'generation_raw_result' not in st.session_state:
		st.session_state[ 'generation_raw_result' ] = None
	
	if 'generation_active_source' not in st.session_state:
		st.session_state[ 'generation_active_source' ] = ''
	
	def _promote_generation_result( provider: str, result: Any ) -> None:
		"""Promote a provider response into the shared generation document state.

		Purpose:
		    Converts the active provider response into LangChain documents used by the shared
		    right-column viewer while retaining the original response object for provider-specific
		    rendering.

		Args:
		    provider (str): Name of the provider that generated the response.
		    result (Any): Response returned by the provider wrapper.

		Returns:
		    None: This function updates Streamlit session state.
		"""
		if not str( provider or '' ).strip( ):
			raise ValueError( 'Provider cannot be empty.' )
		
		documents: list[ Document ] = [ ]
		
		if isinstance( result, list ) and all( isinstance( item, Document ) for item in result ):
			documents = list( result )
		else:
			if isinstance( result, (dict, list) ):
				page_content = json.dumps( normalize( result ), indent=2, ensure_ascii=False )
			else:
				page_content = str( result or '' )
			
			documents = [ Document( page_content=page_content,
				metadata={ 'mode': 'Generation', 'provider': provider, } ) ]
		
		for document in documents:
			if not isinstance( getattr( document, 'metadata', None ), dict ):
				document.metadata = { }
			
			document.metadata.setdefault( 'mode', 'Generation' )
			document.metadata.setdefault( 'provider', provider )
		
		st.session_state[ 'documents' ] = list( documents )
		st.session_state[ 'raw_documents' ] = list( documents )
		st.session_state[ 'raw_text' ] = '\n\n'.join(
			document.page_content for document in documents if
			isinstance( getattr( document, 'page_content', None ), str ) )
		st.session_state[ 'generation_documents' ] = list( documents )
		st.session_state[ 'generation_raw_result' ] = result
		st.session_state[ 'generation_active_source' ] = provider
	
	def _clear_generation_result( provider: str ) -> None:
		"""Clear the shared generation result for the active provider.

		Purpose:
		    Removes the shared generated document only when the provider being cleared currently
		    owns
		    the active result.

		Args:
		    provider (str): Name of the provider whose controls are being cleared.

		Returns:
		    None: This function updates Streamlit session state.
		"""
		if st.session_state.get( 'generation_active_source', '' ) != provider:
			return
		
		st.session_state[ 'documents' ] = [ ]
		st.session_state[ 'raw_documents' ] = [ ]
		st.session_state[ 'raw_text' ] = ''
		st.session_state[ 'generation_documents' ] = [ ]
		st.session_state[ 'generation_raw_result' ] = None
		st.session_state[ 'generation_active_source' ] = ''
	
	left, right = st.columns( [ 0.4, 0.6 ], gap='xxsmall', border=True )
	
	# ------------------------------------------------------------------
	# LEFT COLUMN — GENERATION CONTROLS
	# ------------------------------------------------------------------
	with left:
		
		# ---- Expander GPT
		with st.expander( label='ChatGPT', expanded=True ):
			CHAT_REASONING_EFFORTS = [ 'minimal', 'low', 'medium', 'high' ]
			
			def _clear_chat_state( ) -> None:
				st.session_state[ 'chat_clear_request' ] = True
				_clear_generation_result( 'ChatGPT' )
			
			def _normalize_chat_domains( value: object ) -> list[ str ]:
				text = str( value or '' ).strip( )
				
				if not text:
					return [ ]
				
				values: list[ str ] = [ ]
				entries = re.split( r'[\n,;]+', text )
				
				for entry in entries:
					raw_value = str( entry or '' ).strip( ).lower( )
					if not raw_value:
						continue
					
					if not raw_value.startswith( 'http://' ) and not raw_value.startswith(
							'https://' ):
						raw_value = f'https://{raw_value}'
					
					parsed = urlparse( raw_value )
					domain = (parsed.netloc or parsed.path or '').strip( ).lower( )
					domain = re.sub( r':\d+$', '', domain )
					domain = domain.lstrip( '.' )
					
					if domain.startswith( 'www.' ):
						domain = domain[ 4: ]
					
					if not domain:
						continue
					
					if not re.fullmatch( r'[a-z0-9][a-z0-9.-]*\.[a-z]{2,}', domain ):
						raise ValueError( f'Invalid search domain: {domain}' )
					
					if domain not in values:
						values.append( domain )
				
				return values
			
			if 'chat_clear_request' not in st.session_state:
				st.session_state[ 'chat_clear_request' ] = False
			
			if 'chat_prompt' not in st.session_state:
				st.session_state[ 'chat_prompt' ] = ''
			
			if 'chat_system' not in st.session_state:
				st.session_state[ 'chat_system' ] = ''
			
			if 'chat_domains' not in st.session_state:
				st.session_state[ 'chat_domains' ] = ''
			
			if 'chat_json_mode' not in st.session_state:
				st.session_state[ 'chat_json_mode' ] = False
			
			if 'chat_reasoning' not in st.session_state:
				st.session_state[ 'chat_reasoning' ] = False
			
			if 'chat_web_search' not in st.session_state:
				st.session_state[ 'chat_web_search' ] = False
			
			if 'chat_store' not in st.session_state:
				st.session_state[ 'chat_store' ] = True
			
			if 'chat_stream' not in st.session_state:
				st.session_state[ 'chat_stream' ] = False
			
			if 'chat_seed' not in st.session_state:
				st.session_state[ 'chat_seed' ] = 0
			
			if st.session_state.get( 'chat_reasoning_effort', 'low' ) not in CHAT_REASONING_EFFORTS:
				st.session_state[ 'chat_reasoning_effort' ] = 'low'
			
			if st.session_state.get( 'chat_clear_request', False ):
				st.session_state[ 'chat_prompt' ] = ''
				st.session_state[ 'chat_system' ] = ''
				st.session_state[ 'chat_domains' ] = ''
				st.session_state[ 'chat_json_mode' ] = False
				st.session_state[ 'chat_reasoning' ] = False
				st.session_state[ 'chat_web_search' ] = False
				st.session_state[ 'chat_store' ] = True
				st.session_state[ 'chat_stream' ] = False
				st.session_state[ 'chat_seed' ] = 0
				st.session_state[ 'chat_reasoning_effort' ] = 'low'
				st.session_state[ 'chat_clear_request' ] = False
			
			chat_prompt = st.text_area( 'Prompt', value=st.session_state.get( 'chat_prompt', '' ),
				height=120, key='chat_prompt' )
			
			p_row1 = st.columns( 2 )
			p_row2 = st.columns( 2 )
			p_row3 = st.columns( 2 )
			p_row4 = st.columns( 2 )
			p_row5 = st.columns( 2 )
			
			with p_row1[ 0 ]:
				_chat_models = (
						cfg.GPT_MODELS if hasattr( cfg, 'GPT_MODELS' ) and cfg.GPT_MODELS else [
								'gpt-5.4', 'gpt-5', 'gpt-5-mini', 'gpt-5-nano', 'gpt-4.1' ])
				
				chat_model = _model_selector( key_prefix='chat', label='Model',
					options=_chat_models, default_model=(
							'gpt-5-mini' if 'gpt-5-mini' in _chat_models else _chat_models[ 0 ]), )
			
			with p_row1[ 1 ]:
				chat_temperature = st.slider( 'Temperature', min_value=0.0, max_value=2.0,
					value=0.7, step=0.05, key='chat_temperature' )
			
			with p_row2[ 0 ]:
				chat_max_tokens = st.number_input( 'Max Tokens', min_value=1, max_value=32768,
					value=2048, step=1, key='chat_max_tokens' )
			
			with p_row2[ 1 ]:
				chat_top_p = st.slider( 'Top-P', min_value=0.0, max_value=1.0, value=1.0, step=0.01,
					key='chat_top_p' )
			
			with p_row3[ 0 ]:
				chat_seed = st.number_input( 'Seed', min_value=0, max_value=2_147_483_647,
					value=int( st.session_state.get( 'chat_seed', 0 ) ), step=1, key='chat_seed',
					help='Use 0 to omit the seed parameter.' )
			
			with p_row3[ 1 ]:
				chat_json_mode = st.checkbox( 'JSON Mode',
					value=bool( st.session_state.get( 'chat_json_mode', False ) ),
					key='chat_json_mode',
					help=('Current wrapper behavior adds JSON-only instructions. '
					      'A later Chat class drop-in should wire this to Responses '
					      'API text.format.') )
			
			with p_row4[ 0 ]:
				chat_reasoning = st.checkbox( 'Reasoning',
					value=bool( st.session_state.get( 'chat_reasoning', False ) ),
					key='chat_reasoning' )
			
			with p_row4[ 1 ]:
				chat_web_search = st.checkbox( 'Web Search',
					value=bool( st.session_state.get( 'chat_web_search', False ) ),
					key='chat_web_search' )
			
			with p_row5[ 0 ]:
				chat_store = st.checkbox( 'Store',
					value=bool( st.session_state.get( 'chat_store', True ) ), key='chat_store' )
			
			with p_row5[ 1 ]:
				chat_stream = st.checkbox( 'Stream',
					value=bool( st.session_state.get( 'chat_stream', False ) ), key='chat_stream' )
			
			_chat_supports_reasoning = (
					str( chat_model ).strip( ).lower( ).startswith( 'gpt-5' ) or str(
				chat_model ).strip( ).lower( ).startswith( 'o' ))
			
			if _chat_supports_reasoning and chat_reasoning:
				chat_reasoning_effort = st.selectbox( 'Reasoning Effort',
					options=CHAT_REASONING_EFFORTS, index=CHAT_REASONING_EFFORTS.index(
						st.session_state.get( 'chat_reasoning_effort', 'low' ) ),
					key='chat_reasoning_effort' )
			else:
				chat_reasoning_effort = None
			
			chat_system = st.text_area( 'System', value=st.session_state.get( 'chat_system', '' ),
				height=120, key='chat_system' )
			
			if chat_web_search:
				chat_domains = st.text_area( 'Preferred Search Domains ( comma-separated)',
					value=st.session_state.get( 'chat_domains', '' ), height=90, key='chat_domains',
					help='Examples: openai.com, platform.openai.com, arxiv.org' )
			else:
				chat_domains = ''
			
			btn_row = st.columns( 2 )
			with btn_row[ 0 ]:
				chat_submit = st.button( 'Submit', key='chat_submit' )
			
			with btn_row[ 1 ]:
				st.button( 'Clear', key='chat_clear', on_click=_clear_chat_state )
			
			# -----------------------------
			# Submit Button
			# -----------------------------
			if chat_submit:
				try:
					if not str( chat_prompt or '' ).strip( ):
						raise ValueError( 'Prompt cannot be empty.' )
					
					if chat_json_mode:
						has_json_instruction = (
								'json' in str( chat_prompt or '' ).lower( ) or 'json' in str(
							chat_system or '' ).lower( ))
						
						if not has_json_instruction:
							chat_system = (
									str( chat_system or '' ).strip( ) + '\n\nReturn valid JSON '
									                                    'only.').strip( )
					
					chat_domains_list = (
							_normalize_chat_domains( chat_domains ) if chat_web_search else [ ])
					
					fetcher = Chat( )
					params = { 'model': chat_model, 'temperature': float( chat_temperature ),
					           'max_tokens': int( chat_max_tokens ), 'top_p': float( chat_top_p ),
					           'seed': int( chat_seed ) if int( chat_seed ) > 0 else None,
					           'system': chat_system if str( chat_system ).strip( ) else None,
					           'response_format': 'json' if chat_json_mode else None,
					           'reasoning_effort': (
							           chat_reasoning_effort if _chat_supports_reasoning \
							                                    and chat_reasoning \
							                                    and chat_reasoning_effort else None),
					           'web_search': bool( chat_web_search ),
					           'search_domains': chat_domains_list if chat_domains_list else None,
					           'store': bool( chat_store ), 'stream': bool( chat_stream ),
					           'parallel_tool_calls': True, 'tool_choice': 'auto', }
					
					params = { key: value for key, value in params.items( ) if value is not None }
					
					result = invoke_provider( fetcher, chat_prompt, params )
					_promote_generation_result( provider='ChatGPT', result=result )
				
				except Exception as exc:
					st.error( str( exc ) )
		
		# ---- Expander Groq
		with st.expander( label='Grok', expanded=False ):
			GROK_REASONING_EFFORTS = [ 'none', 'low', 'medium', 'high' ]
			
			def _clear_grok_state( ) -> None:
				st.session_state[ 'grok_clear_request' ] = True
				_clear_generation_result( 'Grok' )
			
			def _normalize_grok_domains( value: object ) -> list[ str ]:
				text = str( value or '' ).strip( )
				
				if not text:
					return [ ]
				
				values: list[ str ] = [ ]
				entries = re.split( r'[\n,;]+', text )
				
				for entry in entries:
					domain = str( entry or '' ).strip( ).lower( )
					
					if not domain:
						continue
					
					domain = re.sub( r'^https?://', '', domain )
					domain = domain.split( '/' )[ 0 ]
					domain = re.sub( r':\d+$', '', domain )
					domain = domain.lstrip( '.' )
					
					if domain.startswith( 'www.' ):
						domain = domain[ 4: ]
					
					if not re.fullmatch( r'[a-z0-9][a-z0-9.-]*\.[a-z]{2,}', domain ):
						raise ValueError( f'Invalid Grok web-search domain: {domain}' )
					
					if domain not in values:
						values.append( domain )
				
				if len( values ) > 5:
					raise ValueError(
						'xAI web-search allowed domains are limited to five domains.' )
				
				return values
			
			def _normalize_grok_stop_lines( value: object ) -> List[ str ]:
				text = str( value or '' )
				if not text.strip( ):
					return [ ]
				
				return [ line.strip( ) for line in text.splitlines( ) if line.strip( ) ]
			
			if 'grok_clear_request' not in st.session_state:
				st.session_state[ 'grok_clear_request' ] = False
			
			if 'groq_prompt_chat' not in st.session_state:
				st.session_state[ 'groq_prompt_chat' ] = ''
			
			if 'groq_system_chat' not in st.session_state:
				st.session_state[ 'groq_system_chat' ] = ''
			
			if 'groq_domains_chat' not in st.session_state:
				st.session_state[ 'groq_domains_chat' ] = ''
			
			if 'groq_stop_chat' not in st.session_state:
				st.session_state[ 'groq_stop_chat' ] = ''
			
			if 'groq_json_mode_chat' not in st.session_state:
				st.session_state[ 'groq_json_mode_chat' ] = False
			
			if 'groq_reasoning_chat' not in st.session_state:
				st.session_state[ 'groq_reasoning_chat' ] = False
			
			if 'groq_web_search_chat' not in st.session_state:
				st.session_state[ 'groq_web_search_chat' ] = False
			
			if 'groq_store_chat' not in st.session_state:
				st.session_state[ 'groq_store_chat' ] = True
			
			if 'groq_stream_chat' not in st.session_state:
				st.session_state[ 'groq_stream_chat' ] = False
			
			if 'groq_seed_chat' not in st.session_state:
				st.session_state[ 'groq_seed_chat' ] = 0
			
			if st.session_state.get( 'groq_reasoning_effort_chat',
					'low' ) not in GROK_REASONING_EFFORTS:
				st.session_state[ 'groq_reasoning_effort_chat' ] = 'low'
			
			if st.session_state.get( 'grok_clear_request', False ):
				st.session_state[ 'groq_prompt_chat' ] = ''
				st.session_state[ 'groq_system_chat' ] = ''
				st.session_state[ 'groq_domains_chat' ] = ''
				st.session_state[ 'groq_stop_chat' ] = ''
				st.session_state[ 'groq_json_mode_chat' ] = False
				st.session_state[ 'groq_reasoning_chat' ] = False
				st.session_state[ 'groq_web_search_chat' ] = False
				st.session_state[ 'groq_store_chat' ] = True
				st.session_state[ 'groq_stream_chat' ] = False
				st.session_state[ 'groq_seed_chat' ] = 0
				st.session_state[ 'groq_reasoning_effort_chat' ] = 'low'
				st.session_state[ 'grok_clear_request' ] = False
			
			groq_prompt = st.text_area( 'Prompt',
				value=st.session_state.get( 'groq_prompt_chat', '' ), height=120,
				key='groq_prompt_chat', )
			
			p_row1 = st.columns( 2 )
			p_row2 = st.columns( 2 )
			p_row3 = st.columns( 2 )
			p_row4 = st.columns( 2 )
			p_row5 = st.columns( 2 )
			with p_row1[ 0 ]:
				_grok_models = cfg.GROK_MODELS
				groq_model = _model_selector( key_prefix='groq', label='Model',
					options=_grok_models, default_model=(
							'grok-4.3' if 'grok-4.3' in _grok_models else _grok_models[ 0 ]), )
			
			with p_row1[ 1 ]:
				groq_temperature = st.slider( 'Temperature', min_value=0.0, max_value=2.0,
					value=0.7, step=0.05, key='groq_temperature_chat', )
			
			with p_row2[ 0 ]:
				groq_max_tokens = st.number_input( 'Max Tokens', min_value=1, max_value=32768,
					value=2048, step=1, key='groq_max_tokens_chat', )
			
			with p_row2[ 1 ]:
				groq_top_p = st.slider( 'Top-P', min_value=0.0, max_value=1.0, value=1.0, step=0.01,
					key='groq_top_p_chat', )
			
			with p_row3[ 0 ]:
				groq_seed = st.number_input( 'Seed', min_value=0, max_value=2_147_483_647,
					value=int( st.session_state.get( 'groq_seed_chat', 0 ) ), step=1,
					key='groq_seed_chat', help='Use 0 to omit the seed parameter.' )
			
			with p_row3[ 1 ]:
				groq_json_mode = st.checkbox( 'JSON Mode',
					value=bool( st.session_state.get( 'groq_json_mode_chat', False ) ),
					key='groq_json_mode_chat',
					help='Adds JSON-only instructions through the current Grok wrapper.' )
			
			with p_row4[ 0 ]:
				groq_reasoning = st.checkbox( 'Reasoning',
					value=bool( st.session_state.get( 'groq_reasoning_chat', False ) ),
					key='groq_reasoning_chat' )
			
			with p_row4[ 1 ]:
				groq_web_search = st.checkbox( 'Web Search',
					value=bool( st.session_state.get( 'groq_web_search_chat', False ) ),
					key='groq_web_search_chat' )
			
			with p_row5[ 0 ]:
				groq_store = st.checkbox( 'Store',
					value=bool( st.session_state.get( 'groq_store_chat', True ) ),
					key='groq_store_chat' )
			
			with p_row5[ 1 ]:
				groq_stream = st.checkbox( 'Stream',
					value=bool( st.session_state.get( 'groq_stream_chat', False ) ),
					key='groq_stream_chat' )
			
			_groq_model_name = str( groq_model or '' ).strip( ).lower( )
			_groq_is_reasoning_model = (
					'reasoning' in _groq_model_name or _groq_model_name.startswith(
				'grok-4' ) or _groq_model_name.startswith(
				'grok-4.3' ) or _groq_model_name.startswith( 'grok-4.20' ))
			
			_groq_supports_reasoning_effort = (
					_groq_model_name == 'grok-4.3' or _groq_model_name == 'grok-4.20-multi-agent')
			
			if _groq_supports_reasoning_effort and groq_reasoning:
				groq_reasoning_effort = st.selectbox( 'Reasoning Effort',
					options=GROK_REASONING_EFFORTS, index=GROK_REASONING_EFFORTS.index(
						st.session_state.get( 'groq_reasoning_effort_chat', 'low' ) ),
					key='groq_reasoning_effort_chat' )
			else:
				groq_reasoning_effort = None
			
			groq_system = st.text_area( 'System',
				value=st.session_state.get( 'groq_system_chat', '' ), height=120,
				key='groq_system_chat' )
			
			if groq_web_search:
				groq_domains = st.text_area( 'Allowed Search Domains',
					value=st.session_state.get( 'groq_domains_chat', '' ), height=90,
					key='groq_domains_chat',
					help='Optional. xAI allows up to five allowed domains.' )
			else:
				groq_domains = ''
			
			groq_stop = st.text_area( 'Stop Sequences',
				value=st.session_state.get( 'groq_stop_chat', '' ), height=80, key='groq_stop_chat',
				disabled=_groq_is_reasoning_model, help='One stop sequence per line. Disabled for '
				                                        'reasoning models.' )
			
			btn_row = st.columns( 2 )
			with btn_row[ 0 ]:
				groq_submit = st.button( 'Submit', key='groq_submit' )
			
			with btn_row[ 1 ]:
				st.button( 'Clear', key='groq_clear', on_click=_clear_grok_state )
			
			# Submit Button
			if groq_submit:
				try:
					if not str( groq_prompt or '' ).strip( ):
						raise ValueError( 'Prompt cannot be empty.' )
					
					if groq_json_mode:
						has_json_instruction = (
								'json' in str( groq_prompt or '' ).lower( ) or 'json' in str(
							groq_system or '' ).lower( ))
						
						if not has_json_instruction:
							groq_system = (
									str( groq_system or '' ).strip( ) + '\n\nReturn valid JSON '
									                                    'only.').strip( )
					
					groq_domains_list = (
							_normalize_grok_domains( groq_domains ) if groq_web_search else [ ])
					
					stop_lines = _normalize_grok_stop_lines( groq_stop )
					
					if stop_lines and _groq_is_reasoning_model:
						stop_lines = [ ]
					
					fetcher = Grok( )
					params = { 'model': groq_model, 'temperature': float( groq_temperature ),
					           'max_tokens': int( groq_max_tokens ), 'top_p': float( groq_top_p ),
					           'seed': int( groq_seed ) if int( groq_seed ) > 0 else None,
					           'system': groq_system if str( groq_system ).strip( ) else None,
					           'response_format': 'json' if groq_json_mode else None,
					           'reasoning_effort': (
							           groq_reasoning_effort if _groq_supports_reasoning_effort \
							                                    and groq_reasoning \
							                                    and groq_reasoning_effort else None),
					           'web_search': bool( groq_web_search ),
					           'search_domains': groq_domains_list if groq_domains_list else None,
					           'stop': stop_lines if stop_lines else None,
					           'stream': bool( groq_stream ), 'store': bool( groq_store ),
					           'parallel_tool_calls': True, 'tool_choice': 'auto', }
					
					params = { key: value for key, value in params.items( ) if value is not None }
					result = invoke_provider( fetcher, groq_prompt, params )
					_promote_generation_result( provider='Grok', result=result )
				
				except Exception as exc:
					st.error( str( exc ) )
		
		# ---- Expander Claude
		with st.expander( label='Claude', expanded=False ):
			def _clear_claude_state( ) -> None:
				'''
					Purpose:
					--------
					Flag the Claude generation state for reset on the next rerun.

					Parameters:
					-----------
					None

					Returns:
					--------
					None
				'''
				st.session_state[ 'claude_clear_request' ] = True
				_clear_generation_result( 'Claude' )
			
			def _normalize_claude_domains( value: object ) -> list[ str ]:
				'''
					Purpose:
					--------
					Normalize newline-, comma-, or semicolon-delimited Claude web-search
					domain entries.

					Parameters:
					-----------
					value (object):
						Domain text supplied by the user.

					Returns:
					--------
					list[str]:
						Canonical, de-duplicated domain names.
				'''
				text = str( value or '' ).strip( )
				
				if not text:
					return [ ]
				
				values: list[ str ] = [ ]
				entries = re.split( r'[\n,;]+', text )
				
				for entry in entries:
					raw_value = str( entry or '' ).strip( ).lower( )
					
					if not raw_value:
						continue
					
					if not raw_value.startswith( 'http://' ) and not raw_value.startswith(
							'https://' ):
						raw_value = f'https://{raw_value}'
					
					parsed = urlparse( raw_value )
					domain = (parsed.netloc or parsed.path or '').strip( ).lower( )
					domain = re.sub( r':\d+$', '', domain )
					domain = domain.lstrip( '.' )
					
					if domain.startswith( 'www.' ):
						domain = domain[ 4: ]
					
					if not re.fullmatch( r'[a-z0-9][a-z0-9.-]*\.[a-z]{2,}', domain ):
						raise ValueError( f'Invalid Claude web-search domain: {domain}' )
					
					if domain not in values:
						values.append( domain )
				
				return values
			
			def _normalize_claude_stop_lines( value: object ) -> list[ str ]:
				'''
					Purpose:
					--------
					Normalize stop sequences entered one per line.

					Parameters:
					-----------
					value (object):
						Stop-sequence textarea value.

					Returns:
					--------
					list[str]:
						Non-empty stop sequences.
				'''
				text = str( value or '' )
				
				if not text.strip( ):
					return [ ]
				
				return [ line.strip( ) for line in text.splitlines( ) if line.strip( ) ]
			
			if 'claude_clear_request' not in st.session_state:
				st.session_state[ 'claude_clear_request' ] = False
			
			if 'claude_prompt_chat' not in st.session_state:
				st.session_state[ 'claude_prompt_chat' ] = ''
			
			if 'claude_system_chat' not in st.session_state:
				st.session_state[ 'claude_system_chat' ] = ''
			
			if 'claude_stop_chat' not in st.session_state:
				st.session_state[ 'claude_stop_chat' ] = ''
			
			if 'claude_domains_chat' not in st.session_state:
				st.session_state[ 'claude_domains_chat' ] = ''
			
			if 'claude_blocked_domains_chat' not in st.session_state:
				st.session_state[ 'claude_blocked_domains_chat' ] = ''
			
			if 'claude_thinking_chat' not in st.session_state:
				st.session_state[ 'claude_thinking_chat' ] = False
			
			if 'claude_web_search_chat' not in st.session_state:
				st.session_state[ 'claude_web_search_chat' ] = False
			
			if 'claude_thinking_budget_chat' not in st.session_state:
				st.session_state[ 'claude_thinking_budget_chat' ] = 1024
			
			if st.session_state.get( 'claude_clear_request', False ):
				st.session_state[ 'claude_prompt_chat' ] = ''
				st.session_state[ 'claude_system_chat' ] = ''
				st.session_state[ 'claude_stop_chat' ] = ''
				st.session_state[ 'claude_domains_chat' ] = ''
				st.session_state[ 'claude_blocked_domains_chat' ] = ''
				st.session_state[ 'claude_thinking_chat' ] = False
				st.session_state[ 'claude_web_search_chat' ] = False
				st.session_state[ 'claude_thinking_budget_chat' ] = 1024
				st.session_state[ 'claude_clear_request' ] = False
			
			claude_prompt = st.text_area( 'Prompt',
				value=st.session_state.get( 'claude_prompt_chat', '' ), height=140,
				key='claude_prompt_chat', )
			
			# Model / Output Controls
			model_row = st.columns( [ 0.55, 0.45 ] )
			
			with model_row[ 0 ]:
				_claude_models = cfg.CLAUDE_MODELS
				claude_model = _model_selector( key_prefix='claude', label='Model',
					options=_claude_models, default_model=(
							'claude-sonnet-4-6' if 'claude-sonnet-4-6' in _claude_models else
							_claude_models[ 0 ]), )
			
			with model_row[ 1 ]:
				claude_max_tokens = st.number_input( 'Max Tokens', min_value=1, max_value=65536,
					value=2048, step=1, key='claude_max_tokens_chat', )
			
			# Sampling Controls
			sampling_row = st.columns( 3 )
			
			with sampling_row[ 0 ]:
				claude_temperature = st.slider( 'Temperature', min_value=0.0, max_value=1.0,
					value=0.7, step=0.05, key='claude_temperature_chat', )
			
			with sampling_row[ 1 ]:
				claude_top_p = st.slider( 'Top-P', min_value=0.0, max_value=1.0, value=1.0,
					step=0.01, key='claude_top_p_chat', )
			
			with sampling_row[ 2 ]:
				claude_top_k = st.number_input( 'Top-k', min_value=0, max_value=500, value=0,
					step=1, key='claude_top_k_chat', )
			
			# Feature Toggles
			option_row = st.columns( 2 )
			with option_row[ 0 ]:
				claude_thinking = st.checkbox( 'Reasoning',
					value=bool( st.session_state.get( 'claude_thinking_chat', False ) ),
					key='claude_thinking_chat',
					help='Anthropic exposes this as extended thinking with a token budget.', )
			
			with option_row[ 1 ]:
				claude_web_search = st.checkbox( 'Web Search',
					value=bool( st.session_state.get( 'claude_web_search_chat', False ) ),
					key='claude_web_search_chat', )
			
			# Reasoning Budget
			if claude_thinking and int( claude_max_tokens ) <= 1024:
				st.warning( 'Max Tokens must exceed 1024 for Claude reasoning.' )
				claude_thinking_budget = None
			elif claude_thinking:
				claude_thinking_budget = st.number_input( 'Thinking Budget', min_value=1024,
					max_value=max( 1024, int( claude_max_tokens ) - 1 ),
					value=min( int( st.session_state.get( 'claude_thinking_budget_chat', 1024 ) ),
						max( 1024, int( claude_max_tokens ) - 1 ) ), step=1024,
					key='claude_thinking_budget_chat', help='Must be less than Max Tokens.' )
			else:
				claude_thinking_budget = None
			
			# Instruction Controls
			claude_system = st.text_area( 'System',
				value=st.session_state.get( 'claude_system_chat', '' ), height=110,
				key='claude_system_chat', )
			
			claude_stop = st.text_area( 'Stop Sequences (one per line)',
				value=st.session_state.get( 'claude_stop_chat', '' ), height=80,
				key='claude_stop_chat', )
			
			# Web Search Controls
			if claude_web_search:
				search_row = st.columns( 2 )
				
				with search_row[ 0 ]:
					claude_domains = st.text_area( 'Allowed Search Domains',
						value=st.session_state.get( 'claude_domains_chat', '' ), height=90,
						key='claude_domains_chat',
						help='Optional allowlist, one domain per line or comma-separated.' )
				
				with search_row[ 1 ]:
					claude_blocked_domains = st.text_area( 'Blocked Search Domains',
						value=st.session_state.get( 'claude_blocked_domains_chat', '' ), height=90,
						key='claude_blocked_domains_chat',
						help='Optional blocklist one domain per line or comma-separated.' )
			else:
				claude_domains = ''
				claude_blocked_domains = ''
			
			# -----------------------------
			# Action Controls
			# -----------------------------
			btn_row = st.columns( 2 )
			
			with btn_row[ 0 ]:
				claude_submit = st.button( 'Submit', key='claude_submit_chat',
					use_container_width=True )
			
			with btn_row[ 1 ]:
				st.button( 'Clear', key='claude_clear_chat', on_click=_clear_claude_state,
					use_container_width=True )
				
			# Submit Button
			if claude_submit:
				try:
					throw_if( 'claude_prompt', claude_prompt )
					if not str( claude_prompt ).strip( ):
						raise ValueError( 'Prompt cannot be empty.' )
					if claude_thinking and int( claude_max_tokens ) <= 1024:
						raise ValueError( 'Max Tokens must exceed 1024 for Claude reasoning.' )
					if claude_thinking and int( claude_thinking_budget ) >= int( claude_max_tokens ):
						raise ValueError( 'Thinking Budget must be less than Max Tokens.' )
					fetcher = Claude( )
					params = {
						'model': claude_model,
						'temperature': float( claude_temperature ),
						'max_tokens': int( claude_max_tokens ),
						'top_p': float( claude_top_p ),
						'top_k': int( claude_top_k ) if int( claude_top_k ) > 0 else None,
						'system': claude_system.strip( ) or None,
						'stop_sequences': _normalize_claude_stop_lines( claude_stop ) or None,
						'thinking': bool( claude_thinking ),
						'thinking_budget': int( claude_thinking_budget ) if claude_thinking else None,
						'web_search': bool( claude_web_search ),
						'search_domains': _normalize_claude_domains( claude_domains ) if claude_web_search else None,
						'blocked_domains': _normalize_claude_domains( claude_blocked_domains ) if claude_web_search else None,
					}
					with st.spinner( 'Generating Claude response...' ):
						result = invoke_provider( fetcher, claude_prompt, params )
					_promote_generation_result( 'Claude', result )
					st.success( 'Claude response generated.' )
				except Exception as ex:
					st.error( f'Claude generation failed: {ex}' )

		# ---- Expander GEMINI
		with st.expander( label='Gemini', expanded=False ):
			GEMINI_THINKING_LEVELS = [ 'minimal', 'low', 'medium', 'high' ]
			
			def _clear_gemini_state( ) -> None:
				st.session_state[ 'gemini_clear_request' ] = True
				_clear_generation_result( 'Gemini' )
			
			def _normalize_gemini_domains( value: object ) -> list[ str ]:
				text = str( value or '' ).strip( )
				
				if not text:
					return [ ]
				
				values: list[ str ] = [ ]
				entries = re.split( r'[\n,;]+', text )
				
				for entry in entries:
					raw_value = str( entry or '' ).strip( ).lower( )
					
					if not raw_value:
						continue
					
					if not raw_value.startswith( 'http://' ) and not raw_value.startswith(
							'https://' ):
						raw_value = f'https://{raw_value}'
					
					parsed = urlparse( raw_value )
					domain = (parsed.netloc or parsed.path or '').strip( ).lower( )
					domain = re.sub( r':\d+$', '', domain )
					domain = domain.lstrip( '.' )
					
					if domain.startswith( 'www.' ):
						domain = domain[ 4: ]
					
					if not re.fullmatch( r'[a-z0-9][a-z0-9.-]*\.[a-z]{2,}', domain ):
						raise ValueError( f'Invalid Gemini grounding domain: {domain}' )
					
					if domain not in values:
						values.append( domain )
				
				return values
			
			def _normalize_gemini_stop_lines( value: object ) -> list[ str ]:
				text = str( value or '' )
				
				if not text.strip( ):
					return [ ]
				
				return [ line.strip( ) for line in text.splitlines( ) if line.strip( ) ]
			
			if 'gemini_clear_request' not in st.session_state:
				st.session_state[ 'gemini_clear_request' ] = False
			
			if 'gemini_prompt_chat' not in st.session_state:
				st.session_state[ 'gemini_prompt_chat' ] = ''
			
			if 'gemini_system_chat' not in st.session_state:
				st.session_state[ 'gemini_system_chat' ] = ''
			
			if 'gemini_domains_chat' not in st.session_state:
				st.session_state[ 'gemini_domains_chat' ] = ''
			
			if 'gemini_stop_chat' not in st.session_state:
				st.session_state[ 'gemini_stop_chat' ] = ''
			
			if 'gemini_json_mode_chat' not in st.session_state:
				st.session_state[ 'gemini_json_mode_chat' ] = False
			
			if 'gemini_grounding_chat' not in st.session_state:
				st.session_state[ 'gemini_grounding_chat' ] = False
			
			if 'gemini_reasoning_chat' not in st.session_state:
				st.session_state[ 'gemini_reasoning_chat' ] = False
			
			if 'gemini_include_thoughts_chat' not in st.session_state:
				st.session_state[ 'gemini_include_thoughts_chat' ] = False
			
			if 'gemini_seed_chat' not in st.session_state:
				st.session_state[ 'gemini_seed_chat' ] = 0
			
			if st.session_state.get( 'gemini_thinking_level_chat',
					'low' ) not in GEMINI_THINKING_LEVELS:
				st.session_state[ 'gemini_thinking_level_chat' ] = 'low'
			
			if st.session_state.get( 'gemini_clear_request', False ):
				st.session_state[ 'gemini_prompt_chat' ] = ''
				st.session_state[ 'gemini_system_chat' ] = ''
				st.session_state[ 'gemini_domains_chat' ] = ''
				st.session_state[ 'gemini_stop_chat' ] = ''
				st.session_state[ 'gemini_json_mode_chat' ] = False
				st.session_state[ 'gemini_grounding_chat' ] = False
				st.session_state[ 'gemini_reasoning_chat' ] = False
				st.session_state[ 'gemini_include_thoughts_chat' ] = False
				st.session_state[ 'gemini_seed_chat' ] = 0
				st.session_state[ 'gemini_thinking_level_chat' ] = 'low'
				st.session_state[ 'gemini_clear_request' ] = False
			
			gemini_prompt = st.text_area( 'Prompt',
				value=st.session_state.get( 'gemini_prompt_chat', '' ), height=160,
				key='gemini_prompt_chat', )
			
			p_row1 = st.columns( 2 )
			p_row2 = st.columns( 2 )
			p_row3 = st.columns( 2 )
			p_row4 = st.columns( 2 )
			p_row5 = st.columns( 2 )
			
			with p_row1[ 0 ]:
				_gemini_models = cfg.GEMINI_MODELS
				gemini_model = _model_selector( key_prefix='gemini', label='Model',
					options=_gemini_models, default_model='gemini-2.5-flash' )
			
			with p_row1[ 1 ]:
				gemini_temperature = st.slider( 'Temperature', min_value=0.0, max_value=2.0,
					value=0.7, step=0.05, key='gemini_temperature_chat', )
			
			with p_row2[ 0 ]:
				gemini_max_tokens = st.number_input( 'Max Tokens', min_value=1, max_value=32768,
					value=2048, step=1, key='gemini_max_tokens_chat', )
			
			with p_row2[ 1 ]:
				gemini_top_p = st.slider( 'Top-p', min_value=0.0, max_value=1.0, value=1.0,
					step=0.01, key='gemini_top_p_chat', )
			
			with p_row3[ 0 ]:
				gemini_top_k = st.number_input( 'Top-k', min_value=0, max_value=500, value=0,
					step=1, key='gemini_top_k_chat', )
			
			with p_row3[ 1 ]:
				gemini_candidate_count = st.number_input( 'Candidates', min_value=1, max_value=8,
					value=1, step=1, key='gemini_candidate_count_chat', )
			
			with p_row4[ 0 ]:
				gemini_seed = st.number_input( 'Seed', min_value=0, max_value=2_147_483_647,
					value=int( st.session_state.get( 'gemini_seed_chat', 0 ) ), step=1,
					key='gemini_seed_chat', help='Use 0 to omit the seed parameter.' )
			
			with p_row4[ 1 ]:
				gemini_json_mode = st.checkbox( 'JSON Mode',
					value=bool( st.session_state.get( 'gemini_json_mode_chat', False ) ),
					key='gemini_json_mode_chat',
					help='Requests JSON output through the current Gemini wrapper.' )
			
			with p_row5[ 0 ]:
				gemini_grounding = st.checkbox( 'Grounding',
					value=bool( st.session_state.get( 'gemini_grounding_chat', False ) ),
					key='gemini_grounding_chat',
					help='Enable Google Search grounding for supported Gemini models.' )
			
			with p_row5[ 1 ]:
				gemini_reasoning = st.checkbox( 'Reasoning',
					value=bool( st.session_state.get( 'gemini_reasoning_chat', False ) ),
					key='gemini_reasoning_chat',
					help='Uses Gemini thinking configuration where supported.' )
			
			_gemini_model_name = str( gemini_model or '' ).strip( ).lower( )
			_gemini_supports_thinking_level = _gemini_model_name.startswith( 'gemini-3' )
			_gemini_supports_thinking_budget = _gemini_model_name.startswith( 'gemini-2.5' )
			
			if _gemini_supports_thinking_level and gemini_reasoning:
				r_row = st.columns( 2 )
				
				with r_row[ 0 ]:
					gemini_thinking_level = st.selectbox( 'Thinking Level',
						options=GEMINI_THINKING_LEVELS, index=GEMINI_THINKING_LEVELS.index(
							st.session_state.get( 'gemini_thinking_level_chat', 'low' ) ),
						key='gemini_thinking_level_chat', )
				
				with r_row[ 1 ]:
					gemini_include_thoughts = st.checkbox( 'Include Thoughts',
						value=bool( st.session_state.get( 'gemini_include_thoughts_chat', False ) ),
						key='gemini_include_thoughts_chat', )
			else:
				gemini_thinking_level = None
				gemini_include_thoughts = False
			
			if gemini_reasoning and _gemini_supports_thinking_budget:
				st.caption( 'Gemini 2.5 models use thinking_budget, but the current Gemini '
				            'generator only exposes thinking_level. This UI preserves the '
				            'current wrapper contract until the Gemini class is updated.' )
			
			if gemini_reasoning and not (
					_gemini_supports_thinking_level or _gemini_supports_thinking_budget):
				st.caption( 'Reasoning controls are only sent for Gemini 3 model names under '
				            'the current wrapper contract.' )
			
			gemini_stop = st.text_area( 'Stop Sequences (one per line)',
				value=st.session_state.get( 'gemini_stop_chat', '' ), height=80,
				key='gemini_stop_chat', )
			
			gemini_system = st.text_area( 'System',
				value=st.session_state.get( 'gemini_system_chat', '' ), height=110,
				key='gemini_system_chat', )
			
			if gemini_grounding:
				gemini_domains = st.text_area(
					'Preferred Search Domains (one per line or comma-separated)',
					value=st.session_state.get( 'gemini_domains_chat', '' ), height=90,
					key='gemini_domains_chat',
					help='Used as preferred source guidance for grounded Gemini responses.' )
			else:
				gemini_domains = ''
			
			btn_row = st.columns( 2 )
			with btn_row[ 0 ]:
				gemini_submit = st.button( 'Submit', key='gemini_submit_chat' )
			
			with btn_row[ 1 ]:
				st.button( 'Clear', key='gemini_clear_chat', on_click=_clear_gemini_state )
			
			# ------ Submit Button
			if gemini_submit:
				try:
					if not str( gemini_prompt or '' ).strip( ):
						raise ValueError( 'Prompt cannot be empty.' )
					
					if gemini_json_mode:
						has_json_instruction = (
								'json' in str( gemini_prompt or '' ).lower( ) or 'json' in str(
							gemini_system or '' ).lower( ))
						
						if not has_json_instruction:
							gemini_system = (
									str( gemini_system or '' ).strip( ) + '\n\nReturn valid JSON '
									                                      'only.').strip( )
					
					gemini_domains_list = (_normalize_gemini_domains(
						gemini_domains ) if gemini_grounding else [ ])
					
					stop_lines = _normalize_gemini_stop_lines( gemini_stop )
					fetcher = Gemini( )
					params = { 'model': gemini_model, 'temperature': float( gemini_temperature ),
					           'max_tokens': int( gemini_max_tokens ),
					           'top_p': float( gemini_top_p ),
					           'top_k': int( gemini_top_k ) if int( gemini_top_k ) > 0 else None,
					           'candidate_count': int( gemini_candidate_count ),
					           'seed': int( gemini_seed ) if int( gemini_seed ) > 0 else None,
					           'system': (gemini_system if str(
						           gemini_system or '' ).strip( ) else None),
					           'response_format': 'json' if gemini_json_mode else None,
					           'stop_sequences': stop_lines if stop_lines else None,
					           'grounding': bool( gemini_grounding ), 'search_domains': (
									gemini_domains_list if gemini_domains_list else None),
					           'reasoning': bool(
						           gemini_reasoning and _gemini_supports_thinking_level ),
					           'thinking_level': (
							           gemini_thinking_level if _gemini_supports_thinking_level \
							                                    and gemini_reasoning else None),
					           'include_thoughts': bool(
						           gemini_include_thoughts ) if _gemini_supports_thinking_level \
					                                            and gemini_reasoning else False, }
					
					params = { key: value for key, value in params.items( ) if value is not None }
					
					result = invoke_provider( fetcher, gemini_prompt, params )
					_promote_generation_result( provider='Gemini', result=result )
				
				except Exception as exc:
					st.error( str( exc ) )
		
		# ---- Expander Mistral
		with st.expander( label='Mistral', expanded=False ):
			def _clear_mistral_state( ) -> None:
				st.session_state[ 'mistral_clear_request' ] = True
				_clear_generation_result( 'Mistral' )
			
			if 'mistral_clear_request' not in st.session_state:
				st.session_state[ 'mistral_clear_request' ] = False
			
			if 'mistral_prompt_chat' not in st.session_state:
				st.session_state[ 'mistral_prompt_chat' ] = ''
			
			if 'mistral_system_chat' not in st.session_state:
				st.session_state[ 'mistral_system_chat' ] = ''
			
			if 'mistral_safe_mode_chat' not in st.session_state:
				st.session_state[ 'mistral_safe_mode_chat' ] = False
			
			if 'mistral_seed_chat' not in st.session_state:
				st.session_state[ 'mistral_seed_chat' ] = 0
			
			if st.session_state.get( 'mistral_clear_request', False ):
				st.session_state[ 'mistral_prompt_chat' ] = ''
				st.session_state[ 'mistral_system_chat' ] = ''
				st.session_state[ 'mistral_safe_mode_chat' ] = False
				st.session_state[ 'mistral_seed_chat' ] = 0
				st.session_state[ 'mistral_clear_request' ] = False
			
			mistral_prompt = st.text_area( 'Prompt',
				value=st.session_state.get( 'mistral_prompt_chat', '' ), height=120,
				key='mistral_prompt_chat' )
			
			p_row1 = st.columns( 2 )
			p_row2 = st.columns( 2 )
			p_row3 = st.columns( 2 )
			with p_row1[ 0 ]:
				_mistral_models = (cfg.MISTRAL_MODELS if hasattr( cfg,
					'MISTRAL_MODELS' ) and cfg.MISTRAL_MODELS else [ 'mistral-large-latest',
				                                                     'mistral-medium-latest',
				                                                     'mistral-small-latest',
				                                                     'open-mistral-7b',
				                                                     'Custom...', ])
				
				mistral_model = _model_selector( key_prefix='mistral', label='Model',
					options=_mistral_models, default_model=(
							'mistral-large-latest' if 'mistral-large-latest' in _mistral_models else
							_mistral_models[ 0 ]), )
			
			with p_row1[ 1 ]:
				mistral_temperature = st.slider( 'Temperature', min_value=0.0, max_value=2.0,
					value=0.7, step=0.05, key='mistral_temperature_chat',
					help='Mistral recommends tuning temperature or top-p not both.' )
			
			with p_row2[ 0 ]:
				mistral_max_tokens = st.number_input( 'Max Tokens', min_value=1, max_value=32768,
					value=1024, step=1, key='mistral_max_tokens_chat', )
			
			with p_row2[ 1 ]:
				mistral_top_p = st.slider( 'Top-p', min_value=0.0, max_value=1.0, value=1.0,
					step=0.01, key='mistral_top_p_chat',
					help='Mistral recommends tuning temperature or top-p, not both.' )
			
			with p_row3[ 0 ]:
				mistral_seed = st.number_input( 'Seed', min_value=0, max_value=2_147_483_647,
					value=int( st.session_state.get( 'mistral_seed_chat', 0 ) ), step=1,
					key='mistral_seed_chat', help='Use 0 to omit random_seed.' )
			
			with p_row3[ 1 ]:
				mistral_safe_mode = st.checkbox( 'Safe Mode',
					value=bool( st.session_state.get( 'mistral_safe_mode_chat', False ) ),
					key='mistral_safe_mode_chat',
					help='Maps to Mistral safe_prompt in the current wrapper.' )
			
			mistral_system = st.text_area( 'System',
				value=st.session_state.get( 'mistral_system_chat', '' ), height=100,
				key='mistral_system_chat', )
			
			st.caption( 'The current Mistral wrapper supports text output only. JSON mode and '
			            'stop sequences require a later complete Mistral class replacement.' )
			
			btn_row = st.columns( 2 )
			with btn_row[ 0 ]:
				mistral_submit = st.button( 'Submit', key='mistral_submit_chat' )
			
			with btn_row[ 1 ]:
				st.button( 'Clear', key='mistral_clear_chat', on_click=_clear_mistral_state )
			
			if mistral_submit:
				try:
					if not str( mistral_prompt or '' ).strip( ):
						raise ValueError( 'Prompt cannot be empty.' )
					
					if float( mistral_temperature ) > 0.0 and float( mistral_top_p ) < 1.0:
						st.warning( 'Mistral recommends adjusting either temperature or top-p, '
						            'but not both, for most use cases.' )
					
					fetcher = Mistral( )
					params = { 'model': mistral_model, 'temperature': float( mistral_temperature ),
					           'max_tokens': int( mistral_max_tokens ),
					           'top_p': float( mistral_top_p ),
					           'seed': int( mistral_seed ) if int( mistral_seed ) > 0 else None,
					           'safe_mode': bool( mistral_safe_mode ), 'system': (
									mistral_system if str(
										mistral_system or '' ).strip( ) else None), }
					
					params = { key: value for key, value in params.items( ) if value is not None }
					
					result = invoke_provider( fetcher, mistral_prompt, params )
					_promote_generation_result( provider='Mistral', result=result )
				
				except Exception as exc:
					st.error( str( exc ) )
					
# ==============================================================================
# DATA UPLOAD
# ==============================================================================
elif mode == 'File Upload':
	left, center, right = st.columns( [ 0.05, 0.90, 0.05 ] )
	with center:
		
		# ---------- DOCUMENT UPLOAD AND PROCESSING
		with st.expander( label='Document Processing', icon='📄', expanded=False ):
			document_file = st.file_uploader( 'Upload Document',
				type=[ 'txt', 'csv', 'xlsx', 'xls', 'pdf', 'docx', 'pptx', 'md', 'html', 'htm',
				       'json', 'xml' ], key='file_upload_document' )
			loader_name = 'File Upload'
			if document_file is not None:
				if st.button( 'Load Document', key='file_upload_document_load' ):
					try:
						loaders = { '.txt': TextLoader, '.csv': CsvLoader, '.xlsx': ExcelLoader,
						            '.xls': ExcelLoader, '.pdf': PdfLoader, '.docx': WordLoader,
						            '.pptx': PowerPointLoader, '.md': MarkdownLoader,
						            '.html': HtmlLoader, '.htm': HtmlLoader, '.json': JsonLoader,
						            '.xml': XmlLoader, }
						throw_if( 'document_file', document_file )
						count = load_uploaded_document( document_file, loaders,
							promote_loader_documents )
						st.success( f'Loaded {count:,} document(s).' )
					except Exception as exc:
						st.error( f'Document loading failed: {exc}' )
			render_document_processing_controls( loader_name, 'file_upload_document' )
			render_loading_tabs( )

		st.subheader( 'Excel / CSV' )
		st.divider( )
		uploaded = st.file_uploader( 'Upload CSV or XLSX', type=[ 'csv', 'xlsx' ],
			key='data_upload_file' )
		
		enrichment_mode = st.selectbox( 'Enrichment Mode',
			options=['City / State / Country', 'Address Column'], key='data_upload_enrichment_mode')
		
		if enrichment_mode == 'City / State / Country':
			city_col = st.text_input( 'City Column', value='City', key='data_upload_city_col' )
			state_col = st.text_input( 'State Column', value='State', key='data_upload_state_col' )
			country_col = st.text_input( 'Country Column', value='Country',
				key='data_upload_country_col' )
			
			address_col = ''
		
		else:
			address_col = st.text_input( 'Address Column', value='Address',
				key='data_upload_address_col' )
			country_col = st.text_input( 'Country Bias Column', value='Country',
				help='Optional. Leave as-is if the uploaded file has no country-bias column.',
				key='data_upload_address_country_col' )
			
			city_col = ''
			state_col = ''
		
		sheet_name = st.text_input( 'Worksheet', value='Sheet1',
			help='Used for Excel files. For CSV files this value is ignored.',
			key='data_upload_sheet_name' )
		
		if uploaded:
			input_path = f'_input_{uploaded.name}'
			output_path = f'_output_{uploaded.name}'
			with open( input_path, 'wb' ) as f:
				f.write( uploaded.read( ) )
			
			if st.button( 'Enrich File', key='data_upload_enrich' ):
				try:
					excel = Excel( api=cfg.GOOGLEMAPS_API_KEY, cache=cache )
					sheet_value = sheet_name if input_path.lower( ).endswith( '.xlsx' ) else None
					if enrichment_mode == 'City / State / Country':
						excel.enrich( inpath=input_path, outpath=output_path, city=city_col,
							state=state_col, cntry=country_col, sheet=sheet_value )
					
					else:
						excel.enrich_from_address( inpath=input_path, outpath=output_path,
							address=address_col, sheet=sheet_value, cntry=country_col )
					
					if output_path.lower( ).endswith( '.csv' ):
						df_output = pd.read_csv( output_path )
					else:
						df_output = pd.read_excel( output_path )
					
					st.data_editor( df_output, key='data_upload_enriched_preview',
						use_container_width=True, disabled=True )
					
					with open( output_path, 'rb' ) as f:
						output_bytes = f.read( )
					
					st.download_button( 'Download Enriched File', data=output_bytes,
						file_name=Path( output_path ).name, key='data_upload_download' )
				
				except Exception as e:
					st.error( f'Enrichment failed: {e}' )
				
				finally:
					try:
						if os.path.exists( input_path ):
							os.remove( input_path )
						if os.path.exists( output_path ):
							os.remove( output_path )
					except Exception:
						pass
		
# ==============================================================================
# DATA MANAGEMENT MODE
# ==============================================================================
elif mode == 'Data Management':
	left, center, right = st.columns( [ 0.05, 0.90, 0.05 ] )
	with center:
		st.subheader( 'Data Management' )
		tabs = st.tabs( [ 'Import', 'Browse', 'CRUD', 'Explore', 'Filter',
		                  'Aggregate', 'Visualize', 'Geocode', 'Admin', 'SQL' ],
			on_change='rerun', key='data_management_active_tab' )
		 
		tables = list_tables( )
		if not tables:
			st.info( 'No tables available.' )
		
		# ------------------------------------------------------------------------------
		# UPLOAD TAB
		# ------------------------------------------------------------------------------
		if tabs[ 0 ].open:
			with tabs[ 0 ]:
				upl_c1, upl_c2 = st.columns( [ 0.70, 0.30 ] )
				with upl_c1:
					uploaded_file = st.file_uploader( 'Upload Excel File', type=[ 'xlsx' ] )
				with upl_c2:
					overwrite = st.checkbox( 'Overwrite existing tables', value=True )
				
				if uploaded_file:
					try:
						sheets = pd.read_excel( uploaded_file, sheet_name=None )
						with create_connection( ) as conn:
							conn.execute( 'BEGIN' )
							for sheet_name, df in sheets.items( ):
								table_name = create_identifier( sheet_name )
								if overwrite:
									conn.execute( f'DROP TABLE IF EXISTS "{table_name}"' )
							
								# --- Create Table ---
								columns = [ ]
								df.columns = [ create_identifier( c ) for c in df.columns ]
								for col in df.columns:
									sql_type = get_sqlite_type( df[ col ].dtype )
									columns.append( f'"{col}" {sql_type}' )
							
								create_stmt = ( f'CREATE TABLE "{table_name}" '
										f'({", ".join( columns )});' )
							
								conn.execute( create_stmt )
							
								# --- Insert Data ---
								placeholders = ", ".join( [ "?" ] * len( df.columns ) )
								insert_stmt = (
										f'INSERT INTO "{table_name}" '
										f'VALUES ({placeholders});' )
							
								conn.executemany( insert_stmt,
									df.where( pd.notnull( df ), None ).values.tolist( ) )
						
							conn.commit( )
					
						st.success( 'Import completed successfully (transaction committed).' )
						st.rerun( )
					except Exception as e:
						try:
							conn.rollback( )
						except:
							pass
						st.error( f'Import failed — transaction rolled back.\n\n{e}' )
		
			# ------------------------------------------------------------------------------
			# BROWSE TAB
			# ------------------------------------------------------------------------------
		if tabs[ 1 ].open:
			with tabs[ 1 ]:
				tables = list_tables( )
				if tables:
					table = st.selectbox( 'Table', tables, key='table_name' )
				
					blue_divider( )
				
					df = read_table( table )
					st.data_editor( df, key='dm_browse_key' )
				else:
					st.info( 'No tables available.' )
		
			# ------------------------------------------------------------------------------
			# CRUD
			# ------------------------------------------------------------------------------
		if tabs[ 2 ].open:
			with tabs[ 2 ]:
				tables = list_tables( )
				if not tables:
					st.info( 'No tables available.' )
				else:
					crud_header_c1, crud_header_c2, crud_header_c3 = st.columns( [ 0.45, 0.25, 0.30 ],
						border=True )
				
					with crud_header_c1:
						table = st.selectbox( 'Select Table', tables, key='crud_table' )
				
					df = read_table( table )
					schema = create_schema( table )
				
					type_map = { col[ 1 ]: col[ 2 ].upper( ) for col in schema if col[ 1 ] != 'rowid' }
				
					with crud_header_c2:
						st.metric( 'Rows', len( df.index ) )
				
					with crud_header_c3:
						st.metric( 'Columns', len( type_map ) )
				
					blue_divider( )
				
					insert_col, update_col = st.columns( [ 0.50, 0.50 ], border=True )
				
					# ------------------------------------------------------------------
					# INSERT
					# ------------------------------------------------------------------
					with insert_col:
						st.markdown( '##### Insert Row' )
						insert_data = { }
						for column, col_type in type_map.items( ):
							if 'INT' in col_type:
								insert_data[ column ] = st.number_input( column, step=1,
									key=f'ins_{table}_{column}' )
							elif 'REAL' in col_type:
								insert_data[ column ] = st.number_input( column, format='%.6f',
									key=f'ins_{table}_{column}' )
							elif 'BOOL' in col_type:
								insert_data[ column ] = 1 if st.checkbox( column,
									key=f'ins_{table}_{column}' ) else 0
							else:
								insert_data[ column ] = st.text_input( column,
									key=f'ins_{table}_{column}' )
					
						if st.button( 'Insert Row', key=f'insert_row_{table}',
								use_container_width=True ):
							cols = list( insert_data.keys( ) )
							quoted_cols = [ f'"{c}"' for c in cols ]
							placeholders = ', '.join( [ '?' ] * len( cols ) )
							stmt = ( f'INSERT INTO "{table}" ({", ".join( quoted_cols )}) '
									f'VALUES ({placeholders});')
						
							with create_connection( ) as conn:
								conn.execute( stmt, list( insert_data.values( ) ) )
								conn.commit( )
						
							st.success( 'Row inserted.' )
							st.rerun( )
				
					# ------------------------------------------------------------------
					# UPDATE
					# ------------------------------------------------------------------
					with update_col:
						st.markdown( '##### Update Row' )
						rowid = st.number_input( 'Row ID', min_value=1, step=1,
							key=f'crud_update_rowid_{table}' )
					
						update_data = { }
					
						for column, col_type in type_map.items( ):
							if 'INT' in col_type:
								val = st.number_input( column, step=1, key=f'upd_{table}_{column}' )
								update_data[ column ] = val
						
							elif 'REAL' in col_type:
								val = st.number_input( column, format='%.6f', key=f'upd_{table}_{column}' )
								update_data[ column ] = val
						
							elif 'BOOL' in col_type:
								val = 1 if st.checkbox( column,
									key=f'upd_{table}_{column}' ) else 0
								update_data[ column ] = val
						
							else:
								val = st.text_input( column, key=f'upd_{table}_{column}' )
								update_data[ column ] = val
					
						if st.button( 'Update Row', key=f'update_row_{table}',
								use_container_width=True ):
							set_clause = ', '.join( [ f'"{c}"=?' for c in update_data ] )
							stmt = f'UPDATE "{table}" SET {set_clause} WHERE rowid=?;'
						
							with create_connection( ) as conn:
								conn.execute( stmt, list( update_data.values( ) ) + [ rowid ] )
								conn.commit( )
						
							st.success( 'Row updated.' )
							st.rerun( )
				
					blue_divider( )
				
					delete_col, preview_col = st.columns( [ 0.35, 0.65 ], border=True )
				
					# ------------------------------------------------------------------
					# DELETE
					# ------------------------------------------------------------------
					with delete_col:
						st.markdown( '##### Delete Row' )
						delete_id = st.number_input( 'Row ID to Delete', min_value=1, step=1,
							key=f'crud_delete_rowid_{table}' )
					
						if st.button( 'Delete Row', key=f'delete_row_{table}', use_container_width=True ):
							with create_connection( ) as conn:
								conn.execute( f'DELETE FROM "{table}" WHERE rowid=?;', (delete_id,) )
								conn.commit( )
						
							st.success( 'Row deleted.' )
							st.rerun( )
				
					# ------------------------------------------------------------------
					# PREVIEW
					# ------------------------------------------------------------------
					with preview_col:
						st.markdown( '##### Current Data Preview' )
						st.data_editor( df.head( 25 ), key=f'dm_crud_preview_{table}',
							use_container_width=True, disabled=True )
		
			# ------------------------------------------------------------------------------
			# EXPLORE
			# ------------------------------------------------------------------------------
		if tabs[ 3 ].open:
			with tabs[ 3 ]:
				tables = list_tables( )
				if tables:
					exp_c1, exp_c2, exp_c3 = st.columns( [ 0.4, 0.4, 0.2 ], border=True )
					with exp_c1:
						table = st.selectbox( 'Table', tables, key='explore_table' )
					with exp_c2:
						page_size = st.slider( 'Rows per page', 10, 500, 50 )
					with exp_c3:
						page = st.number_input( 'Page', min_value=1, step=1 )
						offset = (page - 1) * page_size
						df_page = read_table( table, page_size, offset )
				
					blue_divider( )
				
					st.data_editor( data=df_page, num_rows='dynamic', hide_index=False )
		
			# ------------------------------------------------------------------------------
			# FILTER
			# ------------------------------------------------------------------------------
		if tabs[ 4 ].open:
			with tabs[ 4 ]:
				tables = list_tables( )
				if tables:
					tbl_c1, tbl_c2, tbl_c3 = st.columns( [ 0.25, 0.25, 0.5 ], border=True )
					with tbl_c1:
						table = st.selectbox( 'Select Table', tables, key='filter_table' )
						df = read_table( table )
					
					with tbl_c2:
						column = st.selectbox( 'Select Field', df.columns, key='selected_column' )
					
					with tbl_c3:
						value = st.text_input( 'Contains', placeholder='Enter Text for Lookup' )
						if value:
							df = df[ df[ column ].astype( str ).str.contains( value ) ]
				
					blue_divider( )
				
					st.data_editor( df, key='dm_filter_key' )
		
			# ------------------------------------------------------------------------------
			# AGGREGATE
			# ------------------------------------------------------------------------------
		if tabs[ 5 ].open:
			with tabs[ 5 ]:
				tables = list_tables( )
				if tables:
					agg_c1, agg_c2, agg_c3, agg_c4 = st.columns( [ 0.2, 0.2, 0.2, 0.4 ], border=True )
					with agg_c1:
						table = st.selectbox( 'Table', tables, key='agg_table' )
						df = read_table( table )
						numeric_cols = df.select_dtypes( include=[ 'number' ] ).columns.tolist( )
						if not numeric_cols:
							with agg_c2:
								st.info( 'No numeric columns available.' )
						else:
							with agg_c2:
								col = st.selectbox( 'Column', numeric_cols, key='selected_col' )
							with agg_c3:
								agg = st.selectbox( 'Function', [ 'SUM', 'AVG', 'COUNT' ] )
							with agg_c4:
								if agg == 'SUM':
									st.metric( 'Result', df[ col ].sum( ), width='stretch',
										format='accounting' )
								elif agg == 'AVG':
									st.metric( 'Result', df[ col ].mean( ), width='stretch',
										format='accounting' )
								elif agg == 'COUNT':
									st.metric( 'Result', df[ col ].count( ), width='stretch',
										format='accounting' )
		
			# ------------------------------------------------------------------------------
			# VISUALIZE
			# ------------------------------------------------------------------------------
		if tabs[ 6 ].open:
			with tabs[ 6 ]:
				tables = list_tables( )
				if tables:
					table = st.selectbox( 'Table', tables, key='viz_table' )
					df = read_table( table )
					create_visualization( df )
		
			# ------------------------------------------------------------------------------
			# GEOCODE
			# ------------------------------------------------------------------------------
		if tabs[ 7 ].open:
			with tabs[ 7 ]:
				st.subheader( 'Geocode Missing Report Coordinates' )
			
				tables = list_tables( )
			
				if not tables:
					st.info( 'No tables available.' )
				else:
					default_table = resolve_table_name( cfg.DEFAULT_DATA, tables )
					if default_table is None:
						default_table = tables[ 0 ]
				
					default_index = tables.index( default_table )
				
					control_c1, control_c2, control_c3, control_c4 = st.columns(
						[ 0.25, 0.25, 0.25, 0.25 ], border=True )
				
					with control_c1:
						table = st.selectbox( 'Table', tables, index=default_index,
							key='reports_geocode_table' )
				
					with control_c2:
						use_places = st.checkbox( 'Use Places Fallback', value=True,
							key='reports_geocode_use_places' )
				
					with control_c3:
						limit_enabled = st.checkbox( 'Limit Locations', value=True,
							key='reports_geocode_limit_enabled' )
				
					with control_c4:
						limit = st.number_input( 'Location Limit', min_value=1, max_value=10000,
							value=100, step=25, key='reports_geocode_limit' )
				
					location_limit = int( limit ) if limit_enabled else None
				
					required_cols = [ 'City', 'State', 'Country', 'Latitude', 'Longitude' ]
					schema = create_schema( table )
					table_cols = [ row[ 1 ] for row in schema ]
					missing_cols = [ col for col in required_cols if col not in table_cols ]
				
					if missing_cols:
						st.warning(
							f'Table is missing required column(s): {", ".join( missing_cols )}' )
					else:
						missing_rows = count_missing_report_coordinate_rows( table )
						df_locations = read_missing_report_locations( table, location_limit )
						distinct_total = len( read_missing_report_locations( table, None ) )
					
						status_c1, status_c2, status_c3, status_c4 = st.columns( 4 )
						status_c1.metric( 'Rows Missing Coordinates', f'{missing_rows:,}' )
						status_c2.metric( 'Distinct Locations', f'{distinct_total:,}' )
						status_c3.metric( 'Preview Locations', f'{len( df_locations ):,}' )
						status_c4.metric( 'Fallback', 'Enabled' if use_places else 'Disabled' )
					
						with st.expander( 'Distinct Locations Missing Coordinates', expanded=False ):
							if df_locations.empty:
								st.info( 'No missing coordinate locations found.' )
							else:
								st.data_editor(
									df_locations,
									key='reports_geocode_locations',
									use_container_width=True,
									disabled=True )
					
						action_c1, action_c2, action_c3 = st.columns( [ 0.25, 0.25, 0.50 ] )
					
						with action_c1:
							if st.button( 'Preview Geocoding', key='reports_geocode_preview_button',
									width='stretch' ):
								df_preview = preview_report_coordinate_updates(
									table_name=table,
									geocoder=geocoder,
									places=places,
									use_places=use_places,
									limit=location_limit )
							
								st.session_state[ 'df_reports_geocode_preview' ] = df_preview
					
						with action_c2:
							if st.button( 'Clear', icon='🧹', key='reports_geocode_clear_button',
									width='stretch' ):
								st.session_state[ 'df_reports_geocode_preview' ] = pd.DataFrame( )
					
						df_preview = st.session_state.get( 'df_reports_geocode_preview',
							pd.DataFrame( ) )
					
						if df_preview is not None and not df_preview.empty:
							status_series = df_preview[ 'Status' ].astype( str ).str.lower( )
							matched_count = int( (status_series == 'matched').sum( ) )
							failed_count = int( (status_series == 'failed').sum( ) )
							skipped_count = int( (status_series == 'skipped').sum( ) )
						
							matched_rows = int(
								df_preview.loc[ status_series == 'matched', 'RowCount' ].sum( ) )
						
							result_c1, result_c2, result_c3, result_c4 = st.columns( 4 )
							result_c1.metric( 'Matched Locations', f'{matched_count:,}' )
							result_c2.metric( 'Failed Locations', f'{failed_count:,}' )
							result_c3.metric( 'Skipped Locations', f'{skipped_count:,}' )
							result_c4.metric( 'Rows Eligible For Update', f'{matched_rows:,}' )
						
							st.data_editor(
								df_preview,
								key='reports_geocode_preview_table',
								use_container_width=True,
								disabled=True )
						
							st.warning(
								'Apply Updates writes Latitude and Longitude values back to SQLite '
								'for all missing-coordinate rows matching the previewed City, State, '
								'and Country combinations. Review the preview before applying.' )
						
							apply_c1, apply_c2 = st.columns( [ 0.25, 0.75 ] )
						
							with apply_c1:
								apply_updates = st.checkbox( 'Confirm Apply Updates',
									value=False, key='reports_geocode_confirm_apply' )
						
							with apply_c2:
								if st.button( 'Apply Updates', key='reports_geocode_apply_button',
										width='stretch', disabled=not apply_updates ):
									updated_count = apply_report_coordinate_updates( table, df_preview )
								
									if updated_count:
										st.success(
											f'Updated {updated_count:,} report coordinate row(s).' )
										st.session_state[
											'df_reports_geocode_preview' ] = pd.DataFrame( )
										st.rerun( )
									else:
										st.info( 'No rows were updated.' )
									
			# ------------------------------------------------------------------------------
			# ADMIN
			# ------------------------------------------------------------------------------
		if tabs[ 8 ].open:
			with tabs[ 8 ]:
				tables = list_tables( )
				if tables:
					table = st.selectbox( 'Table', tables, key='admin_table' )
			
				blue_divider( )
			
				st.markdown( '##### Data Profiling' )
				tables = list_tables( )
				if tables:
					table = st.selectbox( 'Select Table', tables, key='profile_table' )
					if st.button( 'Generate Profile' ):
						profile_df = create_profile_table( table )
						render_table( profile_df )
			
				st.markdown( '##### Drop Table' )
			
				tables = list_tables( )
				if tables:
					table = st.selectbox( 'Select Table to Drop', tables, key='admin_drop_table' )
				
					# Initialize confirmation state
					if 'dm_confirm_drop' not in st.session_state:
						st.session_state.dm_confirm_drop = False
				
					# Step 1: Initial Drop click
					if st.button( 'Drop Table', key='admin_drop_button' ):
						st.session_state.dm_confirm_drop = True
				
					# Step 2: Confirmation UI
					if st.session_state.dm_confirm_drop:
						st.warning( f'You are about to permanently delete table {table}. '
						            'This action cannot be undone.' )
					
						col1, col2 = st.columns( 2 )
						if col1.button( 'Confirm Drop', key='admin_confirm_drop' ):
							try:
								drop_table( table )
								st.success( f'Table {table} dropped successfully.' )
							except Exception as e:
								st.error( f'Drop failed: {e}' )
						
							st.session_state.dm_confirm_drop = False
							st.rerun( )
					
						if col2.button( 'Cancel', key='admin_cancel_drop' ):
							st.session_state.dm_confirm_drop = False
							st.rerun( )
				
					df = read_table( table )
					col = st.selectbox( 'Create Index On', df.columns, key='df_key' )
				
					if st.button( 'Create Index' ):
						create_index( table, col )
						st.success( 'Index created.' )
			
				blue_divider( )
			
				st.markdown( '##### Create Custom Table' )
				new_table_name = st.text_input( 'Table Name' )
				column_count = st.number_input( 'Number of Columns', min_value=1,
					max_value=20, value=1 )
			
				columns = [ ]
				for i in range( column_count ):
					st.markdown( f'##### Column {i + 1}' )
					col_name = st.text_input( 'Column Name', key=f'col_name_{i}' )
					col_type = st.selectbox( 'Column Type', [ 'INTEGER', 'REAL', 'TEXT' ],
						key=f'col_type_{i}' )
				
					not_null = st.checkbox( 'NOT NULL', key=f'not_null_{i}' )
					primary_key = st.checkbox( 'PRIMARY KEY', key=f'pk_{i}' )
					auto_inc = st.checkbox( 'AUTOINCREMENT (INTEGER only)', key=f'ai_{i}' )
				
					columns.append( {
							'name': col_name,
							'type': col_type,
							'not_null': not_null,
							'primary_key': primary_key,
							'auto_increment': auto_inc } )
			
				if st.button( 'Create Table' ):
					try:
						create_custom_table( new_table_name, columns )
						st.success( 'Table created successfully.' )
						st.rerun( )
				
					except Exception as e:
						st.error( f'Error: {e}' )
			
				blue_divider( )
				st.markdown( '##### Schema Viewer' )
			
				tables = list_tables( )
				if tables:
					table = st.selectbox( 'Select Table', tables, key='schema_view_table' )
				
					# Column schema
					schema = create_schema( table )
					schema_df = pd.DataFrame( schema,
						columns=[ 'cid', 'name', 'type', 'notnull', 'default', 'pk' ] )
				
					st.markdown( "##### Columns" )
					st.data_editor( make_display_safe( schema_df ), hide_index=True,
						use_container_width=True, disabled=True )
				
					# Row count
					with create_connection( ) as conn:
						count = conn.execute( f'SELECT COUNT(*) FROM "{table}"' ).fetchone( )[ 0 ]
				
					st.metric( "Row Count", f"{count:,}" )
				
					# Indexes
					indexes = get_indexes( table )
					if indexes:
						idx_df = pd.DataFrame( indexes,
							columns=[ 'seq', 'name', 'unique', 'origin', 'partial' ] )
					
						st.markdown( "##### Indexes" )
						st.data_editor( make_display_safe( idx_df ), hide_index=True,
							use_container_width=True, disabled=True )
					else:
						st.info( "No indexes defined." )
			
				blue_divider( )
				st.markdown( '##### ALTER TABLE Operations' )
			
				tables = list_tables( )
				if tables:
					table = st.selectbox( 'Select Table', tables, key='alter_table_select' )
					operation = st.selectbox( 'Operation',
						[ 'Add Column', 'Rename Column', 'Rename Table', 'Drop Column' ], key='op_key' )
				
					if operation == 'Add Column':
						new_col = st.text_input( 'Column Name' )
						col_type = st.selectbox( 'Column Type', [ 'INTEGER', 'REAL', 'TEXT' ],
							key='key_type' )
					
						if st.button( 'Add Column' ):
							add_column( table, new_col, col_type )
							st.success( 'Column added.' )
							st.rerun( )
				
					elif operation == 'Rename Column':
						schema = create_schema( table )
						col_names = [ col[ 1 ] for col in schema ]
					
						old_col = st.selectbox( 'Column to Rename', col_names, key='old_key' )
						new_col = st.text_input( 'New Column Name' )
					
						if st.button( 'Rename Column' ):
							rename_column( table, old_col, new_col )
							st.success( 'Column renamed.' )
							st.rerun( )
				
					elif operation == 'Rename Table':
						new_name = st.text_input( 'New Table Name' )
					
						if st.button( 'Rename Table' ):
							rename_table( table, new_name )
							st.success( 'Table renamed.' )
							st.rerun( )
				
					elif operation == 'Drop Column':
						schema = create_schema( table )
						col_names = [ col[ 1 ] for col in schema ]
					
						drop_col = st.selectbox( 'Column to Drop', col_names, key='drop_key' )
					
						if st.button( 'Drop Column' ):
							drop_column( table, drop_col )
							st.success( 'Column dropped.' )
							st.rerun( )
		
			# ------------------------------------------------------------------------------
			# SQL
			# ------------------------------------------------------------------------------
		if tabs[ 9 ].open:
			with tabs[ 9 ]:
				st.subheader( 'SQL Console' )
				query = st.text_area( 'Enter SQL Query' )
				if st.button( label='Run', icon='🏃', ):
					if not is_safe_query( query ):
						st.error( 'Query blocked: Only read-only SELECT statements are allowed.' )
					else:
						try:
							start_time = time.perf_counter( )
							with create_connection( ) as conn:
								result = pd.read_sql_query( query, conn )
						
							end_time = time.perf_counter( )
							elapsed = end_time - start_time
						
							# ----------------------------------------------------------
							# Display Results
							# ----------------------------------------------------------
							st.dataframe( result, use_container_width=True )
							row_count = len( result )
						
							# ----------------------------------------------------------
							# Execution Metrics
							# ----------------------------------------------------------
							col1, col2 = st.columns( 2 )
							col1.metric( 'Rows Returned', f'{row_count:,}' )
							col2.metric( 'Execution Time (seconds)', f'{elapsed:.6f}' )
						
							# Optional slow query warning
							if elapsed > 2.0:
								st.warning( 'Slow query detected (> 2 seconds). Consider indexing.' )
						
							# ----------------------------------------------------------
							# Download
							# ----------------------------------------------------------
							if not result.empty:
								csv = result.to_csv( index=False ).encode( 'utf-8' )
								st.download_button( 'Download CSV', csv,
									'query_results.csv', 'text/csv' )
					
						except Exception as e:
							st.error( f'Execution failed: {e}' )

# ==============================================================================
# LIVE DATA
# ==============================================================================
render_live_world_map( latitude=get_global_latitude_default( ),
	longitude=get_global_longitude_default( ) )

# ======================================================================================
# FOOTER — SECTION
# ======================================================================================
st.markdown( """
	<style>
	.block-container {
		padding-bottom: 3rem;
	}
	</style>
	""", unsafe_allow_html=True, )

# ---- Fixed Container
st.markdown( """
	<style>
	.foo-status-bar {
		position: fixed;
		bottom: 0;
		left: 0;
		width: 100%;
		background-color: rgba(27, 27, 27, 0.95);
		border-top: 1px solid #5A5A5A;
		padding: 10px 16px;
		font-size: 0.80rem;
		color: #0078FC;
		z-index: 1000;
	}
	.foo-status-inner {
		display: flex;
		justify-content: space-between;
		align-items: center;
		max-width: 100%;
	}
	</style>
	""", unsafe_allow_html=True, )

# ---- Rendering Method
st.markdown( """
    <div class="foo-status-bar">
        <div class="foo-status-inner">
            <span> </span>
            <span> </span>
        </div>
    </div>
    """, unsafe_allow_html=True, )
