## Estructura Básica de un Archivo de Reglas

Un archivo JSON (ubicado en la carpeta rules/) puede contener un único objeto de ruta o una lista de objetos de ruta:

**Ejemplo: Un archivo con una sola ruta**

```
{
  "_comment": "Ruta simple de Teclado A a Sintetizador B",
  "input_device_substring": "Teclado A",
  "output_device_substring": "Sintetizador B",
  "transformations": [
    // ... aquí van las reglas de transformación ...
  ]
}
```

**Ejemplo: Un archivo con múltiples rutas**

```
[
  {
    "_comment": "Ruta 1: Teclado A a Sintetizador B",
    "input_device_substring": "Teclado A",
    "output_device_substring": "Sintetizador B",
    "transformations": [ /* ... reglas ... */ ]
  },
  {
    "_comment": "Ruta 2: Controlador Pads a Sampler",
    "input_device_substring": "Controlador Pads",
    "output_device_substring": "Sampler VST",
    "transformations": [ /* ... reglas ... */ ]
  }
]
```

## Claves Principales de una Ruta

- "_comment" (String, Opcional): Descripción de la ruta.

- "input_device_substring" (String, Opcional): Subcadena para identificar el puerto MIDI de entrada. Si se omite, se usa el primer puerto disponible.

- "output_device_substring" (String, Opcional): Subcadena para identificar el puerto MIDI de salida. Si se omite, se usa el primer puerto disponible.

- "version_midi_map" (Objeto, Opcional): Define cómo mensajes MIDI específicos pueden cambiar la current_active_version global (ver sección de Ayuda o ejemplos específicos de version_midi_map).

- "transformations" (Lista de Objetos): Una lista donde cada objeto define una regla de transformación. Estas se aplican en orden.

### version_midi_map

version_midi_map permite controlar dinámicamente qué conjunto de transformaciones se aplican a tus mensajes MIDI. Las transformaciones pueden ser específicas de una versión o aplicarse siempre.

**1. Selección Directa de Versiones con Notas MIDI**

Puedes asignar notas MIDI específicas para activar diferentes "versiones" de reglas.

**Archivo JSON de Ejemplo (rules/preset_selection_by_note.json):**

```
[
  {
    "_comment": "Ruta con selección de presets por notas",
    "input_device_substring": "MiTecladoControlador",
    "output_device_substring": "MiSintetizador",
    "version_midi_map": {
      "note_on note=60": 0,  // Nota C4 (MIDI 60) activa Versión 0 (Base)
      "note_on note=62": 1,  // Nota D4 (MIDI 62) activa Versión 1
      "note_on note=64": 2   // Nota E4 (MIDI 64) activa Versión 2
    },
    "transformations": [
      // --- Reglas Siempre Activas (sin clave "version") ---
      {
        "_comment": "Siempre: Transponer todas las notas +2 semitonos",
        "nt_st": 2
      },
      // --- Reglas para Versión 0 ---
      {
        "_comment": "V0: CC10 en Ch1 se convierte en CC74 en Ch1",
        "version": 0,
        "ch_in": [0], "cc_in": 10, "cc_out": 74, "ch_out": [0]
      },
      {
        "_comment": "V0: Notas del Ch2 se envían al Ch10",
        "version": 0,
        "ch_in": [1], "ch_out": [9]
      },
      // --- Reglas para Versión 1 ---
      {
        "_comment": "V1: CC10 en Ch1 se convierte en CC20 en Ch2, con rango escalado",
        "version": 1,
        "ch_in": [0], "cc_in": 10, "cc_out": 20, "cc_range": [0, 64], "ch_out": [1]
      },
      {
        "_comment": "V1: Nota F3 (MIDI 53) en Ch1 se convierte en CC50 valor 127",
        "version": 1,
        "ch_in": [0],
        "note_to_cc": { "note_in": 53, "cc_out": 50, "value_on_note_on": 127 }
      },
      // --- Reglas para Versión 2 ---
      {
        "_comment": "V2: Todas las notas del Ch1 se silencian (mapeando a un canal no usado)",
        "version": 2,
        "ch_in": [0], "ch_out": [15] // Asumiendo Ch16 no se usa
      },
      {
        "_comment": "V2: CC10 en Ch1 no hace nada (no hay regla específica para él en V2)",
        "_explanation": "Si un CC10 llega en Ch1 y V2 está activa, pasará sin cambios por esta ruta (solo afectado por la transposición de notas siempre activa si fuera un mensaje de nota)."
      }
    ]
  }
]
```

