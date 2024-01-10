import typing
from pathlib import Path

import numpy as np
from osgeo import gdal
from qgis.core import (
    QgsCategorizedSymbolRenderer,
    QgsColorRampShader,
    QgsCoordinateReferenceSystem,
    QgsDateTimeRange,
    QgsFeatureRenderer,
    QgsField,
    QgsGeometry,
    QgsLineString,
    QgsPoint,
    QgsPolygon,
    QgsProject,
    QgsRasterLayer,
    QgsRasterShader,
    QgsRendererCategory,
    QgsSingleBandPseudoColorRenderer,
    QgsSymbol,
    QgsVectorLayer,
)
from qgis.PyQt.QtCore import QDateTime, QVariant
from qgis.PyQt.QtGui import QColor


class ArrayWithTZ:
    """Simple class to hold raster data with time and z information."""

    def __init__(
        self, array: np.ndarray, time: typing.Optional[QDateTime] = None, z: typing.Optional[float] = None
    ) -> None:
        if time:
            if time.isValid():
                self.time = time
        else:
            self.time = None
        self.z = z
        self.array = array


class RasterTemplate:
    def __init__(
        self, x_coords: typing.List[float], y_coords: typing.List[float], data_type: int, crs_wkt: str, bands: int = 1
    ) -> None:
        """Basic raster template to be used for saving raster data."""
        x_min = x_coords[0] - (x_coords[1] - x_coords[0]) / 2
        x_max = x_coords[-1] + (x_coords[-1] - x_coords[-2]) / 2

        y_min = y_coords[0] - (y_coords[1] - y_coords[0]) / 2
        y_max = y_coords[-1] + (y_coords[-1] - y_coords[-2]) / 2

        self.geotransform = [x_min, (x_max - x_min) / len(x_coords), 0, y_max, 0, -((y_max - y_min) / len(y_coords))]

        self.columns = len(x_coords)
        self.rows = len(y_coords)

        self.bands = bands

        self.data_type = data_type

        self.crs_wkt = crs_wkt

        self.driver = gdal.GetDriverByName("GTiff")

    def save_empty_raster(self, filename: Path) -> gdal.Dataset:
        """Save empty raster with given filename."""
        dp: gdal.Dataset = self.driver.Create(filename.as_posix(), self.columns, self.rows, self.bands, self.data_type)

        dp.SetGeoTransform(self.geotransform)
        dp.SetProjection(self.crs_wkt)

        return dp

    @staticmethod
    def write_array_to_band(
        dp: gdal.Dataset,
        np_array: np.ndarray,
        band_number: int = 1,
        no_data_value: float = -9999999,
    ) -> None:
        """Write given numpy array to given band. No data value is set to -9999999 by default."""
        band: gdal.Band = dp.GetRasterBand(band_number)
        band.SetNoDataValue(no_data_value)

        np_array[np_array == None] = no_data_value

        values = (np_array != no_data_value).sum()
        if values == 0:
            raise ValueError("No resulting data in the Query.")

        np_array = np.flip(np_array, 0)

        band.WriteArray(np_array)

        band = None


def prepare_raster_shader(
    parameter_info: typing.Dict, parameter_ranges: typing.Dict
) -> typing.Optional[QgsRasterShader]:
    """Create raster shader for given parameter if it is specified in CoverageJSON."""

    if "categoryEncoding" not in parameter_info:
        return None

    data = np.array(parameter_ranges["values"])
    data = data[data != np.array(None)]

    color_ramp_items: typing.List[QgsColorRampShader.ColorRampItem] = []

    max_value = np.max(data)
    max_legend_value = 0

    if "categoryEncoding" in parameter_info:
        for element in parameter_info["categoryEncoding"]:
            color_ramp_items.append(
                QgsColorRampShader.ColorRampItem(
                    parameter_info["categoryEncoding"][element],
                    QColor(element),
                    f'{parameter_info["categoryEncoding"][element]}',
                )
            )

            if parameter_info["categoryEncoding"][element] > max_value:
                max_legend_value = parameter_info["categoryEncoding"][element]
                break

    new_color_ramp_shader = QgsColorRampShader(np.min(data), np.max(data))
    new_color_ramp_shader.setColorRampType(QgsColorRampShader.Type.Interpolated)
    new_color_ramp_shader.setColorRampItemList(color_ramp_items)

    raster_shader = QgsRasterShader()
    raster_shader.setRasterShaderFunction(new_color_ramp_shader)
    raster_shader.setMinimumValue(np.min(data))
    raster_shader.setMaximumValue(max_legend_value)

    return raster_shader


def set_layer_render_from_shader(layer: QgsRasterLayer, shader: typing.Optional[QgsRasterShader]) -> None:
    """Set layer render to given shader."""
    if shader:
        renderer = QgsSingleBandPseudoColorRenderer(layer.dataProvider(), 1, shader)
        renderer.setClassificationMin(shader.minimumValue())
        renderer.setClassificationMax(shader.maximumValue())
        layer.setRenderer(renderer)


