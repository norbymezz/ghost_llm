cmake_minimum_required(VERSION 3.16)
project(ghost_overlay LANGUAGES C)

set(CMAKE_C_STANDARD 11)
set(CMAKE_C_STANDARD_REQUIRED ON)

add_library(overlay SHARED
    src/window_win32.c
    src/hotkeys.c
    src/capture.c
)

target_include_directories(overlay
    PUBLIC
        ${CMAKE_CURRENT_SOURCE_DIR}/include
)

target_compile_definitions(overlay
    PRIVATE
        OVERLAY_EXPORTS
        UNICODE
        _UNICODE
)

if(WIN32)
    target_link_libraries(overlay
        PRIVATE
            user32
            gdi32
    )
endif()
