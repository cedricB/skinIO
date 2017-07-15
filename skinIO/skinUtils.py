"""
    MIT License

    L I C E N S E:
        Copyright (c) 2014-2017 Cedric BAZILLOU All rights reserved.

    Permission is hereby granted, free of charge, to any person obtaining a copy of this software 
    and associated documentation files (the "Software"), to deal in the Software without restriction,
    including without limitation the rights to use, copy, modify, merge, publish, distribute,
    sublicense, and/or sell copies of the Software,and to permit persons to whom the Software 
    is furnished to do so, subject to the following conditions:

    The above copyright notice and this permission notice shall be included in all copies 
    or substantial portions of the Software.

    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, 
    INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, 
    FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT 
    HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, 
    TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
    DEALINGS IN THE SOFTWARE.

    https://opensource.org/licenses/MIT
"""


import maya.OpenMaya 
import maya.OpenMayaAnim 
import maya.OpenMayaUI
import maya.cmds 
import maya.mel

import inspect
import json
import os
import posixpath 
import tempfile
import time
import shutil
import uuid
import zipfile


from skinIO import context
from skinIO import settings
from skinIO import validation

reload(context)
reload(settings)
reload(validation)

__version__ = '0.38.6'


class Omphallos(object):
    def __init__(self):
        self.repository = None

    def collectOriginShape(self, 
                           targetName, 
                           targetShapeFile):
        """
            This method will package all shape under a root transform in an alembic file.
            ( Origin shapes used by deformers specifically )

            args:
                targetName(string): root name used to collect all shape data.

                targetShapeFile(file path): alembic file path
        """
        shapeArray = maya.cmds.ls(intermediateObjects=True, 
                                  geometry=True)

        self.repository = maya.cmds.createNode('transform', n=targetName)
        maya.cmds.addAttr(self.repository, ln='shapePaths', dt='stringArray')

        shapePathArray = []

        for shape in shapeArray:
            shapePath = str(maya.cmds.ls(shape, long=True)[0])
            isNotEmpty = maya.cmds.polyEvaluate(shapePath, v=True)

            if isNotEmpty == 0:
                continue

            shapePathArray.append(shapePath)
            maya.cmds.parent(shape, self.repository, add=True, shape=True)

        maya.cmds.setAttr(self.repository+'.shapePaths',
                          len(shapePathArray),
                          *(shapePathArray),
                          type='stringArray')

        duplicateSet = maya.cmds.duplicate(self.repository)
        maya.cmds.delete(self.repository)

        self.repository = maya.cmds.rename(duplicateSet, targetName)

        exportList =  maya.cmds.listRelatives(self.repository,
                                              s=True,
                                              fullPath=True)

        for shape in exportList:
            maya.cmds.setAttr(shape+'.intermediateObject', 0)

        ffdComponents = maya.cmds.lattice(self.repository, 
                                          divisions=[2, 2, 2], 
                                          objectCentered=False,
                                          ldv=[2, 2, 2],
                                          n='{}_Ffd1'.format(self.repository))

        maya.cmds.setAttr(ffdComponents[0]+'.outsideLattice', 1)

        maya.cmds.setKeyframe(ffdComponents[1]+".tz", v=0.0, t=1)
        maya.cmds.setKeyframe(ffdComponents[1]+".tz", v=1.0, t=2)

        exportCommand = "-fr 1 2 -root |{node} -u {attribute} -file {targetFile}"
        exportCommand = exportCommand.format(node=self.repository,
                                             attribute='shapePaths',
                                             targetFile=targetShapeFile)

        maya.cmds.AbcExport(verbose=True, j=exportCommand)
        maya.cmds.delete(self.repository, ch=True)
        maya.cmds.delete(self.repository)

        self.repository = maya.cmds.createNode('transform', n=targetName)

        importCommand = 'AbcImport -crt -ct "|{shape}"  "{inputFile}";'
        importCommand = importCommand.format(shape=targetName,
                                             inputFile=targetShapeFile)

        self.alembicNode = maya.mel.eval(importCommand)

        maya.cmds.disconnectAttr('time1.outTime', '{}.time'.format(self.alembicNode))
        maya.cmds.setAttr('{}.time'.format(self.alembicNode), 1)

        for shapeIndex, shape in enumerate(shapePathArray):
            outputGroupPart = maya.cmds.listConnections('{0}.worldMesh[0]'.format(shape))[0]

            maya.cmds.connectAttr('{0}.outPolyMesh[{1}]'.format(self.alembicNode, shapeIndex),
                                  '{0}.inputGeometry'.format(outputGroupPart),
                                  f=True)

            maya.cmds.delete(shapePathArray[shapeIndex])

        maya.cmds.delete(self.repository)

    def collectShape(self, 
                     shapeArray,
                     targetName, 
                     targetShapeFile):
        """
            This store shape data from the provided shapeArray to an alembic file.

            args:
                shapeArray(array of shape name(string)).

                targetName(string): root name used to collect all shape data.

                targetShapeFile(file path): alembic file path
        """
        self.repository = maya.cmds.createNode('transform', n=targetName)
        maya.cmds.addAttr(self.repository, ln='shapePaths', dt='stringArray')

        shapePathArray = []

        for shape in shapeArray:
            shapePath = str(maya.cmds.ls(shape, long=True)[0])
            isNotEmpty = maya.cmds.polyEvaluate(shapePath, v=True)

            if isNotEmpty == 0:
                continue

            shapePathArray.append(shapePath)
            maya.cmds.parent(shape, self.repository, add=True, shape=True)

        maya.cmds.setAttr(self.repository+'.shapePaths',
                          len(shapePathArray),
                          *(shapePathArray),
                          type='stringArray')

        duplicateSet = maya.cmds.duplicate(self.repository)
        maya.cmds.delete(self.repository)

        self.repository = maya.cmds.rename(duplicateSet, targetName)

        exportList =  maya.cmds.listRelatives(self.repository,
                                              s=True,
                                              fullPath=True)

        for shape in exportList:
            maya.cmds.setAttr(shape+'.intermediateObject', 0)

        ffdComponents = maya.cmds.lattice(self.repository, 
                                          divisions=[2, 2, 2], 
                                          objectCentered=False,
                                          ldv=[2, 2, 2],
                                          n='{}_Ffd1'.format(self.repository))

        maya.cmds.setAttr(ffdComponents[0]+'.outsideLattice', 1)

        maya.cmds.setKeyframe(ffdComponents[1]+".tz", v=0.0, t=1)
        maya.cmds.setKeyframe(ffdComponents[1]+".tz", v=1.0, t=2)

        exportCommand = "-fr 1 2 -root |{node} -u {attribute} -file {targetFile}"
        exportCommand = exportCommand.format(node=self.repository,
                                             attribute='shapePaths',
                                             targetFile=targetShapeFile)

        maya.cmds.AbcExport(verbose=True, j=exportCommand)

        maya.cmds.delete(self.repository, ch=True)
        maya.cmds.delete(self.repository)

        self.repository = maya.cmds.createNode('transform', n=targetName)

        importCommand = 'AbcImport -crt -ct "|{shape}"  "{inputFile}";'
        importCommand = importCommand.format(shape=targetName,
                                             inputFile=targetShapeFile)

        self.alembicNode = maya.mel.eval(importCommand)

        maya.cmds.disconnectAttr('time1.outTime', '{}.time'.format(self.alembicNode))
        maya.cmds.setAttr('{}.time'.format(self.alembicNode), 1)

        for shapeIndex, shape in enumerate(shapePathArray):
            maya.cmds.connectAttr('{0}.outPolyMesh[{1}]'.format(self.alembicNode,
                                                                shapeIndex),
                                  '{0}.inMesh'.format(shape),
                                  f=True)

        maya.cmds.delete(self.repository)


