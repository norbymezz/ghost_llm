#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define OVERLAY_EXPORTS
#include "overlay_api.h"

#ifndef WDA_EXCLUDEFROMCAPTURE
#define WDA_EXCLUDEFROMCAPTURE 0x00000011
#endif

#define WM_OV_SET_VISIBLE (WM_APP + 1)
#define WM_OV_REDRAW_TEXT (WM_APP + 2)
#define WM_OV_SHUTDOWN    (WM_APP + 3)

#define MAX_TEXT_BYTES (64 * 1024)

typedef struct {
    HWND hwnd;
    HANDLE thread;
    HANDLE ready_event;
    DWORD thread_id;
    volatile LONG initialized;
    volatile LONG shutting_down;

    CRITICAL_SECTION text_lock;
    char text_utf8[MAX_TEXT_BYTES];
    int state_code;

    OvConfig cfg;
} OverlayContext;

static OverlayContext g_ov = {0};

static const char* state_to_label(int state_code) {
    switch (state_code) {
        case OV_STATE_CAPTURING: return "[CAPTURING]";
        case OV_STATE_THINKING:  return "[THINKING]";
        case OV_STATE_STREAMING: return "[STREAMING]";
        case OV_STATE_ERROR:     return "[ERROR]";
        case OV_STATE_IDLE:
        default:                 return "[IDLE]";
    }
}

static void paint_overlay(HWND hwnd, HDC hdc) {
    RECT rc;
    GetClientRect(hwnd, &rc);

    HBRUSH bg_brush = CreateSolidBrush(RGB(18, 20, 26));
    FillRect(hdc, &rc, bg_brush);
    DeleteObject(bg_brush);

    HPEN border_pen = CreatePen(PS_SOLID, 1, RGB(60, 72, 92));
    HPEN old_pen = (HPEN)SelectObject(hdc, border_pen);
    HBRUSH old_brush = (HBRUSH)SelectObject(hdc, GetStockObject(HOLLOW_BRUSH));
    Rectangle(hdc, rc.left, rc.top, rc.right, rc.bottom);
    SelectObject(hdc, old_brush);
    SelectObject(hdc, old_pen);
    DeleteObject(border_pen);

    char local_copy[MAX_TEXT_BYTES];
    int local_state = OV_STATE_IDLE;

    EnterCriticalSection(&g_ov.text_lock);
    memcpy(local_copy, g_ov.text_utf8, sizeof(local_copy));
    local_state = g_ov.state_code;
    LeaveCriticalSection(&g_ov.text_lock);

    wchar_t wide_buf[MAX_TEXT_BYTES];
    int wide_len = MultiByteToWideChar(CP_UTF8, 0, local_copy, -1, wide_buf, MAX_TEXT_BYTES);
    if (wide_len <= 0) {
        wcscpy_s(wide_buf, MAX_TEXT_BYTES, L"(UTF-8 decode error)");
    }

    char header_utf8[128];
    snprintf(header_utf8, sizeof(header_utf8), "GhostOverlay %s", state_to_label(local_state));
    wchar_t wide_header[128];
    MultiByteToWideChar(CP_UTF8, 0, header_utf8, -1, wide_header, 128);

    SetBkMode(hdc, TRANSPARENT);

    HFONT font = CreateFontW(
        -16, 0, 0, 0, FW_NORMAL, FALSE, FALSE, FALSE,
        DEFAULT_CHARSET, OUT_DEFAULT_PRECIS, CLIP_DEFAULT_PRECIS,
        CLEARTYPE_QUALITY, FIXED_PITCH | FF_MODERN, L"Consolas"
    );
    HFONT old_font = (HFONT)SelectObject(hdc, font);

    RECT header_rc = { rc.left + 12, rc.top + 8, rc.right - 12, rc.top + 30 };
    SetTextColor(hdc, RGB(120, 190, 255));
    DrawTextW(hdc, wide_header, -1, &header_rc, DT_LEFT | DT_SINGLELINE | DT_NOPREFIX);

    RECT body_rc = { rc.left + 12, rc.top + 34, rc.right - 12, rc.bottom - 12 };
    SetTextColor(hdc, RGB(230, 235, 242));
    DrawTextW(hdc, wide_buf, -1, &body_rc, DT_LEFT | DT_TOP | DT_WORDBREAK | DT_EDITCONTROL | DT_NOPREFIX);

    SelectObject(hdc, old_font);
    DeleteObject(font);
}

