#ifndef GHOST_OVERLAY_INTERNAL_H
#define GHOST_OVERLAY_INTERNAL_H

#define WIN32_LEAN_AND_MEAN
#include <windows.h>

HWND ov_internal_get_hwnd(void);
DWORD ov_internal_get_thread_id(void);
int ov_internal_is_initialized(void);
void ov_internal_dispatch_hotkey(int hotkey_id);
void ov_internal_unregister_all_hotkeys(void);
#define WM_OV_REGISTER_HOTKEY (WM_APP + 10)
#define WM_OV_UNREGISTER_HOTKEY (WM_APP + 11)

#endif
