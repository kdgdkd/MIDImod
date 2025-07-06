# midimod.py
import mido
import time
import json
import argparse
import traceback
import json5 
import signal
import os
from pathlib import Path
import sys
import random
import re 
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from queue import Queue
import threading
import html

# --- OSC Imports ---
from pythonosc import dispatcher, osc_server, udp_client

# --- UI Imports ---
from prompt_toolkit import Application
from prompt_toolkit.layout.containers import HSplit, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.formatted_text import HTML


# --- Global Configuration ---
RULES_DIR_NAME = "rules" 
RULES_DIR = Path(f"./{RULES_DIR_NAME}")
LIVE_RULES_DIR = Path("./live")
shutdown_flag = False
current_active_version = 0
available_versions = {0} 
monitor_active = True 
global_device_aliases = {} 
cc_value_sent = {}
cc_value_control = {}
cc_input_s_state = {}

# --- OSC Globals ---
osc_config = {}
osc_send_clients = {}
osc_server_thread = None
osc_server_instance = None
osc_message_queue = Queue()
all_loaded_osc_filters = []


active_note_map = {}
user_variables = {}      
channel_arrays = {}      
sequencers_state = [] 
persisted_sequencer_states = {}
arpeggiator_templates = {}
arpeggiator_instances = {}
clock_tick_counters = {} 
user_ordered_scale_names = []
clock_tick_counters = {}
user_ordered_scale_names = []


DEFAULT_NOTE_DURATIONS = [
    "1/64", "1/32", "1/16t", "1/16", "1/8t", "1/8", "1/4t", "1/4", "1/2t", "1/2", "1", "1.5", "2", "3", "4"
]
user_ordered_duration_names = []

transport_out_port_obj = None 
midimaster_assumed_status = "STOPPED"
VERBOSE_MODE = False

# --- Constantes para la activación por versión ---
DUMMY_MSG_FOR_VERSION_TRIGGER = mido.Message('note_on', channel=0, note=0, velocity=0) 
DUMMY_PORT_NAME_FOR_VERSION_TRIGGER = "_VERSION_TRIGGER_INTERNAL_"

SEQ_DEFAULTS = {
    "ppqn": 24,
    "step_total": 16,
    "step_duration": "1/16",
    "swing": 0.0,
    "shift_global": 0.0,
    "shift_array": [0.0] * 16, # Se ajustará al tamaño real luego
    "seq_transpose": 0,
    "seq_root_note": 48,
    "seq_active": 1,
    "seq_gate": 1,
    "seq_mute": 0,
    "seq_velocity": 100,
    "seq_probability": 1.0,
    "seq_note_length": 0.9,
    "seq_step_direction": 1, 
    "seq_note": 60,
    "seq_cc_number": 0, 
    "seq_cc_value": 0 
}


ARP_MODES_LIST = [
    "as_played", "sorted", "outside_in", "random1", "random2",
    "first_note_repeat", "stutter", "stutter4", "stutter8", "stutter16"
]


ARP_STEP_DIRECTIONS = [
    "up", "down", "updown", "updown_inclusive", "random_walk", "random_jump"
]

ARP_DEFAULTS = {
    "arp_mode": "sorted",
    "arp_step_direction": "up", 
    "arp_octaves": 1,
    "arp_octave_mode": "up",
    "arp_latch": False,
    "ppqn": 24,
    "step_duration": "1/16",
    "arp_gate": 1,
    "arp_mute": 0,
    "arp_velocity": 100,
    "arp_probability": 1.0,
    "arp_note_length": 0.9
}


CC_SENT_UNINITIALIZED = -1

PREDEFINED_SCALES = {
    "major": [0, 2, 4, 5, 7, 9, 11],
    "ionian": [0, 2, 4, 5, 7, 9, 11],
    "dorian": [0, 2, 3, 5, 7, 9, 10],
    "phrygian": [0, 1, 3, 5, 7, 8, 10],
    "lydian": [0, 2, 4, 6, 7, 9, 11],
    "mixolydian": [0, 2, 4, 5, 7, 9, 10],
    "aeolian": [0, 2, 3, 5, 7, 8, 10],
    "minor_natural": [0, 2, 3, 5, 7, 8, 10],
    "locrian": [0, 1, 3, 5, 6, 8, 10],
    
    # --- Minor Scales ---
    "minor_harmonic": [0, 2, 3, 5, 7, 8, 11],
    "minor_melodic_asc": [0, 2, 3, 5, 7, 9, 11],
    
    # --- Pentatonic Scales ---
    "pentatonic_major": [0, 2, 4, 7, 9],
    "pentatonic_minor": [0, 3, 5, 7, 10],
    "pentatonic_blues": [0, 3, 5, 6, 7, 10],
    "pentatonic_neutral": [0, 2, 5, 7, 10],

    # --- Symmetrical Scales ---
    "chromatic": list(range(12)),
    "whole_tone": [0, 2, 4, 6, 8, 10],
    "diminished_hw": [0, 1, 3, 4, 6, 7, 9, 10], # Half-Whole
    "diminished_wh": [0, 2, 3, 5, 6, 8, 9, 11], # Whole-Half

    # --- Bebop Scales ---
    "bebop_major": [0, 2, 4, 5, 7, 8, 9, 11],
    "bebop_dorian": [0, 2, 3, 5, 7, 9, 10, 11],
    "bebop_dominant": [0, 2, 4, 5, 7, 9, 10, 11],

    # --- "Exotic" / World Scales ---
    "spanish_gypsy": [0, 1, 4, 5, 7, 8, 11],
    "phrygian_dominant": [0, 1, 4, 5, 7, 8, 10],
    "hungarian_minor": [0, 2, 3, 6, 7, 8, 11],
    "double_harmonic": [0, 1, 4, 5, 7, 8, 11],
    "hirajoshi": [0, 2, 3, 7, 8],
    "in-sen": [0, 1, 5, 7, 10],
    "iwato": [0, 1, 5, 6, 10],
    "kumoi": [0, 2, 3, 7, 9],

    # --- Simple Chords (as "scales") ---
    "major_triad": [0, 4, 7],
    "minor_triad": [0, 3, 7],
    "dim_triad": [0, 3, 6],
    "aug_triad": [0, 4, 8],
    "dom7_chord": [0, 4, 7, 10],
    "maj7_chord": [0, 4, 7, 11],
    "min7_chord": [0, 3, 7, 10],
}
active_scales = PREDEFINED_SCALES.copy()

def clear_reloadable_state():
    """Limpia solo las variables de estado que se recargan desde los ficheros."""
    global global_device_aliases, all_loaded_filters, user_variables, sequencers_state
    global arpeggiator_templates, full_json_contents, active_scales
    global user_ordered_scale_names, user_ordered_duration_names

    global_device_aliases = {}
    all_loaded_filters = []
    all_loaded_osc_filters = []
    user_variables = {}
    sequencers_state = []
    arpeggiator_templates = {}
    full_json_contents = []
    active_scales = PREDEFINED_SCALES.copy()
    user_ordered_scale_names = []
    user_ordered_duration_names = []

# Renombrar y expandir la función para inicializar todo el estado global
def initialize_state():
    """Inicializa todas las variables de estado globales a sus valores por defecto."""
    global cc_value_sent, cc_value_control, cc_input_s_state, active_note_map
    global user_variables, channel_arrays, sequencers_state, arpeggiator_templates
    global arpeggiator_instances, clock_tick_counters, user_ordered_scale_names
    global user_ordered_duration_names, midimaster_assumed_status, opened_ports_tracking
    global active_input_handlers, all_loaded_filters, full_json_contents, global_device_aliases
    
    # Estados de CC
    cc_value_sent = {}
    cc_value_control = {}
    cc_input_s_state = {}
    for ch in range(16):
        for cc_num in range(128):
            cc_value_sent[(ch, cc_num)] = CC_SENT_UNINITIALIZED
            cc_value_control[(ch, cc_num)] = 0
            cc_input_s_state[(ch, cc_num)] = CC_SENT_UNINITIALIZED

    # Estados de Módulos y Procesamiento
    active_note_map = {}
    user_variables = {}
    channel_arrays = {}
    sequencers_state = []
    arpeggiator_templates = {}
    arpeggiator_instances = {}
    clock_tick_counters = {}
    
    # Listas de configuración de usuario
    user_ordered_scale_names = []
    user_ordered_duration_names = []

    # Estado de Transporte
    midimaster_assumed_status = "STOPPED"

    # Estructuras de Configuración Cargadas
    global_device_aliases = {}
    all_loaded_filters = []
    full_json_contents = []
    active_scales = PREDEFINED_SCALES.copy()

    # Manejo de Puertos
    opened_ports_tracking = {}
    active_input_handlers = {}


# --- Non-Blocking Character Input ---
try:
    import msvcrt
    def get_char_non_blocking():
        if msvcrt.kbhit():
            try: return msvcrt.getch().decode(errors='ignore')
            except UnicodeDecodeError: return None
        return None
except ImportError:
    import tty, termios, select
    _original_termios_settings_fd = -1; _original_termios_settings = None
    def get_char_non_blocking():
        global _original_termios_settings_fd, _original_termios_settings
        fd = sys.stdin.fileno()
        if not sys.stdin.isatty(): return None
        if _original_termios_settings_fd != fd:
            try: _original_termios_settings = termios.tcgetattr(fd); _original_termios_settings_fd = fd
            except termios.error: return None
        # current_settings = termios.tcgetattr(fd) # No se usa, se puede comentar
        try:
            tty.setraw(fd)
            if select.select([sys.stdin], [], [], 0.0)[0]: return sys.stdin.read(1)
        except Exception: pass
        finally:
            if _original_termios_settings and _original_termios_settings_fd == fd :
                try: termios.tcsetattr(fd, termios.TCSADRAIN, _original_termios_settings)
                except termios.error: pass
        return None



def verbose_print(*args, **kwargs):
    if VERBOSE_MODE:
        print(*args, **kwargs)


# --- Helper Functions ---

# --- Watchdog Event Handler for Live Reload ---
class RuleChangeHandler(FileSystemEventHandler):
    def __init__(self, reload_queue):
        self.queue = reload_queue
        self.last_event_time = 0
        self.debounce_period = 0.5 # 500 ms

    def on_modified(self, event):
        current_time = time.time()
        if not event.is_directory and event.src_path.endswith('.json'):
            # Debounce para evitar múltiples recargas por un solo guardado
            if (current_time - self.last_event_time) > self.debounce_period:
                print(f"[*] Fichero de reglas modificado: {os.path.basename(event.src_path)}. Recargando...")
                self.queue.put("reload")
                self.last_event_time = current_time

def parse_step_duration(duration_input, ppqn):
    # Primero, manejar tipos numéricos directamente.
    if isinstance(duration_input, int):
        return duration_input  # Se asume que ya son ticks.
    
    base_ppqn = ppqn * 4  # Ticks en una nota redonda.

    if isinstance(duration_input, float):
        # Si es un float, es un multiplicador de una redonda.
        ticks = base_ppqn * duration_input
        return int(round(ticks))

    # Si no es un número, debe ser un string para parsear.
    if not isinstance(duration_input, str):
        return int(ppqn / 4)  # Fallback para tipos no soportados.

    duration_str = duration_input.lower().strip()
    multiplier = 1.0

    # Comprobar si es una tripleta (termina en 't')
    if duration_str.endswith('t'):
        multiplier = 2.0 / 3.0
        duration_str = duration_str[:-1]

    # Comprobar si es una fracción del tipo "numerador/denominador"
    match = re.match(r"(\d+)/(\d+)", duration_str)
    if match:
        try:
            num, den = int(match.group(1)), int(match.group(2))
            if den == 0:
                return int(ppqn / 4)  # Fallback
            ticks = (base_ppqn / den) * num * multiplier
            return int(round(ticks))
        except (ValueError, TypeError):
            return int(ppqn / 4)  # Fallback

    # Comprobar si es un número (entero o decimal) en formato string.
    try:
        value = float(duration_str)
        ticks = base_ppqn * value * multiplier
        return int(round(ticks))
    except (ValueError, TypeError):
        pass

    # Fallback final para cualquier otro formato no reconocido.
    return int(ppqn / 4)


def import_from_midi_file(filepath, quantize_grid_str, ppqn, step_total_from_config, track_index_from_config=None, start_step_from_config=0):
    try:
        mid = mido.MidiFile(filepath, clip=True)
    except FileNotFoundError:
        print(f"  [!] ADVERTENCIA SEQ: Archivo MIDI '{filepath}' no encontrado.")
        return None
    except Exception as e:
        print(f"  [!] ERROR SEQ: No se pudo leer el archivo MIDI '{filepath}': {e}")
        return None
        
    print(f"  - Importando datos de '{filepath}'...")
    
    ticks_per_step = parse_step_duration(quantize_grid_str, ppqn)
    if ticks_per_step == 0: ticks_per_step = 1

    track_to_process = None
    if track_index_from_config is not None and isinstance(track_index_from_config, int):
        if 0 <= track_index_from_config < len(mid.tracks):
            track_to_process = mid.tracks[track_index_from_config]
            print(f"    - Usando la pista especificada por el usuario (Pista {track_index_from_config}).")
        else:
            print(f"    [!] ADVERTENCIA SEQ: El índice de pista '{track_index_from_config}' está fuera de rango. Buscando la primera pista con notas.")

    if not track_to_process:
        for i, track in enumerate(mid.tracks):
            if any(msg.is_meta is False and 'note' in msg.type for msg in track):
                track_to_process = track
                print(f"    - Usando la primera pista con notas (Pista {i}).")
                break
    
    if not track_to_process: return None

    notes_on = {}
    imported_events = []
    current_tick = 0
    for msg in track_to_process:
        current_tick += msg.time
        if msg.type == 'note_on' and msg.velocity > 0:
            notes_on[(msg.channel, msg.note)] = current_tick
        elif msg.type == 'note_off' or (msg.type == 'note_on' and msg.velocity == 0):
            key = (msg.channel, msg.note)
            if key in notes_on:
                start_tick = notes_on.pop(key)
                duration_ticks = current_tick - start_tick
                imported_events.append( (start_tick, msg.note, msg.velocity, duration_ticks) )

    if not imported_events: return None

    # Usamos el total_steps de la configuración, no lo calculamos del fichero
    total_steps = step_total_from_config

    imported_arrays = {
        'seq_note': [SEQ_DEFAULTS['seq_note']] * total_steps,
        'seq_velocity': [SEQ_DEFAULTS['seq_velocity']] * total_steps,
        'seq_gate': [0] * total_steps,
        'seq_note_length': [SEQ_DEFAULTS['seq_note_length']] * total_steps
    }

    start_tick_offset = start_step_from_config * ticks_per_step

    for start_tick, note, velocity, duration_ticks in imported_events:
        if start_tick < start_tick_offset:
            continue
        step_index = int(start_tick / ticks_per_step)
        # Ignoramos cualquier nota que caiga fuera de nuestra secuencia de 16 pasos
        if step_index >= total_steps:
            continue
        
        imported_arrays['seq_note'][step_index] = note
        imported_arrays['seq_velocity'][step_index] = velocity
        imported_arrays['seq_gate'][step_index] = 1
        imported_arrays['seq_note_length'][step_index] = round(duration_ticks / ticks_per_step, 2)


        gate_sum = sum(imported_arrays['seq_gate'])
        verbose_print(f"    - Fichero importado: {gate_sum} notas encontradas en los primeros {total_steps} pasos.")
    
    # Ya no necesitamos devolver el total de pasos
    return imported_arrays




def load_sequencers(full_json_contents, device_aliases_map):
    global sequencers_state, user_variables # Añadir user_variables al global

    all_sequencer_configs = []
    for content in full_json_contents:
        if "sequencer" in content and isinstance(content["sequencer"], list):
            all_sequencer_configs.extend(content["sequencer"])

    if not all_sequencer_configs:
        verbose_print("No se encontró la sección 'sequencer' o no es una lista.")
        return

    print("\n--- Configuración de Secuenciadores ---")
    
    for i, seq_conf in enumerate(all_sequencer_configs):
        if not isinstance(seq_conf, dict): continue

        print(f"  - Cargando Secuenciador #{i}...")
        
        new_state = {
            'config': seq_conf, 'is_playing': False, 'tick_counter': 0, 
            'clock_in_port_name': None, 'arrays': {}, 'midi_file_data': {}, 'pending_note_offs': [],
            'is_armed': False,
            'event_schedule': [], 'schedule_needs_rebuild': True, 'last_known_tick': -1,
            'last_step_total': 0, 'last_ticks_per_step': 0
        }
        eval_context = {"version": current_active_version}

        clock_in_alias = seq_conf.get('device_in', seq_conf.get('clock_in'))
        if clock_in_alias:
            new_state['clock_in_port_name'] = device_aliases_map.get(clock_in_alias, clock_in_alias)
        
        ppqn = int(get_evaluated_value_from_output_config(seq_conf.get('ppqn'), SEQ_DEFAULTS['ppqn'], eval_context, f"SEQ{i}", "ppqn"))
        # Evaluate step_total for INITIAL array creation, but DO NOT overwrite the expression in seq_conf
        initial_num_steps = int(get_evaluated_value_from_output_config(seq_conf.get('step_total'), SEQ_DEFAULTS['step_total'], eval_context, f"SEQ{i}", "step_total"))

        # --- LÓGICA DE CARGA REFACTORIZADA (APLICADA A TU CÓDIGO) ---
        # 1. Poblar con los defaults del programa
        for key, value in SEQ_DEFAULTS.items():
            new_state['arrays'][key] = [value] * initial_num_steps

        # 1.5. Aplicar herencia de global_root_note si es necesario
        if 'global_root_note' in user_variables and 'seq_root_note' not in seq_conf:
            new_state['arrays']['seq_root_note'] = [user_variables['global_root_note']] * initial_num_steps
            if VERBOSE_MODE: print(f"    - SEQ{i} hereda 'global_root_note' ({user_variables['global_root_note']}).")

        # 2. Sobrescribir con cualquier array definido en el JSON
        for key, value in seq_conf.items():
            if key in new_state['arrays']:
                # Si el valor es una lista, la usamos para rellenar el array
                if isinstance(value, list):
                    if len(value) > 0:
                        new_state['arrays'][key] = (value + [value[-1]] * initial_num_steps)[:initial_num_steps]
                # Si no es una lista (es un valor único), lo aplicamos a todos los pasos
                elif value is not None:
                     new_state['arrays'][key] = [value] * initial_num_steps

        if 'shift_array' not in seq_conf:
             new_state['arrays']['shift_array'] = [SEQ_DEFAULTS['shift_array'][0]] * initial_num_steps


        # 3. Sobrescribir con datos del fichero MIDI (máxima prioridad)
        if "midi_file" in seq_conf and isinstance(seq_conf["midi_file"], list):
            if len(seq_conf["midi_file"]) > 0:
                mf_block = seq_conf["midi_file"][0]
                mf_path = mf_block.get("add_file")
                if mf_path:
                    track_index = mf_block.get("track_index")
                    start_step = mf_block.get("start_step", 0)
                    imported_data = import_from_midi_file(mf_path, mf_block.get("quantize", "1/16"), ppqn, initial_num_steps, track_index, start_step)
                    if imported_data:
                        new_state['midi_file_data'][0] = (imported_data, initial_num_steps)
                        # El fichero MIDI define la nota absoluta, no la raíz.
                        if 'seq_note' in imported_data:
                            new_state['arrays']['seq_note'] = imported_data['seq_note']
                            # Para el resto de arrays, los sobrescribimos
                            for array_name in ['seq_gate', 'seq_velocity', 'seq_note_length']:
                                if array_name in imported_data:
                                    new_state['arrays'][array_name] = imported_data[array_name]
                        
                        # --- INICIO DEL LOG DETALLADO ---
                        if VERBOSE_MODE:
                            print(f"    - Sobrescribiendo arrays del SEQ{i} con datos del fichero MIDI:")
                            notes = new_state['arrays']['seq_note']
                            gates = new_state['arrays']['seq_gate']
                            velos = new_state['arrays']['seq_velocity']
                            
                            log_line_notes = "      Notas:    "
                            log_line_gates = "      Gates:    "
                            log_line_velos = "      Velocidad:"
                            
                            for step in range(initial_num_steps):
                                note_str = f"{notes[step]:>3}" if gates[step] == 1 else "---"
                                gate_str = f"{gates[step]:>3}"
                                velo_str = f"{velos[step]:>3}" if gates[step] == 1 else "---"
                                
                                log_line_notes += f" {note_str}"
                                log_line_gates += f" {gate_str}"
                                log_line_velos += f" {velo_str}"
                            
                            print(log_line_notes)
                            print(log_line_gates)
                            print(log_line_velos)
                        # --- FIN DEL LOG DETALLADO ---

        sequencers_state.append(new_state)


