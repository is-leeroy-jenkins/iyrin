'''
  ******************************************************************************************
      Assembly:                Iyrin
      Filename:                realtime.py
      Author:                  Terry D. Eppler
      Created:                 05-31-2025

      Last Modified By:        Terry D. Eppler
      Last Modified On:        05-01-2025
  ******************************************************************************************
  <copyright file='realtime.py' company='Terry D. Eppler'>

	     Copyright ©  2025  Terry Eppler

     Permission is hereby granted, free of charge, to any person obtaining a copy
     of this software and associated documentation files (the “Software”),
     to deal in the Software without restriction,
     including without limitation the rights to use,
     copy, modify, merge, publish, distribute, sublicense,
     and/or sell copies of the Software,
     and to permit persons to whom the Software is furnished to do so,
     subject to the following conditions:

     The above copyright notice and this permission notice shall be included in all
     copies or substantial portions of the Software.

     THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
     INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
     FITNESS FOR A PARTICULAR PURPOSE AND NON-INFRINGEMENT.
     IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
     DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
     ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
     DEALINGS IN THE SOFTWARE.

     You can contact me at:  terryeppler@gmail.com or eppler.terry@epa.gov

  </copyright>
  <summary>
        Live World Data functionality inspired by God's Eye View while preserving Iyr's
	    existing GIS modes and execution paths. The module provides isolated sidebar state,
	    live aircraft, military aircraft, satellite, vessel, earthquake, active-fire, infrastructure,
	    and public-camera retrieval, normalized geospatial entities, operational PyDeck rendering,
	    entity tracking and trails, refresh controls,
	    filtering, and source-data inspection.
  </summary>
  ******************************************************************************************
'''
from __future__ import annotations
import datetime as dt
import json
import math
import os
from dataclasses import asdict, dataclass
from typing import Any, Callable, Dict, List
import pandas as pd
import pydeck as pdk
import streamlit as st
import config as cfg
from fetchers import Firms, USGSEarthquakes
from history import (clear_live_world_history, get_live_world_history_snapshots,
                     get_live_world_history_summary,load_live_world_history,
                     persist_live_world_history, purge_live_world_history )
from sources import ( AdsbLolMilitary, AisStreamLive, CelesTrakLive, OpenSkyLive,
                      OverpassCameras, OverpassInfrastructure, OverpassMapLayers )
from tools import LIVE_WORLD_AGENT_TOOLS

LIVE_WORLD_LAYERS: Dict[ str, str ] = { 'aircraft': '✈️ Aircraft (Live)',
		'military_aircraft': '🛩️ Military Aircraft', 'satellites': '🛰️ Satellites',
		'vessels': '🚢 Vessels & Ships', 'earthquakes': '📈 Earthquakes',
		'fires': '🔥 Fires (Wildfires)', 'tracking': '🎯 Tracking & Trails',
		'measurements': '📏 Measurements & Annotations', 'infrastructure': '📡 Infrastructure ',
		'cameras': '📷 CCTV / Web Cameras', 'map_layers': '🗺️ Additional Map Layers', }

LIVE_WORLD_PENDING_LAYERS: Dict[ str, str ] = { }

LIVE_WORLD_DATA_SOURCES: Dict[ str, Dict[ str, str ] ] = {
	'aircraft': {
		'label': 'Aircraft',
		'enabled_key': 'live_world_aircraft',
		'frame_key': 'live_world_df_aircraft',
	},
	'military_aircraft': {
		'label': 'Military Aircraft',
		'enabled_key': 'live_world_military_aircraft',
		'frame_key': 'live_world_df_military_aircraft',
	},
	'satellites': {
		'label': 'Satellites',
		'enabled_key': 'live_world_satellites',
		'frame_key': 'live_world_df_satellites',
	},
	'vessels': {
		'label': 'Vessels',
		'enabled_key': 'live_world_vessels',
		'frame_key': 'live_world_df_vessels',
	},
	'earthquakes': {
		'label': 'Earthquakes',
		'enabled_key': 'live_world_earthquakes',
		'frame_key': 'live_world_df_earthquakes',
	},
	'fires': {
		'label': 'Fires',
		'enabled_key': 'live_world_fires',
		'frame_key': 'live_world_df_fires',
	},
	'infrastructure': {
		'label': 'Infrastructure',
		'enabled_key': 'live_world_infrastructure',
		'frame_key': 'live_world_df_infrastructure',
	},
	'cameras': {
		'label': 'Cameras',
		'enabled_key': 'live_world_cameras',
		'frame_key': 'live_world_df_cameras',
	},
	'map_layers': {
		'label': 'Map Features',
		'enabled_key': 'live_world_map_layers',
		'frame_key': 'live_world_df_map_layers',
	},
}

AI_ADVANCED_TOOLS: Dict[ str, str ] = { 'cross_layer_analysis': '🧭 Cross-Layer Analysis',
		'geofencing': '🛡️ Geofencing', 'historical_replay': '🕓 Historical Replay',
		'agent_tools': '🤖 Agent Tools', }


@dataclass
class GeoEntity:
	"""Normalized geospatial entity used by Live World layers.

	Purpose:
		Represent one normalized geospatial object or event displayed by Live World Data.

	Attributes:
		entity_id (str): Stable source identifier.
		entity_type (str): Logical entity category.
		name (str): Human-readable label.
		latitude (float): Latitude in decimal degrees.
		longitude (float): Longitude in decimal degrees.
		altitude (float): Altitude or depth value when available.
		heading (float): Heading in degrees when available.
		speed (float): Speed when available.
		timestamp (str): Source timestamp.
		source (str): Source system name.
		metadata (Dict[str, Any]): Source-specific attributes.
	"""
	entity_id: str
	entity_type: str
	name: str
	latitude: float
	longitude: float
	altitude: float
	heading: float
	speed: float
	timestamp: str
	source: str
	metadata: Dict[ str, Any ]


def throw_if( name: str, value: object ) -> None:
	'''

	Purpose:
		Validate that a required value is not empty.

	Args:
		name (str): Name of the argument being validated.
		value (object): Value to validate.

	Returns:
		None

	'''
	if value is None:
		raise ValueError( f'Argument "{name}" cannot be None.' )

	if isinstance( value, str ) and not value.strip( ):
		raise ValueError( f'Argument "{name}" cannot be empty.' )
	if isinstance( value, (list, tuple, dict, set) ) and not value:
		raise ValueError( f'Argument "{name}" cannot be empty.' )

def initialize_live_world_state( ) -> None:
	'''

	Purpose:
		Initialize isolated Live World Data state without modifying Iyr's existing mode state.

	Returns:
		None

	'''
	defaults: Dict[ str, object ] = {
		'live_world_enabled': False,
		'live_world_aircraft': False,
		'live_world_aircraft_radius': 2.0,
		'live_world_aircraft_airborne_only': True,
		'opensky_api_client_id': cfg.OPENSKY_CLIENT_ID or '',
		'opensky_api_client_secret': cfg.OPENSKY_API_CLIENT_SECRET or '',
		'live_world_military_aircraft': False,
		'live_world_military_radius_nm': 250,
		'live_world_satellites': False,
		'live_world_satellite_group': 'stations',
		'live_world_satellite_limit': 100,
		'live_world_satellite_propagation_attempts': 0,
		'live_world_satellite_propagation_failures': 0,
		'live_world_vessels': False,
		'live_world_aisstream_api_key': os.getenv( 'AISSTREAM_API_KEY', '' ) or '',
		'live_world_vessel_radius': 2.0,
		'live_world_vessel_limit': 100,
		'live_world_earthquakes': False,
		'live_world_earthquake_feed': 'all_day.geojson',
		'live_world_earthquake_min_magnitude': 1.0,
		'live_world_fires': False,
		'live_world_firms_source': 'VIIRS_NOAA21_NRT',
		'live_world_firms_day_range': 1,
		'live_world_firms_area_mode': 'Local Bounding Box',
		'live_world_firms_max_records': 10000,
		'live_world_firms_source_count': 0,
		'live_world_firms_truncated': False,
		'live_world_infrastructure': False,
		'live_world_infrastructure_radius_km': 50,
		'live_world_infrastructure_categories': [
			'Airports', 'Ports', 'Power Plants', 'Dams', 'Data Centers' ],
		'live_world_infrastructure_limit': 500,
		'live_world_cameras': False,
		'live_world_camera_radius_km': 25,
		'live_world_camera_categories': [ 'CCTV / Surveillance', 'Web Cameras' ],
		'live_world_camera_limit': 500,
		'live_world_map_layers': False,
		'live_world_map_layer_radius_km': 50,
		'live_world_map_layer_categories': [
			'Public Transit', 'Bike Share', 'Emergency Services', 'Healthcare',
			'EV Charging', 'Communications', 'Launch Sites' ],
		'live_world_map_layer_limit': 1000,
		'live_world_tracking': False,
		'live_world_tracking_entity': '',
		'live_world_tracking_active_entity': '',
		'live_world_tracking_follow': True,
		'live_world_tracking_max_points': 100,
		'live_world_tracking_history': [ ],
		'live_world_measurements': False,
		'live_world_measurement_start': 'Current Location',
		'live_world_measurement_end': 'Current Location',
		'live_world_measurement_custom_start_latitude': 0.0,
		'live_world_measurement_custom_start_longitude': 0.0,
		'live_world_measurement_custom_end_latitude': 0.0,
		'live_world_measurement_custom_end_longitude': 0.0,
		'live_world_annotation_label': '',
		'live_world_annotation_latitude': 0.0,
		'live_world_annotation_longitude': 0.0,
		'live_world_annotations': [ ],
		'live_world_cross_layer_analysis': False,
		'live_world_analysis_origin': 'Current Location',
		'live_world_analysis_custom_latitude': 0.0,
		'live_world_analysis_custom_longitude': 0.0,
		'live_world_analysis_radius_nm': 250,
		'live_world_analysis_entity_types': [
			'Aircraft', 'Military Aircraft', 'Satellite', 'Vessel', 'Earthquake', 'Fire',
			'Infrastructure', 'Camera', 'Map Feature' ],
		'live_world_analysis_limit': 100,
		'live_world_geofencing': False,
		'live_world_geofence_origin': 'Current Location',
		'live_world_geofence_custom_latitude': 0.0,
		'live_world_geofence_custom_longitude': 0.0,
		'live_world_geofence_radius_nm': 50,
		'live_world_geofence_entity_types': [
			'Aircraft', 'Military Aircraft', 'Satellite', 'Vessel', 'Earthquake', 'Fire',
			'Infrastructure', 'Camera', 'Map Feature' ],
		'live_world_geofence_event_limit': 100,
		'live_world_geofence_events': [ ],
		'live_world_geofence_snapshot': { },
		'live_world_geofence_initialized': False,
		'live_world_geofence_last_refresh_processed': '',
		'live_world_historical_replay': False,
		'live_world_history_persist': False,
		'live_world_history_retention_days': 30,
		'live_world_history_max_rows_per_source': 5000,
		'live_world_history_window': '24 Hours',
		'live_world_history_entity_types': [
			'Aircraft', 'Military Aircraft', 'Satellite', 'Vessel', 'Earthquake', 'Fire',
			'Infrastructure', 'Camera', 'Map Feature' ],
		'live_world_history_limit': 5000,
		'live_world_history_snapshot': '',
		'live_world_history_last_saved': 0,
		'live_world_history_last_error': '',
		'live_world_agent_tools': False,
		'live_world_refresh_requested': False,
		'live_world_last_refresh': '',
		'live_world_last_error': '',
		'live_world_source_status': {
			key: 'Not Refreshed' for key in LIVE_WORLD_DATA_SOURCES },
		'live_world_source_errors': {
			key: '' for key in LIVE_WORLD_DATA_SOURCES },
		'live_world_source_last_attempt': {
			key: '' for key in LIVE_WORLD_DATA_SOURCES },
		'live_world_source_last_success': {
			key: '' for key in LIVE_WORLD_DATA_SOURCES },
		'live_world_source_stale': {
			key: False for key in LIVE_WORLD_DATA_SOURCES },
		'live_world_df_entities': pd.DataFrame( ),
		'live_world_df_aircraft': pd.DataFrame( ),
		'live_world_df_military_aircraft': pd.DataFrame( ),
		'live_world_df_satellites': pd.DataFrame( ),
		'live_world_df_vessels': pd.DataFrame( ),
		'live_world_df_earthquakes': pd.DataFrame( ),
		'live_world_df_fires': pd.DataFrame( ),
		'live_world_df_infrastructure': pd.DataFrame( ),
		'live_world_df_cameras': pd.DataFrame( ),
		'live_world_df_map_layers': pd.DataFrame( ),
		'live_world_aircraft_result': { },
		'live_world_military_aircraft_result': { },
		'live_world_satellite_result': [ ],
		'live_world_vessel_result': [ ],
		'live_world_earthquake_result': { },
		'live_world_firms_result': { },
		'live_world_infrastructure_result': { },
		'live_world_camera_result': { },
		'live_world_map_layer_result': { },
		'live_world_map_style': 'Carto Dark Matter',
		'live_world_zoom': 4,
		'live_world_point_scale': 1.0,
	}

	for key, value in defaults.items( ):
		if key not in st.session_state:
			st.session_state[ key ] = value

def get_live_world_layers( ) -> Dict[ str, bool ]:
	'''

	Purpose:
		Return the enabled state of every implemented Live World Data layer.

	Returns:
		Dict[str, bool]: Enabled state keyed by layer identifier.

	'''
	initialize_live_world_state( )
	return { key: bool( st.session_state.get( f'live_world_{key}', False ) )
		for key in LIVE_WORLD_LAYERS }

