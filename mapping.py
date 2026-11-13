'''
  ******************************************************************************************
      Assembly:                Iyrin
      Filename:                maps.py
      Author:                  Terry D. Eppler
      Created:                 05-31-2022

      Last Modified By:        Terry D. Eppler
      Last Modified On:        05-01-2025
  ******************************************************************************************
  <copyright file="maps.py" company="Terry D. Eppler">

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
    maps.py
  </summary>
  ******************************************************************************************
'''
import math
import time
from typing import Dict, Optional, List, Any, Tuple
import requests
import datetime as dt
from exceptions import GatewayError
from rates import RateLimiter
from boogr import Error, Logger
import config as cfg
from storage import BaseCache
from exceptions import NotFound

def throw_if( name: str, value: object ) -> None:
	"""
	
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
		
	"""
	if value is None:
		raise ValueError( f'Argument "{name}" cannot be None.' )
	
	if isinstance( value, str ) and not value.strip( ):
		raise ValueError( f'Argument "{name}" cannot be empty.' )

def flatten_geocode( result: Dict[ str, Any ] ) -> Dict[ str, Any ]:
	"""

		Purpose:
			Reduce a geocode result into a compact, row-friendly dict.

		Parameters:
			result (Dict[str, Any]):
				One element from 'results' in Geocoding API response.

		Returns:
			Dict with formatted_address, lat, lng, place_id, types, and components.

	"""
	geometry = result.get( 'geometry', { } ) or { }
	loc = geometry.get( 'location', { } ) or { }
	comps = result.get( 'address_components', [ ] ) or [ ]

	def comp( kind: str, want_long: bool = False ) -> Optional[ str ]:
		for c in comps:
			if kind in (c.get( 'types' ) or [ ]):
				return (c.get( 'long_name' ) if want_long else c.get( 'short_name' )) or None
		return None

	return {
			'formatted_address': result.get( 'formatted_address' ),
			'lat': loc.get( 'lat' ),
			'lng': loc.get( 'lng' ),
			'place_id': result.get( 'place_id' ),
			'types': ','.join( result.get( 'types', [ ] ) ) if result.get( 'types' ) else None,
			'country_code': comp( 'country' ),
			'country_name': comp( 'country', want_long = True ),
			'admin_level_1': comp( 'administrative_area_level_1' ),
			'admin_level_2': comp( 'administrative_area_level_2' ),
			'locality': comp( 'locality' ) or comp( 'postal_town' ),
			'postal_code': comp( 'postal_code' ),
	}

