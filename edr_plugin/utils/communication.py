# Copyright (C) 2023 by Lutra Consulting
from qgis.core import Qgis, QgsMessageLog
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QInputDialog, QMessageBox, QProgressBar, QPushButton


class UICommunication:
    """Class with methods for handling messages using QGIS interface."""

    def __init__(self, iface=None, context=None):
        self.iface = iface
        self.context = context
        self.message_bar = self.iface.messageBar() if iface is not None else None

    def show_info(self, msg, parent=None, context=None):
        """Showing info dialog."""
        if self.iface is not None:
            parent = parent if parent is not None else self.iface.mainWindow()
            context = self.context if context is None else context
            QMessageBox.information(parent, context, msg)
        else:
            print(msg)

    def show_warn(self, msg, parent=None, context=None):
        """Showing warning dialog."""
        if self.iface is not None:
            parent = parent if parent is not None else self.iface.mainWindow()
            context = self.context if context is None else context
            QMessageBox.warning(parent, context, msg)
        else:
            print(msg)

    def show_error(self, msg, parent=None, context=None):
        """Showing error dialog."""
        if self.iface is not None:
            parent = parent if parent is not None else self.iface.mainWindow()
            context = self.context if context is None else context
            QMessageBox.critical(parent, context, msg)
        else:
            print(msg)

    def bar_info(self, msg, dur=5):
        """Showing info message bar."""
        if self.iface is not None:
            self.message_bar.pushMessage(self.context, msg, level=Qgis.Info, duration=dur)
        else:
            print(msg)

    def bar_warn(self, msg, dur=5):
        """Showing warning message bar."""
        if self.iface is not None:
            self.message_bar.pushMessage(self.context, msg, level=Qgis.Warning, duration=dur)
        else:
            print(msg)

    def bar_error(self, msg, dur=5):
        """Showing error message bar."""
        if self.iface is not None:
            self.message_bar.pushMessage(self.context, msg, level=Qgis.Critical, duration=dur)
        else:
            print(msg)

    @staticmethod
    def ask(parent, title, question, box_icon=QMessageBox.Question):
        """Ask for operation confirmation."""
        msg_box = QMessageBox(parent)
        msg_box.setIcon(box_icon)
        msg_box.setWindowTitle(title)
        msg_box.setTextFormat(Qt.RichText)
        msg_box.setText(question)
        msg_box.setStandardButtons(QMessageBox.No | QMessageBox.Yes)
        msg_box.setDefaultButton(QMessageBox.No)
        res = msg_box.exec_()
        if res == QMessageBox.No:
            return False
        else:
            return True

    @staticmethod
    def custom_ask(parent, title, question, *buttons_labels):
        """Ask for custom operation confirmation."""
        msg_box = QMessageBox(parent)
        msg_box.setIcon(QMessageBox.Question)
        msg_box.setWindowTitle(title)
        msg_box.setTextFormat(Qt.RichText)
        msg_box.setText(question)
        for button_txt in buttons_labels:
            msg_box.addButton(QPushButton(button_txt), QMessageBox.YesRole)
        msg_box.exec_()
        clicked_button = msg_box.clickedButton()
        clicked_button_text = clicked_button.text()
        return clicked_button_text

    def pick_item(self, title, message, parent=None, *items):
        """Getting item from list of items."""
        if self.iface is None:
            return None
        parent = parent if parent is not None else self.iface.mainWindow()
        item, accept = QInputDialog.getItem(parent, title, message, items, editable=False)
        if accept is False:
            return None
        return item

    def log_msg(self, msg, level=Qgis.Info):
        """Log the message to QGIS log with a given level."""
        QgsMessageLog.logMessage(msg, self.context, level)

    def log_warn(self, msg):
        """Log the warning to QGIS logs."""
        self.log_msg(msg, level=Qgis.Warning)

    def log_info(self, msg):
        """Log the info message to QGIS logs."""
        self.log_msg(msg, level=Qgis.Info)

    def progress_bar(self, msg, minimum=0, maximum=0, init_value=0, clear_msg_bar=False):
        """Setting progress bar."""
        if self.iface is None:
            return None
        if clear_msg_bar:
            self.iface.messageBar().clearWidgets()
        pmb = self.iface.messageBar().createMessage(msg)
        pb = QProgressBar()
        pb.setMinimum(minimum)
        pb.setMaximum(maximum)
        pb.setValue(init_value)
        pb.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        pmb.layout().addWidget(pb)
        self.iface.messageBar().pushWidget(pmb, Qgis.Info)
        return pb

    def clear_message_bar(self):
        """Clearing message bar."""
        if self.iface is None:
            return None
        self.iface.messageBar().clearWidgets()
