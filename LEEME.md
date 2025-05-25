# MIDImod: Tu Transformador MIDI Inteligente

MIDImod es un script de Python diseñado para darte el control total sobre tus mensajes MIDI en tiempo real. Imagina poder conectar tus dispositivos MIDI de formas nuevas y creativas, transformando las señales para que se adapten perfectamente a tus necesidades. MIDImod lo hace posible a través de archivos de configuración JSON muy sencillos de entender.

## ¿Para Qué Sirve MIDImod?

MIDImod es como una navaja suiza para tus conexiones MIDI. Puedes:

- **Conectar Dispositivos Fácilmente:** ¿Tienes un teclado y un sintetizador? Conéctalos. ¿Un controlador de pads y un módulo de batería? También.

- **Remapear Canales:** Envía la señal de un canal MIDI a otro diferente.

- **Transformar Notas:**
  
  - **Transponer:** Sube o baja octavas, o crea armonías.
  
  - **Duplicar:** Envía la misma melodía a dos sintes o a dos canales de un sinte multitímbrico, quizás con una línea de bajo una octava más abajo en uno de ellos.
  
  - **Escalar a Tonalidades:** Asegúrate de que todas tus notas suenen bien juntas ajustándolas a una escala musical (mayor, menor, pentatónica, etc.).
  
  - **Notas Aleatorias:** ¡Introduce un poco de caos creativo!

- **Manipular Controladores (CCs):**
  
  - **Cambiar Número de CC:** Haz que el knob de volumen (CC7) controle el corte del filtro (CC74).
  
  - **Escalar Valores:** Ajusta el rango de un knob para que tenga un control más fino o más amplio sobre un parámetro.
  
  - **Tipos de CC Avanzados:** Usa potenciómetros que envían valores absolutos como si fueran relativos (ideales para encoders infinitos) o implementa "catch-up" para evitar saltos bruscos de parámetros.

- **Convertir Eventos:**
  
  - Transforma una nota en un Control Change (CC) o un Program Change (PC). Perfecto si tu teclado no tiene knobs o botones de cambio de programa.
  
  - Usa la velocidad de una nota o el aftertouch para controlar un parámetro de tu sinte.

- **Versiones (Presets Dinámicos):**
  
  - Define diferentes "escenarios" o "versiones" de tus reglas.
  
  - Cambia entre estas versiones al instante usando un mensaje MIDI (una nota, un CC) desde uno de tus controladores. Imagina un botón "Shift" que cambia completamente lo que hacen tus otros knobs y botones.

- **Variables de Usuario:** Guarda valores (como la última velocidad de un pad) y úsalos en otras reglas para crear interacciones complejas.

- **Control de Transporte y SysEx:** Envía mensajes de Play/Stop o configuraciones específicas (SysEx) a tus equipos.

**La Clave es la Simplicidad:** Aunque MIDImod es potente, su configuración se basa en archivos JSON diseñados para ser legibles y fáciles de modificar. No necesitas ser un programador experto para empezar a transformar tu flujo de trabajo MIDI.

## Características Principales

- **Alias de Dispositivos:** Nombres amigables para tus aparatos MIDI.

- **Reglas Claras:** Define "filtros" que reaccionan a mensajes específicos.

- **Múltiples Salidas:** Un mensaje de entrada puede generar varias salidas.

- **Versiones Globales:** Cambia todo el comportamiento de tus filtros con un solo mensaje MIDI.

- **Configuración en JSON:** Todo se define en archivos de texto sencillos.

- **Monitor en Tiempo Real:** Ve exactamente qué está pasando con tus mensajes MIDI.

- **Selector Interactivo de Reglas:** Carga tus configuraciones fácilmente.

- **Puertos Virtuales:** Ideal para conectar software MIDI dentro de tu ordenador.

## Requisitos

- Python 3.7 o superior.

- Librerías de Python: mido, python-rtmidi, prompt_toolkit.

### Instalación de Dependencias

Abre tu terminal o línea de comandos y ejecuta:  
pip install mido python-rtmidi prompt-toolkit

(Nota para Linux: podrías necesitar libasound2-dev o similar para python-rtmidi).

