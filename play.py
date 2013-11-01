import rtmidi
import sys
import os
import Queue
import cv2

from VideoCapFile import VideoCapFile

VERSION_FORMAT = '%(prog)s 1.0'

black_mov_path = 'videos/black.wmv'
videos_root_db = 'videos'
videos_dir = os.path.join(videos_root_db, 'eli_plays')

winName = 'Display'
cv2.namedWindow(winName)

class MidiInputCallback(object):
    
    # elements are (should_play, video_name)
    video_messages = Queue.deque()
    
    def __init__(self, do_prints=False):
        self.do_prints = do_prints
        
        self.videos = {}
        for f in os.listdir(videos_dir):
            note = int(os.path.splitext(f)[0])
            vid_path = os.path.join(videos_dir, f)
            self.videos[note] = vid_path
    
    def __call__(self, message_and_delta, data):
        message, time_delta = message_and_delta
        if self.do_prints:
            sys.stdout.write("%s, %s\n" % (time_delta, message))
            
        opcode, note, velocity = message
        
        video_path = self.videos.get(message[1], black_mov_path)
        if opcode == 144 and velocity > 0:
            self.video_messages.append((True, video_path))
        elif opcode == 128 or opcode == 144 and velocity == 0:
            self.video_messages.append((False, video_path))
        
        
def skip_video_percentage(v, skip_seconds=0.3):
    "skip skip_seconds of video v"
    fps = v.get(cv2.cv.CV_CAP_PROP_FPS)
    for i in xrange(int(fps * skip_seconds)):
        v.read()
        
def set_next_action(vid_msgs):
    if vid_msgs:
        should_play, video_name = vid_msgs.pop()
        if should_play:
            currently_playing[video_name] = VideoCapFile(video_name)
            skip_video_percentage(currently_playing[video_name])
        else:
            try:
                currently_playing.pop(video_name)
            except:
                pass


def next_frame_weighted(cur_vids):
    frames_to_combine = []
    for name in cur_vids.keys():
        vc = cur_vids[name]
        ret, frame = vc.read()
        if ret: frames_to_combine.append(frame)
        else: cur_vids.pop(name)
    
    if frames_to_combine:
        num_frames = len(frames_to_combine)
        # divide before sum to avoid overflow. can also use cv2.addWeighted().
        return True, sum([x/num_frames for x in frames_to_combine])
    
    return False, None
    
       
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Receives MIDI messages from a'
        'midi interface and displays videos of people playing the corresponding'
        'notes.')
    parser.add_argument('--midi_in', help="If not specified, the first port that looks like a loopback port is chosen")
    parser.add_argument('--verbose_midi_input', action='store_true')
    parser.add_argument('--version', action='version', version=VERSION_FORMAT)
    args = parser.parse_args()
    
    midiin = rtmidi.MidiIn()
    in_ports = midiin.get_ports()
    if args.midi_in is not None:
        in_port = in_ports.index(args.midi_in)
        in_port_name = args.midi_in
    else:
        for in_port, in_port_name in enumerate(in_ports):
            if "Yoke" in in_port_name or "Creative" in in_port_name or "Loop" in in_port_name:
                break
        else:
            raise ValueError("No MIDI loopback port found.\n"
                "To receive input from a keyboard, specify its name with --midi_in")
    midiin.open_port(in_port)
    print "MIDI received from %s" % (in_port_name, )
    MidiInCb = MidiInputCallback(do_prints=args.verbose_midi_input)
    midiin.set_callback(MidiInCb)
    
    
    currently_playing = {}
    while True:
        set_next_action(MidiInCb.video_messages)

        ret, frame = next_frame_weighted(currently_playing)
        if ret:
            cv2.imshow(winName, frame)
   
        key = cv2.waitKey(38)
        if key == ord('q'):
            cv2.destroyAllWindows()
            break
    
    
    