def render_live_world_sidebar( ) -> None:
	'''

	Purpose:
		Render operational Live World Data controls in an isolated sidebar expander below
		Iyr's existing Mode expander.

	Returns:
		None

	'''
	initialize_live_world_state( )
	with st.expander( '🌐 Mapping', expanded=False ):
		st.checkbox( 'Enable Live Map', key='live_world_enabled' )
		st.divider( )
		st.caption( 'Live Layers' )
		st.checkbox( LIVE_WORLD_LAYERS[ 'aircraft' ], key='live_world_aircraft' )
		if st.session_state[ 'live_world_aircraft' ]:
			st.slider( 'Aircraft Radius (Degrees)', min_value=0.25, max_value=10.0,
				step=0.25, key='live_world_aircraft_radius' )
			st.checkbox( 'Airborne Only', key='live_world_aircraft_airborne_only' )
			st.caption( 'OpenSky API Client credentials are used when configured.' )

		st.checkbox( LIVE_WORLD_LAYERS[ 'military_aircraft' ],
			key='live_world_military_aircraft' )
		if st.session_state[ 'live_world_military_aircraft' ]:
			st.slider( 'Military Aircraft Radius (NM)', min_value=25, max_value=250,
				step=25, key='live_world_military_radius_nm' )
			st.caption( 'Military-tagged aircraft are retrieved from ADSB.lol.' )

		st.checkbox( LIVE_WORLD_LAYERS[ 'satellites' ], key='live_world_satellites' )
		if st.session_state[ 'live_world_satellites' ]:
			st.selectbox( 'Satellite Group',
				options=[ 'stations', 'visual', 'weather', 'gps-ops', 'active' ],
				key='live_world_satellite_group' )
			st.slider( 'Satellite Limit', min_value=10, max_value=500, step=10,
				key='live_world_satellite_limit' )

		st.checkbox( LIVE_WORLD_LAYERS[ 'vessels' ], key='live_world_vessels' )
		if st.session_state[ 'live_world_vessels' ]:
			st.text_input( 'AIS Stream API Key', type='password',
				key='live_world_aisstream_api_key',
				help='Uses AISSTREAM_API_KEY when configured in the environment.' )
			st.slider( 'Vessel Radius (Degrees)', min_value=0.25, max_value=10.0,
				step=0.25, key='live_world_vessel_radius' )
			st.slider( 'Vessel Message Limit', min_value=10, max_value=250, step=10,
				key='live_world_vessel_limit' )

		st.checkbox( LIVE_WORLD_LAYERS[ 'earthquakes' ], key='live_world_earthquakes' )
		if st.session_state[ 'live_world_earthquakes' ]:
			st.selectbox(
				'Earthquake Feed',
				options=[
					'all_hour.geojson', 'all_day.geojson', 'all_week.geojson',
					'2.5_day.geojson', '2.5_week.geojson', '4.5_day.geojson',
					'4.5_week.geojson', 'significant_day.geojson',
					'significant_week.geojson' ],
				key='live_world_earthquake_feed' )
			st.slider( 'Minimum Magnitude', min_value=0.0, max_value=10.0,
				step=0.1, key='live_world_earthquake_min_magnitude' )

		st.checkbox( LIVE_WORLD_LAYERS[ 'fires' ], key='live_world_fires' )
		if st.session_state[ 'live_world_fires' ]:
			st.selectbox( 'FIRMS Source',
				options=[ 'VIIRS_NOAA21_NRT', 'VIIRS_NOAA20_NRT', 'VIIRS_SNPP_NRT',
					'MODIS_NRT', 'LANDSAT_NRT' ],
				key='live_world_firms_source' )
			st.slider( 'Fire Day Range', min_value=1, max_value=5, step=1,
				key='live_world_firms_day_range' )
			st.selectbox( 'Fire Area', options=[ 'Local Bounding Box', 'World' ],
				key='live_world_firms_area_mode' )
			st.slider( 'Fire Record Limit', min_value=1000, max_value=50000, step=1000,
				key='live_world_firms_max_records' )

		st.checkbox( LIVE_WORLD_LAYERS[ 'measurements' ], key='live_world_measurements' )
		if st.session_state[ 'live_world_measurements' ]:
			measurement_options = get_live_world_measurement_options( )
			measurement_keys = list( measurement_options.keys( ) )
			if st.session_state[ 'live_world_measurement_start' ] not in measurement_keys:
				st.session_state[ 'live_world_measurement_start' ] = 'Current Location'
			if st.session_state[ 'live_world_measurement_end' ] not in measurement_keys:
				st.session_state[ 'live_world_measurement_end' ] = 'Current Location'
			measure_c1, measure_c2 = st.columns( 2 )
			with measure_c1:
				st.selectbox( 'Measure From', options=measurement_keys,
					format_func=lambda value: measurement_options[ value ],
					key='live_world_measurement_start' )
			with measure_c2:
				st.selectbox( 'Measure To', options=measurement_keys,
					format_func=lambda value: measurement_options[ value ],
					key='live_world_measurement_end' )
			if st.session_state[ 'live_world_measurement_start' ] == 'Custom Point':
				custom_start_c1, custom_start_c2 = st.columns( 2 )
				with custom_start_c1:
					st.number_input( 'Start Latitude', min_value=-90.0, max_value=90.0,
						format='%.6f', key='live_world_measurement_custom_start_latitude' )
				with custom_start_c2:
					st.number_input( 'Start Longitude', min_value=-180.0, max_value=180.0,
						format='%.6f', key='live_world_measurement_custom_start_longitude' )
			if st.session_state[ 'live_world_measurement_end' ] == 'Custom Point':
				custom_end_c1, custom_end_c2 = st.columns( 2 )
				with custom_end_c1:
					st.number_input( 'End Latitude', min_value=-90.0, max_value=90.0,
						format='%.6f', key='live_world_measurement_custom_end_latitude' )
				with custom_end_c2:
					st.number_input( 'End Longitude', min_value=-180.0, max_value=180.0,
						format='%.6f', key='live_world_measurement_custom_end_longitude' )

			st.caption( 'Annotations' )
			st.text_input( 'Annotation Label', key='live_world_annotation_label' )
			annotation_c1, annotation_c2 = st.columns( 2 )
			with annotation_c1:
				st.number_input( 'Annotation Latitude', min_value=-90.0, max_value=90.0,
					format='%.6f', key='live_world_annotation_latitude' )
			with annotation_c2:
				st.number_input( 'Annotation Longitude', min_value=-180.0, max_value=180.0,
					format='%.6f', key='live_world_annotation_longitude' )
			annotation_button_c1, annotation_button_c2 = st.columns( 2 )
			with annotation_button_c1:
				if st.button( 'Add Annotation', icon='📍', key='live_world_annotation_add',
						width='stretch' ):
					add_live_world_annotation( )
			with annotation_button_c2:
				if st.button( 'Clear Annotations', icon='🧹', key='live_world_annotation_clear',
						width='stretch' ):
					clear_live_world_annotations( )

		st.checkbox( LIVE_WORLD_LAYERS[ 'tracking' ], key='live_world_tracking' )
		if st.session_state[ 'live_world_tracking' ]:
			tracking_options = get_live_world_tracking_options( )
			if tracking_options:
				tracking_keys = list( tracking_options.keys( ) )
				if st.session_state[ 'live_world_tracking_entity' ] not in tracking_keys:
					st.session_state[ 'live_world_tracking_entity' ] = tracking_keys[ 0 ]
				st.selectbox( 'Tracked Entity', options=tracking_keys,
					format_func=lambda value: tracking_options[ value ],
					key='live_world_tracking_entity' )
			else:
				st.info( 'Refresh a moving Live World layer before selecting a tracked entity.' )
			st.checkbox( 'Follow Tracked Entity', key='live_world_tracking_follow' )
			st.slider( 'Trail Points', min_value=10, max_value=500, step=10,
				key='live_world_tracking_max_points' )
			if st.button( 'Clear Trail', icon='🧹', key='live_world_tracking_clear',
					width='stretch' ):
				clear_live_world_tracking( )

		st.divider( )
		refresh_c1, clear_c2 = st.columns( 2 )
		with refresh_c1:
			if st.button( 'Refresh', icon='🔄', key='live_world_refresh', width='stretch' ):
				st.session_state[ 'live_world_refresh_requested' ] = True

		with clear_c2:
			if st.button( 'Clear', icon='🧹', key='live_world_clear', width='stretch' ):
				clear_live_world_data( )

		with st.expander( 'Additional Layers', expanded=False ):
			st.checkbox( LIVE_WORLD_LAYERS[ 'infrastructure' ], key='live_world_infrastructure' )
			if st.session_state[ 'live_world_infrastructure' ]:
				st.multiselect( 'Infrastructure Categories',
					options=[ 'Airports', 'Ports', 'Power Plants', 'Dams', 'Data Centers',
						'Military Installations' ], key='live_world_infrastructure_categories' )
				infra_c1, infra_c2 = st.columns( 2 )
				with infra_c1:
					st.slider( 'Infrastructure Radius (KM)', min_value=10, max_value=250,
						step=10, key='live_world_infrastructure_radius_km' )
				with infra_c2:
					st.slider( 'Infrastructure Limit', min_value=50, max_value=2000,
						step=50, key='live_world_infrastructure_limit' )
				st.caption( 'Infrastructure features are retrieved from OpenStreetMap via Overpass.' )

			st.checkbox( LIVE_WORLD_LAYERS[ 'cameras' ], key='live_world_cameras' )
			if st.session_state[ 'live_world_cameras' ]:
				st.multiselect( 'Camera Categories',
					options=[ 'CCTV / Surveillance', 'Web Cameras' ],
					key='live_world_camera_categories' )
				camera_c1, camera_c2 = st.columns( 2 )
				with camera_c1:
					st.slider( 'Camera Radius (KM)', min_value=1, max_value=100,
						step=1, key='live_world_camera_radius_km' )
				with camera_c2:
					st.slider( 'Camera Limit', min_value=50, max_value=2000,
						step=50, key='live_world_camera_limit' )
				st.caption( 'Public camera locations and webcam tags are retrieved from OpenStreetMap via Overpass.' )

			st.checkbox( LIVE_WORLD_LAYERS[ 'map_layers' ], key='live_world_map_layers' )
			if st.session_state[ 'live_world_map_layers' ]:
				st.multiselect( 'Map Layer Categories',
					options=[ 'Public Transit', 'Bike Share', 'Emergency Services', 'Healthcare',
						'EV Charging', 'Communications', 'Launch Sites' ],
					key='live_world_map_layer_categories' )
				map_layer_c1, map_layer_c2 = st.columns( 2 )
				with map_layer_c1:
					st.slider( 'Map Layer Radius (KM)', min_value=5, max_value=250,
						step=5, key='live_world_map_layer_radius_km' )
				with map_layer_c2:
					st.slider( 'Map Layer Limit', min_value=50, max_value=5000,
						step=50, key='live_world_map_layer_limit' )
				st.caption( 'Contextual public map features are retrieved from OpenStreetMap via Overpass.' )
			for label in LIVE_WORLD_PENDING_LAYERS.values( ):
				st.checkbox( label, value=False, disabled=True )

		with st.expander( 'AI & Advanced Tools', expanded=False ):
			st.caption( 'Advanced tools operate on the currently loaded Live World entity frame.' )
			st.checkbox( AI_ADVANCED_TOOLS[ 'cross_layer_analysis' ],
				key='live_world_cross_layer_analysis' )
			if st.session_state[ 'live_world_cross_layer_analysis' ]:
				analysis_options = get_live_world_analysis_origin_options( )
				analysis_keys = list( analysis_options.keys( ) )
				if st.session_state[ 'live_world_analysis_origin' ] not in analysis_keys:
					st.session_state[ 'live_world_analysis_origin' ] = 'Current Location'
				st.selectbox( 'Analysis Origin', options=analysis_keys,
					format_func=lambda value: analysis_options[ value ],
					key='live_world_analysis_origin' )
				if st.session_state[ 'live_world_analysis_origin' ] == 'Custom Point':
					analysis_c1, analysis_c2 = st.columns( 2 )
					with analysis_c1:
						st.number_input( 'Analysis Latitude', min_value=-90.0, max_value=90.0,
							format='%.6f', key='live_world_analysis_custom_latitude' )
					with analysis_c2:
						st.number_input( 'Analysis Longitude', min_value=-180.0, max_value=180.0,
							format='%.6f', key='live_world_analysis_custom_longitude' )
				st.slider( 'Analysis Radius (NM)', min_value=10, max_value=2500,
					step=10, key='live_world_analysis_radius_nm' )
				st.multiselect( 'Entity Types',
					options=[ 'Aircraft', 'Military Aircraft', 'Satellite', 'Vessel',
						'Earthquake', 'Fire', 'Infrastructure', 'Camera', 'Map Feature' ],
					key='live_world_analysis_entity_types' )
				st.slider( 'Analysis Result Limit', min_value=10, max_value=500,
					step=10, key='live_world_analysis_limit' )

			st.checkbox( AI_ADVANCED_TOOLS[ 'geofencing' ], key='live_world_geofencing' )
			if st.session_state[ 'live_world_geofencing' ]:
				geofence_options = get_live_world_geofence_origin_options( )
				geofence_keys = list( geofence_options.keys( ) )
				if st.session_state[ 'live_world_geofence_origin' ] not in geofence_keys:
					st.session_state[ 'live_world_geofence_origin' ] = 'Current Location'
				st.selectbox( 'Geofence Origin', options=geofence_keys,
					format_func=lambda value: geofence_options[ value ],
					key='live_world_geofence_origin' )
				if st.session_state[ 'live_world_geofence_origin' ] == 'Custom Point':
					geofence_c1, geofence_c2 = st.columns( 2 )
					with geofence_c1:
						st.number_input( 'Geofence Latitude', min_value=-90.0, max_value=90.0,
							format='%.6f', key='live_world_geofence_custom_latitude' )
					with geofence_c2:
						st.number_input( 'Geofence Longitude', min_value=-180.0, max_value=180.0,
							format='%.6f', key='live_world_geofence_custom_longitude' )
				st.slider( 'Geofence Radius (NM)', min_value=5, max_value=1000,
					step=5, key='live_world_geofence_radius_nm' )
				st.multiselect( 'Geofence Entity Types',
					options=[ 'Aircraft', 'Military Aircraft', 'Satellite', 'Vessel',
						'Earthquake', 'Fire', 'Infrastructure', 'Camera', 'Map Feature' ],
					key='live_world_geofence_entity_types' )
				st.slider( 'Geofence Event History', min_value=10, max_value=500,
					step=10, key='live_world_geofence_event_limit' )
				if st.button( 'Clear Geofence Events', icon='🧹',
						key='live_world_geofence_clear_events', width='stretch' ):
					clear_live_world_geofence_events( )

			st.checkbox( AI_ADVANCED_TOOLS[ 'historical_replay' ],
				key='live_world_historical_replay' )
			if st.session_state[ 'live_world_historical_replay' ]:
				st.checkbox( 'Persist Live World Refreshes', key='live_world_history_persist' )
				history_c1, history_c2 = st.columns( 2 )
				with history_c1:
					st.selectbox( 'Replay Window',
						options=[ '1 Hour', '6 Hours', '24 Hours', '7 Days', '30 Days', 'All Retained' ],
						key='live_world_history_window' )
				with history_c2:
					st.slider( 'Retention (Days)', min_value=1, max_value=365, step=1,
						key='live_world_history_retention_days' )
				st.slider( 'Max Rows / Source / Refresh', min_value=100, max_value=10000,
					step=100, key='live_world_history_max_rows_per_source' )
				st.multiselect( 'Replay Entity Types',
					options=[ 'Aircraft', 'Military Aircraft', 'Satellite', 'Vessel',
						'Earthquake', 'Fire', 'Infrastructure', 'Camera', 'Map Feature' ], key='live_world_history_entity_types' )
				st.slider( 'Replay Record Limit', min_value=100, max_value=25000, step=100,
					key='live_world_history_limit' )
				history_hours = get_live_world_history_window_hours(
					str( st.session_state[ 'live_world_history_window' ] ) )
				snapshot_options = get_live_world_history_snapshots( history_hours )
				if snapshot_options:
					if st.session_state[ 'live_world_history_snapshot' ] not in snapshot_options:
						st.session_state[ 'live_world_history_snapshot' ] = snapshot_options[ 0 ]
					st.selectbox( 'Replay Snapshot', options=snapshot_options,
						key='live_world_history_snapshot' )
				else:
					st.session_state[ 'live_world_history_snapshot' ] = ''
					st.caption( 'No persisted Live World snapshots are available in this window.' )
				history_b1, history_b2 = st.columns( 2 )
				with history_b1:
					if st.button( 'Purge Expired', icon='🧹', key='live_world_history_purge',
							width='stretch' ):
						purge_live_world_history(
							int( st.session_state[ 'live_world_history_retention_days' ] ) )
				with history_b2:
					if st.button( 'Clear History', icon='🗑️', key='live_world_history_clear',
							width='stretch' ):
						clear_live_world_history( )
						st.session_state[ 'live_world_history_snapshot' ] = ''
						st.session_state[ 'live_world_history_last_saved' ] = 0
						st.session_state[ 'live_world_history_last_error' ] = ''
			st.checkbox( AI_ADVANCED_TOOLS[ 'agent_tools' ], key='live_world_agent_tools' )

def clear_live_world_data( ) -> None:
	'''

	Purpose:
		Clear retrieved Live World Data while preserving layer selections and map controls.

	Returns:
		None

	'''
	initialize_live_world_state( )
	st.session_state[ 'live_world_df_entities' ] = pd.DataFrame( )
	st.session_state[ 'live_world_df_aircraft' ] = pd.DataFrame( )
	st.session_state[ 'live_world_df_military_aircraft' ] = pd.DataFrame( )
	st.session_state[ 'live_world_df_satellites' ] = pd.DataFrame( )
	st.session_state[ 'live_world_df_vessels' ] = pd.DataFrame( )
	st.session_state[ 'live_world_df_earthquakes' ] = pd.DataFrame( )
	st.session_state[ 'live_world_df_fires' ] = pd.DataFrame( )
	st.session_state[ 'live_world_df_infrastructure' ] = pd.DataFrame( )
	st.session_state[ 'live_world_df_cameras' ] = pd.DataFrame( )
	st.session_state[ 'live_world_df_map_layers' ] = pd.DataFrame( )
	st.session_state[ 'live_world_aircraft_result' ] = { }
	st.session_state[ 'live_world_military_aircraft_result' ] = { }
	st.session_state[ 'live_world_satellite_result' ] = [ ]
	st.session_state[ 'live_world_satellite_propagation_attempts' ] = 0
	st.session_state[ 'live_world_satellite_propagation_failures' ] = 0
	st.session_state[ 'live_world_vessel_result' ] = [ ]
	st.session_state[ 'live_world_earthquake_result' ] = { }
	st.session_state[ 'live_world_firms_result' ] = { }
	st.session_state[ 'live_world_firms_source_count' ] = 0
	st.session_state[ 'live_world_firms_truncated' ] = False
	st.session_state[ 'live_world_infrastructure_result' ] = { }
	st.session_state[ 'live_world_camera_result' ] = { }
	st.session_state[ 'live_world_map_layer_result' ] = { }
	st.session_state[ 'live_world_tracking_history' ] = [ ]
	st.session_state[ 'live_world_tracking_active_entity' ] = ''
	st.session_state[ 'live_world_annotations' ] = [ ]
	st.session_state[ 'live_world_geofence_events' ] = [ ]
	st.session_state[ 'live_world_geofence_snapshot' ] = { }
	st.session_state[ 'live_world_geofence_initialized' ] = False
	st.session_state[ 'live_world_geofence_last_refresh_processed' ] = ''
	st.session_state[ 'live_world_last_refresh' ] = ''
	st.session_state[ 'live_world_last_error' ] = ''
	st.session_state[ 'live_world_source_status' ] = {
		key: 'Not Refreshed' for key in LIVE_WORLD_DATA_SOURCES }
	st.session_state[ 'live_world_source_errors' ] = {
		key: '' for key in LIVE_WORLD_DATA_SOURCES }
	st.session_state[ 'live_world_source_last_attempt' ] = {
		key: '' for key in LIVE_WORLD_DATA_SOURCES }
	st.session_state[ 'live_world_source_last_success' ] = {
		key: '' for key in LIVE_WORLD_DATA_SOURCES }
	st.session_state[ 'live_world_source_stale' ] = {
		key: False for key in LIVE_WORLD_DATA_SOURCES }
	st.session_state[ 'live_world_refresh_requested' ] = False

def create_live_world_bounding_box( latitude: float, longitude: float,
		delta: float=2.0 ) -> str:
	'''

	Purpose:
		Create a NASA FIRMS area-coordinate string centered on the supplied location.

	Args:
		latitude (float): Center latitude.
		longitude (float): Center longitude.
		delta (float): Decimal-degree offset used to create the bounding box.

	Returns:
		str: FIRMS west,south,east,north area-coordinate string.

	'''
	throw_if( 'latitude', latitude )
	throw_if( 'longitude', longitude )
	if type( latitude ) not in (int, float) or not -90 <= latitude <= 90:
		raise ValueError( 'latitude must be between -90 and 90 degrees.' )
	if type( longitude ) not in (int, float) or not -180 <= longitude <= 180:
		raise ValueError( 'longitude must be between -180 and 180 degrees.' )
	if type( delta ) not in (int, float) or not 0 < delta <= 180:
		raise ValueError( 'delta must be positive and no greater than 180.' )
	west = max( -180.0, longitude - delta )
	south = max( -90.0, latitude - delta )
	east = min( 180.0, longitude + delta )
	north = min( 90.0, latitude + delta )
	return f'{west:.6f},{south:.6f},{east:.6f},{north:.6f}'

