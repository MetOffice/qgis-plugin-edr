from qgis.PyQt.QtCore import QRunnable, pyqtSignal, pyqtSlot

from edr_plugin.api_client import EDRApiClient, EDRApiClientError


class EdrDataDownloaderSignals:
    progress = pyqtSignal(str, int, int)
    finished = pyqtSignal(str)
    failed = pyqtSignal(Exception)


class EdrDataDownloader(QRunnable):
    def __init__(self, api_base_url, data_query_definition):
        super().__init__()
        self.api_client = EDRApiClient(api_base_url)
        self.data_query_definition = data_query_definition

    @pyqtSlot()
    def run(self):
        try:
            endpoint_parameters, payload = self.data_query_definition.as_request_parameters()
            response = self.api_client.get_edr_data(*endpoint_parameters, payload)
        except EDRApiClientError as err:
            self.report_error(str(err))
        except Exception as err:
            error_msg = f"Getting data failed due to the following error: {err}"
            self.report_error(error_msg)

    def report_error(self, error_message):
        pass
