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

def show_offline_modal():
    try:
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        messagebox.showwarning(
            "Mode Offline", 
            "No s'ha detectat connexió a Internet.\nS'iniciarà la versió local de l'aplicació en Mode Offline.\nRecorda activar l'interruptor 'Mode Offline' dins l'aplicació per evitar errors de connexió i poder sincronitzar més endavant."
        )
        root.destroy()
    except:
        # Fallback for systems without tkinter
        print("ADVERTÈNCIA: No s'ha detectat Internet. Iniciant en Mode Offline.")

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
    
    if check_internet():
        print("Internet detectat. L'aplicació es connectarà al núvol (Supabase).")
    else:
        print("Sense Internet. Iniciant entorn completament Offline...")
        show_offline_modal()
        
    # Iniciar sempre l'entorn local
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    try:
        import time
        subprocess.Popen([sys.executable, "-m", "streamlit", "run", "app.py", "--server.headless=true"])
        print("Esperant que s'iniciï el servidor local...")
        time.sleep(3)
        browser.open("http://localhost:8501")
    except Exception as e:
        print(f"Error a l'iniciar Streamlit: {e}")
        input("Prem Enter per sortir...")

if __name__ == "__main__":
    main()
