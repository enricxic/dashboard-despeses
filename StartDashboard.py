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
    
    has_internet = check_internet()
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
        
    if has_internet:
        print("Internet detectat. Redirigint al núvol (Cloud) instantàniament...")
        # Obrir URL del núvol a Chrome
        browser.open("https://dashboard-despeses-hbbvfvmtfaneihlxux45k9.streamlit.app/")
        
        # Engegar sincronització de fons per assegurar CSVs actualitzats per si cau la fibra demà
        print("Engegant actualització de fons dels CSVs locals...")
        subprocess.Popen([sys.executable, "scripts/update_csvs_background.py"], creationflags=subprocess.CREATE_NO_WINDOW)
    else:
        print("Sense Internet. Iniciant entorn local d'emergència...")
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
