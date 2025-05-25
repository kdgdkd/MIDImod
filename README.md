# MIDImod: Advanced MIDI Processing and Creative Control

MIDImod is a Python tool for musicians and producers who want to take full command of their MIDI data. It lets you intercept, creatively transform, and precisely reroute MIDI messages between your hardware and software instruments and controllers – all in real time. You define how MIDImod works using simple JSON text files, giving you powerful control without needing to be a coding expert.

Think of MIDImod as a smart, customizable MIDI patchbay and processor, sitting at the heart of your setup.

## What can MIDImod do for you?

MIDImod helps you overcome common MIDI limitations and explore new creative avenues with your gear. Here are some key things you can achieve:

- **Connect and Route Your Gear:**
  
  - Easily link any MIDI keyboard, controller, or sound module to another.
  
  - Direct MIDI signals exactly where needed, e.g., keyboard to synth A, pads to synth B.
  
  - Change MIDI channels for incoming or outgoing messages.

- **Shape Melodies and Harmonies (Note Transformations):**
  
  - **Transpose:** Shift notes up or down by semitones or octaves.
  
  - **Create Layers & Harmonies:** Duplicate a melody to play on another sound or channel, perhaps an octave lower for a bassline, or add a harmony.
  
  - **Stay in Key (Scale Quantization):** Make sure your notes always fit a chosen musical scale (e.g., C Major, A Minor Pentatonic).
  
  - **Add Randomness:** Introduce controlled random variations to note pitches.

