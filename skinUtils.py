import maya.OpenMaya 
import maya.OpenMayaAnim 
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


class AsciiInjection(object):
    def __init__(self):
        self.timeProcessing = TimeProcessor()

    def transferSkinNodeToDisk(self, 
                               skinNodeArray, 
                               targetSkinDirectory):
        outputSkinSettings = {}
        with self.timeProcessing:
            skinPrefix = uuid.uuid1()
            for skin in skinNodeArray:
                targetSkinFileName = '{0}_{1}_skinWeights.ma'.format(skin, skinPrefix)
                targetSkinFile = os.path.join(targetSkinDirectory,
                                              targetSkinFileName)

                outputSkinSettings[targetSkinFileName] = [skin, targetSkinFile]

                maya.cmds.select(skin, r=True)
                maya.cmds.file(targetSkinFile,
                               force=True, 
                               typ="mayaAscii",
                               es=True,
                               ch=False,
                               chn=False,
                               con=False, 
                               exp=False,
                               sh=False)

            report = "<AsciiExtraction Report: \n\tSuccessfully save {0} elements>"
            self.timeProcessing.report = report.format(len(skinNodeArray))

        targetArchiveFile = os.path.join(targetSkinDirectory,
                                         'skinWeights.zip')

        jsonSkinFile = os.path.join(targetSkinDirectory,
                                   'jsonsWeightSetting.json')

        with open(jsonSkinFile, "w") as outfile:
            json.dump(outputSkinSettings, outfile , indent=4)

        with zipfile.ZipFile(targetArchiveFile, 'w', compression=zipfile.ZIP_DEFLATED) as outputZip:
            outputZip.write(jsonSkinFile, r'%s'%'jsonsWeightSetting.json')
            os.remove(jsonSkinFile)

            for component in outputSkinSettings:
                outputZip.write(outputSkinSettings[component][1], r'%s'%component)
                os.remove(outputSkinSettings[component][1])
            
    def filterAscii(self, archive, inputFile, inputSkin):
        startCollect = False
        with archive.open(inputFile, 'r') as asciiFile:
            for line in asciiFile:
                if 'createNode skinCluster -n' in line:
                    startCollect = True

                if startCollect is True and 'createNode' not in line:
                    if 'rename -uid' not in line:
                        yield line

                if startCollect is True and 'createNode' in line and \
                    'createNode skinCluster -n' not in line:
                    startCollect = False

    def consolidateFile(self, archive, inputFile, inputSkin):
        with open("C:/Users/cedric/Desktop/skinIO/UU2.ma", 'w') as asciiFile:
            #asciiFile.write('requires maya "2017";\n')
            for line in self.filterAscii(archive, inputFile, inputSkin):
                asciiFile.write(line)

    def importWeight(self, inputFile, archive, inputSkin):
        self.consolidateFile(archive, inputFile, inputSkin)
        #maya.cmds.select(inputSkin, r=True)
        maya.cmds.file("C:/Users/cedric/Desktop/skinIO/UU2.ma",
                       i=True, 
                       type="mayaAscii")
                           
    def importWeights(self, sourceArchiveFile):
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


class BinaryInjection(object):
    def __init__(self):
        self.timeProcessing = TimeProcessor()

    def transferSkinNodeToDisk(self, 
                               skinNodeArray, 
                               targetSkinFile):
        with self.timeProcessing:
            maya.cmds.select(skinNodeArray, r=True)
            maya.cmds.file(targetSkinFile,
                           force=True, 
                           typ="mayaBinary",
                           es=True,
                           ch=False,
                           chn=False,
                           con=False, 
                           exp=False,
                           sh=False) 

            report = "<BinaryExtraction Report: \n\tSuccessfully save {0} elements>"
            self.timeProcessing.report = report.format(len(skinNodeArray))

    def importWeights(self, 
                      targetSkinFile,
                      skinNodeArray=None):
        namespacePrefix = "skinNamespace_weights"
        with self.timeProcessing:
            maya.cmds.file(targetSkinFile,
                           i=True, 
                           type="mayaBinary",  
                           ignoreVersion=True, 
                           ra=True, 
                           mergeNamespacesOnClash=False, 
                           namespace=namespacePrefix, 
                           pr=True)

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

            maya.cmds.namespace(removeNamespace=namespacePrefix, 
                                deleteNamespaceContent=True)

            report = "<BinaryInjection Report \Import {0} elements>"
            self.timeProcessing.report = report.format(len(skinNodeArray))


