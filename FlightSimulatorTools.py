# -*- coding: utf-8 -*-
"""Flight Simulator Tools

.. note:: This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.
"""

__author__ = '(C) 2020 by Mathieu Pellerin'
__date__ = '05/09/2020'
__copyright__ = 'Copyright 2020, Mathieu Pellerin'
# This will get replaced with a git SHA1 when you do a git archive
__revision__ = '$Format:%H$'

import os
from FlightSimulatorTools.algorithms import FlightPlanMakerProcessingAlgorithm

from qgis.core import QgsApplication, QgsProcessingProvider
from qgis.PyQt.QtGui import QIcon

VERSION = '0.1'

class FlightSimulatorToolsProvider(QgsProcessingProvider):

    def __init__(self):  # pylint: disable=useless-super-delegation
        QgsProcessingProvider.__init__(self)

    def loadAlgorithms(self):  # pylint: disable=missing-docstring
        for alg in [FlightPlanMakerProcessingAlgorithm]:
            self.addAlgorithm(alg())

    def id(self):  # pylint: disable=missing-docstring
        return 'flightsimulatortools'

    def name(self):  # pylint: disable=missing-docstring
        return 'Flight Simulator Tools'

    def longName(self):  # pylint: disable=missing-docstring
        return 'Various Flight Simulator Tools'

    def icon(self):  # pylint: disable=missing-docstring
        return QIcon(os.path.join(os.path.dirname(__file__),'icon.svg'))

    def versionInfo(self):
        # pylint: disable=missing-docstring
        return '0.1'

class FlightSimulatorToolsPlugin:

    def __init__(self, iface):
        super().__init__()
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)
        self.provider = FlightSimulatorToolsProvider()

    def initGui(self):
        QgsApplication.processingRegistry().addProvider(self.provider)

    def unload(self):
        QgsApplication.processingRegistry().removeProvider(self.provider)
        self.provider = None
