'''
******************************************************************************************
 Assembly:                iyr
 Filename:                tools.py
 Author:                  Terry D. Eppler / Assistant
 Created:                 09-12-2026

 Last Modified By:        Terry D. Eppler / Assistant
 Last Modified On:        09-12-2026
******************************************************************************************

Purpose:
    Provider-neutral callable tools for querying Iyr Live World Data. The functions operate
    on the normalized Live World session state and return JSON-serializable dictionaries
    and lists suitable for agent/tool-calling integrations.
******************************************************************************************
'''

from __future__ import annotations

import math
from typing import Dict, List

import pandas as pd
import streamlit as st

from history import get_live_world_history_summary, load_live_world_history

LIVE_WORLD_ENTITY_TYPES: List[ str ] = [ 'Aircraft', 'Military Aircraft', 'Satellite', 'Vessel',
		'Earthquake', 'Fire', 'Infrastructure', 'Camera', 'Map Feature', ]

def throw_if( name: str, value: object ) -> None:
    '''

        Purpose:
        --------
        Validate that a required value is not empty.

        Parameters:
        -----------
        name (str): Name of the argument being validated.
        value (object): Value to validate.

        Returns:
        --------
        None

    '''
    if value is None:
        raise ValueError( f'Argument "{name}" cannot be None.' )

    if isinstance( value, str ) and not value.strip( ):
        raise ValueError( f'Argument "{name}" cannot be empty.' )

def calculate_distance_nm( latitude_a: float, longitude_a: float,
        latitude_b: float, longitude_b: float ) -> float:
    '''

        Purpose:
        --------
        Calculate great-circle distance between two coordinates in nautical miles.

        Parameters:
        -----------
        latitude_a (float): Origin latitude.
        longitude_a (float): Origin longitude.
        latitude_b (float): Destination latitude.
        longitude_b (float): Destination longitude.

        Returns:
        --------
        float: Great-circle distance in nautical miles.

    '''
    lat_a = math.radians( latitude_a )
    lat_b = math.radians( latitude_b )
    delta_lat = math.radians( latitude_b - latitude_a )
    delta_lon = math.radians( longitude_b - longitude_a )
    value = (math.sin( delta_lat / 2.0 ) ** 2
        + math.cos( lat_a ) * math.cos( lat_b ) * math.sin( delta_lon / 2.0 ) ** 2)
    arc = 2.0 * math.atan2( math.sqrt( value ), math.sqrt( 1.0 - value ) )
    return 3440.065 * arc

def calculate_bearing( latitude_a: float, longitude_a: float,
        latitude_b: float, longitude_b: float ) -> float:
    '''

        Purpose:
        --------
        Calculate initial bearing between two coordinates.

        Parameters:
        -----------
        latitude_a (float): Origin latitude.
        longitude_a (float): Origin longitude.
        latitude_b (float): Destination latitude.
        longitude_b (float): Destination longitude.

        Returns:
        --------
        float: Initial bearing in degrees from true north.

    '''
    lat_a = math.radians( latitude_a )
    lat_b = math.radians( latitude_b )
    delta_lon = math.radians( longitude_b - longitude_a )
    y = math.sin( delta_lon ) * math.cos( lat_b )
    x = (math.cos( lat_a ) * math.sin( lat_b )
        - math.sin( lat_a ) * math.cos( lat_b ) * math.cos( delta_lon ))
    return (math.degrees( math.atan2( y, x ) ) + 360.0) % 360.0

def make_entity_record( row: pd.Series ) -> Dict[ str, object ]:
    '''

        Purpose:
        --------
        Convert one normalized Live World entity row to a JSON-serializable record.

        Parameters:
        -----------
        row (pd.Series): Normalized Live World entity row.

        Returns:
        --------
        Dict[str, object]: JSON-serializable entity record.

    '''
    record: Dict[ str, object ] = { }
    for key, value in row.to_dict( ).items( ):
        if isinstance( value, dict ):
            record[ str( key ) ] = value
        elif pd.isna( value ):
            record[ str( key ) ] = None
        elif hasattr( value, 'item' ):
            record[ str( key ) ] = value.item( )
        else:
            record[ str( key ) ] = value
    return record

