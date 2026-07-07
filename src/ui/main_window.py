"""CustomTkinter main window for INNA ATAINA TRAVELS OPS PRO."""

from __future__ import annotations

import json
from tkinter import filedialog

import customtkinter as ctk

from core.controller import ExtractionController


class MainWindow(ctk.CTk):
    def __init__(self, controller: ExtractionController) -> None:
        super().__init__()
        self.controller = controller
        self.title("INNA ATAINA TRAVELS OPS PRO")
        self.geometry("980x680")
        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self.header_label = ctk.CTkLabel(
            self,
            text="INNA ATAINA TRAVELS OPS PRO",
            font=ctk.CTkFont(size=28, weight="bold"),
        )
        self.header_label.grid(row=0, column=0, padx=24, pady=(24, 12), sticky="w")

        self.upload_button = ctk.CTkButton(
            self,
            text="Upload Ticket (PDF/Image)",
            command=self._on_upload_click,
            font=ctk.CTkFont(size=14, weight="bold"),
            width=240,
        )
        self.upload_button.grid(row=1, column=0, padx=24, pady=(0, 8), sticky="w")

        self.status_label = ctk.CTkLabel(self, text="Ready", font=ctk.CTkFont(size=13))
        self.status_label.grid(row=1, column=0, padx=280, pady=(0, 8), sticky="w")

        self.preview_box = ctk.CTkTextbox(self, wrap="word", font=ctk.CTkFont(size=13))
        self.preview_box.grid(row=2, column=0, padx=24, pady=8, sticky="nsew")

        self.footer_label = ctk.CTkLabel(
            self,
            text="Developed by AIO Scholarworks",
            font=ctk.CTkFont(size=12),
        )
        self.footer_label.grid(row=3, column=0, padx=24, pady=(0, 20), sticky="e")

    def _on_upload_click(self) -> None:
        file_path = filedialog.askopenfilename(
            title="Select Ticket Document",
            filetypes=[
                ("Ticket Files", "*.pdf *.png *.jpg *.jpeg *.webp"),
                ("All Files", "*.*"),
            ],
        )
        if not file_path:
            return

        self.status_label.configure(text="Extracting ticket data...")
        self.update_idletasks()
        try:
            data = self.controller.extract_ticket_data(file_path)
            preview = json.dumps(data, indent=2, ensure_ascii=False)
            self.preview_box.delete("1.0", "end")
            self.preview_box.insert("1.0", preview)
            self.status_label.configure(text="Extraction complete.")
        except Exception as error:  # noqa: BLE001
            self.preview_box.delete("1.0", "end")
            self.preview_box.insert("1.0", f"Extraction failed:\n{error}")
            self.status_label.configure(text="Extraction failed.")
