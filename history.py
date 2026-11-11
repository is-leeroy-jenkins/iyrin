'''
	******************************************************************************************
	 Assembly:                iyr
	 Filename:                history.py
	 Author:                  Terry D. Eppler / Assistant
	 Created:                 09-12-2026
	
	 Last Modified By:        Terry D. Eppler / Assistant
	 Last Modified On:        09-17-2026
	******************************************************************************************
	
	Purpose:
	    SQLite-backed persistence and retrieval for normalized Live World observations. The
	    module stores explicit Live World refresh snapshots in Iyr's existing SQLite database
	    and provides bounded historical queries used by Historical Replay.
	******************************************************************************************
'''

from __future__ import annotations

import datetime as dt
import hashlib
import json
import math
import sqlite3
from pathlib import Path
from typing import Dict, List
from boogr import Error, Logger
import pandas as pd
import config as cfg


HISTORY_TABLE = 'LiveWorldHistory'
HISTORY_STATE_TABLE = 'LiveWorldHistoryState'
HISTORY_DEDUP_ENTITY_TYPES: List[ str ] = [
    'Earthquake', 'Fire', 'Infrastructure', 'Camera', 'Map Feature' ]
HISTORY_COLUMNS: List[ str ] = [
    'RefreshId', 'ObservedAt', 'EntityId', 'EntityType', 'Name', 'Latitude', 'Longitude',
    'Altitude', 'Heading', 'Speed', 'Timestamp', 'Source', 'Metadata' ]


def throw_if( name: str, value: object ) -> None:
    '''

        Purpose:
        --------
        Validate that a required argument is not empty.

        Parameters:
        -----------
        name (str): Argument name.
        value (object): Argument value.

        Returns:
        --------
        None

    '''
    if value is None:
        raise ValueError( f'Argument "{name}" cannot be None.' )

    if isinstance( value, str ) and not value.strip( ):
        raise ValueError( f'Argument "{name}" cannot be empty.' )


def initialize_live_world_history( ) -> None:
    '''

        Purpose:
        --------
        Create the Live World history tables and supporting indexes when they do not exist.

        Returns:
        --------
        None

    '''
    try:
	    database_path = Path( cfg.DB_PATH )
	    database_path.parent.mkdir( parents=True, exist_ok=True )
	    with sqlite3.connect( database_path ) as conn:
		    conn.execute( f'''
	            CREATE TABLE IF NOT EXISTS {HISTORY_TABLE} (
	                Id INTEGER PRIMARY KEY AUTOINCREMENT,
	                RefreshId TEXT NOT NULL,
	                ObservedAt TEXT NOT NULL,
	                EntityId TEXT NOT NULL,
	                EntityType TEXT NOT NULL,
	                Name TEXT NOT NULL,
	                Latitude REAL NOT NULL,
	                Longitude REAL NOT NULL,
	                Altitude REAL,
	                Heading REAL,
	                Speed REAL,
	                Timestamp TEXT,
	                Source TEXT NOT NULL,
	                Metadata TEXT,
	                UNIQUE (RefreshId, EntityType, EntityId)
	            )
	        ''' )
		    conn.execute( f'''
	            CREATE INDEX IF NOT EXISTS IX_{HISTORY_TABLE}_ObservedAt
	            ON {HISTORY_TABLE} (ObservedAt)
	        ''' )
		    conn.execute( f'''
	            CREATE INDEX IF NOT EXISTS IX_{HISTORY_TABLE}_Entity
	            ON {HISTORY_TABLE} (EntityType, EntityId, ObservedAt)
	        ''' )
		    conn.execute( f'''
	            CREATE TABLE IF NOT EXISTS {HISTORY_STATE_TABLE} (
	                EntityType TEXT NOT NULL,
	                EntityId TEXT NOT NULL,
	                Fingerprint TEXT NOT NULL,
	                UpdatedAt TEXT NOT NULL,
	                PRIMARY KEY (EntityType, EntityId)
	            )
	        ''' )
    except Exception as e:
	    exception = Error( e )
	    exception.module = 'Iyrin'
	    exception.cause = 'history'
	    exception.method = 'initialize_live_world_history( ) -> None'
	    Logger( ).write( exception )
	    raise exception from e

