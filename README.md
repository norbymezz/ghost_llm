# ghost_llm
# WinOverlay Bridge (C + Python)

Prototipo experimental en Windows que combina un módulo nativo en **C** (Win32) y un orquestador en **Python** para explorar interfaces flotantes excluidas de captura de pantalla (`WDA_EXCLUDEFROMCAPTURE`), atajos globales, adquisición de datos (pantalla/audio) y renderizado de respuestas provenientes de un *pipeline* de alto nivel (como transcripción o modelos de lenguaje).

> **Nota de alcance:** este repositorio es un laboratorio técnico orientado a arquitectura, latencia, concurrencia y pruebas locales. No constituye una solución lista para producción ni garantiza ocultamiento frente a todos los métodos de captura o inspección del sistema.

---

## Arquitectura general

La solución separa la interacción directa con el sistema operativo de la lógica de orquestación y red:

- **Módulo nativo (`native/`) en C:** gestiona la ventana (`HWND`), aplica `SetWindowDisplayAffinity` con `WDA_EXCLUDEFROMCAPTURE`, mantiene el *message loop* de Win32, registra *hotkeys* globales, maneja *buffers* de captura y renderiza texto/estado de forma segura entre hilos.
- **Orquestador (`orchestrator/`) en Python:** conecta con la DLL vía `ctypes`, despacha eventos desde una cola *thread-safe*, coordina captura de pantalla/audio y gestiona llamadas/flujos hacia servicios externos o modelos.

```text
[Hotkeys / Win32 Loop (C)] ──(evento)──► [Cola / Pipeline (Python)]
                                                     │
[Captura Pantalla / Audio (C)] ──(buffer)──────────► [Procesamiento / LLM]
                                                     │
[Orquestador (Python)] ────(UTF-8 / estado)───────► [Overlay Render (C)]
