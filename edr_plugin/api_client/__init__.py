import requests


class EdrApiClientError(Exception):
    """EDR API exception class."""

    pass


class EdrApiClient:
    """EDR API client class."""

    def __init__(self, root="https://labs.metoffice.gov.uk/edr", authorization=None):
        self.root = root
        self.authorization = authorization

    @staticmethod
    def get_request(url, params=None, **kwargs):
        response = requests.get(url=url, params=params, **kwargs)
        response.raise_for_status()
        return response

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
        response = self.get_request(self.collections_path)
        response_json = response.json()
        collections = response_json["collections"]
        return collections

    def get_collection_instances(self, collection_id):
        response = self.get_request(self.collection_instances_path(collection_id))
        response_json = response.json()
        collection_instances = response_json["instances"]
        return collection_instances

    def get_edr_data(self, collection_id, instance_id, data_query_name, payload):
        data_endpoint = f"{self.root}/collections/{collection_id}"
        if instance_id:
            data_endpoint += f"/instances/{instance_id}"
        data_endpoint += f"/{data_query_name}"
        response = self.get_request(data_endpoint, params=payload)
        return response
