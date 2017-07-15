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

from skinIO import context


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
            meshNodes = maya.cmds.listRelatives(inputTransform, 
                                                s=True, 
                                                fullPath=True)

        if meshNodes is None or len(meshNodes) < 1 :
            return []

        for shape in meshNodes:
            skinHistory = maya.cmds.ls(list(set(maya.cmds.listHistory(inputTransform))), 
                                       type='skinCluster')

            if skinHistory != None or len(skinHistory) > 0 :
                skinClusters.extend(skinHistory)

        skinShaped = meshNodes[0].split('|')[-1]
        if skinClusters != None or len(skinClusters) > 0 :
            for skin in skinClusters:
                if skin not in outputSkins:
                    SkinSet = maya.cmds.ls(maya.cmds.listConnections('%s.message'% skin), 
                                                                     type='objectSet')[0]

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
                unorderJointSet.append([joint, 
                                        currentInfluenceIndex,  
                                        jointIndex])

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
                                                 maya.cmds.listRelatives(skinSettings.shape,
                                                                         p=True),
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
            processing = context.TimeProcessor()
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
            processing = context.TimeProcessor()
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