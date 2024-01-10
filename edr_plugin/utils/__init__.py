import os
import re
from types import MappingProxyType
from uuid import uuid4

from qgis.core import QgsLayerTreeGroup, QgsLayerTreeLayer

CONTENT_TYPE_EXTENSIONS = MappingProxyType(
    {
        "application/json": "json",
        "application/prs.coverage+json": "covjson",
        "application/geo+json": "geojson",
        "application/geopackage+sqlite3": "gpkg",
        "application/x-netcdf4": "nc",
        "application/vnd.google-earth.kml+xml": "kml",
        "image/tiff": "tiff",
        "text/csv": "csv",
    }
)


def download_reply_file(reply, download_dir, download_filename=None):
    """Download and write content from the QgsNetworkReplyContent object."""
    if not download_filename:
        raw_content_type_header = reply.rawHeader("content-type".encode())
        content_type_header = raw_content_type_header.data().decode(errors="ignore")
        content_type = content_type_header.split(";")[0]
        file_extension = CONTENT_TYPE_EXTENSIONS.get(content_type, "")
        raw_content_disposition_header = reply.rawHeader("content-disposition".encode())
        if raw_content_disposition_header and file_extension != "covjson":
            content_disposition_header = raw_content_disposition_header.data().decode(errors="ignore")
            download_filename = reply.extractFileNameFromContentDispositionHeader(content_disposition_header)
        else:
            request_url = reply.request().url().toDisplayString()
            collection_name = re.findall("collections/(.+?)/", request_url)[0]
            download_filename = f"{collection_name}_{uuid4()}"
            if file_extension:
                download_filename += f".{file_extension}"
    download_filepath = os.path.join(download_dir, download_filename)
    file_copy_number = 1
    no_extension_download_filepath, download_file_extension = os.path.splitext(download_filepath)
    while os.path.exists(download_filepath):
        download_filepath = f"{no_extension_download_filepath} ({file_copy_number}){download_file_extension}"
        file_copy_number += 1
    with open(download_filepath, "wb") as f:
        f.write(reply.content())
    return download_filepath


def download_response_file(response, download_dir, download_filename=None, chunk_size=1024**2):
    """Download and write content from the response object."""
    if not download_filename:
        try:
            content_disposition = response.headers["content-disposition"]
            download_filename = re.findall("filename=(.+)", content_disposition)[0].strip('"')
        except KeyError:
            collection_name = re.findall("collections/(.+?)/", response.url)[0]
            download_filename = f"{collection_name}_{uuid4()}.json"
    download_filepath = os.path.join(download_dir, download_filename)
    with open(download_filepath, "wb") as f:
        for chunk in response.iter_content(chunk_size=chunk_size):
            if chunk:
                f.write(chunk)
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
