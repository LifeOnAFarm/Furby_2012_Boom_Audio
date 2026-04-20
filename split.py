#!/usr/bin/env python3
"""
Furby ROM Extractor & A18 Converter GUI v1.0
Extract audio tracks and images from Furby ROM dumps and convert A18 files to WAV
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import os
import struct
import threading
import queue
from PIL import Image
import ctypes
from ctypes.wintypes import LPCSTR, UINT

class FurbyExtractorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Furby ROM Extractor & A18 Converter v1.0")
        self.root.geometry("900x750")
        self.root.resizable(True, True)
        
        # Variables
        self.rom_file = tk.StringVar()
        self.dll_file = tk.StringVar()
        self.output_dir = tk.StringVar(value=os.getcwd())
        self.processing_active = False
        
        # Stats variables
        self.audio_count = tk.IntVar()
        self.image_count = tk.IntVar()
        self.wav_count = tk.IntVar()
        
        # Thread communication
        self.message_queue = queue.Queue()
        self.process_thread = None
        
        # Pixel mapping arrays for images
        self.x_offsets = [27, 26, 25, 24, 7, 6, 5, 4, 3, 2, 1, 0, 15, 14, 13, 12,
                         11, 10, 9, 8, 28, 29, 30, 31, 16, 17, 18, 19, 20, 21, 22,
                         23, 55, 54, 53, 52, 51, 50, 49, 48, 63, 62, 61, 60, 40, 41,
                         42, 43, 44, 45, 46, 47, 32, 33, 34, 35, 36, 37, 38, 39, 56,
                         57, 58, 59]
        self.y_offsets = [960, 896, 832, 768, 704, 640, 576, 512, 448, 384, 320, 256,
                         192, 128, 64, 0, 1024, 1088, 1152, 1216, 1280, 1344, 1408,
                         1472, 1536, 1600, 1664, 1728, 1792, 1856, 1920, 1984]
        
        self.setup_ui()
        self.check_messages()
        
    def setup_ui(self):
        """Setup the user interface"""
        # Main notebook for tabs
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill='both', expand=True, padx=10, pady=5)
        
        # Files tab
        files_frame = ttk.Frame(notebook)
        notebook.add(files_frame, text="Files & Settings")
        self.setup_files_tab(files_frame)
        
        # Processing tab
        process_frame = ttk.Frame(notebook)
        notebook.add(process_frame, text="Processing")
        self.setup_process_tab(process_frame)
        
        # Log tab
        log_frame = ttk.Frame(notebook)
        notebook.add(log_frame, text="Log")
        self.setup_log_tab(log_frame)
        
        # Status bar
        self.setup_status_bar()
        
    def setup_files_tab(self, parent):
        """Setup file selection and configuration tab"""
        # ROM File selection frame
        rom_frame = ttk.LabelFrame(parent, text="ROM File", padding=10)
        rom_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Label(rom_frame, text="ROM Binary File:").grid(row=0, column=0, sticky='w', padx=(0,5))
        ttk.Entry(rom_frame, textvariable=self.rom_file, width=60).grid(row=0, column=1, sticky='ew', padx=(0,5))
        ttk.Button(rom_frame, text="Browse", command=self.browse_rom_file).grid(row=0, column=2, padx=5)
        
        rom_frame.columnconfigure(1, weight=1)
        
        # DLL File selection frame
        dll_frame = ttk.LabelFrame(parent, text="A18 Converter DLL", padding=10)
        dll_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Label(dll_frame, text="a1800.dll File:").grid(row=0, column=0, sticky='w', padx=(0,5))
        ttk.Entry(dll_frame, textvariable=self.dll_file, width=60).grid(row=0, column=1, sticky='ew', padx=(0,5))
        ttk.Button(dll_frame, text="Browse", command=self.browse_dll_file).grid(row=0, column=2, padx=5)
        
        dll_frame.columnconfigure(1, weight=1)
        
        # Auto-detect DLL button
        ttk.Button(dll_frame, text="Auto-detect in current directory", 
                  command=self.auto_detect_dll).grid(row=1, column=1, pady=(5,0), sticky='w')
        
        # Output directory frame
        output_frame = ttk.LabelFrame(parent, text="Output Directory", padding=10)
        output_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Label(output_frame, text="Output Directory:").grid(row=0, column=0, sticky='w', padx=(0,5))
        ttk.Entry(output_frame, textvariable=self.output_dir, width=60).grid(row=0, column=1, sticky='ew', padx=(0,5))
        ttk.Button(output_frame, text="Browse", command=self.browse_output_dir).grid(row=0, column=2, padx=5)
        
        output_frame.columnconfigure(1, weight=1)
        
        # Processing Options frame
        options_frame = ttk.LabelFrame(parent, text="Processing Options", padding=10)
        options_frame.pack(fill='x', padx=10, pady=5)
        
        self.extract_audio = tk.BooleanVar(value=True)
        self.extract_images = tk.BooleanVar(value=True)
        self.convert_to_wav = tk.BooleanVar(value=True)
        
        ttk.Checkbutton(options_frame, text="Extract A18 audio files", variable=self.extract_audio).pack(anchor='w')
        ttk.Checkbutton(options_frame, text="Extract image files", variable=self.extract_images).pack(anchor='w')
        ttk.Checkbutton(options_frame, text="Convert A18 files to WAV (requires DLL)", variable=self.convert_to_wav).pack(anchor='w')
        
        # Statistics frame
        stats_frame = ttk.LabelFrame(parent, text="Statistics", padding=10)
        stats_frame.pack(fill='x', padx=10, pady=5)
        
        stats_grid = ttk.Frame(stats_frame)
        stats_grid.pack(fill='x')
        
        ttk.Label(stats_grid, text="Audio files extracted:").grid(row=0, column=0, sticky='w', padx=(0,10))
        ttk.Label(stats_grid, textvariable=self.audio_count).grid(row=0, column=1, sticky='w')
        
        ttk.Label(stats_grid, text="Images extracted:").grid(row=1, column=0, sticky='w', padx=(0,10))
        ttk.Label(stats_grid, textvariable=self.image_count).grid(row=1, column=1, sticky='w')
        
        ttk.Label(stats_grid, text="WAV files created:").grid(row=2, column=0, sticky='w', padx=(0,10))
        ttk.Label(stats_grid, textvariable=self.wav_count).grid(row=2, column=1, sticky='w')
        
        # Information frame
        info_frame = ttk.LabelFrame(parent, text="Information", padding=10)
        info_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        info_text = """Furby ROM Extractor & A18 Converter

