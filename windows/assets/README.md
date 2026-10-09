# Windows icon asset

`chip.ico` is generated from the repository's original `docs/face-ok.png` (upstream MIT artwork), not from an uploaded screenshot.
It contains transparent PNG frames at 16, 24, 32, 48, 64, 128 and 256 pixels.

Regenerate on Windows with `windows/build_icon.ps1`. The same ICO is used by Tk windows, the native notification-area icon,
and the GUI/backend EXE resources. It is checked in so building does not require an extra image library.
