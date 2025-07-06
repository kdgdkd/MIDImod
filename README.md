# MIDImod: Advanced MIDI Processing and Creative Control

MIDImod is a Python tool for musicians and producers who want to take full command of their MIDI data. It lets you intercept, creatively transform, and precisely reroute MIDI messages between your hardware and software instruments and controllers – all in real time. You define how MIDImod works using simple JSON text files, with simple and flexible structure, giving you powerful control without needing to be a coding expert.

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
    
    - **Absolute and Relative Encoders:** Receives, processes and sends absolute and relative control change signals.
    
    - **Accelerated Control (abs_relative):** Avoid sudden sound changes when a knob's physical position doesn't match the current parameter value. abs_relative mode will interpret changes to an absolute encoder as they were increments/decrements coming from a relative encoder.  
    
    - **"Catch-up" Mode (abs_catchup):** With similar purpose, the MIDI output only updates when your knob "catches up" with the parameter value. 

- **New Ways to Control (Event Conversion):**
  
  - Use note buttons on your keyboard to send Program Changes or trigger CC messages.
  
  - Use how hard you play (velocity) or aftertouch pressure to dynamically control synth parameters. For example, assign the note velocity to open the filter cutoff, producing a Velocity Tracking effect. 

- **Switch Setups Instantly (Versions - Dynamic Presets):**
  
  - Create different MIDI processing setups ("versions").
  
  - Use a MIDI note or CC from any controller to instantly switch between these versions – like changing pages on a controller or scenes for your whole MIDI rig with one button.

- **Build Complex Interactions (User Variables):**
  
  - Store values (like a CC value or note number) in temporary memory slots (var_0 to var_15).
  
  - Use these stored values in other rules to create more advanced, conditional MIDI effects.

- **Control Sequencers and Synths (Transport & SysEx):**
  
  - Send Play/Stop/Continue to external sequencers or your DAW.
  
  - Send specific System Exclusive (SysEx) messages to change patches or detailed settings on your hardware synths.

- **Integrate with Your DAW (Virtual Ports):**
  
  - MIDImod can create **virtual MIDI ports** on your computer. This means you can route MIDI from a controller through a MIDImod port, and read the processed output in any piece of software (like your DAW – Ableton Live, Logic Pro, etc.). It easily adds a powerful custom MIDI effects processor right into your digital workflow.

- **Build Rhythmic Patterns (Sequencer):**
  
  - Create complex, multi-track sequences directly within your JSON files. Features include variable step length, probability, swing, micro-timing (shift), and dynamic control over every parameter per step. You can even import note data from standard MIDI files.

- **Generate Melodies (Arpeggiator):**
  
  - Trigger a flexible arpeggiator from any MIDI input. Includes multiple modes (up, down, up/down, random, as-played, stutter), octave controls, and latch functionality for hands-free operation.

- **Combine and Organize (Multiple Rule Files):**
  
  - You can **load several rule files at once**. This allows you to keep your configurations modular. For example, one file for your keyboard setup, another for your drum machine, and a third for global controls. MIDImod merges them all together.

MIDImod is designed to be flexible. The configuration is done through simple JSON text files, making it powerful yet accessible.


## Requirements

- Python 3.7 or higher.

- Python libraries: mido, python-rtmidi, prompt_toolkit.

### Installing Dependencies

Open your computer's terminal or command line interface and type:  
pip install mido python-rtmidi prompt-toolkit json5 python-osc watchdog

(Note for Linux users: You might need to install system packages like libasound2-dev (on Debian/Ubuntu) for python-rtmidi to work correctly.)

## Usage

Run midimod.py from your terminal or command line.

**Basic Syntax:**  
python midimod.py [rule_file_name_1] [rule_file_name_2] [...] [options]

- **[rule_file_name_...]**: (Optional) The names of your rule files (without the .json extension). These files should be in a subfolder named rules/. If you don't provide any, MIDImod will show an interactive selector where you can choose and order multiple files.

- **Options:**
  
  - --list-ports: Shows a list of all MIDI input and output devices connected to your computer and then exits.
  
  - --live: Activates Live Mode. Rules are loaded from the `./live/` directory and are automatically reloaded when any file inside it is saved, without stopping the music.
  
  - --virtual-ports: Activates virtual MIDI port mode. MIDImod will create an input port (default: MIDImod_IN) and an output port (default: MIDImod_OUT) that other software can connect to.
  
  - --vp-in YOUR_INPUT_NAME, --vp-out YOUR_OUTPUT_NAME: Lets you specify custom names for the virtual MIDI ports.
  
  - --no-log: Starts MIDImod without showing the real-time MIDI message monitor in the console.
  
  - --help: Displays detailed help information and all available options.

