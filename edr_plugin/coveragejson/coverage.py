import typing
from pathlib import Path

import numpy as np
from osgeo import gdal
from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsDateTimeRange,
    QgsFeature,
    QgsField,
    QgsMapLayer,
    QgsRasterLayer,
    QgsVectorLayer,
)
from qgis.PyQt.QtCore import QDateTime, Qt, QVariant

from edr_plugin.coveragejson.utils import (
    ArrayWithTZ,
    DimensionAccessor,
    RasterTemplate,
    axes_to_geometries,
    feature_attributes,
    make_file_stem_safe,
    prepare_fields,
    prepare_raster_shader,
    prepare_vector_layer,
    prepare_vector_render,
    set_layer_render_from_shader,
    set_project_time_range,
)


class Coverage:
    """Class representing coverage from CoverageJSON."""

    VECTOR_DATA_DOMAIN_TYPES = ["MultiPolygon", "Trajectory", "PointSeries"]
    TYPES_FOR_MERGE = ["Trajectory", "PointSeries"]
    TYPES_FOR_ATTRIBUTE_SIMPLIFICATION = ["Trajectory"]
    TYPES_DIRECT_COORDINATES = ["PointSeries"]

    FIELD_NAME_TIME = "time"

    def __init__(
        self,
        coverage_json: typing.Dict,
        crs: QgsCoordinateReferenceSystem,
        domain_type: typing.Optional[str] = None,
        parameters_from_parent: typing.Optional[typing.Dict] = None,
        folder_to_save_data: Path = Path("/tmp"),
    ):
        self.coverage_json = coverage_json

        self.crs = crs

        self.folder_to_save_data = folder_to_save_data

        if domain_type is None:
            self.domain_type = self.domain["domainType"]
        else:
            self.domain_type = domain_type

        self.parent_parameters = parameters_from_parent

    @property
    def domain(self) -> typing.Dict:
        """Get domain element."""
        return self.coverage_json["domain"]

    @property
    def axes(self) -> typing.Dict:
        """Get axes element."""
        return self.domain["axes"]

    @property
    def axes_names(self) -> typing.List[str]:
        """Get axes names."""
        return [x for x in self.axes.keys()]

    def range_axes_with_sizes(self, parameter_name: str) -> typing.Dict[str, int]:
        """Get axes names for given parameter."""
        axis_names = self.parameter_ranges(parameter_name)["axisNames"]
        axis_shape = self.parameter_ranges(parameter_name)["shape"]

        relevant_axes = {}
        for i, _ in enumerate(axis_names):
            if axis_shape[i] > 1:
                relevant_axes[axis_names[i]] = axis_shape[i]
        return relevant_axes

    @staticmethod
    def get_axe_values(axe_dict: typing.Dict) -> typing.List[float]:
        """Extract axe values from axes element."""
        if "values" in axe_dict:
            return axe_dict["values"]
        elif "start" in axe_dict and "stop" in axe_dict and "num" in axe_dict:
            return np.linspace(axe_dict["start"], axe_dict["stop"], axe_dict["num"]).tolist()

        raise ValueError("Unsupported axe definition.")

    def axe_values(self, axe: str) -> typing.List[float]:
        """Extract axe values for given axe."""

        if axe not in self.axes_names:
            raise ValueError(f"Missing `f{axe}` axis of data.")

        return self.get_axe_values(self.axes[axe])

    @property
    def parameters(self) -> typing.Dict:
        """Get parameters element."""
        if "parameters" in self.coverage_json:
            return self.coverage_json["parameters"]
        elif self.parent_parameters:
            return self.parent_parameters
        return {}

    @property
    def has_z(self) -> bool:
        """Check if there is a `z` in axes definition."""
        return "z" in self.axes_names

    @property
    def has_t(self) -> bool:
        """Check if there is a `t` in axes definition."""
        return "t" in self.axes_names

    @property
    def has_composite_axe(self) -> bool:
        """Check if there is a `composite` in axes definition."""
        return "composite" in self.axes_names

    @property
    def parameter_names(self) -> typing.List[str]:
        """Extract list of parameter names."""
        return [x for x in self.parameters.keys()]

    @property
    def ranges(self) -> typing.Dict:
        """Get ranges element."""
        return self.coverage_json["ranges"]

    def parameter_ranges(self, parameter_name: str) -> typing.Dict:
        """Get ranges element of parameter by name. Holds the whole structure for the parameter."""
        return self.ranges[parameter_name]

    def _validate_composite_axes(self) -> None:
        """Check if data is composite."""
        # points have directly axes without specification
        if "composite" not in self.axes and self.domain_type in self.TYPES_DIRECT_COORDINATES:
            return
        data_type = self.axes["composite"]["dataType"]
        if data_type not in ["polygon", "tuple"]:
            raise ValueError(f"Unsupported composite data type `{data_type}`.")
        coordinates = self.axes["composite"]["coordinates"]
        if coordinates != ["x", "y"]:
            raise ValueError(f"Unsupported composite coordinates `{coordinates}`.")

    def _format_values_into_rasters(self, parameter_name: str) -> typing.Dict[str, ArrayWithTZ]:
        """Format CoverageJSON values into dictionary of raster data (data name and raster information)."""
        info = self.parameter_ranges(parameter_name)

        if info["type"] != "NdArray":
            raise ValueError("Only NdArray data type supported for now.")

        values = np.array(info["values"])

        values = values.reshape(info["shape"])

        data_dict = {}

        dim_accessor = DimensionAccessor(self.parameter_ranges(parameter_name), self.axes)

        for dimension_values in dim_accessor.iter_product:
            data_dict[dim_accessor.dimensions_to_string_description(dimension_values)] = ArrayWithTZ(
                values[dimension_values],
                QDateTime.fromString(dim_accessor.t(dimension_values), Qt.ISODate),
                dim_accessor.z(dimension_values),
            )

        return data_dict

    def data_type(self, parameter_name: str) -> int:
        """Get data type for given parameter. To be used for GDAL raster creation."""
        data_type = self.parameter_ranges(parameter_name)["dataType"]
        if data_type == "integer":
            return gdal.GDT_Int32
        elif data_type == "float":
            return gdal.GDT_Float32
        else:
            raise ValueError(f"Unsupported data type: {data_type}")

    def parameter_info(self, parameter_name: str) -> typing.Dict:
        """Extract parameter values as dictionary."""
        if "parameters" in self.coverage_json:
            return self.coverage_json["parameters"][parameter_name]
        return {}

    def time_step(self) -> typing.Optional[float]:
        """Extract time step if it exists."""
        if self.has_t:
            t = self.axe_values("t")

            if len(t) < 2:
                return None

            t0 = QDateTime.fromString(t[0], Qt.ISODate)
            t1 = QDateTime.fromString(t[1], Qt.ISODate)

            if t0.isValid() and t1.isValid():
                return t0.secsTo(t1)

        return None

    def raster_layers(self, parameter_name: str) -> typing.List[QgsRasterLayer]:
        """Crete list of raster layers for given parameter. The size of the list can be 1 or more."""
        layers = []

        if parameter_name not in self.ranges:
            return layers

        formatted_data = self._format_values_into_rasters(parameter_name)

        time_step = self.time_step()

        raster_template = RasterTemplate(
            self.axe_values("x"),
            self.axe_values("y"),
            self.data_type(parameter_name),
            self.crs.toWkt(),
        )

        unit = self.unit_label(parameter_name)

        layer_name_start = parameter_name
        if unit:
            layer_name_start = f"{layer_name_start}-[{unit}]"

        for key, data in formatted_data.items():
            if key:
                layer_name = f"{layer_name_start}_{key}"
            else:
                layer_name = layer_name_start

            file_to_save = self.folder_to_save_data / f"{make_file_stem_safe(layer_name)}.tif"

            dp = raster_template.save_empty_raster(file_to_save)

            RasterTemplate.write_array_to_band(dp, data.array, 1)

            dp = None

            layer = QgsRasterLayer(file_to_save.as_posix(), layer_name, "gdal")

            if time_step and data.time:
                layer.temporalProperties().setIsActive(True)
                layer.temporalProperties().setFixedTemporalRange(
                    QgsDateTimeRange(
                        data.time.addSecs(int(-1 * (time_step / 2))), data.time.addSecs(int(time_step / 2))
                    )
                )

            shader = prepare_raster_shader(self.parameter_info(parameter_name), self.parameter_ranges(parameter_name))

            set_layer_render_from_shader(layer, shader)

            layers.append(layer)

        return layers

    def time_range(self) -> typing.Optional[QgsDateTimeRange]:
        """Extract time range from `t` axis if it exists."""
        if self.has_t:
            t = self.axe_values("t")
            t0 = QDateTime.fromString(t[0], Qt.ISODate)
            t1 = QDateTime.fromString(t[-1], Qt.ISODate)

            if t0.isValid() and t1.isValid():
                return QgsDateTimeRange(t0, t1)
        return None

    def qgsproject_setup_time_settings(self) -> None:
        """Set time range and time step to QgsProject if the data supports it."""
        if self.has_t:
            set_project_time_range(self.time_range(), self.time_step())

    @property
    def domain_is_vector_data(self) -> bool:
        """Check if domain is vector data."""
        return self.domain_type in self.VECTOR_DATA_DOMAIN_TYPES

    @property
    def simplify_attributes_to_single_value(self) -> bool:
        return self.domain_type in self.TYPES_FOR_ATTRIBUTE_SIMPLIFICATION

    def coverage_features(self, layer: QgsVectorLayer) -> typing.List[QgsFeature]:
        """Get list of features from Coverage."""
        geoms = axes_to_geometries(self.domain["axes"], self.domain_type)

        if self.has_t:
            t_values = self.axe_values("t")
            geoms = geoms * len(t_values)

        attributes = feature_attributes(self.ranges, len(geoms), self.simplify_attributes_to_single_value)

        features = []
        i = 0
        for geom, attrs in zip(geoms, attributes):
            feature = QgsFeature(layer.fields())
            if self.has_t:
                attrs.append(QDateTime.fromString(t_values[i], Qt.ISODate))
            feature.setAttributes(attrs)
            feature.setGeometry(geom)
            features.append(feature)
            i += 1
            if i > len(geoms) - 1:
                i = 0

        return features

    @property
    def could_be_merged(self) -> bool:
        """Check if the type of coverage would be candidate for merging coverages together."""
        return self.domain_type in self.TYPES_FOR_MERGE

    def vector_layer(self) -> QgsVectorLayer:
        """Create vector layer from Coverage."""
        layer = prepare_vector_layer(self.domain_type, self.crs)
        layer.dataProvider().addAttributes(prepare_fields(self.ranges, self.parameters_units))
        if self.has_t:
            layer.dataProvider().addAttributes([QgsField(self.FIELD_NAME_TIME, QVariant.Type.DateTime)])
        layer.updateFields()
        return layer

    def vector_layers(self) -> typing.List[QgsVectorLayer]:
        layers: typing.List[QgsVectorLayer] = []

        self._validate_composite_axes()

        layer = self.vector_layer()

        layer.dataProvider().addFeatures(self.coverage_features(layer))

        layer.setRenderer(prepare_vector_render(layer, self.parameters))

        layers.append(layer)

        return layers

    def map_layers(self) -> typing.List[QgsMapLayer]:
        """Get list of map layers from Coverage."""
        layers = []
        if self.domain_type == "Grid":
            for parameter in self.parameters:
                layers.extend(self.raster_layers(parameter))

        if self.domain_is_vector_data:
            layers.extend(self.vector_layers())

        if layers:
            return layers

        raise ValueError("Domain type not supported yet.")

    def unit_label(self, parameter_name: str) -> typing.Optional[str]:
        """Unit label for given parameter."""
        parameters = self.parameters
        if parameters:
            for parameter_name in parameters.keys():
                if "unit" in parameters[parameter_name] and "label" in parameters[parameter_name]["unit"]:
                    return parameters[parameter_name]["unit"]["label"][
                        list(parameters[parameter_name]["unit"]["label"].keys())[0]
                    ]
                else:
                    return None
        return None

    @property
    def parameters_units(self) -> typing.Dict[str, str]:
        """Get parameter units if exist."""
        labels = {}

        for parameter in self.parameter_names:
            unit = self.unit_label(parameter)
            if unit:
                labels[parameter] = unit

        return labels