**Explicación:**

- Presionar C4, D4 o E4 en tu "MiTecladoControlador" cambiará la current_active_version.

- La transposición de nt_st: 2 se aplicará a todas las notas en todas las versiones.

- Las reglas de CC y cambio de canal específicas de cada versión solo se aplicarán cuando esa versión esté activa.

**2. "Botones Momentáneos" para Versiones (usando note_on y note_off)**

Activa una versión mientras una tecla está presionada y vuelve a otra al soltarla.

**Archivo JSON de Ejemplo (rules/momentary_version.json):**

```
[
  {
    "_comment": "Ruta con versión momentánea",
    "input_device_substring": "MiTecladoControlador",
    "output_device_substring": "MiSintetizador",
    "version_midi_map": {
      "note_on note=48": 1,   // Al presionar Nota C3 -> Activa Versión 1
      "note_off note=48": 0  // Al soltar Nota C3 -> Vuelve a Versión 0
                                // (Funciona si el controlador envía note_off o si midimod trata note_on vel=0 como note_off para el mapa)
    },
    "transformations": [
      {
        "_comment": "V0: CC1 (ModWheel) en Ch1 controla CC11 (Expression)",
        "version": 0,
        "ch_in": [0], "cc_in": 1, "cc_out": 11, "ch_out": [0]
      },
      {
        "_comment": "V1 (Momentánea): CC1 (ModWheel) en Ch1 controla CC7 (Volume) Y se escala",
        "version": 1,
        "ch_in": [0], "cc_in": 1, "cc_out": 7, "cc_range": [0, 100], "ch_out": [0]
      },
      {
        "_comment": "SIEMPRE ACTIVA: Notas del Ch5 se envían al Ch6",
        "ch_in": [4], "ch_out": [5]
      }
    ]
  }
]
```

**Explicación:**

- Mientras mantienes presionada la Nota C3 (MIDI 48), la Modulación (CC1) controlará el Volumen (CC7) con un rango escalado.

- Al soltar C3, la Modulación volverá a controlar Expression (CC11).

- El remapeo de Ch5 a Ch6 siempre está activo.

**3. Ciclo de Versiones con una Nota MIDI**

Usa una nota para avanzar a la siguiente versión disponible (definida por las reglas que tienen version: N).

**Archivo JSON de Ejemplo (rules/cycle_versions_by_note.json):**

```
[
  {
    "_comment": "Ruta con ciclo de versiones",
    "input_device_substring": "MiFootSwitch", // Un pedal que envía una nota
    "output_device_substring": "MiSampler",
    "version_midi_map": {
      "note_on note=36": "cycle" // Nota C2 (MIDI 36) en note_on cicla las versiones
      // "note_on note=37": "cycle_previous" // Opcional para ciclar hacia atrás
    },
    "transformations": [
      {
        "_comment": "V0: Nota E2 (MIDI 40) en Ch1 dispara CC10 val 127",
        "version": 0, "ch_in": [0],
        "note_to_cc": {"note_in": 40, "cc_out": 10, "value_on_note_on": 127}
      },
      {
        "_comment": "V1: Nota E2 (MIDI 40) en Ch1 dispara CC11 val 127",
        "version": 1, "ch_in": [0],
        "note_to_cc": {"note_in": 40, "cc_out": 11, "value_on_note_on": 127}
      },
      {
        "_comment": "V2: Nota E2 (MIDI 40) en Ch1 dispara CC12 val 127",
        "version": 2, "ch_in": [0],
        "note_to_cc": {"note_in": 40, "cc_out": 12, "value_on_note_on": 127}
      },
      {
        "_comment": "SIEMPRE ACTIVA: CC7 en Ch1 (Volumen) pasa sin cambios",
        "ch_in": [0], "cc_in": 7, "cc_out": 7 // Asegura que se loguee si 'item_acted' lo requiere
      }
    ]
  }
]
```

**Explicación:**

- Cada vez que presionas la Nota C2 (MIDI 36) en tu "MiFootSwitch", midimod cambiará a la siguiente current_active_version disponible (0 -> 1 -> 2 -> 0...).

- Dependiendo de la versión activa, la Nota E2 tendrá un efecto diferente.

- El CC7 del Ch1 siempre pasará.

**4. Especificidad de Canal en version_midi_map**

