**Evolución de Funcionalidades de MIDImod (Perspectiva del Usuario):**

- **v0.1 (Base):**
  
  - Procesamiento básico de mensajes MIDI basado en reglas JSON.

- **v0.2:**
  
  - **CCs de Entrada Avanzados:** Tipos abs, relative_signed, relative_2c, y abs_relative (acelerado) para Control Changes.
  
  - **Control de Versiones:** Múltiples configuraciones (versiones) en un archivo, conmutables por MIDI (version_map) o teclado.
  
  - **Expresiones en Salida:** Uso de variables como value_in_1, value_in_2, val_cc_saved para calcular valores de salida.
  
  - **Selector de Reglas:** Interfaz para elegir archivos de reglas al inicio.

- **v0.3:**
  
  - Principalmente correcciones internas y preparación para cambios de nombres. Sin nuevas funcionalidades destacadas para el usuario final sobre v0.2.

- **v0.4 (Consolidación de Nombres):**
  
  - **Nombres de Variables en Expresiones:** Cambian a val1_in, val2_in, channel_in, val_cc_saved, delta_in, event_type_in, cc_type_in. (Mejora la documentación y entendimiento).
  
  - **Parámetros JSON para abs_relative:** Introducción de fine_adjust_threshold.
  
  - **Escalado de Valores (scale_from_variable):** Posibilidad de remapear rangos de valores en los outputs.

- **v0.5 (Filtros por Versión y abs_catchup):**
  
  - **Filtros Activados por Cambio de Versión:** Reglas que se ejecutan automáticamente al cambiar a una versión específica, sin necesidad de un mensaje MIDI de entrada (filtros sin device_in).
  
  - **Nuevo Tipo de CC de Entrada: abs_catchup:** El CC de entrada solo "engancha" y actualiza su valor si el movimiento del knob está cerca del último valor enviado.
  
  - **Variables de Usuario Globales (Internas):** Introducción de user_named_vars (aún no expuestas directamente en JSON con este nombre).

- **v0.6 (Nomenclatura JSON Unificada y Output Implícito):**
  
  - **Nombres de Claves JSON Unificados:**
    
    - Entrada: ch_in, event_in, value_1_in, value_2_in, cc_type_in, threshold.
    
    - Salida: event_out, value_1_out, value_2_out, cc_type_out, sysex_data.
    
    - Secciones: device_alias, input_filter.
    
    - Escalado: scale_value, range_in, range_out.
  
  - **Variables de Usuario en JSON y Expresiones:** user_var_X cambia a var_X.
  
  - **Variables de Expresión Actualizadas:** event_type_in -> event_in; val_cc_saved -> cc_val2_saved.
  
  - **Output Implícito:** Si un filtro no tiene lista output:[], los parámetros de output definidos directamente en el filtro crean un único output.
  
  - **Herencia de device_out:** Un output en una lista output:[] puede heredar el device_out del filtro padre.

- **v0.7 (Sintaxis version_map Mejorada):**
  
  - **Claves de version_map:** Usan la nomenclatura event_in=... value_1_in=... para mayor consistencia.

- **v0.8 (Escalas Musicales):**
  
  - **Cuantización de Notas (scale_notes):** Nueva funcionalidad en outputs para ajustar notas a una escala musical (ej. "nota inferior más cercana").
  
  - **Sección scales en JSON:** Permite a los usuarios definir sus propias escalas musicales o sobrescribir las predefinidas.
  
  - Escalas predefinidas (major, minor, pentatonic, etc.).

- **v0.9 (Modo Puerto Virtual):**
  
  - **Operación como Puerto MIDI Virtual:** MIDImod puede escuchar en un puerto virtual de entrada (ej. "MIDImod_IN") y enviar a un puerto virtual de salida (ej. "MIDImod_OUT"), creados por software externo.
  
  - **Argumentos CLI:** --virtual-ports, --vp-in, --vp-out para activar y configurar este modo.
  
  - En modo virtual, las definiciones device_in y device_out de los JSON son ignoradas.
