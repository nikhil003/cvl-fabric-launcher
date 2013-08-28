# MASSIVE/CVL Launcher - easy secure login for the MASSIVE Desktop and the CVL
#
# Copyright (c) 2012-2013, Monash e-Research Centre (Monash University, Australia)
# All rights reserved.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version.
#
# In addition, redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# -  Redistributions of source code must retain the above copyright
# notice, this list of conditions and the following disclaimer.
#
# -  Redistributions in binary form must reproduce the above copyright
# notice, this list of conditions and the following disclaimer in the
# documentation and/or other materials provided with the distribution.
#
# -  Neither the name of the Monash University nor the names of its
# contributors may be used to endorse or promote products derived from
# this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
# IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE. SEE THE
# GNU GENERAL PUBLIC LICENSE FOR MORE DETAILS.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# Enquires: help@massive.org.au

# launcher.py
"""
A wxPython GUI to provide easy login to the MASSIVE Desktop.
It can be run using "python launcher.py", assuming that you
have a 32-bit (*) version of Python installed,
wxPython, and the dependent Python modules imported below.

(*) wxPython on Mac OS X doesn't yet work nicely in 64-bit mode.

The py2app module is required to build the "CVL Launcher.app"
application bundle on Mac OS X, which can be built as follows:

   python create_mac_bundle.py py2app

See: https://confluence-vre.its.monash.edu.au/display/CVL/MASSIVE+Launcher+Mac+OS+X+build+instructions

The py2exe module is required to build the "CVL Launcher.exe"
executable on Windows, which can be built as follows:

   python create_windows_bundle.py py2exe

See: https://confluence-vre.its.monash.edu.au/display/CVL/MASSIVE+Launcher+Windows+build+instructions

A Windows installation wizard can be built using InnoSetup,
and the CVL.iss script.

A self-contained Linux binary distribution can be built using
PyInstaller, as described on the following wiki page.

See: https://confluence-vre.its.monash.edu.au/display/CVL/MASSIVE+Launcher+Linux+build+instructions

ACKNOWLEDGEMENT

Thanks to Michael Eager for a concise, non-GUI Python script
which demonstrated the use of the Python pexpect module to
automate SSH logins and to automate calling TurboVNC
on Linux and on Mac OS X.

"""


# Make sure that the Launcher doesn't attempt to write to
# "CVL Launcher.exe.log", because it might not have
# permission to do so.
import sys
if sys.platform.startswith("win"):
    sys.stderr = sys.stdout

if sys.platform.startswith("win"):
    import _winreg
import subprocess
import wx
import time
import traceback
import threading
import os
import HTMLParser
import urllib2
import launcher_version_number
import xmlrpclib
import appdirs
import ConfigParser
import datetime
import shlex
import inspect
import requests
import ssh
from StringIO import StringIO
import logging
import LoginTasks
from utilityFunctions import *
import cvlsshutils.sshKeyDist
import cvlsshutils
import launcher_progress_dialog
from menus.IdentityMenu import IdentityMenu
import tempfile
from cvlsshutils.KeyModel import KeyModel

from MacMessageDialog import LauncherMessageDialog
from logger.Logger import logger

global launcherMainFrame
launcherMainFrame = None
global launcherConfig
global turboVncConfig
turboVncConfig = None
global massiveLauncherPreferencesFilePath
massiveLauncherPreferencesFilePath = None
global cvlLauncherPreferencesFilePath
cvlLauncherPreferencesFilePath = None
global turboVncPreferencesFilePath
turboVncPreferencesFilePath = None
global turboVncLatestVersion
turboVncLatestVersion = None

class LauncherMainFrame(wx.Frame):
    PERM_SSH_KEY=0
    TEMP_SSH_KEY=1


    def shouldSave(self,item):
        # I should be able to use a python iterator here
        shouldSave=False
        for ctrl in self.savedControls:
            if isinstance(item,ctrl):
                shouldSave=True
        return shouldSave

    
    def loadPrefs(self,window=None,site=None):
        if (self.prefs==None):
            self.prefs=ConfigParser.RawConfigParser(allow_no_value=True)
            if (os.path.exists(launcherPreferencesFilePath)):
                with open(launcherPreferencesFilePath,'r') as o:
                    self.prefs.readfp(o)
        if window==None:
            window=self
        if (site==None):
            siteConfigComboBox=self.FindWindowByName('jobParams_configName')
            site=siteConfigComboBox.GetValue()
            if (site==None or site==""):
                if self.prefs.has_option("Launcher Config","siteConfigDefault"):
                    siteConfigDefault = self.prefs.get("Launcher Config","siteConfigDefault")
                    if siteConfigDefault in self.sites.keys():
                        siteConfigComboBox.SetValue(siteConfigDefault)
                        site=siteConfigDefault
                        self.loadPrefs(window=self,site=site)
                        self.updateVisibility()
        if (site != None):
            if self.prefs.has_section(site):
                for item in window.GetChildren():
                    if self.shouldSave(item):
                        name=item.GetName()
                        if self.prefs.has_option(site,name):
                            val=self.prefs.get(site,name)
                            try: # Most wx Controls expect a string in SetValue, but at least SpinCtrl expects an int.
                                item.SetValue(val)
                            except TypeError:
                                item.SetValue(int(val))
                    else:
                        self.loadPrefs(window=item,site=site)

    def savePrefsEventHandler(self,event):
        threading.Thread(target=self.savePrefs).start()
        event.Skip()
        
    def savePrefs(self,prefs=None,window=None,site=None):
        write=False
        # If we called savePrefs without a window specified, its the root of recussion
        if (window==None):
            write=True
            window=self
        if (site==None):
            configName=self.FindWindowByName('jobParams_configName').GetValue()
            if (configName!=None):
                if (not self.prefs.has_section("Launcher Config")):
                    self.prefs.add_section("Launcher Config")
                self.prefs.set("Launcher Config","siteConfigDefault",configName)
                self.savePrefs(prefs=prefs,site=configName)
        elif (site!=None):
            if (not self.prefs.has_section(site)):
                self.prefs.add_section(site)
            for item in window.GetChildren():
                if self.shouldSave(item):
                    self.prefs.set(site,item.GetName(),item.GetValue())
                else:
                    self.savePrefs(prefs=prefs,site=site,window=item)
        if (write):
            with open(launcherPreferencesFilePath,'w') as o:
                self.prefs.write(o)


    def __init__(self, parent, id, title):

