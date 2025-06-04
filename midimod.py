# midimod.py
import mido
import time
import json
import argparse
import traceback
import signal
import os
from pathlib import Path
import sys
import random
import re 

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
shutdown_flag = False
current_active_version = 0
available_versions = {0} 
monitor_active = True 
global_device_aliases = {} 
cc_value_sent = {}
cc_value_control = {}
NUM_USER_VARS = 32 # Define una constante para el número de variables
user_named_vars = {f"var_{i}": 0 for i in range(NUM_USER_VARS)}
cc_input_s_state = {}
active_note_map = {}
global_version_mappers = []
# --- Constantes para la activación por versión ---
DUMMY_MSG_FOR_VERSION_TRIGGER = mido.Message('note_on', channel=0, note=0, velocity=0) 
DUMMY_PORT_NAME_FOR_VERSION_TRIGGER = "_VERSION_TRIGGER_INTERNAL_"

# ARRAY_SIZE = NUM_USER_VARS 
ARRAY_SIZE = 16
named_arrays = {
    "control": [0] * ARRAY_SIZE,
    "trans": [0] * ARRAY_SIZE,
    "offset": [0] * ARRAY_SIZE,
    "prob": [1.0] * ARRAY_SIZE,
    "velo": [100] * ARRAY_SIZE,
    "length": [0] * ARRAY_SIZE,
    "mute": [0] * ARRAY_SIZE,
    "factor": [1.0] * ARRAY_SIZE
}


CC_SENT_UNINITIALIZED = -1

PREDEFINED_SCALES = {
    "major": [0, 2, 4, 5, 7, 9, 11],
    "minor_natural": [0, 2, 3, 5, 7, 8, 10],
    "minor_harmonic": [0, 2, 3, 5, 7, 8, 11],
    "pentatonic_major": [0, 2, 4, 7, 9],
    "pentatonic_minor": [0, 3, 5, 7, 10],
    "chromatic": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11],
    "blues": [0, 3, 5, 6, 7, 10]
}
active_scales = PREDEFINED_SCALES.copy()

def initialize_cc_storage():
    global cc_value_sent, cc_value_control, cc_input_s_state
    for ch in range(16):
        for cc_num in range(128):
            cc_value_sent[(ch, cc_num)] = CC_SENT_UNINITIALIZED 
            cc_value_control[(ch, cc_num)] = 0
            cc_input_s_state[(ch, cc_num)] = CC_SENT_UNINITIALIZED 
# --- Fin Global Configuration ---

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

# --- Helper Functions ---
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
        with open(filepath, 'r', encoding='utf-8') as f: content = json.load(f)
        return content
    except json.JSONDecodeError: print(f"Err: Archivo '{filepath.name}' no es JSON válido.")
    except UnicodeDecodeError: print(f"Err Cod: Archivo '{filepath.name}' no es UTF-8.")
    except Exception as e: print(f"Err inesperado cargando '{filepath.name}': {e}")
    return None

def load_rule_file_new_structure(fp: Path):
    global active_scales, global_version_mappers # Añadir global_version_mappers
    content = _load_json_file_content(fp)
    if not content or not isinstance(content, dict): return None, None
    
    devices = content.get("device_alias", {})
    filters = content.get("input_filter", [])
    version_mappers_from_file = content.get("version_map", []) # Cargar la nueva sección

    if not isinstance(devices, dict): 
        print(f"Adv: Sección 'device_alias' en '{fp.name}' no es diccionario. Usando vacío."); devices = {}
    if not isinstance(filters, list): 
        print(f"Adv: Sección 'input_filter' en '{fp.name}' no es lista. Usando vacía."); filters = []
    
    if isinstance(version_mappers_from_file, list):
        for i, vm_config in enumerate(version_mappers_from_file):
            if isinstance(vm_config, dict):
                vm_config["_source_file"] = fp.name
                vm_config["_vmap_id_in_file"] = i
                global_version_mappers.append(vm_config) # Acumular
    elif version_mappers_from_file: # Si existe pero no es una lista
        print(f"Adv: Sección 'version_map' en '{fp.name}' no es una lista. Ignorada.")

    for i, f_config in enumerate(filters):
        if isinstance(f_config, dict): 
            f_config["_source_file"] = fp.name
            f_config["_filter_id_in_file"] = i
            if "version_map" in f_config: # Advertir si se encuentra el formato antiguo
                print(f"Adv ({fp.name} Filtro {i}): 'version_map' dentro de un filtro está obsoleto. Defínelo a nivel raíz.")
    
    user_defined_scales = content.get("scales", {})
    if isinstance(user_defined_scales, dict):
        active_scales.update(user_defined_scales)
    elif user_defined_scales:
        print(f"Adv: Sección 'scales' en '{fp.name}' no es un diccionario. Ignorada.")
    
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
    global available_versions, global_version_mappers # Añadir global_version_mappers
    versions = {0} # Default version 0
    for f_config in all_filters: # De los input_filter
        if isinstance(f_config, dict):
            if "version" in f_config:
                v = f_config["version"]
                if isinstance(v, int): versions.add(v)
                elif isinstance(v, list): versions.update(item for item in v if isinstance(item, int))

    for vm_entry in global_version_mappers: # De los version_map globales
        action = vm_entry.get("version_out")
        if isinstance(action, int): # Si la acción es un número de versión
            versions.add(action)

    available_versions = sorted(list(versions))
    if not available_versions: available_versions = [0]

def evaluate_expression(expression_str, context_vars_for_eval):
    global user_named_vars

    if not isinstance(expression_str, (str, int, float)): return None
    if isinstance(expression_str, (int, float)): return int(expression_str)

    current_expr_str = str(expression_str)

    try: # Intento 1: ¿Es un string que representa un entero?
        return int(current_expr_str)
    except ValueError:
        pass 

    # Intento 2: ¿Es la función random?
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
        return None # Error en los args de random
    
    # Preparar contexto para eval()
    public_to_internal_var_map = {
        "channel_in": "ch0_in_ctx", "value_1_in": "value_in_1_ctx",
        "value_2_in": "value_in_2_ctx", "delta_in": "delta_in_2_ctx",
        "cc_val2_saved": "cc_value_sent_ctx", "event_in": "event_type_in_ctx",
        "cc_type_in": "cc_type_in_ctx"
    }
    eval_locals = {}
    for public_name, internal_name in public_to_internal_var_map.items():
        if internal_name in context_vars_for_eval:
            eval_locals[public_name] = context_vars_for_eval[internal_name]
    if "version" in context_vars_for_eval: 
        eval_locals["version"] = context_vars_for_eval["version"]
    for i in range(len(user_named_vars)):
        var_name_public  = f"var_{i}"
        eval_locals[var_name_public] = user_named_vars.get(var_name_public, 0)


       
    def _prob_func(probability_arg):
        # El argumento podría ser una expresión que evalúa a un float, o un float directo
        # Necesitamos evaluar el argumento de prob() usando el mismo contexto
        # Pero cuidado con la recursión infinita si la expresión es "prob(prob(0.5))"
        # Por simplicidad, asumamos que el argumento a prob() no es otra llamada a prob() o random()
        
        # Primero, intentamos evaluar el argumento de prob() si es una cadena
        p_val = None
        if isinstance(probability_arg, (int, float)):
            p_val = float(probability_arg)
        elif isinstance(probability_arg, str):

            temp_eval_locals_for_arg = eval_locals.copy() 
        
            # Intento de evaluar el argumento de prob
            evaluated_arg = None
            try:
                evaluated_arg = eval(str(probability_arg), {"__builtins__": {}}, temp_eval_locals_for_arg)
            except Exception:
                # Si la evaluación del argumento falla, no podemos determinar la probabilidad
                print(f"Adv: No se pudo evaluar el argumento '{probability_arg}' para prob().")
                return 0 # O algún valor de error/default
            
            if isinstance(evaluated_arg, (int, float)):
                p_val = float(evaluated_arg)
            else:
                print(f"Adv: Argumento '{probability_arg}' para prob() no evaluó a un número.")
                return 0 # O algún valor de error/default
        else: # Tipo de argumento no soportado para prob
            print(f"Adv: Tipo de argumento '{type(probability_arg)}' no soportado para prob().")
            return 0

        if p_val is not None:
            return 1 if random.random() < p_val else 0
        return 0 # Fallback si p_val no se pudo determinar

    eval_locals['prob'] = _prob_func

    def _rand_val_func(min_arg, max_arg):
        # Similar a _prob_func, necesitamos evaluar los argumentos
        m_val, M_val = None, None
        
        args_to_eval = [min_arg, max_arg]
        evaluated_args_num = []

        for arg_expr in args_to_eval:
            val = None
            if isinstance(arg_expr, int):
                val = arg_expr
            elif isinstance(arg_expr, str):
                try:
                    # Similar a la evaluación de argumentos de prob
                    temp_eval_locals_for_arg = eval_locals.copy()
                    evaluated_arg = eval(str(arg_expr), {"__builtins__": {}}, temp_eval_locals_for_arg)
                    if isinstance(evaluated_arg, int):
                        val = evaluated_arg
                    else:
                        print(f"Adv: Argumento '{arg_expr}' para rand_val() no evaluó a un entero.")
                        return 0 # Fallback
                except Exception:
                    print(f"Adv: No se pudo evaluar el argumento '{arg_expr}' para rand_val().")
                    return 0 # Fallback
            else:
                 print(f"Adv: Tipo de argumento '{type(arg_expr)}' no soportado para rand_val().")
                 return 0 # Fallback
            
            if val is None: return 0 # Si alguno falla, retornamos
            evaluated_args_num.append(val)

        if len(evaluated_args_num) == 2:
            m_val, M_val = evaluated_args_num[0], evaluated_args_num[1]
            if m_val > M_val: m_val, M_val = M_val, m_val # Asegurar orden
            try:
                return random.randint(m_val, M_val)
            except ValueError: # Si m_val == M_val y hay problemas con randint en algunos casos (aunque no debería)
                return m_val
        return 0 # Fallback

    eval_locals['rand_val'] = _rand_val_func

    def _toggle_func(value_arg):
        # Evaluar el argumento para obtener su valor numérico actual
        current_val = None
        if isinstance(value_arg, (int, float)): # Si ya es un número (podría ser 0.0 o 1.0)
            current_val = int(value_arg)
        elif isinstance(value_arg, str):
            try:
                temp_eval_locals_for_arg = eval_locals.copy()
                evaluated_arg = eval(str(value_arg), {"__builtins__": {}}, temp_eval_locals_for_arg)
                if isinstance(evaluated_arg, (int, float, bool)): # Aceptar bool también
                    current_val = int(evaluated_arg) # Convertir bool a int (True->1, False->0)
                else:
                    print(f"Adv: Argumento '{value_arg}' para toggle() no evaluó a un número o booleano.")
                    return int(value_arg) if isinstance(value_arg, (int,float)) else 0 # Fallback: si no se puede evaluar, intenta convertir el original, o 0
            except Exception:
                print(f"Adv: No se pudo evaluar el argumento '{value_arg}' para toggle().")
                return int(value_arg) if isinstance(value_arg, (int,float)) else 0 # Fallback
        else:
            print(f"Adv: Tipo de argumento '{type(value_arg)}' no soportado para toggle().")
            return 0 # Fallback

        if current_val is None: # Si después de todo no pudimos obtener un valor
             return 0 # O el valor original del argumento si fuera numérico

        return 1 if current_val == 0 else 0

    eval_locals['toggle'] = _toggle_func

    def _get_var_func(array_name_expr, index_expr):
        # Evaluar el nombre del array
        array_name_val = evaluate_expression(array_name_expr, context_vars_for_eval) # Recursión cuidadosa
        # Evaluar el índice
        index_val = evaluate_expression(index_expr, context_vars_for_eval) # Recursión cuidadosa

        if isinstance(array_name_val, str) and isinstance(index_val, (int, float)):
            array_name = array_name_val
            index = int(index_val)

            if array_name in named_arrays:
                if 0 <= index < ARRAY_SIZE:
                    return named_arrays[array_name][index]
        return 0 # Valor por defecto
    eval_locals['get_var'] = _get_var_func




    # DEBUG (opcional, pero útil para ver qué se está evaluando)
    # if "var" in current_expr_str or "if" in current_expr_str:
    #    print(f"DEBUG EVAL: In='{current_expr_str}', Locals={eval_locals}")

    # Intento 3: ¿Es solo el nombre de una variable conocida?
    current_expr_str_stripped = current_expr_str.strip()
    if current_expr_str_stripped in eval_locals:
        return eval_locals[current_expr_str_stripped]

    # Intento 4: ¿Es una expresión matemática (con o sin variables ya sustituidas)?
    # Esta parte es para optimizar/manejar expresiones puramente aritméticas.
    # La lógica de sustitución que tenías para temp_expr_for_arithmetic_check puede ir aquí.
    # Por brevedad, si no es una variable directa, pasamos al eval general.

    # Intento 5: Evaluar como una expresión Python general (incluye ternarios, aritmética con variables)
    try:
        result = eval(current_expr_str, {"__builtins__": {}}, eval_locals)
        # No convertir a int aquí necesariamente, el llamador puede hacerlo.
        # Esto permite que la expresión devuelva strings, ints, floats, bools.
        return result
    except Exception: # NameError, SyntaxError, etc.
        pass # Si eval falla, no es una expresión Python válida en este contexto

    # Intento 6: Fallback - si era un string originalmente y nada más funcionó, devolver el string
    if isinstance(expression_str, str): # expression_str es el input original a la función
        return expression_str.strip()

    return None # No se pudo interpretar

