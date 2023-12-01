import os

from qgis.PyQt import uic
from qgis.PyQt.QtCore import QSettings
from qgis.PyQt.QtWidgets import QDialog, QInputDialog


class EDRSettingsDialog(QDialog):
    def __init__(self, plugin, parent=None):
        QDialog.__init__(self, parent)
        # ui_filepath = os.path.join(os.path.dirname(os.path.realpath(__file__)), "ui", "settings.ui")
        # self.ui = uic.loadUi(ui_filepath, self)
        self.plugin = plugin
