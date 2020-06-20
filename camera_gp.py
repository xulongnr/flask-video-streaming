import time
import piggyphoto
from base_camera import BaseCamera


class Camera(BaseCamera):
    gp_cam = None

    @staticmethod
    def get_image(filename):
        with open(filename, "rb") as f:
            return f.read()


    @staticmethod
    def frames():
        pic_tmp = 'preview.jpg'
        while True:
            #time.sleep(1)
            if Camera.gp_cam == None:
                Camera.gp_cam = piggyphoto.camera()
            Camera.gp_cam.capture_preview(pic_tmp)
            yield Camera.get_image(pic_tmp)


    def __del__(self):
        del Camera.gp_cam
        Camera.gp_cam = None
