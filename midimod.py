import mido
import time
import json
import argparse
import traceback
import signal
import os
from pathlib import Path
import sys

RULES_DIR = Path("./rules")
shutdown_flag = False
current_active_version = 0
available_versions = {0} 

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
        current_settings = termios.tcgetattr(fd) 
        try:
            tty.setraw(fd)
            if select.select([sys.stdin], [], [], 0.0)[0]: return sys.stdin.read(1)
        except Exception: pass
        finally:
            if _original_termios_settings and _original_termios_settings_fd == fd :
                try: termios.tcsetattr(fd, termios.TCSADRAIN, _original_termios_settings)
                except termios.error: pass
        return None

from prompt_toolkit import Application
from prompt_toolkit.layout.containers import HSplit, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.formatted_text import HTML

def signal_handler(sig, frame): global shutdown_flag; shutdown_flag = True

def find_port_by_substring(ports, sub, type_desc="puerto"):
    if not ports: return None
    if not sub: return ports[0]
    for name in ports:
        if sub.lower() in name.lower(): return name
    return None

def _load_json_file_content(filepath: Path):
    """Función auxiliar para cargar y parsear un archivo JSON completo."""
    if not filepath.is_file():
        return None
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = json.load(f)
        return content
    except json.JSONDecodeError:
        print(f"Err: Archivo '{filepath.name}' no es JSON válido.") # Mensaje más conciso
    except UnicodeDecodeError:
        print(f"Err Cod: Archivo '{filepath.name}' no es UTF-8.")
    except Exception as e:
        print(f"Err inesperado cargando '{filepath.name}': {e}")
    return None

def load_route_configurations_from_file(fp: Path):
    if not fp.is_file(): return [] 
    try:
        with open(fp, 'r', encoding='utf-8') as f: data = json.load(f)
        routes = []
        item_list = data if isinstance(data, list) else [data]
        for i, item in enumerate(item_list):
            is_transform_route = isinstance(item, dict) and "transformations" in item
            is_direct_action = isinstance(item, dict) and "action_type" in item and "trigger_message" in item # V17 no usa action_type explícito
            if is_transform_route: # V17 se enfoca en rutas con transformations
                item["_source_file"] = fp.name; routes.append(item)
            elif isinstance(data, list): 
                print(f"Adv: Item #{i} en '{fp.name}' no es una configuración de ruta válida (necesita 'transformations').")
        if not routes and not isinstance(data, list) and (isinstance(data,dict) and not ("transformations" in data)):
            print(f"Adv: Contenido de '{fp.name}' no es una ruta o lista de rutas válida.")
        return routes
    except json.JSONDecodeError: print(f"Err: '{fp.name}' no es JSON válido.")
    except UnicodeDecodeError: print(f"Err Cod: '{fp.name}' no es UTF-8.")
    except Exception as e: print(f"Err cargando '{fp.name}': {e}")
    return []

def load_all_selected_routes_with_load_info(names: list[str]):
    all_routes_collected = []
    files_info = []

    for name in names:
        fp = RULES_DIR / f"{name}.json"
        file_info_entry = {"filename": f"{name}.json", "num_routes": 0, "status": "error", "error_msg": ""}
        
        if not fp.exists():
            file_info_entry["error_msg"] = "Archivo no encontrado."
            files_info.append(file_info_entry)
            continue
            
        file_content = _load_json_file_content(fp) # Usar la nueva auxiliar
        
        if file_content and isinstance(file_content, dict) and "routes" in file_content and isinstance(file_content["routes"], list):
            routes_from_this_file = file_content["routes"]
            valid_routes_in_file = []
            for i, item in enumerate(routes_from_this_file):
                if isinstance(item, dict) and "transformations" in item:
                    item["_source_file"] = fp.name
                    valid_routes_in_file.append(item)
                else:
                    print(f"Adv: Item #{i} en la lista 'routes' de '{fp.name}' no es una ruta válida.")

            file_info_entry["num_routes"] = len(valid_routes_in_file)
            if len(valid_routes_in_file) > 0:
                file_info_entry["status"] = "ok"
                all_routes_collected.extend(valid_routes_in_file)
            else:
                file_info_entry["error_msg"] = "Sección 'routes' vacía o sin rutas válidas."
        elif file_content and ("routes" not in file_content or not isinstance(file_content.get("routes"), list)):
             file_info_entry["error_msg"] = "Archivo no contiene una sección 'routes' válida como lista."
        elif not file_content: # Error al cargar/parsear el archivo
            file_info_entry["error_msg"] = "Error al leer o parsear el archivo JSON."
        
        files_info.append(file_info_entry)
            
    return all_routes_collected, files_info

def collect_available_versions(all_route_configurations):
    global available_versions
    versions = {0} 
    for route_conf in all_route_configurations:
        for transform in route_conf.get("transformations", []):
            if "version" in transform and isinstance(transform["version"], int):
                versions.add(transform["version"])
    available_versions = sorted(list(versions))
    if not available_versions: available_versions = [0]


def format_rule_details_for_summary(rule_dict, base_indent="        ", is_always_active_rule=False, current_summary_version=None):
    lines = []
    comment = rule_dict.get("_comment", " ")
    
    # Solo mostrar el comentario directamente si es la única clave relevante (aparte de 'version' si se filtra)
    keys_in_rule = list(rule_dict.keys())
    is_comment_only_rule = True
    for k in keys_in_rule:
        if k == "_comment": continue
        if k == "version" and (is_always_active_rule or current_summary_version is not None): continue
        is_comment_only_rule = False; break
        

    if is_comment_only_rule: # Si solo queda el comentario
        lines.append(f"\n{base_indent}< {comment} >") 
    else:
        lines.append(f"\n{base_indent}( {comment} )") # Con guion, como un item de lista

    child_indent = base_indent + "  "
    for key, value in rule_dict.items():
        if key == "_comment": continue
        if key == "version" and (is_always_active_rule or current_summary_version is not None): continue 
            
        value_str = ""
        if isinstance(value, str): value_str = value
        elif isinstance(value, bool): value_str = str(value).lower()
        elif isinstance(value, (int, float)): value_str = str(value)
        elif isinstance(value, list):
            list_items_str = [str(item) if not isinstance(item, str) else item for item in value]
            value_str = f"[{', '.join(list_items_str)}]"
        elif isinstance(value, dict):
            lines.append(f"{child_indent}{key}: {{")
            for sub_key, sub_value in value.items():
                sub_value_str = str(sub_value) if not isinstance(sub_value, str) else sub_value
                lines.append(f"{child_indent}  {sub_key}: {sub_value_str}")
            lines.append(f"{child_indent}}}")
            continue 
        else: value_str = str(value)
        lines.append(f"{child_indent}{key}: {value_str}")
    return lines