def get_live_world_status( ) -> Dict[ str, object ]:
    '''

        Purpose:
        --------
        Return the current Live World layer, refresh, tracking, analysis, and geofence state.

        Returns:
        --------
        Dict[str, object]: Current Live World operational status.

    '''
    df_entities = st.session_state.get( 'live_world_df_entities', pd.DataFrame( ) )
    counts: Dict[ str, int ] = { }
    if df_entities is not None and not df_entities.empty and 'EntityType' in df_entities.columns:
        counts = {
            str( key ): int( value )
            for key, value in df_entities[ 'EntityType' ].value_counts( ).to_dict( ).items( )
        }
    return {
        'Enabled': bool( st.session_state.get( 'live_world_enabled', False ) ),
        'LastRefresh': str( st.session_state.get( 'live_world_last_refresh', '' ) ),
        'LastError': str( st.session_state.get( 'live_world_last_error', '' ) ),
        'EntityCount': int( 0 if df_entities is None else len( df_entities.index ) ),
        'EntityCounts': counts,
        'TrackingEnabled': bool( st.session_state.get( 'live_world_tracking', False ) ),
        'CrossLayerAnalysisEnabled': bool(
            st.session_state.get( 'live_world_cross_layer_analysis', False ) ),
        'GeofencingEnabled': bool( st.session_state.get( 'live_world_geofencing', False ) ),
    }

def list_live_world_entities( entity_type: str, limit: int ) -> List[ Dict[ str, object ] ]:
    '''

        Purpose:
        --------
        Return loaded normalized Live World entities for a selected entity type.

        Parameters:
        -----------
        entity_type (str): Entity type or All.
        limit (int): Maximum number of records to return.

        Returns:
        --------
        List[Dict[str, object]]: Matching normalized entity records.

    '''
    throw_if( 'entity_type', entity_type )
    throw_if( 'limit', limit )
    if entity_type != 'All' and entity_type not in LIVE_WORLD_ENTITY_TYPES:
        raise ValueError( f'Unsupported entity type: {entity_type}' )
    if limit < 1 or limit > 500:
        raise ValueError( 'Argument "limit" must be between 1 and 500.' )
    df_entities = st.session_state.get( 'live_world_df_entities', pd.DataFrame( ) )
    if df_entities is None or df_entities.empty:
        return [ ]
    df_result = df_entities.copy( )
    if entity_type != 'All':
        df_result = df_result[ df_result[ 'EntityType' ].astype( str ) == entity_type ].copy( )
    return [ make_entity_record( row ) for _, row in df_result.head( limit ).iterrows( ) ]

def search_live_world_entities( query: str, entity_type: str, limit: int ) -> List[ Dict[ str, object ] ]:
    '''

        Purpose:
        --------
        Search loaded Live World entities by identifier or name.

        Parameters:
        -----------
        query (str): Case-insensitive identifier/name search text.
        entity_type (str): Entity type or All.
        limit (int): Maximum number of records to return.

        Returns:
        --------
        List[Dict[str, object]]: Matching normalized entity records.

    '''
    throw_if( 'query', query )
    throw_if( 'entity_type', entity_type )
    throw_if( 'limit', limit )
    if entity_type != 'All' and entity_type not in LIVE_WORLD_ENTITY_TYPES:
        raise ValueError( f'Unsupported entity type: {entity_type}' )
    if limit < 1 or limit > 500:
        raise ValueError( 'Argument "limit" must be between 1 and 500.' )
    df_entities = st.session_state.get( 'live_world_df_entities', pd.DataFrame( ) )
    if df_entities is None or df_entities.empty:
        return [ ]
    df_result = df_entities.copy( )
    if entity_type != 'All':
        df_result = df_result[ df_result[ 'EntityType' ].astype( str ) == entity_type ].copy( )
    search_text = query.casefold( )
    mask = (df_result[ 'EntityId' ].astype( str ).str.casefold( ).str.contains(
        search_text, regex=False, na=False )
        | df_result[ 'Name' ].astype( str ).str.casefold( ).str.contains(
            search_text, regex=False, na=False ))
    df_result = df_result[ mask ].head( limit )
    return [ make_entity_record( row ) for _, row in df_result.iterrows( ) ]

