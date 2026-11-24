#define WIN32_LEAN_AND_MEAN
#include <windows.h>

#define OVERLAY_EXPORTS
#include "overlay_api.h"

int ov_register_hotkey_callback(OvHotkeyCallback cb, void* user_data) {
    (void)cb;
    (void)user_data;
    return OV_OK;
}

int ov_register_hotkey(int hotkey_id, unsigned int modifiers, unsigned int virtual_key) {
    (void)hotkey_id;
    (void)modifiers;
    (void)virtual_key;
    return OV_OK;
}

int ov_unregister_hotkey(int hotkey_id) {
    (void)hotkey_id;
    return OV_OK;
}