def process_sequencer_step(seq_index, seq_state, fire_at_tick, mido_ports_map_g, is_virtual_mode_now, virtual_out_obj=None, virtual_out_name=""):
    global user_variables, monitor_active

    seq_conf = seq_state['config']
    step_index = seq_state['active_step']

    # 1. Construir el contexto base para este paso del secuenciador
    base_context = {
        'step': step_index,
        'version': current_active_version
    }
    base_context.update(user_variables)

    for key, value in seq_conf.items():
        if not isinstance(value, (list, dict)):
            base_context[key] = value

    for key, arr in seq_state['arrays'].items():
        if step_index < len(arr):
            context_key = key.replace('seq_', '') + '_out'
            base_context[context_key] = arr[step_index]


    is_active_expr = base_context.get('seq_active', 1)
    is_active_val = get_evaluated_value_from_output_config(
        is_active_expr, 1, base_context, f"SEQ[{seq_index}]", "seq_active"
    )
    if not is_active_val:
        return # Si no está activo, no procesar este paso.
    
    if base_context.get('gate_out', 1) == 0 or base_context.get('mute_out', 0) == 1:
        return # No procesar este paso si el gate está cerrado o está muteado.
    
    # 2. Determinar qué bloques de 'output' procesar
    output_blocks = seq_conf.get("output", [])
    if not output_blocks:
        output_blocks = [{"event_out": "note"}]

    # 3. Iterar, procesar, ENVIAR y LOGUEAR cada bloque de 'output'
    for i, out_block in enumerate(output_blocks):
        if not isinstance(out_block, dict):
            continue

        generated_outputs = process_single_output_block(
            out_block, i, base_context, seq_conf, f"SEQ[{seq_index}]",
            current_active_version, global_device_aliases, mido_ports_map_g,
            is_virtual_mode_now, virtual_out_obj, virtual_out_name
        )

        if not generated_outputs:
            continue

        for (msg_to_send, dest_port_obj, dest_alias_str, _, event_type, _) in generated_outputs:
            if not dest_port_obj or dest_port_obj.closed:
                continue

            try:
                dest_port_obj.send(msg_to_send)

                if monitor_active:
                    total_steps = len(seq_state['arrays'].get('seq_note', []))
                    log_prefix = f"SQ[{seq_index}]: ({step_index + 1}/{total_steps}):"
                    log_line = format_midi_message_for_log(msg_to_send, log_prefix, current_active_version, None, dest_alias_str)
                    if log_line:
                        print(log_line)

                if event_type == 'note_on' and msg_to_send.velocity > 0:
                    default_length = base_context.get('note_length_out', 0.9)
                    length_val = float(get_evaluated_value_from_output_config(
                        out_block.get('note_length_out'), default_length, base_context, f"SEQ[{seq_index}]", "note_length_out"
                    ))

                    # Si la duración es -1, no se agenda el note_off.
                    if length_val != -1:
                        ppqn = int(base_context.get('ppqn', SEQ_DEFAULTS['ppqn']))
                        step_duration_expr = seq_conf.get('step_duration', "1/16")
                        step_duration_str = get_evaluated_value_from_output_config(
                            step_duration_expr, "1/16", base_context, f"SEQ[{seq_index}]", "note_off_calc"
                        )
                        ticks_for_step = parse_step_duration(step_duration_str, ppqn)
                        
                        note_off_delay = int(round(ticks_for_step * length_val))
                        note_off_fire_at = fire_at_tick + note_off_delay

                        note_off_msg = mido.Message('note_off', channel=msg_to_send.channel, note=msg_to_send.note)
                        seq_state['pending_note_offs'].append((note_off_fire_at, note_off_msg, dest_port_obj, dest_alias_str))

            except Exception as e:
                if monitor_active:
                    print(f"  [!] Error enviando mensaje de SEQ[{seq_index}]: {e}")


def load_arpeggiators(full_json_contents):
    global arpeggiator_templates

    all_arp_configs = []
    for content in full_json_contents:
        if "arpeggiator" in content and isinstance(content["arpeggiator"], list):
            all_arp_configs.extend(content["arpeggiator"])

    if not all_arp_configs:
        return

    print("\n--- Configuración de Plantillas de Arpegiador ---")
    for i, arp_conf in enumerate(all_arp_configs):
        if not isinstance(arp_conf, dict) or "arp_id" not in arp_conf:
            print(f"  [!] ADVERTENCIA ARP: Configuración de arpegiador #{i} inválida (falta 'arp_id').")
            continue
        
        arp_id = arp_conf["arp_id"]
        if not isinstance(arp_id, int):
            print(f"  [!] ADVERTENCIA ARP: El 'arp_id' debe ser un número entero. Ignorando config #{i}.")
            continue

        print(f"  - Cargando Plantilla de Arpegiador id:{arp_id}...")
        
        final_config = ARP_DEFAULTS.copy()
        final_config.update(arp_conf)

        if "octave_mode" in final_config:
            final_config["arp_octave_mode"] = final_config["octave_mode"]

        arpeggiator_templates[arp_id] = final_config


def _recalculate_arp_pattern(instance, instance_key=None):
    arp_conf = instance['config']
    input_tuples = instance['input_notes'] 
    
    if not input_tuples:
        instance['arp_pattern'] = []
        instance['arp_velocity_pattern'] = []
        return

    base_notes = [t[0] for t in input_tuples]
    base_vels = [t[1] for t in input_tuples]
    
    sorted_tuples = sorted(input_tuples, key=lambda x: x[0])
    sorted_notes = [t[0] for t in sorted_tuples]
    sorted_vels = [t[1] for t in sorted_tuples]

    eval_context = { 'step': instance.get('active_step', 0), 'version': current_active_version }
    eval_context.update(user_variables)
    
    log_id_str = f"ARP[{instance['config'].get('arp_id', '?')},?]"
    if instance_key:
        log_id_str = f"ARP[{instance_key[0]},{instance_key[1]}]"

    arp_pattern_manual = arp_conf.get('arp_pattern')
    temp_pattern_notes = []
    temp_pattern_vels = []

    # Prioridad 1: Patrón manual definido por el usuario con 'arp_pattern'
    if arp_pattern_manual and isinstance(arp_pattern_manual, list):
        arp_mode_for_base_expr = arp_conf.get('arp_mode', 'sorted')
        arp_mode_for_base = get_evaluated_value_from_output_config(arp_mode_for_base_expr, 'sorted', eval_context, log_id_str, "arp_mode_base")

        note_base = sorted_notes
        vel_base = sorted_vels
        if arp_mode_for_base == 'as_played':
            note_base = base_notes
            vel_base = base_vels

        num_base_notes = len(note_base)
        if num_base_notes > 0:
            for index in arp_pattern_manual:
                if index == -1: # Silencio
                    temp_pattern_notes.append(None)
                    temp_pattern_vels.append(0)
                else:
                    safe_index = index % num_base_notes
                    temp_pattern_notes.append(note_base[safe_index])
                    temp_pattern_vels.append(vel_base[safe_index])

    # Prioridad 2: Modos de generación automática
    else:
        arp_mode_expr = arp_conf.get('arp_mode', 'sorted')
        arp_mode = get_evaluated_value_from_output_config(arp_mode_expr, 'sorted', eval_context, log_id_str, "arp_mode")
        
        # --- Lógica de dirección movida aquí ---
        direction_expr = arp_conf.get('arp_step_direction', 'up')
        direction = get_evaluated_value_from_output_config(direction_expr, 'up', eval_context, log_id_str, "arp_step_direction")

        # Base de notas para la generación
        working_notes, working_vels = sorted_notes, sorted_vels
        if arp_mode == 'as_played':
            working_notes, working_vels = base_notes, base_vels
        
        # Generar la secuencia unidireccional primero
        if direction == 'down':
            temp_pattern_notes = list(reversed(working_notes))
            temp_pattern_vels = list(reversed(working_vels))
        else: # 'up' es el default
            temp_pattern_notes = list(working_notes)
            temp_pattern_vels = list(working_vels)

        # Expandir para modos bidireccionales si es necesario
        if len(temp_pattern_notes) > 1:
            if direction == 'updown': # Ping-pong sin repetir extremos
                notes_down = list(reversed(temp_pattern_notes))[1:-1]
                vels_down = list(reversed(temp_pattern_vels))[1:-1]
                temp_pattern_notes.extend(notes_down)
                temp_pattern_vels.extend(vels_down)
            elif direction == 'updown_inclusive': # Ping-pong repitiendo extremos
                notes_down = list(reversed(temp_pattern_notes))
                vels_down = list(reversed(temp_pattern_vels))
                temp_pattern_notes.extend(notes_down)
                temp_pattern_vels.extend(vels_down)
        # --- Fin de la nueva lógica de dirección ---

        stutter_match = re.match(r'stutter(\d*)', str(arp_mode))
        if stutter_match:
            repetitions = int(stutter_match.group(1) or 2)
            stuttered_notes, stuttered_vels = [], []
            for i in range(len(temp_pattern_notes)):
                stuttered_notes.extend([temp_pattern_notes[i]] * repetitions)
                stuttered_vels.extend([temp_pattern_vels[i]] * repetitions)
            temp_pattern_notes, temp_pattern_vels = stuttered_notes, stuttered_vels
        elif arp_mode == 'outside_in':
            notes, vels = list(sorted_notes), list(sorted_vels)
            temp_pattern_notes, temp_pattern_vels = [], []
            while notes:
                temp_pattern_notes.append(notes.pop(0))
                temp_pattern_vels.append(vels.pop(0))
                if notes:
                    temp_pattern_notes.append(notes.pop(-1))
                    temp_pattern_vels.append(vels.pop(-1))
        # Otros modos como random, etc. se pueden añadir aquí si es necesario
        
    # La lógica de octavas ahora puede usar temp_pattern_notes de forma segura
    octaves = int(get_evaluated_value_from_output_config(arp_conf.get('arp_octaves', 1), 1, eval_context, log_id_str, "arp_octaves"))
    octave_mode = get_evaluated_value_from_output_config(arp_conf.get('arp_octave_mode', "up"), "up", eval_context, log_id_str, "arp_octave_mode")
    final_pattern_notes = []
    final_pattern_vels = []

    if octaves <= 1:
        final_pattern_notes, final_pattern_vels = temp_pattern_notes, temp_pattern_vels
    elif octave_mode == 'alternate':
        for i, note in enumerate(temp_pattern_notes):
            for j in range(octaves):
                if note is not None:
                    final_pattern_notes.append(note + (12 * j))
                    final_pattern_vels.append(temp_pattern_vels[i])
                else:
                    final_pattern_notes.append(None)
                    final_pattern_vels.append(0)
    else: # Default 'up' mode
        for i in range(octaves):
            final_pattern_notes.extend([n + (12 * i) if n is not None else None for n in temp_pattern_notes])
            final_pattern_vels.extend(temp_pattern_vels)

    instance['arp_pattern'] = final_pattern_notes
    instance['arp_velocity_pattern'] = final_pattern_vels

    # Resetear el patrón de random1 si las notas de entrada han cambiado
    if arp_conf.get('arp_mode') != 'random1':
        instance.pop('fixed_random_pattern', None)

def update_arp_input(instance_key, notes, velocity, event_type):
    global arpeggiator_instances, monitor_active
    
    # verbose_print(f"DBG: update_arp_input llamado para {instance_key}. Config: {arpeggiator_instances.get(instance_key, {}).get('config')}")
    if instance_key not in arpeggiator_instances:
        return

    instance = arpeggiator_instances[instance_key]
    arp_conf = instance['config']
    is_latch_on = arp_conf.get('arp_latch', False)

    # Update input notes list
    if event_type == 'note_on':
        for note in notes:
            note_vel_tuple = (note, velocity)
            if note_vel_tuple not in instance['input_notes']:
                instance['input_notes'].append(note_vel_tuple)
    elif event_type == 'note_off' and not is_latch_on:
        for note in notes:
            instance['input_notes'] = [t for t in instance['input_notes'] if t[0] != note]


    if instance['input_notes'] and midimaster_assumed_status == "PLAYING":
        quantize_config = arp_conf.get("quantize_start")

        should_quantize = False
        display_grid = ""
        if isinstance(quantize_config, str):
            should_quantize = True
            display_grid = quantize_config
        elif quantize_config is True:
            should_quantize = True
            display_grid = "1/16 (default)"

        if should_quantize:
            if not instance['is_playing'] and not instance['is_armed']:
                instance['is_armed'] = True
                if monitor_active: print(f"ARP[{instance_key[0]},{instance_key[1]}] ARMED (esperando a la rejilla de '{display_grid}')")
        else: # Comportamiento original si no hay cuantización (quantize_start es None, false, etc.)
            if not instance['is_playing']:
                instance['is_playing'] = True
                instance['active_step'] = 0
                instance['tick_counter'] = 0
                if monitor_active: print(f"ARP[{instance_key[0]},{instance_key[1]}] Auto-Start (inmediato)")


    _recalculate_arp_pattern(instance, instance_key)
    if monitor_active and instance['is_playing']:
        print(f"     ⇢ ARP: Instancia {instance_key} actualizada. Patrón: {[n for n in instance['arp_pattern'] if n is not None]}")

def process_arpeggiator_step(instance_key, instance_state, mido_ports_map_g, is_virtual_mode_now, virtual_out_obj=None, virtual_out_name="", current_tick=0):
    arp_conf = instance_state['config']
    step_index = instance_state['active_step']
    pattern = instance_state.get('arp_pattern', [])
    
    if not pattern:
        return

    eval_context = { 'step': step_index, 'version': current_active_version }
    eval_context.update(user_variables)
    log_id_str = f"ARP[{instance_key[0]},{instance_key[1]}]"

    gate_val = int(get_evaluated_value_from_output_config(arp_conf.get('arp_gate', 1), 1, eval_context, log_id_str, "arp_gate"))
    mute_val = int(get_evaluated_value_from_output_config(arp_conf.get('arp_mute', 0), 0, eval_context, log_id_str, "arp_mute"))
    if gate_val == 0 or mute_val == 1: return

    note_val = pattern[step_index]
    if note_val is None:
        return

    vel_pattern = instance_state.get('arp_velocity_pattern', [])
    velocity_val = vel_pattern[step_index] if step_index < len(vel_pattern) else int(get_evaluated_value_from_output_config(arp_conf.get('arp_velocity', 100), 100, eval_context, log_id_str, "arp_velocity"))
    
    prob_val = float(get_evaluated_value_from_output_config(arp_conf.get('arp_probability', 1.0), 1.0, eval_context, log_id_str, "arp_probability"))
    if random.random() > prob_val: return

    final_note = max(0, min(127, int(note_val)))
    final_vel = max(0, min(127, int(velocity_val)))
    if final_vel == 0: return

    # --- Find output port ---
    device_out_alias = arp_conf.get('device_out')
    if not device_out_alias: return
    
    target_port_obj = None
    out_dev_sub = global_device_aliases.get(device_out_alias, device_out_alias)
    for p_name, p_info in mido_ports_map_g.items():
        if p_info["type"] == "out" and out_dev_sub.lower() in p_name.lower():
            target_port_obj = p_info["obj"]; break
    
    if target_port_obj:
        final_channel = instance_key[1]
        out_msg = mido.Message('note_on', channel=final_channel, note=final_note, velocity=final_vel)
        target_port_obj.send(out_msg)
        
        if monitor_active:
            log_prefix = f"ARP[{instance_key[0]},{instance_key[1]}]: ({step_index + 1}/{len(pattern)}):"
            log_line = format_midi_message_for_log(out_msg, log_prefix, current_active_version, None, device_out_alias)
            if log_line: print(log_line)

        # Schedule Note Off
        ppqn = int(arp_conf.get('ppqn', ARP_DEFAULTS['ppqn']))
        step_duration_expr = arp_conf.get('step_duration', "1/16")
        step_duration_str = get_evaluated_value_from_output_config(step_duration_expr, "1/16", eval_context, log_id_str, "step_duration")
        ticks_for_step = parse_step_duration(step_duration_str, ppqn)

        note_len_factor = float(get_evaluated_value_from_output_config(arp_conf.get('arp_note_length', 0.9), 0.9, eval_context, log_id_str, "arp_note_length"))
        note_off_delay = int(round(ticks_for_step * note_len_factor))
        fire_at_tick = current_tick + note_off_delay
        note_off_msg = mido.Message('note_off', channel=final_channel, note=final_note)
        instance_state['pending_note_offs'].append((fire_at_tick, note_off_msg, target_port_obj, device_out_alias))



def _silence_instance(instance_state, module_type_str=""):

    global monitor_active
    
    if not instance_state or 'pending_note_offs' not in instance_state:
        return

    # Iterar sobre una copia para poder modificar la original de forma segura
    for _, note_off_msg, target_port_obj, device_out_alias in list(instance_state['pending_note_offs']):
        if target_port_obj and not target_port_obj.closed:
            try:
                target_port_obj.send(note_off_msg)
                if monitor_active:
                    log_line = format_midi_message_for_log(note_off_msg, prefix=f"   silenced {module_type_str}: ", target_port_alias_for_log_output=device_out_alias)
                    if log_line: print(log_line)
            except Exception as e:
                if monitor_active: print(f"  [!] Err sending silence note_off: {e}")

    # Vaciar la lista de notas pendientes
    instance_state['pending_note_offs'].clear()

