#ifndef GHOST_OVERLAY_API_H
#define GHOST_OVERLAY_API_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#if defined(_WIN32)
    #if defined(OVERLAY_EXPORTS)
        #define OV_API __declspec(dllexport)
    #else
        #define OV_API __declspec(dllimport)
    #endif
#else
    #define OV_API
#endif

/* Codigos de retorno */
typedef enum {
    OV_OK = 0,
    OV_ERR_INVALID_ARG = -1,
    OV_ERR_INIT_FAILED = -2,
    OV_ERR_NOT_INITIALIZED = -3,
    OV_ERR_BUFFER_TOO_SMALL = -4,
    OV_ERR_CAPTURE_FAILED = -5
} OvStatus;

/* Estados visuales del overlay */
typedef enum {
    OV_STATE_IDLE = 0,
    OV_STATE_CAPTURING = 1,
    OV_STATE_THINKING = 2,
    OV_STATE_STREAMING = 3,
    OV_STATE_ERROR = 4
} OvState;

/* Identificadores de atajos globales */
typedef enum {
    OV_HOTKEY_TOGGLE_VISIBILITY = 1,
    OV_HOTKEY_CAPTURE_REGION = 2,
    OV_HOTKEY_TOGGLE_AUDIO = 3,
    OV_HOTKEY_CLEAR = 4
} OvHotkeyId;

/* Configuracion inicial de la ventana y geometria */
typedef struct {
    int x;
    int y;
    int width;
    int height;
    int exclude_from_capture; /* 1 para WDA_EXCLUDEFROMCAPTURE, 0 para normal */
    int topmost;              /* 1 para WS_EX_TOPMOST */
    int click_through;        /* 1 para WS_EX_TRANSPARENT + WS_EX_LAYERED */
} OvConfig;

/* Callback invocado desde el hilo nativo cuando ocurre un hotkey */
typedef void (*OvHotkeyCallback)(int hotkey_id, void* user_data);

/* Ciclo de vida */
OV_API int ov_init(const OvConfig* cfg);
OV_API void ov_shutdown(void);

/* Control de ventana y renderizado */
OV_API int ov_set_visible(int visible);
OV_API int ov_set_text(const char* utf8_text, int state_code);

/* Registro de atajos globales */
OV_API int ov_register_hotkey_callback(OvHotkeyCallback cb, void* user_data);
OV_API int ov_register_hotkey(int hotkey_id, unsigned int modifiers, unsigned int virtual_key);
OV_API int ov_unregister_hotkey(int hotkey_id);
OV_API int ov_get_last_win32_error(void);

/* Captura de region de pantalla en formato BGRA raw */
OV_API int ov_capture_region(
    int x,
    int y,
    int width,
    int height,
    uint8_t* out_bgra,
    int max_bytes,
    int* out_written_bytes
);

#ifdef __cplusplus
}
#endif

#endif /* GHOST_OVERLAY_API_H */
