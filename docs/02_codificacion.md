# Codificación del payload

Última actualización: 2026-08-23

Este documento fija cómo se representa una concentración de O₃ en el payload
LoRaWAN, y qué significa exactamente «voltear el bit *k*».

> **Criticidad.** Este módulo produce el *ground truth* de toda la tesis. Un
> error de endianness, de escala o de signo invalidaría todos los resultados
> posteriores sin producir ningún fallo visible: el pipeline seguiría
> ejecutándose y entregando números incorrectos. Todo lo que aquí se decide
> debe estar cubierto por pruebas.

---

## 1. Por qué CayenneLPP

### Verificado

CayenneLPP (Cayenne Low Power Payload), creado por myDevices, es el formato de
facto para payloads en LoRaWAN. La evidencia de su adopción:

- Cumple con la restricción de tamaño de payload, que puede bajar hasta 11
  bytes, y permite enviar datos de varios sensores en un mismo mensaje.
- **The Things Stack lo soporta nativamente** como *payload formatter*. Al
  habilitarlo, los mensajes uplink incluyen un objeto `decoded_payload`.
- Sus tipos de dato siguen las guías **IPSO Alliance Smart Objects**, que
  identifican cada tipo con un *Object ID*. No es un formato propietario
  aislado.
- Existen implementaciones de referencia para Arduino (myDevicesIoT,
  ElectronicCats), integradas en el ecosistema TTN.

### Implicación para el modelo de amenaza

El payload en LoRaWAN es un recurso caro: ciclo de trabajo regulado, tiempo en
aire y consumo de batería. Ninguna implementación real transmite `float32` ni
enteros de gran anchura para una lectura de sensor. Esto **descarta** los
esquemas de codificación considerados en fases previas de esta investigación y
confirma la elección tomada en la línea anterior.

Consecuencia directa: la superficie de ataque real es de 16 bits por magnitud,
no de 32 ni de 64. La tabla de vulnerabilidad se construye sobre esa anchura.

---

## 2. Estructura del formato

Cada medición se codifica como tres campos consecutivos:

```
[canal] [tipo] [datos...]
```

- **Canal** (1 byte): identifica el sensor dentro del dispositivo.
- **Tipo** (1 byte): identifica la magnitud. Object ID de IPSO.
- **Datos** (longitud variable): según el tipo, en **big-endian**.

Ejemplo con temperatura (tipo `0x67`, 2 bytes, 0.1 °C):

```
01 67 01 10
│  │  └──┴── 0x0110 = 272 → 27.2 °C
│  └─────── tipo: temperatura
└────────── canal 1
```

---

## 3. Hallazgo: el formato no cubre el dominio de aplicación

**CayenneLPP no define ningún tipo para concentración de gases.**

Los tipos disponibles son: entrada/salida digital, entrada/salida analógica,
iluminación, presencia, temperatura, humedad, acelerómetro, barómetro,
giroscopio y ubicación GPS. No hay ozono, ni material particulado, ni CO, ni
NO₂, ni SO₂.

Esto no es una laguna menor. Significa que **todo despliegue LoRaWAN de
monitoreo de calidad del aire debe improvisar su propia codificación**, sin
criterio compartido de resolución ni de rango.

La literatura lo confirma: en despliegues publicados de sistemas LoRaWAN para
monitoreo de calidad del aire exterior, los autores desarrollan un algoritmo
propio de adquisición y codificación tras considerar varios esquemas
alternativos.

### Por qué esto es un resultado de la tesis

El análisis de la ventana de vulnerabilidad demostró que **la resolución de
codificación determina qué bits son explotables y con qué probabilidad**:

| Resolución | Bit crítico (O₃) |
|---|---|
| 1 u/LSB | 6 → 7 (4.3% → 47.3%) |
| 0.1 u/LSB | 9 → 10 (2.1% → 23.4%) |
| 0.01 u/LSB | 12 → 13 (0.97% → 10.9%) |

Un mismo ataque físico produce firmas distintas y probabilidades de daño
distintas según cómo se codifique. La elección de resolución deja de ser un
detalle de implementación y se convierte en **una decisión de diseño con
consecuencias de seguridad cuantificables**, que hoy se toma sin criterio
porque el estándar no la cubre.

Ángulo no presente en Alizadeh & Bidgoly (2023).

---

## 4. Decisión: Analog Input reinterpretado a 1 ppb/LSB

### Lo adoptado

O₃ se codifica con el tipo **Analog Input (`0x02`)**, 2 bytes, big-endian,
**reinterpretando la escala a 1 ppb por LSB**.

```
43 ppb  →  01 02 00 2B
           │  │  └──┴── 0x002B = 43
           │  └─────── tipo: Analog Input
           └────────── canal 1
```

### Fundamento

1. **Es lo que haría un implementador real.** A falta de tipo específico, Analog
   Input es el contenedor genérico natural para una magnitud escalar.
2. **Coincide con la resolución normativa.** La Tabla 2 de la
   NOM-172-SEMARNAT-2023 especifica O₃ en ppm con 3 cifras decimales
   significativas, es decir 1 ppb.
3. **Coincide con la resolución de la fuente.** RAMA reporta O₃ como entero en
   ppb (verificado: `int64` en las 37 columnas de estación).
4. **Codificar a 0.01 inventaría precisión inexistente.** El instrumento no
   resuelve centésimas de ppb; representarlas sería fabricar información.

### Desviación respecto a la especificación

La especificación de CayenneLPP define Analog Input con resolución de 0.01 por
LSB. **Esta implementación se desvía de ese valor.**

La desviación es deliberada y debe declararse explícitamente en la tesis. No es
un descuido: es precisamente el tipo de decisión ad hoc que el hallazgo de la
sección 3 documenta como práctica inevitable en este dominio.