static LRESULT CALLBACK overlay_wnd_proc(HWND hwnd, UINT msg, WPARAM wparam, LPARAM lparam) {
    switch (msg) {
        case WM_NCHITTEST: {
            if (g_ov.cfg.click_through) {
                return HTTRANSPARENT;
            }
            return DefWindowProcW(hwnd, msg, wparam, lparam);
        }

        case WM_PAINT: {
            PAINTSTRUCT ps;
            HDC hdc = BeginPaint(hwnd, &ps);

            RECT rc;
            GetClientRect(hwnd, &rc);
            int w = rc.right - rc.left;
            int h = rc.bottom - rc.top;

            if (w > 0 && h > 0) {
                HDC mem_dc = CreateCompatibleDC(hdc);
                HBITMAP mem_bm = CreateCompatibleBitmap(hdc, w, h);
                HBITMAP old_bm = (HBITMAP)SelectObject(mem_dc, mem_bm);

                paint_overlay(hwnd, mem_dc);
                BitBlt(hdc, 0, 0, w, h, mem_dc, 0, 0, SRCCOPY);

                SelectObject(mem_dc, old_bm);
                DeleteObject(mem_bm);
                DeleteDC(mem_dc);
            }

            EndPaint(hwnd, &ps);
            return 0;
        }

        case WM_OV_SET_VISIBLE: {
            int show = (int)wparam;
            ShowWindow(hwnd, show ? SW_SHOWNOACTIVATE : SW_HIDE);
            return 0;
        }

        case WM_OV_REDRAW_TEXT: {
            InvalidateRect(hwnd, NULL, FALSE);
            return 0;
        }

        case WM_OV_SHUTDOWN: {
            DestroyWindow(hwnd);
            return 0;
        }

        case WM_DESTROY: {
            PostQuitMessage(0);
            return 0;
        }

        default:
            return DefWindowProcW(hwnd, msg, wparam, lparam);
    }
}

static DWORD WINAPI overlay_thread_main(LPVOID param) {
    (void)param;

    HINSTANCE hinst = GetModuleHandleW(NULL);
    const wchar_t* class_name = L"GhostOverlayWindowClass";

    WNDCLASSEXW wc = {0};
    wc.cbSize = sizeof(wc);
    wc.lpfnWndProc = overlay_wnd_proc;
    wc.hInstance = hinst;
    wc.lpszClassName = class_name;
    wc.hCursor = LoadCursorW(NULL, IDC_ARROW);

    if (!RegisterClassExW(&wc) && GetLastError() != ERROR_CLASS_ALREADY_EXISTS) {
        SetEvent(g_ov.ready_event);
        return 1;
    }

    DWORD ex_style = WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE;
    if (g_ov.cfg.topmost) {
        ex_style |= WS_EX_TOPMOST;
    }
    if (g_ov.cfg.click_through) {
        ex_style |= WS_EX_LAYERED | WS_EX_TRANSPARENT;
    }

    int width = g_ov.cfg.width > 0 ? g_ov.cfg.width : 520;
    int height = g_ov.cfg.height > 0 ? g_ov.cfg.height : 240;

    HWND hwnd = CreateWindowExW(
        ex_style,
        class_name,
        L"GhostOverlay",
        WS_POPUP,
        g_ov.cfg.x,
        g_ov.cfg.y,
        width,
        height,
        NULL,
        NULL,
        hinst,
        NULL
    );

    if (!hwnd) {
        SetEvent(g_ov.ready_event);
        return 1;
    }

    if (g_ov.cfg.exclude_from_capture) {
        SetWindowDisplayAffinity(hwnd, WDA_EXCLUDEFROMCAPTURE);
    }

    g_ov.hwnd = hwnd;
    InterlockedExchange(&g_ov.initialized, 1);
    SetEvent(g_ov.ready_event);

    MSG msg;
    while (GetMessageW(&msg, NULL, 0, 0) > 0) {
        TranslateMessage(&msg);
        DispatchMessageW(&msg);
    }

    g_ov.hwnd = NULL;
    InterlockedExchange(&g_ov.initialized, 0);
    return 0;
}

