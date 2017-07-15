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


__version__ = '0.38.5'


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

    def collectShape(self, 
                     shapeArray,
                     targetName, 
                     targetShapeFile):
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
            maya.cmds.connectAttr('{0}.outPolyMesh[{1}]'.format(self.alembicNode, shapeIndex),
                                  '{0}.inMesh'.format(shape),
                                  f=True)

        maya.cmds.delete(self.repository)


class SelectionSaved(object):
    def __init__(self):
        self.currentSelection = []

    def __enter__(self):
        self.currentSelection = maya.cmds.ls(sl=True)

    def __exit__(self, 
                 type, 
                 value, 
                 traceback):
        if len(self.currentSelection)==0:
            return

        maya.cmds.select(self.currentSelection,
                         r=True)


class SkinDisabled(object):
    ENABLE_VALUE = 1.0

    DISABLE_VALUE = 0.0

    def __init__(self,
                 currentSkinCluster):
        self.lockState = False

        self.jointLockState = []

        self.skinInfluencelist = []

        self.currentSkinCluster = currentSkinCluster

    def __enter__(self):
        '''
            Disable skinCluster before write operation
        '''
        self.lockState = maya.cmds.getAttr('{0}.{1}'.format(self.currentSkinCluster,
                                                            'normalizeWeights'), l=True)

        maya.cmds.setAttr('{0}.nw'.format(self.currentSkinCluster), l=False)

        maya.cmds.setAttr('{0}.envelope'.format(self.currentSkinCluster), l=False)
        
        maya.cmds.setAttr('{0}.normalizeWeights'.format(self.currentSkinCluster), 
                          self.DISABLE_VALUE)

        maya.cmds.setAttr('{0}.envelope'.format(self.currentSkinCluster), 
                          self.DISABLE_VALUE)

        self.jointLockState = []
        self.skinInfluencelist = maya.cmds.skinCluster(self.currentSkinCluster,
                                                       q=True,
                                                       inf=True)

        for joint in self.skinInfluencelist :
            self.jointLockState.append(maya.cmds.getAttr('{0}.liw'.format(joint)))
            maya.cmds.setAttr('{0}.liw'.format(joint),
                              self.DISABLE_VALUE)

    def __exit__(self, 
                 type, 
                 value, 
                 traceback):
        '''
            Restore skinCluster after write operation
        '''
        maya.cmds.setAttr('{0}.normalizeWeights'.format(self.currentSkinCluster), 
                          self.ENABLE_VALUE)

        maya.cmds.setAttr('{0}.normalizeWeights'.format(self.currentSkinCluster), 
                                                        l=self.lockState)

        maya.cmds.setAttr('{0}.envelope'.format(self.currentSkinCluster), 
                          self.ENABLE_VALUE)
        
        for jointIndex, joint in enumerate(self.skinInfluencelist) :
            maya.cmds.setAttr('{0}.liw'.format(joint),
                              self.jointLockState[jointIndex])


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

        self.processObjectCount = 0

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


class TemporaryNamespace(object):
    def __init__(self,
                 rootNameSpace,
                 namespacePrefix,
                 targetSkinFile=None,
                 fileType="mayaBinary"):
        self.rootNameSpace = rootNameSpace

        self.namespacePrefix = namespacePrefix

        self.targetSkinFile = targetSkinFile

        self.fileType = fileType

    def __enter__(self):
        if self.targetSkinFile is None:
            maya.cmds.namespace(addNamespace=self.namespacePrefix)

            maya.cmds.namespace(setNamespace=self.namespacePrefix)
        else:
            maya.cmds.file(self.targetSkinFile,
                           i=True, 
                           type=self.fileType,  
                           ignoreVersion=True, 
                           ra=True, 
                           mergeNamespacesOnClash=False, 
                           namespace=self.namespacePrefix, 
                           pr=True)

    def __exit__(self, 
                 type, 
                 value, 
                 traceback):
        if self.targetSkinFile is None:
            maya.cmds.namespace(setNamespace=self.rootNameSpace)

            maya.cmds.namespace(removeNamespace=self.namespacePrefix)
        else:
            maya.cmds.namespace(removeNamespace=self.namespacePrefix, 
                                deleteNamespaceContent=True)