Puedes hacer que la misma nota MIDI active diferentes versiones o acciones dependiendo del canal por el que llegue.

**Archivo JSON de Ejemplo (rules/channel_specific_version_map.json):**

```
[
  {
    "_comment": "Control de versión específico por canal",
    "input_device_substring": "MiTecladoMultiCanal",
    "output_device_substring": "MiModuloSonido",
    "version_midi_map": {
      "note_on note=24 channel=0": 1,  // Nota C1 en Ch1 (idx 0) -> V1
      "note_on note=24 channel=1": 2,  // Nota C1 en Ch2 (idx 1) -> V2
      "note_on note=25": "cycle"       // Nota C#1 en cualquier canal -> Cicla
    },
    "transformations": [
      {
        "_comment": "V0: Las notas del Ch1 se transponen +5",
        "version": 0, "ch_in": [0], "nt_st": 5
      },
      {
        "_comment": "V1: Las notas del Ch1 se transponen -7 y se envían al Ch10",
        "version": 1, "ch_in": [0], "nt_st": -7, "ch_out": [9]
      },
      {
        "_comment": "V2: Las notas del Ch1 se convierten en CC80 (valor=velocidad)",
        "version": 2, "ch_in": [0],
        "note_to_cc": {"note_in_any": true, "cc_out": 80, "use_velocity_as_value": true}
        // Nota: "note_in_any": true no está implementado, note_to_cc requiere "note_in": N.
        // Para aplicar a cualquier nota en V2/Ch1, necesitarías una regla por cada nota o una modificación
        // a midimod.py para que note_to_cc pueda omitir "note_in" y aplicar a todas las notas del ch_in.
        // Por ahora, asumimos que note_to_cc se definiría para notas específicas.
      }
    ]
  }
]
```

**Explicación:**

- Presionar C1 en el Canal 1 de tu teclado activará la Versión 1.

- Presionar C1 en el Canal 2 de tu teclado activará la Versión 2.

- Presionar C#1 en cualquier canal ciclará entre las versiones.

**Nota Importante sobre note_to_cc y "cualquier nota":**  
El ejemplo V2 con "note_in_any": true es conceptual. La implementación actual de note_to_cc en midimod.py (V17/V19) **requiere** una "note_in":  específica. Para aplicar una transformación de nota a CC a cualquier nota que pase el filtro ch_in, se necesitaría una modificación en process_message_with_rule.

### Transformaciones

Dentro de la lista "transformations", cada objeto define una regla.

**Claves Comunes a la Mayoría de las Transformaciones:**

- "_comment" (String, Opcional): Describe lo que hace la regla.

- "version" (Entero, Opcional): Si se define, la regla solo aplica cuando current_active_version coincide con este número. Si se omite, la regla aplica siempre (independientemente de la versión activa).

- "ch_in" (Lista de Enteros, Opcional): Canales MIDI de entrada (índices 0-15) a los que aplica esta regla. Si se omite, aplica a mensajes de cualquier canal (que tengan un atributo de canal).

---

**1. Cambio de Canal (ch_out)**

Redirige mensajes de uno o más canales de entrada a uno o más canales de salida.

- **Ejemplo 1.1: Un canal de entrada a un canal de salida**
  
  ```
  // Dentro de "transformations":
  {
    "_comment": "Mensajes del Ch1 (idx 0) se envían por Ch5 (idx 4)",
    "ch_in": [0],
    "ch_out": [4]
  }
  ```

- **Entrada:** note_on channel=0 note=60 velocity=100

- **Salida:** note_on channel=4 note=60 velocity=100

- **Ejemplo 1.2: Un canal de entrada a múltiples canales de salida (duplicación)**
  
  ```
  // Dentro de "transformations":
  {
    "_comment": "Mensajes del Ch1 (idx 0) se duplican a Ch2 (idx 1) y Ch3 (idx 2)",
    "ch_in": [0],
    "ch_out": [1, 2]
  }
  ```

- **Entrada:** control_change channel=0 control=10 value=64

- **Salidas (dos mensajes):**
  
  1. control_change channel=1 control=10 value=64
  
  2. control_change channel=2 control=10 value=64

- **Ejemplo 1.3: Múltiples canales de entrada a un único canal de salida (consolidación)**
  
  ```
  // Dentro de "transformations":
  {
    "_comment": "Mensajes de Ch1 (idx 0) o Ch2 (idx 1) se envían por Ch10 (idx 9)",
    "ch_in": [0, 1],
    "ch_out": [9]
  }
  ```

