import os

from qgis.core import QgsCoordinateReferenceSystem, QgsGeometry, QgsProject, QgsSettings
from qgis.gui import QgsMapToolEmitPoint
from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import QDialog

from edr_plugin.api_client import EdrApiClientError
from edr_plugin.queries import (
    AreaQueryDefinition,
    ItemsQueryDefinition,
    LocationsQueryDefinition,
    PositionQueryDefinition,
    RadiusQueryDefinition,
)
from edr_plugin.utils import EdrSettingsPath, reproject_geometry


class AreaQueryBuilderTool(QDialog):
    """Dialog for defining area data query."""

    def __init__(self, edr_dialog):
        QDialog.__init__(self, parent=edr_dialog)
        ui_filepath = os.path.join(os.path.dirname(os.path.realpath(__file__)), "ui", "query_area.ui")
        self.ui = uic.loadUi(ui_filepath, self)
        self.edr_dialog = edr_dialog
        self.map_canvas = self.edr_dialog.plugin.iface.mapCanvas()
        self.output_crs = None
        self.ok_pb.clicked.connect(self.accept)
        self.setup_data_query_tool()
        self.edr_dialog.hide()
        self.show()

    def accept(self):
        current_extent = self.extent_grp.outputExtent()
        wkt_extent = current_extent.asWktPolygon()
        self.edr_dialog.current_data_query_tool = self
        self.edr_dialog.query_extent_le.setText(wkt_extent)
        self.edr_dialog.query_extent_le.setCursorPosition(0)
        self.edr_dialog.show()
        super().accept()

    def reject(self):
        self.edr_dialog.show()
        super().accept()

    def setup_data_query_tool(self):
        """Initial data query tool setup."""
        self.extent_grp.setMapCanvas(self.map_canvas)
        crs_name, crs_wkt = self.edr_dialog.crs_cbo.currentText(), self.edr_dialog.crs_cbo.currentData()
        if crs_wkt:
            self.output_crs = QgsCoordinateReferenceSystem.fromWkt(crs_wkt)
        else:
            self.output_crs = QgsCoordinateReferenceSystem.fromOgcWmsCrs(crs_name)
        self.extent_grp.setOutputCrs(self.output_crs)
        self.extent_grp.setOutputExtentFromCurrent()

    def get_query_definition(self):
        """Return query definition object based on user input."""
        current_extent = self.extent_grp.outputExtent()
        wkt_extent_polygon = current_extent.asWktPolygon()
        collection_id, sub_endpoints, query_parameters = self.edr_dialog.collect_query_parameters()
        query_definition = AreaQueryDefinition(collection_id, wkt_extent_polygon, **sub_endpoints, **query_parameters)
        return query_definition


class PositionQueryBuilderTool(QgsMapToolEmitPoint):
    """Tool for defining position data query."""

    def __init__(self, edr_dialog):
        self.map_canvas = edr_dialog.plugin.iface.mapCanvas()
        super().__init__(canvas=self.map_canvas)
        self.edr_dialog = edr_dialog
        self.output_crs = None
        self.last_position_geometry = None
        self.setup_data_query_tool()
        self.edr_dialog.hide()

    def setup_data_query_tool(self):
        """Initial data query tool setup."""
        crs_name, crs_wkt = self.edr_dialog.crs_cbo.currentText(), self.edr_dialog.crs_cbo.currentData()
        if crs_wkt:
            self.output_crs = QgsCoordinateReferenceSystem.fromWkt(crs_wkt)
        else:
            self.output_crs = QgsCoordinateReferenceSystem.fromOgcWmsCrs(crs_name)
        self.map_canvas.setMapTool(self)

    def canvasPressEvent(self, e):
        """On canvas press event."""
        point = self.toMapCoordinates(e.pos())
        point_geometry = QgsGeometry.fromPointXY(point)
        source_crs = QgsProject.instance().crs()
        reproject_geometry(point_geometry, source_crs, self.output_crs)
        self.last_position_geometry = point_geometry
        self.edr_dialog.query_extent_le.setText(self.last_position_geometry.asWkt())
        self.edr_dialog.query_extent_le.setCursorPosition(0)
        self.map_canvas.unsetMapTool(self)
        self.edr_dialog.show()

    def get_query_definition(self):
        """Return query definition object based on user input."""
        wkt_position_point = self.last_position_geometry.asWkt()
        collection_id, sub_endpoints, query_parameters = self.edr_dialog.collect_query_parameters()
        query_definition = PositionQueryDefinition(
            collection_id, wkt_position_point, **sub_endpoints, **query_parameters
        )
        return query_definition