def format_midi_message_for_log(msg, prefix="", active_version=-1, 
                                rule_id_source=None, target_port_alias_for_log_output=None,
                                input_port_actual_name=None, device_aliases_global_map=None):
    # print(f"DEBUG format_midi_message_for_log received: {msg}")
    if msg.type in ['clock', 'activesense']: 
        return None
        
    version_prefix = f"[{active_version}] " if active_version != -1 else ""
    port_display_name = ""
    add_filter_id_to_log = True 
    prefix = prefix.strip().upper() 
    
    port_display_name = ""
    if prefix.strip().startswith("IN") and input_port_actual_name:
        resolved_name = input_port_actual_name # Nombre real del puerto
        if device_aliases_global_map: # Intentar encontrar un alias para este nombre real
            for alias, substring_val in device_aliases_global_map.items():
                if substring_val.lower() in input_port_actual_name.lower():
                    resolved_name = alias # Usar el alias si se encuentra
                    break
        port_display_name = f"[{resolved_name}]"
        add_filter_id_to_log = True 
    elif prefix.strip().endswith("OUT:") and target_port_alias_for_log_output:
        # Para OUT, target_port_alias_for_log_output ya es el alias usado en el JSON
        port_display_name = f"[{target_port_alias_for_log_output}]"
        add_filter_id_to_log = False 

    filter_id_prefix_str = f"{{{rule_id_source}}}" if rule_id_source and add_filter_id_to_log else ""
    full_prefix_parts = [version_prefix, prefix, port_display_name, filter_id_prefix_str]
    full_prefix = "".join(p for p in full_prefix_parts if p).strip()
    
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
    global user_named_vars, active_scales 

    # Iniciar con el valor por defecto que se usará si nada más lo modifica
    final_value_to_return = default_value_if_none 
    evaluated_successfully = False # Flag para saber si alguna lógica tuvo éxito

    if isinstance(config_value, dict) and "scale_value" in config_value: # Para escalado de RANGO
        expression_for_scale_value = config_value.get("scale_value") # Renombrado para claridad
        value_source_for_scaling = None

        # Evaluar la expresión que define QUÉ valor escalar
        # Esta expresión puede ser un nombre de variable, un literal, o una llamada a get_var(), etc.
        evaluated_scale_input = evaluate_expression(expression_for_scale_value, current_eval_context_for_expr)

        if evaluated_scale_input is not None: # Si la expresión evaluó a algo
            value_source_for_scaling = evaluated_scale_input
        # Ya no se necesita el 'else' que imprime "Variable no encontrada", porque si evaluate_expression falla,
        # value_source_for_scaling será None, y el bloque 'if value_source_for_scaling is not None:' no se ejecutará,
        # lo cual es el comportamiento correcto. Opcionalmente, puedes añadir un log si evaluated_scale_input es None.

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
                
                # print(f"DEBUG SCALE_PARAMS: val={val_to_scale_num}({type(val_to_scale_num)}), root={root_note_num}({type(root_note_num)}), type='{scale_type_name_str}'({type(scale_type_name_str)})")

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
        
        # TU DEBUG PRINT (déjalo si es útil para ch_out, pero config_value es lo importante)
        # if debug_field_name and "Ch" in debug_field_name: 
        #      print(f"DEBUG GET_EVAL_SIMPLE: For '{debug_field_name}', config_value='{config_value}', evaluated_to={evaluated} (type: {type(evaluated)})")
        
        if evaluated is not None:
            final_value_to_return = evaluated
            evaluated_successfully = True # Se obtuvo un valor
    
    # Si ninguna lógica tuvo éxito en obtener un valor nuevo, final_value_to_return
    # ya tiene el default_value_if_none que se le pasó a la función.
    # No es necesario hacer nada más si no evaluated_successfully.
    return final_value_to_return



