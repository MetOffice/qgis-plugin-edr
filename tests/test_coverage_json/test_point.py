import typing

from qgis.core import Qgis, QgsCategorizedSymbolRenderer, QgsMapLayer, QgsVectorLayer, QgsWkbTypes

from edr_plugin.coveragejson.coverage import Coverage
from edr_plugin.coveragejson.coverage_json_reader import CoverageJSONReader
from edr_plugin.coveragejson.utils import prepare_vector_render


def test_point(data_dir):
    filename = data_dir / "vector_point.covjson"

    assert filename.exists()

    coverage_json = CoverageJSONReader(filename)

    assert coverage_json.domain_type == "Point"
    assert coverage_json.coverages_count == 1

    coverage = coverage_json.coverage()
    assert isinstance(coverage, Coverage)
    assert coverage.domain_type == "Point"

    assert coverage.has_t is False
    assert coverage.has_z is False
    assert coverage.has_composite_axe is False

    assert coverage.parameter_names == ["Pop_Density"]

    for param in coverage.parameter_names:
        assert coverage.parameter_ranges(param)
        assert isinstance(coverage.parameter_ranges(param), typing.Dict)

    layers = coverage.vector_layers()

    assert isinstance(layers, typing.List)
    assert len(layers) == 1
    assert isinstance(layers[0], QgsVectorLayer)
    assert layers[0].dataProvider().featureCount() == 1

    layers = coverage_json.map_layers()

    assert isinstance(layers, typing.List)
    assert len(layers) == 1