- **Enhance Your Knobs and Faders (Control Change - CC - Manipulation):**
  
  - **Remap Controls:** Make one knob control a different parameter (e.g., CC #20 becomes CC #74 for filter control).
  
  - **Fine-Tune Control Ranges (Value Scaling):** Adjust how sensitive a knob is, making it cover a wider or narrower range of values.
  
  - **Smarter Knob Behavior (cc_type_in):**
    
    - **Relative/Encoder Feel:** Make standard knobs act more like endless encoders for smoother changes.
    
    - **Accelerated Control (abs_relative):** Small knob turns give fine adjustments, while quick/large turns make bigger changes – useful for performance. Its sensitivity is defined by "threshold" (default 0, meaning always accelerated unless P==C) and "abs2rel_factor" (default 2.0).
    
    - **"Catch-up" Mode (abs_catchup):** Avoid sudden sound changes when a knob's physical position doesn't match the current parameter value. The MIDI output only updates when your knob "catches up." Its sensitivity is defined by "threshold" (default 5).

- **New Ways to Control (Event Conversion):**
  
  - Use note buttons on your keyboard to send Program Changes or trigger CC messages.
  
  - Use how hard you play (velocity) or aftertouch pressure to dynamically control synth parameters.

- **Switch Setups Instantly (Versions - Dynamic Presets):**
  
  - Create different MIDI processing setups ("versions").
  
  - Use a MIDI note or CC from any controller to instantly switch between these versions – like changing scenes for your whole MIDI rig with one button.

- **Build Complex Interactions (User Variables):**
  
  - Store values (like a CC value or note number) in temporary memory slots (var_0 to var_15).
  
  - Use these stored values in other rules to create more advanced, conditional MIDI effects.

- **Control Sequencers and Synths (Transport & SysEx):**
  
  - Send Play/Stop/Continue to external sequencers or your DAW.
  
  - Send specific System Exclusive (SysEx) messages to change patches or detailed settings on your hardware synths.

- **Integrate with Your DAW (Virtual Ports):**
  
  - MIDImod can create **virtual MIDI ports** on your computer. This means you can route MIDI from one piece of software (like your DAW – Ableton Live, Logic Pro, etc.), through MIDImod for processing, and then into another piece of software or back into your DAW on a different track. It's like adding a powerful custom MIDI effects processor right into your digital workflow.

- **Combine and Organize (Multiple Rule Files):**
  
  - You can **load several rule files at once**. This allows you to keep your configurations modular. For example, one file for your keyboard setup, another for your drum machine, and a third for global controls. MIDImod merges them all together.

MIDImod is designed to be flexible. The configuration is done through simple JSON text files, making it powerful yet accessible.

## Main Features

- **Device Aliases:** Use easy-to-remember names for your MIDI devices (e.g., "MyKeyboard", "MainSynth").

- **Clear Rule Structure:** Define "filters" that react to specific incoming MIDI messages.

- **Multiple Outputs:** A single incoming MIDI message can trigger several different outgoing messages or actions (using the "output": [{...}, {...}] list structure). If a filter has only one simple output action, you can define it directly within the filter.

- **Global Versions:** Switch between entire sets of rules (versions) using a MIDI command.

- **JSON Configuration:** All settings and rules are stored in human-readable JSON text files.

- **Real-time Monitor:** See incoming and outgoing MIDI messages in your console, so you know exactly what's happening.

- **Interactive Rule File Selector:** If you don't specify a rule file when starting, MIDImod offers a simple menu to choose and order multiple files.

- **Virtual MIDI Ports:** Connect MIDImod to other software on your computer using virtual MIDI ports.

## Requirements

- Python 3.7 or higher.

- Python libraries: mido, python-rtmidi, prompt_toolkit.

### Installing Dependencies

Open your computer's terminal or command line interface and type:  
pip install mido python-rtmidi prompt-toolkit

(Note for Linux users: You might need to install system packages like libasound2-dev (on Debian/Ubuntu) for python-rtmidi to work correctly.)

## Usage

Run midimod.py from your terminal or command line.

**Basic Syntax:**  
python midimod.py [rule_file_name_1] [rule_file_name_2] [...] [options]

- **[rule_file_name_...]**: (Optional) The names of your rule files (without the .json extension). These files should be in a subfolder named rules_new/. If you don't provide any, MIDImod will show an interactive selector where you can choose and order multiple files.

- **Options:**
  
  - --list-ports: Shows a list of all MIDI input and output devices connected to your computer and then exits.
  
  - --virtual-ports: Activates virtual MIDI port mode. MIDImod will create an input port (default: MIDImod_IN) and an output port (default: MIDImod_OUT) that other software can connect to.
  
  - --vp-in YOUR_INPUT_NAME, --vp-out YOUR_OUTPUT_NAME: Lets you specify custom names for the virtual MIDI ports.
  
  - --no-log: Starts MIDImod without showing the real-time MIDI message monitor in the console.
  
  - --help: Displays detailed help information and all available options.

**Examples of How to Run MIDImod:**

- **Using the interactive selector to choose rule files:**  
  python midimod.py

- **Loading specific rule files (e.g., my_setup.json and live_performance.json):**  
  python midimod.py my_setup live_performance

- **Listing your available MIDI ports:**  
  python midimod.py --list-ports

## Structure of Rule Files (.json)

Your rule files are the heart of MIDImod. They must be in JSON format and live in a folder named rules_new/ located in the same directory as the midimod.py script.

**Main Sections in a Rule File:**

1. **"device_alias" (Object, Optional but Highly Recommended):**
   
   - Define short, memorable names (aliases) for your MIDI devices.
   
   - Example: { "Keyb": "SL MkII", "Synth": "Uno MIDI", "Pads": "BeatStep" }
   
   - MIDImod uses the device_alias section from the first rule file loaded that contains one.

2. **"version_map" (List of Objects, Optional):**
   
   - Defines how to change the active "version" using MIDI messages.
   
   - Each object is a rule:
     
     - "device_in": Alias of the triggering input device.
     
     - "ch_in", "event_in", "value_1_in", "value_2_in": Conditions for the trigger.
     
     - "version_out": Target version number or "cycle_next" / "cycle_previous".

3. **"input_filter" (List of Objects, Usually Required):**
   
   - Your main MIDI processing rules. Each object is a "filter."

**Inside an "input_filter" Object (a single filter):**

- "_comment": (Optional) Your notes.

- "version": (Optional) Activates filter only for specific version(s).

- "device_in": (Required for MIDI-triggered filters) Input device alias.

- "ch_in", "event_in", "value_1_in", "value_2_in": Input message conditions.

- "cc_type_in": (Optional, for event_in: "cc") How to interpret input CCs ("abs", "relative_signed", "relative_2c", "abs_relative", "abs_catchup").
  
  - For "abs_relative": uses "threshold" (default 0) and "abs2rel_factor" (default 2.0).
  
  - For "abs_catchup": uses "threshold" (default 5).

- **Output Definition (Two Ways):**
  
  1. **For a single, simple output action directly in the filter:**
     
     - "device_out": (Optional) Output device alias.
     
     - "channel_out", "event_out", "value_1_out", "value_2_out": Output parameters.
     
     - "cc_type_out", "sysex_data", variable assignments ("var_0": ...).
  
  2. **For multiple output actions, or more complex structuring, use an "output" list:**
     
     - "output": (List of Objects) Each object defines an output action with the same keys as above ("device_out", "channel_out", etc.).

**Key Output Parameters (whether direct or in "output" list):**

- "device_out": (Optional) Output device.

- "channel_out": (Optional) Output channel. Inherits from input if not set.

- "event_out": (Optional) Output event type. Inherits from input.

- "value_1_out": (Optional) Output note, CC num, PC num. Inherits. Can be number, expression (e.g., "value_1_in + 12"), or "random(min, max)".

- "value_2_out": (Optional) Output velocity, CC value. Inherits. Can be number, expression.

- "cc_type_out": (Optional, for event_out: "cc") Output CC format.

- "sysex_data": (For event_out: "sysex") List of data bytes (script adds F0/F7).

- Variable Assignment: e.g., "var_0": 100. (Access with var_0...var_15).

- Advanced Value Transformations (for value_1_out, value_2_out):
  
  - Range Scaling: { "scale_value": "source", "range_in": [min,max], "range_out": [min,max] }
  
  - Note-to-Scale: { "scale_notes": {"scale_value": "note_var", "scale_root": num, "scale_type": "name"} }

**Variables in Output Expressions:**  
channel_in, value_1_in, value_2_in (input CC value after cc_type_in), delta_in (physical CC change), event_in, cc_type_in, cc_val2_saved (last sent value for output CC/ch), and var_0...var_15.

## Simple Rule File Examples

Using simplified JSON where possible. Remember to adapt "device_alias" to your gear.  
**Common "device_alias" block for these examples:**

```
{
    "device_alias": {
        "MyKeyboard": "PART_OF_YOUR_KEYBOARD_NAME",
        "MyController": "PART_OF_YOUR_CONTROLLER_NAME",
        "MySynth": "PART_OF_YOUR_SYNTH_NAME"
    }
}
```

content_copydownload

Use code [with caution](https://support.google.com/legal/answer/13505487).Json

---

**1. connect_keyboard_to_synth.json** (Direct Connection)  
Purpose: Everything from MyKeyboard goes to MySynth.

```
{
    "device_alias": { "MyKeyboard": "KB_NAME", "MySynth": "SYNTH_NAME" },
    "input_filter": [
        {
            "device_in": "MyKeyboard",
            "device_out": "MySynth"
        }
    ]
}
```

---

**2. change_keyboard_channel.json**  
Purpose: MyKeyboard channel 1 (ch_in: 0) output to MySynth channel 5 (channel_out: 4).

```
{
    "device_alias": { 
        "MyKeyboard": "YourKeyboardName", 
        "MySynth": "YourSynthName" 
    },
    "input_filter": [
        {
            "device_in": "MyKeyboard", 
            "ch_in": 0,
            "device_out": "MySynth", 
            "channel_out": 4
        }
    ]
}
```

---

**3. transpose_octave.json**  
Purpose: Notes from MyKeyboard (Ch 1) sent to MySynth (Ch 1) one octave higher.

```
{
    "device_alias": { "MyKeyboard": "KB_NAME", 
                      "MySynth": "SYNTH_NAME" },
    "input_filter": [
        {
            "device_in": "MyKeyboard", 
            "ch_in": 0, 
            "event_in": "note",
            "device_out": "MySynth", 
            "value_1_out": "value_1_in + 12"
        }
    ]
}
```

---

**4. knob_controls_another_cc.json**  
Purpose: CC #20 from MyController (Ch 1) becomes CC #74 on MySynth (Ch 1).

```
{
    "input_filter": [
        {
            "device_in": "MyController", 
            "ch_in": 0, "event_in": "cc", 
            "value_1_in": 20,
            "device_out": "MySynth", 
            "value_1_out": 74
            /* value_2_out (CC value) will be inherited from input if not specified */
        }
    ]
}
```

---

**5. note_changes_program.json**  
Purpose: Middle C (note 60) on MyKeyboard (Ch 1) sends Program Change #5 to MySynth (Ch 1).

```
{
    "input_filter": [
        {
            "device_in": "MyKeyboard", 
            "ch_in": 0, 
            "event_in": "note_on", 
            "value_1_in": 60,
            "device_out": "MySynth", 
            "event_out": "pc", 
            "value_1_out": 5
        }
    ]
}
```

---

## Advanced Examples

**6. layers_and_scales_by_version.json**  
Purpose: Use MyController to switch MyKeyboard between a layer and scale quantization.

```
{
    "device_alias": { "MyKeyboard": "KB", "MyController": "CTRL", "MySynth": "SYNTH" },
    "version_map": [
        { "device_in": "MyController", "ch_in": 0, "event_in": "note_on", "value_1_in": 36, "version_out": 0 },
        { "device_in": "MyController", "ch_in": 0, "event_in": "note_on", "value_1_in": 37, "version_out": 1 }
    ],
    "input_filter": [
        {
            "version": 0, "device_in": "MyKeyboard", "ch_in": 0, "event_in": "note",
            "output": [ /* Multiple outputs require the "output" list */
                { "device_out": "MySynth", "channel_out": 0 },
                { "device_out": "MySynth", "channel_out": 1, "value_1_out": "value_1_in - 12" }
            ]
        },
        {
            "version": 1, "device_in": "MyKeyboard", "ch_in": 0, "event_in": "note",
            "device_out": "MySynth", "channel_out": 2, /* Single output can be direct */
            "value_1_out": { "scale_notes": {"scale_value": "value_1_in", "scale_root": 60, "scale_type": "major"}}
        }
    ]
}
```

---

**7. advanced_cc_control_and_variables.json**  
Purpose: Accelerated CC, storing CC value to a variable, using variable in another CC.

```
{
    "device_alias": { "MyController": "CTRL", "MySynth": "SYNTH" },
    "input_filter": [
        { /* Knob with acceleration */
            "device_in": "MyController", "ch_in": 0, "event_in": "cc", "value_1_in": 20,
            "cc_type_in": "abs_relative", "abs2rel_factor": 3.0,
            "device_out": "MySynth", "channel_out": 0, "value_1_out": 74
        },
        { /* Knob to store its value in var_0 (no MIDI output from this filter directly) */
            "device_in": "MyController", "ch_in": 0, "event_in": "cc", "value_1_in": 21,
            "var_0": "value_2_in" /* Output is just variable assignment */
        },
        { /* Knob whose output value is modified by var_0 */
            "device_in": "MyController", "ch_in": 0, "event_in": "cc", "value_1_in": 22,
            "device_out": "MySynth", "channel_out": 1, "value_1_out": 70,
            "value_2_out": "value_2_in + var_0"
        }
    ]
}
```

---

**8. transport_control_and_sysex.json**  
Purpose: Pads send Start/Stop and SysEx.

```
{
    "device_alias": { "MyPads": "PADS", "MySynth": "SYNTH_A", "MySequencer": "SEQ_OUT"},
    "input_filter": [
        { /* Pad sends MIDI Start */
            "device_in": "MyPads", "ch_in": 9, "event_in": "note_on", "value_1_in": 36,
            "device_out": "MySequencer", "event_out": "start"
        },
        { /* Pad sends MIDI Stop */
            "device_in": "MyPads", "ch_in": 9, "event_in": "note_on", "value_1_in": 37,
            "device_out": "MySequencer", "event_out": "stop"
        },
        { /* Pad sends a SysEx message */
            "device_in": "MyPads", "ch_in": 9, "event_in": "note_on", "value_1_in": 40,
            "device_out": "MySynth", "event_out": "sysex",
            "sysex_data": [ 0, 32, 41, 2, 18, 116, 0 ]
        },
        { /* MIDI Clock passthrough */
            "device_in": "MyPads", "event_in": "clock",
            "device_out": "MySequencer"
        }
    ]
}
```

## Console Monitor

When MIDImod is running, it displays processed MIDI messages:

- [V] IN:[Device] Ch(C) TYPE(VALUE) vel(X) >> [V] OUT:[Device] Ch(C') TYPE'(VALUE') vel(X')

- [V] IN:[Device] Ch(C) TYPE(VALUE) vel(X) >> [NOUT] (filter matched, no MIDI output)

- [*] >> SET: var_X = Y (user variable set)

**Breakdown:** [V]: Version, Device: Alias, Ch(C): Channel, TYPE(VALUE): e.g., NT_on(60), CC(20), vel(X)/val(X): Velocity/CC Value.

## Troubleshooting

- **"Error opening port..."**: Another program is using the port. Close other MIDI apps.

- **Device not detected**: Use --list-ports to check names; match them in "device_alias".

- **JSON Errors**: MIDImod will report syntax errors. Use an online JSON validator if needed.

- **Encoding**: Save .json files as UTF-8.

## Contributions

Suggestions & bug reports are welcome! Please open an "Issue" on GitHub.

## License

MIT License. See LICENSE file.
