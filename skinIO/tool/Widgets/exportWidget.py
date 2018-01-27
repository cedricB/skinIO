import inspect
import os
import posixpath 


from PySide import QtGui
from PySide import QtCore


from skinIO import skinUtils


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

