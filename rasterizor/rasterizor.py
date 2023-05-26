# -*- coding: utf-8 -*-
"""
/***************************************************************************
 FLO-2D Rasterizor
                                 A QGIS plugin
 A plugin to rasterize general FLO-2D ouptut files.
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                              -------------------
        begin                : 2023-04-10
        git sha              : $Format:%H$
        copyright            : (C) 2023 by Karen OBrien
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
import shutil
import pandas as pd
import numpy as np
import time
from numpy import savetxt
from qgis.core import (
    Qgis,
    QgsMessageLog,
    QgsCoordinateReferenceSystem,
    QgsProject
)
from qgis.utils import iface
from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import (
    QAction,
    QWidget,
    QSizePolicy,
    QPushButton,
    QDialog,
    QGridLayout,
    QDialogButtonBox,
    QMessageBox
)
# from rast_functions import outTable

# Initialize Qt resources from file resources.py
from . import xyz2tif
from .resources import *
# Import the code for the dialog
from .rasterizor_dialog import RasterizorDialog
import os.path
from qgis import processing
from rasterio import transform as riotrans
import rasterio as rio
from rasterio.merge import merge as rmerge
from rasterio.transform import from_origin

class Rasterizor:
    """QGIS Plugin Implementation."""

    

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        
        
        self.dlg = RasterizorDialog()
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'FLO-2DRasterizor_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)
            QCoreApplication.installTranslator(self.translator)

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&FLO-2D Rasterizor')

        # Check if plugin was started the first time in current QGIS session
        # Must be set in initGui() to survive plugin reloads
        self.first_start = None
        
        # Set the CRS to the widget
        self.crs = QgsCoordinateReferenceSystem("EPSG:4326")
        self.dlg.crsselector.setCrs(self.crs)
        
        # Run button
        self.dlg.runButton.clicked.connect(self.run)
        
        # Close button
        self.dlg.cancelButton.clicked.connect(self.closeDialog)     

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('FLO-2DRasterizor', message)


    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            # Adds plugin icon to Plugins toolbar
            self.iface.addToolBarIcon(action)

        if add_to_menu:
            self.iface.addPluginToMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""
        icon_path = ':/plugins/rasterizor/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'FLO-2D Rasterizor'),
            callback=self.open,
            parent=self.iface.mainWindow())

        # will be set False in run()
        self.first_start = True


    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&FLO-2D Rasterizor'),
                action)
            self.iface.removeToolBarIcon(action)
            
    # Closing the dialog
    def closeDialog(self):
        self.dlg.close()

    # Opening the dialog
    def open(self):
        self.dlg.show()
            
    # Adapted function from dlg_sampling_xyz_.py
    def lidar_to_raster(self, lidar_file, raster_file, cell_size, nodata_value=-9999):
        
        # Open the file and read the lines
        self.dlg.plainTextEdit.appendPlainText("Reading data...")
        with open(lidar_file, "r") as f:
            lines = f.readlines()

        x_coords = []
        y_coords = []
        z_values = []

        # Get the coordinates
        self.dlg.plainTextEdit.appendPlainText("Getting coordinates...")
        for line in lines:
            line = line.strip()
            if line:
                _, x, y, z = line.split()
                x_coords.append(float(x))
                y_coords.append(float(y))
                z_values.append(float(z))

        min_x = min(x_coords)
        max_y = max(y_coords)
        num_cols = int((max(x_coords) - min_x) / cell_size) + 1
        num_rows = int((max(y_coords) - min(y_coords)) / cell_size) + 1
        
        transform = from_origin(min_x - cell_size / 2, max_y + cell_size / 2, cell_size, cell_size)

        raster_data = np.full((num_rows, num_cols), nodata_value, dtype=np.float32)

        for x, y, z in zip(x_coords, y_coords, z_values):
            col = int((x - min_x) / cell_size )
            row = int((max_y - y) / cell_size )
            raster_data[row, col] = z


        self.dlg.plainTextEdit.appendPlainText("Creating raster...")
        with rio.open(
            raster_file,
            "w",
            driver="GTiff",
            height=num_rows,
            width=num_cols,
            count=1,
            dtype=raster_data.dtype,
            nodata=nodata_value,
            crs=self.dlg.crsselector.crs().authid(),
            transform=transform,
            compress='lzw'
        ) as dst:
            dst.write(raster_data, 1)
                        
    def run(self):

        # # Create the dialog with elements (after translation) and keep reference
        # # Only create GUI ONCE in callback, so that it will only load when the plugin is started

        # file path
        filePath = self.dlg.readfile.filePath()
        # output directory
        outputPath = self.dlg.outputFile.filePath()
        # cell size (allowing only float number)
        cellSize = self.dlg.cellSize.text()
        try:
            cellSize = float(cellSize)
        except Exception:
            QMessageBox.information(None, 'Error','Cell size can only be a number')
            return
        
        if filePath == "" or outputPath =="" or cellSize =="":
            QMessageBox.information(None, "Error", "Please, select a file, output directory and/or cell size!") 
        else:
            
            # Read the file and adjust the slashes
            fn = filePath.replace(os.sep, '/')
            # create the output file
            raster_file = outputPath + "\output.tif"
            # Verify if the layer exists, if so delete it
            for layer in QgsProject.instance().mapLayers().values():
                if layer.name()=="FLO-2D-Rasterizor":
                     QgsProject.instance().removeMapLayers( [layer.id()] )     
            # Run the function
            self.lidar_to_raster(fn, raster_file, cellSize)
            # Add to map

            self.iface.addRasterLayer(raster_file,"FLO-2D-Rasterizor")
            self.dlg.plainTextEdit.appendPlainText("Process complete!")
                                
            