def set_project_time_range(time_range: QgsDateTimeRange, time_step: typing.Optional[float] = 3600) -> None:
    """Sets project time range and time step. Time step is in seconds (with default being one hour)."""
    time_settings = QgsProject.instance().timeSettings()
    if time_range:
        time_settings.setTemporalRange(time_range)
    if time_step:
        time_settings.setTimeStep(time_step)


def feature_attributes(ranges: typing.Dict, number_of_features: int) -> typing.List[typing.List[typing.Any]]:
    """Prepare fields from given parameter ranges."""

    features_attributes: typing.List[typing.List[typing.Any]] = [[] for _ in range(number_of_features)]

    for key in ranges.keys():
        if ranges[key]["shape"][0] != number_of_features:
            raise ValueError(f"Number of features does not match number of values for element `{key}`.")

        for i, value in enumerate(ranges[key]["values"]):
            features_attributes[i].append(value)

    return features_attributes


def composite_to_geometries(composite_geom: typing.Dict) -> typing.List[QgsGeometry]:
    geom_type = composite_geom["dataType"]
    json_geoms = composite_geom["values"]

    geometries: typing.List[QgsGeometry] = []

    for json_geom in json_geoms:
        if geom_type == "polygon":
            geometries.append(json_to_polygon(json_geom))

    return geometries


def json_to_polygon(json_geom: typing.List) -> QgsGeometry:
    polygon = QgsPolygon()

    for i, ring in enumerate(json_geom):
        linestring = QgsLineString()
        for point in ring:
            linestring.addVertex(QgsPoint(point[0], point[1]))

        if i == 0:
            polygon.setExteriorRing(linestring)
        else:
            polygon.addInteriorRing(linestring)

    return QgsGeometry(polygon)


def prepare_fields(
    ranges: typing.Dict, parameter_units: typing.Optional[typing.Dict[str, str]] = None
) -> typing.List[QgsField]:
    fields = []

    for parameter in ranges.keys():
        param_type = ranges[parameter]["dataType"]

        parameter_name = parameter

        if parameter_units:
            if parameter_name in parameter_units:
                parameter_name = f"{parameter_name} ({parameter_units[parameter_name]})"

        fields.append(QgsField(parameter_name, parameter_data_type_to_qgis_type(param_type)))

    return fields


def parameter_data_type_to_qgis_type(param_type: str) -> QVariant.Type:
    if param_type == "integer":
        return QVariant.Type.Int
    elif param_type == "float":
        return QVariant.Type.Double
    elif param_type == "string":
        return QVariant.Type.String

    raise ValueError(f"Unknown parameter data type: {param_type}")


def prepare_vector_layer(
    wkb_type: str, crs: QgsCoordinateReferenceSystem, layer_name: str = "CoverageJSON"
) -> QgsVectorLayer:
    if crs.isValid():
        crs_str = crs.authid()
    else:
        crs_str = "EPSG:4326"

    layer = QgsVectorLayer(f"{wkb_type}?crs={crs_str}", layer_name, "memory")

    if not layer.isValid():
        raise ValueError(f"Layer {layer_name} is not valid.")

    return layer


def find_field(field_name_start: str, layer: QgsVectorLayer) -> str:
    """Find field name in layer based on start of field name."""
    fields_names = layer.fields().names()

    for name in fields_names:
        if name.startswith(field_name_start):
            return name

    return ""


def prepare_vector_render(
    layer: QgsVectorLayer, parameters: typing.Dict, add_category_for_no_value: bool = True
) -> QgsFeatureRenderer:
    """Create render for given vector layer based on given parameters. Optionally add category for no value.
    If `parameters` is missing required values return original layer renderer."""

    renderer = layer.renderer()

    if len(parameters) < 1:
        return renderer

    variable = parameters[list(parameters.keys())[0]]

    variable_name = find_field(list(parameters.keys())[0], layer)

    if "categories" not in variable["observedProperty"]:
        return layer.renderer()
    else:
        categories = variable["observedProperty"]["categories"]
        category_encoding = variable["categoryEncoding"]

        renderer = QgsCategorizedSymbolRenderer(variable_name)

        for category in categories:
            value = category["id"]
            if value in category_encoding:
                value = category_encoding[value]

            symbol = QgsSymbol.defaultSymbol(layer.geometryType())
            symbol.setColor(QColor(category["preferredColor"]))

            label = category["label"][list(category["label"].keys())[0]]

            category = QgsRendererCategory(value, symbol, label)
            renderer.addCategory(category)

        if add_category_for_no_value:
            symbol = QgsSymbol.defaultSymbol(layer.geometryType())
            symbol.setColor(QColor("#ff00ff"))
            category = QgsRendererCategory(None, symbol, "No data")
            renderer.addCategory(category)

    return renderer