class TemporaryDirectory(object):
    def __init__(self, 
                 suffix="", 
                 prefix="tmp", 
                 dir=None):
        if dir is None:
            self.tempfolder = tempfile.mkdtemp(suffix, prefix, dir)
        else:
            if os.path.exists(dir): 
                self.tempfolder = dir 
            else:
                maya.cmds.sysFile(dir, makeDir=True)
                                                    
                self.tempfolder = dir

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


class SkinValidator(object):
    def __init__(self):
        self.isInvalid = False

        self.rebuildTime = 0

        self.skinWasrebuilt = False

        self.rootNameSpace = None

        self.namespacePrefix = None

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

    def validateGeometries(self, inputShapePath):
        isValidNode = maya.cmds.objExists(inputShapePath)
        return isValidNode

    def validateDeformer(self, inputDeformerName):
        skinComponents = maya.cmds.ls(inputDeformerName, 
                                      type='skinCluster')

        if len(skinComponents)>0:
            return True

        return False

    def validateSkin(self, 
                     inputDeformerName, 
                     inputShapePath):
        inputSkinNodes = self.getSkinHistory(inputShapePath)

        if len(inputSkinNodes)==0:
            return None

        if inputDeformerName in inputSkinNodes:
            return True

        return False

    def validateInfluences(self, 
                           inputInfluenceArray):
        jointReport = JointReport()

        for influence in inputInfluenceArray:
            isValidNode = maya.cmds.objExists(influence)

            if isValidNode is True:
                continue

            jointReport.canFindAllJoints = False 
            jointReport.missingJoints.append(influence)

        return jointReport

    def synchronizeDeformer(self,
                            inputDeformer, 
                            inputInfluenceArray):
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

    def rebuildSkinCluster(self,
                           skinSettings):
        inputSkinCluster = maya.cmds.skinCluster(skinSettings.influences ,
                                                 maya.cmds.listRelatives(skinSettings.shape, p=True),
                                                 dr=4.5,
                                                 skinMethod=0 ,
                                                 toSelectedBones=True ,
                                                 n=skinSettings.deformerName,
                                                 maximumInfluences=1)[0]

        self.removeAccessoryNodes(inputSkinCluster)

        return inputSkinCluster

    def removeAccessoryNodes(self,
                             inputSkinCluster):
        skinHistory = maya.cmds.listHistory(inputSkinCluster)
        if skinHistory is None:
            return

        if len(skinHistory)==0:
            return

        skinHistory = list(set(skinHistory))
        unwantedNodes = []

        for nodeType in ('tweak',
                         'dagPose'):
            pruneNodes = maya.cmds.ls(skinHistory,
                                      type=nodeType)

            if pruneNodes is None:
                continue
 
            unwantedNodes.extend(pruneNodes)

        if len(unwantedNodes)==0:
            return

        maya.cmds.delete(unwantedNodes)

    def processInputSetting(self,
                            skinSettings):
        self.isInvalid = False

        self.rebuildTime = 0

        self.skinWasrebuilt = False

        canFindShapeInScene = self.validateGeometries(skinSettings.shape)

        if canFindShapeInScene is False:
            report = 'Unable to find shape {}'.format(skinSettings.shape)
            maya.OpenMaya.MGlobal.displayWarning(report)

            self.isInvalid = True
            return

        jointReport = self.validateInfluences(skinSettings.influences)

        if jointReport.canFindAllJoints is False:
            for joint in jointReport.missingJoints:
                report = 'Unable to find Influence {}'.format(jointReport)
                maya.OpenMaya.MGlobal.displayWarning(report)

            self.isInvalid = True
            return

        isSkinClusterDeformingCurrentShape = self.validateSkin(skinSettings.deformerName, 
                                                               skinSettings.shape)

        if isSkinClusterDeformingCurrentShape is None:
            processing = TimeProcessor()
            processing.displayProgressbar = False
            processing.displayReport = False

            with processing:
                maya.cmds.namespace(setNamespace=self.rootNameSpace)

                skinSettings.deformerName = self.rebuildSkinCluster(skinSettings)

                maya.cmds.namespace(setNamespace=self.namespacePrefix)

            self.rebuildTime = float(processing.timeRange)

            self.skinWasrebuilt = True

            return

        if isSkinClusterDeformingCurrentShape is False:
            report = 'Please insure {skin} actually deforms {shape}'
            
            report = report.format(skin=skinSettings.deformerName,
                                   shape=skinSettings.shape)

            maya.OpenMaya.MGlobal.displayWarning(report)

            self.isInvalid = True
            return

        needsSkinClusterRebuilding = self.synchronizeDeformer(skinSettings.deformerName,
                                                              skinSettings.influences)

        if needsSkinClusterRebuilding is True:
            processing = TimeProcessor()
            processing.displayProgressbar = False
            processing.displayReport = False

            with processing:
                maya.cmds.namespace(setNamespace=self.rootNameSpace)

                skinSettings.deformerName = self.rebuildSkinCluster(skinSettings)

                maya.cmds.namespace(setNamespace=self.namespacePrefix)

            self.rebuildTime = float(processing.timeRange)

            self.skinWasrebuilt = True


