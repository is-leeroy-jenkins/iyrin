"""Regress Live World entity construction and column-preserving DataFrames."""

import ast
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List
import unittest


ROOT = Path(__file__).resolve().parents[1]


class FakeFrame:
    """Capture entity rows and the unchanged Live World column contract."""

    def __init__(self, data: list | None = None, columns: list | None = None) -> None:
        """Store the supplied entity records without changing their values."""
        self.data = data if data is not None else []
        self.columns = columns if columns is not None else []


class RealtimeEntityContractTests(unittest.TestCase):
    """Ensure replacing the dataclass retains normalized entity behavior."""

    @classmethod
    def setUpClass(cls) -> None:
        """Load production entity and DataFrame functions without UI dependencies."""
        source = (ROOT / 'realtime.py').read_text(encoding='utf-8')
        tree = ast.parse(source)
        entity = next(node for node in tree.body
                      if isinstance(node, ast.ClassDef) and node.name == 'GeoEntity')
        services = next(node for node in tree.body
                        if isinstance(node, ast.ClassDef)
                        and node.name == 'LiveWorldEntities')
        convert = next(node for node in services.body
                       if isinstance(node, ast.FunctionDef)
                       and node.name == 'entities_to_dataframe')
        convert.decorator_list = []
        cls.has_dataclass_decorator = bool(entity.decorator_list)
        namespace = {'Any': Any, 'Dict': Dict, 'List': List,
                     'pd': SimpleNamespace(DataFrame=FakeFrame)}
        module = ast.fix_missing_locations(ast.Module(
            body=[entity, convert], type_ignores=[]))
        exec(compile(module, str(ROOT / 'realtime.py'), 'exec'), namespace)
        cls.GeoEntity = namespace['GeoEntity']
        cls.convert = staticmethod(namespace['entities_to_dataframe'])

    def test_entity_constructor_preserves_all_original_fields(self) -> None:
        """Verify original keyword parameters and returned column values."""
        entity = self.GeoEntity(
            entity_id='A1', entity_type='Aircraft', name='Example',
            latitude=38.5, longitude=-77.0, altitude=1000.0, heading=90.0,
            speed=120.0, timestamp='2025-01-01T00:00:00Z', source='Test',
            metadata={'flight': 'A1'})
        df_entities = self.convert([entity])
        self.assertEqual(11, len(df_entities.columns))
        self.assertEqual('A1', df_entities.data[0]['EntityId'])
        self.assertEqual(38.5, df_entities.data[0]['Latitude'])
        self.assertEqual({'flight': 'A1'}, df_entities.data[0]['Metadata'])

    def test_empty_entities_preserve_schema(self) -> None:
        """Retain existing columns even when there are no observations."""
        df_entities = self.convert([])
        self.assertEqual(11, len(df_entities.columns))
        self.assertEqual([], df_entities.data)

    def test_entity_is_no_longer_a_dataclass(self) -> None:
        """Enforce the user's no-dataclass class convention."""
        self.assertFalse(self.has_dataclass_decorator)
        self.assertTrue(callable(self.GeoEntity))


if __name__ == '__main__':
    unittest.main()
