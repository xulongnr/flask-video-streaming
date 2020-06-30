#!/usr/bin/env python
from importlib import import_module
import os
import sys
import json
import exifread
from datetime import datetime
from flask import Flask, render_template, Response, jsonify, Blueprint, request, redirect, abort
from flask_swagger import swagger
from flask_swagger_ui import get_swaggerui_blueprint


app = Flask(__name__)
_camera = None

@app.route('/')
def index():
    """Video streaming home page."""
    return render_template('index.html')


@app.route('/api/spec')
def spec():
    swag = swagger(app, prefix='/api')
    swag['info']['version'] = "1.0"
    swag['info']['title'] = "Flask Author DB"
    return jsonify(swag) 


def gen(camera):
    """Video streaming generator function."""
    while True:
        frame = camera.get_frame()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')


@app.route('/api/live_view', methods=['DELETE'])
def live_view_del():
    global _camera
    if _camera != None:
        del _camera
        _camera = None
        return '', 204

    return '', 400


@app.route('/api/live_view')
def live_view():
    """Video streaming route. Put this in the src attribute of an img tag."""
    
    # import camera driver
    if os.environ.get('CAMERA'):
        Camera = import_module('camera_' + os.environ['CAMERA']).Camera
    else:
        from camera import Camera

    # Raspberry Pi camera module (requires picamera package)
    # from camera_pi import Camera

    global _camera
    if _camera == None:
        _camera = Camera()

    return Response(gen(_camera),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


import gphoto2 as gp


@app.route('/api/configs')
def get_configs():
    data = []
    camera = gp.Camera()
    camera.init()
    config = camera.get_config()
    config_count = config.count_children()
    if config_count < 0:
        abort(400)

    for child in config.get_children():
        label = '{} ({}),'.format(child.get_label(), child.get_name())
        print label, child.get_type(), child.count_children()
        child_data = {'name': child.get_name(), 'desc': child.get_label(), 'type': child.get_type(), 'count': child.count_children(), 'items': []}
        #if child.get_name() == 'settings':
        if child.get_name() != '':
            for item in child.get_children():
                item_label = '  {} ({}),'.format(item.get_label(), item.get_name())
                print item_label, str(item.get_type())+',', item.get_value()
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
                    lo, hi, inc = item.get_value()
                    #print '  >', lo, hi, inc
                    item_data['lo'] = lo
                    item_data['hi'] = hi
                    item_data['inc'] = inc

                elif item.get_type() == gp.GP_WIDGET_TOGGLE:
                    assert item.count_children() == 0
                    value = item.get_value()
                    #print '  O', value, value != 0
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
                    #print '  @', options
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

    camera.exit()
    return Response(json.dumps(data), mimetype='application/json')


@app.route('/api/config')
def get_config_params():
    config_name = request.args.get('name')
    if not config_name:
        abort(400)
    return get_config(config_name)


@app.route('/api/config/<string:config_name>')
def get_config(config_name):
    camera = gp.Camera()
    camera.init()
    config = camera.get_config()
    item = config.get_child_by_name(str(config_name))
    camera.exit()
    return Response(json.dumps({config_name: item.get_value()}), mimetype='application/json')


@app.route('/api/config', methods=['PUT'])
def set_config_params():
    if not request.json or not 'name' in request.json or not 'value' in request.json:
        abort(400)
    config_name = request.json['name']
    config_value = request.json['value']
    return _set_config(config_name, config_value)


@app.route('/api/config/<string:config_name>', methods=['PUT'])
def set_config(config_name):
    if not request.json or not 'value' in request.json:
        abort(400)

    config_value = request.json['value']
    return _set_config(config_name, config_value)


def _set_config(name, value):
    camera = gp.Camera()
    camera.init()
    config_value = ''
    try:
        config = camera.get_config()
        item = config.get_child_by_name(str(name))
        if not item:
            abort(400)
   
        # set 
        if type(value) is unicode:
            item.set_value(str(value))
        else:
            item.set_value(value)
        camera.set_config(config)
        #yield camera

        # get
        config = camera.get_config()
        item = config.get_child_by_name(str(name))
        if not item:
            abort(400)
        config_value = item.get_value()

    finally:
        camera.exit()

    return jsonify({name: config_value})


@app.route('/api/summary')
def get_summary():
    camera = gp.Camera()
    camera.init()
    summary = camera.get_summary()
    camera.exit()
    return Response(str(summary))
    

import piggyphoto

@app.route('/api/configs')
def list_config():
    cam = piggyphoto.camera()
    config = cam.list_config()
    return Response(json.dumps({'config': config}), mimetype='application/json')


@app.route('/api/capture_preview')
def capture_preview(filename='capture_preview.jpg'):
    cam = piggyphoto.camera()
    cam.capture_preview(filename)
    with open(filename, "rb") as f:
        image = f.read()
    return Response(image, mimetype='image/jpeg')


@app.route('/api/capture_image')
def capture_image(filename='capture_image.jpg'):
    cam = piggyphoto.camera()
    cam.capture_image(filename)
    with open(filename, "rb") as f:
        image = f.read()
    return Response(image, mimetype='image/jpeg')


@app.route('/api/exif_image')
def exif_preview(filename='capture_image.jpg'):
    data = _get_exif(filename)
    return Response(json.dumps(data), mimetype='application/json')


def _get_exif(path):
    exif_json = {}
    with open(path, 'rb') as pf:
        exif = exifread.process_file(pf)
        exif_info = {}
        prefixes = ['EXIF', 'MakerNote', 'Image', 'Thumbnail', 'Interoperability', 'GPS']
        #for prefix in prefixes:
        #    exif_info[prefix] = []
        #    for key in exif.keys():
        #        if key.startswith(prefix):
        #            exif_info[prefix].append(key)
        #print exif_info    
       
        for prefix in prefixes:
            exif_json[prefix] = {} 

            #for key in exif.keys():
            for key in ('Image Make', 'Image Model', 'Image DateTime', 'Image Orientation',
                        'Image Copyright', 'Image Artist',
                        'EXIF DateTimeOriginal', 'EXIF LensModel', 'EXIF Flash', 'EXIF ColorSpace',
                        'EXIF ExposureProgram', 'EXIF ExposureTime', 'EXIF ShutterSpeedValue',
                        'EXIF ApertureValue', 'EXIF FNumber', 'EXIF ISOSpeedRatings',
                        'EXIF FocalLength', 'EXIF WhiteBalance', 'EXIF SceneCaptureType', 
                        'MakerNote AFAreaMode', 'MakerNote LongExposureNoiseReduction2', 'MakerNote SlowShutter',
                        'MakerNote AFPointUsed', 'MakerNote Contrast', 'MakerNote RawJpgSize'):
                if key in exif:
                    print key, ':', exif[key]
                    #exif_json[key] = str(exif[key])
                    if key.startswith(prefix):
                        exif_json[prefix][key] = str(exif[key])

    return exif_json


if __name__ == '__main__':
    SWAGGER_URL='/api/docs'
    swaggerui_blueprint = get_swaggerui_blueprint('/api/docs', '/api/spec', config={'app_name': "Flask Author DB"})
    app.register_blueprint(swaggerui_blueprint, url_prefix=SWAGGER_URL) 
    #app.run(host='0.0.0.0', threaded=True, debug=True)
    app.run(host='0.0.0.0', debug=True)
