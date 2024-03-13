import os
import typing
from abc import abstractmethod

from pytest_qgis import QWidget
from qgis.core import (
    Qgis,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsGeometry,
    QgsPoint,
    QgsProject,
    QgsSettings,
    QgsVectorLayer,
)
from qgis.gui import (
    QgsDateTimeEdit,
    QgsDoubleValidator,
    QgsMapMouseEvent,
    QgsMapToolEmitPoint,
    QgsMapToolIdentifyFeature,
    QgsRubberBand,
)
from qgis.PyQt import uic
from qgis.PyQt.QtCore import QDateTime, Qt, pyqtSignal
from qgis.PyQt.QtGui import QColor
from qgis.PyQt.QtWidgets import QComboBox, QDialog, QDoubleSpinBox, QHeaderView, QLineEdit, QTableWidget

from edr_plugin.api_client import EdrApiClientError
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
from edr_plugin.utils import EdrSettingsPath, reproject_geometry, string_to_bool


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


class CubeQueryBuilderTool(QDialog):
    """Dialog for defining cube data query."""

    def __init__(self, edr_dialog):
        QDialog.__init__(self, parent=edr_dialog)
        ui_filepath = os.path.join(os.path.dirname(os.path.realpath(__file__)), "ui", "query_cube.ui")
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
        bbox = f"{current_extent.xMinimum()},{current_extent.yMinimum()},{current_extent.xMaximum()},{current_extent.yMaximum()}"
        self.edr_dialog.current_data_query_tool = self
        self.edr_dialog.query_extent_le.setText(bbox)
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
        bbox = f"{current_extent.xMinimum()},{current_extent.yMinimum()},{current_extent.xMaximum()},{current_extent.yMaximum()}"
        collection_id, sub_endpoints, query_parameters = self.edr_dialog.collect_query_parameters()
        query_definition = CubeQueryDefinition(collection_id, bbox, **sub_endpoints, **query_parameters)
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
        self.edr_dialog.current_data_query_tool = self

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
        if self.last_radius_center_geometry is None:
            warn_msg = "Radius centre point is not set. Please select it and try again."
            self.edr_dialog.plugin.communication.show_warn(warn_msg)
            return
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


class LineStringQueryBuilderTool(QDialog):
    """Dialog for defining line string data query - base of Trajectory and Corridor."""

    linestring_tw: QTableWidget

    def reject(self) -> None:
        self.edr_dialog.show()
        super().accept()

    def accept(self) -> None:
        """Accept line."""
        if self.selected_geometry is None:
            warn_msg = "Line geometry is not set. Please select it and try again."
            self.edr_dialog.plugin.communication.show_warn(warn_msg)
            return
        self.edr_dialog.current_data_query_tool = self
        geom = self.query_geometry()
        self.edr_dialog.query_extent_le.setText(geom.asWkt())
        self.edr_dialog.query_extent_le.setCursorPosition(0)
        self.disable_main_edr_widgets_based_geometry_type()
        self.edr_dialog.show()
        return super().accept()

    def on_line_select_button_clicked(self):
        """Activate line select tool."""
        self.map_canvas.setMapTool(self.line_select_tool)
        self.hide()

    def on_feature_selected(self, geom: QgsGeometry):
        """Select feature and read its vertices."""
        self.selected_geometry = geom
        source_crs = QgsProject.instance().crs()
        reproject_geometry(self.selected_geometry, source_crs, self.output_crs)
        self.line_select_pb.setText("Linestring : <SELECTED>")
        self._fill_table()
        self.map_canvas.unsetMapTool(self.line_select_tool)
        self.show()

    def _table_item_float(self, value: typing.Optional[float]) -> QLineEdit:
        """Table item for float value."""
        item = QLineEdit()
        item.setValidator(QgsDoubleValidator(item))
        if value is not None:
            item.setText(str(value))
        return item

    def _table_item_datetime(self, value: typing.Optional[int]) -> QgsDateTimeEdit:
        """Table item for datetime value."""
        item = QgsDateTimeEdit()
        if value is not None:
            date_time = QDateTime.fromMSecsSinceEpoch(value)
            item.setDateTime(date_time)
        else:
            item.clear()
        return item

    def _setup_table(self):
        self.linestring_tw.setColumnCount(4)
        self.linestring_tw.setHorizontalHeaderLabels(["x", "y", "z", "Time"])
        header = self.linestring_tw.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)

    def _fill_table(self) -> None:
        """Fill table with vertices from selected geometry."""
        self.linestring_tw.clear()
        self._setup_table()
        if self.selected_geometry:
            for i, vertex in enumerate(self.selected_geometry.vertices()):
                self.linestring_tw.insertRow(i)

                self.linestring_tw.setCellWidget(i, 0, self._table_item_float(vertex.x()))
                self.linestring_tw.setCellWidget(i, 1, self._table_item_float(vertex.y()))

                z_value = None
                if vertex.is3D():
                    z_value = vertex.z()
                self.linestring_tw.setCellWidget(i, 2, self._table_item_float(z_value))

                m_value = None
                if vertex.isMeasure():
                    m_value = int(vertex.m())
                self.linestring_tw.setCellWidget(i, 3, self._table_item_datetime(m_value))

    def _cell_to_float(self, row: int, col: int) -> typing.Optional[float]:
        """Convert cell value from TableWidget to float."""
        text = self.linestring_tw.cellWidget(row, col).text()
        if len(text) == 0:
            value = None
        else:
            value = QgsDoubleValidator.toDouble(text)
        return value

    def _cell_to_datetime_milisecs(self, row: int, col: int) -> typing.Optional[int]:
        """Convert cell value from TableWidget to datetime in miliseconds."""
        date_time = self.linestring_tw.cellWidget(row, col).dateTime()
        if date_time.isNull():
            milisecs = None
        else:
            milisecs = date_time.toMSecsSinceEpoch()
        return milisecs

    def query_geometry(self) -> QgsGeometry:
        """Set geometry to query extent."""
        points: typing.List[QgsPoint] = []

        for i in range(self.linestring_tw.rowCount()):
            point = QgsPoint(self._cell_to_float(i, 0), self._cell_to_float(i, 1))
            z = self._cell_to_float(i, 2)
            if z:
                point.addZValue(z)
            m = self._cell_to_datetime_milisecs(i, 3)
            if m:
                point.addMValue(m)
            points.append(point)

        geom = QgsGeometry.fromPolyline(points)
        return geom

    def disable_main_edr_widgets_based_geometry_type(self) -> None:
        geom = self.selected_geometry.constGet()
        self.edr_dialog.vertical_grp.setEnabled(not geom.is3D())
        self.edr_dialog.temporal_grp.setEnabled(not geom.isMeasure())

    @abstractmethod
    def get_query_definition(self): ...

    @abstractmethod
    def setup_data_query_tool(self): ...


