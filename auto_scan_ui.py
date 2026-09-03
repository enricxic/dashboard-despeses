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
    except Exception as e:
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
        except:
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
root.geometry("400x220")
root.resizable(False, False)
root.attributes("-topmost", True) # Keep on top

# Center window
root.eval('tk::PlaceWindow . center')

frame = tk.Frame(root, padx=20, pady=20)
frame.pack(expand=True, fill="both")

tk.Label(frame, text="Supermercat:", font=("Arial", 10, "bold")).grid(row=0, column=0, sticky="w", pady=5)
supers = load_supers()
combo_super = ttk.Combobox(frame, values=supers, font=("Arial", 10), width=18)
combo_super.grid(row=0, column=1, pady=5, padx=5, sticky="w")
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

tk.Label(frame, text="Data (ddmmaa):", font=("Arial", 10, "bold")).grid(row=1, column=0, sticky="w", pady=5)
today_str = datetime.datetime.today().strftime("%d%m%y")
entry_date = tk.Entry(frame, font=("Arial", 10), width=20)
entry_date.grid(row=1, column=1, pady=5, padx=5, sticky="w")

def btn_today_click():
    entry_date.delete(0, tk.END)
    entry_date.insert(0, datetime.datetime.today().strftime("%d%m%y"))

btn_today = tk.Button(frame, text="Avui", font=("Arial", 9), command=btn_today_click)
btn_today.grid(row=1, column=2, padx=5)

btn_scan = tk.Button(frame, text="🖨️ Escanejar", font=("Arial", 11, "bold"), bg="#4CAF50", fg="white", command=on_scan_click, pady=5)
btn_scan.grid(row=2, column=0, columnspan=3, pady=15, sticky="ew")

lbl_status = tk.Label(frame, text="Llest per escanejar.", font=("Arial", 9))
lbl_status.grid(row=3, column=0, columnspan=3)

root.mainloop()