class PointWeights(object):
    def __init__(self):
        self.timeProcessing = context.TimeProcessor()

    def importWeights(self, inputMesh):
        pass

    def getWeights(self, 
                   inputMesh, 
                   skinSettings,
                   shapeSettings):
        for pointIndex in xrange(shapeSettings.pointCount):
            component = self.getComponent(pointIndex, shapeSettings)

            rawWeights = maya.cmds.skinPercent(component,
                                               skinSettings.skinDeformer,
                                               q=True,
                                               value=True)

            return {weightIndex:weight \
                    for weightIndex, weight \
                    in enumerate(rawWeights) if weight > 0.0}

    def saveWeights(self,
                    inputMesh, 
                    targetDirectory):
        targetFile = os.path.join(targetDirectory, '{0}.wgt'.format(inputMesh))

        skinNode = maya.mel.eval('findRelatedSkinCluster {}'.format(inputMesh))
        if skinNode is None:
            return

        skinSettings = settings.SkinSettings(skinNode)
        shapeSettings = settings.ShapeSettings(skinSettings.shape)

        with open(targetFile, 'w') as skinFile:
            for pointIndex in xrange(shapeSettings.pointCount):
                skinData = self.getWeights(inputMesh, 
                                           skinSettings,
                                           shapeSettings)

                skinFile.write(skinData)