- **Ejemplo 1.4: Sin ch_in (aplica a todos los canales de entrada)**
  
  ```
  // Dentro de "transformations":
  {
    "_comment": "Todos los mensajes (cualquier canal) se envían por Ch16 (idx 15)",
    "ch_out": [15]
  }
  ```

---

**2. Transposición de Notas (nt_st)**

Cambia el tono de los mensajes note_on y note_off.

- **Ejemplo 2.1: Subir una octava las notas del Ch1**
  
  ```
  // Dentro de "transformations":
  {
    "_comment": "Notas del Ch1 (idx 0) suben 12 semitonos",
    "ch_in": [0],
    "nt_st": 12
  }
  ```

- **Entrada:** note_on channel=0 note=60 velocity=100 (C4)

- **Salida:** note_on channel=0 note=72 velocity=100 (C5)

- **Ejemplo 2.2: Bajar 5 semitonos todas las notas (cualquier canal)**
  
  ```
  // Dentro de "transformations":
  {
    "_comment": "Todas las notas bajan 5 semitonos",
    "nt_st": -5
  }
  ```

---

**3. Remapeo de Control Changes (CCs)**

Cambia el número de un CC y/o su valor (con cc_range).

- **Ejemplo 3.1: Cambiar un CC a otro (mismo canal por defecto)**
  
  ```
  // Dentro de "transformations":
  {
    "_comment": "CC20 en Ch1 (idx 0) se convierte en CC74",
    "ch_in": [0],
    "cc_in": 20,
    "cc_out": 74
    // "ch_out" no se especifica, por lo que el mensaje CC74 saldrá por Ch1 (idx 0)
  }
  ```

- **Entrada:** control_change channel=0 control=20 value=100

- **Salida:** control_change channel=0 control=74 value=100

- **Ejemplo 3.2: Cambiar CC y canal de salida**
  
  ```
  // Dentro de "transformations":
  {
    "_comment": "CC1 (ModWheel) en Ch1 (idx 0) se convierte en CC11 (Expression) en Ch2 (idx 1)",
    "ch_in": [0],
    "cc_in": 1,
    "cc_out": 11,
    "ch_out": [1]
  }
  ```

- **Ejemplo 3.3: Solo filtrar por cc_in y cambiar canal (sin cc_out)**
  
  - El CC de salida será el mismo que cc_in.

```
// Dentro de "transformations":
{
  "_comment": "CC10 en Ch1 (idx 0) se envía como CC10 pero por Ch5 (idx 4)",
  "ch_in": [0],
  "cc_in": 10,
  "ch_out": [4]
  // "cc_out" se omite, por lo que el CC enviado será el 10.
}
```

- **Entrada:** control_change channel=0 control=10 value=64

- **Salida:** control_change channel=4 control=10 value=64

---

**4. Escalado de Rango de CC (cc_range)**

Modifica el valor de un CC para que se ajuste a un nuevo rango. Requiere cc_in.

- **Ejemplo 4.1: Escalar valor de CC10 (0-127) al rango 0-64, manteniendo el CC10**
  
  ```
  // Dentro de "transformations":
  {
    "_comment": "CC10 en Ch1: su valor (0-127) se escala a 0-64",
    "ch_in": [0],
    "cc_in": 10,
    // "cc_out" se omite, así que sigue siendo CC10
    "cc_range": [0, 64]
  }
  ```
  
  - **Entrada:** control_change channel=0 control=10 value=127
  
  - **Salida:** control_change channel=0 control=10 value=64
  
  - **Entrada:** control_change channel=0 control=10 value=64
  
  - **Salida:** control_change channel=0 control=10 value=32 (aprox.)

- **Ejemplo 4.2: Escalar valor y cambiar número de CC**
  
  ```
  // Dentro de "transformations":
  {
    "_comment": "CC10 en Ch1 -> CC74, valor escalado a 60-127",
    "ch_in": [0],
    "cc_in": 10,
    "cc_out": 74,
    "cc_range": [60, 127]
  }
  ```

- **Entrada:** control_change channel=0 control=10 value=0

- **Salida:** control_change channel=0 control=74 value=60

- **Entrada:** control_change channel=0 control=10 value=127

- **Salida:** control_change channel=0 control=74 value=127

---

