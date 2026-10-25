import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
import glob
import datetime
import threading
import sys
import shutil
from PIL import Image

# Ensure we can import scanner
sys.path.append('E:/Dashboard')
try:
    import scanner
except ImportError:
    messagebox.showerror("Error", "No s'ha pogut importar scanner.py")
    sys.exit(1)

def load_supers():
    try:
        import toml
        import requests
        secrets = toml.load('E:/Dashboard/.streamlit/secrets.toml')
        url = secrets['SUPABASE_URL'] + '/rest/v1/tb_supers?select=supermercat'
        headers = {
            'apikey': secrets['SUPABASE_KEY_PUBLISHABLE'],
            'Authorization': 'Bearer ' + secrets['SUPABASE_KEY_PUBLISHABLE']
        }
        res = requests.get(url, headers=headers)
        if res.status_code == 200:
            supers = [x['supermercat'] for x in res.json()]
            return sorted(list(set(supers)))
    except Exception:
        pass
    return ["Dia", "BonArea", "Mercadona", "Consum", "Esclat", "Lidl", "Aldi", "Carrefour", "Ametller", "Alcampo"]

def add_super(new_super):
    try:
        import toml
        import requests
        import json
        secrets = toml.load('E:/Dashboard/.streamlit/secrets.toml')
        
        # Add to JSON config to maintain legacy format sync
        try:
            with open('E:/Dashboard/categories_conceptes.json', 'r', encoding='utf-8') as f:
                cat_config = json.load(f)
            if 'supers_tickets' not in cat_config:
                cat_config['supers_tickets'] = []
            if new_super not in cat_config['supers_tickets']:
                cat_config['supers_tickets'].append(new_super)
                with open('E:/Dashboard/categories_conceptes.json', 'w', encoding='utf-8') as f:
                    json.dump(cat_config, f, indent=4, ensure_ascii=False)
        except Exception:
            pass

        # Add to Supabase
        url = secrets['SUPABASE_URL'] + '/rest/v1/tb_supers'
        headers = {
            'apikey': secrets['SUPABASE_KEY_PUBLISHABLE'],
            'Authorization': 'Bearer ' + secrets['SUPABASE_KEY_PUBLISHABLE'],
            'Content-Type': 'application/json',
            'Prefer': 'return=representation'
        }
        data = {'supermercat': new_super}
        res = requests.post(url, headers=headers, json=data)
        if res.status_code in [200, 201]:
            return True
        else:
            messagebox.showerror("Error", f"Error de Supabase: {res.text}")
            return False
    except Exception as e:
        messagebox.showerror("Error", f"No s'ha pogut afegir el súper: {e}")
        return False

def get_target_path(super_val, date_val):
    date_str = date_val.replace("/", "").replace("-", "")
    if len(date_str) == 8:
        date_str = date_str[:4] + date_str[6:]
    super_clean = "".join(c for c in super_val if c.isalnum() or c in (' ', '_')).replace(' ', '_')
    tickets_dir = "E:/Dashboard/tickets"
    if not os.path.exists(tickets_dir):
        os.makedirs(tickets_dir)
    return os.path.join(tickets_dir, f"ticket_{super_clean}_{date_str}.jpg")

def save_image_as_target(source_img_path, target_path):
    try:
        with Image.open(source_img_path) as img:
            rgb_img = img.convert('RGB')
            rgb_img.save(target_path, 'JPEG', quality=90)
        return True
    except Exception as e:
        messagebox.showerror("Error al convertir la imatge", str(e))
        return False

def on_choose_file():
    super_val = combo_super.get().strip()
    date_val = entry_date.get().strip()
    if not super_val or not date_val:
        messagebox.showwarning("Atenció", "Si us plau, omple el Súper i la Data abans de seleccionar el fitxer.")
        return
    fpath = filedialog.askopenfilename(
        title="Selecciona la imatge del tiquet",
        filetypes=[("Imatges", "*.png;*.jpg;*.jpeg;*.bmp;*.tiff"), ("Tots els fitxers", "*.*")]
    )
    if fpath:
        target = get_target_path(super_val, date_val)
        if save_image_as_target(fpath, target):
            lbl_status.config(text=f"Guardat a: {target}", fg="green")
            messagebox.showinfo("Èxit", f"Tiquet guardat correctament a:\n{target}")
            root.destroy()