int ov_init(const OvConfig* cfg) {
    if (!cfg) {
        return OV_ERR_INVALID_ARG;
    }
    if (InterlockedCompareExchange(&g_ov.initialized, 0, 0) == 1) {
        return OV_OK;
    }

    memset(&g_ov, 0, sizeof(g_ov));
    g_ov.cfg = *cfg;
    g_ov.state_code = OV_STATE_IDLE;
    snprintf(g_ov.text_utf8, sizeof(g_ov.text_utf8), "Ventana lista. Esperando eventos...");

    InitializeCriticalSection(&g_ov.text_lock);

    g_ov.ready_event = CreateEventW(NULL, TRUE, FALSE, NULL);
    if (!g_ov.ready_event) {
        DeleteCriticalSection(&g_ov.text_lock);
        return OV_ERR_INIT_FAILED;
    }

    g_ov.thread = CreateThread(NULL, 0, overlay_thread_main, NULL, 0, &g_ov.thread_id);
    if (!g_ov.thread) {
        CloseHandle(g_ov.ready_event);
        DeleteCriticalSection(&g_ov.text_lock);
        return OV_ERR_INIT_FAILED;
    }

    WaitForSingleObject(g_ov.ready_event, 5000);
    CloseHandle(g_ov.ready_event);
    g_ov.ready_event = NULL;

    if (!g_ov.hwnd || InterlockedCompareExchange(&g_ov.initialized, 0, 0) != 1) {
        ov_shutdown();
        return OV_ERR_INIT_FAILED;
    }

    return OV_OK;
}

void ov_shutdown(void) {
    if (InterlockedExchange(&g_ov.shutting_down, 1) == 1 && !g_ov.thread) {
        return;
    }

    if (g_ov.hwnd && g_ov.thread_id != 0) {
        PostMessageW(g_ov.hwnd, WM_OV_SHUTDOWN, 0, 0);
    }

    if (g_ov.thread) {
        WaitForSingleObject(g_ov.thread, 5000);
        CloseHandle(g_ov.thread);
        g_ov.thread = NULL;
    }

    if (g_ov.ready_event) {
        CloseHandle(g_ov.ready_event);
        g_ov.ready_event = NULL;
    }

    DeleteCriticalSection(&g_ov.text_lock);
    memset(&g_ov, 0, sizeof(g_ov));
}

int ov_set_visible(int visible) {
    if (InterlockedCompareExchange(&g_ov.initialized, 0, 0) != 1 || !g_ov.hwnd) {
        return OV_ERR_NOT_INITIALIZED;
    }
    PostMessageW(g_ov.hwnd, WM_OV_SET_VISIBLE, (WPARAM)(visible ? 1 : 0), 0);
    return OV_OK;
}

int ov_set_text(const char* utf8_text, int state_code) {
    if (!utf8_text) {
        return OV_ERR_INVALID_ARG;
    }
    if (InterlockedCompareExchange(&g_ov.initialized, 0, 0) != 1 || !g_ov.hwnd) {
        return OV_ERR_NOT_INITIALIZED;
    }

    EnterCriticalSection(&g_ov.text_lock);
    size_t len = strlen(utf8_text);
    if (len >= MAX_TEXT_BYTES) {
        len = MAX_TEXT_BYTES - 1;
    }
    memcpy(g_ov.text_utf8, utf8_text, len);
    g_ov.text_utf8[len] = '\0';
    g_ov.state_code = state_code;
    LeaveCriticalSection(&g_ov.text_lock);

    PostMessageW(g_ov.hwnd, WM_OV_REDRAW_TEXT, 0, 0);
    return OV_OK;
}