# --- MODIFICADA: summarize_active_processing_units ---
def summarize_active_processing_units(active_handlers: dict, device_aliases_map: dict = None): # Añadido device_aliases_map
    # device_aliases_map es opcional por si se llama desde otro sitio sin él, aunque main() lo pasará.
    if device_aliases_map is None:
        device_aliases_map = {} # Default a dict vacío si no se pasa

    print("\n--- Rutas de Procesamiento ---") 
    num_total_active_routes = sum(len(data.get('routes', [])) for data in active_handlers.values())
    if not num_total_active_routes:
        print("No hay rutas de procesamiento activas.")
        print("----------------------------------------------------------")
        return
    
    global available_versions 
    print(f"Versiones disponibles: {available_versions}")

    items_by_source_then_input = {} 
    for in_port_name, handler_data in active_handlers.items():
        for route_conf in handler_data.get('routes', []):
            source_file = route_conf.get('_source_file', 'FuenteDesconocida.json')
            if source_file not in items_by_source_then_input:
                items_by_source_then_input[source_file] = {}
            if in_port_name not in items_by_source_then_input[source_file]:
                items_by_source_then_input[source_file][in_port_name] = []
            
            # Guardar el alias original para el resumen si se usó
            route_conf_copy = route_conf.copy() # No modificar la original en active_handlers
            route_conf_copy['_summary_in_port_alias_used'] = route_conf.get("input_device_alias", in_port_name)
            route_conf_copy['_summary_out_port_alias_used'] = route_conf.get("output_device_alias", 
                                                                       route_conf.get('_actual_out_port_obj_name', "N/A"))
            items_by_source_then_input[source_file][in_port_name].append(route_conf_copy)


    for source_file, inputs_for_source in items_by_source_then_input.items():
        print(f"\n({source_file})") 
        for in_port_name, routes_in_input_for_source in inputs_for_source.items():
            for route_conf in routes_in_input_for_source:
                route_id_str = route_conf['_id_str']
                
                # Mostrar el alias usado y el nombre real resuelto
                in_display = f"'{route_conf['_summary_in_port_alias_used']}' ({in_port_name})"
                out_display = f"'{route_conf['_summary_out_port_alias_used']}' ({route_conf.get('_actual_out_port_obj_name', 'N/A')})"
                
                print(f"{route_id_str}: {in_display} >> {out_display}")

                route_level_comment = route_conf.get("_comment")
                if route_level_comment: print(f"  _comment: {route_level_comment}")
                
                version_map = route_conf.get("version_midi_map")
                if version_map:
                    print(f"  version_midi_map: {{")
                    for map_key, map_val in version_map.items():
                        print(f"    {map_key}: {json.dumps(map_val)}")
                    print(f"  }}")
                
                transformations_list = route_conf.get("transformations", [])
                if not transformations_list:
                    print("      - Sin transformaciones definidas.")
                else:
                    for t_rule_dict in transformations_list:
                        is_always_active = "version" not in t_rule_dict
                        current_ver_for_summary = t_rule_dict.get("version") if not is_always_active else None
                        for line in format_rule_details_for_summary(
                            t_rule_dict, base_indent="      ", 
                            is_always_active_rule=is_always_active, 
                            current_summary_version=current_ver_for_summary):
                            print(line)
    print("----------------------------------------------------------")

def format_midi_message_for_log(msg, prefix="", active_version=-1):
    if msg.type in ['polytouch', 'clock']: return None
    version_prefix = f"[{active_version}] " if active_version != -1 else ""
    full_prefix = f"{version_prefix}{prefix}"
    parts = [full_prefix.strip()] # Asegurar que no haya espacios extra si un prefijo está vacío
    
    if msg.type in ['note_on', 'note_off']: 
        parts.append(f"ch({msg.channel + 1}) {msg.type.split('_')[0]}({msg.note}) vel({msg.velocity})")
    elif msg.type == 'control_change': 
        parts.append(f"ch({msg.channel + 1}) cc({msg.control}) val({msg.value})")
    elif msg.type == 'program_change': 
        parts.append(f"ch({msg.channel + 1}) pc({msg.program})")
    elif msg.type == 'pitchwheel': 
        parts.append(f"ch({msg.channel + 1}) pitch({msg.pitch})")
    elif msg.type == 'aftertouch':  
        parts.append(f"ch({msg.channel + 1}) at_val({msg.value})")
    elif msg.type == 'start': # CORREGIDO
        parts.append("START")
    elif msg.type == 'stop': # CORREGIDO
        parts.append("STOP")
    elif msg.type == 'continue': # CORREGIDO
        parts.append("CONTINUE")
    else: 
        # Para cualquier otro tipo de mensaje que no sea polytouch o clock (ya filtrados)
        parts.append(f"{msg.type}(raw_hex:{msg.hex()})") # raw_hex puede ser útil para depurar mensajes desconocidos

    current_text = "".join(p.strip() for p in parts if p.strip())
    initial_prefix_text = full_prefix.strip() # El prefijo completo que se añadió al principio
    
    # Si después de añadir la parte del mensaje, la cadena 'parts' solo contiene el prefijo inicial,
    # entonces el mensaje no tenía contenido formateable más allá del prefijo.
    # Esto evita loguear líneas como "[0] IN :" si el mensaje era, por ejemplo, uno desconocido sin datos.
    if current_text == initial_prefix_text and current_text: # Solo si current_text no está vacío
        # Excepción: los comandos de transporte como START/STOP/CONTINUE son válidos incluso si solo tienen el prefijo + el comando
        if msg.type not in ['start', 'stop', 'continue']: 
            return None
            
    if not current_text : return None # Si la cadena es totalmente vacía o solo espacios
    
    return " ".join(p.strip() for p in parts if p.strip()) # Limpiar partes vacías antes de unir


