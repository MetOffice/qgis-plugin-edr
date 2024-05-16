import json
import os
from datetime import datetime
from functools import partial

from qgis.core import QgsCoordinateReferenceSystem, QgsGeometry, QgsSettings
from qgis.gui import QgsCollapsibleGroupBox
from qgis.PyQt import uic
from qgis.PyQt.QtCore import QDateTime, Qt
from qgis.PyQt.QtWidgets import QCheckBox, QComboBox, QDateTimeEdit, QDialog, QFileDialog, QInputDialog, QLineEdit

from edr_plugin.api_client import EdrApiClient, EdrApiClientError
from edr_plugin.gui.query_tools import (
    AreaQueryBuilderTool,
    CorridorQueryBuilderTool,
    CubeQueryBuilderTool,
    ItemsQueryBuilderTool,
    LocationsQueryBuilderTool,
    PositionQueryBuilderTool,
    RadiusQueryBuilderTool,
    TrajectoryQueryBuilderTool,
)
from edr_plugin.queries import (
    AreaQueryDefinition,
    CorridorQueryDefinition,
    CubeQueryDefinition,
    ItemsQueryDefinition,
    LocationsQueryDefinition,
    PositionQueryDefinition,
    RadiusQueryDefinition,
    TrajectoryQueryDefinition,
)
from edr_plugin.queries.enumerators import EdrDataQuery
from edr_plugin.threading import EdrDataDownloader
from edr_plugin.utils import EdrSettingsPath, is_dir_writable, reproject_geometry


