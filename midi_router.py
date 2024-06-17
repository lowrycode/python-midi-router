import rtmidi, time, threading

# Classes
class MidiPorts:
    def __init__(self):
        self.midiin_arturia = rtmidi.MidiIn()
        self.midiin_roland = rtmidi.MidiIn()
        self.midiin_loopbe = rtmidi.MidiIn()
        self.midiout_arturia = rtmidi.MidiOut()
        self.midiout_roland = rtmidi.MidiOut()
        self.midiout_loopbe = rtmidi.MidiOut()

    def close_all_ports(self):
        del self.midiin_arturia
        del self.midiin_roland
        del self.midiin_loopbe
        del self.midiout_arturia
        del self.midiout_roland
        del self.midiout_loopbe

    def open_all_ports(self):
        # in ports
        if not self._open_midi_in_port(self.midiin_arturia, "arturia"): print("MIDI PORT ERROR: unable to open Arturia In Port")
        if not self._open_midi_in_port(self.midiin_roland, "umc"): print("MIDI PORT ERROR: unable to open Roland In Port")
        if not self._open_midi_in_port(self.midiin_loopbe, "loopbe internal midi 1"): print("MIDI PORT ERROR: unable to open LoopBe In Port")
        # out ports
        if not self._open_midi_out_port(self.midiout_arturia, "arturia"): print("MIDI PORT ERROR: unable to open Arturia Out Port")
        if not self._open_midi_out_port(self.midiout_roland, "umc"): print("MIDI PORT ERROR: unable to open Roland Out Port")
        if not self._open_midi_out_port(self.midiout_loopbe, "loopbe internal midi 1"): print("MIDI PORT ERROR: unable to open LoopBe Out Port")

    def _open_midi_in_port(self, midiin, name):
        ports = midiin.get_ports()
        for i in range(len(ports)):
            if name.lower() in ports[i].lower():
                midiin.open_port(i)
                return True
        return False

    def _open_midi_out_port(self, midiout, name):
        ports = midiout.get_ports()
        for i in range(len(ports)):
            if name.lower() in ports[i].lower():
                midiout.open_port(i)
                return True
        return False
    
