import rtmidi

# global variables
IN_PORT_ARTURIA = "Arturia MiniLab mkII"
IN_PORT_KAWAI = "UMC404HD 192k MIDI In"
OUT_PORT_NAME = "LoopBe Internal MIDI 2"

# functions
def my_callback(event, data):
  print(f"event: {event}")
  print(f"data: {data}\n")

# open midi-in port
arturia_in = rtmidi.MidiIn()
ports = arturia_in.get_ports()
for i in range(len(ports)):
  if IN_PORT_ARTURIA in ports[i]:
    arturia_in.open_port(i)
    print(f"OPENED MIDI-IN PORT: {ports[i]}")
    break

# open midi-in port
kawai_in = rtmidi.MidiIn()
ports = kawai_in.get_ports()
for i in range(len(ports)):
  if IN_PORT_KAWAI in ports[i]:
    kawai_in.open_port(i)
    print(f"OPENED MIDI-IN PORT: {ports[i]}")
    break

# open midi-out port
midi_out = rtmidi.MidiOut()
ports = midi_out.get_ports()
for i in range(len(ports)):
  if ports[i] == OUT_PORT_NAME:
    midi_out.open_port(i)
    print(f"OPENED MIDI-OUT PORT: {ports[i]}")
    break

# set callbacks
arturia_in.set_callback(my_callback)

input("\nMidi router is running...\nPress ENTER to exit\n\n")