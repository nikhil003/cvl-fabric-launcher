import sys
import dialogtext
import wx
import Queue
from logger.Logger import logger
import siteConfig
dialogs=dialogtext.default()
if sys.platform.startswith("darwin"):
    from MacMessageDialog import LauncherMessageDialog
elif sys.platform.startswith("win"):
    from WindowsMessageDialog import LauncherMessageDialog
elif sys.platform.startswith("linux"):
    from LinuxMessageDialog import LauncherMessageDialog
class SharedSessions:
    def __init__(self,parent,idp,username,*args,**kwargs):
        self.parent=parent
        self.idp=idp
        self.username=username
        

    def getPassphrase(self,queue):
        import cvlsshutils.PassphraseDialog
        dlg=cvlsshutils.PassphraseDialog.passphraseDialog(self.parent,None,wx.ID_ANY,"title","text","OK","Cancel")
        (canceled,value) = dlg.getPassword()
        if canceled:
            queue.put(None)
        else:
            queue.put(value)

    def showShareFailedMessage(self,q):
        dlg = LauncherMessageDialog(self.parent, dialogs.shareFailedMessage.message, self.parent.programName, helpEmailAddress="help@massive.org.au" )
        dlg.ShowModal()
        dlg.Destroy()
        q.put(None)

    def beginBusyCursor(self):
        try:
            wx.BeginBusyCursor()
        except:
            pass
    def endBusyCursor(self):
        try:
            wx.EndBusyCursor()
        except:
            pass

    def shareSession(self,loginProcess):
        import cvlsshutils.RequestsSessionSingleton
        import cvlsshutils.AAF_Auth
        if len(self.parent.loginProcess)<1:
            q=Queue.Queue()
            wx.CallAfter(lambda:self.showShareFailedMessage(q))
            q.get()
            return
        q=Queue.Queue()
        self.parent.loginProcess[0].getSharedSession(q)
            
        wx.CallAfter(self.beginBusyCursor)
        self.session=cvlsshutils.RequestsSessionSingleton.RequestsSessionSingleton().GetSession()
        baseURL="https://autht.massive.org.au/strudel_share/"
        kwargs={}
        if self.username!=None:
            kwargs['aaf_username']=self.username
        if self.idp!=None:
            kwargs['aaf_idp']=self.idp
        auth=cvlsshutils.AAF_Auth.AAF_Auth(self.session,baseURL+'login',parent=self.parent,**kwargs)
        auth.auth_cycle()
        sc=q.get()
        wx.CallAfter(self.endBusyCursor)
        mydict={}
        mydict['Saved Session']=sc
        import json
        sessionData=json.dumps(mydict,cls=siteConfig.GenericJSONEncoder,sort_keys=True,indent=4,separators=(',',': '))
        r = self.session.post(baseURL+'login',data={'username':'test','password':'mysupersecret'},verify=False)
        print r.status_code
        print r.text
        data={'data':sessionData}
        r = self.session.post(baseURL+'save_config',data=data,verify=False)
        print r.status_code
        print r.text
        key = json.loads(r.text)['key']
        print "saved s sharedSesion with key %s"%key

    def retrieveSession(self):
        import cvlsshutils.RequestsSessionSingleton
        import cvlsshutils.AAF_Auth
        self.session=cvlsshutils.RequestsSessionSingleton.RequestsSessionSingleton().GetSession()
        wx.CallAfter(self.beginBusyCursor)
        baseURL="https://autht.massive.org.au/strudel_share/"
        kwargs={}
        if self.username!=None:
            kwargs['aaf_username']=self.username
        if self.idp!=None:
            kwargs['aaf_idp']=self.idp
        auth=cvlsshutils.AAF_Auth.AAF_Auth(self.session,baseURL,parent=self.parent,**kwargs)
        auth.auth_cycle()
        r = self.session.post(baseURL+'login',data={'username':'test','password':'mysupersecret'},verify=False)
        print r.status_code
        print r.text
        success=False
        canceled=False
        while not success and not canceled:
            q=Queue.Queue()
            wx.CallAfter(self.getPassphrase,q)
            key=q.get()
            print key
            if key!=None:
                r = self.session.get(baseURL+'get_config',params={'key':key},verify=False)
                if r.status_code == 200:
                    success=True
            else:
                canceled=True
        print r.text
        print "retrieving a shared session"
        import StringIO
        import json
        f=StringIO.StringIO(json.loads(r.text)['data'])
        self.parent.loadSession(f)
        wx.CallAfter(self.endBusyCursor)

#
#    def saveSessionThreadTarget(self,q):
#        filename = q.get(block=True)
#        sc = q.get(block=True)
#        if sc!=None and filename!=None:
#            try:
#                f=open(filename,'w')
#                logger.debug('opened file %s to save the session to'%filename)
#            except Exception as e:
#                logger.debug('error opening file for saving')
#                raise e
#            logger.debug('retrieved the session configuration from the loginProcess')
#        if sc==None:
#            sc=q.get()
#        if sc==None:
#            return
#        mydict={}
#        mydict['Saved Session']=sc
#        import json
#        s=json.dumps(mydict,f,cls=siteconfig.genericjsonencoder,sort_keys=true,indent=4,separators=(',',': '))
#        f.write(s)
#        f.close()
#
#        
#
#
#    def saveSession(self):
#        import Queue
#        q=Queue.Queue()
#        dlg=wx.FileDialog(self,"Save your desktop session",style=wx.FD_SAVE|wx.FD_OVERWRITE_PROMPT)
#        status=dlg.ShowModal()
#        if status==wx.ID_CANCEL:
#            logger.debug('saveSession cancelled')
#            return
#        filename=dlg.GetPath()
#        q.put(filename)
#        # Abuse of queue.get as a flow control mechanism.
#        t=threading.Thread(target=self.loginProcess[0].getSharedSession,args=[q])
#        t.start()
#        t=threading.Thread(target=self.saveSessionThreadTarget,args=[q])
#        t.start()
