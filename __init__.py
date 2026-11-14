'''
	******************************************************************************************
	  Assembly:                Iyrin
	  Filename:                __init__.py
	  Author:                  Terry D. Eppler
	  Created:                 05-31-2022
	
	  Last Modified By:        Terry D. Eppler
	  Last Modified On:        05-01-2025
	******************************************************************************************
	<copyright file="__init__.py" company="Terry D. Eppler">
	
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
	__init__.py
	</summary>
	******************************************************************************************
'''

from importlib import import_module
from pathlib import Path
import sys

# Existing script modules resolve their application-local imports from the package root.
sys.path.insert( 0, str( Path( __file__ ).resolve( ).parent ) )

EXPORTS = {
    'IyrinError': 'exceptions', 'GatewayError': 'exceptions', 'NotFound': 'exceptions',
    'RateLimiter': 'rates',
    'BaseCache': 'storage', 'InMemoryCache': 'storage', 'SQLiteCache': 'storage',
    'SQLiteDatabase': 'storage', 'ChromaStore': 'storage', 'PineconeStore': 'storage',
    'Map': 'mapping', 'Maps': 'mapping', 'Geocoder': 'mapping', 'Place': 'mapping',
    'DistanceMatrix': 'mapping', 'Timezone': 'mapping', 'StaticMap': 'mapping',
    'Excel': 'excel',
}
__all__ = list( EXPORTS )


def __getattr__( name: str ) -> object:
    """Load an existing public application class on demand.

    Purpose:
        Preserves public exports without importing runtime dependencies at launcher startup.

    Args:
        name (str): Public export name requested by the caller.

    Returns:
        object: Requested exported class.

    Raises:
        AttributeError: The requested export is not defined.
    """
    if name not in EXPORTS:
        raise AttributeError( f'Module {__name__!r} has no attribute {name!r}' )
    value = getattr( import_module( f'.{EXPORTS[ name ]}', __name__ ), name )
    globals( )[ name ] = value
    return value

__version__ = "0.2.0"













