"""Minimal Windows notification-area icon using only the standard library."""
import ctypes as c
from ctypes import wintypes as w
import os
import threading
from pathlib import Path

class Tray:
    def __init__(self, callback, labels, icon_path):
        self.callback, self.labels = callback, labels
        self.icon_path = Path(icon_path).resolve()
        self.icon_handle = None
        if not self.icon_path.is_file():
            raise FileNotFoundError(self.icon_path)
        self.ready = threading.Event()
        self.hwnd = None
        self.error = None
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        if not self.ready.wait(5) or self.error:
            raise RuntimeError(str(self.error or 'Tray startup timed out'))

    def close(self):
        if self.hwnd:
            self.user.PostMessageW(self.hwnd, 0x10, 0, 0)
            self.thread.join(timeout=3)

    def _run(self):
        try:
            self._loop()
        except Exception as exc:
            self.error = exc
            self.ready.set()

    def _loop(self):
        user = self.user = c.WinDLL('user32', use_last_error=True)
        shell = c.WinDLL('shell32', use_last_error=True)
        kernel = c.WinDLL('kernel32', use_last_error=True)
        LRESULT = c.c_ssize_t
        PROC = c.WINFUNCTYPE(LRESULT, w.HWND, w.UINT, w.WPARAM, w.LPARAM)
        class WNDCLASS(c.Structure):
            _fields_ = [('style',w.UINT),('proc',PROC),('cls',c.c_int),('wnd',c.c_int),('instance',w.HINSTANCE),('icon',w.HICON),('cursor',w.HANDLE),('brush',w.HBRUSH),('menu',w.LPCWSTR),('name',w.LPCWSTR)]
        class GUID(c.Structure):
            _fields_ = [('a',w.DWORD),('b',w.WORD),('c',w.WORD),('d',c.c_byte*8)]
        class NOTIFY(c.Structure):
            _fields_ = [('size',w.DWORD),('hwnd',w.HWND),('id',w.UINT),('flags',w.UINT),('message',w.UINT),('icon',w.HICON),('tip',w.WCHAR*128),('state',w.DWORD),('mask',w.DWORD),('info',w.WCHAR*256),('timeout',w.UINT),('title',w.WCHAR*64),('infoflags',w.DWORD),('guid',GUID),('balloon',w.HICON)]
        kernel.GetModuleHandleW.argtypes=[w.LPCWSTR]; kernel.GetModuleHandleW.restype=w.HMODULE
        user.RegisterClassW.argtypes=[c.POINTER(WNDCLASS)]; user.RegisterClassW.restype=w.ATOM
        user.CreateWindowExW.argtypes=[w.DWORD,w.LPCWSTR,w.LPCWSTR,w.DWORD,c.c_int,c.c_int,c.c_int,c.c_int,w.HWND,w.HMENU,w.HINSTANCE,c.c_void_p]; user.CreateWindowExW.restype=w.HWND
        user.DefWindowProcW.argtypes=[w.HWND,w.UINT,w.WPARAM,w.LPARAM]; user.DefWindowProcW.restype=LRESULT
        user.PostMessageW.argtypes=[w.HWND,w.UINT,w.WPARAM,w.LPARAM]
        user.DestroyWindow.argtypes=[w.HWND]
        user.SetForegroundWindow.argtypes=[w.HWND]
        user.LoadImageW.argtypes=[w.HINSTANCE,w.LPCWSTR,w.UINT,c.c_int,c.c_int,w.UINT]
        user.LoadImageW.restype=w.HICON
        user.DestroyIcon.argtypes=[w.HICON]
        user.GetSystemMetrics.argtypes=[c.c_int]; user.GetSystemMetrics.restype=c.c_int
        user.CreatePopupMenu.restype=w.HMENU
        user.AppendMenuW.argtypes=[w.HMENU,w.UINT,c.c_size_t,w.LPCWSTR]
        user.TrackPopupMenu.argtypes=[w.HMENU,w.UINT,c.c_int,c.c_int,c.c_int,w.HWND,c.c_void_p]; user.TrackPopupMenu.restype=w.UINT
        user.DestroyMenu.argtypes=[w.HMENU]
        user.GetCursorPos.argtypes=[c.POINTER(w.POINT)]
        user.GetMessageW.argtypes=[c.POINTER(w.MSG),w.HWND,w.UINT,w.UINT]
        user.TranslateMessage.argtypes=[c.POINTER(w.MSG)]
        user.DispatchMessageW.argtypes=[c.POINTER(w.MSG)]; user.DispatchMessageW.restype=LRESULT
        user.UnregisterClassW.argtypes=[w.LPCWSTR,w.HINSTANCE]
        shell.Shell_NotifyIconW.argtypes=[w.DWORD,c.POINTER(NOTIFY)]
        notification = NOTIFY()
        callback_msg = 0x8001
        taskbar_created = user.RegisterWindowMessageW('TaskbarCreated')
        def proc(hwnd, msg, wp, lp):
            if msg == taskbar_created:
                shell.Shell_NotifyIconW(0,c.byref(notification))
            elif msg == callback_msg:
                if lp in (0x202,0x203):
                    self.callback('open')
                elif lp == 0x205:
                    menu = user.CreatePopupMenu()
                    try:
                        for i,label in enumerate(self.labels(),1):
                            user.AppendMenuW(menu,0,i,label)
                        point=w.POINT(); user.GetCursorPos(c.byref(point)); user.SetForegroundWindow(hwnd)
                        choice=user.TrackPopupMenu(menu,0x100|2,point.x,point.y,0,hwnd,None)
                        if choice in (1,2,3): self.callback(('open','settings','quit')[choice-1])
                        user.PostMessageW(hwnd,0,0,0)
                    finally: user.DestroyMenu(menu)
                return 0
            elif msg == 0x10:
                shell.Shell_NotifyIconW(2,c.byref(notification))
                user.DestroyWindow(hwnd)
                return 0
            elif msg == 2:
                user.PostQuitMessage(0)
                return 0
            return user.DefWindowProcW(hwnd,msg,wp,lp)
        self.proc = PROC(proc)
        instance=kernel.GetModuleHandleW(None)
        name=f'IsGPTNerfedTray{os.getpid()}-{id(self)}'
        self.icon_handle=user.LoadImageW(None,str(self.icon_path),1,user.GetSystemMetrics(49),user.GetSystemMetrics(50),0x10)
        if not self.icon_handle: raise c.WinError(c.get_last_error())
        cls=WNDCLASS(); cls.proc=self.proc; cls.instance=instance; cls.name=name; cls.icon=self.icon_handle
        if not user.RegisterClassW(c.byref(cls)):
            error=c.get_last_error()
            user.DestroyIcon(self.icon_handle); self.icon_handle=None
            raise c.WinError(error)
        try:
            self.hwnd=user.CreateWindowExW(0,name,name,0,0,0,0,0,None,None,instance,None)
            if not self.hwnd: raise c.WinError(c.get_last_error())
            notification.size=c.sizeof(NOTIFY); notification.hwnd=self.hwnd; notification.id=1
            notification.flags=1|2|4; notification.message=callback_msg
            notification.icon=self.icon_handle; notification.tip='Is GPT nerfed?'
            if not shell.Shell_NotifyIconW(0,c.byref(notification)): raise RuntimeError('Shell_NotifyIcon failed')
            self.ready.set()
            msg=w.MSG()
            while user.GetMessageW(c.byref(msg),None,0,0)>0:
                user.TranslateMessage(c.byref(msg)); user.DispatchMessageW(c.byref(msg))
        finally:
            if self.hwnd:
                shell.Shell_NotifyIconW(2,c.byref(notification))
                user.DestroyWindow(self.hwnd)
                self.hwnd=None
            user.UnregisterClassW(name,instance)
            if self.icon_handle:
                user.DestroyIcon(self.icon_handle)
                self.icon_handle=None
