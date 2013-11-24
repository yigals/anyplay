from collections import defaultdict
import cv2

from VideoFiles import VideoCapFile

class keydefaultdict(defaultdict):
    '''Like defaultdict, but the default_factory function is called with the
       requested key as an argument'''
    def __missing__(self, key):
        if self.default_factory is None:
            raise KeyError(key)
        else:
            self[key] = ret = self.default_factory(key)
            return ret


class VideoOnOffTracker(object):
    '''Processes messages of the form: (should_play, video_path) and returns a
       set of currently playing VideoCapFile objects.
       '''
    # TODO: Make a generic on_off tracker and subclass it to do cv2 video specific work
    
    def __init__(self, skip_ms=300):
        self.captures_cache = keydefaultdict(VideoCapFile)
        self.currently_playing = {}
        self.skip_ms = skip_ms
    
    def process(self, message_queue):
        '''Updates the currently_playing dict according to the messages.
           Returns the updated currently_playing dict'''
        while message_queue:
            should_play, video_name = message_queue.popleft()
            if should_play:
                cur_vid = self.captures_cache[video_name]
                # cur_vid.set(cv2.cv.CV_CAP_PROP_POS_FRAMES, 0) # rewind
                cur_vid.set(cv2.cv.CV_CAP_PROP_POS_MSEC, self.skip_ms)
                self.currently_playing[video_name] = cur_vid
            else:
                self.currently_playing.pop(video_name, None) # del if exists
        return self.currently_playing
