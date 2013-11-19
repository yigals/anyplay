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
    '''Turns NoteOn and NoteOff midi events to (on_or_off, corresponding_note_video_path)
       messages on the message_queue.'''
    
    def __init__(self, channels=None, do_prints=False):
        self.do_prints = do_prints
        self.channels = channels
        self.message_queue = Queue.deque()
        
        self.video_paths = {}
        for f in os.listdir(videos_dir):
            note = int(os.path.splitext(f)[0])
            # Videos are named with the note number only. Description can be put
            # in the folder name.
            vid_path = os.path.join(videos_dir, f)
            self.video_paths[note] = vid_path
    
    def __call__(self, message_and_delta, data):
        message, time_delta = message_and_delta
        
        channel = message[0] & 0x0F
        opcode = message[0] & 0xF0
        
        if self.do_prints:
            sys.stdout.write("%s, 0x%X, %d, %s\n" % (time_delta, opcode, channel, message[1:]))
        
        if opcode not in [144, 128]:
            return
        if self.channels is not None and channel not in self.channels:
            return

        note, velocity = message[1:]
        
        video_path = self.video_paths.get(message[1], black_mov_path)
        if opcode == 144 and velocity > 0:
            self.message_queue.append((True, video_path))
        elif opcode == 128 or opcode == 144 and velocity == 0:
            self.message_queue.append((False, video_path))
        
        
captures = {}
def set_next_action(vid_msgs):
    if vid_msgs:
        should_play, video_name = vid_msgs.pop()
        if should_play:
            if video_name not in captures.keys():
                captures[video_name] = VideoCapFile(video_name)
            cur_vid = captures[video_name]
            # cur_vid.set(cv2.cv.CV_CAP_PROP_POS_FRAMES, 0) # rewind
            cur_vid.set(cv2.cv.CV_CAP_PROP_POS_MSEC, 300)
            currently_playing[video_name] = cur_vid
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
    parser.add_argument('--midi_channels', type=int, nargs='*', metavar='CHANf')
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
    MidiInCb = MidiInputCallback(channels=args.midi_channels,
                                 do_prints=args.verbose_midi_input)
    if args.midi_channels is not None:
        print "Playing channels %s" % (args.midi_channels, )
    else:
        print "Playing all channels"
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
    
    
    