class DataInjection(object):
    TARGET_WEIGHT_PROPERTY = 'skinRepository'

    WEIGHT_HOLDER_TYPE = 'joint'

    WEIGHT_PROPERTY_TYPE = 'doubleArray'

    WEIGHT_NAMESPACE = 'skinNamespace_weights'

    def __init__(self):
        self.timeProcessing = context.TimeProcessor()

        self.batchProcessing = context.TimeProcessor()

        self.processingTime = 0

        self.reportArray = []

        self.reporter = validation.SkinReport()

        self.skinNodeArray = []

        self.sceneWeights = []

        self.skinMetadata = {}

        self.mayaFileType = "mayaAscii"

    def getSkinNodeArray(self,
                         objectArray):
        """
            Validate skinclusters influencing a list of transform
            (specifically their shapes). 

            args:
                objectArray(list of transform names influenced by a skincluster).
        """
        self.skinNodeArray = []

        for inputTransform in objectArray:
            validationUtils = validation.SkinValidator()
            inputSkinNodes = validationUtils.getSkinHistory(inputTransform)

            if len(inputSkinNodes) == 0:
                continue

            self.skinNodeArray.append(inputSkinNodes[0])

    def saveSettings(self, 
                     targetArchiveFile,
                     unpackDirectory,
                     outputSkinSettings):
        """
            Save the current skin dictionary to a json file

            args:
                targetArchiveFile(output archive zip file path(string))

                outputSkinSettings(dict)

            returns:
                jsonSkinFile, jsonSkinFileName (file path(string))
        """
        jsonSkinFileExtention = os.path.splitext(targetArchiveFile)[1]

        jsonSkinFileName = os.path.basename(targetArchiveFile).replace(jsonSkinFileExtention, '.json')
        jsonSkinFile = posixpath.join(unpackDirectory,
                                    jsonSkinFileName)

        with open(jsonSkinFile, "w") as outfile:
            json.dump(outputSkinSettings, outfile , indent=4)

        return jsonSkinFile, jsonSkinFileName

    def bundleSkinComponentsInArchiveFile(self,
                                          sceneWeights,
                                          jsonSkinFile,
                                          jsonSkinFileName,
                                          targetArchiveFile):
        """
            Bind together skin data and their json skin settings
            into an output zip archive.

            args:
                sceneWeights(list of SkinSettings).
                (mostly relevant for their skinData path)

                jsonSkinFile(string):json file path.
                jsonSkinFileName(string): filename of jsonSkinFile.

                targetArchiveFile(file name (string)): file path for the skin Zip file

            returns:
                jsonSkinFile, jsonSkinFileName (file path(string))
        """
        with zipfile.ZipFile(targetArchiveFile, 
                             'w', 
                             compression=zipfile.ZIP_DEFLATED) as outputZip:
            outputZip.write(jsonSkinFile, r'{0}'.format(jsonSkinFileName))

            for component in sceneWeights:
                zipName = os.path.basename(component.abcWeightsFile)
                outputZip.write(component.abcWeightsFile, r'%s'%zipName)

    def transferToDisk(self, 
                       skin, 
                       targetSkinFile):
        """
            Export data for the provided skincluster .

            args:
                skin(string):Name of the skinCluster to save.

                targetSkinFile(string):file path for the exported data.
        """
        self.timeProcessing.displayReport = False

        with self.timeProcessing:
            maya.cmds.select(skin, r=True)
            maya.cmds.file(targetSkinFile,
                           force=True, 
                           typ=self.mayaFileType,
                           es=True,
                           ch=False,
                           chn=False,
                           con=False, 
                           exp=False,
                           sh=False)

    def saveWeights(self,
                    skin,
                    targetSkinDirectory):
        """
            Prepare element for export procedure.

            args:
                skin(string):Name of the skinCluster to save.

                targetSkinDirectory(string):directory path for the exported data.
        """
        maya.cmds.select(skin, 
                         r=True)

        targetSkinFileName = '{0}_skinWeights.ma'.format(skin)

        targetSkinFile = posixpath.join(targetSkinDirectory,
                                        targetSkinFileName)

        self.transferToDisk(skin, 
                            targetSkinFile)

        return targetSkinFile

    def export(self,
               inputTransform,
               targetDirectory,
               displayReport=True):
        """
            Collect skin settings form a transform name.
            (specifically from its shape).

            args:
                inputTransform(string):Name of the transform with a shape deformed by a skincluster.

                targetDirectory(string):directory path for the exported data.

            kwargs:
                displayReport(bool). print time need to evaluate this operation.

            returns:
                (SkinSettings)
        """
        self.timeProcessing.report = ''

        self.timeProcessing.processObjectCount = 0

        validationUtils = validation.SkinValidator()
        inputSkinNodes = validationUtils.getSkinHistory(inputTransform)

        if len(inputSkinNodes) == 0:
            return None

        skinSettings = None

        skinSettings = settings.SkinSettings(inputSkinNodes[0])
        skinSettings.shape = maya.cmds.listRelatives(inputTransform,
                                                     s=True,
                                                     fullPath=True)[0]

        return skinSettings

    def collectSkinSettings(self,
                            objectArray,
                            unpackDirectory,
                            exposeWeightDetails):
        """
            Collect skin settings from a list of transform.
            (specifically from its shape).

            args:
                objectArray(list of string):Names of the transform with a shape deformed by a skincluster.

                unpackDirectory(string):directory path for the exported data.
        """
        for component in objectArray:
            targetSkinSettings = self.export(component,
                                             unpackDirectory,
                                             displayReport=False)

            if targetSkinSettings is None:
                continue

            self.sceneWeights.append(targetSkinSettings)

            self.processingTime += targetSkinSettings.processingTime

            if self.batchProcessing.displayProgressbar is True:
                self.batchProcessing.progressbar.advanceProgress(1)

            if exposeWeightDetails is True:
                if len(targetSkinSettings.report) ==0:
                    continue

                self.batchProcessing.report += targetSkinSettings.report.replace('\n', '\n\t\t')

                self.batchProcessing.report += '\n'

            targetSkinSettings.report = ''

            self.skinMetadata[targetSkinSettings.deformerName] = json.loads(targetSkinSettings.toJson())

    def packageDistribution(self,
                            targetSkinFile,
                            unpackDirectory):
        jsonSkinFile, jsonSkinFileName = self.saveSettings(targetSkinFile, 
                                                           unpackDirectory,
                                                           self.skinMetadata)

        self.bundleSkinComponentsInArchiveFile(self.sceneWeights,
                                               jsonSkinFile,
                                               jsonSkinFileName,
                                               targetSkinFile)

    def resetManager(self,
                     showProgressbar,
                     objectCount,
                     exposeWeightDetails):
        self.batchProcessing = context.TimeProcessor()
        self.batchProcessing.displayProgressbar = showProgressbar

        self.batchProcessing.progressbarRange = objectCount
        self.batchProcessing.displayReport = exposeWeightDetails

        self.batchProcessing.report = '\n<@{0}: Batch Processing report :>'.format(self.__class__.__name__) 

        self.sceneWeights = []

        self.skinMetadata = {}

    def collectAdditionalData(self, *args):
        self.batchProcessing.report += '\n\t Saving {} elements took {} seconds\n'.format(len(self.sceneWeights),
                                                                                          self.processingTime)

    def exportAssetWeights(self,
                           objectArray,
                           targetSkinFile,
                           exposeWeightDetails=True,
                           showProgressbar=True):
        if len(objectArray) == 0:
            return 'Object array is empty'

        targetDirectory = os.path.dirname(targetSkinFile)
 
        if not os.path.isdir(targetDirectory):
            return 'targetDirectory doesnt exists'

        self.resetManager(showProgressbar,
                          len(objectArray),
                          exposeWeightDetails)

        self.getSkinNodeArray(objectArray)

        pathSuffix = str(uuid.uuid1()).replace('-', '')
        neighbourFolder = posixpath.join(targetDirectory, 
                                         pathSuffix[0:len(pathSuffix)/4])

        if len(self.skinNodeArray) == 0:
            return 0.0

        with context.SelectionSaved(), context.TemporaryDirectory(dir=neighbourFolder) as unpackDirectory:
            with self.batchProcessing:
                self.collectSkinSettings(objectArray,
                                         unpackDirectory,
                                         exposeWeightDetails)
    
                self.collectAdditionalData(unpackDirectory)

            self.packageDistribution(targetSkinFile,
                                     unpackDirectory)

        return float(self.batchProcessing.timeRange)


