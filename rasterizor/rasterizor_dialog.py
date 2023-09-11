# -*- coding: utf-8 -*-
"""
/***************************************************************************
 FLO-2DRasterizorDialog
                                 A QGIS plugin
 A plugin to rasterize general FLO-2D ouptut files.
 Generated by Plugin Builder: https://github.com/FLO-2DKaren/FLO-2D-Rasterizor.git
                             -------------------
        begin                : 2023-04-10
        git sha              : $Format:%H$
        copyright            : (C) 2023 by Karen O'Brien
        email                : karen@flo-2d.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

import os

from qgis.PyQt import uic
from qgis.PyQt import QtWidgets

# This loads your .ui file so that PyQt can populate your plugin with the elements from Qt Designer
FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'rasterizor_dialog_base.ui'))


class RasterizorDialog(QtWidgets.QDialog, FORM_CLASS):
    def __init__(self, parent=None):
        """Constructor."""
        super(RasterizorDialog, self).__init__(parent)
        # Set up the user interface from Designer through FORM_CLASS.
        # After self.setupUi() you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)
        self.populateComboBox()
    def populateComboBox(self):
        self.style_cbo.clear()
        style_list = ["Depth", "Velocity", "Elevation", "Time", "Flow"]
        self.style_cbo.addItems(style_list)