def create_live_world_history_fingerprint( row: pd.Series ) -> str:
    '''

        Purpose:
        --------
        Create a stable content fingerprint for event/static Live World entities so
        unchanged observations are not persisted repeatedly across refreshes.

        Parameters:
        -----------
        row (pd.Series): Normalized Live World entity row.

        Returns:
        --------
        str: SHA-256 fingerprint of the entity's persisted state excluding observation time.

    '''
    try:
	    throw_if( 'row', row )
	    if not isinstance( row, pd.Series ):
	        raise TypeError( 'row must be a pandas Series.' )
	    metadata = row.get( 'Metadata', { } )
	    metadata_value = metadata if isinstance( metadata, dict ) else { }
	    state = {
	        'EntityType': str( row.get( 'EntityType', '' ) ),
	        'EntityId': str( row.get( 'EntityId', '' ) ),
	        'Name': str( row.get( 'Name', '' ) ),
	        'Latitude': float( row.get( 'Latitude', 0.0 ) ),
	        'Longitude': float( row.get( 'Longitude', 0.0 ) ),
	        'Altitude': float( row.get( 'Altitude', 0.0 ) )
	            if pd.notna( row.get( 'Altitude', 0.0 ) ) else None,
	        'Heading': float( row.get( 'Heading', 0.0 ) )
	            if pd.notna( row.get( 'Heading', 0.0 ) ) else None,
	        'Speed': float( row.get( 'Speed', 0.0 ) )
	            if pd.notna( row.get( 'Speed', 0.0 ) ) else None,
	        'Source': str( row.get( 'Source', '' ) ),
	        'Metadata': metadata_value,
	    }
	    payload = json.dumps( state, sort_keys=True, ensure_ascii=False,
	        separators=( ',', ':' ), default=str )
	    return hashlib.sha256( payload.encode( 'utf-8' ) ).hexdigest( )
    except Exception as e:
	    exception = Error( e )
	    exception.module = 'Iyrin'
	    exception.cause = 'history'
	    exception.method = 'create_live_world_history_fingerprint( row: pd.Series ) -> str'
	    Logger( ).write( exception )
	    raise exception from e

