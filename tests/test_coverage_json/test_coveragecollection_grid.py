import typing

import numpy as np
from qgis.core import QgsCoordinateReferenceSystem, QgsMapLayer, QgsRasterLayer
from qgis.PyQt.QtCore import QDateTime

from edr_plugin.coveragejson.coverage import Coverage
from edr_plugin.coveragejson.coverage_json_reader import CoverageJSONReader
from edr_plugin.coveragejson.utils import ArrayWithTZ


def test_grid(data_dir):
    filename = data_dir / "coveragecollection_grids.covjson"

    assert filename.exists()

    coverage_json = CoverageJSONReader(filename)

    assert coverage_json.referencing

    assert (
        coverage_json.crs().toWkt()
        == 'GEOGCS["Unknown",DATUM["Unknown",SPHEROID["WGS_1984",6378137,298.257223563]],PRIMEM["Greenwich",0],UNIT["degree",0.017453]]'
    )

    assert coverage_json.domain_type == "Grid"
    assert coverage_json.coverages_count == 4

    coverages = coverage_json.coverages

    assert all(isinstance(c, Coverage) for c in coverages)

    for i in range(4):
        coverage = coverages[i]
        assert isinstance(coverage, Coverage)
        assert len(coverage.parameter_names) == 2

        param_name = list(coverage.ranges.keys())[0]

        assert len(coverage.raster_layers(param_name)) == 1
        assert all(isinstance(layer, QgsRasterLayer) for layer in coverage.raster_layers(param_name))

        assert len(coverage.map_layers()) == 1
