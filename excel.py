'''
  ******************************************************************************************
      Assembly:                Iyrin
      Filename:                excel.py
      Author:                  Terry D. Eppler
      Created:                 05-31-2022

      Last Modified By:        Terry D. Eppler
      Last Modified On:        05-01-2025
  ******************************************************************************************
  <copyright file="excel.py" company="Terry D. Eppler">

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
    excel.py
  </summary>
  ******************************************************************************************
  '''

from typing import Optional, Dict, List
import pandas as pd
from storage import BaseCache
from mapping import Geocoder, Map, Place
from boogr import Error, Logger

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

class Excel:
	"""Excel and CSV location enrichment interface.

	Purpose:
		Reads or writes spreadsheets, preserves existing data columns, and enriches
		geographic records using Geocoder with Places as a fallback. Records row-level
		status, errors, and summary metrics without changing the input column schema.

	Attributes:
		api_key (str): Google Maps credential used by the gateway.
		maps (Optional[Map]): Google Maps request gateway.
		geocoder (Optional[Geocoder]): Address geocoding service.
		places (Optional[Place]): Google Places fallback resolver.
		input_path (Optional[str]): Source spreadsheet filename.
		output_path (Optional[str]): Output spreadsheet filename.
		dataframe (Optional[pd.DataFrame]): Most recent loaded or enriched DataFrame.
		worksheet (Optional[str]): Selected Excel worksheet name.
		output (Optional[Dict[str, List]]): Enrichment output columns and their values.
		address (Optional[str]): Selected address or address-column name.
		cache (Optional[BaseCache]): Optional provider lookup cache.
		file_path (Optional[str]): Most recent file path used for I/O.
		last_summary (Optional[Dict]): Most recently computed enrichment summary.
		city (Optional[str]): City or city-column name.
		state (Optional[str]): State or region-column name.
		country (Optional[str]): Country or country-column name.
	"""
	api_key: str
	maps: Optional[ Map ]
	geocoder: Optional[ Geocoder ]
	places: Optional[ Place ]
	input_path: Optional[ str ]
	output_path: Optional[ str ]
	dataframe: Optional[ pd.DataFrame ]
	worksheet: Optional[ str ]
	output: Optional[ Dict[ str, List ] ]
	address: Optional[ str ]
	cache: Optional[ BaseCache ]
	file_path: Optional[ str ]
	last_summary: Optional[ Dict ]
	city: Optional[ str ]
	state: Optional[ str ]
	country: Optional[ str ]
	
	def __init__( self, api: str, cache: Optional[ BaseCache ] = None ) -> None:
		"""Initialize Excel enrichment with a Google Maps gateway and optional cache.

		Purpose:
			Creates the mapping, geocoding, and Places client members used by enrichment methods.

		Args:
			api (str): Google Maps Platform API credential.
			cache (Optional[BaseCache]): Optional cache shared by the mapping providers.

		Returns:
			None: Initializes the enrichment helper and its member attributes.
		"""
		self.api_key = api
		self.cache = cache
		self.maps = Map( api_key=self.api_key )
		self.geocoder = Geocoder( self.maps, cache=self.cache )
		self.places = Place( self.maps, cache=self.cache )
		self.input_path = None
		self.output_path = None
		self.dataframe = None
		self.worksheet = None
		self.output = None
		self.address = None
		self.file_path = None
		self.last_summary = None
		self.city = None
		self.state = None
		self.country = None
	
	def read( self, path: str, sheet: Optional[ str ] ) -> pd.DataFrame:
		"""Read a CSV or Excel workbook without losing text identifiers.

		Purpose:
			Loads CSV or XLSX data with string preservation, including account codes and leading zeros.

		Args:
			path (str): Source CSV or XLSX file path.
			sheet (Optional[str]): Worksheet to read from an Excel file, or None for the first worksheet.

		Returns:
			pd.DataFrame: Loaded spreadsheet data.
		"""
		try:
			throw_if( 'path', path )
			if not isinstance( path, str ):
				raise TypeError( 'path must be a string.' )
			if sheet is not None and not isinstance( sheet, str ):
				raise TypeError( 'sheet must be a string when provided.' )
			self.file_path = path
			self.worksheet = sheet
			if self.file_path.lower( ).endswith( '.csv' ):
				self.dataframe = pd.read_csv( self.file_path, dtype=str )
			else:
				self.dataframe = pd.read_excel(
					self.file_path,
					sheet_name=self.worksheet or 0,
					dtype=str )
			
			for column in self.dataframe.columns:
				if self.dataframe[ column ].dtype == object:
					self.dataframe[ column ] = (
							self.dataframe[ column ].fillna( '' ).astype( str ).str.strip( ))
			
			return self.dataframe
		
		except Exception as e:
			exception = Error( e )
			exception.module = 'Iyrin'
			exception.cause = 'Excel'
			exception.method = 'read( self, path: str, sheet: Optional[ str ] )'
			raise exception
	
	def write( self, df: pd.DataFrame, path: str, sheet: Optional[ str ] ) -> None:
		"""Write the current DataFrame to CSV or Excel.

		Purpose:
			Writes spreadsheet data without exporting the DataFrame index.

		Args:
			df (pd.DataFrame): DataFrame to write.
			path (str): Destination CSV or XLSX file path.
			sheet (Optional[str]): Excel worksheet name, or None to use Sheet1.

		Returns:
			None: Writes the output file.
		"""
		try:
			throw_if( 'df', df )
			throw_if( 'path', path )
			
			if not isinstance( df, pd.DataFrame ) or not isinstance( path, str ):
				raise TypeError( 'Expected a pandas DataFrame and a string path.' )
			if sheet is not None and not isinstance( sheet, str ):
				raise TypeError( 'sheet must be a string when provided.' )
			self.file_path = path
			self.dataframe = df.copy( )
			self.worksheet = sheet or 'Sheet1'
			if self.file_path.lower( ).endswith( '.csv' ):
				self.dataframe.to_csv( self.file_path, index=False )
			else:
				self.dataframe.to_excel(
					self.file_path,
					index=False,
					sheet_name=self.worksheet )
		
		except Exception as e:
			exception = Error( e )
			exception.module = 'Iyrin'
			exception.cause = 'Excel'
			exception.method = 'write( self, df: pd.DataFrame, path: str, sheet: Optional[ str ] )'
			raise exception
	
	def create_outputs( self ) -> Dict[ str, List ]:
		"""Create the standard enrichment output columns.

		Purpose:
			Returns empty lists for geocode data, status, and error fields.

		Returns:
			Dict[str, List]: Empty output lists keyed by enrichment column names.
		"""
		try:
			return { 'formatted_address': [ ], 'lat': [ ], 'lng': [ ], 'place_id': [ ],
					'types': [ ], 'country_code': [ ], 'country_name': [ ], 'admin_level_1': [ ],
					'admin_level_2': [ ], 'locality': [ ], 'postal_code': [ ],
					'geocode_status': [ ], 'geocode_error': [ ], }
		
		except Exception as e:
			exception = Error( e )
			exception.module = 'Iyrin'
			exception.cause = 'Excel'
			exception.method = 'create_outputs( self )'
			raise exception
	
	def append_empty( self, outputs: Dict[ str, List ], status: str='skipped_empty',
			error: Optional[ str ]=None ) -> None:
		"""Append an empty geographic resolution record.

		Purpose:
			Marks a record skipped or unresolved while retaining aligned output columns.

		Args:
			outputs (Dict[str, List]): Existing output-column container.
			status (str): Row-level status code.
			error (Optional[str]): Optional error description.

		Returns:
			None: Appends the empty result and its status to the container.
		"""
		try:
			throw_if( 'outputs', outputs )
			outputs[ 'formatted_address' ].append( None )
			outputs[ 'lat' ].append( None )
			outputs[ 'lng' ].append( None )
			outputs[ 'place_id' ].append( None )
			outputs[ 'types' ].append( None )
			outputs[ 'country_code' ].append( None )
			outputs[ 'country_name' ].append( None )
			outputs[ 'admin_level_1' ].append( None )
			outputs[ 'admin_level_2' ].append( None )
			outputs[ 'locality' ].append( None )
			outputs[ 'postal_code' ].append( None )
			outputs[ 'geocode_status' ].append( status or 'skipped_empty' )
			outputs[ 'geocode_error' ].append( error )
		
		except Exception as e:
			exception = Error( e )
			exception.module = 'Iyrin'
			exception.cause = 'Excel'
			exception.method = 'append_empty( self, outputs: Dict[ str, List ], status: str=skipped_empty )'
			raise exception
	
	def append_result( self, outputs: Dict[ str, List ], result: Dict,
			status: str, error: Optional[ str ] = None ) -> None:
		"""Append a normalized geocode or Places record.

		Purpose:
			Adds a resolved geographic record and status to the existing output columns.

		Args:
			outputs (Dict[str, List]): Existing output-column container.
			result (Dict): Flattened geocode or Places result.
			status (str): Resolution status code.
			error (Optional[str]): Optional failure description.

		Returns:
			None: Appends the result and status to the container.
		"""
		try:
			throw_if( 'outputs', outputs )
			result_value = result or { }
			status_value = status or 'not_found'
			outputs[ 'formatted_address' ].append( result_value.get( 'formatted_address' ) )
			outputs[ 'lat' ].append( result_value.get( 'lat' ) )
			outputs[ 'lng' ].append( result_value.get( 'lng' ) )
			outputs[ 'place_id' ].append( result_value.get( 'place_id' ) )
			outputs[ 'types' ].append( result_value.get( 'types' ) )
			outputs[ 'country_code' ].append( result_value.get( 'country_code' ) )
			outputs[ 'country_name' ].append( result_value.get( 'country_name' ) )
			outputs[ 'admin_level_1' ].append( result_value.get( 'admin_level_1' ) )
			outputs[ 'admin_level_2' ].append( result_value.get( 'admin_level_2' ) )
			outputs[ 'locality' ].append( result_value.get( 'locality' ) )
			outputs[ 'postal_code' ].append( result_value.get( 'postal_code' ) )
			outputs[ 'geocode_status' ].append( status_value )
			outputs[ 'geocode_error' ].append( error )
		
		except Exception as e:
			exception = Error( e )
			exception.module = 'Iyrin'
			exception.cause = 'Excel'
			exception.method = 'append_result( self, **args )'
			raise exception
	
	def summarize( self, df: pd.DataFrame ) -> Dict:
		"""Summarize the outcome of a spreadsheet enrichment.

		Purpose:
			Calculates row and status counts from the enriched DataFrame.

		Args:
			df (pd.DataFrame): Enriched spreadsheet data.

		Returns:
			Dict: Row counts, status counts, and summary metrics.
		"""
		try:
			throw_if( 'df', df )
			status_counts = { }
			if 'geocode_status' in df.columns:
				status_counts = df[ 'geocode_status' ].value_counts( dropna=False ).to_dict( )
			summary = { 'rows_total': int( len( df ) ),
					'rows_ok': int( status_counts.get( 'ok', 0 ) ),
					'rows_ok_places': int( status_counts.get( 'ok_places', 0 ) ),
					'rows_not_found': int( status_counts.get( 'not_found', 0 ) ),
					'rows_skipped_empty': int( status_counts.get( 'skipped_empty', 0 ) ),
					'rows_error': int( status_counts.get( 'error', 0 ) ),
					'status_counts': status_counts, }
			
			self.last_summary = summary
			return self.last_summary
		
		except Exception as e:
			exception = Error( e )
			exception.module = 'Iyrin'
			exception.cause = 'Excel'
			exception.method = 'summarize( self, df: pd.DataFrame )'
			raise exception
	
	def detect_columns( self, df: pd.DataFrame ) -> Dict:
		"""Identify likely location columns in a spreadsheet.

		Purpose:
			Matches column labels to common address, city, region, and country names.

		Args:
			df (pd.DataFrame): Spreadsheet data to inspect.

		Returns:
			Dict: Suggested column names for geographic enrichment.
		"""
		try:
			throw_if( 'df', df )
			columns = list( df.columns )
			lower_map = { str( column ).strip( ).lower( ): column for column in columns }
			def find_first( names: List[ str ] ) -> Optional[ str ]:
				"""Find the first normalized column label among the candidates.

				Purpose:
					Matches known address-field names to the input spreadsheet schema.

				Args:
					names (List[str]): Candidate normalized column names.

				Returns:
					Optional[str]: Matching source column or None when absent.
				"""
				for name in names:
					if name in lower_map:
						return lower_map[ name ]
				return None
			
			return { 'address': find_first(
				[ 'address', 'street address', 'full address', 'location', 'mailing address' ] ),
					'city': find_first( [ 'city', 'town', 'locality', 'municipality' ] ),
					'state': find_first( [ 'state', 'st', 'province', 'region', 'admin_level_1'
					                       ] ),
					'country': find_first( [ 'country', 'country_code', 'cntry', 'nation' ] ) }
		
		except Exception as e:
			exception = Error( e )
			exception.module = 'Iyrin'
			exception.cause = 'Excel'
			exception.method = 'detect_columns( self, df: pd.DataFrame )'
			raise exception
	
	def resolve_address( self, address: str, country: Optional[ str ] = None ) -> Dict:
		"""Resolve a free-form address through Google geospatial providers.

		Purpose:
			Queries the Geocoder first and falls back to Places if the geocoder fails.

		Args:
			address (str): Free-form address to resolve.
			country (Optional[str]): Optional ISO country-code bias.

		Returns:
			Dict: Result, resolution status, and any error message.
		"""
		try:
			throw_if( 'address', address )
			if not isinstance( address, str ):
				raise TypeError( 'address must be a string.' )
			address_value = address.strip( )
			if country is not None and not isinstance( country, str ):
				raise TypeError( 'country must be a string when provided.' )
			country_value = (country or 'US').strip( ).upper( )
			self.address = address_value
			self.country = country_value
			try:
				result = self.geocoder.freeform( self.address, country=self.country )
				return { 'result': result or { }, 'status': 'ok', 'error': None }
			
			except Exception as geocode_error:
				try:
					result = self.places.text_to_location( self.address, country=self.country )
					return { 'result': result or { }, 'status': 'ok_places', 'error': None }
				
				except Exception as places_error:
					return { 'result': { }, 'status': 'not_found',
							'error': f'{geocode_error}; {places_error}' }
		
		except Exception as e:
			exception = Error( e )
			exception.module = 'Iyrin'
			exception.cause = 'Excel'
			exception.method = 'resolve_address( self, address: str, country: Optional[ str ]=None )'
			raise exception
	
	def resolve_city_state_country( self, city: str, state: Optional[ str ],
			country: str ) -> Dict:
		"""Resolve a city, state, and country combination.

		Purpose:
			Attempts structured geocoding and falls back to a Places query when necessary.

		Args:
			city (str): City or locality text.
			state (Optional[str]): Optional province, state, or region.
			country (str): Country name or ISO country code.

		Returns:
			Dict: Result, resolution status, and any error message.
		"""
		try:
			city_value = str( city or '' ).strip( )
			state_value = str( state or '' ).strip( )
			country_value = str( country or '' ).strip( )
			if not any( [ city_value, state_value, country_value ] ):
				return { 'result': { }, 'status': 'skipped_empty', 'error': None }
			
			self.city = city_value
			self.state = state_value
			self.country = country_value
			try:
				result = self.geocoder.city_state_country( self.city, self.state, self.country )
				return { 'result': result or { }, 'status': 'ok', 'error': None }
			
			except Exception as geocode_error:
				query = ', '.join(
					[ value for value in [ self.city, self.state, self.country ] if value ] )
				try:
					result = self.places.text_to_location( query, country=self.country )
					return { 'result': result or { }, 'status': 'ok_places', 'error': None }
				
				except Exception as places_error:
					return { 'result': { }, 'status': 'not_found',
							'error': f'{geocode_error}; {places_error}' }
		
		except Exception as e:
			exception = Error( e )
			exception.module = 'Iyrin'
			exception.cause = 'Excel'
			exception.method = 'resolve_city_state_country( self, **args )'
			raise exception
	
	def enrich_from_address( self, inpath: str, outpath: str, address: str, sheet: Optional[ str ],
			cntry: Optional[ str ] ) -> pd.DataFrame:
		"""Enrich a spreadsheet using a free-form address column.

		Purpose:
			Reads the source file, resolves unique addresses, appends geographic fields, and writes the result.

		Args:
			inpath (str): Input CSV or XLSX path.
			outpath (str): Output CSV or XLSX path.
			address (str): Address-column name.
			sheet (Optional[str]): Excel worksheet name.
			cntry (Optional[str]): Optional country-bias column.

		Returns:
			pd.DataFrame: Enriched spreadsheet data also written to the output file.
		"""
		try:
			throw_if( 'inpath', inpath )
			throw_if( 'outpath', outpath )
			throw_if( 'address', address )
			self.input_path = inpath
			self.output_path = outpath
			self.address = address
			self.worksheet = sheet
			self.country = cntry
			df = self.read( self.input_path, self.worksheet )
			if self.address not in df.columns:
				raise ValueError( f'Address column "{self.address}" was not found.' )
			
			outputs = self.create_outputs( )
			resolved = { }
			for _, row in df.iterrows( ):
				addr = str( row.get( self.address ) or '' ).strip( )
				if not addr:
					self.append_empty( outputs )
					continue
				hint = (str( row.get( self.country ) or '' ).strip( ).upper( ) if (
							self.country and self.country in df.columns) else 'US')
				cache_key = f'{addr}::{hint}'
				if cache_key not in resolved:
					resolved[ cache_key ] = self.resolve_address( addr, country=hint )
				
				item = resolved[ cache_key ]
				self.append_result( outputs, item.get( 'result', { } ),
					item.get( 'status', 'not_found' ), item.get( 'error' ) )
			
			for key, values in outputs.items( ):
				df[ key ] = values
			
			self.dataframe = df
			self.output = outputs
			self.summarize( self.dataframe )
			self.write( self.dataframe, self.output_path, self.worksheet )
			return self.dataframe
		
		except Exception as e:
			exception = Error( e )
			exception.module = 'Iyrin'
			exception.cause = 'Excel'
			exception.method = 'enrich_from_address( self, **kwargs )'
			raise exception
	
	def enrich( self, inpath: str, outpath: str, city: str, state: Optional[ str ], cntry: str,
			sheet: Optional[ str ] = None, ) -> pd.DataFrame:
		"""Enrich a spreadsheet using city, region, and country columns.

		Purpose:
			Resolves unique combinations, preserves input columns, and writes geographic fields and statuses.

		Args:
			inpath (str): Input CSV or XLSX path.
			outpath (str): Output CSV or XLSX path.
			city (str): City-column name.
			state (Optional[str]): Optional state or province-column name.
			cntry (str): Country-column name.
			sheet (Optional[str]): Optional Excel worksheet.

		Returns:
			pd.DataFrame: Enriched spreadsheet data also written to the output file.
		"""
		try:
			throw_if( 'inpath', inpath )
			throw_if( 'outpath', outpath )
			throw_if( 'city', city )
			throw_if( 'cntry', cntry )
			self.input_path = inpath
			self.output_path = outpath
			self.city = city
			self.state = state
			self.country = cntry
			self.worksheet = sheet
			df = self.read( self.input_path, self.worksheet )
			if self.city not in df.columns:
				raise ValueError( f'City column "{self.city}" was not found.' )
			
			if self.country not in df.columns:
				raise ValueError( f'Country column "{self.country}" was not found.' )
			
			if self.state and self.state not in df.columns:
				raise ValueError( f'State column "{self.state}" was not found.' )
			
			outputs = self.create_outputs( )
			resolved = { }
			for _, row in df.iterrows( ):
				city_value = str( row.get( self.city ) or '' ).strip( )
				state_value = (str( row.get( self.state ) or '' ).strip( ) if (
							self.state and self.state in df.columns) else '')
				country_value = str( row.get( self.country ) or '' ).strip( )
				if not any( [ city_value, state_value, country_value ] ):
					self.append_empty( outputs )
					continue
				cache_key = f'{city_value}::{state_value}::{country_value}'
				if cache_key not in resolved:
					resolved[ cache_key ] = self.resolve_city_state_country( city_value,
						state_value, country_value )
				
				item = resolved[ cache_key ]
				self.append_result( outputs, item.get( 'result', { } ),
					item.get( 'status', 'not_found' ), item.get( 'error' ) )
			
			for key, values in outputs.items( ):
				df[ key ] = values
			
			self.dataframe = df
			self.output = outputs
			self.summarize( self.dataframe )
			self.write( self.dataframe, self.output_path, self.worksheet )
			return self.dataframe
		
		except Exception as e:
			exception = Error( e )
			exception.module = 'Iyrin'
			exception.cause = 'Excel'
			exception.method = 'enrich( self, **kwargs)'
			raise exception