class Map( ):
	"""

	    Purpose:
	        Centralized HTTP gateway for Google Maps Web Services. Handles rate
	        limiting, retry-with-backoff, API-key injection, response diagnostics,
	        and Google payload-status normalization.

	    The Google Maps API key is loaded from configuration during initialization.
	    Use .request("geocode/json", {...}) or another supported endpoint path to
	    execute requests through the configured gateway.

    """
	base_url: Optional[ str ]
	endpoint: Optional[ str ]
	params: Optional[ Dict[ str, str ] ]
	api_key: str
	query_per_second: Optional[ float ]
	retries: Optional[ int ]
	min: Optional[ float ]
	max: Optional[ float ]
	timeout: Optional[ float ]
	url: Optional[ str ]
	session: Optional[ requests.Session ]
	limiter: Optional[ RateLimiter ]
	query: Optional[ Dict[ str, str ] ]
	response: Optional[ requests.Response ]
	last_url: Optional[ str ]
	last_query: Optional[ Dict[ str, str ] ]
	last_status: Optional[ int ]
	last_elapsed_ms: Optional[ float ]
	last_payload_status: Optional[ str ]
	last_payload_error: Optional[ str ]
	BASE = 'https://maps.googleapis.com/maps/api'
	
	def __init__( self, qps: float = 5.0, retries: int = 5, min: float = 1.0, max: float = 30.0,
	              timeout: float = 15.0, api_key: str = None ) -> None:
		self.api_key = api_key if api_key is not None else cfg.GOOGLEMAPS_API_KEY
		self.limiter = RateLimiter( qps )
		self.retries = retries
		self.min = min
		self.max = max
		self.timeout = timeout
		self.session = requests.Session( )
		self.base_url = self.BASE
		self.endpoint = None
		self.params = None
		self.url = None
		self.query = None
		self.response = None
		self.last_url = None
		self.last_query = None
		self.last_status = None
		self.last_elapsed_ms = None
		self.last_payload_status = None
		self.last_payload_error = None
	
	def request( self, endpoint: str, params: Dict[ str, str ] ) -> Dict | None:
		"""

	        Purpose:
	            Execute a GET request to the given Google Maps endpoint with query
	            params and robust retry/backoff for transient errors. The Google
	            Maps API key is injected as the "key" query parameter.

	        Parameters:
	            endpoint (str):
	                Endpoint path, e.g., "geocode/json", "distancematrix/json".
	            params (Dict[str, str]):
	                Query parameters for the request. "key" is injected.

	        Returns:
	            Parsed JSON dictionary on success.

        """
		try:
			throw_if( 'endpoint', endpoint )
			throw_if( 'params', params )
			throw_if( 'api_key', self.api_key )
			self.endpoint = endpoint
			self.params = params
			self.url = f'{self.base_url}/{self.endpoint}'
			self.last_url = self.url
			attempt = 0
			backoff = self.min
			while True:
				self.limiter.wait( )
				retryable_failure = False
				try:
					self.query = dict( self.params )
					self.query[ 'key' ] = self.api_key
					self.last_query = { key: value for key, value in self.query.items( ) if
					                    key != 'key' }
					start = time.perf_counter( )
					self.response = self.session.get( self.url, params=self.query,
						timeout=self.timeout )
					elapsed = time.perf_counter( ) - start
					self.last_elapsed_ms = round( elapsed * 1000.0, 3 )
					self.last_status = self.response.status_code
					if self.last_status != 200:
						if self.last_status in (408, 429, 500, 502, 503, 504):
							retryable_failure = True
							raise GatewayError( f'Transient HTTP {self.last_status}: '
							                    f'{self.response.text[ :200 ]}' )
						raise GatewayError(
							f'HTTP {self.last_status}: {self.response.text[ :200 ]}' )
					payload = self.response.json( )
					self.last_payload_status = None
					self.last_payload_error = None
					if isinstance( payload, dict ):
						payload_status = str( payload.get( 'status', '' ) or '' ).strip( )
						payload_error = str( payload.get( 'error_message', '' ) or '' ).strip( )
						self.last_payload_status = payload_status
						self.last_payload_error = payload_error
						hard_failures = { 'REQUEST_DENIED', 'OVER_DAILY_LIMIT', 'OVER_QUERY_LIMIT',
						                  'INVALID_REQUEST', 'MAX_ELEMENTS_EXCEEDED',
						                  'MAX_DIMENSIONS_EXCEEDED', 'UNKNOWN_ERROR' }
						if payload_status in hard_failures:
							message = payload_error or f'Google API status: {payload_status}'
							if payload_status in ('OVER_QUERY_LIMIT', 'UNKNOWN_ERROR'):
								retryable_failure = True
								raise GatewayError(
									f'Transient Google API status {payload_status}: {message}' )
							raise GatewayError( f'Google API status {payload_status}: {message}' )
					return payload
				except (requests.Timeout, requests.ConnectionError, GatewayError) as ex:
					if isinstance( ex, GatewayError ) and not retryable_failure:
						raise
					attempt += 1
					if attempt > self.retries:
						raise GatewayError( f'Exceeded retries: {ex}' ) from ex
					time.sleep( backoff )
					backoff = min( backoff * 2, self.max )
		except Exception as e:
			exception = Error( e )
			exception.module = 'Iyrin'
			exception.cause = 'Maps'
			exception.method = 'request( self, endpoint: str, params: Dict[ str, str ] )'
			Logger( ).write( exception )
			raise exception from e

