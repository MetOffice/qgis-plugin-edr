from typing import Dict, List, Tuple

from edr_plugin.models.enumerators import EdrDataQuery


class EDRDataQueryDefinition:
    NAME = None

    def __init__(
        self,
        collection_id: str,
        instance_id: str = None,
        output_crs: str = None,
        output_format: str = None,
        parameters: List = None,
        temporal_range: Tuple[str, str] = None,
        vertical_extent: Tuple[List, bool] = None,
        custom_dimension: Tuple[str, List, bool] = None,
    ):
        self.collection_id = collection_id
        self.instance_id = instance_id
        self.output_crs = output_crs
        self.output_format = output_format
        self.parameters = parameters
        self.temporal_range = temporal_range
        self.vertical_extent = vertical_extent
        self.custom_dimension = custom_dimension

    def as_request_parameters(self) -> Tuple[str, Dict, Dict]:
        sub_endpoint_queries = {
            "instance_id": self.instance_id,
            "data_query_name": self.NAME,
        }
        query_parameters = {
            "crs": self.output_crs,
            "f": self.output_format,
        }
        if self.parameters:
            query_parameters["parameter-name"] = ",".join(self.parameters)
        if self.temporal_range:
            query_parameters["datetime"] = "/".join(self.temporal_range)
        if self.vertical_extent:
            vertical_intervals, vertical_is_min_max_range = self.vertical_extent
            if vertical_is_min_max_range:
                z = f"{vertical_intervals[-1]}/{vertical_intervals[0]}"
            else:
                z = ",".join(vertical_intervals)
            query_parameters["z"] = z
        if self.custom_dimension:
            custom_dimension_name, custom_intervals, custom_is_min_max_range = self.custom_dimension
            if custom_is_min_max_range:
                custom_dimension_value = f"{custom_intervals[0]}/{custom_intervals[-1]}"
            else:
                custom_dimension_value = ",".join(custom_intervals)
            query_parameters[custom_dimension_name] = custom_dimension_value
        return self.collection_id, sub_endpoint_queries, query_parameters


class AreaQueryDefinition(EDRDataQueryDefinition):
    NAME = EdrDataQuery.AREA.value

    def __init__(self, collection_id, wkt_polygon, **sub_endpoints_with_parameters):
        super().__init__(collection_id, **sub_endpoints_with_parameters)
        self.wkt_polygon = wkt_polygon

    def as_request_parameters(self) -> Tuple[str, Dict, Dict]:
        collection_id, sub_endpoint_queries, query_parameters = super().as_request_parameters()
        query_parameters["coords"] = self.wkt_polygon
        return collection_id, sub_endpoint_queries, query_parameters


class PositionQueryDefinition(EDRDataQueryDefinition):
    NAME = EdrDataQuery.POSITION.value

    def __init__(self, collection_id, wkt_point, **sub_endpoints_with_parameters):
        super().__init__(collection_id, **sub_endpoints_with_parameters)
        self.wkt_point = wkt_point

    def as_request_parameters(self) -> Tuple[str, Dict, Dict]:
        collection_id, sub_endpoint_queries, query_parameters = super().as_request_parameters()
        query_parameters["coords"] = self.wkt_point
        return collection_id, sub_endpoint_queries, query_parameters


class RadiusQueryDefinition(EDRDataQueryDefinition):
    NAME = EdrDataQuery.RADIUS.value

    def __init__(self, collection_id, wkt_point, radius, units, **sub_endpoints_with_parameters):
        super().__init__(collection_id, **sub_endpoints_with_parameters)
        self.wkt_point = wkt_point
        self.radius = radius
        self.units = units

    def as_request_parameters(self) -> Tuple[str, Dict, Dict]:
        collection_id, sub_endpoint_queries, query_parameters = super().as_request_parameters()
        query_parameters["coords"] = self.wkt_point
        query_parameters["within"] = self.radius
        query_parameters["within-units"] = self.units
        return collection_id, sub_endpoint_queries, query_parameters


class ItemsQueryDefinition(EDRDataQueryDefinition):
    NAME = EdrDataQuery.ITEMS.value

    def __init__(self, collection_id, item_id, **sub_endpoints_with_parameters):
        super().__init__(collection_id, **sub_endpoints_with_parameters)
        self.item_id = item_id

    def as_request_parameters(self) -> Tuple[str, Dict, Dict]:
        collection_id, sub_endpoint_queries, query_parameters = super().as_request_parameters()
        sub_endpoint_queries["item_id"] = self.item_id
        return collection_id, sub_endpoint_queries, query_parameters


class LocationsQueryDefinition(EDRDataQueryDefinition):
    NAME = EdrDataQuery.LOCATIONS.value

    def __init__(self, collection_id, location_id, **sub_endpoints_with_parameters):
        super().__init__(collection_id, **sub_endpoints_with_parameters)
        self.location_id = location_id

    def as_request_parameters(self) -> Tuple[str, Dict, Dict]:
        collection_id, sub_endpoint_queries, query_parameters = super().as_request_parameters()
        sub_endpoint_queries["location_id"] = self.location_id
        return collection_id, sub_endpoint_queries, query_parameters