**Examples of How to Run MIDImod:**

- **Using the interactive selector to choose rule files:**  
  python midimod.py

- **Loading specific rule files (e.g., my_setup.json and live_performance.json):**  
  python midimod.py my_setup live_performance

- **Listing your available MIDI ports:**  
  python midimod.py --list-ports

## Live Mode for Performance and Improvisation

The `--live` option transforms MIDImod into a dynamic instrument for live performance. When activated, it loads all rule files from a `./live/` directory and then watches that directory for any changes.

If you save a modification to any `.json` file in the `./live/` folder, MIDImod will instantly reload its entire configuration **without interrupting the MIDI clock or stopping any playing sequencers**.

This allows for powerful, on-the-fly arrangement and sound design:

-   **Modify Sequences in Real Time:** While a sequence is playing, you can open its JSON file, change the `seq_transpose` or `seq_gate` arrays, and upon saving, the sequence will adopt the new pattern on its next loop.
-   **Tweak Controller Mappings:** You can adjust CC mappings, change a knob's scale, or remap a controller to a different synth parameter mid-performance.
-   **Evolve Your Setup:** Add or remove entire filters or modules. For example, you could introduce a new arpeggiator rule, save the file, and immediately start using it.

**To use Live Mode:**

1.  Create a `live/` directory next to `midimod.py`.
2.  Place your performance rule files inside it.
3.  Run MIDImod with the `--live` flag:
    ```bash
    python midimod.py --live
    ```
4.  Open your rule files in a text editor and start performing. Every `Ctrl+S` becomes part of your musical expression.


## Structure of Rule Files (.json)

Your rule files are the heart of MIDImod. They must be in JSON format and live in a folder named rules/ located in the same directory as the midimod.py script. Sections for the json files are:


1. **"device_alias" (Object, Optional but Highly Recommended):**
   
   - Define aliases for your MIDI devices, allowing for partial coincidence with the port names.

2. **"user_variables" (Object, Optional):**

   - Define global variables that can be accessed and modified by any rule, sequencer, or arpeggiator.

3. **"midi_filter" (List of Objects, Usually Required):**
   
   - Your main MIDI processing rules. Signals that match the input conditions will be processed.

4. **"sequencer" (List of Objects, Optional):**

   - Define one or more pattern-based sequencers.

5. **"arpeggiator" (List of Objects, Optional):**

   - Define templates for the arpeggiator modules.

6. **"osc_filter" (List of Objects, Optional):**

   - Define rules that react to incoming OSC messages.


### Creative Modules: Sequencer & Arpeggiator

Beyond simple MIDI filtering, MIDImod includes powerful, pattern-based creative modules. These are defined in their own top-level sections within your JSON files.

### The Sequencer

The sequencer allows you to create complex, multi-track melodic and rhythmic patterns that are driven by an external MIDI clock. 
**To create a sequencer, add an object to the `"sequencer"` list in your JSON file:**

```
"sequencer": [
 {
 "seq_id": "my_first_sequence",
 "clock_in": "MasterClock",
 "device_out": "MySynth",
 "channel_out": 1,
 "step_total": 16,
 "step_duration": "1/16",
 "seq_root_note": 48,
 "seq_transpose": [0, 3, 5, 7, 0, 3, 5, 7, 0, 3, 5, 7, 0, 3, 5, 7],
 "output": [{
     "value_1_out": "root_note_out + transpose_out"
     }]
 }
]
```

**Key Sequencer Parameters:**

- "seq_id" (String): A unique name for the sequencer. **Crucial for the --live mode** to work without interrupting playback.
  
- "clock_in" (String): The device_alias of the MIDI port sending the clock signal. This is required to drive the sequencer.
  
- "device_out" & "channel_out": Define the destination for the sequencer's MIDI output.
  

**Timing and Rhythm Parameters:**

- "step_total" (Integer): The total number of steps in the sequence (e.g., 16, 32, 64).
  
- "step_duration" (String): The musical duration of a single step (e.g., "1/16", "1/8", "1/4t" for triplets).
  
