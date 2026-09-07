import os
import json
from datetime import datetime, date, time, timedelta
import core.google_calendar_api as gcal_api

MED_PLANS_FILE = "data/medication_plans.json"

FREQUENCY_PRESETS = {
    "Cada 8 hores (3 preses)": ["08:00", "16:00", "00:00"],
    "Cada 12 hores (2 preses)": ["09:00", "21:00"],
    "Cada 24 hores / 1 cop al dia": ["09:00"],
    "Esmorzar, Dinar i Sopar": ["09:00", "14:00", "21:00"],
    "Dinar i Sopar": ["14:00", "21:00"],
    "Abans d'anar a dormir": ["23:00"],
    "Personalitzat": []
}

def ensure_data_dir():
    os.makedirs(os.path.dirname(MED_PLANS_FILE), exist_ok=True)

def load_plans():
    ensure_data_dir()
    if not os.path.exists(MED_PLANS_FILE):
        return []
    try:
        with open(MED_PLANS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception as e:
        print(f"Error loading medication plans: {e}")
        return []

def save_plans(plans):
    ensure_data_dir()
    try:
        with open(MED_PLANS_FILE, "w", encoding="utf-8") as f:
            json.dump(plans, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error saving medication plans: {e}")
        return False

def generate_intake_events(plan_data):
    """Generates the full list of daily intake occurrences for a medication plan."""
    patient_name = plan_data.get("patient_name", "Familiar")
    med_name = plan_data.get("medication_name", "Medicament")
    dosage = plan_data.get("dosage", "")
    instructions = plan_data.get("instructions", "")
    start_d_str = plan_data.get("start_date", datetime.now().strftime("%Y-%m-%d"))
    duration_days = int(plan_data.get("duration_days", 7))
    times = plan_data.get("times", ["09:00"])
    
    start_d = datetime.strptime(start_d_str, "%Y-%m-%d").date()
    events = []
    
    for day_offset in range(duration_days):
        curr_d = start_d + timedelta(days=day_offset)
        curr_d_str = curr_d.strftime("%Y-%m-%d")
        
        for t_str in times:
            ev_title = f"💊 {med_name} - {patient_name}"
            if dosage:
                ev_title = f"💊 {med_name} ({dosage}) - {patient_name}"
                
            desc_lines = [
                f"📋 Medicació per a: {patient_name}",
                f"💊 Medicament: {med_name} {dosage}",
                f"⏰ Hora de la presa: {t_str}",
            ]
            if instructions:
                desc_lines.append(f"ℹ️ Pauta: {instructions}")
            desc_lines.append("─────────────────────────")
            desc_lines.append("✅ Quan t'hagis pres la medicació, afegeix '✅' al principi del títol d'aquest esdeveniment.")
            
            events.append({
                "date": curr_d_str,
                "time": t_str,
                "title": ev_title,
                "description": "\n".join(desc_lines),
                "status": "pending",  # "confirmed", "pending", "overdue"
                "confirmed_at": None,
                "gcal_id": None
            })
            
    return events

def create_plan(plan_data):
    """Creates a new medication plan, generates all intake events and saves it."""
    plans = load_plans()
    next_id = max([p.get("id", 0) for p in plans] + [0]) + 1
    plan_data["id"] = next_id
    plan_data["created_at"] = datetime.now().isoformat()
    plan_data["is_active"] = True
    
    # Generate intake events
    plan_data["events"] = generate_intake_events(plan_data)
    
    # Attempt to send to Google Calendar via API if service account configured and calendar_id provided
    cal_id = plan_data.get("calendar_id", "").strip()
    if cal_id and gcal_api.is_service_account_configured():
        gcal_events_payload = []
        for ev in plan_data["events"]:
            gcal_events_payload.append({
                "start_date": ev["date"],
                "start_time": ev["time"],
                "title": ev["title"],
                "description": ev["description"],
                "location": "Llar"
            })
        count, created_ids = gcal_api.create_batch_medication_events(cal_id, gcal_events_payload)
        # Assign gcal IDs
        for i, gid in enumerate(created_ids):
            if i < len(plan_data["events"]):
                plan_data["events"][i]["gcal_id"] = gid
        plan_data["gcal_synced"] = (count > 0)
    else:
        plan_data["gcal_synced"] = False
        
    plans.append(plan_data)
    save_plans(plans)
    return plan_data

def delete_plan(plan_id):
    plans = load_plans()
    new_plans = [p for p in plans if p.get("id") != plan_id]
    if len(new_plans) != len(plans):
        save_plans(new_plans)
        return True
    return False

def toggle_intake_manual(plan_id, event_index):
    """Manually toggles confirmation of an intake event from the Dashboard."""
    plans = load_plans()
    for p in plans:
        if p.get("id") == plan_id:
            if 0 <= event_index < len(p.get("events", [])):
                ev = p["events"][event_index]
                if ev.get("status") == "confirmed":
                    ev["status"] = "pending"
                    ev["confirmed_at"] = None
                    # Remove checkmark from title if present
                    ev["title"] = ev["title"].replace("✅ ", "").replace("✅", "").strip()
                else:
                    ev["status"] = "confirmed"
                    ev["confirmed_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
                    if not ev["title"].startswith("✅"):
                        ev["title"] = f"✅ {ev['title']}"
                save_plans(plans)
                return True
    return False

def sync_all_plans_with_google_calendar():
    """Checks Google Calendar for confirmation markers (✅) and updates local plans."""
    plans = load_plans()
    has_changes = False
    
    for p in plans:
        cal_id = p.get("calendar_id", "").strip()
        if not cal_id or not gcal_api.is_service_account_configured():
            continue
            
        gcal_map = {ev["gcal_id"]: ev for ev in p.get("events", []) if ev.get("gcal_id")}
        if not gcal_map:
            continue
            
        checked = gcal_api.check_confirmed_events(cal_id, gcal_map)
        for gcal_id, res in checked.items():
            if res.get("is_confirmed"):
                # Mark as confirmed in plan
                for ev in p["events"]:
                    if ev.get("gcal_id") == gcal_id and ev.get("status") != "confirmed":
                        ev["status"] = "confirmed"
                        ev["confirmed_at"] = res.get("confirmed_at") or datetime.now().strftime("%Y-%m-%d %H:%M")
                        ev["title"] = res.get("current_title", ev["title"])
                        has_changes = True
                        
    if has_changes:
        save_plans(plans)
    return has_changes

def get_today_intakes(target_date=None):
    """Retrieves all intakes scheduled for today across all active plans."""
    if not target_date:
        target_date = date.today()
    t_str = target_date.strftime("%Y-%m-%d")
    now_time_str = datetime.now().strftime("%H:%M")
    
    plans = load_plans()
    today_list = []
    
    for p in plans:
        if not p.get("is_active", True):
            continue
        patient = p.get("patient_name", "Familiar")
        patient_type = p.get("patient_type", "Familiar")
        med_name = p.get("medication_name", "Medicament")
        dosage = p.get("dosage", "")
        plan_id = p.get("id")
        
        for idx, ev in enumerate(p.get("events", [])):
            if ev.get("date") == t_str:
                status = ev.get("status", "pending")
                ev_time = ev.get("time", "09:00")
                
                # Check if overdue (passed more than 1 hour and still pending)
                if status == "pending" and target_date == date.today():
                    try:
                        ev_dt = datetime.strptime(f"{t_str} {ev_time}", "%Y-%m-%d %H:%M")
                        if datetime.now() > ev_dt + timedelta(hours=1):
                            status = "overdue"
                    except Exception:
                        pass
                        
                today_list.append({
                    "plan_id": plan_id,
                    "event_index": idx,
                    "patient_name": patient,
                    "patient_type": patient_type,
                    "medication_name": med_name,
                    "dosage": dosage,
                    "time": ev_time,
                    "status": status,
                    "confirmed_at": ev.get("confirmed_at"),
                    "title": ev.get("title"),
                    "instructions": p.get("instructions", ""),
                    "gcal_id": ev.get("gcal_id"),
                    "calendar_id": p.get("calendar_id")
                })
                
    return sorted(today_list, key=lambda x: x["time"])