def persist_live_world_history( df_entities: pd.DataFrame, refresh_id: str,
        observed_at: str, max_rows_per_source: int=5000 ) -> int:
    '''

        Purpose:
        --------
        Persist one normalized Live World refresh while bounding per-source growth and
        suppressing unchanged event/static observations across refreshes.

        Parameters:
        -----------
        df_entities (pd.DataFrame): Normalized Live World entity frame.
        refresh_id (str): Stable identifier for the refresh snapshot.
        observed_at (str): UTC ISO timestamp for the refresh.
        max_rows_per_source (int): Maximum rows persisted for one entity type in a refresh.

        Returns:
        --------
        int: Number of newly inserted observations.

    '''
    try:
	    throw_if( 'df_entities', df_entities )
	    throw_if( 'refresh_id', refresh_id )
	    throw_if( 'observed_at', observed_at )
	    throw_if( 'max_rows_per_source', max_rows_per_source )
	    if not isinstance( df_entities, pd.DataFrame ):
	        raise TypeError( 'df_entities must be a pandas DataFrame.' )
	    if not isinstance( refresh_id, str ) or not isinstance( observed_at, str ):
	        raise TypeError( 'refresh_id and observed_at must be strings.' )
	    if type( max_rows_per_source ) is not int or max_rows_per_source < 1:
	        raise ValueError( 'max_rows_per_source must be a positive integer.' )
	    timestamp = dt.datetime.fromisoformat( observed_at.replace( 'Z', '+00:00' ) )
	    if timestamp.tzinfo is None or timestamp.utcoffset( ) != dt.timedelta( 0 ):
	        raise ValueError( 'observed_at must be an ISO 8601 UTC timestamp.' )
	    initialize_live_world_history( )
	    if df_entities.empty:
	        return 0
	    required_columns = { 'EntityType', 'EntityId', 'Name', 'Latitude', 'Longitude', 'Source' }
	    if not required_columns.issubset( df_entities.columns ):
	        raise ValueError( 'df_entities is missing required history columns.' )
	
	    source_counts: Dict[ str, int ] = { }
	    inserted = 0
	    with sqlite3.connect( cfg.DB_PATH ) as conn:
	        for _, row in df_entities.iterrows( ):
	            entity_type = str( row.get( 'EntityType', '' ) )
	            entity_id = str( row.get( 'EntityId', '' ) )
	            latitude = row[ 'Latitude' ]
	            longitude = row[ 'Longitude' ]
	            if (not isinstance( latitude, (int, float) ) or
	                    not isinstance( longitude, (int, float) ) or
	                    isinstance( latitude, bool ) or isinstance( longitude, bool ) or
	                    not math.isfinite( latitude ) or not math.isfinite( longitude ) or
	                    not -90 <= latitude <= 90 or not -180 <= longitude <= 180):
	                raise ValueError( 'History coordinates must be finite and within valid ranges.' )
	            source_counts[ entity_type ] = source_counts.get( entity_type, 0 )
	            if source_counts[ entity_type ] >= max_rows_per_source:
	                continue
	
	            fingerprint = ''
	            if entity_type in HISTORY_DEDUP_ENTITY_TYPES:
	                fingerprint = create_live_world_history_fingerprint( row )
	                previous = conn.execute( f'''
	                    SELECT Fingerprint
	                    FROM {HISTORY_STATE_TABLE}
	                    WHERE EntityType = ? AND EntityId = ?
	                ''', (entity_type, entity_id) ).fetchone( )
	                if previous is not None and str( previous[ 0 ] ) == fingerprint:
	                    continue
	
	            metadata = row.get( 'Metadata', { } )
	            metadata_text = json.dumps(
	                metadata if isinstance( metadata, dict ) else { },
	                ensure_ascii=False, default=str )
	            cursor = conn.execute( f'''
	                INSERT OR IGNORE INTO {HISTORY_TABLE} (
	                    RefreshId, ObservedAt, EntityId, EntityType, Name, Latitude, Longitude,
	                    Altitude, Heading, Speed, Timestamp, Source, Metadata )
	                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
	            ''', (
	                refresh_id,
	                observed_at,
	                entity_id,
	                entity_type,
	                str( row.get( 'Name', '' ) ),
	                float( latitude ),
	                float( longitude ),
	                float( row.get( 'Altitude', 0.0 ) )
	                    if pd.notna( row.get( 'Altitude', 0.0 ) ) else None,
	                float( row.get( 'Heading', 0.0 ) )
	                    if pd.notna( row.get( 'Heading', 0.0 ) ) else None,
	                float( row.get( 'Speed', 0.0 ) )
	                    if pd.notna( row.get( 'Speed', 0.0 ) ) else None,
	                str( row.get( 'Timestamp', '' ) ),
	                str( row.get( 'Source', '' ) ),
	                metadata_text,
	            ) )
	            if cursor.rowcount != 1:
	                continue
	            inserted += 1
	            source_counts[ entity_type ] += 1
	
	            if fingerprint:
	                conn.execute( f'''
	                    INSERT INTO {HISTORY_STATE_TABLE} (
	                        EntityType, EntityId, Fingerprint, UpdatedAt )
	                    VALUES (?, ?, ?, ?)
	                    ON CONFLICT (EntityType, EntityId) DO UPDATE SET
	                        Fingerprint = excluded.Fingerprint,
	                        UpdatedAt = excluded.UpdatedAt
	                ''', (entity_type, entity_id, fingerprint, observed_at) )
	
	    return inserted
    except Exception as e:
	    exception = Error( e )
	    exception.module = 'Iyrin'
	    exception.cause = 'history'
	    exception.method = 'persist_live_world_history( df_entities, refresh_id, observed_at, max_rows_per_source=5000 ) -> int'
	    Logger( ).write( exception )
	    raise exception from e

