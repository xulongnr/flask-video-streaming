#!/usr/bin/env python
# -- coding:utf-8 --


from redis_queue import RedisQueue, RedisMessageQueue
import time
import json


q_actions = RedisQueue('camera_actions')
q_act_res = RedisQueue('action_responses')
mq_result = RedisMessageQueue('camera_result')

for i in range(1):
    # q.put(i)

    # q_actions.put(json.dumps({"action_type": 0}))

    # q_actions.put(json.dumps({"action_type": 1}))

    # q_actions.put(json.dumps({"action_type": 2, "download_name": "capture_image.jpg"}))

    # q_actions.put(json.dumps({"action_type": 3}))

    # q_actions.put(json.dumps({"action_type": 4, "config": {"iso": "", "aperture": ""}}))

    # q_actions.put(json.dumps({"action_type": 5, "download_path": "download",
    #                          "config": {
    #                             "iso": "100",
    #                             "exposurecompensation": "-0.6",
    #                             "aperture": "8"
    #                          }}))


# time.sleep(2)
# while 1:
#     print(q_act_res.get_wait())

ps = mq_result.subscribe()
for item in ps.listen():
    # print('item_type:', item['type'])
    if item['type'] == 'message':
        # print(item['channel'], item['data'])
        # print(item['channel'])
        if item['channel'] == b'mq:camera_result':
            data = json.loads(item['data'])
            print('type:', data['type'])
            print('data', data)