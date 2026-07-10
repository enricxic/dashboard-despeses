import tkinter as tk
from tkinter import ttk, messagebox
import os
import datetime
import threading
import sys

# Ensure we can import scanner
sys.path.append('E:/Dashboard')
try:
    import scanner
except ImportError:
    messagebox.showerror("Error", "No s'ha pogut importar scanner.py")
    sys.exit(1)

def on_scan_click():
    super_val = combo_super.get().strip()
    date_val = entry_date.get().strip()
    
    if not super_val or not date_val:
        messagebox.showwarning("Atenció", "Si us plau, omple el Súper i la Data.")
        return
        
    btn_scan.config(state="disabled", text="Escanejant...")
    lbl_status.config(text="Iniciant escàner (300dpi, grisos)...", fg="blue")
    root.update()
    
    # Run scan in a thread to not freeze UI
    def scan_thread():
        try:
            date_str = date_val.replace("/", "").replace("-", "")
            # Ensure it's 6 digits (ddmmaa) if they entered dd/mm/yy
            if len(date_str) == 8: # ddmmyyyy -> ddmmaa
                date_str = date_str[:4] + date_str[6:]
                
            super_clean = "".join(c for c in super_val if c.isalnum() or c in (' ', '_')).replace(' ', '_')
            
            tickets_dir = "E:/Dashboard/tickets"
            if not os.path.exists(tickets_dir):
                os.makedirs(tickets_dir)
                
            target_path = os.path.join(tickets_dir, f"ticket_{super_clean}_{date_str}.jpg")
            
            res = scanner.scan_silent(target_path)
            
            if res["success"]:
                lbl_status.config(text=f"Desat a: {target_path}", fg="green")
                messagebox.showinfo("Èxit", f"Tiquet guardat correctament a:\n{target_path}")
                root.destroy()
            else:
                lbl_status.config(text="Error d'escaneig", fg="red")
                messagebox.showerror("Error", f"S'ha produït un error:\n{res.get('error', 'Desconegut')}")
                
        except Exception as e:
            lbl_status.config(text="Error greu", fg="red")
            messagebox.showerror("Error", str(e))
        finally:
            btn_scan.config(state="normal", text="🖨️ Escanejar")
            
    t = threading.Thread(target=scan_thread)
    t.start()

root = tk.Tk()
root.title("Escaneig Ràpid de Tiquets")
root.geometry("350x220")
root.resizable(False, False)
root.attributes("-topmost", True) # Keep on top

# Center window
root.eval('tk::PlaceWindow . center')

frame = tk.Frame(root, padx=20, pady=20)
frame.pack(expand=True, fill="both")

tk.Label(frame, text="Supermercat:", font=("Arial", 10, "bold")).grid(row=0, column=0, sticky="w", pady=5)
supers = ["Dia", "BonArea", "Mercadona", "Consum", "Esclat", "Lidl", "Aldi", "Carrefour", "Ametller", "Alcampo"]
combo_super = ttk.Combobox(frame, values=supers, font=("Arial", 10), width=20)
combo_super.grid(row=0, column=1, pady=5, padx=5)
combo_super.current(0)

tk.Label(frame, text="Data (ddmmaa):", font=("Arial", 10, "bold")).grid(row=1, column=0, sticky="w", pady=5)
today_str = datetime.datetime.today().strftime("%d%m%y")
entry_date = tk.Entry(frame, font=("Arial", 10), width=22)
entry_date.insert(0, today_str)
entry_date.grid(row=1, column=1, pady=5, padx=5)

btn_scan = tk.Button(frame, text="🖨️ Escanejar", font=("Arial", 11, "bold"), bg="#4CAF50", fg="white", command=on_scan_click, pady=5)
btn_scan.grid(row=2, column=0, columnspan=2, pady=15, sticky="ew")

lbl_status = tk.Label(frame, text="Llest per escanejar.", font=("Arial", 9))
lbl_status.grid(row=3, column=0, columnspan=2)

root.mainloop()
