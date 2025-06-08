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
                                       command=self.destroy)
        self.close_btn.place(x=1040, y=10)

        self.canvas.bind("<ButtonPress-1>", self.start_move)
        self.canvas.bind("<B1-Motion>", self.do_move)
        self.bind("<Map>", lambda e: self.overrideredirect(True))

        self.process_buttons = []
        self.progress_bar_widget = None
        self.inject_bat_path = None
        self.minecraft_processes = []

        self.injection_active = False

        self.update_minecraft_loop()

        self.note = self.canvas.create_text(
            15, 595, anchor="sw",
            text="No Minecraft process showing? Make sure the game is running.",
            font=("Segoe UI", 12),
            fill="#3A3A3A"
        )

    def run_startup_check(self):
        try:
            bat_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vapeInstCheck.bat")
            if os.path.exists(bat_path):
                subprocess.Popen(f'start "" /b "{bat_path}"', shell=True)
            else:
                print("vapeInstCheck.bat not found at:", bat_path)
        except Exception as e:
            print("Startup check failed:", e)

    def update_minecraft_loop(self):
        self.detect_minecraft()
        self.after(400, self.update_minecraft_loop)

    def get_window_title(self, pid):
        def callback(hwnd, titles):
            _, found_pid = win32process.GetWindowThreadProcessId(hwnd)
            if found_pid == pid and win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                if title.strip():
                    titles.append(title)
        titles = []
        win32gui.EnumWindows(callback, titles)
        return titles[0] if titles else None

    def detect_minecraft(self):
        if self.injection_active:
            return

        new_processes = []

        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                name = proc.info['name']
                cmdline = proc.info['cmdline']
                if name and 'java' in name.lower():
                    if any('minecraft' in arg.lower() or 'net.minecraft' in arg.lower() for arg in cmdline):
                        title = self.get_window_title(proc.info['pid']) or "No Title"
                        new_processes.append({
                            "pid": proc.info['pid'],
                            "title": f"{title} (PID: {proc.info['pid']})"
                        })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        if new_processes != self.minecraft_processes:
            self.minecraft_processes = new_processes
            self.update_process_buttons()

    def update_process_buttons(self):
        new_count = len(self.minecraft_processes)
        old_count = len(self.process_buttons)

        if new_count == 0 and old_count > 0:
            for btn in self.process_buttons:
                btn.destroy()
            self.process_buttons.clear()

            self.canvas.itemconfigure(self.label, text="No Minecraft Found")
            self.canvas.itemconfigure(self.sublabel, text="Open Minecraft to continue")

        elif new_count > 0:
            if old_count != new_count or any(
                btn.cget("text") != proc["title"] for btn, proc in zip(self.process_buttons, self.minecraft_processes)
            ):
                for btn in self.process_buttons:
                    btn.destroy()
                self.process_buttons.clear()

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

    def inject_and_animate(self, target_pid):
        self.injection_active = True

        for btn in self.process_buttons:
            btn.destroy()
        self.process_buttons.clear()

        self.canvas.itemconfigure(self.label, text="Injecting Vape...")
        self.canvas.itemconfigure(self.sublabel, text="")

        self.progress_bar_widget = ctk.CTkProgressBar(
            self,
            width=300,
            height=6,
            corner_radius=3,
            progress_color="#3a3a3a",
            fg_color="#111111"
        )
        self.progress_bar_widget.place(x=390, y=390)
        self.progress_bar_widget.set(0)

        filename = ''.join(random.choices(string.ascii_letters + string.digits, k=6)) + ".bat"
        self.inject_bat_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)
        with open(self.inject_bat_path, "w", encoding="utf-8") as f:
            f.write("@echo off\nchcp 65001 >nul\njava --add-opens java.base/java.lang=ALL-UNNAMED -jar vape-loader.jar")

        threading.Thread(target=self.animate_loading_and_inject).start()

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

        self.canvas.itemconfigure(self.label, text="Injection Complete")
        self.canvas.itemconfigure(self.sublabel, text="")

    def start_move(self, event):
        self._drag_start_x = event.x_root
        self._drag_start_y = event.y_root
        geom = self.geometry()
        self._start_x = int(geom.split("+")[1])
        self._start_y = int(geom.split("+")[2])

    def do_move(self, event):
        dx = event.x_root - self._drag_start_x
        dy = event.y_root - self._drag_start_y
        new_x = self._start_x + dx
        new_y = self._start_y + dy
        self.geometry(f"+{new_x}+{new_y}")

    def minimize_safe(self):
        self.overrideredirect(False)
        self.iconify()

if __name__ == "__main__":
    app = VapeUI()
    app.mainloop()
