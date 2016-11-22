#!/usr/bin/env python
#-*-coding: utf-8-*-
'''
Created on 2016年7月7日

@author: zhujin
'''

'''
key	tag	type	note
memcached.get_hit_ratio	port(实例端口号)	GAUGE	get命令总体命中率
memcached.incr_hit_ratio	port(实例端口号)	GAUGE	incr命令总体命中率
memcached.decr_hit_ratio	port(实例端口号)	GAUGE	decr命令总体命中率
memcached.delete_hit_ratio	port(实例端口号)	GAUGE	delete命令总体命中率
memcached.usage	port(实例端口号)	GAUGE	分配内存使用率，等于byte/limitmaxbyte
'''

import memcache
import json
import time
from endpoint import EndPoint as myendpoint
from logger import mylogger
import http_api

import os
PATH = os.path.split(os.path.realpath(__file__))[0]

logger = mylogger("MEMCACHED STATUS", PATH+'/../logs/memcached_status.log')

ENDPOINT = myendpoint()

MEMCACHED_HOST = "127.0.0.1"
MEMCACHED_PORT = "11211"
FALCON_CLIETN_PUSH = "http://127.0.0.1:1988/v1/push"


memcached_metric_dict = {
    "get_hit_ratio": "GAUGE",
    "incr_hit_ratio": "GAUGE",
    "decr_hit_ratio": "GAUGE",
    "delete_hit_ratio": "GAUGE",
    "usage": "GAUGE"
}


class MemcachedStats(object):
    def __init__(self, host, port, tag=60):
        self.host = host
        self.port = port
        self.tag = tag
        self.ts = int(time.time())

        try:
            self.mc = memcache.Client(["%s:%s" % (self.host, self.port)])
        except Exception, e:
            raise e

        self.memcache_stat = self.__memcached_stat()

    def __memcached_stat(self):
        mem_stat = self.mc.get_stats()[0][1]

        ret = {}
        ret['usage'] = str(100 * float(mem_stat['bytes']) / float(mem_stat['limit_maxbytes']))
        get_total = float(mem_stat['get_hits']) + float(mem_stat['get_misses'])
        ret['get_hit_ratio'] = str(100*float(mem_stat['get_hits']) / get_total if get_total else 0.0)

        incr_total = float(mem_stat['incr_hits']) + float(mem_stat['incr_misses'])
        ret['incr_hit_ratio'] = str(100 * float(mem_stat['incr_hits']) / incr_total if incr_total else 0.0)

        decr_total = float(mem_stat['incr_hits']) + float(mem_stat['incr_misses'])
        ret['decr_hit_ratio'] = str(100 * float(mem_stat['decr_hits']) / decr_total if decr_total else 0.0)

        delete_total = float(mem_stat['delete_hits']) + float(mem_stat['delete_misses'])
        ret['delete_hit_ratio'] = str(100 * float(mem_stat['delete_hits']) / delete_total if delete_total else 0.0)

        return ret

    def memcached_falcon_data(self):
        memcached_stat_ret = []
        for k,v in self.memcache_stat.items():
            memcached_metric_falcon = {
                "endpoint": ENDPOINT,
                "metric": "memcached.%s" % k,
                "tags": "port=%s" % self.port,
                "timestamp": self.ts,
                "value": self.memcache_stat[k],
                "step": self.tag,
                "counterType": "%s" % memcached_metric_dict[k]
            }

            memcached_stat_ret.append(memcached_metric_falcon)

        return memcached_stat_ret


def main():
    mem = MemcachedStats(MEMCACHED_HOST, MEMCACHED_PORT)
    mymetrics = mem.memcached_falcon_data()
    print(json.dumps(mymetrics, indent=4))
    logger.info(mymetrics)
    logger.info(http_api.facon_push_handler(mymetrics, api=FALCON_CLIETN_PUSH))


if __name__ == '__main__':
    main()