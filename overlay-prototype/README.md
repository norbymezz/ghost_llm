# Overlay prototype

Prototipo experimental para Windows que combina un módulo nativo en C (Win32) con un orquestador en Python.

## Arquitectura

- **Native (C):** administra la ventana overlay, los atajos globales y la captura de regiones de pantalla.
- **Bridge (Python / ctypes):** comunica Python con la DLL nativa mediante una API C.
- **Orchestrator (Python):** coordina los eventos, la captura y la actualización del overlay.
- **Debug capture:** convierte los buffers BGRA a RGBA y permite guardar capturas como archivos PNG.

El contrato C se mantiene independiente de Python. El wrapper `ctypes` utiliza UTF-8 para el intercambio de texto.

## Estado actual

Implementado y probado:

- Creación y control de la ventana overlay.
- Exclusión de la ventana overlay de las capturas compatibles con `WDA_EXCLUDEFROMCAPTURE`.
- Atajos globales para mostrar/ocultar, capturar y limpiar.
- Captura de regiones de pantalla mediante Win32 GDI.
- Transferencia de imágenes BGRA desde C hacia Python.
- Conversión BGRA/RGBA y exportación de diagnóstico a PNG.
- Orquestación de la captura mediante un worker y actualización del estado del overlay.

La captura y el guardado PNG están verificados. El procesamiento semántico de las imágenes todavía no está implementado.

## Construcción

Desde el directorio `overlay-prototype/`, ejecutar en PowerShell:

```powershell
.\native\build.ps1
```

Requiere CMake y un compilador C compatible con Windows.

## Ejecución

Desde la raíz del repositorio:

```
python .\overlay-prototype\orchestrator\run_pipeline.py
```

Los archivos PNG de diagnóstico se guardan en `debug_captures/`.

## Pendiente

- Definir el contrato de datos entre captura y procesamiento.
- Incorporar procesamiento real de imágenes.
- Definir cómo entregar los resultados al overlay.
- Integrar STT y LLM cuando corresponda.
- Revisar rendimiento y comportamiento bajo carga.