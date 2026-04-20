#!/usr/bin/env python3
"""
Furby EEPROM Dump Capture GUI v2.0
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
        self.root.title("Furby EEPROM Dumper v2.0")
        self.root.geometry("800x700")
        self.root.resizable(True, True)
        
        # Variables
        self.ser = None
        self.dump_active = False
        self.total_bytes = 0
        self.chip_size = 0
        self.output_dir = tk.StringVar(value=os.getcwd())
        self.selected_port = tk.StringVar()
        self.baudrate = tk.IntVar(value=115200)
        self.skip_test = tk.BooleanVar(value=False)
        self.skip_identify = tk.BooleanVar(value=False)
        
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
        
        # Connection tab
        conn_frame = ttk.Frame(notebook)
        notebook.add(conn_frame, text="Connection")
        self.setup_connection_tab(conn_frame)
        
        # Options tab
        options_frame = ttk.Frame(notebook)
        notebook.add(options_frame, text="Options")
        self.setup_options_tab(options_frame)
        
        # Log tab
        log_frame = ttk.Frame(notebook)
        notebook.add(log_frame, text="Log")
        self.setup_log_tab(log_frame)
        
        # Status bar
        self.setup_status_bar()
        
    def setup_connection_tab(self, parent):
        """Setup connection configuration tab"""
        # Port selection frame
        port_frame = ttk.LabelFrame(parent, text="Serial Port", padding=10)
        port_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Label(port_frame, text="Port:").grid(row=0, column=0, sticky='w', padx=(0,5))
        self.port_combo = ttk.Combobox(port_frame, textvariable=self.selected_port, width=20)
        self.port_combo.grid(row=0, column=1, sticky='ew', padx=(0,5))
        
        ttk.Button(port_frame, text="Refresh", command=self.refresh_ports).grid(row=0, column=2, padx=5)
        ttk.Button(port_frame, text="List All", command=self.list_all_ports).grid(row=0, column=3, padx=5)
        
        port_frame.columnconfigure(1, weight=1)
        
        # Baudrate
        ttk.Label(port_frame, text="Baud Rate:").grid(row=1, column=0, sticky='w', padx=(0,5), pady=(5,0))
        baud_combo = ttk.Combobox(port_frame, textvariable=self.baudrate, values=[9600, 19200, 38400, 57600, 115200, 230400], width=20)
        baud_combo.grid(row=1, column=1, sticky='w', padx=(0,5), pady=(5,0))
        
        # Output directory frame
        output_frame = ttk.LabelFrame(parent, text="Output Directory", padding=10)
        output_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Label(output_frame, text="Directory:").grid(row=0, column=0, sticky='w', padx=(0,5))
        ttk.Entry(output_frame, textvariable=self.output_dir, width=50).grid(row=0, column=1, sticky='ew', padx=(0,5))
        ttk.Button(output_frame, text="Browse", command=self.browse_output_dir).grid(row=0, column=2, padx=5)
        
        output_frame.columnconfigure(1, weight=1)
        
        # Connection status frame
        status_frame = ttk.LabelFrame(parent, text="Connection Status", padding=10)
        status_frame.pack(fill='x', padx=10, pady=5)
        
        self.connection_status = ttk.Label(status_frame, text="Ready to connect - Select port and start dump", foreground='blue')
        self.connection_status.pack(side='left')
        
        # Dump control frame
        dump_frame = ttk.LabelFrame(parent, text="EEPROM Dump", padding=10)
        dump_frame.pack(fill='x', padx=10, pady=5)
        
        self.dump_btn = ttk.Button(dump_frame, text="Start Dump", command=self.start_dump)
        self.dump_btn.pack(side='left', padx=(0,10))
        
        self.stop_btn = ttk.Button(dump_frame, text="Stop Dump", command=self.stop_dump, state='disabled')
        self.stop_btn.pack(side='left', padx=(0,10))
        
        self.dump_status = ttk.Label(dump_frame, text="Ready to dump")
        self.dump_status.pack(side='left')
        
        # Progress frame
        progress_frame = ttk.LabelFrame(parent, text="Progress", padding=10)
        progress_frame.pack(fill='x', padx=10, pady=5)
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill='x', pady=(0,5))
        
        self.progress_label = ttk.Label(progress_frame, text="0% - 0/0 KB - ETA: --")
        self.progress_label.pack()
        
    def setup_options_tab(self, parent):
        """Setup options tab"""
        options_frame = ttk.LabelFrame(parent, text="Dump Options", padding=10)
        options_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Checkbutton(options_frame, text="Skip connection test", variable=self.skip_test).pack(anchor='w')
        ttk.Checkbutton(options_frame, text="Skip chip identification", variable=self.skip_identify).pack(anchor='w')
        
        info_frame = ttk.LabelFrame(parent, text="Information", padding=10)
        info_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        info_text = """Furby EEPROM Dumper v2.0

