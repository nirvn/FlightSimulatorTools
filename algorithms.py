# -*- coding: utf-8 -*-

# /***************************************************************************
# context.py
# ----------
# Date                 : September 2020
# copyright            : (C) 2020 by Mathieu Pellerin
# email                : nirvn dot asia at gmail.com
#
#  ***************************************************************************/
#
# /***************************************************************************
#  *                                                                         *
#  *   This program is free software; you can redistribute it and/or modify  *
#  *   it under the terms of the GNU General Public License as published by  *
#  *   the Free Software Foundation; either version 2 of the License, or     *
#  *   (at your option) any later version.                                   *
#  *                                                                         *
#  ***************************************************************************/


"""
Flight Simulator Tools QGIS Processing algorithms
"""

import os

from qgis.PyQt.QtCore import QCoreApplication
from qgis.core import (QgsCoordinateFormatter,
                       QgsCoordinateReferenceSystem,
                       QgsExpression,
                       QgsFeature,
                       QgsProcessing,
                       QgsFeatureSink,
                       QgsFeatureRequest,
                       QgsPointXY,
                       QgsProcessingException,
                       QgsProcessingAlgorithm,
                       QgsProcessingParameterDefinition,
                       QgsProcessingParameterExpression,
                       QgsProcessingParameterField,
                       QgsProcessingParameterFeatureSource,
                       QgsProcessingParameterFileDestination,
                       QgsProcessingParameterString,
                       QgsSpatialIndex,
                       QgsVectorLayer)
from qgis import processing

