#!/usr/bin/env python
#-*-coding: utf-8-*-
'''
Created on 2016年10月31日

@author: zhujin
'''

import os
import socket

def EndPoint():
    ret = ''
    filepath = "/app/readme/HostName.md"
    if os.path.isfile(filepath):
        with open(filepath) as fp:
            for line in fp:
                if line.startswith('HOSTNAME'):
                    ret = line.strip().split('=')[1]
    else:
        ret = socket.gethostname()

    return ret