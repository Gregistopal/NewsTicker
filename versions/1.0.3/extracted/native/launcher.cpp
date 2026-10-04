#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <string>

int WINAPI wWinMain(HINSTANCE, HINSTANCE, PWSTR, int) {
    wchar_t module[32768];
    DWORD length = GetModuleFileNameW(nullptr, module, 32768);
    if (!length || length >= 32768) return 2;

    std::wstring base(module, length);
    auto slash = base.find_last_of(L"\\/");
    if (slash == std::wstring::npos) return 2;
    base.resize(slash + 1);

    std::wstring python = base + L"runtime\\pythonw.exe";
    std::wstring script = base + L"app\\server.py";
    if (GetFileAttributesW(python.c_str()) == INVALID_FILE_ATTRIBUTES ||
        GetFileAttributesW(script.c_str()) == INVALID_FILE_ATTRIBUTES) {
        MessageBoxW(nullptr,
            L"NewsTicker's runtime files are missing. Extract the complete ZIP before starting it.",
            L"NewsTicker", MB_OK | MB_ICONERROR);
        return 3;
    }

    std::wstring command = L"\"" + python + L"\" \"" + script + L"\"";
    STARTUPINFOW startup{};
    startup.cb = sizeof(startup);
    PROCESS_INFORMATION process{};
    if (!CreateProcessW(python.c_str(), command.data(), nullptr, nullptr, FALSE,
                        CREATE_NO_WINDOW, nullptr, base.c_str(), &startup, &process)) {
        MessageBoxW(nullptr,
            L"NewsTicker could not start. Run Start-Diagnostics.cmd for details.",
            L"NewsTicker", MB_OK | MB_ICONERROR);
        return 4;
    }
    CloseHandle(process.hThread);
    CloseHandle(process.hProcess);
    return 0;
}
