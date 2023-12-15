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
        if file_extension == filepath:
            try:
                self.load_from_coverage_json(filepath)
                return True
            except ValueError as e:
                self.plugin.communication.bar_warn(f"Can't load CoverageJSON: '{e}'.")
            return False
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

    def load_from_coverage_json(self, filepath: str):
        coverage_reader = CoverageJSONReader(filepath)
        layers = coverage_reader.get_map_layers()
        for layer in layers:
            self.project.addMapLayer(layer)
            self.loaded_layers[layer.id()] = layer
        coverage_reader.qgsproject_setup_time_settings()
