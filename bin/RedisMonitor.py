#!/usr/bin/env python
#-*-coding: utf-8-*-
'''
Created on 2016年7月7日

@author: zhujin
'''

'''
key	tag	type	note
redis.connected_clients	port	GAUGE	已连接客户端的数量
redis.blocked_clients	port	GAUGE	正在等待阻塞命令（BLPOP、BRPOP、BRPOPLPUSH）的客户端的数量
redis.used_memory	port	GAUGE	由 Redis 分配器分配的内存总量，以字节（byte）为单位
redis.used_memory_rss	port	GAUGE	从操作系统的角度，返回 Redis 已分配的内存总量（俗称常驻集大小）
redis.mem_fragmentation_ratio	port	GAUGE	used_memory_rss 和 used_memory 之间的比率
redis.total_commands_processed	port	COUNTER	采集周期内执行命令总数
redis.rejected_connections	port	COUNTER	采集周期内拒绝连接总数
redis.expired_keys	port	COUNTER	采集周期内过期key总数
redis.evicted_keys	port	COUNTER	采集周期内踢出key总数
redis.keyspace_hits	port	COUNTER	采集周期内key命中总数
redis.keyspace_misses	port	COUNTER	采集周期内key拒绝总数
redis.keyspace_hit_ratio	port	GAUGE	访问命中率
'''

import redis
import json
import time
from endpoint import EndPoint as myendpoint
from logger import mylogger
import http_api

import os
PATH = os.path.split(os.path.realpath(__file__))[0]

logger = mylogger("REDIS STATUS", PATH+'/../logs/redis_status.log')


ENDPOINT = myendpoint()

REDIS_HOST="127.0.0.1"
REDIS_PORT=6379

FALCON_CLIETN_PUSH="http://127.0.0.1:1988/v1/push"

redis_metric_dict = {
            "total_connections_received": "COUNTER",
            "rejected_connections": "COUNTER",
            "connected_clients": "GAUGE",
            "blocked_clients": "GAUGE",

            "used_memory": "GAUGE",
            "used_memory_rss": "GAUGE",
            "mem_fragmentation_ratio": "GAUGE",

            "expired_keys": "COUNTER",
            "evicted_keys": "COUNTER",
            "keyspace_hits": "COUNTER",
            "keyspace_misses": "COUNTER",
            "keyspace_hit_ratio": "GAUGE",

            "total_commands_processed": "COUNTER",

            "total_net_input_bytes": "COUNTER",
            "total_net_output_bytes": "COUNTER",

            "expired_keys": "COUNTER",
            "evicted_keys": "COUNTER",

            "used_cpu_sys": "COUNTER",
            "used_cpu_user": "COUNTER",

            "slowlog_len": "COUNTER",
        }


class RedisStat(object):
    def __init__(self,host,port,passwd=None,tag=60):
        self.host = host
        self.port = port
        self.passwd = passwd
        self.tag = tag
        self.ts = int(time.time())

        try:
            self.conn = redis.Redis(host=self.host,port=self.port,password=self.passwd)
        except redis.exceptions.Exception,e:
            raise e

        self.rds_stat = self.__redis_stat()

    def __redis_stat(self):
        return self.conn.info()

    def __redis_alive(self):
        redis_is_alive = 0
        redis_ping = self.conn.ping()
        if redis_ping:
            redis_is_alive = 1

        redis_is_alive_ret = {
            "endpoint": ENDPOINT,
            "metric": "redis.alive",
            "tags": "port=%s" % self.port,
            "timestamp": self.ts,
            "value": redis_is_alive,
            "step": self.tag,
            "counterType": "GAUGE"
        }

        return redis_is_alive_ret

    def __redis_collect_stat(self):
        redis_stat_ret = []

        for k,v in self.rds_stat.items():
            #redis_metric_falcon = {}
            if k in redis_metric_dict.keys():
                redis_metric_falcon = {
                    "endpoint": ENDPOINT,
                    "metric": "redis.%s" % k,
                    "tags": "port=%s" % self.port,
                    "timestamp": self.ts,
                    "value": self.rds_stat[k],
                    "step": self.tag,
                    "counterType": "%s" % redis_metric_dict[k]
                }
            #else:
            #    redis_metric_falcon = {
            #        "endpoint": ENDPOINT,
            #        "metric": "redis.%s" % k,
            #        "tags": "port=%s" % self.port,
            #        "timestamp": self.ts,
            #        "value": self.rds_stat[k],
            #        "step": self.tag,
            #        "counterType": "GAUGE"
            #    }

                redis_stat_ret.append(redis_metric_falcon)

        return redis_stat_ret

    def redis_falcon_data(self):
        redis_falcon_stat = []
        redis_falcon_stat.append(self.__redis_alive())
        redis_falcon_stat = redis_falcon_stat + self.__redis_collect_stat()

        return redis_falcon_stat


def main():
    rds = RedisStat(REDIS_HOST,REDIS_PORT)
    mymetrics = rds.redis_falcon_data()
    logger.info(mymetrics)
    #print(json.dumps(mymetric, indent=4))
    logger.info(http_api.facon_push_handler(mymetrics,api=FALCON_CLIETN_PUSH))


if __name__ == '__main__':
    main()


