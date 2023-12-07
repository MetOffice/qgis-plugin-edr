import os

from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import QDialog

from edr_plugin.queries import AreaQueryDefinition


class AreaQueryBuilderTool(QDialog):
    def __init__(self, edr_dialog):
        QDialog.__init__(self, parent=edr_dialog)
        ui_filepath = os.path.join(os.path.dirname(os.path.realpath(__file__)), "ui", "query_area.ui")
        self.ui = uic.loadUi(ui_filepath, self)
        self.edr_dialog = edr_dialog
        self.map_canvas = self.edr_dialog.plugin.iface.mapCanvas()
        self.extent_grp.setMapCanvas(self.map_canvas)
        self.cancel_pb.clicked.connect(self.reject)
        self.accept_pb.clicked.connect(self.accept)

    def get_query_definition(self):
        current_extent = self.extent_grp.outputExtent()
        wkt_extent_polygon = current_extent.asWktPolygon()
        query_parameters = self.edr_dialog.collect_query_parameters()
        query_definition = AreaQueryDefinition(*query_parameters, wkt_polygon=wkt_extent_polygon)
        return query_definition