class EdrDialog(QDialog):
    """Main EDR plugin dialog."""

    def __init__(self, plugin, parent=None):
        QDialog.__init__(self, parent)
        ui_filepath = os.path.join(os.path.dirname(os.path.realpath(__file__)), "ui", "edr.ui")
        self.ui = uic.loadUi(ui_filepath, self)
        self.plugin = plugin
        self.settings = QgsSettings()
        server_urls = self.read_server_urls()
        self.server_url_cbo.addItems(server_urls)
        last_used_server_url = self.settings.value(EdrSettingsPath.LAST_SERVER_URL.value)
        if last_used_server_url:
            self.server_url_cbo.setCurrentText(last_used_server_url)
        edr_authcfg = self.settings.value(EdrSettingsPath.LAST_AUTHCFG.value, "", type=str)
        self.server_auth_config.setConfigId(edr_authcfg)
        download_dir = self.settings.value(EdrSettingsPath.DOWNLOAD_DIR.value, "", type=str)
        self.download_dir_le.setText(download_dir)
        self.api_client = EdrApiClient(
            self.server_url_cbo.currentText(),
            authentication_config_id=edr_authcfg,
            use_post_request=self.post_cbox.isChecked(),
        )
        self.current_data_query_tool = None
        self.server_url_cbo.currentTextChanged.connect(self.set_edr_server_url)
        self.add_server_pb.clicked.connect(self.add_edr_server_url)
        self.remove_server_pb.clicked.connect(self.remove_edr_server_url)
        self.server_auth_config.selectedConfigIdChanged.connect(self.on_edr_credentials_changed)
        self.post_cbox.stateChanged.connect(self.on_request_method_changed)
        self.change_download_dir_pb.clicked.connect(self.set_download_directory)
        self.collection_cbo.currentIndexChanged.connect(self.populate_collection_data)
        self.instance_cbo.currentIndexChanged.connect(self.populate_data_queries)
        self.query_cbo.currentIndexChanged.connect(self.populate_data_query_attributes)
        self.query_set_pb.clicked.connect(self.set_query_extent)
        self.toggle_parameters_cbox.stateChanged.connect(self.toggle_parameters)
        self.toggle_vertical_intervals_cbox.stateChanged.connect(self.toggle_vertical_intervals)
        self.custom_dimension_cbo.currentIndexChanged.connect(self.populate_custom_dimension_values)
        self.toggle_custom_intervals_cbox.stateChanged.connect(self.toggle_custom_intervals)
        self.cancel_pb.clicked.connect(self.close)
        self.run_and_save_pb.clicked.connect(partial(self.query_data_collection, True))
        self.run_pb.clicked.connect(self.query_data_collection)
        self.run_pb.setFocus()
        if server_urls:
            self.populate_collections()
            self.populate_collection_data()

    def read_server_urls(self):
        """Read server urls from QGIS settings."""
        server_urls = self.settings.value(EdrSettingsPath.SAVED_SERVERS.value, [])
        return server_urls

    def save_server_urls(self):
        """Save server urls into QGIS settings."""
        server_urls = [self.server_url_cbo.itemText(i) for i in range(self.server_url_cbo.count())]
        self.settings.setValue(EdrSettingsPath.SAVED_SERVERS.value, server_urls)

    def set_edr_server_url(self):
        """Set EDR server URL."""
        current_server_url = self.server_url_cbo.currentText()
        authcfg = self.server_auth_config.configId()
        self.api_client = EdrApiClient(
            current_server_url,
            authentication_config_id=authcfg,
            use_post_request=self.post_cbox.isChecked(),
        )
        self.settings.setValue(EdrSettingsPath.LAST_SERVER_URL.value, current_server_url)
        self.populate_collections()
        self.populate_collection_data()

    def add_edr_server_url(self):
        """Add EDR server URL."""
        server_url, accept = QInputDialog.getText(self, "Add EDR Server URL", "Type EDR Server URL:")
        if accept is False:
            return
        server_url = server_url.strip("/")
        if self.server_url_cbo.findText(server_url) > -1:
            return
        self.server_url_cbo.addItem(server_url)
        self.server_url_cbo.setCurrentText(server_url)
        self.set_edr_server_url()
        self.save_server_urls()

    def remove_edr_server_url(self):
        """Remove EDR server URL."""
        self.server_url_cbo.removeItem(self.server_url_cbo.currentIndex())
        self.save_server_urls()

    def on_edr_credentials_changed(self, edr_authcfg):
        """Update EDR server credential settings."""
        server_url = self.server_url_cbo.currentText()
        self.settings.setValue(EdrSettingsPath.LAST_AUTHCFG.value, edr_authcfg)
        self.api_client = EdrApiClient(
            server_url,
            authentication_config_id=edr_authcfg,
            use_post_request=self.post_cbox.isChecked(),
        )
        self.populate_collections()
        self.populate_collection_data()

    def set_download_directory(self):
        """Set download directory."""
        last_download_dir = self.download_dir_le.text()
        parent_download_dir = os.path.dirname(last_download_dir) if last_download_dir else ""
        download_dir = QFileDialog.getExistingDirectory(self, "Pick download directory", parent_download_dir)
        if not download_dir:
            return
        if is_dir_writable(download_dir):
            self.settings.setValue(EdrSettingsPath.DOWNLOAD_DIR.value, download_dir)
            self.download_dir_le.setText(download_dir)
        else:
            self.plugin.communication.bar_warn("Can't write to the selected location. Please pick another folder.")
            return

    def on_request_method_changed(self):
        """Update the API client request method (GET or POST)."""
        self.api_client.use_post_request = self.post_cbox.isChecked()

    def toggle_parameters(self, checked):
        """Check/uncheck all available parameters."""
        if checked:
            self.parameters_cbo.selectAllOptions()
        else:
            self.parameters_cbo.deselectAllOptions()

    def toggle_vertical_intervals(self, checked):
        """Check/uncheck all vertical intervals."""
        if checked:
            self.vertical_intervals_cbo.selectAllOptions()
        else:
            self.vertical_intervals_cbo.deselectAllOptions()

    def toggle_custom_intervals(self, checked):
        """Check/uncheck all custom dimension intervals."""
        if checked:
            self.custom_intervals_cbo.selectAllOptions()
        else:
            self.custom_intervals_cbo.deselectAllOptions()

    @property
    def data_query_definitions(self):
        """Return query definition class associated with type of the query."""
        query_definitions_map = {
            EdrDataQuery.AREA.value: AreaQueryDefinition,
            EdrDataQuery.CUBE.value: CubeQueryDefinition,
            EdrDataQuery.POSITION.value: PositionQueryDefinition,
            EdrDataQuery.RADIUS.value: RadiusQueryDefinition,
            EdrDataQuery.ITEMS.value: ItemsQueryDefinition,
            EdrDataQuery.LOCATIONS.value: LocationsQueryDefinition,
            EdrDataQuery.TRAJECTORY.value: TrajectoryQueryDefinition,
            EdrDataQuery.CORRIDOR.value: CorridorQueryDefinition,
        }
        return query_definitions_map

    @property
    def data_query_tools(self):
        """Return query builder tool associated with type of the query."""
        query_tools_map = {
            EdrDataQuery.AREA.value: AreaQueryBuilderTool,
            EdrDataQuery.CUBE.value: CubeQueryBuilderTool,
            EdrDataQuery.POSITION.value: PositionQueryBuilderTool,
            EdrDataQuery.RADIUS.value: RadiusQueryBuilderTool,
            EdrDataQuery.ITEMS.value: ItemsQueryBuilderTool,
            EdrDataQuery.LOCATIONS.value: LocationsQueryBuilderTool,
            EdrDataQuery.TRAJECTORY.value: TrajectoryQueryBuilderTool,
            EdrDataQuery.CORRIDOR.value: CorridorQueryBuilderTool,
        }
        return query_tools_map

    @property
    def collection_level_widgets(self):
        """Collection level widgets."""
        widgets = [self.instance_cbo] + self.instance_level_widgets
        return widgets

    @property
    def instance_level_widgets(self):
        """Instance level widgets."""
        widgets = [self.query_cbo] + self.query_level_widgets
        return widgets

    @property
    def query_level_widgets(self):
        """Query level widgets."""
        widgets = [
            self.query_extent_le,
            self.crs_cbo,
            self.format_cbo,
            self.parameters_cbo,
            self.toggle_parameters_cbox,
            self.temporal_grp,
            self.vertical_grp,
            self.custom_grp,
            self.from_datetime,
            self.to_datetime,
            self.vertical_intervals_cbo,
            self.toggle_vertical_intervals_cbox,
            self.use_vertical_range_cbox,
            self.custom_dimension_cbo,
            self.custom_intervals_cbo,
            self.use_vertical_range_cbox,
            self.toggle_vertical_intervals_cbox,
        ]
        return widgets

    @staticmethod
    def clear_widgets(*widgets):
        """Clear widgets."""
        for widget in widgets:
            if isinstance(widget, QgsCollapsibleGroupBox):
                widget.setDisabled(True)
            elif isinstance(widget, QCheckBox):
                widget.setChecked(False)
            elif isinstance(widget, (QComboBox, QDateTimeEdit, QLineEdit)):
                widget.clear()
            else:
                pass

    def populate_collections(self):
        """Populate available collections."""
        self.clear_widgets(self.collection_cbo, *self.collection_level_widgets)
        try:
            for collection in self.api_client.get_collections():
                collection_id = collection["id"]
                collection_name = collection.get("title", collection_id)
                if not collection_name:
                    collection_name = collection_id
                self.collection_cbo.addItem(collection_name, collection)
        except Exception as e:
            self.plugin.communication.show_error(f"Fetching collections failed due to the following error:\n{e}")

    def _crs_from_combobox(self) -> QgsCoordinateReferenceSystem:
        crs_name, crs_wkt = self.crs_cbo.currentText(), self.crs_cbo.currentData()
        if crs_wkt:
            crs = QgsCoordinateReferenceSystem.fromWkt(crs_wkt)
        else:
            crs = QgsCoordinateReferenceSystem.fromOgcWmsCrs(crs_name)
        return crs

    def populate_collection_data(self):
        """Populate collection data."""
        previous_geom = None
        previous_query_type = None
        previous_crs = None
        previous_query_data_tool = self.current_data_query_tool
        if self.query_extent_le.text():
            previous_geom = QgsGeometry.fromWkt(self.query_extent_le.text())
            previous_query_type = self.query_cbo.currentText()
            previous_crs = self._crs_from_combobox()

        try:
            self.clear_widgets(*self.collection_level_widgets)
            collection = self.collection_cbo.currentData()
            if not collection:
                return
            try:
                instance_link = False
                data_queries = collection["data_queries"]
                # Add for legacy implementations
                c_links = collection["links"]
                for c_link in c_links:
                    if "/instances" in c_link["href"].lower():
                        instance_link = True
            except KeyError:
                return
            if ("instances" in data_queries) or instance_link:
                self.instance_cbo.setEnabled(True)
                self.populate_instances()
            else:
                self.instance_cbo.setDisabled(True)
                self.populate_data_queries()

            if previous_geom:
                for i in range(self.query_cbo.count()):
                    query_type = self.query_cbo.itemText(i)
                    if query_type == previous_query_type:
                        self.query_cbo.setCurrentIndex(i)
                        current_crs = self._crs_from_combobox()
                        if previous_crs == current_crs:
                            self.current_data_query_tool = previous_query_data_tool
                            self.query_extent_le.setText(previous_geom.asWkt().upper())
                            self.query_extent_le.setCursorPosition(0)
                            break

        except Exception as e:
            self.plugin.communication.show_error(f"Populating collection data failed due to the following error:\n{e}")

    def populate_instances(self):
        """Populate instances."""
        try:
            self.clear_widgets(*self.collection_level_widgets)
            self.instance_cbo.setEnabled(True)
            collection = self.collection_cbo.currentData()
            if not collection:
                return
            collection_id = collection["id"]
            instances = self.api_client.get_collection_instances(collection_id)
            for instance in instances:
                instance_id = instance["id"]
                self.instance_cbo.addItem(instance_id, instance)
            self.populate_data_queries()
        except Exception as e:
            self.plugin.communication.show_error(f"Populating instances failed due to the following error:\n{e}")

    def populate_data_queries(self):
        """Populate collection data queries."""
        try:
            self.clear_widgets(*self.instance_level_widgets)
            if self.instance_cbo.isEnabled():
                collection = self.instance_cbo.currentData()
            else:
                collection = self.collection_cbo.currentData()
            if not collection:
                return
            try:
                data_queries = collection["data_queries"]
            except KeyError:
                return
            for query_name, data_query in data_queries.items():
                if query_name not in self.data_query_tools:
                    continue
                self.query_cbo.addItem(query_name, data_query)
            self.populate_data_query_attributes()
        except Exception as e:
            self.plugin.communication.show_error(f"Populating data queries failed due to the following error:\n{e}")

    def populate_custom_dimension_values(self):
        """Populate custom dimension values."""
        try:
            self.custom_intervals_cbo.clear()
            current_dimension = self.custom_dimension_cbo.currentData()
            if current_dimension:
                raw_custom_values = current_dimension["values"]
                if len(raw_custom_values) == 1:
                    value = raw_custom_values[0]
                    if isinstance(value, str):
                        if value.startswith("R"):
                            try:
                                num_of_intervals, min_value, interval_step = [int(v) for v in value[1:].split("/")]
                                custom_values = [str(v) for v in range(min_value, num_of_intervals + 1, interval_step)]
                            except ValueError:
                                custom_values = [value]
                        elif "," in value:
                            custom_values = [v for v in value.split(",")]
                        else:
                            custom_values = [value]
                    else:
                        custom_values = [str(value)]
                else:
                    custom_values = raw_custom_values
                self.custom_intervals_cbo.addItems(custom_values)
                self.custom_intervals_cbo.toggleItemCheckState(0)
        except Exception as e:
            self.plugin.communication.show_error(
                f"Populating custom dimensions failed due to the following error:\n{e}"
            )

    def populate_data_query_attributes(self):
        """Populate data query attributes."""
        try:
            self.current_data_query_tool = None
            self.clear_widgets(*self.query_level_widgets)
            if self.instance_cbo.isEnabled():
                collection = self.instance_cbo.currentData()
            else:
                collection = self.collection_cbo.currentData()
            if not collection:
                return
            data_query = self.query_cbo.currentData()
            if not data_query:
                return
            crs_data = []
            for crs_name in collection.get("crs", []):
                crs = QgsCoordinateReferenceSystem.fromOgcWmsCrs(crs_name)
                crs_wkt = crs.toWkt()
                crs_data.append((crs_name, crs_wkt))
            output_formats = collection.get("output_formats", [])
            default_output_format = ""
            data_link = data_query["link"]
            data_query_variables = data_link.get("variables", {})
            if data_query_variables:
                crs_details = data_query_variables.get("crs_details", [])
                if crs_details:
                    del crs_data[:]
                for crs_detail in crs_details:
                    crs_name = crs_detail["crs"]
                    crs_wkt = crs_detail["wkt"]
                    crs_data.append((crs_name, crs_wkt))
                output_formats = data_query_variables.get("output_formats", output_formats)
                default_output_format = data_query_variables.get("default_output_format", default_output_format)
            for crs_name, crs_wkt in crs_data:
                self.crs_cbo.addItem(crs_name, crs_wkt)
            self.format_cbo.addItems(output_formats)
            self.format_cbo.setCurrentText(default_output_format)
            parameter_names = collection["parameter_names"]
            for parameter, parameter_data in parameter_names.items():
                if "label" in parameter_data:
                    observed_property_label = parameter_data["label"]
                else:
                    observed_property = parameter_data["observedProperty"]
                    observed_property_label = observed_property["label"]
                parameter_description = parameter_data.get("description", observed_property_label)
                self.parameters_cbo.addItem(parameter_description, parameter)
            self.parameters_cbo.toggleItemCheckState(0)
            collection_extent = collection["extent"]
            try:
                self.temporal_grp.setEnabled(True)
                temporal_extent = collection_extent["temporal"]
                temporal_interval = temporal_extent["interval"]
                from_datetime_str, to_datetime_str = temporal_interval[0]
                from_datetime = QDateTime.fromString(from_datetime_str, Qt.ISODate)
                to_datetime = QDateTime.fromString(to_datetime_str, Qt.ISODate)
                self.from_datetime.setTimeSpec(Qt.UTC)
                self.to_datetime.setTimeSpec(Qt.UTC)
                self.from_datetime.setDateTime(from_datetime)
                self.to_datetime.setDateTime(to_datetime)
            except KeyError:
                self.temporal_grp.setDisabled(True)
            try:
                self.vertical_grp.setEnabled(True)
                vertical_extent = collection_extent["vertical"]
                vertical_values = vertical_extent["values"]
                self.vertical_intervals_cbo.addItems(vertical_values)
                self.vertical_intervals_cbo.toggleItemCheckState(0)
            except KeyError:
                self.vertical_grp.setDisabled(True)
            try:
                self.custom_grp.setEnabled(True)
                custom_dimensions = collection_extent["custom"]
                for custom_dimension in custom_dimensions:
                    custom_dimension_name = custom_dimension["id"]
                    self.custom_dimension_cbo.addItem(custom_dimension_name, custom_dimension)
                self.custom_dimension_cbo.setCurrentIndex(0)
                self.populate_custom_dimension_values()
            except KeyError:
                self.custom_grp.setDisabled(True)
        except Exception as e:
            self.plugin.communication.show_error(
                f"Populating data query attributes failed due to the following error:\n{e}"
            )

    def collect_query_parameters(self):
        """Collect query parameters from the widgets."""
        collection = self.collection_cbo.currentData()
        collection_id = collection["id"]
        sub_endpoints, query_parameters = {}, {}
        if self.instance_cbo.isEnabled():
            sub_endpoints["instance_id"] = self.instance_cbo.currentText()
        query_parameters["output_crs"] = self.crs_cbo.currentText()
        query_parameters["output_format"] = self.format_cbo.currentText()
        query_parameters["parameters"] = self.parameters_cbo.checkedItemsData()
        if self.temporal_grp.isEnabled():
            from_datetime = self.from_datetime.dateTime().toTimeSpec(Qt.UTC).toString(Qt.ISODate)
            to_datetime = self.to_datetime.dateTime().toTimeSpec(Qt.UTC).toString(Qt.ISODate)
            temporal_range = (
                (from_datetime,)
                if not to_datetime
                else (
                    from_datetime,
                    to_datetime,
                )
            )
            query_parameters["temporal_range"] = temporal_range
        if self.vertical_grp.isEnabled():
            vertical_intervals = self.vertical_intervals_cbo.checkedItems()
            vertical_is_min_max_range = self.use_vertical_range_cbox.isChecked()
            vertical_extent = (vertical_intervals, vertical_is_min_max_range)
            query_parameters["vertical_extent"] = vertical_extent
        if self.custom_grp.isEnabled():
            custom_dimension_name = self.custom_dimension_cbo.currentText()
            custom_intervals = self.custom_intervals_cbo.checkedItems()
            custom_is_min_max_range = self.use_custom_range_cbox.isChecked()
            custom_dimension = (custom_dimension_name, custom_intervals, custom_is_min_max_range)
            query_parameters["custom_dimension"] = custom_dimension
        return collection_id, sub_endpoints, query_parameters

    def set_query_extent(self):
        """Set query extent."""
        data_query = self.query_cbo.currentText()
        if not data_query:
            return
        try:
            data_query_tool_cls = self.data_query_tools[data_query]
        except KeyError:
            self.plugin.communication.show_warn(
                f"Missing implementation for '{data_query}' data queries. Action aborted."
            )
            return
        data_query_tool_cls(self)

    def query_data_collection(self, save_query=False):
        """Define data query and get the data collection."""
        collection = self.collection_cbo.currentData()
        if not collection:
            self.plugin.communication.show_warn(f"There is no any collection selected. Action aborted.")
            self.raise_()
            return
        data_query = self.query_cbo.currentText()
        if not data_query:
            self.plugin.communication.show_warn(f"There is no any query selected. Action aborted.")
            self.raise_()
            return
        if data_query not in self.data_query_tools:
            self.plugin.communication.show_warn(
                f"Missing implementation for '{data_query}' data queries. Action aborted."
            )
            self.raise_()
            return
        if self.current_data_query_tool is None:
            self.plugin.communication.show_warn("Query spatial extent is not set. Please set it and try again.")
            self.set_query_extent()
            return
        data_query_definition = self.current_data_query_tool.get_query_definition()
        download_dir = self.download_dir_le.text()
        if not download_dir:
            self.plugin.communication.show_warn("There is no download folder specified. Please set it and try again.")
            self.raise_()
            return
        server_url = self.server_url_cbo.currentText()
        edr_authcfg = self.server_auth_config.configId()
        worker_api_client = EdrApiClient(
            server_url,
            authentication_config_id=edr_authcfg,
            use_post_request=self.post_cbox.isChecked(),
        )
        download_worker = EdrDataDownloader(worker_api_client, data_query_definition, download_dir)
        download_worker.signals.download_progress.connect(self.on_progress_signal)
        download_worker.signals.download_success.connect(self.on_success_signal)
        download_worker.signals.download_failure.connect(self.on_failure_signal)
        if save_query:
            saved_queries = json.loads(self.settings.value(EdrSettingsPath.SAVED_QUERIES.value, "{}"))
            data_query_request_parameters = data_query_definition.as_request_parameters()
            timestamp = datetime.now().isoformat().split(".")[0]
            saved_query_id = f"{data_query_definition.collection_id} [{timestamp}]"
            if server_url not in saved_queries:
                saved_queries[server_url] = {}
            saved_query_value = {
                "query": data_query_request_parameters,
                "authcfg": edr_authcfg,
                "download_dir": download_dir,
            }
            try:
                saved_queries[server_url][saved_query_id] = saved_query_value
            except KeyError:
                saved_queries[server_url] = {saved_query_id: saved_query_value}
            self.settings.setValue(EdrSettingsPath.SAVED_QUERIES.value, json.dumps(saved_queries))
            self.plugin.saved_queries_provider.root_item.refresh_server_items()
        self.plugin.downloader_pool.start(download_worker)
        self.close()

    def read_saved_query(self, server_url, saved_query_id):
        """Read saved query data definition with server URL and authorization config ID."""
        saved_queries = json.loads(self.settings.value(EdrSettingsPath.SAVED_QUERIES.value, "{}"))
        saved_query_value = saved_queries[server_url][saved_query_id]
        data_query_request_parameters = saved_query_value["query"]
        collection_id, sub_endpoint_queries, query_parameters = data_query_request_parameters
        data_query_definition_cls = self.data_query_definitions[sub_endpoint_queries["query"]]
        data_query_definition = data_query_definition_cls.from_request_parameters(
            collection_id, sub_endpoint_queries, query_parameters
        )
        edr_authcfg = saved_query_value["authcfg"]
        download_dir = saved_query_value["download_dir"]
        return data_query_definition, edr_authcfg, download_dir

    def repeat_saved_query_data_collection(self, server_url, saved_query_id):
        """Repeat data collection query."""
        data_query_definition, edr_authcfg, download_dir = self.read_saved_query(server_url, saved_query_id)
        worker_api_client = EdrApiClient(
            server_url,
            authentication_config_id=edr_authcfg,
            use_post_request=self.post_cbox.isChecked(),
        )
        try:
            collection = worker_api_client.get_collection(data_query_definition.collection_id)
        except EdrApiClientError as e:
            self.plugin.communication.show_error(f"Fetching collection failed due to the following error:\n{e}")
            return
        try:
            instances = worker_api_client.get_collection_instances(data_query_definition.collection_id)
        except EdrApiClientError:
            instances = []
        repeat_dialog = RepeatQueryDialog(data_query_definition, collection, instances, parent=self)
        if repeat_dialog.instance_grp.isEnabled() or repeat_dialog.temporal_grp.isEnabled():
            repeat_dialog.exec_()
        worker_api_client = EdrApiClient(
            server_url,
            authentication_config_id=edr_authcfg,
            use_post_request=self.post_cbox.isChecked(),
        )
        download_worker = EdrDataDownloader(worker_api_client, data_query_definition, download_dir)
        download_worker.signals.download_progress.connect(self.on_progress_signal)
        download_worker.signals.download_success.connect(self.on_success_signal)
        download_worker.signals.download_failure.connect(self.on_failure_signal)
        self.plugin.downloader_pool.start(download_worker)

    def on_progress_signal(self, message, current_progress, total_progress, download_filepath):
        """Feedback on getting data progress signal."""
        self.plugin.communication.progress_bar(message, 0, total_progress, current_progress, clear_msg_bar=True)

    def on_success_signal(self, message, download_filepath):
        """Feedback on getting data success signal."""
        self.plugin.communication.clear_message_bar()
        self.plugin.communication.bar_info(message)
        self.plugin.layer_manager.add_layer_from_file(download_filepath)

    def on_failure_signal(self, error_message, download_filepath):
        """Feedback on getting data failure signal."""
        self.plugin.communication.clear_message_bar()
        self.plugin.communication.bar_error(error_message)


