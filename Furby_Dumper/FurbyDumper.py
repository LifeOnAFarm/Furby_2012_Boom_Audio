#!/usr/bin/env python3
"""
Furby EEPROM Dump Capture GUI v2.1
GUI version of the automated Furby EEPROM dumper
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import serial
import serial.tools.list_ports
import time
import re
import threading
from datetime import datetime
import os
import queue

class FurbyDumperGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Furby EEPROM Dumper v2.1")
        self.root.geometry("850x750")
        self.root.resizable(True, True)
        
        # Variables
        self.ser = None
        self.dump_active = False
        self.total_bytes = 0
        self.chip_size = 0
        self.output_dir = tk.StringVar(value=os.getcwd())
        self.selected_port = tk.StringVar()
        self.baudrate = tk.IntVar(value=115200)
        self.progress_var = tk.DoubleVar(value=0)
        self.bytes_received = tk.IntVar(value=0)
        
        # Thread communication
        self.message_queue = queue.Queue()
        self.dump_thread = None
        
        self.setup_ui()
        self.refresh_ports()
        self.check_messages()
        
    def setup_ui(self):
        """Setup the user interface"""
        # Main notebook for tabs
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill='both', expand=True, padx=10, pady=5)
        
        # Main dump tab
        main_frame = ttk.Frame(notebook)
        notebook.add(main_frame, text="Dump Control")
        self.setup_main_tab(main_frame)
        
        # Log tab
        log_frame = ttk.Frame(notebook)
        notebook.add(log_frame, text="Log")
        self.setup_log_tab(log_frame)
        
        # Status bar
        self.setup_status_bar()
        
    def setup_main_tab(self, parent):
        """Setup main dump control tab"""
        # Info box at top
        info_frame = ttk.LabelFrame(parent, text="About", padding=10)
        info_frame.pack(fill='x', padx=10, pady=5)
        
        info_text = ("Furby EEPROM Dumper - Connects to ESP32 running Furby dump firmware\n"
                    "Automatically captures complete EEPROM contents in binary, hex, and raw formats")
        info_label = ttk.Label(info_frame, text=info_text, justify='left', foreground='#555')
        info_label.pack(anchor='w')
        
        # Port selection frame
        port_frame = ttk.LabelFrame(parent, text="Serial Port Configuration", padding=10)
        port_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Label(port_frame, text="Port:").grid(row=0, column=0, sticky='w', padx=(0,5))
        self.port_combo = ttk.Combobox(port_frame, textvariable=self.selected_port, width=30)
        self.port_combo.grid(row=0, column=1, sticky='ew', padx=(0,5))
        
        ttk.Button(port_frame, text="Refresh", command=self.refresh_ports).grid(row=0, column=2, padx=5)
        ttk.Button(port_frame, text="Show All Ports", command=self.list_all_ports).grid(row=0, column=3, padx=5)
        
        port_frame.columnconfigure(1, weight=1)
        
        # Baudrate
        ttk.Label(port_frame, text="Baud Rate:").grid(row=1, column=0, sticky='w', padx=(0,5), pady=(5,0))
        baud_combo = ttk.Combobox(port_frame, textvariable=self.baudrate, 
                                   values=[9600, 19200, 38400, 57600, 115200, 230400], 
                                   width=15, state='readonly')
        baud_combo.grid(row=1, column=1, sticky='w', padx=(0,5), pady=(5,0))
        
        # Connection status
        self.connection_status = ttk.Label(port_frame, text="● Disconnected", foreground='gray')
        self.connection_status.grid(row=1, column=2, columnspan=2, sticky='w', padx=5, pady=(5,0))
        
        # Output directory frame
        output_frame = ttk.LabelFrame(parent, text="Output Directory", padding=10)
        output_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Label(output_frame, text="Save to:").grid(row=0, column=0, sticky='w', padx=(0,5))
        ttk.Entry(output_frame, textvariable=self.output_dir, width=50).grid(row=0, column=1, sticky='ew', padx=(0,5))
        ttk.Button(output_frame, text="Browse...", command=self.browse_output_dir).grid(row=0, column=2, padx=5)
        
        output_frame.columnconfigure(1, weight=1)
        
        # Dump control frame
        dump_frame = ttk.LabelFrame(parent, text="Dump Control", padding=10)
        dump_frame.pack(fill='x', padx=10, pady=5)
        
        btn_frame = ttk.Frame(dump_frame)
        btn_frame.pack(fill='x')
        
        self.dump_btn = ttk.Button(btn_frame, text="▶ Start Dump", command=self.start_dump, width=20)
        self.dump_btn.pack(side='left', padx=(0,10))
        
        self.stop_btn = ttk.Button(btn_frame, text="■ Stop Dump", command=self.stop_dump, state='disabled', width=20)
        self.stop_btn.pack(side='left', padx=(0,10))
        
        # Progress frame
        progress_frame = ttk.LabelFrame(parent, text="Progress", padding=10)
        progress_frame.pack(fill='x', padx=10, pady=5)
        
        # Progress bar
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, 
                                           maximum=100, mode='determinate', length=400)
        self.progress_bar.pack(fill='x', pady=(0,5))
        
        # Progress info labels
        info_grid = ttk.Frame(progress_frame)
        info_grid.pack(fill='x')
        
        ttk.Label(info_grid, text="Bytes Received:").grid(row=0, column=0, sticky='w', padx=(0,5))
        self.bytes_label = ttk.Label(info_grid, text="0", foreground='blue', font=('TkDefaultFont', 9, 'bold'))
        self.bytes_label.grid(row=0, column=1, sticky='w', padx=(0,20))
        
        ttk.Label(info_grid, text="Chip Size:").grid(row=0, column=2, sticky='w', padx=(0,5))
        self.chip_size_label = ttk.Label(info_grid, text="Unknown", foreground='blue', font=('TkDefaultFont', 9, 'bold'))
        self.chip_size_label.grid(row=0, column=3, sticky='w', padx=(0,20))
        
        ttk.Label(info_grid, text="Progress:").grid(row=0, column=4, sticky='w', padx=(0,5))
        self.progress_label = ttk.Label(info_grid, text="0%", foreground='blue', font=('TkDefaultFont', 9, 'bold'))
        self.progress_label.grid(row=0, column=5, sticky='w')
        
        # Status label
        self.dump_status = ttk.Label(progress_frame, text="Ready to begin dump", foreground='green')
        self.dump_status.pack(pady=(5,0))
        
        # Quick tips
        tips_frame = ttk.LabelFrame(parent, text="Quick Tips", padding=10)
        tips_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        tips_text = """• Ensure ESP32 is connected and running compatible firmware before starting
