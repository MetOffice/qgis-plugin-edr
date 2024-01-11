import typing

import numpy as np
from qgis.core import QgsMapLayer, QgsRasterLayer
from qgis.PyQt.QtCore import QDateTime

from edr_plugin.coveragejson.coverage import Coverage
from edr_plugin.coveragejson.coverage_json_reader import CoverageJSONReader
from edr_plugin.coveragejson.utils import ArrayWithTZ


def test_grid_custom_domain(data_dir):
    filename = data_dir / "grid_custom_domain.covjson"

    assert filename.exists()

    coverage_json = CoverageJSONReader(filename)

    assert coverage_json.domain_type == "Grid"
    assert coverage_json.coverages_count == 1

    coverage = coverage_json.coverage()
    assert isinstance(coverage, Coverage)

    assert coverage.has_t is True
    assert coverage.has_z is True
    assert "number" in coverage.axes_names

    parameter_name = "u"

    assert coverage.parameter_names == [parameter_name, "v"]

    assert coverage.parameter_ranges(parameter_name)
    assert isinstance(coverage.parameter_ranges(parameter_name), typing.Dict)

    x_values = coverage.axe_values("x")
    y_values = coverage.axe_values("y")

    assert len(x_values) == 4
    assert len(y_values) == 2

    rasters = coverage._format_values_into_rasters(parameter_name)
    assert isinstance(rasters, typing.Dict)
    for key, raster in rasters.items():
        assert isinstance(raster, ArrayWithTZ)
        assert isinstance(raster.array, np.ndarray)
        assert raster.z
        assert raster.time
        assert raster.array.shape == (2, 4)

    layers = coverage.raster_layers(parameter_name)
    layers_count = len(coverage.axe_values("number")) * len(coverage.axe_values("t")) * len(coverage.axe_values("z"))

    assert isinstance(layers, typing.List)
    assert len(layers) == layers_count
    assert isinstance(layers[0], QgsRasterLayer)

    layers = coverage_json.map_layers()

    assert isinstance(layers, typing.List)
    assert len(layers) == layers_count * len(coverage.parameter_names)
    assert isinstance(layers[0], QgsMapLayer)