def purge_live_world_history( retention_days: int ) -> int:
    '''

        Purpose:
        --------
        Delete persisted Live World observations older than the configured retention period
        and remove deduplication state for entities no longer present in retained history.

        Parameters:
        -----------
        retention_days (int): Number of days of history to retain.

        Returns:
        --------
        int: Number of deleted observations.

    '''
    try:
	    throw_if( 'retention_days', retention_days )
	    if type( retention_days ) is not int or retention_days < 1:
	        raise ValueError( 'retention_days must be a positive integer.' )
	    initialize_live_world_history( )
	    cutoff = dt.datetime.now( dt.timezone.utc ) - dt.timedelta( days=retention_days )
	    with sqlite3.connect( cfg.DB_PATH ) as conn:
	        cursor = conn.execute( f'DELETE FROM {HISTORY_TABLE} WHERE ObservedAt < ?',
	            (cutoff.isoformat( ),) )
	        deleted = int( cursor.rowcount if cursor.rowcount is not None else 0 )
	        conn.execute( f'''
	            DELETE FROM {HISTORY_STATE_TABLE}
	            WHERE NOT EXISTS (
	                SELECT 1
	                FROM {HISTORY_TABLE}
	                WHERE {HISTORY_TABLE}.EntityType = {HISTORY_STATE_TABLE}.EntityType
	                    AND {HISTORY_TABLE}.EntityId = {HISTORY_STATE_TABLE}.EntityId ) ''' )
	        return deleted
    except Exception as e:
	    exception = Error( e )
	    exception.module = 'Iyrin'
	    exception.cause = 'history'
	    exception.method = 'purge_live_world_history( retention_days: int ) -> int'
	    Logger( ).write( exception )
	    raise exception from e

def clear_live_world_history( ) -> int:
    '''

        Purpose:
        --------
        Delete all persisted Live World historical observations and deduplication state.

        Returns:
        --------
        int: Number of deleted observations.

    '''
    try:
	    initialize_live_world_history( )
	    with sqlite3.connect( cfg.DB_PATH ) as conn:
	        cursor = conn.execute( f'DELETE FROM {HISTORY_TABLE}' )
	        deleted = int( cursor.rowcount if cursor.rowcount is not None else 0 )
	        conn.execute( f'DELETE FROM {HISTORY_STATE_TABLE}' )
	        return deleted
    except Exception as e:
	    exception = Error( e )
	    exception.module = 'Iyrin'
	    exception.cause = 'history'
	    exception.method = 'clear_live_world_history( ) -> int'
	    Logger( ).write( exception )
	    raise exception from e

def get_live_world_history_snapshots( hours: int=24 ) -> List[ str ]:
    '''

        Purpose:
        --------
        Return persisted refresh timestamps within a replay window, newest first.

        Parameters:
        -----------
        hours (int): Replay lookback window in hours; zero returns all persisted snapshots.

        Returns:
        --------
        List[str]: Persisted refresh timestamps.

    '''
    try:
	    throw_if( 'hours', hours )
	    if type( hours ) is not int or hours < 0:
	        raise ValueError( 'hours must be a nonnegative integer.' )
	    initialize_live_world_history( )
	    query = f'SELECT DISTINCT ObservedAt FROM {HISTORY_TABLE}'
	    parameters: tuple = ( )
	    if hours > 0:
	        cutoff = dt.datetime.now( dt.timezone.utc ) - dt.timedelta( hours=hours )
	        query += ' WHERE ObservedAt >= ?'
	        parameters = (cutoff.isoformat( ),)
	    query += ' ORDER BY ObservedAt DESC'
	    with sqlite3.connect( cfg.DB_PATH ) as conn:
	        return [ str( row[ 0 ] ) for row in conn.execute( query, parameters ).fetchall( ) ]
    except Exception as e:
	    exception = Error( e )
	    exception.module = 'Iyrin'
	    exception.cause = 'history'
	    exception.method = 'get_live_world_history_snapshots( hours: int=24 ) -> List[ str ]'
	    Logger( ).write( exception )
	    raise exception from e

