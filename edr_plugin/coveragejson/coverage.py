import typing
from pathlib import Path

import numpy as np
from osgeo import gdal
from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsDateTimeRange,
    QgsFeature,
    QgsMapLayer,
    QgsRasterLayer,
    QgsVectorLayer,
)
from qgis.PyQt.QtCore import QDateTime, Qt

from edr_plugin.coveragejson.utils import (
    ArrayWithTZ,
    RasterTemplate,
    composite_to_geometries,
    feature_attributes,
    prepare_fields,
    prepare_raster_shader,
    prepare_vector_layer,
    set_layer_render_from_shader,
    set_project_time_range,
)


class Coverage:
    """Class representing coverage from CoverageJSON."""

    VECTOR_DATA_DOMAIN_TYPES = ["MultiPolygon"]

    def __init__(
        self,
        coverage_json: typing.Dict,
        crs: QgsCoordinateReferenceSystem,
        domain_type: typing.Optional[str] = None,
        folder_to_save_data: Path = Path("/tmp"),
    ):
        self.coverage_json = coverage_json

        self.crs = crs

        self.folder_to_save_data = folder_to_save_data

        if domain_type is None:
            self.domain_type = self.domain["domainType"]
        else:
            self.domain_type = domain_type

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
        if "parameters" not in self.coverage_json:
            return self.coverage_json["ranges"]
        else:
            return self.coverage_json["parameters"]

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
        data_type = self.axes["composite"]["dataType"]
        if data_type not in ["polygon"]:
            raise ValueError(f"Unsupported composite data type `{data_type}`.")
        coordinates = self.axes["composite"]["coordinates"]
        if coordinates != ["x", "y"]:
            raise ValueError(f"Unsupported composite coordinates `{coordinates}`.")

    @staticmethod
    def _validate_axis_names(existing_axis: typing.List[str]) -> None:
        """Check that axis names are in standard order. This is needed for further processing."""
        axis_according_to_standard = ["y", "x"]
        if "z" in existing_axis:
            axis_according_to_standard.insert(0, "z")

        if "t" in existing_axis:
            axis_according_to_standard.insert(0, "t")

        if existing_axis != axis_according_to_standard:
            raise ValueError(f"Unsupported axes found: {existing_axis}")

    def has_z_in_data(self, parameter_name: str) -> bool:
        """Check if there is `z` axis specific parameter."""
        return "z" in self.parameter_ranges(parameter_name)["axisNames"]

    def has_t_in_data(self, parameter_name: str) -> bool:
        """Check if there is `t` axis specific parameter."""
        return "t" in self.parameter_ranges(parameter_name)["axisNames"]

    def _format_values_into_rasters(self, parameter_name: str) -> typing.Dict[str, ArrayWithTZ]:
        """Format CoverageJSON values into dictionary of raster data (data name and raster information)."""
        info = self.parameter_ranges(parameter_name)

        if info["type"] != "NdArray":
            raise ValueError("Only NdArray data type supported for now.")

        values = np.array(info["values"])

        # if values are longer then X * Y coords then we need to validate axis names for correct processing
        if len(values) != len(self.axe_values("x")) * len(self.axe_values("y")):
            self._validate_axis_names(info["axisNames"])

        values = values.reshape(info["shape"])

        data_dict = {}

        if self.has_t_in_data(parameter_name) and self.has_z_in_data(parameter_name):
            for t_i, t in enumerate(self.axe_values("t")):
                for z_i, z in enumerate(self.axe_values("z")):
                    data_dict[f"{t}_{z}"] = ArrayWithTZ(values[t_i, z_i, ...], QDateTime.fromString(t, Qt.ISODate), z)

        elif self.has_t_in_data(parameter_name):
            for t_i, t in enumerate(self.axe_values("t")):
                data_dict[f"{t}"] = ArrayWithTZ(values[t_i, ...], time=QDateTime.fromString(t, Qt.ISODate))

        elif self.has_z_in_data(parameter_name):
            for z_i, z in enumerate(self.axe_values("z")):
                data_dict[f"{z}"] = ArrayWithTZ(values[z_i, ...], z=z)

        else:
            data_dict[""] = ArrayWithTZ(values)

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
        return self.coverage_json["parameters"][parameter_name]

    def time_step(self) -> typing.Optional[float]:
        """Extract time step if it exists."""
        if self.has_t:
            t = self.axe_values("t")
            t0 = QDateTime.fromString(t[0], Qt.ISODate)
            t1 = QDateTime.fromString(t[1], Qt.ISODate)

            if t0.isValid() and t1.isValid():
                return t0.secsTo(t1)

        return None

    def raster_layers(self, parameter_name: str) -> typing.List[QgsRasterLayer]:
        """Crete list of raster layers for given parameter. The size of the list can be 1 or more."""
        formatted_data = self._format_values_into_rasters(parameter_name)
        layers = []

        time_step = self.time_step()

        raster_template = RasterTemplate(
            self.axe_values("x"),
            self.axe_values("y"),
            self.data_type(parameter_name),
            self.crs.toWkt(),
        )

        for key, data in formatted_data.items():
            if key:
                layer_name = f"{parameter_name}_{key}"
            else:
                layer_name = parameter_name

            file_to_save = self.folder_to_save_data / f"{layer_name}.tif"

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

    def vector_layers(self) -> typing.List[QgsVectorLayer]:
        layers: typing.List[QgsVectorLayer] = []

        self._validate_composite_axes()

        layer = prepare_vector_layer(self.domain_type, self.crs)
        layer.dataProvider().addAttributes(prepare_fields(self.ranges))
        layer.updateFields()

        geoms = composite_to_geometries(self.domain["axes"]["composite"])
        attributes = feature_attributes(self.ranges, len(geoms))

        features = []
        for geom, attrs in zip(geoms, attributes):
            feature = QgsFeature(layer.fields())
            feature.setAttributes(attrs)
            feature.setGeometry(geom)

            features.append(feature)

        layer.dataProvider().addFeatures(features)

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
