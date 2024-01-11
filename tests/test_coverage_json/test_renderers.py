from qgis.core import QgsCategorizedSymbolRenderer, QgsRasterShader

from edr_plugin.coveragejson.coverage_json_reader import CoverageJSONReader
from edr_plugin.coveragejson.utils import prepare_raster_shader, prepare_vector_render


def test_raster_shader_1(data_dir):
    filename = data_dir / "grid_single_variable.covjson"

    assert filename.exists()

    coverage_json = CoverageJSONReader(filename)
    coverage = coverage_json.coverage()

    parameter_name = "Pop_Density"

    shader = prepare_raster_shader(coverage.parameter_info(parameter_name), coverage.parameter_ranges(parameter_name))

    assert shader
    assert isinstance(shader, QgsRasterShader)
    assert len(shader.rasterShaderFunction().legendSymbologyItems()) == 27
    assert shader.minimumValue() == 0.0
    assert shader.maximumValue() == 25000.0


def test_raster_shader_2(data_dir):
    filename = data_dir / "grid_time_2_variables.covjson"

    assert filename.exists()

    coverage_json = CoverageJSONReader(filename)
    coverage = coverage_json.coverage()

    parameter_name = "air_pressure_at_sea_level"

    shader = prepare_raster_shader(coverage.parameter_info(parameter_name), coverage.parameter_ranges(parameter_name))

    assert shader is None

    parameter_name = "air_temperature"

    shader = prepare_raster_shader(coverage.parameter_info(parameter_name), coverage.parameter_ranges(parameter_name))

    assert shader
    assert isinstance(shader, QgsRasterShader)
    assert len(shader.rasterShaderFunction().legendSymbologyItems()) == 52
    assert shader.minimumValue() == 286.52
    assert shader.maximumValue() == 303.0


def test_raster_shader_3(data_dir):
    filename = data_dir / "coveragecollection_grids.covjson"

    assert filename.exists()

    coverage_json = CoverageJSONReader(filename)
    coverage = coverage_json.coverage()

    parameter_name = "u-component-storm-motion"

    shader = prepare_raster_shader(coverage.parameter_info(parameter_name), coverage.parameter_ranges(parameter_name))

    assert shader is None


def test_raster_shader_4(data_dir):
    filename = data_dir / "grid_custom_domain.covjson"

    assert filename.exists()

    coverage_json = CoverageJSONReader(filename)
    coverage = coverage_json.coverage()

    parameter_name = "u"

    shader = prepare_raster_shader(coverage.parameter_info(parameter_name), coverage.parameter_ranges(parameter_name))

    assert shader is None


def test_vector_renderer_1(data_dir):
    filename = data_dir / "vector_multipolygon.covjson"

    assert filename.exists()

    coverage_json = CoverageJSONReader(filename)
    coverage = coverage_json.coverage()

    layer = coverage.vector_layers()[0]

    # only existing categories
    renderer = prepare_vector_render(layer, coverage.parameters, False)

    assert isinstance(renderer, QgsCategorizedSymbolRenderer)
    assert len(renderer.categories()) == 13

    # +1 category for no value
    renderer = prepare_vector_render(layer, coverage.parameters)

    assert isinstance(renderer, QgsCategorizedSymbolRenderer)
    assert len(renderer.categories()) == 14