def process_message_with_rule(original_msg_for_this_rule, rule_config, active_version, out_port_for_actions=None):
    # Determinar si la regla tiene intención de actuar basado en claves presentes
    _rule_has_cc_action = "cc_in" in rule_config and ("cc_out" in rule_config or "cc_range" in rule_config)
    _rule_has_note_action = "nt_st" in rule_config or "velocity_range" in rule_config
    _rule_has_ch_action = "ch_out" in rule_config # ch_out: [] es una acción
    _has_note2cc_action = "note_to_cc" in rule_config
    _has_note2pc_action = "note_to_pc" in rule_config 
    _has_at2cc_action = "aftertouch_to_cc" in rule_config
    rule_had_intention_to_act = _rule_has_cc_action or _rule_has_note_action or _rule_has_ch_action or \
                                _has_note2cc_action or _has_at2cc_action or _has_note2pc_action

    # Comprobación de versión
    applies_this_version = False
    if "version" in rule_config:
        version_value  = rule_config["version"]
        if isinstance(version_value, int): # Si es un solo entero
            if version_value == active_version:
                applies_this_version = True
        elif isinstance(version_value, list): # Si es una lista de enteros
            if active_version in version_value:
                applies_this_version = True
    else: applies_this_version = True 
    if not applies_this_version: return [original_msg_for_this_rule], False

    msg_being_processed = original_msg_for_this_rule.copy()
    initial_m_dict_no_time = msg_being_processed.dict(); initial_m_dict_no_time.pop('time', None)
    
    rule_applies_based_on_ch_in = True 
    if "ch_in" in rule_config and hasattr(msg_being_processed, 'channel'):
        ch_in_values = rule_config["ch_in"]
        if not isinstance(ch_in_values, list): ch_in_values = [ch_in_values]
        if msg_being_processed.channel not in ch_in_values: rule_applies_based_on_ch_in = False
    if not rule_applies_based_on_ch_in: 
        return [msg_being_processed], False # No actuó si ch_in no coincide

    # --- Transformaciones que pueden cambiar tipo o consumir ---
    if "note_to_cc" in rule_config and isinstance(rule_config["note_to_cc"], dict):
        ntc_config = rule_config["note_to_cc"]
        is_effective_note_off = (msg_being_processed.type == 'note_off') or (msg_being_processed.type == 'note_on' and msg_being_processed.velocity == 0)
        is_effective_note_on = (msg_being_processed.type == 'note_on' and msg_being_processed.velocity > 0)
        if (is_effective_note_on or is_effective_note_off) and msg_being_processed.note == ntc_config.get("note_in"):
            cc_val=-1; 
            if is_effective_note_on :
                if ntc_config.get("use_velocity_as_value") is True: cc_val = msg_being_processed.velocity
                else: cc_val=ntc_config.get("value_on_note_on",127) 
            elif is_effective_note_off :cc_val=ntc_config.get("value_on_note_off",-1)
            if cc_val!=-1:
                out_cc=ntc_config.get("cc_out")
                if out_cc is not None:
                    cc_ch=ntc_config.get("ch_out_cc", msg_being_processed.channel)
                    return [mido.Message('control_change',channel=cc_ch,control=out_cc,value=max(0,min(127,cc_val)))], True 
            return [], True # Actuó (coincidió nota), pero no produjo CC (o consumió)
            
    elif "note_to_pc" in rule_config and isinstance(rule_config["note_to_pc"], dict):
        npc_config = rule_config["note_to_pc"]
        is_effective_note_off = (msg_being_processed.type == 'note_off')or(msg_being_processed.type == 'note_on' and msg_being_processed.velocity == 0)
        is_effective_note_on = (msg_being_processed.type == 'note_on' and msg_being_processed.velocity > 0)
        if (is_effective_note_on or is_effective_note_off) and msg_being_processed.note == npc_config.get("note_in"):
            should_send_pc=False
            if is_effective_note_on and npc_config.get("send_on_note_on", True):should_send_pc=True
            elif is_effective_note_off and npc_config.get("send_on_note_off", False):should_send_pc=True
            if should_send_pc:
                prog_out=npc_config.get("program_out")
                if prog_out is not None and 0<=prog_out<=127:
                    pc_ch=npc_config.get("ch_out_pc",msg_being_processed.channel)
                    return [mido.Message('program_change',channel=pc_ch,program=prog_out)],True
            return [],True 
            
    elif "aftertouch_to_cc" in rule_config and isinstance(rule_config["aftertouch_to_cc"],dict) and msg_being_processed.type=='aftertouch':
        atc_config=rule_config["aftertouch_to_cc"];out_cc=atc_config.get("cc_out")
        if out_cc is not None:
            at_val=msg_being_processed.value
            if "value_range" in atc_config and isinstance(atc_config["value_range"],list) and len(atc_config["value_range"])==2:
                try:
                    min_o,max_o=int(atc_config["value_range"][0]),int(atc_config["value_range"][1])
                    if 0<=min_o<=127 and 0<=max_o<=127 and min_o<=max_o:norm=at_val/127.0;scaled=norm*(max_o-min_o)+min_o;at_val=max(0,min(127,round(scaled)))
                except ValueError:pass
            at_ch=atc_config.get("ch_out_cc",msg_being_processed.channel);return [mido.Message('control_change',channel=at_ch,control=out_cc,value=at_val)],True
    
    # --- Si no fue una transformación de tipo, procesar CC/Nota normal ---
    # Filtro de cc_in para reglas de CC
    # Y aplicación de cc_out y cc_range
    elif msg_being_processed.type == 'control_change': # Cambiado a elif
        cc_action_this_rule = False # Para determinar si este bloque CC hizo algo
        if "cc_in" in rule_config:
            if msg_being_processed.control == rule_config["cc_in"]:
                # cc_in coincide, aplicar cc_range y luego cc_out
                value_to_scale = msg_being_processed.value 
                if "cc_range" in rule_config and isinstance(rule_config["cc_range"],list) and len(rule_config["cc_range"])==2:
                    try:
                        min_o,max_o=int(rule_config["cc_range"][0]),int(rule_config["cc_range"][1])
                        if 0<=min_o<=127 and 0<=max_o<=127 and min_o<=max_o:
                            norm=value_to_scale/127.0;scaled=norm*(max_o-min_o)+min_o
                            msg_being_processed.value=max(0,min(127,round(scaled)))
                    except ValueError:pass
                
                if "cc_out" in rule_config: 
                    msg_being_processed.control=rule_config["cc_out"]
                cc_action_this_rule = True # Marcamos que la acción de CC se aplicó
            else: # cc_in definido pero no coincide
                return [msg_being_processed], False # No actuó esta regla de CC
        # Si no hay cc_in en la regla, este bloque no modifica el CC a menos que se añada lógica para cc_range/cc_out globales
        if not cc_action_this_rule and not rule_had_intention_to_act : # Si no hubo acción CC y no hay otras intenciones (ej ch_out)
             return [msg_being_processed], False


    # --- Transformaciones de Notas (NT y Velocity) ---
    elif (msg_being_processed.type in ['note_on','note_off']):
        note_action_this_rule = False
        if "nt_st" in rule_config:
            msg_being_processed.note=max(0,min(127,msg_being_processed.note+rule_config["nt_st"]))
            note_action_this_rule = True
        if "velocity_range" in rule_config and isinstance(rule_config["velocity_range"], list) and len(rule_config["velocity_range"]) == 2:
            if hasattr(msg_being_processed, 'velocity') and msg_being_processed.velocity > 0 :
                try:
                    min_vel_out, max_vel_out = int(rule_config["velocity_range"][0]), int(rule_config["velocity_range"][1])
                    if 0 <= min_vel_out <= 127 and 0 <= max_vel_out <= 127 and min_vel_out <= max_vel_out:
                        original_velocity = msg_being_processed.velocity
                        normalized_velocity = (original_velocity - 1) / 126.0 if original_velocity > 0 else 0 
                        scaled_velocity = normalized_velocity * (max_vel_out - min_vel_out) + min_vel_out
                        msg_being_processed.velocity = max(0, min(127, round(scaled_velocity)))
                        note_action_this_rule = True
                except ValueError: pass
        if not note_action_this_rule and not rule_had_intention_to_act: # Si no hubo acción de Nota y no hay otras intenciones (ej ch_out)
            return [msg_being_processed], False


    # --- Aplicar ch_out (al msg_being_processed que ya pudo haber sido modificado arriba) ---
    out_msgs=[]
    made_multi_out_or_channel_changed=False 
    
    if "ch_out" in rule_config: # "ch_out" es una acción en sí misma
        ch_outs_list = rule_config["ch_out"]
        if not isinstance(ch_outs_list, list): ch_outs_list = [ch_outs_list]

        if not ch_outs_list: # Si ch_out es [], significa filtrar (consumir)
            return [], True # Actuó (filtrando), no hay mensajes de salida
        
        if hasattr(msg_being_processed,'channel'):
            orig_ch=msg_being_processed.channel
            for i,out_ch_val in enumerate(ch_outs_list): 
                msg_copy = msg_being_processed.copy() 
                msg_copy.channel = out_ch_val
                out_msgs.append(msg_copy)
                if i==0 and out_ch_val!=orig_ch: made_multi_out_or_channel_changed=True
            if len(ch_outs_list)>1: made_multi_out_or_channel_changed=True
        else: # Mensaje no tiene canal, pero hay ch_out (se pasa la copia)
            out_msgs.append(msg_being_processed.copy())
        if not out_msgs: # No debería pasar si ch_outs_list no estaba vacía
             out_msgs.append(msg_being_processed.copy())
    else: 
        out_msgs.append(msg_being_processed.copy()) # Siempre devolver una copia

    # --- Determinar si esta regla actuó ---
    final_m_dict_no_time = out_msgs[0].dict() if out_msgs else {} # Manejar lista vacía
    if 'time' in final_m_dict_no_time: final_m_dict_no_time.pop('time',None)
    
    content_changed = (initial_m_dict_no_time != final_m_dict_no_time)
    
    # La regla "actuó" si pasó todos los filtros Y:
    #   el contenido del mensaje cambió O
    #   hubo un split/cambio de canal explícito por ch_out O
    #   la regla tenía una "intención de actuar" (ej. cc_out, nt_st, ch_out definido, note_to_cc)
    #   Y los filtros específicos de esa acción (como cc_in para una acción de CC) pasaron.
    acted = False
    if rule_applies_based_on_ch_in: 
        if rule_had_intention_to_act:
            # Si es una regla de CC, el cc_in debe haber coincidido si estaba presente Y la regla tenía cc_out o cc_range
            if msg_being_processed.type == 'control_change' and "cc_in" in rule_config:
                if original_msg_for_this_rule.control == rule_config["cc_in"] and \
                   ("cc_out" in rule_config or "cc_range" in rule_config):
                    acted = True
            # Si es note_to_cc, etc., y llegó aquí, significa que la acción interna ya devolvió True
            elif "note_to_cc" in rule_config or "note_to_pc" in rule_config or "aftertouch_to_cc" in rule_config:
                 pass 
            # Para otras transformaciones con intención
            elif msg_being_processed.type in ['note_on', 'note_off'] and ("nt_st" in rule_config or "velocity_range" in rule_config):
                 acted = True # Si hay claves de acción de nota y pasó filtros, actuó
            elif "ch_out" in rule_config: # ch_out por sí solo es una acción si pasó filtros
                 acted = True # made_multi_out_or_channel_changed ya lo cubre parcialmente
        
        # Si no se marcó 'acted' por intención específica, ver si el contenido cambió o hubo split/cambio de canal
        if not acted:
            acted = content_changed or made_multi_out_or_channel_changed
        
    return out_msgs, acted

