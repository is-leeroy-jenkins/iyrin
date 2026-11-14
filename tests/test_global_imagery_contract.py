"""Mock-backed regression tests for both NASA GIBS image retrieval paths."""

import ast
from contextlib import nullcontext
import io
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from typing import Any
import unittest
from unittest.mock import MagicMock


ROOT = Path(__file__).resolve().parents[1]


class GlobalImageryContractTests(unittest.TestCase):
    """Verify imagery output, resource cleanup and figure-return contracts."""

    def setUp(self) -> None:
        """Compile real provider methods against deterministic external SDK stubs."""
        tree = ast.parse((ROOT / 'fetchers.py').read_text(encoding='utf-8'))
        cls = next(node for node in tree.body
                   if isinstance(node, ast.ClassDef) and node.name == 'GlobalImagery')
        methods = [node for node in cls.body
                   if isinstance(node, ast.FunctionDef)
                   and node.name in ('fetch_map_services', 'fetch_mercator_map')]
        self.assertEqual(2, len(methods))

        self.wms = MagicMock()
        self.wms.getmap.return_value.read.return_value = b'PNG data'
        self.wms_factory = MagicMock(return_value=self.wms)
        self.photo = MagicMock()
        self.photo.copy.return_value = 'decoded-image'
        self.image_module = SimpleNamespace(
            Image=object, open=lambda path: nullcontext(self.photo))
        self.http_response = MagicMock(content=b'PNG bytes')
        self.http = SimpleNamespace(get=MagicMock(return_value=self.http_response))
        self.grid = SimpleNamespace()
        self.axes = MagicMock()
        self.axes.gridlines.return_value = self.grid
        self.figure = MagicMock()
        self.figure.add_subplot.return_value = self.axes
        self.plot = SimpleNamespace(
            imread=MagicMock(return_value='pixels'),
            figure=MagicMock(return_value=self.figure),
            show=MagicMock(),
        )
        self.crs = SimpleNamespace(
            Mercator=MagicMock(return_value='mercator-projection'),
            PlateCarree=MagicMock(return_value='plate-carree'),
        )
        self.logger = MagicMock()
        namespace = {
            'Any': Any, 'Path': Path, 'Image': self.image_module,
            'WebMapService': self.wms_factory,
            'requests': self.http, 'cartopy_crs': self.crs,
            'plt': self.plot, 'mticker': SimpleNamespace(FixedLocator=lambda xs: xs),
            'io': io, 'LONGITUDE_FORMATTER': 'longitude',
            'LATITUDE_FORMATTER': 'latitude',
            'Error': RuntimeError, 'Logger': lambda: self.logger,
        }
        wrapper = ast.ClassDef(
            name='GlobalImageryTest', bases=[], keywords=[],
            body=methods, decorator_list=[])
        module = ast.fix_missing_locations(ast.Module(body=[wrapper], type_ignores=[]))
        exec(compile(module, str(ROOT / 'fetchers.py'), 'exec'), namespace)
        self.provider = namespace['GlobalImageryTest']()
        self.provider.headers = {'User-Agent': 'test'}
        self.provider.timeout = 20

    def test_map_service_writes_png_and_returns_decoded_image(self) -> None:
        """Preserve the local PNG output and return a detached image object."""
        with TemporaryDirectory() as tempdir:
            original = os.getcwd()
            try:
                os.chdir(tempdir)
                result = self.provider.fetch_map_services()
                path = Path('python-examples/MODIS_Terra_CorrectedReflectance_TrueColor.png')
                self.assertEqual(b'PNG data', path.read_bytes())
                self.assertEqual('decoded-image', result)
            finally:
                os.chdir(original)

    def test_mercator_fetch_uses_http_timeout_and_returns_figure(self) -> None:
        """Decode PNG bytes and return the plotted figure with member-based API args."""
        figure = self.provider.fetch_mercator_map()
        self.assertIs(self.figure, figure)
        self.http.get.assert_called_once_with(
            self.provider.url, params=self.provider.params,
            headers=self.provider.headers, timeout=self.provider.timeout)
        self.http_response.raise_for_status.assert_called_once()
        self.plot.imread.assert_called_once()
        self.plot.show.assert_called_once()
        self.figure.add_subplot.assert_called_once()


if __name__ == '__main__':
    unittest.main()
