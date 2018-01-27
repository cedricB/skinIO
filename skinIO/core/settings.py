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
import getpass
import datetime


for pluginName in ('AbcExport',
                   'AbcImport'):
    if maya.cmds.pluginInfo(pluginName, 
                            query=True,
                           loaded=True):
        continue
    maya.cmds.loadPlugin(pluginName)


class ObjectEncoder(json.JSONEncoder):
    def default(self, inputObject):
        if hasattr(inputObject, "to_json"):
            jsonDict = inputObject.to_json()

            if 'NODE_ATTRIBUTES' in jsonDict:
                jsonDict.pop('NODE_ATTRIBUTES')

            return self.default(jsonDict)
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
            if 'NODE_ATTRIBUTES' in jsonDict:
                jsonDict.pop('NODE_ATTRIBUTES')

            return self.default(jsonDict)
        return inputObject


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

            pointComponentFunction = maya.OpenMaya.MFnSingleIndexedComponent()

            if self.shapeType == 'mesh':
                shapeFunctionUtils = maya.OpenMaya.MFnMesh(self.shapePath)
                self.pointCount = shapeFunctionUtils.numVertices()

            elif self.shapeType == 'nurbsCurve':
                shapeFunctionUtils = maya.OpenMaya.MFnNurbsCurve(self.shapePath)
                self.pointCount = shapeFunctionUtils.numCVs()
                self.componentType = maya.OpenMaya .MFn.kCurveCVComponent

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

    def extractEmptyWeights(self):
        self.weightUtils = OpenMaya.MDoubleArray(self.pointCount, 0.0)


class InjectionSettings(object):
    def __init__(self,
                 weightMode,
                 fillStructure=True):
        self.weightMode = ''

        self.assetScene = ''

        self.userName = ''

        self.saveTime = ''

        self.collect(weightMode)

    def collect(self,
                weightMode):
        self.weightMode = weightMode

        self.assetScene = maya.cmds.file(q=True,
                                         sceneName=True)

        self.userName = getpass.getuser()

        self.saveTime = str(datetime.datetime.now())

    def parseJsonFromArchive(self,
                             sourceArchiveFile):
        if not os.path.exists(sourceArchiveFile):
            return False

        with zipfile.ZipFile(sourceArchiveFile, 'r') as archive:
            jsonList = [info.filename for info in archive.infolist() 
                        if info.filename.endswith('.mod')]

            jsonInput = [json.loads(archive.read(jsonElement)) for jsonElement in jsonList][0]

            self.fromJson(jsonInput)

        return True

    def toJson(self):
        return json.dumps(self, 
                          cls=ObjectEncoder, 
                          indent=2, 
                          sort_keys=True)

    def fromJson(self,
                 inputSettings):
        for key in inputSettings:
            if hasattr(self, key):
                setattr(self, key, inputSettings[key])


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
    def __init__(self, 
                 shape):
        self.shape = shape
        self.shapePath = maya.OpenMaya.MDagPath()
        self.transform = None
        self.pointCount = 0
        self.shapeType = ''

        self.uCount = 0
        self.vCount = 0
        self.wCount = 0

        self.getShapeSettings()

    @staticmethod
    def getShapeFromTransform(transformName):
        inputShapeArray = maya.cmds.listRelatives(transformName,
                                                  s=True,
                                                  ni=True)

        if not inputShapeArray:
            return None

        for currentShape in inputShapeArray:
            shapeApiObject = ShapeSettings.getMObject(inputShapeArray[0])
            shapePath = maya.OpenMaya.MDagPath()

            maya.OpenMaya.MDagPath.getAPathTo(shapeApiObject,
                                              shapePath)

            geometryProcessor = maya.OpenMaya.MItGeometry(shapePath)
            if geometryProcessor.count()==0:
                return None

        return inputShapeArray[0]

    @staticmethod
    def getMObject(nodeName):
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