class Geocoder( ):
	"""

		Purpose:
		Provide address, city/state/country, reverse, and batch geocoding with
		optional caching and a consistent flattened output shape.

		Parameters:
		maps (Maps): Maps gateway instance.
		cache (Optional[BaseCache]): Pluggable cache for memoization.

		Returns:
		Geocoder instance with forward, reverse, and batch geocoding methods.

	"""
	maps: Optional[ Map ]
	cache: Optional[ BaseCache ]
	prefix: Optional[ str ]
	data: Optional[ Dict ]
	output: Optional[ Dict ]
	parts: Optional[ Tuple ]
	city: Optional[ str ]
	address: Optional[ str ]
	state: Optional[ str ]
	country: Optional[ str ]
	comps: Optional[ Dict[ str, str ] ]
	key: Optional[ str ]
	query: Optional[ str ]
	latitude: Optional[ float ]
	longitude: Optional[ float ]
	
	def __init__( self, maps: Map, cache: Optional[ BaseCache ]=None ) -> None:
		self._maps = maps
		self._cache = cache
		self.maps = maps
		self.cache = cache
		self.prefix = None
		self.data = None
		self.output = None
		self.parts = None
		self.city = None
		self.address = None
		self.state = None
		self.country = None
		self.comps = None
		self.key = None
		self.query = None
		self.latitude = None
		self.longitude = None
	
	def key_for( self, prefix: str, *parts: str ) -> str | None:
		"""

			Purpose:
				Create a stable cache key from a namespace prefix and one or more
				string parts.

			Parameters:
				prefix (str):
					Cache namespace or operation prefix.
				*parts (str):
					Values that uniquely identify the request.

			Returns:
				str | None:
					Normalized cache key.

		"""
		try:
			throw_if( 'prefix', prefix )
			throw_if( 'parts', parts )
			self.prefix = prefix
			self.parts = parts
			joined = ' '.join( str( p ).strip( ) for p in parts if p and str( p ).strip( ) )
			return f'{prefix}::{joined}'
		except Exception as e:
			exception = Error( e )
			exception.module = 'Iyrin'
			exception.cause = 'Geocoder'
			exception.method = 'key_for( self, *kwargs )'
			raise exception
	
	def validate_coordinates( self, latitude: float, longitude: float ) -> Tuple[ float, float ]:
		"""

			Purpose:
				Validate and normalize a latitude/longitude coordinate pair.

			Parameters:
				latitude (float):
					Latitude in decimal degrees.
				longitude (float):
					Longitude in decimal degrees.

			Returns:
				Tuple[float, float]:
					Validated latitude and longitude.

		"""
		try:
			throw_if( 'latitude', latitude )
			throw_if( 'longitude', longitude )
			lat = float( latitude )
			lng = float( longitude )
			if lat < -90.0 or lat > 90.0:
				raise ValueError( 'Latitude must be between -90 and 90.' )
			if lng < -180.0 or lng > 180.0:
				raise ValueError( 'Longitude must be between -180 and 180.' )
			return lat, lng
		except Exception as e:
			exception = Error( e )
			exception.module = 'Iyrin'
			exception.cause = 'Geocoder'
			exception.method = 'validate_coordinates( self, latitude: float, longitude: float )'
			raise exception
	
	def freeform( self, address: str, country: str='US' ) -> Dict[ str, Any ] | None:
		"""

			Purpose:
				Geocode a free-form address string. Optionally bias by country code.

			Parameters:
				address (str):
					Any human-entered address string.
				country (str):
					ISO-3166 alpha-2 country code to bias results, such as 'US'
					or 'FR'. Pass an empty string to disable country bias.

			Returns:
				Dict[str, Any] | None:
					Flattened geocode result.

			Raises:
				NotFound:
					Raised when no results are returned.

		"""
		try:
			throw_if( 'address', address )
			self.address = address.strip( )
			self.country = str( country or '' ).strip( )
			self.key = self.key_for( 'geocode', self.address, self.country )
			if self._cache:
				hit = self._cache.get( self.key )
				if hit:
					return hit
			self.comps = { 'country': self.country.upper( ) } if self.country else None
			self.data = self._maps.request( 'geocode/json',
				{ 'address': self.address, **(self.comps or { }) } )
			if self.data.get( 'status' ) != 'OK' or not self.data.get( 'results' ):
				raise NotFound( f'No geocode for "{self.address}" ' )
			self.output = flatten_geocode( self.data[ 'results' ][ 0 ] )
			self.output[ 'source' ] = 'geocode'
			self.output[ 'query' ] = self.address
			if self._cache:
				self._cache.set( self.key, self.output )
			return self.output
		except Exception as e:
			exception = Error( e )
			exception.module = 'Iyrin'
			exception.cause = 'Geocoder'
			exception.method = 'freeform( self, address: str, country: str=US )'
			raise exception
	
	def reverse( self, latitude: float, longitude: float ) -> Dict[ str, Any ] | None:
		"""

			Purpose:
				Reverse geocode a latitude/longitude pair into a canonical address.

			Parameters:
				latitude (float):
					Latitude in decimal degrees.
				longitude (float):
					Longitude in decimal degrees.

			Returns:
				Dict[str, Any] | None:
					Flattened geocode result.

			Raises:
				NotFound:
					Raised when no reverse-geocode result is returned.

		"""
		try:
			self.latitude, self.longitude = self.validate_coordinates( latitude, longitude )
			self.key = self.key_for( 'reverse_geocode', str( self.latitude ),
				str( self.longitude ) )
			if self._cache:
				hit = self._cache.get( self.key )
				if hit:
					return hit
			self.data = self._maps.request( 'geocode/json',
				{ 'latlng': f'{self.latitude},{self.longitude}' } )
			if self.data.get( 'status' ) != 'OK' or not self.data.get( 'results' ):
				raise NotFound( f'No reverse geocode for "{self.latitude},{self.longitude}" ' )
			self.output = flatten_geocode( self.data[ 'results' ][ 0 ] )
			self.output[ 'source' ] = 'reverse_geocode'
			self.output[ 'query' ] = f'{self.latitude},{self.longitude}'
			if self._cache:
				self._cache.set( self.key, self.output )
			return self.output
		except Exception as e:
			exception = Error( e )
			exception.module = 'Iyrin'
			exception.cause = 'Geocoder'
			exception.method = 'reverse( self, latitude: float, longitude: float )'
			raise exception
	
	def city_state_country( self, city: str, state: str, country: str ) -> Dict[ str, Any ] | None:
		"""

			Purpose:
				Geocode a structured city/state/country triple.

			Parameters:
				city (str):
					City or locality.
				state (str):
					State, province, territory, or region. May be empty.
				country (str):
					Country name or ISO-2 country code.

			Returns:
				Dict[str, Any] | None:
					Flattened geocode result.

			Raises:
				NotFound:
					Raised when no result is available.

		"""
		try:
			throw_if( 'city', city )
			throw_if( 'country', country )
			self.city = city
			self.state = state
			self.country = country
			self.parts = tuple( [ p for p in [ self.city, self.state, self.country ] if p ] )
			self.query = ', '.join( self.parts )
			hint = (self.country.strip( ).upper( ) if self.country and len(
				self.country.strip( ) ) <= 3 else '')
			return self.freeform( self.query, hint )
		except Exception as e:
			exception = Error( e )
			exception.module = 'Iyrin'
			exception.cause = 'Geocoder'
			exception.method = 'city_state_country( self, city: str, state: str, country: str )'
			raise exception
	
	def batch_freeform( self, addresses: List[ str ], country: str='US' ) -> List[ Dict[ str, Any ] ]:
		"""

			Purpose:
				Geocode a list of free-form addresses while preserving row-level
				success and failure status.

			Parameters:
				addresses (List[str]):
					Address strings to geocode.
				country (str):
					ISO-3166 alpha-2 country code used as a default country bias.

			Returns:
				List[Dict[str, Any]]:
					List of flattened geocode results. Failed rows include
					geocode_status='error' and geocode_error.

		"""
		try:
			throw_if( 'addresses', addresses )
			if not isinstance( addresses, list ):
				raise ValueError( 'addresses must be a list of strings.' )
			results: List[ Dict[ str, Any ] ] = [ ]
			for address in addresses:
				value = str( address or '' ).strip( )
				if not value:
					results.append( { 'formatted_address': None, 'lat': None, 'lng': None, 'place_id': None,
								'types': None, 'country_code': None, 'country_name': None,
								'admin_level_1': None, 'admin_level_2': None, 'locality': None,
								'postal_code': None, 'source': 'geocode', 'query': value,
								'geocode_status': 'skipped_empty', 'geocode_error': None } )
					continue
				try:
					item = self.freeform( value, country=country ) or { }
					item[ 'geocode_status' ] = 'ok'
					item[ 'geocode_error' ] = None
					results.append( item )
				except Exception as row_error:
					results.append( { 'formatted_address': None, 'lat': None, 'lng': None, 'place_id': None,
						  'types': None, 'country_code': None, 'country_name': None,
						  'admin_level_1': None, 'admin_level_2': None, 'locality': None,
						  'postal_code': None, 'source': 'geocode', 'query': value,
						  'geocode_status': 'error', 'geocode_error': str( row_error ) } )
			return results
		except Exception as e:
			exception = Error( e )
			exception.module = 'Iyrin'
			exception.cause = 'Geocoder'
			exception.method = 'batch_freeform( self, *kwargs )'
			raise exception