class RadiusQueryBuilderTool(QDialog):
    """Dialog for defining radius data query."""

    def __init__(self, edr_dialog):
        QDialog.__init__(self, parent=edr_dialog)
        ui_filepath = os.path.join(os.path.dirname(os.path.realpath(__file__)), "ui", "query_radius.ui")
        self.ui = uic.loadUi(ui_filepath, self)
        self.edr_dialog = edr_dialog
        self.map_canvas = self.edr_dialog.plugin.iface.mapCanvas()
        self.output_crs = None
        self.ok_pb.clicked.connect(self.accept)
        self.radius_center_tool = QgsMapToolEmitPoint(self.map_canvas)
        self.radius_center_tool.canvasClicked.connect(self.on_canvas_clicked)
        self.radius_center_point_pb.clicked.connect(self.on_radius_center_point_button_clicked)
        self.last_radius_center_geometry = None
        self.setup_data_query_tool()
        self.edr_dialog.hide()
        self.show()

    def accept(self):
        settings = QgsSettings()
        settings.setValue(EdrSettingsPath.LAST_RADIUS.value, str(self.radius_spinbox.value()))
        settings.setValue(EdrSettingsPath.LAST_RADIUS_UNITS.value, self.radius_units_cbo.currentText())
        self.edr_dialog.current_data_query_tool = self
        self.edr_dialog.query_extent_le.setText(self.last_radius_center_geometry.asWkt())
        self.edr_dialog.query_extent_le.setCursorPosition(0)
        self.edr_dialog.show()
        super().accept()

    def reject(self):
        self.edr_dialog.show()
        super().accept()

    def setup_data_query_tool(self):
        """Initial data query tool setup."""
        crs_name, crs_wkt = self.edr_dialog.crs_cbo.currentText(), self.edr_dialog.crs_cbo.currentData()
        if crs_wkt:
            self.output_crs = QgsCoordinateReferenceSystem.fromWkt(crs_wkt)
        else:
            self.output_crs = QgsCoordinateReferenceSystem.fromOgcWmsCrs(crs_name)
        radius_query_data = self.edr_dialog.query_cbo.currentData()
        within_units = radius_query_data["link"]["variables"]["within_units"]
        self.radius_units_cbo.addItems(within_units)
        settings = QgsSettings()
        last_radius = settings.value(EdrSettingsPath.LAST_RADIUS.value, 10.0, type=float)
        last_radius_units = settings.value(EdrSettingsPath.LAST_RADIUS_UNITS.value, "")
        self.radius_spinbox.setValue(last_radius)
        self.radius_units_cbo.setCurrentText(last_radius_units)

    def on_radius_center_point_button_clicked(self):
        """On radius center point button clicked."""
        self.map_canvas.setMapTool(self.radius_center_tool)
        self.hide()

    def on_canvas_clicked(self, point):
        """On canvas clicked event."""
        point_geometry = QgsGeometry.fromPointXY(point)
        source_crs = QgsProject.instance().crs()
        reproject_geometry(point_geometry, source_crs, self.output_crs)
        self.last_radius_center_geometry = point_geometry
        button_label = f"Radius center point: {self.last_radius_center_geometry.asWkt(precision=5)}"
        self.radius_center_point_pb.setText(button_label)
        self.map_canvas.unsetMapTool(self.radius_center_tool)
        self.show()

    def get_query_definition(self):
        """Return query definition object based on user input."""
        collection_id, sub_endpoints, query_parameters = self.edr_dialog.collect_query_parameters()
        wkt_radius_center = self.last_radius_center_geometry.asWkt()
        radius_value = self.radius_spinbox.value()
        radius = f"{radius_value:.3f}"
        units = self.radius_units_cbo.currentText()
        query_definition = RadiusQueryDefinition(
            collection_id,
            wkt_radius_center,
            radius,
            units,
            **sub_endpoints,
            **query_parameters,
        )
        return query_definition


