#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdint.h>

/* Register and dispatch hotkeys on the overlay's owning message-loop thread. */
int32_t overlay_register_hotkey(int32_t id, uint32_t modifiers, uint32_t virtual_key) {
    return RegisterHotKey(NULL, id, modifiers, virtual_key) ? 0 : (int32_t)GetLastError();
}
int32_t overlay_unregister_hotkey(int32_t id) {
    return UnregisterHotKey(NULL, id) ? 0 : (int32_t)GetLastError();
}
/* WM_HOTKEY dispatch is intentionally exposed as a small event hook for integration. */
int32_t overlay_hotkey_event_id(WPARAM wparam) { return (int32_t)wparam; }