class AsciiInjection(DataInjection):
    def __init__(self):
        super(AsciiInjection, self).__init__()

        self.mayaFileType = "mayaAscii"

    def importWeight(self, 
                     inputFile, 
                     archive, 
                     inputSkin):
        self.consolidateFile(archive, inputFile, inputSkin)
        #maya.cmds.select(inputSkin, r=True)
        maya.cmds.file("C:/Users/cedric/Desktop/skinIO/UU2.ma",
                       i=True, 
                       type="mayaAscii")
                           
    def importWeights(self,
                      sourceArchiveFile):
        if not os.path.exists(sourceArchiveFile):
            return

        jsonArray = []
        with zipfile.ZipFile(sourceArchiveFile, 'r') as archive:
            jsonList = [info.filename for info in archive.infolist() 
                        if info.filename.endswith('.json')]

            jsonArray = [json.loads(archive.read(jsonElement)) for jsonElement in jsonList]

        if len(jsonArray) == 0:
            return

        jsonSettings = jsonArray[0]
    
        with zipfile.ZipFile(sourceArchiveFile, 'r') as archive:
            with self.timeProcessing:
                for skin in jsonSettings :
                    inputFile = os.path.basename(skin)
                    inputSkin = jsonSettings[skin][0]

                    self.importWeight(inputFile, archive, inputSkin)

    def export(self,
               inputTransform,
               targetDirectory,
               displayReport=False):
        skinSettings = super(AsciiInjection,
                             self).export(inputTransform,
                                          targetDirectory,
                                          displayReport=False)

        if skinSettings is None:
            return None

        skinSettings.abcWeightsFile = self.saveWeights(skinSettings.skinDeformer,
                                                       targetDirectory)

        skinSettings.processingTime = float(self.timeProcessing.timeRange)

        skinSettings.report = self.reporter.publishReport(skinSettings.skinDeformer, 
                                                          skinSettings.abcWeightsFile,
                                                          None)

        return skinSettings


