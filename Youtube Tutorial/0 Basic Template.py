import rtmidi

# global variables
IN_PORT_NAME = "XXX"
OUT_PORT_NAME = "XXX"

# functions
def my_callback(event, data):
  print(f"event: {event}")
  print(f"data: {data}\n")

# open midi-in port
midi_in = rtmidi.MidiIn()
ports = midi_in.get_ports()
for i in range(len(ports)):
  if ports[i] == IN_PORT_NAME:
    midi_in.open_port(i)
    print(f"OPENED MIDI-IN PORT: {IN_PORT_NAME}")
    break

# open midi-out port
midi_out = rtmidi.MidiOut()
ports = midi_out.get_ports()
for i in range(len(ports)):
  if ports[i] == OUT_PORT_NAME:
    midi_out.open_port(i)
    print(f"OPENED MIDI-OUT PORT: {OUT_PORT_NAME}")
    break

# set callbacks
midi_in.set_callback(my_callback)

input("\nMidi router is running...\nPress ENTER to exit\n\n")