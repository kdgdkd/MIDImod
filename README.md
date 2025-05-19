# MIDImod: MIDI Transformations


`midimod.py` is a Python script to intercept, transform, and redirect MIDI messages in real-time between different devices. It allows for deep customization through JSON configuration files, offering functionalities like device connection, channel remapping, note transposition, Control Change (CC) transformation, note to CC/PC conversion, and a system of rule "versions" (presets) that can be changed dynamically during execution.

## What is it for

MIDImod can be used to manage MIDI between devices connected to a local computer. For example, you can connect a keyboard or a controller to an external synth. But you can also change the channel, the type of signal, the values, etc. You can duplicate incoming notes, and send them to two different devices, or two channels in a multi-timbral device. And you could apply transposition only to the second copy of the secuence, sending notes one octave below, like a sub-bass. You can turn a note button into a shift function button, changing the values sent by the rest of the controls. Or use note buttons to send Control Change or Program Change events (even if your controller "does not send PC"). You could use the velocity or aftertouch to control LFO speed, or cutoff in a synth, while escaling the resulting values into valid ranges. Because of the versions implementation, you could use a controller to change the behaviour of another device that is also connected to the computer (clicking on a button on a controller, I can change the octave of a separate keyboard).
There are many things that can be done, some may have a practical use and result in better music. 
Personally, I use it to turn my M-AUDIO XSessionPRO (which is very far from a PRO device), into a smart device. My XSessionPRO is expected to work with mixer software (easy to map), and can only send a predefined set of CCs and notes, all on channel 1; this can't be changed. With MIDImod, I use it to control hardware, sending CC data on different channels, with shift buttons and presets, and is very capable of managing an 8 voices set on an Access Virus TI2. 



## Main Features


- **Define Devices by Alias:** Define friendly names (aliases) for your MIDI devices in a global section, and then use these aliases in your routes for greater clarity and ease of maintenance.
- **Multiple Routing:** Define multiple processing "routes," each connecting a MIDI input device (identified by alias or substring) to an output device. A single input device can feed multiple routes, and multiple routes can send to a single output device.
- **Sequential Processing:** Within each route, transformations are applied in the order they are defined in the JSON file. The output of one transformation is the input of the next.
- **Detailed Transformations:**
  - Channel Change (`ch_in`, `ch_out`).
  - Note Transposition (`nt_st`).
  - Control Change Remapping (`cc_in`, `cc_out`).
  - CC Range Scaling (`cc_range`).
  - Note Velocity Scaling (`velocity_range`).
  - Note to CC Conversion (`note_to_cc`), including an option to use note velocity as CC value.
  - Note to Program Change Conversion (`note_to_pc`).
  - Aftertouch to CC Conversion (`aftertouch_to_cc`), with optional value scaling.
- **Rule Version System (Presets):**
  - Define different behaviors for your transformations using the `"version"` key (an integer or a list of integers).
  - Rules without the `"version"` key within a route always apply (regardless of the active version for that route).
  - Change the global `current_active_version` dynamically via:
    - **Keyboard:** Numeric keys (0-9) for direct selection, Spacebar to cycle (the console window must have focus).
    - **MIDI:** Configure `version_midi_map` (route-specific) for specific MIDI messages to select a version or perform cycle actions (e.g., `"note_on note=60 channel=0": 1`, `"note_on note=108": "cycle"`).
- **Interactive Rule File Selector:** If run without specifying rule files, `midimod` presents a console interface to select and sort the rule files to load from the `rules/` folder.
- **Real-time Logging:** Displays input MIDI messages and their corresponding outputs (if a route and its rules acted on the message) in the console, indicating the active version and route identifier.
- **Centralized JSON Configuration:** All logic for device definition, routing, and transformation is defined in external JSON files.


## Prerequisites


- Python 3.7 or higher.
- Python libraries: `mido`, `python-rtmidi`, `prompt_toolkit`.



### Installing Dependencies


You can install all necessary libraries using `pip`, the Python package manager. Open your terminal or command line and run:


**pip install mido python-rtmidi prompt-toolkit**

**Note for Linux users:** Sometimes, for python-rtmidi, you might need to install some ALSA development dependencies (e.g., libasound2-dev on Debian/Ubuntu systems).

## Usage

midimod.py is run from the command line.

**Syntax:**

```
python midimod.py [rule_file_name_1] [rule_file_name_2] [...] [options]
```

- **[rule_file_name_...]**: (Optional) Names of the rule files (without the .json extension) to load from the rules/ subfolder. If omitted, an interactive selector will open. Routes defined in multiple files are combined.

- **Options:**
  
  - --list-ports: Lists detected MIDI input and output devices and exits.
  
  - --help: Displays detailed help information on usage and the structure of rule files.

**Execution Examples:**

- **Use the interactive selector:**
  
  ```
  python midimod.py
  ```
  
  (Navigate with arrow keys, mark/unmark with Space, confirm with Enter).

