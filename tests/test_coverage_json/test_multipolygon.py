import typing

from qgis.core import (
    QgsCategorizedSymbolRenderer,
    QgsMapLayer,
    QgsVectorLayer,
    QgsWkbTypes,
)

from edr_plugin.coveragejson.coverage import Coverage
from edr_plugin.coveragejson.coverage_json_reader import CoverageJSONReader
from edr_plugin.coveragejson.utils import prepare_vector_render


def test_simple_multipolygon(data_dir):
    filename = data_dir / "vector_multipolygon.covjson"

    assert filename.exists()

    coverage_json = CoverageJSONReader(filename)

    assert coverage_json.domain_type == "MultiPolygon"
    assert coverage_json.coverages_count == 1

    coverage = coverage_json.coverage()
    assert isinstance(coverage, Coverage)

    assert coverage.has_t is False
    assert coverage.has_z is False
    assert coverage.has_composite_axe is True

    assert coverage.parameter_names == ["Building_Type", "Building_Levels"]

    for param in coverage.parameter_names:
        assert coverage.has_t_in_data(param) is False
        assert coverage.has_z_in_data(param) is False

        assert coverage.parameter_ranges(param)
        assert isinstance(coverage.parameter_ranges(param), typing.Dict)

    layers = coverage.vector_layers()

    assert isinstance(layers, typing.List)
    assert len(layers) == 1
    assert isinstance(layers[0], QgsVectorLayer)
    assert layers[0].fields().count() == 2
    assert layers[0].dataProvider().featureCount() == 1078
    assert layers[0].crs().authid() == "EPSG:4326"
    assert layers[0].wkbType() == QgsWkbTypes.MultiPolygon

    layers = coverage_json.map_layers()

    assert isinstance(layers, typing.List)
    assert len(layers) == 1
    assert isinstance(layers[0], QgsMapLayer)


def test_create_renderer(data_dir):
    filename = data_dir / "vector_multipolygon.covjson"

    assert filename.exists()

    coverage_json = CoverageJSONReader(filename)

    coverage = coverage_json.coverage()
    assert isinstance(coverage, Coverage)

    layer = coverage.vector_layers()[0]
    assert layer.isValid()

    # only existing categories
    renderer = prepare_vector_render(layer, coverage.parameters, False)

    assert isinstance(renderer, QgsCategorizedSymbolRenderer)
    assert len(renderer.categories()) == 13

    # +1 category for no value
    renderer = prepare_vector_render(layer, coverage.parameters)

    assert isinstance(renderer, QgsCategorizedSymbolRenderer)
    assert len(renderer.categories()) == 14
