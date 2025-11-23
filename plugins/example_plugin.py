# plugins/export_text.py
from tkinter import filedialog, messagebox

def run_tool(editor_instance):
    """ 
    The main entry point. 
    'editor_instance' allows the plugin to control the Main Window! 
    """
    captions = editor_instance.subtitle_segments
    
    if not captions:
        messagebox.showerror("Plugin Error", "No captions generated yet!")
        return

    path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text", "*.txt")])
    if not path: return

    try:
        with open(path, "w", encoding="utf-8") as f:
            for s in captions:
                # Formatting the output
                f.write(f"[{s['start']:.1f}s] {s['text']}\n")
        
        messagebox.showinfo("Plugin Success", f"Exported {len(captions)} lines via Plugin.")
    except Exception as e:
        messagebox.showerror("Error", str(e))

def register_plugin():
    """ Tell the Main App who we are """
    return {
        "name": "Export to Notepad",
        "version": "1.0.0",
        "type": "tool",     # Puts it in the 'Tools' menu
        "action": run_tool  # The function above
    }