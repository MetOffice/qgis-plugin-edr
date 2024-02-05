# QGIS plugin to access EDR services


## What is EDR?

The [Open Geospatial Consortium (OGC) Environmental Data Retrieval (EDR) API standard](https://ogcapi.ogc.org/edr/) defines a set of interfaces for retrieving environmental data from various sources. It is designed to be easy to use and interoperable, so that different applications can easily access and share environmental data.

The EDR API standard uses a simple query-based approach to access data. Clients
can specify the data they want by providing a location, time range, and a set of
parameters. The server then returns the data in a standard format, such as
JSON, GeoJSON, GoeTIFF, GRIB, etc.

## QGIS plugin

To use this plugin, you need to first add a compatible server to your list. You
can then define a query, temporal and spatial extent and format. The result
will be loaded in your QGIS session.

You can use QGIS native tools to style and explore the data.

## Limitations

Currently, there are some limitations in using the plugin:

- Lack of support for trajectories and cubic spatial/temporal queries
- CoverageJSON: the plugin only supports a subset of this formt
- Performace: depending on the spatial/temporal extent of your query, QGIS
might struggle with rendering and displaying the results.