## Uso

Ejecuta MIDImod desde la línea de comandos:

**Sintaxis:**  
python midimod.py [archivo_reglas_1] [archivo_reglas_2] [...] [opciones]

- **[archivo_reglas_...]**: (Opcional) Nombres de tus archivos de configuración (sin .json) que están en la carpeta rules_new/. Si no pones ninguno, se abrirá un selector.

- **Opciones:**
  
  - --list-ports: Muestra tus dispositivos MIDI y sale.
  
  - --virtual-ports: Activa el modo de puertos virtuales (entrada: MIDImod_IN, salida: MIDImod_OUT por defecto).
  
  - --vp-in NOMBRE, --vp-out NOMBRE: Personaliza los nombres de los puertos virtuales.
  
  - --no-log: Desactiva el monitor MIDI al inicio.
  
  - --help: Muestra ayuda detallada.

**Ejemplos de Ejecución:**

- **Selector interactivo:**  
  python midimod.py

- **Cargar un archivo específico:**  
  python midimod.py mi_configuracion_directo

- **Listar puertos MIDI:**  
  python midimod.py --list-ports

## Estructura de los Archivos de Reglas (.json)

Los archivos de reglas deben estar en formato JSON y guardados en una carpeta llamada rules_new/ (al lado de midimod.py).

**Componentes Principales de un Archivo de Reglas:**

1. **"device_alias" (Objeto, Opcional pero Recomendado):**
   
   - Define nombres cortos y fáciles de recordar para tus dispositivos MIDI.
   
   - Ejemplo: "Keyb": "SL MkII", "Synth": "MiSintetizadorHardware"
   
   - MIDImod usará los alias definidos en el primer archivo cargado que contenga esta sección.

2. **"version_map" (Lista, Opcional):**
   
   - Define cómo cambiar la current_active_version global usando mensajes MIDI.
   
   - Cada elemento de la lista es una regla con:
     
     - "device_in": Alias del dispositivo de entrada que dispara el cambio.
     
     - "ch_in" (Opcional): Canal MIDI de entrada (0-15).
     
     - "event_in": Tipo de evento MIDI (ej. "note_on", "cc").
     
     - "value_1_in" (Opcional): Nota o número de CC.
     
     - "value_2_in" (Opcional): Velocidad o valor de CC.
     
     - "version_out": A qué versión cambiar (ej. 0, 1) o una acción ("cycle_next", "cycle_previous").

3. **"input_filter" (Lista, Requerido para procesar MIDI):**
   
   - Contiene la lista de tus reglas de procesamiento principales.
   
   - Cada "filtro" es un objeto que define qué hacer cuando llega un mensaje MIDI.

**Componentes Clave de un Filtro en "input_filter":**

- "_comment" (String, Opcional): Una descripción para ti.

- "version" (Entero o Lista, Opcional): El filtro solo se activa si la current_active_version coincide. Si no está, el filtro siempre está activo.

- "device_in" (String, Requerido si el filtro reacciona a MIDI): Alias del dispositivo de entrada.

- "ch_in" (Entero o Lista, Opcional): Canal(es) de entrada (0-15).

- "event_in" (String o Lista, Opcional): Tipo(s) de evento de entrada (ej. "note", "cc", "note_on").

- "value_1_in" (Entero o Lista, Opcional): Nota(s) o número(s) de CC específicos.

- "value_2_in" (Entero o Lista, Opcional): Velocidad(es) o valor(es) de CC específicos.

- "cc_type_in" (String, Opcional, para event_in: "cc"): Cómo interpretar el CC de entrada.
  
  - "abs" (defecto): Valor absoluto.
  
  - "relative_signed": Relativo con +/- desde 64.
  
  - "relative_2c": Relativo con complemento a dos.
  
  - "abs_relative": Acelerado. Usa "threshold" (defecto 0) y "abs2rel_factor" (defecto 2.0).
  
  - "abs_catchup": Solo envía cuando el valor físico "alcanza" el último enviado. Usa "threshold" (defecto 5).

- "output" (Lista de Objetos, Requerido para enviar MIDI o cambiar variables): Qué hacer cuando el filtro coincide. Cada objeto en la lista es una acción de salida.

