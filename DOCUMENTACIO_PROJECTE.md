# Documentació del Projecte: Dashboard Despeses (V2)

Aquest document descriu l'arquitectura, funcionalitats i regles de l'aplicació per assegurar que qualsevol nova sessió o agent d'IA entengui el context immediatament sense dependre de la memòria de converses anteriors.

## 1. Visió General i Arquitectura (V2 Modular)
L'aplicació ha transicionat d'un model monolític (`app.py`) a una **arquitectura modular V2** molt més neta i fàcil de mantenir.
- **Frontend / Backend**: Construïda en **Streamlit** (Python).
- **Entrada Principal (Router)**: L'arxiu **`app_v2.py`** actua com a menú principal (Home Screen). Mostra grans botons quadrats per accedir als diferents mòduls i s'encarrega d'importar-los dinàmicament quan l'usuari hi fa clic.
- **Base de Dades**: **Supabase** (PostgreSQL). La lògica de comunicació s'ha extret al mòdul centralitzat `core/db.py`.
- **Autenticació**: Es gestiona globalment des de `core/auth.py` només obrir `app_v2.py`.
- **Estat de Navegació**: Es controla mitjançant `st.session_state.current_module`. Per tornar enrere, els mòduls inclouen un botó `🔙 Tornar a l'inici` a la capçalera que posa aquesta variable a `None`.

## 2. Estructura de Directori i Arxius Actius
L'estructura actual del projecte V2 és la següent:
- `app_v2.py`: Router principal de navegació.
- `core/`: Nucli de l'aplicació.
  - `auth.py`: Lògica de login (contrasenya).
  - `db.py`: Totes les crides CRUD a Supabase i sincronització d'estat.
  - `config.json`: Fitxer de configuració global per categories, comptes, etc.
- `modules/`: Mòduls de la interfície. Cadascun té una funció `render()` que dibuixa la pàgina.
  - `economic.py`: Àrea econòmica (Dashboard Despeses, Detalls, Intro Dades, Xat IA).
  - `menjar.py`: Control de rebost, inventari i generació de menús.
  - `compres.py`: Mòdul exclusiu per introduir tiquets del súper (manual o via OCR amb Gemini).
  - `admin.py`: Panell de configuració global.
  - `calendari.py`: Agenda i manteniment.
  - `domotica.py`: Integració futura amb Home Assistant.
- *Nota Històrica*: `app.py` original es manté com a fallback, però el desenvolupament actiu es fa sobre la branca modular.

## 3. Lògica Avançada (OCR i Gemini)
- L'extracció de tiquets del súper a `compres.py` i `app.py` funciona exclusivament a través de **Google Gemini Vision** (`gemini-3.6-flash`), cridant directament l'API mitjançant la llibreria `requests` (amb sistema de reintents / retry automàtic si l'API retorna error 503 per saturació).
- S'evita l'ús de `pytesseract` com a motor principal per qüestions de fiabilitat en el desplegament al núvol.
- L'API Key de Gemini està guardada als `st.secrets` (`GEMINI_API_KEY`).

### 3.1 Introducció Manual de Línies de Tiquet amb Descompte (Enginyeria Inversa)
- Quan un usuari introdueix manualment un article al tiquet a `modules/compres.py`, el flux de treball assumeix que s'està introduint el **preu final ja pagat** (tal com sol sortir als tiquets de Dia o Lidl). 
- Si l'usuari posa un preu de `1.25€` i marca que li han fet un `%` de descompte del `30%`, l'aplicació fa un càlcul a la inversa (*enginyeria inversa*):
  1. Calcula la base original: `preu_original = 1.25 / (1 - 0.30) = 1.79€`
  2. Actualitza la casella del `PREU UNIT.` automàticament a `1.79€`.
  3. Calcula i emplena la casella de `PROMOCIÓ` amb l'estalvi: `0.54€`
  4. Manté el `TOTAL LÍNIA` en `1.25€` (que és l'import que realment es sumarà a la despesa del tiquet).
Això permet registrar històrics de preus fiables dels productes sense que l'usuari hagi de calcular-los a mà.

## 4. Convencions de Disseny (UI/UX)
- **CSS i Marge Superior**: A `app_v2.py` s'injecta CSS extremadament agressiu per eliminar l'espai i el padding superior de Streamlit (`div.block-container {padding-top: 0rem !important;}`). Així mateix, s'oculten les insígnies del núvol (`viewerBadge`, footer).
- **Formatació Títols**: Els mòduls NO utilitzen `st.set_page_config()` per evitar errors de Streamlit. A la funció `render()` dibuixen directament la seva capçalera amb columnes (Títol a l'esquerra, Botó de "Tornar a l'inici" a la dreta).
- **Metriques Horitzontals**: A la secció de bancs (`economic.py`), els botons es dibuixen usant un sistema de *chunking* (grups de 4 columnes màxim per línia) i text amb salt de línia intern (`\n`), per tal d'evitar que els valors dels comptes bancaris quedin truncats i tallats quan n'hi ha molts.

## 5. Estratègia de Sincronització (Memòria i Base de Dades)
L'aplicació utilitza actualitzacions d'estat en temps real (zero latència):
- Quan `core/db.py` executa `insert_db_row`, `update_db_row` o `delete_db_row`, no només envia la petició SQL a Supabase, sinó que automàticament **modifica el DataFrame corresponent a `st.session_state`**.
- Això evita que els dashboards hagin de recarregar massivament totes les taules cada vegada que s'edita o s'afegeix una simple despesa.

## 6. Com instruir a noves IAs
Si inicies una conversa nova amb un agent o assistent, digues-li directament:
**"Abans de res, llegeix l'arxiu `DOCUMENTACIO_PROJECTE.md` per entendre l'arquitectura V2 modular de la meva app."**
Això assegurarà que sàpiga que NO ha d'editar l'antic `app.py` tret que es demani explícitament, sinó que ha d'anar directament a `app_v2.py` i a la carpeta `modules/`.