class BinaryInjection(DataInjection):
    def __init__(self):
        super(BinaryInjection, self).__init__()

        self.mayaFileType = "mayaBinary"

    def export(self,
               inputTransform,
               targetDirectory,
               displayReport=False):
        skinSettings = super(BinaryInjection, self).export(inputTransform,
                                                           targetDirectory,
                                                           displayReport=False)

        if skinSettings is None:
            return None

        skinSettings.abcWeightsFile = ''

        skinSettings.processingTime = float(self.timeProcessing.timeRange)

        skinSettings.report = self.timeProcessing.report

        return skinSettings

    def collectAdditionalData(self,
                              unpackDirectory):
        skinSettings = settings.SkinSettings(None,
                                    collectData=False)

        skinSettings.abcWeightsFile = posixpath.join(unpackDirectory,
                                                     'BinaryInjection_skinweight.mb')

        self.transferToDisk(self.skinNodeArray, 
                            skinSettings.abcWeightsFile)

        self.sceneWeights = [skinSettings]

        report = self.timeProcessing.report.replace('\n', '\n\t')

        report += '\n'
        report += "\n\t<End of BinaryExtraction>"

        self.batchProcessing.report += report
        self.batchProcessing.report += '\n\t Saving {} elements took {} seconds\n'.format(len(self.skinNodeArray),
                                                                                          float(self.timeProcessing.timeRange))

    def importWeights(self, 
                      targetSkinFile,
                      skinNodeArray=None,
                      namespacePrefix="skinNamespace_weights"):
        with self.timeProcessing, context.TemporaryNamespace(None,
                                                     namespacePrefix,
                                                     targetSkinFile,
                                                     fileType="mayaBinary"):
            importSkinNodeArray = maya.cmds.namespaceInfo(namespacePrefix, 
                                                          listOnlyDependencyNodes=True)

            if skinNodeArray is None:
                skinNodeArray = [skin.replace(namespacePrefix+':', '')
                                 for skin in importSkinNodeArray 
                                 if maya.cmds.objExists(skin.replace(namespacePrefix+':', '')) is True \
                                 and maya.cmds.nodeType(skin) == 'skinCluster']

            for skin in skinNodeArray:
                maya.cmds.nodeCast(skin, namespacePrefix+':' + skin, 
                                   disconnectUnmatchedAttrs=True,
                                   swapNames=True )

            report = "\n\t<BinaryInjection Report \Import {0} elements>"
            self.timeProcessing.report = report.format(len(skinNodeArray))


