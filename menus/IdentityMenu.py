# IdentityMenu.py

import wx
import subprocess
import os
import sys
if os.path.abspath("..") not in sys.path:
    sys.path.append(os.path.abspath(".."))

from cvlsshutils.ChangeKeyPassphraseDialog import ChangeKeyPassphraseDialog
from cvlsshutils.InspectKeyDialog import InspectKeyDialog
from cvlsshutils.ResetKeyDialog import ResetKeyDialog
from cvlsshutils.CreateNewKeyDialog import CreateNewKeyDialog
from cvlsshutils.KeyModel import KeyModel

from logger.Logger import logger

# For now, the private key file path in the CreateNewKeyDialog is read-only.
userCanModifyPrivateKeyFilePath = False

class IdentityMenu(wx.Menu):

    def initialize(self, launcherMainFrame,auth_mode=0):

        self.launcherMainFrame = launcherMainFrame
        #self.massiveLauncherConfig = massiveLauncherConfig
        #self.massiveLauncherPreferencesFilePath = massiveLauncherPreferencesFilePath

        createNewKeyMenuItemId = wx.NewId()
        self.Append(createNewKeyMenuItemId, "Create &new key")
        self.launcherMainFrame.Bind(wx.EVT_MENU, self.onCreateNewKey, id=createNewKeyMenuItemId)

        inspectKeyMenuItemId = wx.NewId()
        self.Append(inspectKeyMenuItemId, "&Inspect key")
        self.launcherMainFrame.Bind(wx.EVT_MENU, self.onInspectKey, id=inspectKeyMenuItemId)

        changePassphraseMenuItemId = wx.NewId()
        self.Append(changePassphraseMenuItemId, "&Change passphrase")
        self.launcherMainFrame.Bind(wx.EVT_MENU, self.onChangePassphrase, id=changePassphraseMenuItemId)

        resetKeyMenuItemId = wx.NewId()
        self.Append(resetKeyMenuItemId, "&Reset key")
        self.launcherMainFrame.Bind(wx.EVT_MENU, self.onResetKey, id=resetKeyMenuItemId)

        deleteKeyMenuItemId = wx.NewId()
        self.Append(deleteKeyMenuItemId, "&Delete key")
        self.launcherMainFrame.Bind(wx.EVT_MENU, self.onDeleteKey, id=deleteKeyMenuItemId)

        self.AppendSeparator()

        #privacyOptionsMenuItemId = wx.NewId()
        self.authOpts=wx.MenuItem(self,wx.ID_ANY,"&Authentication options")
        if hasattr(self, 'Append'):
            self.Append(self.authOpts)
        elif hasattr(self, 'AppendItem'):
            self.AppendItem(self.authOpts)
        self.launcherMainFrame.Bind(wx.EVT_MENU, self.onAuthenticationOptions, id=self.authOpts.GetId())

        self.permSSHKey = wx.MenuItem(self,wx.ID_ANY,"Remember me on this computer",kind=wx.ITEM_RADIO)
        self.launcherMainFrame.Bind(wx.EVT_MENU,self.onPermSSHKey,id=self.permSSHKey.GetId())
        if hasattr(self, 'Append'):
            self.Append(self.permSSHKey)
        elif hasattr(self, 'AppendItem'):
            self.AppendItem(self.permSSHKey)

        self.tempSSHKey = wx.MenuItem(self,wx.ID_ANY,"Don't remember me",kind=wx.ITEM_RADIO)
        self.launcherMainFrame.Bind(wx.EVT_MENU,self.onTempSSHKey,id=self.tempSSHKey.GetId())
        if hasattr(self, 'Append'):
            self.Append(self.tempSSHKey)
        elif hasattr(self, 'AppendItem'):
            self.AppendItem(self.tempSSHKey)


        self.AppendSeparator()

        helpAboutKeysMenuItem = wx.NewId()
        self.Append(helpAboutKeysMenuItem, "&Help about \"Remember me\"")
        self.launcherMainFrame.Bind(wx.EVT_MENU, self.onHelpAboutKeys, id=helpAboutKeysMenuItem)
        self.setRadio(auth_mode)
        self.disableItems(auth_mode)

    def onTempSSHKey(self,event):
        options = self.launcherMainFrame.getPrefsSection('Global Preferences')
        options['auth_mode'] = self.launcherMainFrame.TEMP_SSH_KEY
        self.launcherMainFrame.setPrefsSection('Global Preferences',options)
        self.launcherMainFrame.savePrefs(section='Global Preferences')
        self.disableItems(self.launcherMainFrame.TEMP_SSH_KEY)

    def onPermSSHKey(self,event):
        options = self.launcherMainFrame.getPrefsSection('Global Preferences')
        options['auth_mode'] = self.launcherMainFrame.PERM_SSH_KEY
        self.launcherMainFrame.setPrefsSection('Global Preferences',options)
        self.launcherMainFrame.savePrefs(section='Global Preferences')
        self.disableItems(self.launcherMainFrame.PERM_SSH_KEY)

    def setRadio(self,state):
        if state == self.launcherMainFrame.PERM_SSH_KEY:
            self.permSSHKey.Check(True)
            self.tempSSHKey.Check(False)
        else:
            self.permSSHKey.Check(False)
            self.tempSSHKey.Check(True)
    
    def disableItems(self,state):
        if state == self.launcherMainFrame.PERM_SSH_KEY:
            enable=True
        else:
            enable=False
        iditems = self.GetMenuItems()
        for item in iditems:
            item.Enable(enable)
        self.authOpts.Enable(True)
        self.tempSSHKey.Enable(True)
        self.permSSHKey.Enable(True)


    def privateKeyExists(self,warnIfNotFoundInLocalSettings=False):
        import cvlsshutils

        km=cvlsshutils.KeyModel.KeyModel()
        return km.privateKeyExists()

    def offerToCreateKey(self):

        dlg = wx.MessageDialog(None,
                        "You don't seem to have a Launcher key yet. The key will be\n" +
                         "generated automatically when you try logging into a remote\n" +
                         "server, e.g. MASSIVE.\n\n" +
                         "Would you like to generate a key now?",
                        "Strudel", wx.YES_NO | wx.ICON_QUESTION)
        return dlg.ShowModal()


    def createKey(self):

        createNewKeyDialog = CreateNewKeyDialog(None, None, wx.ID_ANY, 'Strudel Private Key',self.launcherMainFrame.keyModel.getPrivateKeyFilePath(),self.launcherMainFrame.displayStrings)
        createNewKeyDialog.Center()
        if createNewKeyDialog.ShowModal()==wx.ID_OK:
            logger.debug("User pressed OK from CreateNewKeyDialog.")
            password = createNewKeyDialog.getPassphrase()
            def success():
                pass
            def failure():
                pass
            self.launcherMainFrame.keyModel.generateNewKey(password,success,failure,failure)
            createdKey = True
        else:
            logger.debug("User canceled from CreateNewKeyDialog.")
            createdKey= False

        return createdKey


    def deleteKey(self):

        success = self.launcherMainFrame.keyModel.deleteKey(ignoreFailureToConnectToAgent=True)
        #success = success and self.launcherMainFrame.keyModel.removeKeyFromAgent()
        if success:
            message = "Launcher key was successfully deleted!"
            logger.debug(message)
        else:
            message = "An error occured while attempting to delete the existing key."
            logger.debug(message)

        return success


    def onCreateNewKey(self,event):

        if self.privateKeyExists():
            dlg = wx.MessageDialog(self.launcherMainFrame,
                            "You already have a Strudel key.\n\n" +
                            "Do you want to delete your existing key and create a new one?",
                            "Strudel", wx.YES_NO | wx.ICON_QUESTION)
            if dlg.ShowModal()==wx.ID_YES:
                success = self.deleteKey()
                if not success:
                    dlg = wx.MessageDialog(self.launcherMainFrame, 
                        "An error occured while attempting to delete your existing key.",
                        "Strudel", wx.OK | wx.ICON_INFORMATION)
                    dlg.ShowModal()
                    return
            else:
                return

        return self.createKey()

    def launcherKeyIsInAgent(self):

        publicKeyFingerprintInAgent = ""
        key = self.launcherMainFrame.keyModel.fingerprintAgent()
        if key != None:
            sshAddOutComponents = key.split(" ")
            if len(sshAddOutComponents)>1:
                publicKeyFingerprintInAgent = sshAddOutComponents[1]

        return publicKeyFingerprintInAgent != ""


    def onInspectKey(self,event):
        if not self.privateKeyExists(warnIfNotFoundInLocalSettings=userCanModifyPrivateKeyFilePath):
            if self.offerToCreateKey()==wx.ID_YES:
                self.createKey()
            else:
                return

        inspectKeyDialog = InspectKeyDialog(None, wx.ID_ANY, 'Strudel Key Properties', self.launcherMainFrame.keyModel)
        inspectKeyDialog.Center()
        inspectKeyDialog.ShowModal()


    def onChangePassphrase(self,event):

        if self.privateKeyExists(warnIfNotFoundInLocalSettings=userCanModifyPrivateKeyFilePath):
            changeKeyPassphraseDialog = ChangeKeyPassphraseDialog(self.launcherMainFrame, wx.ID_ANY, 'Change Key Passphrase', self.launcherMainFrame.keyModel)
            changeKeyPassphraseDialog.ShowModal()
        else:
            if self.offerToCreateKey()==wx.ID_YES:
                self.createKey()


    def onResetKey(self,event):

        if self.privateKeyExists(warnIfNotFoundInLocalSettings=userCanModifyPrivateKeyFilePath):
            resetKeyDialog = ResetKeyDialog(self.launcherMainFrame, wx.ID_ANY, 'Reset Key', self.launcherMainFrame.keyModel, self.launcherKeyIsInAgent())
            resetKeyDialog.ShowModal()
        else:
            if self.offerToCreateKey()==wx.ID_YES:
                self.createKey()


    def onDeleteKey(self,event):

        if self.privateKeyExists(warnIfNotFoundInLocalSettings=userCanModifyPrivateKeyFilePath):
            dlg = wx.MessageDialog(self.launcherMainFrame,
                "Are you sure you want to delete your key, located at:\n\n" +
                self.launcherMainFrame.keyModel.getPrivateKeyFilePath() +
                " ?",
                "Strudel", wx.YES_NO | wx.ICON_QUESTION)
            if dlg.ShowModal()==wx.ID_YES:
                success = self.deleteKey()
                if success:
                    message = "Your Launcher key was successfully deleted!"
                else:
                    message = "An error occured while attempting to delete your key."
                dlg = wx.MessageDialog(self.launcherMainFrame, message,
                    "Strudel", wx.OK | wx.ICON_INFORMATION)
                dlg.ShowModal()
        else:
            dlg = wx.MessageDialog(None,
                        "You don't seem to have a Launcher key yet. The key will be\n" +
                         "generated automatically when you try logging into a remote\n" +
                         "server, e.g. MASSIVE.",
                        "Strudel", wx.OK | wx.ICON_INFORMATION)
            dlg.ShowModal()


    def onAuthenticationOptions(self,event):
        from optionsDialog import LAUNCHER_VNC_OPTIONS_AUTHENTICATION_TAB_INDEX
        self.launcherMainFrame.onOptions(event, tabIndex=LAUNCHER_VNC_OPTIONS_AUTHENTICATION_TAB_INDEX)

    def onHelpAboutKeys(self,event):
        from help.HelpController import helpController
        if helpController is not None and helpController.initializationSucceeded:
            helpController.Display("SSH Keys")
        else:
            wx.MessageBox("Unable to open: " + helpController.launcherHelpUrl,
                          "Error", wx.OK|wx.ICON_EXCLAMATION)