• Output files: .bin (binary), .hex (formatted hex), .txt (raw log)
• Files are automatically timestamped
• Use 'Show All Ports' if your device doesn't appear in the list
• Check the Log tab for detailed operation information"""
        
        tips_label = ttk.Label(tips_frame, text=tips_text, justify='left', foreground='#666')
        tips_label.pack(anchor='w')
        
    def setup_log_tab(self, parent):
        """Setup log output tab"""
        log_frame = ttk.Frame(parent)
        log_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        ttk.Label(log_frame, text="Real-time Operation Log:").pack(anchor='w')
        
        self.log_text = scrolledtext.ScrolledText(log_frame, wrap='word', height=20, font=('Consolas', 9))
        self.log_text.pack(fill='both', expand=True, pady=(5,0))
        
        # Log control buttons
        log_btn_frame = ttk.Frame(log_frame)
        log_btn_frame.pack(fill='x', pady=(5,0))
        
        ttk.Button(log_btn_frame, text="Clear Log", command=self.clear_log).pack(side='left')
        ttk.Button(log_btn_frame, text="Save Log...", command=self.save_log).pack(side='left', padx=(10,0))
        ttk.Button(log_btn_frame, text="Copy to Clipboard", command=self.copy_log).pack(side='left', padx=(10,0))
        
    def setup_status_bar(self):
        """Setup status bar"""
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief='sunken', anchor='w')
        status_bar.pack(side='bottom', fill='x')
        
    def log_message(self, message, level='INFO'):
        """Add message to log with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        formatted_msg = f"[{timestamp}] {level:7s}: {message}\n"
        
        # Thread-safe log update
        self.message_queue.put(('log', formatted_msg))
        
    def update_status(self, message):
        """Update status bar"""
        self.message_queue.put(('status', message))
        
    def update_progress(self, bytes_received, chip_size):
        """Update progress indicators"""
        self.message_queue.put(('progress', (bytes_received, chip_size)))
        
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
                    bytes_received, chip_size = data
                    self.bytes_label.config(text=f"{bytes_received:,}")
                    if chip_size > 0:
                        progress = (bytes_received / chip_size) * 100
                        self.progress_var.set(progress)
                        self.progress_label.config(text=f"{progress:.1f}%")
                elif msg_type == 'chip_size':
                    self.chip_size_label.config(text=f"{data:,} bytes")
                elif msg_type == 'dump_complete':
                    self.dump_complete_callback(data)
                        
        except queue.Empty:
            pass
            
        # Schedule next check
        self.root.after(100, self.check_messages)
        
    def refresh_ports(self):
        """Refresh available serial ports"""
        ports = serial.tools.list_ports.comports()
        esp_ports = []
        
        for port in ports:
            if any(chip in port.description.lower() for chip in 
                   ['cp210', 'ch340', 'ch341', 'ftdi', 'esp32', 'usb serial', 'silicon labs']):
                esp_ports.append(f"{port.device} - {port.description}")
            
        self.port_combo['values'] = esp_ports
        if esp_ports:
            self.port_combo.current(0)
            self.log_message(f"Found {len(esp_ports)} potential ESP32 device(s)")
        else:
            self.log_message("No ESP32-like devices detected. Click 'Show All Ports' to see all available devices.", "WARNING")
            
    def list_all_ports(self):
        """Show all available ports in a dialog"""
        ports = serial.tools.list_ports.comports()
        if not ports:
            messagebox.showinfo("Serial Ports", "No serial ports found")
            return
            
        port_list = "\n".join([f"{p.device}: {p.description}\n  Hardware ID: {p.hwid}" for p in ports])
        messagebox.showinfo("All Serial Ports", port_list)
        
    def browse_output_dir(self):
        """Browse for output directory"""
        directory = filedialog.askdirectory(initialdir=self.output_dir.get())
        if directory:
            self.output_dir.set(directory)
            self.log_message(f"Output directory changed to: {directory}")
            
    def clear_log(self):
        """Clear log text"""
        self.log_text.delete('1.0', 'end')
        self.log_message("Log cleared")
        
    def save_log(self):
        """Save log to file"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            initialfile=f"furby_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        )
        if filename:
            try:
                with open(filename, 'w') as f:
                    f.write(self.log_text.get('1.0', 'end'))
                messagebox.showinfo("Success", f"Log saved to:\n{filename}")
                self.log_message(f"Log saved to {filename}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save log: {e}")
                
    def copy_log(self):
        """Copy log to clipboard"""
        self.root.clipboard_clear()
        self.root.clipboard_append(self.log_text.get('1.0', 'end'))
        self.update_status("Log copied to clipboard")
        
    def start_dump(self):
        """Start EEPROM dump process"""
        if not self.selected_port.get():
            messagebox.showerror("Error", "Please select a serial port")
            return
            
        if self.dump_active:
            messagebox.showwarning("Warning", "Dump already in progress")
            return
            
        # Create output directory if needed
        output_dir = self.output_dir.get()
        if not os.path.exists(output_dir):
            try:
                os.makedirs(output_dir)
                self.log_message(f"Created output directory: {output_dir}")
            except Exception as e:
                messagebox.showerror("Error", f"Cannot create output directory: {e}")
                return
                
        # Reset progress
        self.progress_var.set(0)
        self.bytes_label.config(text="0")
        self.chip_size_label.config(text="Detecting...")
        self.progress_label.config(text="0%")
        
        # Start dump in thread
        self.dump_active = True
        self.dump_btn.config(state='disabled')
        self.stop_btn.config(state='normal')
        self.dump_status.config(text="Connecting to device...", foreground='orange')
        self.connection_status.config(text="● Connecting...", foreground='orange')
        
        # Extract just the port name
        port = self.selected_port.get().split(" - ")[0]
        
        self.dump_thread = threading.Thread(target=self._dump_worker, args=(port, output_dir))
        self.dump_thread.daemon = True
        self.dump_thread.start()
        self.log_message("=" * 60)
        self.log_message("Starting new dump session")
        self.log_message("=" * 60)
        
    def _dump_worker(self, port, output_dir):
        """Worker thread for dump process"""
        try:
            # Connect to ESP32
            self.log_message(f"Connecting to {port} at {self.baudrate.get()} baud")
            self.update_status(f"Connecting to {port}...")
            self.ser = serial.Serial(port, self.baudrate.get(), timeout=2)
            
            # Clear buffers and initialize
            self.ser.flushInput()
            self.ser.flushOutput()
            time.sleep(3)
            
            # Send newline to wake up
            self.ser.write(b'\n')
            time.sleep(0.5)
            
            # Update connection status
            self.message_queue.put(('log', "[INFO   ]: Connection established\n"))
            self.connection_status.config(text="● Connected", foreground='green')
            self.dump_status.config(text="Starting dump...", foreground='blue')
            
            # Generate filenames
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            raw_file = os.path.join(output_dir, f"furby_dump_{timestamp}.txt")
            bin_file = os.path.join(output_dir, f"furby_dump_{timestamp}.bin")
            hex_file = os.path.join(output_dir, f"furby_dump_{timestamp}.hex")
            
            self.log_message(f"Output files:")
            self.log_message(f"  Binary: {os.path.basename(bin_file)}")
            self.log_message(f"  Hex:    {os.path.basename(hex_file)}")
            self.log_message(f"  Raw:    {os.path.basename(raw_file)}")
            
            # Send START command
            self.ser.write(b"START\n")
            self.ser.flush()
            self.log_message("Sent START command to device")
            
            # Process dump
            with open(raw_file, 'w') as raw_f, \
                 open(bin_file, 'wb') as bin_f, \
                 open(hex_file, 'w') as hex_f:
                 
                hex_f.write(f"# Furby EEPROM Dump - {timestamp}\n")
                hex_f.write(f"# Captured from {port} at {self.baudrate.get()} baud\n#\n")
                
                dump_started = False
                dump_complete = False
                total_bytes = 0
                chip_size = 0
                last_update = time.time()
                
                while not dump_complete and self.dump_active:
                    if not self.ser.in_waiting:
                        time.sleep(0.01)
                        continue
                        
                    line = self.ser.readline().decode('utf-8', errors='ignore').strip()
                    if not line:
                        continue
                        
                    # Write raw output
                    raw_f.write(line + '\n')
                    raw_f.flush()
                    
                    # Process different message types
                    if line == "DUMP_START":
                        dump_started = True
                        self.log_message("*** DUMP STARTED ***")
                        self.dump_status.config(text="Receiving data...", foreground='blue')
                        
                    elif line.startswith("TOTAL_SIZE:"):
                        chip_size = int(line.split(":")[1])
                        self.chip_size = chip_size
                        self.log_message(f"Chip size detected: {chip_size:,} bytes ({chip_size/1024:.1f} KB)")
                        self.message_queue.put(('chip_size', chip_size))
                        
                    elif line == "DUMP_COMPLETE":
                        dump_complete = True
                        self.log_message("*** DUMP COMPLETE ***")
                        
                    elif dump_started and not line.startswith(("@", "ERROR:", "DATA_", "TOTAL_", "SPEED:")):
                        # Process hex data
                        hex_data = self._parse_hex_data(line)
                        if hex_data:
                            hex_line = ' '.join([f"{b:02X}" for b in hex_data])
                            hex_f.write(f"{hex_line}\n")
                            bin_f.write(bytes(hex_data))
                            total_bytes += len(hex_data)
                            
                            # Update progress (throttled to every 100ms)
                            current_time = time.time()
                            if current_time - last_update > 0.1:
                                self.update_progress(total_bytes, chip_size)
                                last_update = current_time
                            
                            if total_bytes % (64*1024) == 0:  # Flush every 64KB
                                bin_f.flush()
                                hex_f.flush()
                                
            # Final progress update
            self.update_progress(total_bytes, chip_size)
            self.message_queue.put(('dump_complete', (bin_file, total_bytes)))
            
        except serial.SerialException as e:
            self.log_message(f"Serial connection error: {e}", "ERROR")
            self.message_queue.put(('dump_complete', (None, 0)))
        except Exception as e:
            self.log_message(f"Unexpected error: {e}", "ERROR")
            self.message_queue.put(('dump_complete', (None, 0)))
        finally:
            if self.ser:
                self.ser.close()
                self.ser = None
            
    def _parse_hex_data(self, line):
        """Parse hex data from line"""
        line = line.strip()
        if not line or line.startswith('@') or line.startswith('ERROR'):
            return []
            
        line = re.sub(r"^0x[0-9A-Fa-f]+:\s*", "", line)
        parts = line.split()
        hex_bytes = []
        
        for part in parts:
            if re.fullmatch(r"[0-9A-Fa-f]{2}", part):
                hex_bytes.append(int(part, 16))
                
        return hex_bytes
        
    def stop_dump(self):
        """Stop current dump"""
        self.dump_active = False
        self.log_message("Stop requested by user", "WARNING")
        self.update_status("Stopping dump...")
        self.dump_status.config(text="Stopping...", foreground='red')
        
    def dump_complete_callback(self, data):
        """Handle dump completion"""
        bin_file, total_bytes = data
        
        self.dump_active = False
        self.dump_btn.config(state='normal')
        self.stop_btn.config(state='disabled')
        self.connection_status.config(text="● Disconnected", foreground='gray')
        
        if bin_file:
            self.log_message("=" * 60)
            self.log_message(f"SUCCESS! Dump completed")
            self.log_message(f"Total bytes received: {total_bytes:,}")
            self.log_message(f"Output file: {bin_file}")
            self.log_message("=" * 60)
            self.dump_status.config(text="✓ Dump completed successfully!", foreground='green')
            self.update_status("Ready")
            
            messagebox.showinfo("Dump Complete", 
                              f"EEPROM dump completed successfully!\n\n"
                              f"Total bytes: {total_bytes:,}\n"
                              f"Saved to: {os.path.basename(bin_file)}\n\n"
                              f"Check the output directory for all files.")
        else:
            self.log_message("Dump failed or was interrupted", "ERROR")
            self.dump_status.config(text="✗ Dump failed", foreground='red')
            self.update_status("Ready")
            messagebox.showerror("Dump Failed", "Dump failed or was interrupted.\nCheck the log for details.")

def main():
    root = tk.Tk()
    app = FurbyDumperGUI(root)
    
    # Handle window close
    def on_closing():
        if app.dump_active:
            if messagebox.askokcancel("Quit", "Dump in progress. Really quit?"):
                app.dump_active = False
                if app.ser:
                    app.ser.close()
                root.destroy()
        else:
            if app.ser:
                app.ser.close()
            root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()

if __name__ == "__main__":
    main()