def process_single_output_block(out_conf, i_out_idx, base_context_for_this_output,
                                filter_config_parent_ref, filter_id_for_debug, current_version_for_log,
                                device_aliases_g, mido_ports_map_g,
                                is_virtual_mode_now, virtual_port_out_obj_ref=None, virtual_port_out_name_ref=""):
    global user_named_vars, cc_value_sent, monitor_active, active_note_map 

    # if filter_id_for_debug == "btw_setup3.26": 
    #     print(f"DEBUG P_S_O_B_INSPECT: Filter='{filter_id_for_debug}', OutputIdx={i_out_idx}, Received out_conf={out_conf}")
    #     print(f"DEBUG P_S_O_B_KEYS: out_conf keys = {list(out_conf.keys())}")
    #     channel_out_value_from_json = out_conf.get("channel_out")
    #     print(f"DEBUG P_S_O_B_KEY_VAL: Value for 'channel_out' = '{channel_out_value_from_json}' (type: {type(channel_out_value_from_json)})")

    current_output_eval_context = base_context_for_this_output.copy()

    out_dev_alias = out_conf.get("device_out")
    if out_dev_alias is None:
        if out_conf is not filter_config_parent_ref: # Solo heredar si out_conf no es ya el filtro padre
            out_dev_alias = filter_config_parent_ref.get("device_out")


    event_type_from_json = out_conf.get("event_out") # Antes event_type
    final_event_type_out_str = get_evaluated_value_from_output_config(
        event_type_from_json,
        base_context_for_this_output.get('event_type_in_ctx', 'note_on'),
        current_output_eval_context,
        filter_id_for_debug, f"Out.{i_out_idx}.event_out"
    )

    if isinstance(event_type_from_json, str) and not event_type_from_json.replace("_","").isalnum(): # Heurística para detectar si es una expresión
        final_event_type_out_str = get_evaluated_value_from_output_config(
            event_type_from_json,
            base_context_for_this_output.get('event_type_in_ctx', 'note_on'),
            current_output_eval_context,
            filter_id_for_debug, f"Out.{i_out_idx}.EventType"
        )
    elif isinstance(event_type_from_json, str):
        final_event_type_out_str = event_type_from_json
    else:
        final_event_type_out_str = base_context_for_this_output.get('event_type_in_ctx', 'note_on')

    if isinstance(final_event_type_out_str, str):
        cfg_lower = final_event_type_out_str.lower()
        # Si el evento de salida es "note", resolver a note_on o note_off basado en el evento de entrada
        if cfg_lower == "note":
            input_event_type = base_context_for_this_output.get('event_type_in_ctx', 'note_on')
            if input_event_type in ['note_on', 'note_off']:
                final_event_type_out_str = input_event_type
            else: # Si el input no es nota, pero el output es "note", default a note_on
                final_event_type_out_str = 'note_on'
        elif cfg_lower == "cc": final_event_type_out_str = "control_change"
        elif cfg_lower == "pc": final_event_type_out_str = "program_change"
    elif not out_conf.get("device_out"):
        final_event_type_out_str = base_context_for_this_output.get('event_type_in_ctx', 'note_on')


    ch_out_expr = out_conf.get("channel_out", base_context_for_this_output.get('ch0_in_ctx',0))
    final_ch_out_eval = get_evaluated_value_from_output_config(
        ch_out_expr, 
        base_context_for_this_output.get('ch0_in_ctx',0), 
        current_output_eval_context, 
        filter_id_for_debug, f"Out.{i_out_idx}.Ch")
    final_ch_out_clamped = max(0, min(15, int(final_ch_out_eval if isinstance(final_ch_out_eval, (int,float)) else 0)))
    # print(f"DEBUG P_S_O_B: Filter='{filter_id_for_debug}', OutputIdx={i_out_idx}, CH_OUT_EXPR_VAR='{ch_out_expr}', FROM_JSON_RAW='{out_conf.get('channel_out')}', FINAL_CH_OUT_EVAL={final_ch_out_eval}, FINAL_CH_CLAMPED={final_ch_out_clamped}")

    val1_out_expr = out_conf.get("value_1_out") # Obtener la expresión del JSON, podría ser None
    default_val1_for_output = base_context_for_this_output.get('value_in_1_ctx', 0) # Default es la nota/valor1 de entrada

    # Si val1_out_expr es None (no está en JSON), usamos el default_val1_for_output directamente
    # Si val1_out_expr existe, lo evaluamos. Si la evaluación da None, usamos default_val1_for_output.
    if val1_out_expr is None:
        evaluated_val1_from_json = default_val1_for_output
    else:
        evaluated_val1_from_json = get_evaluated_value_from_output_config(
            val1_out_expr,
            default_val1_for_output, # Pasar el default correcto aquí
            current_output_eval_context,
            filter_id_for_debug, f"Out.{i_out_idx}.Val1"
        )
        if evaluated_val1_from_json is None: # Si la evaluación falló y devolvió None
            evaluated_val1_from_json = default_val1_for_output

    # Ahora, asegurar que tenemos un entero para final_val1_out_eval
    try:
        final_val1_out_eval = int(evaluated_val1_from_json)
    except (ValueError, TypeError):
        # Si no se puede convertir (ej. era un string como "virus_minor" devuelto por error),
        # usar el default_val1_for_output como último recurso.
        final_val1_out_eval = int(default_val1_for_output)


    # --- LÓGICA DE active_note_map (la que te di antes, para listas FIFO) ---
    input_event_type_for_map = base_context_for_this_output.get('event_type_in_ctx')
    original_input_ch_for_map = base_context_for_this_output.get('ch0_in_ctx')
    original_input_val1_for_map = base_context_for_this_output.get('value_in_1_ctx')

    if final_event_type_out_str == "note_on":
        if input_event_type_for_map == 'note_on' and \
           original_input_ch_for_map is not None and \
           original_input_val1_for_map is not None:
            map_key = (original_input_ch_for_map, original_input_val1_for_map, final_ch_out_clamped)
            if map_key not in active_note_map:
                active_note_map[map_key] = []
            active_note_map[map_key].append(final_val1_out_eval)

    elif final_event_type_out_str == "note_off":
        if input_event_type_for_map == 'note_off' and \
           original_input_ch_for_map is not None and \
           original_input_val1_for_map is not None:
            map_key_lookup = (original_input_ch_for_map, original_input_val1_for_map, final_ch_out_clamped)
            if map_key_lookup in active_note_map and active_note_map[map_key_lookup]:
                final_val1_out_eval = active_note_map[map_key_lookup].pop(0)
                if not active_note_map[map_key_lookup]:
                    del active_note_map[map_key_lookup]
            # else:
                # Si no hay mapeo (ej. la lista se vació o la clave no existía),
                # final_val1_out_eval (que se calculó antes a partir de la expresión del JSON) se usa.
                # Esto es importante para que un note_off sin un note_on mapeado aún pueda procesarse
                # según su propia definición de value_1_out en el JSON.
                pass




    

    if final_event_type_out_str == "control_change":
        cc_num_lookup = int(max(0,min(127, final_val1_out_eval if isinstance(final_val1_out_eval, (int,float)) else 0)))
        current_output_eval_context["cc_value_sent_ctx"] = cc_value_sent.get((final_ch_out_clamped, cc_num_lookup), 0)

    val2_out_expr = out_conf.get("value_2_out", base_context_for_this_output.get('value_in_2_ctx',0))
    calculated_target_abs_value_for_output = get_evaluated_value_from_output_config(val2_out_expr, base_context_for_this_output.get('value_in_2_ctx',0), current_output_eval_context, filter_id_for_debug, f"Out.{i_out_idx}.Val2")
    output_msg_value2_encoded = int(calculated_target_abs_value_for_output if isinstance(calculated_target_abs_value_for_output, (int,float)) else 0)

    # La creación del mensaje usará final_val1_out_eval y output_msg_value2_encoded
    if final_event_type_out_str == "control_change":
        output_cc_type_config = out_conf.get("cc_type_out", "abs").lower()
        if "cc_value_sent_ctx" not in current_output_eval_context and final_event_type_out_str == "control_change":
             cc_num_lookup_for_saved = int(max(0,min(127, final_val1_out_eval if isinstance(final_val1_out_eval, (int,float)) else 0)))
             current_output_eval_context["cc_value_sent_ctx"] = cc_value_sent.get((final_ch_out_clamped, cc_num_lookup_for_saved), output_msg_value2_encoded)

        saved_val = current_output_eval_context.get("cc_value_sent_ctx", output_msg_value2_encoded) 

        if output_cc_type_config == "abs": output_msg_value2_encoded = max(0, min(127, output_msg_value2_encoded))
        elif output_cc_type_config == "relative_signed":
            delta = output_msg_value2_encoded - saved_val
            output_msg_value2_encoded = max(0, min(127, 64 + delta))
        elif output_cc_type_config == "relative_2c":
            delta = output_msg_value2_encoded - saved_val
            if delta == 0: output_msg_value2_encoded = 0
            elif delta > 0: output_msg_value2_encoded = max(1, min(63, delta))
            else: output_msg_value2_encoded = max(65, min(127, 128 + delta))

    for key_in_json, expr_assign in out_conf.items():
        if key_in_json.startswith("var_") and key_in_json in user_named_vars:
            val_assign = get_evaluated_value_from_output_config(
                expr_assign, 
                None, # Usar None como default si la evaluación falla
                current_output_eval_context, 
                filter_id_for_debug, 
                f"Assign.{key_in_json}"
            )
            if isinstance(val_assign, (int, float)):
                user_named_vars[key_in_json] = int(val_assign)
            elif isinstance(val_assign, str):
                try:
                    # Intentar convertir a int si es un string numérico (ej. "60")
                    user_named_vars[key_in_json] = int(val_assign)
                except ValueError:
                    # Si no se puede convertir a int, almacenar como string
                    user_named_vars[key_in_json] = val_assign 
            else: # Para otros tipos como booleanos
                try: user_named_vars[key_in_json] = int(val_assign)
                except (ValueError, TypeError): user_named_vars[key_in_json] = str(val_assign) # Fallback a string

            # Logueo (opcionalmente muestra el tipo si no es int)
            # log_pfx = "    V_ASSIGN:" if base_context_for_this_output.get('event_type_in_ctx') == "_version_change" else "[*] >> SET:"
            # if monitor_active: 
                # val_display = user_named_vars[key_in_json]
                # type_display = ""
                # if not isinstance(val_display, int): # Solo muestra el tipo si NO es int
                #     type_display = f" (type: {type(val_display).__name__})"
                # print(f"{log_pfx} {key_in_json} = {val_display}{type_display} ['{expr_assign}']")
                # print(f"{log_pfx} {key_in_json} = ['{val_display}']")
            # elif monitor_active:
                # log_pfx_f = "    V_ASSIGN_F:" if base_context_for_this_output.get('event_type_in_ctx') == "_version_change" else "      !SET_F:"
                # print(f"{log_pfx_f} {key_in_json} en {filter_id_for_debug} (expr '{expr_assign}' evaluó a None)")

    if "set_var" in out_conf:
        set_var_actions = out_conf["set_var"]
        if isinstance(set_var_actions, list):
            for action_item in set_var_actions:
                if isinstance(action_item, dict):
                    array_name_str = action_item.get("name") 
                    index_expr_str = action_item.get("index")
                    value_expr_str = action_item.get("value")

                    if array_name_str and index_expr_str is not None and value_expr_str is not None:
                        # ARRAY_SIZE y named_arrays deben ser accesibles aquí (globales)
                        if array_name_str in named_arrays:
                            index_val = evaluate_expression(index_expr_str, current_output_eval_context)
                            value_to_set_any = evaluate_expression(value_expr_str, current_output_eval_context)

                            if isinstance(index_val, (int, float)) and value_to_set_any is not None:
                                index = int(index_val)
                                
                                if 0 <= index < ARRAY_SIZE: # Usar ARRAY_SIZE global
                                    try:
                                        if array_name_str in ["prob", "factor"]:
                                            final_value = float(value_to_set_any)
                                        elif array_name_str in ["control", "offset", "velo", "length", "mute"]:
                                            final_value = int(value_to_set_any)
                                        else: 
                                            final_value = value_to_set_any 
                                        
                                        named_arrays[array_name_str][index] = final_value
                                        
                                        if monitor_active: # Logueo opcional
                                            print(f"    ARR_ASSIGN: {array_name_str}[{index}] = {final_value} (idx_expr:'{index_expr_str}', val_expr:'{value_expr_str}')")
                                    except (ValueError, TypeError) as e_conv:
                                        if monitor_active:
                                            print(f"Adv ({filter_id_for_debug}): Error convirtiendo valor para {array_name_str}[{index}]: {e_conv}. Valor '{value_to_set_any}'")
                                else:
                                    if monitor_active:
                                        print(f"Adv ({filter_id_for_debug}): Índice '{index}' (de '{index_expr_str}') fuera de rango para array '{array_name_str}'.")
                            else:
                                if monitor_active:
                                     print(f"Adv ({filter_id_for_debug}): No se pudo evaluar índice '{index_expr_str}' o valor '{value_expr_str}' para set_var['{array_name_str}'].")
                        else:
                            if monitor_active:
                                print(f"Adv ({filter_id_for_debug}): Array llamado '{array_name_str}' no encontrado para set_var.")
                    else:
                        if monitor_active:
                            print(f"Adv ({filter_id_for_debug}): Falta 'name', 'index', o 'value' en item de set_var.")



                            
    target_port_obj_to_use = None
    effective_device_out_alias_for_log = out_dev_alias
    output_msg = None

    if is_virtual_mode_now:
        target_port_obj_to_use = virtual_port_out_obj_ref
        effective_device_out_alias_for_log = virtual_port_out_name_ref
        if not target_port_obj_to_use and monitor_active and out_dev_alias and final_event_type_out_str :
            print(f"      WARN_VIRTUAL: Puerto virtual de salida '{virtual_port_out_name_ref}' no disponible para {filter_id_for_debug}.{i_out_idx}")
    elif out_dev_alias and final_event_type_out_str :
        out_dev_sub = device_aliases_g.get(out_dev_alias, out_dev_alias)
        for p_name, p_info in mido_ports_map_g.items():
            if p_info["type"] == "out" and out_dev_sub.lower() in p_name.lower():
                target_port_obj_to_use = p_info["obj"]; break
        # if not target_port_obj_to_use and monitor_active:
        #     print(f"      WARN: Puerto OUT '{out_dev_alias}' no encontrado para {filter_id_for_debug}.{i_out_idx}")

    # print(f"DEBUG P_S_O_B: Filter='{filter_id_for_debug}', OutputIdx={i_out_idx}, CH_OUT_EXPR='{out_conf.get('channel_out', 'inherited')}', FINAL_CH_OUT_EVAL={final_ch_out_eval}, FINAL_CH_CLAMPED={final_ch_out_clamped}")
    if target_port_obj_to_use and final_event_type_out_str:
        # final_val1_out_eval ya está calculado con la lógica de note mapping
        val1_msg = int(final_val1_out_eval) # Asegurar que es int para mido
        try:
            if final_event_type_out_str in ["note_on", "note_off"]:
                val1_msg = max(0,min(127,val1_msg)); current_vel = max(0,min(127, output_msg_value2_encoded))
                eff_type = final_event_type_out_str

                if final_event_type_out_str == "note_on" and current_vel == 0:
                    eff_type = "note_off"
                output_msg = mido.Message(eff_type, channel=final_ch_out_clamped, note=val1_msg, velocity=current_vel)
            elif final_event_type_out_str=="control_change":
                val1_msg = max(0,min(127,val1_msg))
                output_msg = mido.Message('control_change',channel=final_ch_out_clamped,control=val1_msg,value=output_msg_value2_encoded)
            elif final_event_type_out_str=="program_change":
                val1_msg = max(0,min(127,val1_msg))
                output_msg = mido.Message('program_change',channel=final_ch_out_clamped,program=val1_msg)
            elif final_event_type_out_str=="pitchwheel":
                val1_msg = max(-8192,min(8191,val1_msg)) # val1_msg ya es el valor del pitch
                output_msg = mido.Message('pitchwheel',channel=final_ch_out_clamped,pitch=val1_msg)
            elif final_event_type_out_str=="aftertouch": # Channel aftertouch
                val1_msg = max(0,min(127,val1_msg)) # val1_msg es el valor del aftertouch
                output_msg = mido.Message('aftertouch',channel=final_ch_out_clamped,value=val1_msg)
            elif final_event_type_out_str=="polytouch": # Polyphonic aftertouch
                val1_msg = max(0,min(127,val1_msg)) # val1_msg es la nota
                poly_val = max(0,min(127, output_msg_value2_encoded)) # output_msg_value2_encoded es el valor del polytouch
                output_msg = mido.Message('polytouch',channel=final_ch_out_clamped,note=val1_msg,value=poly_val)
            elif final_event_type_out_str == "sysex":
                sysex_data = out_conf.get("sysex_data")
                if isinstance(sysex_data, list) and all(isinstance(b,int) and 0<=b<=255 for b in sysex_data):
                    data_clean = tuple(s for s in sysex_data if s != 0xF0 and s != 0xF7)
                    output_msg=mido.Message('sysex',data=data_clean)
                else: print(f"Adv ({filter_id_for_debug}.{i_out_idx}): SysEx data inválida o no es lista.")
            elif final_event_type_out_str in ["start", "stop", "continue", "clock", "reset"]:
                output_msg = mido.Message(final_event_type_out_str)
            elif final_event_type_out_str == 'songpos':
                    songpos_val = get_evaluated_value_from_output_config(out_conf.get("value_1"),0,current_output_eval_context,filter_id_for_debug,f"Out.{i_out_idx}.Songpos")
                    output_msg = mido.Message(final_event_type_out_str, pos=int(songpos_val if isinstance(songpos_val, (int,float)) else 0))

        except Exception as e: print(f"ERR Creando Msg ({filter_id_for_debug}.{i_out_idx}) tipo '{final_event_type_out_str}': {e}")

    if output_msg:
        return (output_msg,
                target_port_obj_to_use,
                effective_device_out_alias_for_log,
                filter_id_for_debug,
                final_event_type_out_str,
                int(calculated_target_abs_value_for_output) if final_event_type_out_str == "control_change" else None)
    return None


