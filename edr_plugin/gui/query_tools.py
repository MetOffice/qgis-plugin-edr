import os

from qgis.core import QgsCoordinateReferenceSystem, QgsGeometry, QgsProject
from qgis.gui import QgsMapToolEmitPoint
from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import QDialog

from edr_plugin.queries import AreaQueryDefinition, PositionQueryDefinition, RadiusQueryDefinition
from edr_plugin.utils import reproject_geometry


class AreaQueryBuilderTool(QDialog):
    """Dialog for defining area data query."""

    def __init__(self, edr_dialog):
        QDialog.__init__(self, parent=edr_dialog)
        ui_filepath = os.path.join(os.path.dirname(os.path.realpath(__file__)), "ui", "query_area.ui")
        self.ui = uic.loadUi(ui_filepath, self)
        self.edr_dialog = edr_dialog
        self.map_canvas = self.edr_dialog.plugin.iface.mapCanvas()
        self.extent_grp.setMapCanvas(self.map_canvas)
        crs_name, crs_wkt = self.edr_dialog.crs_cbo.currentText(), self.edr_dialog.crs_cbo.currentData()
        if crs_wkt:
            self.output_crs = QgsCoordinateReferenceSystem.fromWkt(crs_wkt)
        else:
            self.output_crs = QgsCoordinateReferenceSystem.fromOgcWmsCrs(crs_name)
        self.extent_grp.setOutputCrs(self.output_crs)
        self.ok_pb.clicked.connect(self.accept)
        self.extent_grp.setOutputExtentFromCurrent()
        self.edr_dialog.hide()
        self.show()

    def accept(self):
        current_extent = self.extent_grp.outputExtent()
        wkt_extent = current_extent.asWktPolygon()
        self.edr_dialog.query_extent_le.setText(wkt_extent)
        self.edr_dialog.query_extent_le.setCursorPosition(0)
        self.edr_dialog.show()
        super().accept()

    def reject(self):
        self.edr_dialog.show()
        super().accept()

    def get_query_definition(self):
        """Return query definition object based on user input."""
        current_extent = self.extent_grp.outputExtent()
        wkt_extent_polygon = current_extent.asWktPolygon()
        query_parameters = self.edr_dialog.collect_query_parameters()
        query_definition = AreaQueryDefinition(*query_parameters, wkt_polygon=wkt_extent_polygon)
        return query_definition


class PositionQueryBuilderTool(QgsMapToolEmitPoint):
    """Tool for defining position data query."""

    def __init__(self, edr_dialog):
        self.map_canvas = edr_dialog.plugin.iface.mapCanvas()
        super().__init__(canvas=self.map_canvas)
        self.edr_dialog = edr_dialog
        crs_name, crs_wkt = self.edr_dialog.crs_cbo.currentText(), self.edr_dialog.crs_cbo.currentData()
        if crs_wkt:
            self.output_crs = QgsCoordinateReferenceSystem.fromWkt(crs_wkt)
        else:
            self.output_crs = QgsCoordinateReferenceSystem.fromOgcWmsCrs(crs_name)
        self.last_position_geometry = None
        self.map_canvas.setMapTool(self)
        self.edr_dialog.hide()

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
        query_parameters = self.edr_dialog.collect_query_parameters()
        query_definition = PositionQueryDefinition(*query_parameters, wkt_point=wkt_position_point)
        return query_definition


class RadiusQueryBuilderTool(QDialog):
    """Dialog for defining radius data query."""

    def __init__(self, edr_dialog):
        QDialog.__init__(self, parent=edr_dialog)
        ui_filepath = os.path.join(os.path.dirname(os.path.realpath(__file__)), "ui", "query_radius.ui")
        self.ui = uic.loadUi(ui_filepath, self)
        self.edr_dialog = edr_dialog
        self.map_canvas = self.edr_dialog.plugin.iface.mapCanvas()
        crs_name, crs_wkt = self.edr_dialog.crs_cbo.currentText(), self.edr_dialog.crs_cbo.currentData()
        if crs_wkt:
            self.output_crs = QgsCoordinateReferenceSystem.fromWkt(crs_wkt)
        else:
            self.output_crs = QgsCoordinateReferenceSystem.fromOgcWmsCrs(crs_name)
        radius_query_data = self.edr_dialog.query_cbo.currentData()
        self.radius_units_cbo.addItems(radius_query_data["link"]["variables"]["within_units"])
        self.ok_pb.clicked.connect(self.accept)
        self.radius_center_tool = QgsMapToolEmitPoint(self.map_canvas)
        self.radius_center_tool.canvasClicked.connect(self.on_canvas_clicked)
        self.radius_center_point_pb.clicked.connect(self.on_radius_center_point_button_clicked)
        self.last_radius_center_geometry = None
        self.edr_dialog.hide()
        self.show()

    def accept(self):
        self.edr_dialog.query_extent_le.setText(self.last_radius_center_geometry.asWkt())
        self.edr_dialog.query_extent_le.setCursorPosition(0)
        self.edr_dialog.show()
        super().accept()

    def reject(self):
        self.edr_dialog.show()
        super().accept()

    def on_radius_center_point_button_clicked(self):
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
        wkt_radius_center = self.last_radius_center_geometry.asWkt()
        query_parameters = self.edr_dialog.collect_query_parameters()
        radius_value = self.radius_spinbox.value()
        radius = f"{radius_value:.3f}"
        units = self.radius_units_cbo.currentText()
        query_definition = RadiusQueryDefinition(
            *query_parameters, wkt_point=wkt_radius_center, radius=radius, units=units
        )
        return query_definition
