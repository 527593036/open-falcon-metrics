#!/usr/bin/env python
#-*-coding: utf-8-*-
'''
Created on 2016年7月7日

@author: zhujin
'''

'''
nginx状态 数据上报到open-falcon，从5个维度监控nginx: 流量维度,并发连接数维度,并发请求数(状态码),req的平均时间维度,upstream维度
1、需要安装tengine

2、reqstat模块文档说明http://tengine.taobao.org/document_cn/http_reqstat_cn.html

3、某reqstat测试结果：
ansible.api.xz.com,192.168.33.11:80,164,456,2,2,2,0,0,0,0,12,2,12,2,2,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
192.168.33.11,192.168.33.11:23456,7317,6482,6,20,18,0,2,0,0,0,0,0,0,18,0,0,0,1,1,0,0,0,0,0,0,0,0,0,0
'''

import urllib2
import shutil
import time
from logger import mylogger
import http_api
import iniparse
from endpoint import EndPoint as myendpoint

import os
PATH = os.path.split(os.path.realpath(__file__))[0]


ENDPOINT = myendpoint()
    
logger = mylogger("TENGINE STATUS", PATH+'/../logs/nginx_status.log')
        
NGINX_STAT_FP_CUR = PATH + '/../logs/nginx.status.tmp'
NGINX_STAT_FP_AGO = PATH + '/../logs/nginx.status.monitor'

        
class TengineReqStat(object):
    def __init__(self,req_stat_url,step=60,domain_list=None):
        self.req_stat_url = req_stat_url
        self.step = step
        self.ts = int(time.time())
        self.ng_stat = self.__nginx_stat()
        self.ng_stat_domains = [ stat.strip().split(',')[0] for stat in self.ng_stat[0] ]
        self.monitor_domain_list = domain_list if domain_list else self.ng_stat_domains

    def __http_handler(self):
        handler = urllib2.HTTPHandler()
        opener = urllib2.build_opener(handler)
        request = urllib2.Request(self.req_stat_url)
        try:
            conn = opener.open(request)
            response = conn.headers.dict
            response['code'] = conn.code
            return [response,conn.read()]
        except urllib2.HTTPError, e:
            raise e

    def __nginx_stat(self):
        #ret = http_api.get_req(self.req_stat_url)[1]
        ret = self.__http_handler()[1]
        with open(NGINX_STAT_FP_CUR,'wb') as fp:
            fp.write(ret)
        #如果是第一次请求
        if not shutil.os.path.isfile(NGINX_STAT_FP_AGO):
            shutil.copyfile(NGINX_STAT_FP_CUR,NGINX_STAT_FP_AGO)
        
        with open(NGINX_STAT_FP_CUR,'r') as fp:
            nginx_stat_cur = [stat for stat in fp]
        with open(NGINX_STAT_FP_AGO,'r') as fp:
            nginx_stat_ago = [stat for stat in fp]
            
        return [nginx_stat_cur,nginx_stat_ago]
        
    def bindwith(self):
        '''
        流量维度
        stat[2] = bytes_in,stat[3] = bytes_out
        bytes_in 从客户端接收流量总和,bytes_out 发送到客户端流量总和
        换算成Kbit/s
        '''
        # 当前请求的结果
        ret1 = {}
        for stat in self.ng_stat[0]:
            stat = stat.strip().split(',')
            if stat[0] in self.monitor_domain_list:
                ret1[stat[0]] = [stat[1],stat[2],stat[3]]
            
        # 上一次请求的结果       
        ret2 = {}
        for stat in self.ng_stat[1]:
            stat = stat.strip().split(',')
            if stat[0] in self.monitor_domain_list:
                ret2[stat[0]] = [stat[1],stat[2],stat[3]]
        
        #按域名获取带宽的metrics,合成列表格式(包含字典)
        ret = []
        for domain in self.ng_stat_domains:
            if domain in self.monitor_domain_list:
                bindwith_in = int(float(int(ret1[domain][1]) - int(ret2[domain][1] if ret2[domain][1] else ret1[domain][1]))/1024*8)
                bindwith_out = int(float(int(ret1[domain][2]) - int(ret2[domain][2] if ret2[domain][2] else ret1[domain][2]))/1024*8)
                endpoint = ENDPOINT
                http_port = ret1[domain][0].split(':')[1]
            
                bind_with_in_metric = {
                    'endpoint': endpoint,
                    'metric': 'nginx.Kbit_in',
                    'timestamp': self.ts,
                    'step': self.step,
                    'value': bindwith_in,
                    'counterType': 'GAUGE',
                    'tags': 'domain=%s,http_port=%s' % (domain,http_port)
                }
                ret.append(bind_with_in_metric)
            
                bind_with_out_metric = {
                    'endpoint': endpoint,
                    'metric': 'nginx.Kbit_out',
                    'timestamp': self.ts,
                    'step': self.step,
                    'value': bindwith_out,
                    'counterType': 'GAUGE',
                    'tags': 'domain=%s,http_port=%s' % (domain,http_port)
                }
                ret.append(bind_with_out_metric)

        return ret
        
    def conn_total(self):
        '''
        并发连接数维度
        stat[0]=host,stat[1]=ip:port,stat[4]=conn_total
        conn_total 处理过的连接总数
        '''
        # 当前请求的结果
        ret1 = {}
        for stat in self.ng_stat[0]:
            stat = stat.strip().split(',')
            if stat[0] in self.monitor_domain_list:
                ret1[stat[0]] = [stat[1],stat[4]]
            
        # 上一次请求的结果        
        ret2 = {}
        for stat in self.ng_stat[1]:
            stat = stat.strip().split(',')
            if stat[0] in self.monitor_domain_list:
                ret2[stat[0]] = [stat[1],stat[4]]
        
        #按域名获取总连接数的metrics,合成列表格式(包含字典)
        ret = []
        for domain in self.ng_stat_domains:
            if domain in self.monitor_domain_list:
                endpoint = ENDPOINT
                http_port = ret1[domain][0].split(':')[1]
                conn_total = int(ret1[domain][1]) - int(ret2[domain][1] if ret2[domain][1] else ret1[domain][1])
                conn_total_metric = {
                    'endpoint': endpoint,
                    'metric': 'nginx.conn',
                    'timestamp': self.ts,
                    'step': self.step,
                    'value': conn_total,
                    'counterType': 'GAUGE',
                    'tags': 'domain=%s,http_port=%s' % (domain,http_port)
                }
            
                ret.append(conn_total_metric)
        
        return ret
        
    def http_code(self):
        '''
        并发请求数(状态码)
        stat[0]=host,stat[1]=ip:port,stat[5]=req_total
        stat[6]=http_2xx,stat[7]=http_3xx,stat[8]=http_4xx
        stat[9]=http_5xx,stat[10]=httpotherstatus
        req_total 处理过的总请求数
        http_2xx 2xx请求的总数
        http_3xx 3xx请求的总数
        http_4xx 4xx请求的总数
        http_5xx 5xx请求的总数
        httpotherstatus 其他请求的总数
        '''
        # 当前请求的结果
        ret1 = {}
        for stat in self.ng_stat[0]:
            stat = stat.strip().split(',')
            if stat[0] in self.monitor_domain_list:
                ret1[stat[0]] = [stat[1],stat[5],stat[6],stat[7],stat[8],stat[9],stat[10]]
            
        #上一次请求的结果        
        ret2 = {}
        for line in self.ng_stat[1]:
            stat = line.strip().split(',')
            if stat[0] in self.monitor_domain_list:
                ret2[stat[0]] = [stat[1],stat[5],stat[6],stat[7],stat[8],stat[9],stat[10]]
        
        #按域名获取请求数的metrics,合成列表格式(包含字典)
        ret = []
        for domain in self.ng_stat_domains:
            if domain in self.monitor_domain_list:
                req_total = int(ret1[domain][1]) - int(ret2[domain][1] if ret2[domain][1] else ret1[domain][1])
                http_2xx = int(ret1[domain][2]) - int(ret2[domain][2] if ret2[domain][2] else ret1[domain][2])
                http_3xx = int(ret1[domain][3]) - int(ret2[domain][3] if ret2[domain][3] else ret1[domain][3])
                http_4xx = int(ret1[domain][4]) - int(ret2[domain][4] if ret2[domain][4] else ret1[domain][4])
                http_5xx = int(ret1[domain][5]) - int(ret2[domain][5] if ret2[domain][5] else ret1[domain][5])
                http_other = int(ret1[domain][6]) - int(ret2[domain][6] if ret2[domain][6] else ret1[domain][6])
                endpoint = ENDPOINT 
                http_port = ret1[domain][0].split(':')[1]
            
                req_total_metric = {
                    'endpoint': endpoint,
                    'metric': 'nginx.req_total',
                    'timestamp': self.ts,
                    'step': self.step,
                    'value': req_total,
                    'counterType': 'GAUGE',
                    'tags': 'domain=%s,http_port=%s' % (domain,http_port)
                }
                ret.append(req_total_metric)
            
                http_2xx_metric = {
                    'endpoint': endpoint,
                    'metric': 'nginx.http_2xx',
                    'timestamp': self.ts,
                    'step': self.step,
                    'value': http_2xx,
                    'counterType': 'GAUGE',
                    'tags': 'domain=%s,http_port=%s' % (domain,http_port)
                }
                ret.append(http_2xx_metric)
            
                http_3xx_metric = {
                    'endpoint': endpoint,
                    'metric': 'nginx.http_3xx',
                    'timestamp': self.ts,
                    'step': self.step,
                    'value': http_3xx,
                    'counterType': 'GAUGE',
                    'tags': 'domain=%s,http_port=%s' % (domain,http_port)
                }
                ret.append(http_3xx_metric)
            
                http_4xx_metric = {
                    'endpoint': endpoint,
                    'metric': 'nginx.http_4xx',
                    'timestamp': self.ts,
                    'step': self.step,
                    'value': http_4xx,
                    'counterType': 'GAUGE',
                    'tags': 'domain=%s,http_port=%s' % (domain,http_port)
                }
                ret.append(http_4xx_metric)
            
                http_5xx_metric = {
                    'endpoint': endpoint,
                    'metric': 'nginx.http_5xx',
                    'timestamp': self.ts,
                    'step': self.step,
                    'value': http_5xx,
                    'counterType': 'GAUGE',
                    'tags': 'domain=%s,http_port=%s' % (domain,http_port)
                }
                ret.append(http_5xx_metric)
            
                httpotherstatus_metric = {
                    'endpoint': endpoint,
                    'metric': 'nginx.http_other_status',
                    'timestamp': self.ts,
                    'step': self.step,
                    'value': http_other,
                    'counterType': 'GAUGE',
                    'tags': 'domain=%s,http_port=%s' % (domain,http_port)
                }
                ret.append(httpotherstatus_metric)
                
        return ret
        
    def req_time(self):
        '''
        req的平均时间维度
        stat[0]=host,stat[1]=ip:port,stat[5]=req_total
        stat[11]=rt,stat[12]=ups_req,stat[13]=ups_rt
        stat[11]/stat[5]:总时间平均
        req_total 处理过的总请求数
        rt rt的总数,是请求的响应时间总和
        ups_req 需要访问upstream的请求总数    
        ups_rt 访问upstream的总rt,是后端的响应时间总和
        单位ms
        '''
        # 当前请求的结果
        ret1 = {}
        for stat in self.ng_stat[0]:
            stat = stat.strip().split(',')
            if stat[0] in self.monitor_domain_list:
                ret1[stat[0]] = [stat[1],stat[5],stat[11],stat[12],stat[13]]
                
        # 上一次请求的结果  
        ret2 = {}
        for line in self.ng_stat[1]:
            stat = line.strip().split(',')
            if stat[0] in self.monitor_domain_list:
                ret2[stat[0]] = [stat[1],stat[5],stat[11],stat[12],stat[13]]
        
        # 平均时间消耗计算
        ret = []
        for domain in self.ng_stat_domains:
            if domain in self.monitor_domain_list:
                cur_req_time = int(ret1[domain][2])-int(ret2[domain][2] if ret2[domain][2] else ret1[domain][2])
                cur_req_count = int(ret1[domain][1])-int(ret2[domain][1] if ret2[domain][1] else ret1[domain][1])
                cur_ups_req_time = int(ret1[domain][4])-int(ret2[domain][4] if ret2[domain][4] else ret1[domain][4])
                cur_ups_req_count = int(ret1[domain][3])-int(ret2[domain][3] if ret2[domain][3] else ret1[domain][3])
                # 总平均耗时
                cur_req_avg_time = round(float(cur_req_time)/cur_req_count,1) if cur_req_count else 0
                # upstream总平均耗时
                cur_ups_req_avg_time = round(float(cur_ups_req_time)/cur_ups_req_count,1) if cur_ups_req_count else 0
                endpoint = ENDPOINT 
                http_port = ret1[domain][0].split(':')[1]
                
                req_rt = {
                    'endpoint': endpoint,
                    'metric': 'nginx.req_rt',
                    'timestamp': self.ts,
                    'step': self.step,
                    'value': cur_req_avg_time,
                    'counterType': 'GAUGE',
                    'tags': 'domain=%s,http_port=%s' % (domain,http_port)
                }
                ret.append(req_rt)
                
                ups_rt = {
                    'endpoint': endpoint,
                    'metric': 'nginx.ups_rt',
                    'timestamp': self.ts,
                    'step': self.step,
                    'value': cur_ups_req_avg_time,
                    'counterType': 'GAUGE',
                    'tags': 'domain=%s,http_port=%s' % (domain,http_port)
                }
                ret.append(ups_rt)

        return ret
        
    def ups_req(self):
        '''
        upstream维度
        ups_req 需要访问upstream的请求总数 
        httpups4xx upstream返回4xx响应的请求总数
        httpups5xx upstream返回5xx响应的请求总数
        '''
        # 当前请求的结果
        ret1 = {}
        for stat in self.ng_stat[0]:
            stat = stat.strip().split(',')
            if stat[0] in self.monitor_domain_list:
                ret1[stat[0]] = [stat[1],stat[12],stat[29],stat[30]]
                
        # 上一次请求的结果  
        ret2 = {}
        for stat in self.ng_stat[1]:
            stat = stat.strip().split(',')
            if stat[0] in self.monitor_domain_list:
                ret2[stat[0]] = [stat[1],stat[12],stat[29],stat[30]]
        
        #按域名获取ups请求数的metrics,合成列表格式(包含字典)
        ret = []
        for domain in self.ng_stat_domains:
            if domain in self.monitor_domain_list:
                ups_req = int(ret1[domain][1]) - int(ret2[domain][1] if ret2[domain][1] else ret1[domain][1])
                ups_http_4xx = int(ret1[domain][2]) - int(ret2[domain][2] if ret2[domain][2] else ret1[domain][2])
                ups_http_5xx = int(ret1[domain][3]) - int(ret2[domain][3] if ret2[domain][3] else ret1[domain][3])
                endpoint = ENDPOINT 
                http_port = ret1[domain][0].split(':')[1]
            
                ups_req_metric = {
                    'endpoint': endpoint,
                    'metric': 'nginx.ups_req',
                    'timestamp': self.ts,
                    'step': self.step,
                    'value': ups_req,
                    'counterType': 'GAUGE',
                    'tags': 'domain=%s,http_port=%s' % (domain,http_port)
                }
                ret.append(ups_req_metric)
            
                ups_http_4xx_metric = {
                    'endpoint': endpoint,
                    'metric': 'nginx.ups_http_4xx',
                    'timestamp': self.ts,
                    'step': self.step,
                    'value': ups_http_4xx,
                    'counterType': 'GAUGE',
                    'tags': 'domain=%s,http_port=%s' % (domain,http_port)
                }
                ret.append(ups_http_4xx_metric)
            
                http_ups_5xx_metric = {
                    'endpoint': endpoint,
                    'metric': 'nginx.ups_http_5xx',
                    'timestamp': self.ts,
                    'step': self.step,
                    'value': ups_http_5xx,
                    'counterType': 'GAUGE',
                    'tags': 'domain=%s,http_port=%s' % (domain,http_port)
                }
                ret.append(http_ups_5xx_metric)
            
        return ret
        
    def updatefp(self):
        shutil.os.remove(NGINX_STAT_FP_AGO)
        shutil.move(NGINX_STAT_FP_CUR,NGINX_STAT_FP_AGO)
    

def main():    
    domain_list = iniparse.domains_parser()
    req_stats_api = iniparse.TENGINE_STAT_API
    open_falcon_api = iniparse.FALCON_PUSH_API
    if domain_list:
        ng_req_stat = TengineReqStat(req_stats_api,domain_list=domain_list)
    else:
        ng_req_stat = TengineReqStat(req_stats_api)
    
    ng_req_stat.updatefp()
    mymetrics = ng_req_stat.bindwith() + ng_req_stat.conn_total() + ng_req_stat.http_code() + ng_req_stat.req_time() + ng_req_stat.ups_req()
    logger.info(mymetrics)
    logger.info(http_api.facon_push_handler(mymetrics,api=open_falcon_api))
    

if __name__ == '__main__':
    main()
