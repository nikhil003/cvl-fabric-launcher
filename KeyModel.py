# KeyModel.py

import sys
import os
import subprocess
import tempfile
import traceback
import threading

if os.path.abspath("..") not in sys.path:
    sys.path.append(os.path.abspath(".."))

from logger.Logger import logger

from os.path import expanduser
class sshpaths():
    def double_quote(x):
        return '"' + x + '"'
    def ssh_binaries(self):
        """
        Locate the ssh binaries on various systems. On Windows we bundle a
        stripped-down OpenSSH build that uses Cygwin.
        """

        if sys.platform.startswith('win'):
            # Assume that our InnoSetup script will set appropriate permissions on the "tmp" directory.

            if hasattr(sys, 'frozen'):
                f = lambda x: os.path.join(os.path.dirname(sys.executable), OPENSSH_BUILD_DIR, 'bin', x)
            else:
                launcherModulePath = os.path.dirname(pkgutil.get_loader("launcher").filename)
                f = lambda x: os.path.join(launcherModulePath, OPENSSH_BUILD_DIR, 'bin', x)

            sshBinary        = double_quote(f('ssh.exe'))
            sshKeyGenBinary  = double_quote(f('ssh-keygen.exe'))
            sshKeyScanBinary = double_quote(f('ssh-keyscan.exe'))
            sshAgentBinary   = double_quote(f('charade.exe'))
            sshAddBinary     = double_quote(f('ssh-add.exe'))
            chownBinary      = double_quote(f('chown.exe'))
            chmodBinary      = double_quote(f('chmod.exe'))
        elif sys.platform.startswith('darwin'):
            sshBinary        = '/usr/bin/ssh'
            sshKeyGenBinary  = '/usr/bin/ssh-keygen'
            sshKeyScanBinary = '/usr/bin/ssh-keyscan'
            sshAgentBinary   = '/usr/bin/ssh-agent'
            sshAddBinary     = '/usr/bin/ssh-add'
            chownBinary      = '/usr/sbin/chown'
            chmodBinary      = '/bin/chmod'
        else:
            sshBinary        = '/usr/bin/ssh'
            sshKeyGenBinary  = '/usr/bin/ssh-keygen'
            sshKeyScanBinary = '/usr/bin/ssh-keyscan'
            sshAgentBinary   = '/usr/bin/ssh-agent'
            sshAddBinary     = '/usr/bin/ssh-add'
            chownBinary      = '/bin/chown'
            chmodBinary      = '/bin/chmod'
 
        return (sshBinary, sshKeyGenBinary, sshAgentBinary, sshAddBinary, sshKeyScanBinary, chownBinary, chmodBinary,)
    
    def ssh_files(self):
        known_hosts_file = os.path.join(expanduser('~'), '.ssh', 'known_hosts')
        sshKeyPath = os.path.join(expanduser('~'), '.ssh', self.keyFileName)

        return (sshKeyPath,known_hosts_file,)

    def __init__(self, keyFileName, massiveLauncherConfig=None, massiveLauncherPreferencesFilePath=None):
        (sshBinary, sshKeyGenBinary, sshAgentBinary, sshAddBinary, sshKeyScanBinary,chownBinary, chmodBinary,) = self.ssh_binaries()
        self.keyFileName                = keyFileName
        self.massiveLauncherConfig      = massiveLauncherConfig
        self.massiveLauncherPreferencesFilePath = massiveLauncherPreferencesFilePath
        (sshKeyPath,sshKnownHosts,)     = self.ssh_files()
        self.sshBinary                  = sshBinary
        self.sshKeyGenBinary            = sshKeyGenBinary
        self.sshAgentBinary             = sshAgentBinary
        self.sshAddBinary               = sshAddBinary
        self.sshKeyScanBinary           = sshKeyScanBinary
        self.chownBinary                = chownBinary
        self.chmodBinary                = chmodBinary

        self.sshKeyPath                 = sshKeyPath
        self.sshKnownHosts              = sshKnownHosts


