import inspect
import os
import posixpath 


from PySide import QtGui
from PySide import QtCore


from skinIO import skinUtils


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

