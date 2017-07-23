import maya.OpenMayaUI as OpenMayaUI
import maya.cmds 

import inspect
import os
import posixpath 

from PySide import QtGui
from PySide import QtCore
from shiboken import wrapInstance

from skinIO import skinUtils
reload(skinUtils)


class mayaTool(QtGui.QMainWindow):
    def __init__(self,
                 title):
        super(mayaTool, self).__init__(self.getMainWindow())

        windowName = '{}_windowTool'.format(title.replace(' ', ''))

        self.removePreviousWindow(windowName)

        self.setWindowTitle(title)
        self.setObjectName(windowName)

    def removePreviousWindow(self,
                             windowName):
        widgetLink = OpenMayaUI.MQtUtil.findControl(windowName)

        if widgetLink is not None:
            guiFullName = OpenMayaUI.MQtUtil.fullName(long(widgetLink))
            maya.cmds.deleteUI(guiFullName)

    def getMainWindow(self):
        """
            Return the Maya main window widget as a Python object
         
            return: Maya Main Window.
        """
        mainWindowPtr = OpenMayaUI.MQtUtil.mainWindow()

        return wrapInstance(long(mainWindowPtr), 
                            QtGui.QWidget)


class SkinImportWidget(QtGui.QWidget):
    def __init__(self,
                 toolbox):
        self.toolbox = toolbox

        self.width = 640

        self.skinManager = skinUtils.SkinIO()

        self.exposeWeightDetails = False

        super(SkinImportWidget, self).__init__()

        self.setupUi()

    def setupUi(self):
        self.mainFrame = QtGui.QWidget()
        self.mainLayout = QtGui.QVBoxLayout()
        self.mainLayout.setContentsMargins(5, 5, 5, 5)

        importButton = QtGui.QPushButton('Load weights')
        importButton.setMinimumHeight(32)
        importButton.setMinimumWidth(self.width)

        self._createWeightFileControls()

        self.reportWidget = QtGui.QTextEdit(self)

        self.mainLayout.addWidget(importButton)

        self.mainLayout.addWidget(self.reportWidget)

        self.setLayout(self.mainLayout)

        importButton.clicked.connect(self._loadWeights)

    def _createWeightFileControls(self):
        self.weightSourcePath = QtGui.QLineEdit(self)

        weightPathWidget = QtGui.QGroupBox("Input weights file:")
        pickButton = QtGui.QPushButton('')
        layout = QtGui.QHBoxLayout()

        layout.setContentsMargins(5, 0, 5, 5)
        layout.setSpacing(5)

        pickButton.setMaximumHeight(20)
        pickButton.setMaximumWidth(20)

        self._setIcon(pickButton,
                      'folder.png')

        layout.addWidget(self.weightSourcePath)
        layout.addWidget(pickButton)

        weightPathWidget.setLayout(layout)

        self.mainLayout.addWidget(weightPathWidget)

        pickButton.clicked.connect(self._pickOutputfile)

    def _pickOutputfile(self):
        targetFile, pathFilter = QtGui.QFileDialog.getOpenFileName(caption="Please choose your input weights file",filter="*.zip" )

        self.weightSourcePath.setText(targetFile)

    def _setIcon(self,
                 button,
                 iconName):
        icon = QtGui.QIcon()

        currentDirectory = os.path.dirname(inspect.getfile(self.__init__))
        imagePath = posixpath.join(os.path.dirname(currentDirectory),
                                   'Icons',
                                   iconName)
        imagePath = imagePath.replace('\\', '/')

        icon.addPixmap(QtGui.QPixmap(imagePath))
        button.setIcon(icon)

    def _loadWeights(self):
        self.reportWidget.setText('')

        outputPath = str(self.weightSourcePath.text())
        if len(outputPath)==0:
            return

        self.skinManager.importAssetWeights(outputPath,
                                            exposeWeightDetails=self.exposeWeightDetails)

        report = self.skinManager.skinProcessor.batchProcessing.report
        
        self.reportWidget.setText(report)