class KeyModel():

    def __init__(self, temporaryKey=False):
        self.sshpaths = sshpaths("MassiveLauncherKey")
        self.sshPathsObject = self.sshpaths
        self.temporaryKey=temporaryKey
        if self.temporaryKey:
            sshKey=tempfile.NamedTemporaryFile(delete=True)
            self.sshpaths.sshKeyPath=sshKey.name
            sshKey.close()
        self.keyComment = "Massive Launcher Key"
        if self.temporaryKey:
            self.keyComment+=" (temporary key)"

    def getPrivateKeyFilePath(self):
        return self.sshPathsObject.sshKeyPath
    
    def getLauncherKeyComment(self):
        return self.keyComment
            

    def getsshBinary(self):
        return self.sshPathsObject.sshBinary
    
    def getsshKeyPath(self):
        return self.sshPathsObject.sshKeyPath

    def isTemporaryKey(self):
        return self.temporaryKey

    def generateNewKey(self, passphrase, keyCreatedSuccessfullyCallback, keyFileAlreadyExistsCallback, passphraseTooShortCallback, keyComment=None ):

        success = False

        if keyComment!=None:
            self.keyComment = keyComment
        print "creating key with key comment %s"%self.keyComment
        if sys.platform.startswith('win'):
            cmdList = [self.sshPathsObject.sshKeyGenBinary.strip('"'), "-f", self.getPrivateKeyFilePath(), "-C", self.keyComment, "-N", passphrase]
            proc = subprocess.Popen(cmdList,
                                    stdin=subprocess.PIPE,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT,
                                    universal_newlines=True)
            stdout, stderr = proc.communicate('\r\n')

            if stdout is None or str(stdout).strip() == '':
                logger.debug("KeyModel.generateNewKey: " + '(1) Got EOF from ssh-keygen binary')
            elif "Your identification has been saved" in stdout:
                success = True
                keyCreatedSuccessfullyCallback()
            elif "passphrase too short" in stdout:
                passphraseTooShortCallback()
            elif 'already exists' in stdout:
                keyFileAlreadyExistsCallback()
            elif 'Could not open a connection to your authentication agent' in stdout:
                logger.debug("KeyModel.generateNewKey: " + "Could not open a connection to your authentication agent.")
                failedToConnectToAgentCallback()
            else:
                logger.debug("KeyModel.generateNewKey: " + 'Got unknown error from ssh-keygen binary')
                logger.debug("KeyModel.generateNewKey: " + stdout)
        else:
            # On Linux or BSD/OSX we can use pexpect to talk to ssh-keygen.

            import pexpect

            args = ["-f", self.getPrivateKeyFilePath(), "-C", self.keyComment]
            lp = pexpect.spawn(self.sshPathsObject.sshKeyGenBinary, args=args)

            idx = lp.expect(["Enter passphrase", "already exists", pexpect.EOF])

            if idx == 0:
                lp.sendline(passphrase)
                idx = lp.expect(["Enter same passphrase again"])
                lp.sendline(passphrase)
                idx = lp.expect(["Your identification has been saved", "do not match.", "passphrase too short"])
                if idx == 0:
                    success = True
                    keyCreatedSuccessfullyCallback()
                elif idx == 1:
                    # This shouldn't happen.
                    logger.debug("KeyModel.generateNewKey: " + "Passphrases do not match")
                elif idx == 2:
                    passphraseTooShortCallback()
            elif idx == 1:
                keyFileAlreadyExistsCallback()
            else:
                #logger.debug("1 returning KEY_LOCKED %s %s"%(lp.before,lp.after))
                logger.debug("KeyModel.generateNewKey: " + "Unexpected result from attempt to create new key.")
            lp.close()
        return success

    def changePassphrase(self, existingPassphrase, newPassphrase, 
        passphraseUpdatedSuccessfullyCallback,
        existingPassphraseIncorrectCallback,
        newPassphraseTooShortCallback,
        keyLockedCallback):

        success = False

        if sys.platform.startswith('win'):
            cmdList = [self.sshPathsObject.sshKeyGenBinary.strip('"'), "-f", self.getPrivateKeyFilePath(), 
                        "-p", "-P", existingPassphrase, "-N", newPassphrase]
            proc = subprocess.Popen(cmdList,
                                    stdin=subprocess.PIPE,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT,
                                    universal_newlines=True)
            stdout, stderr = proc.communicate(input=existingPassphrase + '\r\n')

            if stdout is None or str(stdout).strip() == '':
                logger.debug("KeyModel.changePassphrase: " + '(1) Got EOF from ssh-keygen binary')
                keyLockedCallback()
            if "Your identification has been saved" in stdout:
                success = True
                passphraseUpdatedSuccessfullyCallback()
            elif "passphrase too short" in stdout:
                newPassphraseTooShortCallback()
            elif 'Bad pass' in stdout or 'load failed' in stdout:
                logger.debug("changePassphrase %i %s: Got \"Bad pass\" from ssh-keygen binary"%(threading.currentThread().ident,threading.currentThread().name))
                if existingPassphrase == '':
                    keyLockedCallback()
                else:
                    existingPassphraseIncorrectCallback()
            else:
                logger.debug("changePassphrase %i %s: Got unknown error from ssh-keygen binary"%(threading.currentThread().ident,threading.currentThread().name))
                logger.debug("KeyModel.changePassphrase: " + stdout)
                keyLockedCallback()
        else:
            # On Linux or BSD/OSX we can use pexpect to talk to ssh-keygen.

            import pexpect

            args = ["-f", self.getPrivateKeyFilePath(), "-p"]
            lp = pexpect.spawn(self.sshPathsObject.sshKeyGenBinary, args=args)

            idx = lp.expect(["Enter old passphrase", "Key has comment"])

            if idx == 0:
                logger.debug("changePassphrase %i %s: sending passphrase to "%(threading.currentThread().ident,threading.currentThread().name) + self.sshPathsObject.sshKeyGenBinary + " -f " + self.getPrivateKeyFilePath() + " -p")
                lp.sendline(existingPassphrase)

            idx = lp.expect(["Enter new passphrase", "Bad pass", "load failed", pexpect.EOF])

            if idx == 0:
                lp.sendline(newPassphrase)
                idx = lp.expect(["Enter same passphrase again"])
                lp.sendline(newPassphrase)
                idx = lp.expect(["Your identification has been saved", "do not match.", "passphrase too short"])
                if idx == 0:
                    success = True
                    passphraseUpdatedSuccessfullyCallback()
                elif idx == 1:
                    # This shouldn't happen because changePassphrase 
                    # only takes one argument for newPassphrase,
                    # so repeated newPassphrase should have 
                    # already been checked before changePassphrase
                    # is called.
                    logger.debug("changePassphrase %i %s: Passphrases do not match"%(threading.currentThread().ident,threading.currentThread().name))
                elif idx == 2:
                    newPassphraseTooShortCallback()
            elif idx == 1 or idx == 2:
                existingPassphraseIncorrectCallback()
            else:
                #logger.debug("1 returning KEY_LOCKED %s %s"%(lp.before,lp.after))
                logger.debug("changePassphase %i %s: Unexpected result from attempt to change passphrase."%(threading.currentThread().ident,threading.currentThread().name))
            lp.close()
        return success

    def deleteKey(self):
        # Delete key

        # Should we ask for the passphrase before deleting the key?

        logger.debug("KeyModel.deleteKey: self.getPrivateKeyFilePath() = " + self.getPrivateKeyFilePath())


        try:

            logger.debug("KeyModel.deleteKey: Deleting private key...")
            os.unlink(self.getPrivateKeyFilePath())
            logger.debug("KeyModel.deleteKey: Deleted private key!")

            logger.debug("KeyModel.deleteKey: Looking for public key...")
            if os.path.exists(self.getPrivateKeyFilePath() + ".pub"):
                logger.debug("KeyModel.deleteKey: Found public key: " + self.getPrivateKeyFilePath() + ".pub")
                logger.debug("KeyModel.deleteKey: Deleting public key...")
                os.unlink(self.getPrivateKeyFilePath() + ".pub")
            else:
                logger.debug("KeyModel.deleteKey: Public key not found.")

            # Remove key(s) from SSH agent:

            logger.debug("KeyModel.deleteKey: Removing Launcher public key(s) from agent.")

            publicKeysInAgentProc = subprocess.Popen([self.sshPathsObject.sshAddBinary.strip('"'),"-L"],stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
            publicKeysInAgent = publicKeysInAgentProc.stdout.readlines()
            for publicKey in publicKeysInAgent:
                if "Launcher" in publicKey:
                    tempPublicKeyFile = tempfile.NamedTemporaryFile(delete=False)
                    tempPublicKeyFile.write(publicKey)
                    tempPublicKeyFile.close()
                    try:
                        removePublicKeyFromAgent = subprocess.Popen([self.sshPathsObject.sshAddBinary.strip('"'),"-d",tempPublicKeyFile.name],stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
                        stdout, stderr = removePublicKeyFromAgent.communicate()
                        if stderr is not None and len(stderr) > 0:
                            logger.debug("KeyModel.deleteKeyAndRemoveFromAgent: " + stderr)
                        success = ("Identity removed" in stdout)
                    finally:
                        os.unlink(tempPublicKeyFile.name)
            logger.debug("KeyModel.deleteKeyAndRemoveFromAgent: Finished removing Launcher public key(s) from agent.")
        except:
            logger.debug("KeyModel.deleteKeyAndRemoveFromAgent: " + traceback.format_exc())
            return False

        return True

    def addKeyToAgent(self, passphrase, keyAddedSuccessfullyCallback, passphraseIncorrectCallback, privateKeyFileNotFoundCallback, failedToConnectToAgentCallback):

        success = False
        if not os.path.exists(self.sshPathsObject.sshKeyPath):
            privateKeyFileNotFoundCallback()
            return success

        if sys.platform.startswith('win'):
            # The patched OpenSSH binary on Windows/cygwin allows us
            # to send the passphrase via STDIN.
            cmdList = [self.sshPathsObject.sshAddBinary.strip('"'), self.getPrivateKeyFilePath()]
            logger.debug("KeyModel.addKeyToAgent: " + 'on Windows, so running: ' + str(cmdList))
            proc = subprocess.Popen(cmdList,
                                    stdin=subprocess.PIPE,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT,
                                    universal_newlines=True)
            stdout, stderr = proc.communicate(input=passphrase + '\r\n')

            if stdout is None or str(stdout).strip() == '':
                logger.debug("KeyModel.addKeyToAgent: " + '(1) Got EOF from ssh-add binary, probably because an empty passphrase was entered for a passphrase-locked key.')
                passphraseIncorrectCallback()
            elif stdout is not None and "No such file or directory" in stdout:
                logger.debug("KeyModel.addKeyToAgent: " + "addKeyToAgent couldn't find a private key")
                privateKeyFileNotFoundCallback()
                return False
            elif "Identity added" in stdout:
                success = True
                logger.debug("KeyModel.addKeyToAgent: " + "addKeyToAgent succesfully added a key to the agent")
                keyAddedSuccessfullyCallback()
            elif 'Bad pass' in stdout:
                logger.debug("KeyModel.addKeyToAgent: " + 'Got "Bad pass" from ssh-add binary')
                proc.kill()
                passphraseIncorrectCallback()
            elif 'Could not open a connection to your authentication agent' in stdout:
                logger.debug("KeyModel.addKeyToAgent: " + "Could not open a connection to your authentication agent.")
                failedToConnectToAgentCallback()
            else:
                logger.debug("KeyModel.addKeyToAgent: " + 'Got unknown error from ssh-add binary')
                logger.debug("KeyModel.addKeyToAgent: " + stdout)
        else:
            # On Linux or BSD/OSX we can use pexpect to talk to ssh-add.

            import pexpect

            args = [self.sshPathsObject.sshKeyPath]
            lp = pexpect.spawn(self.sshPathsObject.sshAddBinary, args=args)

            idx = lp.expect(["Enter passphrase", "Identity added"])

            if idx == 1:
                success = True
                logger.debug("addKeyToAgent %i %s sucesfully added the key to the agent, calling keyAddedSuccesfullCallback"%(threading.currentThread().ident,threading.currentThread().name))
                keyAddedSuccessfullyCallback()
            elif idx == 0:
                lp.sendline(passphrase)

                idx = lp.expect(["Identity added", "Bad pass", pexpect.EOF])
                if idx == 0:
                    success = True
                    logger.debug("addKeyToAgent %i %s sucesfully added the key to the agent, calling keyAddedSuccesfullCallback"%(threading.currentThread().ident,threading.currentThread().name))
                    keyAddedSuccessfullyCallback()
                elif idx == 1:
                    lp.kill(0)
                    logger.debug("addKeyToAgent %i %s determined the passphrase was incorrect, calling passphraseIncorrectCallback"%(threading.currentThread().ident,threading.currentThread().name))
                    passphraseIncorrectCallback()
                    success = False
                    return success
                elif idx == 2:
                    # ssh-add seems to fail silently if you don't enter a passphrase
                    # It will exit without displaying "Identity added" or "Bad passphrase".
                    lp.kill(0)
                    passphraseIncorrectCallback()
                    success = False
                    return success
            else:
                logger.debug("KeyModel.addKeyToAgent: " + "Unexpected result from attempt to add key.")
            lp.close()
        return success


    def removeKeyFromAgent(self):

        # FIXME
        # We use a method which doesn't require entering the key's passphrase :-)
        # but it just greps for Launcher in the agent's keys, rather than 
        # specifically identifying this key. :-(

        try:
            # Remove key(s) from SSH agent:

            logger.debug("Removing Launcher public key(s) from agent.")

            publicKeysInAgentProc = subprocess.Popen([self.sshPathsObject.sshAddBinary.strip('"'),"-L"],stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
            publicKeysInAgent = publicKeysInAgentProc.stdout.readlines()
            for publicKey in publicKeysInAgent:
                if "Launcher" in publicKey:
                    tempPublicKeyFile = tempfile.NamedTemporaryFile(delete=False)
                    tempPublicKeyFile.write(publicKey)
                    tempPublicKeyFile.close()
                    try:
                        removePublicKeyFromAgent = subprocess.Popen([self.sshPathsObject.sshAddBinary.strip('"'),"-d",tempPublicKeyFile.name],stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
                        stdout, stderr = removePublicKeyFromAgent.communicate()
                        if stderr is not None and len(stderr) > 0:
                            logger.debug("KeyModel.removeKeyFromAgent: " + stderr)
                        success = ("Identity removed" in stdout)
                    finally:
                        os.unlink(tempPublicKeyFile.name)
        except:
            logger.debug("KeyModel.removeKeyFromAgent: " + traceback.format_exc())
            return False

        return True
