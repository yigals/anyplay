import cv2

def avoid_end_lag(func):
    def decor(self):
        if self._read_frames == self._num_frames:
            return False, None
        else: 
            self._read_frames += 1
            return func(self)
    
    return decor
    
class VideoCapFile(object):
    def __init__(self, video):
        self._capture = cv2.VideoCapture(video)
        self._read_frames = 0
        self._num_frames = int(self._capture.get(cv2.cv.CV_CAP_PROP_FRAME_COUNT))

    @avoid_end_lag
    def read(self):
        return self._capture.read()

    @avoid_end_lag
    def retrieve(self):
        return self._capture.retrieve()
    
    def __getattr__(self, att):
        return getattr(self._capture, att)
