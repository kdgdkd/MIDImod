# MIDImod: Transformaciones MIDI

`midimod.py` es un script de Python para interceptar, transformar y redirigir mensajes MIDI en tiempo real entre diferentes dispositivos. Permite una personalización profunda a través de archivos de configuración JSON, ofreciendo funcionalidades como conexión de dispositivos, remapeo de canales, transposición de notas, transformación de Control Changes (CCs), conversión de notas a CC/PC, y un sistema de "versiones" (presets) de reglas que se pueden cambiar dinámicamente durante la ejecución.

## Características Principales

- **Definición de Dispositivos por Alias:** Define nombres amigables (alias) para tus dispositivos MIDI en una sección global, y luego usa estos alias en tus rutas para mayor claridad y facilidad de mantenimiento.
- **Ruteo Múltiple:** Define múltiples "rutas" de procesamiento, cada una conectando un dispositivo de entrada MIDI (identificado por alias o subcadena) a un dispositivo de salida. Un mismo dispositivo de entrada puede alimentar múltiples rutas, y múltiples rutas pueden enviar a un mismo dispositivo de salida.
- **Procesamiento Secuencial:** Dentro de cada ruta, las transformaciones se aplican en el orden en que se definen en el archivo JSON. La salida de una transformación es la entrada de la siguiente.
- **Transformaciones Detalladas:**
  - Cambio de Canal (`ch_in`, `ch_out`).
  - Transposición de Notas (`nt_st`).
  - Remapeo de Control Changes (`cc_in`, `cc_out`).
  - Escalado de Rango de CC (`cc_range`).
  - Escalado de Velocidad de Nota (`velocity_range`).
  - Conversión de Nota a CC (`note_to_cc`), incluyendo opción de usar la velocidad de la nota como valor del CC.
  - Conversión de Nota a Program Change (`note_to_pc`).
  - Conversión de Aftertouch a CC (`aftertouch_to_cc`), con escalado de valor opcional.
- **Sistema de Versiones de Reglas (Presets):**
  - Define diferentes comportamientos para tus transformaciones usando la clave `"version"` (un entero o una lista de enteros).
  - Las reglas sin la clave `"version"` dentro de una ruta se aplican siempre (independientemente de la versión activa para esa ruta).
  - Cambia la `current_active_version` global dinámicamente mediante:
    - **Teclado:** Teclas numéricas (0-9) para selección directa, Barra Espaciadora para ciclar (la ventana de la consola debe tener el foco).
    - **MIDI:** Configura `version_midi_map` (específico de cada ruta) para que mensajes MIDI concretos seleccionen una versión o realicen acciones de ciclo (ej. `"cycle"`, `"cycle_previous"`).
- **Selector Interactivo de Archivos de Reglas:** Si se ejecuta sin especificar archivos de reglas, `midimod` presenta una interfaz en la consola para seleccionar y ordenar los archivos de reglas a cargar de la carpeta `rules/`.
- **Logueo en Tiempo Real:** Muestra los mensajes MIDI de entrada y sus correspondientes salidas (si una ruta y sus reglas actuaron sobre el mensaje) en la consola, indicando la versión activa y el identificador de la ruta.
- **Configuración Centralizada por JSON:** Toda la lógica de definición de dispositivos, ruteo y transformación se define en archivos JSON externos.

## Requisitos Previos

- Python 3.7 o superior.
- Bibliotecas de Python: `mido`, `python-rtmidi`, `prompt_toolkit`.

### Instalación de Dependencias

Puedes instalar todas las bibliotecas necesarias usando `pip`, el gestor de paquetes de Python. Abre tu terminal o línea de comandos y ejecuta:

```bash
pip install mido python-rtmidi prompt-toolkit
```

**Nota para usuarios de Linux:** A veces, para python-rtmidi, podrías necesitar instalar algunas dependencias de desarrollo de ALSA (ej. libasound2-dev en sistemas Debian/Ubuntu).

## Uso

midimod.py se ejecuta desde la línea de comandos.

**Sintaxis:**

```
python midimod.py [nombre_archivo_reglas_1] [nombre_archivo_reglas_2] [...] [opciones]
```

- **[nombre_archivo_reglas_...]**: (Opcional) Nombres de los archivos de reglas (sin la extensión .json) a cargar desde la subcarpeta rules/. Si se omiten, se abrirá un selector interactivo. Las rutas definidas en múltiples archivos se combinan.
  
- **Opciones:**
  
  - --list-ports: Muestra los dispositivos MIDI de entrada y salida detectados y sale.
    
  - --help: Muestra información de ayuda detallada sobre el uso y la estructura de los archivos de reglas.
    

**Ejemplos de Ejecución:**

- **Usar el selector interactivo:**
  
  ```
  python midimod.py
  ```
  
  (Navega con flechas, marca/desmarca con Espacio, confirma con Enter).
  
- **Cargar un archivo de reglas específico:**
  
  ```
  python midimod.py virus play
  ```
  
  (Cargará rules/virus.json y rules/play.json).
  
- **Listar puertos MIDI:**
  
  ```
  python midimod.py --list-ports
  ```
  

## Estructura de los Archivos de Reglas (.json)

Los archivos de reglas deben estar en formato JSON y ubicarse en una carpeta llamada rules/ en el mismo directorio que midimod.py. Un archivo puede contener un único objeto de "ruta" o una lista de objetos de "ruta".

**Componentes Principales de una Ruta:**

