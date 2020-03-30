import os
import configparser

class Config():
    '''配置类'''
    def __init__(self, filePath=None):
        if filePath:
            configPath = filePath
        else:
            root_dir = os.path.dirname(os.path.abspath(__file__))
            configPath = os.path.join(root_dir,"config.ini")
        
        self.cf = configparser.ConfigParser()
        self.cf.read(configPath,encoding='utf-8-sig')
    def getValue(self,parm):
        value = self.cf.get("info",parm)
        return value
 