def apply_all_transformations(msg_to_process, list_of_all_transforms_for_route, active_version, out_port_for_actions=None): # out_port_for_actions no se usa en V17
    current_messages = [msg_to_process.copy()]
    overall_acted_by_route = False
    if not list_of_all_transforms_for_route: return current_messages, False # Devolver solo 2 valores

    for rule_config in list_of_all_transforms_for_route: # Renombrado item_config a rule_config
        if "_comment" in rule_config and list(rule_config.keys()) == ["_comment"]: continue
        
        next_round_messages = []
        for m_current_in_chain in current_messages:
            processed_outputs, this_rule_did_act = process_message_with_rule( # this_item_did_act -> this_rule_did_act
                m_current_in_chain, rule_config, active_version 
            )
            
            if this_rule_did_act: 
                overall_acted_by_route = True
            
            if not processed_outputs and "note_to_cc" in rule_config: # Si note_to_cc consumió
                current_messages = [] 
                break 
            
            next_round_messages.extend(processed_outputs)
        
        current_messages = next_round_messages
        if not current_messages: break 
            
    return current_messages, overall_acted_by_route

def list_midi_ports_action():
    print("Puertos de ENTRADA MIDI disponibles:")
    input_names = mido.get_input_names()
    if not input_names:
        print("  (Ninguno detectado)")
    else:
        for i, name in enumerate(input_names):
            print(f"  {i}: '{name}'")
    
    print("\nPuertos de SALIDA MIDI disponibles:")
    output_names = mido.get_output_names()
    if not output_names:
        print("  (Ninguno detectado)")
    else:
        for i, name in enumerate(output_names):
            print(f"  {i}: '{name}'")
    print("-" * 40) # Separador
