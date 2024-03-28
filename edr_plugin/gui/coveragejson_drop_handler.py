from qgis.gui import QgsCustomDropHandler


class CoverageJSONDropHandler(QgsCustomDropHandler):
    """
    coveragejson file drop handler
    """

    def __init__(self, communication, layer_manager) -> None:
        super().__init__()
        self.communication = communication
        self.layer_manager = layer_manager

    def handleFileDrop(self, file):  # pylint: disable=missing-docstring
        if not (file.lower().endswith(".coveragejson") or file.lower().endswith(".covjson")):
            return False
        self.layer_manager.add_layer_from_file(file)
        return True
