# Valkyrie Connect - Auto Hero Quest Farmer

**Versión 1.0.0**

Automatización por reconocimiento de imagen para las **Misiones de Héroe** de Valkyrie Connect (versión de escritorio). El bot navega el menú de selección, resuelve la ruta de nodos de cada héroe (escenas de historia + combates) y reclama los cofres finales automáticamente. Sin acceso a memoria ni modificación del juego.

> **⚠️ Aviso importante**  
> Esta herramienta automatiza acciones de ratón y teclado sobre la ventana del juego. El uso que le des es bajo tu exclusiva responsabilidad. No me hago responsable de cualquier sanción, baneo o consecuencia que pueda derivarse de su uso. Respeta los términos de servicio del juego.

> **⚠️ Limitaciones**  
> Esto no es una herramienta perfecta. El reconocimiento de imagen depende de la calidad de tus capturas, la resolución de tu pantalla y las condiciones del juego. Puede fallar de vez en cuando — un botón que no se detecta, un scroll que no cae exacto, un cofre que no se abre. En general cumple su función, pero si ves que se atasca, para con F8 y reajusta. No esperes milagros.

---

## Requisitos

- Python 3.9 o superior
- Valkyrie Connect ejecutándose en ventana (no a pantalla completa)
- Capturas de pantalla de tu propia partida para el reconocimiento de imagen

## Instalación

```bash
pip install -r requirements.txt
```

En Windows, si quieres usar la tecla de parada **F8** con el juego en primer plano, ejecuta la terminal **como Administrador**. Esto le da al script el mismo nivel de privilegios que el juego, necesario para que los hooks de teclado funcionen entre procesos.

## Prepara tus plantillas

El bot se guía por imágenes. Tienes que capturar tus propias referencias desde el juego y guardarlas en una carpeta `templates/`. Cada recorte debe ser justo lo necesario, sin fondo de más:

| Archivo | Qué capturar |
|---|---|
| `icono_disponible.png` | El círculo naranja con "!" que marca un nodo pendiente |
| `boton_omitir.png` | El botón "Omitir" en las escenas de historia |
| `boton_aceptar_omitir.png` | La confirmación después de pulsar Omitir |
| `boton_play.png` / `boton_play_v2.png` | El botón Play (preparación y selección de equipo) |
| `pantalla_resultados.png` | La pantalla de victoria con las alas y estrellas |
| `cofre_1.png` / `cofre_2.png` / `cofre_3.png` | Los tres cofres finales (madera, plata, oro) |
| `flecha_volver.png` | La flecha de la esquina para volver a la lista |
| `insignia_completa.png` | La insignia dorada "★ 9/9" de héroe completado |

## Cómo se usa

### Con interfaz gráfica

```bash
python interfaz_valkyrie.py
```

1. Abre el menú de selección de héroes en el juego.
2. Pulsa **PLAY** en la interfaz.
3. En 5 segundos pon el foco en la ventana del juego.
4. El bot empieza a recorrer héroes automáticamente.

### Solo por consola

```bash
python recorrido_heroes.py
```

### Para una sola misión (prueba)

```bash
python auto_farmeo_valkyrie.py
```

Esto resuelve la ruta del héroe que tengas abierto en pantalla y reclama sus cofres. Sin navegación entre héroes.

## Cómo parar

- **Botón STOP** en la interfaz.
- **Tecla F8** (global, funciona aunque el juego tenga el foco).
- Mueve el ratón a la **esquina superior izquierda** de la pantalla (fail-safe de pyautogui).

## Cómo funciona

No usa coordenadas fijas ni memoria del juego. Todo se basa en lo que ve en pantalla:

- **Reconocimiento de nodos y botones**: compara las plantillas que capturaste con la pantalla en tiempo real usando OpenCV. Así encuentra el botón "Play", los cofres, los nodos pendientes, etc.
- **Navegación entre héroes**: la rejilla de selección se recorre con coordenadas relativas a la resolución de tu pantalla. Como el scroll del juego no siempre cae exactamente donde toca, el bot busca la posición real de cada tarjeta ajustando hacia arriba o abajo hasta encontrar texto legible.
- **Scroll**: hace un arrastre (swipe) en vez de usar la rueda del ratón, porque el juego responde mal al scroll tradicional.
- **Evita repetir héroes**: cuando haces scroll y algunas tarjetas se repiten, el bot las identifica por un hash perceptual de la zona del nombre (no por OCR). Si dos hashes se parecen lo suficiente, asume que es el mismo héroe y lo salta.
- **Detección de héroe completado**: busca la insignia "★ 9/9" con template matching. Además comprueba si quedan nodos "!" pendientes, porque los libros de historia no cuentan para las estrellas y un héroe puede estar en 9/9 pero aún tener escenas sin ver.

## Estructura del proyecto

```
.
├── auto_farmeo_valkyrie.py   # Lógica principal: nodos, combates, cofres
├── recorrido_heroes.py       # Navegación por la rejilla de héroes
├── interfaz_valkyrie.py      # Interfaz gráfica con Tkinter
├── requirements.txt
├── gui_templates/            # Iconos decorativos para la interfaz
└── templates/                # Tus capturas de referencia (las que tú crees)
```

## Licencia

Uso personal. Cada cual que lo adapte como quiera.