def _rebuild_sequencer_schedule(seq_index, seq_state):
    global user_variables

    try:
        seq_conf = seq_state['config']
        eval_context_rebuild = {"version": current_active_version, **user_variables}

        # --- Add dynamic array resizing logic ---
        # Evaluate the step_total expression to get the CURRENT desired number of steps
        new_num_steps = int(get_evaluated_value_from_output_config(
            seq_conf.get('step_total'), 
            SEQ_DEFAULTS['step_total'], 
            eval_context_rebuild, 
            f"SEQ[{seq_index}]", 
            "step_total"
        ))

        # Check if resizing is needed by comparing with the current array length
        current_array_size = len(seq_state['arrays'].get('seq_note', []))

        if new_num_steps != current_array_size:
            if VERBOSE_MODE:
                print(f"    - SEQ[{seq_index}] Resizing arrays from {current_array_size} to {new_num_steps} steps.")
            
            for array_name, old_array in list(seq_state['arrays'].items()):
                if not isinstance(old_array, list):
                    continue

                last_value = old_array[-1] if old_array else SEQ_DEFAULTS.get(array_name, 0)
                
                if new_num_steps > current_array_size:
                    extension = [last_value] * (new_num_steps - current_array_size)
                    new_array = old_array + extension
                else:
                    new_array = old_array[:new_num_steps]
                
                seq_state['arrays'][array_name] = new_array
        # --- End of resizing logic ---

        # --- Continue with schedule generation using the new size ---
        ppqn = int(get_evaluated_value_from_output_config(seq_conf.get('ppqn'), SEQ_DEFAULTS['ppqn'], eval_context_rebuild, f"SEQ[{seq_index}]", "ppqn"))
        step_duration_expr = seq_conf.get('step_duration', "1/16")
        base_duration_str = get_evaluated_value_from_output_config(
            step_duration_expr, "1/16", eval_context_rebuild, f"SEQ[{seq_index}]", "step_duration"
        )
        ticks_per_base_step = parse_step_duration(base_duration_str, ppqn)

        

        old_ticks_per_base_step = seq_state.get('last_ticks_per_step', 0)
        if old_ticks_per_base_step > 0 and (ticks_per_base_step != old_ticks_per_base_step or new_num_steps != current_array_size):
            old_cycle_duration = old_ticks_per_base_step * current_array_size
            current_ticks = seq_state.get('tick_counter', 0)
            relative_position = current_ticks / old_cycle_duration if old_cycle_duration > 0 else 0
            
            new_cycle_duration = ticks_per_base_step * new_num_steps
            new_tick_position = relative_position * new_cycle_duration
            
            seq_state['tick_counter'] = int(round(new_tick_position))
            seq_state['last_known_tick'] = -1

        swing_val = get_evaluated_value_from_output_config(seq_conf.get('swing', 0.0), 0.0, eval_context_rebuild, f"SEQ[{seq_index}]", "swing")
        shift_global_val = get_evaluated_value_from_output_config(seq_conf.get('shift_global', 0.0), 0.0, eval_context_rebuild, f"SEQ[{seq_index}]", "shift_global")
        shift_array_val = seq_state['arrays'].get('shift_array', [0.0] * new_num_steps)

        new_schedule = []
        for step_idx in range(new_num_steps):
            ideal_fire_tick = step_idx * ticks_per_base_step
            shift_offset_ticks = int(round((shift_global_val + shift_array_val[step_idx]) * ticks_per_base_step))
            swing_offset_ticks = 0
            if swing_val != 0.0 and step_idx % 2 != 0:
                swing_offset_ticks = int(round((ticks_per_base_step / 2) * swing_val))
            final_fire_tick = ideal_fire_tick + shift_offset_ticks + swing_offset_ticks
            new_schedule.append({'fire_at': final_fire_tick, 'step': step_idx})

        new_schedule.sort(key=lambda x: x['fire_at'])
        
        seq_state['event_schedule'] = new_schedule
        seq_state['schedule_needs_rebuild'] = False

        seq_state['current_cycle_duration'] = new_num_steps * ticks_per_base_step
        seq_state['last_ticks_per_step'] = ticks_per_base_step

        if VERBOSE_MODE:
            log_str = f"    - SEQ[{seq_index}] Agenda reconstruida (Total Pasos: {new_num_steps}, Ticks/Paso: {ticks_per_base_step}):\n      "
            log_str += " -> ".join([f"P{ev['step']:02d}@{ev['fire_at']}" for ev in new_schedule])
            print(log_str)

    except Exception as e:
        print(f"\n[!!!] ERROR en _rebuild_sequencer_schedule: {e}\n")
        traceback.print_exc()
        seq_state['schedule_needs_rebuild'] = False

        
        
def signal_handler(sig, frame):
    global shutdown_flag
    shutdown_flag = True
    print("\n[*] Interrupción recibida")

def find_port_by_substring(ports, sub, type_desc="puerto"):
    if not ports: return None
    if not sub: return None
    for name in ports:
        if sub.lower() in name.lower(): return name
    return None


def _load_json_file_content(filepath: Path):
    if not filepath.is_file(): print(f"Err: Archivo '{filepath.name}' no encontrado."); return None
    try:
        with open(filepath, 'r', encoding='utf-8') as f: content = json5.load(f) 
        return content
    except Exception as e: 
        print(f"Err inesperado cargando o parseando '{filepath.name}': {e}")
    return None

def load_rule_file_new_structure(fp: Path):
    global active_scales
    content = _load_json_file_content(fp)
    if not content or not isinstance(content, dict): return None, None
    
    devices = content.get("device_alias", {})
    filters = content.get("midi_filter", [])
    

    if not isinstance(devices, dict): 
        print(f"Adv: Sección 'device_alias' en '{fp.name}' no es diccionario. Usando vacío."); devices = {}
    if not isinstance(filters, list): 
        print(f"Adv: Sección 'midi_filter' en '{fp.name}' no es lista. Usando vacía."); filters = []
    

    for i, f_config in enumerate(filters):
        if isinstance(f_config, dict): 
            f_config["_source_file"] = fp.name
            f_config["_filter_id_in_file"] = i
    
    user_defined_scales = content.get("user_scales", {})
    if isinstance(user_defined_scales, dict):
        active_scales.update(user_defined_scales)
    elif user_defined_scales:
        print(f"Adv: Sección 'user_scales' en '{fp.name}' no es un diccionario. Ignorada.")
    
    return devices, filters


def do_scale_notes(value_to_scale, root_note_midi, scale_type_name, available_scales_dict):
    # print(f"DEBUG do_scale_notes: IN_NOTE={value_to_scale}, ROOT={root_note_midi}, SCALE_TYPE='{scale_type_name}', AVAILABLE_SCALES_KEYS={list(available_scales_dict.keys())}")
    if not isinstance(value_to_scale, int):
        return value_to_scale 

    scale_intervals = available_scales_dict.get(scale_type_name)
    if scale_intervals is None:
        # print(f"DEBUG do_scale_notes: Scale type '{scale_type_name}' NOT FOUND. Returning original: {value_to_scale}")
        return value_to_scale 

    # print(f"DEBUG do_scale_notes: Using intervals {scale_intervals} for scale '{scale_type_name}'")
    if not scale_intervals: 
        return value_to_scale

    note_octave_offset = value_to_scale // 12
    note_degree_in_octave = value_to_scale % 12
    root_degree_in_octave = root_note_midi % 12
    absolute_scale_degrees = sorted([(root_degree_in_octave + interval) % 12 for interval in scale_intervals])

    if note_degree_in_octave in absolute_scale_degrees:
        return value_to_scale 
    
    closest_lower_degree = -1
    for degree in reversed(absolute_scale_degrees):
        if degree < note_degree_in_octave:
            closest_lower_degree = degree
            break
    
    if closest_lower_degree != -1:
        result = (note_octave_offset * 12) + closest_lower_degree
        # print(f"==> do_scale_notes: RETURNING {result} (found lower in octave)")
        return result
    else:
        result = ((note_octave_offset - 1) * 12) + absolute_scale_degrees[-1]
        # print(f"==> do_scale_notes: RETURNING {result} (used prev octave highest)")
        return result


def collect_available_versions_from_filters(all_filters):
    global available_versions
    versions = {0} # Default version 0
    for f_config in all_filters:
        if not isinstance(f_config, dict):
            continue
        
        # 1. Añadir las versiones de la condición de entrada "version"
        if "version" in f_config:
            v_cond = f_config["version"]
            if isinstance(v_cond, int):
                versions.add(v_cond)
            elif isinstance(v_cond, list):
                versions.update(item for item in v_cond if isinstance(item, int))
        
        # 2. Añadir las versiones del resultado "set_version" (si es un entero)
        if "set_version" in f_config:
            v_action = f_config["set_version"]
            if isinstance(v_action, int):
                versions.add(v_action)
            # Nota: No podemos evaluar expresiones aquí, así que solo añadimos enteros literales.
            # Esto es suficiente para que el ciclo por teclado (espacio) funcione correctamente.

    available_versions = sorted(list(versions))
    if not available_versions:
        available_versions = [0]


def evaluate_expression(expression_str, context_vars_for_eval):
    global user_variables, channel_arrays

    if not isinstance(expression_str, (str, int, float, list, dict)): return expression_str 
    if isinstance(expression_str, (int, float)): return int(expression_str)

    current_expr_str = str(expression_str)

    try:
        return int(current_expr_str)
    except ValueError:
        pass 

    
    random_match = re.match(r"^\s*random\s*\(\s*(.+)\s*,\s*(.+)\s*\)\s*$", current_expr_str, re.IGNORECASE)
    if random_match:
        min_expr_str = random_match.group(1).strip()
        max_expr_str = random_match.group(2).strip()
        min_val = evaluate_expression(min_expr_str, context_vars_for_eval)
        max_val = evaluate_expression(max_expr_str, context_vars_for_eval)
        if isinstance(min_val, int) and isinstance(max_val, int):
            if min_val > max_val: min_val, max_val = max_val, min_val
            try: return random.randint(min_val, max_val)
            except ValueError: return min_val 
        return None
    
    eval_locals = context_vars_for_eval.copy()

    # Añade alias más amigables para las variables de entrada comunes.
    public_to_internal_var_map = {
        "channel_in": "ch0_in_ctx", "ch_in": "ch0_in_ctx", "channel": "ch0_in_ctx",
        "value_1_in": "value_in_1_ctx", "value_1": "value_in_1_ctx",
        "value_2_in": "value_in_2_ctx", "value_2": "value_in_2_ctx",
        "delta_in": "delta_in_2_ctx",
        "cc_val2_saved": "cc_value_sent_ctx",
        "event_in": "event_type_in_ctx", "event": "event_type_in_ctx",
        "cc_type_in": "cc_type_in_ctx", "cc_type": "cc_type_in_ctx"
    }
    for public_name, internal_name in public_to_internal_var_map.items():
        if internal_name in context_vars_for_eval:
            eval_locals[public_name] = context_vars_for_eval[internal_name]

    # Añade las variables de usuario globales, que pueden sobrescribir otras si tienen el mismo nombre.
    eval_locals.update(user_variables)

    # if VERBOSE_MODE and "step" in context_vars_for_eval: # Solo para logs del secuenciador
    #     verbose_print(f"    - DEBUG_EVAL: Expresión='{expression_str}'")
    #     verbose_print(f"    - DEBUG_EVAL: Contexto RECIBIDO: {context_vars_for_eval}")
    #     verbose_print(f"    - DEBUG_EVAL: Contexto CONSTRUIDO para eval(): {eval_locals}")

    eval_locals['random'] = random.randint
    eval_locals['prob'] = lambda p: 1 if random.random() < float(p) else 0

    def _toggle_func(value_arg):
        """Invierte un valor numérico (0 a 1, y cualquier otro número a 0)."""
        try:
            # El argumento ya debería ser un número evaluado.
            current_val = int(value_arg)
            return 1 if current_val == 0 else 0
        except (ValueError, TypeError):
            # Si la expresión no resolvió a un número, retorna 0 de forma segura.
            return 0

    eval_locals['toggle'] = _toggle_func

    def _chord_func(root, num_notes=3, scale_def='major'):
        root = int(root)
        num_notes = int(get_evaluated_value_from_output_config(num_notes, 3, context_vars_for_eval, "chord", "num_notes"))

        intervals = []
        if isinstance(scale_def, str):
            scale_name = str(scale_def)
            if scale_name in active_scales:
                intervals = active_scales[scale_name]
        elif isinstance(scale_def, list):
            intervals = scale_def
        
        if not intervals: return [root]

        if isinstance(scale_def, list):
            # If scale_def is a list of intervals, num_notes is ignored.
            return [min(127, max(0, root + i)) for i in intervals]
        else:
            # Build chord from scale name
            chord_notes = []
            for i in range(num_notes):
                octave = i // len(intervals)
                degree_index = i % len(intervals)
                note = root + intervals[degree_index] + (12 * octave)
                chord_notes.append(min(127, max(0, note)))
            return chord_notes

    eval_locals['chord'] = _chord_func

    def _scale_number_func(index):
        # Prioridad 1: Usar la lista personalizada si existe
        if user_ordered_scale_names:
            scale_source_list = user_ordered_scale_names
        # Prioridad 2: Usar todas las escalas activas como fallback
        else:
            scale_source_list = list(active_scales.keys())

        if not scale_source_list:
            return "major" # Fallback final
        try:
            safe_index = int(index) % len(scale_source_list)
            return scale_source_list[safe_index]
        except (ValueError, TypeError):
            return "major"
    eval_locals['scale_number'] = _scale_number_func

    def _arp_mode_number_func(index):
        if not ARP_MODES_LIST:
            return "as_played" # Fallback
        try:
            safe_index = int(index) % len(ARP_MODES_LIST)
            return ARP_MODES_LIST[safe_index]
        except (ValueError, TypeError):
            return "as_played" # Fallback
    eval_locals['arp_mode_number'] = _arp_mode_number_func
            

    def _duration_index_func(index):
        # Prioridad 1: Usar la lista personalizada si existe
        if user_ordered_duration_names:
            duration_source_list = user_ordered_duration_names
        # Prioridad 2: Usar la lista por defecto como fallback
        else:
            duration_source_list = DEFAULT_NOTE_DURATIONS

        if not duration_source_list:
            return "1/16" # Fallback final
        try:
            safe_index = int(index) % len(duration_source_list)
            return duration_source_list[safe_index]
        except (ValueError, TypeError):
            return "1/16" # Fallback si el índice no es un número
    eval_locals['duration_index'] = _duration_index_func




    def _get_var_func(array_name, index, seq_idx=None):
        # Como los argumentos vienen de `eval`, ya están evaluados.
        if not isinstance(array_name, str): return 0
        
        array_name = array_name.strip()
        index = int(index) if isinstance(index, (int, float)) else 0

        # Prioridad 1: Acceso directo a un secuenciador por índice
        if seq_idx is not None and isinstance(seq_idx, int):
            if 0 <= seq_idx < len(sequencers_state):
                seq_arrays = sequencers_state[seq_idx].get('arrays', {})
                if array_name in seq_arrays and 0 <= index < len(seq_arrays[array_name]):
                    return seq_arrays[array_name][index]
        
        # Prioridad 2: Arrays de Canal (lógica existente)
        elif array_name.startswith("ch_"):
            if array_name in channel_arrays and 0 <= index < len(channel_arrays.get(array_name, [])):
                return channel_arrays[array_name][index]
        
        elif array_name in user_variables:
            target_array = user_variables[array_name]
            if isinstance(target_array, list) and 0 <= index < len(target_array):
                # Devolver el valor. Puede ser un número o None (para silencios).
                return target_array[index]
            
        # Prioridad 3: Contexto del secuenciador (para llamadas internas, lógica existente)
        elif '_seq_arrays_ctx' in context_vars_for_eval and array_name in context_vars_for_eval['_seq_arrays_ctx']:
            target_array = context_vars_for_eval['_seq_arrays_ctx'][array_name]
            if 0 <= index < len(target_array):
                return target_array[index]
        
        return 0 # Valor por defecto si no se encuentra nada

    
    eval_locals['get_var'] = _get_var_func

    current_expr_str_stripped = current_expr_str.strip()
    if current_expr_str_stripped in eval_locals:
        return eval_locals[current_expr_str_stripped]

    try:
        result = eval(current_expr_str, {"__builtins__": {}}, eval_locals)
        return result
    except Exception:
        pass 

    if isinstance(expression_str, str):
        return expression_str.strip()

    return None




def format_midi_message_for_log(msg, prefix="", active_version=-1, 
                                rule_id_source=None, target_port_alias_for_log_output=None,
                                input_port_actual_name=None, device_aliases_global_map=None):
    # print(f"DEBUG format_midi_message_for_log received: {msg}")
    if msg.type in ['clock', 'activesense']: 
        return None
        
    version_prefix = f"[{active_version}] " if active_version != -1 and len(available_versions) > 1 else ""
    port_display_name = ""
    add_filter_id_to_log = True 

    normalized_prefix = prefix.strip().upper()

    if normalized_prefix.startswith("IN") and input_port_actual_name:
        resolved_name = input_port_actual_name
        if device_aliases_global_map:
            for alias, substring_val in device_aliases_global_map.items():
                if substring_val.lower() in input_port_actual_name.lower():
                    resolved_name = alias
                    break
        port_display_name = f"[{resolved_name}]"
        add_filter_id_to_log = True 
    elif normalized_prefix.endswith("OUT:") and target_port_alias_for_log_output:
        port_display_name = f"[{target_port_alias_for_log_output}]"
        add_filter_id_to_log = False 

    filter_id_prefix_str = ""
    if rule_id_source and add_filter_id_to_log:
        if isinstance(rule_id_source, str) and rule_id_source.startswith("SEQ ("):
            filter_id_prefix_str = rule_id_source
        else:
            filter_id_prefix_str = f"{{{rule_id_source}}}"
    
    # Aquí usamos la variable 'prefix' original, que conserva los espacios
    full_prefix_parts = [version_prefix, prefix, port_display_name, filter_id_prefix_str]
    full_prefix = "".join(p for p in full_prefix_parts if p)
    
    parts = [full_prefix]
    msg_type_display = msg.type.replace("_", " ").title() 
    
    if msg.type in ['note_on', 'note_off']:
        vel_info = f" vel({msg.velocity})" if msg.type == 'note_on' else ""
        # Considerar note_on con velocity 0 como note_off efectivo
        is_eff_off = msg.type == 'note_off' or (msg.type == 'note_on' and msg.velocity == 0)
        type_str = "NT_off" if is_eff_off else "NT_on"
        parts.append(f"Ch({msg.channel + 1}) {type_str}({msg.note}){vel_info}")
    elif msg.type == 'control_change': parts.append(f"Ch({msg.channel + 1}) CC({msg.control}) val({msg.value})")
    elif msg.type == 'program_change': parts.append(f"Ch({msg.channel + 1}) PC({msg.program})")
    elif msg.type == 'pitchwheel': parts.append(f"Ch({msg.channel + 1}) Pitch({msg.pitch})")
    elif msg.type == 'aftertouch': parts.append(f"Ch({msg.channel + 1}) AfTouch({msg.value})")
    elif msg.type == 'polytouch': parts.append(f"Ch({msg.channel + 1}) PolyTouch({msg.note}) val({msg.value})")
    elif msg.type == 'sysex': parts.append(f"SysEx (len {len(msg.data) if hasattr(msg, 'data') else 'N/A'})")
    elif msg.type in ['start', 'stop', 'continue', 'songpos', 'clock', 'reset']: parts.append(f"{msg_type_display}")
    else: parts.append(f"{msg_type_display} (raw:{msg.hex()})") # Mensajes menos comunes

    log_line = " ".join(p.strip() for p in parts if p.strip())
    return log_line if log_line != full_prefix else None # Evitar líneas vacías si solo hay prefijo

