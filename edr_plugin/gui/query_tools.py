import os

from qgis._core import QgsCoordinateReferenceSystem
from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import QDialog

from edr_plugin.queries import AreaQueryDefinition


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
        self.extent_grp.extentChanged.connect(self.on_extent_changed)
        self.ok_pb.clicked.connect(self.accept)
        self.extent_grp.setOutputExtentFromCurrent()

    def on_extent_changed(self, rectangle):
        """Action on extent changed signal."""
        wkt_extent = rectangle.asWktPolygon()
        self.edr_dialog.query_extent_le.setText(wkt_extent)
        self.edr_dialog.query_extent_le.setCursorPosition(0)

    def get_query_definition(self):
        """Return query definition object based on user input."""
        current_extent = self.extent_grp.outputExtent()
        wkt_extent_polygon = current_extent.asWktPolygon()
        query_parameters = self.edr_dialog.collect_query_parameters()
        query_definition = AreaQueryDefinition(*query_parameters, wkt_polygon=wkt_extent_polygon)
        return query_definition
