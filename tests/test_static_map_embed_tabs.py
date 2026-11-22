"""Regression coverage for full-width static maps and supported Google embeds.

Purpose:
    Verify the static-map rendering contracts without requesting live Google services.
"""

from __future__ import annotations

import ast
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict
import unittest


ROOT = Path(__file__).resolve().parents[1]


class ProviderError(Exception):
    """Represent the application's API exception wrapper."""


class StaticMapEmbedContractTests(unittest.TestCase):
    """Check map rendering and documented Google Static Maps parameter limits."""

    def test_static_map_resolution_uses_google_supported_scale(self) -> None:
        """The optional scale preserves the old interface and supports scale=2."""
        tree = ast.parse((ROOT / 'mapping.py').read_text(encoding='utf-8'))
        cls = next(node for node in tree.body
            if isinstance(node, ast.ClassDef) and node.name == 'StaticMap')
        method = next(node for node in cls.body
            if isinstance(node, ast.FunctionDef) and node.name == 'pin')
        module = ast.fix_missing_locations(ast.Module(body=[method], type_ignores=[]))
        namespace: Dict[str, Any] = {
            'throw_if': lambda name, value: None,
            'Error': ProviderError,
            'Logger': lambda: SimpleNamespace(write=lambda exception: None),
        }
        exec(compile(module, str(ROOT / 'mapping.py'), 'exec'), namespace)
        pin = namespace['pin']
        service = SimpleNamespace(
            validate_coordinate=lambda lat, lng: (lat, lng),
            build_url=lambda params: params.copy(),
        )
        parameters = pin(service, 38.861562, -77.063107, zoom=8,
            size='640x400', scale=2)
        self.assertEqual(2, parameters['scale'])
        self.assertEqual('640x400', parameters['size'])
        self.assertEqual('38.861562,-77.063107', parameters['center'])
        self.assertEqual(1, pin(service, 38.861562, -77.063107)['scale'])
        with self.assertRaises(ProviderError):
            pin(service, 38.861562, -77.063107, scale=3)

    def test_static_map_tab_fills_container(self) -> None:
        """Keep the existing static result, but display it at content width."""
        source = (ROOT / 'app.py').read_text(encoding='utf-8')
        self.assertIn("st.image( map_url, width='stretch' )", source)
        self.assertIn("st.code( map_url )", source)
        self.assertIn("scale=2 )", source)
        self.assertNotIn("'800x600'", source)

    def test_static_map_preferences_are_independent_of_coordinate_save(self) -> None:
        """Saving image preferences must not depend on the coordinate checkbox."""
        source = (ROOT / 'app.py').read_text(encoding='utf-8')
        section = source.split('with static_maps_tab:', 1)[1].split(
            '# ----- Street View and satellite imagery', 1)[0]
        checkbox = section.index("save_coordinates = st.checkbox(")
        zoom_assignment = section.index("st.session_state[ 'zoom' ] = int( zoom )")
        size_assignment = section.index("st.session_state[ 'map_size' ] = str( size )")
        generate_button = section.index("if st.button( 'Generate Map'")
        self.assertLess(checkbox, zoom_assignment)
        self.assertLess(zoom_assignment, generate_button)
        self.assertLess(size_assignment, generate_button)
        self.assertIn('if save_coordinates:', section)
        self.assertIn("set_location_state( location=f'{lat:.6f}, {lng:.6f}'", section)
        self.assertIn("st.session_state[ 'active_location_source' ] = 'static_map'",
            section)

    def test_saved_static_location_is_not_overwritten_by_browser_reruns(self) -> None:
        """A deliberate manual map save remains active until the browser reset."""
        tree = ast.parse((ROOT / 'app.py').read_text(encoding='utf-8'))
        methods = [node for node in tree.body
            if isinstance(node, ast.FunctionDef) and node.name in (
                'bootstrap_browser_geolocation', 'ensure_active_location_state')]
        self.assertEqual(2, len(methods))
        module = ast.fix_missing_locations(ast.Module(body=methods, type_ignores=[]))
        session = {'active_location_source': 'static_map',
            'latitude': 38.861562, 'longitude': -77.063107,
            'browser_geolocation_enabled': True, 'browser_geolocation_loaded': True,
            'browser_geolocation': {'coords': {
                'latitude': 40.0, 'longitude': -74.0}}}
        namespace: Dict[str, Any] = {
            'st': SimpleNamespace(session_state=session),
            'Geocoder': object,
            'has_valid_global_coordinates': lambda: True}
        exec(compile(module, str(ROOT / 'app.py'), 'exec'), namespace)
        namespace['bootstrap_browser_geolocation'](None)
        namespace['ensure_active_location_state']()
        self.assertEqual(38.861562, session['latitude'])
        self.assertEqual(-77.063107, session['longitude'])
        source = (ROOT / 'app.py').read_text(encoding='utf-8')
        self.assertIn("st.session_state[ 'active_location_source' ] = ''",
            source.split("key='browser_geolocation_reset'", 1)[1].split(
                'st.rerun( )', 1)[0])

    def test_existing_static_map_rebuilds_for_zoom_and_size_changes(self) -> None:
        """The production render block must use updated widgets and saved location."""
        tree = ast.parse((ROOT / 'app.py').read_text(encoding='utf-8'))
        candidates = [node for node in ast.walk(tree)
            if isinstance(node, ast.If)
            and isinstance(node.test, ast.Name) and node.test.id == 'map_url'
            and any(isinstance(item, ast.Call)
                and isinstance(item.func, ast.Attribute) and item.func.attr == 'image'
                for item in ast.walk(node))]
        self.assertEqual(1, len(candidates))
        module = ast.fix_missing_locations(ast.Module(body=candidates, type_ignores=[]))
        urls = []
        state = {'maps_last_latitude': 38.861562,
            'maps_last_longitude': -77.063107,
            'maps_last_url': 'previous-url'}

        def pin(lat: float, lng: float, zoom: int, size: str, scale: int) -> str:
            """Record actual arguments passed by the production rendering block."""
            urls.append((lat, lng, zoom, size, scale))
            return f'map-{zoom}-{size}'

        streamlit = SimpleNamespace(
            session_state=state,
            markdown=lambda message: None,
            image=lambda url, width: None,
            caption=lambda message: None,
            code=lambda url: None)
        namespace: Dict[str, Any] = {
            'st': streamlit, 'static_maps': SimpleNamespace(pin=pin),
            'blue_divider': lambda: None, 'map_url': state['maps_last_url'],
            'zoom': 9, 'size': '600x400'}
        exec(compile(module, str(ROOT / 'app.py'), 'exec'), namespace)
        namespace['zoom'] = 11
        namespace['size'] = '640x400'
        namespace['map_url'] = state['maps_last_url']
        exec(compile(module, str(ROOT / 'app.py'), 'exec'), namespace)
        self.assertEqual([
            (38.861562, -77.063107, 9, '600x400', 2),
            (38.861562, -77.063107, 11, '640x400', 2)], urls)
        self.assertEqual('map-11-640x400', state['maps_last_url'])
        self.assertNotIn('latitude', state)
        self.assertNotIn('longitude', state)

    def test_street_and_satellites_are_top_level_mapping_tabs(self) -> None:
        """Street and Satellites belong directly to Mapping Tools after Static Maps."""
        source = (ROOT / 'app.py').read_text(encoding='utf-8')
        self.assertIn(
            "geocoding_tab, distances_tab, timezones_tab, static_maps_tab, "
            "street_tab, satellites_tab =", source.replace('\\\n', ' '))
        self.assertIn(
            "st.tabs( [ 'Geocoding', 'Distances', 'Time Zones', 'Static Maps', 'Street',",
            source)
        self.assertIn("'Satellites' ] )", source)
        self.assertIn("with static_maps_tab:", source)
        self.assertIn("with street_tab:", source)
        self.assertIn("with satellites_tab:", source)
        self.assertNotIn("st.tabs( [ 'Map', 'Street', 'Earth' ] )", source)
        self.assertIn("https://www.google.com/maps/embed/v1/streetview?", source)
        self.assertIn("https://www.google.com/maps/embed/v1/view?", source)
        self.assertIn("'maptype': 'satellite'", source)
        satellites_section = source.split("with satellites_tab:", 1)[1].split(
            "# MAP MODE", 1)[0]
        self.assertEqual(1, satellites_section.count("components.iframe( "))
        self.assertIn("st.link_button( 'Open Google Earth', earth_url )", source)

    def test_satellites_default_to_photorealistic_3d(self) -> None:
        """Render Google's 3D map component, not a tilted 2D iframe."""
        source = (ROOT / 'app.py').read_text(encoding='utf-8')
        self.assertIn("options=[ '3D Satellite', '2D Satellite' ]", source)
        self.assertIn("key='maps_satellite_rendering'", source)
        self.assertIn("elif satellite_mode == '3D Satellite':", source)
        self.assertIn('<gmp-map-3d center=', source)
        self.assertIn('mode="SATELLITE"', source)
        self.assertIn('range="3000" tilt="65"', source)
        self.assertIn("'libraries': 'maps3d'", source)
        self.assertIn("maps.googleapis.com/maps/api/js?", source)
        self.assertIn("components.html( maps3d_html, height=700, scrolling=False )", source)
        self.assertIn("html_lib.escape( maps3d_script_url, quote=True )", source)

    def test_satellite_2d_fallback_preserves_existing_google_embed(self) -> None:
        """Keep 2D satellite imagery available without embedding Google Earth."""
        source = (ROOT / 'app.py').read_text(encoding='utf-8')
        self.assertIn("with satellites_tab:", source)
        self.assertIn("https://www.google.com/maps/embed/v1/view?", source)
        self.assertIn("'maptype': 'satellite'", source)
        self.assertIn("components.iframe( satellite_url, height=700, scrolling=False )", source)
        self.assertIn("st.link_button( 'Open Google Earth', earth_url )", source)
        self.assertIn("cfg.GOOGLEMAPS_API_KEY", source)


if __name__ == '__main__':
    unittest.main()
