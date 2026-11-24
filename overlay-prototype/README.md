# Overlay prototype

Esqueleto experimental Windows-only. Construcción: ejecutar `native/build.ps1` desde PowerShell con CMake y un compilador C instalados. La captura, STT y LLM quedan como puntos de integración; no se envían datos ni se configuran credenciales.

El contrato C se mantiene independiente de Python. El wrapper `ctypes` usa UTF-8 para texto.