class Roland:
    def __init__(self, midiports):
        self.midiports = midiports
        # Define constants
        self.NAME = "Roland"
        self.MIDI_CHANNEL = 1
        self.BASS_UPPER_KEY = MIDI_NOTE_VALUES["F3"]   # F below middle C
        # Define variables
        self.exp_pedal_value = 0
        self.bass_mode = False

    def initialise_bassmode(self):
        prompt = "\nWould you like to turn bass mode on? (Please enter 'y' for yes or 'n' for no)\n"
        user_input = input(prompt).strip().lower()
        if user_input == "y": self.bass_mode = True

    def initialise_callback(self):
        self.midiports.midiin_roland.set_callback(self._callback)

    def _callback(self, msg, data):
        status_byte, data_byte_1, data_byte_2 = msg[0]
        msg_type = MIDI_MESSAGE_TYPES[status_byte//16]  # alternatively use bitwise operation to extract first 4 bits: msg_type = (status_byte & 0xF0) >> 4
        msg_channel = (status_byte%16) + 1   # alternatively use bitwise operation to extract last 4 bits: msg_channel = status_byte & 0x0F
        # Catch messages to ignore
        if msg_type == "System Message":
            print(f"Unexpected system message received from {self.NAME}")
            return
        if msg_channel != self.MIDI_CHANNEL: 
            print(f"Unexpected message received from {self.NAME} on channel {msg_channel}")
            return
        # Update exp_pedal_value
        if msg_type == "Control Change" and data_byte_1 == 7:      # control change from expression pedal
            self.exp_pedal_value = data_byte_2
        # Tweak velocities if bass mode on
        if self.bass_mode and msg_type == "Note On" and data_byte_1 <= self.BASS_UPPER_KEY:
            data_byte_2 = int(data_byte_2 * (127 - self.exp_pedal_value) / 127)
            print(f"Edit Value: {str(data_byte_2)}")
        # Forward midi message
        msg = [status_byte, data_byte_1, data_byte_2]
        self.midiports.midiout_loopbe.send_message(msg)

class Arturia:
    def __init__(self, midiports):
        self.midiports = midiports
        # Define constants
        self.NAME = "Arturia"
        self.MIDI_CHANNEL = 3
        self.KNOB_CC = (102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114, 115, 116, 117)  # Must match values set in Arturia's Midi Control Center
        self.KNOB_SYSEX_ID = (48, 1, 2, 9, 11, 12, 13, 14, 51, 3, 4, 10, 5, 6, 7, 8)    # Knob ID values used in sysex (converted from hexadecimal to decimal)
        self.PAD_NOTE_VALUES = (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15)   # Must match values set in Arturia's Midi Control Center - they correspond to C-1 C#-1 etc.
        self.PAD_ROTARY_SWITCH = (5, 13)  # Pads used to turn rotary on and off
        self.PAD_LINKED_TO_KNOB = (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 8)  # From 1 to 16 - CHANGE THIS if you wish to link a pad to a different knob
        self.PAD_COLOURS = (20, 20, 127, 5, 1, 0, 17, 20, 20, 20, 127, 5, 1, 0, 17, 20)  # 0 black, 1 red, 4 green, 5 yellow, 16 blue, 17 magenta, 20 cyan, 127 white
        self.TRANSITION_STEPS = 60  # Must be multiple of 2
        # Define variables
        self.rotary_on = False
        self.knob_values = [127, 127, 127, 90, 100, 127, 127, 127, 0, 0, 0, 0, 0, 0, 60, 0]   # These default values are edited by this application
        self.target_knob = 16  # Between 1 and 16 - changed when pressure pads are used to trigger a transition
        self.base_pitch = MIDI_NOTE_VALUES["C1"]   # Default pitch for pad sound is C
        self.octave_transpose = 0
        self.notes_on = []

    def initialise_callback(self):
        self.midiports.midiin_arturia.set_callback(self._callback)

    def initialise_knobs_and_pads(self):
        status_byte = 0xB0 + self.MIDI_CHANNEL - 1  # control change on related midi channel
        for i in range(16):
            data_byte_1 = self.KNOB_CC[i]
            data_byte_2 = self.knob_values[i]
            msg = [status_byte, data_byte_1, data_byte_2]
            self.midiports.midiout_arturia.send_message(msg)
            self._updatePadColour(i, 2)
            knobID = int(self.KNOB_SYSEX_ID[i])
            self._updateKnobPosition(knobID, data_byte_2)
            #msg = [240, 0, 32, 107, 127, 66, 2, 0, 16, 112, 4, 247]  #makes first pad green as a test
            #self.midiports.midiout_arturia.send_message(msg)

    def _callback(self, msg, data):
        status_byte, data_byte_1, data_byte_2 = msg[0]
        msg_type = MIDI_MESSAGE_TYPES[status_byte//16]
        msg_channel = (status_byte%16) + 1
        # Catch messages to ignore
        if msg_type == "System Message":
            print(f"Unexpected system message received from {self.NAME}")
            return
        if msg_channel != self.MIDI_CHANNEL: 
            print(f"Message received from {self.NAME} on unexpected channel ({msg_channel})")
            return
        if msg_type == "Note Off":
            return
        if msg_type == "Channel Pressure (Aftertouch)":
            return  #Ignore all aftertouch messages from pads
        if msg_type == "Polyphonic Key Pressure (Aftertouch)":
            return  #Ignore all aftertouch messages from pads
        # Messages requiring action
        if msg_type == "Control Change":
            # For control changes, data_byte_1 refers to the controller number (which is set in Arturia Control Centre)
            if data_byte_1 == 1:  #Mod wheel - used as another way of setting self.target_knob value
                i = self.target_knob - 1
                data_byte_1 = self.KNOB_CC[i]
                self.knob_values[i] = data_byte_2
                knob_id = int(self.KNOB_SYSEX_ID[i])
                self._updateKnobPosition(knob_id, data_byte_2)
                return
            if data_byte_1 in self.KNOB_CC:  #knob turned
                i = self.KNOB_CC.index(data_byte_1)
                #Check knob value not undergoing transition - stop transition if so
                if i + 1 in self.PAD_LINKED_TO_KNOB:
                    iPad = self.PAD_LINKED_TO_KNOB.index(i+1)
                    if iPad in threads:
                        threads.remove(iPad)
                        self._updatePadColour(iPad, 2)
                        knob_id = int(self.KNOB_SYSEX_ID[i])
                        self._updateKnobPosition(knob_id, self.knob_values[i])
                        return 0
                #Send knob value            
                self.knob_values[i] = data_byte_2
            msg = [status_byte, data_byte_1, data_byte_2]
            self.midiports.midiout_loopbe.send_message(msg)
            return
        if msg_type == "Note On":
            print(data_byte_1)
            if data_byte_1 in self.PAD_ROTARY_SWITCH:  # Pressed pad for switching organ rotary
                status_byte = 0xB0 + self.MIDI_CHANNEL - 1  # Change status_byte to CC on specified midi channel (must be same as organ channel)
                data_byte_1 = 1  # Change to CC1 (normally mod wheel)
                if self.rotary_on == True:
                    self.rotary_on = False
                    data_byte_2 = 0
                else:
                    self.rotary_on = True
                    data_byte_2 = 127
                msg = [status_byte, data_byte_1, data_byte_2]
                self.midiports.midiout_loopbe.send_message(msg)
                return
            elif data_byte_1 in self.PAD_NOTE_VALUES:  # Pressed another pad
                iPad = self.PAD_NOTE_VALUES.index(data_byte_1)
                transitionTime = 128 - data_byte_2
                transitionTime = transitionTime*transitionTime
                t = threading.Thread(target=self._makeTransition, args=(iPad, transitionTime))
                t.start()
                return
            elif data_byte_1 >= MIDI_NOTE_VALUES["C3"] and data_byte_1 < MIDI_NOTE_VALUES["C4"]:   # Pressed key in bottom octave on Arturia Minilab
                self.base_pitch = data_byte_1 - MIDI_NOTE_VALUES["C1"]   # Value for equivalent note in octave C1-B1
                self._sendAllNotesOff()
                return
            elif data_byte_1 >= MIDI_NOTE_VALUES["C4"] and data_byte_1 < MIDI_NOTE_VALUES["C5"]:  #Pressed key in upper octave on Arturia Minilab
                self.octave_transpose = data_byte_1 - MIDI_NOTE_VALUES["C4"]
                data_byte_1 = self.base_pitch + (12*self.octave_transpose)
                if data_byte_1 in self.notes_on:   #Turn off note
                    self.notes_on.remove(data_byte_1)
                    status_byte = 0x80 + self.MIDI_CHANNEL - 1    #Note Off on specified midi channel
                    data_byte_2 = 0
                    msg = [status_byte, data_byte_1, data_byte_2]
                    self.midiports.midiout_loopbe.send_message(msg)
                    return
                else:   #Turn on note
                    self.notes_on.append(data_byte_1)
                    msg = [status_byte, data_byte_1, data_byte_2]
                    self.midiports.midiout_loopbe.send_message(msg)
                    return
            else:
                # msg = [status_byte, data_byte_1, data_byte_2]
                # self.midiports.midiout_loopbe.send_message(msg)
                print(f"Note On for {note_value_to_name(data_byte_1)} is outside of expected range (C3-B4)")
                return
        # If reaches here, log unexpected message before sending
        print("Received unexpected midi input: "+str(status_byte)+" "+str(data_byte_1)+" "+str(data_byte_2))
        msg = [status_byte, data_byte_1, data_byte_2]
        self.midiports.midiout_loopbe.send_message(msg)

    def _makeTransition(self, iPad, t):
        # Check if thread already running for this pad
        if iPad in threads:
            threads.remove(iPad)
            self._updatePadColour(iPad, 2)
            return 0
        else:
            threads.append(iPad)
        # Define value variables
        knobNumber = self.PAD_LINKED_TO_KNOB[iPad]
        i = knobNumber - 1
        initialValue = self.knob_values[i]
        targetValue = self.knob_values[self.target_knob-1]
        incrementValue = (targetValue-initialValue)/self.TRANSITION_STEPS
        status_byte = 175 + self.MIDI_CHANNEL
        data_byte_1 = self.KNOB_CC[i]
        # Send midi messages using loop
        j = 1
        while j <= self.TRANSITION_STEPS and iPad in threads:
            tempValue = initialValue + (j*incrementValue)
            data_byte_2 = int(tempValue)
            msg = [status_byte, data_byte_1, data_byte_2]
            self.midiports.midiout_loopbe.send_message(msg)
            self.knob_values[i] = data_byte_2
            self._updatePadColour(iPad, j)
            time.sleep(t*0.00003)        
            j += 1
        # Update knob position
        knobID = int(self.KNOB_SYSEX_ID[i])
        self._updateKnobPosition(knobID, self.knob_values[i])
        if iPad in threads:
            threads.remove(iPad)
    
    def _sendAllNotesOff(self):
        for n in self.notes_on:
            status_byte = 0x80 + self.MIDI_CHANNEL - 1   # Note Off on specified midi channel
            data_byte_1 = n
            data_byte_2 = 0
            msg = [status_byte, data_byte_1, data_byte_2]
            self.midiports.midiout_loopbe.send_message(msg)
        self.notes_on.clear()

    def _updateKnobPosition(self, knobID, knobValue):
        # Sends a SysEx message back to Arturia
        msg = [0xF0, 0, 32, 107, 127, 66, 2, 0, 0, knobID, knobValue, 247]
        self.midiports.midiout_arturia.send_message(msg)

    def _updatePadColour(self, iPad, j):
        # Sends a SysEx message back to Arturia
        padNo = iPad + 112
        padNo = int(padNo)
        c = self.PAD_COLOURS[iPad]
        if j % 2 > 0:
            if c == 0:
                c = 4  # green
            else:
                c = 0
        msg = [240, 0, 32, 107, 127, 66, 2, 0, 16, padNo, c, 247]
        self.midiports.midiout_arturia.send_message(msg)

# Useful Reference Dictionaries
MIDI_MESSAGE_TYPES = {
    0x8: "Note Off",
    0x9: "Note On",
    0xA: "Polyphonic Key Pressure (Aftertouch)",
    0xB: "Control Change",
    0xC: "Program Change",
    0xD: "Channel Pressure (Aftertouch)",
    0xE: "Pitch Bend Change",
    0xF: "System Message"
}

MIDI_NOTE_VALUES = {
    "C0": 12, "C#0": 13, "D0": 14, "D#0": 15, "E0": 16, "F0": 17, "F#0": 18, "G0": 19, "G#0": 20, "A0": 21, "A#0": 22, "B0": 23, 
    "C1": 24, "C#1": 25, "D1": 26, "D#1": 27, "E1": 28, "F1": 29, "F#1": 30, "G1": 31, "G#1": 32, "A1": 33, "A#1": 34, "B1": 35, 
    "C2": 36, "C#2": 37, "D2": 38, "D#2": 39, "E2": 40, "F2": 41, "F#2": 42, "G2": 43, "G#2": 44, "A2": 45, "A#2": 46, "B2": 47, 
    "C3": 48, "C#3": 49, "D3": 50, "D#3": 51, "E3": 52, "F3": 53, "F#3": 54, "G3": 55, "G#3": 56, "A3": 57, "A#3": 58, "B3": 59, 
    "C4": 60, "C#4": 61, "D4": 62, "D#4": 63, "E4": 64, "F4": 65, "F#4": 66, "G4": 67, "G#4": 68, "A4": 69, "A#4": 70, "B4": 71, 
    "C5": 72, "C#5": 73, "D5": 74, "D#5": 75, "E5": 76, "F5": 77, "F#5": 78, "G5": 79, "G#5": 80, "A5": 81, "A#5": 82, "B5": 83, 
    "C6": 84, "C#6": 85, "D6": 86, "D#6": 87, "E6": 88, "F6": 89, "F#6": 90, "G6": 91, "G#6": 92, "A6": 93, "A#6": 94, "B6": 95, 
    "C7": 96, "C#7": 97, "D7": 98, "D#7": 99, "E7": 100, "F7": 101, "F#7": 102, "G7": 103, "G#7": 104, "A7": 105, "A#7": 106, "B7": 107
}

# Useful Functions
def note_value_to_name(value):
    for key, val in MIDI_NOTE_VALUES.items():
        if val == value:
            return key
    return None

# MAIN PROCEDURE
threads = []
midiports = MidiPorts()
midiports.open_all_ports()

roland = Roland(midiports)
roland.initialise_callback()
roland.initialise_bassmode()  # This asks the user to write 'y' or 'n'

arturia = Arturia(midiports)
arturia.initialise_callback()
arturia.initialise_knobs_and_pads()

k = input("\nAbleton mapper is running (Roland and Arturia)")

midiports.close_all_ports()