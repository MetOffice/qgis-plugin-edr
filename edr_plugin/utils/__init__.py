import os
from types import MappingProxyType
from uuid import uuid4

from qgis.core import (
    QgsContrastEnhancement,
    QgsCoordinateTransform,
    QgsLayerTreeGroup,
    QgsLayerTreeLayer,
    QgsProject,
    QgsRasterBandStats,
    QgsRasterLayer,
    QgsSingleBandGrayRenderer,
)

CONTENT_TYPE_EXTENSIONS = MappingProxyType(
    {
        "application/json": ".json",
        "application/prs.coverage+json": ".covjson",
        "application/geo+json": ".geojson",
        "application/geopackage+sqlite3": ".gpkg",
        "application/x-netcdf4": ".nc",
        "application/vnd.google-earth.kml+xml": ".kml",
        "image/tiff": ".tiff",
        "text/csv": ".csv",
    }
)


def download_reply_file(reply, download_dir, data_query_definition, download_filename=None):
    """Download and write content from the QgsNetworkReplyContent object."""
    if not download_filename:
        json_ext, geojson_ext, covjson_ext = ".json", ".geojson", ".covjson"
        raw_content_type_header = reply.rawHeader("content-type".encode())
        content_type_header = raw_content_type_header.data().decode(errors="ignore")
        content_type = content_type_header.split(";", 1)[0]
        content_type_extension = CONTENT_TYPE_EXTENSIONS.get(content_type, "")
        raw_content_disposition_header = reply.rawHeader("content-disposition".encode())
        if raw_content_disposition_header:
            content_disposition_header = raw_content_disposition_header.data().decode(errors="ignore")
            download_filename = reply.extractFileNameFromContentDispositionHeader(content_disposition_header)
            no_extension_download_filename, raw_extension = os.path.splitext(download_filename)
            file_extension = raw_extension.lower()
        else:
            raw_extension = None
            download_filename = f"{data_query_definition.collection_id}_{uuid4()}"
            file_extension = content_type_extension
        if file_extension and raw_extension is None:
            if file_extension == json_ext:
                exact_json_format = data_query_definition.output_format.lower()
                if "coveragejson" in exact_json_format:
                    file_extension = covjson_ext
                elif "geojson" in exact_json_format:
                    file_extension = geojson_ext
                else:
                    pass
            download_filename += file_extension
    download_filepath = os.path.join(download_dir, download_filename)
    file_copy_number = 1
    no_extension_download_filepath, download_file_extension = os.path.splitext(download_filepath)
    while os.path.exists(download_filepath):
        download_filepath = f"{no_extension_download_filepath} ({file_copy_number}){download_file_extension}"
        file_copy_number += 1
    with open(download_filepath, "wb") as f:
        f.write(reply.content())
    return download_filepath


def is_dir_writable(working_dir):
    """Try to write an empty text file into given location to check if location is writable."""
    test_filename = f"{uuid4()}.txt"
    test_file_path = os.path.join(working_dir, test_filename)
    try:
        with open(test_file_path, "w") as test_file:
            test_file.write("")
        os.remove(test_file_path)
    except (PermissionError, OSError):
        return False
    return True


def spawn_layer_group(project, name, top_insert=True):
    """Creating layer tree group."""
    r = project.layerTreeRoot()
    group = QgsLayerTreeGroup(name)
    r.insertChildNode(0 if top_insert else -1, group)
    return group


def add_to_layer_group(project, group, layer, top_insert=False, expanded=False, add_to_legend=False):
    """Add layer to the group."""
    root = project.layerTreeRoot()
    project.addMapLayer(layer, add_to_legend)
    group.insertChildNode(0 if top_insert else -1, QgsLayerTreeLayer(layer))
    layer_node = root.findLayer(layer.id())
    layer_node.setExpanded(expanded)


def single_band_gray_renderer(layer: QgsRasterLayer) -> None:
    """Set raster layer to gray scale."""
    stats = layer.dataProvider().bandStatistics(1, QgsRasterBandStats.All, layer.extent(), 0)

    rnd = QgsSingleBandGrayRenderer(layer.dataProvider(), 1)
    ce = QgsContrastEnhancement(layer.dataProvider().dataType(1))
    ce.setContrastEnhancementAlgorithm(QgsContrastEnhancement.StretchToMinimumMaximum)

    ce.setMinimumValue(stats.minimumValue)
    ce.setMaximumValue(stats.maximumValue)

    rnd.setContrastEnhancement(ce)

    layer.setRenderer(rnd)
    layer.triggerRepaint()


def reproject_geometry(geometry, src_crs, dst_crs, transformation=None):
    """Reproject geometry from source CRS to destination CRS."""
    if src_crs == dst_crs:
        return geometry
    if transformation is None:
        project = QgsProject.instance()
        transform_context = project.transformContext()
        transformation = QgsCoordinateTransform(src_crs, dst_crs, transform_context)
    geometry.transform(transformation)
    return geometry


def icon_filepath(icon_filename):
    """Return icon filepath."""
    plugin_dirname = os.path.dirname(os.path.dirname(__file__))
    filepath = os.path.join(plugin_dirname, "icons", icon_filename)
    return filepath