class CorridorQueryBuilderTool(LineStringQueryBuilderTool):
    """Dialog for defining corridor data query."""

    height_spinbox: QDoubleSpinBox
    width_spinbox: QDoubleSpinBox
    width_units_cbo: QComboBox
    height_units_cbo: QComboBox

    def __init__(self, edr_dialog) -> None:
        super().__init__(parent=edr_dialog)
        ui_filepath = os.path.join(os.path.dirname(os.path.realpath(__file__)), "ui", "query_corridor.ui")
        self.ui = uic.loadUi(ui_filepath, self)
        self.edr_dialog = edr_dialog
        self.map_canvas = self.edr_dialog.plugin.iface.mapCanvas()
        self.output_crs = None
        self.setup_data_query_tool()
        self.selected_geometry: typing.Optional[QgsGeometry] = None
        self.line_select_tool = LineSelectMapTool(self.edr_dialog)
        self.line_select_tool.featureSelected.connect(self.on_feature_selected)
        self.line_select_pb.clicked.connect(self.on_line_select_button_clicked)
        self.ok_pb.clicked.connect(self.accept)
        self._setup_table()
        self.edr_dialog.hide()
        self.show()

    def setup_data_query_tool(self):
        """Initial data query tool setup."""
        crs_name, crs_wkt = self.edr_dialog.crs_cbo.currentText(), self.edr_dialog.crs_cbo.currentData()
        if crs_wkt:
            self.output_crs = QgsCoordinateReferenceSystem.fromWkt(crs_wkt)
        else:
            self.output_crs = QgsCoordinateReferenceSystem.fromOgcWmsCrs(crs_name)
        corridor_query_data = self.edr_dialog.query_cbo.currentData()
        width_units = corridor_query_data["link"]["variables"]["width_units"]
        self.width_units_cbo.addItems(width_units)
        height_units = corridor_query_data["link"]["variables"]["height_units"]
        self.height_units_cbo.addItems(height_units)

    def get_query_definition(self):
        collection_id, sub_endpoints, query_parameters = self.edr_dialog.collect_query_parameters()
        wkt_corridor = self.edr_dialog.query_extent_le.text()
        query_definition = CorridorQueryDefinition(
            collection_id,
            wkt_corridor,
            str(self.width_spinbox.value()),
            self.width_units_cbo.currentText(),
            str(self.height_spinbox.value()),
            self.height_units_cbo.currentText(),
            **sub_endpoints,
            **query_parameters,
        )
        return query_definition