- **Load a specific rule file:**
  
  ```
  python midimod.py virus play
  ```
  
  (Will load rules/virus.json and rules/play.json).

- **List MIDI ports:**
  
  ```
  python midimod.py --list-ports
  ```
  
  

## Structure of Rule Files (.json)

Rule files must be in JSON format and located in a folder named rules/ in the same directory as midimod.py. A file can contain a single "route" object or a list of "route" objects.

**Main Components of a Route:**

- **"devices" (Object, Optional):**
  
  - Maps friendly alias names (e.g., "MyMainController") to substrings of your actual MIDI device names (e.g., "X-Session Pro").
  
  - midimod will use the devices section from the **first** rule file (in load order) that contains it.

- "_comment" (String, Optional): General description of the route. It will be displayed in the rules summary.

- "input_device_substring" (String, Optional): Part of the MIDI input device name. If omitted, the first available input port is used.

- "output_device_substring" (String, Optional): Part of the MIDI output device name. If omitted, the first available output port is used.

- "version_midi_map" (Object, Optional): Maps specific MIDI messages to changes in the current_active_version or cycle actions (e.g., "note_on note=60 channel=0": 1, "note_on note=108": "cycle"). Messages that trigger this are "consumed."

- "transformations" (List of Objects): Defines the transformation rules that are applied sequentially.

- **"routes" (List, Required for processing):**
  
  - Each element is an object defining a processing route.

**Common Keys within a Transformation Object:**

- "_comment" (String, Optional): Describes the transformation.

- "version" (Integer or List of Integers, Optional): The transformation only applies if the current_active_version matches or is in the list. If omitted, the transformation always applies within its route.

- "ch_in" (List of Integers, Optional): Input MIDI channels (0-15) it applies to.

- "ch_out" (List of Integers, Optional): Output MIDI channel(s) (0-15). An empty list [] filters the message.

- "cc_in" (Integer, Optional): Filters by this CC number.

- "cc_out" (Integer, Optional): Changes the CC number to the specified value. If cc_in is present but cc_out is not, the CC number does not change.

- "cc_range" (List [min, max], Optional): Scales the incoming CC value (matching cc_in, or any CC if cc_in is not present) to the new range.

- "nt_st" (Integer, Optional): Semitones to transpose notes.

- "velocity_range" (List [min, max], Optional): Scales the velocity of note_on messages.

- "note_to_cc" (Object, Optional): Transforms a specific note into a CC.
  
  - Contains: "note_in", "cc_out", "value_on_note_on", "value_on_note_off", "ch_out_cc", "use_velocity_as_value".

- "note_to_pc" (Object, Optional): Transforms a specific note into a Program Change.
  
  - Contains: "note_in", "program_out", "send_on_note_on", "send_on_note_off", "ch_out_pc".

- "aftertouch_to_cc" (Object, Optional): Transforms Channel Aftertouch messages into CCs.
  
  - Contains: "cc_out", "ch_out_cc", "value_range".

**Note:** For an exhaustive description of all keys and their behavior, run

```
python midimod.py --help
```

## Detailed Rule Examples

To see concrete examples of how to configure different types of transformations and combinations, please refer to the RULES_EXAMPLES.md file.

## Console Output Log

When midimod is running, processed MIDI messages are displayed in the console. The general format is:

[V] RouteID|IN : ch(C) type(N) attr(V) >> [V] RouteID|OUT: ch(C') type(N') attr(V')

- [V]: The current_active_version at the time of processing.

- RouteID: Identifier of the route that processed the message (e.g., R1, R2).

- IN :: Indicates the original MIDI message that entered the route.

- (empty) If there is no OUT: part, it means the route processed the message but no transformation was performed.

- OUT:: Indicates the MIDI message after being processed by the transformations of that route.

- ch(C): MIDI Channel (1-16).

- type(N): Message type and note/CC (e.g., note_on(60), cc(10)).

- attr(V): Relevant attribute and its value (e.g., vel(100), val(64)).

If a single input message is processed by multiple routes (because they share the same physical input port), or if a route splits a message into multiple outputs (e.g., with ch_out), you will see multiple >> OUT: lines under a single IN : line.

## Common Troubleshooting

- **"Error opening port..." or "Error sending message..."**: Usually means the MIDI port is being used by another application (DAW, virtual patchbay, another instance of midimod). Close all other applications that might use MIDI.

- **Device not detected**: Run python midimod.py --list-ports to see the exact names of your devices and ensure the *_device_substring in your JSON match.

- **JSON File Encoding**: Ensure your .json files are saved with UTF-8 encoding, especially if you use special characters in _comment.

## Contributions

Suggestions, bug reports, and contributions are welcome. Please open an "Issue" on GitHub to discuss changes or report problems.

## License

This project is under the MIT License. See the LICENSE file for more details.
