import cv2

def avoid_end_lag(func):
    def decor(self):
        if self._read_frames == self._num_frames - 1:
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
        fps = int(self._capture.get(cv2.cv.CV_CAP_PROP_FPS))
        self._ms = self._num_frames*1000.0/fps

    @avoid_end_lag
    def read(self):
        return self._capture.read()

    @avoid_end_lag
    def retrieve(self):
        return self._capture.retrieve()
        
    def set(self, propId, value):
        if propId == cv2.cv.CV_CAP_PROP_POS_MSEC: # value is in ms
            self._read_frames = int(value * 1.0 / self._ms * self._num_frames)
        return self._capture.set(propId, value)
            
    def __getattr__(self, att):
        return getattr(self._capture, att)


class VideoCapCombiner(object):
    'Combines currently_playing videos. May have state in the future.'

    def read(self, currently_playing):
        '''Returns a new frame which is a combination of the new frames of the
           given dict of cv2.VideoCapture-like files.
           Note: The function removes finished/faulty videos from the set.
           cv2.VideoCapture-style return value'''
        frames_to_combine = []
        for name, video_cap in currently_playing.items():
        # Can't iteritems since we're changing the dict while iterating.
            ret, frame = video_cap.read()
            if ret: frames_to_combine.append(frame)
            else: currently_playing.pop(name, None) # del if exists

        if frames_to_combine:
            num_frames = len(frames_to_combine)
            # divide before sum to avoid overflow. can also use cv2.addWeighted().
            return True, sum([x/num_frames for x in frames_to_combine])
        return False, None