def find_live_world_nearest( latitude: float, longitude: float, radius_nm: float,
        entity_type: str, limit: int ) -> List[ Dict[ str, object ] ]:
    '''

        Purpose:
        --------
        Return the nearest loaded Live World entities to a coordinate within a radius.

        Parameters:
        -----------
        latitude (float): Search-origin latitude.
        longitude (float): Search-origin longitude.
        radius_nm (float): Maximum search radius in nautical miles.
        entity_type (str): Entity type or All.
        limit (int): Maximum number of records to return.

        Returns:
        --------
        List[Dict[str, object]]: Nearest entities with distance and bearing.

    '''
    throw_if( 'latitude', latitude )
    throw_if( 'longitude', longitude )
    throw_if( 'radius_nm', radius_nm )
    throw_if( 'entity_type', entity_type )
    throw_if( 'limit', limit )
    if latitude < -90.0 or latitude > 90.0:
        raise ValueError( 'Argument "latitude" must be between -90 and 90.' )
    if longitude < -180.0 or longitude > 180.0:
        raise ValueError( 'Argument "longitude" must be between -180 and 180.' )
    if radius_nm <= 0.0:
        raise ValueError( 'Argument "radius_nm" must be greater than zero.' )
    if entity_type != 'All' and entity_type not in LIVE_WORLD_ENTITY_TYPES:
        raise ValueError( f'Unsupported entity type: {entity_type}' )
    if limit < 1 or limit > 500:
        raise ValueError( 'Argument "limit" must be between 1 and 500.' )
    df_entities = st.session_state.get( 'live_world_df_entities', pd.DataFrame( ) )
    if df_entities is None or df_entities.empty:
        return [ ]
    df_result = df_entities.copy( )
    if entity_type != 'All':
        df_result = df_result[ df_result[ 'EntityType' ].astype( str ) == entity_type ].copy( )
    records: List[ Dict[ str, object ] ] = [ ]
    for _, row in df_result.iterrows( ):
        row_latitude = float( row[ 'Latitude' ] )
        row_longitude = float( row[ 'Longitude' ] )
        distance_nm = calculate_distance_nm(
            latitude, longitude, row_latitude, row_longitude )
        if distance_nm > radius_nm:
            continue
        record = make_entity_record( row )
        record[ 'DistanceNM' ] = distance_nm
        record[ 'DistanceKM' ] = distance_nm * 1.852
        record[ 'DistanceMiles' ] = distance_nm * 1.150779448
        record[ 'Bearing' ] = calculate_bearing(
            latitude, longitude, row_latitude, row_longitude )
        records.append( record )
    records.sort( key=lambda value: float( value[ 'DistanceNM' ] ) )
    return records[ :limit ]

def get_live_world_geofence_status( ) -> Dict[ str, object ]:
    '''

        Purpose:
        --------
        Return the current geofence configuration, membership snapshot, and transition events.

        Returns:
        --------
        Dict[str, object]: Current geofence state and event history.

    '''
    snapshot = dict( st.session_state.get( 'live_world_geofence_snapshot', { } ) or { } )
    events = list( st.session_state.get( 'live_world_geofence_events', [ ] ) or [ ] )
    return {
        'Enabled': bool( st.session_state.get( 'live_world_geofencing', False ) ),
        'Origin': str( st.session_state.get( 'live_world_geofence_origin', 'Current Location' ) ),
        'RadiusNM': float( st.session_state.get( 'live_world_geofence_radius_nm', 50 ) ),
        'EntityTypes': list( st.session_state.get( 'live_world_geofence_entity_types', [ ] ) or [ ] ),
        'CurrentMemberCount': len( snapshot ),
        'CurrentMembers': list( snapshot.values( ) ),
        'EventCount': len( events ),
        'Events': events,
    }

def get_live_world_source_status( ) -> List[ Dict[ str, object ] ]:
    '''

        Purpose:
        --------
        Return provider-level Live World refresh status and failure diagnostics.

        Returns:
        --------
        List[Dict[str, object]]: Provider status records.

    '''
    statuses = dict( st.session_state.get( 'live_world_source_status', { } ) or { } )
    errors = dict( st.session_state.get( 'live_world_source_errors', { } ) or { } )
    last_attempt = dict( st.session_state.get( 'live_world_source_last_attempt', { } ) or { } )
    last_success = dict( st.session_state.get( 'live_world_source_last_success', { } ) or { } )
    stale = dict( st.session_state.get( 'live_world_source_stale', { } ) or { } )
    keys = sorted( set( statuses ) | set( errors ) | set( last_attempt ) | set( last_success ) )
    return [ {
        'Source': key,
        'Status': str( statuses.get( key, 'Not Refreshed' ) ),
        'Error': str( errors.get( key, '' ) ),
        'LastAttempt': str( last_attempt.get( key, '' ) ),
        'LastSuccess': str( last_success.get( key, '' ) ),
        'Stale': bool( stale.get( key, False ) ),
    } for key in keys ]