def load_live_world_history( hours: int, entity_types: List[ str ], snapshot: str,
        limit: int=5000 ) -> pd.DataFrame:
    '''

        Purpose:
        --------
        Load the most recent bounded set of persisted observations through a selected replay
        snapshot and return those observations in chronological order.

        Parameters:
        -----------
        hours (int): Replay lookback window in hours; zero loads all retained history.
        entity_types (List[str]): Entity types to include.
        snapshot (str): Maximum replay timestamp to include.
        limit (int): Maximum number of historical observations returned.

        Returns:
        --------
        pd.DataFrame: Recent historical observations ordered chronologically.

    '''
    try:
	    throw_if( 'hours', hours )
	    throw_if( 'entity_types', entity_types )
	    throw_if( 'snapshot', snapshot )
	    throw_if( 'limit', limit )
	    if type( hours ) is not int or hours < 0:
	        raise ValueError( 'hours must be a nonnegative integer.' )
	    if type( limit ) is not int or limit < 1:
	        raise ValueError( 'limit must be a positive integer.' )
	    if not isinstance( entity_types, list ) or any(
	            not isinstance( item, str ) or not item.strip( ) for item in entity_types ):
	        raise TypeError( 'entity_types must be a list of nonempty strings.' )
	    if not isinstance( snapshot, str ):
	        raise TypeError( 'snapshot must be a string.' )
	    snapshot_time = dt.datetime.fromisoformat( snapshot.replace( 'Z', '+00:00' ) )
	    if snapshot_time.tzinfo is None or snapshot_time.utcoffset( ) != dt.timedelta( 0 ):
	        raise ValueError( 'snapshot must be an ISO 8601 UTC timestamp.' )
	    if not entity_types:
	        return pd.DataFrame( columns=HISTORY_COLUMNS )
	    initialize_live_world_history( )
	
	    placeholders = ','.join( '?' for _ in entity_types )
	    clauses = [ f'EntityType IN ({placeholders})', 'ObservedAt <= ?' ]
	    parameters: List[ object ] = list( entity_types ) + [ snapshot ]
	    if hours > 0:
	        cutoff = dt.datetime.now( dt.timezone.utc ) - dt.timedelta( hours=hours )
	        clauses.append( 'ObservedAt >= ?' )
	        parameters.append( cutoff.isoformat( ) )
	    parameters.append( limit )
	    query = f'''
	        SELECT RefreshId, ObservedAt, EntityId, EntityType, Name, Latitude, Longitude,
	            Altitude, Heading, Speed, Timestamp, Source, Metadata
	        FROM (
	            SELECT RefreshId, ObservedAt, EntityId, EntityType, Name, Latitude, Longitude,
	                Altitude, Heading, Speed, Timestamp, Source, Metadata
	            FROM {HISTORY_TABLE}
	            WHERE {' AND '.join( clauses )}
	            ORDER BY ObservedAt DESC, EntityType ASC, EntityId ASC
	            LIMIT ?
	        )
	        ORDER BY ObservedAt ASC, EntityType ASC, EntityId ASC
	    '''
	    with sqlite3.connect( cfg.DB_PATH ) as conn:
	        df_history = pd.read_sql_query( query, conn, params=parameters )
	    if not df_history.empty:
	        df_history[ 'Metadata' ] = df_history[ 'Metadata' ].apply(
	            lambda value: json.loads( value ) if value else { } )
	    return df_history
    except Exception as e:
	    exception = Error( e )
	    exception.module = 'Iyrin'
	    exception.cause = 'history'
	    exception.method = 'load_live_world_history( hours, entity_types, snapshot, limit: int=5000 ) -> pd.DataFrame'
	    Logger( ).write( exception )
	    raise exception from e

def get_live_world_history_summary( ) -> Dict[ str, object ]:
    '''

        Purpose:
        --------
        Return aggregate persistence statistics for the Historical Replay interface.

        Returns:
        --------
        Dict[str, object]: Observation count, snapshot count, and retained time bounds.

    '''
    try:
	    initialize_live_world_history( )
	    with sqlite3.connect( cfg.DB_PATH ) as conn:
	        row = conn.execute( f'''
	            SELECT COUNT(*), COUNT(DISTINCT RefreshId), MIN(ObservedAt), MAX(ObservedAt)
	            FROM {HISTORY_TABLE}
	        ''' ).fetchone( )
	    return {
	        'ObservationCount': int( row[ 0 ] or 0 ),
	        'SnapshotCount': int( row[ 1 ] or 0 ),
	        'FirstObservedAt': str( row[ 2 ] or '' ),
	        'LastObservedAt': str( row[ 3 ] or '' ),
	    }
    except Exception as e:
	    exception = Error( e )
	    exception.module = 'Iyrin'
	    exception.cause = 'history'
	    exception.method = 'get_live_world_history_summary( ) -> Dict[ str, object ]'
	    Logger( ).write( exception )
	    raise exception from e
