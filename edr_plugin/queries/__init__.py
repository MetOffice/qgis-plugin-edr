from typing import Dict, List, Tuple

from edr_plugin.queries.enumerators import EdrDataQuery


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
            "query": self.NAME,
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

    def populate_from_request_parameters(self, sub_endpoint_queries, query_parameters):
        self.instance_id = sub_endpoint_queries.pop("instance_id", None)
        self.output_crs = query_parameters.pop("crs", None)
        self.output_format = query_parameters.pop("f", None)
        parameter_name = query_parameters.pop("parameter-name", None)
        if parameter_name:
            self.parameters = parameter_name.split(",")
        datetime_str = query_parameters.pop("datetime", None)
        if datetime_str:
            self.temporal_range = tuple(datetime_str.split("/"))
        z = query_parameters.pop("z", None)
        if z:
            if "/" in z:
                vertical_intervals = z.split("/")
                vertical_is_min_max_range = True
            else:
                vertical_intervals = z.split(",")
                vertical_is_min_max_range = False
            self.vertical_extent = (
                vertical_intervals,
                vertical_is_min_max_range,
            )
        custom_dimensions = query_parameters  # Nothing should be left in parameters beside custom dimensions
        for custom_dimension_name, custom_dimension_value in custom_dimensions.items():
            if "/" in custom_dimension_value:
                custom_intervals = custom_dimension_value.split("/")
                custom_is_min_max_range = True
            else:
                custom_intervals = custom_dimension_value.split(",")
                custom_is_min_max_range = False
            self.custom_dimension = custom_dimension_name, custom_intervals, custom_is_min_max_range
            break  # We support only one dimension at the moment

    @classmethod
    def from_request_parameters(cls, collection_id, sub_endpoint_queries, query_parameters):
        query_definition = cls(collection_id)
        query_definition.populate_from_request_parameters(sub_endpoint_queries, query_parameters)
        return query_definition


class AreaQueryDefinition(EDRDataQueryDefinition):
    NAME = EdrDataQuery.AREA.value

    def __init__(self, collection_id, wkt_polygon, **sub_endpoints_with_parameters):
        super().__init__(collection_id, **sub_endpoints_with_parameters)
        self.wkt_polygon = wkt_polygon

    def as_request_parameters(self) -> Tuple[str, Dict, Dict]:
        collection_id, sub_endpoint_queries, query_parameters = super().as_request_parameters()
        query_parameters["coords"] = self.wkt_polygon
        return collection_id, sub_endpoint_queries, query_parameters

    @classmethod
    def from_request_parameters(cls, collection_id, sub_endpoint_queries, query_parameters):
        wkt_polygon = query_parameters.pop("coords", None)
        query_definition = cls(collection_id, wkt_polygon)
        query_definition.populate_from_request_parameters(sub_endpoint_queries, query_parameters)
        return query_definition


class CubeQueryDefinition(EDRDataQueryDefinition):
    NAME = EdrDataQuery.CUBE.value

    def __init__(self, collection_id, bbox, **sub_endpoints_with_parameters):
        super().__init__(collection_id, **sub_endpoints_with_parameters)
        self.bbox = bbox

    def as_request_parameters(self) -> Tuple[str, Dict, Dict]:
        collection_id, sub_endpoint_queries, query_parameters = super().as_request_parameters()
        z = query_parameters.pop("z", None)
        if (not (z is None)):
            if (z.find("/") + z.find(",")) < 0:
                query_parameters["z"] = f'{z}/{z}'
            else:
                query_parameters["z"] = z
        query_parameters["bbox"] = self.bbox
        return collection_id, sub_endpoint_queries, query_parameters

    @classmethod
    def from_request_parameters(cls, collection_id, sub_endpoint_queries, query_parameters):
        bbox = query_parameters.pop("bbox", None)
        query_definition = cls(collection_id, bbox)
        query_definition.populate_from_request_parameters(sub_endpoint_queries, query_parameters)
        return query_definition


class PositionQueryDefinition(EDRDataQueryDefinition):
    NAME = EdrDataQuery.POSITION.value

    def __init__(self, collection_id, wkt_point, **sub_endpoints_with_parameters):
        super().__init__(collection_id, **sub_endpoints_with_parameters)
        self.wkt_point = wkt_point

    def as_request_parameters(self) -> Tuple[str, Dict, Dict]:
        collection_id, sub_endpoint_queries, query_parameters = super().as_request_parameters()
        query_parameters["coords"] = self.wkt_point
        return collection_id, sub_endpoint_queries, query_parameters

    @classmethod
    def from_request_parameters(cls, collection_id, sub_endpoint_queries, query_parameters):
        wkt_point = query_parameters.pop("coords", None)
        query_definition = cls(collection_id, wkt_point)
        query_definition.populate_from_request_parameters(sub_endpoint_queries, query_parameters)
        return query_definition


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

    @classmethod
    def from_request_parameters(cls, collection_id, sub_endpoint_queries, query_parameters):
        wkt_point = query_parameters.pop("coords", None)
        radius = query_parameters.pop("within", None)
        units = query_parameters.pop("within-units", None)
        query_definition = cls(collection_id, wkt_point, radius, units)
        query_definition.populate_from_request_parameters(sub_endpoint_queries, query_parameters)
        return query_definition


class ItemsQueryDefinition(EDRDataQueryDefinition):
    NAME = EdrDataQuery.ITEMS.value

    def __init__(self, collection_id, item_id, **sub_endpoints_with_parameters):
        super().__init__(collection_id, **sub_endpoints_with_parameters)
        self.item_id = item_id

    def as_request_parameters(self) -> Tuple[str, Dict, Dict]:
        collection_id, sub_endpoint_queries, query_parameters = super().as_request_parameters()
        sub_endpoint_queries["item_id"] = self.item_id
        return collection_id, sub_endpoint_queries, query_parameters

    @classmethod
    def from_request_parameters(cls, collection_id, sub_endpoint_queries, query_parameters):
        item_id = query_parameters.pop("item_id", None)
        query_definition = cls(collection_id, item_id)
        query_definition.populate_from_request_parameters(sub_endpoint_queries, query_parameters)
        return query_definition


class LocationsQueryDefinition(EDRDataQueryDefinition):
    NAME = EdrDataQuery.LOCATIONS.value

    def __init__(self, collection_id, location_id, **sub_endpoints_with_parameters):
        super().__init__(collection_id, **sub_endpoints_with_parameters)
        self.location_id = location_id

    def as_request_parameters(self) -> Tuple[str, Dict, Dict]:
        collection_id, sub_endpoint_queries, query_parameters = super().as_request_parameters()
        sub_endpoint_queries["location_id"] = self.location_id
        return collection_id, sub_endpoint_queries, query_parameters

    @classmethod
    def from_request_parameters(cls, collection_id, sub_endpoint_queries, query_parameters):
        location_id = query_parameters.pop("location_id", None)
        query_definition = cls(collection_id, location_id)
        query_definition.populate_from_request_parameters(sub_endpoint_queries, query_parameters)
        return query_definition
