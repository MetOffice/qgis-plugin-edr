import json

from qgis.core import QgsDataCollectionItem, QgsDataItem, QgsDataItemProvider, QgsDataProvider, QgsSettings
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction, QInputDialog

from edr_plugin.utils import EdrSettingsPath, icon_filepath


class EdrRootItem(QgsDataCollectionItem):
    """EDR root data containing server groups item with saved queries within servers."""

    def __init__(
        self,
        plugin,
        name=None,
        parent=None,
    ):
        super().__init__(parent, plugin.PLUGIN_NAME if not name else name, plugin.PLUGIN_ENTRY_NAME)
        self.plugin = plugin
        self.setIcon(QIcon(icon_filepath("edr.png")))
        self.server_items = []

    def createChildren(self):
        del self.server_items[:]
        settings = QgsSettings()
        available_servers = settings.value(EdrSettingsPath.SAVED_SERVERS.value, [])
        saved_queries = json.loads(settings.value(EdrSettingsPath.SAVED_QUERIES.value, "{}"))
        items = []
        for server_url in available_servers:
            queries = saved_queries.get(server_url, {})
            if not queries:
                continue
            server_item = EdrServerItem(self.plugin, server_url, self)
            server_item.setState(QgsDataItem.Populated)
            server_item.refresh()
            items.append(server_item)
            self.server_items.append(server_item)
        return items

    def refresh_server_items(self):
        self.depopulate()
        self.createChildren()

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
        super().__init__(plugin, server_url, parent)
        self.plugin = plugin
        self.server_url = server_url
        self.setIcon(QIcon(icon_filepath("server.png")))
        self.query_items = []

    def new_server_query(self):
        self.plugin.ensure_main_dialog_initialized()
        self.plugin.main_dialog.server_url_cbo.setCurrentText(self.server_url)
        self.plugin.run()

    def delete_server_queries(self):
        deletion_confirmed = self.plugin.communication.ask(
            None, "Confirm deletion", "Are you sure you want to delete all saved queries for this server?"
        )
        if deletion_confirmed:
            settings = QgsSettings()
            saved_queries = json.loads(settings.value(EdrSettingsPath.SAVED_QUERIES.value, "{}"))
            queries = saved_queries.get(self.server_url, {})
            queries.clear()
            settings.setValue(EdrSettingsPath.SAVED_QUERIES.value, json.dumps(saved_queries))
            self.parent().refresh_server_items()

    def createChildren(self):
        settings = QgsSettings()
        saved_queries = json.loads(settings.value(EdrSettingsPath.SAVED_QUERIES.value, "{}"))
        queries = saved_queries.get(self.server_url, {})
        items = []
        for query_name in queries.keys():
            query_item = SavedQueryItem(self.plugin, self.server_url, query_name, self)
            query_item.setState(QgsDataItem.Populated)
            query_item.refresh()
            items.append(query_item)
            self.query_items.append(query_item)
        return items

    def actions(self, parent):
        action_new_server_query = QAction(QIcon(icon_filepath("play_solid.png")), "New server query", parent)
        action_new_server_query.triggered.connect(self.new_server_query)
        action_delete_server_queries = QAction(QIcon(icon_filepath("delete_all.png")), "Delete server queries", parent)
        action_delete_server_queries.triggered.connect(self.delete_server_queries)
        actions = [action_new_server_query, action_delete_server_queries]
        return actions


class SavedQueryItem(QgsDataItem):
    """Saved query item."""

    def __init__(self, plugin, server_url, query_name, parent):
        super().__init__(QgsDataItem.Collection, parent, query_name, f"/{server_url}/{query_name}")
        self.plugin = plugin
        self.server_url = server_url
        self.query_name = query_name
        self.setIcon(QIcon(icon_filepath("request.png")))

    def repeat_query(self):
        self.plugin.ensure_main_dialog_initialized()
        self.plugin.main_dialog.repeat_saved_query_data_collection(self.server_url, self.query_name)

    def rename_query(self):
        settings = QgsSettings()
        saved_queries = json.loads(settings.value(EdrSettingsPath.SAVED_QUERIES.value, "{}"))
        new_name, accept = QInputDialog.getText(None, "Rename", "New name", text=self.name())
        if accept:
            server_saved_queries = saved_queries[self.server_url]
            if not new_name:
                self.plugin.communication.show_warn("Empty name provided. Renaming canceled!")
                return
            if new_name in server_saved_queries:
                self.plugin.communication.show_warn("Query name already exists. Renaming canceled!")
                return
            self.setName(new_name)
            server_saved_queries[new_name] = server_saved_queries[self.query_name]
            del server_saved_queries[self.query_name]
            settings.setValue(EdrSettingsPath.SAVED_QUERIES.value, json.dumps(saved_queries))
            self.parent().refresh()

    def delete_query(self):
        settings = QgsSettings()
        saved_queries = json.loads(settings.value(EdrSettingsPath.SAVED_QUERIES.value, "{}"))
        del saved_queries[self.server_url][self.query_name]
        settings.setValue(EdrSettingsPath.SAVED_QUERIES.value, json.dumps(saved_queries))
        self.parent().refresh()

    def actions(self, parent):
        action_repeat = QAction(QIcon(icon_filepath("replay.png")), "Repeat query", parent)
        action_repeat.triggered.connect(self.repeat_query)
        action_rename = QAction(QIcon(icon_filepath("rename.png")), "Rename query", parent)
        action_rename.triggered.connect(self.rename_query)
        action_delete = QAction(QIcon(icon_filepath("delete.png")), "Delete", parent)
        action_delete.triggered.connect(self.delete_query)
        actions = [action_repeat, action_rename, action_delete]
        return actions


class SavedQueriesItemProvider(QgsDataItemProvider):
    """Saved queries provider."""

    def __init__(self, plugin):
        super().__init__()
        self.root_item = None
        self.plugin = plugin

    def name(self):
        return "EdrProvider"

    def capabilities(self):
        return QgsDataProvider.Net

    def createDataItem(self, path, parentItem):
        if not parentItem:
            ri = EdrRootItem(plugin=self.plugin)
            self.root_item = ri
            return ri
        else:
            return None
