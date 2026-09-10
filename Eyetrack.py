import os
import tkinter as tk
from datetime import datetime
from tkinter import ttk

import cv2
import openpyxl  # Added for Excel logging
from PIL import Image, ImageTk

from controller import FaceHandController


class PremiumApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Face & Hand Controlled Mouse")
        self.root.geometry("1280x800")
        self.root.minsize(1000, 600)
        self.root.configure(bg='#f0f2f5')

        # Variables
        self.status_var = tk.StringVar(value="System ready")
        self.quick_buttons = []
        self.smooth_var = tk.IntVar(value=2)
        self.click_duration_var = tk.DoubleVar(value=2.0)
        self.excel_file = "tracking_details.xlsx"

        # Initialize the Excel Log
        self.init_excel_log()

        # Setup custom style
        self.setup_styles()

        # Build UI with grid layout (half video, half controls)
        self.setup_ui_grid()

        # Controller instance
        self.controller = FaceHandController(
            callback=self.update_gui,
            on_long_click=self.handle_button_click
        )

        # Update button positions after window is ready
        self.root.after(500, self.update_button_rects)
        self.root.bind("<Configure>", self.on_window_resize)

        # Bind sensitivity changes
        self.smooth_var.trace_add('write', self.update_sensitivity)
        self.click_duration_var.trace_add('write', self.update_click_duration)

    def init_excel_log(self):
        """Creates the Excel file with headers if it doesn't exist."""
        if not os.path.exists(self.excel_file):
            try:
                wb = openpyxl.Workbook()
                ws = wb.active
                ws.title = "Action Logs"
                ws.append(["Date", "Time", "Action"])
                wb.save(self.excel_file)
                print(f"Created new tracking file: {self.excel_file}")
            except Exception as e:
                print(f"Error creating Excel file: {e}")

    def log_action(self, action):
        """Appends a new action to the Excel file with the current timestamp."""
        try:
            now = datetime.now()
            date_str = now.strftime("%Y-%m-%d")
            time_str = now.strftime("%H:%M:%S")
            
            wb = openpyxl.load_workbook(self.excel_file)
            ws = wb.active
            ws.append([date_str, time_str, action])
            wb.save(self.excel_file)
            print(f"Logged to Excel: {action}")
        except Exception as e:
            print(f"Failed to log action to Excel: {e}")

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')

        bg_color = '#f0f2f5'
        fg_color = '#1a1a1a'
        accent = '#2c7da0'
        accent_light = '#61a5c2'
        button_bg = '#ffffff'
        button_active = '#e9ecef'

        style.configure('TFrame', background=bg_color)
        style.configure('TLabel', background=bg_color, foreground=fg_color, font=('Segoe UI', 10))
        style.configure('TLabelframe', background=bg_color, foreground=fg_color, font=('Segoe UI', 10, 'bold'))
        style.configure('TLabelframe.Label', background=bg_color, foreground=fg_color, font=('Segoe UI', 10, 'bold'))
        style.configure('TButton', background=button_bg, foreground=fg_color, font=('Segoe UI', 10), borderwidth=0, focusthickness=0)
        style.map('TButton', background=[('active', button_active), ('pressed', '#dee2e6')])
        style.configure('Accent.TButton', background=accent, foreground='white')
        style.map('Accent.TButton', background=[('active', accent_light), ('pressed', '#1f5068')])

    def setup_ui_grid(self):
        # Main container using grid with equal columns (half-half)
        main_container = ttk.Frame(self.root, padding=20)
        main_container.grid(row=0, column=0, sticky="nsew")
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        main_container.grid_rowconfigure(0, weight=1)
        main_container.grid_columnconfigure(0, weight=1)  # video takes half
        main_container.grid_columnconfigure(1, weight=1)  # controls takes half

        # Left panel: Video feed (half width)
        video_card = ttk.LabelFrame(main_container, text="📷 Camera Feed", padding=10)
        video_card.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        self.video_label = ttk.Label(video_card, background='#000000')
        self.video_label.pack(fill=tk.BOTH, expand=True)

        # Right panel: Controls (half width)
        controls_card = ttk.Frame(main_container)
        controls_card.grid(row=0, column=1, sticky="nsew", padx=(10, 0))

        # Header
        header = ttk.Label(controls_card, text="Hands‑Free Control Panel", font=('Segoe UI', 16, 'bold'))
        header.pack(pady=(0, 15))

        # Buttons row
        btn_frame = ttk.Frame(controls_card)
        btn_frame.pack(pady=5, fill=tk.X)

        self.start_btn = ttk.Button(btn_frame, text="▶ Start", command=self.start_controller, style='Accent.TButton')
        self.start_btn.pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)

        self.stop_btn = ttk.Button(btn_frame, text="⏹ Stop", command=self.stop_controller, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)

        self.keyboard_btn = ttk.Button(btn_frame, text="⌨ Keyboard", command=self.open_keyboard)
        self.keyboard_btn.pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)

        self.emergency_btn = tk.Button(
            btn_frame, text="🚨 EMERGENCY", command=self.emergency_alert,
            bg='#dc3545', fg='white', font=('Segoe UI', 10, 'bold'),
            relief=tk.FLAT, activebackground='#c82333', activeforeground='white'
        )
        self.emergency_btn.pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)

        self.exit_btn = ttk.Button(btn_frame, text="✖ Exit", command=self.exit_app)
        self.exit_btn.pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)

        # Status card
        status_card = ttk.LabelFrame(controls_card, text="Status", padding=10)
        status_card.pack(fill=tk.X, pady=15)

        self.status_label = ttk.Label(status_card, textvariable=self.status_var, font=('Segoe UI', 10, 'italic'), foreground='#2c7da0')
        self.status_label.pack(anchor=tk.W)

        # Sensitivity settings
        sens_card = ttk.LabelFrame(controls_card, text="⚙ Sensitivity", padding=10)
        sens_card.pack(fill=tk.X, pady=10)

        ttk.Label(sens_card, text="Mouse Smoothing:").grid(row=0, column=0, sticky=tk.W, pady=5)
        smooth_scale = ttk.Scale(sens_card, from_=1, to=10, variable=self.smooth_var, orient=tk.HORIZONTAL)
        smooth_scale.grid(row=0, column=1, sticky=tk.EW, padx=10)
        ttk.Label(sens_card, textvariable=self.smooth_var).grid(row=0, column=2)

        ttk.Label(sens_card, text="Click Duration (s):").grid(row=1, column=0, sticky=tk.W, pady=5)
        duration_scale = ttk.Scale(sens_card, from_=0.5, to=5.0, variable=self.click_duration_var, orient=tk.HORIZONTAL)
        duration_scale.grid(row=1, column=1, sticky=tk.EW, padx=10)
        ttk.Label(sens_card, textvariable=self.click_duration_var).grid(row=1, column=2)

        sens_card.columnconfigure(1, weight=1)

        # Quick actions
        quick_card = ttk.LabelFrame(controls_card, text="⚡ Quick Actions (hover & close eyes)", padding=10)
        quick_card.pack(fill=tk.X, pady=10)

        quick_actions = [
            ("🍔 Hungry", "hungry"), ("💧 Thirsty", "thirsty"), ("🆘 Help", "help"),
            ("🚨 Emergency", "emergency"), ("🚪 Take me out", "take me out"), ("💧 Water", "water"),
            ("🚽 Bathroom", "bathroom"), ("🤕 Pain", "pain"), ("⚠️ I need attention", "attention")
        ]
        for text, phrase in quick_actions:
            btn = ttk.Button(quick_card, text=text, width=18)
            btn.pack(pady=2, fill=tk.X)
            self.quick_buttons.append({'widget': btn, 'phrase': phrase, 'rect': None})

        # Test TTS
        test_btn = ttk.Button(controls_card, text="🔊 Test Voice", command=self.test_tts)
        test_btn.pack(pady=5, fill=tk.X)

        # Instructions
        instr_card = ttk.LabelFrame(controls_card, text="📖 Quick Guide", padding=10)
        instr_card.pack(fill=tk.BOTH, expand=True, pady=10)

        instructions = [
            "▶ Start: Nod 3x / open hand / click Start",
            "⏹ Stop: head left→right→left / fist / Stop button",
            "🖱 Move: move your nose (laser pointer)",
            "👆 Click: close eyes for 2 seconds",
            "⚡ Quick actions: hover + close eyes",
            "⌨ Keyboard: click button or show both open hands",
            "🚨 Emergency: sends email alert"
        ]
        for line in instructions:
            ttk.Label(instr_card, text=line, justify=tk.LEFT).pack(anchor=tk.W, pady=2)

    def update_sensitivity(self, *args):
        if hasattr(self, 'controller'):
            self.controller.smooth_factor = self.smooth_var.get()
            self.controller.LONG_CLOSURE_DURATION = self.click_duration_var.get()

    def update_click_duration(self, *args):
        if hasattr(self, 'controller'):
            self.controller.LONG_CLOSURE_DURATION = self.click_duration_var.get()

    def update_button_rects(self):
        for btn_info in self.quick_buttons:
            widget = btn_info['widget']
            widget.update_idletasks()
            x = widget.winfo_rootx()
            y = widget.winfo_rooty()
            w = widget.winfo_width()
            h = widget.winfo_height()
            btn_info['rect'] = (x, y, x + w, y + h)

    def on_window_resize(self, event):
        self.root.after(100, self.update_button_rects)

    def handle_button_click(self, x, y):
        for btn_info in self.quick_buttons:
            rect = btn_info['rect']
            if rect and rect[0] <= x <= rect[2] and rect[1] <= y <= rect[3]:
                phrase = btn_info['phrase']
                
                # Speak the phrase
                self.controller.speak_repeated(phrase, 3)

                # Log to Excel
                self.log_action(f"Quick Action Triggered: {phrase.capitalize()}")

                # Background email logic
                if phrase == "emergency":
                    self.controller.send_emergency_email()
                
                return True
        return False

    def emergency_alert(self):
        self.log_action("Emergency Dashboard Button Clicked")
        self.controller.send_emergency_email()

    def start_controller(self):
        self.log_action("Controller Started")
        self.controller.start()
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.status_var.set("Controller started – move your nose")

    def stop_controller(self):
        self.log_action("Controller Stopped")
        self.controller.stop()
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.status_var.set("Controller stopped")

    def open_keyboard(self):
        self.log_action("Keyboard Opened")
        self.controller.open_keyboard()

    def test_tts(self):
        self.log_action("Voice Tested")
        self.controller.speak_repeated("Voice test successful", 1)

    def exit_app(self):
        self.log_action("Application Exited")
        self.controller.stop()
        self.root.quit()
        self.root.destroy()

    def update_gui(self, frame, status_text):
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(frame_rgb)
        video_width = self.video_label.winfo_width()
        video_height = self.video_label.winfo_height()
        if video_width > 1 and video_height > 1:
            img = img.resize((video_width, video_height), Image.Resampling.LANCZOS)
        imgtk = ImageTk.PhotoImage(image=img)
        self.root.after(0, self._display_frame, imgtk, status_text)

    def _display_frame(self, imgtk, status_text):
        self.video_label.config(image=imgtk)
        self.video_label.image = imgtk
        self.status_var.set(status_text)

if __name__ == "__main__":
    root = tk.Tk()
    app = PremiumApp(root)
    root.mainloop()