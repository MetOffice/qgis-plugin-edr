import json

import sip
from qgis.core import QgsDataCollectionItem, QgsDataItem, QgsDataItemProvider, QgsDataProvider, QgsSettings
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction

from edr_plugin.utils import EdrSettingsPath, icon_filepath


class EdrRootItem(QgsDataCollectionItem):
    """EDR root data containing server groups item with saved queries within servers."""

    def __init__(
        self,
        plugin,
        name=None,
        parent=None,
    ):
        name = plugin.PLUGIN_NAME if not name else name
        provider_key = plugin.PLUGIN_ENTRY_NAME
        QgsDataCollectionItem.__init__(self, parent, name, provider_key)
        self.plugin = plugin
        self.setIcon(QIcon(icon_filepath("edr.png")))
        self.server_items = []

    def createChildren(self):
        settings = QgsSettings()
        available_servers = settings.value("edr_plugin/server_urls", [])
        items = []
        for server_url in available_servers:
            server_item = EdrServerItem(self.plugin, server_url, self)
            server_item.setState(QgsDataItem.Populated)
            server_item.refresh()
            sip.transferto(server_item, self)
            items.append(server_item)
            self.server_items.append(server_item)
        return items

    def refresh_server_items(self):
        for item in self.server_items:
            item.refresh()

    def reload_collections(self):
        self.plugin.ensure_main_dialog_initialized()
        self.plugin.main_dialog.populate_collections()
        self.plugin.run()

    def actions(self, parent):
        action_new_query = QAction(QIcon(icon_filepath("play.png")), "New query", parent)
        action_new_query.triggered.connect(self.plugin.run)
        action_reload_collections = QAction(QIcon(icon_filepath("reload.png")), "Reload collections", parent)
        action_reload_collections.triggered.connect(self.reload_collections)
        action_refresh = QAction(QIcon(icon_filepath("refresh.png")), "Refresh", parent)
        action_refresh.triggered.connect(self.refresh_server_items)
        actions = [action_new_query, action_reload_collections, action_refresh]
        return actions


class EdrServerItem(EdrRootItem):
    """EDR server data item. Contains saved queries."""

    def __init__(self, plugin, server_url, parent):
        EdrRootItem.__init__(self, plugin, server_url, parent)
        self.plugin = plugin
        self.server_url = server_url
        self.setIcon(QIcon(icon_filepath("server.png")))
        self.query_items = []

    def new_server_query(self):
        self.plugin.ensure_main_dialog_initialized()
        self.plugin.main_dialog.server_url_cbo.setCurrentText(self.server_url)
        self.plugin.run()

    def createChildren(self):
        settings = QgsSettings()
        saved_queries = json.loads(settings.value(EdrSettingsPath.SAVED_QUERIES.value, "{}"))
        queries = saved_queries.get(self.server_url, {})
        items = []
        for query_name in queries.keys():
            query_item = SavedQueryItem(self.plugin, self.server_url, query_name, self)
            query_item.setState(QgsDataItem.Populated)
            query_item.refresh()
            sip.transferto(query_item, self)
            items.append(query_item)
            self.query_items.append(query_item)
        return items

    def actions(self, parent):
        action_new_server_query = QAction(QIcon(icon_filepath("play_solid.png")), "New server query", parent)
        action_new_server_query.triggered.connect(self.new_server_query)
        actions = [action_new_server_query]
        return actions


class SavedQueryItem(QgsDataItem):
    """Saved query item."""

    def __init__(self, plugin, server_url, query_name, parent):
        self.plugin = plugin
        self.server_url = server_url
        self.query_name = query_name
        QgsDataItem.__init__(self, QgsDataItem.Collection, parent, query_name, f"/{server_url}/{query_name}")
        self.setIcon(QIcon(icon_filepath("request.png")))

    def repeat_query(self):
        self.plugin.ensure_main_dialog_initialized()
        self.plugin.main_dialog.repeat_saved_query_data_collection(self.server_url, self.query_name)

    def delete_query(self):
        settings = QgsSettings()
        saved_queries = json.loads(settings.value(EdrSettingsPath.SAVED_QUERIES.value, "{}"))
        del saved_queries[self.server_url][self.query_name]
        settings.setValue(EdrSettingsPath.SAVED_QUERIES.value, json.dumps(saved_queries))
        self.parent().refresh()

    def actions(self, parent):
        action_repeat = QAction(QIcon(icon_filepath("replay.png")), "Repeat query", parent)
        action_repeat.triggered.connect(self.repeat_query)
        action_delete = QAction(QIcon(icon_filepath("delete.png")), "Delete", parent)
        action_delete.triggered.connect(self.delete_query)
        actions = [action_repeat, action_delete]
        return actions


class SavedQueriesItemProvider(QgsDataItemProvider):
    """Saved queries provider."""

    def __init__(self, plugin):
        QgsDataItemProvider.__init__(self)
        self.root_item = None
        self.plugin = plugin

    def name(self):
        return "EdrProvider"

    def capabilities(self):
        return QgsDataProvider.Net

    def createDataItem(self, path, parentItem):
        if not parentItem:
            ri = EdrRootItem(plugin=self.plugin)
            sip.transferto(ri, None)
            self.root_item = ri
            return ri
        else:
            return None
