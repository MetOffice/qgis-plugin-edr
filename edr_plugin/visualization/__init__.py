import os

from qgis.core import QgsMeshLayer, QgsProject, QgsRasterLayer, QgsVectorLayer

from edr_plugin.coveragejson.coverage_json_reader import CoverageJSONReader
from edr_plugin.utils import add_to_layer_group, spawn_layer_group


class EdrLayerException(Exception):
    pass


class EdrLayerManager:
    def __init__(self, plugin):
        self.plugin = plugin
        self.project = QgsProject.instance()
        self.loaded_layers = {}

    def add_layers(self, *layers, group=None):
        if group is None:
            for layer in layers:
                self.project.addMapLayer(layer)
                self.loaded_layers[layer.id()] = layer
        else:
            for layer in layers:
                add_to_layer_group(self.project, group, layer)
                self.loaded_layers[layer.id()] = layer

    def ogr_layer_loader(self, filepath, layer_name):
        layer = QgsVectorLayer(filepath, layer_name, "ogr")
        self.add_layers(layer)

    def gdal_layer_loader(self, filepath, layer_name):
        layer = QgsRasterLayer(filepath, layer_name, "gdal")
        self.add_layers(layer)

    def mdal_layer_loader(self, filepath, layer_name):
        layer = QgsMeshLayer(filepath, layer_name, "mdal")
        self.add_layers(layer)

    def covjson_layer_loader(self, filepath, layer_name):
        try:
            covjson_reader = CoverageJSONReader(filepath)
        except ValueError as e:
            error_msg = f"Can't load CoverageJSON: '{e}'."
            raise EdrLayerException(error_msg)
        layers = covjson_reader.map_layers()
        layers_group = spawn_layer_group(self.project, layer_name)
        self.add_layers(*layers, group=layers_group)
        covjson_reader.qgsproject_setup_time_settings()

    @property
    def file_extension_layer_loaders(self):
        extension_to_loader_map = {
            ".covjson": self.covjson_layer_loader,
            ".geojson": self.ogr_layer_loader,
            ".gpkg": self.ogr_layer_loader,
            ".grib2": self.mdal_layer_loader,
            ".json": self.ogr_layer_loader,
            ".kml": self.ogr_layer_loader,
            ".nc": self.mdal_layer_loader,
            ".tif": self.gdal_layer_loader,
            ".tiff": self.gdal_layer_loader,
            ".geotiff": self.gdal_layer_loader,
        }
        return extension_to_loader_map

    def add_layer_from_file(self, filepath, layer_name=None):
        no_extension_filepath, file_extension = os.path.splitext(filepath)
        file_extension = file_extension.lower()
        try:
            layer_loader = self.file_extension_layer_loaders[file_extension]
            if layer_name is None:
                layer_name = os.path.basename(filepath)
            layer_loader(filepath, layer_name)
        except KeyError:
            self.plugin.communication.bar_warn(f"Can't load file as a layer - unsupported format: '{file_extension}'.")
            return False
        except EdrLayerException as e:
            self.plugin.communication.bar_warn(f"{e}")
            return False
        except Exception as e:
            self.plugin.communication.bar_warn(f"Loading of '{filepath}' failed due to the following exception: {e}")
            return False
        return True