def fetch_live_aircraft( latitude: float, longitude: float ) -> pd.DataFrame:
	'''

	Purpose:
		Retrieve current OpenSky aircraft state vectors around the Iyr/global location and
		normalize positioned aircraft for Live World rendering.

	Args:
		latitude (float): Geographic center latitude.
		longitude (float): Geographic center longitude.

	Returns:
		pd.DataFrame: Normalized aircraft entities.

	'''
	initialize_live_world_state( )
	throw_if( 'latitude', latitude )
	throw_if( 'longitude', longitude )
	client_id = str( st.session_state.get( 'opensky_api_client_id', '' ) or '' )
	client_secret = str( st.session_state.get( 'opensky_api_client_secret', '' ) or '' )
	radius = float( st.session_state[ 'live_world_aircraft_radius' ] )
	airborne_only = bool( st.session_state[ 'live_world_aircraft_airborne_only' ] )
	service = OpenSkyLive( client_id=client_id, client_secret=client_secret, timeout=20 )
	result = service.fetch_states( latitude=latitude, longitude=longitude,
		radius_degrees=radius ) or { }
	states = result.get( 'states', [ ] ) or [ ]
	entities: List[ GeoEntity ] = [ ]

	for state in states:
		if not isinstance( state, list ) or len( state ) < 17:
			continue

		icao24 = str( state[ 0 ] or '' ).strip( )
		callsign = str( state[ 1 ] or '' ).strip( )
		longitude_value = state[ 5 ]
		latitude_value = state[ 6 ]
		if latitude_value is None or longitude_value is None:
			continue

		on_ground = bool( state[ 8 ] )
		if airborne_only and on_ground:
			continue

		try:
			lat = float( latitude_value )
			lon = float( longitude_value )
		except ( TypeError, ValueError ):
			continue

		geo_altitude = state[ 13 ] if len( state ) > 13 else None
		baro_altitude = state[ 7 ] if len( state ) > 7 else None
		altitude = geo_altitude if geo_altitude is not None else baro_altitude
		try:
			altitude_value = float( altitude ) if altitude is not None else 0.0
		except ( TypeError, ValueError ):
			altitude_value = 0.0

		velocity = state[ 9 ] if len( state ) > 9 else None
		heading = state[ 10 ] if len( state ) > 10 else None
		try:
			velocity_value = float( velocity ) if velocity is not None else 0.0
		except ( TypeError, ValueError ):
			velocity_value = 0.0
		try:
			heading_value = float( heading ) if heading is not None else 0.0
		except ( TypeError, ValueError ):
			heading_value = 0.0

		metadata = {
			'ICAO24': icao24,
			'Callsign': callsign,
			'Origin Country': state[ 2 ],
			'Time Position': state[ 3 ],
			'Last Contact': state[ 4 ],
			'Barometric Altitude': baro_altitude,
			'Geometric Altitude': geo_altitude,
			'Vertical Rate': state[ 11 ] if len( state ) > 11 else None,
			'On Ground': on_ground,
			'Squawk': state[ 14 ] if len( state ) > 14 else None,
			'SPI': state[ 15 ] if len( state ) > 15 else None,
			'Position Source': state[ 16 ] if len( state ) > 16 else None,
			'Category': state[ 17 ] if len( state ) > 17 else None,
		}
		entities.append( GeoEntity(
			entity_id=icao24 or f'OPENSKY-{len( entities ) + 1}',
			entity_type='Aircraft',
			name=callsign or icao24,
			latitude=lat,
			longitude=lon,
			altitude=altitude_value,
			heading=heading_value,
			speed=velocity_value,
			timestamp=str( state[ 4 ] or '' ),
			source='OpenSky Network',
			metadata=metadata ) )

	st.session_state[ 'live_world_aircraft_result' ] = result
	return entities_to_dataframe( entities )

def calculate_live_world_distance_nm( latitude_a: float, longitude_a: float,
		latitude_b: float, longitude_b: float ) -> float:
	'''

	Purpose:
		Calculate great-circle distance between two geospatial points in nautical miles.

	Args:
		latitude_a (float): First latitude.
		longitude_a (float): First longitude.
		latitude_b (float): Second latitude.
		longitude_b (float): Second longitude.

	Returns:
		float: Great-circle distance in nautical miles.

	'''
	throw_if( 'latitude_a', latitude_a )
	throw_if( 'longitude_a', longitude_a )
	throw_if( 'latitude_b', latitude_b )
	throw_if( 'longitude_b', longitude_b )
	lat_a = math.radians( float( latitude_a ) )
	lat_b = math.radians( float( latitude_b ) )
	delta_lat = math.radians( float( latitude_b ) - float( latitude_a ) )
	delta_lon = math.radians( float( longitude_b ) - float( longitude_a ) )
	value = (math.sin( delta_lat / 2.0 ) ** 2
		+ math.cos( lat_a ) * math.cos( lat_b ) * math.sin( delta_lon / 2.0 ) ** 2)
	central_angle = 2.0 * math.atan2( math.sqrt( value ), math.sqrt( 1.0 - value ) )
	return 3440.065 * central_angle

def fetch_live_military_aircraft( latitude: float, longitude: float ) -> pd.DataFrame:
	'''

	Purpose:
		Retrieve ADSB.lol military-tagged aircraft and normalize aircraft within the
		configured nautical-mile radius around the current Iyr location.

	Args:
		latitude (float): Geographic center latitude.
		longitude (float): Geographic center longitude.

	Returns:
		pd.DataFrame: Normalized military-aircraft entities.

	'''
	initialize_live_world_state( )
	throw_if( 'latitude', latitude )
	throw_if( 'longitude', longitude )
	radius_nm = float( st.session_state[ 'live_world_military_radius_nm' ] )
	service = AdsbLolMilitary( timeout=20 )
	result = service.fetch_military( latitude=latitude, longitude=longitude,
		radius_nm=radius_nm ) or { }
	rows = result.get( 'ac', [ ] ) or [ ]
	entities: List[ GeoEntity ] = [ ]

	for index, row in enumerate( rows ):
		if not isinstance( row, dict ):
			continue
		latitude_value = row.get( 'lat', None )
		longitude_value = row.get( 'lon', None )
		if latitude_value is None or longitude_value is None:
			continue

		try:
			lat = float( latitude_value )
			lon = float( longitude_value )
		except ( TypeError, ValueError ):
			continue

		distance_nm = calculate_live_world_distance_nm( latitude, longitude, lat, lon )
		if distance_nm > radius_nm:
			continue

		altitude = row.get( 'alt_geom', row.get( 'alt_baro', 0.0 ) )
		ground_speed = row.get( 'gs', 0.0 )
		heading = row.get( 'track', row.get( 'true_heading', 0.0 ) )
		try:
			altitude_meters = float( altitude ) * 0.3048 if altitude not in [ None, 'ground' ] else 0.0
		except ( TypeError, ValueError ):
			altitude_meters = 0.0
		try:
			speed_mps = float( ground_speed ) * 0.514444 if ground_speed is not None else 0.0
		except ( TypeError, ValueError ):
			speed_mps = 0.0
		try:
			heading_value = float( heading ) if heading is not None else 0.0
		except ( TypeError, ValueError ):
			heading_value = 0.0

		hex_id = str( row.get( 'hex', '' ) or '' ).strip( )
		flight = str( row.get( 'flight', '' ) or '' ).strip( )
		registration = str( row.get( 'r', '' ) or '' ).strip( )
		metadata = {
			'ICAO Hex': hex_id,
			'Callsign': flight,
			'Registration': registration,
			'Aircraft Type': row.get( 't', '' ),
			'Description': row.get( 'desc', '' ),
			'Category': row.get( 'category', '' ),
			'Squawk': row.get( 'squawk', '' ),
			'Emergency': row.get( 'emergency', '' ),
			'DB Flags': row.get( 'dbFlags', 1 ),
			'Altitude (ft)': altitude,
			'Ground Speed (kt)': ground_speed,
			'Vertical Rate': row.get( 'baro_rate', row.get( 'geom_rate', None ) ),
			'Distance (NM)': round( distance_nm, 2 ),
		}
		entities.append( GeoEntity(
			entity_id=hex_id or f'ADSBLOL-MIL-{index + 1}',
			entity_type='Military Aircraft',
			name=flight or registration or hex_id,
			latitude=lat,
			longitude=lon,
			altitude=altitude_meters,
			heading=heading_value,
			speed=speed_mps,
			timestamp=dt.datetime.now( dt.timezone.utc ).isoformat( ),
			source='ADSB.lol',
			metadata=metadata ) )

	st.session_state[ 'live_world_military_aircraft_result' ] = result
	return entities_to_dataframe( entities )

def fetch_live_vessels( latitude: float, longitude: float ) -> pd.DataFrame:
	'''

	Purpose:
		Retrieve a bounded live AIS Stream vessel sample around the current Iyr location
		and normalize the messages for Live World rendering and tracking.

	Args:
		latitude (float): Geographic center latitude.
		longitude (float): Geographic center longitude.

	Returns:
		pd.DataFrame: Normalized vessel entities.

	'''
	initialize_live_world_state( )
	throw_if( 'latitude', latitude )
	throw_if( 'longitude', longitude )
	api_key = str( st.session_state.get( 'live_world_aisstream_api_key', '' ) or '' )
	throw_if( 'live_world_aisstream_api_key', api_key )
	radius = float( st.session_state[ 'live_world_vessel_radius' ] )
	limit = int( st.session_state[ 'live_world_vessel_limit' ] )
	service = AisStreamLive( api_key=api_key, timeout=5 )
	result = service.fetch_positions( latitude=latitude, longitude=longitude,
		radius_degrees=radius, max_messages=limit, duration_seconds=3.0 )
	entities_by_mmsi: Dict[ str, GeoEntity ] = { }

	for index, envelope in enumerate( result ):
		metadata_source = envelope.get( 'MetaData', { } ) or { }
		message_type = str( envelope.get( 'MessageType', '' ) or '' )
		message = envelope.get( 'Message', { } ) or { }
		body = message.get( message_type, { } ) or { }
		latitude_value = metadata_source.get( 'Latitude', body.get( 'Latitude', None ) )
		longitude_value = metadata_source.get( 'Longitude', body.get( 'Longitude', None ) )
		if latitude_value is None or longitude_value is None:
			continue

		try:
			lat = float( latitude_value )
			lon = float( longitude_value )
		except ( TypeError, ValueError ):
			continue

		mmsi = str( metadata_source.get( 'MMSI', body.get( 'UserID', '' ) ) or '' )
		ship_name = str( metadata_source.get( 'ShipName', '' ) or '' ).strip( )
		speed_knots = body.get( 'Sog', 0.0 )
		heading = body.get( 'TrueHeading', body.get( 'Cog', 0.0 ) )
		try:
			speed_mps = float( speed_knots ) * 0.514444 if speed_knots is not None else 0.0
		except ( TypeError, ValueError ):
			speed_mps = 0.0
		try:
			heading_value = float( heading ) if heading is not None else 0.0
		except ( TypeError, ValueError ):
			heading_value = 0.0

		metadata = {
			'MMSI': mmsi,
			'Message Type': message_type,
			'Speed Over Ground (kt)': speed_knots,
			'Course Over Ground': body.get( 'Cog', None ),
			'True Heading': body.get( 'TrueHeading', None ),
			'Navigational Status': body.get( 'NavigationalStatus', None ),
			'Position Accuracy': body.get( 'PositionAccuracy', None ),
			'RAIM': body.get( 'Raim', None ),
		}
		entity_id = mmsi or f'AIS-{index + 1}'
		entities_by_mmsi[ entity_id ] = GeoEntity(
			entity_id=entity_id,
			entity_type='Vessel',
			name=ship_name or entity_id,
			latitude=lat,
			longitude=lon,
			altitude=0.0,
			heading=heading_value,
			speed=speed_mps,
			timestamp=dt.datetime.now( dt.timezone.utc ).isoformat( ),
			source='AIS Stream',
			metadata=metadata )

	st.session_state[ 'live_world_vessel_result' ] = result
	return entities_to_dataframe( list( entities_by_mmsi.values( ) ) )

def fetch_live_satellites( ) -> pd.DataFrame:
	'''

	Purpose:
		Retrieve current CelesTrak OMM records, propagate each orbit to the current UTC time,
		and normalize successfully propagated satellites for Live World rendering.

	Returns:
		pd.DataFrame: Normalized satellite entities.

	'''
	initialize_live_world_state( )
	st.session_state[ 'live_world_satellite_propagation_attempts' ] = 0
	st.session_state[ 'live_world_satellite_propagation_failures' ] = 0
	group = str( st.session_state[ 'live_world_satellite_group' ] )
	limit = int( st.session_state[ 'live_world_satellite_limit' ] )
	service = CelesTrakLive( timeout=20 )
	records = service.fetch_group( group=group, limit=limit )
	when = dt.datetime.now( dt.timezone.utc )
	entities: List[ GeoEntity ] = [ ]
	failures = 0
	st.session_state[ 'live_world_satellite_propagation_attempts' ] = len( records )

	for record in records:
		try:
			position = service.propagate( record=record, when=when )
		except Exception:
			failures += 1
			continue

		catalog_number = str( position.get( 'CatalogNumber', '' ) or '' )
		name = str( position.get( 'Name', '' ) or catalog_number )
		metadata = {
			'Catalog Number': catalog_number,
			'Object ID': position.get( 'ObjectId', '' ),
			'Epoch': position.get( 'Epoch', '' ),
			'Classification': position.get( 'Classification', '' ),
			'Group': group,
		}
		entities.append( GeoEntity(
			entity_id=catalog_number or name,
			entity_type='Satellite',
			name=name,
			latitude=float( position[ 'Latitude' ] ),
			longitude=float( position[ 'Longitude' ] ),
			altitude=float( position[ 'Altitude' ] ),
			heading=0.0,
			speed=float( position[ 'Velocity' ] ),
			timestamp=when.isoformat( ),
			source='CelesTrak',
			metadata=metadata ) )

	st.session_state[ 'live_world_satellite_propagation_failures' ] = failures
	st.session_state[ 'live_world_satellite_result' ] = records
	if records and not entities:
		raise RuntimeError(
			f'CelesTrak returned {len( records )} records but every propagation failed.' )
	return entities_to_dataframe( entities )

def fetch_live_earthquakes( ) -> pd.DataFrame:
	'''

	Purpose:
		Retrieve the selected USGS earthquake feed through Iyr's existing provider and
		normalize matching events for Live World rendering.

	Returns:
		pd.DataFrame: Normalized earthquake entities.

	'''
	initialize_live_world_state( )
	feed = str( st.session_state[ 'live_world_earthquake_feed' ] )
	min_magnitude = float( st.session_state[ 'live_world_earthquake_min_magnitude' ] )
	service = USGSEarthquakes( )
	result = service.fetch( mode='feed', feed=feed, time=20 ) or { }
	rows = result.get( 'rows', [ ] ) or [ ]
	entities: List[ GeoEntity ] = [ ]

	for index, row in enumerate( rows ):
		latitude = row.get( 'Latitude', None )
		longitude = row.get( 'Longitude', None )
		magnitude = row.get( 'Magnitude', None )
		if latitude is None or longitude is None:
			continue

		try:
			magnitude_value = float( magnitude ) if magnitude is not None else 0.0
			latitude_value = float( latitude )
			longitude_value = float( longitude )
		except ( TypeError, ValueError ):
			continue

		if magnitude_value < min_magnitude:
			continue

		depth = row.get( 'Depth (km)', 0.0 )
		try:
			depth_value = float( depth ) if depth is not None else 0.0
		except ( TypeError, ValueError ):
			depth_value = 0.0

		entity_id = str( row.get( 'Id', '' ) or f'USGS-{index + 1}' )
		metadata = {
			'Magnitude': magnitude_value,
			'Depth (km)': depth_value,
			'Alert': row.get( 'Alert', '' ),
			'Status': row.get( 'Status', '' ),
			'Tsunami': row.get( 'Tsunami', None ),
			'Felt Reports': row.get( 'Felt Reports', None ),
			'Event Type': row.get( 'Event Type', '' ),
			'URL': row.get( 'URL', '' ),
		}
		entities.append( GeoEntity(
			entity_id=entity_id,
			entity_type='Earthquake',
			name=str( row.get( 'Place', '' ) or entity_id ),
			latitude=latitude_value,
			longitude=longitude_value,
			altitude=-depth_value,
			heading=0.0,
			speed=0.0,
			timestamp=str( row.get( 'Time', '' ) or '' ),
			source='USGS Earthquakes',
			metadata=metadata ) )

	st.session_state[ 'live_world_earthquake_result' ] = result
	return entities_to_dataframe( entities )

