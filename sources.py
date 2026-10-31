'''
	******************************************************************************************
	 Assembly:                iyrin
	 Filename:                sources.py
	 Author:                  Terry D. Eppler
	 Created:                 09-12-2026
	
	 Last Modified By:        Terry D. Eppler
	 Last Modified On:        09-12-2026
	******************************************************************************************
	
	Purpose:
	    Provider clients used by Iyr Live World Data for real-time aircraft state vectors,
	    military aircraft, maritime AIS positions, current satellite orbital elements, public
	    infrastructure, and public camera features.
	    OpenSky access uses the current OAuth2 client-credentials flow when API-client
	    credentials are available. ADSB.lol provides public military-tagged aircraft data.
	    AIS Stream provides server-side WebSocket maritime position events. CelesTrak data is
	    requested in OMM JSON format and propagated with SGP4 before conversion to Earth-fixed
	    coordinates.
	******************************************************************************************
'''

from __future__ import annotations
from boogr import Error, Logger
import datetime as dt
import json
import math
import time
from typing import Any, Dict, List
import requests
from astropy import units as u
from astropy.coordinates import CartesianRepresentation, EarthLocation, ITRS, TEME
from astropy.time import Time
from requests import Response
from sgp4 import omm
from sgp4.api import Satrec
from websocket import WebSocket, WebSocketTimeoutException, create_connection


