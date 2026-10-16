# -*- coding: utf-8 -*-
"""
Script de prova d'impressió directa per a BIXOLON SRP-275.
Executa una prova física de paper, línies i tall automàtic.
"""

import sys
import os

# Configurar stdout a UTF-8 a Windows
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

# Afegir directori arrel al PATH
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.impressora import imprimir_directe_bixolon, is_local_printer_available

def main():
    print("=" * 45)
    print("PROVA D'IMPRESSORA BIXOLON SRP-275")
    print("=" * 45)
    
    if not is_local_printer_available():
        print("⚠️ Advertència: No s'ha detectat la impressora 'BIXOLON_SRP275' instal·lada a Windows.")
        print("Ports actuals disponibles:")
        try:
            import win32print
            for p in win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS):
                print(f" - {p[2]}")
        except Exception as e:
            print(f"Error enumerant impressores: {e}")
        return
        
    print("✅ Impressora detectada correctament a Windows!")
    
    items_prova = [
        {'nom_estandard': 'Llet sencera', 'falta': 2, 'total_linia': 2.10},
        {'nom_estandard': 'Ous docena', 'falta': 1, 'total_linia': 2.45},
        {'nom_estandard': 'Pa de pagès', 'falta': 1, 'total_linia': 1.80},
        {'nom_estandard': 'Formatge curat', 'falta': 1, 'total_linia': 3.90}
    ]
    
    print("Enviant tiquet de prova de 'Mercadona' per USB...")
    ok, msg = imprimir_directe_bixolon("Mercadona", items_prova, 10.25)
    if ok:
        print(f"🎉 ÈXIT: {msg}")
    else:
        print(f"❌ ERROR: {msg}")

if __name__ == "__main__":
    main()
