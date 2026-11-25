#define WIN32_LEAN_AND_MEAN
#include <windows.h>

#define OVERLAY_EXPORTS
#include "overlay_api.h"
#include "internal.h"

#define MAX_HOTKEYS 32

typedef struct {
    int active;
    int hotkey_id;
    unsigned int modifiers;
    unsigned int virtual_key;
} HotkeyEntry;

static CRITICAL_SECTION g_hk_lock;
static volatile LONG g_hk_lock_ready = 0;
static HotkeyEntry g_hotkeys[MAX_HOTKEYS];
static OvHotkeyCallback g_callback = NULL;
static void* g_user_data = NULL;
static volatile LONG g_last_win32_error = ERROR_SUCCESS;
int ov_get_last_win32_error(void) {
    return (int)InterlockedCompareExchange(&g_last_win32_error, 0, 0);
}

static void ensure_lock(void) {
    if (InterlockedCompareExchange(&g_hk_lock_ready, 0, 0) == 0) {
        InitializeCriticalSection(&g_hk_lock);
        if (InterlockedCompareExchange(&g_hk_lock_ready, 1, 0) != 0) {
            DeleteCriticalSection(&g_hk_lock);
        }
    }
}

void ov_internal_dispatch_hotkey(int hotkey_id) {
    ensure_lock();
    EnterCriticalSection(&g_hk_lock);
    OvHotkeyCallback cb = g_callback;
    void* ud = g_user_data;
    LeaveCriticalSection(&g_hk_lock);

    if (cb) {
        /* Mantener el callback liviano; el lado Python debe encolar y volver rápido */
        cb(hotkey_id, ud);
    }
}

int ov_register_hotkey_callback(OvHotkeyCallback cb, void* user_data) {
    ensure_lock();
    EnterCriticalSection(&g_hk_lock);
    g_callback = cb;
    g_user_data = user_data;
    LeaveCriticalSection(&g_hk_lock);
    return OV_OK;
}

int ov_register_hotkey(int hotkey_id, unsigned int modifiers, unsigned int virtual_key) {
    if (hotkey_id <= 0 || virtual_key == 0) {
        return OV_ERR_INVALID_ARG;
    }
    if (!ov_internal_is_initialized()) {
        return OV_ERR_NOT_INITIALIZED;
    }

    ensure_lock();
    HWND hwnd = ov_internal_get_hwnd();
    if (!hwnd) {
        return OV_ERR_NOT_INITIALIZED;
    }

    /*
     * RegisterHotKey funciona sobre el HWND indicado; para asegurar que el
     * registro ocurra en el hilo dueno del HWND, enviamos un mensaje sincronizado
     * o registramos directamente si ya estamos en ese hilo.
     */
    if (GetCurrentThreadId() != ov_internal_get_thread_id()) {
        /* Uso directo si el hilo actual ya atiende su cola, o via SendMessage */
        LRESULT result = SendMessageW(
            hwnd,
            WM_OV_REGISTER_HOTKEY,
            (WPARAM)hotkey_id,
            MAKELPARAM(modifiers, virtual_key)
        );

        if (result != 1) {
            DWORD win_error = result > 1
                ? (DWORD)(result - 1)
                : ERROR_GEN_FAILURE;

            InterlockedExchange(&g_last_win32_error, (LONG)win_error);
            return OV_ERR_INIT_FAILED;
        }

    } else {
        if (!RegisterHotKey(hwnd, hotkey_id, modifiers, virtual_key)) {
            DWORD win_error = GetLastError();
            InterlockedExchange(&g_last_win32_error, (LONG)win_error);
            return OV_ERR_INIT_FAILED;
        }
    }

    EnterCriticalSection(&g_hk_lock);
    int slot = -1;
    for (int i = 0; i < MAX_HOTKEYS; ++i) {
        if (g_hotkeys[i].active && g_hotkeys[i].hotkey_id == hotkey_id) {
            slot = i;
            break;
        }
        if (slot == -1 && !g_hotkeys[i].active) {
            slot = i;
        }
    }
    if (slot != -1) {
        g_hotkeys[slot].active = 1;
        g_hotkeys[slot].hotkey_id = hotkey_id;
        g_hotkeys[slot].modifiers = modifiers;
        g_hotkeys[slot].virtual_key = virtual_key;
    }
    LeaveCriticalSection(&g_hk_lock);

    return OV_OK;
}

int ov_unregister_hotkey(int hotkey_id) {
    if (hotkey_id <= 0) {
        return OV_ERR_INVALID_ARG;
    }
    HWND hwnd = ov_internal_get_hwnd();
    if (!hwnd) {
        return OV_ERR_NOT_INITIALIZED;
    }

    LRESULT result = SendMessageW(
        hwnd,
        WM_OV_UNREGISTER_HOTKEY,
        (WPARAM)hotkey_id,
        0
    );

    if (result != 1) {
        return OV_ERR_INIT_FAILED;
    }

    ensure_lock();
    EnterCriticalSection(&g_hk_lock);
    for (int i = 0; i < MAX_HOTKEYS; ++i) {
        if (g_hotkeys[i].active && g_hotkeys[i].hotkey_id == hotkey_id) {
            g_hotkeys[i].active = 0;
        }
    }
    LeaveCriticalSection(&g_hk_lock);

    return OV_OK;
}

void ov_internal_unregister_all_hotkeys(void) {
    HWND hwnd = ov_internal_get_hwnd();

    ensure_lock();
    EnterCriticalSection(&g_hk_lock);

    for (int i = 0; i < MAX_HOTKEYS; ++i) {
        if (g_hotkeys[i].active) {
            if (hwnd) {
                SendMessageW(
                    hwnd,
                    WM_OV_UNREGISTER_HOTKEY,
                    (WPARAM)g_hotkeys[i].hotkey_id,
                    0
                );
            }
            g_hotkeys[i].active = 0;
            g_hotkeys[i].hotkey_id = 0;
            g_hotkeys[i].modifiers = 0;
            g_hotkeys[i].virtual_key = 0;
        }
    }

    g_callback = NULL;
    g_user_data = NULL;

    LeaveCriticalSection(&g_hk_lock);
}