def get_evaluated_value_from_output_config(config_value, default_value_if_none, current_eval_context_for_expr, filter_id_for_debug, debug_field_name=""):
    global user_variables, active_scales, monitor_active

    original_expression = config_value
    final_value_to_return = default_value_if_none 
    evaluated_successfully = False

    if isinstance(config_value, dict) and "scale_value" in config_value:
        expression_for_scale_value = config_value.get("scale_value")
        value_source_for_scaling = None
        evaluated_scale_input = evaluate_expression(expression_for_scale_value, current_eval_context_for_expr)

        if evaluated_scale_input is not None:
            value_source_for_scaling = evaluated_scale_input

        if value_source_for_scaling is not None:
            try:
                input_val_to_scale = int(value_source_for_scaling)
                min_in, max_in = config_value.get("range_in", [0, 127])
                min_out, max_out = config_value.get("range_out", [0, 127]) 
                if not (isinstance(min_out, (int,float)) and isinstance(max_out, (int,float))):
                     print(f"Adv ({filter_id_for_debug}): 'range_out' malformado para {debug_field_name}.")
                else:
                    min_in, max_in = int(min_in), int(max_in); min_out, max_out = int(min_out), int(max_out)
                    normalized_val = 0.0
                    if max_in == min_in: 
                        normalized_val = 0.0 if input_val_to_scale <= min_in else 1.0
                    else: 
                        clamped_input = max(min_in, min(max_in, input_val_to_scale))
                        normalized_val = (float(clamped_input) - min_in) / (max_in - min_in)
                    scaled_val = normalized_val * (max_out - min_out) + min_out
                    final_value_to_return = int(round(scaled_val))
                    evaluated_successfully = True # Se obtuvo un valor
            except (ValueError, TypeError) as e: print(f"Adv ({filter_id_for_debug}): Error escalando {debug_field_name} '{expression_for_scale_value}': {e}.")
        else: print(f"Adv ({filter_id_for_debug}): Variable '{expression_for_scale_value}' para escalado en {debug_field_name} no encontrada.")

    elif isinstance(config_value, dict) and "scale_notes" in config_value:
        scale_notes_params = config_value["scale_notes"]
        if isinstance(scale_notes_params, dict):
            val_expr = scale_notes_params.get("scale_value")
            root_expr = scale_notes_params.get("scale_root")
            type_expr = scale_notes_params.get("scale_type")

            if val_expr is not None and root_expr is not None and type_expr is not None:
                val_to_scale_num = evaluate_expression(val_expr, current_eval_context_for_expr)
                root_note_num = evaluate_expression(root_expr, current_eval_context_for_expr)
                scale_type_name_str = evaluate_expression(type_expr, current_eval_context_for_expr)
                

                if VERBOSE_MODE:
                    print(f"    DEBUG_SCALE_PARAMS ({filter_id_for_debug}):")
                    print(f"      - val_expr: '{val_expr}' -> {val_to_scale_num} (Tipo: {type(val_to_scale_num)})")
                    print(f"      - root_expr: '{root_expr}' -> {root_note_num} (Tipo: {type(root_note_num)})")
                    print(f"      - type_expr: '{type_expr}' -> '{scale_type_name_str}' (Tipo: {type(scale_type_name_str)})")

                if isinstance(val_to_scale_num, int) and \
                   isinstance(root_note_num, int) and \
                   isinstance(scale_type_name_str, str):
                    calculated_scaled_value  = do_scale_notes(val_to_scale_num, root_note_num, scale_type_name_str, active_scales)
                    if isinstance(calculated_scaled_value, int): # Asegurar que do_scale_notes devolvió un int
                        final_value_to_return = calculated_scaled_value
                        evaluated_successfully = True # Se obtuvo un valor
                    else:
                        print(f"Adv ({filter_id_for_debug}): do_scale_notes no devolvió un entero para {debug_field_name}.")
                else:
                    print(f"Adv ({filter_id_for_debug}): Parámetros inválidos para scale_notes en {debug_field_name}.")
            else:
                print(f"Adv ({filter_id_for_debug}): Faltan parámetros (scale_value, scale_root, scale_type) para scale_notes en {debug_field_name}.")
        else:
            print(f"Adv ({filter_id_for_debug}): Valor de 'scale_notes' debe ser un diccionario en {debug_field_name}.")
    

    elif config_value is not None: 
        evaluated = evaluate_expression(config_value, current_eval_context_for_expr)
        if evaluated is not None:
            final_value_to_return = evaluated
            evaluated_successfully = True

    # Loguear si una de nuestras funciones de índice ha resuelto un valor.
    if monitor_active and original_expression != final_value_to_return:
        log_source = filter_id_for_debug or "???"
        
        # Determinar si es una asignación de variable de usuario o una función de índice.
        is_assignment = isinstance(debug_field_name, str) and debug_field_name.startswith("Assign.")
        is_indexed_func = isinstance(original_expression, str) and any(
            f in original_expression for f in ["scale_number", "arp_mode_number", "duration_index"]
        )

        if is_assignment or is_indexed_func:
            # Limpiar el nombre del campo para un log más legible.
            field_name_for_log = debug_field_name
            if is_assignment:
                field_name_for_log = debug_field_name.split('.')[-1]
            elif not field_name_for_log and isinstance(config_value, dict):
                field_name_for_log = next(iter(config_value))

            print(f"     ⇢ SET: {log_source}:{field_name_for_log} = {final_value_to_return}")
    
    # Si ninguna lógica tuvo éxito en obtener un valor nuevo, final_value_to_return
    # ya tiene el default_value_if_none que se le pasó a la función.
    # No es necesario hacer nada más si no evaluated_successfully.
    return final_value_to_return


def process_single_output_block(out_conf, i_out_idx, base_context_for_this_output,
                                filter_config_parent_ref, filter_id_for_debug, current_version_for_log,
                                device_aliases_g, mido_ports_map_g,
                                is_virtual_mode_now, virtual_port_out_obj_ref=None, virtual_port_out_name_ref=""):
    global user_variables, cc_value_sent, monitor_active, active_note_map, channel_arrays
    global arpeggiator_templates, arpeggiator_instances, sequencers_state
    global osc_send_clients

    # --- INICIO DE LA NUEVA LÓGICA CONDICIONAL ---
    if "if" in out_conf:
        # El contexto de evaluación ya debe tener las variables de usuario
        current_output_eval_context_for_if = base_context_for_this_output.copy()
        current_output_eval_context_for_if.update(user_variables)

        condition_result = get_evaluated_value_from_output_config(
            out_conf["if"], 
            default_value_if_none=False, 
            current_eval_context_for_expr=current_output_eval_context_for_if,
            filter_id_for_debug=filter_id_for_debug,
            debug_field_name="if"
        )
        if not condition_result:
            return []
        
    # --- 1. Manejar acciones especiales que no generan MIDI directamente ---
    if "send_osc" in out_conf:
        osc_action = out_conf["send_osc"]
        target_name = osc_action.get("target")
        
        if target_name in osc_send_clients:
            client_info = osc_send_clients[target_name]
            client = client_info["client"]
            address = client_info.get("address", "/") # Usar dirección del target
            
            # Permitir sobreescribir la dirección en la propia acción
            address = osc_action.get("address", address)

            eval_context = base_context_for_this_output.copy()
            eval_context.update(user_variables)

            args_to_send = []
            for arg_expr in osc_action.get("args", []):
                evaluated_arg = get_evaluated_value_from_output_config(
                    arg_expr, None, eval_context, filter_id_for_debug, "osc_arg"
                )
                if evaluated_arg is not None:
                    args_to_send.append(evaluated_arg)
            
            try:
                client.send_message(address, args_to_send)
                if monitor_active:
                    print(f"     ⇢ OSC: [{target_name}] a '{address}' con {args_to_send}")
            except Exception as e:
                print(f"  [!] Error enviando OSC a '{target_name}': {e}")
        else:
            if monitor_active:
                print(f"  [!] Adv: Intento de enviar OSC a un destino no definido: '{target_name}'")
        return [] # La acción OSC no genera mensajes MIDI
    if out_conf.get("action") == "silence":
        target_arp_id_expr = out_conf.get("target_arp_id")
        target_seq_idx_expr = out_conf.get("target_seq_index")
        if target_arp_id_expr is not None:
            target_arp_id = get_evaluated_value_from_output_config(target_arp_id_expr, None, base_context_for_this_output, filter_id_for_debug, "target_arp_id")
            if target_arp_id is not None:
                for (arp_id, ch), instance in list(arpeggiator_instances.items()):
                    if arp_id == int(target_arp_id):
                        if monitor_active: print(f"[*] ACTION: Silenciando y deteniendo Arpegiador (id:{arp_id}, ch:{ch})")
                        _silence_instance(instance, f"ARP[{arp_id},{ch}]")
                        instance['is_playing'] = False; instance['is_armed'] = False
        if target_seq_idx_expr is not None:
            target_seq_idx = get_evaluated_value_from_output_config(target_seq_idx_expr, None, base_context_for_this_output, filter_id_for_debug, "target_seq_index")
            if target_seq_idx is not None:
                idx = int(target_seq_idx)
                if 0 <= idx < len(sequencers_state):
                    if monitor_active: print(f"[*] ACTION: Silenciando y deteniendo Secuenciador #{idx}")
                    _silence_instance(sequencers_state[idx], f"SEQ[{idx}]")
                    sequencers_state[idx]['is_playing'] = False; sequencers_state[idx]['is_armed'] = False
                else:
                    if monitor_active: print(f"  [!] Adv: Índice de secuenciador '{idx}' para la acción 'silence' está fuera de rango.")
        return None

    if out_conf.get("action") == "start_module":
        target_seq_idx_expr = out_conf.get("target_seq_index")
        if target_seq_idx_expr is not None:
            idx_eval = get_evaluated_value_from_output_config(target_seq_idx_expr, -1, base_context_for_this_output, filter_id_for_debug, "target_seq_index")
            idx = int(idx_eval) if idx_eval is not None else -1
            if 0 <= idx < len(sequencers_state):
                seq_conf = sequencers_state[idx]['config']
                quantize_config = seq_conf.get("quantize_start")
                should_quantize = False; display_grid = ""
                if isinstance(quantize_config, str): should_quantize = True; display_grid = quantize_config
                elif quantize_config is True: should_quantize = True; display_grid = "1/16 (default)"
                if should_quantize:
                    if not sequencers_state[idx]['is_playing'] and not sequencers_state[idx]['is_armed']:
                        sequencers_state[idx]['is_armed'] = True
                        if monitor_active: print(f"[*] ACTION: SEQ[{idx}] ARMED (esperando a la rejilla de '{display_grid}')")
                else:
                    if not sequencers_state[idx]['is_playing']:
                        sequencers_state[idx]['is_playing'] = True; sequencers_state[idx]['tick_counter'] = 0
                        sequencers_state[idx]['schedule_needs_rebuild'] = True; sequencers_state[idx]['last_known_tick'] = -1
                        if monitor_active: print(f"[*] ACTION: SEQ[{idx}] START (inmediato)")
        return None

    # --- 2. Manejar asignaciones de variables y configuración de módulos ---
    current_output_eval_context = base_context_for_this_output.copy()
    current_output_eval_context.update(user_variables)


    # Primero, procesamos todas las asignaciones de variables de usuario en el bloque
    processed_user_vars = False
    for key_in_json, expr_assign in out_conf.items():
        if key_in_json in user_variables:
            processed_user_vars = True # Marcamos que hemos procesado al menos una
            original_value = user_variables[key_in_json]
            val_assign = get_evaluated_value_from_output_config(expr_assign, None, current_output_eval_context, filter_id_for_debug, f"Assign.{key_in_json}")
            if val_assign is not None:
                try: user_variables[key_in_json] = type(user_variables[key_in_json])(val_assign)
                except (ValueError, TypeError): user_variables[key_in_json] = val_assign
                if user_variables[key_in_json] != original_value:
                    for i, seq_state in enumerate(sequencers_state):
                        seq_conf = seq_state['config']
                        params_to_check = [str(seq_conf.get(p, '')) for p in ['swing', 'step_duration', 'step_total', 'seq_transpose']]
                        if any(key_in_json in s for s in params_to_check):
                            seq_state['schedule_needs_rebuild'] = True
                            if VERBOSE_MODE: print(f"    - SEQ[{i}] marcado para reconstrucción de agenda (cambio en '{key_in_json}').")


    # Ahora, comprobamos si este bloque era SOLO para asignar variables,
    # verificando si carece de claves que generen acciones MIDI.
    midi_action_keys = {
        'event_out', 'value_1_out', 'value_2_out', 'channel_out', 'device_out',
        'action', 'set_var', 'arp_id', 'sysex_data'
    }
    has_midi_action = False
    shortcut_pattern_local = re.compile(r"^\s*(note|note_on|note_off|cc|pc)\s*\((.+)\)\s*$")
    for key in out_conf.keys():
        if key in midi_action_keys or (isinstance(key, str) and shortcut_pattern_local.match(key)):
            has_midi_action = True
            break
            
    if processed_user_vars and not has_midi_action:
        return [] # Detenerse aquí si solo se asignaron variables.



    if "set_var" in out_conf:
        set_var_actions = out_conf["set_var"]
        if isinstance(set_var_actions, list):
            for action_item in set_var_actions:
                if isinstance(action_item, dict):
                    array_name_str = action_item.get("name")
                    index_expr_str = action_item.get("index")
                    value_expr_str = action_item.get("value")
                    sequencer_index_expr = action_item.get("sequencer_index")
                    sequencer_index_target = None
                    if sequencer_index_expr is not None:
                        sequencer_index_target = evaluate_expression(sequencer_index_expr, current_output_eval_context)
                    if array_name_str and index_expr_str is not None and value_expr_str is not None:
                        target_array_dict = None; temp_eval_context = current_output_eval_context.copy(); is_channel_array = array_name_str.startswith("ch_")
                        if is_channel_array:
                            target_array_dict = channel_arrays
                            if array_name_str not in target_array_dict: target_array_dict[array_name_str] = [0] * 16
                        elif sequencer_index_target is not None and isinstance(sequencer_index_target, int) and 0 <= sequencer_index_target < len(sequencers_state):
                            target_array_dict = sequencers_state[sequencer_index_target]['arrays']
                            temp_eval_context['_seq_arrays_ctx'] = target_array_dict
                        if target_array_dict:
                            index_val = evaluate_expression(index_expr_str, temp_eval_context)
                            value_to_set_any = get_evaluated_value_from_output_config(value_expr_str, None, temp_eval_context, filter_id_for_debug, f"set_var.{array_name_str}")
                            if isinstance(index_val, (int, float)) and value_to_set_any is not None:
                                index = int(index_val)
                                if sequencer_index_target is not None and array_name_str not in target_array_dict:
                                    num_steps_target_eval = get_evaluated_value_from_output_config(sequencers_state[sequencer_index_target]['config'].get('step_total', 16), 16, temp_eval_context, f"SEQ{sequencer_index_target}", "step_total")
                                    target_array_dict[array_name_str] = [0] * int(num_steps_target_eval)
                                    if monitor_active: print(f"    INFO: Array '{array_name_str}' creado dinámicamente para SEQ{sequencer_index_target}.")
                                if 0 <= index < len(target_array_dict.get(array_name_str, [])):
                                    try:
                                        is_float_array = any(substr in array_name_str for substr in ["prob", "factor", "length", "shift"])
                                        final_value = float(value_to_set_any) if is_float_array else int(value_to_set_any)
                                        target_array_dict[array_name_str][index] = final_value
                                        if monitor_active:
                                            log_target = f"SEQ{sequencer_index_target}" if sequencer_index_target is not None else ("CH" if is_channel_array else "GLB")
                                            print(f"     ⇢ SET: {log_target}:{array_name_str}[{index}] = {final_value}")
                                        if sequencer_index_target is not None and array_name_str in ["shift_array", "swing_array"]:
                                            sequencers_state[sequencer_index_target]['schedule_needs_rebuild'] = True
                                    except (ValueError, TypeError) as e:
                                        if monitor_active: print(f"Adv ({filter_id_for_debug}): Error convirtiendo valor para {array_name_str}[{index}]: {e}. Valor '{value_to_set_any}'")

    if "arp_id" in out_conf:
        arp_id_eval = get_evaluated_value_from_output_config(out_conf["arp_id"], -1, current_output_eval_context, filter_id_for_debug, "arp_id")
        if arp_id_eval == -1: return []
        arp_id = int(arp_id_eval)
        if arp_id not in arpeggiator_templates: arpeggiator_templates[arp_id] = {}
        for param_key, param_expr in out_conf.items():
            if param_key in ['arp_id', '_comment'] or re.compile(r"^\s*(note|note_on|note_off|cc|pc)\s*\((.+)\)\s*$").match(str(param_key)): continue
            resolved_value = get_evaluated_value_from_output_config(param_expr, None, current_output_eval_context, filter_id_for_debug, param_key)
            if resolved_value is not None: arpeggiator_templates[arp_id][param_key] = resolved_value
        for instance in arpeggiator_instances.values():
            if instance['config'].get('arp_id') == arp_id: instance['config'].update(arpeggiator_templates[arp_id])
        if base_context_for_this_output.get('event_type_in_ctx') not in ['note_on', 'note_off']: return []
        final_template = ARP_DEFAULTS.copy(); final_template.update(arpeggiator_templates.get(arp_id, {}))
        ch_out_arp_expr = final_template.get("channel_out", base_context_for_this_output.get('ch0_in_ctx', 0) + 1)
        final_ch_out_eval = get_evaluated_value_from_output_config(ch_out_arp_expr, 1, current_output_eval_context, filter_id_for_debug, "channel_out")
        final_ch_out_arp = max(0, min(15, int(final_ch_out_eval) - 1))
        instance_key = (arp_id, final_ch_out_arp)
        if instance_key not in arpeggiator_instances:
             arpeggiator_instances[instance_key] = {'config': final_template, 'is_playing': False, 'tick_counter': 0, 'active_step': 0, 'input_notes': [], 'arp_pattern': [], 'arp_velocity_pattern': [], 'pending_note_offs': [], 'is_armed': False, 'direction_state': 'up', 'direction_index': 0}
             if monitor_active: print(f"     ⇢ ARP: New instance created for ({arp_id}, {final_ch_out_arp})")
        else: arpeggiator_instances[instance_key]['config'].update(final_template)
        notes_to_send = get_evaluated_value_from_output_config(out_conf.get("value_1_out"), [base_context_for_this_output.get('value_in_1_ctx')], current_output_eval_context, filter_id_for_debug, "Arp.Val1")
        if not isinstance(notes_to_send, list): notes_to_send = [notes_to_send]
        velocity_to_send = get_evaluated_value_from_output_config(out_conf.get("value_2_out"), base_context_for_this_output.get('value_in_2_ctx'), current_output_eval_context, filter_id_for_debug, "Arp.Val2")
        update_arp_input(instance_key, notes_to_send, velocity_to_send, base_context_for_this_output['event_type_in_ctx'])
        return []

    # --- 3. Unificar parámetros para la generación de MIDI ---
    output_messages_and_meta = []
    params = {}
    shortcut_pattern = re.compile(r"^\s*(note|note_on|note_off|cc|pc)\s*\((.+)\)\s*$")
    
    # Buscamos atajos de SALIDA solo en el bloque de output actual
    shortcut_actions = {k: v for k, v in out_conf.items() if isinstance(k, str) and shortcut_pattern.match(k)}

    if shortcut_actions:
        key, value = list(shortcut_actions.items())[0]
        match = shortcut_pattern.match(key)
        keyword, val1_expr = match.groups()

        params['event_type_expr'] = {'note': 'note_on', 'cc': 'control_change', 'pc': 'program_change'}.get(keyword, keyword)
        params['val1_expr'] = val1_expr
        params['val2_expr'] = value
    else:
        params['event_type_expr'] = out_conf.get("event_out")
        params['val1_expr'] = out_conf.get("value_1_out")
        params['val2_expr'] = out_conf.get("value_2_out")

    # Para canal y dispositivo, usamos el del output si existe, si no, el del filtro padre
    params['channel_expr'] = out_conf.get("channel_out", filter_config_parent_ref.get("channel_out"))
    params['device_out_alias'] = out_conf.get("device_out", filter_config_parent_ref.get("device_out"))

    # --- 4. Lógica de generación de MIDI unificada ---
    out_dev_alias = params['device_out_alias']
    if not out_dev_alias:
        return []

    ch_out_expr = params['channel_expr']
    final_ch_out_clamped = 0
    if ch_out_expr is not None:
        final_ch_out_eval = get_evaluated_value_from_output_config(ch_out_expr, 1, current_output_eval_context, filter_id_for_debug, f"Out.{i_out_idx}.Ch")
        final_ch_out_clamped = max(0, min(15, int(final_ch_out_eval) - 1))
    else:
        final_ch_out_clamped = base_context_for_this_output.get('ch0_in_ctx', 0)

    is_sequencer_call = isinstance(filter_id_for_debug, str) and filter_id_for_debug.startswith("SEQ")
    default_event_type = 'note_on' if is_sequencer_call else base_context_for_this_output.get('event_type_in_ctx', 'note_on')
    final_event_type_out_str = get_evaluated_value_from_output_config(params['event_type_expr'], default_event_type, current_output_eval_context, filter_id_for_debug, f"Out.{i_out_idx}.event_out")


    default_val1 = base_context_for_this_output.get('note_out' if is_sequencer_call and final_event_type_out_str in ['note_on', 'note'] else 'value_in_1_ctx', 0)
    evaluated_val1 = get_evaluated_value_from_output_config(params['val1_expr'], default_val1, current_output_eval_context, filter_id_for_debug, f"Out.{i_out_idx}.Val1")

    default_val2 = base_context_for_this_output.get('velocity_out' if is_sequencer_call and final_event_type_out_str in ['note_on', 'note'] else 'value_in_2_ctx', 0)
    evaluated_val2 = get_evaluated_value_from_output_config(params['val2_expr'], default_val2, current_output_eval_context, filter_id_for_debug, f"Out.{i_out_idx}.Val2")


    if VERBOSE_MODE:
        verbose_print(f"    - DEBUG_OUT [{filter_id_for_debug}.{i_out_idx}]:")
        verbose_print(f"      - Evento: '{final_event_type_out_str}', Canal: {final_ch_out_clamped + 1}")
        verbose_print(f"      - Valor1: {evaluated_val1}, Valor2: {evaluated_val2}")
        verbose_print(f"      - Destino: '{out_dev_alias}'")

    notes_to_process = evaluated_val1 if isinstance(evaluated_val1, list) else [evaluated_val1]
    output_msg_value2_encoded = int(evaluated_val2) if isinstance(evaluated_val2, (int, float)) else 0

    for note_val in notes_to_process:
        final_val1_out_eval = int(note_val) if isinstance(note_val, (int, float)) else 0
        if final_event_type_out_str in ['note_on', 'note_off']:
            final_val1_out_eval += int(user_variables.get('global_transpose', 0))

        output_msg = None
        try:
            mido_event_type = final_event_type_out_str
            if mido_event_type == 'note':
                mido_event_type = 'note_on'
            elif mido_event_type == 'cc':
                mido_event_type = 'control_change'
            elif mido_event_type == 'pc':
                mido_event_type = 'program_change'
            

            if mido_event_type in ["note_on", "note_off"]:
                output_msg = mido.Message(mido_event_type, channel=final_ch_out_clamped, note=max(0, min(127, final_val1_out_eval)), velocity=max(0, min(127, output_msg_value2_encoded)))
            elif mido_event_type  == "control_change":
                output_msg = mido.Message('control_change', channel=final_ch_out_clamped, control=max(0, min(127, final_val1_out_eval)), value=max(0, min(127, output_msg_value2_encoded)))
            elif mido_event_type  == "program_change":
                output_msg = mido.Message('program_change', channel=final_ch_out_clamped, program=max(0, min(127, final_val1_out_eval)))
        except Exception as e:
            print(f"ERROR Creando Msg: {e}")

        if output_msg:
            target_port_obj_to_use = None
            out_dev_sub = device_aliases_g.get(out_dev_alias, out_dev_alias)
            for p_name, p_info in mido_ports_map_g.items():
                if p_info["type"] == "out" and out_dev_sub.lower() in p_name.lower():
                    target_port_obj_to_use = p_info["obj"]
                    break
            if target_port_obj_to_use:
                output_messages_and_meta.append((output_msg, target_port_obj_to_use, out_dev_alias, filter_id_for_debug, final_event_type_out_str, None))

    return output_messages_and_meta



