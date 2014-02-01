import midi
import time
import sys
import os
import Queue
import cv2

from VideoOnOffTracker import VideoOnOffTracker
from VideoFiles import VideoCapCombiner, VideoCombinedWriter, get_avg_fps

VERSION_FORMAT = '%(prog)s 1.0'

winName = 'Display'

class MidiEventHandler(object):
    '''Turns NoteOn and NoteOff midi events to (on_or_off, corresponding_note_video_path)
       messages on the message_queue.'''
    
    def __init__(self, video_paths, channels=None, do_prints=False):
        self.do_prints = do_prints
        self.channels = channels
        self.message_queue = Queue.deque()
        self.video_paths = video_paths
        self.last_bpm = 1 # First SetTempoEvent is expected to arrive at tick 0
    
    def __call__(self, midi_event):
        if isinstance(midi_event, midi.SetTempoEvent):
            self.last_bpm = midi_event.bpm
            return
        
        if self.do_prints and isinstance(midi_event, (midi.NoteOnEvent, midi.NoteOffEvent)):
            sys.stdout.write("%s\n" % (midi_event, ))
            
        if isinstance(midi_event, (midi.NoteOnEvent, midi.NoteOffEvent)) == False:
            return
        
        channel = midi_event.channel
        
        if self.channels is not None and channel not in self.channels:
            return

        note, velocity = midi_event.pitch, midi_event.velocity
        
        try:
            video_path = self.video_paths[note]
        except KeyError:
            sys.stdout.write("Key %d is missing from video_paths\n" % (note, ))
            return
        if isinstance(midi_event, midi.NoteOnEvent) and velocity > 0:
            self.message_queue.append((True, video_path))
        elif isinstance(midi_event, midi.NoteOffEvent) or velocity == 0:
            self.message_queue.append((False, video_path))
        
        
def run(out_file, pattern, msg_handler, video_paths):
    'Finishes when exit_key is entered'
    exit_key = ord('q')
    on_off_tracker = VideoOnOffTracker()
    combiner = VideoCapCombiner()
    fps = get_avg_fps(video_paths.values())
    writer = VideoCombinedWriter(video_paths, out_file)

    
    pattern.make_ticks_abs()
    messages = sorted(sum(pattern, []), key=lambda x:x.tick) # Use heapq.merge later
    
    frame_interval = 1000./fps # The output vid will have the same fps as the input vids, to avoid resampling issues
    current_ms = 0
    
    for msg in messages:
        iteration_start = time.time()
        
        # Handle delta
        delta_ms = msg.tick * 60000. / (msg_handler.last_bpm * pattern.resolution) # 60,000 / (BPM * PPQ)
        num_frames_passed = (current_ms + delta_ms) / frame_interval - current_ms / frame_interval
        for i in xrange(int(num_frames_passed)):
            ret, frame = combiner.read(currently_playing)
            if ret:
                writer.write(frame)
        current_ms += delta_ms

        # Handle data
        msg_handler(msg)
        currently_playing = on_off_tracker.process(msg_handler.message_queue)
   
        processing_time = time.time() - iteration_start

    writer.release()
    results_path = os.path.join(os.path.dirname(__file__), 'results')
    if not os.path.exists(results_path):
        os.mkdir(results_path)
    os.rename(writer._vidname, os.path.join('results', writer._vidname)) # VideoWriter can't get results/asd.avi
        

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Receives a MIDI file and '
        'displays videos of people playing the corresponding notes.')
    parser.add_argument('in_file', metavar="MIDI_FILE", help="The MIDI file to simulate playing of")
    parser.add_argument('-v', '--verbose_midi_input', action='store_true')
    parser.add_argument('-o', '--out_file', help="If not given, a suitable file name is chosen")
    parser.add_argument('-d', '--videos_dir', default='shenk_plays', help="Dir from which to take videos. Should be absolute or placed under videos dir")
    parser.add_argument('-m', '--midi_channels', type=int, nargs='*', metavar='CHAN')
    parser.add_argument('--version', action='version', version=VERSION_FORMAT)
    args = parser.parse_args()
    
    pattern = midi.read_midifile(args.in_file)
    
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
        
    if args.out_file is None:
        args.out_file = "%s_%s.avi" % (args.videos_dir, os.path.splitext(args.in_file)[0])

    msg_handler = MidiEventHandler(video_paths, channels=args.midi_channels,
                                 do_prints=args.verbose_midi_input)
    if args.midi_channels is not None:
        print "Playing channels %s" % (args.midi_channels, )
    else:
        print "Playing all channels"
    
    run(args.out_file, pattern, msg_handler, video_paths)