def execute_all_outputs_for_filter(f_config, base_context, current_version, device_aliases_g, mido_ports_map_g, is_virtual_mode_now, virtual_out_obj=None, virtual_out_name=""):
    outputs_generated_by_this_filter = []
    output_configs_list = f_config.get("output", [])
    filter_id_str = f_config.get("_filter_id_str", "UnknownFilter")

    if not (isinstance(output_configs_list, list) and len(output_configs_list) > 0):
        # No hay lista "output" o está vacía. Tratar f_config como un solo output_conf.
        # Solo si f_config tiene al menos un parámetro de output (device_out o una asignación var_X)
        has_direct_output_params = False
        if f_config.get("device_out"): has_direct_output_params = True
        if not has_direct_output_params:
            for k in f_config.keys():
                if k.startswith("var_") and k in user_named_vars: # user_named_vars usa claves "var_X"
                    has_direct_output_params = True; break
        
        if has_direct_output_params:
            output_configs_list = [f_config] # Tratar el filtro entero como una lista de un solo output
        else:
            output_configs_list = [] # No hay outputs definidos



    for i_output_block, out_conf_item in enumerate(output_configs_list):
        if not isinstance(out_conf_item, dict): continue
        
        output_result_tuple = process_single_output_block( out_conf_item, i_output_block, base_context, f_config, filter_id_str, current_version, device_aliases_g, mido_ports_map_g, is_virtual_mode_now, virtual_out_obj, virtual_out_name
        )
        if output_result_tuple: 
            outputs_generated_by_this_filter.append(output_result_tuple)
    return outputs_generated_by_this_filter


