import json

from PyQt5.QtNetwork import QNetworkRequest
from qgis.core import QgsBlockingNetworkRequest
from qgis.PyQt.QtCore import QUrl, QUrlQuery


class EdrApiClientError(Exception):
    """EDR API exception class."""

    pass


class EdrApiClient:
    """EDR API client class."""

    def __init__(self, root, authentication_config_id=None):
        self.root = root
        self.authentication_config_id = authentication_config_id

    def get_request(self, url, **params):
        request_url = QUrl(url)
        request_query = QUrlQuery()
        for k, v in params.items():
            request_query.addQueryItem(k, v)
        request_url.setQuery(request_query)
        network_request = QNetworkRequest(request_url)
        blocking_network_request = QgsBlockingNetworkRequest()
        if self.authentication_config_id:
            blocking_network_request.setAuthCfg(self.authentication_config_id)
        blocking_network_request.get(network_request)
        error_message = blocking_network_request.errorMessage()
        if error_message:
            raise EdrApiClientError(error_message)
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

    def collection_items_path(self, collection_id, instance_id=None):
        if instance_id is None:
            url = self.collection_path(collection_id)
        else:
            url = self.collection_instance_path(collection_id, instance_id)
        url += "/items"
        return url

    def collection_locations_path(self, collection_id, instance_id=None):
        if instance_id is None:
            url = self.collection_path(collection_id)
        else:
            url = self.collection_instance_path(collection_id, instance_id)
        url += "/locations"
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
        raw_content = response.content().data().decode(errors="ignore")
        response_json = json.loads(raw_content)
        collections = response_json.get("collections", [])
        return collections

    def get_collection(self, collection_id):
        response = self.get_request_reply(self.collection_path(collection_id))
        raw_content = response.content().data().decode(errors="ignore")
        collection = json.loads(raw_content)
        return collection

    def get_collection_instances(self, collection_id):
        response = self.get_request_reply(self.collection_instances_path(collection_id))
        raw_content = response.content().data().decode(errors="ignore")
        response_json = json.loads(raw_content)
        collection_instances = response_json.get("instances", [])
        return collection_instances

    def get_collection_items(self, collection_id, instance_id=None):
        response = self.get_request_reply(self.collection_items_path(collection_id, instance_id))
        raw_content = response.content().data().decode(errors="ignore")
        response_json = json.loads(raw_content)
        collection_items = response_json.get("features", [])
        return collection_items

    def get_collection_locations(self, collection_id, instance_id=None):
        response = self.get_request_reply(self.collection_locations_path(collection_id, instance_id))
        raw_content = response.content().data().decode(errors="ignore")
        response_json = json.loads(raw_content)
        collection_locations = response_json.get("features", [])
        return collection_locations

    def get_edr_data(
        self, collection_id, query_parameters, instance_id=None, item_id=None, location_id=None, data_query_name=None
    ):
        data_endpoint = f"{self.root}/collections/{collection_id}"
        if instance_id is not None:
            data_endpoint += f"/instances/{instance_id}"
        if item_id is not None:
            data_endpoint += f"/items/{item_id}"
        elif location_id is not None:
            data_endpoint += f"/locations/{location_id}"
        else:
            data_endpoint += f"/{data_query_name}"
        response = self.get_request_reply(data_endpoint, **query_parameters)
        return response
