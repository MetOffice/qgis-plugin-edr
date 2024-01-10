import os.path

from qgis.PyQt.QtCore import QThreadPool
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction

from edr_plugin.gui import EdrDialog
from edr_plugin.utils.communication import UICommunication
from edr_plugin.visualization import EdrLayerManager


def classFactory(iface):
    return EDRPlugin(iface)


class EDRPlugin:
    PLUGIN_NAME = "Environmental Data Retrieval"
    PLUGIN_ENTRY_NAME = "EDR"
    MAX_SIMULTANEOUS_DOWNLOADS = 1

    def __init__(self, iface):
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)
        self.menu = self.PLUGIN_NAME
        self.toolbar = self.iface.addToolBar(self.PLUGIN_ENTRY_NAME)
        self.toolbar.setObjectName(self.PLUGIN_ENTRY_NAME)
        self.downloader_pool = QThreadPool()
        self.downloader_pool.setMaxThreadCount(self.MAX_SIMULTANEOUS_DOWNLOADS)
        self.main_dialog = None
        self.layer_manager = EdrLayerManager(self)
        self.communication = UICommunication(self.iface, self.PLUGIN_NAME)
        self.actions = []

    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None,
    ):
        """Add a toolbar icon to the toolbar."""

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            self.toolbar.addAction(action)

        if add_to_menu:
            self.iface.addPluginToMenu(self.menu, action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""
        icon_path = os.path.join(self.plugin_dir, "icon.svg")
        self.add_action(icon_path, text=self.PLUGIN_NAME, callback=self.run, parent=self.iface.mainWindow())

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(self.PLUGIN_NAME, action)
            self.iface.removeToolBarIcon(action)
        # remove the toolbar
        del self.toolbar

    def run(self):
        """Run method that loads and starts the plugin"""
        if self.main_dialog is None:
            self.main_dialog = EdrDialog(self)
        self.main_dialog.show()
        self.main_dialog.raise_()
        self.main_dialog.activateWindow()