class Omphallos(object):
    def __init__(self):
        self.repository = None

    def collectOriginShape(self, targetName, targetShapeFile):
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


class TemporaryDirectory(object):
    def __init__(self, suffix="", prefix="tmp", dir=None):
        self.tempfolder = tempfile.mkdtemp(suffix, prefix, dir)

    def __enter__(self):
        return self.tempfolder

    def __exit__(self, type, value, traceback):
        if os.path.exists(self.tempfolder): 
            shutil.rmtree(self.tempfolder)


class ObjectEncoder(json.JSONEncoder):
    def default(self, inputObject):
        if hasattr(inputObject, "to_json"):
            return self.default(inputObject.to_json())
        elif hasattr(inputObject, "__dict__"):
            jsonDict = dict(
                            (key, value)
                            for key, value in inspect.getmembers(inputObject)
                            if not key.startswith("__")
                            and not inspect.isabstract(value)
                            and not inspect.isbuiltin(value)
                            and not inspect.isfunction(value)
                            and not inspect.isgenerator(value)
                            and not inspect.isgeneratorfunction(value)
                            and not inspect.ismethod(value)
                            and not inspect.ismethoddescriptor(value)
                            and not inspect.isroutine(value)
                            )
            return self.default(jsonDict)
        return inputObject


class SkinSettings(object):
    def __init__(self):
        self.deformerName = None
        self.shape  = None
        self.influences = []

        self.skinningMethod = 0
        self.normalizeWeights = False
        self.abcWeightsFile = None

        self.processingTime = 0
        self.report = ''

    def toJson(self):
        return json.dumps(self, 
                          cls=ObjectEncoder, 
                          indent=2, 
                          sort_keys=True)


class SkinSet(object):
    def __init__(self, inputSkinCluster):
        self.shapePath = maya.OpenMaya.MDagPath()
        self.jointPaths = maya.OpenMaya.MDagPathArray()
        self.skinFunctionUtils = None

        self.extractData(inputSkinCluster)

    def getMObject(self, nodeName):
        selList = maya.OpenMaya.MSelectionList()
        maya.OpenMaya.MGlobal.getSelectionListByName(nodeName, 
                                                     selList)
        depNode = maya.OpenMaya.MObject()
        selList.getDependNode(0, depNode) 

        return depNode

    def extractData(self, inputSkinCluster):
        skinClusterApiObject = self.getMObject(inputSkinCluster)
        self.skinFunctionUtils = maya.OpenMayaAnim.MFnSkinCluster(skinClusterApiObject)

        self.skinFunctionUtils.influenceObjects(self.jointPaths)
        self.skinFunctionUtils.getPathAtIndex(0, self.shapePath)


class ClusterIO(object):
    def __init__(self):
        self.weights = maya.OpenMaya.MDoubleArray()
        self.indexArray = maya.OpenMaya.MIntArray()

        self.joint = ''
        self.setType = '' #cluster/All


