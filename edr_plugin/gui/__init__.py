import os

from qgis.PyQt import uic
from qgis.PyQt.QtCore import QSettings
from qgis.PyQt.QtWidgets import QDialog, QInputDialog

from edr_plugin.api_client import EDRApiClient, EDRApiClientError


class EDRDialog(QDialog):
    def __init__(self, plugin, parent=None):
        QDialog.__init__(self, parent)
        ui_filepath = os.path.join(os.path.dirname(os.path.realpath(__file__)), "ui", "edr.ui")
        self.ui = uic.loadUi(ui_filepath, self)
        self.plugin = plugin
        self.api_client = EDRApiClient("https://labs.metoffice.gov.uk/edr")
        self.cancel_pb.clicked.connect(self.close)
        self.get_data_pb.clicked.connect(self.populate_collections)
        self.populate_collections()

    def populate_collections(self):
        self.collection_cbo.clear()
        for collection in self.api_client.get_collections():
            collection_name = collection["title"]
            self.collection_cbo.addItem(collection_name, collection)
