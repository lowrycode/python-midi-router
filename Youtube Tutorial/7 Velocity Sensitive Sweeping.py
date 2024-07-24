import rtmidi, time, threading

# global variables
IN_PORT_ARTURIA = "Arturia MiniLab mkII"
IN_PORT_KAWAI = "UMC404HD 192k MIDI In"
OUT_PORT_NAME = "LoopBe Internal MIDI 2"
held_notes = []  # record of note values (data_byte_1)
threads = []  # record sweep_cc
MSG_TYPES = {
    0x8: "note off",
    0x9: "note on",
    0xA: "polyphonic key pressure (aftertouch)",
    0xB: "control change",
    0xC: "program change",
    0xD: "channel pressure (aftertouch)",
    0xE: "pitch bend change",
    0xF: "system message"
}
NOTE_VALUES = {
    "C-1": 0, "C#-1": 1, "D-1": 2, "D#-1": 3, "E-1": 4, "F-1": 5, "F#-1": 6, "G-1": 7, "G#-1": 8, "A-1": 9, "A#-1": 10, "B-1": 11,
    "C0": 12, "C#0": 13, "D0": 14, "D#0": 15, "E0": 16, "F0": 17, "F#0": 18, "G0": 19, "G#0": 20, "A0": 21, "A#0": 22, "B0": 23,
    "C1": 24, "C#1": 25, "D1": 26, "D#1": 27, "E1": 28, "F1": 29, "F#1": 30, "G1": 31, "G#1": 32, "A1": 33, "A#1": 34, "B1": 35,
    "C2": 36, "C#2": 37, "D2": 38, "D#2": 39, "E2": 40, "F2": 41, "F#2": 42, "G2": 43, "G#2": 44, "A2": 45, "A#2": 46, "B2": 47,
    "C3": 48, "C#3": 49, "D3": 50, "D#3": 51, "E3": 52, "F3": 53, "F#3": 54, "G3": 55, "G#3": 56, "A3": 57, "A#3": 58, "B3": 59,
    "C4": 60, "C#4": 61, "D4": 62, "D#4": 63, "E4": 64, "F4": 65, "F#4": 66, "G4": 67, "G#4": 68, "A4": 69, "A#4": 70, "B4": 71,
    "C5": 72, "C#5": 73, "D5": 74, "D#5": 75, "E5": 76, "F5": 77, "F#5": 78, "G5": 79, "G#5": 80, "A5": 81, "A#5": 82, "B5": 83,
    "C6": 84, "C#6": 85, "D6": 86, "D#6": 87, "E6": 88, "F6": 89, "F#6": 90, "G6": 91, "G#6": 92, "A6": 93, "A#6": 94, "B6": 95,
    "C7": 96, "C#7": 97, "D7": 98, "D#7": 99, "E7": 100, "F7": 101, "F#7": 102, "G7": 103, "G#7": 104, "A7": 105, "A#7": 106, "B7": 107,
    "C8": 108, "C#8": 109, "D8": 110, "D#8": 111, "E8": 112, "F8": 113, "F#8": 114, "G8": 115, "G#8": 116, "A8": 117, "A#8": 118, "B8": 119,
    "C9": 120, "C#9": 121, "D9": 122, "D#9": 123, "E9": 124, "F9": 125, "F#9": 126, "G9": 127
}
PAD_MAP = {0:102, 1:103, 2:104}  # key = note val for pad, value = cc of knob

# functions
def arturia_callback(event, data):
  # global held_notes -- NOT NEEDED FOR MUTABLE DATA TYPES (e.g. lists) --
  midi_msg = event[0]
  status_byte = midi_msg[0]
  data_byte_1 = midi_msg[1]
  data_byte_2 = midi_msg[2]
  msg_type = MSG_TYPES[status_byte//16]  # note off, note on, ...
  print(f"ARTURIA MESSAGE: {hex(status_byte), data_byte_1, data_byte_2}")
  # handle note on/off
  if ((msg_type == "note off" or msg_type == "note on") and 
      data_byte_1 >= NOTE_VALUES["C3"] and data_byte_1 <= NOTE_VALUES["C5"]):
    handle_note_off(status_byte, data_byte_1, data_byte_2, msg_type)
    return
  
  # control sweep
  if msg_type == "note on" and data_byte_1 >= NOTE_VALUES["C-1"] and data_byte_1 <= NOTE_VALUES["B-1"]:
    # control_sweep(status_byte, data_byte_1)
    t = threading.Thread(target=control_sweep, args=(status_byte, data_byte_1, data_byte_2))
    t.start()
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

def handle_note_off(status_byte, data_byte_1, data_byte_2, msg_type):
  if msg_type == "note off": return  # note off
  if msg_type == "note on":  # note on
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

def control_sweep(status_byte, data_byte_1, data_byte_2):
  print("You have called the control sweep")
  sweep_cc = PAD_MAP.get(data_byte_1)
  if sweep_cc:
    if sweep_cc in threads:
      #stop sweep
      threads.remove(sweep_cc)
      return
    else:
      #start sweep
      threads.append(sweep_cc)
      sleep_time = (128-data_byte_2) * 0.001
      for i in range(128):
        if sweep_cc not in threads: return
        # print(f"CC {sweep_cc} value {i}")
        midi_out.send_message([status_byte+32, sweep_cc, i])
        time.sleep(sleep_time)
      threads.remove(sweep_cc)
  else:
    return

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