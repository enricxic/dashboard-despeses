import os
import threading

def scan_with_dialog(output_path):
    result = {"success": False, "error": None}
    
    try:
        import win32com.client
        import pythoncom
    except ImportError:
        result["error"] = "Escaneig no disponible al núvol (requereix Windows i execució local)."
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
    result = {"success": False, "error": None}
    
    try:
        import win32com.client
        import pythoncom
    except ImportError:
        result["error"] = "Escaneig no disponible al núvol (requereix Windows i execució local)."
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
                        prop.Value = 2550 # 8.5 inches * 300 dpi
                    elif prop.PropertyID == 6152: # Vertical Extent
                        prop.Value = 3510 # 11.7 inches * 300 dpi
            except Exception as prop_err:
                pass # ignore property setting errors if scanner doesn't support it

            image = item.Transfer("{B96B3CAE-0728-11D3-9D7B-0000F81EF32E}")
            
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

def scan_ticket(output_path=None):
    if not output_path:
        temp_dir = "temp_scans"
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir)
        output_path = os.path.abspath(os.path.join(temp_dir, "scanned_ticket.jpg"))
        
    res = scan_silent(output_path)
    
    if res["success"]:
        return output_path
    else:
        return None