def interactive_rule_selector():
    RULES_DIR.mkdir(parents=True, exist_ok=True); rule_files = sorted([f for f in RULES_DIR.iterdir() if f.is_file() and f.name.endswith('.json')])
    if not rule_files: print(f"No .json en '{RULES_DIR}'."); return None 
    sel_idx={}; cur_sel_idx=0; next_ord=1; kb=KeyBindings()
    @kb.add('c-c', eager=True)
    @kb.add('c-q', eager=True)
    def _(event): event.app.exit(result=None)
    @kb.add('up', eager=True)
    def _(event): nonlocal cur_sel_idx; cur_sel_idx=(cur_sel_idx-1+len(rule_files))%len(rule_files)
    @kb.add('down', eager=True)
    def _(event): nonlocal cur_sel_idx; cur_sel_idx=(cur_sel_idx+1)%len(rule_files)
    @kb.add('space', eager=True)
    def _(event):
        nonlocal next_ord; sf=rule_files[cur_sel_idx]
        if sf in sel_idx: ro=sel_idx.pop(sf);_=[sel_idx.update({fpk:sel_idx[fpk]-1}) for fpk in list(sel_idx.keys()) if sel_idx[fpk]>ro];next_ord-=1;
        else: sel_idx[sf]=next_ord; next_ord+=1
    @kb.add('enter', eager=True)
    def _(event):
        nonlocal cur_sel_idx; rrn=[]
        if not sel_idx: 
            if rule_files: rrn.append(rule_files[cur_sel_idx].stem)
        else: os=sorted(sel_idx.items(),key=lambda i:i[1]); rrn=[f.stem for f,o in os]
        event.app.exit(result=rrn)
    def get_text_for_ui():
        frags=["<b>Selecciona las reglas (Espacio: marcar, Enter: ok, ↑↓: nav):</b>\n"]
        for i,fp in enumerate(rule_files): mk=f"[{sel_idx[fp]}]" if fp in sel_idx else "[ ]";lc=f"{mk} {fp.name}";frags.append(f"<style bg='ansiblue' fg='ansiwhite'>> {lc}</style>\n" if i==cur_sel_idx else f"  {lc}\n")
        frags.append("\nCtrl+C/Q para salir.")
        return HTML("".join(frags))
    ctrl=FormattedTextControl(text=get_text_for_ui,focusable=True,key_bindings=kb);app=Application(layout=Layout(HSplit([Window(content=ctrl)])),full_screen=False,mouse_support=False)
    print("MIDImod - Abriendo selector..."); names=app.run()
    if names is None:print("Cancelado.")
    return names


