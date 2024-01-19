import typing

import numpy as np
import pytest
from qgis.core import QgsMapLayer, QgsRasterLayer
from qgis.PyQt.QtCore import QDateTime

from edr_plugin.coveragejson.coverage import Coverage
from edr_plugin.coveragejson.coverage_json_reader import CoverageJSONReader
from edr_plugin.coveragejson.utils import ArrayWithTZ


def test_simple_grid(data_dir):
    filename = data_dir / "grid_single_variable.covjson"

    assert filename.exists()

    parameter_name = "Pop_Density"

    coverage_json = CoverageJSONReader(filename)

    assert coverage_json.file_size_mg == pytest.approx(2.34, 0.01)
    assert coverage_json.domain_type == "Grid"
    assert coverage_json.coverages_count == 1

    coverage = coverage_json.coverage()
    assert isinstance(coverage, Coverage)

    assert coverage.has_t is False
    assert coverage.has_z is False

    assert coverage.parameter_names == [parameter_name]

    assert coverage.parameter_ranges(parameter_name)
    assert isinstance(coverage.parameter_ranges(parameter_name), typing.Dict)

    x_values = coverage.axe_values("x")
    y_values = coverage.axe_values("y")

    assert len(x_values) == 432
    assert len(y_values) == 270

    rasters = coverage._format_values_into_rasters(parameter_name)
    assert isinstance(rasters, typing.Dict)
    for key, raster in rasters.items():
        assert isinstance(raster, ArrayWithTZ)
        assert isinstance(raster.array, np.ndarray)
        assert raster.z is None
        assert raster.time is None
        assert raster.array.shape == (270, 432)

    layers = coverage.raster_layers(parameter_name)

    assert isinstance(layers, typing.List)
    assert len(layers) == 1
    assert isinstance(layers[0], QgsRasterLayer)

    layers = coverage_json.map_layers()

    assert isinstance(layers, typing.List)
    assert len(layers) == 1
    assert isinstance(layers[0], QgsMapLayer)


def test_time_2variables_grid(data_dir):
    filename = data_dir / "grid_time_2_variables.covjson"

    assert filename.exists()

    coverage_json = CoverageJSONReader(filename)

    assert coverage_json.file_size_mg == pytest.approx(0.14, 0.01)
    assert coverage_json.domain_type == "Grid"
    assert coverage_json.coverages_count == 1

    coverage = coverage_json.coverage()
    assert isinstance(coverage, Coverage)

    assert coverage.has_t is True
    assert coverage.has_z is False

    x_values = coverage.axe_values("x")
    y_values = coverage.axe_values("y")
    t_values = coverage.axe_values("t")

    assert len(x_values) == 16
    assert len(y_values) == 14
    assert len(t_values) == 13

    assert coverage.parameter_names == ["air_pressure_at_sea_level", "air_temperature"]

    parameter_name = "air_temperature"

    assert coverage.parameter_ranges(parameter_name)
    assert isinstance(coverage.parameter_ranges(parameter_name), typing.Dict)

    rasters = coverage._format_values_into_rasters(parameter_name)
    assert isinstance(rasters, typing.Dict)

    for key, raster in rasters.items():
        assert isinstance(raster, ArrayWithTZ)
        assert isinstance(raster.array, np.ndarray)
        assert raster.z is None
        assert isinstance(raster.time, QDateTime)
        assert raster.array.shape == (14, 16)

    layers = coverage.raster_layers(parameter_name)

    assert isinstance(layers, typing.List)
    assert len(layers) == 13
    for layer in layers:
        assert isinstance(layer, QgsRasterLayer)

    layers = coverage_json.map_layers()

    assert isinstance(layers, typing.List)
    assert len(layers) == 26
    for layer in layers:
        assert isinstance(layer, QgsMapLayer)


def test_two_dimensions_data(data_dir):
    filename = data_dir / "grid_time_z_variable.covjson"

    assert filename.exists()

    coverage_json = CoverageJSONReader(filename)

    assert coverage_json.file_size_mg == pytest.approx(0.237, 0.01)
    assert coverage_json.domain_type == "Grid"
    assert coverage_json.coverages_count == 1

    coverage = coverage_json.coverage()
    assert isinstance(coverage, Coverage)

    assert coverage.has_t is True
    assert coverage.has_z is True

    x_values = coverage.axe_values("x")
    y_values = coverage.axe_values("y")
    t_values = coverage.axe_values("t")
    z_values = coverage.axe_values("z")

    assert len(x_values) == 53
    assert len(y_values) == 48
    assert len(t_values) == 2
    assert len(z_values) == 2

    assert coverage.parameter_names == ["soil_temperature"]

    parameter_name = "soil_temperature"

    assert coverage.parameter_ranges(parameter_name)
    assert isinstance(coverage.parameter_ranges(parameter_name), typing.Dict)

    rasters = coverage._format_values_into_rasters(parameter_name)
    assert isinstance(rasters, typing.Dict)

    for key, raster in rasters.items():
        assert isinstance(raster, ArrayWithTZ)
        assert isinstance(raster.array, np.ndarray)
        assert isinstance(raster.time, QDateTime)
        assert raster.array.shape == (48, 53)

    layers = coverage.raster_layers(parameter_name)

    assert isinstance(layers, typing.List)
    assert len(layers) == 4
    for layer in layers:
        assert isinstance(layer, QgsRasterLayer)

    layers = coverage_json.map_layers()

    assert isinstance(layers, typing.List)
    assert len(layers) == 4
    for layer in layers:
        assert isinstance(layer, QgsMapLayer)
