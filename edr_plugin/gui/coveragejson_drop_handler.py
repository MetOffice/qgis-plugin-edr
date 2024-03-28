from PyQt5.QtCore import QMimeData, Qt
from qgis.core import QgsDataItem, QgsDataItemProvider, QgsDataProvider, QgsMimeDataUtils
from qgis.gui import QgsCustomDropHandler
from qgis.PyQt.QtCore import QCoreApplication, QDir, QFileInfo
from qgis.PyQt.QtWidgets import QAction


class CoverageJSONDropHandler(QgsCustomDropHandler):
    """
    coveragejson file drop handler
    """

    def __init__(self, layer_manager) -> None:
        super().__init__()
        self.layer_manager = layer_manager

    def handleFileDrop(self, file):  # pylint: disable=missing-docstring
        if not (file.lower().endswith("coveragejson") or file.lower().endswith("covjson")):
            return False
        self.layer_manager.add_layer_from_file(file)
        return True
class CoverageJSONItemProvider(QgsDataItemProvider):
    """
    Data item provider for coveragejson files
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

        if file_info.suffix().lower() == "coveragejson" or file_info.suffix().lower() == "covjson":
            return CoverageJSONItem(parentItem, file_info.fileName(), path, self.layer_manager)
        return None


class CoverageJSONItem(QgsDataItem):
    """
    Data item for .mxd files
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

    def handleDrop(self, a0: QMimeData, a1: Qt.DropAction) -> bool:
        pass
        return super().handleDrop(a0, a1)

    # def icon(self):  # pylint: disable=missing-docstring
    #     return GuiUtils.get_icon("mxd.svg")

    def mimeUri(self):  # pylint: disable=missing-docstring
        u = QgsMimeDataUtils.Uri()
        u.layerType = "custom"
        u.providerKey = "coveragejson"
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
        if self.path().lower().endswith("covjson") or self.path().lower().endswith("coveragejson"):
            action_text = QCoreApplication.translate("CoverageJSON", "&Open CoverageJSON…")
        open_action = QAction(action_text, parent)
        open_action.triggered.connect(self.open_coveragejson)
        return [open_action]
