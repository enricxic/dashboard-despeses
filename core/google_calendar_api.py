import os
import json
from datetime import datetime, date, time, timedelta

CREDENTIALS_FILE = "core/google_credentials.json"
SCOPES = ["https://www.googleapis.com/auth/calendar"]

def get_calendar_service():
    """Returns an authorized Google Calendar API service instance if credentials exist, else None."""
    if not os.path.exists(CREDENTIALS_FILE):
        return None
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        creds = service_account.Credentials.from_service_account_file(
            CREDENTIALS_FILE, scopes=SCOPES
        )
        service = build("calendar", "v3", credentials=creds)
        return service
    except Exception as e:
        print(f"Error initializing Google Calendar service: {e}")
        return None

def is_service_account_configured():
    """Checks whether the Google Service Account credentials file is present."""
    return os.path.exists(CREDENTIALS_FILE)

def get_service_account_email():
    """Extracts the client email of the configured service account."""
    if not os.path.exists(CREDENTIALS_FILE):
        return None
    try:
        with open(CREDENTIALS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("client_email")
    except Exception:
        return None

def create_single_event(service, calendar_id, event_dict):
    """Creates a single event in the specified Google Calendar."""
    start_d = event_dict.get("start_date")
    start_t = event_dict.get("start_time", "09:00")
    title = event_dict.get("title", "Esdeveniment")
    desc = event_dict.get("description", "")
    loc = event_dict.get("location", "")
    
    start_dt = f"{start_d}T{start_t}:00"
    # End 15 minutes later by default for medication dose
    try:
        dt_obj = datetime.strptime(start_dt, "%Y-%m-%dT%H:%M:%S") + timedelta(minutes=15)
        end_dt = dt_obj.strftime("%Y-%m-%dT%H:%M:%S")
    except Exception:
        end_dt = start_dt

    body = {
        "summary": title,
        "description": desc,
        "location": loc,
        "start": {
            "dateTime": start_dt,
            "timeZone": "Europe/Madrid"
        },
        "end": {
            "dateTime": end_dt,
            "timeZone": "Europe/Madrid"
        },
        "reminders": {
            "useDefault": False,
            "overrides": [
                {"method": "popup", "minutes": 15},
                {"method": "popup", "minutes": 0}
            ]
        }
    }
    
    try:
        created = service.events().insert(calendarId=calendar_id, body=body).execute()
        return created.get("id")
    except Exception as e:
        print(f"Error inserting event into Google Calendar ({calendar_id}): {e}")
        return None

def create_batch_medication_events(calendar_id, events_list):
    """
    Creates multiple events via Google Calendar API.
    Returns (success_count, list_of_created_event_ids).
    """
    service = get_calendar_service()
    if not service:
        return 0, []
        
    created_ids = []
    for ev in events_list:
        ev_id = create_single_event(service, calendar_id, ev)
        if ev_id:
            created_ids.append(ev_id)
            
    return len(created_ids), created_ids

def check_confirmed_events(calendar_id, event_id_map):
    """
    Checks if events in Google Calendar have been marked with ✅ or OK in summary/description.
    event_id_map is a dict {gcal_event_id: internal_event_obj}.
    Returns a dict {gcal_event_id: {"is_confirmed": bool, "confirmed_at": str, "title": str}}.
    """
    service = get_calendar_service()
    results = {}
    if not service or not event_id_map:
        return results
        
    for gcal_id in event_id_map.keys():
        try:
            ev = service.events().get(calendarId=calendar_id, eventId=gcal_id).execute()
            summary = ev.get("summary", "")
            desc = ev.get("description", "")
            
            # Check for confirmation markers
            is_confirmed = (
                "✅" in summary or 
                "✔️" in summary or 
                "☑️" in summary or 
                summary.strip().lower().startswith("ok") or 
                "[x]" in summary.lower() or
                "✅" in desc
            )
            
            updated_ts = ev.get("updated", datetime.now().isoformat())
            results[gcal_id] = {
                "is_confirmed": is_confirmed,
                "confirmed_at": updated_ts if is_confirmed else None,
                "current_title": summary
            }
        except Exception as e:
            print(f"Error fetching event {gcal_id}: {e}")
            
    return results

def generate_ics_download_content(events_list, plan_title="Pla_Medicacio"):
    """Generates standard iCalendar (.ics) format file content for manual bulk import."""
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Dashboard Familiar//Pla Medicacio//CA",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH"
    ]
    
    for idx, ev in enumerate(events_list):
        d_str = ev.get("start_date", "").replace("-", "")
        t_str = ev.get("start_time", "08:00").replace(":", "") + "00"
        dt_start = f"{d_str}T{t_str}"
        
        # End 15 min later
        try:
            st_dt = datetime.strptime(f"{ev.get('start_date')} {ev.get('start_time')}", "%Y-%m-%d %H:%M") + timedelta(minutes=15)
            dt_end = st_dt.strftime("%Y%m%dT%H%M00")
        except Exception:
            dt_end = dt_start
            
        uid = f"med_plan_{datetime.now().strftime('%Y%m%d%H%M%S')}_{idx}@dashboard.local"
        
        lines.extend([
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"DTSTAMP:{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}",
            f"DTSTART:{dt_start}",
            f"DTEND:{dt_end}",
            f"SUMMARY:{ev.get('title')}",
            f"DESCRIPTION:{ev.get('description', '')}",
            "STATUS:CONFIRMED",
            "BEGIN:VALARM",
            "TRIGGER:-PT15M",
            "ACTION:DISPLAY",
            "DESCRIPTION:Recordatori de presa de medicació",
            "END:VALARM",
            "END:VEVENT"
        ])
        
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines)
