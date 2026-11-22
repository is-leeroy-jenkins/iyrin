"""Regression coverage for Realtime mode layout and Live World controls.

Purpose:
    Ensure Live World provider controls and visualizations are rendered only
    within the dedicated Realtime mode without altering provider integrations.
"""

from __future__ import annotations

import ast
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict
import unittest

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]


class RealtimeModeLayoutTests(unittest.TestCase):
    """Verify the dedicated Realtime page and retained live-data functionality."""

    def test_realtime_mode_is_available_in_mode_selector(self) -> None:
        """Expose Realtime through the existing cfg.MODES radio selector."""
        source = (ROOT / 'config.py').read_text(encoding='utf-8')
        tree = ast.parse(source)
        assignments = [node for node in tree.body
            if isinstance(node, ast.Assign)
            and any(isinstance(target, ast.Name) and target.id == 'MODES'
                for target in node.targets)]
        self.assertEqual(1, len(assignments))
        modes = ast.literal_eval(assignments[0].value)
        self.assertIn('Realtime', modes)

    def test_live_controls_and_map_render_only_in_realtime_mode(self) -> None:
        """Keep Live Data outside the sidebar and other application modes."""
        source = (ROOT / 'app.py').read_text(encoding='utf-8')
        tree = ast.parse(source)
        calls: Dict[str, list[ast.Call]] = {}
        for name in ('render_world_sidebar', 'render_live_world_map'):
            calls[name] = [node for node in ast.walk(tree)
                if isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name) and node.func.id == name]
            self.assertEqual(1, len(calls[name]))
        branches = [node for node in ast.walk(tree)
            if isinstance(node, ast.If) and isinstance(node.test, ast.Compare)
            and isinstance(node.test.left, ast.Name)
            and node.test.left.id == 'mode'
            and any(isinstance(value, ast.Constant) and value.value == 'Realtime'
                for value in node.test.comparators)]
        self.assertEqual(1, len(branches))
        branch = branches[0]
        nested_calls = set()
        for node in ast.walk(branch):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                nested_calls.add(node.func.id)
        self.assertIn('render_world_sidebar', nested_calls)
        self.assertIn('render_live_world_map', nested_calls)
        self.assertIn('st.columns( [ 0.40, 0.60 ], border=True', source)
        self.assertNotIn("st.markdown( '#### 📡 Live Data' )", source)

    def test_live_controls_are_grouped_without_duplicate_widget_keys(self) -> None:
        """Retain the source and action keys in four separate expanders."""
        tree = ast.parse((ROOT / 'realtime.py').read_text(encoding='utf-8'))
        method = next(node for node in tree.body
            if isinstance(node, ast.FunctionDef) and node.name == 'render_world_sidebar')
        expanders = [node for node in ast.walk(method)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
            and node.func.attr == 'expander'
            and isinstance(node.args[0], ast.Constant)]
        labels = [node.args[0].value for node in expanders]
        self.assertEqual([
            '🌐 Live Layers', '🎯 Tracking & Measurements',
            'Additional Layers', 'AI & Advanced Tools'], labels)
        keys = [keyword.value.value for node in ast.walk(method)
            if isinstance(node, ast.Call)
            for keyword in node.keywords
            if keyword.arg == 'key' and isinstance(keyword.value, ast.Constant)
            and isinstance(keyword.value.value, str)]
        self.assertEqual(len(keys), len(set(keys)))
        for name in ('live_world_enabled', 'live_world_aircraft', 'live_world_vessels',
                'live_world_satellites', 'live_world_fires', 'live_world_earthquakes',
                'live_world_infrastructure', 'live_world_cameras',
                'live_world_map_layers', 'live_world_tracking',
                'live_world_measurements', 'live_world_refresh', 'live_world_clear'):
            self.assertIn(name, keys)

    def test_empty_basemap_and_entities_editor_are_rendered_without_fetch(self) -> None:
        """A disabled Live World map still displays an empty right-side workspace."""
        tree = ast.parse((ROOT / 'realtime.py').read_text(encoding='utf-8'))
        method = next(node for node in tree.body
            if isinstance(node, ast.FunctionDef) and node.name == 'render_empty_world_map')
        namespace: Dict[str, Any] = {
            'st': SimpleNamespace(
                session_state={'live_world_zoom': 4},
                pydeck_chart=lambda deck, use_container_width: records.append('map'),
                markdown=lambda title: records.append('heading'),
                data_editor=lambda data, key, use_container_width, disabled, hide_index:
                    records.append('editor')),
            'pdk': SimpleNamespace(
                Deck=lambda **values: values,
                ViewState=lambda **values: values),
            'is_valid_world_coordinates': lambda lat, lng: True,
            'entities_to_dataframe': lambda items: pd.DataFrame(
                columns=['EntityId', 'EntityType']),
            'generate_world_display': lambda df_frame: df_frame,
        }
        records: list[str] = []
        module = ast.fix_missing_locations(ast.Module(body=[method], type_ignores=[]))
        exec(compile(module, 'realtime.py', 'exec'), namespace)
        namespace['render_empty_world_map'](0.0, 0.0)
        self.assertEqual(['map', 'heading', 'editor'], records)

    def test_live_entities_editor_is_directly_under_the_chart(self) -> None:
        """Keep all detailed source tabs as well as the top-level entity editor."""
        source = (ROOT / 'realtime.py').read_text(encoding='utf-8')
        section = source.split('def render_live_world_map(', 1)[1].split(
            'def generate_world_display(', 1)[0]
        self.assertLess(section.index('st.pydeck_chart( deck'),
            section.index("key='live_world_map_entities_editor'"))
        self.assertLess(section.index("key='live_world_map_entities_editor'"),
            section.index("(entities_tab, aircraft_tab"))
        self.assertIn("key='live_world_aircraft_table'", section)
        self.assertIn("key='live_world_vessel_table'", section)
        self.assertIn("key='live_world_history_latest_table'", section)


if __name__ == '__main__':
    unittest.main()