**5. Transformación de Nota a CC (note_to_cc)**

Convierte un mensaje note_on o note_off específico en un mensaje control_change.

- **Ejemplo 5.1: Botón de Nota como Toggle CC (On/Off)**
  
  ```
  // Dentro de "transformations":
  {
    "_comment": "Nota 60 (C4) en Ch1 -> CC20 (On=127, Off=0) en el mismo canal",
    "ch_in": [0],
    "note_to_cc": {
      "note_in": 60,
      "cc_out": 20,
      "value_on_note_on": 127,
      "value_on_note_off": 0
      // "ch_out_cc" se omite, usa el canal de la nota original (Ch1)
    }
  }
  ```

- **Entrada:** note_on channel=0 note=60 velocity=100

- **Salida:** control_change channel=0 control=20 value=127

- **Entrada:** note_off channel=0 note=60 velocity=0 (o note_on con vel 0)

- **Salida:** control_change channel=0 control=20 value=0

- **Ejemplo 5.2: Nota note_on dispara CC con valor fijo, note_off no hace nada**
  
  ```
  // Dentro de "transformations":
  {
    "_comment": "Nota 62 (D4) en Ch1 -> CC21 valor 99 en Ch5 (idx 4). NoteOff ignorado.",
    "ch_in": [0],
    "note_to_cc": {
      "note_in": 62,
      "cc_out": 21,
      "value_on_note_on": 99,
      // "value_on_note_off" se omite (o es -1), por lo que no se envía CC en note_off.
      "ch_out_cc": 4 
    }
  }
  ```

- **Ejemplo 5.3: Usar velocidad de la nota como valor del CC (requiere modificación en midimod.py)**
  
  - Nota: El midimod.py (V17 que me proporcionaste) no tiene esta capacidad directamente. Esto es un ejemplo de cómo lo definirías si se implementara.

```
// Dentro de "transformations":
{
  "_comment": "Nota 64 (E4) en Ch1 -> CC22, valor = velocidad de la nota",
  "_explanation": "Esto requiere que 'use_velocity_as_value' esté implementado en midimod.py",
  "ch_in": [0],
  "note_to_cc": {
    "note_in": 64,
    "cc_out": 22,
    "use_velocity_as_value": true, // Clave hipotética
    "value_on_note_off": 0        // Para cuando se suelta
  }
}
```

---

**6. Escalar Velocidad de Nota (velocity_range)**

Modifica la velocidad de los mensajes note_on.

- **Ejemplo 6.1: Comprimir rango dinámico de velocidad**
  
  ```
  // Dentro de "transformations":
  {
    "_comment": "Notas en Ch1: velocidad (1-127) se escala a 40-100",
    "ch_in": [0],
    "velocity_range": [40, 100]
  }
  ```

- **Entrada:** note_on channel=0 note=60 velocity=1

- **Salida:** note_on channel=0 note=60 velocity=40 (aprox.)

- **Entrada:** note_on channel=0 note=60 velocity=127

- **Salida:** note_on channel=0 note=60 velocity=100

- **Entrada:** note_on channel=0 note=60 velocity=64

- **Salida:** note_on channel=0 note=60 velocity=70 (aprox.)

---

#### Combinación de Transformaciones:

Recuerda que las transformaciones dentro de una lista "transformations" para una ruta se aplican secuencialmente.

**Ejemplo Combinado:**

```
// Dentro de "transformations":
[
  {
    "_comment": "V0: Siempre Activa: Todas las notas entrantes por Ch1 bajan una octava",
    "ch_in": [0],
    "nt_st": -12
  },
  {
    "_comment": "V0: Solo para V0: El CC10 (en Ch1, después de cualquier transposición) se convierte en CC70 y va al Ch2",
    "version": 0,
    "ch_in": [0], // Se refiere al canal del mensaje que LLEGA a esta regla
    "cc_in": 10,
    "cc_out": 70,
    "ch_out": [1]
  },
  {
    "_comment": "V0: Solo para V0: Las notas que AHORA están en Ch2 (resultado de un ch_out anterior, o si entraron así) se limitan en velocidad",
    "version": 0,
    "ch_in": [1], // Atrapa mensajes que ahora están en el canal 2
    "velocity_range": [50, 90]
  }
]
```

Estos ejemplos deberían darte una buena base para construir tus propias configuraciones complejas y aprovechar las diferentes capacidades de transformación de midimod.
