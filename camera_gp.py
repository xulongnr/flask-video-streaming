import time
import piggyphoto
from base_camera import BaseCamera


class Camera(BaseCamera):
    """An emulated camera implementation that streams a repeated sequence of
    files 1.jpg, 2.jpg and 3.jpg at a rate of one frame per second."""
    imgs = [open(f + '.jpg', 'rb').read() for f in ['1', '2', '3']]
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
            #yield Camera.imgs[int(time.time()) % 3]