def fetch_live_fires( latitude: float, longitude: float ) -> pd.DataFrame:
	'''

	Purpose:
		Retrieve NASA FIRMS active-fire detections through Iyr's existing Firms provider
		and normalize the response for Live World rendering.

	Args:
		latitude (float): Current Iyr/global latitude used for local bounding-box mode.
		longitude (float): Current Iyr/global longitude used for local bounding-box mode.

	Returns:
		pd.DataFrame: Normalized FIRMS fire entities.

	'''
	initialize_live_world_state( )
	throw_if( 'latitude', latitude )
	throw_if( 'longitude', longitude )
	st.session_state[ 'live_world_firms_source_count' ] = 0
	st.session_state[ 'live_world_firms_truncated' ] = False
	source = str( st.session_state[ 'live_world_firms_source' ] )
	day_range = int( st.session_state[ 'live_world_firms_day_range' ] )
	area_mode = str( st.session_state[ 'live_world_firms_area_mode' ] )
	area_coordinates = 'world' if area_mode == 'World' else create_live_world_bounding_box(
		latitude, longitude )

	service = Firms( )
	result = service.fetch_area(
		source=source,
		area_coordinates=area_coordinates,
		day_range=day_range,
		date='',
		time=20 ) or { }
	rows = result.get( 'rows', [ ] ) or [ ]
	max_records = int( st.session_state[ 'live_world_firms_max_records' ] )
	st.session_state[ 'live_world_firms_source_count' ] = len( rows )
	st.session_state[ 'live_world_firms_truncated' ] = len( rows ) > max_records
	rows = rows[ :max_records ]
	entities: List[ GeoEntity ] = [ ]

	for index, row in enumerate( rows ):
		latitude_value = get_row_value( row, [ 'latitude', 'Latitude' ] )
		longitude_value = get_row_value( row, [ 'longitude', 'Longitude' ] )
		if latitude_value is None or longitude_value is None:
			continue

		try:
			lat = float( latitude_value )
			lon = float( longitude_value )
		except ( TypeError, ValueError ):
			continue

		acq_date = str( get_row_value( row,
			[ 'acq_date', 'Acq Date', 'Acquisition Date' ] ) or '' )
		acq_time = str( get_row_value( row,
			[ 'acq_time', 'Acq Time', 'Acquisition Time' ] ) or '' )
		satellite = str( get_row_value( row, [ 'satellite', 'Satellite' ] ) or source )
		metadata = {
			'Satellite': satellite,
			'Instrument': get_row_value( row, [ 'instrument', 'Instrument' ] ),
			'Confidence': get_row_value( row, [ 'confidence', 'Confidence' ] ),
			'FRP': get_row_value( row, [ 'frp', 'FRP' ] ),
			'Brightness': get_row_value( row,
				[ 'bright_ti4', 'brightness', 'Brightness', 'bright_t31' ] ),
			'Day/Night': get_row_value( row, [ 'daynight', 'Day/Night' ] ),
			'Version': get_row_value( row, [ 'version', 'Version' ] ),
		}
		entity_id = (
			f'FIRMS-{source}-{acq_date}-{acq_time}-{lat:.5f}-{lon:.5f}' )
		entities.append( GeoEntity(
			entity_id=entity_id,
			entity_type='Fire',
			name=f'Active Fire - {satellite}',
			latitude=lat,
			longitude=lon,
			altitude=0.0,
			heading=0.0,
			speed=0.0,
			timestamp=f'{acq_date} {acq_time}'.strip( ),
			source='NASA FIRMS',
			metadata=metadata ) )

	st.session_state[ 'live_world_firms_result' ] = result
	return entities_to_dataframe( entities )

def fetch_live_infrastructure( latitude: float, longitude: float ) -> pd.DataFrame:
	'''

	Purpose:
		Retrieve public infrastructure features from OpenStreetMap Overpass and normalize
		them into the Live World GeoEntity contract.

	Args:
		latitude (float): Current Iyr/global latitude.
		longitude (float): Current Iyr/global longitude.

	Returns:
		pd.DataFrame: Normalized infrastructure entities.

	'''
	initialize_live_world_state( )
	throw_if( 'latitude', latitude )
	throw_if( 'longitude', longitude )
	categories = list( st.session_state.get( 'live_world_infrastructure_categories', [ ] ) or [ ] )
	if not categories:
		return entities_to_dataframe( [ ] )
	radius_km = float( st.session_state[ 'live_world_infrastructure_radius_km' ] )
	limit = int( st.session_state[ 'live_world_infrastructure_limit' ] )
	service = OverpassInfrastructure( timeout=30 )
	result = service.fetch_infrastructure( latitude, longitude, radius_km, categories, limit )
	elements = result.get( 'elements', [ ] ) or [ ]
	entities: List[ GeoEntity ] = [ ]
	observed_at = dt.datetime.now( dt.timezone.utc ).isoformat( )

	for element in elements:
		if not isinstance( element, dict ):
			continue
		center = element.get( 'center', { } ) or { }
		latitude_value = element.get( 'lat', center.get( 'lat', None ) )
		longitude_value = element.get( 'lon', center.get( 'lon', None ) )
		if latitude_value is None or longitude_value is None:
			continue
		try:
			lat = float( latitude_value )
			lon = float( longitude_value )
		except ( TypeError, ValueError ):
			continue
		tags = element.get( 'tags', { } ) or { }
		category = str( element.get( 'InfrastructureCategory', '' ) or 'Infrastructure' )
		osm_type = str( element.get( 'type', '' ) or '' )
		osm_id = str( element.get( 'id', '' ) or '' )
		entity_id = f'OSM-{osm_type}-{osm_id}'
		name = str( tags.get( 'name', '' ) or tags.get( 'operator', '' ) or f'{category} {osm_id}' )
		metadata = {
			'Category': category,
			'OSM Type': osm_type,
			'OSM ID': osm_id,
			'Operator': tags.get( 'operator', '' ),
			'IATA': tags.get( 'iata', '' ),
			'ICAO': tags.get( 'icao', '' ),
			'Website': tags.get( 'website', '' ),
			'Tags': tags,
		}
		entities.append( GeoEntity(
			entity_id=entity_id,
			entity_type='Infrastructure',
			name=name,
			latitude=lat,
			longitude=lon,
			altitude=0.0,
			heading=0.0,
			speed=0.0,
			timestamp=observed_at,
			source='OpenStreetMap Overpass',
			metadata=metadata ) )

	st.session_state[ 'live_world_infrastructure_result' ] = result
	return entities_to_dataframe( entities )

def fetch_live_cameras( latitude: float, longitude: float ) -> pd.DataFrame:
	'''

	Purpose:
		Retrieve public CCTV, surveillance-camera, and webcam features from OpenStreetMap
		Overpass and normalize them into the Live World GeoEntity contract.

	Args:
		latitude (float): Current Iyr/global latitude.
		longitude (float): Current Iyr/global longitude.

	Returns:
		pd.DataFrame: Normalized camera entities.

	'''
	initialize_live_world_state( )
	throw_if( 'latitude', latitude )
	throw_if( 'longitude', longitude )
	categories = list( st.session_state.get( 'live_world_camera_categories', [ ] ) or [ ] )
	if not categories:
		return entities_to_dataframe( [ ] )
	radius_km = float( st.session_state[ 'live_world_camera_radius_km' ] )
	limit = int( st.session_state[ 'live_world_camera_limit' ] )
	service = OverpassCameras( timeout=30 )
	result = service.fetch_cameras( latitude, longitude, radius_km, categories, limit )
	elements = result.get( 'elements', [ ] ) or [ ]
	entities: List[ GeoEntity ] = [ ]
	observed_at = dt.datetime.now( dt.timezone.utc ).isoformat( )

	for element in elements:
		if not isinstance( element, dict ):
			continue
		center = element.get( 'center', { } ) or { }
		latitude_value = element.get( 'lat', center.get( 'lat', None ) )
		longitude_value = element.get( 'lon', center.get( 'lon', None ) )
		if latitude_value is None or longitude_value is None:
			continue
		try:
			lat = float( latitude_value )
			lon = float( longitude_value )
		except ( TypeError, ValueError ):
			continue
		tags = element.get( 'tags', { } ) or { }
		category = str( element.get( 'CameraCategory', '' ) or 'Camera' )
		osm_type = str( element.get( 'type', '' ) or '' )
		osm_id = str( element.get( 'id', '' ) or '' )
		entity_id = f'OSM-CAMERA-{osm_type}-{osm_id}'
		web_url = str( tags.get( 'webcam', '' ) or tags.get( 'contact:webcam', '' )
			or tags.get( 'website', '' ) or tags.get( 'url', '' ) or '' )
		name = str( tags.get( 'name', '' ) or tags.get( 'operator', '' )
			or f'{category} {osm_id}' )
		metadata = {
			'Category': category,
			'OSM Type': osm_type,
			'OSM ID': osm_id,
			'Operator': tags.get( 'operator', '' ),
			'Surveillance Type': tags.get( 'surveillance:type', '' ),
			'Surveillance Zone': tags.get( 'surveillance:zone', '' ),
			'Direction': tags.get( 'camera:direction', tags.get( 'direction', '' ) ),
			'Web URL': web_url,
			'Tags': tags,
		}
		entities.append( GeoEntity(
			entity_id=entity_id,
			entity_type='Camera',
			name=name,
			latitude=lat,
			longitude=lon,
			altitude=0.0,
			heading=0.0,
			speed=0.0,
			timestamp=observed_at,
			source='OpenStreetMap Overpass',
			metadata=metadata ) )

	st.session_state[ 'live_world_camera_result' ] = result
	return entities_to_dataframe( entities )

def fetch_live_map_layers( latitude: float, longitude: float ) -> pd.DataFrame:
	'''

	Purpose:
		Retrieve selected contextual public map features from OpenStreetMap Overpass and
		normalize them into the Live World GeoEntity contract.

	Args:
		latitude (float): Current Iyr/global latitude.
		longitude (float): Current Iyr/global longitude.

	Returns:
		pd.DataFrame: Normalized contextual map features.

	'''
	initialize_live_world_state( )
	throw_if( 'latitude', latitude )
	throw_if( 'longitude', longitude )
	categories = list( st.session_state.get( 'live_world_map_layer_categories', [ ] ) or [ ] )
	if not categories:
		return entities_to_dataframe( [ ] )
	radius_km = float( st.session_state[ 'live_world_map_layer_radius_km' ] )
	limit = int( st.session_state[ 'live_world_map_layer_limit' ] )
	service = OverpassMapLayers( timeout=30 )
	result = service.fetch_features( latitude, longitude, radius_km, categories, limit )
	elements = result.get( 'elements', [ ] ) or [ ]
	entities: List[ GeoEntity ] = [ ]
	observed_at = dt.datetime.now( dt.timezone.utc ).isoformat( )

	for element in elements:
		if not isinstance( element, dict ):
			continue
		center = element.get( 'center', { } ) or { }
		latitude_value = element.get( 'lat', center.get( 'lat', None ) )
		longitude_value = element.get( 'lon', center.get( 'lon', None ) )
		if latitude_value is None or longitude_value is None:
			continue
		try:
			lat = float( latitude_value )
			lon = float( longitude_value )
		except ( TypeError, ValueError ):
			continue
		tags = element.get( 'tags', { } ) or { }
		category = str( element.get( 'MapLayerCategory', '' ) or 'Map Feature' )
		osm_type = str( element.get( 'type', '' ) or '' )
		osm_id = str( element.get( 'id', '' ) or '' )
		entity_id = f'OSM-MAP-{osm_type}-{osm_id}'
		name = str( tags.get( 'name', '' ) or tags.get( 'operator', '' )
			or tags.get( 'brand', '' ) or f'{category} {osm_id}' )
		metadata = {
			'Category': category,
			'OSM Type': osm_type,
			'OSM ID': osm_id,
			'Operator': tags.get( 'operator', '' ),
			'Network': tags.get( 'network', '' ),
			'Website': tags.get( 'website', '' ),
			'Amenity': tags.get( 'amenity', '' ),
			'Public Transport': tags.get( 'public_transport', '' ),
			'Tags': tags,
		}
		entities.append( GeoEntity(
			entity_id=entity_id,
			entity_type='Map Feature',
			name=name,
			latitude=lat,
			longitude=lon,
			altitude=0.0,
			heading=0.0,
			speed=0.0,
			timestamp=observed_at,
			source='OpenStreetMap Overpass',
			metadata=metadata ) )

	st.session_state[ 'live_world_map_layer_result' ] = result
	return entities_to_dataframe( entities )

def get_row_value( row: Dict[ str, Any ], keys: List[ str ] ) -> object:
	'''

	Purpose:
		Read the first available value from an explicit list of known provider keys.

	Args:
		row (Dict[str, Any]): Provider row.
		keys (List[str]): Ordered known keys for the same source field.

	Returns:
		object: Matching value or None.

	'''
	if not isinstance( row, dict ):
		raise TypeError( 'row must be a dictionary.' )
	throw_if( 'keys', keys )
	for key in keys:
		if key in row:
			return row[ key ]
	return None

def entities_to_dataframe( entities: List[ GeoEntity ] ) -> pd.DataFrame:
	'''

	Purpose:
		Convert normalized GeoEntity objects into the Live World DataFrame contract.

	Args:
		entities (List[GeoEntity]): Normalized geospatial entities.

	Returns:
		pd.DataFrame: Live World entity records.

	'''
	columns = [ 'EntityId', 'EntityType', 'Name', 'Latitude', 'Longitude', 'Altitude',
		'Heading', 'Speed', 'Timestamp', 'Source', 'Metadata' ]
	if not entities:
		return pd.DataFrame( columns=columns )

	rows: List[ Dict[ str, object ] ] = [ ]
	for entity in entities:
		row = asdict( entity )
		rows.append( {
			'EntityId': row[ 'entity_id' ],
			'EntityType': row[ 'entity_type' ],
			'Name': row[ 'name' ],
			'Latitude': row[ 'latitude' ],
			'Longitude': row[ 'longitude' ],
			'Altitude': row[ 'altitude' ],
			'Heading': row[ 'heading' ],
			'Speed': row[ 'speed' ],
			'Timestamp': row[ 'timestamp' ],
			'Source': row[ 'source' ],
			'Metadata': row[ 'metadata' ],
		} )
	return pd.DataFrame( rows, columns=columns )

def get_live_world_tracking_options( ) -> Dict[ str, str ]:
	'''

	Purpose:
		Return selectable moving entities from the current Live World entity frame.

	Returns:
		Dict[str, str]: Tracking keys mapped to human-readable labels.

	'''
	initialize_live_world_state( )
	df_entities = st.session_state.get( 'live_world_df_entities', pd.DataFrame( ) )
	if df_entities is None or df_entities.empty:
		return { }

	required = [ 'EntityId', 'EntityType', 'Name' ]
	if any( column not in df_entities.columns for column in required ):
		return { }

	df_tracking = df_entities[ df_entities[ 'EntityType' ].isin(
		[ 'Aircraft', 'Military Aircraft', 'Satellite', 'Vessel' ] ) ].copy( )
	options: Dict[ str, str ] = { }
	for _, row in df_tracking.iterrows( ):
		entity_id = str( row[ 'EntityId' ] )
		entity_type = str( row[ 'EntityType' ] )
		name = str( row[ 'Name' ] )
		tracking_key = f'{entity_type}::{entity_id}'
		options[ tracking_key ] = f'{entity_type} | {name} | {entity_id}'
	return options

def get_live_world_measurement_options( ) -> Dict[ str, str ]:
	'''

	Purpose:
		Return selectable measurement endpoints from current location and loaded entities.

	Returns:
		Dict[str, str]: Measurement endpoint keys mapped to display labels.

	'''
	initialize_live_world_state( )
	options: Dict[ str, str ] = {
		'Current Location': 'Current Location',
		'Custom Point': 'Custom Point',
	}
	df_entities = st.session_state.get( 'live_world_df_entities', pd.DataFrame( ) )
	if df_entities is None or df_entities.empty:
		return options
	for _, row in df_entities.iterrows( ):
		entity_id = str( row[ 'EntityId' ] )
		entity_type = str( row[ 'EntityType' ] )
		name = str( row[ 'Name' ] )
		key = f'Entity::{entity_type}::{entity_id}'
		options[ key ] = f'{entity_type} | {name} | {entity_id}'
	return options

def resolve_live_world_measurement_point( key: str, latitude: float,
		longitude: float, endpoint: str ) -> Dict[ str, object ]:
	'''

	Purpose:
		Resolve one configured measurement endpoint into coordinates and a display label.

	Args:
		key (str): Selected endpoint key.
		latitude (float): Current Iyr/global latitude.
		longitude (float): Current Iyr/global longitude.
		endpoint (str): Endpoint selector, either start or end.

	Returns:
		Dict[str, object]: Resolved endpoint label and coordinates.

	'''
	throw_if( 'key', key )
	throw_if( 'latitude', latitude )
	throw_if( 'longitude', longitude )
	throw_if( 'endpoint', endpoint )
	if key == 'Current Location':
		return { 'Label': 'Current Location', 'Latitude': float( latitude ),
			'Longitude': float( longitude ) }
	if key == 'Custom Point':
		if endpoint == 'start':
			return {
				'Label': 'Custom Start',
				'Latitude': float( st.session_state[ 'live_world_measurement_custom_start_latitude' ] ),
				'Longitude': float( st.session_state[ 'live_world_measurement_custom_start_longitude' ] ),
			}
		return {
			'Label': 'Custom End',
			'Latitude': float( st.session_state[ 'live_world_measurement_custom_end_latitude' ] ),
			'Longitude': float( st.session_state[ 'live_world_measurement_custom_end_longitude' ] ),
		}
	if not key.startswith( 'Entity::' ):
		raise ValueError( f'Unknown measurement endpoint: {key}' )
	_, entity_type, entity_id = key.split( '::', 2 )
	df_entities = st.session_state.get( 'live_world_df_entities', pd.DataFrame( ) )
	df_match = df_entities[
		(df_entities[ 'EntityType' ].astype( str ) == entity_type)
		& (df_entities[ 'EntityId' ].astype( str ) == entity_id) ].copy( )
	if df_match.empty:
		raise ValueError( f'Measurement entity is no longer available: {entity_id}' )
	row = df_match.iloc[ 0 ]
	return {
		'Label': f'{entity_type} | {row[ "Name" ]}',
		'Latitude': float( row[ 'Latitude' ] ),
		'Longitude': float( row[ 'Longitude' ] ),
	}

def calculate_live_world_measurement( latitude: float, longitude: float ) -> Dict[ str, object ]:
	'''

	Purpose:
		Calculate distance and initial bearing between the configured measurement endpoints.

	Args:
		latitude (float): Current Iyr/global latitude.
		longitude (float): Current Iyr/global longitude.

	Returns:
		Dict[str, object]: Resolved endpoints, distances, and initial bearing.

	'''
	start = resolve_live_world_measurement_point(
		str( st.session_state[ 'live_world_measurement_start' ] ), latitude, longitude, 'start' )
	end = resolve_live_world_measurement_point(
		str( st.session_state[ 'live_world_measurement_end' ] ), latitude, longitude, 'end' )
	distance_nm = calculate_live_world_distance_nm(
		float( start[ 'Latitude' ] ), float( start[ 'Longitude' ] ),
		float( end[ 'Latitude' ] ), float( end[ 'Longitude' ] ) )
	lat_a = math.radians( float( start[ 'Latitude' ] ) )
	lat_b = math.radians( float( end[ 'Latitude' ] ) )
	delta_lon = math.radians( float( end[ 'Longitude' ] ) - float( start[ 'Longitude' ] ) )
	y = math.sin( delta_lon ) * math.cos( lat_b )
	x = (math.cos( lat_a ) * math.sin( lat_b )
		- math.sin( lat_a ) * math.cos( lat_b ) * math.cos( delta_lon ))
	bearing = (math.degrees( math.atan2( y, x ) ) + 360.0) % 360.0
	return {
		'Start': start,
		'End': end,
		'DistanceNM': distance_nm,
		'DistanceKM': distance_nm * 1.852,
		'DistanceMiles': distance_nm * 1.150779448,
		'Bearing': bearing,
	}

