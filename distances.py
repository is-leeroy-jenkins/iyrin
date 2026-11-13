'''
  ******************************************************************************************
      Assembly:                Iyrin
      Filename:                distances.py
      Author:                  Terry D. Eppler
      Created:                 05-31-2022

      Last Modified By:        Terry D. Eppler
      Last Modified On:        05-01-2025
  ******************************************************************************************
  <copyright file="distances.py" company="Terry D. Eppler">

	     Iyrin is a python framework encapsulating the Google Maps functionality.
	     Copyright ©  2022  Terry Eppler

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
    distances.py
  </summary>
  ******************************************************************************************
'''
from __future__ import annotations
from typing import Any, Dict, List, Tuple, Union
import math
import pandas as pd
from mapping import Map
from boogr import Error, Logger


def throw_if( name: str, value: object ) -> None:
	"""Validate a required runtime value.

	Purpose:
		Ensures required embedding configuration and input values are present before provider or
		local-model work begins.

	Args:
		name (str): Argument name included in validation errors.
		value (object): Runtime value to validate.

	Returns:
		None: This function validates input and does not return a value.
	"""
	if value is None:
		raise ValueError( f'Argument "{name}" cannot be empty!' )

	if isinstance( value, str ) and not value.strip( ):
		raise ValueError( f'Argument "{name}" cannot be empty!' )

	if isinstance( value, ( list, tuple, dict, set ) ) and len( value ) == 0:
		raise ValueError( f'Argument "{name}" cannot be empty!' )


Coord = Tuple[ float, float ]
AddressOrCoord = Union[ str, Coord ]

def fmt( o: AddressOrCoord ) -> str:
	"""
	
		Purpose:
			Normalize an origin/destination input to the API's expected string.
	
		Parameters:
			o (AddressOrCoord):
				Either "lat,lng" as tuple or a free-form string address.
	
		Returns:
			String representation for the API, "lat,lng" or the original string.
			
	"""
	throw_if( 'o', o )
	if isinstance( o, str ):
		return o
	if isinstance( o, tuple ) and len( o ) == 2:
		latitude, longitude = o
		if (type( latitude ) not in (int, float) or
				type( longitude ) not in (int, float) or
				not math.isfinite( latitude ) or not math.isfinite( longitude ) or
				not -90 <= latitude <= 90 or not -180 <= longitude <= 180):
			raise ValueError( 'Coordinates must be finite latitude/longitude values in range.' )
		return f'{latitude},{longitude}'
	raise TypeError( 'A location must be an address string or (latitude, longitude) tuple.' )

