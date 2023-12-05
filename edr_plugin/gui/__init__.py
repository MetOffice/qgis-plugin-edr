import os

from qgis.core import QgsCoordinateReferenceSystem
from qgis.gui import QgsCollapsibleGroupBox, QgsProjectionSelectionWidget
from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import QCheckBox, QComboBox, QDialog, QDateTimeEdit
from qgis.PyQt.QtCore import QDateTime, Qt
from edr_plugin.api_client import EDRApiClient, EDRApiClientError


class EDRDialog(QDialog):
    def __init__(self, plugin, parent=None):
        QDialog.__init__(self, parent)
        ui_filepath = os.path.join(os.path.dirname(os.path.realpath(__file__)), "ui", "edr.ui")
        self.ui = uic.loadUi(ui_filepath, self)
        self.plugin = plugin
        self.api_client = EDRApiClient("https://labs.metoffice.gov.uk/edr")
        self.populate_collections()
        self.populate_collection_data()
        self.cancel_pb.clicked.connect(self.close)
        self.new_pb.clicked.connect(self.populate_collections)
        self.collection_cbo.currentIndexChanged.connect(self.populate_collection_data)
        self.instance_cbo.currentIndexChanged.connect(self.populate_data_queries)
        self.query_cbo.currentIndexChanged.connect(self.populate_data_query_attributes)

    @property
    def collection_level_widgets(self):
        widgets = [self.instance_cbo] + self.instance_level_widgets
        return widgets

    @property
    def instance_level_widgets(self):
        widgets = [self.query_cbo] + self.query_level_widgets
        return widgets

    @property
    def query_level_widgets(self):
        widgets = [
            self.crs_widget,
            self.format_cbo,
            self.parameters_cbo,
            self.temporal_grp,
            self.vertical_grp,
            self.from_datetime,
            self.to_datetime,
            self.intervals_cbo,
            self.use_range_cbox,
        ]
        return widgets

    @staticmethod
    def clear_widgets(*widgets):
        for widget in widgets:
            if isinstance(widget, QgsProjectionSelectionWidget):
                pass
            elif isinstance(widget, QgsCollapsibleGroupBox):
                widget.setDisabled(True)
            elif isinstance(widget, QCheckBox):
                widget.setChecked(False)
            elif isinstance(widget, (QComboBox, QDateTimeEdit)):
                widget.clear()
            else:
                pass

    def populate_collections(self):
        self.clear_widgets(self.collection_cbo, *self.collection_level_widgets)
        for collection in self.api_client.get_collections():
            collection_name = collection["title"]
            self.collection_cbo.addItem(collection_name, collection)

    def populate_collection_data(self):
        self.clear_widgets(*self.collection_level_widgets)
        collection = self.collection_cbo.currentData()
        if not collection:
            return
        if "instances" in collection["data_queries"]:
            self.instance_cbo.setEnabled(True)
            self.populate_instances()
        else:
            self.instance_cbo.setDisabled(True)
            self.populate_data_queries()

    def populate_instances(self):
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
        self.clear_widgets(*self.instance_level_widgets)
        if self.instance_cbo.isEnabled():
            collection = self.instance_cbo.currentData()
        else:
            collection = self.collection_cbo.currentData()
        if not collection:
            return
        data_queries = collection["data_queries"]
        for query_name, data_query in data_queries.items():
            self.query_cbo.addItem(query_name, data_query)
        self.populate_data_query_attributes()

    def populate_data_query_attributes(self):
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
        data_query_variables = data_query["link"]["variables"]
        crs_str = data_query_variables["crs_details"][0]["crs"]  # TODO: Handle multiple CRS
        crs = QgsCoordinateReferenceSystem.fromOgcWmsCrs(crs_str)
        output_formats = data_query_variables["output_formats"]
        default_output_format = data_query_variables["default_output_format"]
        self.crs_widget.setCrs(crs)
        self.format_cbo.addItems(output_formats)
        self.format_cbo.setCurrentText(default_output_format)
        parameter_names = collection["parameter_names"]
        for parameter, parameter_data in parameter_names.items():
            parameter_description = parameter_data["description"]
            self.parameters_cbo.addItem(parameter_description, parameter)
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
            self.intervals_cbo.selectAllOptions()
        except KeyError:
            self.vertical_grp.setDisabled(True)