**Componentes Clave de un Objeto de Salida en "output":**

- "device_out" (String, Opcional): Alias del dispositivo de salida. Si no está, la acción podría ser solo cambiar una variable.

- "channel_out" (Entero o Expresión, Opcional): Canal de salida. Hereda del canal de entrada si no se especifica.

- "event_out" (String o Expresión, Opcional): Tipo de evento de salida. Hereda del tipo de evento de entrada. Puede ser "note", "cc", "pc", "pitchwheel", "aftertouch", "polytouch", "sysex", "start", "stop", etc.

- "value_1_out" (Entero, String o Expresión, Opcional): Para notas, CCs, PCs. Ej: 60, "value_1_in + 12", "random(40, 80)". Hereda de value_1_in.

- "value_2_out" (Entero, String o Expresión, Opcional): Para velocidad de nota, valor de CC. Ej: 100, "value_2_in / 2", "var_0". Hereda de value_2_in.

- "cc_type_out" (String, Opcional, para event_out: "cc"): Cómo codificar el valor de CC de salida ("abs", "relative_signed", "relative_2c").

- "sysex_data" (Lista de enteros, para event_out: "sysex"): Los bytes de datos SysEx (el script añade F0 y F7 automáticamente).

- Asignación de Variables: "var_0": 10, "var_1": "value_1_in + var_0". Hay 16 variables (var_0 a var_15).

- Transformaciones de Valor Avanzadas (para value_1_out, value_2_out, etc.):
  
  - Escalado de Rango: { "scale_value": "variable_o_valor", "range_in": [min, max], "range_out": [min, max] }
  
  - Escalado de Notas a Tonalidad: { "scale_notes": {"scale_value": "nota_a_escalar", "scale_root": nota_raiz, "scale_type": "nombre_escala"} } (escalas: "major", "minor_natural", "pentatonic_major", etc.).

**Variables Disponibles en Expresiones de Salida:**  
channel_in, value_1_in, value_2_in (valor de CC ya procesado por cc_type_in), delta_in (cambio físico del CC), event_in, cc_type_in, cc_val2_saved (último valor enviado a ese CC/canal de salida), y var_0 a var_15.

## Ejemplos Sencillos de Archivos de Reglas

Estos ejemplos usan alias simples. Recuerda adaptarlos a tus dispositivos.  
**Alias Comunes para Ejemplos Sencillos:**

```
{
    "device_alias": {
        "MiTeclado": "SL MkII",      // Cambia "SL MkII" por parte del nombre de tu teclado
        "MiControlador": "BeatStep", // Cambia "BeatStep" por parte del nombre de tu controlador
        "MiSinte": "Uno MIDI"        // Cambia "Uno MIDI" por parte del nombre de tu sinte
    }
}
```



(Guarda esto como, por ejemplo, mis_dispositivos.json y cárgalo primero, o incluye la sección "device_alias" en cada archivo de ejemplo).

---

**1. conectar_teclado_a_sinte.json** (Conexión Directa)  
Propósito: Todo lo que tocas en MiTeclado va directamente a MiSinte en el mismo canal.

```
{
    "device_alias": { "MiTeclado": "SL MkII", "MiSinte": "Uno MIDI" },
    "input_filter": [
        {
            "device_in": "MiTeclado",
            "output": [{ "device_out": "MiSinte" }]
        }
    ]
}
```



---

**2. cambiar_canal_teclado.json**  
Propósito: Lo que tocas en MiTeclado en el canal 1 MIDI (ch_in: 0) se envía a MiSinte en el canal 5 MIDI (channel_out: 4).

```
{
    "device_alias": { "MiTeclado": "SL MkII", "MiSinte": "Uno MIDI" },
    "input_filter": [
        {
            "device_in": "MiTeclado", "ch_in": 0,
            "output": [{ "device_out": "MiSinte", "channel_out": 4 }]
        }
    ]
}
```



---

**3. transponer_octava.json**  
Propósito: Las notas de MiTeclado (canal 1) se envían a MiSinte (canal 1) una octava más arriba.

