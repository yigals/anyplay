import rtmidi
import sys
import cv2

VERSION_FORMAT = '%(prog)s 1.0'

sol_img = cv2.imread('sol.png')
do_img = cv2.imread('do.png')
re_img = cv2.imread('re.png')
black_img = cv2.imread('black.png')

winName = "Display"
cv2.namedWindow(winName)


class MidiInputCallback(object):
    images = { 72 : do_img,  74 : re_img, 79 : sol_img}
    def __init__(self, midiout, do_prints=False):
        self.midiout = midiout
        self.do_prints = do_prints
    
    def __call__(self, message_and_delta, data):
        message, time_delta = message_and_delta
        if self.do_prints:
            sys.stdout.write("%s, %s\n" % (time_delta, message))
            
        opcode, note, intensity = message
           
        if opcode == 144:
            cv2.imshow(winName, self.images.get(message[1], black_img))
        elif opcode == 128:
            cv2.imshow(winName, black_img)
        
       
        #play sound
        self.midiout.send_message(message)
       
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
        midiin.set_callback(MidiInputCallback(midiout, do_prints=True))
    
    while True:
            key = cv2.waitKey(10)
            if key == ord('q'):
                cv2.destroyWindow(winName)
                break
    
    
    
    
    
    