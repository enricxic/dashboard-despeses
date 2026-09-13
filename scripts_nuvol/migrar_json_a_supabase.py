import os
import sys
import json
import streamlit as st

# Afegir el path pare per poder importar mòduls del projecte
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.db import get_supabase_client

def migrate_file_to_supabase(filepath, target_id, description):
    print(f"🔄 Migrant {description} ({filepath}) a Supabase ID {target_id}...")
    if not os.path.exists(filepath):
        print(f"⚠️ El fitxer {filepath} no existeix. Saltant.")
        return False
        
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        supabase = get_supabase_client("admin")
        res = supabase.table("app_config").upsert({
            "id": target_id,
            "config_json": data
        }).execute()
        
        print(f"✅ Èxit! {description} migrat correctament.")
        return True
    except Exception as e:
        print(f"❌ Error migrant {description}: {e}")
        return False

if __name__ == "__main__":
    print("🚀 INICIANT MIGRACIÓ DE JSON A SUPABASE 🚀")
    print("-" * 50)
    
    # 1. Categories i Conceptes (ID=1) - Tot i que ja està fet, ho re-pujem per si de cas
    migrate_file_to_supabase("categories_conceptes.json", 1, "Categories i Conceptes")
    
    # 2. Configuració Principal i Família (ID=2)
    migrate_file_to_supabase("core/config.json", 2, "Configuració Principal i Família")
    
    # 3. Calendari (ID=3)
    migrate_file_to_supabase("core/events.json", 3, "Esdeveniments del Calendari")
    
    # 4. Memòria cau del Calendari (ID=4)
    migrate_file_to_supabase("core/cache_feeds.json", 4, "Memòria Cau dels Calendaris de Google")
    
    # 5. Plans de Medicació (ID=5)
    migrate_file_to_supabase("core/med_plans.json", 5, "Plans de Medicació")
    
    print("-" * 50)
    print("🎉 MIGRACIÓ FINALITZADA! 🎉")
    print("Pots tancar aquest script.")