```
{
    "device_alias": { "MiTeclado": "SL MkII", "MiSinte": "Uno MIDI" },
    "input_filter": [
        {
            "device_in": "MiTeclado", "ch_in": 0, "event_in": "note",
            "output": [{ "device_out": "MiSinte", "value_1_out": "value_1_in + 12" }]
        }
    ]
}
```



---

**4. knob_controla_otro_cc.json**  
Propósito: El CC #20 de MiControlador (canal 1) se convierte en CC #74 (típicamente filtro) en MiSinte (canal 1), usando el mismo valor.

```
{
    "device_alias": { "MiControlador": "BeatStep", "MiSinte": "Uno MIDI" },
    "input_filter": [
        {
            "device_in": "MiControlador", "ch_in": 0, "event_in": "cc", "value_1_in": 20,
            "output": [{ "device_out": "MiSinte", "value_1_out": 74 }]
        }
    ]
}
```



---

**5. nota_cambia_programa.json**  
Propósito: Tocar la nota Do central (nota 60) en MiTeclado (canal 1) envía un Program Change #5 a MiSinte (canal 1).

```
{
    "device_alias": { "MiTeclado": "SL MkII", "MiSinte": "Uno MIDI" },
    "input_filter": [
        {
            "device_in": "MiTeclado", "ch_in": 0, "event_in": "note_on", "value_1_in": 60,
            "output": [{ "device_out": "MiSinte", "event_out": "pc", "value_1_out": 5 }]
        }
    ]
}
```



---

## Ejemplos Avanzados

**6. capas_y_escalas_por_version.json**  
Propósito: Usar MiControlador para cambiar cómo MiTeclado interactúa con MiSinte, alternando entre una capa simple y notas escaladas.

```
{
    "device_alias": { "MiTeclado": "SL MkII", "MiControlador": "BeatStep", "MiSinte": "Uno MIDI" },
    "version_map": [
        { "device_in": "MiControlador", "ch_in": 0, "event_in": "note_on", "value_1_in": 36, "version_out": 0 },
        { "device_in": "MiControlador", "ch_in": 0, "event_in": "note_on", "value_1_in": 37, "version_out": 1 }
    ],
    "input_filter": [
        {
            "version": 0, "device_in": "MiTeclado", "ch_in": 0, "event_in": "note",
            "output": [
                { "device_out": "MiSinte", "channel_out": 0 },
                { "device_out": "MiSinte", "channel_out": 1, "value_1_out": "value_1_in - 12" }
            ]
        },
        {
            "version": 1, "device_in": "MiTeclado", "ch_in": 0, "event_in": "note",
            "output": [{
                "device_out": "MiSinte", "channel_out": 2,
                "value_1_out": { "scale_notes": {"scale_value": "value_1_in", "scale_root": 60, "scale_type": "major"}}
            }]
        }
    ]
}
```

- **Uso:**
  
  - Con la nota 36 de MiControlador (V0): MiTeclado envía notas a MiSinte en el canal 1 y una octava abajo en el canal 2.
  
  - Con la nota 37 de MiControlador (V1): MiTeclado envía notas a MiSinte en el canal 3, ajustadas a la escala de Do Mayor.

---

**7. control_cc_avanzado_y_variables.json**  
Propósito: Usar un knob con abs_relative y otro para almacenar un valor en var_0 que modifica la salida de un tercer knob.

```
{
    "device_alias": { "MiControlador": "BeatStep", "MiSinte": "Uno MIDI" },
    "version_map": [
        { "device_in": "MiControlador", "ch_in": 0, "event_in": "note_on", "value_1_in": 40, "version_out": "cycle_next" }
    ],
    "input_filter": [
        { /* Knob con aceleración */
            "device_in": "MiControlador", "ch_in": 0, "event_in": "cc", "value_1_in": 20,
            "cc_type_in": "abs_relative", "abs2rel_factor": 3.0, /* "threshold" por defecto es 0 */
            "output": [{ "device_out": "MiSinte", "channel_out": 0, "value_1_out": 74 }]
        },
        { /* Knob para guardar en var_0 */
            "device_in": "MiControlador", "ch_in": 0, "event_in": "cc", "value_1_in": 21,
            "output": [{ "var_0": "value_2_in" }]
        },
        { /* Knob que usa var_0 */
            "device_in": "MiControlador", "ch_in": 0, "event_in": "cc", "value_1_in": 22,
            "output": [{
                "device_out": "MiSinte", "channel_out": 1, "value_1_out": 70,
                "value_2_out": "value_2_in + var_0"
            }]
        }
    ]
}
```

