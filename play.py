import rtmidi
import time
import sys
import os
import Queue
import cv2

from VideoOnOffTracker import VideoOnOffTracker
from VideoFiles import VideoCapCombiner, VideoCombinedWriter, get_avg_fps

VERSION_FORMAT = '%(prog)s 1.0'

winName = 'Display'

class MidiInputCallback(object):
    '''Turns NoteOn and NoteOff midi events to (on_or_off, corresponding_note_video_path)
       messages on the message_queue.'''
    
    def __init__(self, video_paths, channels=None, do_prints=False):
        self.do_prints = do_prints
        self.channels = channels
        self.message_queue = Queue.deque()
        self.video_paths = video_paths
    
    def __call__(self, message_and_delta, data):
        message, time_delta = message_and_delta
        
        channel = message[0] & 0x0F
        opcode = message[0] & 0xF0
        
        if self.do_prints and opcode in [144, 128]:
            sys.stdout.write("%s, 0x%X, %d, %s\n" % (time_delta, opcode, channel, message[1:]))
        
        if opcode not in [144, 128]:
            return
        if self.channels is not None and channel not in self.channels:
            return

        note, velocity = message[1:]
        
        try:
            video_path = self.video_paths[note]
        except KeyError:
            sys.stdout.write("Key %d is missing from video_paths\n" % (note, ))
            return
        if opcode == 144 and velocity > 0:
            self.message_queue.append((True, video_path))
        elif opcode == 128 or velocity == 0:
            self.message_queue.append((False, video_path))
        
        
def run(args, message_queue, video_paths):
    'Finishes when exit_key is entered'
    exit_key = ord('q')
    on_off_tracker = VideoOnOffTracker()
    combiner = VideoCapCombiner()
    fps = get_avg_fps(video_paths.values())
    
    if args.out_vid:
        writer = VideoCombinedWriter(video_paths)
    
    while True:
        iteration_start = time.time()
        currently_playing = on_off_tracker.process(message_queue)

        ret, frame = combiner.read(currently_playing)
        if ret:
            cv2.imshow(winName, frame)
            if args.out_vid: writer.write(frame)
   
        processing_time = time.time() - iteration_start
        key = cv2.waitKey(int(1000./fps - processing_time))
        if key == exit_key:
            cv2.destroyAllWindows()
            break

    if args.out_vid: 
        writer.release()
        results_path = os.path.join(os.path.dirname(__file__), 'results')
        if not os.path.exists(results_path):
            os.mkdir(results_path)
        os.rename(writer._vidname, os.path.join('results', writer._vidname)) # VideoWriter can't get results/asd.avi
        

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Receives MIDI messages from a'
        'midi interface and displays videos of people playing the corresponding'
        'notes.')
    parser.add_argument('-i', '--midi_in', help="If not specified, the first port that looks like a loopback port is chosen. Can also specify keyboard as midi input")
    parser.add_argument('-l', '--list_midi_inputs', action="store_true", help="Prints midi input port names and exit.")
    parser.add_argument('-v', '--verbose_midi_input', action='store_true')
    parser.add_argument('-o', '--out_vid', action='store_true', help="If specified, video is being saved to results dir")
    parser.add_argument('-d', '--videos_dir', default='shenk_plays', help="Dir from which to take videos. Should be absolute or placed under videos dir")
    parser.add_argument('-m', '--midi_channels', type=int, nargs='*', metavar='CHAN')
    parser.add_argument('--version', action='version', version=VERSION_FORMAT)
    args = parser.parse_args()
    
    midiin = rtmidi.MidiIn()
    in_ports = midiin.get_ports()
    if args.list_midi_inputs:
        print "Available midi input ports: %s" % (in_ports, )
        sys.exit()
    if args.midi_in is not None:
        try:
            in_port = in_ports.index(args.midi_in)
        except ValueError:
            raise ValueError("%s is not a valid input midi port. Available ports are %s\n" % (args.midi_in, in_ports))
        in_port_name = args.midi_in
    else:
        for in_port, in_port_name in enumerate(in_ports):
            if "loop" in in_port_name.lower():
                break
        else:
            raise ValueError("No MIDI loopback port found. Available ports for use with --midi_in are %s\n" % (in_ports, ))
    midiin.open_port(in_port)
    print "MIDI received from %s" % (in_port_name, )
    
    videos_dir = args.videos_dir if os.path.isabs(args.videos_dir) else os.path.join('videos', args.videos_dir)
    video_paths = {}
    for f in os.listdir(videos_dir):
        try:
            note = int(os.path.splitext(f)[0])
        except ValueError:
            # Videos are named with the note number only. Description can be put
            # in the folder name. Other videos are skipped.
            continue
        vid_path = os.path.join(videos_dir, f)
        video_paths[note] = vid_path

    MidiInCb = MidiInputCallback(video_paths, channels=args.midi_channels,
                                 do_prints=args.verbose_midi_input)
    if args.midi_channels is not None:
        print "Playing channels %s" % (args.midi_channels, )
    else:
        print "Playing all channels"
    midiin.set_callback(MidiInCb)
    
    cv2.namedWindow(winName, cv2.WINDOW_NORMAL)    
    run(args, MidiInCb.message_queue, video_paths)

