from typing import Dict, List, Tuple

from edr_plugin.models.enumerators import EDRDataQuery


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
    ):
        self.collection_id = collection_id
        self.instance_id = instance_id
        self.output_crs = output_crs
        self.output_format = output_format
        self.parameters = parameters
        self.temporal_range = temporal_range
        self.vertical_extent = vertical_extent

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
            intervals, is_min_max_range = self.vertical_extent
            if is_min_max_range:
                z = f"{intervals[-1]}/{intervals[0]}"
            else:
                z = ",".join(intervals)
            query_parameters["z"] = z
        return endpoint_parameters, query_parameters


class AreaQueryDefinition(EDRDataQueryDefinition):
    NAME = EDRDataQuery.AREA.value

    def __init__(self, *parameters, wkt_polygon):
        super().__init__(*parameters)
        self.wkt_polygon = (
            wkt_polygon  #  "POLYGON((-5.869 49.811,-5.892 51.366,-2.681 51.367,-2.674 49.845,-5.869 49.811))"
        )

    def as_request_parameters(self) -> Tuple[Tuple, Dict]:
        endpoint_parameters, query_parameters = super().as_request_parameters()
        query_parameters["coords"] = self.wkt_polygon
        return endpoint_parameters, query_parameters
