#ifndef OVERLAY_API_H
#define OVERLAY_API_H

#include <stdint.h>

#ifdef _WIN32
  #ifdef OVERLAY_BUILD
    #define OVERLAY_API __declspec(dllexport)
  #else
    #define OVERLAY_API __declspec(dllimport)
  #endif
#else
  #define OVERLAY_API
#endif

#ifdef __cplusplus
extern "C" {
#endif

typedef struct OverlayConfig {
    int32_t width;
    int32_t height;
    int32_t x;
    int32_t y;
} OverlayConfig;

/* UTF-8 text is copied before this function returns. */
OVERLAY_API int32_t overlay_initialize(const OverlayConfig *config);
OVERLAY_API int32_t overlay_set_text(const char *utf8_text);
OVERLAY_API int32_t overlay_set_visible(int32_t visible);
OVERLAY_API int32_t overlay_shutdown(void);

#ifdef __cplusplus
}
#endif

#endif /* OVERLAY_API_H */