- "ppqn" (Integer): Pulses Per Quarter Note. Defines the timing resolution. Defaults to 24.
  
- "swing" (Float): A value from 0.0 to 1.0 to apply swing to every second step.
  
- "shift_global" (Float): A value from -1.0 to 1.0 to shift the timing of all steps forward or backward.
  
- "shift_array" (List of Floats): An array to apply a specific micro-timing shift to each individual step.
  

**Note and Gate Parameters (Per-Step Arrays):**

These are arrays where each element corresponds to a step in the sequence.

- "seq_gate" (List of Integers): Determines if a step is active (1) or silent (0).
  
- "seq_note" (List of Integers): An array of absolute MIDI note numbers. This is a simple way to define a melody.
  
- "seq_root_note" (Integer or List): Sets a base note for the sequence. Can be a single value or an array to change the root note per step.
  
- "seq_transpose" (List of Integers): An array of semitone values that are added to the root note for each step.
  
- "seq_velocity" (Integer or List): Sets the velocity for each step.
  
- "seq_note_length" (Float or List): A multiplier for the step duration that controls the length of the note (from 0.0 to 1.0 for staccato, >1.0 for legato/overlapping notes).
  
- "seq_probability" (Float or List): The chance (from 0.0 to 1.0) that a step will actually play.
  

**Dynamic Control:**

- "seq_active" (Integer or Expression): Use 1 or 0 (or an expression like "1 if my_var > 50 else 0") to turn the entire sequencer on or off dynamically.
  
- "seq_mute" (Integer or Expression): Similar to seq_active, but mutes the output without stopping the sequence's internal clock.
  

**Output Generation:**

The sequencer prepares **context variables** for each step (e.g., root_note_out, transpose_out, velocity_out). You should define how these variables are combined to create the final MIDI message in the output block, giving you full control.

### The Arpeggiator

The arpeggiator is a real-time performance module that takes incoming notes and generates rhythmic, melodic patterns from them. Unlike the sequencer, it is not driven by a pre-defined pattern but by the notes you play live.

It works in two parts: a template definition in the "arpeggiator" list, and a midi_filter to trigger it.

**1. Define an Arpeggiator Template:**

```
"arpeggiator": [
    {
        "arp_id": 1,
        "device_out": "MySynth",
        "channel_out": 2,
        "arp_mode": "updown",
        "step_duration": "1/16",
        "arp_octaves": 2,
        "arp_latch": false
    }
]
```

**2. Create a midi_filter to Feed it Notes:**

```
"midi_filter": [
    {
        "device_in": "MyKeyboard",
        "event_in": "note",
        "arp_id": 1
    }
]
```

- This filter listens for notes and, instead of producing a direct output, its "arp_id": 1 command sends the incoming note information to the arpeggiator engine with the matching ID.

**Key Arpeggiator Parameters (defined in the template):**

- "arp_id" (Integer): A unique number to identify this arpeggiator template.
  
- "device_out" & "channel_out": Define the destination for the arpeggiator's MIDI output.
  
- "arp_latch" (Boolean): If true, the arpeggiator will continue playing the last held notes even after the keys are released. If false (default), it stops when all keys are released.
  

**Pattern and Note Selection Parameters:**

- "arp_mode" (String): Controls how the arpeggiator selects notes from the ones you are holding down.
  
  - "as_played": Uses the notes in the exact order you played them.
    
  - "sorted": Sorts the notes from lowest to highest (this is the base for direction modes).
    
  - "outside_in": Plays the lowest note, then the highest, then the second-lowest, second-highest, and so on.
    
  - "random1": Shuffles the notes once and repeats that random pattern.
    
  - "random2": Picks a completely random note from the input on every step.
    
  - "stutter", "stutter4", "stutter8": Repeats each note in the pattern 2, 4, or 8 times before moving to the next.
    
- "arp_step_direction" (String): Determines the direction of the pattern after it has been generated by arp_mode.
  
  - "up": Plays the pattern from start to end.
    
  - "down": Plays the pattern in reverse.
    
  - "updown": Plays forward, then backward, without repeating the end notes.
    
  - "updown_inclusive": Plays forward, then backward, repeating the start and end notes.
    
  - "random_walk": Moves one step up or down the pattern at random.
    
  - "random_jump": Jumps to any random step in the pattern.
    
- "arp_octaves" (Integer): The number of octaves the pattern should span.
  