#        global launcherMainFrame
#        launcherMainFrame = self
        # List all the types of control that should be saved explicitly since apparently StaticText et al inherit from wx.Control
        self.savedControls=[]
        self.savedControls.append(wx.TextCtrl)
        self.savedControls.append(wx.ComboBox)
        self.savedControls.append(wx.SpinCtrl)

        self.prefs=None
        self.loginProcess=[]
        self.logWindow = None
        self.progressDialog = None


        if sys.platform.startswith("darwin"):
            wx.Frame.__init__(self, parent, id, title, style=wx.DEFAULT_FRAME_STYLE ^ wx.RESIZE_BORDER)
        else:
            wx.Frame.__init__(self, parent, id, title, style=wx.DEFAULT_FRAME_STYLE ^ wx.RESIZE_BORDER)

        self.vncOptions = {}
        import optionsDialog
        if len(self.vncOptions)==0:
            if turboVncConfig.has_section("TurboVNC Preferences"):
                savedTurboVncOptions =  turboVncConfig.items("TurboVNC Preferences")
                for option in savedTurboVncOptions:
                    key = option[0]
                    value = option[1]
                    if value=='True':
                        value = True
                    if value=='False':
                        value = False
                    self.vncOptions[key] = value

        self.launcherOptionsDialog = optionsDialog.LauncherOptionsDialog(self, wx.ID_ANY, "VNC Options", self.vncOptions, 0)
        self.launcherOptionsDialog.Show(False)

        if turboVncConfig.has_section("TurboVNC Preferences"):
            savedTurboVncOptions =  turboVncConfig.items("TurboVNC Preferences")
            for option in savedTurboVncOptions:
                key = option[0]
                value = option[1]
                if value=='True':
                    value = True
                if value=='False':
                    value = False
                self.vncOptions[key] = value
        import optionsDialog
        self.launcherOptionsDialog = optionsDialog.LauncherOptionsDialog(launcherMainFrame, wx.ID_ANY, "Preferences", self.vncOptions, 0)

        if sys.platform.startswith("win"):
            _icon = wx.Icon('MASSIVE.ico', wx.BITMAP_TYPE_ICO)
            self.SetIcon(_icon)

        if sys.platform.startswith("linux"):
            import MASSIVE_icon
            self.SetIcon(MASSIVE_icon.getMASSIVElogoTransparent128x128Icon())

        self.menu_bar  = wx.MenuBar()

        self.file_menu = wx.Menu()
        self.menu_bar.Append(self.file_menu, "&File")
        shareDesktop=wx.MenuItem(self.file_menu,wx.ID_ANY,"&Share my Desktop")
        self.file_menu.AppendItem(shareDesktop)
        self.Bind(wx.EVT_MENU, self.saveSessionEvent, id=shareDesktop.GetId())
        loadSession=wx.MenuItem(self.file_menu,wx.ID_ANY,"&Load a saved Session")
        self.file_menu.AppendItem(loadSession)
        self.Bind(wx.EVT_MENU, self.loadSessionEvent, id=loadSession.GetId())
        loadDefaultSessions=wx.MenuItem(self.file_menu,wx.ID_ANY,"&Load default sessions")
        self.file_menu.AppendItem(loadDefaultSessions)
        self.Bind(wx.EVT_MENU, self.loadDefaultSessionsEvent, id=loadDefaultSessions.GetId())
        if sys.platform.startswith("win") or sys.platform.startswith("linux"):
            self.file_menu = wx.Menu()
            self.file_menu.Append(wx.ID_EXIT, "E&xit", "Close window and exit program.")
            self.Bind(wx.EVT_MENU, self.onExit, id=wx.ID_EXIT)
           
            

        #if sys.platform.startswith("darwin"):
            ## Only do this for Mac OS X, because other platforms have
            ## a right-click pop-up menu for wx.TextCtrl with Copy,
            ## Select All etc. Plus, the menu doesn't look that good on
            ## the MASSIVE Launcher main dialog, and doesn't work for
            ## non Mac platforms, because FindFocus() will always
            ## find the window/dialog which contains the menu.
            #self.edit_menu = wx.Menu()
            #self.edit_menu.Append(wx.ID_CUT, "Cut", "Cut the selected text")
            #self.Bind(wx.EVT_MENU, self.onCut, id=wx.ID_CUT)
            #self.edit_menu.Append(wx.ID_COPY, "Copy", "Copy the selected text")
            #self.Bind(wx.EVT_MENU, self.onCopy, id=wx.ID_COPY)
            #self.edit_menu.Append(wx.ID_PASTE, "Paste", "Paste text from the clipboard")
            #self.Bind(wx.EVT_MENU, self.onPaste, id=wx.ID_PASTE)
            #self.edit_menu.Append(wx.ID_SELECTALL, "Select All")
            #self.Bind(wx.EVT_MENU, self.onSelectAll, id=wx.ID_SELECTALL)
            #self.menu_bar.Append(self.edit_menu, "&Edit")
        self.edit_menu = wx.Menu()
        self.edit_menu.Append(wx.ID_CUT, "Cu&t", "Cut the selected text")
        self.Bind(wx.EVT_MENU, self.onCut, id=wx.ID_CUT)
        self.edit_menu.Append(wx.ID_COPY, "&Copy", "Copy the selected text")
        self.Bind(wx.EVT_MENU, self.onCopy, id=wx.ID_COPY)
        self.edit_menu.Append(wx.ID_PASTE, "&Paste", "Paste text from the clipboard")
        self.Bind(wx.EVT_MENU, self.onPaste, id=wx.ID_PASTE)
        self.edit_menu.Append(wx.ID_SELECTALL, "Select &All")
        self.Bind(wx.EVT_MENU, self.onSelectAll, id=wx.ID_SELECTALL)
        self.edit_menu.AppendSeparator()
        if sys.platform.startswith("win") or sys.platform.startswith("linux"):
            self.edit_menu.Append(wx.ID_PREFERENCES, "P&references\tCtrl-P")
        else:
            self.edit_menu.Append(wx.ID_PREFERENCES, "&Preferences")
        self.Bind(wx.EVT_MENU, self.onOptions, id=wx.ID_PREFERENCES)
        self.menu_bar.Append(self.edit_menu, "&Edit")

        self.identity_menu = IdentityMenu()
        self.identity_menu.initialize(self, massiveLauncherConfig, massiveLauncherPreferencesFilePath)
        self.menu_bar.Append(self.identity_menu, "&Identity")

        self.help_menu = wx.Menu()
        helpContentsMenuItemID = wx.NewId()
        self.help_menu.Append(helpContentsMenuItemID, "&MASSIVE/CVL Launcher Help")
        self.Bind(wx.EVT_MENU, self.onHelpContents, id=helpContentsMenuItemID)
        self.help_menu.Append(wx.ID_ABOUT,   "&About MASSIVE/CVL Launcher")
        self.Bind(wx.EVT_MENU, self.onAbout, id=wx.ID_ABOUT)
        self.menu_bar.Append(self.help_menu, "&Help")

        self.SetTitle("MASSIVE / CVL Launcher")

        self.SetMenuBar(self.menu_bar)

        self.AUTOLAYOUT=1
        self.SetAutoLayout(self.AUTOLAYOUT)
        self.loginDialogPanel = wx.Panel(self, wx.ID_ANY)
        self.loginDialogPanel.SetAutoLayout(self.AUTOLAYOUT)
        self.loginDialogPanelSizer = wx.BoxSizer(wx.VERTICAL)
        self.loginDialogPanel.SetSizer(self.loginDialogPanelSizer)

        self.loginFieldsPanel = wx.Panel(self.loginDialogPanel, wx.ID_ANY)
        self.loginFieldsPanel.SetAutoLayout(self.AUTOLAYOUT)
        self.loginFieldsPanelSizer = wx.BoxSizer(wx.VERTICAL)
        self.loginFieldsPanel.SetSizer(self.loginFieldsPanelSizer)

        widgetWidth1 = 180
        widgetWidth2 = 180
        if not sys.platform.startswith("win"):
            widgetWidth2 = widgetWidth2 + 25
        widgetWidth3 = 75

        DEFAULT_SITES_JSON='defaultSites.json'
        self.defaultSites={}
        with open(DEFAULT_SITES_JSON,'r') as f:
            self.defaultSites=GenericJSONDecoder().decode(f.read())
        
        self.noneVisible={}
        self.noneVisible['usernamePanel']=False
        self.noneVisible['projectPanel']=False
        self.noneVisible['resourcePanel']=False
        self.noneVisible['resolutionPanel']=False
        self.noneVisible['cipherPanel']=False
        self.noneVisible['debugCheckBoxPanel']=False
        self.noneVisible['advancedCheckBoxPanel']=False
        self.noneVisible['optionsDialog']=False

        self.sites=self.defaultSites.copy()

        self.siteConfigPanel = wx.Panel(self.loginFieldsPanel, wx.ID_ANY)
        self.siteConfigPanel.SetAutoLayout(self.AUTOLAYOUT)
        self.siteConfigPanel.SetSizer(wx.BoxSizer(wx.HORIZONTAL))
        self.configLabel = wx.StaticText(self.siteConfigPanel, wx.ID_ANY, 'Site')
        self.siteConfigPanel.GetSizer().Add(self.configLabel, proportion=0, flag=wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.EXPAND, border=5)
        self.siteConfigComboBox = wx.ComboBox(self.siteConfigPanel, wx.ID_ANY, choices=self.sites.keys(), value='', style=wx.CB_READONLY,name='jobParams_configName')
        self.siteConfigComboBox.Bind(wx.EVT_TEXT, self.onSiteConfigChanged)
        self.siteConfigPanel.GetSizer().Add(self.siteConfigComboBox, proportion=1,flag=wx.EXPAND|wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.EXPAND|wx.ALIGN_CENTER_VERTICAL, border=5)
        self.siteConfigPanel.Fit()
        self.loginFieldsPanel.GetSizer().Add(self.siteConfigPanel,proportion=0,flag=wx.EXPAND)

        self.usernamePanel=wx.Panel(self.loginFieldsPanel,name='usernamePanel')
        self.usernamePanel.SetAutoLayout(self.AUTOLAYOUT)
        self.usernamePanel.SetSizer(wx.BoxSizer(wx.HORIZONTAL))
        self.usernameLabel = wx.StaticText(self.usernamePanel, wx.ID_ANY, 'Username',name='label_username')
        self.usernamePanel.GetSizer().Add(self.usernameLabel, proportion=1,flag=wx.EXPAND|wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.ALIGN_CENTER_VERTICAL, border=5)
        self.usernameTextField = wx.TextCtrl(self.usernamePanel, wx.ID_ANY, size=(widgetWidth2, -1),name='jobParams_username')
        self.usernamePanel.GetSizer().Add(self.usernameTextField, flag=wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.EXPAND|wx.ALIGN_CENTER_VERTICAL, border=5)
        self.usernamePanel.Fit()
        self.loginFieldsPanel.GetSizer().Add(self.usernamePanel,proportion=0,flag=wx.EXPAND)

        self.projectPanel = wx.Panel(self.loginFieldsPanel,wx.ID_ANY,name="projectPanel")
        self.projectPanel.SetSizer(wx.BoxSizer(wx.HORIZONTAL))
        self.projectPanel.SetAutoLayout(self.AUTOLAYOUT)
        self.projectLabel = wx.StaticText(self.projectPanel, wx.ID_ANY, 'Project')
        self.projectPanel.GetSizer().Add(self.projectLabel, proportion=1, flag=wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.ALIGN_CENTER_VERTICAL|wx.EXPAND, border=5)

        self.defaultProjectPlaceholder = '[Use my default project]'
        self.projects = ['[Use my default projec]']
        self.projectField = wx.ComboBox(self.projectPanel, wx.ID_ANY, value='', choices=self.projects, size=(widgetWidth2, -1), style=wx.CB_DROPDOWN,name='jobParams_project')
        #self.projectComboBox.Bind(wx.EVT_TEXT, self.onProjectTextChanged)
        self.projectPanel.GetSizer().Add(self.projectField, flag=wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.ALIGN_CENTER_VERTICAL, border=5)
        self.projectPanel.Fit()
        self.loginFieldsPanel.GetSizer().Add(self.projectPanel, proportion=0,flag=wx.EXPAND|wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.EXPAND|wx.ALIGN_CENTER_VERTICAL)


        self.resourcePanel = wx.Panel(self.loginFieldsPanel, wx.ID_ANY,name="resourcePanel")
        self.resourcePanel.SetAutoLayout(self.AUTOLAYOUT)
        self.resourcePanel.SetSizer(wx.BoxSizer(wx.HORIZONTAL))

        self.hoursLabel = wx.StaticText(self.resourcePanel, wx.ID_ANY, 'Hours requested')
        self.resourcePanel.GetSizer().Add(self.hoursLabel, proportion=1,flag=wx.EXPAND|wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.ALIGN_CENTER_VERTICAL,border=5)
        # Maximum of 336 hours is 2 weeks:
        #self.massiveHoursField = wx.SpinCtrl(self.massiveLoginFieldsPanel, wx.ID_ANY, value=self.massiveHoursRequested, min=1,max=336)
        self.hoursField = wx.SpinCtrl(self.resourcePanel, wx.ID_ANY, size=(widgetWidth3,-1), min=1,max=336,name='jobParams_hours')
        self.resourcePanel.GetSizer().Add(self.hoursField, proportion=0,flag=wx.TOP|wx.BOTTOM|wx.RIGHT|wx.ALIGN_CENTER_VERTICAL,border=5)
        self.nodesLabel = wx.StaticText(self.resourcePanel, wx.ID_ANY, 'Vis nodes')
        self.resourcePanel.GetSizer().Add(self.nodesLabel, proportion=0,flag=wx.EXPAND|wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.ALIGN_CENTER_VERTICAL,border=5)
        self.nodesField = wx.SpinCtrl(self.resourcePanel, wx.ID_ANY, value="1", size=(widgetWidth3,-1), min=1,max=10,name='jobParams_nodes')
        self.resourcePanel.GetSizer().Add(self.nodesField, flag=wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.EXPAND|wx.ALIGN_CENTER_VERTICAL, border=5)
        self.resourcePanel.Fit()
        self.loginFieldsPanel.GetSizer().Add(self.resourcePanel, proportion=0,border=0,flag=wx.EXPAND|wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.EXPAND|wx.ALIGN_CENTER_VERTICAL)


        self.resolutionPanel = wx.Panel(self.loginFieldsPanel,name="resolutionPanel")
        self.resolutionPanel.SetAutoLayout(self.AUTOLAYOUT)
        self.resolutionPanel.SetSizer(wx.BoxSizer(wx.HORIZONTAL))
        self.resolutionLabel = wx.StaticText(self.resolutionPanel, wx.ID_ANY, 'Resolution',name='label_resolution')
        self.resolutionPanel.GetSizer().Add(self.resolutionLabel, proportion=1,flag=wx.EXPAND|wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.ALIGN_CENTER_VERTICAL, border=5)

        displaySize = wx.DisplaySize()
        desiredWidth = displaySize[0] * 0.99
        desiredHeight = displaySize[1] * 0.85
        defaultResolution = str(int(desiredWidth)) + "x" + str(int(desiredHeight))

        displaySize = wx.DisplaySize()
        desiredWidth = displaySize[0] * 0.99
        desiredHeight = displaySize[1] * 0.85
        defaultResolution = str(int(desiredWidth)) + "x" + str(int(desiredHeight))
        vncDisplayResolutions = [
            defaultResolution, "1024x768", "1152x864", "1280x800", "1280x1024", "1360x768", "1366x768", "1440x900", "1600x900", "1680x1050", "1920x1080", "1920x1200", "7680x3200",
            ]
        self.resolutionField = wx.ComboBox(self.resolutionPanel, wx.ID_ANY, value=defaultResolution, choices=vncDisplayResolutions, size=(widgetWidth2, -1), style=wx.CB_DROPDOWN,name='jobParams_resolution')
        self.resolutionPanel.GetSizer().Add(self.resolutionField, flag=wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.EXPAND|wx.ALIGN_CENTER_VERTICAL, border=5)
        self.resolutionPanel.Fit()
        self.loginFieldsPanel.GetSizer().Add(self.resolutionPanel,proportion=0,flag=wx.EXPAND)

        
        self.cipherPanel = wx.Panel(self.loginFieldsPanel,name="cipherPanel")
        self.cipherPanel.SetAutoLayout(self.AUTOLAYOUT)
        self.cipherPanel.SetSizer(wx.BoxSizer(wx.HORIZONTAL))
        self.sshTunnelCipherLabel = wx.StaticText(self.cipherPanel, wx.ID_ANY, 'SSH tunnel cipher',name='label_cipher')
        self.cipherPanel.GetSizer().Add(self.sshTunnelCipherLabel, proportion=1,flag=wx.EXPAND|wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.ALIGN_CENTER_VERTICAL, border=5)

        if sys.platform.startswith("win"):
            defaultCipher = "arcfour"
            sshTunnelCiphers = ["3des-cbc", "aes128-cbc", "blowfish-cbc", "arcfour"]
        else:
            defaultCipher = "arcfour128"
            sshTunnelCiphers = ["3des-cbc", "aes128-cbc", "blowfish-cbc", "arcfour128"]
        self.sshTunnelCipherComboBox = wx.ComboBox(self.cipherPanel, wx.ID_ANY, value=defaultCipher, choices=sshTunnelCiphers, size=(widgetWidth2, -1), style=wx.CB_DROPDOWN,name='jobParams_cipher')
        self.cipherPanel.GetSizer().Add(self.sshTunnelCipherComboBox, proportion=0,flag=wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT|wx.EXPAND|wx.ALIGN_CENTER_VERTICAL, border=5)
        self.cipherPanel.Fit()
        self.loginFieldsPanel.GetSizer().Add(self.cipherPanel,proportion=0,flag=wx.EXPAND)


        self.checkBoxPanel = wx.Panel(self.loginFieldsPanel,name="checkBoxPanel")
        self.checkBoxPanel.SetAutoLayout(self.AUTOLAYOUT)
        self.checkBoxPanel.SetSizer(wx.BoxSizer(wx.HORIZONTAL))
        
        p = wx.Panel(self.checkBoxPanel,name="debugCheckBoxPanel")
        p.SetAutoLayout(self.AUTOLAYOUT)
        p.SetSizer(wx.BoxSizer(wx.HORIZONTAL))
        l = wx.StaticText(p, wx.ID_ANY, 'Show debug window')
        c = wx.CheckBox(p, wx.ID_ANY, "",name='debugCheckBox')
        c.Bind(wx.EVT_CHECKBOX, self.onDebugWindowCheckBoxStateChanged)
        p.GetSizer().Add(l,border=5,flag=wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT)
        p.GetSizer().Add(c,border=5,flag=wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT)
        p.Fit()
        self.checkBoxPanel.GetSizer().Add(p,flag=wx.ALIGN_LEFT)
    
        t=wx.StaticText(self.checkBoxPanel,label="")
        self.checkBoxPanel.GetSizer().Add(t,proportion=1,flag=wx.EXPAND)
  
        p = wx.Panel(self.checkBoxPanel,name="advancedCheckBoxPanel")
        p.SetAutoLayout(self.AUTOLAYOUT)
        p.SetSizer(wx.BoxSizer(wx.HORIZONTAL))
        l = wx.StaticText(p, wx.ID_ANY, 'Show Advanced Options')
        c = wx.CheckBox(p, wx.ID_ANY, "",name='advancedCheckBox')
        c.Bind(wx.EVT_CHECKBOX, self.onAdvancedVisibilityStateChanged)
        p.GetSizer().Add(l,border=5,flag=wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT)
        p.GetSizer().Add(c,border=5,flag=wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT)
        p.Fit()
        self.checkBoxPanel.GetSizer().Add(p,flag=wx.ALIGN_RIGHT)

        self.checkBoxPanel.Fit()
        self.loginFieldsPanel.GetSizer().Add(self.checkBoxPanel,flag=wx.ALIGN_BOTTOM)

        #self.tabbedView.AddPage(self.loginFieldsPanel, "Login")

        #self.loginDialogPanelSizer.Add(self.tabbedView, flag=wx.EXPAND|wx.TOP|wx.LEFT|wx.RIGHT, border=10)
        self.loginFieldsPanel.Fit()
        self.loginDialogPanel.GetSizer().Add(self.loginFieldsPanel, flag=wx.EXPAND|wx.TOP|wx.LEFT|wx.RIGHT, border=10)

        #MASSIVE_TAB_INDEX = 0
        #self.tabbedView.ChangeSelection(MASSIVE_TAB_INDEX)

        # Buttons Panel

        self.buttonsPanel = wx.Panel(self.loginDialogPanel, wx.ID_ANY)
        self.buttonsPanel.SetAutoLayout(self.AUTOLAYOUT)
        self.buttonsPanelSizer = wx.FlexGridSizer(rows=1, cols=4, vgap=5, hgap=10)
        self.buttonsPanel.SetSizer(self.buttonsPanelSizer)

        self.preferencesButton = wx.Button(self.buttonsPanel, wx.ID_ANY, 'Preferences')
        self.buttonsPanelSizer.Add(self.preferencesButton, flag=wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT, border=10)
        self.Bind(wx.EVT_BUTTON, self.onOptions, id=self.preferencesButton.GetId())

        self.saveButton = wx.Button(self.buttonsPanel, wx.ID_ANY, 'Save Preferences')
        self.buttonsPanel.GetSizer().Add(self.saveButton, flag=wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT, border=10)
        self.saveButton.Bind(wx.EVT_BUTTON, self.savePrefsEventHandler)

        self.exitButton = wx.Button(self.buttonsPanel, wx.ID_ANY, 'Exit')
        self.buttonsPanelSizer.Add(self.exitButton, flag=wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT, border=10)
        self.Bind(wx.EVT_BUTTON, self.onExit,  id=self.exitButton.GetId())

        self.loginButton = wx.Button(self.buttonsPanel, wx.ID_ANY, 'Login')
        self.buttonsPanel.GetSizer().Add(self.loginButton, flag=wx.TOP|wx.BOTTOM|wx.LEFT|wx.RIGHT, border=10)
        self.loginButton.Bind(wx.EVT_BUTTON, self.savePrefsEventHandler)
        self.loginButton.Bind(wx.EVT_BUTTON, self.onLogin)
        self.loginButton.SetDefault()

        self.buttonsPanel.SetSizerAndFit(self.buttonsPanelSizer)

        self.preferencesButton.Show(False)

        self.loginDialogPanelSizer.Add(self.buttonsPanel, flag=wx.ALIGN_RIGHT|wx.BOTTOM|wx.LEFT|wx.RIGHT, border=15)

        self.loginDialogStatusBar = LauncherStatusBar(self)
        self.SetStatusBar(self.loginDialogStatusBar)

        self.loginDialogPanel.SetSizerAndFit(self.loginDialogPanelSizer)
        self.loginDialogPanel.Fit()
        self.loginDialogPanel.Layout()

        self.Fit()
        self.Layout()
        #self.menu_bar.Show(False)

        self.Centre()

        import getpass
        logger.debug('getpass.getuser(): ' + getpass.getuser())

        logger.debug('sys.platform: ' + sys.platform)

        import platform

        logger.debug('platform.architecture: '  + str(platform.architecture()))
        logger.debug('platform.machine: '       + str(platform.machine()))
        logger.debug('platform.node: '          + str(platform.node()))
        logger.debug('platform.platform: '      + str(platform.platform()))
        logger.debug('platform.processor: '     + str(platform.processor()))
        logger.debug('platform.release: '       + str(platform.release()))
        logger.debug('platform.system: '        + str(platform.system()))
        logger.debug('platform.version: '       + str(platform.version()))
        logger.debug('platform.uname: '         + str(platform.uname()))

        if sys.platform.startswith("win"):
            logger.debug('platform.win32_ver: ' + str(platform.win32_ver()))

        if sys.platform.startswith("darwin"):
            logger.debug('platform.mac_ver: ' + str(platform.mac_ver()))

        if sys.platform.startswith("linux"):
            logger.debug('platform.linux_distribution: ' + str(platform.linux_distribution()))
            logger.debug('platform.libc_ver: ' + str(platform.libc_ver()))

        logger.debug('launcher_version_number.version_number: ' + launcher_version_number.version_number)
        import commit_def
        logger.debug('launcher commit hash: ' + commit_def.LATEST_COMMIT)
        logger.debug('cvlsshutils commit hash: ' + commit_def.LATEST_COMMIT_CVLSSHUTILS)
        self.updateVisibility(self.noneVisible)
        self.contacted_massive_website = False
        self.loadPrefs()
