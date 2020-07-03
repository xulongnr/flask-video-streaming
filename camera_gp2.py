import io
# import time
import gphoto2 as gp
from base_camera import BaseCamera


class Camera(BaseCamera):
    gp_cam = None

    @staticmethod
    def frames():
        while True:
            #time.sleep(1)
            if Camera.gp_cam == None:
                Camera.gp_cam = gp.Camera()
                Camera.gp_cam.init()

            camera_file = gp.check_result(gp.gp_camera_capture_preview(Camera.gp_cam))
            file_data = gp.check_result(gp.gp_file_get_data_and_size(camera_file))
            yield ''.join(io.BytesIO(file_data))

    def __del__(self):
        if Camera.gp_cam != None:
            Camera.gp_cam.exit()
            del Camera.gp_cam
        Camera.gp_cam = None