def add_live_world_annotation( ) -> None:
	'''

	Purpose:
		Add one labeled annotation to the in-session Live World annotation collection.

	Returns:
		None

	'''
	initialize_live_world_state( )
	label = str( st.session_state.get( 'live_world_annotation_label', '' ) or '' ).strip( )
	throw_if( 'live_world_annotation_label', label )
	latitude = float( st.session_state[ 'live_world_annotation_latitude' ] )
	longitude = float( st.session_state[ 'live_world_annotation_longitude' ] )
	annotations = list( st.session_state.get( 'live_world_annotations', [ ] ) or [ ] )
	annotations.append( {
		'AnnotationId': f'ANNOTATION-{len( annotations ) + 1}',
		'Label': label,
		'Latitude': latitude,
		'Longitude': longitude,
		'CreatedAt': dt.datetime.now( dt.timezone.utc ).isoformat( ),
	} )
	st.session_state[ 'live_world_annotations' ] = annotations

def clear_live_world_annotations( ) -> None:
	'''

	Purpose:
		Clear all in-session Live World annotations.

	Returns:
		None

	'''
	initialize_live_world_state( )
	st.session_state[ 'live_world_annotations' ] = [ ]

def get_live_world_annotation_frame( ) -> pd.DataFrame:
	'''

	Purpose:
		Return current Live World annotations as a DataFrame.

	Returns:
		pd.DataFrame: Annotation records.

	'''
	initialize_live_world_state( )
	columns = [ 'AnnotationId', 'Label', 'Latitude', 'Longitude', 'CreatedAt' ]
	return pd.DataFrame( st.session_state.get( 'live_world_annotations', [ ] ) or [ ],
		columns=columns )

def get_live_world_analysis_origin_options( ) -> Dict[ str, str ]:
	'''

	Purpose:
		Return selectable Cross-Layer Analysis origins from current location and loaded entities.

	Returns:
		Dict[str, str]: Analysis origin keys mapped to display labels.

	'''
	initialize_live_world_state( )
	options: Dict[ str, str ] = {
		'Current Location': 'Current Location',
		'Custom Point': 'Custom Point',
	}
	df_entities = st.session_state.get( 'live_world_df_entities', pd.DataFrame( ) )
	if df_entities is None or df_entities.empty:
		return options
	for _, row in df_entities.iterrows( ):
		entity_id = str( row[ 'EntityId' ] )
		entity_type = str( row[ 'EntityType' ] )
		name = str( row[ 'Name' ] )
		key = f'Entity::{entity_type}::{entity_id}'
		options[ key ] = f'{entity_type} | {name} | {entity_id}'
	return options

def resolve_live_world_analysis_origin( key: str, latitude: float,
		longitude: float ) -> Dict[ str, object ]:
	'''

	Purpose:
		Resolve the configured Cross-Layer Analysis origin into coordinates and a label.

	Args:
		key (str): Selected analysis origin key.
		latitude (float): Current Iyr/global latitude.
		longitude (float): Current Iyr/global longitude.

	Returns:
		Dict[str, object]: Resolved analysis origin.

	'''
	throw_if( 'key', key )
	throw_if( 'latitude', latitude )
	throw_if( 'longitude', longitude )
	if key == 'Current Location':
		return { 'Label': 'Current Location', 'Latitude': float( latitude ),
			'Longitude': float( longitude ), 'EntityType': '', 'EntityId': '' }
	if key == 'Custom Point':
		return {
			'Label': 'Custom Point',
			'Latitude': float( st.session_state[ 'live_world_analysis_custom_latitude' ] ),
			'Longitude': float( st.session_state[ 'live_world_analysis_custom_longitude' ] ),
			'EntityType': '',
			'EntityId': '',
		}
	if not key.startswith( 'Entity::' ):
		raise ValueError( f'Unknown analysis origin: {key}' )
	_, entity_type, entity_id = key.split( '::', 2 )
	df_entities = st.session_state.get( 'live_world_df_entities', pd.DataFrame( ) )
	df_match = df_entities[
		(df_entities[ 'EntityType' ].astype( str ) == entity_type)
		& (df_entities[ 'EntityId' ].astype( str ) == entity_id) ].copy( )
	if df_match.empty:
		raise ValueError( f'Analysis origin entity is no longer available: {entity_id}' )
	row = df_match.iloc[ 0 ]
	return {
		'Label': f'{entity_type} | {row[ "Name" ]}',
		'Latitude': float( row[ 'Latitude' ] ),
		'Longitude': float( row[ 'Longitude' ] ),
		'EntityType': entity_type,
		'EntityId': entity_id,
	}

def calculate_live_world_cross_layer_analysis( latitude: float,
		longitude: float ) -> pd.DataFrame:
	'''

	Purpose:
		Rank loaded Live World entities by distance from the configured analysis origin.

	Args:
		latitude (float): Current Iyr/global latitude.
		longitude (float): Current Iyr/global longitude.

	Returns:
		pd.DataFrame: Radius-filtered entities ordered by nearest distance.

	'''
	initialize_live_world_state( )
	throw_if( 'latitude', latitude )
	throw_if( 'longitude', longitude )
	columns = [ 'EntityId', 'EntityType', 'Name', 'Latitude', 'Longitude', 'Altitude',
		'Heading', 'Speed', 'Timestamp', 'Source', 'Metadata', 'DistanceNM',
		'DistanceKM', 'DistanceMiles', 'Bearing' ]
	df_entities = st.session_state.get( 'live_world_df_entities', pd.DataFrame( ) )
	if df_entities is None or df_entities.empty:
		return pd.DataFrame( columns=columns )
	entity_types = list( st.session_state.get( 'live_world_analysis_entity_types', [ ] ) or [ ] )
	if not entity_types:
		return pd.DataFrame( columns=columns )
	origin = resolve_live_world_analysis_origin(
		str( st.session_state[ 'live_world_analysis_origin' ] ), latitude, longitude )
	df_analysis = df_entities[ df_entities[ 'EntityType' ].isin( entity_types ) ].copy( )
	if df_analysis.empty:
		return pd.DataFrame( columns=columns )
	df_analysis[ 'Latitude' ] = pd.to_numeric( df_analysis[ 'Latitude' ], errors='coerce' )
	df_analysis[ 'Longitude' ] = pd.to_numeric( df_analysis[ 'Longitude' ], errors='coerce' )
	df_analysis = df_analysis.dropna( subset=[ 'Latitude', 'Longitude' ] )
	rows: List[ Dict[ str, object ] ] = [ ]
	for _, row in df_analysis.iterrows( ):
		if (str( origin[ 'EntityType' ] ) == str( row[ 'EntityType' ] )
				and str( origin[ 'EntityId' ] ) == str( row[ 'EntityId' ] )
				and str( origin[ 'EntityId' ] )):
			continue
		distance_nm = calculate_live_world_distance_nm(
			float( origin[ 'Latitude' ] ), float( origin[ 'Longitude' ] ),
			float( row[ 'Latitude' ] ), float( row[ 'Longitude' ] ) )
		if distance_nm > float( st.session_state[ 'live_world_analysis_radius_nm' ] ):
			continue
		lat_a = math.radians( float( origin[ 'Latitude' ] ) )
		lat_b = math.radians( float( row[ 'Latitude' ] ) )
		delta_lon = math.radians( float( row[ 'Longitude' ] ) - float( origin[ 'Longitude' ] ) )
		y = math.sin( delta_lon ) * math.cos( lat_b )
		x = (math.cos( lat_a ) * math.sin( lat_b )
			- math.sin( lat_a ) * math.cos( lat_b ) * math.cos( delta_lon ))
		bearing = (math.degrees( math.atan2( y, x ) ) + 360.0) % 360.0
		result = row.to_dict( )
		result[ 'DistanceNM' ] = distance_nm
		result[ 'DistanceKM' ] = distance_nm * 1.852
		result[ 'DistanceMiles' ] = distance_nm * 1.150779448
		result[ 'Bearing' ] = bearing
		rows.append( result )
	if not rows:
		return pd.DataFrame( columns=columns )
	df_result = pd.DataFrame( rows )
	df_result = df_result.sort_values( by='DistanceNM', ascending=True, kind='stable' )
	limit = int( st.session_state[ 'live_world_analysis_limit' ] )
	return df_result.head( limit ).reset_index( drop=True )

def get_live_world_geofence_origin_options( ) -> Dict[ str, str ]:
	'''

	Purpose:
		Return selectable Geofencing origins from current location and loaded entities.

	Returns:
		Dict[str, str]: Geofence origin keys mapped to display labels.

	'''
	initialize_live_world_state( )
	options: Dict[ str, str ] = {
		'Current Location': 'Current Location',
		'Custom Point': 'Custom Point',
	}
	df_entities = st.session_state.get( 'live_world_df_entities', pd.DataFrame( ) )
	if df_entities is None or df_entities.empty:
		return options
	for _, row in df_entities.iterrows( ):
		entity_id = str( row[ 'EntityId' ] )
		entity_type = str( row[ 'EntityType' ] )
		name = str( row[ 'Name' ] )
		key = f'Entity::{entity_type}::{entity_id}'
		options[ key ] = f'{entity_type} | {name} | {entity_id}'
	return options

def resolve_live_world_geofence_origin( key: str, latitude: float,
		longitude: float ) -> Dict[ str, object ]:
	'''

	Purpose:
		Resolve the configured Geofencing origin into coordinates and a display label.

	Args:
		key (str): Selected geofence origin key.
		latitude (float): Current Iyr/global latitude.
		longitude (float): Current Iyr/global longitude.

	Returns:
		Dict[str, object]: Resolved geofence origin.

	'''
	throw_if( 'key', key )
	throw_if( 'latitude', latitude )
	throw_if( 'longitude', longitude )
	if key == 'Current Location':
		return { 'Label': 'Current Location', 'Latitude': float( latitude ),
			'Longitude': float( longitude ), 'EntityType': '', 'EntityId': '' }
	if key == 'Custom Point':
		return {
			'Label': 'Custom Point',
			'Latitude': float( st.session_state[ 'live_world_geofence_custom_latitude' ] ),
			'Longitude': float( st.session_state[ 'live_world_geofence_custom_longitude' ] ),
			'EntityType': '',
			'EntityId': '',
		}
	if not key.startswith( 'Entity::' ):
		raise ValueError( f'Unknown geofence origin: {key}' )
	_, entity_type, entity_id = key.split( '::', 2 )
	df_entities = st.session_state.get( 'live_world_df_entities', pd.DataFrame( ) )
	df_match = df_entities[
		(df_entities[ 'EntityType' ].astype( str ) == entity_type)
		& (df_entities[ 'EntityId' ].astype( str ) == entity_id) ].copy( )
	if df_match.empty:
		raise ValueError( f'Geofence origin entity is no longer available: {entity_id}' )
	row = df_match.iloc[ 0 ]
	return {
		'Label': f'{entity_type} | {row[ "Name" ]}',
		'Latitude': float( row[ 'Latitude' ] ),
		'Longitude': float( row[ 'Longitude' ] ),
		'EntityType': entity_type,
		'EntityId': entity_id,
	}

def calculate_live_world_geofence( latitude: float, longitude: float ) -> pd.DataFrame:
	'''

	Purpose:
		Return loaded Live World entities currently inside the configured circular geofence.

	Args:
		latitude (float): Current Iyr/global latitude.
		longitude (float): Current Iyr/global longitude.

	Returns:
		pd.DataFrame: Geofence members ordered by nearest distance.

	'''
	initialize_live_world_state( )
	throw_if( 'latitude', latitude )
	throw_if( 'longitude', longitude )
	columns = [ 'EntityId', 'EntityType', 'Name', 'Latitude', 'Longitude', 'Altitude',
		'Heading', 'Speed', 'Timestamp', 'Source', 'Metadata', 'DistanceNM',
		'DistanceKM', 'DistanceMiles', 'Bearing' ]
	df_entities = st.session_state.get( 'live_world_df_entities', pd.DataFrame( ) )
	if df_entities is None or df_entities.empty:
		return pd.DataFrame( columns=columns )
	entity_types = list( st.session_state.get( 'live_world_geofence_entity_types', [ ] ) or [ ] )
	if not entity_types:
		return pd.DataFrame( columns=columns )
	origin = resolve_live_world_geofence_origin(
		str( st.session_state[ 'live_world_geofence_origin' ] ), latitude, longitude )
	df_geofence = df_entities[ df_entities[ 'EntityType' ].isin( entity_types ) ].copy( )
	df_geofence[ 'Latitude' ] = pd.to_numeric( df_geofence[ 'Latitude' ], errors='coerce' )
	df_geofence[ 'Longitude' ] = pd.to_numeric( df_geofence[ 'Longitude' ], errors='coerce' )
	df_geofence = df_geofence.dropna( subset=[ 'Latitude', 'Longitude' ] )
	rows: List[ Dict[ str, object ] ] = [ ]
	for _, row in df_geofence.iterrows( ):
		if (str( origin[ 'EntityType' ] ) == str( row[ 'EntityType' ] )
				and str( origin[ 'EntityId' ] ) == str( row[ 'EntityId' ] )
				and str( origin[ 'EntityId' ] )):
			continue
		distance_nm = calculate_live_world_distance_nm(
			float( origin[ 'Latitude' ] ), float( origin[ 'Longitude' ] ),
			float( row[ 'Latitude' ] ), float( row[ 'Longitude' ] ) )
		if distance_nm > float( st.session_state[ 'live_world_geofence_radius_nm' ] ):
			continue
		lat_a = math.radians( float( origin[ 'Latitude' ] ) )
		lat_b = math.radians( float( row[ 'Latitude' ] ) )
		delta_lon = math.radians( float( row[ 'Longitude' ] ) - float( origin[ 'Longitude' ] ) )
		y = math.sin( delta_lon ) * math.cos( lat_b )
		x = (math.cos( lat_a ) * math.sin( lat_b )
			- math.sin( lat_a ) * math.cos( lat_b ) * math.cos( delta_lon ))
		bearing = (math.degrees( math.atan2( y, x ) ) + 360.0) % 360.0
		result = row.to_dict( )
		result[ 'DistanceNM' ] = distance_nm
		result[ 'DistanceKM' ] = distance_nm * 1.852
		result[ 'DistanceMiles' ] = distance_nm * 1.150779448
		result[ 'Bearing' ] = bearing
		rows.append( result )
	if not rows:
		return pd.DataFrame( columns=columns )
	return pd.DataFrame( rows ).sort_values(
		by='DistanceNM', ascending=True, kind='stable' ).reset_index( drop=True )

def update_live_world_geofence_events( df_geofence: pd.DataFrame ) -> None:
	'''

	Purpose:
		Record entity entry and exit transitions for the configured geofence after refreshes.

	Args:
		df_geofence (pd.DataFrame): Current entities inside the configured geofence.

	Returns:
		None

	'''
	initialize_live_world_state( )
	throw_if( 'df_geofence', df_geofence )
	current_snapshot: Dict[ str, Dict[ str, object ] ] = { }
	for _, row in df_geofence.iterrows( ):
		key = f'{row[ "EntityType" ]}::{row[ "EntityId" ]}'
		current_snapshot[ key ] = {
			'EntityId': str( row[ 'EntityId' ] ),
			'EntityType': str( row[ 'EntityType' ] ),
			'Name': str( row[ 'Name' ] ),
			'Latitude': float( row[ 'Latitude' ] ),
			'Longitude': float( row[ 'Longitude' ] ),
			'DistanceNM': float( row[ 'DistanceNM' ] ),
			'Source': str( row[ 'Source' ] ),
		}
	previous_snapshot = dict( st.session_state.get( 'live_world_geofence_snapshot', { } ) or { } )
	if not st.session_state[ 'live_world_geofence_initialized' ]:
		st.session_state[ 'live_world_geofence_snapshot' ] = current_snapshot
		st.session_state[ 'live_world_geofence_initialized' ] = True
		return
	entered = sorted( set( current_snapshot ) - set( previous_snapshot ) )
	exited = sorted( set( previous_snapshot ) - set( current_snapshot ) )
	events = list( st.session_state.get( 'live_world_geofence_events', [ ] ) or [ ] )
	observed_at = dt.datetime.now( dt.timezone.utc ).isoformat( )
	for key in entered:
		item = current_snapshot[ key ]
		events.append( {
			'Event': 'Entered', 'EntityId': item[ 'EntityId' ],
			'EntityType': item[ 'EntityType' ], 'Name': item[ 'Name' ],
			'Latitude': item[ 'Latitude' ], 'Longitude': item[ 'Longitude' ],
			'DistanceNM': item[ 'DistanceNM' ], 'Source': item[ 'Source' ],
			'ObservedAt': observed_at,
		} )
	for key in exited:
		item = previous_snapshot[ key ]
		events.append( {
			'Event': 'Exited', 'EntityId': item[ 'EntityId' ],
			'EntityType': item[ 'EntityType' ], 'Name': item[ 'Name' ],
			'Latitude': item[ 'Latitude' ], 'Longitude': item[ 'Longitude' ],
			'DistanceNM': item[ 'DistanceNM' ], 'Source': item[ 'Source' ],
			'ObservedAt': observed_at,
		} )
	limit = int( st.session_state[ 'live_world_geofence_event_limit' ] )
	st.session_state[ 'live_world_geofence_events' ] = events[ -limit: ]
	st.session_state[ 'live_world_geofence_snapshot' ] = current_snapshot