class Place( ):
	"""

		Purpose:
			Use Places Text Search and Place Details to recover locations that
			Geocoding may miss. Results are returned in the same canonical shape
			used by Geocoder so both services can be used interchangeably.

		Parameters:
			maps (Maps): Maps gateway instance.
			cache (Optional[BaseCache]): Optional cache for query results.

		Returns: Places instance with text search and place-details helpers.

	"""
	map: Optional[ Map ]
	cache: Optional[ BaseCache ]
	country: Optional[ str ]
	query: Optional[ str ]
	hit: Optional[ Dict[ str, Any ] ]
	params: Optional[ Dict[ str, str ] ]
	request: Optional[ Dict[ str, str ] ]
	search: Optional[ Dict ]
	results: Optional[ List ]
	details: Optional[ Dict ]
	geometry: Optional[ Dict ]
	key: Optional[ str ]
	output: Optional[ Dict ]
	
	def __init__( self, maps: Map, cache: Optional[ BaseCache ] = None ) -> None:
		"""

			Purpose:
				Initializes Place objects given a map and optional cache

			Parameters:
				maps (Maps): Maps gateway instance.
				cache (Optional[BaseCache]): Optional cache for query results.

			Returns:
				Places instance with text search and place-details helpers.

		"""
		self.maps = maps
		self.cache = cache
		self.country = None
		self.query = None
		self.hit = None
		self.params = None
		self.request = None
		self.search = None
		self.results = None
		self.details = None
		self.geometry = None
		self.key = None
		self.output = None
	
	def key_for( self, prefix: str, *parts: str ) -> str | None:
		"""

			Purpose:
				Create a stable cache key from a namespace prefix and one or more
				string parts.

			Parameters:
				prefix (str):
					Cache namespace or operation prefix.
				*parts (str):
					Values that uniquely identify the request.

			Returns:
				str | None:
					Normalized cache key.

		"""
		try:
			throw_if( 'prefix', prefix )
			throw_if( 'parts', parts )
			joined = ' '.join( str( p ).strip( ) for p in parts if p and str( p ).strip( ) )
			return f'{prefix}::{joined}'
		except Exception as e:
			exception = Error( e )
			exception.module = 'Iyrin'
			exception.cause = 'Places'
			exception.method = 'key_for( self, *args )'
			raise exception
	
	def component_value( self, components: List[ Dict[ str, Any ] ], kind: str,
	                     want_long: bool = False ) -> Optional[ str ]:
		"""

			Purpose:
				Extract a single address component value from a Google Places or
				Geocoding address_components collection.

			Parameters:
				components (List[Dict[str, Any]]):
					Google address component dictionaries.
				kind (str):
					Component type to extract, such as country or locality.
				want_long (bool):
					When True, return long_name instead of short_name.

			Returns:
				Optional[str]:
					Component value when present; otherwise None.

		"""
		try:
			throw_if( 'components', components )
			throw_if( 'kind', kind )
			for component in components or [ ]:
				if kind in (component.get( 'types' ) or [ ]):
					if want_long:
						return component.get( 'long_name' ) or None
					return component.get( 'short_name' ) or None
			return None
		except Exception as e:
			exception = Error( e )
			exception.module = 'Iyrin'
			exception.cause = 'Places'
			exception.method = 'component_value( self, *args )'
			raise exception
	
	def flatten_place_details( self, details: Dict[ str, Any ], query: str = '' ) -> Dict[
		str, Any ]:
		"""

			Purpose:
				Convert a Place Details result into the same flattened output shape
				used by Geocoder.flatten_geocode(...).

			Parameters:
				details (Dict[str, Any]):
					Google Place Details result dictionary.
				query (str):
					Original query text, when available.

			Returns:
				Dict[str, Any]:
					Canonical location dictionary.

		"""
		try:
			throw_if( 'details', details )
			geometry = (details.get( 'geometry' ) or { }).get( 'location' ) or { }
			components = details.get( 'address_components', [ ] ) or [ ]
			return { 'formatted_address': details.get( 'formatted_address' ),
			         'lat': geometry.get( 'lat' ), 'lng': geometry.get( 'lng' ),
			         'place_id': details.get( 'place_id' ),
			         'types': ','.join( details.get( 'types', [ ] ) ) if details.get(
				         'types' ) else None,
			         'country_code': self.component_value( components, 'country' ),
			         'country_name': self.component_value( components, 'country', want_long=True ),
			         'admin_level_1': self.component_value( components,
				         'administrative_area_level_1' ),
			         'admin_level_2': self.component_value( components,
				         'administrative_area_level_2' ), 'locality': (
								self.component_value( components,
									'locality' ) or self.component_value( components,
							'postal_town' )),
			         'postal_code': self.component_value( components, 'postal_code' ),
			         'name': details.get( 'name' ),
			         'business_status': details.get( 'business_status' ),
			         'rating': details.get( 'rating' ),
			         'user_ratings_total': details.get( 'user_ratings_total' ),
			         'website': details.get( 'website' ),
			         'formatted_phone_number': details.get( 'formatted_phone_number' ),
			         'source': 'places', 'query': query }
		except Exception as e:
			exception = Error( e )
			exception.module = 'Iyrin'
			exception.cause = 'Places'
			exception.method = 'flatten_place_details( self, *args )'
			raise exception
	
	def place_details( self, place_id: str ) -> Dict[ str, Any ] | None:
		"""

			Purpose:
				Fetch and flatten details for a known Google place_id.

			Parameters:
				place_id (str):
					Google Places place identifier.

			Returns:
				Dict[str, Any] | None:
					Canonical flattened place details.

		"""
		try:
			throw_if( 'place_id', place_id )
			self.key = self.key_for( 'place_details', place_id )
			if self.cache:
				self.hit = self.cache.get( self.key )
				if self.hit:
					return self.hit
			fields = ('formatted_address,geometry,address_component,place_id,type,'
			          'name,business_status,rating,user_ratings_total,website,'
			          'formatted_phone_number')
			pyld = { 'place_id': place_id, 'fields': fields }
			self.details = self.maps.request( 'place/details/json', pyld ).get( 'result', { } )
			if not self.details:
				raise NotFound( f'No place details found for "{place_id}" ' )
			self.output = self.flatten_place_details( self.details, query=place_id )
			if self.cache:
				self.cache.set( self.key, self.output )
			return self.output
		except Exception as e:
			exception = Error( e )
			exception.module = 'Iyrin'
			exception.cause = 'Places'
			exception.method = 'place_details( self, *args )'
			raise exception
	
	def text_to_location( self, query: str, country: str = 'US' ) -> Dict[ str, Any ] | None:
		"""

			Purpose:
				Resolve a free-text query into a canonical address and coordinate
				record via Google Places Text Search and Place Details.

			Parameters:
				query (str):
					Arbitrary human-entered text such as "Newcastle, NSW, AU".
				country (str):
					ISO-2 region bias such as "AU" or "US".

			Returns:
				Dict[str, Any] | None:
					Canonical location dictionary compatible with Geocoder output.

			Raises:
				NotFound:
					Raised when no candidate is returned.

		"""
		try:
			throw_if( 'query', query )
			self.query = query.strip( )
			self.country = str( country or '' ).strip( )
			self.key = self.key_for( 'places', self.query, self.country.upper( ) )
			if self.cache:
				self.hit = self.cache.get( self.key )
				if self.hit:
					return self.hit
			self.params = { 'query': self.query }
			if self.country:
				self.params[ 'region' ] = self.country.upper( )
			self.search = self.maps.request( 'place/textsearch/json', self.params )
			self.results = self.search.get( 'results' ) or [ ]
			if not self.results:
				raise NotFound( f'No places match for "{self.query}" ' )
			top = self.results[ 0 ]
			place_id = top.get( 'place_id' )
			if not place_id:
				raise NotFound( 'Top place had no place_id' )
			fields = ('formatted_address,geometry,address_component,place_id,type,'
			          'name,business_status,rating,user_ratings_total,website,'
			          'formatted_phone_number')
			_payload = { 'place_id': place_id, 'fields': fields }
			self.details = self.maps.request( 'place/details/json', _payload ).get( 'result', { } )
			if not self.details:
				raise NotFound( f'No place details found for "{self.query}" ' )
			self.output = self.flatten_place_details( self.details, query=self.query )
			if self.cache:
				self.cache.set( self.key, self.output )
			return self.output
		except Exception as e:
			exception = Error( e )
			exception.module = 'Iyrin'
			exception.cause = 'Places'
			exception.method = 'text_to_location( self, *args )'
			raise exception
	
	def search_candidates( self, query: str, country: str = 'US', lmt: int = 5 ) -> List[
		Dict[ str, Any ] ]:
		"""

			Purpose:
				Return multiple Places Text Search candidates for a query. This is
				intended for future UI candidate-selection workflows.

			Parameters:
				query (str):
					Free-text search query.
				country (str):
					ISO-2 region bias.
				lmt (int):
					Maximum candidates to return.

			Returns:
				List[Dict[str, Any]]:
					Raw candidate dictionaries returned by Text Search.

		"""
		try:
			throw_if( 'query', query )
			self.query = query.strip( )
			self.country = str( country or '' ).strip( )
			self.params = { 'query': self.query }
			if self.country:
				self.params[ 'region' ] = self.country.upper( )
			self.search = self.maps.request( 'place/textsearch/json', self.params )
			self.results = self.search.get( 'results' ) or [ ]
			if not self.results:
				raise NotFound( f'No places match for "{self.query}" ' )
			return self.results[ :max( 1, int( lmt ) ) ]
		except Exception as e:
			exception = Error( e )
			exception.module = 'Iyrin'
			exception.cause = 'Places'
			exception.method = 'search_candidates( self, *args )'
			raise exception

