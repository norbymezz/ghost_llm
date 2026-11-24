#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <dwmapi.h>
#include <stdlib.h>
#include <string.h>
#include "../include/overlay_api.h"

#ifndef WDA_EXCLUDEFROMCAPTURE
#define WDA_EXCLUDEFROMCAPTURE 0x00000011
#endif

static HWND g_window;
static HANDLE g_thread;
static DWORD g_thread_id;
static volatile LONG g_running;
static char *g_text;

static LRESULT CALLBACK overlay_wndproc(HWND hwnd, UINT msg, WPARAM wp, LPARAM lp) {
    switch (msg) {
    case WM_PAINT: {
        PAINTSTRUCT ps;
        HDC dc = BeginPaint(hwnd, &ps);
        RECT rc; GetClientRect(hwnd, &rc);
        SetBkMode(dc, TRANSPARENT);
        SetTextColor(dc, RGB(255, 255, 255));
        DrawTextA(dc, g_text ? g_text : "", -1, &rc, DT_LEFT | DT_TOP | DT_WORDBREAK);
        EndPaint(hwnd, &ps);
        return 0;
    }
    case WM_DESTROY: PostQuitMessage(0); return 0;
    }
    return DefWindowProcW(hwnd, msg, wp, lp);
}

static DWORD WINAPI overlay_thread(void *unused) {
    (void)unused;
    WNDCLASSW wc = {0};
    wc.lpfnWndProc = overlay_wndproc;
    wc.hInstance = GetModuleHandleW(NULL);
    wc.lpszClassName = L"GhostOverlayPrototype";
    RegisterClassW(&wc);
    g_window = CreateWindowExW(WS_EX_TOPMOST | WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_TOOLWINDOW,
        wc.lpszClassName, L"", WS_POPUP, 100, 100, 640, 240, NULL, NULL, wc.hInstance, NULL);
    if (g_window) {
        SetLayeredWindowAttributes(g_window, 0, 230, LWA_ALPHA);
        SetWindowDisplayAffinity(g_window, WDA_EXCLUDEFROMCAPTURE);
        ShowWindow(g_window, SW_SHOW);
        MSG msg;
        while (GetMessageW(&msg, NULL, 0, 0) > 0) { TranslateMessage(&msg); DispatchMessageW(&msg); }
    }
    InterlockedExchange(&g_running, 0);
    return 0;
}

int32_t overlay_initialize(const OverlayConfig *config) {
    (void)config;
    if (InterlockedCompareExchange(&g_running, 1, 0) != 0) return 0;
    g_thread = CreateThread(NULL, 0, overlay_thread, NULL, 0, &g_thread_id);
    if (!g_thread) { InterlockedExchange(&g_running, 0); return -1; }
    return 0;
}
int32_t overlay_set_text(const char *text) {
    if (!text) return -1;
    size_t n = strlen(text) + 1;
    char *copy = (char *)malloc(n);
    if (!copy) return -2;
    memcpy(copy, text, n);
    char *old = g_text; g_text = copy; free(old);
    if (g_window) InvalidateRect(g_window, NULL, TRUE);
    return 0;
}
int32_t overlay_set_visible(int32_t visible) {
    if (!g_window) return -1;
    ShowWindow(g_window, visible ? SW_SHOW : SW_HIDE);
    return 0;
}
int32_t overlay_shutdown(void) {
    if (g_window) PostMessageW(g_window, WM_CLOSE, 0, 0);
    if (g_thread) { WaitForSingleObject(g_thread, 3000); CloseHandle(g_thread); g_thread = NULL; }
    free(g_text); g_text = NULL; g_window = NULL;
    return 0;
}