class JointReport(object):
    def __init__(self):
        self.canFindAllJoints = True

        missingJoints = []


class SkinReport(object):
    def __init__(self):
        self.inputSkinNode = None

    def collectInfos(self, 
                     inputSkinNode):
        jointArray = maya.cmds.skinCluster(inputSkinNode, 
                                           q=True, 
                                           inf=True)

        geometry = maya.cmds.skinCluster(inputSkinNode, 
                                         q=True, 
                                         geometry=True)[0]
        
        return [len(jointArray), geometry]

    def publishReport(self, 
                      inputSkinNode, 
                      targetSkinFile, 
                      sampleLength):
        metaData = self.collectInfos(inputSkinNode)
        vertexCount = maya.cmds.polyEvaluate(metaData[1], v=True)

        componentReport = '\n<Skin Weights Saving report:>' 
        componentReport += '\n\tExport to {} was successful'.format(targetSkinFile) 
        componentReport += '\n\tGeometry {0}'.format(metaData[1]) 
        componentReport += '\n\t\tNumber of vertex {0}'.format(vertexCount)
        componentReport += '\n\t\tNumber of influences {0}'.format(metaData[0]) 
        componentReport += '\n\t\tNumber of weights Samples {0}'.format(sampleLength)

        return componentReport

    def publishImportReport(self, 
                            shape, 
                            inReport,
                            sourceAbcFile,
                            rebuildTime,
                            skinWasrebuilt):
        componentReport = '\n<Skin Weights Import report:>' 
        componentReport += '\n\tLoading data from {} .'.format(os.path.basename(sourceAbcFile)) 
        componentReport += '\n\tGeometry {0}'.format(shape) 

        if skinWasrebuilt:
            componentReport += '\n\tRebuilding skincluster took {0} seconds'.format(rebuildTime)

        componentReport += '\t{0}'.format(inReport) 

        return componentReport


class ClusterIO(object):
    def __init__(self):
        self.weights = maya.OpenMaya.MDoubleArray()
        self.indexArray = maya.OpenMaya.MIntArray()

        self.joint = ''

        #Possible values: cluster/All
        self.setType = ''


