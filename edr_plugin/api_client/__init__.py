import requests


class EDRApiClientError(Exception):
    pass


class EDRApiClient:
    def __init__(self, root, authorization=None):
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
        collections_with_links = response.json()
        collections = collections_with_links["collections"]
        return collections
