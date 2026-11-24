#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdint.h>

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
    (void)x;
    (void)y;
    (void)width;
    (void)height;
    (void)out_bgra;
    (void)max_bytes;
    if (out_written_bytes) {
        *out_written_bytes = 0;
    }
    return OV_ERR_CAPTURE_FAILED;
}
