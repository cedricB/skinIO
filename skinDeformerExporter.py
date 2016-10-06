import xml.etree.ElementTree
import time
import maya.mel as mel
import maya.cmds as cmds


class SkinDeformerExporter(object):
    def __init__(self, path=None):
        self.path = path
        self.shapes = {}
        self.fileName = None
        
        if self.path:
            self.parseFile(self.path)
    
    class skinnedShape(object):
        def __init__(self, joints=None, shape=None, skin=None, verts=None):
            self.joints = joints
            self.shape = shape
            self.skin = skin
            self.verts = verts
    
    def applyWeightInfo(self):
        for shape in self.shapes:
            #make a skincluster using the joints
            if cmds.objExists(shape):
                ss = self.shapes[shape]
                skinList = ss.joints
                skinList.append(shape)
                cmds.select(skinList, r=True)
                cluster = cmds.skinCluster(name=ss.skin, tsb=1)
                cmds.deformerWeights(fname , path = fpath, deformer=ss.skin, im=1)
    
    def saveWeightInfo(self, fpath, meshes, all=True):
        t1 = time.time()
        
        #get skin clusters
        meshDict = {}
        for mesh in meshes:
            sc = mel.eval('findRelatedSkinCluster '+mesh)
            #not using shape atm, mesh instead
            msh =  cmds.listRelatives(mesh, shapes=1)
            if sc != '':
                meshDict[sc] = mesh
            else:
                cmds.warning('>>>saveWeightInfo: ' + mesh + ' is not connected to a skinCluster!')
        
        for skin in meshDict:
            cmds.deformerWeights(meshDict[skin] + '.skinWeights', path=fpath, ex=True, deformer=skin)
        
        elapsed = time.time()-t1
        print 'Exported skinWeights for', len(meshes), 'meshes in', elapsed, 'seconds.'
    
    def parseFile(self, path):
        root = xml.etree.ElementTree.parse(path).getroot()
        
        #set the header info
        for atype in root.findall('headerInfo'):
            self.fileName = atype.get('fileName')
        
        for atype in root.findall('weights'):
            jnt = atype.get('source')
            shape = atype.get('shape')
            clusterName = atype.get('deformer')
            
            if shape not in self.shapes.keys():
                self.shapes[shape] = self.skinnedShape(shape=shape, skin=clusterName, joints=[jnt])
            else:
                s = self.shapes[shape]
                s.joints.append(jnt)