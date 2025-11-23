# main.py
import customtkinter as ctk
from ui.styles import Theme
from ui.main_window import MainWindow

if __name__ == "__main__":
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")
    
    app = ctk.CTk()
    app.title("Kanha AI Studio - Modular Edition")
    app.geometry("1600x900")
    app.configure(fg_color=Theme.BG_MAIN)
    
    # ACTIVATE THE GUI
    gui = MainWindow(app) 
    
    app.mainloop()