class SkinExportWidget(QtGui.QWidget):
    def __init__(self,
                 toolbox):
        self.toolbox = toolbox

        self.skinManager = skinUtils.SkinIO()

        self.exposeWeightDetails = False

        self.width = 640

        super(SkinExportWidget, self).__init__()

        self.setupUi()

    def setupUi(self):
        self.mainLayout = QtGui.QVBoxLayout()
        self.mainLayout.setContentsMargins(5, 5, 5, 5)

        exportButton = QtGui.QPushButton('Save weights')
        exportButton.setMinimumHeight(32)
        exportButton.setMinimumWidth(self.width)

        self._createWeightFileControls()

        self.reportWidget = QtGui.QTextEdit(self)

        self.mainLayout.addWidget(self._createInjectionWidget())

        self.mainLayout.addWidget(exportButton)

        self.mainLayout.addWidget(self.reportWidget)

        self.setLayout(self.mainLayout)

        exportButton.clicked.connect(self._saveSelectedObjectWeights)

    def _createInjectionWidget(self):
        injectionWidget = QtGui.QGroupBox('')

        layout = QtGui.QHBoxLayout()
        layout.setContentsMargins(10, 5, 5, 5)

        self.injectionModeComboBox = QtGui.QComboBox(self)
        self.injectionModeComboBox.setMinimumWidth(540)
        injectionModel = QtGui.QStringListModel()

        injectionModel.setStringList(list(skinUtils.SkinIO.SKIN_PROCESSING_METHOD))
        self.injectionModeComboBox.setModel(injectionModel)
        self.injectionModeComboBox.setCurrentIndex(0)

        layout.addWidget(QtGui.QLabel('Injection Mode:'))
        layout.addWidget(self.injectionModeComboBox)

        injectionWidget.setLayout(layout)
        return injectionWidget

    def _createWeightFileControls(self):
        self.weightTargetPath = QtGui.QLineEdit(self)

        weightPathWidget = QtGui.QGroupBox("Output weights file:")
        pickButton = QtGui.QPushButton('')
        layout = QtGui.QHBoxLayout()

        layout.setContentsMargins(5, 0, 5, 5)
        layout.setSpacing(5)

        pickButton.setMaximumHeight(20)
        pickButton.setMaximumWidth(20)

        self._setIcon(pickButton,
                      'folder.png')

        layout.addWidget(self.weightTargetPath)
        layout.addWidget(pickButton)

        weightPathWidget.setLayout(layout)

        self.mainLayout.addWidget(weightPathWidget)

        pickButton.clicked.connect(self._pickOutputfile)

    def _pickOutputfile(self):
        targetFile, pathFilter = QtGui.QFileDialog.getSaveFileName(caption="Please choose your target path for your weights",filter="*.zip" )

        self.weightTargetPath.setText(targetFile)        #QtGui.QFileDialog.getOpenFileName()

    def _setIcon(self,
                 button,
                 iconName):
        icon = QtGui.QIcon()

        currentDirectory = os.path.dirname(inspect.getfile(self.__init__))
        imagePath = posixpath.join(os.path.dirname(currentDirectory),
                                   'Icons',
                                   iconName)
        imagePath = imagePath.replace('\\', '/')

        icon.addPixmap(QtGui.QPixmap(imagePath))
        button.setIcon(icon)

    def _saveSelectedObjectWeights(self):
        self.reportWidget.setText('')

        outputPath = str(self.weightTargetPath.text())
        if len(outputPath)==0:
            return

        self.skinManager.skinHandler = str(self.injectionModeComboBox.currentText())
        self.skinManager.exportAssetWeights(maya.cmds.ls(sl=True),
                                            outputPath,
                                            exposeWeightDetails=self.exposeWeightDetails)

        report = self.skinManager.skinProcessor.batchProcessing.report
        
        self.reportWidget.setText(report)


class SkinTool(mayaTool):
    def __init__(self):
        self.width = 680

        super(SkinTool, self).__init__('Skin Tool')

        self.setupUi()

    def setupUi(self):
        self.mainFrame = QtGui.QWidget()
        self.mainLayout = QtGui.QVBoxLayout()

        self.exporterWidget = SkinExportWidget(self)
        
        self.importerWidget = SkinImportWidget(self)

        self.tabWidget = QtGui.QTabWidget()

        self.tabWidget.addTab(self.exporterWidget, "Export")

        self.tabWidget.addTab(self.importerWidget, 'Import')

        self.mainLayout.addWidget(self.tabWidget)

        self.mainFrame.setLayout(self.mainLayout)
        self.setCentralWidget(self.mainFrame)


def Run():
    skinUI = SkinTool()

    skinUI.show()