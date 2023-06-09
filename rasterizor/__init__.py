# -*- coding: utf-8 -*-
"""
/***************************************************************************
 FLO-2D Rasterizor
                                 A QGIS plugin
 A plugin to rasterize general FLO-2D ouptut files.
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                             -------------------
        begin                : 2023-04-10
        copyright            : (C) 2023 by Karen OBrien
        email                : karen@flo-2d.com
        git sha              : $Format:%H$
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
 This script initializes the plugin, making it known to QGIS.
"""


# noinspection PyPep8Naming
def classFactory(iface):  # pylint: disable=invalid-name
    """Load FLO-2D Rasterizor class from file FLO-2D Rasterizor.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from .rasterizor import Rasterizor
    return Rasterizor(iface)
