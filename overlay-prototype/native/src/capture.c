#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdint.h>
#include <limits.h>
#include <string.h>

#define OVERLAY_EXPORTS
#include "overlay_api.h"

int ov_capture_region(
    int x,
    int y,
    int width,
    int height,
    uint8_t* out_bgra,
    int max_bytes,
    int* out_written_bytes
) {
    if (out_written_bytes) {
        *out_written_bytes = 0;
    }

    if (!out_bgra || width <= 0 || height <= 0 || max_bytes <= 0) {
        return OV_ERR_INVALID_ARG;
    }

    if (width > 16384 || height > 16384) {
        return OV_ERR_INVALID_ARG;
    }

    /* Validar producto en 64 bits sin signo antes de convertir a int */
    uint64_t required_u64 = (uint64_t)width * (uint64_t)height * 4ULL;
    if (required_u64 > (uint64_t)INT_MAX) {
        return OV_ERR_INVALID_ARG;
    }

    int required_bytes = (int)required_u64;
    if (max_bytes < required_bytes) {
        return OV_ERR_BUFFER_TOO_SMALL;
    }

    HDC screen_dc = GetDC(NULL);
    if (!screen_dc) {
        return OV_ERR_CAPTURE_FAILED;
    }

    HDC mem_dc = CreateCompatibleDC(screen_dc);
    if (!mem_dc) {
        ReleaseDC(NULL, screen_dc);
        return OV_ERR_CAPTURE_FAILED;
    }

    HBITMAP dib = CreateCompatibleBitmap(screen_dc, width, height);
    if (!dib) {
        DeleteDC(mem_dc);
        ReleaseDC(NULL, screen_dc);
        return OV_ERR_CAPTURE_FAILED;
    }

    HGDIOBJ old_obj = SelectObject(mem_dc, dib);
    if (!old_obj || old_obj == HGDI_ERROR) {
    DeleteObject(dib);
    DeleteDC(mem_dc);
    ReleaseDC(NULL, screen_dc);
    return OV_ERR_CAPTURE_FAILED;
    }
    BOOL blt_ok = BitBlt(mem_dc, 0, 0, width, height, screen_dc, x, y, SRCCOPY);

    /* Deseleccionar el bitmap de mem_dc antes de llamar a GetDIBits */
    SelectObject(mem_dc, old_obj);

    if (!blt_ok) {
        DeleteObject(dib);
        DeleteDC(mem_dc);
        ReleaseDC(NULL, screen_dc);
        return OV_ERR_CAPTURE_FAILED;
    }

    BITMAPINFO bmi;
    memset(&bmi, 0, sizeof(bmi));
    bmi.bmiHeader.biSize = sizeof(BITMAPINFOHEADER);
    bmi.bmiHeader.biWidth = width;
    /* Alto negativo para obtener filas de arriba hacia abajo (top-down) */
    bmi.bmiHeader.biHeight = -height;
    bmi.bmiHeader.biPlanes = 1;
    bmi.bmiHeader.biBitCount = 32;
    bmi.bmiHeader.biCompression = BI_RGB;

    int scanlines = GetDIBits(
        mem_dc,
        dib,
        0,
        (UINT)height,
        out_bgra,
        &bmi,
        DIB_RGB_COLORS
    );

    DeleteObject(dib);
    DeleteDC(mem_dc);
    ReleaseDC(NULL, screen_dc);

    if (scanlines != height) {
        return OV_ERR_CAPTURE_FAILED;
    }

    /* Asegurar canal alfa definido (0xFF = opaco) en layout BGRA */
    uint64_t pixel_count = (uint64_t)width * (uint64_t)height;
    for (uint64_t i = 0; i < pixel_count; ++i) {
        out_bgra[i * 4ULL + 3ULL] = 0xFF;
    }

    if (out_written_bytes) {
        *out_written_bytes = required_bytes;
    }

    return OV_OK;
}
