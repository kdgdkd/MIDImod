# MIDImod Rule File Examples

This document provides detailed examples of how to create rule files for MIDImod. For a general overview, please refer to the main README.md.

## Basic Structure of a Rule File

A rule file is a JSON document located in the rules/ folder (or live/ for Live Mode). It contains a single JSON object with different sections that define MIDImod's behavior.



```
{
    "device_alias": {
        "MyKeyboard": "Your Keyboard Name",
        "MyController": "Your Controller Name",
        "MySynth": "Your Synth Name"
    },
    "midi_filter": [
        {
            "_comment": "Rule 1: Send notes from keyboard to synth",
            "device_in": "MyKeyboard",
            "event_in": "note",
            "device_out": "MySynth"
        },
        {
            "_comment": "Rule 2: Send CCs from controller to synth",
            "device_in": "MyController",
            "event_in": "cc",
            "device_out": "MySynth"
        }
    ]
}
```



## Key Sections

- "device_alias": (Optional but highly recommended) Create easy-to-remember names for your MIDI devices. They may be substrings of the actual port name. Using aliases also allows to replace one MIDI keyboard by another with a single change in this section, for example.
  
- "user_variables": (Optional) Define global variables you can use in any expression.
  
- "midi_filter": (List) The main MIDI processing rules. Each object in this list is a filter that listens for specific MIDI events.
  
- "sequencer": (List) Define one or more pattern-based sequencers.
  
- "arpeggiator": (List) Define templates for the arpeggiator modules.
  
- "osc_filter": (List) Define rules that react to incoming OSC messages.
  

## MIDI Filter Examples

A midi_filter listens for messages and triggers one or more outputs if the conditions match.

### 1. Simple Device Connection

**Goal:** Route everything from MyKeyboard to MySynth.



```
{
    "device_alias": { "MyKeyboard": "KeyStep", "MySynth": "Crave" },
    "midi_filter": [
        {
            "device_in": "MyKeyboard",
            "device_out": "MySynth"
        }
    ]
}
```



- Any MIDI message from the device containing "KeyStep" in its name will be sent to the device containing "Crave".

### 2. Channel Remapping

**Goal:** Messages on MyKeyboard's channel 1 are sent to MySynth on channel 5.



```
{
    "device_alias": { "MyKeyboard": "KeyStep", "MySynth": "Crave" },
    "midi_filter": [
        {
            "device_in": "MyKeyboard",
            "ch_in": 1,
            "device_out": "MySynth",
            "channel_out": 5
        }
    ]
}
```



- ch_in and channel_out use 1-based numbering (1-16).

### 3. Note Transposition

**Goal:** Transpose notes from MyKeyboard up by one octave.



```
{
    "device_alias": { "MyKeyboard": "KeyStep", "MySynth": "Crave" },
    "midi_filter": [
        {
            "device_in": "MyKeyboard",
            "event_in": "note",
            "device_out": "MySynth",
            "value_1_out": "value_1_in + 12"
        }
    ]
}
```



- event_in: "note" matches both note_on and note_off.
  
- value_1_in holds the incoming note number. The expression adds 12 to it.
  

### 4. Creating a Layer

**Goal:** A single note press plays the original note on channel 1 and a lower octave on channel 2.



```
{
    "device_alias": { "MyKeyboard": "KeyStep", "MySynth": "Crave" },
    "midi_filter": [
        {
            "device_in": "MyKeyboard",
            "event_in": "note",
            "output": [
                {
                    "_comment": "Original note on channel 1",
                    "device_out": "MySynth",
                    "channel_out": 1
                },
                {
                    "_comment": "Lower octave on channel 2",
                    "device_out": "MySynth",
                    "channel_out": 2,
                    "value_1_out": "value_1_in - 12"
                }
            ]
        }
    ]
}
```



- The "output" list allows a single input to trigger multiple actions.

### 5. CC Knob Remapping

**Goal:** Remap CC #20 from a controller to control CC #74 (Filter Cutoff) on a synth.



```
{
    "device_alias": { "MyController": "BCR2000", "MySynth": "Crave" },
    "midi_filter": [
        {
            "device_in": "MyController",
            "event_in": "cc",
            "value_1_in": 20,
            "device_out": "MySynth",
            "value_1_out": 74
        }
    ]
}
```



- For CC messages, value_1_in is the CC number and value_2_in is the CC value.
  
- Since value_2_out is not specified, the original CC value is passed through.
  

### 6. Change Type of MIDI events: Note to Program Change

**Goal:** Use a specific key (C4, note 60) to send Program Change #5.



```
{
    "device_alias": { "MyKeyboard": "KeyStep", "MySynth": "Crave" },
    "midi_filter": [
        {
            "device_in": "MyKeyboard",
            "event_in": "note_on",
            "value_1_in": 60,
            "device_out": "MySynth",
            "event_out": "pc",
            "value_1_out": 5
        }
    ]
}
```