> **Pendiente V13.** Verificar la resolución exacta de Analog Input contra la
> tabla oficial del repositorio de myDevices antes de citarla en la tesis. No
> debe darse por sentada.

### Alternativas descartadas

| Alternativa | Motivo del descarte |
|---|---|
| Analog Input a 0.01/LSB (según especificación) | 43 ppb → raw 4300. El bit 5 valdría 0.32 ppb. Toda la tabla de vulnerabilidad se desplaza siete bits y los desplazamientos explotables dejan de corresponder a magnitudes físicamente significativas |
| Tipo propietario fuera del estándar | Más honesto formalmente, pero se aleja de lo que un despliegue real haría y debilita el argumento de representatividad |
| `float32` / enteros de gran anchura | Descartado por evidencia: incompatible con la restricción de tamaño de payload en LoRaWAN. No se usa en producción |

---

## 5. Signo

Analog Input es un tipo **con signo** en la especificación.

El O₃ nunca es negativo: el mínimo observado en RAMA 2025 es 0 ppb. Sin embargo
se conserva la semántica con signo, porque tiene una consecuencia relevante para
el modelo de adversario.

Si el atacante voltea el bit 15 sobre un valor pequeño, el resultado decodificado
es negativo. La función de decisión `banda_o3()` rechaza valores negativos con
`ValueError`.

**Esto no es un fallo: es información.** Un valor negativo tras el ataque
corresponde a una lectura físicamente imposible, que cualquier validación de
rango en el Application Server rechazaría. Constituye un **ataque
autodelatado**, y merece categoría propia en los resultados: no produce daño,
pero sí evidencia de manipulación.

---

## 6. Numeración de bits

Hay tres niveles de numeración y confundirlos es el error más probable en este
módulo.

### Nivel 1 — bit del valor

43 ppb en 16 bits:

```
bit:  15 14 13 12 11 10  9  8   7  6  5  4  3  2  1  0
       0  0  0  0  0  0  0  0   0  0  1  0  1  0  1  1
```

El bit *k* vale 2^k ppb. Bit 5 = 32 ppb.

**Ésta es la numeración usada en todas las tablas de la tesis.**

### Nivel 2 — posición en el arreglo de bytes

CayenneLPP es big-endian: el byte más significativo va primero.

```
índice:   0        1        2          3
        canal    tipo      MSB        LSB
         01       02    bits 15-8   bits 7-0
```

Conversión de bit del valor a posición en el arreglo:

```python
byte_idx = OFFSET_DATOS + (1 - k // 8)   # big-endian: MSB primero
bit_pos  = k % 8
```

El término `1 - k // 8` es lo que invierte el orden por ser big-endian. Omitirlo
es el error clásico en este punto, y produce que el bit 5 se aplique donde debía
ir el bit 13.

### Nivel 3 — bit del texto cifrado

AES en modo contador cifra por XOR con un keystream:

```
C = P ⊕ Ks
```

Por tanto:

```
(C ⊕ 2^j) ⊕ Ks = P ⊕ Ks ⊕ 2^j ⊕ Ks = P ⊕ 2^j
```

**Voltear el bit *j* del texto cifrado voltea exactamente el bit *j* del texto
claro.** XOR es transparente a la posición del bit.

Ésta es la propiedad de maleabilidad que hace posible el ataque sin conocer la
clave: el nivel 3 y el nivel 2 se corresponden uno a uno.

---

## 7. Restricción del adversario: no controla el signo

Voltear el bit *k* **no suma** 2^k: **conmuta** el bit.

- Si el bit estaba en 0 → el valor aumenta en 2^k
- Si el bit estaba en 1 → el valor disminuye en 2^k

El atacante situado entre NS y AS observa texto cifrado, no texto claro. **No
conoce el estado previo del bit, y por tanto no controla la dirección del daño.**

Consecuencias:

- Un flip repetido sobre el mismo bit produce **oscilación**, no deriva
  acumulada. El desplazamiento neto esperado de un atacante ciego es cero.
- Producir deriva sostenida requiere un atacante que **estime** el valor
  probable y elija en cada mensaje el bit cuyo flip produce el signo deseado.
- El ciclo diurno del O₃, público y regular, es el conocimiento de dominio que
  permite esa estimación.

> **Pendiente V1.** La oscilación está derivada analíticamente pero **no
> verificada empíricamente**. Debe comprobarse sobre datos reales antes de
> afirmarse en la tesis.

---

## 8. Prueba de extremo a extremo

La cadena completa se valida con una sola aserción:

```python
cifrado = encrypt(encode_o3(43), key, devaddr, fcnt)
atacado = flip_bit(cifrado, 5)
recibido = decode_o3(decrypt(atacado, key, devaddr, fcnt))
assert recibido == 43 + 32
```

Si esta prueba pasa, están correctos simultáneamente: la codificación, el orden
de bytes, el cifrado, el descifrado y la propiedad de maleabilidad.

---

## 9. Interfaz del módulo

```python
encode_o3(ppb, channel=1) -> bytes
decode_o3(frame) -> int
flip_bit(data, k) -> bytes
encrypt(plaintext, key, devaddr, fcnt) -> bytes
decrypt(ciphertext, key, devaddr, fcnt) -> bytes
```

---

## Pendientes

| ID | Descripción | Estado |
|---|---|---|
| V1 | Oscilación vs. deriva bajo flip repetido | Abierto — bloquea afirmaciones sobre el ataque sostenido |
| V13 | Resolución exacta de Analog Input en la especificación de myDevices | Abierto |
| V14 | Construcción exacta del bloque contador A_i en LoRaWAN 1.1 (DevAddr, dirección de enlace, FCnt, índice de bloque) contra la especificación | Abierto |