def execute_all_outputs_for_filter(f_config, base_context, current_version, device_aliases_g, mido_ports_map_g, is_virtual_mode_now, virtual_out_obj=None, virtual_out_name=""):
    outputs_generated_by_this_filter = []
    output_configs_list = f_config.get("output", [])
    filter_id_str = f_config.get("_filter_id_str", "UnknownFilter")

    for key, value in f_config.items():
        if key in user_variables:
            temp_out_conf = {key: value}
            process_single_output_block(
                temp_out_conf, -1, base_context, f_config, f_config.get('_filter_id_str'), 
                current_version, device_aliases_g, mido_ports_map_g, 
                is_virtual_mode_now, virtual_out_obj, virtual_out_name
            )

    # Luego, procesamos el bloque "output" si existe
    output_configs_list = f_config.get("output", [])
    if not isinstance(output_configs_list, list):
        output_configs_list = []

    filter_id_str = f_config.get("_filter_id_str", "UnknownFilter")


    for i_output_block, out_conf_item in enumerate(output_configs_list):
        if not isinstance(out_conf_item, dict): continue

        if filter_id_str == "SEQ": # Esta lógica solo aplica al secuenciador
            seq_out_id_expr = out_conf_item.get("seq_out_id")
            if seq_out_id_expr is not None:
                seq_out_id = int(get_evaluated_value_from_output_config(seq_out_id_expr, -1, base_context, "SEQ", "seq_out_id"))
                if seq_out_id != -1:
                    mute_array = sequencer_arrays.get('seq_out_mute', [])
                    if 0 <= seq_out_id < len(mute_array) and mute_array[seq_out_id] == 1:
                        continue 
        
        output_result_tuple_or_list = process_single_output_block( out_conf_item, i_output_block, base_context, f_config, filter_id_str, current_version, device_aliases_g, mido_ports_map_g, is_virtual_mode_now, virtual_out_obj, virtual_out_name
        )
        if output_result_tuple_or_list: 
            outputs_generated_by_this_filter.extend(output_result_tuple_or_list)
    return outputs_generated_by_this_filter

def summarize_active_processing_config(active_filters_list, device_aliases_map, opened_ports_map, connection_map,
                                       is_virtual_mode, vp_in_name="", vp_out_name=""):
    print("\n--- Configuración ---")
    if is_virtual_mode:
        print("[!] MODO PUERTO VIRTUAL ACTIVADO")
        print(f"    - Entrada Virtual: '{vp_in_name}'")
        print(f"    - Salida Virtual:  '{vp_out_name}'")

    if not active_filters_list and not sequencers_state and not arpeggiator_templates:
        print("No hay filtros ni módulos activos.")
        print("----------------------------------------------------")
        return
        
    print(f"Versión: {available_versions}")
    if device_aliases_map: print(f"Alias: {device_aliases_map}")
    
    if opened_ports_map:
        print("Puertos abiertos:")
        for port_name, port_info in opened_ports_map.items():
            alias_str = f"(por '{port_info['alias_used']}')" 
            if port_info['alias_used'] == port_name or port_info['alias_used'] in ["* (default)", "CUALQUIERA (default)"]:
                alias_str = f"({port_info['alias_used']})" if port_info['alias_used'] in ["* (default)", "CUALQUIERA (default)"] else ""
            print(f"  - [{port_info['type'].upper()}] '{port_name}' {alias_str.strip()}")
    else: print("\[!]: No hay puertos MIDI abiertos.")

    if connection_map:
        print("\n--- Mapa de Conexiones ---")
        sorted_inputs = sorted(connection_map.keys())
        for input_alias in sorted_inputs:
            if connection_map[input_alias]:
                print(f"[IN]  {input_alias}")
                sorted_outputs = sorted(list(connection_map[input_alias]))
                for output_alias in sorted_outputs:
                    print(f"  └─> [OUT] {output_alias}")

    verbose_print("\n--- Filtros de Eventos --- ")
    for i, f_config in enumerate(active_filters_list):
        filter_id_str = f_config.get('_filter_id_str', f"F{i}")
        source_file_info = f"(de {f_config.get('_source_file', 'Fuente Desconocida')})"
        verbose_print(f"\n{filter_id_str}: {source_file_info}")
        filter_comment = f_config.get("_comment");
        if filter_comment: verbose_print(f"  [[ {filter_comment} ]]")
        version_cond = f_config.get("version");
        if version_cond is not None: verbose_print(f"  Versiones: {version_cond}")
        else: verbose_print(f"  Versiones: Todas")
        
        dev_in_alias = f_config.get("device_in"); dev_in_display = f"{dev_in_alias}"
        if dev_in_alias in device_aliases_map: dev_in_display += f" (alias de '{device_aliases_map[dev_in_alias]}')"
        else: dev_in_display += " (subcadena directa)"
        verbose_print(f"  [IN]: '{dev_in_display}'")
        
        conditions = []
        if "ch_in" in f_config: conditions.append(f"Canal: {f_config['ch_in']}")
        if "event_in" in f_config: conditions.append(f"Evento: {f_config['event_in']}")
        if "value_1_in" in f_config: conditions.append(f"Valor1: {f_config['value_1_in']}")
        if "value_2_in" in f_config: conditions.append(f"Valor2: {f_config['value_2_in']}")
        
        is_cc_filter_type = False; filter_event_type_config = f_config.get("event_in")
        if isinstance(filter_event_type_config, str) and filter_event_type_config.lower() == "cc": is_cc_filter_type = True
        elif isinstance(filter_event_type_config, list) and "cc" in [str(et).lower() for et in filter_event_type_config]: is_cc_filter_type = True
        
        if is_cc_filter_type:
            cc_type_val = f_config.get("cc_type_in", "abs")
            proc_str = f"Tipo CC: {cc_type_val}"
            if cc_type_val == "abs_relative": 
                abs2rel_factor_val = f_config.get("abs2rel_factor", 2.0)    
                threshold_val = f_config.get("threshold", 0)  
                proc_str += f" (Factor: {abs2rel_factor_val}, Umbral Delta: {threshold_val})"
            conditions.append(proc_str)

        if conditions:
            verbose_print(f"  Filtro Entrada:")
            for cond in conditions: verbose_print(f"    - {cond}")

        default_device_out_at_filter_level = f_config.get("device_out")
        if default_device_out_at_filter_level:
            resolved_default_out = device_aliases_map.get(default_device_out_at_filter_level, default_device_out_at_filter_level)
            actual_port_for_default = f"'{resolved_default_out}' (no abierto/encontrado)"
            for p_name, p_info in opened_ports_map.items():
                if p_info["type"] == "out" and (resolved_default_out.lower() in p_name.lower() or default_device_out_at_filter_level == p_info.get("alias_used")):
                    actual_port_for_default = f"'{p_name}'"; break
            verbose_print(f"  [OUT Default Filtro]: '{default_device_out_at_filter_level}' (hacia {actual_port_for_default})")



        outputs = f_config.get("output", [])
        if outputs and isinstance(outputs, list):
            verbose_print(f"  Procesos ({len(outputs)}):")
            for j, out_conf in enumerate(outputs):
                if not isinstance(out_conf, dict): continue
                output_comment = out_conf.get("_comment"); output_title = f"    {j+1}_Output:"
                if output_comment: output_title += f" ({output_comment})"
                verbose_print(output_title)
                
                out_dev_alias_specific = out_conf.get("device_out")
                effective_out_dev_alias = out_dev_alias_specific if out_dev_alias_specific is not None else default_device_out_at_filter_level

                if not effective_out_dev_alias:
                    is_only_user_var_assign = True
                    has_any_midi_param = False
                    for k_out_check in out_conf.keys():
                        if k_out_check.startswith("user_var_"): continue
                        if k_out_check == "_comment": continue
                        has_any_midi_param = True; break 
                    # if has_any_midi_param:
                        # print(f"      AVISO: Output sin 'device_out' y sin default en filtro. No se enviará MIDI.")
                else: # Sí hay un effective_out_dev_alias
                    out_dev_resolved_substring = device_aliases_map.get(effective_out_dev_alias, effective_out_dev_alias)
                    actual_port_name_for_output_display = f"'{out_dev_resolved_substring}' (no abierto/encontrado)"
                    for opened_port_name, opened_port_info in opened_ports_map.items():
                        if opened_port_info["type"] == "out":
                            if out_dev_resolved_substring.lower() in opened_port_name.lower() or \
                            effective_out_dev_alias == opened_port_info.get("alias_used"):
                                actual_port_name_for_output_display = f"'{opened_port_name}'"; break
                    
                    source_of_device_out = ""
                    if out_dev_alias_specific is not None:
                        source_of_device_out = "(específico)"
                    elif default_device_out_at_filter_level is not None:
                        source_of_device_out = "(default del filtro)"
                    verbose_print(f"      [OUT] '{effective_out_dev_alias}' {source_of_device_out} (hacia {actual_port_name_for_output_display})")
                

                
                out_details = []
                # Helper local para simplificar
                def add_detail_summary(key, display_name):
                    val = out_conf.get(key)
                    if val is not None: out_details.append(f"{display_name}: {val}")

                add_detail_summary("channel_out", "Canal Salida")
                add_detail_summary("event_out", "Tipo Evento Salida")
                add_detail_summary("cc_type_out", "Tipo CC Salida")
                add_detail_summary("value_1_out", "Valor1 Salida")
                add_detail_summary("value_2_out", "Valor2 Salida")
                if "sysex_data" in out_conf: add_detail_summary("sysex_data", "Datos SysEx")
                
                # Mostrar asignaciones a user_var_X si existen en la configuración del output
                for k_user_var in out_conf.keys():
                    if k_user_var.startswith("var_") and k_user_var in user_variables: # user_named_vars es global
                        add_detail_summary(k_user_var, f"Asigna a {k_user_var}")
                
                if out_details:
                    for detail in out_details: verbose_print(f"        - {detail}")
                else:
                    # Comprobar si era solo para user_vars y no tenía device_out
                    is_only_user_var_output = True
                    if effective_out_dev_alias: # Si tiene device_out, no es "solo user_var"
                        is_only_user_var_output = False
                    else: # No tiene device_out, verificar si solo tiene claves user_var o _comment
                        for k_check in out_conf.keys():
                            if not (k_check.startswith("user_var_") or k_check == "_comment"):
                                is_only_user_var_output = False; break
                    
                    if not is_only_user_var_output: # Si tenía otros parámetros pero no se listaron (improbable si add_detail_summary es completo)
                        verbose_print(f"        (valores por defecto para parámetros no especificados)")
            
    print("----------------------------------------------------")


def process_osc_event_new_logic(address, args, filter_config, current_active_version_global, device_aliases_global, mido_ports_map, is_virtual_mode_now, virtual_out_obj=None, virtual_out_name=""):
    """Procesa un evento OSC contra una configuración de filtro OSC."""
    
    # 1. Comprobar si el filtro aplica a este evento OSC
    if filter_config.get("address") != address:
        return [] # La dirección no coincide

    base_context_for_outputs = {'args': list(args)}
    base_context_for_outputs.update(user_variables)

    if "if" in filter_config:
        if_cond = filter_config["if"]
        if not get_evaluated_value_from_output_config(if_cond, False, base_context_for_outputs, filter_config.get('_filter_id_str'), "if"):
            return [] # La condición 'if' no se cumple

    # 2. Si las condiciones se cumplen, ejecutar todas las acciones del bloque 'output'
    # Esta llamada reutiliza el mismo motor que los filtros MIDI para garantizar consistencia.
    generated_outputs_with_meta = execute_all_outputs_for_filter(
        filter_config, 
        base_context_for_outputs, 
        current_active_version_global, 
        device_aliases_global, 
        mido_ports_map, 
        is_virtual_mode_now, 
        virtual_out_obj, 
        virtual_out_name
    )

    return generated_outputs_with_meta