def get_live_world_analysis_status( ) -> Dict[ str, object ]:
    '''

        Purpose:
        --------
        Return the current Cross-Layer Analysis configuration exposed by the Live World UI.

        Returns:
        --------
        Dict[str, object]: Cross-layer analysis configuration.

    '''
    return {
        'Enabled': bool( st.session_state.get( 'live_world_cross_layer_analysis', False ) ),
        'Origin': str( st.session_state.get( 'live_world_analysis_origin', 'Current Location' ) ),
        'RadiusNM': float( st.session_state.get( 'live_world_analysis_radius_nm', 250 ) ),
        'EntityTypes': list( st.session_state.get( 'live_world_analysis_entity_types', [ ] ) or [ ] ),
        'Limit': int( st.session_state.get( 'live_world_analysis_limit', 100 ) ),
    }

def get_live_world_history_status( ) -> Dict[ str, object ]:
    '''

        Purpose:
        --------
        Return Historical Replay configuration and persisted-history summary statistics.

        Returns:
        --------
        Dict[str, object]: Historical Replay configuration and persistence summary.

    '''
    summary = get_live_world_history_summary( )
    return {
        'Enabled': bool( st.session_state.get( 'live_world_historical_replay', False ) ),
        'PersistRefreshes': bool( st.session_state.get( 'live_world_history_persist', False ) ),
        'RetentionDays': int( st.session_state.get( 'live_world_history_retention_days', 30 ) ),
        'Window': str( st.session_state.get( 'live_world_history_window', '24 Hours' ) ),
        'EntityTypes': list( st.session_state.get( 'live_world_history_entity_types', [ ] ) or [ ] ),
        'Limit': int( st.session_state.get( 'live_world_history_limit', 5000 ) ),
        'Snapshot': str( st.session_state.get( 'live_world_history_snapshot', '' ) ),
        'LastSaved': int( st.session_state.get( 'live_world_history_last_saved', 0 ) ),
        'LastError': str( st.session_state.get( 'live_world_history_last_error', '' ) ),
        'Summary': summary,
    }

def list_live_world_history( hours: int, entity_type: str, snapshot: str,
        limit: int ) -> List[ Dict[ str, object ] ]:
    '''

        Purpose:
        --------
        Return persisted Live World observations through a selected historical snapshot.

        Parameters:
        -----------
        hours (int): Replay lookback in hours; zero loads all retained history.
        entity_type (str): Entity type or All.
        snapshot (str): Maximum replay timestamp to include.
        limit (int): Maximum observations returned.

        Returns:
        --------
        List[Dict[str, object]]: Historical observations in chronological order.

    '''
    throw_if( 'hours', hours )
    throw_if( 'entity_type', entity_type )
    throw_if( 'snapshot', snapshot )
    throw_if( 'limit', limit )
    if hours < 0:
        raise ValueError( 'Argument "hours" cannot be negative.' )
    if entity_type != 'All' and entity_type not in LIVE_WORLD_ENTITY_TYPES:
        raise ValueError( f'Unsupported entity type: {entity_type}' )
    if limit < 1 or limit > 25000:
        raise ValueError( 'Argument "limit" must be between 1 and 25000.' )
    entity_types = LIVE_WORLD_ENTITY_TYPES if entity_type == 'All' else [ entity_type ]
    df_history = load_live_world_history(
        hours=hours, entity_types=entity_types, snapshot=snapshot, limit=limit )
    if df_history.empty:
        return [ ]
    return [ make_entity_record( row ) for _, row in df_history.iterrows( ) ]



def get_live_world_tracking_status( ) -> Dict[ str, object ]:
    '''

        Purpose:
        --------
        Return the active tracking target and recorded trail history.

        Returns:
        --------
        Dict[str, object]: Current tracking state and trail points.

    '''
    history = list( st.session_state.get( 'live_world_tracking_history', [ ] ) or [ ] )
    return {
        'Enabled': bool( st.session_state.get( 'live_world_tracking', False ) ),
        'Entity': str( st.session_state.get( 'live_world_tracking_entity', '' ) ),
        'ActiveEntity': str( st.session_state.get( 'live_world_tracking_active_entity', '' ) ),
        'Follow': bool( st.session_state.get( 'live_world_tracking_follow', True ) ),
        'TrailPointCount': len( history ),
        'Trail': history,
    }


LIVE_WORLD_AGENT_TOOLS: Dict[ str, object ] = {
    'get_live_world_status': get_live_world_status,
    'list_live_world_entities': list_live_world_entities,
    'search_live_world_entities': search_live_world_entities,
    'find_live_world_nearest': find_live_world_nearest,
    'get_live_world_source_status': get_live_world_source_status,
    'get_live_world_analysis_status': get_live_world_analysis_status,
    'get_live_world_geofence_status': get_live_world_geofence_status,
    'get_live_world_tracking_status': get_live_world_tracking_status,
    'get_live_world_history_status': get_live_world_history_status,
    'list_live_world_history': list_live_world_history,
}