class SkinSet(object):
    FIRST_ITEM = 0

    def __init__(self, inputSkinCluster):
        self.shapePath = maya.OpenMaya.MDagPath()
        self.jointPaths = maya.OpenMaya.MDagPathArray()
        self.skinFunctionUtils = None
        self.pointComponentsUtils = None
        self.fullComponentPointSet = None
        self.componentType = None

        self.pointCount = 0

        self.shapeType = None

        self.influenceIndices = None

        self.oldValues = None

        self.weightUtils = None

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

    def getInfluenceIndices(self):
        self.oldValues = maya.OpenMaya.MDoubleArray()

        self.influenceIndices = maya.OpenMaya.MIntArray(self.jointPaths.length())

        for jointIndex in xrange(self.jointPaths.length()):
            self.influenceIndices.set(jointIndex,
                                      jointIndex)

    def getShapeFullComponents(self):
        simpleShapeType = ['mesh', 'nurbsCurve']
        
        self.shapeType = maya.cmds.nodeType(self.shapePath.fullPathName())

        if self.shapeType in simpleShapeType:
            self.componentType = maya.OpenMaya.MFn.kMeshVertComponent

            if self.shapeType == 'mesh':
                shapeFunctionUtils = maya.OpenMaya.MFnMesh(self.shapePath)
                self.pointCount = shapeFunctionUtils.numVertices()

                pointComponentFunction = maya.OpenMaya.MFnSingleIndexedComponent()

            elif self.shapeType == 'nurbsCurve':
                shapeFunctionUtils = maya.OpenMaya.MFnNurbsCurve(self.shapePath)
                self.pointCount = shapeFunctionUtils.numVertices()
                self.componentType = OpenMaya.MFn.kCurveCVComponent

            self.fullComponentPointSet = pointComponentFunction.create(self.componentType)
            pointComponentFunction.setCompleteData(self.pointCount)

        elif self.shapeType == 'nurbsSurface':
            self.componentType = maya.OpenMaya.MFn.kSurfaceCVComponent
            shapeFunctionUtils = maya.OpenMaya.MFnNurbsSurface(self.shapePath)

            self.pointCount = shapeFunctionUtils.numCVsInU() * shapeFunctionUtils.numCVsInV()

            pointComponentFunction = maya.OpenMaya.MFnDoubleIndexedComponent()
            self.fullComponentPointSet = pointComponentFunction.create(self.componentType)

            pointComponentFunction.setCompleteData(shapeFunctionUtils.numCVsInU(),
                                                   shapeFunctionUtils.numCVsInV())

        elif self.shapeType == 'lattice':
            self.componentType = maya.OpenMaya.MFn.kLatticeComponent
            shapeFunctionUtils = maya.OpenMaya.MFnLattice(self.shapePath)

            sDivivision = 0
            tDivivision = 0
            uDivivision = 0

            shapeFunctionUtils.getDivisions(sDivivision,
                                            tDivivision,
                                            uDivivision)

            self.pointCount = sDivivision * tDivivision * uDivivision

            pointComponentFunction = maya.OpenMaya.MFnTripleIndexedComponent()
            self.fullComponentPointSet = pointComponentFunction.create(self.componentType)
            
            pointComponentFunction.setCompleteData(sDivivision,
                                                   tDivivision,
                                                   uDivivision)

    def extractFromAlembic(self,
                           sourceAlembic,
                           abcNamespace):
        maya.cmds.AbcImport(sourceAlembic, 
                            mode='import')

        importAbcArray = maya.cmds.namespaceInfo(abcNamespace,
                                                 listNamespace=True)

        if len(importAbcArray)==0:
            anchorNode = importAbcArray[self.FIRST_ITEM]
            abcNode = self.getMObject(importAbcArray[self.FIRST_ITEM])
        else:
            anchorNode = None
            for node in importAbcArray:
                if maya.cmds.nodeType(node) == 'transform':
                    anchorNode = node

            abcNode = self.getMObject(anchorNode)

        skinAttribute = maya.cmds.listAttr(anchorNode,
                                           ud=True)

        dependNode = maya.OpenMaya.MFnDependencyNode(abcNode)

        attributePlug = dependNode.findPlug(skinAttribute[self.FIRST_ITEM],
                                            False)

        self.weightUtils = maya.OpenMaya.MFnDoubleArrayData(attributePlug.asMObject())

        maya.cmds.delete(anchorNode)


class SkinSettings(object):
    NODE_ATTRIBUTES = ('deformerName',
                       'shape',
                       'shapePath',
                       'influences',
                       'skinningMethod',
                       'normalizeWeights',
                       'abcWeightsFile')

    def __init__(self, 
                 skinDeformer,
                 collectData=True):
        self.deformerName = None
        self.shape = None
        self.shapePath = None
        self.influences = []

        self.skinningMethod = 0
        self.normalizeWeights = False
        self.abcWeightsFile = None

        self.processingTime = 0
        self.report = ''

        if collectData is False:
            return

        self.skinDeformer = skinDeformer

        self.getSkinSettings()

    def getSkinSettings(self):
        self.deformerName = self.skinDeformer
        self.influences = maya.cmds.skinCluster(self.skinDeformer,
                                                q=True,
                                                inf=True)

        self.skinningMethod = maya.cmds.getAttr('{}.skinningMethod'.format(self.skinDeformer))
        self.normalizeWeights = maya.cmds.getAttr('{}.normalizeWeights'.format(self.skinDeformer))

        self.shape = maya.cmds.skinCluster(self.skinDeformer,
                                           q=True,
                                           geometry=True)[0]

    def toJson(self):
        return json.dumps(self, 
                          cls=ObjectEncoder, 
                          indent=2, 
                          sort_keys=True)

    def fromJson(self,
                 inputSkinSettings):
        for key in inputSkinSettings:
            if hasattr(self, key):
                setattr(self, key, inputSkinSettings[key])

    def __repr__(self):
        reportData = '<{0}'.format(self.__class__.__name__)

        for attribute in self.NODE_ATTRIBUTES:
            reportData += '\n\t{0}: {1}'.format(attribute, 
                                                getattr(self,attribute))

        reportData += '>'
        return reportData


