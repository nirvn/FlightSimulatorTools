# Flight Simulator Tools, a QGIS plugin

This QGIS plugin is intented to be a collection of tools to export spatial content from QGIS into flight simulators.

## Flight Plan Maker tool

The flight plan maker tool is a processing algorithm that allows users to make a flight plan (.PLN) file from a set of vector points. To access the tool, open the processing toolbox and expand the Flight Simulator Tools node:

![Procesing toolbox](/documentation/processing_tool.jpg?raw=true)

The tool has several options to specify waypoints' name, elevation, and ordering. Departure and destination airports will be automatically selected by locating the nearest airports to the first and last waypoint. Alternatively, custom departure and/or destination airports can be specified by entering ICAO IDs:

![Flight plan marker tool dialog](/documentation/flight_plan_maker.jpg?raw=true)

Tip: you can select a point dataset outside of available project layers by click on the \[...\] button.
