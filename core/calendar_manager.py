import json
import os
import re
import urllib.parse
from datetime import datetime, date, time, timedelta
import dateutil.parser
import requests

EVENTS_FILE = "data/events.json"
CACHE_FEEDS_FILE = "data/feeds_cache.json"

CATEGORIES = {
    "Metge": {"icon": "🏥", "color": "#ef4444", "label": "Metge i Salut"},
    "Dinar": {"icon": "🍽️", "color": "#f97316", "label": "Dinar"},
    "Sopar": {"icon": "🍲", "color": "#6366f1", "label": "Sopar"},
    "Escola": {"icon": "🏫", "color": "#3b82f6", "label": "Escola i Estudis"},
    "Feina": {"icon": "💼", "color": "#8b5cf6", "label": "Feina i Tasques"},
    "Aniversari": {"icon": "🎂", "color": "#ec4899", "label": "Aniversari i Celebració"},
    "Oci": {"icon": "✈️", "color": "#10b981", "label": "Oci, Viatges i Esport"},
    "Llar": {"icon": "🏠", "color": "#f59e0b", "label": "Llar i Manteniment"},
    "Altres": {"icon": "⭐", "color": "#06b6d4", "label": "Altres / General"}
}

def ensure_data_dir():
    os.makedirs(os.path.dirname(EVENTS_FILE), exist_ok=True)

def _normalize_event(ev: dict) -> dict:
    if not isinstance(ev, dict):
        return ev
    if "date" in ev and not ev.get("start_date"):
        ev["start_date"] = ev["date"]
    elif "start_date" in ev and not ev.get("date"):
        ev["date"] = ev["start_date"]

    if "time" in ev and not ev.get("start_time"):
        ev["start_time"] = ev["time"]
    elif "start_time" in ev and not ev.get("time"):
        ev["time"] = ev["start_time"]

    if "assigned_to" in ev and not ev.get("member"):
        ev["member"] = ev["assigned_to"]
    elif "member" in ev and not ev.get("assigned_to"):
        ev["assigned_to"] = ev["member"]
    return ev