- **"devices" (Objeto, Opcional):**
  
  - Mapea nombres de alias amigables (ej. "MiControladorPrincipal") a subcadenas de los nombres reales de tus dispositivos MIDI (ej. "X-Session Pro").
    
  - midimod usará la sección devices del **primer** archivo de reglas (en el orden de carga) que la contenga.
    
- "_comment" (String, Opcional): Descripción general de la ruta. Se mostrará en el resumen de reglas.
  
- "input_device_substring" (String, Opcional): Parte del nombre del dispositivo MIDI de entrada. Si se omite, se usa el primer puerto de entrada disponible.
  
- "output_device_substring" (String, Opcional): Parte del nombre del dispositivo MIDI de salida. Si se omite, se usa el primer puerto de salida disponible.
  
- "version_midi_map" (Objeto, Opcional): Mapea mensajes MIDI específicos a cambios de la current_active_version o acciones de ciclo (ej. "note_on note=60 channel=0": 1, "note_on note=108": "cycle"). Los mensajes que activan esto son "consumidos".
  
- "transformations" (Lista de Objetos): Define las reglas de transformación que se aplican secuencialmente.
  
- **"routes" (Lista, Requerida para procesamiento):**
  
  - Cada elemento es un objeto que define una ruta de procesamiento.

**Claves Comunes dentro de un Objeto de Transformación:**

- "_comment" (String, Opcional): Describe la transformación.
  
- "version" (Entero o Lista de Enteros, Opcional): La transformación solo aplica si la current_active_version coincide o está en la lista. Si se omite, la transformación aplica siempre dentro de su ruta.
  
- "ch_in" (Lista de Enteros, Opcional): Canales MIDI de entrada (0-15) a los que aplica.
  
- "ch_out" (Lista de Enteros, Opcional): Canal(es) MIDI de salida (0-15). Una lista vacía [] filtra el mensaje.
  
- "cc_in" (Entero, Opcional): Filtra por este número de CC.
  
- "cc_out" (Entero, Opcional): Cambia el número de CC al valor especificado. Si cc_in está presente pero cc_out no, el número de CC no cambia.
  
- "cc_range" (Lista [min, max], Opcional): Escala el valor del CC entrante (que coincide con cc_in, o cualquier CC si cc_in no está) al nuevo rango.
  
- "nt_st" (Entero, Opcional): Semitonos para transponer notas.
  
- "velocity_range" (Lista [min, max], Opcional): Escala la velocidad de los note_on.
  
- "note_to_cc" (Objeto, Opcional): Transforma una nota específica en un CC.
  
  - Contiene: "note_in", "cc_out", "value_on_note_on", "value_on_note_off", "ch_out_cc", "use_velocity_as_value".
- "note_to_pc" (Objeto, Opcional): Transforma una nota específica en un Program Change.
  
  - Contiene: "note_in", "program_out", "send_on_note_on", "send_on_note_off", "ch_out_pc".
- "aftertouch_to_cc" (Objeto, Opcional): Transforma mensajes de Channel Aftertouch en CCs.
  
  - Contiene: "cc_out", "ch_out_cc", "value_range".

**Nota:** Para una descripción exhaustiva de todas las claves y su comportamiento, ejecuta 

```
python midimod.py --help.
```

## Ejemplos Detallados de Reglas

Para ver ejemplos concretos de cómo configurar diferentes tipos de transformaciones y combinaciones, por favor consulta el archivo RULES_EXAMPLES.md.

## Log de Salida en Consola

Cuando midimod está en funcionamiento, los mensajes MIDI procesados se muestran en la consola. El formato general es:

[V] RutaID|IN : ch(C) tipo(N) atr(V) >> [V] RutaID|OUT: ch(C') tipo(N') atr(V')

- [V]: La current_active_version en el momento del procesamiento.
  
- RutaID: Identificador de la ruta que procesó el mensaje (ej. R1, R2).
  
- IN :: Indica el mensaje MIDI original que entró a la ruta.
  
- > > (vacío) Si no hay una parte OUT:, significa que la ruta procesó el mensaje pero no se realizó ninguna transformación.
  
- OUT:: Indica el mensaje MIDI después de ser procesado por las transformaciones de esa ruta.
  
- ch(C): Canal MIDI (1-16).
  
- tipo(N): Tipo de mensaje y nota/CC (ej. note_on(60), cc(10)).
  
- atr(V): Atributo relevante y su valor (ej. vel(100), val(64)).
  

Si un único mensaje de entrada es procesado por múltiples rutas (porque comparten el mismo puerto de entrada físico), o si una ruta divide un mensaje en múltiples salidas (ej. con ch_out), verás múltiples líneas >> OUT: bajo una única línea IN :.

## Solución de Problemas Comunes

- **"Error abriendo puerto..." o "Error enviando mensaje..."**: Usualmente significa que el puerto MIDI está siendo utilizado por otra aplicación (DAW, patchbay virtual, otra instancia de midimod). Cierra todas las demás aplicaciones que puedan usar MIDI.
  
- **Dispositivo no detectado**: Ejecuta python midimod.py --list-ports para ver los nombres exactos de tus dispositivos y asegúrate de que las *_device_substring en tu JSON coincidan.
  
- **Codificación de Archivos JSON**: Asegúrate de que tus archivos .json estén guardados con codificación UTF-8, especialmente si usas caracteres especiales en los _comment.
  

## Contribuciones

Las sugerencias, reportes de bugs y contribuciones son bienvenidas. Por favor, abre un "Issue" en GitHub para discutir cambios o reportar problemas.

## Licencia

Este proyecto está bajo la Licencia MIT. Ver el archivo LICENSE para más detalles.