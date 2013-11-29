import os
import time
import subprocess
import re
import cv2


def get_fps(vid):
    "cv2 lies about certain props... so preferably use ffprobe"
    try:
        result = subprocess.Popen(["ffprobe", vid], stdout = subprocess.PIPE, stderr = subprocess.STDOUT)
        out = result.stdout.read()
        fps = float(re.findall('(\d\d\.\d\d) fps', out)[0])
    except: # no ffprobe or ffprobe failed to get fps
        v = cv2.VideoCapture(vid)
        fps = v.get(cv2.cv.CV_CAP_PROP_FPS)
        v.release()
    return fps
    

def avoid_end_lag(func):
    def decor(self):
        if self._read_frames == self._num_frames - 1:
            return False, self._last_frame
        else: 
            self._read_frames += 1
            res, self._last_frame = func(self)
            return res, self._last_frame
    
    return decor
    
class VideoCapFile(object):
    def __init__(self, video):
        self._capture = cv2.VideoCapture(video)
        self._read_frames = 0
        self._num_frames = int(self._capture.get(cv2.cv.CV_CAP_PROP_FRAME_COUNT))
        fps = get_fps(video)
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
        elif propId == cv2.cv.CV_CAP_PROP_POS_FRAMES: # value is in frames
            self._read_frames = value
        return self._capture.set(propId, value)
            
    def __getattr__(self, att):
        return getattr(self._capture, att)


class VideoCapCombiner(object):
    'Combines currently_playing videos. May have state in the future.'

    def read(self, currently_playing):
        '''Returns a new frame which is a combination of the new frames of the
           given dict of cv2.VideoCapture-like files.
           cv2.VideoCapture-style return value'''
        frames_to_combine = []
        for name, video_cap in currently_playing.items():
        # Can't iteritems since we're changing the dict while iterating.
            ret, frame = video_cap.read() 
            # VideoCapFile returns False, last_frame at end of file instead False, None
            if frame is not None: frames_to_combine.append(frame)

        if frames_to_combine:
            num_frames = len(frames_to_combine)
            # divide before sum to avoid overflow. can also use cv2.addWeighted().
            return True, sum([x/num_frames for x in frames_to_combine])
        return False, None


class BadVideosError(Exception):
    pass

    
def get_avg_fps(vid_arr):
    "Taking at most 10 first videos since ffprobe takes a lot of time"
    num = min(10, len(vid_arr))
    fpss = [get_fps(vid) for vid in vid_arr[:num]]
    return sum(fpss) / num


class VideoCombinedWriter(object):
    'Writes results to a file. Also, performs a sanity check of the given videos.'

    def __init__(self, video_paths):
        videos = [(os.path.basename(vid_path), cv2.VideoCapture(vid_path)) for vid_path in video_paths.values()]
        vid_props = [(name, (int(v.get(cv2.cv.CV_CAP_PROP_FRAME_WIDTH)),
                              int(v.get(cv2.cv.CV_CAP_PROP_FRAME_HEIGHT))))
                              for name, v in videos]
        fourcc = int(videos[0][1].get(cv2.cv.CV_CAP_PROP_FOURCC))
        for _, v in videos:
            v.release()
        # Find videos that don't conform to the arbitrarily chosen first video:
        bad_vids = [x[0] for x in vid_props if x[1] != vid_props[0][1]]
        if bad_vids:
            raise BadVideosError("Videos with properties different than those of %s: %s" % (vid_props[0][0], bad_vids, ))
        
        w, h = vid_props[0][1]
        fps = int(round(get_avg_fps(video_paths.values())))
        
        self._vidname = time.strftime("%y_%m_%d__%H_%M_%S") + '.avi'
        try: 
            self._video = cv2.VideoWriter(self._vidname, fourcc, fps, (w, h))
            assert self._video.isOpened() # If the above line fails, it's silently...
        except Exception:
            self._video = cv2.VideoWriter(self._vidname, cv2.cv.CV_FOURCC('X','V','I','D'), fps, (w, h))
            # Not asserting here... no vid will be written but output will be displayed.
            
    def write(self, frame):
        self._video.write(frame)
        
    def release(self):
        self._video.release()