#        self.checkVersionNumber()


    def loadSessionEvent(self,event):
        dlg=wx.FileDialog(launcherMainFrame,"Load a session",style=wx.FD_OPEN)
        status=dlg.ShowModal()
        if status==wx.ID_CANCEL:
            logger.debug('loadSession cancled')
        f=open(dlg.GetPath(),'r')
        self.loadSession(f)
        f.close()

    def loadSession(self,f):
        import pickle
        u=pickle.Unpickler(f)
        saved=u.load()
        self.sites=saved
        cb=self.FindWindowByName('jobParams_configName')
        cbid=cb.GetId()
        size=cb.GetSize()
        pos=cb.GetPosition()
        si=self.siteConfigPanel.GetSizer().GetItem(cb)
        si.DeleteWindows()
        cb = wx.ComboBox(self.siteConfigPanel, cbid, choices=self.sites.keys(), value=self.sites.keys()[0], style=wx.CB_READONLY,name='jobParams_configName')
        cb.Bind(wx.EVT_TEXT, self.onSiteConfigChanged)
        cb.SetSize(size)
        cb.SetPosition(pos)
        si.SetWindow(cb)
        self.updateVisibility()

    def loadDefaultSessions(self):
        self.sites=self.defaultSites.copy()
        cb=self.FindWindowByName('jobParams_configName')
        cbid=cb.GetId()
        size=cb.GetSize()
        pos=cb.GetPosition()
        si=self.siteConfigPanel.GetSizer().GetItem(cb)
        si.DeleteWindows()
        cb = wx.ComboBox(self.siteConfigPanel, cbid, choices=self.sites.keys(), value='', style=wx.CB_READONLY,name='jobParams_configName')
        cb.Bind(wx.EVT_TEXT, self.onSiteConfigChanged)
        cb.SetSize(size)
        cb.SetPosition(pos)
        si.SetWindow(cb)
        self.updateVisibility(self.noneVisible)

    def loadDefaultSessionsEvent(self,event):
        self.loadDefaultSessions()

    def saveSessionEvent(self,event):
        self.saveSession()

    def saveSession(self,f=None,siteConfig=None):
        try:
            from queue import Queue
            print("running python 3")
        except:
            from Queue import Queue
            print("running python 2")
        q=Queue()
        if siteConfig==None:
            try:
                self.loginProcess[0].getSharedSession(q)
            except:
                logger.debug("Tried to save while no session was running. This menu itme should be disabled")
                return
        if f==None:
            dlg=wx.FileDialog(launcherMainFrame,"Save your desktop session",style=wx.FD_SAVE|wx.FD_OVERWRITE_PROMPT)
            status=dlg.ShowModal()
            if status==wx.ID_CANCEL:
                logger.debug('saveSession canceled')
                return
            filename=dlg.GetPath()
            logger.debug('saving session to file %s'%filename)
            try:
                f=open(filename,'w')
                logger.debug('opened file %s to save the session to'%filename)
            except Exception as e:
                logger.debug('error opening file for saving')
                raise e
            logger.debug('retrieved the session configuration from the loginProcess')
        print("dumping siteConfig")
        if siteConfig==None:
            siteConfig=q.get()
        print(siteConfig)
        #import pickle
        mydict={}
        mydict['Saved Session']=siteConfig
        #p=pickle.Pickler(f)
        #p.dump(mydict)
        #f.close()
        import json
        encoder=siteConfig.siteConfigJSONEncoder()
        json.dump(mydict,f,cls=siteConfig.siteConfigJSONEncoder,sort_keys=True,indent=4, separators=(',', ': '))
        f.close()

        
    def checkVersionNumber(self):
        # Check for the latest version of the launcher:
        try:
            myHtmlParser = MyHtmlParser('MassiveLauncherLatestVersionNumber')
            feed = urllib2.urlopen(LAUNCHER_URL, timeout=10)
            html = feed.read()
            myHtmlParser.feed(html)
            myHtmlParser.close()

            latestVersionNumber = myHtmlParser.latestVersionNumber
            htmlComments = myHtmlParser.htmlComments
            htmlCommentsSplit1 = htmlComments.split("<pre id=\"CHANGES\">")
            htmlCommentsSplit2 = htmlCommentsSplit1[1].split("</pre>")
            latestVersionChanges = htmlCommentsSplit2[0].strip()
            self.contacted_massive_website = True
        except:
            logger.debug(traceback.format_exc())
            self.contacted_massive_website = False
            dlg = wx.MessageDialog(self, "Warning: Could not contact the MASSIVE website to check version number.\n\n",
                                "MASSIVE/CVL Launcher", wx.OK | wx.ICON_INFORMATION)
            dlg.ShowModal()

            latestVersionNumber = launcher_version_number.version_number
            latestVersionChanges = ''

        if latestVersionNumber != launcher_version_number.version_number:
            import new_version_alert_dialog
            newVersionAlertDialog = new_version_alert_dialog.NewVersionAlertDialog(launcherMainFrame, wx.ID_ANY, "MASSIVE/CVL Launcher", latestVersionNumber, latestVersionChanges, LAUNCHER_URL)
            newVersionAlertDialog.ShowModal()

            # Tried submit_log=True, but it didn't work.
            # Maybe the requests stuff hasn't been initialized yet.
            logger.debug("Failed version number check.")
            logger.dump_log(launcherMainFrame,submit_log=False)
            sys.exit(1)


    def onMassiveLoginHostNameChanged(self, event):
        event.Skip()
        selectedMassiveLoginHost = self.massiveLoginHostComboBox.GetValue()

    def onMassiveProjectTextChanged(self, event):
        massiveProjectTextFieldValue = launcherMainFrame.massiveProjectComboBox.GetValue().strip()
        if massiveProjectTextFieldValue=="" or massiveProjectTextFieldValue.startswith("[Use"):
            launcherMainFrame.massiveProjectComboBox.SetValue(launcherMainFrame.defaultProjectPlaceholder)
            launcherMainFrame.massiveProjectComboBox.SelectAll()
            launcherMainFrame.massiveProjectComboBox.SetFocus()
        if massiveProjectTextFieldValue in launcherMainFrame.massiveProjects:
            launcherMainFrame.massiveProjectComboBox.SetSelection(launcherMainFrame.massiveProjects.index(massiveProjectTextFieldValue))

    def buildJobParams(self,window):
        jobParams={}
        for item in window.GetChildren():
            name = item.GetName()
            if ('jobParam' in name):
                (prefix,keyname) = name.split('_') 
                jobParams[keyname]=item.GetValue()
            r = self.buildJobParams(item)
            jobParams.update(r)
        return jobParams

    def onSiteConfigChanged(self,event):
        self.loadPrefs(site=event.GetEventObject().GetValue())
        self.updateVisibility()
        self.configName=self.FindWindowByName('jobParams_configName').GetValue()


    def onAdvancedVisibilityStateChanged(self, event):
        self.updateVisibility()

    def showAll(self,window=None):
        if window==None:
            window=self
        for p in window.GetChildren():
            self.showAll(p)
        window.Show()

    def updateVisibility(self,visible=None):
        self.showAll()
        advanced=self.FindWindowByName('advancedCheckBox').GetValue()
        if visible==None:
            try:
                visible = self.sites[self.FindWindowByName('jobParams_configName').GetValue()].visibility
            except Exception as e:
                logger.debug('updateVisibility: no visibility information associated with the siteConfig configName: %s'%self.FindWindowByName('jobParams_configName').GetValue())
                visible={}
        for key in visible.keys():
            try:
                window=self.FindWindowByName(key) #Panels and controls are all subclasses of windows
                if visible[key]==False:
                    window.Hide()
                if visible[key]==True:
                    window.Show()
                if visible[key]=='Advanced' and advanced==True:
                    window.Show()
                if visible[key]=='Advanced' and advanced==False:
                    window.Hide()
            except:
                pass # a value in the dictionary didn't correspond to a named component of the panel. Fail silently.
        self.Fit()
        self.Layout()
        if self.logWindow != None:
            self.logWindow.Show(self.FindWindowByName('debugCheckBox').GetValue())

    def onDebugWindowCheckBoxStateChanged(self, event):
        if launcherMainFrame.logWindow!=None:
            launcherMainFrame.logWindow.Show(event.GetEventObject().GetValue())

    def onCvlDebugWindowCheckBoxStateChanged(self, event):
        if launcherMainFrame.logWindow!=None:
            if launcherMainFrame.cvlTabSelected:
                launcherMainFrame.logWindow.Show(self.cvlShowDebugWindowCheckBox.GetValue())

    def onCvlAdvancedLoginCheckBox(self, event):
        if self.cvlAdvancedLoginCheckBox.GetValue():
            launcherMainFrame.cvlAdvancedLoginFieldsPanel.Show()
        else:
            launcherMainFrame.cvlAdvancedLoginFieldsPanel.Hide()

    def onCloseMassiveDebugWindow(self, event):
        if launcherMainFrame.massiveTabSelected:
            self.massiveShowDebugWindowCheckBox.SetValue(False)
        if launcherMainFrame.logWindow!=None:
            launcherMainFrame.logWindow.Show(False)

    def onCloseCvlDebugWindow(self, event):
        if launcherMainFrame.cvlTabSelected:
            self.cvlShowDebugWindowCheckBox.SetValue(False)
        if launcherMainFrame.logWindow!=None:
            launcherMainFrame.logWindow.Show(False)

    def onHelpContents(self, event):
        from help.HelpController import helpController
        if helpController is not None and helpController.initializationSucceeded:
            helpController.DisplayContents()
        else:
            wx.MessageBox("Unable to open: " + helpController.launcherHelpUrl,
                          "Error", wx.OK|wx.ICON_EXCLAMATION)

    def onAbout(self, event):
        import commit_def
        dlg = wx.MessageDialog(self, "Version " + launcher_version_number.version_number + "\n"
                                   + 'launcher Commit: ' + commit_def.LATEST_COMMIT + '\n'
                                   + 'cvlsshutils Commit: ' + commit_def.LATEST_COMMIT_CVLSSHUTILS + '\n',
                                "MASSIVE/CVL Launcher", wx.OK | wx.ICON_INFORMATION)
        dlg.ShowModal()
        dlg.Destroy()

    def onExit(self, event):
        # Clean-up (including qdel if necessary) is now done in LoginTasks.py
        # No longer using temporary private key file, 
        # so there's no need to delete it as part of clean-up.
        for lp in self.loginProcess:
            logger.debug("LauncherMainFrame.onExit: calling shutdown on a loginprocess")
            lp.shutdown()
