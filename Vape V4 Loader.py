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

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

class VapeUI(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.run_startup_check()

        self.geometry("1080x615")
        self.title("Vape V4")
        self.configure(fg_color="#111111")
        self.wm_attributes("-topmost", True)
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

        self.label = self.canvas.create_text(540, 300, text="Select a Minecraft to use",
                                             font=("Segoe UI", 16, "bold"), fill="#cccccc")
        self.sublabel = self.canvas.create_text(540, 325, text="Make sure game is fully loaded first",
                                                font=("Segoe UI", 13), fill="#666666")

        self.minimize_btn = ctk.CTkButton(self, text="–", width=30, height=25,
                                          fg_color="#222", hover_color="#444",
                                          command=self.minimize_safe)
        self.minimize_btn.place(x=1000, y=10)

        self.close_btn = ctk.CTkButton(self, text="✕", width=30, height=25,
                                       fg_color="#222", hover_color="#c00",
                                       command=self.fade_out_and_close)
        self.close_btn.place(x=1040, y=10)

        self.canvas.bind("<ButtonPress-1>", self.start_move)
        self.canvas.bind("<B1-Motion>", self.do_move)
        self.canvas.bind("<ButtonRelease-1>", self.end_move)
        self.bind("<Map>", lambda e: self.overrideredirect(True))

        self.process_buttons = []
        self.progress_bar_widget = None
        self.inject_bat_path = None
        self.minecraft_processes = []
        self.injection_active = False
        self.last_process_check = 0
        self.process_cache = {}
        self.is_dragging = False
        self.last_drag_time = 0
        self.check_scheduled = False

        # Persistent background scanner
        self.scanner_thread = threading.Thread(target=self.process_scanner_loop, daemon=True)
        self.scanner_thread.start()

        self.note = self.canvas.create_text(
            15, 595, anchor="sw",
            text="No Minecraft process showing? Make sure the game is running.",
            font=("Segoe UI", 12),
            fill="#3A3A3A"
        )

    def process_scanner_loop(self):
        """Persistent background scanner for Minecraft processes"""
        while True:
            if not self.is_dragging and not self.injection_active:
                self.detect_minecraft()

            # Faster scanning when no processes found
            if not self.minecraft_processes:
                time.sleep(1.0)
            else:
                time.sleep(2.5)

    def run_startup_check(self):
        try:
            bat_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vapeInstCheck.bat")
            if os.path.exists(bat_path):
                subprocess.Popen(f'start "" /b "{bat_path}"', shell=True)
        except Exception as e:
            print("Startup check failed:", e)

    def fade_in(self, current=0.0):
        step = 1 / (0.4 * 50)
        if current < 1.0:
            self.attributes("-alpha", current)
            self.after(20, lambda: self.fade_in(current + step))
        else:
            self.attributes("-alpha", 1.0)

    def fade_out_and_close(self, current=1.0):
        step = 1 / (0.2 * 50)
        if current > 0.0:
            self.attributes("-alpha", current)
            self.after(20, lambda: self.fade_out_and_close(current - step))
        else:
            self.destroy()

    def detect_minecraft(self):
        """Robust Minecraft detection with command-line verification"""
        try:
            if self.injection_active or self.is_dragging:
                return

            current_time = time.time()
            found_pids = set()

            # Scan all processes
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    # Skip processes without names
                    if not proc.info['name']:
                        continue

                    # Check for Java processes
                    if 'java' in proc.info['name'].lower() or 'javaw' in proc.info['name'].lower():
                        # Verify this is actually Minecraft
                        cmdline = " ".join(proc.info.get('cmdline', [])).lower()
                        if 'minecraft' in cmdline or 'net.minecraft' in cmdline:
                            found_pids.add(proc.info['pid'])
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            # Process new Minecraft instances
            new_processes = []
            for pid in found_pids:
                # Use cached title if available
                if pid in self.process_cache:
                    title = self.process_cache[pid]
                else:
                    # Fetch window title for new process
                    title = self.get_window_title_fast(pid)
                    self.process_cache[pid] = title

                if title:
                    new_processes.append({
                        "pid": pid,
                        "title": f"{title} (PID: {pid})"
                    })

            # Only update if changes detected
            new_pids = sorted(p['pid'] for p in new_processes)
            old_pids = sorted(p['pid'] for p in self.minecraft_processes)

            if new_pids != old_pids:
                self.minecraft_processes = new_processes
                self.update_process_buttons()

        except Exception as e:
            print("Error detecting Minecraft:", e)

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

        data = {'done': False, 'title': None}
        try:
            # Only enumerate for 100ms max
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

            if not self.minecraft_processes:
                self.canvas.itemconfigure(self.label, text="No Minecraft Found")
                self.canvas.itemconfigure(self.sublabel, text="Open Minecraft to continue")
                return

            self.canvas.itemconfigure(self.label, text="Select a Minecraft to use")
            self.canvas.itemconfigure(self.sublabel, text="Make sure game is fully loaded first")

            for i, proc in enumerate(self.minecraft_processes):
                button = ctk.CTkButton(self, text=proc["title"], width=250, height=40,
                                       corner_radius=6,
                                       font=("Segoe UI", 14),
                                       fg_color="#1e1e1e", hover_color="#2c2c2c",
                                       text_color="#cccccc",
                                       border_color="#333", border_width=2,
                                       command=lambda p=proc['pid']: self.inject_and_animate(p))
                button.place(x=415, y=360 + i * 50)
                self.process_buttons.append(button)

        # Ensure UI updates happen on main thread
        self.after(0, update_ui)

    def inject_and_animate(self, target_pid):
        self.injection_active = True

        # Clear UI immediately
        for btn in self.process_buttons:
            btn.destroy()
        self.process_buttons.clear()

        self.canvas.itemconfigure(self.label, text="")
        self.canvas.itemconfigure(self.sublabel, text="")

        self.progress_bar_widget = ctk.CTkProgressBar(
            self,
            width=300,
            height=6,
            corner_radius=3,
            progress_color="#3a3a3a",
            fg_color="#111111"
        )
        self.progress_bar_widget.place(x=390, y=300)
        self.progress_bar_widget.set(0)

        filename = ''.join(random.choices(string.ascii_letters + string.digits, k=6)) + ".bat"
        self.inject_bat_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)
        with open(self.inject_bat_path, "w", encoding="utf-8") as f:
            f.write("@echo off\nchcp 65001 >nul\njava --add-opens java.base/java.lang=ALL-UNNAMED -jar vape-loader.jar")

        threading.Thread(target=self.animate_loading_and_inject, daemon=True).start()

    def animate_loading_and_inject(self):
        total_steps = 1000
        duration = 3.605
        injected = False

        for i in range(total_steps + 1):
            progress = i / total_steps
            self.progress_bar_widget.set(progress)

            if not injected and progress >= 0.01:
                injected = True
                try:
                    subprocess.Popen(self.inject_bat_path, creationflags=subprocess.CREATE_NO_WINDOW)
                except Exception:
                    pass

            time.sleep(duration / total_steps)

        self.collapse_bar_and_exit()

    def collapse_bar_and_exit(self):
        initial_width = 300
        steps = int(1.4 * 50)

        def collapse(step=0):
            if step == int(1.2 * 50):
                self.fade_out_and_close()

            if step <= steps:
                scale = 1 - (step / steps)
                width = max(int(initial_width * scale), 1)
                self.progress_bar_widget.configure(width=width)
                self.progress_bar_widget.place(x=540 - width 
                self.after(20, lambda: collapse(step + 1))

        collapse()

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
        # 60fps dragging (16ms)
        if current_time - self.last_drag_time > 0.016:
            dx = event.x_root - self._drag_start_x
            dy = event.y_root - self._drag_start_y
            new_x = self._start_x + dx
            new_y = self._start_y + dy
            self.geometry(f"+{new_x}+{new_y}")
            self.last_drag_time = current_time

    def end_move(self, event):
        self.is_dragging = False
        # Trigger immediate scan after dragging stops
        threading.Thread(target=self.detect_minecraft, daemon=True).start()

    def minimize_safe(self):
        self.overrideredirect(False)
        self.iconify()
        self.is_dragging = False

if __name__ == "__main__":
    app = VapeUI()
    app.mainloop()
