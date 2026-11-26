# ghost_llm - WinOverlay Bridge (C + Python)

Prototipo experimental en Windows que combina un módulo nativo en **C** (Win32) y un orquestador en **Python**. Actualmente implementa una ventana flotante (*overlay*), atajos globales y captura de regiones de pantalla, con transferencia de imágenes BGRA hacia Python y exportación de diagnóstico a PNG.

El proyecto está orientado a incorporar progresivamente procesamiento de imágenes, adquisición de audio, transcripción (STT) y modelos de lenguaje (LLM). Estas últimas funcionalidades todavía son objetivos de desarrollo, no capacidades implementadas.

> **Nota de alcance:** este repositorio es un laboratorio técnico orientado a arquitectura, latencia, concurrencia y pruebas locales. No constituye una solución lista para producción ni garantiza ocultamiento frente a todos los métodos de captura o inspección del sistema.

---

## Arquitectura general

La solución separa la interacción directa con el sistema operativo de la lógica de orquestación y procesamiento:

- **Módulo nativo (`overlay-prototype/native/`) en C:** gestiona la ventana (`HWND`), aplica `SetWindowDisplayAffinity` con `WDA_EXCLUDEFROMCAPTURE`, mantiene el *message loop* de Win32, registra *hotkeys* globales, captura regiones de pantalla mediante Win32 GDI y renderiza texto/estado de forma segura entre hilos.
- **Orquestador (`overlay-prototype/orchestrator/`) en Python:** conecta con la DLL vía `ctypes`, despacha eventos desde una cola *thread-safe* y coordina el ciclo de captura y actualización del overlay.

```text
[Hotkeys / Win32 Loop (C)]
             │
             ▼
     [Event Queue (Python)]
             │
             ▼
      [Capture Worker]
             │
             ▼
 [Screen Capture (C / Win32 GDI)]
             │
       [BGRA Buffer]
             │
             ▼
       [Python Callback]
             │
             ▼
 [BGRA → RGBA / PNG (diagnóstico)]

[Python Orchestrator] ──(texto / estado)──► [Overlay Render (C)]
```

---

## Estado actual

### Implementado y verificado

- Ventana overlay nativa mediante Win32.
- Exclusión del overlay de métodos de captura compatibles con `WDA_EXCLUDEFROMCAPTURE`.
- Atajos globales para mostrar/ocultar, capturar y limpiar.
- Captura de regiones de pantalla mediante Win32 GDI.
- Transferencia de imágenes BGRA desde C hacia Python mediante `ctypes`.
- Conversión BGRA/RGBA y exportación de capturas de diagnóstico a PNG.
- Pipeline de eventos y captura con worker independiente.
- Actualización del texto y estado del overlay.
- Cierre controlado del pipeline y espera del worker.

### Pendiente de desarrollo

- Definir un contrato de datos estable para las imágenes capturadas.
- Incorporar procesamiento real de imágenes.
- Definir el formato de resultados y su comunicación hacia el overlay.
- Integrar adquisición de audio y transcripción (STT).
- Integrar modelos de lenguaje (LLM).
- Evaluar rendimiento y comportamiento bajo carga.

## Hitos

- Implementación inicial del overlay y su comunicación C/Python.
- Incorporación de captura de pantalla y diagnósticos PNG.
- Commit de referencia: `f8c482f` — `Add screen capture pipeline and PNG diagnostics`.