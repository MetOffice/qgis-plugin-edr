import typing

from qgis.core import QgsMapLayer, QgsVectorLayer, QgsWkbTypes

from edr_plugin.coveragejson.coverage_json_reader import CoverageJSONReader


def test_simple_grid(data_dir):
    filename = data_dir / "vector_multipolygon.covjson"

    assert filename.exists()

    coverage_json = CoverageJSONReader(filename)

    assert coverage_json.domain_type == "MultiPolygon"
    assert coverage_json.has_t is False
    assert coverage_json.has_z is False
    assert coverage_json.has_composite_axe is True

    assert coverage_json.parameter_names == ["Building_Type", "Building_Levels"]

    for param in coverage_json.parameter_names:
        assert coverage_json.parameter(param)
        assert isinstance(coverage_json.parameter(param), typing.Dict)

        assert coverage_json.has_t_in_data(param) is False
        assert coverage_json.has_z_in_data(param) is False

        assert coverage_json.parameter_ranges(param)
        assert isinstance(coverage_json.parameter_ranges(param), typing.Dict)

    layers = coverage_json.vector_layers()

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