def clear_live_world_geofence_events( ) -> None:
	'''

	Purpose:
		Clear Geofencing event history and reset the transition baseline.

	Returns:
		None

	'''
	initialize_live_world_state( )
	st.session_state[ 'live_world_geofence_events' ] = [ ]
	st.session_state[ 'live_world_geofence_snapshot' ] = { }
	st.session_state[ 'live_world_geofence_initialized' ] = False
	st.session_state[ 'live_world_geofence_last_refresh_processed' ] = ''

def get_live_world_geofence_event_frame( ) -> pd.DataFrame:
	'''

	Purpose:
		Return current Geofencing transition events as a DataFrame.

	Returns:
		pd.DataFrame: Ordered Geofencing event history.

	'''
	initialize_live_world_state( )
	columns = [ 'Event', 'EntityId', 'EntityType', 'Name', 'Latitude', 'Longitude',
		'DistanceNM', 'Source', 'ObservedAt' ]
	return pd.DataFrame( st.session_state.get( 'live_world_geofence_events', [ ] ) or [ ],
		columns=columns )

def get_live_world_history_window_hours( window: str ) -> int:
	'''

	Purpose:
		Translate the Historical Replay window label into a lookback duration in hours.

	Args:
		window (str): Historical Replay window label.

	Returns:
		int: Lookback duration in hours; zero means all retained history.

	'''
	throw_if( 'window', window )
	windows: Dict[ str, int ] = {
		'1 Hour': 1,
		'6 Hours': 6,
		'24 Hours': 24,
		'7 Days': 168,
		'30 Days': 720,
		'All Retained': 0,
	}
	if window not in windows:
		raise ValueError( f'Unsupported Historical Replay window: {window}' )
	return windows[ window ]

def load_live_world_replay_frame( ) -> pd.DataFrame:
	'''

	Purpose:
		Load Historical Replay observations using the current sidebar configuration.

	Returns:
		pd.DataFrame: Persisted observations through the selected replay snapshot.

	'''
	initialize_live_world_state( )
	snapshot = str( st.session_state.get( 'live_world_history_snapshot', '' ) or '' )
	if not snapshot:
		return pd.DataFrame( )
	entity_types = list( st.session_state.get( 'live_world_history_entity_types', [ ] ) or [ ] )
	if not entity_types:
		return pd.DataFrame( )
	hours = get_live_world_history_window_hours(
		str( st.session_state[ 'live_world_history_window' ] ) )
	return load_live_world_history( hours, entity_types, snapshot,
		int( st.session_state[ 'live_world_history_limit' ] ) )

def clear_live_world_tracking( ) -> None:
	'''

	Purpose:
		Clear the current tracking trail without changing the selected tracked entity.

	Returns:
		None

	'''
	initialize_live_world_state( )
	st.session_state[ 'live_world_tracking_history' ] = [ ]
	st.session_state[ 'live_world_tracking_active_entity' ] = ''

def update_live_world_tracking( df_entities: pd.DataFrame ) -> None:
	'''

	Purpose:
		Append the selected moving entity's newest position to its in-session trail.

	Args:
		df_entities (pd.DataFrame): Current normalized Live World entity records.

	Returns:
		None

	'''
	initialize_live_world_state( )
	throw_if( 'df_entities', df_entities )
	if not st.session_state[ 'live_world_tracking' ]:
		return

	tracking_key = str( st.session_state.get( 'live_world_tracking_entity', '' ) or '' )
	if not tracking_key or '::' not in tracking_key or df_entities.empty:
		return

	entity_type, entity_id = tracking_key.split( '::', 1 )
	df_match = df_entities[
		(df_entities[ 'EntityType' ].astype( str ) == entity_type)
		& (df_entities[ 'EntityId' ].astype( str ) == entity_id) ].copy( )
	if df_match.empty:
		return

	active_entity = str( st.session_state.get(
		'live_world_tracking_active_entity', '' ) or '' )
	if active_entity != tracking_key:
		st.session_state[ 'live_world_tracking_history' ] = [ ]
		st.session_state[ 'live_world_tracking_active_entity' ] = tracking_key

	row = df_match.iloc[ 0 ]
	point = {
		'EntityKey': tracking_key,
		'EntityId': str( row[ 'EntityId' ] ),
		'EntityType': str( row[ 'EntityType' ] ),
		'Name': str( row[ 'Name' ] ),
		'Latitude': float( row[ 'Latitude' ] ),
		'Longitude': float( row[ 'Longitude' ] ),
		'Altitude': float( row[ 'Altitude' ] ),
		'Heading': float( row[ 'Heading' ] ),
		'Speed': float( row[ 'Speed' ] ),
		'Timestamp': str( row[ 'Timestamp' ] ),
		'ObservedAt': dt.datetime.now( dt.timezone.utc ).isoformat( ),
	}

	history = list( st.session_state.get( 'live_world_tracking_history', [ ] ) or [ ] )
	if history:
		previous = history[ -1 ]
		if (float( previous[ 'Latitude' ] ) == point[ 'Latitude' ]
				and float( previous[ 'Longitude' ] ) == point[ 'Longitude' ]):
			return

	history.append( point )
	max_points = int( st.session_state[ 'live_world_tracking_max_points' ] )
	st.session_state[ 'live_world_tracking_history' ] = history[ -max_points: ]

def get_live_world_tracking_frame( ) -> pd.DataFrame:
	'''

	Purpose:
		Return the current tracking trail as a DataFrame for rendering and inspection.

	Returns:
		pd.DataFrame: Ordered tracking trail points.

	'''
	initialize_live_world_state( )
	history = list( st.session_state.get( 'live_world_tracking_history', [ ] ) or [ ] )
	columns = [ 'EntityKey', 'EntityId', 'EntityType', 'Name', 'Latitude', 'Longitude',
		'Altitude', 'Heading', 'Speed', 'Timestamp', 'ObservedAt' ]
	return pd.DataFrame( history, columns=columns )

def update_live_world_source_state( source_key: str, status: str, error: str='',
		stale: bool=False, attempted_at: str='', successful_at: str='' ) -> None:
	'''

	Purpose:
		Update the operational state for one Live World provider without changing any
		other provider state.

	Args:
		source_key (str): Live World source identifier.
		status (str): Current source status.
		error (str): Current source error text.
		stale (bool): Whether retained source data predates the current refresh attempt.
		attempted_at (str): UTC timestamp for the most recent refresh attempt.
		successful_at (str): UTC timestamp for the most recent successful refresh.

	Returns:
		None

	'''
	initialize_live_world_state( )
	throw_if( 'source_key', source_key )
	throw_if( 'status', status )
	if source_key not in LIVE_WORLD_DATA_SOURCES:
		raise ValueError( f'Unsupported Live World source: {source_key}' )

	statuses = dict( st.session_state[ 'live_world_source_status' ] )
	errors = dict( st.session_state[ 'live_world_source_errors' ] )
	last_attempt = dict( st.session_state[ 'live_world_source_last_attempt' ] )
	last_success = dict( st.session_state[ 'live_world_source_last_success' ] )
	stale_state = dict( st.session_state[ 'live_world_source_stale' ] )
	statuses[ source_key ] = status
	errors[ source_key ] = error
	stale_state[ source_key ] = stale
	if attempted_at:
		last_attempt[ source_key ] = attempted_at
	if successful_at:
		last_success[ source_key ] = successful_at
	st.session_state[ 'live_world_source_status' ] = statuses
	st.session_state[ 'live_world_source_errors' ] = errors
	st.session_state[ 'live_world_source_last_attempt' ] = last_attempt
	st.session_state[ 'live_world_source_last_success' ] = last_success
	st.session_state[ 'live_world_source_stale' ] = stale_state

def refresh_live_world_source( source_key: str,
		fetcher: Callable[ [ ], pd.DataFrame ] ) -> pd.DataFrame:
	'''

	Purpose:
		Refresh one enabled Live World provider while isolating provider failures from
		the remaining refresh cycle.

	Args:
		source_key (str): Live World source identifier.
		fetcher (Callable[[], pd.DataFrame]): Source-specific fetch operation.

	Returns:
		pd.DataFrame: Current source frame, including retained stale data after a failure.

	'''
	initialize_live_world_state( )
	throw_if( 'source_key', source_key )
	throw_if( 'fetcher', fetcher )
	if source_key not in LIVE_WORLD_DATA_SOURCES:
		raise ValueError( f'Unsupported Live World source: {source_key}' )

	source = LIVE_WORLD_DATA_SOURCES[ source_key ]
	frame_key = source[ 'frame_key' ]
	previous_frame = st.session_state.get( frame_key, pd.DataFrame( ) )
	if previous_frame is None or not isinstance( previous_frame, pd.DataFrame ):
		previous_frame = pd.DataFrame( )
	attempted_at = dt.datetime.now( dt.timezone.utc ).isoformat( )
	update_live_world_source_state(
		source_key, 'Refreshing', attempted_at=attempted_at )

	try:
		df_source = fetcher( )
		if df_source is None:
			df_source = entities_to_dataframe( [ ] )
		if not isinstance( df_source, pd.DataFrame ):
			raise TypeError(
				f'Live World source {source_key} must return a pandas DataFrame.' )
		st.session_state[ frame_key ] = df_source
		update_live_world_source_state(
			source_key, 'Success', attempted_at=attempted_at,
			successful_at=dt.datetime.now( dt.timezone.utc ).isoformat( ) )
		return df_source

	except Exception as ex:
		has_stale_data = not previous_frame.empty
		st.session_state[ frame_key ] = previous_frame
		update_live_world_source_state(
			source_key, 'Failed', error=str( ex ), stale=has_stale_data,
			attempted_at=attempted_at )
		return previous_frame

def refresh_live_world_data( latitude: float, longitude: float ) -> pd.DataFrame:
	'''

	Purpose:
		Refresh every enabled implemented Live World layer independently and persist the
		combined frame only when all enabled providers complete successfully.

	Args:
		latitude (float): Current Iyr/global latitude.
		longitude (float): Current Iyr/global longitude.

	Returns:
		pd.DataFrame: Combined normalized entity data.

	'''
	initialize_live_world_state( )
	throw_if( 'latitude', latitude )
	throw_if( 'longitude', longitude )
	st.session_state[ 'live_world_last_error' ] = ''

	fetchers: Dict[ str, Callable[ [ ], pd.DataFrame ] ] = {
		'aircraft': lambda: fetch_live_aircraft( latitude, longitude ),
		'military_aircraft': lambda: fetch_live_military_aircraft( latitude, longitude ),
		'satellites': lambda: fetch_live_satellites( ),
		'vessels': lambda: fetch_live_vessels( latitude, longitude ),
		'earthquakes': lambda: fetch_live_earthquakes( ),
		'fires': lambda: fetch_live_fires( latitude, longitude ),
		'infrastructure': lambda: fetch_live_infrastructure( latitude, longitude ),
		'cameras': lambda: fetch_live_cameras( latitude, longitude ),
		'map_layers': lambda: fetch_live_map_layers( latitude, longitude ),
	}

	try:
		frames: List[ pd.DataFrame ] = [ ]
		for source_key, source in LIVE_WORLD_DATA_SOURCES.items( ):
			frame_key = source[ 'frame_key' ]
			enabled_key = source[ 'enabled_key' ]
			if st.session_state[ enabled_key ]:
				df_source = refresh_live_world_source(
					source_key, fetchers[ source_key ] )
				if not df_source.empty:
					frames.append( df_source )
			else:
				st.session_state[ frame_key ] = pd.DataFrame( )
				update_live_world_source_state(
					source_key, 'Disabled', error='', stale=False )

		df_entities = pd.concat( frames,
			ignore_index=True ) if frames else entities_to_dataframe( [ ] )
		st.session_state[ 'live_world_df_entities' ] = df_entities
		update_live_world_tracking( df_entities )
		observed_at = dt.datetime.now( dt.timezone.utc ).isoformat( )
		st.session_state[ 'live_world_last_refresh' ] = dt.datetime.now( ).strftime(
			'%Y-%m-%d %H:%M:%S' )

		statuses = dict( st.session_state[ 'live_world_source_status' ] )
		errors = dict( st.session_state[ 'live_world_source_errors' ] )
		failures: List[ str ] = [ ]
		for source_key, status in statuses.items( ):
			if status != 'Failed':
				continue
			label = LIVE_WORLD_DATA_SOURCES[ source_key ][ 'label' ]
			failures.append( f'{label}: {errors.get( source_key, "" )}' )
		st.session_state[ 'live_world_last_error' ] = '; '.join( failures )

		if (st.session_state[ 'live_world_historical_replay' ]
				and st.session_state[ 'live_world_history_persist' ] and not failures):
			try:
				st.session_state[ 'live_world_history_last_saved' ] = persist_live_world_history(
					df_entities, observed_at, observed_at,
					int( st.session_state[ 'live_world_history_max_rows_per_source' ] ) )
				purge_live_world_history(
					int( st.session_state[ 'live_world_history_retention_days' ] ) )
				st.session_state[ 'live_world_history_last_error' ] = ''
			except Exception as history_ex:
				st.session_state[ 'live_world_history_last_saved' ] = 0
				st.session_state[ 'live_world_history_last_error' ] = str( history_ex )
		elif failures:
			st.session_state[ 'live_world_history_last_saved' ] = 0

		return df_entities

	finally:
		st.session_state[ 'live_world_refresh_requested' ] = False

