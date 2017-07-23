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

import maya.cmds 

import os
import posixpath 
import tempfile
import time
import shutil


class SelectionSaved(object):
    """
        Python context which will restore the current selection of object
    """
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
    """
        Python context used for skinweight IO
    """
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
    """
        Time stamping utility context
    """
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
    """
        namespace utility use to isoled imported object with 
        namespace and clean it up once processing is done
    """
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
    """
        Temporary directory used for compressing/decompressing archive elements
    """
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