#        for lp in self.loginProcess:
#            while not lp.complete():
#                time.sleep(0.5)

        try:
            logger.dump_log(launcherMainFrame)
        finally:
            os._exit(0)


    def onOptions(self, event, tabIndex=0):

        self.launcherOptionsDialog.tabbedView.SetSelection(tabIndex)
        rv = self.launcherOptionsDialog.ShowModal()

        if rv == wx.OK:
            self.vncOptions = self.launcherOptionsDialog.getVncOptions()
            self.saveGlobalOptions()
    
    def saveGlobalOptions(self):

        for key in self.vncOptions:
            turboVncConfig.set("TurboVNC Preferences", key, self.vncOptions[key])

        with open(turboVncPreferencesFilePath, 'wb') as turboVncPreferencesFileObject:
            turboVncConfig.write(turboVncPreferencesFileObject)

    def onCut(self, event):
        textCtrl = self.FindFocus()
        if textCtrl is not None:
            textCtrl.Cut()

    def onCopy(self, event):
        textCtrl = self.FindFocus()
        if textCtrl is not None:
            textCtrl.Copy()

    def onPaste(self, event):
        textCtrl = self.FindFocus()
        if textCtrl is not None:
            textCtrl.Paste()

    def onSelectAll(self, event):
        textCtrl = self.FindFocus()
        if textCtrl is not None:
            textCtrl.SelectAll()

    def SetCursor(self, cursor):
        self.massiveLoginDialogPanel.SetCursor(cursor)
        self.massiveLoginFieldsPanel.SetCursor(cursor)
        self.massiveLoginHostLabel.SetCursor(cursor)
        self.massiveProjectLabel.SetCursor(cursor)
        self.massiveHoursLabel.SetCursor(cursor)
        self.massiveVncDisplayResolutionLabel.SetCursor(cursor)
        self.massiveSshTunnelCipherLabel.SetCursor(cursor)
        self.massiveUsernameLabel.SetCursor(cursor)
        self.massiveLoginHostComboBox.SetCursor(cursor)
        self.massiveVncDisplayResolutionComboBox.SetCursor(cursor)
        self.massiveSshTunnelCipherComboBox.SetCursor(cursor)
        self.massiveProjectComboBox.SetCursor(cursor)
        self.massiveHoursField.SetCursor(cursor)
        self.massiveUsernameTextField.SetCursor(cursor)

        self.cvlConnectionProfileComboBox.SetCursor(cursor)
        self.cvlUsernameTextField.SetCursor(cursor)
        self.cvlVncDisplayResolutionComboBox.SetCursor(cursor)
        self.cvlSshTunnelCipherComboBox.SetCursor(cursor)

        self.buttonsPanel.SetCursor(cursor)
        self.preferencesButton.SetCursor(cursor)
        self.exitButton.SetCursor(cursor)
        self.loginButton.SetCursor(cursor)

        if self.progressDialog!=None:
            self.progressDialog.SetCursor(cursor)

        super(LauncherMainFrame, self).SetCursor(cursor)

    def queryAuthMode(self):
        import LauncherOptionsDialog
        var='auth_mode'
        auth_mode=self.launcherOptionsDialog.FindWindowByName(var)
        choices=[]
        for i in range(auth_mode.GetCount()):
            choices.append(auth_mode.GetString(i))
        dlg = LauncherOptionsDialog.LauncherOptionsDialog(launcherMainFrame,"""
Would you like to use an SSH Key pair or your password to authenticate yourself?
Most of the time, an SSH Key pair is preferable.
If this account is shared by a number of people then passwords are preferable
""",title="MASSIVE/CVL Launcher",ButtonLabels=choices)
        rv=dlg.ShowModal()
        if rv in range(auth_mode.GetCount()):
            return int(rv)
        else:
            self.queryAuthMode()
    def loginComplete(self,lp,jobParams):
        try:
            self.loginProcess.remove(lp)
        except:
            logger.debug("launcher: Couldn't remove the loginprocess")
    def loginCancel(self,lp,jobParams):
        self.loginProcess.remove(lp)

    def onLogin(self, event):
        MASSIVE_TAB_INDEX = 0
        CVL_TAB_INDEX =1
        configName=self.FindWindowByName('jobParams_configName').GetValue()
        if configName=="" or configName==None:
            dlg=LauncherMessageDialog(self,"Please select a site to log into first","Please select a site")
            dlg.ShowModal()
            return
        jobParams={}
        jobParams = self.buildJobParams(self)
        if jobParams['username'] == "":
            dlg = LauncherMessageDialog(launcherMainFrame,
                    "Please enter your username.",
                    "MASSIVE/CVL Launcher", flags=wx.OK | wx.ICON_INFORMATION)
            dlg.ShowModal()
            usernamefield = self.FindWindowByName('jobParams_username')
            usernamefield.SetFocus()
            return


        if (self.logWindow == None):

            #self.logWindow = wx.Frame(self, title='{configName} Login'.format(**jobParams), name='{configName} Login'.format(**jobParams),pos=(200,150),size=(700,450))
            self.logWindow = wx.Frame(self, title='Debug Log'.format(**jobParams), pos=(200,150),size=(700,450))
            #self.logWindow.Bind(wx.EVT_CLOSE, self.onCloseDebugWindow)

            if sys.platform.startswith("win"):
                _icon = wx.Icon('MASSIVE.ico', wx.BITMAP_TYPE_ICO)
                self.logWindow.SetIcon(_icon)

            if sys.platform.startswith("linux"):
                import MASSIVE_icon
                self.logWindow.SetIcon(MASSIVE_icon.getMASSIVElogoTransparent128x128Icon())

            self.logTextCtrl = wx.TextCtrl(self.logWindow, style=wx.TE_MULTILINE|wx.TE_READONLY)
            logWindowSizer = wx.GridSizer(rows=1, cols=1, vgap=5, hgap=5)
            logWindowSizer.Add(self.logTextCtrl, 0, wx.EXPAND)
            self.logWindow.SetSizer(logWindowSizer)
            if sys.platform.startswith("darwin"):
                font = wx.Font(13, wx.MODERN, wx.NORMAL, wx.NORMAL, False, u'Courier New')
            else:
                font = wx.Font(11, wx.MODERN, wx.NORMAL, wx.NORMAL, False, u'Courier New')
            self.logTextCtrl.SetFont(font)


            logger.sendLogMessagesToDebugWindowTextControl(self.logTextCtrl)

        dcb=self.FindWindowByName('debugCheckBox').GetValue()
        self.logWindow.Show(self.FindWindowByName('debugCheckBox').GetValue())


        userCanAbort=True
        maximumProgressBarValue = 10

        try:
            os.mkdir(os.path.join(os.path.expanduser('~'), '.ssh'))
        except:
            logger.debug(traceback.format_exc())
            pass

        # project hours and nodes will be ignored for the CVL login, but they will be used for Massive.
        configName=self.FindWindowByName('jobParams_configName').GetValue()
        if not self.vncOptions.has_key('auth_mode'):
            mode=self.queryAuthMode()
            self.vncOptions['auth_mode']=mode
            self.launcherOptionsDialog.FindWindowByName('auth_mode').SetSelection(mode)
            self.identity_menu.disableItems()
            self.saveGlobalOptions()
        jobParams=self.buildJobParams(self)
        jobParams['wallseconds']=int(jobParams['hours'])*60*60
        if launcherMainFrame.launcherOptionsDialog.FindWindowByName('auth_mode').GetSelection()==LauncherMainFrame.TEMP_SSH_KEY:
            logger.debug("launcherMainFrame.onLogin: using a temporary Key pair")
            try:
                del os.environ['SSH_AUTH_SOCK']
                logger.debug("launcherMainFrame.onLogin: spawning an ssh-agent (not using the existing agent)")
            except:
                logger.debug("launcherMainFrame.onLogin: spawning an ssh-agent (no existing agent found)")
                pass
            launcherMainFrame.keyModel=KeyModel(temporaryKey=True)
            removeKeyOnExit = True
        else:
            logger.debug("launcherMainFrame.onLogin: using a permanent Key pair")
            launcherMainFrame.keyModel=KeyModel(temporaryKey=False)
        jobParams=self.buildJobParams(self)
        jobParams['wallseconds']=int(jobParams['hours'])*60*60
        self.configName=self.FindWindowByName('jobParams_configName').GetValue()
        autoExit=False
        lp=LoginTasks.LoginProcess(launcherMainFrame,jobParams,self.keyModel,siteConfig=self.sites[self.configName],displayStrings=self.sites[self.configName].displayStrings,autoExit=autoExit,vncOptions=self.vncOptions,removeKeyOnExit=launcherMainFrame.vncOptions['public_mode'])
        lp.setCallback(lambda jobParams: self.loginComplete(lp,jobParams))
        lp.setCancelCallback(lambda jobParams: self.loginCancel(lp,jobParams))
        self.loginProcess.append(lp)
        lp.doLogin()
        event.Skip()