def render_live_world_map( latitude: float, longitude: float ) -> None:
	'''

	Purpose:
		Render normalized Live World entities on an operational PyDeck map with metrics,
		map controls, source tooltips, and source-data tabs.

	Args:
		latitude (float): Current Iyr/global latitude used for initial map centering.
		longitude (float): Current Iyr/global longitude used for initial map centering.

	Returns:
		None

	'''
	initialize_live_world_state( )
	throw_if( 'latitude', latitude )
	throw_if( 'longitude', longitude )
	if not st.session_state[ 'live_world_enabled' ]:
		return

	st.divider( )
	st.subheader( '🌐 Live World Data' )
	if not any( get_live_world_layers( ).values( ) ):
		st.info( 'Select at least one implemented Live World layer in the sidebar.' )
		return

	if st.session_state[ 'live_world_refresh_requested' ]:
		try:
			with st.spinner( 'Refreshing Live World Data...' ):
				refresh_live_world_data( latitude, longitude )
		except Exception as ex:
			st.error( f'Live World refresh failed before provider isolation completed: {ex}' )

	source_status = dict( st.session_state[ 'live_world_source_status' ] )
	source_errors = dict( st.session_state[ 'live_world_source_errors' ] )
	source_stale = dict( st.session_state[ 'live_world_source_stale' ] )
	for source_key, status in source_status.items( ):
		if status != 'Failed':
			continue
		label = LIVE_WORLD_DATA_SOURCES[ source_key ][ 'label' ]
		error = source_errors.get( source_key, '' ) or 'Unknown provider error.'
		message = f'{label} refresh failed: {error}'
		if source_stale.get( source_key, False ):
			message += ' Showing data from the previous successful refresh.'
		st.error( message )
	if (source_status.get( 'fires', '' ) == 'Success'
			and st.session_state.get( 'live_world_firms_truncated', False )):
		loaded_count = len( st.session_state.get( 'live_world_df_fires', pd.DataFrame( ) ).index )
		source_count = int( st.session_state.get( 'live_world_firms_source_count', loaded_count ) )
		st.warning(
			f'Fires: displaying {loaded_count:,} of {source_count:,} FIRMS records for this refresh.' )

	df_entities = st.session_state.get( 'live_world_df_entities', pd.DataFrame( ) )
	if df_entities is None or df_entities.empty:
		if not st.session_state[ 'live_world_measurements' ]:
			st.info( 'No Live World data has been loaded. Select Refresh in the sidebar.' )
			return
		df_entities = entities_to_dataframe( [ ] )

	df_map = df_entities.copy( )
	df_map[ 'MetadataText' ] = df_map[ 'Metadata' ].map(
		lambda value: json.dumps( value, default=str ) if isinstance( value, dict ) else str( value ) )
	df_map[ 'Latitude' ] = pd.to_numeric( df_map[ 'Latitude' ], errors='coerce' )
	df_map[ 'Longitude' ] = pd.to_numeric( df_map[ 'Longitude' ], errors='coerce' )
	df_map = df_map.dropna( subset=[ 'Latitude', 'Longitude' ] )
	if (df_map.empty and not st.session_state[ 'live_world_measurements' ]
			and not st.session_state[ 'live_world_historical_replay' ]):
		st.info( 'Live World data does not contain usable map coordinates.' )
		return

	last_refresh = str( st.session_state.get( 'live_world_last_refresh', '' ) or 'Not refreshed' )
	metric_c1, metric_c2, metric_c3, metric_c4, metric_c5 = st.columns( 5, border=True )
	metric_c1.metric( 'Entities', f'{len( df_map ):,}' )
	metric_c2.metric( 'Aircraft',
		f'{int( (df_map[ "EntityType" ] == "Aircraft").sum( ) ):,}' )
	metric_c3.metric( 'Military',
		f'{int( (df_map[ "EntityType" ] == "Military Aircraft").sum( ) ):,}' )
	metric_c4.metric( 'Satellites',
		f'{int( (df_map[ "EntityType" ] == "Satellite").sum( ) ):,}' )
	metric_c5.metric( 'Vessels',
		f'{int( (df_map[ "EntityType" ] == "Vessel").sum( ) ):,}' )
	event_c1, event_c2, event_c3, event_c4, event_c5 = st.columns( 5, border=True )
	event_c1.metric( 'Earthquakes',
		f'{int( (df_map[ "EntityType" ] == "Earthquake").sum( ) ):,}' )
	event_c2.metric( 'Fires', f'{int( (df_map[ "EntityType" ] == "Fire").sum( ) ):,}' )
	event_c3.metric( 'Infrastructure',
		f'{int( (df_map[ "EntityType" ] == "Infrastructure").sum( ) ):,}' )
	event_c4.metric( 'Cameras', f'{int( (df_map[ "EntityType" ] == "Camera").sum( ) ):,}' )
	event_c5.metric( 'Map Features', f'{int( (df_map[ "EntityType" ] == "Map Feature").sum( ) ):,}' )
	st.caption( f'Last refresh: {last_refresh}' )

	map_style_options = {
		'Carto Dark Matter': 'https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json',
		'Carto Positron': 'https://basemaps.cartocdn.com/gl/positron-gl-style/style.json',
		'Carto Voyager': 'https://basemaps.cartocdn.com/gl/voyager-gl-style/style.json',
		'Dark': 'dark',
		'Light': 'light',
		'Road': 'road',
		'Satellite': 'satellite',
	}
	control_c1, control_c2, control_c3 = st.columns( 3, border=True )
	with control_c1:
		st.selectbox( 'Map Style', options=list( map_style_options.keys( ) ),
			key='live_world_map_style' )
	with control_c2:
		st.slider( 'Zoom', min_value=0, max_value=18, key='live_world_zoom' )
	with control_c3:
		st.slider( 'Point Scale', min_value=0.5, max_value=3.0, step=0.25,
			key='live_world_point_scale' )

	layers: List[ pdk.Layer ] = [ ]
	point_scale = float( st.session_state[ 'live_world_point_scale' ] )
	df_aircraft = df_map[ df_map[ 'EntityType' ] == 'Aircraft' ].copy( )
	df_military = df_map[ df_map[ 'EntityType' ] == 'Military Aircraft' ].copy( )
	df_satellites = df_map[ df_map[ 'EntityType' ] == 'Satellite' ].copy( )
	df_vessels = df_map[ df_map[ 'EntityType' ] == 'Vessel' ].copy( )
	df_earthquakes = df_map[ df_map[ 'EntityType' ] == 'Earthquake' ].copy( )
	df_fires = df_map[ df_map[ 'EntityType' ] == 'Fire' ].copy( )
	df_infrastructure = df_map[ df_map[ 'EntityType' ] == 'Infrastructure' ].copy( )
	df_cameras = df_map[ df_map[ 'EntityType' ] == 'Camera' ].copy( )
	df_map_layers = df_map[ df_map[ 'EntityType' ] == 'Map Feature' ].copy( )

	df_analysis = pd.DataFrame( )
	analysis_origin: Dict[ str, object ] = { }
	analysis_error = ''
	if st.session_state[ 'live_world_cross_layer_analysis' ]:
		try:
			analysis_origin = resolve_live_world_analysis_origin(
				str( st.session_state[ 'live_world_analysis_origin' ] ), latitude, longitude )
			df_analysis = calculate_live_world_cross_layer_analysis( latitude, longitude )
			df_analysis_origin = pd.DataFrame( [ analysis_origin ] )
			df_analysis_origin[ 'Radius' ] = float(
				st.session_state[ 'live_world_analysis_radius_nm' ] ) * 1852.0
			layers.append( pdk.Layer( 'ScatterplotLayer', data=df_analysis_origin,
				get_position='[Longitude, Latitude]', get_radius='Radius',
				get_fill_color=[ 80, 180, 255, 20 ], get_line_color=[ 80, 180, 255, 180 ],
				line_width_min_pixels=2, radius_min_pixels=1,
				filled=True, stroked=True, pickable=False ) )
			df_analysis_origin[ 'Radius' ] = 12000.0 * point_scale
			layers.append( pdk.Layer( 'ScatterplotLayer', data=df_analysis_origin,
				get_position='[Longitude, Latitude]', get_radius='Radius',
				get_fill_color=[ 80, 180, 255, 180 ], get_line_color=[ 255, 255, 255, 255 ],
				line_width_min_pixels=2, radius_min_pixels=8, radius_max_pixels=30,
				filled=True, stroked=True, pickable=False ) )
			if not df_analysis.empty:
				df_analysis_points = df_analysis.copy( )
				df_analysis_points[ 'Radius' ] = 11000.0 * point_scale
				layers.append( pdk.Layer( 'ScatterplotLayer', data=df_analysis_points,
					get_position='[Longitude, Latitude]', get_radius='Radius',
					get_fill_color=[ 255, 255, 255, 35 ], get_line_color=[ 80, 180, 255, 255 ],
					line_width_min_pixels=2, radius_min_pixels=7, radius_max_pixels=28,
					filled=True, stroked=True, pickable=True ) )
		except Exception as ex:
			analysis_error = str( ex )

	df_geofence = pd.DataFrame( )
	geofence_origin: Dict[ str, object ] = { }
	geofence_error = ''
	if st.session_state[ 'live_world_geofencing' ]:
		try:
			geofence_origin = resolve_live_world_geofence_origin(
				str( st.session_state[ 'live_world_geofence_origin' ] ), latitude, longitude )
			df_geofence = calculate_live_world_geofence( latitude, longitude )
			df_geofence_origin = pd.DataFrame( [ geofence_origin ] )
			df_geofence_origin[ 'Radius' ] = float(
				st.session_state[ 'live_world_geofence_radius_nm' ] ) * 1852.0
			layers.append( pdk.Layer( 'ScatterplotLayer', data=df_geofence_origin,
				get_position='[Longitude, Latitude]', get_radius='Radius',
				get_fill_color=[ 255, 80, 80, 15 ], get_line_color=[ 255, 80, 80, 190 ],
				line_width_min_pixels=2, radius_min_pixels=1,
				filled=True, stroked=True, pickable=False ) )
			df_geofence_origin[ 'Radius' ] = 12000.0 * point_scale
			layers.append( pdk.Layer( 'ScatterplotLayer', data=df_geofence_origin,
				get_position='[Longitude, Latitude]', get_radius='Radius',
				get_fill_color=[ 255, 80, 80, 180 ], get_line_color=[ 255, 255, 255, 255 ],
				line_width_min_pixels=2, radius_min_pixels=8, radius_max_pixels=30,
				filled=True, stroked=True, pickable=False ) )
			if not df_geofence.empty:
				df_geofence_points = df_geofence.copy( )
				df_geofence_points[ 'Radius' ] = 11000.0 * point_scale
				layers.append( pdk.Layer( 'ScatterplotLayer', data=df_geofence_points,
					get_position='[Longitude, Latitude]', get_radius='Radius',
					get_fill_color=[ 255, 80, 80, 45 ], get_line_color=[ 255, 80, 80, 255 ],
					line_width_min_pixels=2, radius_min_pixels=7, radius_max_pixels=28,
					filled=True, stroked=True, pickable=True ) )
			last_refresh = str( st.session_state.get( 'live_world_last_refresh', '' ) or '' )
			last_processed = str( st.session_state.get(
				'live_world_geofence_last_refresh_processed', '' ) or '' )
			if not st.session_state[ 'live_world_geofence_initialized' ]:
				update_live_world_geofence_events( df_geofence )
				st.session_state[ 'live_world_geofence_last_refresh_processed' ] = last_refresh
			elif last_refresh and last_refresh != last_processed:
				update_live_world_geofence_events( df_geofence )
				st.session_state[ 'live_world_geofence_last_refresh_processed' ] = last_refresh
		except Exception as ex:
			geofence_error = str( ex )

	if not df_aircraft.empty:
		df_aircraft[ 'Radius' ] = 7000.0 * point_scale
		layers.append( pdk.Layer(
			'ScatterplotLayer', data=df_aircraft,
			get_position='[Longitude, Latitude]', get_radius='Radius',
			get_fill_color=[ 0, 170, 255, 220 ], get_line_color=[ 220, 245, 255, 240 ],
			line_width_min_pixels=1, radius_min_pixels=5, radius_max_pixels=26,
			filled=True, stroked=True, pickable=True ) )

	if not df_military.empty:
		df_military[ 'Radius' ] = 8500.0 * point_scale
		layers.append( pdk.Layer(
			'ScatterplotLayer', data=df_military,
			get_position='[Longitude, Latitude]', get_radius='Radius',
			get_fill_color=[ 255, 45, 85, 225 ], get_line_color=[ 255, 220, 225, 245 ],
			line_width_min_pixels=2, radius_min_pixels=6, radius_max_pixels=30,
			filled=True, stroked=True, pickable=True ) )

	if not df_satellites.empty:
		df_satellites[ 'Radius' ] = 8500.0 * point_scale
		layers.append( pdk.Layer(
			'ScatterplotLayer', data=df_satellites,
			get_position='[Longitude, Latitude]', get_radius='Radius',
			get_fill_color=[ 180, 120, 255, 220 ], get_line_color=[ 245, 235, 255, 240 ],
			line_width_min_pixels=1, radius_min_pixels=5, radius_max_pixels=28,
			filled=True, stroked=True, pickable=True ) )

	if not df_vessels.empty:
		df_vessels[ 'Radius' ] = 7500.0 * point_scale
		layers.append( pdk.Layer(
			'ScatterplotLayer', data=df_vessels,
			get_position='[Longitude, Latitude]', get_radius='Radius',
			get_fill_color=[ 0, 210, 190, 220 ], get_line_color=[ 210, 255, 250, 240 ],
			line_width_min_pixels=1, radius_min_pixels=5, radius_max_pixels=28,
			filled=True, stroked=True, pickable=True ) )

	if not df_earthquakes.empty:
		df_earthquakes[ 'Magnitude' ] = df_earthquakes[ 'Metadata' ].map(
			lambda value: get_metadata_number( value, 'Magnitude', 0.0 ) )
		df_earthquakes[ 'Radius' ] = df_earthquakes[ 'Magnitude' ].map(
			lambda value: max( 4000.0, (float( value ) + 1.0) * 9000.0 * point_scale ) )
		layers.append( pdk.Layer(
			'ScatterplotLayer', data=df_earthquakes,
			get_position='[Longitude, Latitude]', get_radius='Radius',
			get_fill_color=[ 255, 196, 0, 185 ], get_line_color=[ 255, 255, 255, 210 ],
			line_width_min_pixels=1, radius_min_pixels=4, radius_max_pixels=40,
			filled=True, stroked=True, pickable=True ) )

	if not df_fires.empty:
		df_fires[ 'Radius' ] = 9000.0 * point_scale
		layers.append( pdk.Layer(
			'ScatterplotLayer', data=df_fires,
			get_position='[Longitude, Latitude]', get_radius='Radius',
			get_fill_color=[ 255, 70, 0, 210 ], get_line_color=[ 255, 225, 180, 230 ],
			line_width_min_pixels=1, radius_min_pixels=4, radius_max_pixels=28,
			filled=True, stroked=True, pickable=True ) )

	df_measurement = pd.DataFrame( )
	measurement_result: Dict[ str, object ] = { }
	if st.session_state[ 'live_world_measurements' ]:
		try:
			measurement_result = calculate_live_world_measurement( latitude, longitude )
			start = measurement_result[ 'Start' ]
			end = measurement_result[ 'End' ]
			df_measurement = pd.DataFrame( [ start, end ] )
			path_data = [ { 'Path': [
				[ float( start[ 'Longitude' ] ), float( start[ 'Latitude' ] ) ],
				[ float( end[ 'Longitude' ] ), float( end[ 'Latitude' ] ) ] ] } ]
			layers.append( pdk.Layer( 'PathLayer', data=path_data, get_path='Path',
				get_color=[ 255, 255, 255, 230 ], get_width=4,
				width_min_pixels=2, width_max_pixels=7, pickable=False ) )
			df_measurement[ 'Radius' ] = 10000.0 * point_scale
			layers.append( pdk.Layer( 'ScatterplotLayer', data=df_measurement,
				get_position='[Longitude, Latitude]', get_radius='Radius',
				get_fill_color=[ 255, 255, 255, 80 ], get_line_color=[ 255, 255, 255, 255 ],
				line_width_min_pixels=2, radius_min_pixels=7, radius_max_pixels=28,
				filled=True, stroked=True, pickable=False ) )
		except Exception as ex:
			measurement_result = { 'Error': str( ex ) }

	df_annotations = get_live_world_annotation_frame( )
	if st.session_state[ 'live_world_measurements' ] and not df_annotations.empty:
		df_annotation_points = df_annotations.copy( )
		df_annotation_points[ 'Radius' ] = 9000.0 * point_scale
		layers.append( pdk.Layer( 'ScatterplotLayer', data=df_annotation_points,
			get_position='[Longitude, Latitude]', get_radius='Radius',
			get_fill_color=[ 255, 210, 0, 180 ], get_line_color=[ 255, 255, 255, 255 ],
			line_width_min_pixels=2, radius_min_pixels=7, radius_max_pixels=28,
			filled=True, stroked=True, pickable=True ) )
		layers.append( pdk.Layer( 'TextLayer', data=df_annotations,
			get_position='[Longitude, Latitude]', get_text='Label', get_size=14,
			get_color=[ 255, 255, 255, 255 ], get_angle=0,
			get_text_anchor='middle', get_alignment_baseline='bottom', pickable=False ) )

	if not df_infrastructure.empty:
		df_infrastructure[ 'Radius' ] = 8500.0 * point_scale
		layers.append( pdk.Layer( 'ScatterplotLayer', data=df_infrastructure,
			get_position='[Longitude, Latitude]', get_radius='Radius',
			get_fill_color=[ 255, 165, 60, 190 ], get_line_color=[ 255, 225, 180, 255 ],
			line_width_min_pixels=1, stroked=True, pickable=True ) )

	if not df_cameras.empty:
		df_cameras[ 'Radius' ] = 7500.0 * point_scale
		layers.append( pdk.Layer( 'ScatterplotLayer', data=df_cameras,
			get_position='[Longitude, Latitude]', get_radius='Radius',
			get_fill_color=[ 70, 210, 255, 205 ], get_line_color=[ 220, 250, 255, 255 ],
			line_width_min_pixels=1, radius_min_pixels=5, radius_max_pixels=28,
			stroked=True, pickable=True ) )


	if not df_map_layers.empty:
		df_map_layers[ 'Radius' ] = 7000.0 * point_scale
		layers.append( pdk.Layer( 'ScatterplotLayer', data=df_map_layers,
			get_position='[Longitude, Latitude]', get_radius='Radius',
			get_fill_color=[ 85, 220, 140, 190 ], get_line_color=[ 220, 255, 235, 255 ],
			line_width_min_pixels=1, radius_min_pixels=4, radius_max_pixels=26,
			filled=True, stroked=True, pickable=True ) )

	df_tracking = get_live_world_tracking_frame( )
	if st.session_state[ 'live_world_tracking' ] and not df_tracking.empty:
		if len( df_tracking ) > 1:
			path_data = [ {
				'Path': df_tracking[ [ 'Longitude', 'Latitude' ] ].values.tolist( ) } ]
			layers.append( pdk.Layer(
				'PathLayer', data=path_data, get_path='Path',
				get_color=[ 0, 255, 170, 235 ], get_width=5,
				width_min_pixels=2, width_max_pixels=8, pickable=False ) )

		df_tracked_point = df_tracking.tail( 1 ).copy( )
		df_tracked_point[ 'Radius' ] = 15000.0 * point_scale
		layers.append( pdk.Layer(
			'ScatterplotLayer', data=df_tracked_point,
			get_position='[Longitude, Latitude]', get_radius='Radius',
			get_fill_color=[ 0, 255, 170, 80 ], get_line_color=[ 0, 255, 170, 255 ],
			line_width_min_pixels=3, radius_min_pixels=10, radius_max_pixels=40,
			filled=True, stroked=True, pickable=False ) )

	center_latitude = float( latitude )
	center_longitude = float( longitude )
	if not (-90.0 <= center_latitude <= 90.0 and -180.0 <= center_longitude <= 180.0):
		center_latitude = float( df_map[ 'Latitude' ].median( ) )
		center_longitude = float( df_map[ 'Longitude' ].median( ) )
	if (st.session_state[ 'live_world_geofencing' ] and geofence_origin
			and not st.session_state[ 'live_world_cross_layer_analysis' ]):
		center_latitude = float( geofence_origin[ 'Latitude' ] )
		center_longitude = float( geofence_origin[ 'Longitude' ] )
	if (st.session_state[ 'live_world_cross_layer_analysis' ] and analysis_origin):
		center_latitude = float( analysis_origin[ 'Latitude' ] )
		center_longitude = float( analysis_origin[ 'Longitude' ] )
	if (st.session_state[ 'live_world_tracking' ]
			and st.session_state[ 'live_world_tracking_follow' ]
			and not df_tracking.empty):
		center_latitude = float( df_tracking.iloc[ -1 ][ 'Latitude' ] )
		center_longitude = float( df_tracking.iloc[ -1 ][ 'Longitude' ] )

	view_state = pdk.ViewState( latitude=center_latitude, longitude=center_longitude,
		zoom=int( st.session_state[ 'live_world_zoom' ] ), pitch=0 )
	tooltip = {
		'html': (
			'<b>{EntityType}</b><br/><b>{Name}</b><br/>'
			'<b>Source:</b> {Source}<br/><b>Time:</b> {Timestamp}<br/>'
			'<b>Coordinates:</b> {Latitude}, {Longitude}<br/>'
			'<b>Altitude / Depth:</b> {Altitude}<br/>'
			'<b>Speed:</b> {Speed}<br/><b>Heading:</b> {Heading}<br/>'
			'<b>Metadata:</b> {MetadataText}' ),
		'style': {
			'backgroundColor': 'rgba(0, 0, 0, 0.88)',
			'color': 'white',
			'fontSize': '12px',
		},
	}
	df_history = pd.DataFrame( )
	df_history_latest = pd.DataFrame( )
	if st.session_state[ 'live_world_historical_replay' ]:
		try:
			df_history = load_live_world_replay_frame( )
			if not df_history.empty:
				df_history_latest = df_history.sort_values( by='ObservedAt', kind='stable' ).groupby(
					[ 'EntityType', 'EntityId' ], as_index=False ).last( )
				df_replay_points = df_history_latest.copy( )
				df_replay_points[ 'Radius' ] = 7000.0 * float(
					st.session_state[ 'live_world_point_scale' ] )
				layers.append( pdk.Layer( 'ScatterplotLayer', data=df_replay_points,
					get_position='[Longitude, Latitude]', get_radius='Radius',
					get_fill_color=[ 180, 120, 255, 180 ], get_line_color=[ 240, 220, 255, 255 ],
					line_width_min_pixels=1, stroked=True, pickable=True ) )
				moving_types = [ 'Aircraft', 'Military Aircraft', 'Satellite', 'Vessel' ]
				path_rows: List[ Dict[ str, object ] ] = [ ]
				for (entity_type, entity_id), group in df_history[
					df_history[ 'EntityType' ].isin( moving_types ) ].groupby(
						[ 'EntityType', 'EntityId' ], sort=False ):
					group = group.sort_values( by='ObservedAt', kind='stable' )
					path_points = group[ [ 'Longitude', 'Latitude' ] ].values.tolist( )
					if len( path_points ) > 1:
						path_rows.append( { 'EntityType': entity_type, 'EntityId': entity_id,
							'Path': path_points } )
				if path_rows:
					layers.append( pdk.Layer( 'PathLayer', data=pd.DataFrame( path_rows ),
						get_path='Path', get_color=[ 180, 120, 255, 210 ],
						get_width=3, width_min_pixels=2, pickable=True ) )
		except Exception as history_ex:
			st.session_state[ 'live_world_history_last_error' ] = str( history_ex )

	deck = pdk.Deck( layers=layers, initial_view_state=view_state,
		map_style=map_style_options[ st.session_state[ 'live_world_map_style' ] ], tooltip=tooltip )
	st.pydeck_chart( deck, use_container_width=True )

	entities_tab, aircraft_tab, military_tab, satellites_tab, vessels_tab, earthquakes_tab, fires_tab, infrastructure_tab, cameras_tab, map_layers_tab, tracking_tab, measurements_tab, analysis_tab, geofence_tab, history_tab, agent_tools_tab = st.tabs(
		[ '🌐 Entities', '✈️ Aircraft', '🛩️ Military', '🛰️ Satellites', '🚢 Vessels',
			'📈 Earthquakes', '🔥 Fires', '📡 Infrastructure', '📷 Cameras', '🗺️ Map Layers', '🎯 Tracking',
			'📏 Measurements', '🧭 Analysis', '🛡️ Geofence', '🕓 Historical Replay', '🤖 Agent Tools' ] )

	with entities_tab:
		st.data_editor( make_live_world_display_frame( df_map ), key='live_world_entities_table',
			use_container_width=True, disabled=True, hide_index=True )

	with aircraft_tab:
		df_aircraft_records = st.session_state.get( 'live_world_df_aircraft', pd.DataFrame( ) )
		if df_aircraft_records is None or df_aircraft_records.empty:
			st.info( 'No aircraft records loaded.' )
		else:
			st.data_editor( make_live_world_display_frame( df_aircraft_records ),
				key='live_world_aircraft_table', use_container_width=True,
				disabled=True, hide_index=True )

	with military_tab:
		df_military_records = st.session_state.get(
			'live_world_df_military_aircraft', pd.DataFrame( ) )
		if df_military_records is None or df_military_records.empty:
			st.info( 'No military aircraft records loaded.' )
		else:
			st.data_editor( make_live_world_display_frame( df_military_records ),
				key='live_world_military_aircraft_table', use_container_width=True,
				disabled=True, hide_index=True )

	with satellites_tab:
		df_satellite_records = st.session_state.get( 'live_world_df_satellites', pd.DataFrame( ) )
		if df_satellite_records is None or df_satellite_records.empty:
			st.info( 'No satellite records loaded.' )
		else:
			st.data_editor( make_live_world_display_frame( df_satellite_records ),
				key='live_world_satellite_table', use_container_width=True,
				disabled=True, hide_index=True )

	with vessels_tab:
		df_vessel_records = st.session_state.get( 'live_world_df_vessels', pd.DataFrame( ) )
		if df_vessel_records is None or df_vessel_records.empty:
			st.info( 'No vessel records loaded.' )
		else:
			st.data_editor( make_live_world_display_frame( df_vessel_records ),
				key='live_world_vessel_table', use_container_width=True,
				disabled=True, hide_index=True )

	with earthquakes_tab:
		df_quakes = st.session_state.get( 'live_world_df_earthquakes', pd.DataFrame( ) )
		if df_quakes is None or df_quakes.empty:
			st.info( 'No earthquake records loaded.' )
		else:
			st.data_editor( make_live_world_display_frame( df_quakes ),
				key='live_world_earthquake_table', use_container_width=True,
				disabled=True, hide_index=True )

	with fires_tab:
		df_fire_records = st.session_state.get( 'live_world_df_fires', pd.DataFrame( ) )
		if df_fire_records is None or df_fire_records.empty:
			st.info( 'No fire records loaded.' )
		else:
			st.data_editor( make_live_world_display_frame( df_fire_records ),
				key='live_world_fire_table', use_container_width=True,
				disabled=True, hide_index=True )


	with infrastructure_tab:
		if df_infrastructure.empty:
			st.info( 'No infrastructure features are loaded.' )
		else:
			categories = df_infrastructure[ 'Metadata' ].map(
				lambda value: value.get( 'Category', '' ) if isinstance( value, dict ) else '' )
			infra_c1, infra_c2 = st.columns( 2, border=True )
			infra_c1.metric( 'Features', f'{len( df_infrastructure.index ):,}' )
			infra_c2.metric( 'Categories', f'{categories.nunique( ):,}' )
			df_display = df_infrastructure.copy( )
			df_display[ 'Category' ] = categories
			st.data_editor( df_display[ [ 'EntityId', 'Category', 'Name', 'Latitude', 'Longitude',
				'Source', 'Metadata' ] ], key='live_world_infrastructure_table',
				use_container_width=True, disabled=True, hide_index=True )


	with cameras_tab:
		if df_cameras.empty:
			st.info( 'No public CCTV or webcam features are loaded.' )
		else:
			categories = df_cameras[ 'Metadata' ].map(
				lambda value: value.get( 'Category', '' ) if isinstance( value, dict ) else '' )
			web_urls = df_cameras[ 'Metadata' ].map(
				lambda value: value.get( 'Web URL', '' ) if isinstance( value, dict ) else '' )
			camera_c1, camera_c2, camera_c3 = st.columns( 3, border=True )
			camera_c1.metric( 'Cameras', f'{len( df_cameras.index ):,}' )
			camera_c2.metric( 'Categories', f'{categories.nunique( ):,}' )
			camera_c3.metric( 'Web URLs', f'{int( web_urls.astype( bool ).sum( ) ):,}' )
			df_display = df_cameras.copy( )
			df_display[ 'Category' ] = categories
			df_display[ 'WebURL' ] = web_urls
			st.data_editor( df_display[ [ 'EntityId', 'Category', 'Name', 'Latitude', 'Longitude',
				'WebURL', 'Source', 'Metadata' ] ], key='live_world_camera_table',
				use_container_width=True, disabled=True, hide_index=True )


	with map_layers_tab:
		if df_map_layers.empty:
			st.info( 'No additional map features are loaded.' )
		else:
			categories = df_map_layers[ 'Metadata' ].map(
				lambda value: value.get( 'Category', '' ) if isinstance( value, dict ) else '' )
			map_c1, map_c2 = st.columns( 2, border=True )
			map_c1.metric( 'Features', f'{len( df_map_layers.index ):,}' )
			map_c2.metric( 'Categories', f'{categories.nunique( ):,}' )
			df_display = df_map_layers.copy( )
			df_display[ 'Category' ] = categories
			st.data_editor( make_live_world_display_frame( df_display[ [
				'EntityId', 'Category', 'Name', 'Latitude', 'Longitude', 'Source', 'Metadata' ] ] ),
				key='live_world_map_layers_table', use_container_width=True,
				disabled=True, hide_index=True )

	with tracking_tab:
		if df_tracking.empty:
			st.info( 'No tracking trail has been recorded. Select a moving entity and Refresh.' )
		else:
			tracking_c1, tracking_c2, tracking_c3 = st.columns( 3, border=True )
			tracking_c1.metric( 'Trail Points', f'{len( df_tracking ):,}' )
			tracking_c2.metric( 'Entity', str( df_tracking.iloc[ -1 ][ 'Name' ] ) )
			tracking_c3.metric( 'Type', str( df_tracking.iloc[ -1 ][ 'EntityType' ] ) )
			st.data_editor( df_tracking, key='live_world_tracking_table',
				use_container_width=True, disabled=True, hide_index=True )


	with measurements_tab:
		if not st.session_state[ 'live_world_measurements' ]:
			st.info( 'Enable Measurements & Annotations in the sidebar.' )
		else:
			if 'Error' in measurement_result:
				st.error( f'Measurement failed: {measurement_result[ "Error" ]}' )
			elif measurement_result:
				measure_c1, measure_c2, measure_c3, measure_c4 = st.columns( 4, border=True )
				measure_c1.metric( 'Nautical Miles', f'{measurement_result[ "DistanceNM" ]:,.2f}' )
				measure_c2.metric( 'Kilometers', f'{measurement_result[ "DistanceKM" ]:,.2f}' )
				measure_c3.metric( 'Miles', f'{measurement_result[ "DistanceMiles" ]:,.2f}' )
				measure_c4.metric( 'Bearing', f'{measurement_result[ "Bearing" ]:,.1f}°' )
				st.data_editor( df_measurement, key='live_world_measurement_table',
					use_container_width=True, disabled=True, hide_index=True )
			st.caption( 'Annotations' )
			if df_annotations.empty:
				st.info( 'No annotations have been added.' )
			else:
				st.data_editor( df_annotations, key='live_world_annotation_table',
					use_container_width=True, disabled=True, hide_index=True )



	with analysis_tab:
		if not st.session_state[ 'live_world_cross_layer_analysis' ]:
			st.info( 'Enable Cross-Layer Analysis in AI & Advanced Tools.' )
		elif analysis_error:
			st.error( f'Cross-Layer Analysis failed: {analysis_error}' )
		elif df_analysis.empty:
			st.info( 'No loaded entities match the selected radius and entity types.' )
		else:
			nearest = df_analysis.iloc[ 0 ]
			analysis_c1, analysis_c2, analysis_c3, analysis_c4 = st.columns( 4, border=True )
			analysis_c1.metric( 'Entities in Radius', f'{len( df_analysis ):,}' )
			analysis_c2.metric( 'Radius (NM)',
				f'{int( st.session_state[ "live_world_analysis_radius_nm" ] ):,}' )
			analysis_c3.metric( 'Nearest Entity', str( nearest[ 'Name' ] ) )
			analysis_c4.metric( 'Nearest Distance (NM)', f'{float( nearest[ "DistanceNM" ] ):,.2f}' )
			st.caption( f'Origin: {analysis_origin[ "Label" ]}' )
			df_nearest_by_type = df_analysis.sort_values( by='DistanceNM', kind='stable' ).groupby(
				'EntityType', as_index=False ).first( )
			st.markdown( '**Nearest by Entity Type**' )
			st.data_editor( make_live_world_display_frame( df_nearest_by_type ),
				key='live_world_analysis_nearest_by_type_table', use_container_width=True,
				disabled=True, hide_index=True )
			st.markdown( '**Entities Within Radius**' )
			st.data_editor( make_live_world_display_frame( df_analysis ),
				key='live_world_analysis_table', use_container_width=True,
				disabled=True, hide_index=True )

	with geofence_tab:
		if not st.session_state[ 'live_world_geofencing' ]:
			st.info( 'Enable Geofencing in AI & Advanced Tools.' )
		elif geofence_error:
			st.error( f'Geofencing failed: {geofence_error}' )
		else:
			df_geofence_events = get_live_world_geofence_event_frame( )
			geofence_c1, geofence_c2, geofence_c3, geofence_c4 = st.columns( 4, border=True )
			geofence_c1.metric( 'Inside Geofence', f'{len( df_geofence ):,}' )
			geofence_c2.metric( 'Radius (NM)',
				f'{float( st.session_state[ "live_world_geofence_radius_nm" ] ):,.0f}' )
			geofence_c3.metric( 'Events', f'{len( df_geofence_events ):,}' )
			last_event = str( df_geofence_events.iloc[ -1 ][ 'Event' ] ) if not df_geofence_events.empty else 'None'
			geofence_c4.metric( 'Last Event', last_event )
			if geofence_origin:
				st.caption( f'Origin: {geofence_origin[ "Label" ]}' )
			if df_geofence.empty:
				st.info( 'No selected Live World entities are currently inside the geofence.' )
			else:
				st.markdown( '**Entities Inside Geofence**' )
				st.data_editor( make_live_world_display_frame( df_geofence ),
					key='live_world_geofence_table', use_container_width=True,
					disabled=True, hide_index=True )
			st.markdown( '**Entry / Exit Events**' )
			if df_geofence_events.empty:
				st.info( 'No geofence transition events have been recorded.' )
			else:
				st.data_editor( df_geofence_events, key='live_world_geofence_events_table',
					use_container_width=True, disabled=True, hide_index=True )

	with history_tab:
		if not st.session_state[ 'live_world_historical_replay' ]:
			st.info( 'Enable Historical Replay in AI & Advanced Tools.' )
		else:
			history_summary = get_live_world_history_summary( )
			history_c1, history_c2, history_c3, history_c4 = st.columns( 4, border=True )
			history_c1.metric( 'Observations', f'{int( history_summary[ "ObservationCount" ] ):,}' )
			history_c2.metric( 'Snapshots', f'{int( history_summary[ "SnapshotCount" ] ):,}' )
			history_c3.metric( 'Replay Records', f'{len( df_history ):,}' )
			history_c4.metric( 'Replay Entities', f'{len( df_history_latest ):,}' )
			if st.session_state[ 'live_world_history_last_error' ]:
				st.error( f'Historical Replay failed: {st.session_state[ "live_world_history_last_error" ]}' )
			st.caption( f'Replay snapshot: {st.session_state.get( "live_world_history_snapshot", "" ) or "None"}' )
			st.caption( f'Last refresh inserted {int( st.session_state.get( "live_world_history_last_saved", 0 ) ):,} historical observations.' )
			if df_history.empty:
				st.info( 'No persisted observations match the selected replay window and entity types.' )
			else:
				st.markdown( '**Replay Positions**' )
				st.data_editor( make_live_world_display_frame( df_history_latest ),
					key='live_world_history_latest_table', use_container_width=True,
					disabled=True, hide_index=True )
				st.markdown( '**Historical Observations**' )
				st.data_editor( make_live_world_display_frame( df_history ),
					key='live_world_history_table', use_container_width=True,
					disabled=True, hide_index=True )

	with agent_tools_tab:
		if not st.session_state[ 'live_world_agent_tools' ]:
			st.info( 'Enable Agent Tools in AI & Advanced Tools.' )
		else:
			provider_status = LIVE_WORLD_AGENT_TOOLS[ 'get_live_world_source_status' ]( )
			agent_c1, agent_c2, agent_c3 = st.columns( 3, border=True )
			agent_c1.metric( 'Callable Tools', f'{len( LIVE_WORLD_AGENT_TOOLS ):,}' )
			agent_c2.metric( 'Entity Types', '9' )
			agent_c3.metric( 'Provider Sources', f'{len( provider_status ):,}' )
			st.markdown( '**Available Callable Tools**' )
			df_agent_tools = pd.DataFrame( [ {
				'Tool': name,
				'Callable': callable( tool ),
			} for name, tool in LIVE_WORLD_AGENT_TOOLS.items( ) ] )
			st.data_editor( df_agent_tools, key='live_world_agent_tools_table',
				width='stretch', disabled=True, hide_index=True )
			st.markdown( '**Provider Status**' )
			st.data_editor( pd.DataFrame( provider_status ),
				key='live_world_agent_provider_status_table', width='stretch',
				disabled=True, hide_index=True )
			st.caption(
				'Provider-neutral tools operate on normalized Live World state and return '
				'JSON-serializable results for external agent frameworks.' )