class TrajectoryQueryBuilderTool(LineStringQueryBuilderTool):
    """Dialog for defining trajectory data query."""

    def __init__(self, edr_dialog):
        super().__init__(parent=edr_dialog)
        ui_filepath = os.path.join(os.path.dirname(os.path.realpath(__file__)), "ui", "query_trajectory.ui")
        self.ui = uic.loadUi(ui_filepath, self)
        self.edr_dialog = edr_dialog
        self.map_canvas = self.edr_dialog.plugin.iface.mapCanvas()
        self.output_crs = None
        self.setup_data_query_tool()
        self.selected_geometry: typing.Optional[QgsGeometry] = None
        self.line_select_tool = LineSelectMapTool(self.edr_dialog)
        self.line_select_tool.featureSelected.connect(self.on_feature_selected)
        self.line_select_pb.clicked.connect(self.on_line_select_button_clicked)
        self.ok_pb.clicked.connect(self.accept)
        self._setup_table()
        self.edr_dialog.hide()
        self.show()

    def setup_data_query_tool(self):
        """Initial data query tool setup."""
        crs_name, crs_wkt = self.edr_dialog.crs_cbo.currentText(), self.edr_dialog.crs_cbo.currentData()
        if crs_wkt:
            self.output_crs = QgsCoordinateReferenceSystem.fromWkt(crs_wkt)
        else:
            self.output_crs = QgsCoordinateReferenceSystem.fromOgcWmsCrs(crs_name)

    def get_query_definition(self):
        """Return query definition object based on user input."""
        collection_id, sub_endpoints, query_parameters = self.edr_dialog.collect_query_parameters()
        wkt_trajectory = self.edr_dialog.query_extent_le.text()
        query_definition = TrajectoryQueryDefinition(
            collection_id,
            wkt_trajectory,
            **sub_endpoints,
            **query_parameters,
        )
        return query_definition


class LineSelectMapTool(QgsMapToolIdentifyFeature):
    """Tool to select Line from Map Canvas."""

    featureSelected = pyqtSignal(QgsGeometry)

    def __init__(self, edr_dialog) -> None:
        self.edr_dialog = edr_dialog
        self.iface = self.edr_dialog.plugin.iface
        self.map_canvas = self.iface.mapCanvas()
        self.active_layer = self.iface.activeLayer()

        # Rubber band for highlighting selected feature
        self.rubber_band = QgsRubberBand(self.map_canvas, Qgis.GeometryType.Line)
        self.rubber_band.setColor(QColor.fromRgb(255, 255, 0))
        self.rubber_band.setWidth(2)
        self.rubber_band.setOpacity(1)

        # feature and layer for identify
        self.identify_feature = None
        self.identify_layer = None

        QgsMapToolIdentifyFeature.__init__(self, self.map_canvas, self.active_layer)
        self.iface.currentLayerChanged.connect(self.active_changed)

    def active_changed(self, layer):
        """Change active layer."""
        try:
            if self.active_layer:
                self.active_layer.removeSelection()
            if isinstance(layer, QgsVectorLayer) and layer.isSpatial():
                self.active_layer = layer
                self.setLayer(self.active_layer)
        except Exception:
            pass

    @property
    def _line_layers(self):
        """Select layers that have Line GeometryType."""
        map_layers = QgsProject.instance().mapLayers()

        selected_layers = [
            x
            for x in map_layers.values()
            if isinstance(x, QgsVectorLayer) and x.geometryType() == Qgis.GeometryType.Line
        ]

        return selected_layers

    def _find_feature(self, x: float, y: float) -> None:
        """Set identify feature and layer for given coordinates."""
        self.identify_feature = None
        self.identify_layer = None

        features = self.identify(x, y, self._line_layers, QgsMapToolIdentifyFeature.TopDownAll)
        if features:
            self.identify_feature = features[0].mFeature
            self.identify_layer = features[0].mLayer
        return None

    def canvasPressEvent(self, event):
        self._find_feature(event.x(), event.y())
        if self.identify_feature:
            # returned geometry is always in project CRS for simplicity
            transform = QgsCoordinateTransform(
                self.identify_layer.crs(), self.map_canvas.mapSettings().destinationCrs(), QgsProject.instance()
            )
            geom = QgsGeometry(self.identify_feature.geometry())
            result = geom.transform(transform)
            if result == Qgis.GeometryOperationResult.Success:
                self.featureSelected.emit(geom)
        self.rubber_band.reset()
        self.map_canvas.unsetMapTool(self)
        self.edr_dialog.show()

    def canvasMoveEvent(self, e: QgsMapMouseEvent) -> None:
        self._find_feature(e.x(), e.y())
        # highlight feature
        if self.identify_feature:
            self.rubber_band.addGeometry(QgsGeometry(self.identify_feature.geometry()))
        else:
            self.rubber_band.reset()


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
