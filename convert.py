import ctypes
from ctypes.wintypes import LPCSTR, UINT
import os

dll = ctypes.WinDLL(os.getcwd()+"\\"+"a1800.dll")
decproto = ctypes.WINFUNCTYPE(ctypes.c_uint, LPCSTR, LPCSTR, ctypes.POINTER(UINT), UINT, UINT)
decparamflags = ((1, 'infile'), (1, 'outfile'), (2, 'fp'), (1, 'unk1', 16000), (1, 'unk2', 0))
decfunc = decproto(('dec', dll), decparamflags)

os.makedirs('wavs', exist_ok=True)

files = os.listdir('a18_files')

for f in files:
    inpath = os.path.join('a18_files', f)
    basename, _ = os.path.splitext(f)
    outpath = os.path.join('wavs', basename + '.wav')
    print(f"Converting {f} -> {basename}.wav")
    decfunc(infile=LPCSTR(inpath.encode('ascii')), outfile=LPCSTR(outpath.encode('ascii')))

print("Converted successfully!")