- "arp_octave_mode" (String): How the octaves are applied.
  
  - "up": Plays the full pattern, then plays it again an octave up, and so on.
    
  - "alternate": Plays each note of the pattern through all octaves before moving to the next note.
    

**Rhythm and Gate Parameters:**

- "step_duration" (String): The musical duration of each arpeggiator step (e.g., "1/16", "1/8").
  
- "arp_gate" (Integer or Expression): A master gate (1 or 0) to turn the arpeggiator's output on or off.
  
- "arp_mute" (Integer or Expression): Mutes the arpeggiator.
  
- "arp_note_length" (Float): A multiplier for the step duration to control note length.
  
- "arp_probability" (Float): The chance (from 0.0 to 1.0) that a step will play.
  

**Dynamic Control:**

Just like the sequencer, all arpeggiator parameters can be assigned dynamic expressions and controlled by user variables or incoming MIDI messages, allowing you to change the arpeggiation style in real-time.



**Inside an "midi_filter" Object (a single filter):**

- "version": (Optional) Activates filter only for specific version(s).

- "device_in": (Required for MIDI-triggered filters) Input device alias.

- Optional conditions on incoming events: "ch_in", "event_in", "value_1_in", "value_2_in", "cc_type_in": (for CC types "abs", "relative_signed", "relative_2c", "abs_relative", "abs_catchup").

- If the incoming signal matches the filter, the values of the signal (channel, value 1, value 2, event type) are used for output processing, and will be used by default of no changes are defined. 


- **Output Definition:**
       
     - "output": Optional section that defines a single transformation coming from an midi_filter. It can be ommited if there is a single output for the incoming filter.





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



User Variables and State Management

MIDImod allows you to store and recall values in memory, enabling complex interactions and stateful logic. This is handled through two mechanisms: simple **User Variables** and indexed **Arrays** (like channel or sequencer arrays).

#### Simple User Variables

You can define global variables in the "user_variables" section of your JSON file. These act like memory slots that can be read from or written to by any filter or module.

**1. Defining a User Variable:**

```
"user_variables": {
    "global_transpose": 0,
    "effect_rate": 80,
    "is_special_mode_active": 0
}
```

**2. Reading a User Variable:**

Once defined, you can access a variable directly by its name in any expression.

```
"output": [{
    "value_1_out": "value_1_in + global_transpose"
}]
```

**3. Writing to a User Variable:**

To change the value of a user variable, use its name as a key inside an "output" block.

```
"output": [{
    "global_transpose": "value_2_in",
    "is_special_mode_active": "toggle(is_special_mode_active)"
}]
```

- This output block reads the current value of global_transpose, adds 12, and saves it back. It also toggles the value of is_special_mode_active between 0 and 1.
  
- If this block has no "device_out", its only purpose is to modify the variables without sending any MIDI.
  

#### Indexed Arrays (set_var and get_var)

For more complex state management, like storing the value of all 128 CCs for a specific channel, you need indexed arrays. MIDImod provides two special functions for this: set_var and get_var.

- **Channel Arrays:** MIDImod automatically manages internal arrays for you, like ch_1_cc_values, ch_2_cc_values, etc. You don't need to define them.
  
- **Sequencer Arrays:** You can also use set_var to modify the arrays of a running sequencer (seq_transpose, seq_gate, etc.) from a midi_filter.
  

**set_var (Writing to an Array):**

The set_var action is used inside an "output" block to write a value to a specific index in an array.

```
"output": [{
    "set_var": {
        "name": "ch_1_cc_values",
        "index": 21,
        "value": "value_2_in"
    }
}]
```
- "name": The name of the array to modify.

- "index": The position within the array to change (0-based).
  
- "value": The new value to store at that index.
  

**get_var (Reading from an Array):**

The get_var function is used inside any expression to read a value from a specific index in an array.

```
"if": "get_var('ch_1_cc_values', 21) > 64"
```

- The first argument is the name of the array to read from.
  
- The second argument is the index to read.
  

This set_var/get_var mechanism is what allows you to create powerful, stateful logic where one control can influence the behavior of another.

#### Expressions and Built-in Functions

All string values for output parameters are processed by Python's eval() function, giving you access to a powerful expression engine. You can perform mathematical operations, use comparisons, and call special built-in helper functions provided by MIDImod:

- random(min, max): Returns a random integer between min and max.
  
  - Example: "value_2_out": "random(80, 110)"
- toggle(variable): Flips a variable's value between 0 and 1.
  
  - Example: "my_var": "toggle(my_var)"
- chord(root, num_notes, scale_name): Generates a list of notes for a chord.
  
  - Example: "value_1_out": "chord(60, 3, 'minor')"
- scale_number(index): Returns the name of a scale from the user-defined scale_list.
  
- get_var(array_name, index): Retrieves a value from an indexed array.
  

This allows for incredibly dynamic and generative possibilities directly within your rule files.

##### Advanced Value Transformation Functions

For more complex manipulations, MIDImod provides special functions that you use by creating a JSON object as the value, instead of a simple string expression.

- **scale_value (Range Scaling):** Remaps a numeric value from an input range to a new output range. This is perfect for limiting the range of a knob or inverting its response.
  
  **Example:** Limit a knob's output to a range between 50 and 100.
  
  ```
  "value_2_out": {
      "scale_value": "value_2_in",
      "range_in": [0, 127],
      "range_out": [50, 100]
  }
  ```
  
- **scale_notes (Note-to-Scale Quantization):** Forces an incoming MIDI note to snap to the nearest note within a specified musical scale. This is a powerful tool for ensuring your melodies are always in key.
  
  **Example:** Snap all incoming notes to the C Minor Pentatonic scale.
  
  ```
  "value_1_out": {
      "scale_notes": {
          "scale_value": "value_1_in",
          "scale_root": 60,
          "scale_type": "minor_pentatonic"
      }
  }
  ```
  
  - scale_value: The incoming note number to be quantized.
    
  - scale_root: The root note of the scale (e.g., 60 for C).
    
  - scale_type: The name of the scale to use. MIDImod includes over 80 predefined scales, from major and minor to dorian, phrygian_dominant, and pentatonic_blues.
    
  

##### The chord() Function

The chord() function is a powerful tool for generating multiple notes from a single trigger. It can be used in value_1_out to create chords, layers, or complex harmonies.

**Syntax:** chord(root, num_notes, scale_or_intervals)

- root: The base MIDI note number for the chord.
  
- num_notes: The number of notes to generate.
  
- scale_or_intervals: Can be either:
  
  - A string with the name of a scale (e.g., "major", "minor_pentatonic"). The function will build a chord by stacking notes from this scale.
    
  - A list of integer intervals (e.g., [0, 4, 7]). The function will generate exactly those notes relative to the root.
    

**Example 1: Generating a C Major 7th chord**

This filter takes a single C4 note and transforms it into a full 4-note C-Major 7th chord.

```
"midi_filter": [{
    "device_in": "MyKeyboard",
    "event_in": "note_on",
    "value_1_in": 60,
    "device_out": "MyPads",
    "value_1_out": "chord(60, 4, 'maj7_chord')"
}]
```

- **Output:** Four note_on messages for notes 60, 64, 67, and 71.

**Example 2: Creating a thick, layered synth stab**

This uses a custom list of intervals to create a specific voicing.

```
"midi_filter": [{
    "device_in": "MyPads",
    "event_in": "note_on",
    "value_1_in": 36,
    "device_out": "MySynth",
    "value_1_out": "chord(value_1, 5, [0, 7, 12, 19, 24])"
}]
```

- **Output:** Five note_on messages: the original note, a fifth above, one octave up, a fifth above that, and two octaves up.

When value_1_out evaluates to a list of notes (like the output of chord()), MIDImod automatically sends a separate MIDI message for each note in the list.




### MIDI Filters: The Core Logic

The "midi_filter" list is the heart of MIDImod. Each object in this list is a rule that listens for specific MIDI messages. If an incoming message matches all the conditions of a filter, it triggers one or more output actions.

**To create a filter, add an object to the "midi_filter" list:**

```
"midi_filter": [
    {
        "_comment": "A descriptive name for your rule",
        "version": 0,
        "device_in": "MyKeyboard",
        "ch_in": 1,
        "event_in": "note_on",
        "value_1_in": "36-72",

        "output": [
            {
                "device_out": "MySynth",
                "value_1_out": "value_1_in + 12"
            }
        ]
    }
]
```

A filter is composed of two main parts: **Input Conditions** (the "if" part of the rule) and **Output Actions** (the "then" part).

### Input Conditions