def on_scan_click():
    super_val = combo_super.get().strip()
    date_val = entry_date.get().strip()
    
    if not super_val or not date_val:
        messagebox.showwarning("Atenció", "Si us plau, omple el Súper i la Data abans d'escanejar.")
        return
        
    btn_scan.config(state="disabled", text="⏳ Escanejant...")
    btn_choose.config(state="disabled")
    lbl_status.config(text="Escanejant document directament de l'escàner...", fg="#0284c7")
    root.update()
    
    def scan_thread():
        try:
            target_path = get_target_path(super_val, date_val)
            res = scanner.scan_silent(target_path)
            
            if res["success"]:
                lbl_status.config(text=f"Desat a: {target_path}", fg="green")
                messagebox.showinfo("Èxit", f"Tiquet guardat correctament a:\n{target_path}")
                root.destroy()
            else:
                err_detail = res.get('error', 'Error desconegut')
                lbl_status.config(text=f"Error: {err_detail}", fg="red")
                messagebox.showerror("Error d'escaneig", f"No s'ha pogut completar l'escaneig:\n\n{err_detail}")
        except Exception as e:
            lbl_status.config(text="Error greu", fg="red")
            messagebox.showerror("Error greu", str(e))
        finally:
            try:
                btn_scan.config(state="normal", text="🖨️ Escanejar Tiquet")
                btn_choose.config(state="normal")
            except Exception:
                pass
            
    t = threading.Thread(target=scan_thread)
    t.start()

root = tk.Tk()
root.title("Escaneig Ràpid de Tiquets")
root.geometry("420x240")
root.resizable(False, False)
root.attributes("-topmost", True)

# Center window
root.eval('tk::PlaceWindow . center')

frame = tk.Frame(root, padx=16, pady=14)
frame.pack(expand=True, fill="both")

# Row 0: Súper
tk.Label(frame, text="Supermercat:", font=("Arial", 10, "bold")).grid(row=0, column=0, sticky="w", pady=4)
supers = load_supers()
combo_super = ttk.Combobox(frame, values=supers, font=("Arial", 10), width=18)
combo_super.grid(row=0, column=1, pady=4, padx=5, sticky="w")
combo_super.set("")

def btn_add_super_click():
    from tkinter import simpledialog
    new_super = simpledialog.askstring("Nou Súper", "Nom del nou supermercat:", parent=root)
    if new_super and new_super.strip():
        if add_super(new_super.strip()):
            updated_supers = load_supers()
            combo_super.config(values=updated_supers)
            combo_super.set(new_super.strip())
            messagebox.showinfo("Èxit", f"Súper '{new_super.strip()}' afegit correctament.")

btn_new_super = tk.Button(frame, text="+ Nou", font=("Arial", 9), command=btn_add_super_click)
btn_new_super.grid(row=0, column=2, padx=5)

# Row 1: Data
tk.Label(frame, text="Data (ddmmaa):", font=("Arial", 10, "bold")).grid(row=1, column=0, sticky="w", pady=4)
today_str = datetime.datetime.today().strftime("%d%m%y")
entry_date = tk.Entry(frame, font=("Arial", 10), width=20)
entry_date.grid(row=1, column=1, pady=4, padx=5, sticky="w")
entry_date.insert(0, today_str)

def btn_today_click():
    entry_date.delete(0, tk.END)
    entry_date.insert(0, datetime.datetime.today().strftime("%d%m%y"))

btn_today = tk.Button(frame, text="Avui", font=("Arial", 9), command=btn_today_click)
btn_today.grid(row=1, column=2, padx=5)

# Separador visual
ttk.Separator(frame, orient="horizontal").grid(row=2, column=0, columnspan=3, sticky="ew", pady=8)

# Row 3: Botó Principal Escanejar
btn_scan = tk.Button(
    frame,
    text="🖨️ Escanejar Tiquet",
    font=("Arial", 11, "bold"),
    bg="#16a34a",
    fg="white",
    command=on_scan_click,
    pady=6,
    cursor="hand2"
)
btn_scan.grid(row=3, column=0, columnspan=3, pady=4, sticky="ew")

# Row 4: Botó secundari (Triar arxiu ja existent)
btn_choose = tk.Button(
    frame,
    text="📁 Triar fitxer existent...",
    font=("Arial", 9),
    bg="#f1f5f9",
    command=on_choose_file,
    pady=2
)
btn_choose.grid(row=4, column=0, columnspan=3, pady=2, sticky="ew")

# Row 5: Status
lbl_status = tk.Label(frame, text="Col·loca el tiquet a l'escàner i prem 'Escanejar Tiquet'.", font=("Arial", 8), fg="#64748b")
lbl_status.grid(row=5, column=0, columnspan=3, pady=4)

root.mainloop()