def get_metadata_number( metadata: object, key: str, default: float=0.0 ) -> float:
	'''

	Purpose:
		Read a numeric value from a GeoEntity metadata dictionary for map sizing.

	Args:
		metadata (object): Metadata dictionary.
		key (str): Metadata key.
		default (float): Fallback value.

	Returns:
		float: Numeric metadata value.

	'''
	throw_if( 'key', key )
	if not isinstance( metadata, dict ):
		return default
	try:
		return float( metadata.get( key, default ) )
	except ( TypeError, ValueError ):
		return default

def make_live_world_display_frame( df_frame: pd.DataFrame ) -> pd.DataFrame:
	'''

	Purpose:
		Create a Streamlit-safe display copy of Live World entity data.

	Args:
		df_frame (pd.DataFrame): Live World entity data.

	Returns:
		pd.DataFrame: Display-safe entity data.

	'''
	throw_if( 'df_frame', df_frame )
	df_display = df_frame.copy( )
	if 'Metadata' in df_display.columns:
		df_display[ 'Metadata' ] = df_display[ 'Metadata' ].map(
			lambda value: json.dumps( value, default=str ) if isinstance( value, dict ) else str( value ) )
	for column in [ 'Radius', 'Magnitude', 'MetadataText' ]:
		if column in df_display.columns:
			df_display = df_display.drop( columns=[ column ] )
	return df_display
