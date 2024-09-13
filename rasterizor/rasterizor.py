# -*- coding: utf-8 -*-
"""
/***************************************************************************
 FLO-2D Rasterizor
                                 A QGIS plugin
 A plugin to rasterize general FLO-2D output files.
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
import numpy as np
from qgis.core import *
from qgis.utils import iface
from qgis.PyQt.QtCore import Qt, QSettings, QTranslator, QCoreApplication
from qgis.PyQt.QtGui import QIcon, QColor
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
from qgis._core import (QgsGradientColorRamp, QgsGradientStop)
# from rast_functions import outTable
# Initialize Qt resources from file resources.py
from .resources import *
# Import the code for the dialog
from .rasterizor_dialog import RasterizorDialog
import os.path
from osgeo import gdal

import processing

class Rasterizor:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """

        self.cellSize = 30
        self.dlg = RasterizorDialog()
        self.dlg.setWindowFlags(Qt.WindowStaysOnTopHint)
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
        self.crs = QgsCoordinateReferenceSystem(QgsProject.instance().crs().authid())
        self.dlg.crsselector.setCrs(self.crs)
        self.dlg.crsselector_2.setCrs(self.crs)

        # Run button
        self.dlg.runButton.clicked.connect(self.run)
        self.dlg.runButton_2.clicked.connect(self.run_comparison)

        # Close button
        self.dlg.cancelButton.clicked.connect(self.closeDialog)
        self.dlg.cancelButton_2.clicked.connect(self.closeDialog)

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
        """Shows the dialog"""
        self.crs = QgsCoordinateReferenceSystem(QgsProject.instance().crs().authid())
        self.dlg.crsselector.setCrs(self.crs)
        self.dlg.crsselector_2.setCrs(self.crs)
        self.dlg.show()

    # Adapted function from dlg_sampling_xyz_.py
    def lidar_to_raster(self, lidar_file, raster_file, nodata_value=-9999):
        """
        Function to sample an ascii text file for x y z data into a numpy array and 
        build a raster.
        """
        # Open the file and read the lines
        self.dlg.plainTextEdit.appendPlainText("Reading data...")

        values = []
        cellSize_data = []

        with open(lidar_file, "r") as file:
            for line in file:
                line = line.strip()
                fields = line.split()
                if fields[0].isnumeric():
                    cell, x, y, value = (
                        float(fields[0]),
                        float(fields[1]),
                        float(fields[2]),
                        float(fields[3]),
                    )
                    values.append((x, y, value))
                    if len(cellSize_data) < 2:
                        cellSize_data.append((x, y))

        # Calculate the differences in X and Y coordinates
        dx = abs(cellSize_data[1][0] - cellSize_data[0][0])
        dy = abs(cellSize_data[1][1] - cellSize_data[0][1])

        # If the coordinate difference is equal 0, assign a huge number
        if dx == 0:
            dx = 9999
        if dy == 0:
            dy = 9999

        self.cellSize = min(dx, dy)

        # Get the extent and number of rows and columns
        min_x = min(point[0] for point in values)
        max_x = max(point[0] for point in values)
        min_y = min(point[1] for point in values)
        max_y = max(point[1] for point in values)
        num_cols = int((max_x - min_x) / self.cellSize) + 1
        num_rows = int((max_y - min_y) / self.cellSize) + 1

        # Convert the list of values to an array.
        raster_data = np.full((num_rows, num_cols), -9999, dtype=np.float32)
        for point in values:
            col = int((point[0] - min_x) / self.cellSize)
            row = int((max_y - point[1]) / self.cellSize)
            raster_data[row, col] = point[2]

        # Initialize the raster
        driver = gdal.GetDriverByName("GTiff")
        raster = driver.Create(raster_file, num_cols, num_rows, 1, gdal.GDT_Float32)
        raster.SetGeoTransform(
            (
                min_x - self.cellSize / 2,
                self.cellSize,
                0,
                max_y + self.cellSize / 2,
                0,
                -self.cellSize,
            )
        )
        raster.SetProjection(self.crs.toWkt())

        band = raster.GetRasterBand(1)
        band.SetNoDataValue(nodata_value)  # Set a no-data value if needed
        band.WriteArray(raster_data)

        raster.FlushCache()


    def setStyle(self, layer, style):
        """Function to set the styles"""

        provider = layer.dataProvider()
        extent = layer.extent()
        myRasterShader = QgsRasterShader()

        stats = provider.bandStatistics(1, QgsRasterBandStats.All, extent, 0)
        if stats.minimumValue <= 0.01:
            min = 0.01
        else:
            min = stats.minimumValue

        max = stats.maximumValue
        range = max - min
        add = range / 2
        interval = min + add
        valueList = [min, interval, max]
    
        colDic = {
            'white': '#ffffff',
            'lightblue': '#add8e6',
            'blue': '#0000ff',
            'green': '#008000',
            'palegreen': '#98FB98',
            'black': '#000000',
            'grey': '#808080',
            'red': '#FF0000',
            'yellow': '#FFFF00',
        }

        # Flood maps
        if style == 0:
            color_list = [QColor(colDic["white"]), QColor(colDic["lightblue"]), QColor(colDic["blue"])]
            self.set_renderer(layer, color_list, myRasterShader, min, max)

        # Velocity maps
        elif style == 1:
            color_list = [QColor(colDic["white"]), QColor(colDic["palegreen"]), QColor(colDic["green"])]
            self.set_renderer(layer, color_list, myRasterShader, min, max)

        # Elevation maps
        elif style == 2:
            color_list = [QColor(colDic["black"]), QColor(colDic["grey"]), QColor(colDic["white"])]
            self.set_renderer(layer, color_list, myRasterShader, min, max)

        # Time maps
        elif style == 3:
            color_list = [QColor(colDic["green"]), QColor(colDic["yellow"]), QColor(colDic["red"])]
            self.set_renderer(layer, color_list, myRasterShader, min, max)

        # Flow maps
        elif style == 4:
            color_list = [QColor(colDic["white"]), QColor(colDic["lightblue"]), QColor(colDic["blue"])]
            self.set_renderer(layer, color_list, myRasterShader, min, max)

        # Difference map
        elif style == 5:

            min = stats.minimumValue

            range_distance = max - min
            zero_position = 0 - min
            normalized_position = zero_position / range_distance

            color_ramp = QgsGradientColorRamp(
                QColor(QColor(colDic["blue"])),
                QColor(QColor(colDic["red"])),
                discrete=False, stops=[
                    QgsGradientStop(normalized_position, QColor(colDic["green"])),
                ])

            myPseudoRenderer = QgsSingleBandPseudoColorRenderer(
                layer.dataProvider(), layer.type(), myRasterShader
            )

            myPseudoRenderer.setClassificationMin(min)
            myPseudoRenderer.setClassificationMax(max)
            myPseudoRenderer.createShader(color_ramp)

            layer.setRenderer(myPseudoRenderer)

        layer.triggerRepaint()

    def run(self):

        # # Create the dialog with elements (after translation) and keep reference
        # # Only create GUI ONCE in callback, so that it will only load when the plugin is started

        # file path
        filePath = self.dlg.readfile.filePath()
        # output directory
        outputPath = self.dlg.outputFile.filePath()

        if filePath == "":
            QMessageBox.information(None, "Error", "Please, select a file, output directory and/or cell size!")
            return

        if outputPath == "":
            outputPath = QgsProcessingUtils.tempFolder()

        # Read the file and adjust the slashes
        fn = filePath.replace(os.sep, '/')
        layername = self.dlg.lineEdit_layerName.text()
        # create the output file
        raster_file = outputPath + "/" + layername + ".tif"
        # Verify if the layer exists, if so delete it

        for layer in QgsProject.instance().mapLayers().values():
            if layer.name() == self.dlg.lineEdit_layerName.text():
                QgsProject.instance().removeMapLayers([layer.id()])
                # Run the function
        self.lidar_to_raster(fn, raster_file)
        # Add to map
        self.iface.addRasterLayer(raster_file, layername)
        active_layer = iface.activeLayer()
        style = self.dlg.style_cbo.currentIndex()
        self.setStyle(active_layer, style)
        self.dlg.plainTextEdit.appendPlainText("Process complete!")

    def run_comparison(self):
        """
        Function to run the comparison between two rasters
        """
        raster_1 = self.dlg.readFile_1.currentLayer()
        raster_2 = self.dlg.readFile_2.currentLayer()

        outputPath = self.dlg.outputFile_2.filePath()

        layername = self.dlg.lineEdit_layerName_2.text()

        if raster_1 == "" or raster_2 == "" or layername == "":
            QMessageBox.information(None, "Error", "Please, select two valid rasters and layer name!")
            return

        if outputPath == "":
            outputPath = QgsProcessingUtils.tempFolder()

        # create the output file
        raster_file = outputPath + "/" + layername + ".tif"
        # Verify if the layer exists, if so delete it
        for layer in QgsProject.instance().mapLayers().values():
            if layer.name() == self.dlg.lineEdit_layerName_2.text():
                QgsProject.instance().removeMapLayers([layer.id()])

        # Run the function
        # raster_difference = self.raster_comparison(raster_1, raster_2)
        raster_difference = self.raster_comparison(raster_1, raster_2, raster_file, layername)
        # Add to map
        QgsProject.instance().addMapLayer(raster_difference)
        active_layer = iface.activeLayer()
        self.setStyle(active_layer, 5)
        self.dlg.plainTextEdit_2.appendPlainText("Process complete!")

    def raster_comparison(self, raster_1, raster_2, raster_file, layer_name):
        """
        Function to compare two rasters and return a difference raster layer
        """

        expression = f'"{raster_1.name()}@1" - "{raster_2.name()}@1"'
        QgsMessageLog.logMessage(expression)

        difference = processing.run(
            "qgis:rastercalculator",
            {
                "EXPRESSION": expression,
                "LAYERS": [raster_1],
                "CELLSIZE": 0,
                "EXTENT": None,
                "CRS": self.crs,
                "OUTPUT": raster_file,
            },
        )["OUTPUT"]

        return QgsRasterLayer(difference, layer_name)

    def set_renderer(self, layer, color_list, raster_shader, min, max):
        """
        Function to set the render to layer
        """""
        # Three colors -> all layers
        color_ramp = QgsGradientColorRamp(
            QColor(color_list[0]),
            QColor(color_list[2]),
            discrete=False, stops=[
                QgsGradientStop(0.5, QColor(color_list[1])),
            ])

        myPseudoRenderer = QgsSingleBandPseudoColorRenderer(
            layer.dataProvider(), layer.type(), raster_shader
        )

        myPseudoRenderer.setClassificationMin(min)
        myPseudoRenderer.setClassificationMax(max)
        myPseudoRenderer.createShader(color_ramp, clip=True)

        layer.setRenderer(myPseudoRenderer)

