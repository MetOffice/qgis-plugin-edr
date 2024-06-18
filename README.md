# QGIS plugin to access EDR services


Introduction
============

The QGIS EDR Plugin allows users of the open source geographical
information system to gain access to Open Geospatial Consortium (OGC)
API -[Environmental Date Retrieval (EDR)](https://ogcapi.ogc.org/edr/)
compatible services. The
services will return data to the client machines and save it locally.
The plugin allows users to re-run saved queries for a particular
location, for example, given the nature of the spatio-temporal service
where data may change on a regular basis. This enables users to get the
latest copy of data for their area of interest.

Getting The Plugin
==================

If the QGIS EDR Plugin has not been installed, then the plugin can be
obtained from the official repository for QGIS plugins here:
<https://plugins.qgis.org/plugins/edr_plugin/>.

Using The Plugin
================

This section illustrates how the plugin is to be used.

After the QGIS plugin is installed, the user can begin a request for
data through an OGC API – EDR endpoint by clicking on the EDR icon.

<img src="./docs/images/image1.png"
style="width:2.24892in;height:2.00694in" />

This will open the following dialog box which will enable the service to
be queried.

<img src="./docs/images/image2.png"
style="width:2.47222in;height:2.65319in" alt="A screenshot of a computer
Description automatically generated" />

Overview Of The Plugin Connection Interface
-------------------------------------------

This illustrates the main features of the EDR dialogue.

<img src="./docs/images/image2.png"
style="width:4.19954in;height:4.50694in" alt="A screenshot of a computer
Description automatically generated" />

Building an EDR Request
-----------------------

### Server Details

The first step is to add a new **Server URL**. This is the location of
the root for the EDR service from which QGIS can read the metadata for
the service.

Authentication: if the service is an authenticated service, then add
credentials for the service. Supported authentication includes the
following sets: API header, basic authentication (username and
password), identity certificate authentication, MapTiler HMAC-SHA256,
OAuth2, PKI PKCS\#12 and PKI paths authentication types.

<img src="./docs/images/image3.png"
style="width:2.20231in;height:1.66976in" alt="A screenshot of a computer
Description automatically generated" />

Each of these use the existing QGIS authentication management system and
will store details in the QGIS authentication database which is included
in QGIS. This will appear upon starting QGIS and needs a password to be
setup.

<img src="./docs/images/image4.png"
style="width:2.82659in;height:1.49308in" alt="A screenshot of a computer
Description automatically generated" />

#### *HTTP Methods*

QGIS supports both GET and POST HTTP methods. It is possible to change
between the two by selecting the option to use POST queries or toggling
it off (as shown) which is the default and enables GET methods:

<img src="./docs/images/image5.png"
style="width:1.98266in;height:0.26226in" />

The main advantage of the POST request is to include more data in a
request to the EDR server (for example a bigger geometry object) as part
of the query request.

### Collection Options

When the service has been configured and a connection has been
successful, the collections along with any instances (if present) and
the data queries that the service supports will be shown in the drop
downs. This information is read from the service metadata and will be
displayed in the drop down menus for each of these. It is possible to
select values from the options for the service.

If the service metadata does not support instances for example, then no
instances will be present. Data query options will be those available in
the EDR service.

#### Setting the Spatial Extent

The spatial extent needs to be created based upon the type of query
type. To set the spatial extent, the ‘Set spatial extent’ button should
be clicked. This will open a dialogue box that will vary according to
the data query type. A polygon will be created for an area and cube query, a
point for a position query, a line string for the corridor and trajectory queries and a circle radius based on a centre point
for the radius query. These are defined in detail below.

Should the spatial extent not be set, and the user attempts to run the
query, then there will be a warning message before the user is prompted
to select the extent after clicking OK.

<img src="./docs/images/image6.png"
style="width:2.06358in;height:0.70871in" alt="Warning of the spatial extent not being set" />

The user will then be given an option to input the extent for the type of query selected based upon the input dialogues listed below.

**NOTE: the corridor and the trajectory queries are experimental services and may experience issues based upon the EDR server configuration.** All EDR queries, perhaps with the exception of trajectory and point, which are expected to return a large amount of data could suffer from slow responses. For potentially large data requests (large geospatial area, number of levels, timesteps, parameters, high data resolution), users should choose a binary format such as netCDF or GRIB2 (if available). JSON, CoverageJSON and GeoJSON are verbose and can add delay to requests. This can be attributed to the time to respond to the request from the server, the time to transmit the data, or the time for QGIS to process and render the data payload.

<img src="./docs/images/image7.png"
style="width:1.86127in;height:1.06403in" alt="A screenshot of a computer
Description automatically generated" />

1.  **Area Query** – the user has the option to enter a rectangular
    extent based upon maximum values for the north, west, east and south
    coordinate values, there is an option to use the map canvas extent
    that is showing or there is an option to draw a rectangular area on
    the map.

<img src="./docs/images/image8.png"
style="width:2.75936in;height:1.57678in" alt="Area query spatial extent." />

Clicking on the **Map Canvas Extent** button the coordinates of the
existing map view will be added to the north, west, east and south
values to form a rectangle based upon the current map view.

The **Draw on Canvas** option allows the user to select a rectangular
area from the background map. Select the top left corner of the bounding
box and drag the area to form a bounding box. Upon completion the
coordinates will be populated in the north, west, east and south boxes.

<img src="./docs/images/image9.png"
style="width:2.48128in;height:1.68085in" alt="Drag a bounding box to draw on the canvas" />

It is also possible to create an extent from a pre-existing **layer**
that is present in the QGIS project. Select the layer option and select
the layer that the area should be. There are also options to select a
**layout map** or from pre-saved **bookmarks**. Each of these options
functions in the same way, bringing in a selected geometry.

1.  **Position Query** – when a data query of position is selected the
    user will be prompted to select a point from the map when clicking
    on the set spatial extent button.

2.  **Radius Query** – a radius data query enables the user to create a
    radius from a centre point with a defined radius in particular
    units. Select a radius query, then select the set spatial extent
    button which will show the following dialogue:

<img src="./docs/images/image10.png"
style="width:4.16688in;height:2.25012in" alt="Defining a radius query" />

Click on the Radius centre point: &lt;NOT SET&gt; to select a point on
the map and select the desired radius value and units from the drop down
list. It is possible to change the radius values by typing into the text
box or use the selectors to increase or decrease the values by 1.

1.  **Locations Query** – when the locations query type is selected the
    set spatial extent button reveals a list of possible location to
    select. The list is presented in a drop down menu, and the user can
    then select the location that is of interest.

<img src="./docs/images/image11.png"
style="width:4.13216in;height:2.27095in" alt="Select an available location for the location query" />

Select one of the location names and then click on the OK button to get
data for the pre-defined location.

1.  **Items Query** – this query allows users to select a particular
    pre-defined item from the EDR service and it behaves in a similar
    way to the locations. When the user has selected an items query type
    and clicked on the set spatial extent button then a list of
    available items is displayed to be selected from the drop down menu.
    Select a value and click OK.

<img src="./docs/images/image12.png"
style="width:4.13216in;height:2.27095in" alt="Select an available item from the drop down for an items query" />

Selected items will be displayed on the EDR interface:

<img src="./docs/images/image13.png"
style="width:5.19471in;height:0.59031in" />

1.  **Cube Query** - the cube query functions similarly to an area query (above). It needs to have a bounding box set for the x, y dimensions of the cube to be defined.

![image](https://github.com/MetOffice/qgis-plugin-edr/assets/4614980/a41646c6-7887-4591-88cb-14201f08be95)
![image](https://github.com/MetOffice/qgis-plugin-edr/assets/4614980/a41646c6-7887-4591-88cb-14201f08be95)

The z dimension is determined by selecting the vertical extent in the EDR plugin interface.
![image](https://github.com/MetOffice/qgis-plugin-edr/assets/4614980/3d1f35b6-a444-42b6-9edd-31dbf7de769d)
![image](https://github.com/MetOffice/qgis-plugin-edr/assets/4614980/3d1f35b6-a444-42b6-9edd-31dbf7de769d)

1.  **Corridor Query** - the corridor is based on a line string that can have either x and y parameters, x, y and z or x, y, z and time (m) components. 
	
It is possible to select an existing line feature that is open on the map to save having to input the nodes of the line. To select an existing line, click on the ‘Select an existing line feature’ button and then select the line on the map view. This will update the table with the coordinates from the line. 

There is a manual option to insert a line node (as x, y / x, y, z  or x, y, z, m (for time)) by clicking on the green + button. Enter the sets of coordinates until the line is defined. To remove a set of coordinates, click on the red – button when the cursor is in that row. 

It is possible to define a corridor’s width, height with their units, selected by the drop downs, and the resolutions for sampling the corridor with the resolution x / y or z parameters (if they are supported by the EDR service). 

As another option it is possible to copy and paste a well known text (WKT) line string that must conform to the WKT LineString / LineStringZ, LineStringM or LineStringZM standard with the elements all present. The interface will turn red for an invalid line string that is pasted into the dialogue box. If this is the case the line string will need to be edited to correct the error.

![image](https://github.com/MetOffice/qgis-plugin-edr/assets/4614980/8cbaafb2-5cdb-4166-ae5d-eb951cc365d9)
![image](https://github.com/MetOffice/qgis-plugin-edr/assets/4614980/8cbaafb2-5cdb-4166-ae5d-eb951cc365d9)

**NOTE:** If the EDR service is not configured to include information on width or height units then there will be an error messagge displayed:

![image](https://github.com/MetOffice/qgis-plugin-edr/assets/4614980/3780a0a5-ba8d-4943-b2f9-313abe949b79)
![image](https://github.com/MetOffice/qgis-plugin-edr/assets/4614980/3780a0a5-ba8d-4943-b2f9-313abe949b79)
	
**THE CORRIDOR QUERY IS EXPERIMENTAL and relies on EDR servers adhering to the OGC API – Environmental Data Retrieval standard.**

1.  **Trajectory Query** - the trajectory query allows the input of a 4 dimensional trajectory object that will be sent to the EDR service in WKT format. The input allows an existing trajectory line feature to be selected form the map, coordinates to be input or a WKT line string to be pasted into the dialogue box. Each box will be updated upon the input of line geometry data from one of the other options.

To select an existing line feature that must be open on the map, click on the ‘Select an existing line feature box'. Alternatively, there is an option to manually build a trajectory as a line string using x, y, z and m (time) elements or to paste a valid line string WKT object into the enter geometry box. 

![image](https://github.com/MetOffice/qgis-plugin-edr/assets/4614980/c5913460-4ae3-4483-b91b-670f7cdddd78)
![image](https://github.com/MetOffice/qgis-plugin-edr/assets/4614980/c5913460-4ae3-4483-b91b-670f7cdddd78)

Upon completion of the trajectory, click on the OK button. 

When the trajectory has been created with a m (temporal) dimension then the  temporal extent (m dimension of the line string) on the main menu will be disabled. When the trajectory has a z (height) dimension set then the vertical extent options are disabled as the values will be taken from the defined geometry object. Both the vertical and temporal extents will be disabled when a z and m value are set on the geometry. 

![image](https://github.com/MetOffice/qgis-plugin-edr/assets/4614980/7ee95a95-a743-4519-9ed8-447362496902)
![image](https://github.com/MetOffice/qgis-plugin-edr/assets/4614980/7ee95a95-a743-4519-9ed8-447362496902)

The values in the vertical and temporal extents can be selected when the geometry only has an x and y dimension set on the geometry.

### Setting Output Options

There are two output options to select: the **output coordinate
reference system (CRS)** and the **output format**. The CRS options are
based upon the supported service as well as the output formats.

**NOTE:** The QGIS plugin officially supports output formats of NetCDF4,
GRIB2 and CovJSON, however, other formats such as geotiff, geojson are
supported and do work.

### Setting Parameters

Some services provide parameters that can be selected. When present the
parameters will appear in the Parameters drop down menu list and may be
selected from this list, either individually or a selection of more than
one. Select a parameter by ticking the tick box.

<img src="./docs/images/image14.png"
style="width:5.2086in;height:0.52086in" />

There is an option to select or deselect all parameters. By ticking or
unticking this option, all available parameters will be selected or
deselected. When it is selected all parameters will be shown as a comma
delimited list in the parameters text on the drop down menu.

<img src="./docs/images/image15.png"
style="width:5.13221in;height:0.50697in" alt="A white rectangular object with a
black border Description automatically generated" />

Extents and Dimensions
----------------------

The Environmental Data Retrieval API has been created with temporal and
spatial data in mind. It works with multi-dimensional data that has a
temporal, vertical and multidimensional aspects that include instances.
There are also custom dimensions that a service can provide.

### Temporal Extent

For any EDR collection that supports temporal data the temporal extent
shall be shown for the collection. The values will be dynamically shown
when they are present. It is possible to change the time range from the
dropdown menus for the ‘from’ and ‘to’ values.

<img src="./docs/images/image16.png"
style="width:5.29888in;height:0.56947in" alt="Temporal extent input" />

Clicking on the dropdown menu allows the user to select another date
from a calendar date picker. It is possible to select a different date
within the range of the temporal extent. As mentioned above, this may be disabled for a trajectory query that has had a temporal (m) value defined in the line string. 

<img src="./docs/images/image17.png"
style="width:5.29194in;height:1.70842in" alt="Changing the temporal extent" />

The time values may be edited in the text boxes by overtyping the values
present. This applies to the ‘from’ and the ‘to’ extents.

<img src="./docs/images/image18.png"
style="width:2.09038in;height:0.63198in" alt="The time values can be directly edited" />

### Vertical Extent

When vertical extents are supported by the collection in the service,
then there is an option to select these manually from the drop down
menu. If the service does not support a vertical extent this option will
be greyed out or if there is a trajectory query that has a line string defining the vertical extent.

<img src="./docs/images/image19.png"
style="width:5.2711in;height:0.79865in" alt="The vertical extent drop down" />

Select as many vertical extents as needed by selecting values from the
drop down menu using the tick boxes.

<img src="./docs/images/image20.png"
style="width:5.19471in;height:1.46535in" alt="Select vertical extents from the drop down" />

There is also an option to select the minimum and maximum range (click
the use min/max range tick box) or to select or deselect all (use the
check/uncheck all tick box).

Selecting all will show all values as a delimited list in the text box:

<img src="./docs/images/image21.png"
style="width:5.27805in;height:0.77782in" alt="Delimited list of selected vertical extents" />

### Custom Dimensions

A service may have further dimensions defined as custom dimensions and
these will appear in the drop down menu when they are in the service
metadata.

The dimension dropdown menu shall display all available dimensions that
the service offers, there is an option to select this. The intervals
option allows users to select either individual or multiple values by
means of the drop down menu.

There is also an option to select the minimum and maximum range (click
the use min/max range tick box) or to select or deselect all (use the
check/uncheck all tick box). Selecting all will show all values as a
delimited list in the text box.

Download Directory
------------------

The final option to select on the EDR plugin interface is the directory
where files returned from the service will be saved.

<img src="./docs/images/image22.png"
style="width:5.13221in;height:0.27779in" alt="Download directory location" />

This can be altered by clicking on the change button and navigating to a
directory location where the user wants to save EDR data.

<img src="./docs/images/image23.png"
style="width:5.87139in;height:2.35573in" alt="Choosing the directory location" />

After all the above has been completed, there are some options to
execute the query that has been built.

Running The Query
-----------------

There are three options for running the query: There is an option to run and save the query (Run and save
query), another just to run the query (Run query) and one to cancel the operation.

The run and save query will create an entry in the **QGIS Browser** view
to be able to re-run the same EDR API request later. This has the
advantage of being able to specify an area for example and allows the
user to re-use parameters to get an updated set of data in the future.
The saved queries will appear under the Environmental Data Retrieval
heading (highlighted below):

<img src="./docs/images/image24.png"
style="width:2.83237in;height:2.79769in" alt="The browser window showing where the Environmental Data Retrieval queries are saved" />

Running the query will just download the file format defined into the
directory that has been specified. When the query is running a blue bar will
appear above the map. This shows the user the collection being selected
and highlights the progress.

<img src="./docs/images/image25.png"
style="width:6.26806in;height:0.15764in" alt="Query running blue bar" />

Data will be downloaded to the specified directory in the chosen file
format. When it is downloaded the file will appear on the **QGIS
Layers** list and can be interacted with (toggled off and on for
example) from here. It is possible to change the properties of the layer
from this view.

### Working with Saved Queries

When an EDR query has been saved the service will appear under the
Environmental Data Retrieval heading in the QGIS Browser view (if this
is not visible it can be opened from the menu: View, then Panels and
Browser). The query will appear with the service URL. By right clicking
on this there are options to have a new server query or delete the
service reference from the Browser panel.

<img src="./docs/images/image26.png"
style="width:1.8784in;height:0.47399in" alt="Right click to run or delete an existing query." />

Below the service URL will be a collection name with a date when the
query was executed.

By right clicking on the saved query a menu will appear with options to:

1.  Repeat the query. This will re-run the query as it is.

2.  Rename the query. This enables the query to be renamed.

3.  Delete the query. This allows the query to be deleted.

<img src="./docs/images/image27.png"
style="width:1.49133in;height:0.65651in" alt="Optionally repeat, rename or delete an existing query by right clicking on it." />

Guidance: Working With The QGIS Plugin
======================================

The following section highlights how QGIS works with certain types of
data and file types. It gives some hints to users on how best to use the
plugin with the different types of data.

Temporally Enabled Data
-----------------------

Where data has a temporal (time) element then the temporal navigation
tool will enable it to be animated through time. To get this go to the
menu item View, Panels, Temporal Controller. This will show the
controller:

<img src="./docs/images/image28.png"
style="width:6.26806in;height:0.4375in" alt="Temporal controller" />

Temporally enabled layers will have a clock icon next to them in the
QGIS Layers panel.
<img src="./docs/images/image29.png"
style="width:0.13873in;height:0.15607in" alt="Clock icon for the temporal controller" />

Viewing NetCDF Data
-------------------

The NetCDF files may not apparently appear on the map layer when they
are downloaded and added as a layer in QGIS. To resolve this issue,
which may be associated with the temporal controller, ensure that the
temporal navigation is turned off.

Navigate to the temporal controller and disable the control by clicking
on the ‘turn off temporal navigation’ button (the lefthand button with
the red cross). It will be shown as disabled:

<img src="./docs/images/image30.png"
style="width:1.84037in;height:0.45836in" alt="Temporal controller showing as disabled with a red cross" />

This should make the NetCDF file appear on the map view.

Viewing CovJSON Data
--------------------

The CovJSON data sometimes may not appear on the map, with the temporal
controller enabled, if this is the case refresh the temporal range from
the temporal controller by clicking on the ‘set to full range’ (refresh)
button. This is the two blue arrows on the right of the image below.

<img src="./docs/images/image31.png"
style="width:4.29883in;height:0.75698in" alt="To refresh the times on the temporal controller press the blue arrow icon." />

Working With Multiple Vertical Extents
--------------------------------------

When there is a dataset with multiple vertical extents the user can
navigate between each vertical level by using the layers panel to turn
layers off and on.

Here data is displayed for the temperature on 13 February 2024 18:00
model run at three vertical height levels: 850, 925 and 1000.

<img src="./docs/images/image32.png"
style="width:3.46546in;height:1.02783in" alt="Data displayed for multiple vertical levels." />

For a NetCDF file it is possible to change the vertical levels by using
the symbology groups control to toggle each level on or off:

<img src="./docs/images/image33.png"
style="width:6.26806in;height:1.80625in" alt="Click on the right hand group icon to toggle a group on or off" />

In the above diagram the isobaric 1000 vertical height level is on, it
is possible to click on another value to enable other vertical height
levels.

In **versions of QGIS that are 3.37.0, or above,** there is an option to include a vertical slider to visualise the vertical levels in the data at each vertical level. To enable this functionality, which is out of scope of the EDR plugin, navigate to View, select Data Filtering and enable the Elevation Controller. This will enable a controller to vertically navigate the data at different levels in the map view. Once enabled the vertical slider appears in the map view, on the lefthand side. It is possible to adjust the levels using the two sliders by moving them up or down. It is possible to move the range having set it and then sliding and using the left click button at the same time.

![image](https://github.com/MetOffice/qgis-plugin-edr/assets/4614980/f8db0812-e0c8-4634-bee0-aa279d41864a)
![image](https://github.com/MetOffice/qgis-plugin-edr/assets/4614980/f8db0812-e0c8-4634-bee0-aa279d41864a)

By default, the slider is set from 0 to 100, although this may be changed or inverted for displaying the data being analysed. 

![image](https://github.com/MetOffice/qgis-plugin-edr/assets/4614980/cea908db-0e81-41af-bf14-f76aefcf368b)
![image](https://github.com/MetOffice/qgis-plugin-edr/assets/4614980/cea908db-0e81-41af-bf14-f76aefcf368b)

To invert the direction of the slider from 0 at the top to 100 at the bottom of the control, check the tick box ‘Invert Direction’. Clicking on Set Elevation Range… allows the elevation values to be amended for the data. It will open a Vertical Reference dialogue in the Project Properties. Here it is possible to set the lower and upper elevation range for example and apply a vertical reference system if this is set on the metadata. For terrain it is possible to alter the shading styles. 

![image](https://github.com/MetOffice/qgis-plugin-edr/assets/4614980/3d914908-d183-4edc-b443-c983e333a9ae)
![image](https://github.com/MetOffice/qgis-plugin-edr/assets/4614980/3d914908-d183-4edc-b443-c983e333a9ae)

Layer Properties
----------------

For each layer it is possible to configure the layer properties, by right clicking on the layer and then selecting layer properties and navigating to ‘Elevation’ on the left of the properties. 

![image](https://github.com/MetOffice/qgis-plugin-edr/assets/4614980/6b30a7c3-1bae-418f-abf9-0bbe9873939f)
![image](https://github.com/MetOffice/qgis-plugin-edr/assets/4614980/6b30a7c3-1bae-418f-abf9-0bbe9873939f)

By selecting the Configuration of ‘Fixed Elevation Range Per Group’ from the drop down list, it is possible to add lower and upper bounds to a group of data. In this case it is NetCDF  data. Type the values in the data grid. In the example below there are three isobaric elevations that are set to the values in the grouped layers. They represent 850, 925 and 1000 pressure levels so have had these values added as both upper and lower band values. Click OK or Apply after setting values.

![image](https://github.com/MetOffice/qgis-plugin-edr/assets/4614980/0d7a4253-044a-48cf-bdff-e8d6f6b5dd50)
![image](https://github.com/MetOffice/qgis-plugin-edr/assets/4614980/0d7a4253-044a-48cf-bdff-e8d6f6b5dd50)

Having adjusted the lower and upper band values, the vertical slider will then reflect the values added. Sliding the control to one of the values will mean that the data can then be visualised for that level. 

![image](https://github.com/MetOffice/qgis-plugin-edr/assets/4614980/c23369df-815c-4a17-9e4f-8d6127ca46a1)
![image](https://github.com/MetOffice/qgis-plugin-edr/assets/4614980/c23369df-815c-4a17-9e4f-8d6127ca46a1)

It is possible to load styles for the data here. Click on Style and load style for example. There are other options to manage the layer styles.