- **Uso:**
  
  - El CC#20 funciona con aceleración.
  
  - El CC#21 guarda su valor en var_0.
  
  - El CC#22 envía su valor + el valor de var_0 al CC#70 del canal 2 de MiSinte.
  
  - La nota 40 de MiControlador cicla las versiones (aunque este ejemplo no las use explícitamente para diferenciar filtros).

---

**8. control_transporte_y_sysex.json**  
Propósito: Usar notas para enviar Start/Stop y un mensaje SysEx.

```
{
    "device_alias": { "MiPads": "BeatStep", "MiSinte": "Uno MIDI", "MiSecuenciador": "MIDImod_OUT"},
    "version_map": [
        {"device_in": "MiPads", "ch_in": 9, "event_in": "note_on", "value_1_in": 48, "version_out": 0}
    ],
    "input_filter": [
        { /* Start */
            "device_in": "MiPads", "ch_in": 9, "event_in": "note_on", "value_1_in": 36,
            "output": [{ "device_out": "MiSecuenciador", "event_out": "start" }]
        },
        { /* Stop */
            "device_in": "MiPads", "ch_in": 9, "event_in": "note_on", "value_1_in": 37,
            "output": [{ "device_out": "MiSecuenciador", "event_out": "stop" }]
        },
        { /* Enviar SysEx */
            "version": 0,
            "device_in": "MiPads", "ch_in": 9, "event_in": "note_on", "value_1_in": 40,
            "output": [{
                "device_out": "MiSinte", "event_out": "sysex",
                "sysex_data": [ 0, 32, 41, 2, 18, 116, 0 ] // Ejemplo: Roland GS Reset (sin F0/F7)
            }]
        },
        { /* Passthrough de clock */
            "device_in": "MiPads", "event_in": "clock",
            "output": [{"device_out": "MiSecuenciador"}]
        }
    ]
}
```



- **Uso:**
  
  - Pad 36 en MiPads (Canal 10) envía Start a MiSecuenciador.
  
  - Pad 37 en MiPads (Canal 10) envía Stop a MiSecuenciador.
  
  - En Versión 0, Pad 40 en MiPads (Canal 10) envía un SysEx a MiSinte.
  
  - El reloj MIDI de MiPads se reenvía a MiSecuenciador.

## Monitor en Consola

Cuando MIDImod está en ejecución, verás los mensajes MIDI procesados:  
[V] IN:[Dispositivo] Ch(C) TIPO(VALOR) >> [V] OUT:[Dispositivo] Ch(C') TIPO'(VALOR')  
[V] IN:[Dispositivo] Ch(C) TIPO(VALOR) >> [NOUT] (si el filtro coincidió pero no generó salida)  
[*] >> SET: var_X = Y (cuando una variable de usuario se modifica)

- [V]: Versión activa.

- Dispositivo: Alias del dispositivo.

- Ch(C): Canal MIDI (1-16).

- TIPO(VALOR): ej. NT_on(60) vel(100), CC(20) val(64).

## Resolución de Problemas

- **"Error opening port..."**: Otro programa está usando el puerto MIDI. Cierra otras aplicaciones MIDI.

- **Dispositivo no detectado**: Usa --list-ports para ver los nombres exactos y ajusta tus alias.

- **JSON Inválido**: MIDImod te avisará si hay errores de sintaxis en tu archivo JSON. Valida tu JSON online si tienes dudas.

- **Codificación**: Guarda tus archivos .json en UTF-8.

## Contribuciones

¡Las sugerencias y reportes de error son bienvenidos! Por favor, abre un "Issue" en GitHub.

## Licencia

MIT License. Ver archivo LICENSE.