This tool processes Furby ROM binary dumps and:

1. Extracts A18 audio files to 'a18_files' folder
2. Extracts images to 'imgs' folder as BMP files
3. Converts A18 files to WAV using the a1800.dll

Requirements:
• ROM binary file (from the dumper tool)
• a1800.dll for A18→WAV conversion (32-bit DLL)

The tool will create subdirectories in your chosen output folder:
• a18_files/ - Raw A18 audio files
• imgs/ - Extracted bitmap images
• wavs/ - Converted WAV audio files

Note: This tool requires 32-bit Python to use the a1800.dll properly."""
        
        info_display = tk.Text(info_frame, wrap='word', height=8, bg='#f0f0f0')
        info_display.insert('1.0', info_text)
        info_display.config(state='disabled')
        info_display.pack(fill='both', expand=True)
        
    def setup_process_tab(self, parent):
        """Setup processing control tab"""
        # Control buttons frame
        control_frame = ttk.LabelFrame(parent, text="Processing Control", padding=10)
        control_frame.pack(fill='x', padx=10, pady=5)
        
        self.start_btn = ttk.Button(control_frame, text="Start Processing", command=self.start_processing)
        self.start_btn.pack(side='left', padx=(0,10))
        
        self.stop_btn = ttk.Button(control_frame, text="Stop Processing", command=self.stop_processing, state='disabled')
        self.stop_btn.pack(side='left', padx=(0,10))
        
        self.status_label = ttk.Label(control_frame, text="Ready to process")
        self.status_label.pack(side='left')
        
        # Progress frame
        progress_frame = ttk.LabelFrame(parent, text="Progress", padding=10)
        progress_frame.pack(fill='x', padx=10, pady=5)
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill='x', pady=(0,5))
        
        self.progress_label = ttk.Label(progress_frame, text="Ready")
        self.progress_label.pack()
        
        # Output folders frame
        folders_frame = ttk.LabelFrame(parent, text="Output Folders", padding=10)
        folders_frame.pack(fill='x', padx=10, pady=5)
        
        self.folder_info = tk.Text(folders_frame, height=6, bg='#f8f8f8')
        self.folder_info.pack(fill='x')
        self.update_folder_info()
        
        # Quick actions frame
        actions_frame = ttk.LabelFrame(parent, text="Quick Actions", padding=10)
        actions_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Button(actions_frame, text="Open Output Directory", command=self.open_output_dir).pack(side='left', padx=(0,10))
        ttk.Button(actions_frame, text="Clear Statistics", command=self.clear_stats).pack(side='left', padx=(0,10))
        
    def setup_log_tab(self, parent):
        """Setup log output tab"""
        log_frame = ttk.Frame(parent)
        log_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        ttk.Label(log_frame, text="Processing Log:").pack(anchor='w')
        
        self.log_text = scrolledtext.ScrolledText(log_frame, wrap='word', height=20)
        self.log_text.pack(fill='both', expand=True, pady=(5,0))
        
        # Log control buttons
        log_btn_frame = ttk.Frame(log_frame)
        log_btn_frame.pack(fill='x', pady=(5,0))
        
        ttk.Button(log_btn_frame, text="Clear Log", command=self.clear_log).pack(side='left')
        ttk.Button(log_btn_frame, text="Save Log", command=self.save_log).pack(side='left', padx=(10,0))
        
    def setup_status_bar(self):
        """Setup status bar"""
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief='sunken', anchor='w')
        status_bar.pack(side='bottom', fill='x')
        
    def log_message(self, message, level='INFO'):
        """Add message to log with timestamp"""
        import datetime
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        formatted_msg = f"[{timestamp}] {level}: {message}\n"
        self.message_queue.put(('log', formatted_msg))
        
    def update_status(self, message):
        """Update status bar"""
        self.message_queue.put(('status', message))
        
    def update_progress(self, percent, message=""):
        """Update progress bar and label"""
        self.message_queue.put(('progress', (percent, message)))
        
    def check_messages(self):
        """Check for thread messages and update UI"""
        try:
            while True:
                msg_type, data = self.message_queue.get_nowait()
                
                if msg_type == 'log':
                    self.log_text.insert('end', data)
                    self.log_text.see('end')
                elif msg_type == 'status':
                    self.status_var.set(data)
                elif msg_type == 'progress':
                    percent, message = data
                    self.progress_var.set(percent)
                    self.progress_label.config(text=message)
                elif msg_type == 'stats_update':
                    audio, images, wavs = data
                    self.audio_count.set(audio)
                    self.image_count.set(images)
                    self.wav_count.set(wavs)
                elif msg_type == 'processing_complete':
                    self.processing_complete_callback()
                    
        except queue.Empty:
            pass
            
        # Schedule next check
        self.root.after(100, self.check_messages)
        
    def browse_rom_file(self):
        """Browse for ROM file"""
        filename = filedialog.askopenfilename(
            title="Select ROM Binary File",
            filetypes=[("Binary files", "*.bin"), ("All files", "*.*")]
        )
        if filename:
            self.rom_file.set(filename)
            
    def browse_dll_file(self):
        """Browse for DLL file"""
        filename = filedialog.askopenfilename(
            title="Select a1800.dll",
            filetypes=[("DLL files", "*.dll"), ("All files", "*.*")]
        )
        if filename:
            self.dll_file.set(filename)
            
    def auto_detect_dll(self):
        """Auto-detect a1800.dll in current directory"""
        dll_path = os.path.join(os.getcwd(), "a1800.dll")
        if os.path.exists(dll_path):
            self.dll_file.set(dll_path)
            self.log_message(f"Found a1800.dll: {dll_path}")
        else:
            messagebox.showwarning("Not Found", "a1800.dll not found in current directory")
            
    def browse_output_dir(self):
        """Browse for output directory"""
        directory = filedialog.askdirectory(initialdir=self.output_dir.get())
        if directory:
            self.output_dir.set(directory)
            self.update_folder_info()
            
    def update_folder_info(self):
        """Update folder information display"""
        output_dir = self.output_dir.get()
        info_text = f"Output Directory: {output_dir}\n\n"
        info_text += f"Subdirectories that will be created:\n"
        info_text += f"• {os.path.join(output_dir, 'a18_files')}\n"
        info_text += f"• {os.path.join(output_dir, 'imgs')}\n"
        info_text += f"• {os.path.join(output_dir, 'wavs')}\n"
        
        self.folder_info.delete('1.0', 'end')
        self.folder_info.insert('1.0', info_text)
        
    def open_output_dir(self):
        """Open output directory in file explorer"""
        output_dir = self.output_dir.get()
        if os.path.exists(output_dir):
            os.startfile(output_dir)  # Windows
        else:
            messagebox.showwarning("Warning", "Output directory does not exist")
            
    def clear_stats(self):
        """Clear statistics"""
        self.audio_count.set(0)
        self.image_count.set(0)
        self.wav_count.set(0)
        
    def clear_log(self):
        """Clear log text"""
        self.log_text.delete('1.0', 'end')
        
    def save_log(self):
        """Save log to file"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if filename:
            try:
                with open(filename, 'w') as f:
                    f.write(self.log_text.get('1.0', 'end'))
                messagebox.showinfo("Success", f"Log saved to {filename}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save log: {e}")
                
    def start_processing(self):
        """Start the processing"""
        # Validate inputs
        if not self.rom_file.get():
            messagebox.showerror("Error", "Please select a ROM binary file")
            return
            
        if not os.path.exists(self.rom_file.get()):
            messagebox.showerror("Error", "ROM file does not exist")
            return
            
        if self.convert_to_wav.get() and not self.dll_file.get():
            messagebox.showerror("Error", "Please select a1800.dll for WAV conversion")
            return
            
        if self.convert_to_wav.get() and not os.path.exists(self.dll_file.get()):
            messagebox.showerror("Error", "a1800.dll file does not exist")
            return
            
        # Create output directory if needed
        if not os.path.exists(self.output_dir.get()):
            try:
                os.makedirs(self.output_dir.get())
            except Exception as e:
                messagebox.showerror("Error", f"Cannot create output directory: {e}")
                return
                
        # Start processing
        self.processing_active = True
        self.start_btn.config(state='disabled')
        self.stop_btn.config(state='normal')
        self.status_label.config(text="Processing...")
        self.clear_stats()
        
        self.process_thread = threading.Thread(target=self._processing_worker)
        self.process_thread.daemon = True
        self.process_thread.start()
        
    def _processing_worker(self):
        """Worker thread for processing"""
        try:
            self.log_message("Starting Furby ROM processing...")
            self.update_status("Loading ROM data...")
            self.update_progress(0, "Loading ROM data...")
            
            # Load ROM data
            with open(self.rom_file.get(), "rb") as f:
                rom_data = f.read()
            
            self.log_message(f"Loaded ROM file: {len(rom_data):,} bytes")
            self.update_progress(10, "Analyzing ROM header...")
            
            # Analyze header
            offsets = self._analyze_header(rom_data)
            self.log_message(f"Found {len(offsets)} offsets in ROM header")
            
            audio_offsets = []
            audio_count = 0
            image_count = 0
            
            # Extract audio tracks if enabled
            if self.extract_audio.get() and self.processing_active:
                self.update_progress(20, "Extracting audio files...")
                audio_offsets, audio_count = self._extract_audio_tracks(rom_data, offsets)
                
            # Extract images if enabled  
            if self.extract_images.get() and self.processing_active:
                self.update_progress(60, "Extracting images...")
                image_count = self._extract_images(rom_data, offsets, audio_offsets)
                
            # Convert to WAV if enabled
            wav_count = 0
            if self.convert_to_wav.get() and self.processing_active:
                self.update_progress(80, "Converting A18 to WAV...")
                wav_count = self._convert_to_wav()
                
            self.message_queue.put(('stats_update', (audio_count, image_count, wav_count)))
            
            if self.processing_active:
                self.update_progress(100, "Processing complete!")
                self.log_message("Processing completed successfully!")
                self.message_queue.put(('processing_complete', None))
            else:
                self.log_message("Processing stopped by user")
                
        except Exception as e:
            self.log_message(f"Processing error: {e}", "ERROR")
            self.message_queue.put(('processing_complete', None))
            
    def _analyze_header(self, rom_data):
        """Read offsets from the ROM header."""
        num_offsets = struct.unpack('<I', rom_data[0:4])[0]
        offsets = []
        for i in range(num_offsets):
            offset = struct.unpack('<I', rom_data[4 + i*4 : 8 + i*4])[0]
            offsets.append(offset)
        return offsets
        
    def _extract_audio_tracks(self, rom_data, offsets):
        """Extract audio tracks from ROM data."""
        output_dir = os.path.join(self.output_dir.get(), "a18_files")
        os.makedirs(output_dir, exist_ok=True)
        
        audio_offsets = []
        audio_count = 0
        
        for i, start in enumerate(offsets):
            if not self.processing_active:
                break
                
            end_idx = offsets.index(start) + 1
            end = offsets[end_idx] if end_idx < len(offsets) else len(rom_data)
            
            # Only process if audio marker present
            if rom_data[start+4:start+6] != b'\x80\x3e':
                continue
            
            track_data = rom_data[start:end]
            audio_count += 1
            filename = os.path.join(output_dir, f"audio{audio_count:04d}.a18")
            
            with open(filename, "wb") as out:
                out.write(track_data)
            
            audio_offsets.append(start)
            self.log_message(f"Audio Track {audio_count}: {len(track_data)} bytes → {os.path.basename(filename)}")
            
            # Update progress within audio extraction
            progress = 20 + (i / len(offsets)) * 40
            self.update_progress(progress, f"Extracting audio files... ({audio_count} found)")
        
        return audio_offsets, audio_count
        
    def _extract_images(self, rom_data, offsets, audio_offsets):
        """Extract 256-byte image records, skipping audio offsets."""
        output_dir = os.path.join(self.output_dir.get(), "imgs")
        os.makedirs(output_dir, exist_ok=True)
        
        image_count = 0
        
        for i, start in enumerate(offsets):
            if not self.processing_active:
                break
                
            if start in audio_offsets:
                continue
            
            end = offsets[i+1] if i < len(offsets)-1 else len(rom_data)
            size = end - start
            if size != 256:
                continue  # Skip non-image records
            
            buf = rom_data[start:end]
            
            bits = []
            for b in buf:
                bits.extend(self._get_bits(b))
            
            width, height = 64, 32
            img = Image.new("RGB", (width, height), "white")
            pixels = img.load()
            
            for h in range(height):
                for w in range(width):
                    pos = self.x_offsets[w] + self.y_offsets[h]
                    bit = bits[pos]
                    pixels[w, h] = (255, 255, 255) if bit else (0, 0, 0)
                    
            image_count += 1
            img = img.transpose(Image.FLIP_TOP_BOTTOM).transpose(Image.FLIP_LEFT_RIGHT)
            filename = os.path.join(output_dir, f"img_{image_count:04d}.bmp")
            img.save(filename)
            self.log_message(f"Extracted image at offset {hex(start)} → img_{image_count:04d}.bmp")
            
            # Update progress within image extraction
            progress = 60 + (i / len(offsets)) * 20
            self.update_progress(progress, f"Extracting images... ({image_count} found)")
            
        return image_count
        
    def _convert_to_wav(self):
        """Convert A18 files to WAV using DLL"""
        try:
            dll = ctypes.WinDLL(self.dll_file.get())
            decproto = ctypes.WINFUNCTYPE(ctypes.c_uint, LPCSTR, LPCSTR, ctypes.POINTER(UINT), UINT, UINT)
            decparamflags = ((1, 'infile'), (1, 'outfile'), (2, 'fp'), (1, 'unk1', 16000), (1, 'unk2', 0))
            decfunc = decproto(('dec', dll), decparamflags)
            
            a18_dir = os.path.join(self.output_dir.get(), "a18_files")
            wav_dir = os.path.join(self.output_dir.get(), "wavs")
            os.makedirs(wav_dir, exist_ok=True)
            
            files = [f for f in os.listdir(a18_dir) if f.endswith('.a18')]
            wav_count = 0
            
            for i, f in enumerate(files):
                if not self.processing_active:
                    break
                    
                inpath = os.path.join(a18_dir, f)
                basename, _ = os.path.splitext(f)
                outpath = os.path.join(wav_dir, basename + '.wav')
                
                self.log_message(f"Converting {f} → {basename}.wav")
                
                try:
                    decfunc(infile=LPCSTR(inpath.encode('ascii')), 
                           outfile=LPCSTR(outpath.encode('ascii')))
                    wav_count += 1
                except Exception as e:
                    self.log_message(f"Failed to convert {f}: {e}", "ERROR")
                
                # Update progress within WAV conversion
                progress = 80 + (i / len(files)) * 20
                self.update_progress(progress, f"Converting to WAV... ({wav_count}/{len(files)})")
                
            return wav_count
            
        except Exception as e:
            self.log_message(f"WAV conversion error: {e}", "ERROR")
            return 0
            
    def _get_bits(self, byte):
        """Convert a byte into a list of 8 bits (MSB first)."""
        return [(byte >> i) & 1 for i in reversed(range(8))]
        
    def stop_processing(self):
        """Stop current processing"""
        self.processing_active = False
        self.log_message("Stopping processing...")
        self.update_status("Stopping...")
        
    def processing_complete_callback(self):
        """Handle processing completion"""
        self.processing_active = False
        self.start_btn.config(state='normal')
        self.stop_btn.config(state='disabled')
        self.status_label.config(text="Ready to process")
        
        audio_count = self.audio_count.get()
        image_count = self.image_count.get()
        wav_count = self.wav_count.get()
        
        summary = f"Processing completed!\n\n"
        summary += f"• Audio files extracted: {audio_count}\n"
        summary += f"• Images extracted: {image_count}\n"
        summary += f"• WAV files created: {wav_count}"
        
        messagebox.showinfo("Processing Complete", summary)
        self.update_status("Ready")

def main():
    root = tk.Tk()
    app = FurbyExtractorGUI(root)
    
    # Handle window close
    def on_closing():
        if app.processing_active:
            if messagebox.askokcancel("Quit", "Processing in progress. Really quit?"):
                app.processing_active = False
                root.destroy()
        else:
            root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()

if __name__ == "__main__":
    main()