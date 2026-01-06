import itertools
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
from qgis.PyQt.QtCore import QDateTime, QMetaType
from qgis.PyQt.QtGui import QColor


class DimensionAccessor:
    """Class for handling dimensions for complex Grid Coverages."""

    def __init__(self, parameter_ranges: typing.Dict, axes: typing.Dict) -> None:
        """Build based on parameter ranges (values and axes) and global axes definition."""
        self.axes = axes
        self.parameter_axes_names = parameter_ranges["axisNames"]

        self.axes_values: typing.Dict[str, typing.Any] = {}
        self.axes_indices: typing.Dict[str, list[int]] = {}
        for axe in self.parameter_axes_names:
            if "x" == axe:
                self.axes_values["space"] = [...]
                self.axes_indices["space"] = [...]
            elif "y" == axe:
                continue
            else:
                self.axes_values[axe] = self._axe_values(axe)
                self.axes_indices[axe] = list(range(0, len(self._axe_values(axe))))

        self._iter_product = itertools.product(*self.axes_indices.values())

    @property
    def iter_product(self) -> itertools.product:
        """Iter tuples of dimension indices with x and y dimensions listed as ellipsis."""
        return self._iter_product

    @staticmethod
    def _axe_values_as_list(axe_dict: typing.Dict) -> typing.List[float]:
        """Extract axe values from axes element."""
        if "values" in axe_dict:
            return axe_dict["values"]
        elif "start" in axe_dict and "stop" in axe_dict and "num" in axe_dict:
            return np.linspace(axe_dict["start"], axe_dict["stop"], axe_dict["num"]).tolist()

        raise ValueError("Unsupported axe definition.")

    def _axe_values(self, axe: str) -> typing.List[float]:
        """Extract axe values for given axe."""

        if axe not in self.axes_names:
            raise ValueError(f"Missing `f{axe}` axis of data.")

        return self._axe_values_as_list(self.axes[axe])

    @property
    def axes_names(self) -> typing.List[str]:
        """Get axes names."""
        return [x for x in self.axes.keys()]

    def t(self, dimension_values: itertools.product) -> typing.Optional[str]:
        """Return time for given dimension values."""
        return self.dimension_value("t", dimension_values)

    def z(self, dimension_values: itertools.product) -> typing.Optional[str]:
        """Return z for given dimension values."""
        z = self.dimension_value("z", dimension_values)
        return z

    def dimension_value(self, dimension: str, dimension_values: itertools.product) -> typing.Optional[str]:
        """Return specified dimension from dimension values."""
        axes = list(self.axes_values.keys())
        if dimension in axes:
            value_index = list(dimension_values)[axes.index(dimension)]
            return self.axes_values[dimension][value_index]
        return None

    def dimensions_to_string_description(self, dimension_values: itertools.product) -> str:
        """For dimension values return name for the dimension.
        This consists of axes names and values. Axes x and y are skipped and not used in the name."""
        names = []
        for axe in self.axes_values.keys():
            if "space" == axe:
                continue
            names.append(f"{axe}_{self.dimension_value(axe, dimension_values)}")

        return "_".join(names)


class ArrayWithTZ:
    """Simple class to hold raster data with time and z information."""

    def __init__(
        self, array: np.ndarray, time: typing.Optional[QDateTime] = None, z: typing.Optional[str] = None
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


def feature_attributes(
    ranges: typing.Dict, number_of_features: int, simplify_into_single_value: bool = False
) -> typing.List[typing.List[typing.Any]]:
    """Prepare fields from given parameter ranges."""

    features_attributes: typing.List[typing.List[typing.Any]] = [[] for _ in range(number_of_features)]

    for key in ranges.keys():
        if not simplify_into_single_value:
            if "shape" in ranges[key]:
                if ranges[key]["shape"][0] != number_of_features:
                    raise ValueError(f"Number of features does not match number of values for element `{key}`.")
            else:
                if len(ranges[key]["values"]) != number_of_features:
                    raise ValueError(f"Number of features does not match number of values for element `{key}`.")

        for i, value in enumerate(ranges[key]["values"]):
            if simplify_into_single_value:
                features_attributes[i].append(value)
                break
            else:
                features_attributes[i].append(value)

    return features_attributes


def axes_to_geometries(axes_geom: typing.Dict, domain_type: str) -> typing.List[QgsGeometry]:
    domain_type = domain_type.lower()

    geometries: typing.List[QgsGeometry] = []

    if domain_type in ["polygon", "multipolygon"]:
        json_geoms = axes_geom["composite"]["values"]
        for json_geom in json_geoms:
            geometries.append(json_to_polygon(json_geom))

    if domain_type == "trajectory":
        json_geoms = axes_geom["composite"]["values"]
        geometries.append(json_to_linestring(json_geoms))

    if domain_type in ["pointseries", "point"]:
        for i in range(len(axes_geom["x"]["values"])):
            geometries.append(QgsGeometry(QgsPoint(axes_geom["x"]["values"][i], axes_geom["y"]["values"][i])))

    if domain_type == "multipoint":
        json_geoms = axes_geom["composite"]["values"]
        for json_geom in json_geoms:
            geometries.append(json_to_point(json_geom))

    return geometries


def json_to_point(json_geom: typing.List) -> QgsGeometry:
    return QgsGeometry(QgsPoint(json_geom[0], json_geom[1]))


def json_to_linestring(json_geom: typing.List) -> QgsGeometry:
    linestring = QgsLineString()

    for point in json_geom:
        linestring.addVertex(QgsPoint(point[0], point[1]))

    return QgsGeometry(linestring)


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


def parameter_data_type_to_qgis_type(param_type: str) -> QMetaType.Type:
    if param_type == "integer":
        return QMetaType.Type.Int
    elif param_type == "float":
        return QMetaType.Type.Double
    elif param_type == "string":
        return QMetaType.Type.QString

    raise ValueError(f"Unknown parameter data type: {param_type}")


def covjson_geom_to_wkb_type(covjson_geom_type: str) -> str:
    """Convert CoverageJSON geometry type to WKB type for QGIS memory layer."""
    covjson_geom_type = covjson_geom_type.lower()

    types = {
        "multipolygon": "MultiPolygon",
        "polygon": "Polygon",
        "trajectory": "LineString",
        "pointseries": "Point",
        "point": "Point",
        "multipoint": "Point",
    }

    if covjson_geom_type not in types:
        raise ValueError(f"Unsupported geometry type: {covjson_geom_type}")

    return types[covjson_geom_type]


def prepare_vector_layer(
    wkb_type: str, crs: QgsCoordinateReferenceSystem, layer_name: str = "CoverageJSON"
) -> QgsVectorLayer:

    if crs.isValid():
        crs_str = crs.toWkt()
    else:
        crs_str = "EPSG:4326"

    layer = QgsVectorLayer(f"{covjson_geom_to_wkb_type(wkb_type)}?crs={crs_str}", layer_name, "memory")

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


def make_file_stem_safe(file_stem: str) -> str:
    """Make file stem safe for saving."""
    return file_stem.replace(" ", "_").replace(":", "_").replace("/", "-").replace("\\", "-")