class Timezone:
	"""

		Purpose:
			Wrap Google Time Zone API for coordinate lookups, full payload retrieval,
			UTC offset extraction, local-time conversion, and batch enrichment.

		The instance exposes get_id, lookup, offset_hours, local_time, and batch_lookup.

	"""
	timestamp: Optional[ int ]
	maps: Optional[ Map ]
	latitude: Optional[ float ]
	longitude: Optional[ float ]
	data: Optional[ Dict ]
	offset: Optional[ float ]
	local: Optional[ str ]
	rows: Optional[ list ]
	lat_field: Optional[ str ]
	lng_field: Optional[ str ]
	utc_datetime: Optional[ dt.datetime ]
	
	def __init__( self, maps: Map ) -> None:
		self.maps = maps
		self.timestamp = None
		self.latitude = None
		self.longitude = None
		self.data = None
		self.offset = None
		self.local = None
		self.rows = None
		self.lat_field = None
		self.lng_field = None
		self.utc_datetime = None
	
	def validate_coordinates( self, lat: float, lng: float ) -> tuple:
		"""

			Purpose:
				Validate and normalize a latitude and longitude pair.

			Parameters:
				lat (float):
					Latitude in decimal degrees.

				lng (float):
					Longitude in decimal degrees.

			Returns:
				tuple:
					Validated latitude and longitude.

		"""
		try:
			throw_if( 'lat', lat )
			throw_if( 'lng', lng )
			latitude = float( lat )
			longitude = float( lng )
			if latitude < -90.0 or latitude > 90.0:
				raise ValueError( 'Latitude must be between -90 and 90.' )
			if longitude < -180.0 or longitude > 180.0:
				raise ValueError( 'Longitude must be between -180 and 180.' )
			self.latitude = latitude
			self.longitude = longitude
			return self.latitude, self.longitude
		
		except Exception as e:
			exception = Error( e )
			exception.module = 'Iyrin'
			exception.cause = 'Timezone'
			exception.method = 'validate_coordinates( self, lat: float, lng: float )'
			raise exception
	
	def lookup( self, lat: float, lng: float ) -> Dict | None:
		"""

			Purpose:
				Fetch the full Google Time Zone API response for a coordinate.

			Parameters:
				lat (float):
					Latitude.

				lng (float):
					Longitude.

			Returns:
				Dict | None:
					Full time zone response payload, including timeZoneId, timeZoneName,
					rawOffset, dstOffset, and status when available.

		"""
		try:
			latitude, longitude = self.validate_coordinates( lat, lng )
			timestamp_value = int( time.time( ) )
			self.latitude = latitude
			self.longitude = longitude
			self.timestamp = timestamp_value
			self.data = self.maps.request( 'timezone/json', { 'location': f'{self.latitude},{self.longitude}',
						'timestamp': str( self.timestamp ) } )
			return self.data
		
		except Exception as e:
			exception = Error( e )
			exception.module = 'Iyrin'
			exception.cause = 'Timezone'
			exception.method = 'lookup( self, lat: float, lng: float )'
			raise exception
	
	def get_id( self, lat: float, lng: float ) -> Optional[ str ]:
		"""

			Purpose:
				Fetch the IANA time zone id for a coordinate.

			Parameters:
				lat (float):
					Latitude.

				lng (float):
					Longitude.

			Returns:
				Optional[str]:
					Time zone id string or None if unavailable.

		"""
		try:
			self.data = self.lookup( lat, lng )
			if not isinstance( self.data, dict ):
				return None
			return self.data.get( 'timeZoneId' )
		
		except Exception as e:
			exception = Error( e )
			exception.module = 'Iyrin'
			exception.cause = 'Timezone'
			exception.method = 'get_id( self, lat: float, lng: float )'
			raise exception
	
	def offset_hours( self, lat: float, lng: float ) -> Optional[ float ]:
		"""

			Purpose:
				Fetch the total UTC offset in hours for a coordinate.

			Parameters:
				lat (float):
					Latitude.

				lng (float):
					Longitude.

			Returns:
				Optional[float]:
					Total UTC offset in hours, including daylight-saving offset
					when returned by the API.

		"""
		try:
			self.data = self.lookup( lat, lng )
			if not isinstance( self.data, dict ):
				return None
			raw_offset = self.data.get( 'rawOffset', 0 ) or 0
			dst_offset = self.data.get( 'dstOffset', 0 ) or 0
			offset_value = round( (float( raw_offset ) + float( dst_offset )) / 3600.0, 3 )
			self.offset = offset_value
			return self.offset
		
		except Exception as e:
			exception = Error( e )
			exception.module = 'Iyrin'
			exception.cause = 'Timezone'
			exception.method = 'offset_hours( self, lat: float, lng: float )'
			raise exception
	
	def local_time( self, lat: float, lng: float,
	                utc_datetime: Optional[ dt.datetime ]=None ) -> Dict | None:
		"""

			Purpose:
				Convert a UTC datetime into local time at a coordinate using the
				Google Time Zone API rawOffset and dstOffset fields.

			Parameters:
				lat (float):
					Latitude.

				lng (float):
					Longitude.

				utc_datetime (Optional[dt.datetime]):
					Optional UTC datetime. If None, the current UTC time is used.

			Returns:
				Dict | None:
					Dictionary containing timezone metadata, UTC time, local time,
					and total offset hours.

		"""
		try:
			self.data = self.lookup( lat, lng )
			if not isinstance( self.data, dict ):
				return None
			if utc_datetime is None:
				utc_value = dt.datetime.now( dt.timezone.utc )
			else:
				utc_value = utc_datetime
				if utc_value.tzinfo is None:
					utc_value = utc_value.replace( tzinfo=dt.timezone.utc )
				else:
					utc_value = utc_value.astimezone( dt.timezone.utc )
			raw_offset = self.data.get( 'rawOffset', 0 ) or 0
			dst_offset = self.data.get( 'dstOffset', 0 ) or 0
			total_seconds = float( raw_offset ) + float( dst_offset )
			local_value = utc_value + dt.timedelta( seconds=total_seconds )
			offset_value = round( total_seconds / 3600.0, 3 )
			self.utc_datetime = utc_value
			self.offset = offset_value
			self.local = local_value.isoformat( )
			return { 'timeZoneId': self.data.get( 'timeZoneId' ),
					'timeZoneName': self.data.get( 'timeZoneName' ),
					'status': self.data.get( 'status' ), 'rawOffset': raw_offset,
					'dstOffset': dst_offset, 'offset_hours': self.offset,
					'utc_time': self.utc_datetime.isoformat( ), 'local_time': self.local,
					'lat': self.latitude, 'lng': self.longitude }
		
		except Exception as e:
			exception = Error( e )
			exception.module = 'Iyrin'
			exception.cause = 'Timezone'
			exception.method = 'local_time( self, lat: float, lng: float, utc_datetime: Optional[ dt.datetime ]=None )'
			raise exception
	
	def batch_lookup( self, rows: list, lat_field: str = 'lat', lng_field: str = 'lng' ) -> list:
		"""

			Purpose:
				Enrich a list of row dictionaries with Google Time Zone API fields.

			Parameters:
				rows (list):
					List of dictionaries containing latitude and longitude fields.

				lat_field (str):
					Latitude field name.

				lng_field (str):
					Longitude field name.

			Returns:
				list:
					List of copied row dictionaries with timezone fields appended.

		"""
		try:
			throw_if( 'rows', rows )
			if not isinstance( rows, list ):
				raise ValueError( 'rows must be a list of dictionaries.' )
			lat_field_value = lat_field or 'lat'
			lng_field_value = lng_field or 'lng'
			self.rows = rows
			self.lat_field = lat_field_value
			self.lng_field = lng_field_value
			output = [ ]
			for row in self.rows:
				item = dict( row or { } )
				try:
					lat_value = item.get( self.lat_field )
					lng_value = item.get( self.lng_field )
					data = self.lookup( lat_value, lng_value )
					if not isinstance( data, dict ):
						item[ 'timeZoneId' ] = None
						item[ 'timeZoneName' ] = None
						item[ 'rawOffset' ] = None
						item[ 'dstOffset' ] = None
						item[ 'offset_hours' ] = None
						item[ 'timezone_status' ] = 'not_found'
						item[ 'timezone_error' ] = 'No timezone response returned.'
					
					else:
						raw_offset = data.get( 'rawOffset', 0 ) or 0
						dst_offset = data.get( 'dstOffset', 0 ) or 0
						offset_value = round( (float( raw_offset ) + float( dst_offset )) / 3600.0,
							3 )
						self.offset = offset_value
						item[ 'timeZoneId' ] = data.get( 'timeZoneId' )
						item[ 'timeZoneName' ] = data.get( 'timeZoneName' )
						item[ 'rawOffset' ] = raw_offset
						item[ 'dstOffset' ] = dst_offset
						item[ 'offset_hours' ] = self.offset
						item[ 'timezone_status' ] = data.get( 'status', 'OK' )
						item[ 'timezone_error' ] = None
				
				except Exception as row_error:
					item[ 'timeZoneId' ] = None
					item[ 'timeZoneName' ] = None
					item[ 'rawOffset' ] = None
					item[ 'dstOffset' ] = None
					item[ 'offset_hours' ] = None
					item[ 'timezone_status' ] = 'error'
					item[ 'timezone_error' ] = str( row_error )
				output.append( item )
			return output
		
		except Exception as e:
			exception = Error( e )
			exception.module = 'Iyrin'
			exception.cause = 'Timezone'
			exception.method = 'batch_lookup( self, rows: list, lat_field: str=lat, lng_field: str=lng )'
			raise exception