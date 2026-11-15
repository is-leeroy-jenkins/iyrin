"""Regression checks for splitting the Geoscience Data mode into standalone pipelines.

Purpose:
    Verify that Weather, Environmental, and Geological Data are independent
    top-level Streamlit modes and preserve their existing provider and
    document-processing workflows without reintroducing nested wrappers.
"""
from __future__ import annotations

import ast
from pathlib import Path
import unittest


ROOT = Path( __file__ ).resolve( ).parents[ 1 ]
SOURCE = (ROOT / 'app.py').read_text( encoding='utf-8' )
CONFIG = (ROOT / 'config.py').read_text( encoding='utf-8' )
TREE = ast.parse( SOURCE )


class ScientificDataModeTests( unittest.TestCase ):
    """Validate standalone mode dispatch and retained source functionality.

    Attributes:
        modes (list[str]): Configured sidebar pipeline selections.
        branches (dict[str, ast.If]): AST conditions for top-level mode dispatch.
    """

    @classmethod
    def setUpClass( cls ) -> None:
        """Load actual sidebar modes and map the matching dispatch statements.

        Returns:
            None: Initializes class-level parsed application information.
        """
        config_tree = ast.parse( CONFIG )
        assignments = [ node for node in config_tree.body if isinstance( node, ast.Assign )
            and any( isinstance( target, ast.Name ) and target.id == 'MODES'
                for target in node.targets ) ]
        cls.modes = ast.literal_eval( assignments[ 0 ].value )
        cls.branches = { }
        for node in ast.walk( TREE ):
            if not isinstance( node, ast.If ) or not isinstance( node.test, ast.Compare ):
                continue
            comparison = node.test
            if (not isinstance( comparison.left, ast.Name )
                    or comparison.left.id != 'mode'
                    or len( comparison.comparators ) != 1
                    or not isinstance( comparison.comparators[ 0 ], ast.Constant )):
                continue
            cls.branches[ comparison.comparators[ 0 ].value ] = node

    def test_sidebar_exposes_three_distinct_modes( self ) -> None:
        """Replace the old combined selection with exactly three separate modes."""
        expected = [ 'Weather Data', 'Environmental Data', 'Geological Data' ]
        for mode in expected:
            self.assertEqual( 1, self.modes.count( mode ) )
            self.assertIn( mode, self.branches )
        self.assertNotIn( 'Geoscience Data', self.modes )
        self.assertEqual( 12, len( self.modes ) )

    def test_each_mode_uses_astronomical_style_layout( self ) -> None:
        """Match Astronomical Data's full-width columns instead of nested expanders."""
        for mode in [ 'Weather Data', 'Environmental Data', 'Geological Data' ]:
            branch = self.branches[ mode ]
            code = ast.get_source_segment( SOURCE, branch ) or ''
            self.assertIn( "left, center, right = st.columns(", code )
            self.assertIn( "with center:", code )
            self.assertIn( f"st.subheader( '{mode}' )", code )
            self.assertNotIn( "with st.expander( 'Geoscience Data'", code )

    def test_weather_sources_and_processing_remain( self ) -> None:
        """Retain weather providers, session keys, and document display."""
        code = ast.get_source_segment( SOURCE, self.branches[ 'Weather Data' ] ) or ''
        for marker in [ 'Google Weather', 'OpenWeather', 'Historical Weather',
                'Climate Data', 'Tides & Currents', "'weather_last_result'",
                "render_mode_document_tabs( 'weather'", 
                "render_source_processing_controls( 'weather'" ]:
            self.assertIn( marker, code )

    def test_environmental_sources_and_processing_remain( self ) -> None:
        """Retain environmental providers, state, and processed document tabs."""
        code = ast.get_source_segment( SOURCE, self.branches[ 'Environmental Data' ] ) or ''
        for marker in [ 'AirNow', 'OpenAQ', 'PurpleAir', 'Envirofacts',
                'FIRMS', 'EONET', "'env_last_result'",
                "render_mode_document_tabs( 'env'",
                "render_source_processing_controls( 'env'" ]:
            self.assertIn( marker, code )

    def test_geological_sources_and_processing_remain( self ) -> None:
        """Retain all USGS sources and the Geological document workflow."""
        code = ast.get_source_segment( SOURCE, self.branches[ 'Geological Data' ] ) or ''
        for marker in [ 'USGS Earthquakes', 'USGS Water Data',
                'USGS The National Map', 'USGS ScienceBase',
                "'geo_last_result'", "render_mode_document_tabs( 'geo'",
                "render_source_processing_controls( 'geo'" ]:
            self.assertIn( marker, code )

    def test_astronomical_and_other_modes_remain( self ) -> None:
        """Do not change the separately configured Astronomical and other pipelines."""
        for mode in [ 'Mapping Tools', 'Interactive Map', 'Local Data',
                'Astronomical Data', 'Celestial Map', 'Public Health',
                'Artificial Intelligence', 'File Upload', 'Data Management' ]:
            self.assertIn( mode, self.modes )
            self.assertIn( mode, self.branches )

    def test_mkdocs_navigation_links_exist( self ) -> None:
        """Ensure new mode guide pages and navigation entries correspond."""
        nav = (ROOT / 'mkdocs.yml').read_text( encoding='utf-8' )
        for name in [ 'weather', 'environmental', 'geological' ]:
            self.assertIn( f'user-guide/{name}-data.md', nav )
            self.assertTrue( (ROOT / 'docs' / 'user-guide' /
                f'{name}-data.md').is_file( ) )


if __name__ == '__main__':
    unittest.main( )
