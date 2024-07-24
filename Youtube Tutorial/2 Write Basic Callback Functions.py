import rtmidi

# global variables
IN_PORT_ARTURIA = "Arturia MiniLab mkII"
IN_PORT_KAWAI = "UMC404HD 192k MIDI In"
OUT_PORT_NAME = "LoopBe Internal MIDI 2"

# functions
def arturia_callback(event, data):
  midi_msg = event[0]
  status_byte = midi_msg[0]
  data_byte_1 = midi_msg[1]
  data_byte_2 = midi_msg[2]
  print(f"ARTURIA MESSAGE: {hex(status_byte), data_byte_1, data_byte_2}")
  midi_out.send_message(midi_msg)

def kawai_callback(event, data):
  midi_msg = event[0]
  status_byte = midi_msg[0]
  data_byte_1 = midi_msg[1]
  data_byte_2 = midi_msg[2]
  print(f"ARTURIA MESSAGE: {hex(status_byte), data_byte_1, data_byte_2}")
  midi_out.send_message(midi_msg)


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
arturia_in.set_callback(arturia_callback)
kawai_in.set_callback(kawai_callback)

input("\nMidi router is running...\nPress ENTER to exit\n\n")