def summarize_active_processing_config(active_filters_list, device_aliases_map, opened_ports_map, 
                                       is_virtual_mode, vp_in_name="", vp_out_name=""):
    print("\n--- Configuración ---")
    if is_virtual_mode:
        print("[!] MODO PUERTO VIRTUAL ACTIVADO")
        print(f"    - Entrada Virtual: '{vp_in_name}'")
        print(f"    - Salida Virtual:  '{vp_out_name}'")

    if not active_filters_list: 
        print("No hay filtros activos.")
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

    if global_version_mappers:
        print("\n--- Mapeadores de Versión Globales ---")
        for i, vm_conf in enumerate(global_version_mappers):
            source_file = vm_conf.get('_source_file', 'Desconocido')
            vm_id_in_file = vm_conf.get('_vmap_id_in_file', i)
            print(f"\nVM ({source_file} / ID {vm_id_in_file}):")
            if vm_conf.get("_comment"): print(f"  [[ {vm_conf['_comment']} ]]")
            
            details = []
            if "device_in" in vm_conf: details.append(f"Disp IN: '{vm_conf['device_in']}'")
            if "ch_in" in vm_conf: details.append(f"Ch IN: {vm_conf['ch_in']}")
            if "event_in" in vm_conf: details.append(f"Evt IN: '{vm_conf['event_in']}'")
            if "value_1_in" in vm_conf: details.append(f"V1 IN: {vm_conf['value_1_in']}")
            if "value_2_in" in vm_conf: details.append(f"V2 IN: {vm_conf['value_2_in']}")
            if details: print(f"  Condiciones: {', '.join(details)}")
            print(f"  Acción: {vm_conf.get('version_out', 'N/A')}")

    print("\n--- Filtros de Eventos --- ")
    for i, f_config in enumerate(active_filters_list):
        filter_id_str = f_config.get('_filter_id_str', f"F{i}")
        source_file_info = f"(de {f_config.get('_source_file', 'Fuente Desconocida')})"
        print(f"\n{filter_id_str}: {source_file_info}")
        filter_comment = f_config.get("_comment");
        if filter_comment: print(f"  [[ {filter_comment} ]]")
        version_cond = f_config.get("version");
        if version_cond is not None: print(f"  Versiones: {version_cond}")
        else: print(f"  Versiones: Todas")
        
        dev_in_alias = f_config.get("device_in"); dev_in_display = f"{dev_in_alias}"
        if dev_in_alias in device_aliases_map: dev_in_display += f" (alias de '{device_aliases_map[dev_in_alias]}')"
        else: dev_in_display += " (subcadena directa)"
        print(f"  [IN]: '{dev_in_display}'")
        
        # vmap = f_config.get("version_map")
        # if vmap and isinstance(vmap, dict):
            # print(f"  Control de Versión:")
            # for vmap_key_string, action in vmap.items():
                # trigger_display = event_trigger.replace("control_change", "CC").replace("note_on", "NoteOn").replace("note_off", "NoteOff").replace("program_change", "PC")
                # trigger_display = trigger_display.replace("note=", "N=").replace("channel=", "Ch=").replace("control=", "Ctrl=").replace("value=", "Val=")
                # print(f"    - '{vmap_key_string}' -> Acción: {action}") 
        
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
            print(f"  Filtro Entrada:")
            for cond in conditions: print(f"    - {cond}")

        default_device_out_at_filter_level = f_config.get("device_out")
        if default_device_out_at_filter_level:
            resolved_default_out = device_aliases_map.get(default_device_out_at_filter_level, default_device_out_at_filter_level)
            actual_port_for_default = f"'{resolved_default_out}' (no abierto/encontrado)"
            for p_name, p_info in opened_ports_map.items():
                if p_info["type"] == "out" and (resolved_default_out.lower() in p_name.lower() or default_device_out_at_filter_level == p_info.get("alias_used")):
                    actual_port_for_default = f"'{p_name}'"; break
            print(f"  [OUT Default Filtro]: '{default_device_out_at_filter_level}' (hacia {actual_port_for_default})")



        outputs = f_config.get("output", [])
        if outputs and isinstance(outputs, list):
            print(f"  Procesos ({len(outputs)}):")
            for j, out_conf in enumerate(outputs):
                if not isinstance(out_conf, dict): continue
                output_comment = out_conf.get("_comment"); output_title = f"    {j+1}_Output:"
                if output_comment: output_title += f" ({output_comment})"
                print(output_title)
                
                out_dev_alias_specific = out_conf.get("device_out")
                # out_dev_alias_filter_default = f_config.get("device_out") 
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
                    print(f"      [OUT] '{effective_out_dev_alias}' {source_of_device_out} (hacia {actual_port_name_for_output_display})")
                

                
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
                    if k_user_var.startswith("var_") and k_user_var in user_named_vars: # user_named_vars es global
                        add_detail_summary(k_user_var, f"Asigna a {k_user_var}")
                
                if out_details:
                    for detail in out_details: print(f"        - {detail}")
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
                        print(f"        (valores por defecto para parámetros no especificados)")
            
    print("----------------------------------------------------")

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
    global cc_value_sent, cc_value_control # user_named_vars es accedida por las funciones de output
    # filter_id_for_debug se obtiene de filter_config dentro de execute_all_outputs_for_filter y process_single_output_block
    if msg_input_port_name_or_dummy != DUMMY_PORT_NAME_FOR_VERSION_TRIGGER and original_msg_or_dummy is None:
        print(f"ADVERTENCIA: original_msg_or_dummy es None en llamada no-trigger para filtro {filter_config.get('_filter_id_str')}")
        return []
    
    # (El DUMMY_MSG_FOR_VERSION_TRIGGER es note_on, channel=0, note=0, velocity=0)
    if original_msg_or_dummy.type == 'note_on' and original_msg_or_dummy.velocity == 0:
        effective_msg_for_context = mido.Message('note_off',
                                                 channel=original_msg_or_dummy.channel,
                                                 note=original_msg_or_dummy.note,
                                                 velocity=0) # Usar 0 para la velocidad del note_off generado
    else:
        effective_msg_for_context = original_msg_or_dummy.copy()
    
    is_version_trigger_call = (msg_input_port_name_or_dummy == DUMMY_PORT_NAME_FOR_VERSION_TRIGGER)

    # 1. Filtro de Versión (Siempre se evalúa)
    # Si "version" está en el filtro, debe coincidir.
    # Si no está y es una llamada de trigger de versión, process_version_activated_filters ya lo validó.
    # Si no está y es una llamada MIDI normal, el filtro no es sensible a la versión en este punto.
    if "version" in filter_config:
        version_cond = filter_config["version"]
        version_match = False
        if isinstance(version_cond, int) and version_cond == current_active_version_global:
            version_match = True
        elif isinstance(version_cond, list) and current_active_version_global in version_cond:
            version_match = True
        if not version_match:
            return [] # No aplica a esta versión
    elif is_version_trigger_call and filter_config.get("version") is None:
        pass

    # 2. Filtro de Dispositivo de Entrada
    filter_device_in_alias = filter_config.get("device_in")
    if is_version_trigger_call:
        if filter_device_in_alias is not None: 
            return [] 
    elif is_virtual_mode_now:
        if filter_device_in_alias is None and not is_version_trigger_call:
            return [] 
        pass

    else: # Llamada por MIDI normal
        if filter_device_in_alias is None: # Un filtro normal DEBE tener device_in
            return [] 
        device_in_substring = device_aliases_global.get(filter_device_in_alias, filter_device_in_alias)
        if device_in_substring.lower() not in msg_input_port_name_or_dummy.lower():
            return []

    # --- Preparar CONTEXTO DE ENTRADA (base_context_for_outputs) ---
    base_context_for_outputs = {}
    # effective_msg_for_context = None 

    if is_version_trigger_call:
        base_context_for_outputs = {
            'ch0_in_ctx': effective_msg_for_context.channel,
            'value_in_1_ctx': getattr(effective_msg_for_context, 'note', getattr(effective_msg_for_context, 'control', 0)),
            'value_in_2_ctx': getattr(effective_msg_for_context, 'velocity', getattr(effective_msg_for_context, 'value', 0)),
            'delta_in_2_ctx': 0,
            'event_type_in_ctx': effective_msg_for_context.type,
            'cc_type_in_ctx': "abs" # Para DUMMY_MSG, el tipo de CC de entrada no es relevante
        }
    else: 
        ch0_in_ctx = getattr(effective_msg_for_context, 'channel', -1)
        value_in_1_ctx_real = 0
        value_in_2_ctx_real = 0
        delta_in_2_ctx_real = 0
        event_type_in_ctx_real = effective_msg_for_context.type
        cc_type_in_filter_config_real = filter_config.get("cc_type_in", "abs").lower()

        if effective_msg_for_context.type == 'control_change':
            value_in_1_ctx_real = effective_msg_for_context.control
            cc_ch_input = effective_msg_for_context.channel
            cc_num_input = effective_msg_for_context.control
            C_current_abs_input = effective_msg_for_context.value
        elif event_type_in_ctx_real in ['note_on', 'note_off']: # effective_msg_for_context.type ya está corregido
            value_in_1_ctx_real = effective_msg_for_context.note
            value_in_2_ctx_real = effective_msg_for_context.velocity 
        elif event_type_in_ctx_real == 'program_change':
            value_in_1_ctx_real = effective_msg_for_context.program
        elif event_type_in_ctx_real == 'pitchwheel':
            value_in_1_ctx_real = effective_msg_for_context.pitch
        elif event_type_in_ctx_real == 'aftertouch':
            value_in_1_ctx_real = effective_msg_for_context.value
            # value_in_2_ctx_real permanece 0 o como lo definas
        elif event_type_in_ctx_real == 'polytouch':
            value_in_1_ctx_real = effective_msg_for_context.note
            value_in_2_ctx_real = effective_msg_for_context.value
        
        base_context_for_outputs = {
            'ch0_in_ctx': ch0_in_ctx, 'value_in_1_ctx': value_in_1_ctx_real,
            'value_in_2_ctx': value_in_2_ctx_real, 'delta_in_2_ctx': delta_in_2_ctx_real,
            'event_type_in_ctx': event_type_in_ctx_real,
            'cc_type_in_ctx': cc_type_in_filter_config_real if effective_msg_for_context.type == 'control_change' else "abs"
        }

        
        ch0_in_ctx = getattr(effective_msg_for_context, 'channel', -1)
        value_in_1_ctx_real = 0; value_in_2_ctx_real = 0; delta_in_2_ctx_real = 0
        event_type_in_ctx_real = effective_msg_for_context.type 
        cc_type_in_filter_config_real = filter_config.get("cc_type_in", "abs").lower()

        if effective_msg_for_context.type == 'control_change':
            value_in_1_ctx_real = effective_msg_for_context.control
            cc_ch_input = effective_msg_for_context.channel
            cc_num_input = effective_msg_for_context.control
            C_current_abs_input = effective_msg_for_context.value

            if cc_type_in_filter_config_real == "abs":
                value_in_2_ctx_real = C_current_abs_input
                delta_in_2_ctx_real = 0 
            elif cc_type_in_filter_config_real == "relative_signed":
                delta_in_2_ctx_real = C_current_abs_input - 64
                value_in_2_ctx_real = max(0, min(127, cc_value_sent.get((cc_ch_input, cc_num_input), 64) + delta_in_2_ctx_real))
            elif cc_type_in_filter_config_real == "relative_2c":
                if 1 <= C_current_abs_input <= 63: delta_in_2_ctx_real = C_current_abs_input
                elif 65 <= C_current_abs_input <= 127: delta_in_2_ctx_real = C_current_abs_input - 128
                else: delta_in_2_ctx_real = 0
                value_in_2_ctx_real = max(0, min(127, cc_value_sent.get((cc_ch_input, cc_num_input), 64) + delta_in_2_ctx_real))
            elif cc_type_in_filter_config_real == "abs_relative":
                abs2rel_factor = float(filter_config.get("abs2rel_factor", 2.0))
                threshold = int(filter_config.get("threshold", 0))
                
                C = C_current_abs_input
                L_internal_state = cc_input_s_state.get((cc_ch_input, cc_num_input), C)
                P = cc_value_control.get((cc_ch_input, cc_num_input), C)
                
                diff_C_L = abs(C - L_internal_state)
                new_processed_value_for_L = L_internal_state

                if threshold > 0 and diff_C_L < threshold:
                    # MODO DE CONTROL DIRECTO / "CATCH-UP" (Solo si threshold > 0)
                    value_in_2_ctx_real = C
                    new_processed_value_for_L = C
                else:
                    # MODO RELATIVO / ACELERADO (O threshold es 0)
                    # Si el knob no se movió (C == P), el valor no debería cambiar desde L.
                    if C == P:
                        value_in_2_ctx_real = L_internal_state
                        new_processed_value_for_L = L_internal_state
                    else: # El knob se movió (C != P)
                        # Si threshold es 0, queremos forzar la aceleración siempre que C != P.
                        # Si threshold > 0, pero estamos fuera de la zona de catch-up, también aceleramos.
                        # La condición L_internal_state == P ya no es tan relevante aquí para decidir si *no* acelerar
                        # cuando threshold es 0.

                        delta_knob = C - P
                        accelerated = L_internal_state + abs2rel_factor * delta_knob
                        value_in_2_ctx_real = max(0, min(127, int(round(accelerated))))
                        new_processed_value_for_L = value_in_2_ctx_real
                
                cc_input_s_state[(cc_ch_input, cc_num_input)] = new_processed_value_for_L
                delta_in_2_ctx_real = C - P


            elif cc_type_in_filter_config_real == "abs_catchup":
                threshold_val = int(filter_config.get("delta_threshold", 5))
                I_knob_current_value = C_current_abs_input # Input value (actual del knob)
                
                # S: Último valor que esta lógica de catchup consideró válido para ESTE INPUT (ch_in, cc_in)
                S_internal_state = cc_input_s_state.get((cc_ch_input, cc_num_input), CC_SENT_UNINITIALIZED)
                # C: Último valor físico del knob (valor anterior de I)
                C_knob_previous_value = cc_value_control.get((cc_ch_input, cc_num_input), I_knob_current_value) 

                send_output_flag = False

                if S_internal_state == CC_SENT_UNINITIALIZED: # Si S no está inicializado, siempre enviar I.
                    send_output_flag = True
                else:
                    if C_knob_previous_value == S_internal_state:
                        if abs(I_knob_current_value - C_knob_previous_value) < threshold_val:
                            send_output_flag = True # Enganchado y dentro del umbral: S=C=I
                        else:
                            send_output_flag = False # Enganchado pero fuera del umbral: C=I, S no cambia, no enviar
                    else: # C_knob_previous_value != S_internal_state (desenganchado)
                        if (I_knob_current_value < S_internal_state and S_internal_state < C_knob_previous_value) or \
                           (I_knob_current_value > S_internal_state and S_internal_state > C_knob_previous_value):
                            send_output_flag = True # Re-enganchado: S=C=I
                        else:
                            send_output_flag = False # Sigue desenganchado: C=I, S no cambia, no enviar
                
                if send_output_flag:
                    value_in_2_ctx_real = I_knob_current_value
                    # Actualizar S para este input (ch_in, cc_in) al valor actual del knob I.
                    cc_input_s_state[(cc_ch_input, cc_num_input)] = I_knob_current_value
                    
                    if S_internal_state == CC_SENT_UNINITIALIZED:
                        delta_in_2_ctx_real = I_knob_current_value 
                    else:
                        delta_in_2_ctx_real = I_knob_current_value - S_internal_state
                    # C (cc_value_control) se actualizará a I_knob_current_value al final del procesamiento del mensaje de entrada.
                else:
                    # No enviar. C (cc_value_control) se actualiza a I_knob_current_value. S (cc_input_s_state) no cambia.
                    return []


            else: 
                value_in_2_ctx_real = C_current_abs_input; delta_in_2_ctx_real = 0
                cc_type_in_filter_config_real = "abs"
        elif effective_msg_for_context.type in ['note_on', 'note_off']:
            value_in_1_ctx_real = effective_msg_for_context.note
            value_in_2_ctx_real = effective_msg_for_context.velocity if effective_msg_for_context.type == 'note_on' else 0
        elif effective_msg_for_context.type == 'program_change': value_in_1_ctx_real = effective_msg_for_context.program
        elif effective_msg_for_context.type == 'pitchwheel': value_in_1_ctx_real = effective_msg_for_context.pitch
        elif effective_msg_for_context.type == 'aftertouch': value_in_1_ctx_real = effective_msg_for_context.value
        elif effective_msg_for_context.type == 'polytouch': 
            value_in_1_ctx_real = effective_msg_for_context.note
            value_in_2_ctx_real = effective_msg_for_context.value
        
        base_context_for_outputs = {
            'ch0_in_ctx': ch0_in_ctx, 'value_in_1_ctx': value_in_1_ctx_real, 
            'value_in_2_ctx': value_in_2_ctx_real, 'delta_in_2_ctx': delta_in_2_ctx_real,   
            'event_type_in_ctx': event_type_in_ctx_real,
            'cc_type_in_ctx': cc_type_in_filter_config_real if effective_msg_for_context.type == 'control_change' else "abs"
        }

    # --- Filtros de Condición de Evento (channel, event_type, value_1, value_2) ---
    # Estos se aplican SOLO si NO es una llamada de activación por versión.
    if not is_version_trigger_call:
        if "ch_in" in filter_config:
            ch_cond_config = filter_config["ch_in"]
            actual_ch = base_context_for_outputs.get('ch0_in_ctx', -1) # Canal es 0-15
            if not _check_value_condition(ch_cond_config, actual_ch):
                return []
        if "event_in" in filter_config:
            et_cond = filter_config["event_in"]; et_list = [et_cond] if isinstance(et_cond, str) else et_cond
            if not isinstance(et_list, list): return []
            et_list_lower = [str(et).lower() for et in et_list]; input_event_lower = base_context_for_outputs.get('event_type_in_ctx',"").lower()
            matches = False
            if input_event_lower in et_list_lower: matches = True
            elif "note" in et_list_lower and input_event_lower in ["note_on", "note_off"]: matches = True
            elif "cc" in et_list_lower and input_event_lower == "control_change": matches = True
            elif "pc" in et_list_lower and input_event_lower == "program_change": matches = True
            if not matches: return []

        
        if "value_1_in" in filter_config:
            v1_cond_config = filter_config["value_1_in"]
            actual_v1 = base_context_for_outputs.get('value_in_1_ctx', None)
            if not _check_value_condition(v1_cond_config, actual_v1):
                return []
        if "value_2_in" in filter_config:
            v2_cond_config = filter_config["value_2_in"]
            actual_v2 = base_context_for_outputs.get('value_in_2_ctx', None)
            if not _check_value_condition(v2_cond_config, actual_v2):
                return []
    
    # Si llegamos aquí, el filtro aplica. Llamar a execute_all_outputs_for_filter.
    generated_outputs_with_meta = execute_all_outputs_for_filter( filter_config, base_context_for_outputs, current_active_version_global, device_aliases_global, mido_ports_map, is_virtual_mode_now, virtual_out_obj, virtual_out_name
    )

    # Actualización de P_in (cc_value_control) solo si hubo un mensaje de input CC real
    if not is_version_trigger_call and original_msg_or_dummy and original_msg_or_dummy.type == 'control_change':
        cc_value_control[(original_msg_or_dummy.channel, original_msg_or_dummy.control)] = original_msg_or_dummy.value
        
    return generated_outputs_with_meta

