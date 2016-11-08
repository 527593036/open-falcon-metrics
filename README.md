# open-falcon metrics

上报metrics脚本汇总

# 工具说明

1、TengineReqStat.py,tengine状态监控工具(按域名)，上报到open-falcon
	
	1.1、tengine配置好reqstat（http_reqstatus模块）
	
	1.2、按域名从5个维度来监控nginx(req/min)
	
		1.2.1、流量
		
		1.2.2、并发连接数
		
		1.2.3、并发请求数
		
		1.2.4、req的平均时间
		
		1.2.5、upstream请求
		
	1.3、crontab部署每分钟执行一次
		
2、RedisMonitor.py，redis状态监控脚本

3、MemcachedMonitor.py, memcached状态监控脚本