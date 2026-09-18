import urllib.request
import webbrowser
import subprocess
import os
import sys

def check_internet():
    try:
        urllib.request.urlopen('http://google.com', timeout=3)
        return True
    except:
        return False

def force_offline_dialog():
    """Mostra un diàleg durant 3 segons per si es vol forçar el mode offline. Retorna True si es força."""
    force_offline = False
    try:
        import tkinter as tk
        root = tk.Tk()
        root.title("ControlHouse")
        
        window_width = 300
        window_height = 150
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        center_x = int(screen_width/2 - window_width / 2)
        center_y = int(screen_height/2 - window_height / 2)
        root.geometry(f'{window_width}x{window_height}+{center_x}+{center_y}')
        
        root.attributes('-topmost', True)
        
        tk.Label(root, text="Iniciant ControlHouse...", font=("Arial", 12)).pack(pady=10)
        
        def on_force():
            nonlocal force_offline
            force_offline = True
            root.destroy()
            
        btn = tk.Button(root, text="Forçar Mode Offline (Emergència)", command=on_force, bg="#f39c12", fg="white")
        btn.pack(pady=10)
        
        # Tancar automàticament després de 3 segons
        root.after(3000, root.destroy)
        root.mainloop()
    except Exception as e:
        print("Error mostrant el diàleg:", e)
        
    return force_offline

def show_offline_modal():
    try:
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        messagebox.showwarning(
            "Mode Offline", 
            "S'iniciarà la versió local de l'aplicació en Mode Offline.\nL'arrencada trigarà aproximadament 15 segons.\nRecorda activar l'interruptor 'Mode Offline' dins l'aplicació per evitar errors de connexió i poder sincronitzar més endavant."
        )
        root.destroy()
    except:
        print("ADVERTÈNCIA: Iniciant en Mode Offline.")

def main():
    # Intentar forçar Google Chrome
    chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    if not os.path.exists(chrome_path):
        chrome_path = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
        
    if os.path.exists(chrome_path):
        webbrowser.register('chrome', None, webbrowser.BackgroundBrowser(chrome_path))
        browser = webbrowser.get('chrome')
    else:
        browser = webbrowser.get()
    
    # Oferir opció per forçar offline durant 3 segons
    wants_offline = force_offline_dialog()
    
    has_internet = False
    if not wants_offline:
        has_internet = check_internet()
        
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
        
    if has_internet and not wants_offline:
        print("Internet detectat. Redirigint al núvol (Cloud) instantàniament...")
        # Obrir URL del núvol a Chrome
        browser.open("https://dashboard-despeses-hbbvfvmtfaneihlxux45k9.streamlit.app/")
        
        # Engegar sincronització de fons per assegurar CSVs actualitzats per si cau la fibra demà
        print("Engegant actualització de fons dels CSVs locals...")
        subprocess.Popen([sys.executable, "scripts/update_csvs_background.py"], creationflags=subprocess.CREATE_NO_WINDOW)
    else:
        if wants_offline:
            print("Mode Offline forçat per l'usuari. Iniciant entorn local...")
        else:
            print("Sense Internet. Iniciant entorn local d'emergència...")
            
        show_offline_modal()
        
        try:
            import time
            process = subprocess.Popen([sys.executable, "-m", "streamlit", "run", "app.py", "--server.headless=true"])
            print("Esperant que s'iniciï el servidor local (pot trigar fins a 15 segons)...")
            
            import urllib.request
            max_retries = 30
            for i in range(max_retries):
                try:
                    urllib.request.urlopen("http://localhost:8501/_stcore/health", timeout=1)
                    break
                except:
                    time.sleep(1)
                    
            browser.open("http://localhost:8501")
            process.wait()
        except Exception as e:
            print(f"Error a l'iniciar Streamlit: {e}")
            input("Prem Enter per sortir...")

if __name__ == "__main__":
    main()
