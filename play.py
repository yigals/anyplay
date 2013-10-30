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
    
    def __init__(self, midiout, do_prints=False):
        self.midiout = midiout
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
        #play sound
        self.midiout.send_message(message)
            
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
    
       
if __name__ == "__main__":
    midiout = rtmidi.MidiOut()
    midiin = rtmidi.MidiIn()
    out_ports = midiout.get_ports()
    out_port = out_ports.index('LoopBe Internal MIDI')
    midiout.open_port(out_port)
    print "MIDI sent to %s" % ('LoopBe Internal MIDI', )

    # if not args.no_midi_in:
    if not 0:
        in_ports = midiin.get_ports()
        # if args.midi_in is not None:
        if 0:
            in_port = in_ports.index(args.midi_in)
        else:
            for in_port, in_port_name in enumerate(in_ports):
                if "Yoke" not in in_port_name and "Creative" not in in_port_name and "Loop" not in in_port_name:
                    break
            else:
                raise ValueError("No suitable MIDI input port found")
        midiin.open_port(in_port)
        print "MIDI received from %s" % (in_port_name, )
        MidiInCb = MidiInputCallback(midiout, do_prints=True)
        midiin.set_callback(MidiInCb)
    
    
    currently_playing = {}
    while True:
        if MidiInCb.video_messages:
            should_play, video_name = MidiInCb.video_messages.pop()
            if should_play:
                currently_playing[video_name] = VideoCapFile(video_name)
                skip_video_percentage(currently_playing[video_name])
            else:
                try:
                    currently_playing.pop(video_name)
                except:
                    pass


        frames_to_combine = []
        for name in currently_playing.keys():
            vc = currently_playing[name]
            ret, frame = vc.read()
            if ret: frames_to_combine.append(frame)
            else: currently_playing.pop(name)
        
        if frames_to_combine:
            num_frames = len(frames_to_combine)
            # divide before sum to avoid overflow. can also use cv2.addWeighted().
            frame = sum([x/num_frames for x in frames_to_combine])
            cv2.imshow(winName, frame)
   
        key = cv2.waitKey(38)
        if key == ord('q'):
            cv2.destroyAllWindows()
            break
    
    
    