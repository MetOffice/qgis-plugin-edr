import os

from qgis.core import QgsMeshLayer, QgsProject, QgsRasterLayer, QgsVectorLayer

from edr_plugin.visualization.coverage_json_reader import CoverageJSONReader


class EdrLayerManager:
    def __init__(self, plugin):
        self.plugin = plugin
        self.project = QgsProject.instance()
        self.loaded_layers = {}

    @property
    def extension_layer_type(self):
        extension_layer_type_map = {
            "csv": (QgsVectorLayer, "csv"),
            "geojson": (QgsVectorLayer, "ogr"),
            "gpkg": (QgsVectorLayer, "ogr"),
            "grib2": (QgsMeshLayer, "mdal"),
            "nc": (QgsMeshLayer, "mdal"),
            "tif": (QgsRasterLayer, "gdal"),
            "tiff": (QgsRasterLayer, "gdal"),
        }
        return extension_layer_type_map

    def add_layer_from_file(self, filepath, layer_name=None):
        file_extension = filepath.rsplit(".", 1)[-1].lower()
        try:
            layer_cls, provider = self.extension_layer_type[file_extension]
        except KeyError:
            self.plugin.communication.bar_warn(f"Can't load file as a layer - unsupported format: '{file_extension}'.")
            return False
        if layer_name is None:
            layer_name = os.path.basename(filepath)
        layer = layer_cls(filepath, layer_name, provider)
        self.project.addMapLayer(layer)
        self.loaded_layers[layer.id()] = layer
        return True

    def load_layers_from_coverage_json(self, filepath: str) -> bool:
        try:
            covjson_reader = CoverageJSONReader(filepath)
        except ValueError as e:
            self.plugin.communication.bar_warn(f"Can't load CoverageJSON: '{e}'.")
            return False

        for layer in covjson_reader.map_layers():
            QgsProject.instance().addMapLayer(layer)
            self.loaded_layers[layer.id()] = layer

        covjson_reader.qgsproject_setup_time_settings()
        return True
