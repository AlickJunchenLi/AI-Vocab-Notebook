@echo off
setlocal EnableDelayedExpansion

if not exist out mkdir out

set "SOURCES="
for %%f in (c++-file\source-files\*.cpp) do (
    set "FILE=%CD%\%%f"
    set "FILE=!FILE:\=/!"
    set "SOURCES=!SOURCES! !FILE!"
)


if not defined SOURCES (
    echo No source files found under c++-file\source-files.
    exit /b 1
)

g++ -std=c++20 -Wall -Wextra -O2 -g ^
  -I "c++-file\header-files" ^
  !SOURCES! ^
  -o out\app.exe

endlocal