class FlightPlanMakerProcessingAlgorithm(QgsProcessingAlgorithm):
    """
    Flight plan maker for Flight Simulator 2020
    """

    TITLE = 'TITLE'
    INPUT = 'INPUT'
    NAME_FIELD = 'NAME_FIELD'
    ELEVATION_FIELD = 'ELEVATION_FIELD'
    ORDERBY_EXPRESSION = 'ORDERBY_EXPRESSION'
    DEPARTURE_AIRPORT = 'DEPARTURE_AIRPORT'
    DESTINATION_AIRPORT = 'DESTINATION_AIRPORT'
    OUTPUT = 'OUTPUT'

    def tr(self, string):
        """
        Returns a translatable string with the self.tr() function.
        """
        return QCoreApplication.translate('Processing', string)

    def createInstance(self):
        return FlightPlanMakerProcessingAlgorithm()

    def name(self):
        return 'flightplanmaker'

    def displayName(self):
        return self.tr('Flight Plan Maker')

    def group(self):
        return self.tr('Flight Simulator 2020')

    def groupId(self):
        return 'flightsimulator2020'

    def shortHelpString(self):
        return self.tr("Build a flight plan for Flight Simulator 2020 using a point layer as intermediary waypoints.\n\nDeparture and destination airports will be automatically selected by locating the nearest airports to the first and last waypoint. Alternatively, custom departure and/or destination airports can be specified by entering ICAO IDs.")

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterString(self.TITLE,
                                                       self.tr('Flight plan description'), 'QGIS flight plan' ))

        self.addParameter(QgsProcessingParameterFeatureSource(self.INPUT,
                                                              self.tr('Flight waypoints layer'),
                                                              [QgsProcessing.TypeVectorPoint]))        
        self.addParameter(QgsProcessingParameterField(self.NAME_FIELD,
                                                      self.tr('Waypoints name field'), parentLayerParameterName=self.INPUT, type=QgsProcessingParameterField.String, optional=True))
        
        elevation_param = QgsProcessingParameterField(self.ELEVATION_FIELD,
                                                      self.tr('Waypoints elevation field'), parentLayerParameterName=self.INPUT, type=QgsProcessingParameterField.Numeric, optional=True)
        elevation_param.setFlags(elevation_param.flags() | QgsProcessingParameterDefinition.FlagAdvanced)
        self.addParameter(elevation_param)        
        orderby_param = QgsProcessingParameterExpression(self.ORDERBY_EXPRESSION,
                                                         self.tr('Waypoints ordering by expression'), parentLayerParameterName=self.INPUT, optional=True)
        orderby_param.setFlags(orderby_param.flags() | QgsProcessingParameterDefinition.FlagAdvanced)
        self.addParameter(orderby_param)

        departure_airport_param = QgsProcessingParameterString(self.DEPARTURE_AIRPORT,
                                                               self.tr('Custom departure airport ICAO ID'), '', optional=True)
        departure_airport_param.setFlags(departure_airport_param.flags() | QgsProcessingParameterDefinition.FlagAdvanced)
        self.addParameter(departure_airport_param)
        destination_airport_param = QgsProcessingParameterString(self.DESTINATION_AIRPORT,
                                                               self.tr('Custom destination airport ICAO ID'), '', optional=True)
        destination_airport_param.setFlags(destination_airport_param.flags() | QgsProcessingParameterDefinition.FlagAdvanced)
        self.addParameter(destination_airport_param)

        self.addParameter(QgsProcessingParameterFileDestination(self.OUTPUT,
                                                                self.tr('Output flight plan file (.PLN)'), fileFilter='Flight plan files (*.PLN *.pln)'))

    def processAlgorithm(self, parameters, context, feedback):
        source = self.parameterAsSource(parameters, self.INPUT, context)
        if source is None:
            raise QgsProcessingException(self.invalidSourceError(parameters, self.INPUT))

        name_field_name = self.parameterAsString(parameters, self.NAME_FIELD, context)
        elevation_field_name = self.parameterAsString(parameters, self.ELEVATION_FIELD, context)
        name_field_index = source.fields().lookupField(name_field_name)
        elevation_field_index = source.fields().lookupField(elevation_field_name)

        request = QgsFeatureRequest()
        request.setDestinationCrs(QgsCoordinateReferenceSystem('EPSG:4326'),context.transformContext())
        expression_string = self.parameterAsString(parameters, self.ORDERBY_EXPRESSION, context)
        if expression_string:
            expression = QgsExpression(expression_string)
            if expression.hasParserError():
                raise QgsProcessingException(expression.parserErrorString())
            request.addOrderBy(expression_string)

        departure_point = QgsPointXY()
        destination_point = QgsPointXY()
        user_points = ''

        total = 100.0 / source.featureCount() if source.featureCount() else 0
        features = source.getFeatures(request)
        for current, feature in enumerate(features):
            if feedback.isCanceled():
                break
            if not feature.hasGeometry():
                continue
            point = feature.geometry().asPoint()
            
            if departure_point.isEmpty():
                departure_point = point
            destination_point = point

            name = 'UNTITLED'
            if name_field_index >= 0:
                name = feature[name_field_index]

            elevation = 1000.0
            if elevation_field_index >= 0:
                elevation = feature[elevation_field_index]
            user_points += '        <ATCWaypoint id="{}">\n            <ATCWaypointType>User</ATCWaypointType>\n            <WorldPosition>{}</WorldPosition>\n        </ATCWaypoint>\n'.format(name, self.formattedCoordinateElevation(point, elevation))
            feedback.setProgress(int(current * total))

        if departure_point.isEmpty():
            raise QgsProcessingException('Error: departure point is missing')
        if destination_point.isEmpty():
            raise QgsProcessingException('Error: destination point is missing')

        strips = QgsVectorLayer(os.path.join(os.path.dirname(__file__),'data','strips.gpkg'),'strips')
        index = QgsSpatialIndex(strips.getFeatures())

        icao_index = strips.fields().lookupField('icao')
        name_short_index = strips.fields().lookupField('nameshort')

        departure_airport = self.parameterAsString(parameters, self.DEPARTURE_AIRPORT, context)
        if departure_airport:
            feature = QgsFeature()
            expression = QgsExpression("icao ILIKE '{}'".format(departure_airport))
            strips.getFeatures(QgsFeatureRequest(expression)).nextFeature(feature)
            if feature:
                departure_point = feature.geometry().asPoint()
            else:
                raise QgsProcessingException('Error: custom departure airport ICAO ID not found')

        destination_airport = self.parameterAsString(parameters, self.DESTINATION_AIRPORT, context)
        if destination_airport:
            feature = QgsFeature()
            expression = QgsExpression("icao ILIKE '{}'".format(destination_airport))
            strips.getFeatures(QgsFeatureRequest(expression)).nextFeature(feature)
            if feature:
                destination_point = feature.geometry().asPoint()
            else:
                raise QgsProcessingException('Error: custom destination airport ICAO ID not found')

        departure = ''
        departure_header = ''
        destination = ''
        destination_header = ''
        if not departure_point.isEmpty():
            departure_id = index.nearestNeighbor(departure_point)
            feature = strips.getFeature(departure_id[0])
            point = feature.geometry().asPoint()
            elevation = 50.0
            departure = '        <ATCWaypoint id="{}">\n            <ATCWaypointType>Airport</ATCWaypointType>\n            <WorldPosition>{}</WorldPosition>\n            <RunwayNumberFP>1</RunwayNumberFP>\n            <ICAO>\n                <ICAOIdent>{}</ICAOIdent>\n            </ICAO>\n        </ATCWaypoint>\n'.format(feature[icao_index], self.formattedCoordinateElevation(point, elevation), feature[icao_index])
            departure_header = '        <DepartureID>{}</DepartureID>\n        <DepartureLLA>{}</DepartureLLA>\n        <DepartureName>{}</DepartureName>\n'.format(feature[icao_index], self.formattedCoordinateElevation(point, elevation), feature[name_short_index])
        
        if not destination_point.isEmpty():
            destination_id = index.nearestNeighbor(destination_point)
            feature = strips.getFeature(destination_id[0])
            point = feature.geometry().asPoint()
            elevation = 50.0
            destination = '        <ATCWaypoint id="{}">\n            <ATCWaypointType>Airport</ATCWaypointType>\n            <WorldPosition>{}</WorldPosition>\n            <RunwayNumberFP>1</RunwayNumberFP>\n            <ICAO>\n                <ICAOIdent>{}</ICAOIdent>\n            </ICAO>\n        </ATCWaypoint>\n'.format(feature[icao_index], self.formattedCoordinateElevation(point, elevation), feature[icao_index])
            destination_header = '        <DestinationID>{}</DestinationID>\n        <DestinationLLA>{}</DestinationLLA>\n        <DestinationName>{}</DestinationName>\n'.format(feature[icao_index], self.formattedCoordinateElevation(point, elevation), feature[name_short_index])
        
        title = self.parameterAsString(parameters, self.TITLE, context)

        plan_file_path = self.parameterAsString(parameters,self.OUTPUT,context)
        plan_file = open(plan_file_path,'w')
        plan_file.write('<?xml version="1.0" encoding="UTF-8"?>\n\n<SimBase.Document Type="AceXML" version="1,0">\n    <Descr>AceXML Document</Descr>\n    <FlightPlan.FlightPlan>\n        <Title>{}</Title>\n        <FPType>IFR</FPType>\n        <RouteType>LowAlt</RouteType>\n        <CruisingAlt>11000.000</CruisingAlt>\n'.format(title))
        plan_file.write(departure_header + destination_header)
        plan_file.write('        <Descr>{}</Descr>\n        <AppVersion>\n            <AppVersionMajor>11</AppVersionMajor>\n            <AppVersionBuild>282174</AppVersionBuild>\n        </AppVersion>\n'.format(title))
        plan_file.write(departure + user_points + destination)
        plan_file.write('    </FlightPlan.FlightPlan>\n</SimBase.Document>\n')
        plan_file.close()
        
        return {self.OUTPUT: plan_file_path}

    def formattedCoordinateElevation(self, point, elevation):
        lon = QgsCoordinateFormatter.formatX(point.x(), QgsCoordinateFormatter.FormatDegreesMinutesSeconds, 3)
        lon = lon[-1:] + lon[:-1]
        lon = lon.replace('°', '° ').replace('′', '\' ').replace('″', '\"')
        lat = QgsCoordinateFormatter.formatY(point.y(), QgsCoordinateFormatter.FormatDegreesMinutesSeconds, 3)            
        lat = lat[-1:] + lat[:-1]
        lat = lat.replace('°', '° ').replace('′', '\' ').replace('″', '\"')
            
        if (elevation > 999999.99):
            elevation = 999999.99
        elevation = f'{elevation:.2f}'
        elevation = elevation.rjust(9,'0')
        
        return '{},{},+{}'.format(lat,lon,elevation)
