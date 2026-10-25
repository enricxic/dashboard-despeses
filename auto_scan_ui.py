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

def find_latest_windows_scan():
    possible_dirs = [
        os.path.expanduser(r"~\Pictures\Digitalizaciones"),
        os.path.expanduser(r"~\Pictures\Scans"),
        os.path.expanduser(r"~\Imatges\Digitalitzacions"),
        os.path.expanduser(r"~\Pictures")
    ]
    candidates = []
    exts = ("*.png", "*.jpg", "*.jpeg", "*.bmp", "*.tiff")
    for d in possible_dirs:
        if os.path.exists(d):
            for ext in exts:
                candidates.extend(glob.glob(os.path.join(d, ext)))
    if not candidates:
        return None
    candidates.sort(key=lambda x: os.path.getmtime(x), reverse=True)
    return candidates[0]

def on_import_windows_scan():
    super_val = combo_super.get().strip()
    date_val = entry_date.get().strip()
    if not super_val or not date_val:
        messagebox.showwarning("Atenció", "Si us plau, omple el Súper i la Data abans d'importar.")
        return
        
    latest = find_latest_windows_scan()
    if not latest:
        messagebox.showinfo("Sense fitxers", "No s'ha trobat cap escaneig a la carpeta Digitalizaciones.\nSi us plau, prem 'Digitalizar' a l'Escàner de Windows o tria el fitxer manualment.")
        on_choose_file()
        return

    # Comprova si el fitxer és d'avui
    mtime = datetime.datetime.fromtimestamp(os.path.getmtime(latest))
    nom_base = os.path.basename(latest)
    pregunta = f"Vols importar el darrer escaneig trobat?\n\n📁 {nom_base}\n🕒 {mtime.strftime('%d/%m/%Y %H:%M')}"
    if not messagebox.askyesno("Confirmar Importació", pregunta):
        on_choose_file()
        return

    target = get_target_path(super_val, date_val)
    if save_image_as_target(latest, target):
        lbl_status.config(text=f"Importat a: {target}", fg="green")
        messagebox.showinfo("Èxit", f"Tiquet guardat correctament a:\n{target}")
        root.destroy()

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

def on_open_win_scanner():
    try:
        os.system("start explorer.exe shell:AppsFolder\\Microsoft.WindowsScan_8wekyb3d8bbwe!App")
        lbl_status.config(text="S'ha obert l'Escàner de Windows. Fes 'Digitalizar' i després '📥 Importar'.", fg="blue")
    except Exception as e:
        messagebox.showerror("Error", f"No s'ha pogut obrir l'Escàner de Windows: {e}")

def on_scan_click():
    super_val = combo_super.get().strip()
    date_val = entry_date.get().strip()
    
    if not super_val or not date_val:
        messagebox.showwarning("Atenció", "Si us plau, omple el Súper i la Data.")
        return
        
    btn_scan.config(state="disabled", text="Escanejant...")
    lbl_status.config(text="Iniciant escàner WIA (300dpi)...", fg="blue")
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
                lbl_status.config(text="Error d'escaneig directe", fg="red")
                err_detail = res.get('error', 'Desconegut')
                preg = (
                    f"L'escaneig automàtic directe no ha pogut completar-se:\n{err_detail}\n\n"
                    "Com que l'Escàner oficial de Windows funciona bé, vols obrir-lo o importar el darrer tiquet digitalitzat?"
                )
                if messagebox.askyesno("Problema amb WIA", preg):
                    root.after(100, on_import_windows_scan)
        except Exception as e:
            lbl_status.config(text="Error greu", fg="red")
            messagebox.showerror("Error", str(e))
        finally:
            btn_scan.config(state="normal", text="🖨️ Escaneig Directe")
            
    t = threading.Thread(target=scan_thread)
    t.start()

root = tk.Tk()
root.title("Escaneig Ràpid de Tiquets")
root.geometry("440x310")
root.resizable(False, False)
root.attributes("-topmost", True)

# Center window
root.eval('tk::PlaceWindow . center')

frame = tk.Frame(root, padx=16, pady=12)
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
ttk.Separator(frame, orient="horizontal").grid(row=2, column=0, columnspan=3, sticky="ew", pady=10)

# Row 3: Botó Importar Darrer Escaneig (Opció Recomanada i Més Ràpida)
btn_import = tk.Button(
    frame,
    text="📥 Importar darrer tiquet d'Escàner de Windows",
    font=("Arial", 10, "bold"),
    bg="#0284c7",
    fg="white",
    command=on_import_windows_scan,
    pady=4,
    cursor="hand2"
)
btn_import.grid(row=3, column=0, columnspan=3, pady=3, sticky="ew")

# Row 4: Botons secundaris (Escaneig directe i triar arxiu)
c_btn_frame = tk.Frame(frame)
c_btn_frame.grid(row=4, column=0, columnspan=3, pady=4, sticky="ew")
c_btn_frame.columnconfigure(0, weight=1)
c_btn_frame.columnconfigure(1, weight=1)
c_btn_frame.columnconfigure(2, weight=1)

btn_scan = tk.Button(
    c_btn_frame,
    text="🖨️ Escaneig Directe",
    font=("Arial", 9),
    bg="#4CAF50",
    fg="white",
    command=on_scan_click,
    pady=3
)
btn_scan.grid(row=0, column=0, padx=2, sticky="ew")

btn_open_win = tk.Button(
    c_btn_frame,
    text="🔍 Obrir Escàner",
    font=("Arial", 9),
    bg="#f1f5f9",
    command=on_open_win_scanner,
    pady=3
)
btn_open_win.grid(row=0, column=1, padx=2, sticky="ew")

btn_choose = tk.Button(
    c_btn_frame,
    text="📁 Triar arxiu...",
    font=("Arial", 9),
    bg="#f1f5f9",
    command=on_choose_file,
    pady=3
)
btn_choose.grid(row=0, column=2, padx=2, sticky="ew")

# Row 5: Status
lbl_status = tk.Label(frame, text="Digilitza el tiquet i fes clic a '📥 Importar'.", font=("Arial", 8), fg="#64748b")
lbl_status.grid(row=5, column=0, columnspan=3, pady=6)

root.mainloop()