# --- Helper Function para parsear condiciones de valor ---
def _check_value_condition(condition_config, actual_value):
    if actual_value is None: return False # No hay valor para comparar

    if isinstance(condition_config, (int, float)):
        return actual_value == condition_config
    elif isinstance(condition_config, list):
        return actual_value in condition_config
    elif isinstance(condition_config, str):
        condition_str = condition_config.strip()
        # Rangos: "min-max"
        range_match = re.match(r"^\s*(\d+)\s*-\s*(\d+)\s*$", condition_str)
        if range_match:
            try:
                min_val = int(range_match.group(1))
                max_val = int(range_match.group(2))
                return min_val <= actual_value <= max_val
            except ValueError: return False # Malformado

        # Comparaciones: ">X", ">=X", "<X", "<=X", "==X" (==X es redundante pero puede incluirse)
        comp_match = re.match(r"^\s*(>=|<=|>|<|==)\s*(-?\d+)\s*$", condition_str) # Añadido -? para números negativos
        if comp_match:
            operator = comp_match.group(1)
            try:
                limit = int(comp_match.group(2))
                if operator == ">": return actual_value > limit
                if operator == ">=": return actual_value >= limit
                if operator == "<": return actual_value < limit
                if operator == "<=": return actual_value <= limit
                if operator == "==": return actual_value == limit
            except ValueError: return False # Malformado
        
        # Si no es ninguno de los formatos especiales, y es un string, no coincide (a menos que quieras parsear "eval")
        return False 
    return False # Tipo de condición no soportado




def process_midi_event_new_logic(original_msg_or_dummy, msg_input_port_name_or_dummy, filter_config, current_active_version_global, device_aliases_global, mido_ports_map, is_virtual_mode_now, virtual_out_obj=None, virtual_out_name=""):
    global cc_value_sent, cc_value_control
    
    if msg_input_port_name_or_dummy != DUMMY_PORT_NAME_FOR_VERSION_TRIGGER and original_msg_or_dummy is None:
        return ([], None)
    
    if original_msg_or_dummy.type == 'note_on' and original_msg_or_dummy.velocity == 0:
        effective_msg_for_context = mido.Message('note_off', channel=original_msg_or_dummy.channel, note=original_msg_or_dummy.note, velocity=0)
    else:
        effective_msg_for_context = original_msg_or_dummy.copy()
    
    is_version_trigger_call = (msg_input_port_name_or_dummy == DUMMY_PORT_NAME_FOR_VERSION_TRIGGER)

    # --- INICIO: Lógica de desacoplamiento de filtros ---
    f_config_processed = None
    shortcut_pattern = re.compile(r"^\s*(note|note_on|note_off|cc|pc)\s*\((.+)\)\s*$")
    
    shortcut_key_found = None
    for key in filter_config.keys():
        if isinstance(key, str) and shortcut_pattern.match(key):
            shortcut_key_found = key
            break

    if shortcut_key_found:
        # Es un filtro de atajo. Lo transformamos a un filtro estándar.
        temp_config = filter_config.copy()
        action_block = temp_config.pop(shortcut_key_found)
        if isinstance(action_block, dict):
            temp_config.update(action_block)
        
        match = shortcut_pattern.match(shortcut_key_found)
        keyword, value_expr = match.groups()
        keyword_map = {'note': 'note_on', 'note_on': 'note_on', 'note_off': 'note_off', 'cc': 'control_change', 'pc': 'program_change'}
        temp_config['event_in'] = keyword_map.get(keyword, keyword)
        temp_config['value_1_in'] = value_expr
        f_config_processed = temp_config
    else:
        # Es un filtro estándar. Lo usamos tal cual.
        f_config_processed = filter_config
    # --- FIN: Lógica de desacoplamiento ---

    if "version" in f_config_processed:
        version_cond = f_config_processed["version"]
        if not ((isinstance(version_cond, int) and version_cond == current_active_version_global) or \
                (isinstance(version_cond, list) and current_active_version_global in version_cond)):
            return ([], None)
    
    filter_device_in_alias = f_config_processed.get("device_in")
    if not is_version_trigger_call:
        if filter_device_in_alias is None: return ([], None)
        device_in_substring = device_aliases_global.get(filter_device_in_alias, filter_device_in_alias)
        if device_in_substring.lower() not in msg_input_port_name_or_dummy.lower(): return ([], None)
    elif filter_device_in_alias is not None:
        return ([], None)

    ch0_in_ctx = getattr(effective_msg_for_context, 'channel', -1)
    event_type_in_ctx = effective_msg_for_context.type
    value_in_1_ctx, value_in_2_ctx = 0, 0

    if event_type_in_ctx in ['note_on', 'note_off']:
        value_in_1_ctx = effective_msg_for_context.note
        value_in_2_ctx = effective_msg_for_context.velocity
    elif event_type_in_ctx == 'control_change':
        value_in_1_ctx = effective_msg_for_context.control
        value_in_2_ctx = effective_msg_for_context.value
    elif event_type_in_ctx == 'program_change':
        value_in_1_ctx = effective_msg_for_context.program
    
    base_context_for_outputs = {
        'ch0_in_ctx': ch0_in_ctx, 'value_in_1_ctx': value_in_1_ctx, 'value_in_2_ctx': value_in_2_ctx,
        'event_type_in_ctx': event_type_in_ctx, 'cc_type_in_ctx': "abs"
    }

    if not is_version_trigger_call:
        if "event_in" in f_config_processed:
            event_conditions = f_config_processed["event_in"]
            if not isinstance(event_conditions, list):
                event_conditions = [event_conditions]
            
            normalized_conditions = []
            for cond in event_conditions:
                cond_lower = str(cond).lower()
                if cond_lower == "note":
                    normalized_conditions.extend(["note_on", "note_off"])
                elif cond_lower == "cc":
                    normalized_conditions.append("control_change")
                elif cond_lower == "pc":
                    normalized_conditions.append("program_change")
                else:
                    normalized_conditions.append(cond_lower)
            
            if event_type_in_ctx.lower() not in normalized_conditions:
                return ([], None)
        
        if "ch_in" in f_config_processed:
            cond = evaluate_expression(f_config_processed["ch_in"], base_context_for_outputs)
            # Comparamos la condición con el canal en formato 1-16
            if not _check_value_condition(cond, ch0_in_ctx + 1): return ([], None)
        if "value_1_in" in f_config_processed:
            cond = evaluate_expression(f_config_processed["value_1_in"], base_context_for_outputs)
            if not _check_value_condition(cond, value_in_1_ctx): return ([], None)
        if "value_2_in" in f_config_processed:
            cond = evaluate_expression(f_config_processed["value_2_in"], base_context_for_outputs)
            if not _check_value_condition(cond, value_in_2_ctx): return ([], None)

    version_action_from_this_filter = None
    if "set_version" in f_config_processed:
        base_context_for_outputs["version"] = current_active_version_global
        version_action_from_this_filter = get_evaluated_value_from_output_config(f_config_processed["set_version"], None, base_context_for_outputs, f_config_processed.get('_filter_id_str', 'ID?'), "set_version")

    generated_outputs_with_meta = execute_all_outputs_for_filter(f_config_processed, base_context_for_outputs, current_active_version_global, device_aliases_global, mido_ports_map, is_virtual_mode_now, virtual_out_obj, virtual_out_name)

    if not is_version_trigger_call and original_msg_or_dummy and original_msg_or_dummy.type == 'control_change':
        cc_value_control[(original_msg_or_dummy.channel, original_msg_or_dummy.control)] = original_msg_or_dummy.value
        
    return (generated_outputs_with_meta, version_action_from_this_filter)



def process_version_activated_filters(new_version_activated, all_filters_list, device_aliases_g, mido_ports_map_g, is_virtual_mode_now, virtual_out_obj=None, virtual_out_name=""):
    global monitor_active, cc_value_sent # Para logueo y actualización de L_out
    
    verbose_print(f"[*] Procesando filtros 'sin device_in' para activación de Versión: {new_version_activated}") # Log opcional
    generated_outputs_for_version_activation = []

    for f_config in all_filters_list:
        if f_config.get("device_in") is None: # CONDICIÓN 1: Sin device_in explícito en JSON
            
            applies_to_this_version_change = False
            version_cond_in_filter = f_config.get("version")

            if version_cond_in_filter is None:
                applies_to_this_version_change = True 
                if monitor_active: verbose_print(f"    V_INFO: Filtro '{f_config.get('_filter_id_str', 'ID?')}': Sin device_in y sin 'version' -> activando para V{new_version_activated}.")
            elif isinstance(version_cond_in_filter, int) and version_cond_in_filter == new_version_activated:
                applies_to_this_version_change = True
            elif isinstance(version_cond_in_filter, list) and new_version_activated in version_cond_in_filter:
                applies_to_this_version_change = True

            if applies_to_this_version_change:
                if monitor_active and f_config.get("output"): # Solo loguear si hay outputs definidos para este filtro
                     verbose_print(f"    VU: Variables de usuario de '{f_config.get('_filter_id_str', 'ID?')}' para v{new_version_activated}.")


                outputs_from_filter, _ = process_midi_event_new_logic( DUMMY_MSG_FOR_VERSION_TRIGGER, DUMMY_PORT_NAME_FOR_VERSION_TRIGGER, f_config, new_version_activated, device_aliases_g, mido_ports_map_g, is_virtual_mode_now, virtual_out_obj, virtual_out_name
                )
                if outputs_from_filter:
                    generated_outputs_for_version_activation.extend(outputs_from_filter)


    if generated_outputs_for_version_activation:
        if monitor_active:
            print(f"[*] IN:[Versión {new_version_activated}]")

        for (msg_to_send, dest_port_obj, dest_alias_str, src_filter_id_str, 
             sent_event_type_str, abs_val_for_cc_sent_if_cc) in generated_outputs_for_version_activation:
            
            if dest_port_obj and hasattr(dest_port_obj, "send"):
                try: 
                    dest_port_obj.send(msg_to_send) # Enviar el msg_to_send
                    if monitor_active:
                        log_line = format_midi_message_for_log(msg_to_send, prefix="  \u21E2 OUT: ", active_version=new_version_activated, rule_id_source=src_filter_id_str, target_port_alias_for_log_output=dest_alias_str)
                        if log_line: print(f"{log_line}")
                    
                    if sent_event_type_str == 'control_change':
                        cc_value_sent[(msg_to_send.channel, msg_to_send.control)] = msg_to_send.value 
                except Exception as e_send: 
                    if monitor_active: print(f"      ERR V_SEND: {e_send} (para '{dest_alias_str}', msg: {msg_to_send})")


# --- interactive_rule_selector ---
def interactive_rule_selector():
    RULES_DIR.mkdir(parents=True, exist_ok=True)
    rule_files_paths = sorted([f for f in RULES_DIR.iterdir() if f.is_file() and f.name.endswith('.json')])
    if not rule_files_paths: print(f"No se encontraron archivos .json en el directorio '{RULES_DIR}'."); return None
    selected_indices_ordered = {}; current_selection_index_ui = 0; next_selection_order = 1
    kb = KeyBindings()
    @kb.add('c-c', eager=True)
    @kb.add('c-q', eager=True)
    def _(event): event.app.exit(result=None) # Cancel
    @kb.add('up', eager=True)
    def _(event): nonlocal current_selection_index_ui; current_selection_index_ui = (current_selection_index_ui - 1 + len(rule_files_paths)) % len(rule_files_paths)
    @kb.add('down', eager=True)
    def _(event): nonlocal current_selection_index_ui; current_selection_index_ui = (current_selection_index_ui + 1) % len(rule_files_paths)
    @kb.add('space', eager=True)
    def _(event):
        nonlocal next_selection_order; selected_file_path = rule_files_paths[current_selection_index_ui]
        if selected_file_path in selected_indices_ordered: # Desmarcar
            removed_order = selected_indices_ordered.pop(selected_file_path)
            # Re-numerar los que quedaron después del desmarcado
            for fp_key in list(selected_indices_ordered.keys()): # Iterar sobre copia de claves
                if selected_indices_ordered[fp_key] > removed_order:
                    selected_indices_ordered[fp_key] -= 1
            next_selection_order -=1
        else: # Marcar
            selected_indices_ordered[selected_file_path] = next_selection_order
            next_selection_order += 1
    @kb.add('enter', eager=True)
    def _(event):
        final_selected_paths = []
        if not selected_indices_ordered: # Si no se marcó ninguno, usar el actualmente resaltado
            if rule_files_paths: final_selected_paths.append(rule_files_paths[current_selection_index_ui])
        else: # Usar los marcados, en el orden en que se marcaron
            sorted_selection = sorted(selected_indices_ordered.items(), key=lambda item: item[1])
            final_selected_paths = [item[0] for item in sorted_selection] 
        event.app.exit(result=final_selected_paths) 
    def get_text_for_ui():
        fragments = ["(↑↓: navegar, Esp: marcar/desmarcar, Enter: confirmar)\n"]
        for i, file_path_obj in enumerate(rule_files_paths):
            marker = f"[{selected_indices_ordered[file_path_obj]}]" if file_path_obj in selected_indices_ordered else "[ ]"
            
            # Escapar caracteres especiales en el nombre del fichero para evitar errores de HTML
            line_content = html.escape(f"{marker} {file_path_obj.name}")

            if i == current_selection_index_ui:
                # El carácter de la flecha también se escapa por seguridad
                fragments.append(f"<style bg='ansiblue' fg='ansiwhite'>{html.escape('→')} {line_content}</style>\n")
            else:
                fragments.append(f"  {line_content}\n")
        fragments.append("\nCtrl+C o Ctrl+Q para salir.")
        return HTML("".join(fragments))
    control = FormattedTextControl(text=get_text_for_ui, focusable=True, key_bindings=kb)
    application = Application(layout=Layout(HSplit([Window(content=control)])), full_screen=False, mouse_support=False)
    script_name = Path(sys.argv[0]).name 
    print(f"\nMIDImod ({script_name})\n")
    print(f"--- Selección de Reglas ---")
    print(f"  desde '{RULES_DIR}'")
    selected_paths = application.run() 
    if selected_paths is None: print("Selección cancelada."); return None
    if not selected_paths: print("No se encontraron archivos de reglas."); return [] # Podría ser [] si el usuario da Enter sin seleccionar nada y la lista estaba vacía
    return [p.stem for p in selected_paths] # Devolver solo los nombres base sin .json

# --- list_midi_ports_action ---
def list_midi_ports_action():
    print("Puertos de ENTRADA MIDI disponibles:")
    input_names = mido.get_input_names()
    if not input_names: print("  (Ningún puerto detectado)")
    else:
        for i, name in enumerate(input_names): print(f"  {i}: '{name}'")
    print("\nPuertos de SALIDA MIDI disponibles:")
    output_names = mido.get_output_names()
    if not output_names: print("  (Ningún puerto detectado)")
    else:
        for i, name in enumerate(output_names): print(f"  {i}: '{name}'")
    print("-" * 40)


# --- OSC Server Implementation ---
def _osc_message_handler(address, *args):
    """Pone los mensajes OSC recibidos en una cola para el hilo principal."""
    global osc_message_queue
    osc_message_queue.put((address, args))

def start_osc_server():
    """Inicia el servidor OSC en un hilo separado si está configurado."""
    global osc_config, osc_server_thread, osc_server_instance
    
    receive_conf = osc_config.get("receive")
    if not receive_conf:
        return # No hay configuración de recepción, no hacer nada.

    try:
        ip = receive_conf.get("ip", "127.0.0.1")
        port = receive_conf.get("port", 9000)

        disp = dispatcher.Dispatcher()
        disp.map("*", _osc_message_handler) # Capturar todas las direcciones

        osc_server_instance = osc_server.ThreadingOSCUDPServer((ip, port), disp)
        
        osc_server_thread = threading.Thread(target=osc_server_instance.serve_forever)
        osc_server_thread.daemon = True
        osc_server_thread.start()
        
        print(f"\n[*] Servidor OSC escuchando en {ip}:{port}")

    except Exception as e:
        print(f"\n[!!!] ERROR al iniciar el servidor OSC: {e}")
        osc_server_instance = None
        osc_server_thread = None


def _cleanup_for_reload():
    """Preserva el estado de los módulos activos y limpia las configuraciones recargables."""
    global sequencers_state, persisted_sequencer_states, monitor_active

    print("[*] Limpiando configuración actual...")

    # Preservar estado de secuenciadores activos
    persisted_sequencer_states.clear()
    for seq_state in sequencers_state:
        if seq_state.get('is_playing') and 'seq_id' in seq_state.get('config', {}):
            seq_id = seq_state['config']['seq_id']
            persisted_sequencer_states[seq_id] = {
                'is_playing': True,
                'tick_counter': seq_state.get('tick_counter', 0),
                'last_known_tick': seq_state.get('last_known_tick', -1),
                'active_step': seq_state.get('active_step', 0)
            }
            if monitor_active:
                print(f"  - Preservando estado del secuenciador en reproducción: '{seq_id}'")

    # Enviar panic a los puertos ANTES de limpiarlos
    for port_info in opened_ports_tracking.values():
        if port_info["type"] == "out" and port_info["obj"] and not port_info["obj"].closed:
            try:
                for channel in range(16):
                    port_info["obj"].send(mido.Message('control_change', channel=channel, control=123, value=0))
            except Exception as e:
                print(f"  [!] Adv: No se pudo enviar 'All Notes Off' a '{port_info['obj'].name}': {e}")

    # Limpiar solo las configuraciones, no los recursos (puertos)
    clear_reloadable_state()