These keys define what MIDI messages the filter will "catch". A message must match all specified conditions to trigger the filter.

- "_comment" (String): An optional description of what the rule does.
  
- "version" (Integer or List of Integers): The rule is only active if the global current_active_version matches this value (or is in the list). If omitted, the rule is active in all versions.
  
- "device_in" (String): The device_alias of the MIDI input port. This is required for any filter that should react to hardware or virtual MIDI messages.
  
- "ch_in" (Integer or String): Filters by MIDI channel (1-16). You can use a single number, a list ([1, 2, 5]), or a range as a string ("1-8").
  
- "event_in" (String or List of Strings): Filters by the type of MIDI message.
  
  - Common values: "note_on", "note_off", "note" (matches both), "cc" (for control_change), "pc" (for program_change), "pitchwheel", "aftertouch".
- "value_1_in" (Integer or String): Filters by the first MIDI value.
  
  - For notes, this is the note number (0-127).
    
  - For CCs, this is the CC number (0-127).
    
  - For PCs, this is the program number (0-127).
    
  - Can be a single number, a list, or a range string ("60-72").
    
- "value_2_in" (Integer or String): Filters by the second MIDI value.
  
  - For notes, this is the velocity (0-127).
    
  - For CCs, this is the CC value (0-127).
    
- "if" (String Expression): For complex conditions that cannot be expressed with the keys above.
  
  Imagine you want to add a sub-bass layer to your main synth sound, but only when you've activated a special "sub mode" and are playing in the lower register of the keyboard.
  
  - The first filter sends all notes from your keyboard to your main synth channel, as usual.
    
  - The second filter also listens to your keyboard, but it has a condition: "if": "sub_mode == 1 and value_1 >= 48". This means it will only trigger if:
    
    1. The sub_mode variable has been set to 1.
      
    2. The incoming note (value_1) is C3 (note 48) or higher.
      
  - When both conditions are met, it sends a second note to channel 2, pitched one octave lower.
    
  - The third filter allows you to toggle the sub_mode variable on and off using a button on your controller.
    
  
  ```
  "user_variables": {
      "sub_mode": 0
  },
  "midi_filter": [
      {
          "_comment": "Notes from Keyboard to Synth on ch1, always active",
          "device_in": "MyKeyboard",
          "event_in": "note",
          "device_out": "MySynth"
      },
      {
          "_comment": "Sub-bass layer on ch2, activated by sub_mode and higher notes",
          "device_in": "MyKeyboard",
          "event_in": "note",
          "if": "sub_mode == 1 and value_1 >= 48",
          "output": [{
              "device_out": "MySynth",
              "channel_out": 2,
              "value_1_out": "value_1 - 12"
          }]
      },
      {
          "_comment": "A controller button to toggle the sub_mode on and off",
          "device_in": "MyController",
          "event_in": "note_on",
          "value_1_in": 48,
          "output": [{
              "sub_mode": "toggle(sub_mode)"
          }]
      }
  ]
  ```
  

### Output Actions

If a message matches the input conditions, the filter executes the actions defined in the "output" list. Each object in the list is a separate action.

**Key Output Parameters:**

- "device_out" (String): The device_alias of the MIDI output port for this specific action.
  
- "channel_out" (Integer or Expression): Sets the MIDI channel for the outgoing message. If omitted, the original channel is used.
  
- "event_out" (String): Transforms the message type (e.g., "note_on" can become "pc").
  
- "value_1_out" & "value_2_out" (Integer or Expression): Define the values for the outgoing message. They can be a fixed number or a dynamic expression.
  
- "set_version" (Integer or String Expression): Changes the global current_active_version. Can be a number or a string like "cycle" to advance to the next available version.
  
- **Variable Assignment:** You can assign a value to any variable defined in "user_variables" by using its name as a key (e.g., "my_var": "value_2_in * 2"). If the output block contains only variable assignments and no device_out, no MIDI message will be sent.
  

**Context Variables for Expressions:**

When writing expressions for output parameters, you have access to these context variables from the original message:

- value_1_in, value_2_in: The primary and secondary values of the incoming MIDI message.
  
- channel_in: The channel of the incoming message (1-16).
  
- event_in: The type of the incoming message as a string.
  
- delta_in: For CCs, this holds the amount of change from the last value, useful for relative encoder logic.
  
- ...user_variables: Any variable you have defined in the user_variables section is directly accessible by its name (e.g., global_transpose).
  