class ShapeSettings(object):
    def __init__(self, shape):
        self.shape = shape
        self.shapePath = maya.OpenMaya.MDagPath()
        self.transform = None
        self.pointCount = 0
        self.shapeType = ''

        self.uCount = 0
        self.vCount = 0
        self.wCount = 0

        self.getShapeSettings()

    def getMObject(self, nodeName):
        selList = maya.OpenMaya.MSelectionList()
        maya.OpenMaya.MGlobal.getSelectionListByName(nodeName, 
                                                     selList)
        depNode = maya.OpenMaya.MObject()
        selList.getDependNode(0, depNode) 

        return depNode

    def getShapeSettings(self):
        self.transform = maya.cmds.listRelatives(self.shape, p=True)[0]
        shapeApiObject = self.getMObject(self.shape)

        maya.OpenMaya.MDagPath.getAPathTo(shapeApiObject,
                                          self.shapePath)    

        pointCount = 0
        simpleShapeType = ['mesh', 'nurbsCurve']
        self.shapeType = maya.cmds.nodeType(self.shape)

        if self.shapeType in simpleShapeType:
            componentType = maya.OpenMaya.MFn.kMeshVertComponent

            if self.shapeType == 'mesh':
                shapeFunctionUtils = maya.OpenMaya.MFnMesh(self.shapePath)
                self.pointCount = shapeFunctionUtils.numVertices()

            elif self.shapeType == 'nurbsCurve':
                shapeFunctionUtils = maya.OpenMaya.MFnNurbsCurve(self.shapePath)
                self.pointCount = shapeFunctionUtils.numVertices()

            self.uCount = int(self.pointCount)

        elif self.shapeType == 'nurbsSurface':
            shapeFunctionUtils = maya.OpenMaya.MFnNurbsSurface(self.shapePath)

            self.uCount = shapeFunctionUtils.numCVsInU()
            self.wCount = shapeFunctionUtils.numCVsInV()

            self.pointCount = shapeFunctionUtils.numCVsInU() * shapeFunctionUtils.numCVsInV()

        elif self.shapeType == 'lattice':
            componentType = maya.OpenMaya.MFn.kLatticeComponent
            shapeFunctionUtils = maya.OpenMayaAnim.MFnLattice(self.shapePath)

            sDivivisionParam = maya.OpenMaya.MScriptUtil()
            sDivivisionParam.createFromInt(0)    
            sDivivisionPtr = sDivivisionParam.asUintPtr()    

            tDivivisionParam = maya.OpenMaya.MScriptUtil()
            tDivivisionParam.createFromInt(0)    
            tDivivisionPtr = tDivivisionParam.asUintPtr()  

            uDivivisionParam = maya.OpenMaya.MScriptUtil()
            uDivivisionParam.createFromInt(0)    
            uDivivisionPtr = uDivivisionParam.asUintPtr()  

            shapeFunctionUtils.getDivisions(sDivivisionPtr,
                                            tDivivisionPtr,
                                            uDivivisionPtr)

            sDivivision = maya.OpenMaya.MScriptUtil(sDivivisionPtr).asInt()
            tDivivision = maya.OpenMaya.MScriptUtil(tDivivisionPtr).asInt()
            uDivivision = maya.OpenMaya.MScriptUtil(uDivivisionPtr).asInt()

            self.uCount = sDivivision
            self.vCount = tDivivision
            self.wCount = uDivivision

            self.pointCount = sDivivision * tDivivision * uDivivision

    def getComponent(self, pointIndex):
        simpleShapeType = ['mesh', 'nurbsCurve']
        if self.shapeType in simpleShapeType:
            return '{shape}.vtx[{pointIndex}]'.format(shape=self.transform,
                                                      pointIndex=pointIndex)

        elif self.shapeType == 'nurbsSurface':
            targetRow = pointIndex / self.vCount
            targetColumn = pointIndex - targetRow
            return '{shape}.cv[{row1}][{row2}]'.format(shape=self.transform,
                                                       row1=targetRow,
                                                       row2=targetColumn)

        elif self.shapeType == 'lattice':
            heightRatio = (self.uCount*self.vCount)
            targetHeight = pointIndex / heightRatio

            heightLevel = heightRatio*targetHeight
            rowLevel = (heightLevel - targetHeight)

            #print targetHeight, heightRatio, heightLevel, rowLevel, pointIndex

            targetRow = pointIndex / self.vCount
            targetColumn = pointIndex - targetRow
            return '{shape}.pt[{row1}][{row2}][{row3}]'.format(shape=self.transform,
                                                               row1=targetColumn,
                                                               row2=targetRow,
                                                               row3=targetHeight)


