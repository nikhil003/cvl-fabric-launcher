import requests
import wx
import cvlsshutils.RequestsSessionSingleton
import cvlsshutils.AAF_Auth
            
class shibbolethDance():


    def __init__(self,pubkey,parent,*args,**kwargs):
        self.pubkey=pubkey
        self.parent=parent
        if kwargs.has_key('idp'):
            self.idp=kwargs['idp']
        else:
            self.idp=None

    def postKey(self,r):
        p=cvlsshutils.AAF_Auth.AAF_Auth.genericForm()
        p.feed(r.text)
        nexturl = p.attrs['action']
        if  not 'http' in nexturl[0:4]:
            nexturl=r.url.split('/')[0]+'//'+r.url.split('/')[2]+nexturl
        p.inputs['ssh_pub_key']=self.pubkey

        r=self.session.post(nexturl,data=p.inputs,verify=False)
        if r.status_code!=200:
            raise Exception("%s"%r.text)

    def getIdP(self):
        return self.idp


    def copyID(self):

        # Use of a singleton here means that we should be able to do SSO on any AAF/Shibolleth web service. However we might have to guess the IdP.
        self.session=cvlsshutils.RequestsSessionSingleton.RequestsSessionSingleton().GetSession()
        destURL="https://118.138.241.242/cvl/"
        auth=cvlsshutils.AAF_Auth.AAF_Auth(self.session,destURL,parent=self.parent,idp=self.idp)
        self.idp=auth.getIdP()
        self.postKey(auth.response)