- event_out: "pc" converts the event type.
  
- For a Program Change, value_1_out specifies the program number.
  

## Advanced Examples

### 7. Using Versions for Different Setups

**Goal:** Use two notes on a controller to switch between two "versions". Version 0 is a simple layer, and Version 1 is a C-Major scale quantizer.



```
{
    "device_alias": { "MyKeyboard": "Key", "MyController": "Ctrl", "MySynth": "Synth" },
    "midi_filter": [
        {
            "_comment": "Version switching logic",
            "device_in": "MyController",
            "event_in": "note_on",
            "value_1_in": 36,
            "set_version": 0
        },
        {
            "device_in": "MyController",
            "event_in": "note_on",
            "value_1_in": 37,
            "set_version": 1
        },
        {
            "_comment": "Version 0: Layering (all notes from MyKeyboard to MySynth on ch1, and one octave lower on ch2)",
            "version": 0,
            "device_in": "MyKeyboard",
            "event_in": "note",
            "output": [
                { "device_out": "MySynth", 
                "channel_out": 1 },
                { "device_out": "MySynth", 
                "channel_out": 2, 
                "value_1_out": "value_1_in - 12" }
            ]
        },
        {
            "_comment": "Version 1: Scale Quantizer (all notes from MyKeyboard are filtered to C major scale and sent to MySynth)",
            "version": 1,
            "device_in": "MyKeyboard",
            "event_in": "note",
            "device_out": "MySynth",
            "value_1_out": {
                "scale_notes": {
                    "scale_value": "value_1_in",
                    "scale_root": 48,
                    "scale_type": "major"
                }
            }
        }
    ]
}
```



- set_version changes the global current_active_version.
  
- The version key in a filter makes it active only when the global version matches.
  

### 8. Using User Variables