class PointWeights(object):
    def __init__(self):
        self.timeProcessing = TimeProcessor()

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

        skinSettings = SkinSettings(skinNode)
        shapeSettings = ShapeSettings(skinSettings.shape)

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
        self.timeProcessing = TimeProcessor()

        self.batchProcessing = TimeProcessor()

        self.processingTime = 0

        self.reportArray = []

        self.reporter = SkinReport()

        self.skinNodeArray = []

        self.sceneWeights = []

        self.skinMetadata = {}

        self.mayaFileType = "mayaAscii"

    def getSkinNodeArray(self,
                         objectArray):
        self.skinNodeArray = []

        for inputTransform in objectArray:
            validationUtils = SkinValidator()
            inputSkinNodes = validationUtils.getSkinHistory(inputTransform)

            if len(inputSkinNodes) == 0:
                continue

            self.skinNodeArray.append(inputSkinNodes[0])

    def saveSettings(self, 
                     targetArchiveFile,
                     unpackDirectory,
                     outputSkinSettings):
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
        with zipfile.ZipFile(targetArchiveFile, 
                             'wb', 
                             compression=zipfile.ZIP_DEFLATED) as outputZip:
            outputZip.write(jsonSkinFile, r'{0}'.format(jsonSkinFileName))

            for component in sceneWeights:
                zipName = os.path.basename(component.abcWeightsFile)
                outputZip.write(component.abcWeightsFile, r'%s'%zipName)

    def transferToDisk(self, 
                       skin, 
                       targetSkinFile):
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
        self.timeProcessing.report = ''

        self.timeProcessing.processObjectCount = 0

        validationUtils = SkinValidator()
        inputSkinNodes = validationUtils.getSkinHistory(inputTransform)

        if len(inputSkinNodes) == 0:
            return None

        skinSettings = None

        skinSettings = SkinSettings(inputSkinNodes[0])
        skinSettings.shape = maya.cmds.listRelatives(inputTransform,
                                                     s=True,
                                                     fullPath=True)[0]

        return skinSettings

    def collectSkinSettings(self,
                            objectArray,
                            unpackDirectory,
                            exposeWeightDetails):
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
        self.batchProcessing = TimeProcessor()
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

        with SelectionSaved(), TemporaryDirectory(dir=neighbourFolder) as unpackDirectory:
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
        skinSettings = SkinSettings(None,
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
        with self.timeProcessing, TemporaryNamespace(None,
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
        skinInput = SkinSet(inputSkinCluster)
        skinInput.getShapeFullComponents()

        skinData = ClusterIO()
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
        skinData = SkinSet(currentSkinCluster)

        skinData.getShapeFullComponents()

        skinData.getInfluenceIndices()

        skinData.extractFromAlembic(sourceAlembic,
                                    "skinNamespace_weights")

        with SkinDisabled(currentSkinCluster):
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
        self.timeProcessing = TimeProcessor()

        self.reporter = SkinReport()

        self.skinProcessor = None

        self.skinHandler = 'alembicIO'

        self.reportArray = []

        self.processingTime = 0

    def importFromAlembic(self, 
                          jsonDataArray,
                          unpackDirectory,
                          batchProcessing):
        self.skinProcessor = AlembicInjection()

        validationUtils = SkinValidator()

        validationUtils.rootNameSpace = maya.cmds.namespaceInfo(currentNamespace=True)

        validationUtils.namespacePrefix = self.WEIGHT_NAMESPACE

        with TemporaryNamespace(validationUtils.rootNameSpace,
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

        validationUtils = SkinValidator()

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
            skinData = SkinSettings(None,
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

        batchProcessing = TimeProcessor()
        batchProcessing.displayProgressbar = showProgressbar
        batchProcessing.displayReport = False
        batchProcessing.progressbarRange = len(jsonSettings)

        with batchProcessing:
            with TemporaryDirectory() as unpackDirectory, \
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