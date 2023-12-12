import json

from PyQt5.QtNetwork import QNetworkRequest
from qgis.core import QgsBlockingNetworkRequest
from qgis.PyQt.QtCore import QUrl, QUrlQuery


class EdrApiClientError(Exception):
    """EDR API exception class."""

    pass


class EdrApiClient:
    """EDR API client class."""

    def __init__(self, root, authorization=None):
        self.root = root
        self.authorization = authorization

    @staticmethod
    def get_request(url, **params):
        request_url = QUrl(url)
        request_query = QUrlQuery()
        for k, v in params.items():
            request_query.addQueryItem(k, v)
        request_url.setQuery(request_query)
        network_request = QNetworkRequest(request_url)
        blocking_network_request = QgsBlockingNetworkRequest()
        blocking_network_request.get(network_request)
        return blocking_network_request

    def get_request_reply(self, url, **params):
        network_request = self.get_request(url, **params)
        reply = network_request.reply()
        return reply

    @property
    def landing_page_path(self):
        url = f"{self.root}/"
        return url

    @property
    def api_description_path(self):
        url = f"{self.root}/api"
        return url

    @property
    def conformance_path(self):
        url = f"{self.root}/conformance"
        return url

    @property
    def collections_path(self):
        url = f"{self.root}/collections"
        return url

    def collection_path(self, collection_id):
        url = f"{self.root}/collections/{collection_id}"
        return url

    def collection_items_path(self, collection_id):
        url = f"{self.root}/collections/{collection_id}/items"
        return url

    def collection_query_path(self, collection_id, query_type):
        url = f"{self.root}/collections/{collection_id}/{query_type}"
        return url

    def collection_instances_path(self, collection_id):
        url = f"{self.root}/collections/{collection_id}/instances"
        return url

    def collection_instance_path(self, collection_id, instance_id):
        url = f"{self.root}/collections/{collection_id}/instances/{instance_id}"
        return url

    def collection_instance_query_path(self, collection_id, instance_id, query_type):
        url = f"{self.root}/collections/{collection_id}/instances/{instance_id}/{query_type}"
        return url

    def get_collections(self):
        response = self.get_request_reply(self.collections_path)
        raw_content = response.content().data().decode()
        response_json = json.loads(raw_content)
        collections = response_json["collections"]
        return collections

    def get_collection_instances(self, collection_id):
        response = self.get_request_reply(self.collection_instances_path(collection_id))
        raw_content = response.content().data().decode()
        response_json = json.loads(raw_content)
        collection_instances = response_json["instances"]
        return collection_instances

    def get_edr_data(self, collection_id, instance_id, data_query_name, payload):
        data_endpoint = f"{self.root}/collections/{collection_id}"
        if instance_id:
            data_endpoint += f"/instances/{instance_id}"
        data_endpoint += f"/{data_query_name}"
        response = self.get_request_reply(data_endpoint, **payload)
        return response
