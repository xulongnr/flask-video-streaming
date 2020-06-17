import time
import piggyphoto
from base_camera import BaseCamera


class Camera(BaseCamera):
    gp_cam = piggyphoto.camera()

    @staticmethod
    def get_image(filename):
        with open(filename, "rb") as f:
            return f.read()


    @staticmethod
    def frames():
        pic_tmp = 'preview.jpg'
        while True:
            #time.sleep(1)
            Camera.gp_cam.capture_preview(pic_tmp)
            yield Camera.get_image(pic_tmp)
