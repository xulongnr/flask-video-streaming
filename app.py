#!/usr/bin/env python
from importlib import import_module
import os
import json
from flask import Flask, render_template, Response, jsonify


app = Flask(__name__)
_camera = None

@app.route('/home')
def index():
    """Video streaming home page."""
    return render_template('index.html')


def gen(camera):
    """Video streaming generator function."""
    while True:
        frame = camera.get_frame()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')


@app.route('/live_view', methods=['DELETE'])
def live_view_del():
    global _camera
    if _camera != None:
        del _camera
        _camera = None
        return '', 204

    return '', 400


@app.route('/live_view')
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


import piggyphoto

@app.route('/config')
def list_config():
    cam = piggyphoto.camera()
    config = cam.list_config()
    return Response(json.dumps({'config': config}))
    

@app.route('/capture_preview')
def capture_preview(filename='capture_preview.jpg'):
    cam = piggyphoto.camera()
    cam.capture_preview(filename)
    with open(filename, "rb") as f:
        image = f.read()
    return Response(image, mimetype='image/jpeg')


@app.route('/capture_image')
def capture_image(filename='capture_image.jpg'):
    cam = piggyphoto.camera()
    cam.capture_image(filename)
    with open(filename, "rb") as f:
        image = f.read()
    return Response(image, mimetype='image/jpeg')


if __name__ == '__main__':
    app.run(host='0.0.0.0', threaded=True, debug=True)
