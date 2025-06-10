import customtkinter as ctk
from PIL import Image, ImageTk
import psutil
import subprocess
import os
import random
import string
import threading
import time
import win32gui
import win32process
import webbrowser
from datetime import datetime
import re
import ctypes  # Added for admin privileges

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

class SplashScreen(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.geometry("600x400")
        self.title("Vape V4 - Dependency Check")
        self.configure(fg_color="#111111")
        self.resizable(False, False)
        
        # Logo
        logo_raw = Image.open("vape.png").resize((200, 56))
        self.logo_tk = ImageTk.PhotoImage(logo_raw)
        self.logo_label = ctk.CTkLabel(self, image=self.logo_tk, text="")
        self.logo_label.pack(pady=20)
        
        # Title
        self.title_label = ctk.CTkLabel(
            self, 
            text="Checking Dependencies...",
            font=("Segoe UI", 16, "bold"),
            text_color="#cccccc"
        )
        self.title_label.pack(pady=10)
        
        # Status Frame
        self.status_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.status_frame.pack(pady=20, padx=20, fill="x")
        
        # Configure grid for status frame
        self.status_frame.columnconfigure(0, weight=1)  # Status label column
        self.status_frame.columnconfigure(1, weight=0)  # Button column
        
        # Java Check
        self.java_status = ctk.CTkLabel(
            self.status_frame,
            text="Java 17+ : Checking...",
            font=("Segoe UI", 12),
            text_color="#aaaaaa"
        )
        self.java_status.grid(row=0, column=0, sticky="w", padx=10, pady=5)
        
        # Time Check with button
        self.time_status = ctk.CTkLabel(
            self.status_frame,
            text="System Time : Checking...",
            font=("Segoe UI", 12),
            text_color="#aaaaaa"
        )
        self.time_status.grid(row=1, column=0, sticky="w", padx=10, pady=5)
        
        # NEW: "Set Automatically" button
        self.set_time_btn = ctk.CTkButton(
            self.status_frame,
            text="Set Automatically",
            width=120,
            state="disabled",
            fg_color="#222",
            hover_color="#333",
            command=self.set_system_time
        )
        self.set_time_btn.grid(row=1, column=1, padx=(0, 10), pady=5)
        
        # Download button (initially hidden)
        self.download_btn = ctk.CTkButton(
            self, 
            text="Download Java 17",
            fg_color="#222",
            hover_color="#333",
            command=self.download_java,
            state="disabled"
        )
        
        # Launch button (initially disabled)
        self.launch_btn = ctk.CTkButton(
            self, 
            text="Launch Vape V4",
            fg_color="#1a5e1a",
            hover_color="#2a7e2a",
            command=self.launch_main_app,
            state="disabled"
        )
        self.launch_btn.pack(pady=20)
        
        # Exit button
        self.exit_btn = ctk.CTkButton(
            self, 
            text="Exit",
            fg_color="#222",
            hover_color="#333",
            command=self.destroy
        )
        self.exit_btn.pack(pady=5)
        
        # Start dependency checks
        self.check_dependencies()
        
    def check_dependencies(self):
        """Check all required dependencies"""
        threading.Thread(target=self.check_java, daemon=True).start()
        threading.Thread(target=self.check_time, daemon=True).start()
        
    def check_java(self):
        """Check if Java 17+ is installed"""
        try:
            # Run java -version command
            result = subprocess.run(
                ["java", "-version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',
                errors='ignore',
                creationflags=subprocess.CREATE_NO_WINDOW,
                timeout=5
            )
            
            version_output = result.stdout

            # Parse Java version
            version_match = re.search(r'version "(\d+)\.', version_output)
            
            if version_match:
                major_version = int(version_match.group(1))
                if major_version >= 17:
                    self.update_java_status("Java 17+ : Installed", "#4CAF50")
                    # Disable download button if Java is installed
                    self.download_btn.configure(state="disabled")
                    return True
                else:
                    self.update_java_status(f"Java 17+ required (found {major_version})", "#F44336")
                    self.show_download_button()
            else:
                self.update_java_status("Java not found", "#F44336")
                self.show_download_button()
                
        except FileNotFoundError:
            self.update_java_status("Java not installed", "#F44336")
            self.show_download_button()
        except Exception as e:
            self.update_java_status(f"Error: {str(e)}", "#F44336")
            self.show_download_button()
            
        return False
        
    def update_java_status(self, text, color):
        """Update Java status label"""
        self.java_status.configure(text=text, text_color=color)
        self.enable_launch_if_ready()
        
    def show_download_button(self):
        """Show Java download button"""
        self.download_btn.pack(pady=10)
        self.download_btn.configure(state="normal")
        
    def download_java(self):
        """Open Java download URL in browser"""
        webbrowser.open("https://download.oracle.com/java/17/archive/jdk-17.0.6_windows-x64_bin.exe")
        
    def check_time(self):
        """Check if system time is in safe zone"""
        safe_date = datetime(2022, 9, 20)
        current_date = datetime.now()
        
        if current_date.date() == safe_date.date():
            self.update_time_status("System Time : Safe Zone (2022-09-20)", "#4CAF50", True)
            return True
        else:
            self.update_time_status(
                f"System Time : {current_date.strftime('%Y-%m-%d')} (requires 2022-09-20)", 
                "#F44336",
                False
            )
        return False
        
    def update_time_status(self, text, color, is_safe):
        """Update time status label and button state"""
        self.time_status.configure(text=text, text_color=color)
        # Enable/disable set time button based on time status
        self.set_time_btn.configure(state="normal" if not is_safe else "disabled")
        self.enable_launch_if_ready()
        
    # NEW: System time setting function
    def set_system_time(self):
        """Attempt to set system time to required date (requires admin privileges)"""
        try:
            # Format: MM-DD-YYYY
            target_date = "09-20-2022"
            
            # Request admin privileges for time change
            if ctypes.windll.shell32.IsUserAnAdmin():
                # We already have admin privileges
                subprocess.run(f'date {target_date}', shell=True, check=True)
                self.update_time_status("System time set successfully! Restarting check...", "#4CAF50", False)
            else:
                # Re-run with admin privileges
                ctypes.windll.shell32.ShellExecuteW(
                    None, "runas", "cmd.exe", f"/c date {target_date}", None, 1
                )
                self.update_time_status("Admin request sent. Please accept UAC prompt.", "#FF9800", False)
            
            # Re-check time after a short delay
            threading.Timer(3.0, self.check_time).start()
            
        except Exception as e:
            self.update_time_status(f"Error setting time: {str(e)}", "#F44336", False)
        
    def enable_launch_if_ready(self):
        """Enable launch button if all dependencies are met"""
        java_ok = "Installed" in self.java_status.cget("text")
        time_ok = "Safe Zone" in self.time_status.cget("text")
        
        if java_ok and time_ok:
            self.launch_btn.configure(state="normal")
            self.title_label.configure(text="Dependencies Met - Ready to Launch")
            
    def launch_main_app(self):
        """Launch the main Vape application"""
        self.destroy()
        app = VapeUI()
        app.mainloop()

class VapeUI(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.run_startup_check()

        self.geometry("1080x615")
        self.title("Vape V4")
        self.configure(fg_color="#111111")
        self.wm_attributes("-topmost", False)
        self.overrideredirect(True)

        self.attributes("-alpha", 0)
        self.fade_in()

        self.canvas = ctk.CTkCanvas(self, width=1080, height=615, highlightthickness=0, bd=0, bg="#111111")
        self.canvas.pack(fill="both", expand=True)

        bg_image_raw = Image.open("bg.png").resize((1080, 615))
        self.bg_image = ImageTk.PhotoImage(bg_image_raw)
        self.canvas.create_image(0, 0, anchor="nw", image=self.bg_image)

        self.logo_raw = Image.open("vape.png").resize((220, 61))
        self.logo_tk = ImageTk.PhotoImage(self.logo_raw)
        self.canvas.create_image(540, 220, image=self.logo_tk)

        self.label = self.canvas.create_text(540, 300, text="Select a Minecraft Process",
                                             font=("Segoe UI", 16, "bold"), fill="#cccccc")
        self.sublabel = self.canvas.create_text(540, 325, text="Make sure game is fully loaded first",
                                                font=("Segoe UI", 13), fill="#666666")

        self.minimize_btn = ctk.CTkButton(self, text="–", width=30, height=25,
                                          fg_color="#222", hover_color="#444",
                                          command=self.minimize_safe)
        self.minimize_btn.place(x=1000, y=10)

        self.close_btn = ctk.CTkButton(self, text="✕", width=30, height=25,
                                       fg_color="#222", hover_color="#c00",
                                       command=self.fade_out)
        self.close_btn.place(x=1040, y=10)

        self.canvas.bind("<ButtonPress-1>", self.start_move)
        self.canvas.bind("<B1-Motion>", self.do_move)
        self.canvas.bind("<ButtonRelease-1>", self.end_move)
        self.bind("<Map>", lambda e: self.overrideredirect(True))

        self.process_buttons = []
        self.progress_bar_widget = None
        self.progress_frame = None
        self.inject_bat_path = None
        self.java_processes = []  # Changed from minecraft_processes
        self.injection_active = False
        self.process_cache = {}
        self.is_dragging = False
        self.last_drag_time = 0
        self.last_process_check = 0
        self.check_scheduled = False

        # Start the scanner immediately and schedule regular checks
        self.scanner_thread = threading.Thread(target=self.process_scanner_loop, daemon=True)
        self.scanner_thread.start()
        
        # Start the UI update scheduler
        self.schedule_process_check()

        self.note = self.canvas.create_text(
            15, 595, anchor="sw",
            text="No Minecraft processes showing? Make sure the game is running.",
            font=("Segoe UI", 12),
            fill="#3A3A3A"
        )
        
    def schedule_process_check(self):
        """Schedule process check every 2000ms"""
        if not self.injection_active:
            self.after(2000, self.schedule_process_check)
            self.detect_java_processes()

    def process_scanner_loop(self):
        """Persistent background scanner for Java processes with 2000ms interval"""
        while True:
            try:
                if not self.is_dragging and not self.injection_active:
                    self.detect_java_processes()
                time.sleep(2.0)
            except Exception as e:
                print(f"Scanner error: {e}")
                time.sleep(2.0)

    def run_startup_check(self):
        try:
            bat_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vapeInstCheck.bat")
            if os.path.exists(bat_path):
                subprocess.Popen(f'cmd /c start "" /WAIT "{bat_path}"', shell=True)
        except Exception as e:
            print("Startup check failed:", e)

    def fade_in(self, current=0.0):
        step = 1 / (0.4 * 50)
        if current < 1.0:
            self.attributes("-alpha", current)
            self.after(20, lambda: self.fade_in(current + step))
        else:
            self.attributes("-alpha", 1.0)

    def fade_out(self):
        def fade(step=0):
            alpha = max(0, 1.0 - step * 0.05)
            self.attributes("-alpha", alpha)
            if alpha <= 0:
                self.destroy()
            else:
                self.after(50, lambda: fade(step + 1))

        fade()

    def detect_java_processes(self):
        """Detect all Java processes and their window titles"""
        try:
            if self.injection_active or self.is_dragging:
                return

            found_pids = set()

            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    name = proc.info['name']
                    if not name:
                        continue

                    # Detect all Java processes (java.exe or javaw.exe)
                    name_lower = name.lower()
                    if name_lower in ['java.exe', 'javaw.exe']:
                        found_pids.add(proc.info['pid'])
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            new_processes = []
            for pid in found_pids:
                if pid in self.process_cache:
                    title = self.process_cache[pid]
                else:
                    title = self.get_window_title_fast(pid)
                    # Use "No Title" if we couldn't get a window title
                    if not title:
                        title = "No Title"
                    self.process_cache[pid] = title

                new_processes.append({
                    "pid": pid,
                    "title": f"{title} (PID: {pid})"
                })

            new_pids = sorted(p['pid'] for p in new_processes)
            old_pids = sorted(p['pid'] for p in self.java_processes)

            if new_pids != old_pids:
                self.java_processes = new_processes
                self.update_process_buttons()

        except Exception as e:
            print("Error detecting Java processes:", e)

    def get_window_title_fast(self, pid):
        """Optimized window title fetcher with timeout"""
        def callback(hwnd, data):
            if data['done']:
                return
            try:
                _, found_pid = win32process.GetWindowThreadProcessId(hwnd)
                if found_pid == pid and win32gui.IsWindowVisible(hwnd):
                    title = win32gui.GetWindowText(hwnd)
                    if title.strip():
                        data['title'] = title
                        data['done'] = True
            except:
                pass

        data = {'done': False, 'title': "No Title"}  # Default to "No Title"
        try:
            start = time.time()
            while not data['done'] and (time.time() - start) < 0.1:
                win32gui.EnumWindows(callback, data)
        except:
            pass

        return data['title']

    def update_process_buttons(self):
        """Thread-safe UI update"""
        if self.injection_active:
            return

        def update_ui():
            for btn in self.process_buttons:
                btn.destroy()
            self.process_buttons.clear()

            if not self.java_processes:
                self.canvas.itemconfigure(self.label, text="No Minecraft Found")
                self.canvas.itemconfigure(self.sublabel, text="Open Minecraft to continue")
                return

            self.canvas.itemconfigure(self.label, text="Select a Minecraft Process")
            self.canvas.itemconfigure(self.sublabel, text="Make sure game is fully loaded first")

            for i, proc in enumerate(self.java_processes):
                button = ctk.CTkButton(self, text=proc["title"], width=350, height=40,
                                       corner_radius=6,
                                       font=("Segoe UI", 14),
                                       fg_color="#1e1e1e", hover_color="#2c2c2c",
                                       text_color="#cccccc",
                                       border_color="#333", border_width=2,
                                       command=lambda p=proc['pid']: self.inject_and_animate(p))
                button.place(x=365, y=360 + i * 50)
                self.process_buttons.append(button)

        self.after(0, update_ui)

    def inject_and_animate(self, target_pid):
        self.injection_active = True

        for btn in self.process_buttons:
            btn.destroy()
        self.process_buttons.clear()

        self.canvas.itemconfigure(self.label, text="")
        self.canvas.itemconfigure(self.sublabel, text="")

        self.progress_frame = ctk.CTkFrame(self, width=300, height=6, fg_color="transparent")
        self.progress_frame.place(x=390, y=300)

        self.progress_bar_widget = ctk.CTkProgressBar(
            self.progress_frame,
            width=300,
            height=6,
            corner_radius=3,
            progress_color="#3a3a3a",
            fg_color="#111111"
        )
        self.progress_bar_widget.pack(fill="both", expand=True)
        self.progress_bar_widget.set(0)

        filename = ''.join(random.choices(string.ascii_letters + string.digits, k=6)) + ".bat"
        self.inject_bat_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)
        with open(self.inject_bat_path, "w", encoding="utf-8") as f:
            f.write("@echo off\nchcp 65001 >nul\njava --add-opens java.base/java.lang=ALL-UNNAMED -jar vape-loader.jar")

        threading.Thread(target=self.animate_loading_and_inject, args=(target_pid,), daemon=True).start()

    def animate_loading_and_inject(self, target_pid):
        total_steps = 1000
        duration = 3.605
        injected = False

        for i in range(total_steps + 1):
            progress = i / total_steps
            self.progress_bar_widget.set(progress)

            if not injected and progress >= 0.01:
                injected = True
                try:
                    subprocess.Popen(
                        [self.inject_bat_path, str(target_pid)],
                        creationflags=subprocess.CREATE_NO_WINDOW | subprocess.SW_HIDE
                    )
                except Exception as e:
                    print(f"Injection failed: {e}")

            time.sleep(duration / total_steps)

        # When progress reaches 100%, start fading out
        self.fade_out()

    def start_move(self, event):
        self._drag_start_x = event.x_root
        self._drag_start_y = event.y_root
        geom = self.geometry()
        self._start_x = int(geom.split("+")[1])
        self._start_y = int(geom.split("+")[2])
        self.is_dragging = True
        self.last_drag_time = time.time()

    def do_move(self, event):
        current_time = time.time()
        if current_time - self.last_drag_time > 0.016:
            dx = event.x_root - self._drag_start_x
            dy = event.y_root - self._drag_start_y
            new_x = self._start_x + dx
            new_y = self._start_y + dy
            self.geometry(f"+{new_x}+{new_y}")
            self.last_drag_time = current_time

    def end_move(self, event):
        self.is_dragging = False
        # Immediately trigger a new process scan after dragging
        threading.Thread(target=self.detect_java_processes, daemon=True).start()

    def minimize_safe(self):
        self.overrideredirect(False)
        self.iconify()
        self.is_dragging = False

if __name__ == "__main__":
    splash = SplashScreen()
    splash.mainloop()
