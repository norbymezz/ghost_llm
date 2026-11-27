# Overlay prototype

Prototipo experimental para Windows que combina un módulo nativo en C (Win32) con un orquestador en Python.

## Arquitectura

- **Native (C):** administra la ventana overlay, los atajos globales y la captura de regiones de pantalla.
- **Bridge (Python / ctypes):** comunica Python con la DLL nativa mediante una API C.
- **Orchestrator (Python):** coordina los eventos, la captura y la actualización del overlay.
- **Debug capture:** convierte los buffers BGRA a RGBA y permite guardar capturas como archivos PNG.

El contrato C se mantiene independiente de Python. El wrapper `ctypes` utiliza UTF-8 para el intercambio de texto.

## OCR

El pipeline admite motores OCR desacoplados mediante el protocolo `FrameOcrEngine`.

### Contrato de datos

- `CaptureFrame`: contiene coordenadas, dimensiones, buffer BGRA inmutable, cantidad de bytes escritos y timestamp de captura.
- `FrameOcrEngine`: define el método `recognize(frame)`.
- `OcrResult`: devuelve el texto reconocido, tiempo de procesamiento y posible error.

### Motor implementado: Tesseract

Se utiliza Tesseract OCR 5 mediante `pytesseract`.

**Requisitos:**
- Tesseract OCR instalado localmente.
- Modelo de idioma `eng`.
- Python con `pytesseract` y Pillow.

Instalación del wrapper Python:

```powershell
python -m pip install pytesseract
```

Ejecutable configurado actualmente:

`C:\Program Files\Tesseract-OCR\tesseract.exe`

**Configuración inicial:**
- Motor LSTM (`--oem 1`).
- Segmentación de página PSM 6.
- Preservación de espacios entre palabras.
- Diccionarios léxicos desactivados.
- Timeout de reconocimiento: 5 segundos.

El tiempo informado incluye conversión de imagen y reconocimiento.

### Motor de prueba

`StubOcrEngine` permite simular latencia, errores periódicos y resultados vacíos sin depender de Tesseract.

### Limitaciones conocidas

El OCR reconoce texto, pero no garantiza reconstruir fielmente:
- Sangrías y espacios consecutivos.
- Posiciones originales de los caracteres.
- Estructura exacta del código fuente.

La reconstrucción geométrica y la evaluación de fidelidad siguen pendientes.


## Estado actual

Implementado y probado:

- Creación y control de la ventana overlay.
- Exclusión de la ventana overlay de las capturas compatibles con `WDA_EXCLUDEFROMCAPTURE`.
- Atajos globales para mostrar/ocultar, capturar y limpiar.
- Captura de regiones de pantalla mediante Win32 GDI.
- Transferencia de imágenes BGRA desde C hacia Python.
- Conversión BGRA/RGBA y exportación de diagnóstico a PNG.
- Orquestación de la captura mediante un worker y actualización del estado del overlay.
- Contrato de datos para el intercambio entre captura y OCR.
- Integración de Tesseract OCR 5 mediante Python.
- Motor OCR configurable y stub para pruebas.
- Visualización de resultados OCR en el overlay.

La captura, el guardado PNG y el reconocimiento OCR local están implementados y probados. La fidelidad del reconocimiento sobre código fuente todavía requiere evaluación.

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

### Interfaz del overlay
- Movimiento mediante atajos de teclado.
- Redimensionamiento del overlay.
- Control de transparencia.
- Ajuste independiente de la región de captura.
- Revisión del escalado DPI de Windows.

### OCR
- Evaluar fidelidad sobre código fuente.
- Mejorar la reconstrucción de espacios, sangrías y saltos de línea.
- Medir latencia y rendimiento bajo carga.

### Evolución
- Evaluar integración de STT y LLM.