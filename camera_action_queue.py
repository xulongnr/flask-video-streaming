#!/usr/bin/env python
# -- coding:utf-8 --


from redis_queue import RedisQueue, RedisMessageQueue
import io
import os
import sys
import time
import json
import base64
from datetime import datetime

import gphoto2 as gp

q_actions = RedisQueue('camera_actions')
mq_result = RedisMessageQueue('camera_result')

sleep_delay = 5
camera_init = False

def _get_configs(_camera):
    data = []
    config = camera.get_config()
    config_count = config.count_children()
    if config_count < 0:
        return ''

    for child in config.get_children():
        label = '{} ({}),'.format(child.get_label(), child.get_name())
        # print(label, child.get_type(), child.count_children())
        child_data = {'name': child.get_name(), 'desc': child.get_label(), 'type': child.get_type(), 'count': child.count_children(), 'items': []}
        # if child.get_name() == 'settings':
        if child.get_name() != '':
            for item in child.get_children():
                item_label = '  {} ({}),'.format(item.get_label(), item.get_name())
                # print(item_label, str(item.get_type())+',', item.get_value())
                item_data = {'name': item.get_name(), 'desc': item.get_label(), 'type': item.get_type(),
                            #'count_child': item.count_children(),
                             'ro': item.get_readonly(), 'value':''}
                if item.get_type() == gp.GP_WIDGET_TEXT:
                    assert item.count_children() == 0
                    value = item.get_value()
                    if value:
                        if sys.version_info[0] < 3:
                            value = value.decode('utf-8')

                elif item.get_type() == gp.GP_WIDGET_RANGE:
                    assert item.count_children() == 0
                    try:
                        lo, hi, inc = item.get_value()
                        # print('  >', lo, hi, inc)
                        item_data['lo'] = lo
                        item_data['hi'] = hi
                        item_data['inc'] = inc
                    except Exception as e:
                        print('Exception on getting value: ', e)
                    else:
                        value = item.get_value()

                elif item.get_type() == gp.GP_WIDGET_TOGGLE:
                    assert item.count_children() == 0
                    value = item.get_value()
                    # print('  O', value, value != 0)
                    item_data['toggle'] = (value != 0)

                elif item.get_type() == gp.GP_WIDGET_RADIO:
                    assert item.count_children() == 0
                    value = item.get_value()
                    options = ''
                    choices = []
                    index = 0
                    for choice in item.get_choices():
                        if choice == value:
                            options += '(*)'
                            item_data['choice_index'] = index
                        options += choice + ', '
                        choices.append(choice)
                        index += 1
                    # print('  @', options)
                    item_data['choices'] = choices
                    item_data['choice_count'] = item.count_choices()

                elif item.get_type() == gp.GP_WIDGET_DATE:
                    assert item.count_children() == 0
                    value = item.get_value()
                    if value:
                        item_data['date'] = datetime.fromtimestamp(value).strftime("%Y-%m-%d %H:%M:%S")

                item_data['value'] = value

                if item.get_type() in [ gp.GP_WIDGET_TEXT,
                                        gp.GP_WIDGET_RANGE,
                                        gp.GP_WIDGET_TOGGLE,
                                        gp.GP_WIDGET_RADIO,
                                        gp.GP_WIDGET_DATE ]:
                    child_data['items'].append(item_data)

        data.append(child_data)

    return json.dumps(data, sort_keys=True)


def _get_config(_camera, _name):
    _config = _camera.get_config()
    item = _config.get_child_by_name(str(_name))
    if not item:
        return ''
    return item.get_value()


def _set_config(_camera, _name, _value):
    _config = _camera.get_config()
    item = _config.get_child_by_name(str(_name))
    if not item:
        return ''
    item.set_value(str(_value))
    _camera.set_config(_config)


"""
main procedure
"""
while True:
    print('MQ Subs:', mq_result.sub_num()[0])

    while q_actions.qsize():
        # print('init:', camera_init, 'qsize:', q.qsize())
        if not camera_init:
            camera = gp.Camera()
            camera.init()
            camera_init = True

        result = q_actions.get_wait(5)
        if not result:
            break
        # print(result[1])

        try:
            obj = json.loads(result[1])
            id = "00000000-0000-0000-0000-000000000000"
            if 'id' in obj:
                id = obj['id']
            type = obj['action_type']
            if type == 0: # capture preview
                camera_file = camera.capture_preview()
                file_data = gp.check_result(gp.gp_file_get_data_and_size(camera_file))
                # io.BytesIO
                # with open('preview.jpg', 'wb') as f:
                #     f.write(file_data)
                #     f.close()
                # q_img_p.put(base64.b64encode(file_data))
                data = base64.b64encode(file_data)
                mq_result.publish(json.dumps({"id": id, "type": type, "data": str(data)}))

            elif type == 1: # capture image
                file_path = camera.capture(gp.GP_CAPTURE_IMAGE)
                file_info = camera.file_get_info(file_path.folder, file_path.name)
                # q_img_t.put(file_path.folder + ',' + file_path.name + ',' + datetime.fromtimestamp(file_info.file.mtime).isoformat(' '))
                mq_result.publish(json.dumps({"id": id, "type": type, "r_folder": file_path.folder, "r_name": file_path.name, 
                    "time": file_info.file.mtime, 
                    # "time_str": datetime.fromtimestamp(file_info.file.mtime).isoformat(' ')
                }))

            elif type == 2: # capture image and download
                download_path = '.'
                if 'download_path' in obj:
                    download_path = str(obj['download_path'])
                if 'download_name' in obj:
                    file_name = str(obj['download_name'])
                else:
                    file_name = None

                file_path = camera.capture(gp.GP_CAPTURE_IMAGE)
                file_info = camera.file_get_info(file_path.folder, file_path.name)
                camera_file = camera.file_get(file_path.folder, file_path.name, gp.GP_FILE_TYPE_NORMAL)
                if not file_name:
                    file_suffix = os.path.splitext(file_path.name)[1]
                    file_name = datetime.fromtimestamp(file_info.file.mtime).isoformat('_') + file_suffix
                if not os.path.exists(download_path):
                    os.makedirs(download_path)
                saved_file_path = download_path + '/' + file_name
                camera_file.save(saved_file_path)
                camera.file_delete(file_path.folder, file_path.name)
                # q_img_d.put(saved_file_path)                
                mq_result.publish(json.dumps({"id": id, "type": type, "path": saved_file_path, "time": file_info.file.mtime}))

            elif type == 3: # get all configures
                # q_act_res.put(_get_configs(camera))
                mq_result.publish(json.dumps({"id": id, "type": type, "configs": _get_configs(camera)}))

            elif type == 4: # get config
                result = {}
                if 'config' in obj:
                    config = obj['config']

                    for key in config.keys():
                        # print key, config[key]
                        result[key] = _get_config(camera, key)

                # q_act_res.put(json.dumps({"config": result}))
                mq_result.publish(json.dumps({"id": id, "type": type, "config": result}))

            elif type == 5: # set config
                result = {}
                if 'config' in obj:
                    config = obj['config']

                    for key in config.keys():
                        # print key, config[key]
                        _set_config(camera, key, str(config[key]))
                        result[key] = _get_config(camera, key)

                # q_act_res.put(json.dumps({"config": result}))
                mq_result.publish(json.dumps({"id": id, "type": type, "config": result}))


        except Exception as e:
            print('Exception:', e)

    if camera_init:
        camera.exit()
        camera_init = False

    # print("after inner loop, init: {}, qsize: {}".format(camera_init, q.qsize()))
    time.sleep(sleep_delay)