class AlembicInjection(DataInjection):
    def __init__(self):
        self.weightFunctionUtils = maya.OpenMaya.MFnDoubleArrayData()

        self.sourceAlembic = None

        super(AlembicInjection, self).__init__()

    def getMObject(self, nodeName):
        selList = maya.OpenMaya.MSelectionList()
        maya.OpenMaya.MGlobal.getSelectionListByName(nodeName, 
                                                     selList)
        depNode = maya.OpenMaya.MObject()
        selList.getDependNode(0, depNode) 

        return depNode

    def collectSkinWeights(self, 
                           inputSkinCluster):
        skinInput = settings.SkinSet(inputSkinCluster)
        skinInput.getShapeFullComponents()

        skinData = settings.ClusterIO()
        skinData.setType = 'All'
        skinData.joint = self.TARGET_WEIGHT_PROPERTY

        intptrUtil = maya.OpenMaya.MScriptUtil() 
        intptrUtil.createFromInt(0)
        intPtr = intptrUtil.asUintPtr()

        skinInput.skinFunctionUtils.getWeights(skinInput.shapePath,
                                               skinInput.fullComponentPointSet,
                                               skinData.weights,
                                               intPtr)

        return skinData

    def tranferWeightToAttribute(self, 
                                 skinWeightsHolder,
                                 inputSkinData):
        weightWriter = maya.OpenMaya.MDGModifier()

        targetAttribute = '{}_weights'.format(inputSkinData.joint)
        maya.cmds.addAttr(skinWeightsHolder, 
                          ln=targetAttribute,
                          dt=self.WEIGHT_PROPERTY_TYPE)

        skinWeightsHolderApiObject = self.getMObject(skinWeightsHolder)
        nodeFunctionUtils = maya.OpenMaya.MFnDependencyNode(skinWeightsHolderApiObject)

        skinWeightsApiPlug = nodeFunctionUtils.findPlug(targetAttribute,
                                                        False)

        skinDataApiObject = self.weightFunctionUtils.create(inputSkinData.weights)

        weightWriter.newPlugValue(skinWeightsApiPlug,
                                  skinDataApiObject)
  
        weightWriter.doIt()

        return targetAttribute

    def saveToDisk(self,
                   skinWeightsHolder,
                   skinWeight,
                   targetSkinFile):
        targetAttribute = self.tranferWeightToAttribute(skinWeightsHolder,
                                                        skinWeight)

        exportCommand = " -root |{node} -u {attribute} -file {targetFile}"
        exportCommand = exportCommand.format(node=skinWeightsHolder,
                                             attribute=targetAttribute,
                                             targetFile=targetSkinFile)

        maya.cmds.AbcExport(j=exportCommand)

    def saveWeights(self, 
                    inputSkinNode,
                    targetSkinDirectory,
                    displayReport=False):
        targetSkinFile = posixpath.join(targetSkinDirectory,
                                        '{0}.abc'.format(inputSkinNode))

        self.timeProcessing.displayReport = displayReport
        self.timeProcessing.report = ''

        with self.timeProcessing:
            skinWeightsHolder = maya.cmds.createNode(self.WEIGHT_HOLDER_TYPE)
            self.timeProcessing.cleanupNodes.append(skinWeightsHolder)

            skinWeight = self.collectSkinWeights(inputSkinNode)

            self.saveToDisk(skinWeightsHolder, 
                            skinWeight, 
                            targetSkinFile)

            self.timeProcessing.report = self.reporter.publishReport(inputSkinNode, 
                                                                     targetSkinFile,
                                                                     skinWeight.weights.length())

        return targetSkinFile

    def export(self,
               inputTransform,
               targetDirectory,
               displayReport=True):
        skinSettings = super(AlembicInjection, self).export(inputTransform,
                                                            targetDirectory)

        if skinSettings is None:
            return None

        skinSettings.abcWeightsFile = self.saveWeights(skinSettings.skinDeformer,
                                                       targetDirectory)

        skinSettings.processingTime = float(self.timeProcessing.timeRange)

        skinSettings.report = self.timeProcessing.report

        return skinSettings

    def importWeights(self,
                      skinSettings,
                      unpackDirectory):
        self.sourceAlembic = os.path.join(unpackDirectory,
                                     os.path.basename(skinSettings.abcWeightsFile))

        self.sourceAlembic = self.sourceAlembic.replace("\\", "/")

        self.timeProcessing.displayReport = False
        self.timeProcessing.report = ''

        with self.timeProcessing:
            self.loadFromDisk(skinSettings.deformerName,
                              self.sourceAlembic)

    def loadFromDisk(self,
                     currentSkinCluster,
                     sourceAlembic):
        skinData = settings.SkinSet(currentSkinCluster)

        skinData.getShapeFullComponents()

        skinData.getInfluenceIndices()

        skinData.extractFromAlembic(sourceAlembic,
                                    "skinNamespace_weights")

        with context.SkinDisabled(currentSkinCluster):
            skinData.skinFunctionUtils.setWeights(skinData.shapePath,
                                                  skinData.fullComponentPointSet,
                                                  skinData.influenceIndices,
                                                  skinData.weightUtils.array(),
                                                  False,
                                                  skinData.oldValues) 