**Variable Aliases**

For convenience and readability in your expressions, MIDImod provides several shorter aliases for the main context variables. You can use the long name or the short name interchangeably.

- **For ch0_in_ctx (the incoming channel index, 0-15):**
  
  - channel_in
    
  - ch_in
    
  - channel
    
- **For value_in_1_ctx (the first MIDI value):**
  
  - value_1_in
    
  - value_1
    
- **For value_in_2_ctx (the second MIDI value):**
  
  - value_2_in
    
  - value_2
    
- **For event_type_in_ctx (the event type string):**
  
  - event_in
    
  - event
    

**Example:**

These two expressions are identical and will produce the same result:

- "value_1_out": "value_in_1 + 12"
  
- "value_1_out": "value_1 + 12"
  

#### Shortcut Syntax

For more concise rules, MIDImod supports a special shortcut syntax that combines event type and value conditions into a single key. This is particularly useful for simple, direct filters.

**General Format:** event_type(value_1)

- **note_on(60)**: This key is a shortcut for "event_in": "note_on" and "value_1_in": 60.
  
- **cc(22)**: This is a shortcut for "event_in": "cc" and "value_1_in": 22.
  
- **pc(5)**: This is a shortcut for "event_in": "pc" and "value_1_in": 5.
  

This syntax can be used for both **input conditions** and **output actions**.

**Example: Rewriting a "Note to PC" filter with shortcuts:**

```
// Standard Syntax
{
    "device_in": "MyKeyboard",
    "event_in": "note_on",
    "value_1_in": 60,
    "output": [{ "device_out": "MySynth", "event_out": "pc", "value_1_out": 5 }]
}

// Shortcut Syntax
{
    "device_in": "MyKeyboard",
    "note_on(60)": {
        "device_out": "MySynth",
        "pc(5)": null
    }
}
```

- In the shortcut version, "note_on(60)" defines the input trigger. The value of that key is a dictionary defining the output actions.
  
- Inside the output dictionary, "pc(5)": null defines the outgoing message. The null is used because no further parameters (like velocity) are needed for a Program Change.
  

**Note on null vs. Expressions:**

When using shortcut syntax for an output action, the value of the key determines the second MIDI parameter.

- Use null when no second parameter is needed. This is typical for Program Change or transport messages.
  
  ```
  "pc(5)": null
  "start()": null
  ```
  
- Provide an expression or a number when a second parameter is required. This is typical for Control Change messages, where you need to specify the CC's value.
  
  ```
  // Sends CC #22 with the same value that came in
  "cc(22)": "value_2_in"
  
  // Sends CC #22 with a fixed value of 127
  "cc(22)": 127
  ```



## Simple Rule File Examples



**For a comprehensive list of practical examples, please see the [EXAMPLES.md](EXAMPLES.md) file.**


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


---

**1. connect_keyboard_to_synth.json** (Direct Connection)  
Purpose: Everything from MyKeyboard goes to MySynth.

```
{
    "device_alias": { "MyKeyboard": "KB_NAME", "MySynth": "SYNTH_NAME" },
    "midi_filter": [
        {
            "device_in": "MyKeyboard",
            "device_out": "MySynth"
        }
    ]
}
```

---

**2. change_keyboard_channel.json**  
Purpose: MyKeyboard channel 1 (ch_in: 1) output to MySynth channel 5 (channel_out: 4).

```
{
    "device_alias": { 
        "MyKeyboard": "YourKeyboardName", 
        "MySynth": "YourSynthName" 
    },
    "midi_filter": [
        {
            "device_in": "MyKeyboard", 
            "ch_in": 1,
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
    "midi_filter": [
        {
            "device_in": "MyKeyboard", 
            "ch_in": 1, 
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
    "midi_filter": [
        {
            "device_in": "MyController", 
            "ch_in": 1, "event_in": "cc", 
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
    "midi_filter": [
        {
            "device_in": "MyKeyboard", 
            "ch_in": 1, 
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

## Contributions

This code has been written by an amateur musician AND coder. I use MIDImod on a headless Raspberry-Pi, which powers my controllers and reroutes/transforms the MIDI; it seems to work. I am very open to suggestions, comments & bug reports. You can open an "Issue" on GitHub.

## License

under [GNU AGPLv3](https://www.gnu.org/licenses/agpl-3.0.html) license
