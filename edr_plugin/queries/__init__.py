from typing import Dict, List, Tuple

from edr_plugin.models.enumerators import EdrDataQuery


class EDRDataQueryDefinition:
    NAME = None

    def __init__(
        self,
        collection_id: str,
        instance_id: str,
        output_crs: str,
        output_format: str,
        parameters: List,
        temporal_range: Tuple[str, str],
        vertical_extent: Tuple[List, bool],
        custom_dimension: Tuple[str, List, bool],
    ):
        self.collection_id = collection_id
        self.instance_id = instance_id
        self.output_crs = output_crs
        self.output_format = output_format
        self.parameters = parameters
        self.temporal_range = temporal_range
        self.vertical_extent = vertical_extent
        self.custom_dimension = custom_dimension

    def as_request_parameters(self) -> Tuple[Tuple, Dict]:
        endpoint_parameters = (self.collection_id, self.instance_id, self.NAME)
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
        return endpoint_parameters, query_parameters


class AreaQueryDefinition(EDRDataQueryDefinition):
    NAME = EdrDataQuery.AREA.value

    def __init__(self, *parameters, wkt_polygon):
        super().__init__(*parameters)
        self.wkt_polygon = wkt_polygon

    def as_request_parameters(self) -> Tuple[Tuple, Dict]:
        endpoint_parameters, query_parameters = super().as_request_parameters()
        query_parameters["coords"] = self.wkt_polygon
        return endpoint_parameters, query_parameters


class PositionQueryDefinition(EDRDataQueryDefinition):
    NAME = EdrDataQuery.POSITION.value

    def __init__(self, *parameters, wkt_point):
        super().__init__(*parameters)
        self.wkt_point = wkt_point

    def as_request_parameters(self) -> Tuple[Tuple, Dict]:
        endpoint_parameters, query_parameters = super().as_request_parameters()
        query_parameters["coords"] = self.wkt_point
        return endpoint_parameters, query_parameters


class RadiusQueryDefinition(EDRDataQueryDefinition):
    NAME = EdrDataQuery.RADIUS.value

    def __init__(self, *parameters, wkt_point, radius, units):
        super().__init__(*parameters)
        self.wkt_point = wkt_point
        self.radius = radius
        self.units = units

    def as_request_parameters(self) -> Tuple[Tuple, Dict]:
        endpoint_parameters, query_parameters = super().as_request_parameters()
        query_parameters["coords"] = self.wkt_point
        query_parameters["within"] = self.radius
        query_parameters["within-units"] = self.units
        return endpoint_parameters, query_parameters
