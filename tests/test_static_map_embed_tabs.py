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
