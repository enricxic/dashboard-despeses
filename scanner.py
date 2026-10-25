import os
import subprocess
import threading
from PIL import Image

def get_connected_scanners():
    """
    Retorna la llista d'escàners connectats detectats per la nova API WinRT de Windows:
    [{'nom': 'hp scanjet', 'id': '...'}]
    """
    ps_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scan_winrt.ps1")
    if not os.path.exists(ps_script):
        return []
    cmd = [
        "powershell.exe",
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", ps_script,
        "-ListDevices"
    ]
    creationflags = 0x08000000 if os.name == 'nt' else 0
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, creationflags=creationflags, timeout=12)
        devices = []
        for line in proc.stdout.splitlines():
            line = line.strip()
            if line.startswith("DEVICE:"):
                raw = line[len("DEVICE:"):].strip()
                if "|" in raw:
                    nom, dev_id = raw.split("|", 1)
                else:
                    nom, dev_id = raw, raw
                devices.append({"nom": nom, "id": dev_id})
        return devices
    except Exception:
        return []

def scan_winrt(output_path, device_name=None, dpi=None, color_mode=None):
    """
    Escaneig directe utilitzant la infraestructura moderna de Windows (WinRT / Windows.Devices.Scanners).
    Permet seleccionar el dispositiu per defecte o un concret configurat a l'aplicació.
    """
    result = {"success": False, "error": None}
    
    ps_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scan_winrt.ps1")
    if not os.path.exists(ps_script):
        result["error"] = f"Script d'escaneig no trobat: {ps_script}"
        return result
        
    temp_dir = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "temp_scans"))
    os.makedirs(temp_dir, exist_ok=True)

    # Llegir configuració si no s'especifica
    if device_name is None or dpi is None or color_mode is None:
        try:
            from core.config_manager import load_app_config
            cfg = load_app_config().get("periferics", {}).get("escaner", {})
            if device_name is None:
                device_name = cfg.get("dispositiu", "default")
            if dpi is None:
                dpi = int(cfg.get("dpi", 300))
            if color_mode is None:
                color_mode = cfg.get("mode_color", "Color")
        except Exception:
            device_name = device_name or "default"
            dpi = dpi or 300
            color_mode = color_mode or "Color"
    
    cmd = [
        "powershell.exe",
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-File", ps_script,
        "-OutputDir", temp_dir,
        "-DeviceName", str(device_name if device_name != "default" else ""),
        "-Dpi", str(dpi),
        "-ColorMode", str(color_mode)
    ]
    
    # Hide PowerShell console window
    creationflags = 0x08000000 if os.name == 'nt' else 0 # CREATE_NO_WINDOW
    
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            creationflags=creationflags,
            timeout=120
        )
        
        output = proc.stdout.strip()
        scanned_file = None
        
        for line in output.splitlines():
            line = line.strip()
            if line.startswith("SUCCESS:"):
                scanned_file = line[len("SUCCESS:"):].strip()
            elif line.startswith("ERROR:"):
                result["error"] = line[len("ERROR:"):].strip()
                
        if not scanned_file or not os.path.exists(scanned_file):
            if not result["error"]:
                result["error"] = proc.stderr.strip() or "No s'ha obtingut cap imatge de l'escàner."
            return result
            
        # Convert scanned file (BMP/PNG) to JPG with Pillow
        with Image.open(scanned_file) as img:
            rgb_img = img.convert('RGB')
            target_dir = os.path.dirname(os.path.abspath(output_path))
            if target_dir:
                os.makedirs(target_dir, exist_ok=True)
            if os.path.exists(output_path):
                os.remove(output_path)
            rgb_img.save(output_path, 'JPEG', quality=90)
            
        # Clean up temporary scanned BMP/PNG
        try:
            if os.path.exists(scanned_file):
                os.remove(scanned_file)
        except Exception:
            pass
            
        result["success"] = True
        return result
        
    except subprocess.TimeoutExpired:
        result["error"] = "Temps d'espera esgotat durant l'escaneig (l'escàner no ha respost en 120s)."
        return result
    except Exception as e:
        result["error"] = str(e)
        return result

def scan_wia_silent(output_path):
    result = {"success": False, "error": None}
    
    try:
        import win32com.client
        import pythoncom
    except ImportError:
        result["error"] = "Escaneig no disponible (requereix win32com i Windows)."
        return result
        
    def worker():
        try:
            pythoncom.CoInitialize()
            dev_manager = win32com.client.Dispatch("WIA.DeviceManager")
            if dev_manager.DeviceInfos.Count == 0:
                result["error"] = "No s'ha trobat cap escàner connectat."
                return
                
            device = dev_manager.DeviceInfos(1).Connect()
            item = device.Items(1)
            
            # Configure 300 DPI
            try:
                for prop in item.Properties:
                    if prop.PropertyID == 6147: # Horizontal Resolution
                        prop.Value = 300
                    elif prop.PropertyID == 6148: # Vertical Resolution
                        prop.Value = 300
                    elif prop.PropertyID == 6146: # Current Intent
                        prop.Value = 2 # Grayscale
                    elif prop.PropertyID == 6151: # Horizontal Extent
                        prop.Value = 2550
                    elif prop.PropertyID == 6152: # Vertical Extent
                        prop.Value = 3510
            except Exception:
                pass

            image = item.Transfer("{B96B3CAA-0728-11D3-9D7B-0000F81EF32E}") # wiaFormatBMP
            
            target_dir = os.path.dirname(os.path.abspath(output_path))
            if target_dir:
                os.makedirs(target_dir, exist_ok=True)
            if os.path.exists(output_path):
                os.remove(output_path)
            image.SaveFile(output_path)
            result["success"] = True
            
        except Exception as e:
            result["error"] = str(e)
        finally:
            pythoncom.CoUninitialize()

    t = threading.Thread(target=worker)
    t.start()
    t.join()
    
    return result

def scan_with_dialog(output_path):
    result = {"success": False, "error": None}
    
    try:
        import win32com.client
        import pythoncom
    except ImportError:
        result["error"] = "Escaneig no disponible (requereix Windows)."
        return result
        
    def worker():
        try:
            pythoncom.CoInitialize()
            dialog = win32com.client.Dispatch("WIA.CommonDialog")
            image = dialog.ShowAcquireImage(1, 1, 1, "{B96B3CAE-0728-11D3-9D7B-0000F81EF32E}", False, True, False)
            if image:
                if os.path.exists(output_path):
                    os.remove(output_path)
                image.SaveFile(output_path)
                result["success"] = True
            else:
                result["error"] = "Cancel·lat per l'usuari"
        except Exception as e:
            result["error"] = str(e)
        finally:
            pythoncom.CoUninitialize()

    t = threading.Thread(target=worker)
    t.start()
    t.join()
    
    return result

def scan_silent(output_path):
    """
    Intenta escanejar directament mitjançant WinRT; si falla, prova fallback WIA.
    """
    # 1. Provar WinRT modern (nadiu, ràpid i configurable)
    res = scan_winrt(output_path)
    if res["success"]:
        return res
        
    # 2. Fallback a WIA antic si cal
    wia_res = scan_wia_silent(output_path)
    if wia_res["success"]:
        return wia_res
        
    return res if res.get("error") else wia_res

def scan_ticket(output_path=None):
    if not output_path:
        temp_dir = "temp_scans"
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir)
        output_path = os.path.abspath(os.path.join(temp_dir, "scanned_ticket.jpg"))
        
    res = scan_silent(output_path)
    
    if res["success"]:
        return output_path, None
    else:
        return None, res.get("error", "Error desconegut")
