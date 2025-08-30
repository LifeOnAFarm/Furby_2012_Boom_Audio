import ctypes
from ctypes.wintypes import LPCSTR, UINT
import os
import wave

# Load the DLL
dll = ctypes.WinDLL(os.getcwd() + "\\" + "a1800.dll")

# Set up the encoding function
encproto = ctypes.WINFUNCTYPE(
    ctypes.c_uint,
    LPCSTR,                           # infile
    LPCSTR,                           # outfile  
    ctypes.c_uint,                    # buffer size
    ctypes.POINTER(ctypes.c_byte),    # buffer pointer
    ctypes.c_uint                     # mode (always 0)
)

encfunc = encproto(('enc', dll))

def get_wav_info(wav_path):
    """Get WAV file information"""
    try:
        with wave.open(wav_path, 'rb') as wav_file:
            frames = wav_file.getnframes()
            sample_rate = wav_file.getframerate()
            channels = wav_file.getnchannels()
            sample_width = wav_file.getsampwidth()
            total_samples = frames * channels
            return total_samples, sample_rate, channels, sample_width
    except Exception as e:
        print(f"Error reading WAV file {wav_path}: {e}")
        return None, None, None, None

def convert_wav_to_a18(wav_file, a18_file):
    """Convert WAV to A18"""
    abs_wav_path = os.path.abspath(wav_file)
    abs_a18_path = os.path.abspath(a18_file)
    
    # Read WAV data
    try:
        with open(abs_wav_path, 'rb') as f:
            wav_data = f.read()
    except Exception as e:
        print(f"Cannot read WAV file: {e}")
        return False
    
    total_samples, sample_rate, channels, sample_width = get_wav_info(abs_wav_path)
    if total_samples is None:
        return False
    
    # Use the magic buffer size
    buffer_size = 16000
    buffer = (ctypes.c_byte * buffer_size)()
    
    # Copy audio data (skip 44-byte WAV header)
    raw_audio_bytes = total_samples * sample_width
    if len(wav_data) > 44:
        audio_data = wav_data[44:44 + min(raw_audio_bytes, buffer_size)]
        for i, byte_val in enumerate(audio_data):
            buffer[i] = byte_val
    
    try:
        result = encfunc(
            LPCSTR(abs_wav_path.encode('ascii')),
            LPCSTR(abs_a18_path.encode('ascii')),
            buffer_size,
            buffer,
            0
        )
        
        if os.path.exists(abs_a18_path) and os.path.getsize(abs_a18_path) > 0:
            print(f"Converted: {os.path.basename(wav_file)}")
            return True
        else:
            print(f"Failed: {os.path.basename(wav_file)}")
            return False
            
    except Exception as e:
        print(f"Error converting {os.path.basename(wav_file)}: {e}")
        return False

# Main conversion
input_dir = 'convert_wavs'
output_dir = 'converted_a18'

if not os.path.exists(input_dir):
    print(f"Input directory '{input_dir}' not found!")
    exit(1)

os.makedirs(output_dir, exist_ok=True)

wav_files = [f for f in os.listdir(input_dir) if f.lower().endswith('.wav')]

if not wav_files:
    print(f"No WAV files found in '{input_dir}' directory!")
    exit(1)

print(f"Converting {len(wav_files)} WAV files to A18 format...")
print("-" * 50)

success_count = 0
for wav_file in wav_files:
    wav_path = os.path.join(input_dir, wav_file)
    basename = os.path.splitext(wav_file)[0]
    a18_path = os.path.join(output_dir, basename + '.a18')
    
    if convert_wav_to_a18(wav_path, a18_path):
        success_count += 1

print("-" * 50)
print(f"Conversion complete: {success_count}/{len(wav_files)} files converted successfully!")
print(f"Output files saved to: {output_dir}/")