class RepeatQueryDialog(QDialog):
    """Repeat saved query dialog."""

    def __init__(self, data_query_definition, collection, instances=None, parent=None):
        QDialog.__init__(self, parent)
        ui_filepath = os.path.join(os.path.dirname(os.path.realpath(__file__)), "ui", "repeat_query.ui")
        self.ui = uic.loadUi(ui_filepath, self)
        self.data_query_definition = data_query_definition
        self.collection = collection
        self.instances = instances or []
        self.populate_instances()
        self.populate_time_range()
        self.instance_cbo.currentIndexChanged.connect(self.populate_time_range)
        self.accept_pb.clicked.connect(self.accept)
        self.skip_pb.clicked.connect(self.reject)

    def populate_instances(self):
        """Populate instances if available."""
        if self.instances:
            for instance in self.instances:
                self.instance_cbo.addItem(instance["id"], instance)
        else:
            self.instance_grp.setDisabled(True)

    def populate_time_range(self):
        """Populate temporal extent if available."""
        collection = self.instance_cbo.currentData() if self.instances else self.collection
        collection_extent = collection["extent"]
        try:
            self.temporal_grp.setEnabled(True)
            temporal_extent = collection_extent["temporal"]
            temporal_interval = temporal_extent["interval"]
            from_datetime_str, to_datetime_str = temporal_interval[0]
            from_datetime = QDateTime.fromString(from_datetime_str, Qt.ISODate)
            to_datetime = QDateTime.fromString(to_datetime_str, Qt.ISODate)
            self.from_datetime.setTimeSpec(Qt.UTC)
            self.to_datetime.setTimeSpec(Qt.UTC)
            self.from_datetime.setDateTime(from_datetime)
            self.to_datetime.setDateTime(to_datetime)
        except KeyError:
            self.temporal_grp.setDisabled(True)

    def collect_variables(self):
        """Collect variables from the dialog."""
        instance_id = self.instance_cbo.currentText() if self.instance_grp.isEnabled() else None
        if self.temporal_grp.isEnabled():
            from_datetime = self.from_datetime.dateTime().toTimeSpec(Qt.UTC).toString(Qt.ISODate)
            to_datetime = self.to_datetime.dateTime().toTimeSpec(Qt.UTC).toString(Qt.ISODate)
            temporal_range = (
                (from_datetime,)
                if not to_datetime
                else (
                    from_datetime,
                    to_datetime,
                )
            )
        else:
            temporal_range = None
        return instance_id, temporal_range

    def accept(self):
        """Modify data query definition if changes accepted."""
        instance_id, temporal_range = self.collect_variables()
        self.data_query_definition.instance_id = instance_id
        self.data_query_definition.temporal_range = temporal_range
        super().accept()
