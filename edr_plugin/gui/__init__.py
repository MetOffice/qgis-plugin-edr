import os

from qgis.core import QgsCoordinateReferenceSystem
from qgis.gui import QgsCollapsibleGroupBox
from qgis.PyQt import uic
from qgis.PyQt.QtCore import QDateTime, QSettings, Qt
from qgis.PyQt.QtWidgets import QCheckBox, QComboBox, QDateTimeEdit, QDialog, QFileDialog, QInputDialog, QLineEdit

from edr_plugin.api_client import EdrApiClient, EdrApiClientError
from edr_plugin.gui.query_tools import AreaQueryBuilderTool
from edr_plugin.models.enumerators import EdrDataQuery
from edr_plugin.threading import EdrDataDownloader
from edr_plugin.utils import is_dir_writable


class EdrDialog(QDialog):
    """Main EDR plugin dialog."""

    DEFAULT_ROOT = "https://labs.metoffice.gov.uk/edr"

    def __init__(self, plugin, parent=None):
        QDialog.__init__(self, parent)
        ui_filepath = os.path.join(os.path.dirname(os.path.realpath(__file__)), "ui", "edr.ui")
        self.ui = uic.loadUi(ui_filepath, self)
        self.plugin = plugin
        settings = QSettings()
        server_url = settings.value("edr_plugin/server_url", self.DEFAULT_ROOT, type=str)
        self.server_url_le.setText(server_url)
        download_dir = settings.value("edr_plugin/download_dir", "", type=str)
        self.download_dir_le.setText(download_dir)
        self.api_client = EdrApiClient(server_url)
        self.current_data_query_tool = None
        self.populate_collections()
        self.populate_collection_data()
        self.change_server_pb.clicked.connect(self.set_edr_server_url)
        self.change_download_dir_pb.clicked.connect(self.set_download_directory)
        self.collection_cbo.currentIndexChanged.connect(self.populate_collection_data)
        self.instance_cbo.currentIndexChanged.connect(self.populate_data_queries)
        self.query_cbo.currentIndexChanged.connect(self.populate_data_query_attributes)
        self.query_set_pb.clicked.connect(self.set_query_extent)
        self.toggle_parameters_cbox.stateChanged.connect(self.toggle_parameters)
        self.toggle_intervals_cbox.stateChanged.connect(self.toggle_intervals)
        self.cancel_pb.clicked.connect(self.close)
        self.run_pb.clicked.connect(self.query_data_collection)

    def set_edr_server_url(self):
        """Set EDR server URL."""
        server_url, accept = QInputDialog.getText(self, "Set EDR Server URL", "Type EDR Server URL:")
        if accept is False:
            return
        server_url = server_url.strip("/")
        QSettings().setValue("edr_plugin/server_url", server_url)
        self.server_url_le.setText(server_url)
        self.api_client = EdrApiClient(server_url)
        self.populate_collections()
        self.populate_collection_data()

    def set_download_directory(self):
        """Set download directory."""
        settings = QSettings()
        last_download_dir = self.download_dir_le.text()
        parent_download_dir = os.path.dirname(last_download_dir) if last_download_dir else ""
        download_dir = QFileDialog.getExistingDirectory(self, "Pick download directory", parent_download_dir)
        if not download_dir:
            return
        if is_dir_writable(download_dir):
            settings.setValue("edr_plugin/download_dir", download_dir)
            self.download_dir_le.setText(download_dir)
        else:
            self.plugin.communication.bar_warn("Can't write to the selected location. Please pick another folder.")
            return

    def toggle_parameters(self, checked):
        """Check/uncheck all available parameters."""
        if checked:
            self.parameters_cbo.selectAllOptions()
        else:
            self.parameters_cbo.deselectAllOptions()

    def toggle_intervals(self, checked):
        """Check/uncheck all available intervals."""
        if checked:
            self.intervals_cbo.selectAllOptions()
        else:
            self.intervals_cbo.deselectAllOptions()

    @property
    def data_query_tools(self):
        """Return query builder tool associated with type of the query."""
        query_tools_map = {EdrDataQuery.AREA.value: AreaQueryBuilderTool}
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
            self.from_datetime,
            self.to_datetime,
            self.intervals_cbo,
            self.toggle_intervals_cbox,
            self.use_range_cbox,
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
        except EdrApiClientError as e:
            self.plugin.communication.show_error(f"Fetching collections failed due to the following error:\n{e}")

    def populate_collection_data(self):
        """Populate collection data."""
        self.clear_widgets(*self.collection_level_widgets)
        collection = self.collection_cbo.currentData()
        if not collection:
            return
        try:
            data_queries = collection["data_queries"]
        except KeyError:
            return
        if "instances" in data_queries:
            self.instance_cbo.setEnabled(True)
            self.populate_instances()
        else:
            self.instance_cbo.setDisabled(True)
            self.populate_data_queries()

    def populate_instances(self):
        """Populate instances."""
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

    def populate_data_queries(self):
        """Populate collection data queries."""
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
            self.query_cbo.addItem(query_name, data_query)
        self.populate_data_query_attributes()

    def populate_data_query_attributes(self):
        """Populate data query attributes."""
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
            observed_property = parameter_data["observedProperty"]
            observed_property_label = observed_property["label"]
            parameter_description = parameter_data.get("description", observed_property_label)
            self.parameters_cbo.addItem(parameter_description, parameter)
        self.parameters_cbo.toggleItemCheckState(0)
        collection_extent = collection["extent"]
        try:
            self.temporal_grp.setEnabled(True)
            temporal_extent = collection_extent["temporal"]
            interval = temporal_extent["interval"]
            from_datetime_str, to_datetime_str = interval[0]
            from_datetime = QDateTime.fromString(from_datetime_str, Qt.ISODate)
            to_datetime = QDateTime.fromString(to_datetime_str, Qt.ISODate)
            self.from_datetime.setDateTime(from_datetime)
            self.to_datetime.setDateTime(to_datetime)
        except KeyError:
            self.temporal_grp.setDisabled(True)
        try:
            self.vertical_grp.setEnabled(True)
            vertical_extent = collection_extent["vertical"]
            values = vertical_extent["values"]
            self.intervals_cbo.addItems(values)
            self.intervals_cbo.toggleItemCheckState(0)
        except KeyError:
            self.vertical_grp.setDisabled(True)

    def collect_query_parameters(self):
        """Collect query parameters from the widgets."""
        collection = self.collection_cbo.currentData()
        collection_id = collection["id"]
        instance = self.instance_cbo.currentText() if self.instance_cbo.isEnabled() else None
        crs = self.crs_cbo.currentText()
        output_format = self.format_cbo.currentText()
        parameters = self.parameters_cbo.checkedItemsData()
        if self.temporal_grp.isEnabled():
            from_datetime = self.from_datetime.dateTime().toString(Qt.ISODate)
            to_datetime = self.to_datetime.dateTime().toString(Qt.ISODate)
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
        if self.vertical_grp.isEnabled():
            intervals = self.intervals_cbo.checkedItems()
            is_min_max_range = self.use_range_cbox.isChecked()
            vertical_extent = (intervals, is_min_max_range)
        else:
            vertical_extent = None
        return collection_id, instance, crs, output_format, parameters, temporal_range, vertical_extent

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
        self.current_data_query_tool = data_query_tool_cls(self)
        self.current_data_query_tool.show()

    def query_data_collection(self):
        """Define data query and get the data collection."""
        data_query = self.query_cbo.currentText()
        if not data_query:
            return
        if data_query not in self.data_query_tools:
            self.plugin.communication.show_warn(
                f"Missing implementation for '{data_query}' data queries. Action aborted."
            )
            return
        if self.current_data_query_tool is None:
            self.plugin.communication.show_warn("Query spatial extent is not set. Please set it and try again.")
            return
        data_query_definition = self.current_data_query_tool.get_query_definition()
        download_dir = self.download_dir_le.text()
        if not download_dir:
            self.plugin.communication.show_warn("There is no download folder specified. Please set it and try again.")
            return
        worker_api_client = EdrApiClient(self.server_url_le.text())
        download_worker = EdrDataDownloader(worker_api_client, data_query_definition, download_dir)
        download_worker.signals.download_progress.connect(self.on_progress_signal)
        download_worker.signals.download_success.connect(self.on_success_signal)
        download_worker.signals.download_failure.connect(self.on_failure_signal)
        self.plugin.downloader_pool.start(download_worker)
        self.close()

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