def throw_if( name: str, value: object ) -> None:
	'''

		Purpose:
		--------
		Validate a required runtime argument.

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

class OpenSkyLive( ):
	'''

		Purpose:
		--------
		Retrieve current OpenSky state vectors for a geographic bounding box.

	'''
	client_id: str
	client_secret: str
	timeout: int
	token_url: str
	states_url: str
	access_token: str
	response: Response | None

	def __init__( self, client_id: str='', client_secret: str='', timeout: int=20 ) -> None:
		'''

			Purpose:
			--------
			Initialize OpenSky REST API access. Credentials are optional because OpenSky can
			serve anonymous requests subject to the provider's current access limits.

			Parameters:
			-----------
			client_id (str): OpenSky API Client identifier.
			client_secret (str): OpenSky API Client secret.
			timeout (int): HTTP timeout in seconds.

			Returns:
			--------
			None

		'''
		self.client_id = client_id
		self.client_secret = client_secret
		self.timeout = timeout
		self.token_url = ( 'https://auth.opensky-network.org/auth/realms/opensky-network/'
			'protocol/openid-connect/token' )
		self.states_url = 'https://opensky-network.org/api/states/all'
		self.access_token = ''
		self.response = None

	def get_access_token( self ) -> str:
		'''

			Purpose:
			--------
			Obtain an OpenSky OAuth2 access token using the configured API Client.

			Returns:
			--------
			str: Bearer access token, or an empty string when credentials were not supplied.

		'''
		if not self.client_id or not self.client_secret:
			return ''

		data = { 'grant_type': 'client_credentials', 'client_id': self.client_id,
			'client_secret': self.client_secret, }
		self.response = requests.post( self.token_url, data=data, timeout=self.timeout )
		self.response.raise_for_status( )
		payload = self.response.json( ) or { }
		self.access_token = str( payload.get( 'access_token', '' ) or '' )
		throw_if( 'access_token', self.access_token )
		return self.access_token

	def fetch_states( self, latitude: float, longitude: float,
			radius_degrees: float=2.0 ) -> Dict[ str, Any ]:
		'''

			Purpose:
			--------
			Retrieve live aircraft state vectors within a geographic bounding box centered
			on the supplied latitude and longitude.

			Parameters:
			-----------
			latitude (float): Bounding-box center latitude.
			longitude (float): Bounding-box center longitude.
			radius_degrees (float): Decimal-degree half-width of the bounding box.

			Returns:
			--------
			Dict[str, Any]: OpenSky state-vector payload.

		'''
		throw_if( 'latitude', latitude )
		throw_if( 'longitude', longitude )
		throw_if( 'radius_degrees', radius_degrees )
		try:
			self.latitude = float( latitude )
			self.longitude = float( longitude )
			self.radius_degrees = float( radius_degrees )
			self.lamin = max( -90.0, self.latitude - self.radius_degrees )
			self.lamax = min( 90.0, self.latitude + self.radius_degrees )
			self.lomin = max( -180.0, self.longitude - self.radius_degrees )
			self.lomax = min( 180.0, self.longitude + self.radius_degrees )
			self.params = {
				'lamin': self.lamin,
				'lomin': self.lomin,
				'lamax': self.lamax,
				'lomax': self.lomax,
			}
			self.headers: Dict[ str, str ] = { }
			self.access_token = self.get_access_token( )
			if self.access_token:
				self.headers[ 'Authorization' ] = f'Bearer {self.access_token}'
	
			self.response = requests.get( self.states_url, params=self.params,
				headers=self.headers, timeout=self.timeout )
			self.response.raise_for_status( )
			return self.response.json( ) or { }
		except Exception as e:
			exception = Error( e )
			exception.module = 'mappy'
			exception.cause = 'StaticMap'
			exception.method = 'bbox( self, west: float, south: float, east: float, north: float )'
			Logger.write( exception )
			raise exception


class AdsbLolMilitary( ):
	'''

		Purpose:
		--------
		Retrieve aircraft currently tagged as military by ADSB.lol.

	'''
	timeout: int
	url: str
	response: Response | None

	def __init__( self, timeout: int=20 ) -> None:
		'''

			Purpose:
			--------
			Initialize ADSB.lol military-aircraft access.

			Parameters:
			-----------
			timeout (int): HTTP timeout in seconds.

			Returns:
			--------
			None

		'''
		self.timeout = timeout
		self.url = 'https://api.adsb.lol/v2/point'
		self.response = None

	def fetch_military( self, latitude: float, longitude: float,
			radius_nm: float=250.0 ) -> Dict[ str, Any ]:
		'''

			Purpose:
			--------
			Retrieve ADSB.lol aircraft around a geographic point and retain records
			whose database flags identify them as military aircraft.

			Parameters:
			-----------
			latitude (float): Geographic center latitude.
			longitude (float): Geographic center longitude.
			radius_nm (float): Search radius in nautical miles.

			Returns:
			--------
			Dict[str, Any]: ADSB.lol payload containing only military-tagged aircraft.

		'''
		throw_if( 'latitude', latitude )
		throw_if( 'longitude', longitude )
		throw_if( 'radius_nm', radius_nm )
		try:
			self.latitude = float( latitude )
			self.longitude = float( longitude )
			self.radius_nm = float( radius_nm )
			self.request_url = (
				f'{self.url}/{self.latitude:.6f}/{self.longitude:.6f}/{self.radius_nm:.1f}' )
			self.response = requests.get( self.request_url, timeout=self.timeout )
			self.response.raise_for_status( )
			payload = self.response.json( ) or { }
			if not isinstance( payload, dict ):
				raise TypeError( 'ADSB.lol point response must be a dictionary.' )
			aircraft = payload.get( 'ac', [ ] ) or [ ]
			payload[ 'ac' ] = [ row for row in aircraft
				if isinstance( row, dict ) and int( row.get( 'dbFlags', 0 ) or 0 ) & 1 ]
			return payload
		except Exception as e:
			exception = Error( e )
			exception.module = 'source'
			exception.cause = 'SAdsbLolMilitary'
			exception.method = 'fetch_militar( self, **args ) -> Dict[ str, Any ]'
			Logger.write( exception )
			raise exception

class AisStreamLive( ):
	'''

		Purpose:
		--------
		Retrieve live maritime AIS position reports through the AIS Stream WebSocket API.

	'''
	api_key: str
	timeout: int
	url: str
	socket: WebSocket | None
	max_retries: int
	retry_delay: float

	def __init__( self, api_key: str, timeout: int=5, max_retries: int=2,
			retry_delay: float=0.5 ) -> None:
		'''

			Purpose:
			--------
			Initialize AIS Stream server-side WebSocket access with bounded reconnect behavior.

			Parameters:
			-----------
			api_key (str): AIS Stream API key.
			timeout (int): WebSocket connection and receive timeout in seconds.
			max_retries (int): Maximum reconnect attempts after the initial connection.
			retry_delay (float): Initial reconnect delay in seconds.

			Returns:
			--------
			None

		'''
		self.api_key = api_key
		self.timeout = int( timeout )
		self.max_retries = int( max_retries )
		self.retry_delay = float( retry_delay )
		if self.timeout < 1:
			raise ValueError( 'Argument "timeout" must be greater than zero.' )
		if self.max_retries < 0:
			raise ValueError( 'Argument "max_retries" cannot be negative.' )
		if self.retry_delay < 0.0:
			raise ValueError( 'Argument "retry_delay" cannot be negative.' )
		self.url = 'wss://stream.aisstream.io/v0/stream'
		self.socket = None

	def fetch_positions( self, latitude: float, longitude: float,
			radius_degrees: float=2.0, max_messages: int=100,
			duration_seconds: float=3.0 ) -> List[ Dict[ str, Any ] ]:
		'''

			Purpose:
			--------
			Collect a bounded sample of live AIS vessel position messages around a geographic
			center point while reconnecting after transient WebSocket failures.

			Parameters:
			-----------
			latitude (float): Bounding-box center latitude.
			longitude (float): Bounding-box center longitude.
			radius_degrees (float): Decimal-degree half-width of the bounding box.
			max_messages (int): Maximum matching AIS messages returned.
			duration_seconds (float): Maximum total receive window in seconds.

			Returns:
			--------
			List[Dict[str, Any]]: AIS Stream message envelopes containing vessel positions.

		'''
		throw_if( 'latitude', latitude )
		throw_if( 'longitude', longitude )
		throw_if( 'radius_degrees', radius_degrees )
		throw_if( 'max_messages', max_messages )
		throw_if( 'duration_seconds', duration_seconds )
		try:
			self.latitude = float( latitude )
			self.longitude = float( longitude )
			self.radius_degrees = float( radius_degrees )
			self.max_messages = int( max_messages )
			self.duration_seconds = float( duration_seconds )
			self.north = min( 90.0, self.latitude + self.radius_degrees )
			self.south = max( -90.0, self.latitude - self.radius_degrees )
			self.west = max( -180.0, self.longitude - self.radius_degrees )
			self.east = min( 180.0, self.longitude + self.radius_degrees )
			self.subscription = { 'APIKey': self.api_key,
				'BoundingBoxes': [ [ [ self.north, self.west ], [ self.south, self.east ] ] ],
				'FilterMessageTypes': [
					'PositionReport',
					'StandardClassBPositionReport',
					'ExtendedClassBPositionReport',
					'LongRangeAisBroadcastMessage', ], }
			messages: List[ Dict[ str, Any ] ] = [ ]
			started = time.monotonic( )
			last_error = ''
			for attempt in range( self.max_retries + 1 ):
				remaining_window = self.duration_seconds - (time.monotonic( ) - started)
				if remaining_window <= 0.0:
					break
	
				try:
					self.socket = create_connection( self.url, timeout=self.timeout )
					self.socket.send( json.dumps( self.subscription ) )
					while len( messages ) < self.max_messages:
						remaining = self.duration_seconds - (time.monotonic( ) - started)
						if remaining <= 0.0:
							return messages
	
						self.socket.settimeout( min( 1.0, max( 0.1, remaining ) ) )
						try:
							frame = self.socket.recv( )
						except WebSocketTimeoutException:
							continue
	
						if frame is None or frame == '':
							raise ConnectionError( 'AIS Stream closed the WebSocket connection.' )
						if isinstance( frame, bytes ):
							frame = frame.decode( 'utf-8' )
						try:
							payload = json.loads( frame )
						except json.JSONDecodeError:
							continue
						if not isinstance( payload, dict ):
							continue
						provider_error = str( payload.get( 'Error', payload.get( 'error', '' ) ) or '' )
						if provider_error:
							raise RuntimeError( f'Rejected the subscription: {provider_error}' )
						if payload.get( 'MessageType' ) == 'SubscriptionConfirmation':
							continue
						metadata = payload.get( 'MetaData', { } ) or { }
						if metadata.get( 'Latitude' ) is None or metadata.get( 'Longitude' ) is None:
							continue
						messages.append( payload )
					return messages
	
				except Exception as ex:
					last_error = str( ex )
				finally:
					if self.socket is not None:
						try:
							self.socket.close( )
						except Exception:
							pass
						self.socket = None
	
				if attempt < self.max_retries:
					remaining = self.duration_seconds - (time.monotonic( ) - started)
					if remaining <= 0.0:
						break
					delay = min( self.retry_delay * (2 ** attempt), remaining )
					if delay > 0.0:
						time.sleep( delay )
	
			if messages:
				return messages
			if last_error:
				_alert = f'Failed after {self.max_retries + 1} connection attempts: {last_error}'
				raise RuntimeError( _alert )
			return messages
		except Exception as e:
			exception = Error( e )
			exception.module = 'sources'
			exception.cause = 'AisStreamLive'
			exception.method = 'fetch_positions( self, **args ) -> Dict[ str, Any ]'
			Logger.write( exception )
			raise exception


class CelesTrakLive( ):
	'''

		Purpose:
		--------
		Retrieve current CelesTrak OMM records and propagate them to current Earth-fixed
		latitude, longitude, and altitude values using SGP4.

	'''
	timeout: int
	url: str
	response: Response | None

	def __init__( self, timeout: int=20 ) -> None:
		'''

			Purpose:
			--------
			Initialize current CelesTrak GP-data access.

			Parameters:
			-----------
			timeout (int): HTTP timeout in seconds.

			Returns:
			--------
			None

		'''
		self.timeout = timeout
		self.url = 'https://celestrak.org/NORAD/elements/gp.php'
		self.response = None

	def fetch_group( self, group: str, limit: int=250 ) -> List[ Dict[ str, Any ] ]:
		'''

			Purpose:
			--------
			Retrieve current general-perturbation records for one CelesTrak satellite group
			in OMM JSON format.

			Parameters:
			-----------
			group (str): CelesTrak group identifier such as stations, visual, weather,
				gps-ops, or active.
			limit (int): Maximum records returned to the caller.

			Returns:
			--------
			List[Dict[str, Any]]: OMM records.

		'''
		throw_if( 'group', group )
		try:
			self.group = group
			self.limit = int( limit )
			self.params = { 'GROUP': self.group, 'FORMAT': 'JSON' }
			self.response = requests.get( self.url, params=self.params, timeout=self.timeout )
			self.response.raise_for_status( )
			payload = self.response.json( ) or [ ]
			if not isinstance( payload, list ):
				raise TypeError( 'CelesTrak GP JSON response must be a list.' )
			return payload[ :self.limit ]
		except Exception as e:
			exception = Error( e )
			exception.module = 'sources'
			exception.cause = 'CelesTrakLive'
			exception.method = 'fetch_group( self, **args ) -> Dict[ str, Any ]'
			Logger.write( exception )
			raise exception

	def propagate( self, record: Dict[ str, Any ], when: dt.datetime ) -> Dict[ str, Any ]:
		'''

			Purpose:
			--------
			Propagate one OMM record to the requested UTC time and transform its TEME
			position into Earth-fixed geodetic coordinates.

			Parameters:
			-----------
			record (Dict[str, Any]): CelesTrak OMM record.
			when (datetime): UTC propagation time.

			Returns:
			--------
			Dict[str, Any]: Propagated latitude, longitude, altitude, velocity, and identity.

		'''
		throw_if( 'record', record )
		throw_if( 'when', when )
		try:
			self.record = record
			self.when = when
			self.satellite = Satrec( )
			omm.initialize( self.satellite, self.record )
			self.obstime = Time( self.when )
			error, position, velocity = self.satellite.sgp4( self.obstime.jd1, self.obstime.jd2 )
			if error != 0:
				raise RuntimeError( f'SGP4 propagation failed with error code {error}.' )
	
			self.teme = TEME( CartesianRepresentation( position[ 0 ] * u.km, position[ 1 ] * u.km,
					position[ 2 ] * u.km ), obstime=self.obstime )
			self.itrs = self.teme.transform_to( ITRS( obstime=self.obstime ) )
			self.location = EarthLocation.from_geocentric( self.itrs.cartesian.x,
				self.itrs.cartesian.y, self.itrs.cartesian.z )
			self.speed = math.sqrt( float( velocity[ 0 ] ) ** 2 + float( velocity[ 1 ] ) ** 2
				+ float( velocity[ 2 ] ) ** 2 )
	
			return { 'Name': str( self.record.get( 'OBJECT_NAME', '' ) or '' ),
				'CatalogNumber': str( self.record.get( 'NORAD_CAT_ID', '' ) or '' ),
				'ObjectId': str( self.record.get( 'OBJECT_ID', '' ) or '' ),
				'Latitude': float( self.location.lat.deg ),
				'Longitude': float( self.location.lon.deg ),
				'Altitude': float( self.location.height.to( u.km ).value ),
				'Velocity': float( self.speed ),
				'Epoch': str( self.record.get( 'EPOCH', '' ) or '' ),
				'Classification': str( self.record.get( 'CLASSIFICATION_TYPE', '' ) or '' ), }
		except Exception as e:
			exception = Error( e )
			exception.module = 'sources'
			exception.cause = 'CelesTrakLive'
			exception.method = 'propagate( self, **args ) -> Dict[ str, Any ]'
			Logger.write( exception )
			raise exception


class OverpassClient( ):
	'''

		Purpose:
		--------
		Provide shared resilient HTTP transport for Iyr OpenStreetMap Overpass providers.

	'''
	timeout: int
	retries: int
	retry_delay: float
	url: str
	endpoints: List[ str ]
	headers: Dict[ str, str ]
	response: Response | None

	def __init__( self, timeout: int=30, retries: int=2, retry_delay: float=0.75 ) -> None:
		'''

			Purpose:
			--------
			Initialize shared Overpass request identity, endpoints, and retry policy.

			Parameters:
			-----------
			timeout (int): HTTP timeout in seconds.
			retries (int): Retries per endpoint for transient provider responses.
			retry_delay (float): Initial exponential-backoff delay in seconds.

			Returns:
			--------
			None

		'''
		self.timeout = int( timeout )
		self.retries = int( retries )
		self.retry_delay = float( retry_delay )
		if self.timeout < 1:
			raise ValueError( 'Argument "timeout" must be greater than zero.' )
		if self.retries < 0:
			raise ValueError( 'Argument "retries" cannot be negative.' )
		if self.retry_delay < 0.0:
			raise ValueError( 'Argument "retry_delay" cannot be negative.' )
		self.endpoints = [ 'https://overpass-api.de/api/interpreter',
			'https://overpass.kumi.systems/api/interpreter', ]
		self.url = self.endpoints[ 0 ]
		self.headers = { 'User-Agent': 'Iyrin/1.0 (+https://github.com/is-leeroy-jenkins/iyr)',
			'Accept': 'application/json', 'Content-Type': 'application/x-www-form-urlencoded', }
		self.response = None

	def execute( self, query: str ) -> Dict[ str, Any ]:
		'''

			Purpose:
			--------
			Execute one Overpass query with request identification, bounded retry, and
			alternate-endpoint fallback.

			Parameters:
			-----------
			query (str): Overpass QL query.

			Returns:
			--------
			Dict[str, Any]: Decoded Overpass JSON response.

		'''
		throw_if( 'query', query )
		try:
			transient_statuses = { 406, 429, 500, 502, 503, 504 }
			errors: List[ str ] = [ ]
			for endpoint in self.endpoints:
				for attempt in range( self.retries + 1 ):
					try:
						self.url = endpoint
						self.response = None
						self.response = requests.post( self.url, data={ 'data': query }, headers=self.headers,
							timeout=self.timeout )
						status_code = int( self.response.status_code )
						if status_code in transient_statuses and attempt < self.retries:
							delay = self.retry_delay * (2 ** attempt)
							if delay > 0.0:
								time.sleep( delay )
							continue
						self.response.raise_for_status( )
						payload = self.response.json( ) or { }
						if not isinstance( payload, dict ):
							raise TypeError( 'Overpass response must be a dictionary.' )
						return payload
	
					except ( requests.RequestException, TypeError, ValueError ) as ex:
						errors.append( f'{endpoint}: {ex}' )
						status_code = int( self.response.status_code ) if self.response is not None else 0
						if status_code and status_code not in transient_statuses:
							break
						if attempt < self.retries:
							delay = self.retry_delay * (2 ** attempt)
							if delay > 0.0:
								time.sleep( delay )
	
			detail = ' | '.join( errors[ -6: ] )
			raise RuntimeError( f'Overpass request failed across configured endpoints: {detail}' )
		except Exception as e:
			exception = Error( e )
			exception.module = 'sources'
			exception.cause = 'OverpassClient'
			exception.method = 'execute( self, **args ) -> None'
			Logger.write( exception )
			raise exception

class OverpassInfrastructure( OverpassClient ):
	'''

		Purpose:
		--------
		Retrieve nearby public infrastructure features from OpenStreetMap through the
		Overpass API using explicit infrastructure categories.

	'''
	timeout: int
	url: str
	response: Response | None
	category_filters: Dict[ str, List[ str ] ]

	def __init__( self, timeout: int=30 ) -> None:
		'''

			Purpose:
			--------
			Initialize OpenStreetMap Overpass infrastructure access.

			Parameters:
			-----------
			timeout (int): HTTP timeout in seconds.

			Returns:
			--------
			None

		'''
		super( ).__init__( timeout=timeout )
		self.category_filters = { 'Airports': [ '["aeroway"="aerodrome"]', '["aeroway"="heliport"]' ],
			'Ports': [ '["harbour"="yes"]', '["amenity"="ferry_terminal"]' ],
			'Power Plants': [ '["power"="plant"]' ],
			'Dams': [ '["waterway"="dam"]' ],
			'Data Centers': [ '["telecom"="data_center"]', '["building"="data_center"]' ],
			'Military Installations': [ '["landuse"="military"]', '["military"]' ], }

	def fetch_infrastructure( self, latitude: float, longitude: float,
			radius_km: float, categories: List[ str ], max_results: int ) -> Dict[ str, Any ]:
		'''

			Purpose:
			--------
			Retrieve tagged OpenStreetMap infrastructure within a circular search radius.

			Parameters:
			-----------
			latitude (float): Search-origin latitude.
			longitude (float): Search-origin longitude.
			radius_km (float): Search radius in kilometers.
			categories (List[str]): Infrastructure categories to retrieve.
			max_results (int): Maximum normalized Overpass elements to return.

			Returns:
			--------
			Dict[str, Any]: Overpass elements with an added InfrastructureCategory field.

		'''
		throw_if( 'latitude', latitude )
		throw_if( 'longitude', longitude )
		throw_if( 'radius_km', radius_km )
		throw_if( 'categories', categories )
		throw_if( 'max_results', max_results )
		try:
			self.latitude = float( latitude )
			self.longitude = float( longitude )
			self.radius_km = float( radius_km )
			self.categories = list( categories )
			self.max_results = int( max_results )
			if self.latitude < -90.0 or self.latitude > 90.0:
				raise ValueError( 'Argument "latitude" must be between -90 and 90.' )
			if self.longitude < -180.0 or self.longitude > 180.0:
				raise ValueError( 'Argument "longitude" must be between -180 and 180.' )
			if self.radius_km <= 0.0:
				raise ValueError( 'Argument "radius_km" must be greater than zero.' )
			if self.max_results < 1:
				raise ValueError( 'Argument "max_results" must be greater than zero.' )
			for category in self.categories:
				if category not in self.category_filters:
					raise ValueError( f'Unsupported infrastructure category: {category}' )
	
			radius_meters = int( self.radius_km * 1000.0 )
			selectors: List[ str ] = [ ]
			for category in self.categories:
				for tag_filter in self.category_filters[ category ]:
					selectors.append(
						f'nwr(around:{radius_meters},{self.latitude:.6f},{self.longitude:.6f})'
						f'{tag_filter};' )
			query = '[out:json][timeout:25];(' + ''.join( selectors ) + ');out center tags qt;'
			payload = self.execute( query )
			if not isinstance( payload, dict ):
				raise TypeError( 'Overpass response must be a dictionary.' )
			elements = payload.get( 'elements', [ ] ) or [ ]
			if not isinstance( elements, list ):
				raise TypeError( 'Overpass elements must be a list.' )
	
			rows: List[ Dict[ str, Any ] ] = [ ]
			seen: set[ str ] = set( )
			for element in elements:
				if not isinstance( element, dict ):
					continue
				tags = element.get( 'tags', { } ) or { }
				category = self.classify_infrastructure( tags )
				if not category or category not in self.categories:
					continue
				entity_key = f'{element.get( "type", "" )}:{element.get( "id", "" )}'
				if entity_key in seen:
					continue
				seen.add( entity_key )
				row = dict( element )
				row[ 'InfrastructureCategory' ] = category
				rows.append( row )
				if len( rows ) >= self.max_results:
					break
			payload[ 'elements' ] = rows
			return payload
		except Exception as e:
			exception = Error( e )
			exception.module = 'sources'
			exception.cause = 'OverpassInfrastructure'
			exception.method = 'fetch_infrastructure( self, **args ) -> Dict[ str, Any ]'
			Logger.write( exception )
			raise exception

	def classify_infrastructure( self, tags: Dict[ str, Any ] ) -> str:
		'''

			Purpose:
			--------
			Classify one OpenStreetMap tag collection into a supported infrastructure category.

			Parameters:
			-----------
			tags (Dict[str, Any]): OpenStreetMap feature tags.

			Returns:
			--------
			str: Infrastructure category, or an empty string when unsupported.

		'''
		throw_if( 'tags', tags )
		try:
			if tags.get( 'aeroway' ) in [ 'aerodrome', 'heliport' ]:
				return 'Airports'
			if tags.get( 'harbour' ) == 'yes' or tags.get( 'amenity' ) == 'ferry_terminal':
				return 'Ports'
			if tags.get( 'power' ) == 'plant':
				return 'Power Plants'
			if tags.get( 'waterway' ) == 'dam':
				return 'Dams'
			if tags.get( 'telecom' ) == 'data_center' or tags.get( 'building' ) == 'data_center':
				return 'Data Centers'
			if tags.get( 'landuse' ) == 'military' or 'military' in tags:
				return 'Military Installations'
			return ''
		except Exception as e:
			exception = Error( e )
			exception.module = 'sources'
			exception.cause = 'OverpassInfrastructure'
			exception.method = 'classify_infrastructure( self, **args ) -> str'
			Logger.write( exception )
			raise exception

class OverpassCameras( OverpassClient ):
	'''

		Purpose:
		--------
		Retrieve nearby public CCTV, surveillance-camera, and webcam features from
		OpenStreetMap through the Overpass API.

	'''
	timeout: int
	url: str
	response: Response | None
	category_filters: Dict[ str, List[ str ] ]

	def __init__( self, timeout: int=30 ) -> None:
		'''

			Purpose:
			--------
			Initialize OpenStreetMap Overpass camera access.

			Parameters:
			-----------
			timeout (int): HTTP timeout in seconds.

			Returns:
			--------
			None

		'''
		super( ).__init__( timeout=timeout )
		self.category_filters = {
				'CCTV / Surveillance': [ '["man_made"="surveillance"]',
				                         '["surveillance:type"="camera"]' ],
			'Web Cameras': [ '["webcam"]', '["contact:webcam"]' ], }

	def fetch_cameras( self, latitude: float, longitude: float, radius_km: float,
			categories: List[ str ], max_results: int ) -> Dict[ str, Any ]:
		'''

			Purpose:
			--------
			Retrieve tagged public camera features within a circular search radius.

			Parameters:
			-----------
			latitude (float): Search-origin latitude.
			longitude (float): Search-origin longitude.
			radius_km (float): Search radius in kilometers.
			categories (List[str]): Camera categories to retrieve.
			max_results (int): Maximum normalized Overpass elements to return.

			Returns:
			--------
			Dict[str, Any]: Overpass elements with an added CameraCategory field.

		'''
		throw_if( 'latitude', latitude )
		throw_if( 'longitude', longitude )
		throw_if( 'radius_km', radius_km )
		throw_if( 'categories', categories )
		throw_if( 'max_results', max_results )
		try:
			self.latitude = float( latitude )
			self.longitude = float( longitude )
			self.radius_km = float( radius_km )
			self.categories = list( categories )
			self.max_results = int( max_results )
			if self.latitude < -90.0 or self.latitude > 90.0:
				raise ValueError( 'Argument "latitude" must be between -90 and 90.' )
			if self.longitude < -180.0 or self.longitude > 180.0:
				raise ValueError( 'Argument "longitude" must be between -180 and 180.' )
			if self.radius_km <= 0.0:
				raise ValueError( 'Argument "radius_km" must be greater than zero.' )
			if self.max_results < 1:
				raise ValueError( 'Argument "max_results" must be greater than zero.' )
			for category in self.categories:
				if category not in self.category_filters:
					raise ValueError( f'Unsupported camera category: {category}' )
	
			radius_meters = int( self.radius_km * 1000.0 )
			selectors: List[ str ] = [ ]
			for category in self.categories:
				for tag_filter in self.category_filters[ category ]:
					selectors.append(
						f'nwr(around:{radius_meters},{self.latitude:.6f},{self.longitude:.6f})'
						f'{tag_filter};' )
			query = '[out:json][timeout:25];(' + ''.join( selectors ) + ');out center tags qt;'
			payload = self.execute( query )
			if not isinstance( payload, dict ):
				raise TypeError( 'Overpass camera response must be a dictionary.' )
			elements = payload.get( 'elements', [ ] ) or [ ]
			if not isinstance( elements, list ):
				raise TypeError( 'Overpass camera elements must be a list.' )
	
			rows: List[ Dict[ str, Any ] ] = [ ]
			seen: set[ str ] = set( )
			for element in elements:
				if not isinstance( element, dict ):
					continue
				tags = element.get( 'tags', { } ) or { }
				category = self.classify_camera( tags )
				if not category or category not in self.categories:
					continue
				entity_key = f'{element.get( "type", "" )}:{element.get( "id", "" )}'
				if entity_key in seen:
					continue
				seen.add( entity_key )
				row = dict( element )
				row[ 'CameraCategory' ] = category
				rows.append( row )
				if len( rows ) >= self.max_results:
					break
			payload[ 'elements' ] = rows
			return payload
		except Exception as e:
			exception = Error( e )
			exception.module = 'sources'
			exception.cause = 'OverpassCamera'
			exception.method = 'fetch_cameras( self, **args ) -> Dict[ str, Any ]'
			Logger.write( exception )
			raise exception

	def classify_camera( self, tags: Dict[ str, Any ] ) -> str:
		'''

			Purpose:
			--------
			Classify one OpenStreetMap camera feature into a supported camera category.

			Parameters:
			-----------
			tags (Dict[str, Any]): OpenStreetMap feature tags.

			Returns:
			--------
			str: Camera category, or an empty string when unsupported.

		'''
		throw_if( 'tags', tags )
		try:
			if tags.get( 'webcam' ) or tags.get( 'contact:webcam' ):
				return 'Web Cameras'
			if tags.get( 'man_made' ) == 'surveillance' or tags.get( 'surveillance:type' ) == 'camera':
				return 'CCTV / Surveillance'
			return ''
		except Exception as e:
			exception = Error( e )
			exception.module = 'sources'
			exception.cause = 'OverpassCameras'
			exception.method = 'classify_camera( self, **args ) -> str'
			Logger.write( exception )
			raise exception

class OverpassMapLayers( OverpassClient ):
	'''

		Purpose:
		--------
		Retrieve contextual public map features from OpenStreetMap through the Overpass API.

	'''
	timeout: int
	url: str
	response: Response | None
	category_filters: Dict[ str, List[ str ] ]

	def __init__( self, timeout: int=30 ) -> None:
		'''

			Purpose:
			--------
			Initialize OpenStreetMap Overpass contextual map-layer access.

			Parameters:
			-----------
			timeout (int): HTTP timeout in seconds.

			Returns:
			--------
			None

		'''
		super( ).__init__( timeout=timeout )
		self.category_filters = {
			'Public Transit': [ '["public_transport"="station"]', '["railway"="station"]' ],
			'Bike Share': [ '["amenity"="bicycle_rental"]' ],
			'Emergency Services': [ '["amenity"="police"]', '["amenity"="fire_station"]' ],
			'Healthcare': [ '["amenity"="hospital"]', '["amenity"="clinic"]' ],
			'EV Charging': [ '["amenity"="charging_station"]' ],
			'Communications': [
				'["man_made"="tower"]["tower:type"="communication"]',
				'["man_made"="mast"]["tower:type"="communication"]' ],
			'Launch Sites': [ '["aeroway"="spaceport"]', '["man_made"="launch_pad"]' ],
		}

	def fetch_features( self, latitude: float, longitude: float, radius_km: float,
			categories: List[ str ], max_results: int ) -> Dict[ str, Any ]:
		'''

			Purpose:
			--------
			Retrieve selected contextual map features within a circular search radius.

			Parameters:
			-----------
			latitude (float): Search-origin latitude.
			longitude (float): Search-origin longitude.
			radius_km (float): Search radius in kilometers.
			categories (List[str]): Contextual map categories to retrieve.
			max_results (int): Maximum normalized Overpass elements to return.

			Returns:
			--------
			Dict[str, Any]: Overpass elements with an added MapLayerCategory field.

		'''
		throw_if( 'latitude', latitude )
		throw_if( 'longitude', longitude )
		throw_if( 'radius_km', radius_km )
		throw_if( 'categories', categories )
		throw_if( 'max_results', max_results )
		try:
			self.latitude = float( latitude )
			self.longitude = float( longitude )
			self.radius_km = float( radius_km )
			self.categories = list( categories )
			self.max_results = int( max_results )
			if self.latitude < -90.0 or self.latitude > 90.0:
				raise ValueError( 'Argument "latitude" must be between -90 and 90.' )
			if self.longitude < -180.0 or self.longitude > 180.0:
				raise ValueError( 'Argument "longitude" must be between -180 and 180.' )
			if self.radius_km <= 0.0:
				raise ValueError( 'Argument "radius_km" must be greater than zero.' )
			if self.max_results < 1:
				raise ValueError( 'Argument "max_results" must be greater than zero.' )
			for category in self.categories:
				if category not in self.category_filters:
					raise ValueError( f'Unsupported map layer category: {category}' )
	
			radius_meters = int( self.radius_km * 1000.0 )
			selectors: List[ str ] = [ ]
			for category in self.categories:
				for tag_filter in self.category_filters[ category ]:
					selectors.append(
						f'nwr(around:{radius_meters},{self.latitude:.6f},{self.longitude:.6f})'
						f'{tag_filter};' )
			query = '[out:json][timeout:25];(' + ''.join( selectors ) + ');out center tags qt;'
			payload = self.execute( query )
			if not isinstance( payload, dict ):
				raise TypeError( 'Overpass map-layer response must be a dictionary.' )
			elements = payload.get( 'elements', [ ] ) or [ ]
			if not isinstance( elements, list ):
				raise TypeError( 'Overpass map-layer elements must be a list.' )
	
			rows: List[ Dict[ str, Any ] ] = [ ]
			seen: set[ str ] = set( )
			for element in elements:
				if not isinstance( element, dict ):
					continue
				tags = element.get( 'tags', { } ) or { }
				category = self.classify_feature( tags )
				if not category or category not in self.categories:
					continue
				entity_key = f'{element.get( "type", "" )}:{element.get( "id", "" )}'
				if entity_key in seen:
					continue
				seen.add( entity_key )
				row = dict( element )
				row[ 'MapLayerCategory' ] = category
				rows.append( row )
				if len( rows ) >= self.max_results:
					break
			payload[ 'elements' ] = rows
			return payload
		except Exception as e:
			exception = Error( e )
			exception.module = 'sources'
			exception.cause = 'OverpassMapLayers'
			exception.method = 'fetch_features( self, **args ) -> Dict[ str, Any ]'
			Logger.write( exception )
			raise exception

	def classify_feature( self, tags: Dict[ str, Any ] ) -> str:
		'''

			Purpose:
			--------
			Classify one OpenStreetMap feature into a supported contextual map category.

			Parameters:
			-----------
			tags (Dict[str, Any]): OpenStreetMap feature tags.

			Returns:
			--------
			str: Contextual map category, or an empty string when unsupported.

		'''
		throw_if( 'tags', tags )
		try:
			if tags.get( 'aeroway' ) == 'spaceport' or tags.get( 'man_made' ) == 'launch_pad':
				return 'Launch Sites'
			if tags.get( 'amenity' ) == 'bicycle_rental':
				return 'Bike Share'
			if tags.get( 'amenity' ) in [ 'police', 'fire_station' ]:
				return 'Emergency Services'
			if tags.get( 'amenity' ) in [ 'hospital', 'clinic' ]:
				return 'Healthcare'
			if tags.get( 'amenity' ) == 'charging_station':
				return 'EV Charging'
			if tags.get( 'public_transport' ) == 'station' or tags.get( 'railway' ) == 'station':
				return 'Public Transit'
			if (tags.get( 'man_made' ) in [ 'tower', 'mast' ]
					and tags.get( 'tower:type' ) == 'communication'):
				return 'Communications'
			return ''
		except Exception as e:
			exception = Error( e )
			exception.module = 'sources'
			exception.cause = 'OverpassMapLayers'
			exception.method = 'classify_feature( self, **args ) -> str'
			Logger.write( exception )
			raise exception