class DistanceMatrix( ):
	"""
	
		Purpose:
			Provide route, route-comparison, and matrix wrappers around the Google
			Distance Matrix API.

		The instance exposes summary, matrix, compare_modes, and DataFrame helpers.
			
	"""
	_maps: Map
	modes: List[ str ]
	data: Dict[ str, Any ] | None
	rows: List[ Dict[ str, Any ] ] | None
	
	def __init__( self, maps: Map ) -> None:
		self._maps = maps
		self.modes = [ 'driving', 'walking', 'bicycling', 'transit' ]
		self.data = None
		self.rows = None
	
	def normalize_mode( self, mode: str ) -> str:
		"""

			Purpose:
				Validate and normalize a Google Distance Matrix travel mode.

			Parameters:
				mode (str):
					Travel mode: driving, walking, bicycling, or transit.

			Returns:
				str:
					Normalized travel mode.

		"""
		try:
			throw_if( 'mode', mode )
			if not isinstance( mode, str ):
				raise TypeError( 'mode must be a string.' )
			value = mode.strip( ).lower( )
			if value not in self.modes:
				raise ValueError( f'Unsupported travel mode "{mode}". Use one of: {self.modes}.' )
			
			return value
		except Exception as e:
			exception = Error( e )
			exception.module = 'iyrin'
			exception.cause = 'DistanceMatrix'
			exception.method = 'normalize_mode( self, mode: str )'
			Logger( ).write( exception )
			raise exception from e
	
	def normalize_inputs( self, values: List[ AddressOrCoord ] | Tuple[ AddressOrCoord, ... ] | AddressOrCoord ) -> List[ AddressOrCoord ]:
		"""

			Purpose:
				Normalize one or many origins/destinations into a list.

			Parameters:
				values (List[AddressOrCoord] | Tuple[AddressOrCoord, ...] | AddressOrCoord):
					Single address/coordinate or a list/tuple of them.

			Returns:
				List[AddressOrCoord]:
					Normalized input list.

		"""
		try:
			throw_if( 'values', values )
			if isinstance( values, list ):
				locations = values
			elif isinstance( values, tuple ):
				if len( values ) == 2 and all(
					type( x ) in (int, float) for x in values ):
					locations = [ values ]
				else:
					locations = list( values )
			else:
				locations = [ values ]
			throw_if( 'locations', locations )
			for location in locations:
				fmt( location )
			return locations
		except Exception as e:
			exception = Error( e )
			exception.module = 'iyrin'
			exception.cause = 'DistanceMatrix'
			exception.method = 'normalize_inputs( self, values: object )'
			Logger( ).write( exception )
			raise exception from e
	
	def convert_distance( self, meters: int | float | None ) -> Dict[ str, float | None ]:
		"""

			Purpose:
				Convert meters into kilometers and miles.

			Parameters:
				meters (int | float | None):
					Distance in meters.

			Returns:
				Dict[str, float | None]:
					Distance conversions.

		"""
		try:
			if meters is None:
				return { 'distance_km': None, 'distance_miles': None }
			if (type( meters ) not in (int, float) or
					not math.isfinite( meters ) or meters < 0):
				raise ValueError( 'meters must be a finite, nonnegative number.' )
			return { 'distance_km': round( meters / 1000.0, 3 ),
					'distance_miles': round( meters / 1609.344, 3 ) }
		except Exception as e:
			exception = Error( e )
			exception.module = 'iyrin'
			exception.cause = 'DistanceMatrix'
			exception.method = 'convert_distance( self, meters: int | float | None )'
			Logger( ).write( exception )
			raise exception from e
	
	def convert_duration( self, seconds: int | float | None ) -> Dict[ str, float | None ]:
		"""

			Purpose:
				Convert seconds into minutes and hours.

			Parameters:
				seconds (int | float | None):
					Duration in seconds.

			Returns:
				Dict[str, float | None]:
					Duration conversions.

		"""
		try:
			if seconds is None:
				return { 'duration_minutes': None,
						'duration_hours': None }
			if (type( seconds ) not in (int, float) or
					not math.isfinite( seconds ) or seconds < 0):
				raise ValueError( 'seconds must be a finite, nonnegative number.' )
			return { 'duration_minutes': round( seconds / 60.0, 2 ),
					'duration_hours': round( seconds / 3600.0, 3 ) }
		except Exception as e:
			exception = Error( e )
			exception.module = 'iyrin'
			exception.cause = 'DistanceMatrix'
			exception.method = 'convert_duration( self, seconds: int | float | None )'
			Logger( ).write( exception )
			raise exception from e
	
	def flatten_element( self, origin: str, destination: str, mode: str,
			element: Dict[ str, Any ] ) -> Dict[ str, Any ]:
		"""

			Purpose:
				Flatten one Distance Matrix element into a row-friendly dictionary.

			Parameters:
				origin (str):
					Resolved origin label from the API.
				destination (str):
					Resolved destination label from the API.
				mode (str):
					Travel mode used for the request.
				element (Dict[str, Any]):
					One Distance Matrix element.

			Returns:
				Dict[str, Any]:
					Flattened route row.

		"""
		try:
			throw_if( 'origin', origin )
			throw_if( 'destination', destination )
			throw_if( 'mode', mode )
			if not isinstance( element, dict ):
				raise TypeError( 'element must be a dictionary.' )
			distance = element.get( 'distance' ) or { }
			duration = element.get( 'duration' ) or { }
			duration_traffic = element.get( 'duration_in_traffic' ) or { }
			distance_meters = distance.get( 'value' )
			duration_seconds = duration.get( 'value' )
			traffic_seconds = duration_traffic.get( 'value' )
			row = { 'origin': origin,
					'destination': destination,
					'mode': mode,
					'status': element.get( 'status' ),
					'distance_text': distance.get( 'text' ),
					'distance_meters': distance_meters,
					'duration_text': duration.get( 'text' ),
					'duration_seconds': duration_seconds,
					'duration_in_traffic_text': duration_traffic.get( 'text' ),
					'duration_in_traffic_seconds': traffic_seconds }
			row.update( self.convert_distance( distance_meters ) )
			row.update( self.convert_duration( duration_seconds ) )
			if traffic_seconds is None:
				row[ 'duration_in_traffic_minutes' ] = None
				row[ 'duration_in_traffic_hours' ] = None
			else:
				traffic_duration = self.convert_duration( traffic_seconds )
				row[ 'duration_in_traffic_minutes' ] = traffic_duration[ 'duration_minutes' ]
				row[ 'duration_in_traffic_hours' ] = traffic_duration[ 'duration_hours' ]
			return row
		except Exception as e:
			exception = Error( e )
			exception.module = 'iyrin'
			exception.cause = 'DistanceMatrix'
			exception.method = 'flatten_element( self, origin: str, destination: str, mode: str, element: Dict[ str, Any ] )'
			Logger( ).write( exception )
			raise exception from e
	
	def matrix( self, origins: List[ AddressOrCoord ] | Tuple[ AddressOrCoord, ... ] | AddressOrCoord,
			destinations: List[ AddressOrCoord ] | Tuple[ AddressOrCoord, ... ] | AddressOrCoord,
			mode: str='driving', departure_time: str='' ) -> List[ Dict[ str, Any ] ]:
		"""

			Purpose:
				Execute a Distance Matrix request for one or more origins and one
				or more destinations.

			Parameters:
				origins (List[AddressOrCoord] | Tuple[AddressOrCoord, ...] | AddressOrCoord):
					Single origin or multiple origins.
				destinations (List[AddressOrCoord] | Tuple[AddressOrCoord, ...] | AddressOrCoord):
					Single destination or multiple destinations.
				mode (str):
					Travel mode: driving, walking, bicycling, or transit.
				departure_time (str):
					Optional departure time. Use 'now' for traffic-aware driving
					results when supported.

			Returns:
				List[Dict[str, Any]]:
					Flattened route rows.

		"""
		try:
			throw_if( 'origins', origins )
			throw_if( 'destinations', destinations )
			if not isinstance( departure_time, str ):
				raise TypeError( 'departure_time must be a string.' )
			travel_mode = self.normalize_mode( mode )
			origin_values = self.normalize_inputs( origins )
			destination_values = self.normalize_inputs( destinations )
			origin_query = '|'.join( fmt( value ) for value in origin_values )
			destination_query = '|'.join( fmt( value ) for value in destination_values )
			params = { 'origins': origin_query,
					'destinations': destination_query,
					'mode': travel_mode }
			if departure_time:
				params[ 'departure_time' ] = departure_time
			self.data = self._maps.request( 'distancematrix/json', params )
			if not isinstance( self.data, dict ):
				raise ValueError( 'Distance Matrix response was not a dictionary.' )
			status = self.data.get( 'status' )
			if status != 'OK':
				raise RuntimeError(
					f'Google Distance Matrix request failed: {status or "UNKNOWN_STATUS"}. '
					f'{self.data.get( "error_message", "" )}' )
			origin_addresses = self.data.get(
				'origin_addresses' ) or [ fmt( x ) for x in origin_values ]
			destination_addresses = self.data.get(
				'destination_addresses' ) or [ fmt( x ) for x in destination_values]
			api_rows = self.data.get( 'rows' )
			if not isinstance( api_rows, list ) or len( api_rows ) != len( origin_values ):
				raise ValueError( 'Distance Matrix response origin count does not match request.' )
			output_rows: List[ Dict[ str, Any ] ] = [ ]
			for origin_index, row in enumerate( api_rows ):
				if not isinstance( row, dict ):
					raise TypeError( 'Distance Matrix response row must be a dictionary.' )
				origin_label = ( origin_addresses[ origin_index ]
						if origin_index < len( origin_addresses )
						else fmt( origin_values[ origin_index ] ) )
				elements = row.get( 'elements' )
				if not isinstance( elements, list ) or len( elements ) != len( destination_values ):
					raise ValueError( 'Distance Matrix response destination count does not match request.' )
				for destination_index, element in enumerate( elements ):
					destination_label = ( destination_addresses[ destination_index ]
							if destination_index < len( destination_addresses )
							else fmt( destination_values[ destination_index ] ) )
					output_rows.append( self.flatten_element( origin=origin_label,
							destination=destination_label, mode=travel_mode, element=element ) )
			self.rows = output_rows
			return output_rows
		except Exception as e:
			exception = Error( e )
			exception.module = 'iyrin'
			exception.cause = 'DistanceMatrix'
			exception.method = "matrix( self, origins, destinations, mode: str='driving', departure_time: str='' )"
			Logger( ).write( exception )
			raise exception from e
	
	def summary( self, origin: AddressOrCoord, destination: AddressOrCoord,
			mode: str='driving' ) -> Dict:
		"""
		
			Purpose:
				Return a compact dict with meters/seconds and human text fields
				for one origin, one destination, and one travel mode.
	
			Parameters:
				origin (AddressOrCoord):
					Origin address string or (lat, lng) tuple.
				destination (AddressOrCoord):
					Destination address string or (lat, lng) tuple.
				mode (str):
					Travel mode: driving, walking, bicycling, transit.
	
			Returns:
				Dict:
					Distance and duration summary.
				
		"""
		try:
			throw_if( 'origin', origin )
			throw_if( 'destination', destination )
			rows = self.matrix( origins=origin, destinations=destination, mode=mode )
			if not rows:
				return { 'distance_text': None,
						'distance_meters': None,
						'duration_text': None,
						'duration_seconds': None,
						'status': 'NO_RESULTS' }
			
			row = rows[ 0 ]
			return { 'distance_text': row.get( 'distance_text' ),
					'distance_meters': row.get( 'distance_meters' ),
					'distance_km': row.get( 'distance_km' ),
					'distance_miles': row.get( 'distance_miles' ),
					'duration_text': row.get( 'duration_text' ),
					'duration_seconds': row.get( 'duration_seconds' ),
					'duration_minutes': row.get( 'duration_minutes' ),
					'duration_hours': row.get( 'duration_hours' ),
					'duration_in_traffic_text': row.get( 'duration_in_traffic_text' ),
					'duration_in_traffic_seconds': row.get( 'duration_in_traffic_seconds' ),
					'duration_in_traffic_minutes': row.get( 'duration_in_traffic_minutes' ),
					'origin': row.get( 'origin' ),
					'destination': row.get( 'destination' ),
					'mode': row.get( 'mode' ),
					'status': row.get( 'status' ) }
		except Exception as e:
			exception = Error( e )
			exception.module = 'iyrin'
			exception.cause = 'DistanceMatrix'
			exception.method = "summary( self, origin, destination, mode: str='driving' ) -> Dict"
			Logger( ).write( exception )
			raise exception from e
	
	def compare_modes( self, origin: AddressOrCoord, destination: AddressOrCoord,
			modes: List[ str ] | None=None, departure_time: str='' ) -> List[ Dict[ str, Any ] ]:
		"""

			Purpose:
				Compare route distance and duration across multiple travel modes.

			Parameters:
				origin (AddressOrCoord):
					Origin address string or coordinate tuple.
				destination (AddressOrCoord):
					Destination address string or coordinate tuple.
				modes (List[str] | None):
					Optional travel modes. Defaults to all supported modes.
				departure_time (str):
					Optional departure time. Use 'now' for traffic-aware driving
					results when supported.

			Returns:
				List[Dict[str, Any]]:
					One flattened route summary per travel mode.

		"""
		try:
			throw_if( 'origin', origin )
			throw_if( 'destination', destination )
			if modes is not None:
				throw_if( 'modes', modes )
				if not isinstance( modes, list ):
					raise TypeError( 'modes must be a list of travel modes.' )
			selected_modes = self.modes if modes is None else modes
			results: List[ Dict[ str, Any ] ] = [ ]
			for mode in selected_modes:
				active_mode = self.normalize_mode( mode )
				active_departure = departure_time if active_mode == 'driving' else ''
				rows = self.matrix( origins=origin, destinations=destination,
					mode=active_mode, departure_time=active_departure )
				if rows:
					results.append( rows[ 0 ] )
			return results
		except Exception as e:
			exception = Error( e )
			exception.module = 'Iyrin'
			exception.cause = 'DistanceMatrix'
			exception.method = "compare_modes( self, origin, destination, modes=None, departure_time: str='' )"
			Logger( ).write( exception )
			raise exception from e
	
	def to_dataframe( self, rows: List[ Dict[ str, Any ] ] | None=None ) -> pd.DataFrame:
		"""

			Purpose:
				Convert route rows into a pandas DataFrame for Streamlit display,
				export, or downstream analytics.

			Parameters:
				rows (List[Dict[str, Any]] | None):
					Optional rows. Defaults to the most recent matrix rows.

			Returns:
				pd.DataFrame:
					Route results as a DataFrame.

		"""
		try:
			active_rows = rows if rows is not None else self.rows
			if not active_rows:
				return pd.DataFrame( )
			return pd.DataFrame( active_rows )
		except Exception as e:
			exception = Error( e )
			exception.module = 'iyrin'
			exception.cause = 'DistanceMatrix'
			exception.method = 'to_dataframe( self, rows=None ) -> pd.DataFrame'
			Logger( ).write( exception )
			raise exception