def load_raw_local_events():
    events_raw = []
    # Supabase (id=3)
    try:
        from core.db import get_supabase_client
        supabase = get_supabase_client("guest")
        res = supabase.table("app_config").select("config_json").eq("id", 3).execute()
        if res.data and len(res.data) > 0:
            data = res.data[0]["config_json"]
            if isinstance(data, list):
                events_raw = data
    except Exception as e:
        print("Supabase events load failed:", e)

    # Fallback local
    if not events_raw:
        ensure_data_dir()
        if os.path.exists(EVENTS_FILE):
            try:
                with open(EVENTS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        events_raw = data
            except Exception as e:
                print(f"Error loading {EVENTS_FILE}: {e}")
    return events_raw

def save_raw_local_events(events):
    # Supabase (id=3)
    try:
        from core.db import get_supabase_client
        supabase = get_supabase_client("admin")
        supabase.table("app_config").upsert({
            "id": 3,
            "config_json": events
        }).execute()
    except Exception as e:
        print("Error saving events to Supabase:", e)

    # Backup local
    ensure_data_dir()
    try:
        with open(EVENTS_FILE, "w", encoding="utf-8") as f:
            json.dump(events, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error saving {EVENTS_FILE}: {e}")
        return False

def load_local_events():
    raw = load_raw_local_events()
    return [_normalize_event(e) for e in raw if not e.get("is_deleted") and not e.get("is_status_override")]

def get_event_status_map():
    raw = load_raw_local_events()
    status_map = {}
    for e in raw:
        if e.get("is_status_override") and not e.get("is_deleted"):
            status_map[e.get("status_key")] = e.get("status")
        elif e.get("status") and not e.get("is_deleted"):
            status_map[f"{e.get('id')}_{e.get('start_date')}"] = e.get("status")
    return status_map

def set_event_status(event_id, start_date, status):
    """Sets status ('done', 'cancelled', or 'pending') for an event on a specific date."""
    key = f"{event_id}_{start_date}"
    raw = load_raw_local_events()
    
    for e in raw:
        if not e.get("is_deleted") and not e.get("is_status_override"):
            if str(e.get("id")) == str(event_id) and e.get("start_date") == start_date:
                e["status"] = status
                
    override_found = False
    for e in raw:
        if e.get("is_status_override") and e.get("status_key") == key:
            override_found = True
            if status == "pending":
                e["is_deleted"] = True
            else:
                e["status"] = status
                e["is_deleted"] = False
            break
            
    if not override_found and status != "pending":
        raw.append({
            "id": f"status_{key}",
            "is_status_override": True,
            "status_key": key,
            "status": status,
            "updated_at": datetime.now().isoformat()
        })
        
    save_raw_local_events(raw)
    return True

def save_local_events(events):
    raw = load_raw_local_events()
    tombstones = [e for e in raw if e.get("is_deleted")]
    normalized = [_normalize_event(e) for e in events if not e.get("is_deleted")]
    return save_raw_local_events(normalized + tombstones)

def add_event(event_data):
    events = load_local_events()
    next_id = max([e.get("id", 0) for e in events if isinstance(e.get("id"), int)] + [0]) + 1
    event_data["id"] = next_id
    event_data["created_at"] = datetime.now().isoformat()
    event_data = _normalize_event(event_data)
    if not event_data.get("category") or event_data["category"] not in CATEGORIES:
        event_data["category"] = "Altres"
    events.append(event_data)
    save_local_events(events)
    return event_data

def update_event(event_id, updated_data):
    events = load_local_events()
    found = False
    for i, e in enumerate(events):
        if str(e.get("id")) == str(event_id):
            updated_data["id"] = event_id
            updated_data["updated_at"] = datetime.now().isoformat()
            updated_data = _normalize_event(updated_data)
            events[i] = updated_data
            save_local_events(events)
            return True
            
    # If not found in local events, it is an external event (e.g. from Google Calendar)
    # We exclude the original external event and save the modified version locally!
    delete_event(event_id, uid=updated_data.get("uid"), start_date=updated_data.get("start_date"))
    next_id = max([e.get("id", 0) for e in events if isinstance(e.get("id"), int)] + [0]) + 1
    updated_data["id"] = next_id
    updated_data["is_external"] = False
    updated_data["created_at"] = datetime.now().isoformat()
    updated_data = _normalize_event(updated_data)
    events.append(updated_data)
    save_local_events(events)
    return True

def delete_event(event_id, uid=None, start_date=None):
    raw = load_raw_local_events()
    new_raw = []
    found_local = False
    for e in raw:
        if str(e.get("id")) == str(event_id) and not e.get("is_deleted"):
            found_local = True
        else:
            new_raw.append(e)
            
    if found_local:
        save_raw_local_events(new_raw)
        return True
        
    # If it is an external event (or recurrence instance), register a tombstone
    tombstone = {
        "id": f"deleted_{event_id}",
        "excluded_id": str(event_id),
        "excluded_uid": uid,
        "excluded_date": start_date,
        "is_deleted": True,
        "created_at": datetime.now().isoformat()
    }
    new_raw.append(tombstone)
    save_raw_local_events(new_raw)
    return True

def unfold_ics_lines(raw_text):
    """Unfolds lines in iCalendar format where folded lines start with space or tab."""
    lines = raw_text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    unfolded = []
    for line in lines:
        if line.startswith(" ") or line.startswith("\t"):
            if unfolded:
                unfolded[-1] += line[1:]
        else:
            unfolded.append(line)
    return unfolded

def parse_ics_datetime(dt_str):
    """Parse iCalendar DTSTART / DTEND strings like 20260419T140000Z or 20260419."""
    if not dt_str:
        return None, True
    # Strip parameters if any (e.g., TZID=Europe/Madrid:20260419T140000)
    if ":" in dt_str:
        dt_str = dt_str.split(":")[-1]
    dt_str = dt_str.strip()
    
    # Date only (All day)
    if len(dt_str) == 8 and dt_str.isdigit():
        try:
            d = datetime.strptime(dt_str, "%Y%m%d").date()
            return datetime.combine(d, time(0, 0)), True
        except Exception:
            return None, True
            
    # DateTime with Z or local
    dt_clean = dt_str.rstrip("Z")
    for fmt in ["%Y%m%dT%H%M%S", "%Y%m%dT%H%M", "%Y%m%d"]:
        try:
            return datetime.strptime(dt_clean, fmt), False
        except ValueError:
            continue
    try:
        return dateutil.parser.parse(dt_str), False
    except Exception:
        return None, True

def parse_ics_content(ics_text, source_name="Google Calendar", default_member="Tota la família", default_color="#407faf"):
    """Parses standard iCalendar VEVENT components into normalized event dictionaries."""
    unfolded = unfold_ics_lines(ics_text)
    events = []
    in_event = False
    cur = {}
    
    for line in unfolded:
        line_clean = line.strip()
        if line_clean == "BEGIN:VEVENT":
            in_event = True
            cur = {
                "source": source_name,
                "member": default_member,
                "color": default_color,
                "is_external": True,
                "category": "Altres"
            }
        elif line_clean == "END:VEVENT" and in_event:
            in_event = False
            if "start_date" in cur:
                # Deduce category from title/description
                title_lower = (cur.get("title", "") + " " + cur.get("description", "")).lower()
                if any(w in title_lower for w in ["metge", "dentista", "hospital", "salut", "dr", "doctor", "analitica", "medic"]):
                    cur["category"] = "Metge"
                elif any(w in title_lower for w in ["dinar", "almuerzo", "comida"]):
                    cur["category"] = "Dinar"
                elif any(w in title_lower for w in ["sopar", "cena"]):
                    cur["category"] = "Sopar"
                elif any(w in title_lower for w in ["escola", "cole", "classe", "curs", "examen", "universitat", "institut"]):
                    cur["category"] = "Escola"
                elif any(w in title_lower for w in ["feina", "reunio", "meeting", "work", "projecte", "client"]):
                    cur["category"] = "Feina"
                elif any(w in title_lower for w in ["aniversari", "cumple", "festa", "celebracio", "boda"]):
                    cur["category"] = "Aniversari"
                elif any(w in title_lower for w in ["viatge", "vol", "hotel", "partit", "gimnas", "padel", "futbol", "cinema"]):
                    cur["category"] = "Oci"
                elif any(w in title_lower for w in ["llar", "reparacio", "itv", "assegurança", "neteja", "compra"]):
                    cur["category"] = "Llar"
                events.append(cur)
            cur = {}
        elif in_event:
            if ":" in line_clean:
                prop_header, val = line_clean.split(":", 1)
                prop = prop_header.split(";")[0].upper()
                val = val.replace(r"\n", "\n").replace(r"\,", ",").replace(r"\;", ";")
                
                if prop == "UID":
                    cur["uid"] = val
                    cur["id"] = f"gcal_{val}"
                elif prop == "SUMMARY":
                    cur["title"] = val
                elif prop == "DESCRIPTION":
                    cur["description"] = val
                elif prop == "LOCATION":
                    cur["location"] = val
                elif prop == "DTSTART":
                    dt_val, is_allday = parse_ics_datetime(line_clean)
                    if dt_val:
                        cur["start"] = dt_val.strftime("%Y-%m-%d %H:%M")
                        cur["start_date"] = dt_val.strftime("%Y-%m-%d")
                        cur["start_time"] = dt_val.strftime("%H:%M") if not is_allday else ""
                        cur["all_day"] = is_allday
                elif prop == "DTEND":
                    dt_val, is_allday = parse_ics_datetime(line_clean)
                    if dt_val:
                        cur["end"] = dt_val.strftime("%Y-%m-%d %H:%M")
                        cur["end_date"] = dt_val.strftime("%Y-%m-%d")
                        cur["end_time"] = dt_val.strftime("%H:%M") if not is_allday else ""
                elif prop == "RRULE":
                    cur["rrule"] = val
                elif prop == "RECURRENCE-ID":
                    cur["recurrence_id"] = val
                    cur["has_recurrence_id"] = True
                    
    return events

def fetch_feed_cached(feed_url, member_name="Enric", member_color="#407faf", max_age_seconds=600):
    """Fetches iCal feed with caching."""
    cache = {}
    
    # Try Supabase (id=4)
    try:
        from core.db import get_supabase_client
        supabase = get_supabase_client("guest")
        res = supabase.table("app_config").select("config_json").eq("id", 4).execute()
        if res.data and len(res.data) > 0:
            cache = res.data[0]["config_json"] or {}
    except Exception as e:
        print("Supabase cache_feeds load failed:", e)
        # Fallback local
        ensure_data_dir()
        if os.path.exists(CACHE_FEEDS_FILE):
            try:
                with open(CACHE_FEEDS_FILE, "r", encoding="utf-8") as f:
                    cache = json.load(f)
            except Exception:
                cache = {}
            
    cache_entry = cache.get(feed_url, {})
    last_fetched = cache_entry.get("timestamp", 0)
    now_ts = datetime.now().timestamp()
    
    # If valid cache
    if now_ts - last_fetched < max_age_seconds and "events" in cache_entry:
        return cache_entry["events"]
        
    ics_text = ""
    # Check if local file path
    if os.path.exists(feed_url):
        try:
            with open(feed_url, "r", encoding="utf-8", errors="ignore") as f:
                ics_text = f.read()
        except Exception as e:
            print(f"Error reading local ICS {feed_url}: {e}")
    elif feed_url.startswith("http://") or feed_url.startswith("https://") or feed_url.startswith("webcal://"):
        try:
            # Handle webcal:// links by replacing with https://
            url = feed_url.replace("webcal://", "https://")
            resp = requests.get(url, timeout=8)
            if resp.status_code == 200:
                ics_text = resp.text
        except Exception as e:
            print(f"Error fetching iCal feed {feed_url}: {e}")
            if "events" in cache_entry:
                return cache_entry["events"]
                
    if ics_text:
        events = parse_ics_content(ics_text, source_name=f"Google Calendar ({member_name})", default_member=member_name, default_color=member_color)
        cache[feed_url] = {
            "timestamp": now_ts,
            "events": events
        }
        
        # Save to Supabase (id=4)
        try:
            from core.db import get_supabase_client
            supabase = get_supabase_client("admin")
            supabase.table("app_config").upsert({
                "id": 4,
                "config_json": cache
            }).execute()
        except Exception as e:
            print("Error saving cache to Supabase:", e)
            
        # Backup local
        ensure_data_dir()
        try:
            with open(CACHE_FEEDS_FILE, "w", encoding="utf-8") as f:
                json.dump(cache, f, ensure_ascii=False)
        except Exception:
            pass
        return events
        
    return cache_entry.get("events", [])

def sort_events_by_time(events_list):
    def _time_key(e):
        is_timed = bool(not e.get("all_day", False) and e.get("start_time"))
        t_str = e.get("start_time", "") or ""
        if ":" in t_str:
            parts = t_str.split(":")
            try:
                t_str = f"{int(parts[0]):02d}:{parts[1]}"
            except Exception:
                pass
        return (1 if is_timed else 0, t_str)
    return sorted(events_list, key=_time_key)

def clean_title_for_dedup(title: str) -> str:
    if not title:
        return ""
    t = re.sub(r'[✅✔✓⭐️]+', '', title)
    t = re.sub(r'\s+', ' ', t).strip().lower()
    return t

def deduplicate_events(events: list) -> list:
    """Deduplicates calendar events based on date, time, title, member, and UID."""
    seen_keys = {}
    deduped = []
    
    for ev in events:
        uid = ev.get("uid", "")
        d_str = ev.get("start_date", "")
        t_str = ev.get("start_time", "") if not ev.get("all_day", False) else ""
        title_c = clean_title_for_dedup(ev.get("title", ""))
        mem = (ev.get("member") or "").strip().lower()
        
        # Primary key: date, time, normalized title, member
        key = (d_str, t_str, title_c, mem)
        # Secondary key for Google Calendar UID per date
        uid_key = (uid, d_str) if uid else None
        
        match_idx = None
        if uid_key and uid_key in seen_keys:
            match_idx = seen_keys[uid_key]
        elif key in seen_keys:
            match_idx = seen_keys[key]
            
        if match_idx is not None:
            existing = deduped[match_idx]
            # If current is an exception instance (recurrence override), it takes precedence over recurring instance
            # Preserve status if existing had it or current has it
            final_status = ev.get("status") or existing.get("status") or "pending"
            if ev.get("has_recurrence_id") or ev.get("recurrence_id"):
                ev["status"] = final_status
                deduped[match_idx] = ev
            elif final_status != "pending":
                existing["status"] = final_status
            # Otherwise keep the version with checkmark or richer description
            elif ("✅" in ev.get("title", "") or "✔" in ev.get("title", "")) and not ("✅" in existing.get("title", "") or "✔" in existing.get("title", "")):
                deduped[match_idx] = ev
            elif len(ev.get("description", "") or "") > len(existing.get("description", "") or ""):
                if existing.get("description") and existing.get("description") not in (ev.get("description") or ""):
                    ev["description"] = f"{existing.get('description')}\n{ev.get('description')}".strip()
                deduped[match_idx] = ev
            continue
            
        idx = len(deduped)
        deduped.append(ev)
        seen_keys[key] = idx
        if uid_key:
            seen_keys[uid_key] = idx
            
    return deduped

def expand_recurring_events(events, target_year, target_month=None):
    """Expands annual or recurring events into target year/month, and filters non-recurring events."""
    expanded = []
    status_map = get_event_status_map()
    
    for ev in events:
        recurrence = ev.get("repeat", "Cap")
        start_date_str = ev.get("start_date", "")
        if not start_date_str:
            continue
            
        try:
            ev_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        except Exception:
            continue
            
        rrule_str = ev.get("rrule", "").upper()
        if recurrence == "Cap" and rrule_str:
            if "FREQ=YEARLY" in rrule_str:
                recurrence = "Anual"
            elif "FREQ=MONTHLY" in rrule_str:
                recurrence = "Mensual"
            elif "FREQ=WEEKLY" in rrule_str:
                recurrence = "Setmanal"
            elif "FREQ=DAILY" in rrule_str:
                recurrence = "Diari"
                
        until_date = None
        if "UNTIL=" in rrule_str:
            try:
                until_part = rrule_str.split("UNTIL=")[1].split(";")[0][:8]
                until_date = datetime.strptime(until_part, "%Y%m%d").date()
            except Exception:
                pass

        is_anniversary_local = (ev.get("category") == "Aniversari" and not ev.get("is_external", False))
        is_override = bool(ev.get("has_recurrence_id") or ev.get("recurrence_id"))

        if (recurrence == "Anual" or is_anniversary_local) and not is_override:
            try:
                new_date = date(target_year, ev_date.month, ev_date.day)
            except ValueError:
                new_date = date(target_year, ev_date.month, 28)
                
            if until_date and new_date > until_date:
                continue
            if ev_date > new_date:
                continue
            if target_month and new_date.month != target_month:
                continue
                
            ev_copy = dict(ev)
            ev_copy["start_date"] = new_date.strftime("%Y-%m-%d")
            ev_copy["is_recurrence_instance"] = True
            expanded.append(ev_copy)
            
        elif recurrence == "Mensual":
            m_start = target_month if target_month else 1
            m_end = target_month if target_month else 12
            for m in range(m_start, m_end + 1):
                try:
                    new_date = date(target_year, m, ev_date.day)
                    if until_date and new_date > until_date:
                        continue
                    if new_date < ev_date:
                        continue
                    ev_copy = dict(ev)
                    ev_copy["start_date"] = new_date.strftime("%Y-%m-%d")
                    ev_copy["is_recurrence_instance"] = True
                    expanded.append(ev_copy)
                except ValueError:
                    pass
                    
        elif recurrence == "Setmanal":
            if target_month:
                first_d = date(target_year, target_month, 1)
                last_d = date(target_year, target_month, 28) + timedelta(days=4)
                last_d = last_d.replace(day=1) - timedelta(days=1)
                
                curr = first_d
                while curr <= last_d:
                    if curr.weekday() == ev_date.weekday() and curr >= ev_date:
                        if not (until_date and curr > until_date):
                            ev_copy = dict(ev)
                            ev_copy["start_date"] = curr.strftime("%Y-%m-%d")
                            ev_copy["is_recurrence_instance"] = True
                            expanded.append(ev_copy)
                    curr += timedelta(days=1)
            else:
                expanded.append(ev)
                
        else:
            # Non-recurring event: strictly filter by target_year and target_month
            if target_year:
                if target_month:
                    # Allow 7 days buffer around the month for the calendar grid border weeks
                    first_d = date(target_year, target_month, 1) - timedelta(days=7)
                    last_d = date(target_year, target_month, 28) + timedelta(days=11)
                    if not (first_d <= ev_date <= last_d):
                        continue
                else:
                    if ev_date.year != target_year:
                        continue
            expanded.append(ev)
            
    return deduplicate_events(expanded)

def get_all_events(app_cfg=None, target_year=None, target_month=None):
    """Retrieves merged list of local events and configured Google Calendar feeds."""
    local_events = load_local_events()
    raw_local = load_raw_local_events()
    excluded_ids = {str(e.get("excluded_id")) for e in raw_local if e.get("is_deleted") and e.get("excluded_id")}
    excluded_uids = {(e.get("excluded_uid"), e.get("excluded_date")) for e in raw_local if e.get("is_deleted") and e.get("excluded_uid")}
    
    feed_events = []
    if app_cfg:
        familia = app_cfg.get("familia", [])
        for mem in familia:
            g_feed = mem.get("google_calendar_ical", "").strip()
            mem_nom = mem.get("nom", "Familiar")
            mem_color = mem.get("color", "#407faf")
            if g_feed:
                f_evs = fetch_feed_cached(g_feed, member_name=mem_nom, member_color=mem_color)
                feed_events.extend(f_evs)
                
    # Also check if enricxicars@gmail.com.ics exists locally as fallback demo feed if no URL
    if not feed_events and os.path.exists("enricxicars@gmail.com.ics"):
        local_ics_evs = fetch_feed_cached("enricxicars@gmail.com.ics", member_name="Enric", member_color="#407faf")
        feed_events.extend(local_ics_evs)
        
    filtered_feed = []
    for f in feed_events:
        if str(f.get("id")) in excluded_ids:
            continue
        if f.get("uid") and (f.get("uid"), f.get("start_date")) in excluded_uids:
            continue
        filtered_feed.append(f)
        
    all_raw = local_events + filtered_feed
    status_map = get_event_status_map()
    for ev in all_raw:
        s_k = f"{ev.get('id')}_{ev.get('start_date')}"
        if s_k in status_map:
            ev["status"] = status_map[s_k]
    
    if target_year:
        return expand_recurring_events(all_raw, target_year, target_month)
    return deduplicate_events(all_raw)

def generate_google_calendar_url(event):
    """Generates direct Google Calendar Web template URL to add event in 1 click."""
    title = event.get("title", "Esdeveniment")
    desc = event.get("description", "")
    loc = event.get("location", "")
    start_d = event.get("start_date", datetime.now().strftime("%Y-%m-%d"))
    start_t = event.get("start_time", "10:00").replace(":", "")
    all_day = event.get("all_day", False)
    
    if all_day:
        d_start = start_d.replace("-", "")
        try:
            d_obj = datetime.strptime(start_d, "%Y-%m-%d") + timedelta(days=1)
            d_end = d_obj.strftime("%Y%m%d")
        except Exception:
            d_end = d_start
        dates_param = f"{d_start}/{d_end}"
    else:
        end_d = event.get("end_date", start_d)
        end_t = event.get("end_time", "11:00").replace(":", "")
        dates_param = f"{start_d.replace('-', '')}T{start_t}00/{end_d.replace('-', '')}T{end_t}00"
        
    params = {
        "action": "TEMPLATE",
        "text": title,
        "dates": dates_param,
        "details": desc,
        "location": loc
    }
    return "https://calendar.google.com/calendar/render?" + urllib.parse.urlencode(params)

def parse_natural_language_event(text_input, default_member="Tota la família"):
    """Quick natural text parser to extract event details from Catalan / Spanish sentences."""
    txt = text_input.strip()
    if not txt:
        return None
        
    today = date.today()
    extracted_date = today
    extracted_time = "10:00"
    all_day = False
    
    t_lower = txt.lower()
    if "avui" in t_lower or "hoy" in t_lower:
        extracted_date = today
    elif "demà passat" in t_lower or "pasado mañana" in t_lower:
        extracted_date = today + timedelta(days=2)
    elif "demà" in t_lower or "dema" in t_lower or "mañana" in t_lower:
        extracted_date = today + timedelta(days=1)
        
    weekdays_ca = {
        "dilluns": 0, "dimarts": 1, "dimecres": 2, "dijous": 3, "divendres": 4, "dissabte": 5, "diumenge": 6,
        "lunes": 0, "martes": 1, "miercoles": 2, "miércoles": 2, "jueves": 3, "viernes": 4, "sabado": 5, "sábado": 5, "domingo": 6
    }
    for wname, wday in weekdays_ca.items():
        if wname in t_lower:
            days_ahead = (wday - today.weekday() + 7) % 7
            if days_ahead == 0:
                days_ahead = 7
            extracted_date = today + timedelta(days=days_ahead)
            break
            
    date_match = re.search(r"(\d{1,2})[\/\.-](\d{1,2})(?:[\/\.-](\d{2,4}))?", txt)
    if date_match:
        day = int(date_match.group(1))
        month = int(date_match.group(2))
        year = int(date_match.group(3)) if date_match.group(3) else today.year
        if year < 100:
            year += 2000
        try:
            extracted_date = date(year, month, day)
        except Exception:
            pass
            
    time_match = re.search(r"(?:a les|a las|les|las|at)?\s*(\d{1,2})(?::(\d{2})|h(?:(\d{2}))?)", t_lower)
    if time_match:
        hr = int(time_match.group(1))
        mn = int(time_match.group(2) or time_match.group(3) or 0)
        extracted_time = f"{hr:02d}:{mn:02d}"
    elif "tot el dia" in t_lower or "todo el dia" in t_lower:
        all_day = True
        
    cat = "Altres"
    if any(w in t_lower for w in ["metge", "dentista", "hospital", "salut", "dr", "doctor", "analitica", "oculista"]):
        cat = "Metge"
    elif any(w in t_lower for w in ["dinar", "almuerzo", "comida"]):
        cat = "Dinar"
        if not time_match and not all_day:
            extracted_time = "14:00"
    elif any(w in t_lower for w in ["sopar", "cena"]):
        cat = "Sopar"
        if not time_match and not all_day:
            extracted_time = "21:00"
    elif any(w in t_lower for w in ["escola", "cole", "classe", "curs", "examen", "reunio escola"]):
        cat = "Escola"
    elif any(w in t_lower for w in ["feina", "reunio", "meeting", "treball", "projecte", "client"]):
        cat = "Feina"
    elif any(w in t_lower for w in ["aniversari", "cumple", "festa", "celebracio"]):
        cat = "Aniversari"
    elif any(w in t_lower for w in ["viatge", "vol", "hotel", "partit", "gimnas", "padel", "futbol"]):
        cat = "Oci"
    elif any(w in t_lower for w in ["llar", "reparacio", "itv", "assegurança", "neteja", "cotxe"]):
        cat = "Llar"
        
    return {
        "title": txt,
        "member": default_member,
        "category": cat,
        "start_date": extracted_date.strftime("%Y-%m-%d"),
        "start_time": extracted_time,
        "all_day": all_day,
        "repeat": "Cap",
        "description": f"Creat ràpidament: {txt}",
        "location": ""
    }