from utilityFunctions import siteConfig 



class LauncherStatusBar(wx.StatusBar):
    def __init__(self, parent):
        wx.StatusBar.__init__(self, parent)

        self.SetFieldsCount(2)
        #self.SetStatusText('Welcome to MASSIVE', 0)
        self.SetStatusWidths([-5, -2])

class MyApp(wx.App):
    def OnInit(self):

        appDirs = appdirs.AppDirs("MASSIVE Launcher", "Monash University")
        appUserDataDir = appDirs.user_data_dir
        # Add trailing slash:
        appUserDataDir = os.path.join(appUserDataDir,"")
        if not os.path.exists(appUserDataDir):
            os.makedirs(appUserDataDir)

        global launcherConfig
#        launcherConfig=ConfigParser.RawConfigParser(allow_no_value=True)
        global launcherPreferencesFilePath 
        launcherPreferencesFilePath = os.path.join(appUserDataDir,"Launcher Preferences.cfg")
#        if (os.path.exists(launcherPreferencesFilePath)):
#            launcherConfig.read(launcherPreferencesFilePath)
        

        global massiveLauncherConfig
        massiveLauncherConfig = ConfigParser.RawConfigParser(allow_no_value=True)

        global massiveLauncherPreferencesFilePath
        massiveLauncherPreferencesFilePath = os.path.join(appUserDataDir,"MASSIVE Launcher Preferences.cfg")
        if os.path.exists(massiveLauncherPreferencesFilePath):
            massiveLauncherConfig.read(massiveLauncherPreferencesFilePath)
        if not massiveLauncherConfig.has_section("MASSIVE Launcher Preferences"):
            massiveLauncherConfig.add_section("MASSIVE Launcher Preferences")

        global cvlLauncherConfig
        cvlLauncherConfig = ConfigParser.RawConfigParser(allow_no_value=True)

        global cvlLauncherPreferencesFilePath
        cvlLauncherPreferencesFilePath = os.path.join(appUserDataDir,"CVL Launcher Preferences.cfg")
        if os.path.exists(cvlLauncherPreferencesFilePath):
            cvlLauncherConfig.read(cvlLauncherPreferencesFilePath)
        if not cvlLauncherConfig.has_section("CVL Launcher Preferences"):
            cvlLauncherConfig.add_section("CVL Launcher Preferences")

        global turboVncConfig
        turboVncConfig = ConfigParser.RawConfigParser(allow_no_value=True)

        global turboVncPreferencesFilePath
        turboVncPreferencesFilePath = os.path.join(appUserDataDir,"TurboVNC Preferences.cfg")
        if os.path.exists(turboVncPreferencesFilePath):
            turboVncConfig.read(turboVncPreferencesFilePath)
        if not turboVncConfig.has_section("TurboVNC Preferences"):
            turboVncConfig.add_section("TurboVNC Preferences")

        if sys.platform.startswith("win"):
            os.environ['CYGWIN'] = "nodosfilewarning"
        global launcherMainFrame
        launcherMainFrame = LauncherMainFrame(None, wx.ID_ANY, 'MASSIVE/CVL Launcher')
        launcherMainFrame.Show(True)
        launcherMainFrame.menu_bar.Show(True)


#        if massiveLauncherConfig is not None:
#            massiveLauncherConfig.set("MASSIVE Launcher Preferences", "massive_launcher_private_key_path", launcherMainFrame.keyModel.getsshKeyPath())
#            with open(massiveLauncherPreferencesFilePath, 'wb') as massiveLauncherPreferencesFileObject:
#                massiveLauncherConfig.write(massiveLauncherPreferencesFileObject)


        return True

if __name__ == '__main__':
    app = MyApp(False) # Don't automatically redirect sys.stdout and sys.stderr to a Window.
    app.MainLoop()
