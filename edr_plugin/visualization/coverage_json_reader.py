import json
import tempfile
import typing

import numpy as np
from osgeo import gdal
from qgis.core import (
    QgsColorRampShader,
    QgsCoordinateReferenceSystem,
    QgsDateTimeRange,
    QgsMapLayer,
    QgsProject,
    QgsRasterLayer,
    QgsRasterShader,
    QgsSingleBandPseudoColorRenderer,
)
from qgis.PyQt.QtCore import QDateTime, Qt
from qgis.PyQt.QtGui import QColor


class RasterWithTZ:
    """Simple class to hold raster data with time and z information."""

    def __init__(
        self, raster: np.ndarray, time: typing.Optional[QDateTime] = None, z: typing.Optional[float] = None
    ) -> None:
        if time:
            if time.isValid():
                self.time = time
        else:
            self.time = None
        self.z = z
        self.raster = raster


class CoverageJSONReader:
    def __init__(self, filename: str) -> None:
        self.filename = filename
        with open(self.filename, encoding="utf-8") as file:
            self.coverage_json = json.load(file)

        if "type" not in self.coverage_json:
            raise ValueError("Not a valid CoverageJSON")

        if self.coverage_json["type"] != "Coverage":
            raise ValueError("Not a valid CoverageJSON")

    @property
    def domain(self) -> typing.Dict:
        """Get domain element."""
        return self.coverage_json["domain"]

    @property
    def referencing(self) -> typing.Dict:
        """Get referencing element."""
        if "referencing" not in self.domain:
            raise ValueError("Missing `referencing` element in domain.")

        return self.domain["referencing"]

    @property
    def parameters(self) -> typing.Dict:
        """Get parameters element."""
        if "parameters" not in self.coverage_json:
            raise ValueError("Missing `parameters` element in coverage.")

        return self.coverage_json["parameters"]

    @property
    def has_z(self) -> bool:
        """Check if there is a `z` in axes definition."""
        return "z" in self.domain["axes"]

    @property
    def has_t(self) -> bool:
        """Check if there is a `t` in axes definition."""
        return "t" in self.domain["axes"]

    def get_crs(self) -> QgsCoordinateReferenceSystem:
        """Get CRS from referencing element."""
        if "system" not in self.referencing[0]:
            raise ValueError("Missing `system` element in referencing.")

        crs_id = self.referencing[0]["system"]["id"]

        if "http:" in crs_id:
            # content = requests.get(id).content
            raise ValueError("Getting CRS from HTTP not supported yet.")

        crs = QgsCoordinateReferenceSystem(crs_id)

        return crs

    def parameter_names(self) -> typing.List[str]:
        """Extract list of parameter names."""
        return [x for x in self.parameters.keys()]

    def get_parameter(self, name: str) -> typing.Dict:
        """Extract parameter json element by name."""
        return self.coverage_json["parameters"][name]

    def get_domain_type(self) -> str:
        """Get domain type."""
        return self.domain["domainType"]

    def parameter_ranges(self, parameter_name: str) -> typing.Dict:
        """Get ranges element of parameter by name. Holds the whole structure for the parameter."""
        return self.coverage_json["ranges"][parameter_name]

    def _get_axe_values(self, axe: str) -> typing.List[float]:
        """Extract axe values for given axe."""
        axes = self.domain["axes"]

        if axe not in axes:
            raise ValueError(f"Missing `f{axe}` axis of data.")

        return axes[axe]["values"]

    @staticmethod
    def _validate_axis_names(existing_axis: typing.List[str]) -> None:
        """Check that axis names are in standard order. This is needed for further processing."""
        axis_according_to_standard = ["y", "x"]
        if "z" in existing_axis:
            axis_according_to_standard.insert(0, "z")

        if "t" in existing_axis:
            axis_according_to_standard.insert(0, "t")

        if existing_axis != axis_according_to_standard:
            raise ValueError(f"Unsupported axes: {existing_axis}")

    def has_z_in_data(self, parameter_name: str) -> bool:
        """Check if there is `z` axis specific parameter."""
        return "z" in self.parameter_ranges(parameter_name)["axisNames"]

    def has_t_in_data(self, parameter_name: str) -> bool:
        """Check if there is `t` axis specific parameter."""
        return "t" in self.parameter_ranges(parameter_name)["axisNames"]

    def _format_values_into_rasters(self, parameter_name: str) -> typing.Dict[str, RasterWithTZ]:
        """Format CoverageJSON values into dictionary of raster data (data name and raster information)."""
        info = self.parameter_ranges(parameter_name)

        if info["type"] != "NdArray":
            raise ValueError("Only NdArray data type supported for now.")

        self._validate_axis_names(info["axisNames"])

        values = np.array(info["values"])
        values = values.reshape(info["shape"])

        data_dict = {}

        if self.has_t_in_data(parameter_name) and self.has_z_in_data(parameter_name):
            for t_i, t in enumerate(self._get_axe_values("t")):
                for z_i, z in enumerate(self._get_axe_values("z")):
                    data_dict[f"{t}_{z}"] = RasterWithTZ(values[t_i, z_i, ...], QDateTime.fromString(t, Qt.ISODate), z)

        elif self.has_t_in_data(parameter_name):
            for t_i, t in enumerate(self._get_axe_values("t")):
                data_dict[f"{t}"] = RasterWithTZ(values[t_i, ...], time=QDateTime.fromString(t, Qt.ISODate))

        elif self.has_z_in_data(parameter_name):
            for z_i, z in enumerate(self._get_axe_values("z")):
                data_dict[f"{z}"] = RasterWithTZ(values[z_i, ...], z=z)

        else:
            data_dict[""] = RasterWithTZ(values)

        return data_dict

    def _data_type(self, parameter_name: str) -> int:
        """Get data type for given parameter. To be used for GDAL raster creation."""
        data_type = self.parameter_ranges(parameter_name)["dataType"]
        if data_type == "integer":
            return gdal.GDT_Int32
        elif data_type == "float":
            return gdal.GDT_Float32
        else:
            raise ValueError(f"Unsupported data type: {data_type}")

    def _prepare_empty_raster(
        self,
        file_name: str,
        x_coords: typing.List[float],
        y_coords: typing.List[float],
        data_type: int,
    ) -> typing.Tuple[gdal.Dataset, str]:
        """Prepare empty raster file with given size (rows, cols), calculated extent extracted CRS."""
        x_min = x_coords[0] - (x_coords[1] - x_coords[0]) / 2
        x_max = x_coords[-1] + (x_coords[-1] - x_coords[-2]) / 2

        y_min = y_coords[0] - (y_coords[1] - y_coords[0]) / 2
        y_max = y_coords[-1] + (y_coords[-1] - y_coords[-2]) / 2

        driver = gdal.GetDriverByName("GTiff")
        dp: gdal.Dataset = driver.Create(file_name, len(x_coords), len(y_coords), 1, data_type)

        dp.SetGeoTransform([x_min, (x_max - x_min) / len(x_coords), 0, y_max, 0, -((y_max - y_min) / len(y_coords))])
        dp.SetProjection(self.get_crs().toWkt())

        return dp, file_name

    @staticmethod
    def _write_array_to_band(
        dp: gdal.Dataset,
        band_number: int,
        np_array: np.ndarray,
        no_data_value: float = -9999999,
    ) -> None:
        """Write given numpy array to given band. No data value is set to -9999999 by default."""
        band: gdal.Band = dp.GetRasterBand(band_number)
        band.SetNoDataValue(no_data_value)

        np_array[np_array == None] = no_data_value
        np_array = np.flip(np_array, 0)

        band.WriteArray(np_array)

        band = None

    def get_raster_shader(self, parameter_name: str) -> typing.Optional[QgsRasterShader]:
        """Create raster shader for given parameter if it is specified in CoverageJSON."""
        parameter = self.coverage_json["parameters"][parameter_name]
        if "categoryEncoding" not in parameter:
            return None

        data_range = self.parameter_ranges(parameter_name)
        data = np.array(data_range["values"])
        data = data[data != np.array(None)]

        color_ramp_items: typing.List[QgsColorRampShader.ColorRampItem] = []

        max_value = np.max(data)
        max_legend_value = 0

        if "categoryEncoding" in parameter:
            for element in parameter["categoryEncoding"]:
                color_ramp_items.append(
                    QgsColorRampShader.ColorRampItem(
                        parameter["categoryEncoding"][element],
                        QColor(element),
                        f'{parameter["categoryEncoding"][element]}',
                    )
                )

                if parameter["categoryEncoding"][element] > max_value:
                    max_legend_value = parameter["categoryEncoding"][element]
                    break

        new_color_ramp_shader = QgsColorRampShader(np.min(data), np.max(data))
        new_color_ramp_shader.setColorRampType(QgsColorRampShader.Type.Interpolated)
        new_color_ramp_shader.setColorRampItemList(color_ramp_items)

        raster_shader = QgsRasterShader()
        raster_shader.setRasterShaderFunction(new_color_ramp_shader)
        raster_shader.setMinimumValue(np.min(data))
        raster_shader.setMaximumValue(max_legend_value)

        return raster_shader

    def save_temp_raster(
        self, filename_without_extension: str, data: np.ndarray, data_type: int = gdal.GDT_Float32
    ) -> str:
        """Save raster to temporary file and return filename."""
        x_coords = self._get_axe_values("x")
        y_coords = self._get_axe_values("y")

        file_to_save = f"{tempfile.gettempdir()}/{filename_without_extension}.tif"

        dp, file_name = self._prepare_empty_raster(
            file_to_save,
            x_coords,
            y_coords,
            data_type,
        )

        self._write_array_to_band(dp, 1, data)

        dp = None

        return file_name

    def _get_time_step(self) -> typing.Optional[float]:
        """Extract time step if it exists."""
        if self.has_t:
            t = self._get_axe_values("t")
            t0 = QDateTime.fromString(t[0], Qt.ISODate)
            t1 = QDateTime.fromString(t[1], Qt.ISODate)

            if t0.isValid() and t1.isValid():
                return t0.secsTo(t1)

        return None

    def raster_layers(self, parameter_name: str) -> typing.List[QgsRasterLayer]:
        """Crete list of raster layers for given parameter. The size of the list can be 1 or more."""
        formatted_data = self._format_values_into_rasters(parameter_name)
        layers = []

        time_step = self._get_time_step()

        for key, data in formatted_data.items():
            if key:
                layer_name = f"{parameter_name}_{key}"
            else:
                layer_name = parameter_name

            filename = self.save_temp_raster(
                layer_name,
                data.raster,
                self._data_type(parameter_name),
            )

            layer = QgsRasterLayer(filename, layer_name, "gdal")

            if time_step and data.time:
                layer.temporalProperties().setIsActive(True)
                layer.temporalProperties().setFixedTemporalRange(
                    QgsDateTimeRange(
                        data.time.addSecs(int(-1 * (time_step / 2))), data.time.addSecs(int(time_step / 2))
                    )
                )

            shader = self.get_raster_shader(parameter_name)
            if shader:
                renderer = QgsSingleBandPseudoColorRenderer(layer.dataProvider(), 1, shader)
                renderer.setClassificationMin(shader.minimumValue())
                renderer.setClassificationMax(shader.maximumValue())
                layer.setRenderer(renderer)

            layers.append(layer)

        return layers

    def _get_time_range(self) -> typing.Optional[QgsDateTimeRange]:
        """Extract time range from `t` axis if it exists."""
        if self.has_t:
            t = self._get_axe_values("t")
            t0 = QDateTime.fromString(t[0], Qt.ISODate)
            t1 = QDateTime.fromString(t[-1], Qt.ISODate)

            if t0.isValid() and t1.isValid():
                return QgsDateTimeRange(t0, t1)
        return None

    def qgsproject_setup_time_settings(self) -> None:
        """Set time range and time step to QgsProject if the data supports it."""
        time_range = self._get_time_range()
        if time_range:
            time_settings = QgsProject.instance().timeSettings()
            time_settings.setTemporalRange(self._get_time_range())
            time_settings.setTimeStep(self._get_time_step())

    def map_layers(self) -> typing.List[QgsMapLayer]:
        """Get list of map layers for all parameters in the CoverageJSON file."""
        layers = []
        if self.get_domain_type() == "Grid":
            for parameter in self.parameters:
                layers.extend(self.raster_layers(parameter))
            return layers
        raise ValueError("Domain type not supported yet.")
