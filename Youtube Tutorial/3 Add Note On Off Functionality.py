import rtmidi

# global variables
IN_PORT_ARTURIA = "Arturia MiniLab mkII"
IN_PORT_KAWAI = "UMC404HD 192k MIDI In"
OUT_PORT_NAME = "LoopBe Internal MIDI 2"
held_notes = []  # record of note values (data_byte_1)

# functions
def arturia_callback(event, data):
  # global held_notes -- NOT NEEDED FOR MUTABLE DATA TYPES (e.g. lists) --
  midi_msg = event[0]
  status_byte = midi_msg[0]
  data_byte_1 = midi_msg[1]
  data_byte_2 = midi_msg[2]
  msg_type = status_byte//16
  print(f"ARTURIA MESSAGE: {hex(status_byte), data_byte_1, data_byte_2}")
  # handle note on/off
  if msg_type == 0x8 and data_byte_1 >= 48 and data_byte_1 <= 72:  # note off within pitch range
    return
  if msg_type == 0x9 and data_byte_1 >= 48 and data_byte_1 <= 72:  # note on within pitch range
    if data_byte_1 in held_notes:
      #turn off
      held_notes.remove(data_byte_1)
      midi_out.send_message([status_byte-16, data_byte_1, data_byte_2])
      return
    else:
      #turn on
      held_notes.append(data_byte_1)
      midi_out.send_message([status_byte, data_byte_1, data_byte_2])
      return

  # If reaches here, send message unaltered
  midi_out.send_message(midi_msg)

def kawai_callback(event, data):
  midi_msg = event[0]
  status_byte = midi_msg[0]
  data_byte_1 = midi_msg[1]
  data_byte_2 = midi_msg[2]
  print(f"KAWAI MESSAGE: {hex(status_byte), data_byte_1, data_byte_2}")
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