class SkinIO(object):
    TARGET_WEIGHT_PROPERTY = 'skinRepository'
    WEIGHT_HOLDER_TYPE = 'joint'
    WEIGHT_PROPERTY_TYPE = 'doubleArray'

    WEIGHT_NAMESPACE = 'skinNamespace_weights'

    SKIN_PROCESSING_METHOD = ('alembicIO',
                              'mayaBinary',
                              'mayaAscii')

    def __init__(self):
        self.timeProcessing = context.TimeProcessor()

        self.reporter = validation.SkinReport()

        self.skinProcessor = None

        self.skinHandler = 'alembicIO'

        self.reportArray = []

        self.processingTime = 0

    def importFromAlembic(self, 
                          jsonDataArray,
                          unpackDirectory,
                          batchProcessing):
        self.skinProcessor = AlembicInjection()

        validationUtils = validation.SkinValidator()

        validationUtils.rootNameSpace = maya.cmds.namespaceInfo(currentNamespace=True)

        validationUtils.namespacePrefix = self.WEIGHT_NAMESPACE

        with context.TemporaryNamespace(validationUtils.rootNameSpace,
                                validationUtils.namespacePrefix):

            self.timeProcessing.displayReport = False
            self.timeProcessing.report = ''

            for skinSettings in jsonDataArray:
                validationUtils.processInputSetting(skinSettings)

                if validationUtils.isInvalid:
                    continue

                batchProcessing.processObjectCount += 1

                self.skinProcessor.importWeights(skinSettings,
                                                 unpackDirectory)

                self.reportArray.append(self.reporter.publishImportReport(skinSettings.shape, 
                                                                          self.skinProcessor.timeProcessing.report,
                                                                          self.skinProcessor.sourceAlembic,
                                                                          validationUtils.rebuildTime,
                                                                          validationUtils.skinWasrebuilt))

                batchProcessing.progressbar.advanceProgress(1)

    def importFromMayaBinary(self, 
                             jsonData,
                             unpackDirectory,
                             batchProcessing):
        self.skinProcessor = BinaryInjection()

        validationUtils = validation.SkinValidator()

        validationUtils.rootNameSpace = maya.cmds.namespaceInfo(currentNamespace=True)

        validationUtils.namespacePrefix = self.WEIGHT_NAMESPACE

        skinNodeArray = []

        batchProcessing.displayProgressbar = False

        for skinSettings in jsonData.itervalues() :
            validationUtils.processInputSetting(skinSettings)

            if validationUtils.isInvalid:
                continue

            batchProcessing.processObjectCount += 1

            skinNodeArray.append[skinSettings.deformerName]

        targetSkinFile = None
        self.skinProcessor.importWeights(targetSkinFile,
                                         skinNodeArray=skinNodeArray,
                                         namespacePrefix=self.WEIGHT_NAMESPACE)

    def importWeights(self, 
                      jsonData,
                      unpackDirectory,
                      batchProcessing):
        self.reportArray = []

        if self.skinHandler == 'alembicIO':
            self.importFromAlembic(jsonData,
                                   unpackDirectory,
                                   batchProcessing)

        elif self.skinHandler == 'mayaBinary':
            self.importFromMayaBinary(jsonData,
                                      unpackDirectory,
                                      batchProcessing)

        elif self.skinHandler == 'mayaAscii':
            pass

        for report in self.reportArray:
            self.timeProcessing.report += report.replace('\n', '\n\t\t')

            self.timeProcessing.report += '\n'

    def parseJsonFromArchive(self,
                             sourceArchiveFile):
        with zipfile.ZipFile(sourceArchiveFile, 'r') as archive:
            jsonList = [info.filename for info in archive.infolist() 
                        if info.filename.endswith('.json')]

            jsonInput = [json.loads(archive.read(jsonElement)) for jsonElement in jsonList][0]

        jsonArray = []
        for jsonData in jsonInput:
            skinData = settings.SkinSettings(None,
                                    collectData=False)

            skinData.fromJson(jsonInput[jsonData])

            jsonArray.append(skinData)

        return jsonArray

    def importAssetWeights(self, 
                           sourceArchiveFile,
                           exposeWeightDetails=True,
                           showProgressbar=True):
        if not os.path.exists(sourceArchiveFile):
            return

        jsonSettings = self.parseJsonFromArchive(sourceArchiveFile)

        batchProcessing = context.TimeProcessor()
        batchProcessing.displayProgressbar = showProgressbar
        batchProcessing.displayReport = False
        batchProcessing.progressbarRange = len(jsonSettings)

        with batchProcessing:
            with context.TemporaryDirectory() as unpackDirectory, \
            zipfile.ZipFile(sourceArchiveFile, 'r') as archive:
                archive.extractall(unpackDirectory)
                batchProcessing.report = '\n<Batch Processing report :>' 

                self.importWeights(jsonSettings,
                                   unpackDirectory,
                                   batchProcessing)

                batchProcessing.report += self.timeProcessing.report

                batchProcessing.report += '\n<Successfully processed {} components>'.format(batchProcessing.processObjectCount) 

        if exposeWeightDetails is True:
            print batchProcessing.report

        return float(batchProcessing.timeRange)

    def exportAssetWeights(self,
                           objectArray,
                           targetArchiveFile,
                           exposeWeightDetails=True,
                           showProgressbar=True):
        if len(objectArray) == 0:
            return

        if objectArray is None:
            return

        self.processingTime = 0

        self.reportArray = []

        if self.skinHandler == 'alembicIO':
            self.skinProcessor = AlembicInjection()

            return self.skinProcessor.exportAssetWeights(objectArray,
                                                         targetArchiveFile,
                                                         exposeWeightDetails=exposeWeightDetails)

        if self.skinHandler == 'mayaBinary':
            self.skinProcessor = BinaryInjection()

            return self.skinProcessor.exportAssetWeights(objectArray,
                                                         targetArchiveFile,
                                                         exposeWeightDetails=exposeWeightDetails)

        if self.skinHandler == 'mayaAscii':
            self.skinProcessor = AsciiInjection()

            return self.skinProcessor.exportAssetWeights(objectArray,
                                                         targetArchiveFile,
                                                         exposeWeightDetails=exposeWeightDetails)