"""Windows ICO structure and native icon loading, without model or account access."""
import ctypes
from ctypes import wintypes
import os
from pathlib import Path
import struct
import unittest

ROOT=Path(__file__).resolve().parents[1]
ICON=ROOT/'windows/assets/chip.ico'

class IconTests(unittest.TestCase):
    def test_multiresolution_transparent_png_frames(self):
        data=ICON.read_bytes()
        reserved,kind,count=struct.unpack_from('<HHH',data)
        self.assertEqual((reserved,kind,count),(0,1,7))
        sizes=[]
        for i in range(count):
            width,height,colors,reserved,planes,bits,length,offset=struct.unpack_from('<BBBBHHII',data,6+16*i)
            width=width or 256; height=height or 256
            self.assertEqual((planes,bits),(1,32))
            frame=data[offset:offset+length]
            self.assertEqual(len(frame),length)
            self.assertTrue(frame.startswith(b'\x89PNG\r\n\x1a\n'))
            self.assertEqual(struct.unpack_from('>II',frame,16),(width,height))
            self.assertEqual(frame[25],6,'PNG must retain RGBA transparency')
            sizes.append(width)
        self.assertEqual(sizes,[16,24,32,48,64,128,256])

    @unittest.skipUnless(os.name=='nt','Native Windows icon loader')
    def test_native_windows_loads_each_size(self):
        user=ctypes.WinDLL('user32',use_last_error=True)
        user.LoadImageW.argtypes=[wintypes.HINSTANCE,wintypes.LPCWSTR,wintypes.UINT,ctypes.c_int,ctypes.c_int,wintypes.UINT]
        user.LoadImageW.restype=wintypes.HICON
        user.DestroyIcon.argtypes=[wintypes.HICON]
        for size in (16,24,32,48,64,128,256):
            icon=user.LoadImageW(None,str(ICON),1,size,size,0x10)
            self.assertTrue(icon,(size,ctypes.get_last_error()))
            self.assertTrue(user.DestroyIcon(icon))

if __name__=='__main__':unittest.main()
