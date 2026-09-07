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
    "Escola": {"icon": "🏫", "color": "#3b82f6", "label": "Escola i Estudis"},
    "Feina": {"icon": "💼", "color": "#8b5cf6", "label": "Feina i Tasques"},
    "Aniversari": {"icon": "🎂", "color": "#ec4899", "label": "Aniversari i Celebració"},
    "Oci": {"icon": "✈️", "color": "#10b981", "label": "Oci, Viatges i Esport"},
    "Llar": {"icon": "🏠", "color": "#f59e0b", "label": "Llar i Manteniment"},
    "Altres": {"icon": "⭐", "color": "#06b6d4", "label": "Altres / General"}
}

def ensure_data_dir():
    os.makedirs(os.path.dirname(EVENTS_FILE), exist_ok=True)

def load_local_events():
    ensure_data_dir()
    if not os.path.exists(EVENTS_FILE):
        return []
    try:
        with open(EVENTS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception as e:
        print(f"Error loading {EVENTS_FILE}: {e}")
        return []

def save_local_events(events):
    ensure_data_dir()
    try:
        with open(EVENTS_FILE, "w", encoding="utf-8") as f:
            json.dump(events, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error saving {EVENTS_FILE}: {e}")
        return False

def add_event(event_data):
    events = load_local_events()
    next_id = max([e.get("id", 0) for e in events if isinstance(e.get("id"), int)] + [0]) + 1
    event_data["id"] = next_id
    event_data["created_at"] = datetime.now().isoformat()
    if not event_data.get("category") or event_data["category"] not in CATEGORIES:
        event_data["category"] = "Altres"
    events.append(event_data)
    save_local_events(events)
    return event_data

def update_event(event_id, updated_data):
    events = load_local_events()
    for i, e in enumerate(events):
        if e.get("id") == event_id:
            updated_data["id"] = event_id
            updated_data["updated_at"] = datetime.now().isoformat()
            events[i] = updated_data
            save_local_events(events)
            return True
    return False

def delete_event(event_id):
    events = load_local_events()
    new_events = [e for e in events if e.get("id") != event_id]
    if len(new_events) != len(events):
        save_local_events(new_events)
        return True
    return False

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
                    
    return events

def fetch_feed_cached(feed_url, member_name="Enric", member_color="#407faf", max_age_seconds=600):
    """Fetches iCal feed with caching."""
    ensure_data_dir()
    cache = {}
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
        try:
            with open(CACHE_FEEDS_FILE, "w", encoding="utf-8") as f:
                json.dump(cache, f, ensure_ascii=False)
        except Exception:
            pass
        return events
        
    return cache_entry.get("events", [])

def expand_recurring_events(events, target_year, target_month=None):
    """Expands annual or recurring events into target year/month."""
    expanded = []
    
    for ev in events:
        recurrence = ev.get("repeat", "Cap")
        start_date_str = ev.get("start_date", "")
        if not start_date_str:
            continue
            
        try:
            ev_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        except Exception:
            continue
            
        if recurrence == "Anual" or ev.get("category") == "Aniversari":
            if target_month:
                if ev_date.month == target_month:
                    ev_copy = dict(ev)
                    new_date = date(target_year, ev_date.month, ev_date.day)
                    ev_copy["start_date"] = new_date.strftime("%Y-%m-%d")
                    ev_copy["is_recurrence_instance"] = True
                    expanded.append(ev_copy)
            else:
                ev_copy = dict(ev)
                new_date = date(target_year, ev_date.month, ev_date.day)
                ev_copy["start_date"] = new_date.strftime("%Y-%m-%d")
                ev_copy["is_recurrence_instance"] = True
                expanded.append(ev_copy)
        elif recurrence == "Mensual":
            m_start = target_month if target_month else 1
            m_end = target_month if target_month else 12
            for m in range(m_start, m_end + 1):
                try:
                    new_date = date(target_year, m, ev_date.day)
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
                        ev_copy = dict(ev)
                        ev_copy["start_date"] = curr.strftime("%Y-%m-%d")
                        ev_copy["is_recurrence_instance"] = True
                        expanded.append(ev_copy)
                    curr += timedelta(days=1)
            else:
                expanded.append(ev)
        else:
            expanded.append(ev)
            
    return expanded

def get_all_events(app_cfg=None, target_year=None, target_month=None):
    """Retrieves merged list of local events and configured Google Calendar feeds."""
    local_events = load_local_events()
    
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
        
    all_raw = local_events + feed_events
    
    if target_year:
        return expand_recurring_events(all_raw, target_year, target_month)
    return all_raw

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
    elif any(w in t_lower for w in ["escola", "cole", "classe", "curs", "examen", "reunio escola"]):
        cat = "Escola"
    elif any(w in t_lower for w in ["feina", "reunio", "meeting", "treball", "projecte", "client"]):
        cat = "Feina"
    elif any(w in t_lower for w in ["aniversari", "cumple", "festa", "celebracio"]):
        cat = "Aniversari"
    elif any(w in t_lower for w in ["viatge", "vol", "hotel", "partit", "gimnas", "padel", "futbol", "sopar", "dinar"]):
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