def load_configuration(rule_files_to_load, base_dir, is_virtual_mode, vp_in_name, vp_out_name):
    """Carga toda la configuración desde una lista de archivos y gestiona los puertos de forma inteligente."""
    global global_device_aliases, all_loaded_filters, user_variables, sequencers_state, arpeggiator_templates, opened_ports_tracking
    global active_input_handlers, transport_out_port_obj, virtual_output_port_object_ref, full_json_contents
    global active_scales, user_ordered_scale_names, user_ordered_duration_names
    global osc_config, osc_send_clients, all_loaded_osc_filters, osc_server_instance

    # --- Carga de Ficheros y Definición de Requisitos ---
    osc_conf_from_rules = None
    osc_conf_source_file = None
    if not osc_server_instance:
        osc_conf_file = Path("./midimod.conf.json")
        if osc_conf_file.is_file():
            conf_content = _load_json_file_content(osc_conf_file)
            if conf_content and "osc_configuration" in conf_content:
                osc_config = conf_content["osc_configuration"]
                osc_conf_source_file = osc_conf_file.name

    print(f"\n--- Reglas ---")
    print(f"Cargando reglas: {', '.join(rule_files_to_load)}")
    
    files_processed_summary = []
    for rule_file_name_stem in rule_files_to_load:
        file_path = base_dir / (rule_file_name_stem + '.json')
        json_content = _load_json_file_content(file_path)
        if not json_content: continue
        
        full_json_contents.append(json_content)
        global_device_aliases.update(json_content.get("device_alias", {}))
        
        if not osc_conf_source_file and "osc_configuration" in json_content:
            osc_conf_from_rules = json_content["osc_configuration"]
            osc_conf_source_file = file_path.name

        scale_list_from_file = json_content.get("scale_list")
        if isinstance(scale_list_from_file, list):
            all_known_scales = PREDEFINED_SCALES.copy()
            user_scales_in_file = json_content.get("user_scales", {})
            if isinstance(user_scales_in_file, dict):
                all_known_scales.update(user_scales_in_file)
            for scale_name in scale_list_from_file:
                if isinstance(scale_name, str) and scale_name in all_known_scales:
                    if scale_name not in user_ordered_scale_names: user_ordered_scale_names.append(scale_name)
        
        duration_list_from_file = json_content.get("duration_list")
        if isinstance(duration_list_from_file, list):
            for duration_str in duration_list_from_file:
                if isinstance(duration_str, str) and duration_str not in user_ordered_duration_names:
                    user_ordered_duration_names.append(duration_str)

        filters_from_this_file = json_content.get("midi_filter", [])
        if isinstance(filters_from_this_file, list):
            for i, f_config in enumerate(filters_from_this_file):
                if isinstance(f_config, dict):
                    f_config["_source_file"] = file_path.name
                    f_config["_filter_id_str"] = f"{rule_file_name_stem}.{i}"
                    all_loaded_filters.append(f_config)
        
        osc_filters_from_file = json_content.get("osc_filter", [])
        if isinstance(osc_filters_from_file, list):
            for i, osc_f in enumerate(osc_filters_from_file):
                if isinstance(osc_f, dict):
                    osc_f["_source_file"] = file_path.name
                    osc_f["_filter_id_str"] = f"{rule_file_name_stem}.osc.{i}"
                    all_loaded_osc_filters.append(osc_f)

    user_variables.update(next((content.get("user_variables", {}) for content in full_json_contents if "user_variables" in content), {}))
    if user_variables:
        print("\nVariables de Usuario Globales:")
        for var_name, initial_value in user_variables.items(): print(f"  - {var_name}: {initial_value}")

    # --- Carga de Módulos (Sequencers, Arps) ---
    load_sequencers(full_json_contents, global_device_aliases)
    load_arpeggiators(full_json_contents)
    collect_available_versions_from_filters(all_loaded_filters)

    # --- Gestión Inteligente de Puertos ---
    print("\n--- Gestión de Puertos MIDI ---")
    required_ports = set()
    all_configs = all_loaded_filters + sequencers_state + list(arpeggiator_instances.values())
    for item in all_configs:
        # --- INICIO DE LA CORRECCIÓN ---
        # Extraer el diccionario de configuración real, ya sea un filtro o un módulo de estado
        conf_dict = item.get('config', item)
        # --- FIN DE LA CORRECCIÓN ---

        for key in ["device_in", "clock_in", "device_out"]:
            alias = conf_dict.get(key)
            if alias: required_ports.add(global_device_aliases.get(alias, alias))
        
        outputs = conf_dict.get("output", [])
        if isinstance(outputs, list):
            for out_block in outputs:
                if isinstance(out_block, dict):
                    alias = out_block.get("device_out")
                    if alias: required_ports.add(global_device_aliases.get(alias, alias))

    if "TPT_out" in global_device_aliases:
        required_ports.add(global_device_aliases["TPT_out"])

    # Cerrar puertos que ya no se necesitan
    for port_name, port_info in list(opened_ports_tracking.items()):
        # Comprobamos si la subcadena/alias que se usó para abrirlo sigue siendo requerida
        if port_info["alias_used"] not in required_ports:
            print(f"  - [CLOSE] Puerto '{port_name}' (usado por '{port_info['alias_used']}') ya no es necesario. Cerrando...")
            try:
                port_info["obj"].close()
                del opened_ports_tracking[port_name]
                if port_name in active_input_handlers:
                    del active_input_handlers[port_name]
            except Exception as e:
                print(f"  [!] Error cerrando puerto '{port_name}': {e}")


    # Abrir puertos nuevos que se necesiten
    mido_inputs = mido.get_input_names()
    mido_outputs = mido.get_output_names()

    for alias in required_ports:
        if not alias: continue # Ignorar alias vacíos

        # Intentar abrir como entrada
        port_name_in = find_port_by_substring(mido_inputs, alias)
        if port_name_in and port_name_in not in active_input_handlers:
            try:
                in_port_obj = mido.open_input(port_name_in)
                active_input_handlers[port_name_in] = in_port_obj
                opened_ports_tracking[port_name_in] = {"obj": in_port_obj, "type": "in", "alias_used": alias}
                print(f"  - [OPEN-IN] Abierto '{port_name_in}' (requerido por '{alias}')")
            except Exception as e:
                print(f"  [!] Error abriendo IN '{port_name_in}': {e}")

        # Intentar abrir como salida
        port_name_out = find_port_by_substring(mido_outputs, alias)
        if port_name_out and not any(p_info.get("obj") and p_info["obj"].name == port_name_out for p_info in opened_ports_tracking.values()):
            try:
                out_port_obj = mido.open_output(port_name_out)
                opened_ports_tracking[port_name_out] = {"obj": out_port_obj, "type": "out", "alias_used": alias}
                print(f"  - [OPEN-OUT] Abierto '{port_name_out}' (requerido por '{alias}')")
                if alias == global_device_aliases.get("TPT_out"):
                    transport_out_port_obj = out_port_obj
            except Exception as e:
                print(f"  [!] Error abriendo OUT '{port_name_out}': {e}")

    # --- Finalización ---
    active_filters_final = [f for f in all_loaded_filters if f.get("device_in") is None or any(global_device_aliases.get(f.get("device_in"), f.get("device_in")).lower() in name.lower() for name in active_input_handlers)]
    return active_filters_final, None


def reload_all_configuration(base_dir, is_virtual_mode, vp_in_name, vp_out_name):
    """Orquesta una recarga completa de la configuración."""
    global sequencers_state, persisted_sequencer_states, monitor_active

    print("\n" + "="*50)
    print("RECARGANDO CONFIGURACIÓN EN VIVO")
    print("="*50)
    
    _cleanup_for_reload()
    
    # Recargar con los archivos del directorio live
    rule_files = [f.stem for f in base_dir.iterdir() if f.name.endswith('.json')]
    active_filters, virtual_port_ref = load_configuration(rule_files, base_dir, is_virtual_mode, vp_in_name, vp_out_name)
    
    # --- Lógica para restaurar el estado de los secuenciadores ---
    if persisted_sequencer_states:
        print("\n--- Restauración de Estado de Secuenciadores ---")
        for i, new_seq_state in enumerate(sequencers_state):
            seq_id = new_seq_state.get('config', {}).get('seq_id')
            if seq_id and seq_id in persisted_sequencer_states:
                preserved_state = persisted_sequencer_states[seq_id]
                new_seq_state.update(preserved_state)
                new_seq_state['schedule_needs_rebuild'] = True # Forzar actualización de arrays
                if monitor_active:
                    print(f"  - Estado de reproducción restaurado para el secuenciador '{seq_id}'")
        persisted_sequencer_states.clear() # Limpiar para la próxima recarga

    # Volver a mostrar el resumen
    summarize_active_processing_config(active_filters, global_device_aliases, opened_ports_tracking, {}, is_virtual_mode, vp_in_name, vp_out_name)
    print(f"\n{len(active_filters)} filtro(s) recargados. Reanudando procesamiento...")
    
    # Activar la nueva versión 0 si existe
    process_version_activated_filters(0, active_filters, global_device_aliases, opened_ports_tracking, is_virtual_mode, virtual_port_ref, vp_out_name)
    
    return active_filters, virtual_port_ref



