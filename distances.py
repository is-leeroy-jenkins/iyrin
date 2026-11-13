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