**Goal:** Use one knob (CC #21) to set a rate variable, and then use that variable to affect the output of another knob (CC #22).



```
{
    "device_alias": {
        "MyController": "BCR2000",
        "MyKeyboard": "BeatStep",
        "MySynth": "Crave"
    },
    "user_variables": {
        "global_transpose": 0
    },
    "midi_filter": [
        {
            "_comment": "Notes from BeatStep are transposed by 'global_transpose'",
            "device_in": "MyKeyboard",
            "event_in": "note",
            "device_out": "MySynth",
            "value_1_out": "value_1_in + global_transpose"
        },
        {
            "_comment": "Knob (CC 21) on Controller sets the transposition value directly.",
            "_comment_details": "We scale the 0-127 input to a -12 to +12 semitone range.",
            "device_in": "MyController",
            "event_in": "cc",
            "value_1_in": 21,
            "output": [{
                "global_transpose": {
                    "scale_value": "value_2_in",
                    "range_in": [0, 127],
                    "range_out": [-12, 12]
                }
            }]
        },
        {
            "_comment": "Note 20 on Controller shifts transposition down one octave.",
            "device_in": "MyController",
            "event_in": "note_on",
            "value_1_in": 20,
            "output": [{
                "global_transpose": "global_transpose - 12"
            }]
        },
        {
            "_comment": "Note 21 on Controller shifts transposition up one octave.",
            "device_in": "MyController",
            "event_in": "note_on",
            "value_1_in": 21,
            "output": [{
                "global_transpose": "global_transpose + 12"
            }]
        }
    ]
}
```



- The first filter has no device_out, so it only performs the variable assignment.
  
- The second filter reads the global rate variable in its value_2_out expression.
  

## Sequencer & Arpeggiator Examples

### 9. A Basic Sequencer

**Goal:** A 16-step bassline that plays when a MIDI clock is received.



```
{
    "device_alias": {
        "Clock": "CLOCK",
        "BassSynth": "MIDImod_OUT"
    },
    "sequencer": [
        {
            "seq_id": "bass_1",
            "clock_in": "Clock",
            "step_total": 16,
            "step_duration": "1/16",
            "seq_root_note": 48,
            "seq_transpose": [0, 0, 3, 0, 5, 0, 7, 0, 8, 0, 10, 0, 12, 0, 12, 0]
            "output": [{
                "device_out": "BassSynth",
                "channel_out": 1,
                "value_1_out": "root_note_out + transpose_out"
            }]
        }
    ]
}
```



- seq_id is optional, but crucial for live reloading to work without interrupting the sequence.
  
- The output Block and Context Variables: The output block is where you explicitly define how the final MIDI message is constructed *for each step*. 

  For each step, MIDImod takes the values from the seq arrays and makes them available inside the output expression:
    - root_note_out is the value of seq_root_note for the current step
    - transpose_out is the value of seq_transpose for the current step
    - velocity_out is the value of seq_velocity for the current step
    - gate_out is the value of seq_gate for the current step
    - ...and so on for all seq_ arrays.

In this example, the expression "value_1_out": "root_note_out + transpose_out" instructs MIDImod to take the root note for the current step, add the transposition value for that same step, and use the result as the final MIDI note number. You could include mathematical operations, user_variables, ranges of values... 

This mechanism gives you complete control over how the sequence data is interpreted.
  

### 10. A Dynamic Arpeggiator

**Goal:** When notes are played on MyKeyboard, trigger an arpeggiator that sends notes to MySynth.

```
{
    "device_alias": {
        "MyKeyboard": "KeyStep",
        "MySynth": "Crave"
    },
    "arpeggiator": [
        {
            "arp_id": 1,
            "device_out": "MySynth",
            "arp_mode": "updown",
            "step_duration": "1/16",
            "arp_octaves": 2
        }
    ],
    "midi_filter": [
        {
            "_comment": "This filter sends notes to Arpeggiator #1",
            "device_in": "MyKeyboard",
            "event_in": "note",
            "arp_id": 1
        }
    ]
}
```


**How it Works:**

An arpeggiator is a sequencer with a structure (nuber of steps, notes per step) that is defined by the keys that are played. This setup demonstrates the powerful interaction between a standard midi_filter and an arpeggiator module. They work together in two stages:

**The arpeggiator (arp engine)**: 
- This block defines a reusable arpeggiator "template" with a unique arp_id (in this case, 1).  
- It sets the core behavior of the arpeggiator: where its notes should go (device_out), its pattern (arp_mode), its speed (step_duration), and its range (arp_octaves).  
- This block itself does not listen for MIDI. It's an engine waiting to be activated.  

**The midi_filter (arp trigger)**:
- This is a standard filter that listens for incoming note events from MyKeyboard.  
- The key is the "arp_id": 1 line. Instead of generating a direct MIDI output, this command tells MIDImod: "Take the note that this filter just caught and send it to the input of the arpeggiator with ID #1."  
- When you press one or more keys, this filter continuously updates the list of notes that the arpeggiator engine will use to generate its pattern. When you release the keys, the arpeggiator stops (unless arp_latch is set to true in its template).  

This separation is very powerful: you can have multiple filters feeding notes into the same arpeggiator, or use a single controller to dynamically change the parameters of an arpeggiator template while it's running.



## Live Mode Example: On-the-Fly Sequence Modification

The --live mode is designed for real-time performance. It watches your rule files and instantly applies any changes you save, without ever stopping the music. This allows you to "conduct" your arrangement by editing a simple text file.

Let's use this example file, saved as live/my_performance.json:



```
{
  "device_alias": {
    "reloj_maestro": "CLOCK",
    "sinte_bajo": "MIDImod_OUT"
  },
  "sequencer": [
    {
      "seq_id": "b1",
      "clock_in": "reloj_maestro",
      "device_out": "sinte_bajo",
      "step_duration": "1/16",
      "seq_root_note": 48,
      "seq_transpose": [
        7,  0,  0,  0, 
        7,  5,  0,  0, 
        7,  0,  0,  0, 
        7,  0,  0,  0
      ],
      "output": [{ "value_1_out": "root_note_out + transpose_out" }]
    }
  ]
}
```


**Performance Workflow:**

1. **Start MIDImod in Live Mode:**  
  Open your terminal and run:
  
  
  ```
  python midimod.py --live
  ```

  
  MIDImod will load the my_performance.json file.
  
2. **Start Your Master Clock:**  
  Press play in your DAW or hardware sequencer. MIDImod will receive the MIDI clock and the "b1" sequencer will start playing its pattern: (E, C, C, C), (E, G, C, C), ...
  
3. **Open the File:**  
  In a text editor (like VS Code, Sublime Text, etc.), open live/my_performance.json.
  
4. **Modify the Sequence in Real Time:**  
  While the bassline is playing, change the seq_transpose array to create a new melodic variation. For example, let's make it more tense:
  
  
  ```
  "seq_transpose": [
     7,  0,  0,  0, 
     7,  5,  0,  0, 
     8,  0,  0,  0,  // Changed from 7
     8,  0,  0,  0   // Changed from 7
   ],
  ```
  
  
5. **Save the File:**  
  Simply press Ctrl+S in your editor.
  

**What Happens Next:**

- The moment you save, MIDImod's console will show: [*] Fichero de reglas modificado: my_performance.json. Recargando...
  
- The "b1" sequencer **will not stop**. It will finish its current 16-step loop.
  
- On the very next beat after the loop completes, it will start playing the **new pattern** you just saved: (E, C, C, C), (E, G, C, C), (F, C, C, C), (F, C, C, C), ...
  

Because the seq_id ("b1") is present, MIDImod knows to preserve the running state of the sequencer, applying the new configuration seamlessly. This allows you to build and evolve your musical ideas live, using a simple text file as your arrangement tool.