# --- Main Application ---
def main():
    global shutdown_flag, current_active_version, available_versions, RULES_DIR, monitor_active, global_device_aliases
    global cc_value_sent, cc_value_control, user_variables, midimaster_assumed_status, sequencers_state
    global all_loaded_osc_filters 

    initialize_state() 
    signal.signal(signal.SIGINT, signal_handler)

    script_version = "1.40" # Actualizar versión
    help_desc = f"""MIDImod {script_version}: Procesador MIDI avanzado con transformaciones y enrutamiento flexible."""
    help_epilog = f"""
-------------------------------------------------------------------------------
MIDImod {script_version} - Command Line & Interactive Controls
-------------------------------------------------------------------------------

**Basic Syntax:**
  python {Path(sys.argv[0]).name} [rule_files...] [options]

**Arguments & Options:**

  `rule_files...`
    One or more rule file names (without .json) from the '{RULES_DIR_NAME}/' directory.
    If omitted, an interactive selector will launch.

  `--live`
    Activates Live Mode. Rules are loaded from the './{LIVE_RULES_DIR.name}/' directory
    and are automatically reloaded when any .json file in it is saved.

  `--list-ports`
    Lists available MIDI input/output ports and exits.

  `--virtual-ports`
    Enables virtual MIDI ports ('MIDImod_IN', 'MIDImod_OUT') for use
    with DAWs or other software.

  `--vp-in NAME`, `--vp-out NAME`
    Specify custom names for the virtual input and output ports.

  `--no-log`
    Starts without the real-time MIDI monitor.

  `--verbose`
    Enables detailed logging for module loading and value evaluation.

  `--help`, `-h`
    Displays this help message and exits.

**Examples:**

  - List available MIDI ports:
    `python {Path(sys.argv[0]).name} --list-ports`

  - Load rules from 'setup.json' and 'chords.json':
    `python {Path(sys.argv[0]).name} setup chords`

  - Start in Live Mode with rules from the './live' folder:
    `python {Path(sys.argv[0]).name} --live`

  - Use virtual ports with a specific rule file:
    `python {Path(sys.argv[0]).name} daw_integration --virtual-ports`

**Interactive Controls (during execution):**

  `[Spacebar]`   : Cycles to the next available 'version'.
  `[0-9]`        : Jumps directly to a specific 'version' number.
  `m`            : Toggles the MIDI monitor log on/off.
  `[Enter]`      : Sends Start/Stop transport commands to the port
                 aliased as 'TPT_out' in your JSON files.
  `[Ctrl+C]`     : Safely shuts down the script.
-------------------------------------------------------------------------------
"""

    parser = argparse.ArgumentParser(
        prog=Path(sys.argv[0]).name,
        description=help_desc,
        epilog=help_epilog,
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("rule_files", nargs='*', default=None, 
                        help=f"Nombres base (sin .json) de archivos de reglas de './{RULES_DIR_NAME}/'. Si no se da, se abre selector interactivo.")
    parser.add_argument("--list-ports", action="store_true", help="Lista puertos MIDI y sale.")
    parser.add_argument("--no-log", action="store_false", dest="monitor_active_cli", default=True, help="Desactiva monitor MIDI al inicio.")

    parser.add_argument("--virtual-ports", action="store_true", help="Activa el modo de puertos MIDI virtuales.")
    parser.add_argument("--vp-in", type=str, default="MIDImod_IN", metavar="NOMBRE", help="Puerto MIDI virtual de ENTRADA (default: MIDImod_IN).")
    parser.add_argument("--vp-out", type=str, default="MIDImod_OUT", metavar="NOMBRE", help="Puerto MIDI virtual de SALIDA (default: MIDImod_OUT).")
    parser.add_argument("--verbose", action="store_true", help="Muestra detalles adicionales de los filtros.")
    parser.add_argument("--live", action="store_true", help="Activa el modo Live, cargando reglas de './live' y recargando al guardar.")
    args = parser.parse_args()


    if args.list_ports:
        list_midi_ports_action()
        return
    
    is_live_mode = args.live
    
    if is_live_mode:
        print("[*] MODO LIVE ACTIVADO. Cargando reglas de la carpeta '/live'.")
        LIVE_RULES_DIR.mkdir(parents=True, exist_ok=True)
        rule_file_names_to_load = [f.stem for f in LIVE_RULES_DIR.iterdir() if f.name.endswith('.json')]
        rules_base_dir = LIVE_RULES_DIR
    else:
        rules_base_dir = RULES_DIR
        rule_file_names_to_load = args.rule_files
        if not rule_file_names_to_load:
            selected_names = interactive_rule_selector()
            if selected_names is None: return
            if not selected_names: print("Saliendo."); return
            rule_file_names_to_load = selected_names

    global VERBOSE_MODE
    VERBOSE_MODE = args.verbose
    if VERBOSE_MODE:
        print("[!] Modo VERBOSO")

    monitor_active = args.monitor_active_cli

    virtual_port_mode_active = args.virtual_ports
    virtual_input_name = args.vp_in
    virtual_output_name = args.vp_out

    # Llamada a la función de carga que faltaba

    active_filters_final, virtual_output_port_object_ref = load_configuration(
        rule_file_names_to_load, rules_base_dir, virtual_port_mode_active,
        virtual_input_name, virtual_output_name
    )

    # --- Iniciar servidor OSC ---
    start_osc_server()


    if not active_input_handlers and not osc_server_instance:
        print("\nNo hay puertos de ENTRADA (MIDI u OSC) activos. Saliendo.")
        return
    if not active_filters_final and not sequencers_state and not all_loaded_osc_filters:
        print("\nNo hay filtros (MIDI u OSC) ni secuenciadores configurados. Saliendo.")
        return

    summarize_active_processing_config(active_filters_final, global_device_aliases, opened_ports_tracking, {}, virtual_port_mode_active, virtual_input_name, virtual_output_name)

    monitor_status_str = "activo" if monitor_active else "desactivado"


    observer = None
    if is_live_mode:
        reload_queue = Queue()
        event_handler = RuleChangeHandler(reload_queue)
        observer = Observer()
        observer.schedule(event_handler, str(LIVE_RULES_DIR), recursive=False)
        observer.start()
        print(f"[*] Vigilando la carpeta '{LIVE_RULES_DIR}' en busca de cambios...")

        

    print(f"\n{len(active_filters_final)} filtro(s), {len(active_input_handlers)} puerto(s) IN. ")
    if len(available_versions) > 1 or (len(available_versions)==1 and 0 not in available_versions) : # Mostrar si hay más de una o si la única no es 0
        print(f"Versión {current_active_version}/{len(available_versions) - 1} (cambiar con [0-{len(available_versions) - 1}], [Espacio]).")
    print(f"Monitor {monitor_status_str} (cambiar con 'm').")
    print("[!] Ctrl+C para salir. Procesando... \n")

    version_log_header=f"[*] Versión {current_active_version}/{len(available_versions) - 1}" if len(available_versions) > 1 else ""
    print(version_log_header)
    process_version_activated_filters(current_active_version, active_filters_final, global_device_aliases, opened_ports_tracking,
                                    virtual_port_mode_active, virtual_output_port_object_ref, virtual_output_name)


    try:
        while not shutdown_flag:
            # 1. El hilo principal comprueba si hay una solicitud de recarga y la ejecuta.
            if is_live_mode and not reload_queue.empty():
                if reload_queue.get() == "reload":
                    active_filters_final, virtual_output_port_object_ref = reload_all_configuration(
                        LIVE_RULES_DIR, virtual_port_mode_active, virtual_input_name, virtual_output_name
                    )
            
            # 2. El hilo principal continúa con su trabajo normal.
            # --- MANEJO DE TECLADO ---
            kb_char_processed_this_loop = False
            char_input = get_char_non_blocking()
            if char_input:
                kb_char_processed_this_loop = True
                # ... (toda la lógica del teclado se queda igual que antes)
                prev_active_version_kb = current_active_version
                version_changed_by_kb = False
                
                if char_input.isdigit():
                    new_version_attempt = int(char_input)
                    if new_version_attempt in available_versions:
                        if current_active_version != new_version_attempt:
                            current_active_version = new_version_attempt
                            version_changed_by_kb = True
                elif char_input == ' ':
                    if available_versions:
                        try: current_idx = available_versions.index(current_active_version)
                        except ValueError: current_idx = -1
                        current_active_version = available_versions[(current_idx + 1) % len(available_versions)]
                        version_changed_by_kb = True
                elif char_input.lower() == 'm':
                    monitor_active = not monitor_active
                    print(f"[*] Monitor {'activado' if monitor_active else 'desactivado'}")
                elif (char_input == '\r' or char_input == '\n'): # TECLA ENTER
                    if transport_out_port_obj:
                        try:
                            if midimaster_assumed_status == "STOPPED":
                                transport_out_port_obj.send(mido.Message('start'))
                                midimaster_assumed_status = "PLAYING"
                                print(f"[!] Comando START enviado a TPT")
                            elif midimaster_assumed_status == "PLAYING":
                                transport_out_port_obj.send(mido.Message('stop'))
                                midimaster_assumed_status = "STOPPED"
                                print(f"[!] Comando STOP enviado a TPT")
                        except Exception as e:
                            print(f"[!] Error enviando comando a TPT: {e}")
                    elif monitor_active: # Solo loguear si el monitor está activo y no hay puerto
                        print(f"[!] Puerto TPT no disponible.")
                
                if version_changed_by_kb and current_active_version != prev_active_version_kb:
                    print(f"[*] Versión {current_active_version}/{len(available_versions) - 1}")
                    process_version_activated_filters(current_active_version, all_loaded_filters, global_device_aliases, opened_ports_tracking, virtual_port_mode_active, virtual_output_port_object_ref, virtual_output_name)
                elif version_changed_by_kb and char_input.isdigit() and current_active_version == prev_active_version_kb : 
                    print(f"[*] Versión '{char_input}' no disponible o ya activa. Actual: V{current_active_version}.")


            osc_processed_this_loop = False
            while not osc_message_queue.empty():
                osc_processed_this_loop = True
                address, args = osc_message_queue.get()

                if monitor_active:
                    # Imprimir el log de entrada OSC.
                    # El log de la acción (ej. ⇢ SET) se generará automáticamente desde el motor de filtros.
                    print(f"IN:  OSC '{address}' {list(args)}")

                # Iterar por todos los filtros OSC y procesarlos con el motor unificado
                for osc_filter_config in all_loaded_osc_filters:
                    outputs_from_this_filter = process_osc_event_new_logic(
                        address, args, osc_filter_config,
                        current_active_version, global_device_aliases, opened_ports_tracking,
                        virtual_port_mode_active, virtual_output_port_object_ref, virtual_output_name
                    )
                    
                    # Si el filtro OSC genera mensajes MIDI, enviarlos y loguearlos
                    if outputs_from_this_filter:
                        for (msg_to_send, dest_port_obj, alias_log, rule_log, _, _) in outputs_from_this_filter:
                            if dest_port_obj and hasattr(dest_port_obj, "send"):
                                dest_port_obj.send(msg_to_send)
                                if monitor_active:
                                    log_line = format_midi_message_for_log(
                                        msg_to_send, prefix="  ⇢ OUT: ", active_version=current_active_version,
                                        rule_id_source=rule_log, target_port_alias_for_log_output=alias_log
                                    )
                                    if log_line: print(log_line)
                                    

                                    

            # --- 2. PROCESAMIENTO MIDI (ESTRUCTURA CORREGIDA) ---

            
            incoming_messages_this_cycle = []
            for port_full_name, mido_in_port_obj in active_input_handlers.items():
                for msg in mido_in_port_obj.iter_pending():
                    incoming_messages_this_cycle.append({'msg': msg, 'port_name': port_full_name})
            
            midi_event_processed_this_loop = bool(incoming_messages_this_cycle)
            all_generated_outputs_this_cycle = []
            version_change_request = None
            
            if midi_event_processed_this_loop:
                version_before_action = current_active_version
                
                other_messages_to_process = []

                for event in incoming_messages_this_cycle:
                    msg = event['msg']
                    port_name = event['port_name']
                    is_transport_msg = msg.type in ['start', 'stop', 'continue', 'reset', 'clock']


                    if is_transport_msg:
                        # --- 1. Lógica de contadores maestros (para cuantización) ---
                        # Inicializar contador si es la primera vez que vemos este puerto de reloj
                        if port_name not in clock_tick_counters:
                            clock_tick_counters[port_name] = 0
                        
                        if msg.type == 'start':
                            clock_tick_counters[port_name] = 0
                            midimaster_assumed_status = "PLAYING"
                        elif msg.type == 'stop':
                            midimaster_assumed_status = "STOPPED"
                        elif msg.type == 'clock' and midimaster_assumed_status == "PLAYING":
                            clock_tick_counters[port_name] += 1


                        # --- 2. Lógica de distribución a módulos (para reproducción) ---
                        # Distribuir a Sequencers
                        for i, seq_state in enumerate(sequencers_state):
                            if seq_state['clock_in_port_name'] and seq_state['clock_in_port_name'].lower() in port_name.lower():
                                if msg.type == 'start':
                                    seq_conf = seq_state['config']
                                    # Si no se cuantiza, arranca inmediatamente
                                    if not seq_conf.get("quantize_start"):
                                        seq_state['is_playing'] = True
                                        seq_state['tick_counter'] = 0
                                        seq_state['last_known_tick'] = -1
                                        _silence_instance(seq_state, f"SEQ[{i}] start")
                                        _rebuild_sequencer_schedule(i, seq_state) # Reconstruir inmediatamente
                                        if monitor_active: print(f"SQ[{i}] Start (transport)")
                                    # Si se cuantiza, simplemente se "arma"
                                    else:
                                        if not seq_state['is_playing'] and not seq_state['is_armed']:
                                            seq_state['is_armed'] = True
                                            display_grid = seq_conf.get("quantize_start")
                                            if not isinstance(display_grid, str): display_grid = "grid"
                                            if monitor_active: print(f"SQ[{i}] ARMED by transport (waiting for '{display_grid}')")

                                elif msg.type in ['stop', 'reset']:
                                    seq_state['is_playing'] = False
                                    seq_state['is_armed'] = False # Desarmar si se detiene el transporte
                                    if monitor_active: print(f"SQ[{i}] Stop")
                                    # ... (lógica para enviar note_offs pendientes)
                                elif msg.type == 'continue':
                                    seq_state['is_playing'] = True
                                    if monitor_active: print(f"SQ[{i}] Continue")
                                elif msg.type == 'clock' and seq_state['is_playing']:
                                    seq_state['tick_counter'] += 1
                        
                        # Distribuir a Arpegiadores
                        for key, instance in arpeggiator_instances.items():
                            arp_clock_in_alias = instance['config'].get('clock_in', instance['config'].get('device_in'))
                            if arp_clock_in_alias:
                                arp_clock_in_substr = global_device_aliases.get(arp_clock_in_alias, arp_clock_in_alias)
                                if arp_clock_in_substr.lower() in port_name.lower():
                                    if msg.type == 'start':
                                        if not instance['config'].get("quantize_start"):
                                            instance['is_playing'] = True; instance['tick_counter'] = 0; instance['active_step'] = 0; instance['pending_note_offs'].clear()
                                            if monitor_active: print(f"ARP[{key[0]},{key[1]}] Start (transport)")
                                    elif msg.type in ['stop', 'reset']:
                                        instance['is_playing'] = False
                                        instance['is_armed'] = False # Desarmar si se detiene
                                        if monitor_active: print(f"ARP[{key[0]},{key[1]}] Stop")
                                        # ... (lógica para enviar note_offs pendientes)
                                    elif msg.type == 'continue':
                                        instance['is_playing'] = True
                                        if monitor_active: print(f"ARP[{key[0]},{key[1]}] Continue")
                                    elif msg.type == 'clock' and instance['is_playing']:
                                        instance['tick_counter'] += 1
                    else:
                        other_messages_to_process.append(event)

                # 2.2 PROCESAR todos los mensajes restantes contra los filtros
                for event in other_messages_to_process:
                    original_input_msg = event['msg']
                    port_full_name = event['port_name']

                    for event_filter_config in active_filters_final:
                        outputs_from_this_filter, version_action = process_midi_event_new_logic(
                            original_input_msg, port_full_name, event_filter_config,
                            current_active_version, global_device_aliases, opened_ports_tracking,
                            virtual_port_mode_active, virtual_output_port_object_ref, virtual_output_name
                        )
                        if outputs_from_this_filter:
                            all_generated_outputs_this_cycle.extend(outputs_from_this_filter)
                        if version_action is not None and version_change_request is None:
                            # ... (lógica de cambio de versión sin cambios) ...
                            version_change_request = version_action
                            if monitor_active:
                                filter_id_str = event_filter_config.get('_filter_id_str', 'ID?')
                                log_in_vchange = format_midi_message_for_log(original_input_msg, "IN: ", version_before_action,
                                                                          rule_id_source=filter_id_str,
                                                                          input_port_actual_name=port_full_name,
                                                                          device_aliases_global_map=global_device_aliases)
                                if log_in_vchange:
                                    raw_set_version = event_filter_config.get('set_version', 'N/A')
                                    print(f"{log_in_vchange} ⇢ (set_version: '{raw_set_version}' -> '{version_action}')")



                # 2.3 ENVIAR todas las salidas generadas
                if all_generated_outputs_this_cycle:
                    for (msg_to_send, dest_port_obj, _, _,
                         sent_event_type_str, _) in all_generated_outputs_this_cycle:
                        if dest_port_obj and hasattr(dest_port_obj, "send"):
                            try:
                                dest_port_obj.send(msg_to_send)
                                if sent_event_type_str == 'control_change':
                                    cc_value_sent[(msg_to_send.channel, msg_to_send.control)] = msg_to_send.value
                            except Exception as e_send:
                                print(f"  ERR SEND: {e_send}")

                # 2.4 LOGUEAR todo lo que pasó en este ciclo
                if monitor_active:
                    for event in other_messages_to_process:
                        log_line = format_midi_message_for_log(
                            event['msg'], prefix="IN: ", active_version=current_active_version,
                            input_port_actual_name=event['port_name'], device_aliases_global_map=global_device_aliases
                        )
                        if log_line:
                            suffix = ""
                            if not all_generated_outputs_this_cycle:
                                # Comprobar si se envió a un arpegiador (que no genera output inmediato)
                                was_sent_to_arp = False
                                for f_conf in active_filters_final:
                                    # Esta es una comprobación simplificada pero efectiva
                                    if "arp_id" in f_conf.get("output", [{}])[0]:
                                        # Comprobamos si el filtro realmente se aplicó a este mensaje
                                        dev_in_alias = f_conf.get("device_in")
                                        if dev_in_alias:
                                            dev_in_sub = global_device_aliases.get(dev_in_alias, dev_in_alias)
                                            if dev_in_sub.lower() in event['port_name'].lower():
                                                was_sent_to_arp = True
                                                break
                                if not was_sent_to_arp:
                                    suffix = " ⇢ [NOUT]"
                            
                            print(f"{log_line}{suffix}")


                    # Loguear las salidas generadas
                    for out_m_log, _, alias_log, rule_log, _, _ in all_generated_outputs_this_cycle:
                        log_msg_output_formatted = format_midi_message_for_log(
                            out_m_log, prefix="  ⇢ OUT: ", active_version=current_active_version,
                            rule_id_source=rule_log, target_port_alias_for_log_output=alias_log
                        )
                        if log_msg_output_formatted:
                            print(log_msg_output_formatted)
                
                # 2.5 APLICAR cambio de versión si se solicitó
                if version_change_request is not None:
                    new_version = -1
                    action_value = version_change_request
                    if isinstance(action_value, str):
                        action_lower = action_value.lower()
                        if available_versions:
                            try:
                                current_idx = available_versions.index(current_active_version)
                                if action_lower in ["cycle", "cycle_next"]:
                                    new_version = available_versions[(current_idx + 1) % len(available_versions)]
                                elif action_lower == "cycle_previous":
                                    new_version = available_versions[(current_idx - 1 + len(available_versions)) % len(available_versions)]
                            except ValueError:
                                if available_versions: new_version = available_versions[0]
                    elif isinstance(action_value, int):
                        if action_value in available_versions:
                            new_version = action_value
                    
                    if new_version != -1 and new_version != current_active_version:
                        current_active_version = new_version
                        version_changed_by_midi = True
                    
                    if version_changed_by_midi:
                        print(f"[*] Versión {current_active_version}/{len(available_versions) - 1}")
                        process_version_activated_filters(current_active_version, all_loaded_filters, global_device_aliases, opened_ports_tracking, virtual_port_mode_active, virtual_output_port_object_ref, virtual_output_name)

            armed_modules_to_check = []
            for i, s_state in enumerate(sequencers_state):
                if s_state.get('is_armed'):
                    armed_modules_to_check.append({'type': 'seq', 'state': s_state, 'id': i})
            for key, a_state in arpeggiator_instances.items():
                if a_state.get('is_armed'):
                    armed_modules_to_check.append({'type': 'arp', 'state': a_state, 'id': key})

            if armed_modules_to_check:
                for mod in armed_modules_to_check:
                    state = mod['state']
                    config = state['config']
                    quantize_config = config.get("quantize_start")
                    
                    grid_to_use = None
                    if isinstance(quantize_config, str):
                        grid_to_use = quantize_config
                    elif quantize_config is True:
                        grid_to_use = "1/16" 

                    if not grid_to_use:
                        state['is_armed'] = False
                        continue


                    clock_alias_expr = config.get('device_in')
                    if not clock_alias_expr: continue # No se puede cuantizar sin un device_in explícito
                    
                    clock_alias = get_evaluated_value_from_output_config(clock_alias_expr, None, state.get('eval_context',{}), "quantize_launch", "device_in")
                    if not clock_alias: continue

                    clock_port_name = None
                    # Buscar por alias primero, que es más preciso
                    for p_name, p_info in opened_ports_tracking.items():
                        if p_info.get('alias_used') == clock_alias:
                            clock_port_name = p_name
                            break
                    # Si no se encuentra por alias, buscar por subcadena como fallback
                    if not clock_port_name:
                         resolved_substring = global_device_aliases.get(clock_alias, clock_alias)
                         for p_name in opened_ports_tracking.keys():
                              if resolved_substring.lower() in p_name.lower():
                                   clock_port_name = p_name
                                   break
                    
                    if not clock_port_name:
                        if monitor_active: print(f"Adv: No se pudo encontrar un puerto abierto para el reloj '{clock_alias}' del módulo {mod['id']}. No se puede lanzar cuantizado.")
                        continue

                    master_ticks = clock_tick_counters.get(clock_port_name, 0)
                    ppqn = int(config.get('ppqn', 24))
                    ticks_for_quantize = parse_step_duration(grid_to_use, ppqn)

                    if ticks_for_quantize > 0 and master_ticks % ticks_for_quantize == 0:
                        state['is_playing'] = True
                        state['is_armed'] = False
                        state['tick_counter'] = 0
                        state['active_step'] = 0
                        if monitor_active:
                            id_str = f"{mod['type'].upper()}[{mod['id']}]"
                            print(f"[*] {id_str} LAUNCHED (cuantizado a {grid_to_use})")






# --- 3. PROCESAMIENTO DE SECUENCIADORES (LÓGICA FINAL) ---
# midimod.py

            for i, seq_state in enumerate(sequencers_state):
                if not seq_state.get('is_playing', False):
                    continue

                if seq_state.get('schedule_needs_rebuild'):
                    _rebuild_sequencer_schedule(i, seq_state)

                current_tick = seq_state['tick_counter']
                cycle_duration = seq_state.get('current_cycle_duration', 0)

                # Si el ciclo ha terminado, reiniciamos contadores y reconstruimos la agenda para el siguiente.
                if cycle_duration > 0 and current_tick >= cycle_duration:
                    seq_state['tick_counter'] -= cycle_duration
                    current_tick = seq_state['tick_counter']
                    seq_state['last_known_tick'] -= cycle_duration
                    
                    adjusted_offs = []
                    for fire_at, msg, port, alias in seq_state['pending_note_offs']:
                        adjusted_offs.append((fire_at - cycle_duration, msg, port, alias))
                    seq_state['pending_note_offs'] = adjusted_offs
                    
                    # Reconstruimos la agenda inmediatamente para el nuevo ciclo
                    _rebuild_sequencer_schedule(i, seq_state)

                # Procesar Note Offs pendientes
                due_note_offs = [item for item in seq_state['pending_note_offs'] if current_tick >= item[0]]
                if due_note_offs:
                    seq_state['pending_note_offs'] = [item for item in seq_state['pending_note_offs'] if item not in due_note_offs]
                    for _, msg, port, alias in due_note_offs:
                        try:
                            port.send(msg)
                            if monitor_active:
                                log_prefix = f"  \u21E2 SQ[{i}] off:"
                                log_line = format_midi_message_for_log(msg, log_prefix, current_active_version, None, alias)
                                if log_line: print(log_line)
                        except Exception as e:
                            print(f"Err sending scheduled note_off: {e}")

                # Disparar eventos de la agenda
                schedule = seq_state.get('event_schedule', [])
                for event_to_fire in schedule:
                    if event_to_fire['fire_at'] <= current_tick and event_to_fire['fire_at'] > seq_state['last_known_tick']:
                        seq_state['active_step'] = event_to_fire['step']
                        process_sequencer_step(i, seq_state, event_to_fire['fire_at'], opened_ports_tracking, virtual_port_mode_active, virtual_output_port_object_ref, virtual_output_name)
                        seq_state['last_known_tick'] = event_to_fire['fire_at']






            # --- 4. PROCESAMIENTO DE ARPEGIADORES (CORREGIDO) ---
            arp_instances_to_remove = []
            for instance_key, instance_state in list(arpeggiator_instances.items()):
                # verbose_print(f"DBG:   - Proc. {instance_key}: playing={instance_state['is_playing']}, ticks={instance_state['tick_counter']}, pattern_len={len(instance_state['arp_pattern'])}")
                arp_conf = instance_state['config']
                
                due_note_offs = [item for item in instance_state['pending_note_offs'] if instance_state['tick_counter'] >= item[0]]
                for item in due_note_offs:
                    _, msg, port, alias = item
                    try: port.send(msg)
                    except Exception: pass
                    if item in instance_state['pending_note_offs']:
                        instance_state['pending_note_offs'].remove(item)

                if instance_state['is_playing']:
                    # El tick_counter ya fue incrementado por el mensaje de reloj
                    ppqn = int(arp_conf.get('ppqn', ARP_DEFAULTS['ppqn']))
                    step_duration = arp_conf.get('step_duration', ARP_DEFAULTS['step_duration'])
                    ticks_for_step = parse_step_duration(step_duration, ppqn)

                    # verbose_print(f"DBG: Procesando {instance_key}. Ticks: {instance_state['tick_counter']}, Ticks para paso: {ticks_for_step}")


                    if ticks_for_step > 0 and instance_state['tick_counter'] >= ticks_for_step:
                        pattern = instance_state.get('arp_pattern', [])
                        if pattern:
                           current_tick_snapshot = instance_state['tick_counter']
                           process_arpeggiator_step(instance_key, instance_state, opened_ports_tracking, virtual_port_mode_active, virtual_output_port_object_ref, virtual_output_name, current_tick_snapshot)
                           instance_state['tick_counter'] -= ticks_for_step

                           
                           current_step = instance_state.get('active_step', 0)
                           pattern_len = len(pattern)
                           
                           # La lógica compleja se ha ido. Solo avanzamos al siguiente paso.
                           next_step = (current_step + 1) % pattern_len
                           
                           instance_state['active_step'] = next_step if pattern_len > 0 else 0

                
                # Limpieza de instancias detenidas y sin notas pendientes
                elif not instance_state['is_playing'] and not instance_state['input_notes'] and not instance_state['pending_note_offs']:
                    arp_instances_to_remove.append(instance_key)

            for key in arp_instances_to_remove:
                if key in arpeggiator_instances:
                    del arpeggiator_instances[key]
                    if monitor_active: print(f"     ⇢ ARP: Instancia {key} eliminada.")


            # --- 4. PAUSA ---
            if not midi_event_processed_this_loop and not kb_char_processed_this_loop and not osc_processed_this_loop:
                time.sleep(0.001)

    except KeyboardInterrupt:
        if not shutdown_flag: shutdown_flag=True
        print("\nInterrupción por teclado recibida en el bucle principal.")
    except Exception as e_main_loop:
        if not shutdown_flag:
            print(f"\nERROR INESPERADO EN BUCLE PRINCIPAL: {e_main_loop}")
            traceback.print_exc()
    finally:
        print("\nCerrando puertos y deteniendo de MIDImod...")
        if osc_server_instance:
            print("  - Deteniendo servidor OSC...")
            osc_server_instance.shutdown()
        if osc_server_thread:
            osc_server_thread.join()
            print("  - Servidor OSC detenido.")
        # --- INICIO: Detener el Watchdog ---
        if observer:
            observer.stop()
            observer.join()
            print("  Observador de ficheros detenido.")





        for port_name_final, port_data_final in opened_ports_tracking.items():
            port_obj_final = port_data_final.get("obj")
            if port_obj_final and hasattr(port_obj_final,'close') and not port_obj_final.closed:
                try: 
                    port_obj_final.close()
                    print(f"  Puerto '{port_name_final}' (tipo {port_data_final['type']}) cerrado.")
                except Exception as e_close: 
                    print(f"  Error cerrando puerto '{port_name_final}': {e_close}")
        
        # Restaurar termios si se modificó (solo en Linux/macOS)
        if 'termios' in sys.modules and sys.stdin.isatty() and _original_termios_settings:
            try: 
                termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, _original_termios_settings)
                print("  Configuración original de terminal restaurada.")
            except Exception as e_termios:
                print(f"  Error restaurando termios: {e_termios}")
        print("  MIDImod detenido.")

if __name__ == "__main__":
    # Asegurar que el directorio de reglas existe al inicio
    RULES_DIR.mkdir(parents=True, exist_ok=True) 
    
    # Guardar configuración original de termios si es aplicable (Linux/macOS en tty)
    if 'termios' in sys.modules and 'tty' in sys.modules and sys.stdin.isatty():
        try: 
            _original_termios_settings_fd = sys.stdin.fileno()
            _original_termios_settings = termios.tcgetattr(_original_termios_settings_fd)
        except termios.error: # Puede fallar si no es un tty real (ej. en algunos IDEs)
            _original_termios_settings = None 
            _original_termios_settings_fd = -1
    
    initialize_state() # Inicializar ANTES de llamar a main()
    main()