#-*-coding: utf-8-*-
'''
Created on 2016年10月23日

@author: zhujin
'''
import httplib2
import json
from logger import mylogger
import urllib2

import os
PATH = os.path.split(os.path.realpath(__file__))[0]

FALCON_PUSH_API = "http://127.0.0.1:1988/v1/push"

def http_api(api,method='GET',metrics=None):
    ret = []
    http = httplib2.Http()
    logger = mylogger("NGINX STATUS", PATH+'/../logs/nginx_status.log')
    req_body = json.dumps(metrics)
    logger.info(req_body)
    try:
        if method == 'GET':
            response, content = http.request(api,'GET')
            ret = [response,content]
        elif method == 'POST':
            response, content = http.request(api,'POST',body=req_body, headers={'Content-Type': 'application/json'})
            ret = [response,content]
        return ret
    except httplib2.HttpLib2Error, e:
        raise e
        
        
def get_req(api):
    ret = []
    http = httplib2.Http()
    
    try:
        response, content = http.request(api,'GET')
        ret = [response,content]
        return ret
    except httplib2.HttpLib2Error, e:
        raise e
        
def post_req(api,metrics):
    ret = []
    http = httplib2.Http()
    req_body = json.dumps(metrics)
    try:
        response, content = http.request(api,'POST',body=req_body, headers={'Content-Type': 'application/json'})
        ret = [response,content]
        return ret
    except httplib2.HttpLib2Error, e:
        raise e

def facon_push_handler(metrics, api=FALCON_PUSH_API):
    method = "POST"
    handler = urllib2.HTTPHandler()
    opener = urllib2.build_opener(handler)
    request = urllib2.Request(api, data=json.dumps(metrics))
    request.add_header("Content-Type",'application/json')
    request.get_method = lambda: method  #
    try:
        conn = opener.open(request)
        response = conn.headers.dict
        response['code'] = conn.code
        return [response,conn.read()]
    except urllib2.HTTPError,e:
        raise e