This tool connects to an ESP32 running the Furby EEPROM dump firmware and automatically captures the complete EEPROM contents.

Features:
• Auto-detection of ESP32 serial ports
• Real-time progress monitoring
• Multiple output formats (raw, binary, hex)
• Connection testing and chip identification
• Automatic file timestamping

Output files:
• .bin - Binary dump (main output)
• .hex - Hex formatted dump
• .txt - Raw capture log

Make sure your ESP32 is connected and running the compatible firmware before starting."""
        
        info_display = tk.Text(info_frame, wrap='word', height=15, bg='#f0f0f0')
        info_display.insert('1.0', info_text)
        info_display.config(state='disabled')
        info_display.pack(fill='both', expand=True)
        
    def setup_log_tab(self, parent):
        """Setup log output tab"""
        log_frame = ttk.Frame(parent)
        log_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        ttk.Label(log_frame, text="Real-time Log Output:").pack(anchor='w')
        
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
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_msg = f"[{timestamp}] {level}: {message}\n"
        
        # Thread-safe log update
        self.message_queue.put(('log', formatted_msg))
        
    def update_status(self, message):
        """Update status bar"""
        self.message_queue.put(('status', message))
        
    def update_progress(self, percent, current, total, eta):
        """Update progress bar and label"""
        self.message_queue.put(('progress', (percent, current, total, eta)))
        
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
                    percent, current, total, eta = data
                    self.progress_var.set(percent)
                    self.progress_label.config(text=f"{percent:.1f}% - {current//1024}/{total//1024} KB - ETA: {eta}s")
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
                   ['cp210', 'ch340', 'ch341', 'ftdi', 'esp32', 'usb serial']):
                esp_ports.append(f"{port.device} - {port.description}")
            
        self.port_combo['values'] = esp_ports
        if esp_ports:
            self.port_combo.current(0)
            self.log_message(f"Found {len(esp_ports)} potential ESP32 device(s)")
        else:
            self.log_message("No ESP32-like devices detected", "WARNING")
            
    def list_all_ports(self):
        """Show all available ports in a dialog"""
        ports = serial.tools.list_ports.comports()
        if not ports:
            messagebox.showinfo("Serial Ports", "No serial ports found")
            return
            
        port_list = "\n".join([f"{p.device}: {p.description}" for p in ports])
        messagebox.showinfo("All Serial Ports", port_list)
        
    def browse_output_dir(self):
        """Browse for output directory"""
        directory = filedialog.askdirectory(initialdir=self.output_dir.get())
        if directory:
            self.output_dir.set(directory)
            
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
            except Exception as e:
                messagebox.showerror("Error", f"Cannot create output directory: {e}")
                return
                
        # Start dump in thread
        self.dump_active = True
        self.dump_btn.config(state='disabled')
        self.stop_btn.config(state='normal')
        self.dump_status.config(text="Connecting and dumping...")
        self.connection_status.config(text="Connecting...", foreground='orange')
        
        # Extract just the port name
        port = self.selected_port.get().split(" - ")[0]
        
        self.dump_thread = threading.Thread(target=self._dump_worker, args=(port, output_dir))
        self.dump_thread.daemon = True
        self.dump_thread.start()
        
    def _dump_worker(self, port, output_dir):
        """Worker thread for dump process"""
        try:
            # Connect to ESP32
            self.log_message(f"Connecting to {port} at {self.baudrate.get()} baud")
            self.ser = serial.Serial(port, self.baudrate.get(), timeout=2)
            
            # Clear buffers and initialize
            self.ser.flushInput()
            self.ser.flushOutput()
            time.sleep(3)
            
            # Send newline to wake up
            self.ser.write(b'\n')
            time.sleep(0.5)
            
            # Update connection status
            self.connection_status.config(text="Connected - Starting dump...", foreground='green')
            
            # Generate filenames
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            raw_file = os.path.join(output_dir, f"furby_dump_raw_{timestamp}.txt")
            bin_file = os.path.join(output_dir, f"furby_dump_{timestamp}.bin")
            hex_file = os.path.join(output_dir, f"furby_dump_{timestamp}.hex")
            
            self.log_message(f"Starting dump to {bin_file}")
            
            # Send START command
            self.ser.write(b"START\n")
            self.ser.flush()
            
            # Process dump
            with open(raw_file, 'w') as raw_f, \
                 open(bin_file, 'wb') as bin_f, \
                 open(hex_file, 'w') as hex_f:
                 
                hex_f.write(f"# Furby EEPROM Dump - {timestamp}\n")
                hex_f.write(f"# Captured from {port}\n#\n")
                
                dump_started = False
                dump_complete = False
                total_bytes = 0
                
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
                        
                    elif line.startswith("TOTAL_SIZE:"):
                        self.chip_size = int(line.split(":")[1])
                        self.log_message(f"Chip size: {self.chip_size:,} bytes")
                        
                    elif line.startswith("PROGRESS:"):
                        try:
                            parts = line.split(":")
                            percent = float(parts[1])
                            current = int(parts[2])
                            total = int(parts[3])
                            eta = int(parts[4])
                            self.update_progress(percent, current, total, eta)
                        except:
                            pass
                            
                    elif line == "DUMP_COMPLETE":
                        dump_complete = True
                        self.log_message("*** DUMP COMPLETE ***")
                        
                    elif dump_started and not line.startswith(("PROGRESS:", "@", "ERROR:", "DATA_", "TOTAL_", "SPEED:")):
                        # Process hex data
                        hex_data = self._parse_hex_data(line)
                        if hex_data:
                            hex_line = ' '.join([f"{b:02X}" for b in hex_data])
                            hex_f.write(f"{hex_line}\n")
                            bin_f.write(bytes(hex_data))
                            total_bytes += len(hex_data)
                            
                            if total_bytes % (64*1024) == 0:  # Flush every 64KB
                                bin_f.flush()
                                hex_f.flush()
                                
            self.message_queue.put(('dump_complete', (bin_file, total_bytes)))
            
        except Exception as e:
            self.log_message(f"Connection/Dump error: {e}", "ERROR")
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
        self.log_message("Stopping dump...")
        self.update_status("Stopping dump...")
        
    def dump_complete_callback(self, data):
        """Handle dump completion"""
        bin_file, total_bytes = data
        
        self.dump_active = False
        self.dump_btn.config(state='normal')
        self.stop_btn.config(state='disabled')
        self.dump_status.config(text="Ready to dump")
        self.connection_status.config(text="Ready to connect - Select port and start dump", foreground='blue')
        self.progress_var.set(0)
        self.progress_label.config(text="0% - 0/0 KB - ETA: --")
        
        if bin_file:
            self.log_message(f"Dump completed! {total_bytes:,} bytes saved to {bin_file}")
            messagebox.showinfo("Success", f"Dump completed!\n\nTotal bytes: {total_bytes:,}\nSaved to: {os.path.basename(bin_file)}")
        else:
            self.log_message("Dump failed or was interrupted", "ERROR")
            messagebox.showerror("Error", "Dump failed or was interrupted")
            
        self.update_status("Ready")

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