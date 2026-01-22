import os
from textwrap import dedent

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
WINDOWS_AUTOCHROME_DIR = os.path.join(BASE_DIR, "WindowsAutochrome")


def ensure_structure():
    os.makedirs(WINDOWS_AUTOCHROME_DIR, exist_ok=True)
    # profiles folder (sub-profiles will be created automatically at runtime)
    profiles_dir = os.path.join(WINDOWS_AUTOCHROME_DIR, "profiles")
    os.makedirs(profiles_dir, exist_ok=True)
    # bin folder (user will place portable Chromium here)
    bin_dir = os.path.join(WINDOWS_AUTOCHROME_DIR, "bin")
    os.makedirs(bin_dir, exist_ok=True)
    return profiles_dir, bin_dir


def write_main_py():
    main_py_path = os.path.join(WINDOWS_AUTOCHROME_DIR, "main.py")

    main_py_code = dedent(
        r'''
        import os
        import sys
        import subprocess
        import customtkinter as ctk
        from tkinter import messagebox

        # Windows-specific creation flags to hide console and detach process
        DETACHED_PROCESS = 0x00000008
        CREATE_NO_WINDOW = 0x08000000

        BASE_DIR = os.path.abspath(os.path.dirname(__file__))
        BIN_DIR = os.path.join(BASE_DIR, "bin")
        CHROME_PATH = os.path.join(BIN_DIR, "chrome.exe")
        PROFILES_DIR = os.path.join(BASE_DIR, "profiles")

        PROFILE_COLORS = [
            ("Red",    "#ff4b4b"),
            ("Blue",   "#3b82f6"),
            ("Green",  "#22c55e"),
            ("Yellow", "#eab308"),
            ("Purple", "#a855f7"),
            ("Orange", "#f97316"),
        ]


        def ensure_environment():
            """
            Check for bin/chrome.exe and base profile directory.
            """
            if not os.path.isdir(BIN_DIR) or not os.path.isfile(CHROME_PATH):
                messagebox.showerror(
                    "Chromium Not Found",
                    "Please place Portable Chromium at 'WindowsAutochrome/bin/chrome.exe' path."
                )
                return False

            os.makedirs(PROFILES_DIR, exist_ok=True)
            return True


        def build_chrome_command(profile_name: str):
            """
            Build Chromium launch command with Autochrome's security flags.
            """
            profile_path = os.path.join(PROFILES_DIR, profile_name.lower())
            os.makedirs(profile_path, exist_ok=True)

            # Autochrome environment spoofing
            env = os.environ.copy()
            env["GOOGLE_API_KEY"] = "invalid"
            env["GOOGLE_DEFAULT_CLIENT_ID"] = "invalid"
            env["GOOGLE_DEFAULT_CLIENT_SECRET"] = "invalid"

            flags = [
                "--ignore-certificate-errors",
                "--disable-xss-auditor",
                "--no-default-browser-check",
                "--no-first-run",
                "--disable-background-networking",
                "--disable-client-side-phishing-detection",
                "--disable-component-update",
                "--disable-sync",
                "--disable-translate",
                "--disable-web-resources",
                "--safebrowsing-disable-auto-update",
                "--safebrowsing-disable-download-protection",
                "--proxy-server=127.0.0.1:8080",
                f'--user-data-dir="{profile_path}"',
            ]

            cmd = [CHROME_PATH] + flags
            return cmd, env


        def launch_chrome_and_exit(profile_name: str, root: ctk.CTk):
            if not ensure_environment():
                return

            cmd, env = build_chrome_command(profile_name)

            try:
                # Start Chromium detached, no console window.
                subprocess.Popen(
                    " ".join(cmd),
                    shell=True,
                    env=env,
                    creationflags=DETACHED_PROCESS | CREATE_NO_WINDOW,
                )
            except Exception as e:
                messagebox.showerror("Launch Error", f"Failed to launch Chromium:\n{e}")
                return

            # Close launcher
            try:
                root.destroy()
            except Exception:
                pass
            sys.exit(0)


        class ProfileLauncher(ctk.CTk):
            def __init__(self):
                super().__init__()

                # General window config
                ctk.set_appearance_mode("dark")
                ctk.set_default_color_theme("dark-blue")

                self.title("WindowsAutochrome")
                self.geometry("600x260")
                self.resizable(False, False)

                # Frameless window
                self.overrideredirect(True)

                # Center window on screen
                self.update_idletasks()
                width = self.winfo_width()
                height = self.winfo_height()
                x = (self.winfo_screenwidth() // 2) - (width // 2)
                y = (self.winfo_screenheight() // 2) - (height // 2)
                self.geometry(f"{width}x{height}+{x}+{y}")

                # Allow dragging the frameless window
                self._offsetx = 0
                self._offsety = 0
                self.bind("<Button-1>", self._click_win)
                self.bind("<B1-Motion>", self._drag_win)

                # Main frame
                main_frame = ctk.CTkFrame(self, corner_radius=16)
                main_frame.pack(expand=True, fill="both", padx=16, pady=16)

                # Header
                header_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
                header_frame.pack(fill="x", pady=(4, 12))

                title_label = ctk.CTkLabel(
                    header_frame,
                    text="WindowsAutochrome",
                    font=ctk.CTkFont(size=20, weight="bold")
                )
                title_label.pack(side="left", padx=(4, 0))

                subtitle_label = ctk.CTkLabel(
                    header_frame,
                    text="Launch secure Chromium with selected profile",
                    font=ctk.CTkFont(size=12),
                    text_color=("gray70", "gray60"),
                )
                subtitle_label.pack(side="left", padx=(12, 0))

                close_button = ctk.CTkButton(
                    header_frame,
                    text="✕",
                    width=32,
                    height=24,
                    fg_color="transparent",
                    hover_color="#ff4b4b",
                    command=self._on_close,
                )
                close_button.pack(side="right", padx=(0, 4))

                # Profile buttons grid
                buttons_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
                buttons_frame.pack(expand=True, pady=(8, 4))

                for i, (name, color) in enumerate(PROFILE_COLORS):
                    btn = ctk.CTkButton(
                        buttons_frame,
                        text=name,
                        width=150,
                        height=60,
                        corner_radius=16,
                        fg_color=color,
                        hover_color=_darken_hex(color, 0.15),
                        font=ctk.CTkFont(size=16, weight="bold"),
                        command=lambda n=name: launch_chrome_and_exit(n, self),
                    )
                    row = i // 3
                    col = i % 3
                    btn.grid(row=row, column=col, padx=12, pady=12, sticky="nsew")

                # Make grid responsive
                for col in range(3):
                    buttons_frame.grid_columnconfigure(col, weight=1)
                for row in range(2):
                    buttons_frame.grid_rowconfigure(row, weight=1)

            def _click_win(self, event):
                self._offsetx = event.x
                self._offsety = event.y

            def _drag_win(self, event):
                x = event.x_root - self._offsetx
                y = event.y_root - self._offsety
                self.geometry(f"+{x}+{y}")

            def _on_close(self):
                self.destroy()
                sys.exit(0)


        def _darken_hex(hex_color: str, factor: float) -> str:
            """
            Darken a hex color by factor (0-1).
            """
            hex_color = hex_color.lstrip("#")
            if len(hex_color) != 6:
                return "#" + hex_color
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
            r = int(r * (1 - factor))
            g = int(g * (1 - factor))
            b = int(b * (1 - factor))
            return "#{:02x}{:02x}{:02x}".format(r, g, b)


        def main():
            if not ensure_environment():
                # Exit without opening GUI if environment is not suitable
                return
            app = ProfileLauncher()
            app.mainloop()


        if __name__ == "__main__":
            main()
        '''
    )

    with open(main_py_path, "w", encoding="utf-8") as f:
        f.write(main_py_code)

    return main_py_path


def main():
    profiles_dir, bin_dir = ensure_structure()
    main_py_path = write_main_py()

    print(f"WindowsAutochrome structure created:")
    print(f"  - Folder: {WINDOWS_AUTOCHROME_DIR}")
    print(f"  - Profiles: {profiles_dir}")
    print(f"  - Bin: {bin_dir}")
    print(f"  - Launcher: {main_py_path}")
    print("\nPlease place portable Chromium at:")
    print(f"  {os.path.join(bin_dir, 'chrome.exe')}")
    print("\nTo start the launcher:")
    print(f"  python {main_py_path}")


if __name__ == "__main__":
    main()