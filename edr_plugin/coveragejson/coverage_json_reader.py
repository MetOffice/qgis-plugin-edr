import json
import tempfile
import typing
from pathlib import Path

from qgis.core import QgsCoordinateReferenceSystem, QgsMapLayer, QgsVectorLayer

from edr_plugin.coveragejson.coverage import Coverage
from edr_plugin.coveragejson.utils import set_project_time_range


class CoverageJSONReader:
    """Class for reading CoverageJSON files. Handles reading Coverage from the file, CoverageJSON may contain more then one Coverage."""

    def __init__(
        self, filename: typing.Union[str, Path], folder_to_save_data: typing.Optional[typing.Union[str, Path]] = None
    ) -> None:
        self.filename = Path(filename)

        if folder_to_save_data:
            self.folder_to_save_data = Path(folder_to_save_data)
        else:
            self.folder_to_save_data = Path(tempfile.gettempdir())

        with open(self.filename, encoding="utf-8") as file:
            self.coverage_json = json.load(file)

        if "type" not in self.coverage_json:
            raise ValueError("Not a valid CoverageJSON")

        if self.coverage_json["type"] not in ["Coverage", "CoverageCollection"]:
            raise ValueError("Not a valid CoverageJSON")

        self.time_range = None
        self.time_step = None

    @property
    def is_collection(self) -> bool:
        """Check if coverage is collection."""
        return self.coverage_json["type"] == "CoverageCollection"

    @property
    def domain(self) -> typing.Dict:
        """Get domain element."""
        return self.coverage_json["domain"]

    @property
    def referencing(self) -> typing.Dict:
        """Get referencing element."""
        if self.is_collection:
            if "referencing" not in self.coverage_json:
                raise ValueError("Missing `referencing` element in coverage collection.")

            return self.coverage_json["referencing"]
        else:
            if "referencing" not in self.domain:
                raise ValueError("Missing `referencing` element in domain.")

            return self.domain["referencing"]

    def crs(self) -> QgsCoordinateReferenceSystem:
        """Get CRS from referencing element."""

        crs = QgsCoordinateReferenceSystem()

        for ref in self.referencing:
            if "system" not in ref:
                raise ValueError("Missing `system` element in referencing.")

            if "x" in ref["coordinates"] and "y" in ref["coordinates"]:
                crs_id = ref["system"]["id"]

                if "wkt" in ref["system"]:
                    crs = QgsCoordinateReferenceSystem(ref["system"]["wkt"])
                else:
                    if "http:" in crs_id:
                        if "CRS84" in crs_id or "4326" in crs_id:
                            return QgsCoordinateReferenceSystem("EPSG:4326")
                        raise ValueError("Getting CRS from HTTP not supported yet.")

                    crs = QgsCoordinateReferenceSystem(crs_id)

        return crs

    @property
    def domain_type(self) -> typing.Optional[str]:
        """Get domain type."""
        if self.is_collection:
            if "domainType" not in self.coverage_json:
                # domain not specified on collection level, have to exist in each coverage
                return None
            return self.coverage_json["domainType"]
        else:
            return self.domain["domainType"]

    @property
    def coverages(self) -> typing.List[Coverage]:
        """Get list of coverages in CoverageCollection."""
        if self.is_collection:
            coverages = []
            for coverage in self.coverage_json["coverages"]:
                parent_parameters = None
                if "parameters" in self.coverage_json:
                    parent_parameters = self.coverage_json["parameters"]
                coverages.append(
                    Coverage(
                        coverage,
                        self.crs(),
                        self.domain_type,
                        parameters_from_parent=parent_parameters,
                        folder_to_save_data=self.folder_to_save_data,
                    )
                )
            return coverages
        else:
            return [Coverage(self.coverage_json, self.crs(), folder_to_save_data=self.folder_to_save_data)]

    @property
    def coverages_count(self) -> int:
        """Get number of coverages in file."""
        return len(self.coverages)

    def coverage(self, i: int = 0) -> Coverage:
        """Get single coverage from file."""
        if self.is_collection:
            return self.coverages[i]
        else:
            return self.coverages[0]

    def map_layers(self) -> typing.List[QgsMapLayer]:
        """Get list of map layers for all parameters in the CoverageJSON file."""
        layers = []

        layers_for_merge: typing.List[QgsVectorLayer] = []

        if self.is_collection:
            for i in range(self.coverages_count):
                coverage = self.coverage(i)

                time_range_coverage = coverage.time_range()
                time_step_coverage = coverage.time_step()

                if time_range_coverage:
                    if self.time_range:
                        self.time_range.extend(time_range_coverage)
                    else:
                        self.time_range = time_range_coverage

                if self.time_step:
                    if time_step_coverage < self.time_step:
                        self.time_step = time_step_coverage
                else:
                    self.time_step = time_step_coverage

                if not self.coverages[0].could_be_merged:
                    layers.extend(coverage.map_layers())
                else:
                    layers_for_merge.extend(coverage.map_layers())

            if layers_for_merge:
                main_layer = layers_for_merge[0]
                main_layer_dp = main_layer.dataProvider()
                for i in range(1, len(layers_for_merge)):
                    for feature in layers_for_merge[i].getFeatures():
                        main_layer_dp.addFeature(feature)
                layers.append(main_layer)
        else:
            coverage = self.coverage()

            self.time_range = coverage.time_range()
            self.time_step = coverage.time_step()

            layers.extend(coverage.map_layers())

        if layers:
            return layers

        raise ValueError("Domain type not supported yet.")

    def qgsproject_setup_time_settings(self) -> None:
        set_project_time_range(self.time_range, self.time_step)
