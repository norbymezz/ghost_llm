#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdint.h>
#include <stdlib.h>

/* Capture is opt-in; this scaffold does not record or transmit data. */
int32_t overlay_capture_screen_stub(void **buffer, size_t *size) {
    if (buffer) *buffer = NULL;
    if (size) *size = 0;
    return -1; /* Implement with an explicit region and caller-owned buffer. */
}
int32_t overlay_capture_audio_stub(void **buffer, size_t *size) {
    if (buffer) *buffer = NULL;
    if (size) *size = 0;
    return -1; /* Implement with an explicit device and caller-owned buffer. */
}