def process_version_activated_filters(new_version_activated, all_filters_list, device_aliases_g, mido_ports_map_g, is_virtual_mode_now, virtual_out_obj=None, virtual_out_name=""):
    global monitor_active, cc_value_sent # Para logueo y actualización de L_out
    
    # print(f"[*] Procesando filtros 'sin device_in' para activación de Versión: {new_version_activated}") # Log opcional
    generated_outputs_for_version_activation = []

    for f_config in all_filters_list:
        if f_config.get("device_in") is None: # CONDICIÓN 1: Sin device_in explícito en JSON
            
            applies_to_this_version_change = False
            version_cond_in_filter = f_config.get("version")

            if version_cond_in_filter is None:
                applies_to_this_version_change = True 
                # if monitor_active: print(f"    V_INFO: Filtro '{f_config.get('_filter_id_str', 'ID?')}': Sin device_in y sin 'version' -> activando para V{new_version_activated}.")
            elif isinstance(version_cond_in_filter, int) and version_cond_in_filter == new_version_activated:
                applies_to_this_version_change = True
            elif isinstance(version_cond_in_filter, list) and new_version_activated in version_cond_in_filter:
                applies_to_this_version_change = True

            if applies_to_this_version_change:
                # if monitor_active and f_config.get("output"): # Solo loguear si hay outputs definidos para este filtro
                #      print(f"    VU: Variables de usuario de '{f_config.get('_filter_id_str', 'ID?')}' para v{new_version_activated}.")

                outputs_from_filter = process_midi_event_new_logic( DUMMY_MSG_FOR_VERSION_TRIGGER, DUMMY_PORT_NAME_FOR_VERSION_TRIGGER, f_config, new_version_activated, device_aliases_g, mido_ports_map_g, is_virtual_mode_now, virtual_out_obj, virtual_out_name
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
                        log_line = format_midi_message_for_log(msg_to_send, prefix="  >> OUT: ", active_version=new_version_activated, rule_id_source=src_filter_id_str, target_port_alias_for_log_output=dest_alias_str)
                        if log_line: print(f"{log_line}")
                    
                    if sent_event_type_str == 'control_change':
                        cc_value_sent[(msg_to_send.channel, msg_to_send.control)] = msg_to_send.value 
                except Exception as e_send: 
                    if monitor_active: print(f"      ERR V_SEND: {e_send} (para '{dest_alias_str}', msg: {msg_to_send})")
    # elif monitor_active: # Log si no hubo acciones
        # (Comentado para reducir verbosidad, puedes reactivarlo si es útil)
        # ...

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
            line_content = f"{marker} {file_path_obj.name}"
            if i == current_selection_index_ui: fragments.append(f"<style bg='ansiblue' fg='ansiwhite'>> {line_content}</style>\n")
            else: fragments.append(f"  {line_content}\n")
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

# --- Main Application ---
def main():
    global shutdown_flag, current_active_version, available_versions, RULES_DIR, monitor_active, global_device_aliases
    global cc_value_sent, cc_value_control, user_named_vars

    initialize_cc_storage() 
    signal.signal(signal.SIGINT, signal_handler)

    script_version = "1.0" # Actualizar versión
    help_desc = f"""MIDImod {script_version}: Procesador MIDI avanzado con transformaciones y enrutamiento flexible."""
    help_epilog = f"""
-------------------------------------------------------------------------------
MIDImod {script_version} - Command Line Usage
-------------------------------------------------------------------------------

**Basic Syntax:**
  python {Path(sys.argv[0]).name} [rule_files...] [options]

**Arguments & Options:**

  `rule_files...`
    (Optional) One or more rule file names (without the .json extension)
    located in the '{RULES_DIR_NAME}/' directory.
    If no rule files are provided, an interactive selector will launch.
    Rules from multiple files are combined.

  `--list-ports`
    Lists all available MIDI input and output ports and exits.
    Useful for identifying device names for your JSON 'device_alias' section.

  `--virtual-ports`
    Enables virtual MIDI port mode. MIDImod will create an input port
    (default: 'MIDImod_IN') and an output port (default: 'MIDImod_OUT')
    for inter-application MIDI routing (e.g., with DAWs).

  `--vp-in NAME`
    Specifies a custom name for the virtual MIDI input port.
    (Requires --virtual-ports). Default: 'MIDImod_IN'.

  `--vp-out NAME`
    Specifies a custom name for the virtual MIDI output port.
    (Requires --virtual-ports). Default: 'MIDImod_OUT'.

  `--no-log`
    Starts MIDImod without the real-time MIDI message monitor in the console.

  `--help`, `-h`
    Displays this help message and exits.

**Examples:**

  - List MIDI ports:
    `python {Path(sys.argv[0]).name} --list-ports`

  - Load 'my_setup.json' and 'performance_rules.json':
    `python {Path(sys.argv[0]).name} my_setup performance_rules`

  - Use virtual ports with rules from 'daw_integration.json':
    `python {Path(sys.argv[0]).name} daw_integration --virtual-ports`

  - Use custom named virtual ports:
    `python {Path(sys.argv[0]).name} --virtual-ports --vp-in "MyMIDImodInput" --vp-out "ToDAW"`

-------------------------------------------------------------------------------
Detailed MIDI processing logic is defined within the JSON rule files.
For information on the JSON file structure, please refer to README.md.
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
    args = parser.parse_args()

    monitor_active = args.monitor_active_cli
    RULES_DIR = Path(f"./{RULES_DIR_NAME}") 
    if args.list_ports: list_midi_ports_action(); return


    virtual_port_mode_active = args.virtual_ports
    virtual_input_name = args.vp_in
    virtual_output_name = args.vp_out

    if virtual_port_mode_active:
        print(f"\n[*] MODO PUERTO VIRTUAL ACTIVADO:")
        print(f"    - Escuchando en: '{virtual_input_name}'")
        print(f"    - Enviando a:    '{virtual_output_name}'")

    rule_file_names_to_load = args.rule_files
    if not rule_file_names_to_load : # Si está vacío (vino de CLI como lista vacía) o es None (default)
        selected_names = interactive_rule_selector()
        if selected_names is None: return # Cancelado
        if not selected_names: print("Saliendo."); return
        rule_file_names_to_load = selected_names

    print(f"\n--- Reglas ---")
    print(f"Cargando reglas: {', '.join(rule_file_names_to_load)}")
    all_loaded_filters = []
    files_processed_summary = []

    for rule_file_name_stem_from_cli in rule_file_names_to_load:
        file_path = RULES_DIR / f"{rule_file_name_stem_from_cli}.json"
        summary_entry = {"filename": file_path.name, "status": "error", "aliases_found": 0, "filters_found": 0, "error_msg": ""}
        if not file_path.exists():
            summary_entry["error_msg"] = "Archivo no encontrado."; files_processed_summary.append(summary_entry)
            print(f"Error: Archivo '{file_path.name}' no encontrado."); continue
        
        devices_from_this_file, filters_from_this_file = load_rule_file_new_structure(file_path) 
        
        if devices_from_this_file is None and filters_from_this_file is None: 
            summary_entry["error_msg"] = "Error al cargar o parsear JSON."; files_processed_summary.append(summary_entry); continue
        
        if devices_from_this_file is not None: 
            global_device_aliases.update(devices_from_this_file)
            summary_entry["aliases_found"] = len(devices_from_this_file)
            
        if filters_from_this_file is not None:
            valid_filters_this_file = []
            for i_filter_in_file, f_config_item in enumerate(filters_from_this_file): # Usar enumerate para el índice original
                if isinstance(f_config_item, dict):    
                    original_filter_index = f_config_item.get('_filter_id_in_file', i_filter_in_file) # Usar el índice del bucle si no está
                    f_config_item["_filter_id_str"] = f"{rule_file_name_stem_from_cli}.{original_filter_index}"
                    valid_filters_this_file.append(f_config_item)


        all_loaded_filters.extend(valid_filters_this_file)
        summary_entry["filters_found"] = len(valid_filters_this_file)

        
        summary_entry["status"] = "ok"; files_processed_summary.append(summary_entry)

    print("\nFicheros cargados:")
    for s in files_processed_summary:
        if s["status"] == "ok": print(f"  - '{s['filename']}': OK ({s['filters_found']} filtros)")
        else: print(f"  - '{s['filename']}': Error ({s['error_msg']})")
    
    if not all_loaded_filters: print("\nNo se cargaron filtros válidos. Saliendo."); return

    collect_available_versions_from_filters(all_loaded_filters)
    
    # --- Preparación de Puertos ---
    opened_ports_tracking = {} # key: full_port_name, value: {"obj": mido_port, "type": "in"/"out", "alias_used": alias_o_subcadena}
    active_input_handlers = {} # key: full_port_name, value: mido_input_port_obj (subconjunto de opened_ports_tracking)
    
    print("\n--- Apertura de Puertos MIDI ---")

    virtual_output_port_object_ref = None # Asegurar que está definida

    if virtual_port_mode_active:
        print(f"Abriendo puertos virtuales...")
        
        # --- INICIO DE CAMBIO: Lógica de apertura de puerto virtual de ENTRADA más robusta ---
        actual_vp_in_name_to_open = None
        available_input_ports = mido.get_input_names() # Obtener nombres una vez
        for name in available_input_ports:
            if virtual_input_name.lower() in name.lower(): # Buscar subcadena insensible a mayúsculas
                actual_vp_in_name_to_open = name 
                break
        
        if actual_vp_in_name_to_open:
            try:
                in_port_obj = mido.open_input(actual_vp_in_name_to_open) 
                active_input_handlers[actual_vp_in_name_to_open] = in_port_obj 
                opened_ports_tracking[actual_vp_in_name_to_open] = {"obj": in_port_obj, "type": "in", "alias_used": "virtual_in"}
                print(f"  - [IN-VIRTUAL] Abierto '{actual_vp_in_name_to_open}' (buscando '{virtual_input_name}')")
            except Exception as e:
                print(f"  [!] ERROR abriendo puerto virtual IN '{actual_vp_in_name_to_open}' (buscando '{virtual_input_name}'): {e}.")
                return 
        else:
            print(f"  [!] ERROR: Puerto virtual de ENTRADA que contenga '{virtual_input_name}' no encontrado.")
            print(f"    Puertos de entrada disponibles: {available_input_ports}")
            return

        actual_vp_out_name_to_open = None
        available_output_ports = mido.get_output_names() # Obtener nombres una vez
        for name in available_output_ports:
            if virtual_output_name.lower() in name.lower(): # Buscar subcadena insensible a mayúsculas
                actual_vp_out_name_to_open = name
                break

        if actual_vp_out_name_to_open:
            try:
                out_port_obj = mido.open_output(actual_vp_out_name_to_open)
                opened_ports_tracking[actual_vp_out_name_to_open] = {"obj": out_port_obj, "type": "out", "alias_used": "virtual_out"}
                virtual_output_port_object_ref = out_port_obj # Guardar el objeto para pasarlo después
                print(f"  - [OUT-VIRTUAL] Abierto '{actual_vp_out_name_to_open}' (buscando '{virtual_output_name}')")
            except Exception as e:
                print(f"  [!] ERROR abriendo puerto virtual OUT '{actual_vp_out_name_to_open}' (buscando '{virtual_output_name}'): {e}.")
                # Considerar si retornar aquí o permitir continuar sin output virtual
        else:
            print(f"  [!] ERROR: Puerto virtual de SALIDA que contenga '{virtual_output_name}' no encontrado.")
            print(f"    Puertos de salida disponibles: {available_output_ports}")

    else: # Modo normal, basado en JSON
        print("Abriendo puertos según JSON...")
        required_input_ports_details = {}
        required_output_ports_details = {}

        for f_config_ports in all_loaded_filters: # Renombrar para evitar conflicto con f_config más abajo
            f_id = f_config_ports["_filter_id_str"]
            dev_in_alias_ports = f_config_ports.get("device_in")
            if dev_in_alias_ports is not None:
                key_in = global_device_aliases.get(dev_in_alias_ports, dev_in_alias_ports)
                if key_in not in required_input_ports_details: 
                    required_input_ports_details[key_in] = {"is_alias": (dev_in_alias_ports in global_device_aliases), "filters_using_it": []}
                required_input_ports_details[key_in]["filters_using_it"].append(f_id)
            
            # Determinar outputs requeridos (considerando output implícito y lista de outputs)
            output_defs_for_port_check = []
            if isinstance(f_config_ports.get("output"), list) and len(f_config_ports["output"]) > 0:
                output_defs_for_port_check.extend(f_config_ports["output"])
            elif f_config_ports.get("device_out"): # Hay un output implícito a nivel de filtro
                output_defs_for_port_check.append(f_config_ports) 

            for out_idx, out_c in enumerate(output_defs_for_port_check):
                if not isinstance(out_c, dict): continue
                dev_out_alias_ports = out_c.get("device_out")
                # Heredar del filtro padre si out_c es un item de la lista y no tiene device_out
                if dev_out_alias_ports is None and out_c is not f_config_ports: # out_c es de la lista "output"
                    dev_out_alias_ports = f_config_ports.get("device_out")

                if dev_out_alias_ports:
                    key_out = global_device_aliases.get(dev_out_alias_ports, dev_out_alias_ports)
                    if key_out not in required_output_ports_details: 
                        required_output_ports_details[key_out] = {"is_alias": (dev_out_alias_ports in global_device_aliases), "filters_using_it": []}
                    required_output_ports_details[key_out]["filters_using_it"].append(f"{f_id}.Out{out_idx}")
        
        mido_all_input_names = mido.get_input_names(); mido_all_output_names = mido.get_output_names()
        for sub_or_alias_key, details in required_input_ports_details.items():
            port_name_to_open = find_port_by_substring(mido_all_input_names, sub_or_alias_key, "entrada")
            if port_name_to_open:
                if port_name_to_open not in opened_ports_tracking:
                    try:
                        in_port_obj = mido.open_input(port_name_to_open)
                        active_input_handlers[port_name_to_open] = in_port_obj
                        opened_ports_tracking[port_name_to_open] = {"obj": in_port_obj, "type": "in", "alias_used": sub_or_alias_key}
                        print(f"  - [IN] Abierto '{port_name_to_open}' (por '{sub_or_alias_key}')")
                    except Exception as e: print(f"  Error abriendo IN '{port_name_to_open}' (para '{sub_or_alias_key}'): {e}")
            else: print(f"  - [!] IN: Puerto para '{sub_or_alias_key}' no encontrado. {len(details['filters_using_it'])} filtros desactivados.")

        for sub_or_alias_key_out, details_out in required_output_ports_details.items():
            port_name_to_open_out = find_port_by_substring(mido_all_output_names, sub_or_alias_key_out, "salida")
            if port_name_to_open_out:
                if port_name_to_open_out not in opened_ports_tracking:
                    try:
                        out_port_obj = mido.open_output(port_name_to_open_out)
                        opened_ports_tracking[port_name_to_open_out] = {"obj": out_port_obj, "type": "out", "alias_used": sub_or_alias_key_out}
                        print(f"  - [OUT] Abierto '{port_name_to_open_out}' (por '{sub_or_alias_key_out}')")
                    except Exception as e: print(f"  Error abriendo OUT '{port_name_to_open_out}' (para '{sub_or_alias_key_out}'): {e}")
            else: print(f"  - [!] OUT Puerto para '{sub_or_alias_key_out}' no encontrado.")

    
    active_filters_final = []
    if virtual_port_mode_active: # global virtual_port_mode_active debe estar disponible
        if active_input_handlers:
            active_filters_final.extend(all_loaded_filters)
        else:
            if monitor_active: 
                print("[!] No se pudo abrir el puerto virtual de entrada. No se activarán filtros que dependan de MIDI.")
            active_filters_final.extend([f_cfg for f_cfg in all_loaded_filters if f_cfg.get("device_in") is None])

    else: # Modo normal (tu lógica existente)
        for f_config in all_loaded_filters: 
            dev_in_alias_filter = f_config.get("device_in")
            if dev_in_alias_filter is None:
                active_filters_final.append(f_config)
            else:
                dev_in_sub_filter = global_device_aliases.get(dev_in_alias_filter, dev_in_alias_filter)
                is_input_port_active_for_this_filter = False
                for opened_full_port_name in active_input_handlers.keys():
                    if dev_in_sub_filter.lower() in opened_full_port_name.lower():
                        is_input_port_active_for_this_filter = True
                        break
                if is_input_port_active_for_this_filter:
                    active_filters_final.append(f_config)
                else:
                    print(f"  [!]: Filtro '{f_config['_filter_id_str']}' desactivado (IN:'{dev_in_alias_filter}' ['{dev_in_sub_filter}'] no está abierto).")


    if not active_input_handlers: print("\nNo hay puertos de ENTRADA MIDI activos. Saliendo."); return
    if not active_filters_final: print("\nNo hay filtros activos. Saliendo."); return

    summarize_active_processing_config(active_filters_final, global_device_aliases, opened_ports_tracking, virtual_port_mode_active, virtual_input_name, virtual_output_name)

    monitor_status_str = "activo" if monitor_active else "desactivado"

    print(f"\n{len(active_filters_final)} filtro(s), {len(active_input_handlers)} puerto(s) IN. ")
    if len(available_versions) > 1 or (len(available_versions)==1 and 0 not in available_versions) : # Mostrar si hay más de una o si la única no es 0
        print(f"Versión {current_active_version}/{len(available_versions) - 1} (cambiar con [0-{len(available_versions) - 1}], [Espacio]).")
    print(f"Monitor {monitor_status_str} (cambiar con 'm').")
    print("[!] Ctrl+C para salir. Procesando... \n")

    print(f"[*] Versión {current_active_version}/{len(available_versions) - 1}")
    process_version_activated_filters(current_active_version, all_loaded_filters, global_device_aliases, opened_ports_tracking,
                                    virtual_port_mode_active, virtual_output_port_object_ref, virtual_output_name)

    # print(f"[*] Ctrl+C para salir. Procesando MIDI para v{current_active_version}...\n")

    try:
        while not shutdown_flag:
            # --- MANEJO DE TECLADO ---
            kb_char_processed_this_loop = False # Resetear para este ciclo del while
            char_input = get_char_non_blocking()
            if char_input:
                kb_char_processed_this_loop = True
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
                
                if version_changed_by_kb and current_active_version != prev_active_version_kb:
                    print(f"[*] Versión {current_active_version}/{len(available_versions) - 1}")
                    process_version_activated_filters(current_active_version, all_loaded_filters, global_device_aliases, opened_ports_tracking, virtual_port_mode_active, virtual_output_port_object_ref, virtual_output_name)
                elif version_changed_by_kb and char_input.isdigit() and current_active_version == prev_active_version_kb : 
                    print(f"[*] Versión '{char_input}' no disponible o ya activa. Actual: V{current_active_version}.")

            # --- PROCESAMIENTO MIDI ---
            midi_event_processed_this_loop = False # Resetear para este ciclo del while

            for port_full_name, mido_in_port_obj in active_input_handlers.items():
                original_input_msg = mido_in_port_obj.poll()

                if original_input_msg: # SOLO SI HAY UN MENSAJE MIDI REAL
                    
                    # if original_input_msg.type == 'clock' and not monitor_active:
                        # continue 

                    midi_event_processed_this_loop = True 
                    vmap_consumed_event = False
                    version_before_action = current_active_version 

                    # --- 1. Procesamiento de Version Mappers Globales ---
                    if global_version_mappers:
                        # msg_copy_for_vmap = original_input_msg.copy() # Se crea después de la comprobación
                        
                        temp_msg_for_vmap_logic = None # Variable temporal para el mensaje a usar en la lógica de vmap
                        
                        if original_input_msg.type == 'note_on' and original_input_msg.velocity == 0:
                            # Crear un NUEVO mensaje note_off
                            temp_msg_for_vmap_logic = mido.Message('note_off',
                                                                 channel=original_input_msg.channel,
                                                                 note=original_input_msg.note,
                                                                 velocity=0) # O la velocidad que consideres para el note_off
                        else:
                            # Usar una copia del mensaje original
                            temp_msg_for_vmap_logic = original_input_msg.copy()

                        for vm_rule in global_version_mappers:
                            rule_match = True 

                            vm_dev_alias = vm_rule.get("device_in")
                            if not vm_dev_alias: rule_match = False
                            
                            if rule_match: 
                                vm_dev_substr = global_device_aliases.get(vm_dev_alias, vm_dev_alias)
                                if vm_dev_substr.lower() not in port_full_name.lower():
                                    rule_match = False
                            
                            if rule_match and "ch_in" in vm_rule and getattr(temp_msg_for_vmap_logic, 'channel', -1) != vm_rule["ch_in"]:
                                rule_match = False
                            
                            if rule_match:
                                vm_event = vm_rule.get("event_in")
                                if vm_event:
                                    msg_event = temp_msg_for_vmap_logic.type
                                    if vm_event == "note" and msg_event not in ["note_on", "note_off"]: rule_match = False
                                    elif vm_event == "cc" and msg_event != "control_change": rule_match = False
                                    elif vm_event == "pc" and msg_event != "program_change": rule_match = False
                                    elif vm_event not in ["note", "cc", "pc"] and msg_event != vm_event: rule_match = False
                                else: 
                                    rule_match = False
                            
                            if rule_match and "value_1_in" in vm_rule:
                                msg_v1 = -1
                                if temp_msg_for_vmap_logic.type in ['note_on', 'note_off']: msg_v1 = temp_msg_for_vmap_logic.note
                                elif temp_msg_for_vmap_logic.type == 'control_change': msg_v1 = temp_msg_for_vmap_logic.control
                                elif temp_msg_for_vmap_logic.type == 'program_change': msg_v1 = temp_msg_for_vmap_logic.program
                                if msg_v1 != vm_rule["value_1_in"]: rule_match = False
                            
                            if rule_match and "value_2_in" in vm_rule and vm_rule["value_2_in"] is not None:
                                msg_v2 = getattr(temp_msg_for_vmap_logic, 'velocity', getattr(temp_msg_for_vmap_logic, 'value', -1))
                                if isinstance(vm_rule["value_2_in"], str) and vm_rule["value_2_in"].startswith(">"):
                                    try:
                                        limit = int(vm_rule["value_2_in"][1:])
                                        if not (msg_v2 > limit): rule_match = False
                                    except (ValueError, TypeError): rule_match = False
                                elif msg_v2 != vm_rule["value_2_in"]:
                                    rule_match = False
                            
                            if rule_match:
                                vmap_consumed_event = True
                                action_config = vm_rule.get("version_out") # Obtener la configuración original
                                version_changed_by_vmap = False
                                
                                if monitor_active: 
                                    vm_log_src = vm_rule.get('_source_file', 'VMAP') + "." + str(vm_rule.get('_vmap_id_in_file', '?'))
                                    # temp_msg_for_vmap_logic fue definido unas líneas antes
                                    log_in_vmap = format_midi_message_for_log(temp_msg_for_vmap_logic, "IN: ", version_before_action,
                                                                              input_port_actual_name=port_full_name,
                                                                              device_aliases_global_map=global_device_aliases)
                                    if log_in_vmap: print(f"{log_in_vmap} >> (VMap '{vm_log_src}' -> Acción: '{action_config}')")

                                prev_version_for_this_action = current_active_version
                                final_action_to_process = None

                                if isinstance(action_config, str):
                                    # Primero, verificar si es una de las cadenas especiales directamente
                                    if action_config.lower() in ["cycle", "cycle_next", "cycle_previous"]:
                                        final_action_to_process = action_config.lower()
                                    else:
                                        # Si no, intentar evaluarla como expresión.
                                        # `evaluate_expression` accede a `user_named_vars` globalmente.
                                        # Creamos un contexto básico para el mensaje que disparó el vmap,
                                        # por si la expresión lo necesitara y `evaluate_expression` se adaptara.
                                        # El `context_vars_for_eval` de `evaluate_expression` espera "ch0_in_ctx", etc.
                                        
                                        # Contexto mínimo para `evaluate_expression` (principalmente para las var_#)
                                        # (El acceso a `channel_in` etc. del mensaje disparador del vmap
                                        # requeriría un mapeo o adaptación de `evaluate_expression`)
                                        expression_eval_context = {
                                            "version": version_before_action 
                                        }
                                        
                                        # (Opcional: si se quiere pasar explícitamente el contexto del mensaje del vmap)
                                        # expression_eval_context = {
                                        #    'ch0_in_ctx': getattr(temp_msg_for_vmap_logic, 'channel', -1),
                                        #    'value_in_1_ctx': getattr(temp_msg_for_vmap_logic, 'note', getattr(temp_msg_for_vmap_logic, 'control', 0)),
                                        #    'value_in_2_ctx': getattr(temp_msg_for_vmap_logic, 'velocity', getattr(temp_msg_for_vmap_logic, 'value', 0)),
                                        #    'event_type_in_ctx': temp_msg_for_vmap_logic.type
                                        # }
                                        
                                        evaluated_expr_result = evaluate_expression(action_config, expression_eval_context)

                                        if isinstance(evaluated_expr_result, (int, str)):
                                            final_action_to_process = evaluated_expr_result
                                        elif evaluated_expr_result is not None and monitor_active:
                                            print(f"Adv (VMap): Expr. 'version_out: {action_config}' evaluó a tipo {type(evaluated_expr_result)}. Ignorado.")
                                        # Si es None (error de evaluación o expresión no válida), final_action_to_process sigue None

                                elif isinstance(action_config, int):
                                    final_action_to_process = action_config

                                # --- Ahora procesar final_action_to_process ---
                                if isinstance(final_action_to_process, int):
                                    if final_action_to_process in available_versions and current_active_version != final_action_to_process:
                                        current_active_version = final_action_to_process
                                        version_changed_by_vmap = True
                                elif isinstance(final_action_to_process, str):
                                    action_lower = final_action_to_process.lower()
                                    current_idx = available_versions.index(current_active_version) if current_active_version in available_versions else -1
                                    
                                    if action_lower in ["cycle", "cycle_next"] and available_versions:
                                        new_version_idx = (current_idx + 1) % len(available_versions)
                                        if available_versions[new_version_idx] != current_active_version:
                                            current_active_version = available_versions[new_version_idx]
                                            version_changed_by_vmap = True
                                    elif action_lower == "cycle_previous" and available_versions:
                                        new_version_idx = (current_idx - 1 + len(available_versions)) % len(available_versions)
                                        if available_versions[new_version_idx] != current_active_version:
                                            current_active_version = available_versions[new_version_idx]
                                            version_changed_by_vmap = True
                                    elif action_config != final_action_to_process and monitor_active : # Era una expresión que evaluó a una string no reconocida
                                        print(f"Adv (VMap): Expr. 'version_out: {action_config}' evaluó a string '{final_action_to_process}' no es acción válida. Ignorado.")
                                
                                if version_changed_by_vmap: 
                                    print(f"[*] Versión {current_active_version}/{len(available_versions) - 1}")
                                    process_version_activated_filters(current_active_version, all_loaded_filters, global_device_aliases, opened_ports_tracking, virtual_port_mode_active, virtual_output_port_object_ref, virtual_output_name)
                                break # Salir del bucle de vm_rule porque ya se procesó una
                    
                    if vmap_consumed_event:
                        continue 

                    all_generated_output_msgs_meta = []
                    for event_filter_config in active_filters_final:
                        outputs_from_this_filter = process_midi_event_new_logic(
                            original_input_msg, port_full_name, event_filter_config,
                            current_active_version, global_device_aliases, opened_ports_tracking,
                            virtual_port_mode_active, virtual_output_port_object_ref, virtual_output_name
                        )
                        if outputs_from_this_filter:
                            all_generated_output_msgs_meta.extend(outputs_from_this_filter)
                 
                    # --- INICIO DEL BLOQUE QUE DEBES INSERTAR/RESTAURAR ---
                    # --- BLOQUE DE ENVÍO DE MENSAJES MIDI (FUERA DE if monitor_active) ---
                    if all_generated_output_msgs_meta:
                        for (msg_to_send, dest_port_obj, dest_alias_str, src_filter_id_str,
                             sent_event_type_str, abs_val_for_cc_sent_if_cc) in all_generated_output_msgs_meta:
                            if dest_port_obj and hasattr(dest_port_obj, "send"):
                                try:
                                    dest_port_obj.send(msg_to_send)
                                    if sent_event_type_str == 'control_change':
                                        cc_value_sent[(msg_to_send.channel, msg_to_send.control)] = msg_to_send.value
                                except Exception as e_send:
                                    print(f"  ERR SEND: {e_send} (al puerto para '{dest_alias_str}', msg: {msg_to_send})")
                    # --- FIN DEL BLOQUE DE ENVÍO ---
                    # --- FIN DEL BLOQUE QUE DEBES INSERTAR/RESTAURAR ---

                    # --- INICIO DEL BLOQUE DE LOGGING (DENTRO DE if monitor_active) ---
                    if monitor_active:
                        # Primero, intentar loguear el mensaje de entrada
                        log_msg_input_formatted = None
                        if original_input_msg: # Solo si hay un mensaje de entrada
                            log_msg_input_formatted = format_midi_message_for_log(
                                original_input_msg, prefix="IN: ", active_version=current_active_version,
                                input_port_actual_name=port_full_name, device_aliases_global_map=global_device_aliases
                            )
                            if log_msg_input_formatted:
                                print(log_msg_input_formatted)
                            elif original_input_msg.type == 'clock' and all_generated_output_msgs_meta:
                                # Si la entrada fue un clock que generó salidas, imprimir una cabecera para los OUT
                                print(f"[{current_active_version}] IN:[{port_full_name}] Clock (generó lo siguiente):")

                        # Luego, si hay mensajes de salida, loguearlos
                        if all_generated_output_msgs_meta:
                            for out_m_log, _, alias_log, rule_log, _, _ in all_generated_output_msgs_meta:
                                log_msg_output_formatted = format_midi_message_for_log(
                                    out_m_log, prefix="  >> OUT: ", active_version=current_active_version,
                                    rule_id_source=rule_log, target_port_alias_for_log_output=alias_log,
                                    device_aliases_global_map=global_device_aliases
                                )
                                if log_msg_output_formatted: print(log_msg_output_formatted)
                        # Si no hubo salidas Y el input era logueable (y no era clock que ya imprimió cabecera)
                        elif log_msg_input_formatted: # Implica que original_input_msg existía y no era clock/activesense
                            print(f"{log_msg_input_formatted} >> [NOUT]")
                    # --- FIN DEL BLOQUE DE LOGGING ---
                # else: original_input_msg era None


            if not midi_event_processed_this_loop and not kb_char_processed_this_loop:
                time.sleep(0.001)

    except KeyboardInterrupt:
        if not shutdown_flag: shutdown_flag=True # Asegurar que el flag se setea
        print("\nInterrupción por teclado recibida en el bucle principal.")
    except Exception as e_main_loop:
        if not shutdown_flag: # Solo imprimir si no es parte del cierre normal
            print(f"\nERROR INESPERADO EN BUCLE PRINCIPAL: {e_main_loop}")
            traceback.print_exc()
    finally:
        print("\nCerrando puertos y deteniendo de MIDImod...")
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
    
    initialize_cc_storage() # Inicializar ANTES de llamar a main()
    main()