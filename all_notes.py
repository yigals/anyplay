import sys
import midi

midi_pattern = midi.read_midifile(sys.argv[1])
all_notes = {event.pitch for event in sum(midi_pattern, []) \
             if midi.NoteOnEvent.is_event(event.statusmsg) or midi.NoteOffEvent.is_event(event.statusmsg)}
print "This MIDI file has the following notes played:"
print all_notes
print

print "The following track names:"
for track_num, track in enumerate(midi_pattern):
   track_name = [event.text for event in track if isinstance(event, midi.TrackNameEvent)]
   print track_num, track_name
print
    
print "The following track channels:"
for track_num, track in enumerate(midi_pattern):
    track_channels = {event.channel for event in track if isinstance(event, midi.Event)}
    print track_num, track_channels
