def singleton(cls):
    instances = {}
    def getinstance():
        if cls not in instances:
            instances[cls] = cls()
        return instances[cls]
    return getinstance

@singleton
class RequestsSessionSingleton():

    def __init__(self):
        import requests
        self.session = requests.Session()
        self.idp=None

    def GetSession(self):
        return self.session

    def SetIdP(self,idp):
        pass

    def GetIdP(self):
        return self.idp
