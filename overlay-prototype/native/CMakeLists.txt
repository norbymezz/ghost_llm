cmake_minimum_required(VERSION 3.20)
project(overlay_prototype C)

if(NOT WIN32)
  message(FATAL_ERROR "overlay-prototype requires Windows/Win32")
endif()

add_library(overlay SHARED src/window_win32.c src/hotkeys.c src/capture.c)
target_compile_definitions(overlay PRIVATE OVERLAY_BUILD UNICODE _UNICODE WIN32_LEAN_AND_MEAN)
target_include_directories(overlay PUBLIC include)
target_link_libraries(overlay PRIVATE user32 gdi32 dwmapi)
set_target_properties(overlay PROPERTIES C_STANDARD 11 C_STANDARD_REQUIRED YES)
