from qgis.PyQt.QtCore import QObject, QRunnable, pyqtSignal, pyqtSlot

from edr_plugin.api_client import EdrApiClient, EdrApiClientError
from edr_plugin.utils import download_response_file


class EdrDataDownloaderSignals(QObject):
    """EDR downloader signals."""

    download_progress = pyqtSignal(str, int, int)
    download_success = pyqtSignal(str, str)
    download_failure = pyqtSignal(str)


class EdrDataDownloader(QRunnable):
    """Runnable class for retrieving EDR data within separate thread."""

    def __init__(self, data_query_definition, download_dir):
        super().__init__()
        self.api_client = EdrApiClient()
        self.data_query_definition = data_query_definition
        self.download_dir = download_dir
        self.signals = EdrDataDownloaderSignals()

    @pyqtSlot()
    def run(self):
        """Run download task."""
        try:
            self.report_progress(f"Requesting '{self.data_query_definition.collection_id}' collection data..")
            endpoint_parameters, payload = self.data_query_definition.as_request_parameters()
            response = self.api_client.get_edr_data(*endpoint_parameters, payload)
            response.raise_for_status()
            self.report_progress(f"Downloading '{self.data_query_definition.collection_id}' collection data..")
            download_filepath = download_response_file(response, self.download_dir)
            self.report_success(f"Downloading '{download_filepath}' file finished.", download_filepath)
        except EdrApiClientError as err:
            self.report_error(str(err))
        except Exception as err:
            error_msg = f"Getting data failed due to the following error: {err}"
            self.report_error(error_msg)

    def report_progress(self, message, current_progress=0, total_progress=0):
        """Report runnable progress."""
        self.signals.download_progress.emit(message, current_progress, total_progress)

    def report_success(self, message, downloaded_filepath):
        """Report runnable finished message."""
        self.signals.download_success.emit(message, downloaded_filepath)

    def report_error(self, error_message):
        """Report runnable error message."""
        self.signals.download_failure.emit(error_message)
