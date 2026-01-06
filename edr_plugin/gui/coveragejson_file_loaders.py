from qgis.core import QgsApplication, QgsDataItem, QgsDataItemProvider, QgsDataProvider, QgsMimeDataUtils
from qgis.gui import QgsCustomDropHandler
from qgis.PyQt.QtCore import QCoreApplication, QDir, QFileInfo
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction

COVERAGE_JSON_PROVIDERKEY = "coveragejson"

COVERAGEJSON_EXTENSIONS = ["covjson", "coveragejson"]


def is_path_coverage_json(path: str) -> bool:
    for ext in COVERAGEJSON_EXTENSIONS:
        if path.lower().endswith(ext):
            return True
    return False


class CoverageJSONDropHandler(QgsCustomDropHandler):
    """
    CoverageJSON file drop handler
    """

    def __init__(self, layer_manager) -> None:
        super().__init__()
        self.layer_manager = layer_manager

    def handleFileDrop(self, file):  # pylint: disable=missing-docstring
        if not is_path_coverage_json(file):
            return False
        self.layer_manager.add_layer_from_file(file)
        return True

    def handleCustomUriDrop(self, uri: QgsMimeDataUtils.Uri) -> None:
        self.layer_manager.add_layer_from_file(uri.uri)
        return super().handleCustomUriDrop(uri)

    def customUriProviderKey(self) -> str:
        return COVERAGE_JSON_PROVIDERKEY


class CoverageJSONItemProvider(QgsDataItemProvider):
    """
    Data item provider for CoverageJSON files
    """

    def __init__(self, layer_manager):
        super().__init__()
        self.layer_manager = layer_manager

    def name(self):  # pylint: disable=missing-docstring
        return "coveragejson"

    def capabilities(self):  # pylint: disable=missing-docstring
        return QgsDataProvider.File

    def createDataItem(self, path, parentItem):  # pylint: disable=missing-docstring
        file_info = QFileInfo(path)

        if is_path_coverage_json(file_info.suffix()):
            return CoverageJSONItem(parentItem, file_info.fileName(), path, self.layer_manager)
        return None


class CoverageJSONItem(QgsDataItem):
    """
    Data item for CoverageJSON files
    """

    def __init__(self, parent, name, path, layer_manager):
        super().__init__(QgsDataItem.Custom, parent, name, path)
        self.setState(QgsDataItem.Populated)  # no children
        self.setToolTip(QDir.toNativeSeparators(path))
        self.layer_manager = layer_manager

    def hasDragEnabled(self):  # pylint: disable=missing-docstring
        return True

    def handleDoubleClick(self):  # pylint: disable=missing-docstring
        self.open_coveragejson()
        return True

    def mimeUri(self):  # pylint: disable=missing-docstring
        u = QgsMimeDataUtils.Uri()
        u.layerType = "custom"
        u.providerKey = COVERAGE_JSON_PROVIDERKEY
        u.name = self.name()
        u.uri = self.path()
        return u

    def mimeUris(self):  # pylint: disable=missing-docstring
        return [self.mimeUri()]

    def open_coveragejson(self):
        """
        Handles opening coveragejson files
        """
        self.layer_manager.add_layer_from_file(self.path())
        return True

    def actions(self, parent):  # pylint: disable=missing-docstring
        if is_path_coverage_json(self.path()):
            action_text = QCoreApplication.translate("CoverageJSON", "&Open CoverageJSON…")
        open_action = QAction(action_text, parent)
        open_action.triggered.connect(self.open_coveragejson)
        return [open_action]

    def icon(self) -> QIcon:
        return QIcon(QgsApplication.getThemeIcon("/mIconFile.svg"))