def main(): # Basado en TU última versión de main()
    global shutdown_flag, current_active_version, available_versions
    signal.signal(signal.SIGINT, signal_handler)

    # --- DEFINICIÓN DE help_desc y help_epilog (COMO EN TU VERSIÓN) ---
    help_desc = """midimod: Procesador MIDI con alias de dispositivos y versiones de reglas.
Permite definir alias para dispositivos MIDI y luego usarlos en múltiples rutas
de procesamiento. Cada ruta puede tener su propio mapa de control de versiones
y una secuencia de transformaciones.
"""
    help_epilog = f"""
ESTRUCTURA DE ARCHIVOS JSON (en ./{RULES_DIR.name}/):
Un archivo JSON puede contener (ambos opcionales pero 'routes' es necesario para procesar):
1. Una sección "devices":
   {{
     "devices": {{
       "MiControlador": "USB X-Session", 
       "SinteA": "USB Uno MIDI Interface" 
     }},
     "routes": [ ... ] 
   }}
   La sección "devices" del PRIMER archivo de reglas que la contenga será usada globalmente.

2. Una lista de "routes":
   Cada ruta: {{ 
     "_comment": "Descripción de la ruta",
     "input_device_alias": "MiControlador", // Usa alias de "devices" o substring directa
     "output_device_alias": "SinteA",   // Usa alias de "devices" o substring directa
     "version_midi_map": {{ "note_on note=20": 1, "note_on note=108": "cycle" }}, // Opcional
     "transformations": [ {{...}} ] // Requerido para que la ruta procese
   }}

TRANSFORMACIONES (dentro de "transformations" de una ruta):
{{
  "_comment":"Desc", "version":0, "ch_in":[0], "cc_in":10, "cc_out":74, ...
}}
- Sin "version": Aplica siempre en su ruta.
- Con "version":N : Solo si current_active_version == N.

CAMBIO DE VERSIÓN (GLOBAL):
- Teclado: [0-9] selecciona; [Espacio] cicla.
- MIDI: Definido en "version_midi_map" de una ruta.

Uso:
  python midimod.py [regla1 ...] | --list-ports | --help
"""
    parser=argparse.ArgumentParser(prog="midimod",description=help_desc,epilog=help_epilog,formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("rule_files",nargs='*',default=None,help=f"Archivos de reglas de './{RULES_DIR.name}/' (sin .json).")
    parser.add_argument("--list-ports",action="store_true",help="Lista puertos MIDI y sale.")
    args=parser.parse_args();

    if args.list_ports:list_midi_ports_action();return

    rule_names_to_load=args.rule_files
    all_route_configurations=[] 
    files_loaded_summary_info_accumulator=[] # Para acumular info de todos los archivos
    device_aliases = {} 

    if not rule_names_to_load:
        selected_names=interactive_rule_selector();
        if selected_names is None:return
        rule_names_to_load=selected_names
        if not rule_names_to_load:print("No reglas. Saliendo.");return
    
    # --- Carga de Alias de Dispositivos y Rutas ---
    if rule_names_to_load:
        found_device_aliases_section = False
        for name in rule_names_to_load:
            fp = RULES_DIR / f"{name}.json"
            file_summary = {"filename": f"{name}.json", "num_routes": 0, "status": "error", "error_msg": "No procesado"}

            if not fp.exists():
                file_summary["error_msg"] = "Archivo no encontrado."
                files_loaded_summary_info_accumulator.append(file_summary)
                continue

            # Usar _load_json_file_content (que debes definir globalmente)
            file_content = _load_json_file_content(fp) 

            if not file_content or not isinstance(file_content, dict):
                # Podría ser una lista de rutas (formato antiguo) o un JSON inválido
                if isinstance(file_content, list): # Formato antiguo: lista de rutas
                    routes_from_list = []
                    for i, item_in_list in enumerate(file_content):
                        if isinstance(item_in_list, dict) and "transformations" in item_in_list:
                            item_in_list["_source_file"] = fp.name
                            routes_from_list.append(item_in_list)
                    if routes_from_list:
                        all_route_configurations.extend(routes_from_list)
                        file_summary["num_routes"] = len(routes_from_list)
                        file_summary["status"] = "ok"
                        file_summary["error_msg"] = ""
                    else:
                        file_summary["error_msg"] = "Lista de rutas vacía o con formato incorrecto."
                else: # Error de carga o no es un dict
                    file_summary["error_msg"] = file_info_entry.get("error_msg", "Error al leer o parsear el archivo.") # file_info_entry no existe aquí, usar un msg genérico
                    # file_summary["error_msg"] = "Error al leer o parsear el archivo, o no es un objeto JSON."
                files_loaded_summary_info_accumulator.append(file_summary)
                continue # Pasar al siguiente archivo

            # Procesar la sección "devices" si existe y no se ha cargado ya
            if not found_device_aliases_section and "devices" in file_content and isinstance(file_content["devices"], dict):
                device_aliases = file_content["devices"]
                print(f"Dispositivos alias cargados desde: {fp.name}")
                found_device_aliases_section = True
            
            # Procesar la sección "routes"
            if "routes" in file_content and isinstance(file_content["routes"], list):
                routes_in_file_section = file_content["routes"]
                valid_routes_from_this_section = []
                for i, item in enumerate(routes_in_file_section):
                    if isinstance(item, dict) and "transformations" in item:
                        item["_source_file"] = fp.name 
                        valid_routes_from_this_section.append(item)
                
                file_summary["num_routes"] = len(valid_routes_from_this_section)
                if len(valid_routes_from_this_section) > 0:
                    file_summary["status"] = "ok"
                    all_route_configurations.extend(valid_routes_from_this_section)
                    file_summary["error_msg"] = ""
                else:
                    file_summary["error_msg"] = "Sección 'routes' vacía o sin rutas válidas."
            elif "routes" not in file_content: # El archivo es un dict pero no tiene "routes"
                file_summary["error_msg"] = "Archivo no contiene una sección 'routes' como lista."
            
            files_loaded_summary_info_accumulator.append(file_summary)
    
    if not all_route_configurations:print("No configs de ruta válidas. Saliendo.");return
    
    if device_aliases:
        print("Aliases de dispositivos definidos:")
        for alias, substring in device_aliases.items(): print(f"  '{alias}' -> '{substring}'")
    else:
        print("No se definieron alias de dispositivos globales. Se usarán directamente las subcadenas/alias de las rutas.")

    collect_available_versions(all_route_configurations)
    
    input_handlers={}
    opened_output_ports={}
    route_setup_log_lines=[] 
    
    print("\n--- Estado Rutas ---") 
    for fi in files_loaded_summary_info_accumulator: # Usar el acumulador
        status_detail = f" ({fi['num_routes']})" if fi['status']=='ok' else f" (ERR: {fi.get('error_msg','Error')})"
        print(f"Cargando: {fi['filename']}{status_detail}:")

    all_mido_in_ports = mido.get_input_names()
    all_mido_out_ports = mido.get_output_names()
    
    for i,route_conf in enumerate(all_route_configurations):
        i_id=f"R{i+1}";route_conf['_id_str']=i_id 
        input_alias_or_substring = route_conf.get("input_device_alias") 
        output_alias_or_substring = route_conf.get("output_device_alias")
        in_s = device_aliases.get(input_alias_or_substring, input_alias_or_substring) 
        out_s = device_aliases.get(output_alias_or_substring, output_alias_or_substring)
        pfx=f"{i_id}: "
        
        act_in_n=find_port_by_substring(all_mido_in_ports,in_s)
        if not act_in_n:
            route_setup_log_lines.append(f"  {pfx}ERR: ENTRADA '{input_alias_or_substring or 'POR DEFECTO'}({in_s or 'DEF'})' No detectada.")
            continue
        in_o=input_handlers.get(act_in_n,{}).get('port_obj')
        if not in_o:
            try:in_o=mido.open_input(act_in_n)
            except(IOError,OSError) as e: route_setup_log_lines.append(f"  {pfx}ERR: Abriendo entrada '{act_in_n}'. ({e})");continue
        
        out_o=None; act_out_n_item="N/A (Ruta sin salida configurada)"
        if "transformations" in route_conf: 
            act_out_n=find_port_by_substring(all_mido_out_ports,out_s) 
            if not act_out_n:
                route_setup_log_lines.append(f"  {pfx}ERR: SALIDA '{output_alias_or_substring or 'POR DEFECTO'}({out_s or 'DEF'})' No detectada.")
                if act_in_n not in input_handlers and hasattr(in_o,'close')and not in_o.closed:in_o.close()
                continue
            out_o=opened_output_ports.get(act_out_n)
            if not out_o:
                try:out_o=mido.open_output(act_out_n);opened_output_ports[act_out_n]=out_o
                except(IOError,OSError) as e:
                    route_setup_log_lines.append(f"  {pfx}ERR: Abriendo salida '{act_out_n}'. ({e})")
                    if act_in_n not in input_handlers and hasattr(in_o,'close')and not in_o.closed:in_o.close()
                    continue
            route_conf['_actual_out_port_obj']=out_o; act_out_n_item=out_o.name
            route_setup_log_lines.append(f"  {pfx}'{in_o.name}' >> '{out_o.name}'")
        
        if act_in_n not in input_handlers:input_handlers[act_in_n]={'port_obj':in_o,'routes':[]}
        input_handlers[act_in_n]['routes'].append(route_conf)
        route_conf['_actual_out_port_obj_name']=act_out_n_item

    for msl in route_setup_log_lines:print(msl)

    valid_handlers={n:d for n,d in input_handlers.items() if d.get('routes',[])}
    if not valid_handlers:
        print("No rutas activas. Saliendo.");_=[(d.get('port_obj').close() if d.get('port_obj')and hasattr(d['port_obj'],'close')and not d['port_obj'].closed else None)for d in input_handlers.values()];_=[(p.close() if hasattr(p,'close')and not p.closed else None)for p in opened_output_ports.values()];return
    
    summarize_active_processing_units(valid_handlers, device_aliases) 
        
    num_ar=sum(len(h.get('routes',[]))for h in valid_handlers.values());
    if num_ar > 0: 
        if len(available_versions) > 1:
            print(f"\n{num_ar} ruta(s) activas. Versión actual: {current_active_version}.")
            print("Teclado: [0-9] selecciona versión, [Esp] cicla entre versiones.")
        else: 
            print(f"\n{num_ar} ruta(s) activas.") 
    print("Ctrl+C para salir. Monitor MIDI:")

    last_vcd_time=0;v_ch_cycle=False 
    try:
        while not shutdown_flag:
            v_ch_cycle=False;char=get_char_non_blocking()
            if char:
                v_ch_cycle=True
                if char.isdigit():
                    nv=int(char)
                    if nv in available_versions:
                        if current_active_version!=nv:current_active_version=nv;print(f"Versión activa: {nv}    ",end="\r");last_vcd_time=time.time()
                    else:print(f"(V{nv} no def:{available_versions})",end='\r');last_vcd_time=time.time()
                elif char==' ':
                    if available_versions:
                        try:ci=available_versions.index(current_active_version)
                        except ValueError:ci=-1
                        current_active_version=available_versions[(ci+1)%len(available_versions)];print(f"Versión activa: {current_active_version}    ",end="\r");last_vcd_time=time.time()
            if last_vcd_time and(time.time()-last_vcd_time>2):print(" "*70,end="\r");last_vcd_time=0
            proc_midi_cycle=False 
            for inp_n,h_data in valid_handlers.items():
                in_obj=h_data['port_obj'];msg_orig=in_obj.poll() 
                if msg_orig is not None:
                    proc_midi_cycle=True;msg_vchk=msg_orig.copy();v_ch_midi=False
                    for route_conf_for_map in h_data.get('routes', []): 
                        mmap=route_conf_for_map.get("version_midi_map",{});
                        if not mmap:continue
                        lk=""; msg_type_original = msg_vchk.type; note = getattr(msg_vchk, 'note', None)
                        control = getattr(msg_vchk, 'control', None); value = getattr(msg_vchk, 'value', None)
                        velocity = getattr(msg_vchk, 'velocity', None); msg_channel = getattr(msg_vchk, 'channel', None)
                        effective_msg_type_for_map_lookup = msg_type_original
                        if msg_type_original == 'note_on' and velocity == 0: effective_msg_type_for_map_lookup = 'note_off'
                        possible_lookup_keys = []; base_key_part = ""
                        if effective_msg_type_for_map_lookup in ['note_on','note_off'] and note is not None: base_key_part = f"{effective_msg_type_for_map_lookup} note={note}"
                        elif effective_msg_type_for_map_lookup =='control_change' and control is not None and value is not None: base_key_part = f"{effective_msg_type_for_map_lookup} control={control} value={value}"  
                        if base_key_part:
                            if msg_channel is not None: possible_lookup_keys.append(f"{base_key_part} channel={msg_channel}")
                            possible_lookup_keys.append(base_key_part)
                        target_action_or_version = None; matched_key_for_log = None
                        for lk_map_key in possible_lookup_keys: 
                            if lk_map_key in mmap: target_action_or_version = mmap[lk_map_key]; matched_key_for_log = lk_map_key; break
                        if target_action_or_version is not None:
                            prev_active_ver = current_active_version; action_performed_for_log = ""
                            if isinstance(target_action_or_version,int):
                                if target_action_or_version in available_versions: current_active_version=target_action_or_version
                            elif isinstance(target_action_or_version,str) and msg_type_original == 'note_on' and (velocity is None or velocity > 0):
                                action_str = target_action_or_version.lower()
                                if action_str in ["cycle","cycle_next"]:
                                    if available_versions:
                                        try:ci=available_versions.index(current_active_version)
                                        except ValueError:ci=-1
                                        current_active_version=available_versions[(ci+1)%len(available_versions)]; action_performed_for_log = f"CycleNext V{current_active_version}"
                                elif action_str == "cycle_previous":
                                    if available_versions:
                                        try:ci=available_versions.index(current_active_version)
                                        except ValueError:ci=len(available_versions)
                                        current_active_version=available_versions[(ci-1+len(available_versions))%len(available_versions)]; action_performed_for_log = f"CyclePrev V{current_active_version}"
                            if current_active_version != prev_active_ver or (action_performed_for_log and "Cycle" in action_performed_for_log):
                                log_print_action = action_performed_for_log if action_performed_for_log else f"Set V{current_active_version}"
                                print(f"Versión activa: {current_active_version} (MIDI:{matched_key_for_log} -> {log_print_action}) ",end="\r");last_vcd_time=time.time();v_ch_cycle=True;v_ch_midi=True;break
                        if v_ch_midi:break 
                    if v_ch_midi:continue
                    if msg_orig.type=='clock':continue
                    fmt_in=format_midi_message_for_log(msg_orig,prefix="IN:",active_version=current_active_version) 
                    if not fmt_in:continue
                    out_log_buf=[]; any_out_this_event_was_logged = False
                    for route_conf in h_data.get('routes', []): 
                        if "transformations" not in route_conf : continue 
                        i_id=route_conf['_id_str'];out_p_item=route_conf.get('_actual_out_port_obj')
                        final_outs,item_acted = apply_all_transformations(msg_orig.copy(), route_conf.get("transformations",[]), current_active_version)
                        if out_p_item: 
                            for p_msg in final_outs:
                                try: out_p_item.send(p_msg)
                                except (IOError, OSError) as send_error: print(f"ERR|{i_id}: Error enviando a '{out_p_item.name if out_p_item else 'N/A'}': {send_error}"); route_conf['_actual_out_port_obj'] = None; break 
                                except Exception as e_unhandled_send: print(f"ERR|{i_id}: Error INESPERADO enviando a '{out_p_item.name if out_p_item else 'N/A'}': {e_unhandled_send}"); route_conf['_actual_out_port_obj'] = None; break
                        if item_acted or(msg_orig.type in['start','stop','continue']):
                            for p_out in final_outs:
                                out_pfx=f"{i_id}|OUT:"
                                fmt_out=format_midi_message_for_log(p_out,prefix=out_pfx,active_version=current_active_version)
                                if fmt_out:out_log_buf.append(fmt_out)
                    if out_log_buf:
                        print(fmt_in,end="")
                        for j,o_line in enumerate(out_log_buf):
                            if j==0: print(f"  >>  {o_line}")
                            else: print(f"{' '*(len(f'[{current_active_version}] IN: ')) } >>  {o_line}") 
                        any_out_this_event_was_logged = True 
                    elif fmt_in: print(fmt_in+" >>")
            if not proc_midi_cycle and not v_ch_cycle:time.sleep(0.001)
            elif v_ch_cycle and not last_vcd_time:pass
    except KeyboardInterrupt:
        if not shutdown_flag:shutdown_flag=True
    except Exception as e:
        if not shutdown_flag:print(f"\nERROR INESPERADO:{e}");traceback.print_exc()
    finally:
        print("\nCerrando puertos...");
        for data_h in input_handlers.values(): 
            port_obj_in = data_h.get('port_obj')
            if port_obj_in and hasattr(port_obj_in,'close') and not port_obj_in.closed: port_obj_in.close()
        for port_obj_out in opened_output_ports.values():
            if port_obj_out and hasattr(port_obj_out,'close') and not port_obj_out.closed: port_obj_out.close()
        if'termios'in sys.modules and'tty'in sys.modules and sys.stdin.isatty()and _original_termios_settings:
            try:termios.tcsetattr(sys.stdin.fileno(),termios.TCSADRAIN,_original_termios_settings)
            except:pass
        print("midimod detenido.")

# ... (Resto de funciones auxiliares: interactive_rule_selector, 
#      summarize_active_processing_units (MODIFICADA ABAJO), 
#      format_rule_details_for_summary (MODIFICADA ABAJO), 
#      process_message_with_rule, apply_all_transformations, etc.) ...

if __name__=="__main__":
    RULES_DIR.mkdir(parents=True,exist_ok=True)
    if'termios'in sys.modules and'tty'in sys.modules and sys.stdin.isatty():
        try:_original_termios_settings_fd=sys.stdin.fileno();_original_termios_settings=termios.tcgetattr(_original_termios_settings_fd)
        except:_original_termios_settings=None
    main()