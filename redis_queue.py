#!/usr/bin/env python
# -- coding:utf-8 --

import time
import redis

class RedisQueue(object):
    def __init__(self, name, namespace='queue', **redis_kwargs):
        # redis的默认参数为：host='localhost', port=6379, db=0， 其中db为定义redis database的数量
        # self.__db = redis.StrictRedis(host='localhost', port='6379', db=0, password='', **redis_kwargs) 
        self.__db = redis.Redis(**redis_kwargs)
        self.key = '%s:%s' % (namespace, name)

    def qsize(self):
        return self.__db.llen(self.key)  # 返回队列里面list内元素的数量

    def put(self, item):
        self.__db.rpush(self.key, item)  # 添加新元素到队列最右方

    def get_wait(self, timeout=None):
        # 返回队列第一个元素，如果为空则等待至有元素被加入队列（超时时间阈值为timeout，如果为None则一直等待）
        item = self.__db.blpop(self.key, timeout=timeout)
        # if item:
        #     item = item[1]  # 返回值为一个tuple
        return item

    def get_nowait(self):
        # 直接返回队列第一个元素，如果队列为空返回的是None
        item = self.__db.lpop(self.key)
        return item

class RedisMessageQueue(object):
    def __init__(self, channel, namespace='mq', **redis_kwargs):
        self._channel = '%s:%s' % (namespace, channel)
        self._rc = redis.StrictRedis(host='localhost', port='6379', db=3, password='', **redis_kwargs)
        
    def publish(self, data):
        self._rc.publish(self._channel, data)

    def subscribe(self):
        ps = self._rc.pubsub()
        ps.subscribe(self._channel)
        return ps

    def sub_num(self):
        num = self._rc.pubsub_numsub(self._channel)
        return num

class RedisMonitor(object):
    def __init__(self, **redis_kwargs):
        self._rc = redis.StrictRedis(host='localhost', port='6379', db=0, password='', **redis_kwargs)
        with self._rc.monitor() as m:
            for command in m.listen():
                print('monitor:', command)