class TimeProcessor(object):
    def __init__(self):
        self.startTime = 0.0
        self.endTime = 0.0
        self.report = ''
        self.cleanupNodes = []
        self.timeRange = 0

        self.displayReport = True

        self.displayProgressbar = False
        self.progressbar = None
        self.progressbarRange = 1

    def __enter__(self):
        if self.displayProgressbar is True:
            self.progressbar = maya.OpenMayaUI.MProgressWindow()
            self.progressbar.reserve()
            self.progressbar.setProgressRange(0, self.progressbarRange)

            self.progressbar.startProgress()

        self.stampProcessingTime()

    def __exit__(self, type, value, traceback):
        if len(self.cleanupNodes) > 0:
            maya.cmds.delete(self.cleanupNodes)

        self.reportProcessingTime()
        if self.displayProgressbar is True:
            self.progressbar.endProgress()

    def stampProcessingTime(self):
        self.startTime = time.clock()

    def reportProcessingTime(self):
        self.endTime = time.clock()
        self.timeRange = (self.endTime - self.startTime)

        self.report = '{0}\n{1}\nProcessings took {2} seconds'.format(self.report,
                                                                      '-'*70,
                                                                      self.timeRange)
        if self.displayReport is True:
            print self.report


class SkinIO(object):
    TARGET_WEIGHT_PROPERTY = 'skinRepository'
    WEIGHT_HOLDER_TYPE = 'joint'
    WEIGHT_PROPERTY_TYPE = 'doubleArray'

    def __init__(self):
        self.weightFunctionUtils = maya.OpenMaya .MFnDoubleArrayData()
        self.timeProcessing = TimeProcessor()

    def getMObject(self, nodeName):
        selList = maya.OpenMaya.MSelectionList()
        maya.OpenMaya.MGlobal.getSelectionListByName(nodeName, 
                                                     selList)
        depNode = maya.OpenMaya.MObject()
        selList.getDependNode(0, depNode) 

        return depNode

    def collectInfos(self, 
                    inputSkinNode):
        jointArray = maya.cmds.skinCluster(inputSkinNode, q=True, inf=True)
        geometry = maya.cmds.skinCluster(inputSkinNode, q=True, geometry=True)[0]
        
        return [len(jointArray), geometry]

    def publishReport(self, inputSkinNode, targetSkinFile, sampleLength):
        metaData = self.collectInfos(inputSkinNode)
        vertexCount = maya.cmds.polyEvaluate(metaData[1], v=True)

        componentReport = '\n<Skin Weights Saving report:>' 
        componentReport += '\n\tExport to {} was successful'.format(targetSkinFile) 
        componentReport += '\n\tGeometry {0}'.format(metaData[1]) 
        componentReport += '\n\t\tNumber of vertex {0}'.format(vertexCount)
        componentReport += '\n\t\tNumber of influences {0}'.format(metaData[0]) 
        componentReport += '\n\t\tNumber of weights Samples {0}'.format(sampleLength)

        return componentReport

    def getShapeFullComponents(self, skinInput):
        simpleShapeType = ['mesh', 'nurbsCurve']
        shapeType = maya.cmds.nodeType(skinInput.shapePath.fullPathName())

        if shapeType in simpleShapeType:
            componentType = maya.OpenMaya.MFn.kMeshVertComponent

            if shapeType == 'mesh':
                shapeFunctionUtils = maya.OpenMaya.MFnMesh(skinInput.shapePath)
                pointCount = shapeFunctionUtils.numVertices()

                pointComponentFunction = maya.OpenMaya.MFnSingleIndexedComponent()

            elif shapeType == 'nurbsCurve':
                shapeFunctionUtils = maya.OpenMaya.MFnNurbsCurve(skinInput.shapePath)
                pointCount = shapeFunctionUtils.numVertices()
                componentType = OpenMaya.MFn.kCurveCVComponent

            fullComponent = pointComponentFunction.create(componentType)
            pointComponentFunction.setCompleteData(pointCount)
            
            return fullComponent

        elif shapeType == 'nurbsSurface':
            componentType = maya.OpenMaya.MFn.kSurfaceCVComponent
            shapeFunctionUtils = maya.OpenMaya.MFnNurbsSurface(skinInput.shapePath)

            pointComponentFunction = maya.OpenMaya.MFnDoubleIndexedComponent()
            fullComponent = pointComponentFunction.create(componentType)

            pointComponentFunction.setCompleteData(shapeFunctionUtils.numCVsInU(),
                                                   shapeFunctionUtils.numCVsInV())

            return fullComponent

        elif shapeType == 'lattice':
            componentType = maya.OpenMaya.MFn.kLatticeComponent
            shapeFunctionUtils = maya.OpenMaya.MFnLattice(skinInput.shapePath)

            sDivivision = 0
            tDivivision = 0
            uDivivision = 0

            shapeFunctionUtils.getDivisions(sDivivision,
                                            tDivivision,
                                            uDivivision)

            pointComponentFunction = maya.OpenMaya.MFnTripleIndexedComponent()
            fullComponent = pointComponentFunction.create(componentType)
            
            pointComponentFunction.setCompleteData(sDivivision,
                                                   tDivivision,
                                                   uDivivision)

            return fullComponent

    def collectSkinWeights(self, inputSkinCluster):
        skinInput = SkinSet(inputSkinCluster)
        fullComponent = self.getShapeFullComponents(skinInput)

        skinData = ClusterIO()
        skinData.setType = 'All'
        skinData.joint = self.TARGET_WEIGHT_PROPERTY

        intptrUtil = maya.OpenMaya.MScriptUtil() 
        intptrUtil.createFromInt(0)
        intPtr = intptrUtil.asUintPtr()

        skinInput.skinFunctionUtils.getWeights(skinInput.shapePath, 
                                               fullComponent,
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

    def transferToDisk(self,
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
                    displayReport=True):
        targetSkinFile = posixpath.join(targetSkinDirectory,
                                        '{0}.abc'.format(inputSkinNode))

        self.timeProcessing.displayReport = displayReport

        with self.timeProcessing:
            skinWeightsHolder = maya.cmds.createNode(self.WEIGHT_HOLDER_TYPE)
            self.timeProcessing.cleanupNodes.append(skinWeightsHolder)

            skinWeight = self.collectSkinWeights(inputSkinNode)

            self.transferToDisk(skinWeightsHolder, skinWeight, targetSkinFile)

            self.timeProcessing.report = self.publishReport(inputSkinNode, 
                                                            targetSkinFile,
                                                            skinWeight.weights.length())
        return targetSkinFile

    def getSkinFromObjectSet(self, inputShape):
        outputSkins = []
        skinObjectSets = maya.cmds.listConnections(inputShape,
                                                   type='objectSet',
                                                   source=True)

        if skinObjectSets is None:
            return []
        
        for objectSet in skinObjectSets:
            skinArray = maya.cmds.listConnections(objectSet,
                                                  type='skinCluster')

            if skinArray is None:
                continue

            outputSkins.extend(skinArray)

        return outputSkins

    def getSkinHistory(self, inputTransform):
        skinClusters = []
        outputSkins = []
        shapeNode = None

        supportedType = ['mesh','nurbsCurve', 'nurbsSurface', 'lattice']
        shapeType = maya.cmds.nodeType(inputTransform)

        if shapeType in supportedType:
            shapeNode = inputTransform
        else:
            shapeNodeArray = maya.cmds.listRelatives(inputTransform,
                                                     s=True,
                                                     fullPath=True)
            if shapeNodeArray is None:
                shapeNode = None
            else:
                if len(shapeNodeArray)>0:
                    shapeNode = shapeNodeArray[0]

        if shapeNode is None:
            return outputSkins

        outputSkins = maya.cmds.listConnections(shapeNode, 
                                                type='skinCluster',
                                                source=True)

        if outputSkins is None:
            outputSkins = []

        outputSkins.extend(self.getSkinFromObjectSet(shapeNode))

        return list(set(outputSkins))

    def getSkinClusters(self, inputTransform):
        skinClusters = []
        outputSkins = []
        shapeNode = None

        supportedType = ['mesh','nurbsCurve', 'nurbsSurface', 'lattice']
        shapeType = maya.cmds.nodeType(inputTransform)

        if shapeType in supportedType == True:
            meshNodes.append(inputTransform)
        else:
            meshNodes = maya.cmds.listRelatives(inputTransform, s=True, fullPath=True)

        if meshNodes is None or len(meshNodes) < 1 :
            return []

        for shape in meshNodes:
            skinHistory = maya.cmds.ls( list(set(maya.cmds.listHistory(inputTransform))), type='skinCluster')
            if skinHistory != None or len(skinHistory) > 0 :
                skinClusters.extend(skinHistory)

        skinShaped = meshNodes[0].split('|')[-1]
        if skinClusters != None or len(skinClusters) > 0 :
            for skin in skinClusters:
                if skin not in outputSkins:
                    SkinSet = maya.cmds.ls(maya.cmds.listConnections('%s.message'% skin), type='objectSet')[0]
                    geo = maya.cmds.listConnections('%s.dagSetMembers[0]'%SkinSet, sh=True)[0]
                    
                    if skinShaped in geo:
                        outputSkins.append(skin)

        return list(set(outputSkins))

    def getSkinSettings(self, skinDeformer):
        skinSettings = SkinSettings()

        skinSettings.deformerName = skinDeformer
        skinSettings.influences = maya.cmds.skinCluster(skinDeformer, q=True, inf=True)
        skinSettings.skinningMethod = maya.cmds.getAttr('{}.skinningMethod'.format(skinDeformer))
        skinSettings.normalizeWeights = maya.cmds.getAttr('{}.normalizeWeights'.format(skinDeformer))

        return skinSettings

    def extractSettings(self, inputSkinSettings):
        inputSkinSettings.report = ''
        jsonData = inputSkinSettings.toJson()

        return jsonData

    def saveSettings(self, 
                     targetArchiveFile, 
                     outputSkinSettings):
        jsonSkinFileExtention = os.path.splitext(targetArchiveFile)[1]
        jsonSkinFile = targetArchiveFile.replace(jsonSkinFileExtention, '.json')

        jsonSkinFileName = os.path.basename(targetArchiveFile).replace(jsonSkinFileExtention, '.json')

        with open(jsonSkinFile, "w") as outfile:
            json.dump(outputSkinSettings, outfile , indent=4)

        return jsonSkinFile, jsonSkinFileName

    def export(self,
               inputTransform,
               targetDirectory,
               skipZipArchive=False,
               displayReport=True,
               intersectSceneWeights=None):
        #inputSkinNodes = self.getSkinClusters(inputTransform)
        inputSkinNodes = self.getSkinHistory(inputTransform)

        targetSkinSettings = []

        if intersectSceneWeights is not None:
            inputSkinNodes = list(set(inputSkinNodes) - set(intersectSceneWeights))

        if len(inputSkinNodes) == 0:
            return []

        for inputSkinNode in inputSkinNodes:
            skinSettings = self.getSkinSettings(inputSkinNode)
            skinSettings.shape = maya.cmds.listRelatives(inputTransform,
                                                         s=True,
                                                         fullPath=True)[0]

            skinSettings.abcWeightsFile = self.saveWeights(inputSkinNode,
                                                           targetDirectory,
                                                           displayReport=displayReport)

            skinSettings.processingTime = float(self.timeProcessing.timeRange)
            skinSettings.report = self.timeProcessing.report

            targetSkinSettings.append(skinSettings)

        if skipZipArchive is False:
            outputZip =  posixpath.join(targetDirectory, '{0}.zip'.format(inputTransform))

            skinMetadata = {}
            for component in targetSkinSettings:
                jsonData = self.extractSettings(component)
                skinMetadata[component.deformerName] = json.loads(jsonData)

            jsonSkinFile, jsonSkinFileName = self.saveSettings(outputZip, 
                                                               skinMetadata)

            with zipfile.ZipFile(outputZip, 'w', compression=zipfile.ZIP_DEFLATED) as outputZip:
                outputZip.write(jsonSkinFile, r'%s'%jsonSkinFileName)

                for component in targetSkinSettings:
                    zipName = os.path.basename(component.abcWeightsFile)
                    outputZip.write(component.abcWeightsFile, r'%s'%zipName)

            for component in targetSkinSettings:
                os.remove(component.abcWeightsFile) 

            os.remove(jsonSkinFile)

        return targetSkinSettings

    def exportAssetWeights(self,
                           objectArray,
                           targetArchiveFile,
                           exposeWeightDetails=True,
                           showProgressbar=True):
        if len(objectArray) == 0:
            return

        batchProcessing = TimeProcessor()
        batchProcessing.displayProgressbar = showProgressbar
        batchProcessing.progressbarRange = len(objectArray)

        sceneWeights = []

        processingTime = 0
        validComponent = 0
        reportArray = []

        targetDirectory = os.path.dirname(targetArchiveFile)
        if not os.path.isdir(targetDirectory):
            return

        skinNames = []
        with batchProcessing:
            for component in objectArray:
                targetSkinSettings = self.export(component,
                                                 targetDirectory,
                                                 skipZipArchive=True,
                                                 displayReport=False,
                                                 intersectSceneWeights=skinNames)
                if len(targetSkinSettings) == 0:
                    continue

                for skinSettings in targetSkinSettings:
                    skinNames.append(skinSettings.deformerName)

                sceneWeights.append(targetSkinSettings)

                for component in targetSkinSettings:
                    processingTime += component.processingTime
                    validComponent += 1
                    reportArray.append(component.report)

                if batchProcessing.displayProgressbar is True:
                    batchProcessing.progressbar.advanceProgress(1)

            batchProcessing.report = '\n<Batch Processing report :>' 
            batchProcessing.report += '\n\t Saving {} elements took {} seconds\n'.format(validComponent,
                                                                                processingTime)

            if exposeWeightDetails is True:
                for report in reportArray:
                    batchProcessing.report += report.replace('\n', '\n\t\t')

                    batchProcessing.report += '\n'

        skinMetadata = {}
        for targetSkinSettings in sceneWeights:
            for component in targetSkinSettings:
                jsonData = self.extractSettings(component)
                skinMetadata[component.deformerName] = json.loads(jsonData)

        jsonSkinFile, jsonSkinFileName = self.saveSettings(targetArchiveFile, 
                                                           skinMetadata)

        with zipfile.ZipFile(targetArchiveFile, 'w', compression=zipfile.ZIP_DEFLATED) as outputZip:
            outputZip.write(jsonSkinFile, r'%s'%jsonSkinFileName)

            for targetSkinSettings in sceneWeights:
                for component in targetSkinSettings:
                    zipName = os.path.basename(component.abcWeightsFile)
                    outputZip.write(component.abcWeightsFile, r'%s'%zipName)

        for targetSkinSettings in sceneWeights:
            for component in targetSkinSettings:
                os.remove(component.abcWeightsFile) 

        os.remove(jsonSkinFile)

    def validateGeometries(self, inputShapePath):
        isValidNode = maya.cmds.objExists(inputShapePath)
        return isValidNode

    def validateDeformer(self, inputDeformerName):
        isValidSkinDeformer = False
        skinComponents = maya.cmds.ls(inputDeformerName, typ='skinCluster')

        if len(skinComponents)>0:
            isValidSkinDeformer = True

        return isValidSkinDeformer

    def validateSkin(self, inputDeformerName, inputShapePath):
        inputSkinNodes = self.getSkinHistory(inputShapePath)

        if inputSkinNodes is None:
            print inputDeformerName, inputShapePath
            return False

        if inputDeformerName in inputSkinNodes:
            return True

        return False

    def validateInfluences(self, inputInfluenceArray):
        jointReport = [True, []]

        for influence in inputInfluenceArray:
            isValidNode = maya.cmds.objExists(influence)

            if isValidNode is False:
                jointReport[0] =  False, 
                jointReport[1].append(influence)

        return jointReport

    def synchronizeDeformer(self, inputDeformer, inputInfluenceArray):
        currentInfluencesList = maya.cmds.skinCluster(inputDeformer, q=True, inf=True)
        rebuildSkinCluster = False

        #Case 1: Influence count mismatch 
        if len(currentInfluencesList) != len(inputInfluenceArray):
            report = 'Influence count mismatch in {skin} [{currentCount}/{importCount}]'
            report = report.format(skin=inputDeformer,
                                   currentCount=len(currentInfluencesList),
                                   importCount=len(inputInfluenceArray))

            maya.OpenMaya.MGlobal.displayInfo(report)
            maya.OpenMaya.MGlobal.displayInfo("Rebuilding skinnCluster")

            rebuildSkinCluster = True

        #Case 2: Influence Order mismatch
        unorderJointSet = []
        for jointIndex, joint in enumerate(inputInfluenceArray):
            currentInfluenceIndex = currentInfluencesList.index(joint)

            if currentInfluenceIndex != jointIndex:
                unorderJointSet.append([joint, currentInfluenceIndex,  jointIndex])

        if len(unorderJointSet) > 0:
            reportBase = 'Influence order mismatch {joint} index is {currentIndex} instead of {importIndex}'

            for component in unorderJointSet:
                report = reportBase.format(joint=component[0],
                                           currentIndex=component[1],
                                           importIndex=component[2])

                maya.OpenMaya.MGlobal.displayInfo(report)

            maya.OpenMaya.MGlobal.displayInfo("Rebuilding skinnCluster")
            rebuildSkinCluster = True

        return rebuildSkinCluster

    def rebuildSkinCluster(self):
        pass

    def importWeights(self):
        pass

    def loadSkinSettings(self, jsonArray):
        influArray = []
        for jsonData in jsonArray:
            for skinSettings in jsonData.itervalues() :
                canFindShapeInScene = self.validateGeometries(skinSettings['shape'])

                if canFindShapeInScene is False:
                    report = 'Unable to find shape {}'.format(skinSettings['shape'])
                    maya.OpenMaya.MGlobal.displayWarning(report)

                    continue

                canFindAllJoints = self.validateInfluences(skinSettings['influences'])

                if canFindAllJoints[0] is False:
                    for jointReport in canFindAllJoints[1]:
                        report = 'Unable to find Influence {}'.format(jointReport)
                        maya.OpenMaya.MGlobal.displayWarning(report)

                    continue

                canFindSkinDeformerWithName = self.validateDeformer(skinSettings['deformerName'])
                if canFindSkinDeformerWithName is False:
                    report = 'Unable to find skinCluster {}'.format(skinSettings['deformerName'])
                    maya.OpenMaya.MGlobal.displayWarning(report)
                    continue

                needsSkinClusterRebuilding = self.synchronizeDeformer(skinSettings['deformerName'],
                                                                      skinSettings['influences'])

                if needsSkinClusterRebuilding is True:
                    self.rebuildSkinCluster()

                isSkinClusterDeformingCurrentShape = self.validateSkin(skinSettings['deformerName'], 
                                                                       skinSettings['shape'])

                if isSkinClusterDeformingCurrentShape is False:
                    report = 'Please insure {skin} actually deforms {shape}'
                    
                    report = report.format(skin=skinSettings['deformerName'],
                                           shape=skinSettings['shape'])

                    maya.OpenMaya.MGlobal.displayWarning(report)

                    continue

                influArray.extend(skinSettings['influences'])

        return list(set(influArray))

    def importAssetWeights(self, sourceArchiveFile):
        if not os.path.exists(sourceArchiveFile):
            return

        jsonList = []
        jsonArray = []

        with zipfile.ZipFile(sourceArchiveFile, 'r') as archive:
            jsonList = [info.filename for info in archive.infolist() 
                        if info.filename.endswith('.json')]

            jsonArray = [json.loads(archive.read(jsonElement)) for jsonElement in jsonList]

        batchProcessing = TimeProcessor()
        tt = []
        with batchProcessing:
            tt = self.loadSkinSettings(jsonArray)

        return tt

        with TemporaryDirectory() as unpackDirectory:
            with zipfile.ZipFile(sourceArchiveFile, 'r') as archive:
                archive.extractall(unpackDirectory)

                with batchProcessing:
                    self.loadSkinSettings(jsonArray)