class ItemsQueryBuilderTool(QDialog):
    """Dialog for defining items data query."""

    def __init__(self, edr_dialog):
        QDialog.__init__(self, parent=edr_dialog)
        ui_filepath = os.path.join(os.path.dirname(os.path.realpath(__file__)), "ui", "query_items.ui")
        self.ui = uic.loadUi(ui_filepath, self)
        self.edr_dialog = edr_dialog
        self.ok_pb.clicked.connect(self.accept)
        self.setup_data_query_tool()
        self.edr_dialog.hide()
        self.show()

    def accept(self):
        selected_item = self.items_cbo.currentText()
        QgsSettings().setValue(EdrSettingsPath.LAST_ITEM.value, selected_item)
        self.edr_dialog.current_data_query_tool = self
        self.edr_dialog.query_extent_le.setText(selected_item)
        self.edr_dialog.query_extent_le.setCursorPosition(0)
        self.edr_dialog.show()
        super().accept()

    def reject(self):
        self.edr_dialog.show()
        super().accept()

    def setup_data_query_tool(self):
        """Initial data query tool setup."""
        collection = self.edr_dialog.collection_cbo.currentData()
        collection_id = collection["id"]
        instance_id = self.edr_dialog.instance_cbo.currentText() if self.edr_dialog.instance_cbo.isEnabled() else None
        try:
            collection_items = self.edr_dialog.api_client.get_collection_items(collection_id, instance_id)
        except EdrApiClientError:
            collection_items = []
        for collection_item in collection_items:
            self.items_cbo.addItem(collection_item["id"], collection_item)
        last_item = QgsSettings().value(EdrSettingsPath.LAST_ITEM.value, "")
        self.items_cbo.setCurrentText(last_item)

    def get_query_definition(self):
        """Return query definition object based on user input."""
        collection_id, sub_endpoints, query_parameters = self.edr_dialog.collect_query_parameters()
        item_id = self.items_cbo.currentText()
        query_definition = ItemsQueryDefinition(collection_id, item_id, **sub_endpoints, **query_parameters)
        return query_definition


class LocationsQueryBuilderTool(QDialog):
    """Dialog for defining locations data query."""

    def __init__(self, edr_dialog):
        QDialog.__init__(self, parent=edr_dialog)
        ui_filepath = os.path.join(os.path.dirname(os.path.realpath(__file__)), "ui", "query_locations.ui")
        self.ui = uic.loadUi(ui_filepath, self)
        self.edr_dialog = edr_dialog
        self.ok_pb.clicked.connect(self.accept)
        self.setup_data_query_tool()
        self.edr_dialog.hide()
        self.show()

    def accept(self):
        selected_location = self.locations_cbo.currentText()
        QgsSettings().setValue(EdrSettingsPath.LAST_LOCATION.value, selected_location)
        self.edr_dialog.current_data_query_tool = self
        self.edr_dialog.query_extent_le.setText(selected_location)
        self.edr_dialog.query_extent_le.setCursorPosition(0)
        self.edr_dialog.show()
        super().accept()

    def reject(self):
        self.edr_dialog.show()
        super().accept()

    def setup_data_query_tool(self):
        """Initial data query tool setup."""
        collection = self.edr_dialog.collection_cbo.currentData()
        collection_id = collection["id"]
        instance_id = self.edr_dialog.instance_cbo.currentText() if self.edr_dialog.instance_cbo.isEnabled() else None
        try:
            collection_locations = self.edr_dialog.api_client.get_collection_locations(collection_id, instance_id)
        except EdrApiClientError:
            collection_locations = []
        for collection_location in collection_locations:
            self.locations_cbo.addItem(collection_location["id"], collection_location)
        last_location = QgsSettings().value(EdrSettingsPath.LAST_LOCATION.value, "")
        self.locations_cbo.setCurrentText(last_location)

    def get_query_definition(self):
        """Return query definition object based on user input."""
        collection_id, sub_endpoints, query_parameters = self.edr_dialog.collect_query_parameters()
        location_id = self.locations_cbo.currentText()
        query_definition = LocationsQueryDefinition(collection_id, location_id, **sub_endpoints, **query_parameters)
        return query_definition
