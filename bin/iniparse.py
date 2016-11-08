#-*-coding: utf-8-*-
'''
Created on 2016年10月23日

@author: zhujin
'''

import ConfigParser
import os

PATH = os.path.split(os.path.realpath(__file__))[0]

def domains_parser():
    ret = []
    conf = ConfigParser.ConfigParser()
    CONFPATH = PATH + '/../conf/domains.ini'
    conf.read(CONFPATH)
    for sec in conf.sections():
        for k, v in conf.items(sec):
            ret += v.split(',')
            
    return ret
    
def api_parser(api_sec):
    ret = {}
    conf = ConfigParser.ConfigParser()
    confpath = PATH + '/../conf/api.ini'
    conf.read(confpath)
    for sec in conf.sections():
        if sec == api_sec:
            for k, v in conf.items(sec):
                ret[k] = v
            
    return ret.values()[0]
    
TENGINE_STAT_API = api_parser('tengine')
FALCON_PUSH_API = api_parser('falcon-agent')

if __name__ == '__main__':
    print(domains_parser())
    print(TENGINE_STAT_API)
    print(FALCON_PUSH_API)
    