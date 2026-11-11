# Documentació del Projecte: Dashboard Despeses i Gestió de la Llar - XiquiHouse
> **Versió Generalitzada i Modular**  
> *Data d'actualització: 5 de novembre de 2026*  
> *Fitxer mestre de referència per a desenvolupament, noves sessions d'IA i desplegament del sistema.*

---

## Taula de Continguts
1. [Instruccions per a IA i Directrius Crítiques (Prioritat 1)](#1-instruccions-per-a-ia-i-directrius-crítiques-prioritat-1)
2. [Arquitectura del Sistema, Sincronització i Rendiment (Prioritat 1)](#2-arquitectura-del-sistema-sincronització-i-rendiment-prioritat-1)
3. [Estructura del Projecte i Mapa de Fitxers](#3-estructura-del-projecte-i-mapa-de-fitxers)
4. [Mòduls de Prioritat 2: Gestió Econòmica i Compres](#4-mòduls-de-prioritat-2-gestió-econòmica-i-compres)
   - [4.1 Compres Super i Stock (`modules/compres.py`)](#41-compres-super-i-stock-modulescomprespy)
   - [4.2 Mòdul Econòmic i Dashboard (`modules/economic.py`, `modules/dashboard.py`)](#42-mòdul-econòmic-i-dashboard-moduleseconomicpy-modulesdashboardpy)
5. [Mòduls de Prioritat 3: Subministraments i Manteniment de la Llar](#5-mòduls-de-prioritat-3-subministraments-i-manteniment-de-la-llar)
   - [5.1 Llum i Aigua (`modules/llum_aigua.py`)](#51-llum-i-aigua-modulesllum_aiguapy)
   - [5.2 Manteniment de la Llar (`modules/manteniment.py`)](#52-manteniment-de-la-llar-modulesmantenimentpy)
   - [5.3 Cotxe i Mobilitat (`modules/cotxe.py`)](#53-cotxe-i-mobilitat-modulescotxepy)
6. [Mòduls de Prioritat 4: Família, Nutrició i Benestar](#6-mòduls-de-prioritat-4-família-nutrició-i-benestar)
   - [6.1 Menús i Cuina (`modules/menjar.py`)](#61-menús-i-cuina-modulesmenjarpy)
   - [6.2 Agenda i Calendari Familiar (`modules/calendari.py`)](#62-agenda-i-calendari-familiar-modulescalendaripy)
   - [6.3 Control de Medicació (`modules/medicacio.py`)](#63-control-de-medicació-modulesmedicaciopy)
   - [6.4 Seguretat i Domòtica (`modules/seguretat.py`, `modules/domotica.py`)](#64-seguretat-i-domòtica-modulesseguretatpy-modulesdomoticapy)
7. [Mòduls de Prioritat 5: Administració, Nucli i Serveis Transversals](#7-mòduls-de-prioritat-5-administració-nucli-i-serveis-transversals)
   - [7.1 Configuració Global (`modules/admin.py`, `core/config_manager.py`)](#71-configuració-global-modulesadminpy-coreconfig_managerpy)
   - [7.2 Laboratori IA - Harness (`core/harness.py`)](#72-laboratori-ia---harness-coreharnesspy)
   - [7.3 Gestió de Bases de Dades i Sincronització Offline (`modules/bases_dades.py`, `modules/sincronitzacio.py`)](#73-gestió-de-bases-de-dades-i-sincronització-offline-modulesbases_dadespy-modulessincronitzaciopy)
   - [7.4 Sistema Global d'Alertes (`core/alerts.py`)](#74-sistema-global-dalertes-corealertspy)
   - [7.5 Impressora de Tiquets (`modules/impressora.py`)](#75-impressora-de-tiquets-modulesimpressorapy)
8. [Annex: Historial de Canvis Recents Consolidat](#8-annex-historial-de-canvis-recents-consolidat)

---

## 1. Instruccions per a IA i Directrius Crítiques (Prioritat 1)

> [!IMPORTANT]
> **Instrucció d'Arrencada per a Noves Sessions d'IA**  
> Si inicies una conversa nova amb un assistent d'IA, cal indicar-li:  
> **"Llegeix `DOCUMENTACIO_PROJECTE.md` per entendre l'arquitectura modular, les prioritats i el funcionament de l'aplicació abans de tocar cap codi."**

### 1.1 Directriu Obligatòria de Desplegament a GitHub (`git push`)
- L'aplicació s'executa tant en entorn local com des del núvol (**Streamlit Community Cloud** sincronitzat amb el repositori GitHub del projecte).
- **REGLE INVIOLABLE**: Un cop realitzat i provat qualsevol canvi en local, l'assistent d'IA **TÉ L'OBLIGACIÓ STRICTA DE DESAR I PUJAR SEMPRE ELS CANVIS A GITHUB** (`git add`, `git commit -m "..."`, `git push origin main`).
- Mai es dóna una tasca per finalitzada sense haver sincronitzat els canvis al repositori remot, garantint que la versió web estigui sempre actualitzada.

### 1.2 Llengua de Comunicació
- La llengua vehicular del projecte i de totes les comunicacions amb l'usuari és el **Català** per defecte, però es pot triar altres idiomes.

---

## 2. Arquitectura del Sistema, Sincronització i Rendiment (Prioritat 1)

### 2.1 Model Dual Híbrid (Cloud-First + Fallback Offline)
1. **Entorn Núvol (Streamlit Cloud)**: Accés multi-dispositiu permanent per a mòbils, tauletes i ordinadors.
2. **Arrencador d'Escriptori (`StartDashboard.py`)**:
   - En sistemes d'escriptori, obre automàticament la versió del núvol al navegador predeterminat (Google Chrome) en arrencar l'equip si hi ha connexió a Internet.
   - Paral·lelament, un procés silenciós en segon pla (`scripts/update_csvs_background.py`) sincronitza les dades remotes de PostgreSQL directament amb els fitxers CSV locals, assegurant una font de veritat íntegra a disc sense límits de paginació.
3. **Emergency Offline Mode**: Si no hi ha internet (o si es desconnecta manualment la xarxa abans d'iniciar l'aplicació), s'arrenca l'entorn local Streamlit de forma instantània llegint exclusivament dels CSV locals mitjançant *Lazy Loading*. Totes les mutacions locals (altes, edicions, esborrats) es retenen en una cua local (`sync_queue.json`) i es consoliden a la base de dades remota en recuperar la connexió.

### 2.2 Estratègia d'Optimització de Rendiment (Finestra Activa de 30 Dies)
Per mantenir la màxima fluïdesa fins i tot amb taules històriques massives de milers de registres (`despeses` i `compresSuper`):
- **Finestra Activa de 30 dies**: Es consulta a Supabase mitjançant una sola petició HTTP ultra-ràpida (`~0,15 s`) per obtenir els registres del mes en curs i els tiquets pendents de desglossar.
- **Arxiu Històric (Mesos vençuts)**: Carregat en memòria cau persistent de 24 hores (`@st.cache_data(ttl=86400)`) des del CSV local (`~0,04 s`).
- **Fusió Transparent**: L'aplicació unifica els registres recents amb l'històric sense duplicats, garantint càlculs i saldos exactes.
- **Mutacions Locals amb Zero Latència**: Les operacions `insert_db_row`, `update_db_row` i `delete_db_row` actualitzen directament el DataFrame a `st.session_state` i buiden quirúrgicament la finestra recent, **sense invalidar mai la memòria cau completa** (evitant bloquejos de 15 a 20 segons).
- **Càrrega Selectiva (*Lazy Loading*) per Mòdul**: Cada mòdul només demana les taules que utilitza estrictament.
- **Interfícies Adaptades amb Navegació Dinàmica**: L'ús de selectors de navegació horitzontal o menús redueix la càrrega del DOM del navegador, renderitzant únicament el contingut de la vista activa.

### 2.3 Centralització de Configuracions a Supabase (`app_config`)
Per assegurar la persistència completa de les dades al núvol i evitar pèrdues en reiniciar les màquines virtuals de Streamlit Cloud, totes les configuracions del sistema s'emmagatzemen a Supabase:
| ID | Fitxer Equivalent Local | Descripció |
|:---|:---|:---|
| **02/11/2026** | **Configuració / Activació d'Eines i IoT** | **Activació / Desactivació d'Eines (`st.toggle`), Càmeres de Seguretat i Detectors de Presència**: Incorporats commutadors interactius d'estat (`🟢 Actiu` vs `⚪ Inactiu`) directament a la línia de cada dispositiu a `modules/admin.py` i a `modules/domotica.py`. Afegits botons d'activació ràpida 1-clic per a `📹 + Càmera` (seguretat/vigilància) i `🚶 + Presència` (sensors PIR / radar mmWave), a més d'un selector desplegable universal per activar qualsevol tipus d'eina o equipament addicional a qualsevol estança de la casa amb persistència immediata. |
| **02/11/2026** | **Configuració / Estances i Acumuladors Tuya** | **Suport Natiu per a Acumuladors de Calor Elèctrics i Contactors Wi-Fi Tuya / Smart Life**: Afegits botons ràpids 1-clic (`🧱 + Acumulador (Tuya)` i `⚡ + Contactor Wi-Fi`) a l'administrador d'estances (`modules/admin.py`), categories dedicades (`acumulador`, `contactor`) i protocol `Tuya / Smart Life`. S'incorpora avís contextual vinculat a l'optimitzador d'hores barates PVPC de `modules/llum_aigua.py` per coordinar la recàrrega de potència dels equips a cost mínim. |
| **02/11/2026** | **Configuració / Estances i Domòtica IoT** | **Manteniment d'Elements IoT per Estança (`iot_elements`) i Integració a Domòtica**: Incorporat el manteniment integral de dispositius intel·ligents dins de cada estança de la casa (`modules/admin.py`). Permet donar d'alta i modificar sensors de temperatura/humitat, il·luminació, endolls, detectors d'inundació/aigua/pou, sensors de contacte de portes i relés de bombes d'aigua amb assignació de protocols (Wi-Fi, Zigbee, Shelly, Tuya, Sonoff, Matter, etc.) i referències d'entitat/IP de Home Assistant. Actualitzat el mòdul de domòtica (`modules/domotica.py`) per reflectir l'estat dels equips instal·lats per cada espai de la llar. |
| **1** | `categories_conceptes.json` | Categories i conceptes de despeses i ingressos |
| **2** | `core/config.json` | Perfil familiar, al·lèrgies, vetos, eines de cuina i admin |
| **3** | `data/events.json` | Esdeveniments del calendari familiar i estats fet/no fet |
| **4** | `data/feeds_cache.json` | Memòria cau dels feeds de calendaris personals |
| **5** | `data/medication_plans.json` | Plans i horaris de medicació familiar |
| **6** | `data/ofertes.json` | Registre d'ofertes setmanals i fulletons |
| **7** | `data/manteniment_docs.json` | Registre documental de Manuals i Garanties de la llar |
| **8** | `data/registre_manteniment.json` / `csv/manteniment.csv` | Registre de tasques, reparacions i periodicitats de la llar |
| **9** | `data/consum_llum.json` / `csv/consum_llum.csv` | Factures elèctriques, potències i consums per tram (històric) |
| **10** | `data/consum_aigua.json` / `csv/consum_aigua.csv` | Factures d'aigua, lectures de comptador i consums en m³ |
| **11** | `data/projectes_manteniment.json` | Projectes d'obra, reformes, plànols, materials i fases de la llar |

---

## 3. Estructura del Projecte i Mapa de Fitxers

```
Dashboard/
├── app.py                         # Router principal canònic, barra superior i Landing interactiva
├── app_v2.py                      # Bridge de compatibilitat transparent per a Streamlit Cloud
├── StartDashboard.py              # Llançador d'escriptori de Windows (Chrome + background sync)
├── auto_scan_ui.py                # Interfície ràpida d'escaneig de tiquets en 1 clic
├── scan_winrt.ps1                 # Pont natiu WinRT (Windows.Devices.Scanners) per a escàners USB
├── scanner.py                     # Controlador d'escaneig (WinRT prioritari + WIA fallback)
├── core/
│   ├── aigua_manager.py           # Gestor de factures i lectures d'aigua (Supabase ID 10)
│   ├── alerts.py                  # Motor centralitzat d'alertes i campaneta de notificacions
│   ├── auth.py                    # Autenticació, sessions i tokens
│   ├── calendar_manager.py        # Gestor de calendari, sincronització iCal i desduplicació
│   ├── config_manager.py          # Gestor de configuració JSON i perfil familiar
│   ├── cut_optimizer.py           # Algorisme Guillotine 2D i generador SVG de talls per a mobles i taulers
│   ├── db.py                      # Connexions CRUD a Supabase, gestió híbrida i offline
│   ├── harness.py                 # Motor de tests IA asíncron en segon pla i informes .txt
│   ├── llm.py / llm_ui.py         # Connectors d'intel·ligència artificial (Gemini, DeepSeek, etc.)
│   ├── llum_manager.py            # Preus PVPC directe, optimitzador d'acumuladors i estudi solar PVGIS
│   ├── manteniment_manager.py     # Gestor de manuals, garanties i tasques de manteniment periòdiques
│   ├── normalitzador.py           # Motor d'harmonització de dades (dates, categories sense accents, conceptes)
│   ├── projectes_manager.py       # Gestor de dades i persistència híbrida de projectes d'obra (id=11)
│   ├── ai_projectes.py            # Assistent IA d'obra (materials, tutorials pas a pas, preus de mercat)
│   └── ocr_rules.md               # Regles d'extracció de tiquets per supermercat
├── modules/
│   ├── admin.py                   # ⚙️ Configuració global i laboratori IA (Harness)
│   ├── bases_dades.py             # 🗄️ Gestor de taules Supabase en temps real
│   ├── calendari.py               # 📅 Agenda familiar (Graella, Dia, Fet/No fet, mòbil 1 línia)
│   ├── canvas_planol.py           # 📐 Editor gràfic HTML5 Canvas tàctil per a mòbil/PC i galeria d'obra
│   ├── compres.py                 # 🛒 Compres Super (OCR, tiquets, desglossament, rebost, estalvi)
│   ├── cotxe.py                   # 🚗 Km, repostatge, consum i manteniment col·lapsable
│   ├── dashboard.py               # 📊 Dashboard general i KPIs financers
│   ├── domotica.py                # 📶 Integració amb Home Assistant
│   ├── economic.py                # 📈 Previsió despeses/ingressos, nou any, pagues extres, inversions
│   ├── impressora.py              # 🖨️ Controlador d'impressora de tiquets de compra
│   ├── llum_aigua.py              # 💡 Preus PVPC, acumuladors, factures PDF i simulador solar
│   ├── manteniment.py             # 🛠️ Tasques periòdiques, subtasques, manuals, garanties i projectes
│   ├── medicacio.py               # 💊 Control de medicació, pautes i tutelats
│   ├── menjar.py                  # 🍽️ Receptari, recomanador IA, calories i mise en place
│   ├── moble_disseny_ui.py        # 🪚 Disseny paramètric 3D de mobles i CutList Optimizer
│   ├── normalitzador_ui.py        # 🧹 Interfície visual d'auditoria i normalització de dades
│   ├── projectes_ui.py            # 🏗️ Interfície completa de la pestanya de projectes i reformes
│   ├── seguretat.py               # 📹 Estat de càmeres, accessos i alarmes
│   └── sincronitzacio.py          # 🔄 Consolidació de dades offline retingudes
├── PDF/                           # Magatzem centralitzat de documents en PDF
│   ├── Factures_Aigua/	           # Dipòsit de factures d'aigua en PDF
│   ├── Factures_Llum/             # Dipòsit de factures elèctriques en PDF
│   ├── Factures_Gas/              # Dipòsit de factures de gas en PDF
│   ├── Garanties/                 # Factures i pòlisses de garantia de la llar
│   └── Manuals/                   # Manuals d'instruccions d'aparells de la llar
├── imatges/
│   ├── Disseny/                   # Logotips de la llar, fons i elements de disseny
│   ├── Eines/                     # Miniatures dels aparells i eines de cuina
│   ├── Productes/                 # Imatges d'articles de compra i rebost
│   └── Receptes/                  # Imatges gastronòmiques oficials 4:3
└── DOCUMENTACIO_PROJECTE.md       # Document mestre de referència integral del projecte
```

---

## 4. Mòduls de Prioritat 2: Gestió Econòmica i Compres

### 4.1 Compres Super i Stock (`modules/compres.py`)
Mòdul central i neuràlgic per a la ingesta intel·ligent de tiquets de compra, control pressupostari d'alimentació, gestió d'estoc del rebost domèstic, generació dinàmica de llistes de compra, comparativa històrica de preus i seguiment d'ofertes.

#### A. Arquitectura del Mòdul i Fonts de Dades
El mòdul articula el flux complet dels queviures de la llar connectant les següents taules i fonts de configuració:
1. **Taules a Supabase (PostgreSQL)**:
   - `compresSuper`: Registre atòmic línia per línia de cada article comprat (`IdCompra`, `data`, `mes`, `any`, `super`, `familia`, `article`, `pes`, `quantitat`, `preuUnit`, `prom`, `totLinea`, `IdDespesa`, `descompte`, `rebost`).
   - `despeses`: Moviments comptables i bancaris. Els moviments de supermercat pendents de desglossar tenen `ticketPendent = True`. En finalitzar la compra, s'enllacen automàticament via `IdDespesa` i el flag s'actualitza a `False`.
   - `tb_productes`: Catàleg mestre d'articles normalitzats amb la seva família canònica (`lactics`, `fruita`, `verdura`, `carn`, etc.) i equivalències de text segons cada supermercat.
   - `tb_supers`: Llista de comerços homologats (`Dia`, `bonArea`, `Mercadona`, `Consum`, `Esclat`, `Novavenda`, `Lidl`, `Aldi`, etc.).
2. **Fitxers de Configuració Centralitzats**:
   - `categories_conceptes.json` (ID 1): Defineix les famílies permeses i el catàleg de supermercats actius.
   - `data/ofertes.json` (ID 6): Registre d'ofertes de fulletons i descomptes setmanals.
   - `core/ocr_rules.md`: Regles manuals d'extracció que s'injecten al prompt d'IA per resoldre particularitats d'estil de tiquets segons la cadena comercial.
3. **Perifèrics Integrats**:
   - **Escàner USB (WinRT / WIA)**: Captura física de tiquets a 300 DPI mitjançant `scanner.py` i `auto_scan_ui.py`.
   - **Impressora Tèrmica ESC/POS**: Impressió física directa de la llista de la compra a través de `modules/impressora.py`.

---

#### B. Cicle de Vida i Flux Pas a Pas d'un Tiquet

```mermaid
flowchart TD
    A["🖨️ Escaneig 1-Clic o Càrrega Fitxer"] --> B["⚡ Extracció OCR / Visió Multimodal"]
    B --> C["🤖 Estructuració JSON + Fallback Nom Fitxer"]
    C --> D["🔍 Reconciliació Automàtica amb tb_productes"]
    D --> E{"Hi ha articles 'Pendent'?"}
    E -- Sí --> F["⚠️ Bloqueig: L'usuari ha d'assignar Família/Article"]
    E -- No --> G["📅 Validació de Data (Control > 7 dies)"]
    G --> H["💰 Vinculació Financera (Banc / Forma Pagament)"]
    H --> I["💾 Desat Final: INSERT compresSuper + UPDATE despeses"]
    I --> J["🥫 Actualització Automàtica d'Estoc al Rebost"]
```

- **Pas 1: Ingesta del document**:
  - *Opció 1-Clic Escàner*: En prémer `🖨️ Obrir Escàner`, s'obre la finestra d'escriptori [`auto_scan_ui.py`](file:///e:/Dashboard/auto_scan_ui.py) que adquireix la imatge del vidre a 300 DPI i la desa a `tickets/ticket_<super>_<data>.jpg`. En tornar a Streamlit, el botó verd destacat `📥 Carregar últim tiquet escanejat` l'ingereix instantàniament al motor d'OCR sense obrir cap diàleg de carpetes de Windows mitjançant [`LocalFileWrapper`](file:///e:/Dashboard/modules/compres.py).
  - *Opció Càrrega Manual*: Admet imatges (`png`, `jpg`, `jpeg`, `webp`, `bmp`), documents digitals de supermercat (`pdf` amb extracció de text per `pypdf`) i tiquets de text (`txt`).
- **Pas 2: Extracció intel·ligent per IA**:
  - *Mode Híbrid*: Tesseract OCR llegeix el text i el model de llenguatge (Gemini 2.5 Flash) el parseja a JSON net.
  - *Mode Visió Pura*: Envia la imatge directament al model multimodal.
  - *Fallback intel·ligent*: Si la capçalera està borrosa, el sistema extreu el súper i la data directament del nom del fitxer (`ticket_<super>_<data>.jpg`).
- **Pas 3: Reconciliació amb el catàleg i descomptes**:
  - Cada línia s'emparella amb `tb_productes` mitjançant cerca difusa (`difflib`).
  - **Fórmula d'Enginyeria Inversa de Descomptes**: El preu final pagat ($PF$) roman invariable i el sistema dedueix la base teòrica ($B$):
    $$PF = B \times (1 - d) \implies B = \frac{PF}{1 - d}$$
- **Pas 4: Validació de data i bloqueig de seguretat**:
  - Data mai superior a avui (`> date.today()`).
  - Si té més de 7 dies, s'obre el modal interactiu `@st.dialog` de confirmació de data.
  - Els articles desconeguts (`Pendent`) bloquegen el desat per evitar embrutar el catàleg.
- **Pas 5: Desat i consolidació econòmica**:
  - Es genera la despesa a `despeses` o es desglossa el tiquet bancari existent (`ticketPendent = False`).
  - S'insereixen els articles a `compresSuper` de forma atòmica.
- **Pas 6: Sincronització amb el Rebost**:
  - Els articles marcats incrementen automàticament l'estoc al rebost domèstic.

---

#### C. Detall Exhaustiu de les 6 Pestanyes de la Interfície Gràfica

El mòdul s'estructura en 6 vistes especialitzades mitjançant `st.tabs` amb suport natiu per a commutació dinàmica i paràmetres URL (`?tab=...`):

---

##### 4.1.1 Pestanya 1: `🛒 Compres Super` (Entrada de Tiquets i Desglossament)
La interfície d'adquisició, estructuració per IA, auditoria i consolidació comptable.

1. **Capçalera Superior Esquerra (Reconciliació de Tiquets Bancaris Pendents)**:
   - **Informació de Tiquet Pendent**: Mostra la referència del moviment bancari carregat pel banc que encara no s'ha desglossat *(Exemple: `🛒 Desglossant: Nº 8207 — Plaça (24/10/2026) — 43.65 €`)*.
   - **Botó `🛒 Desglossar Nº X`**: Si hi ha tiquets pendents a `despeses`, cada línia compta amb aquest botó verd destacat que precarrega automàticament el súper, la data i el banc a la sessió actual.
   - **Botó `❌ Desvincular`**: Allibera el tiquet pendent actiu per permetre a l'usuari entrar una compra independent des de zero.
   - **Botó Túnel `⚡ Mòdul Econòmic`**: Redirigeix a la pestanya econòmica per revisar els detalls del moviment original.
   - **Control de Coincidència de Total (Mismatch)**: Compara el càrrec registrat al banc amb l'import **net** del tiquet (`total_productes - descompte_global`). Si difereixen en més d'1 cèntim, apareix una alerta taronja detallant els articles i el descompte, amb un botó interactiu **`Forçar correcció del banc a X.XX €`** per ajustar el moviment financer sense errors manuals. Si el net coincideix amb el càrrec, el tiquet es desa correctament a `compresSuper`, s'actualitza l'apunt a `despeses` i es desmarca `ticketPendent = False`.

2. **Capçalera Superior Dreta (Escaneig i Gestió d'Imatge)**:
   - **Botó `🖨️ Obrir Escàner`**: Executa en segon pla l'aplicació nativa WinRT [`auto_scan_ui.py`](file:///e:/Dashboard/auto_scan_ui.py), obrint la interfície ràpida d'escaneig de sobretaula directament a la pantalla de l'usuari.
   - **Botó `📥 Carregar últim (tiquet)`**: Detecta automàticament el darrer fitxer generat a `tickets/` (ex. `ticket_BonPreu_281026.jpg`). Si s'ha escanejat fa menys d'una hora, es ressalta en color verd (`type="primary"`) i amb un sol clic l'ingereix a l'OCR encapsulant-lo amb [`LocalFileWrapper`](file:///e:/Dashboard/modules/compres.py) sense obrir cap diàleg de fitxers de Windows.
   - **Expander `📂 Historial de tiquets escanejats`**: Desplegable per seleccionar qualsevol dels 8 darrers tiquets escanejats amb data i hora de captura.
   - **Selector Manual `📷 Llegir ticket` (`st.file_uploader`)**: Admet fitxers en formats d'imatge (`jpg`, `png`, `webp`, `bmp`), documents `pdf` de supermercat (processats mitjançant `pypdf`) i fitxers `txt`.
   - **Badge d'Arxiu Actiu**: Mostra el nom del fitxer i la mida en KB.
   - **Botó `🔄` (Reintentar)**: Permet canviar de model d'IA i forçar una reavaluació de la mateixa imatge si la primera lectura no ha estat òptima.
   - **Botó `❌` (Descartar)**: Neteja la imatge de la memòria cau i reinicia el selector per carregar-ne un de nou.

3. **Configuració Financera i Models d'IA**:
   - **Casella `Enviar a despeses`**: Marca si el tiquet ha de crear automàticament un apunt comptable a la taula `despeses` (si no prové d'un tiquet bancari pendent).
   - **Desplegables `Banc` i `Forma de Pagament`**: Selecció del compte financer (BBVA, LaCaixa, Efectiu, etc.) i el mitjà (Targeta, Transferència, Efectiu). Bloqueja el desat si no s'ha triat banc.
   - **Selector Ràdio `Mètode d'Escaneig`**: Permet alternar entre **⚡ Híbrid (Tesseract+IA, recomanat)** (extracció de text local per OCR i estructuració per IA) o **👁️ Visió Pura (Directa)** (enviament directe de la imatge al model multimodal).
   - **Selector de Models d'Intel·ligència Artificial (`render_ai_selector`)**: Desplegable dinàmic per triar el proveïdor (Gemini, Groq, DeepSeek) i el model concret (Gemini 2.5 Flash, Gemini 3.8 Flash, etc.), adaptant-se automàticament si el model suporta visió directa o requereix Tesseract previ.

4. **Metadades del Tiquet (Data i Supermercat)**:
   - **Selector `Data` (`st.date_input`)**: Data del tiquet amb bloqueig absolut de dates futures. Si té més de 7 dies d'antiguitat, s'activa un avís informatiu.
   - **Botó `Avui`**: Assigna instantàniament la data actual al selector amb un sol clic.
   - **Desplegable `Supermercat`**: Llista de cadenes comercials homologades.
   - **Botó `Nou` / Panell d'Alta de Súper**: Obre un camp de text que permet enregistrar un nou supermercat tant a Supabase (`tb_supers`) com al fitxer de configuració local (`categories_conceptes.json`) sense sortir de la pàgina.

5. **Panell d'Entrada i Correcció Manual d'Articles**:
   - **Camps en Cascada `FAMILIA` i `ARTICLE`**: Desplegables interconnectats per seleccionar la família (ex: `lactics`, `fruita`, `carn`) i l'article normalitzat de la base de dades.
   - **Botó `✚` (Afegir Nou Article al Catàleg)**: Obre el diàleg modal `@st.dialog("➕ Afegir nou article")` per enregistrar un producte desconegut a `tb_productes` al vol, assignant-li nom canònic, família i equivalència de supermercat.
   - **Camp `PES`**: Camp per indicar el pes en grams o quilos (si és un article a granel).
   - **Camp Numèric `QUANTITAT`**: Unitats de l'article (normalitzat a 1 en productes a pes).
   - **Camp Numèric `PREU UNIT.`**: Preu per unitat en euros.
   - **Camps de Descompte (`%` i `PROMOCIÓ`)**: Permeten aplicar la fórmula d'enginyeria inversa de promocions. En modificar qualsevol dels dos valors, el sistema recalcula la base teòrica mantenint fix el preu real pagat.
   - **Camp `TOTAL LÍNIA`**: Mostra l'import líquid total de la línia calculat automàticament (deshabilitat per protegir la integritat matemàtica).
   - **Casella `Reb.`**: Casella per indicar si aquest producte ha d'incrementar les existències del rebost domèstic en finalitzar el tiquet.
   - **Botó `Intro línia`**: Afegeix l'article a la taula provisional de compra.

6. **Taula Interactiva d'Articles i Accions Finals**:
   - **Llistat de Línies**: Graella amb tots els productes extrets per la IA o afegits manualment.
   - **Botó `✏️` (Modificar línia)**: Carrega les dades de la línia seleccionada als camps superiors per editar-ne la família, article, preu o promoció.
   - **Botó `🗑️` (Eliminar línia)**: Elimina l'article del tiquet provisional.
   - **Camp `Descompte global del Tiquet (€)`**: Permet introduir descomptes globals de caixa (ex: vals de 5 € de fidelitat) que es reparteixen de forma ponderada.
   - **Botó `💾 Fi Tiquet` (`type="primary"`)**: Porta a terme la validació integral:
     - Bloqueja l'acció si hi ha articles pendents de categoritzar (`familia == 'Pendent'`).
     - Si la data supera els 7 dies, activa el modal de confirmació expressa `@st.dialog`.
     - Executa la inserció massiva a `compresSuper`, actualitza `despeses` (`ticketPendent = False`), refresca el rebost i neteja els formularis.
   - **Botó `Netejar Tiquet`**: Restableix la sessió buidant la taula temporal sense modificar la base de dades.

---

##### 4.1.2 Pestanya 2: `📝 Llista de la Compra` (Planificació i Checklist)
Eina àgil per preparar la compra des de casa i marcar els productes al mòbil o imprimir-los en paper físic.

1. **Generador Automàtic d'Estocs Mínims**:
   - Analitza el rebost en temps real: qualsevol article amb `stock < stock_minim` s'incorpora automàticament a la llista de compra proposada, calculant la quantitat exacta que cal reposar.
   - Agrupació intel·ligent per establiment comercial habitual (BonPreu, Dia, Mercadona, etc.) o sota la secció `Sense súper assignat`.

2. **Panell d'Alta de Peticions Puntuals**:
   - **Botó `➕ Afegir petició puntual`**: Desplega un formulari per afegir articles que no formen part de l'inventari regular (ex: bateries, eines, articles especials).
   - **Desplegable `Supermercat`**: Assigna a quina botiga s'ha d'anar a comprar l'article.
   - **Camp `Nom lliure (nou)`** o **`O tria del catàleg`**: Permet escriure qualsevol text lliure o cercar un producte ja existent a la base de dades.
   - **Camp `Quantitat`**: Nombre d'unitats requerides.

3. **Interfície de Checklist per a Supermercat**:
   - **Acordions per Supermercat (`st.expander`)**: Cada botiga es presenta en un acordió independent que mostra el nombre total d'articles pendents i la suma estimada de diners.
   - **Caselles de Verificació Interactives (`st.checkbox`)**: Dissenyades per utilitzar-se des del navegador del telèfon mòbil mentre s'és al passadís del súper. En marcar un producte, queda ratllat visualment.
   - **Botó `🧹 Netejar peticions lliures`**: Elimina de cop les peticions puntuals que ja s'han adquirit.
   - **Selector de Canvi de Destí**: Permet moure un article pendent d'un supermercat a un altre amb un sol clic si es decideix comprar-lo en una altra botiga.

4. **Integració amb Impressora Tèrmica ESC/POS**:
   - Botó directe per transmetre la llista completa o d'un sol supermercat a la impressora física de tiquets mitjançant [`modules/impressora.py`](file:///e:/Dashboard/modules/impressora.py), amb tall automàtic de paper per portar la llista impresa a la butxaca.

---

##### 4.1.3 Pestanya 3: `🥫 Rebost` (Gestió d'Inventari Domèstic)
Control físic dels queviures emmagatzemats a la cuina, armaris i congelador.

1. **Inventari General de Queviures**:
   - Graella completa d'articles agrupats per categories (`Conserves`, `Làctics`, `Begudes`, `Neteja`, etc.).
   - Mostra en columnes: Article, Família, Estoc Actual, Estoc Mínim de Seguretat i Data de Darrera Entrada.

2. **Semàfor Visual d'Estoc**:
   - 🟢 **Verd (Suficient)**: Quantitat per sobre de l'estoc mínim.
   - 🟡 **Groc (Sota mínims)**: Quantitat igual o per sota del llindar de seguretat (alerta groga d'atenció).
   - 🔴 **Vermell (Esgotat)**: Estoc a zero (provoca l'alta automàtica a la *Llista de la Compra*).

3. **Controls d'Ajust Ràpid en 1 Clic**:
   - **Botó `➕ Afegir 1`**: Incrementa l'estoc manualment quan es porta un article a casa sense tiquet.
   - **Botó `➖ Gastar 1`**: Descompta una unitat quan s'obre o consumeix un paquet a la cuina.
   - Sincronització immediata amb Supabase sense requerir recàrregues completes de pàgina.

4. **Control de Caducitats i Consum Preferent**:
   - Registre de dates de venciment per a productes peribles.
   - Avisos visuals i notificacions a la campaneta d'alertes superior (`🔔`) quan un producte està a punt de caducar.

5. **Vinculació de Codis de Barres (Lectura Làser)**:
   - Desplegable de productes i botó **`🔗 Enllaçar Codi i Producte`**: Permet assignar el codi EAN d'un codi de barres llegit per pistola làser a un article del catàleg per a futures lectures instantànies.

---

##### 4.1.4 Pestanya 4: `📊 Estadístiques` (Mètriques Financeres i Gràfics Interactius)
Panell analític per auditar el cost dels aliments, l'estalvi aconseguit i els patrons de consum familiar.

1. **Filtres de Segmentació Temporal**:
   - **Selector `Any`**: Filtra l'històric d'anys disponibles (ex: 2024, 2025, 2026).
   - **Selector `Mes`**: Permet avaluar tot l'any conjuntament (`Tots`) o centrar-se en un mes específic.

2. **Targetes KPI Resum i Conciliació de Categories**:
   - **`Total Compra Pagada`**: Despesa total neta en euros abonada en conjunt per tots els tiquets de supermercat del període.
   - **`Alimentació (Menjar)`**: Import net destinat exclusivament a alimentació, conciliat al cèntim amb la categoria `menjar` del Dashboard econòmic (descomptant vals de caixa globals).
   - **`Neteja i Llar`**: Despesa en articles de drogueria, higiene i neteja adquirits als supermercats (conciliat amb la categoria `neteja` del Dashboard).
   - **`Total Estalvi Generat`**: Suma de tots els descomptes i promocions assolits, amb percentatge d'estalvi aconseguit sobre el total teòric brut.
   - **`Nº Línies / Articles`**: Volum total d'articles físics adquirits.

3. **Gràfics Interactius de Plotly i Panells de Conciliació**:
   - **Pestanyes de Donut (*Compra vs Estalvi* i *Menjar vs Neteja*)**: Permet alternar entre la comparativa de despesa vs estalvi i la divisió exacta entre Alimentació (`menjar`) i Neteja/Drogueria (`neteja`).
   - **Capsetes Informatives de Desglossament**:
     - *Desglossament de l'Estalvi*: Detall de pagat net, promocions directes d'articles i descomptes globals de tiquet.
     - *Conciliació Comptable (Dashboard)*: Taula explicativa que concilia el total del supermercat amb les categories de despesa del Dashboard econòmic.
   - **Gràfic de Pastís per Famílies de Productes**: Distribució percentual de la despesa en funció de les famílies (Carn, Làctics, Verdura, Fruita, Neteja, etc.).
   - **Gràfic de Barres per Supermercat**: Rànquing visual del volum de despesa acumulat a cada comerç per conèixer a quina cadena es destina el pressupost familiar.

---

##### 4.1.5 Pestanya 5: `🔍 Comparador de Preus` (Intel·ligència de Compra)
Cercador creuat per identificar diferències de preu entre cadenes i contrarestar la inflació.

1. **Filtres de Cerca de Mercat**:
   - **Selector Ràdio `👀 Filtrar productes per`**: Permet triar entre visualitzar només els articles que falten a la llista de compra actual (`🛒 A la llista de compra`) o explorar tot l'històric de la base de dades (`📦 Tot el catàleg`).
   - **Camp `🔍 Buscar producte...`**: Cerca en temps real per nom o paraula clau.

2. **Graella Comparativa de Comerços**:
   - Taula comparativa que creua els productes amb els diferents supermercats, mostrant el darrer preu registrat i el preu unitari normalitzat (€/kg o €/u).
   - Identificació visual del comerç que ofereix el millor preu per a cada producte.

3. **Històric d'Evolució Temporal per Article**:
   - **Desplegable `🔍 Selecciona un producte`**: Mostra la cronologia completa de compres d'aquell article al llarg dels mesos.
   - Taula d'evolució amb data, supermercat, preu unitari pagat i variació percentual per detectar pujades o baixades de preu entre cadenes.

4. **Panell d'Anotació d'Ofertes de Mercat**:
   - Formulari per registrar ofertes externes detectades: selectors de producte, súper, tipus de promoció (`Preu rebaixat`, `3x2`, `2a unitat %`) i preu final ofertat.

---

##### 4.1.6 Pestanya 6: `📰 Fulletons` (Catàlegs i Promocions Setmanals)
Espai dedicat a consultar i arxivar catàlegs promocionals i descomptes especials.

1. **Visualitzador de Fulletons Comercials**:
   - Galeria d'imatges i documents PDF dels fulletons en curs de les cadenes habituals (Lidl, Dia, BonPreu, etc.).
   - Consulta ràpida abans de planificar els menús de la setmana o fer la llista de la compra.

2. **Cercador de Promocions Actives**:
   - Selector de producte que creua els descomptes vigents amb el catàleg per saber si algun article habitual té promoció activa.

3. **Persistència i Sincronització Núvol**:
   - Integrat directament amb la taula `data/ofertes.json` (Config ID 6 de Supabase), garantint que les ofertes desades es mantinguin disponibles a tots els dispositius mòbils i ordinadors.

---

#### D. Navegació Dinàmica i Enllaços amb Altres Mòduls
- **Navegació per Paràmetres URL (`st.query_params`)**:
  - Permet crear enllaços directes des de notificacions o altres mòduls: `?tab=rebost`, `?tab=llista_compra`, `?tab=compres_super`.
  - Commutació de pestanyes automàtica mitjançant JavaScript injectat al document pare sense recàrregues completes.
- **Interconnexió amb el Sistema Global**:
  - **[`modules/economic.py`](file:///e:/Dashboard/modules/economic.py)**: Actualització directa dels saldos bancaris i del balanç mensual d'ingressos/despeses.
  - **[`modules/menjar.py`](file:///e:/Dashboard/modules/menjar.py)**: Els ingredients del rebost alimenten les receptes i el recomanador IA de menús setmanals.
  - **[`modules/impressora.py`](file:///e:/Dashboard/modules/impressora.py)**: Servei d'impressió en paper tèrmic per a la llista de la compra.
  - **Menú Superior `Editar`**: Accés directe a `✏️ Regles OCR` (`core/ocr_rules.md`) i `📂 Arxius JSON` (`categories_conceptes.json`) sense canviar de pàgina.

---

#### E. Normes de Codificació de Tiquets per Supermercat

Aquesta secció recull els patrons d'extracció, regles de desglossament i particularitats de format dels tiquets físics segons cada cadena comercial, assegurant la màxima fidelitat entre el tiquet imprès, la base de dades `compresSuper` i el moviment bancari a `despeses`.

##### 1. Supermercat BonPreu / Esclat

El tiquet de BonPreu / Esclat presenta una estructura regular i detallada, amb patrons clars per a promocions, productes a pes i vals de descompte al peu del document.

```text
+-------------------------------------------------------------+
|                      BONPREU / ESCLAT                       |
|  Data: 28/10/2026   Hora: 12:45   Caixa: 04   Tiquet: 8229  |
+-------------------------------------------------------------+
|  CANELONS                          4,49 €                   |
|    PROMOCIO                       -1,35 €                   |
|  POLLASTRE SENCER                                           |
|    1,225 kg x 4,49 €/kg            5,50 €                   |
|  FUET                              2,95 €                   |
|    PROMOCIO                       -2,95 €                   |
|  ...                                                        |
+-------------------------------------------------------------+
|  TOTAL PRODUCTES                  24,05 €                   |
|  -3 EUR REGAL                     -3,00 €                   |
|  - EUROS BESCANVIATS              -0,85 €                   |
|  TOTAL PAGAT                      20,20 €                   |
|  TARGETA BANCARIA                 20,20 €                   |
+-------------------------------------------------------------+
```

###### A. Dades de Capçalera i Vinculació Bancària
1. **Identificació Comercial**: S'assigna el supermercat com a `BonPreu` (o `Esclat`).
2. **Data**: Figura a la capçalera o al bloc inferior. Sempre en format dia/mes/any.
3. **Conciliació Financera**: L'apunt a `despeses` es registra sota la categoria `menjar` i concepte `BonPreu`. L'import ha de coincidir al cèntim amb l'import final cobrat (`Import càrrec`).

###### B. Articles Unitaris i Promocions en Línia
1. **Producte Estàndard**:
   - Descripció a l'esquerra (ex: `CANELONS`, `FORMATGE TALL`, `PA DE VIDRE`).
   - Preu brut unitari a la dreta.
   - `quantitat = 1` (o enter si es compren múltiples unitats).
2. **Línies de Promoció / Descompte Directe**:
   - Immediatament sota el producte pot aparèixer una línia `PROMOCIÓ -X,XX` o `PROM. -X,XX`.
   - **Regla**: S'assigna aquest descompte al camp `prom` d'aquell article (`prom = -1.35`).
   - El preu total de la línia (`totLinea`) reflecteix sempre el preu net real pagat:
     $$\text{totLinea} = \text{Preu Brut} - |\text{Promoció}|$$
3. **Promocions al 100% (Producte Regal o 2a Unitat Gratis)**:
   - Si la promoció iguala el preu brut (ex: `FUET 2,95 €` amb `PROMOCIÓ -2,95 €`), el camp `totLinea` serà `0.00 €`.
   - **Regla obligatòria**: L'article **NO** s'elimina; s'ha de registrar a `compresSuper` per mantenir la traçabilitat del consum, la família (`carn`) i l'actualització d'estoc al rebost.

###### C. Articles a Pes (Fruiteria, Carnisseria, Peixateria)
1. **Format en Dues Línies**:
   - **Línia 1**: Nom del producte (ex: `POLLASTRE SENCER`).
   - **Línia 2**: Pes i preu unitari (ex: `1,225 kg x 4,49 €/kg`) i a la dreta l'import total de la línia (`5,50 €`).
2. **Regla de Codificació**:
   - Fusionar ambdues línies en un únic registre.
   - `quantitat = 1` (enter invariant).
   - `pes = "1.225 kg"`.
   - `preuUnit = 4.49` (preu per quilo) o preu total de la línia.
   - `totLinea = 5.50` (import net facturat a la dreta).

###### D. Descomptes Globals de Caixa (Final del Tiquet)
1. **Tipus de Descomptes Globals a BonPreu**:
   - Cupons regal en euros: `-3 EUR REGAL`, `-5 EUR REGAL`.
   - Targeta client / guardiola: `- EUROS BESCANVIATS`.
   - Vals promocionals de caixa.
2. **Regla Fonamental d'Imputació**:
   - Aquests descomptes **mai** s'assignen a un sol producte ni es creen com a línies d'article a `compresSuper`.
   - Es sumen conjuntament en el valor de descompte global (`descompte_global`).
   - A la base de dades `compresSuper`, s'enregistra a la columna `descompte` de la **primera línia** del tiquet (`descompte = suma_descomptes_globals`), quedant la resta de línies amb `0.0`.
3. **Equació de Validació**:
   $$\text{Total Net Tiquet} = \sum_{i=1}^{n} \text{totLinea}_i - \text{descompte\_global} \equiv \text{Import Càrrec Bancari}$$

###### E. Línies Informatives que Cal Ometre
- **Saldo i Acumulació Targeta Client**: `EUROS ACUMULATS`, `SALDO TARGETA CLIENT`, `ACUMULAT EN AQUESTA COMPRA` (són saldos per a futures compres, no rebaixes de la compra actual).
- **Quadre d'Impostos**: Taules d'IVA (`BASE`, `IVA 4%`, `IVA 10%`, `IVA 21%`, `QUOTA`).
- **Dades de Transacció TPV**: Dades bancàries, número d'autorització, targeta emmascarada i missatges de confirmació de pagament.

##### 2. Supermercat Novavenda

El tiquet de Novavenda (habitualment gestionat per la societat *Comerbal, S.A.* a les comarques gironines) té una estructura molt característica en blocs multilínia per cada article, incorporant directament el codi de barres EAN i el detall de càlcul de quantitats.

```text
+-------------------------------------------------------------+
|                          NOVAVENDA                          |
|                       Comerbal, S.A.                        |
|              C/. Ramon Pagès, 3 baixos - Arbúcies           |
+-------------------------------------------------------------+
|  BAGUETTE BELLSOLA 255G                            0,62 €   |
|  1601             1 x 0,62 €                                |
|  ARROS INTEGRAL A/ CHIA                            1,45 €   |
|  VASET 2X125 G                                              |
|  8410184033749     1 x 1,45 €                               |
|  COOKIES INT                                       0,99 €   |
|  MUES/TAR/PANSES FLORBU                                     |
|  180G                                                       |
|  8411414010677     1 x 0,99 €                               |
|  PIPES GREFUSA TUJUANA 165                         4,86 €   |
|  8413164004975     3 x 1,62 €                               |
|  XOCOLATA MILKA 125G                              15,48 €   |
|  8410172652525     12 x 1,29 €                              |
|  OFERTA                                                     |
+-------------------------------------------------------------+
|  Base         Tipus        Quota        Total               |
|   3,94         4,00         0,16         4,10               |
|  22,64        10,00         2,26        24,90               |
|  TOTAL                                    29,00 €           |
|  Factura simplificada 228                 Caixa 1           |
|  Data: 31/10/2026 18:28:27                                  |
|  PAGAMENT TARGETA                         29,00 €           |
+-------------------------------------------------------------+
```

###### A. Dades de Capçalera i Peu del Tiquet
1. **Nom Comercial**: S'identifica pel logotip superior `NOVAVENDA` (NIF d'empresa: Comerbal, S.A.). A la base de dades es codifica com a `Novavenda`.
2. **Ubicació de la Data i Hora**: A diferència d'altres supermercats, la data **NO** és a la capçalera sinó al **peu del tiquet**, just sota el total i la taula d'impostos *(Exemple: `Data: 31/10/2026 18:28:27`)*.
3. **Número de Tiquet**: Figura al peu com a `Factura simplificada XXX` al costat del número de caixa (`Caixa X`).
4. **Conciliació Financera**: Es concilia a `despeses` sota la categoria `menjar` i concepte `Novavenda`.

###### B. Estructura de Bloc Multilínia per Article
Cada article comprat a Novavenda es compon sempre d'un bloc de **2, 3 o fins i tot 4 línies consecutives**:
1. **Primera Línia del Bloc (Nom i Import Total)**:
   - Conté l'inici de la descripció del producte en majúscules (ex: `BAGUETTE BELLSOLA 255G`, `COOKIES INT`, `XOCOLATA MILKA 125G`).
   - A l'extrem dret porta sempre el **preu total facturat de la línia** (`totLinea`).
2. **Línies Intermèdies (Continuació de Descripció)**:
   - Si el nom de l'article o el gramatge no caben en una sola línia, continuen a la segona o tercera línia (ex: `VASET 2X125 G`, `MUES/TAR/PANSES FLORBU`, `180G`, `FLORBU 120G`, `CLASSIQUES 150G`).
   - **Regla d'or**: Cal concatenar totes aquestes línies de text en un sol nom descriptiu complet de l'article per cercar o desar a `tb_productes`.
3. **Darrera Línia de Detall (Codi de Barres EAN i Fórmula de Càlcul)**:
   - A l'esquerra: Codi intern de 4 dígits (ex: `1601`) o el **codi de barres EAN complet de 13 dígits** (ex: `8410184033749`, `8411414010677`, `8410172652525`).
   - Al mig/dreta: La fórmula de quantitat i preu unitari: **`QUANTITAT x PREU_UNITARI €`** (ex: `1 x 0,62 €`, `3 x 1,62 €`, `12 x 1,29 €`).
4. **Línia Opcional d'Oferta**:
   - Si el producte gaudeix d'un preu especial o rebaixat, a sota de la línia de càlcul pot aparèixer la paraula `OFERTA`.
   - El preu unitari que figura a `QUANTITAT x PREU_UNITARI €` ja és el **preu net reduït** (ex: la tauleta de Milka 125g venuda a 1,29 € en comptes del preu estàndard de 1,69 €).

###### C. Regles de Codificació a compresSuper
1. **Nom de l'Article**: Fusió íntegra de les línies de text del producte:
   - `"COOKIES INT"` + `"MUES/TAR/PANSES FLORBU"` + `"180G"` $\rightarrow$ `"Cookies integrals muesli panses Florbu 180g"`.
2. **Quantitat i Preu Unitari**:
   - Extreure `quantitat` directament del primer valor de la fórmula (`3 x 1,62 €` $\rightarrow$ `quantitat = 3`).
   - Assignar `preuUnit = 1.62`.
   - `totLinea = 4.86` (preu de la primera línia, que compleix $\text{quantitat} \times \text{preuUnit} = \text{totLinea}$).
3. **Codi de Barres EAN**:
   - El número de 13 dígits permet l'emparellament directe amb la columna `codi_barres` a `tb_productes`, facilitant la lectura làser del rebost.
4. **Descomptes Globals**:
   - Si el tiquet no inclou cupons de caixa al peu, el total net és la suma exacta de tots els `totLinea` ($\sum \text{totLinea} = 29{,}00\text{ €}$, `descompte = 0.00`).

###### D. Línies que Cal Ometre
- Capçalera fiscal (`Comerbal, S.A.`, NIF, telèfon, adreça).
- Quadre de desglossament d'IVA (`Base`, `Tipus`, `Quota`, `Total`).
- Bloc de peu de pàgina de terminal de caixa (`Factura simplificada`, `Caixa`, `PAGAMENT`).

##### 3. Supermercat AreaGuissona (bonÀrea)

El tiquet de bonÀrea (gestionat per la societat *Corporació Alimentària Guissona S.A.*) té una disposició compacta en una sola línia per article, caracteritzada per punts suspensius de separació, la inclusió del percentatge d'IVA a l'extrem dret i la fórmula de múltiples unitats incrustada abans del preu.

```text
+-------------------------------------------------------------+
|                        bonArea (T391)                       |
|             Corporació Alimentària Guissona S.A.            |
|                        NIF: A25445131                       |
|                   C/ Traspalau,8 , Guissona                 |
|               CL CAMPRODON 52-56 , Arbucies                 |
|                      TEL: 972861906                         |
+-------------------------------------------------------------+
| Descripció                         Import %%%%%%            |
| BANANA BOLSA.....................   2,15  4.00              |
| COCTEL AMANIDES 10   3x  1,10       3,30 10.00              |
| TOMÀQUE UNT P BANDE..............   4,06  4.00              |
| IOGURT CABRA 2X125...............   1,27  4.00              |
| FINISIM PERNIL...................   1,03 10.00              |
| TAC DE PANXETA CURADA............   1,43 10.00              |
| FINISIM PERNIL...................   1,07 10.00              |
| CARPACCIO DE MORRO...............   0,87 10.00              |
| FINISSIM DE GALL.................   1,72 10.00              |
| FARINA AMETLLA...................   3,40 10.00              |
| PANET V AMB O BOSS 380 G.........   1,00  4.00              |
| GORGONZ DOP BALLAR CUÑ 1.........   1,65  4.00              |
| CREMETT FIN H PREM 150GR.........   1,75  4.00              |
| DATILS AMB PINYOL................   1,85  4.00              |
+-------------------------------------------------------------+
|                        Desglòs d'IVA                        |
| Tipus Iva        Base        Quota        Total             |
|   4.00%         13,20         0,53        13,73             |
|  10.00%         11,65         1,17        12,82             |
|                                                             |
| Fact. Simplificada Nº 2627-T0391C01-133133                 |
| ||||||||||||||||||||||||||||||||||||||||||||||||            |
| TOTAL A PAGAR                              26,55€           |
+-------------------------------------------------------------+
```

###### A. Dades de Capçalera i Conciliació Bancària
1. **Nom Comercial i Concepte Oficial**: S'identifica per `bonArea` o `Corporació Alimentària Guissona S.A.`. A l'aplicació (`categories_conceptes.json`) i base de dades es codifica de forma canònica sota la categoria `menjar` com a concepte **`AreaGuissona`**.
2. **Codi d'Establiment i Factura Simplificada**: La capçalera indica el codi de botiga (ex: `bonArea (T391)`). El número de factura simplificada té l'estructura `[Sèrie]-[Botiga][Caixa]-[Número]` (ex: `2627-T0391C01-133133`).
3. **Conciliació Financera**: L'apunt es concilia directament amb el moviment de banc/targeta `Import càrrec = 26.55` a `despeses`, canviant `ticketPendent = False`.

###### B. Estructura de Línia d'Article i Parany de l'IVA
1. **Separació per Punts Suspensius**:
   - El nom del producte sol estar seguit d'una cadena de punts suspensius (`.....`) que uneix el text amb la zona numèrica. Aquests punts s'han de suprimir en netejar el nom estàndard de l'article per a `tb_productes`.
2. **MOLT CRÍTIC - Parany del Percentatge d'IVA**:
   - A l'extrem dret de cada línia figura el tipus impositiu d'IVA aplicat (`4.00` per a alimentació bàsica, `10.00` per a carns i elaborats).
   - **Regla d'or**: El darrer número **MAI** és el preu total ni el preu unitari de l'article. El preu total facturat (`totLinea`) és sempre el valor numèric immediatament anterior al percentatge d'IVA.
3. **Quantitats Múltiples Incrustades (`Nx P_Unit`)**:
   - Si s'adquireix més d'una unitat, la fórmula de multiplicació s'intercala a la mateixa línia entre el nom i el total (ex: `COCTEL AMANIDES 10   3x  1,10       3,30 10.00`).
   - S'extreu:
     - `quantitat = 3` (nombre enter invariant).
     - `preuUnit = 1.10`.
     - `totLinea = 3.30` (ja que 3 x 1,10 = 3,30 €).
     - L'IVA `10.00` s'omet del càlcul de preu.

###### C. Desglòs d'IVA i Comprovació Matemàtica
1. **Quadre de Desglòs d'IVA**:
   - Separa les bases imponibles i quotes al 4% i 10%.
   - La suma dels totals dels blocs d'IVA ha de quadrar amb exactitud cèntim a cèntim amb el `TOTAL A PAGAR`:
     $$\text{Total} = \text{Total}_{4\%} + \text{Total}_{10\%} = 13{,}73\text{ €} + 12{,}82\text{ €} = 26{,}55\text{ €}$$
2. **Descomptes Globals**:
   - Habitualment no inclou descomptes de caixa posteriors; per tant, `descompte = 0.00` i la suma de tots els `totLinea` és idèntica al càrrec bancari final (26,55 €).

###### D. Línies que Cal Ometre
- Capçalera fiscal (`Corporació Alimentària Guissona S.A.`, NIF `A25445131`, adreça fiscal i de botiga, telèfon).
- Capçalera de columnes `Descripció       Import %%%%%%`.
- Quadre de `Desglòs d'IVA` (`Tipus Iva`, `Base`, `Quota`, `Total`).
- Codi de barres del peu i cadena `Fact. Simplificada Nº ...`.
- Dades de pagament i terminal de caixa.

---

### 4.2 Mòdul Econòmic i Dashboard (`modules/economic.py`, `modules/dashboard.py`)
Mòdul mestre de control pressupostari, tresoreria bancària, seguiment patrimonial, projecció financera plurianual i comptabilitat familiar integral. Articula la dualitat entre la **Vista Executiva de Dashboard** ([`modules/dashboard.py`](file:///e:/Dashboard/modules/dashboard.py)) i la **Vista Operativa de Gestió Econòmica** ([`modules/economic.py`](file:///e:/Dashboard/modules/economic.py)).

#### A. Arquitectura Financera i Fonts de Dades
El mòdul opera sincronitzant les següents taules a Supabase (PostgreSQL) i fitxers de configuració:
1. **Taules Principals**:
   - `despeses`: Moviments reals de despesa (`ID_mov`, `Data`, `Banc`, `FormaPago`, `IdCategoria`, `Idconcepte`, `Import càrrec`, `ticketPendent`).
   - `ingressos`: Ingressos reals i cobraments (`ID_mov`, `Data`, `Banc`, `FormaPago`, `IdCategoria`, `Idconcepte`, `Import abonament`).
   - `pagaments`: Taula mestre de **previsió de despeses i quotes periòdiques** de tot l'any (`idPago`, `Banc`, `Formapago`, `Data`, `dia`, `mes`, `any`, `Categoria`, `Concepte`, `Import`, `pagat`, `banc_desti`, `import_desti`).
   - `inversions`: Seguiment de posicions financeres, accions i fons indexats (Trade Republic, NVIDIA, S&P 500, etc.).
   - `sync_queue.json`: Cua local de mutacions retingudes en cas de pèrdua de connectivitat.
2. **Configuració Centralitzada**:
   - `categories_conceptes.json` (Config ID 1): Arbre taxonòmic de categories de despesa/ingrés, conceptes associats, llista de comptes bancaris oficials (`BBVA`, `La Caixa`, `Trade Repub.`, `Casa`, `Tg.Moneder`, `CORTEINGLÉS`, `Pago VISA`) i formes de pagament.
3. **Mecanisme de Zero Latència**:
   - Totes les modificacions (`insert_db_row`, `update_db_row`, `delete_db_row`) alteren directament el DataFrame a `st.session_state` i buiden quirúrgicament la finestra recent, sense reiniciar la memòria cau massiva de 24 hores.

---

#### B. Cicle de Vida del Flux Financer

```mermaid
flowchart TD
    A["📅 Generador de Nou Any Comptable"] --> B["🔴 Previsió de Despeses i Ingressos (pagat = 'pendent')"]
    B --> C["🏦 Arribada del Càrrec Bancari o Cobrament Real"]
    C --> D{"Comprovació d'Import i Concepte"}
    D --> E["✅ Marcatge com a 'Pagat' / Liquidat"]
    E --> F["📊 Actualització Instantània de Saldos Bancaris"]
    F --> G["🔍 Conciliació d'Extracte Bancari (show_bank_extract_modal)"]
    G --> H["📈 Anàlisi d'Inversions i Fons d'Estalvi"]
```

- **Pas 1: Planificació Anual**: A través del generador d'any comptable, es projecten totes les quotes fixes, subministraments, hipoteques, impostos i pagues extres dels 12 mesos com a `pendent`.
- **Pas 2: Execució Mensual**: A mesura que avança el mes, l'usuari o el banc van liquidant càrrecs. Des de la taula de previsió es pot marcar com a `Pagat` individualment o mitjançant liquidació massiva.
- **Pas 3: Conciliació i Extracte**: Fent clic a qualsevol targeta de compte bancari, s'obre l'extracte mensual per verificar que el saldo quadra amb el banc real.
- **Pas 4: Traspassos i Inversions**: Gestió de traspassos entre comptes amb control d'imports a destí i seguiment de les carteres d'inversió.

---

#### C. Detall Exhaustiu de les Vistes i Controls Interactius

##### 4.2.1 Vista Executiva: Dashboard General (`view_mode == "dashboard"`)
La pantalla d'inici i comandament financer del Dashboard ([`modules/dashboard.py`](file:///e:/Dashboard/modules/dashboard.py)).

1. **Targetes Interactives de Tresoreria i Comptes Bancaris (Top Container)**:
   - **Mètrica Principal de Saldo Global**: Mostra la suma consolidada de diners de tots els comptes actius: `💰 Saldo Comptes: X.XX €` en verd vibrant i tipografia destacada.
   - **Botons-Targeta de Comptes Bancaris**: Bloc horitzontal amb un botó estilitzat per a cada compte oficial en l'ordre estricte: `BBVA`, `La Caixa`, `TRADE REPUB.`, `Casa` (Efectiu), `Tg.Moneder`, `CORTEINGLÉS`, `Pago VISA`.
     - Tipografia condicional: Verd si el saldo és positiu (`> 0.05 €`), Vermell si és negatiu (`< -0.05 €`).
     - **Acció en 1 Clic**: En clicar sobre qualsevol targeta de banc, s'obre el modal **`show_bank_extract_modal(banc, any, mes)`**.
   - **Diàleg Modal d'Extracte Bancari (`show_bank_extract_modal`)**:
     - Mostra l'extracte complet d'aquell compte per al mes actiu: Saldo inicial a l'inici de mes, llistat cronològic de càrrecs i abonaments amb categoria i concepte, i saldo final resultant.

2. **Filtres Temporals i Límits de Despesa**:
   - **Títol Dinàmic**: `📅 Resum Mensual d'Ingressos i Despeses {Any}`.
   - **Botó Popover `🔍`**: Desplega el selector d'Any i la casella **`Veure límits despesa`** per mostrar les fites pressupostàries mensuals.

3. **Gràfica Temporal i Taula Resum de Categories**:
   - **Gràfic Comparatiu d'Ingressos vs Despeses (Plotly)**: Finestra temporal de 3 anys (`Any-1`, `Any`, `Any+1`) per comparar l'evolució del mes actual amb anys anteriors i projeccions futures.
   - **Taula Resum Ràpida (`generate_fast_summary_table_html`)**: Taula HTML optimitzada amb estils visuals i gradient cromàtic verd/vermell segons el saldo de cada categoria.
   - **Taula Interactiva de Detall del Mes (`st.dataframe` amb `on_select="rerun"`)**: Permet fer clic a qualsevol fila o categoria per filtrar automàticament els moviments individuals a la part inferior de la pantalla.

4. **Seccions Operatives de Detall Mensual: `📤 Pagaments del Mes` i `📥 Ingressos del Mes`**:
   - **Llistats de Moviments del Mes**: Visualització clara de les previsions del mes actiu segregades entre pendents de liquidar i ja pagats/cobrats.
   - **Ajust d'Import Real en 1 Clic**: Cada concepte pendent disposa d'una casella (`st.checkbox`) que en activar-se desplega un selector numèric per ajustar l'import real abans de confirmar l'operació.
   - **Botons d'Acció de Traspàs a BBDD**: Botons dedicats `📥 Passar seleccionats a la BBDD` (per a pagaments) i `📥 Passar ingressos a BBDD` (per a ingressos) que activen el diàleg modal de conciliació.
   - **Modal de Confirmació i Conciliació (`dialog_confirmar_operacions`)**:
     - **Modificació de la Data de l'Apunt (`st.date_input`)**: Cada pagament o ingrés seleccionat inclou un selector de data individual en format `dd/mm/aaaa` que permet indicar exactament el dia de cobrament o càrrec en compte.
     - **Control Estricte de Data del Mes**: El selector de data està blindat tant per interfície (`min_value` al dia 1 i `max_value` a l'últim dia del mes seleccionat) com per comprovació al servidor, impedint que es puguin desar operacions amb dates fora del mes en curs.
     - **Assignació de Banc i Forma de Pagament**: Verificació del compte bancari associat amb selector desplegable si manca assignació prèvia.
     - **Compatibilitat de Tipus amb PyArrow**: El registre de la data i del dia (`dia`) als DataFrames en memòria (`df_pag_local`, `df_ing_local`) està protegit mitjançant assignació polimòrfica i blocs d'excepció segurs, garantint el correcte funcionament en entorns cloud amb PyArrow (`string[pyarrow]`).
     - **Automatització de Traspassos a Inversions**: Si un pagament té com a destí `TR Cartera`, el sistema genera simultàniament l'apunt de despesa, l'ingrés compensatori bancari i la compra a la taula d'inversions `tr_cartera` (NVIDIA o S&P500).

---

##### 4.2.2 Vista Operativa: Mòdul Econòmic (`view_mode == "economic"`)
La interfície de treball comptable estructurada en 6 pestanyes especialitzades ([`modules/economic.py`](file:///e:/Dashboard/modules/economic.py)):

---

##### 4.2.2.1 Pestanya 1: `📝 Ingrés / Despesa General`
Panell d'entrada de transaccions reals del dia a dia i moviments d'efectiu/bancaris que no provenen de tiquets de supermercat.

1. **Formulari Ràpid d'Apunt Contable**:
   - **Ràdio de Tipus**: `Despesa`, `Ingrés`, `Gasolina`, `Traspàs entre comptes`.
   - **Selectors en Cascada**: `Categoria` i `Concepte` amb càrrega dinàmica des de `categories_conceptes.json`.
   - **Selector de Compte i Mètode**: `Banc` (origen) i `Forma de Pagament`.
   - **Camps Numèrics**: `Import (€)` i `Data` de la transacció.
2. **Sub-formulari de Traspassos entre Comptes (`op_banc`)**:
   - En seleccionar un traspàs, apareixen els camps: `Banc d'Origen`, `Banc de Destí`, `Import a Origen` i el camp especial **`Quantitat al banc de destí (€)`**.
   - **Control de Retencions**: Permet reflectir situacions on una part del traspàs es reté en comissions o es desvia a una altra guardiola, calculant automàticament la diferència.
   - **Filtre de Neteja**: El sistema marca aquests moviments com a `op_banc` per no falsejar les estadístiques de consum familiar.
3. **Històric Recent de Moviments**:
   - Graella amb botons d'edició ràpida `✏️` i eliminació `🗑️` amb desplaçament automàtic cap a la paperera de reciclatge.

---

##### 4.2.2.2 Pestanya 2: `🔴 Prev. Despeses` (Pagaments Programats)
Gestió integral de totes les obligacions econòmiques futures i passades de l'exercici.

1. **Formulari Acordió `➕ Nova Previsió de Pagament`**:
   - Permet programar una nova despesa futura: Data/Dia, Concepte, Categoria, Import estimat, Banc assignat i periodicitat.
2. **Filtres i Cercadors de la Taula de Pagaments**:
   - Selectors de filtratge múltiple per: `Any`, `Mes`, `Banc` i `Estat` (Tots, Només Pagats, Només Pendents).
   - Cercador per text de conceptes (ex: `Ibi`, `Assegurança`, `Lloguer`).
3. **Taula Interactiva de Previsió (`st.dataframe`)**:
   - Configuració nativa de columnes (`st.column_config`): Data en format català, imports en euros alineats, i checkboxes interactives de `pagat`.
4. **Accions Massives i Confirmació d'Operacions amb Control de Dates**:
   - **Modificació d'Imports en Bloc**: Permet ajustar l'import previst de múltiples rebuts o ingressos abans de traspassar-los a la comptabilitat definitiva.
   - **Liquidació i Confirmació en Bloc (`dialog_confirmar_operacions`)**: Diàleg modal interactiu que permet revisar cada concepte, verificar el banc associat (o assignar-ne un si manca) i **modificar la data de l'apunt** mitjançant un selector de dates (`st.date_input`) en format `dd/mm/aaaa`.
   - **Control Estricte de Data del Mes**: El selector de dates està blindat visualment (`min_value` i `max_value`) i validat al servidor per garantir que la data de l'apunt estigui obligatòriament compresa entre el dia 1 i l'últim dia del mes consultat, impedint apunts erronis fora de període.

---

##### 4.2.2.3 Pestanya 3: `🟢 Prev. Ingressos` (Nòmines i Rendiments)
Seguiment de les fonts d'entrada monetària de la unitat familiar.

1. **Formulari `➕ Nova Previsió d'Ingrés`**:
   - Registre d'ingressos futurs programats: Nòmines mensuals, pensions, cobraments d'assegurances, lloguers o devolucions fiscals.
2. **Control d'Estat de Cobrament**:
   - Taula amb indicadors d'estat: `🟢 Pagat/Cobrat` vs `🟡 Pendent`.
   - Enllaç directe amb el banc receptor per comprovar la data exacta d'ingrés en compte.
3. **Mètriques Resum d'Ingressos**:
   - KPIs de total ingressat al mes, total pendent de cobrar i comparativa respecte a la previsió inicial.

---

##### 4.2.2.4 Pestanya 4: `📈 Inversions` (Patrimoni i Actius)
Control de carteres de valors, fons indexats i plataformes fintech.

1. **Integració de Posicions (Trade Republic, ETFs, Accions)**:
   - Monitorització de carteres amb detall de títols (ex: NVIDIA, S&P 500, fons monetaris).
   - Registre d'aportacions mensuals recurrents (ex: aportacions de 25 €/mes programades).
2. **Seguiment de Rendibilitat i Plusvàlues**:
   - Càlcul de capital invertit acumulat enfront del valor liquidatiu actual.
   - Gràfics d'evolució patrimonial i gràfic de barres d'aportacions netes.

---

##### 4.2.2.5 Pestanya 5: `💰 Estalvis` (Metes i Reserves)
Gestió de fons d'emergència i guardioles familiars.

1. **Compte i Caixes d'Estalvi**:
   - Separació comptable dels fons immobilitzats per a contingències (reparacions del vehicle, vacances, impostos anuals).
2. **Definició de Metes d'Estalvi**:
   - Barres de progrés interactives que mostren el percentatge assolit per a cada objectiu d'estalvi familiar.
   - Formulari per registrar aportacions o rescats de diners entre el compte corrent i la guardiola d'estalvis.

---

##### 4.2.2.6 Pestanya 6: `🤖 Xat IA` (Assistent Financer Intel·ligent)
Agent conversacional dotat de context sobre la situació econòmica real de la llar.

1. **Context Financer Connectat**:
   - L'assistent disposa de visibilitat sobre els saldos actuals dels comptes, les despeses del mes en curs i les previsions pendents.
2. **Consultes en Llenguatge Natural**:
   - Permet formular preguntes com: *"Puc afrontar una despesa extraordinària de 500 € aquest mes?"*, *"A quant puja la despesa de supermercat aquest trimestre?"* o *"Quin marge d'estalvi tenim fins a final d'any?"*.
3. **Respostes Estructurades**:
   - Proporciona recomanacions d'ajust pressupostari, càlculs de desviació i alertes de liquiditat.

---

#### D. Diàlegs Modals i Eines Globals del Mòdul

1. **`📅 Afegir Nou Any Comptable` (`show_afegir_any_comptable_dialog`)**:
   - Accessible des del menú superior: `Mòduls > Mòdul Econòmic > 📅 Afegir nou any comptable`.
   - Modal amb 3 pestanyes interactives:
     - **Pestanya 1 (Ingressos recurrents)**: Revisa imports de nòmines i pensions per projectar els 12 mesos de l'any següent.
     - **Pestanya 2 (Despeses recurrents)**: Permet editar l'estimació de quotes mensuals (lloguer, hipoteca, assegurances, llum, aigua, etc.) abans de generar-les.
     - **Pestanya 3 (Pagues Extres)**: Permet programar les pagues dobles d'estiu (juny) i Nadal (novembre/desembre), afegint-les automàticament a les previsions.
   - **Botó Generador**: Genera en bloc centenars de registres a `pagaments` amb `pagat = 'pendent'` sense bloquejar la base de dades.

2. **`🗑️ Paperera de Reciclatge` (`show_paperera_modal`)**:
   - Registre d'auditoria de moviments eliminats.
   - Permet restaurar un registre esborrat per error amb un sol clic (`Restaurar`).

3. **`📦 Modal d'Inventari` (`modal_inventari`)**:
   - Balanç patrimonial de béns materials i equipament de la llar.

---

#### E. Enllaços i Interconnexions amb Altres Mòduls
- **[`modules/compres.py`](file:///e:/Dashboard/modules/compres.py)**: Connexió bidireccional immediata. Cada desglossament de tiquet a compres tanca el pendent a `despeses` (`ticketPendent = False`), i el botó `⚡ Mòdul Econòmic` permet alternar entre ambdós mòduls sense perdre context.
- **[`modules/llum_aigua.py`](file:///e:/Dashboard/modules/llum_aigua.py)**: Les factures elèctriques i d'aigua confirmades es consoliden automàticament a les partides corresponents de despeses generals.
- **[`modules/cotxe.py`](file:///e:/Dashboard/modules/cotxe.py)**: Els repostatges de combustible i les factures de taller s'imputen com a despeses del vehicle a la categoria de mobilitat.

---

## 5. Mòduls de Prioritat 3: Subministraments i Manteniment de la Llar

### 5.1 Llum i Aigua (`modules/llum_aigua.py`)
Mòdul central per al seguiment, control analític i optimització energètica dels subministraments bàsics de la llar (electricitat i aigua potable), monitorització de tarifes regulades (PVPC), gestió d'acumuladors tèrmics de calor, ingesta digital de factures en PDF amb visor interactiu i estudi fotovoltaic d'autoconsum basat en dades satel·litàries oficials de la Unió Europea (PVGIS).

#### A. Arquitectura Energètica i Fonts de Dades
El mòdul integra de forma transparent múltiples fonts d'informació oficials, fitxers de configuració i bases de dades al núvol:
1. **Taules a Supabase (PostgreSQL)**:
   - `data/consum_llum.json` / `csv/consum_llum.csv` (Config ID 9): Registre històric complet de factures elèctriques (`idFactura`, `numFactura`, `dataInici`, `dataFi`, `diesFactura`, `importTotal`, `consumTotal`, `kWh_P1`, `kWh_P2`, `kWh_P3`, `potencia_P1`, `potencia_P2`, `pdf_filename`).
   - `data/consum_aigua.json` / `csv/consum_aigua.csv` (Config ID 10): Registre de factures d'aigua (`idFactura`, `numFactura`, `dataInici`, `dataFi`, `diesFactura`, `importTotal`, `consum_m3`, `lecturaAnterior`, `lecturaActual`, `pdf_filename`).
2. **Arxius de Registre Diari i Configuració Local**:
   - `data/preus_llum_diaris.json`: Registre continuat de les 24 hores dels preus PVPC de cada dia, permetent contrastar consums històrics hora a hora amb els preus reals de mercat. Accessible des del menú superior `Editar > 📂 Arxius JSON`.
   - `data/acumuladors_config.json`: Paràmetres tècnics dels acumuladors de calor de la llar (potències en kW i hores de càrrega necessàries per a cada estança).
   - Dipòsits de Documents PDF: `PDF/Factures_Llum/` i `PDF/Factures_Aigua/`.
3. **APIs Externes en Temps Real**:
   - **Red Eléctrica de España (REE / ESIOS - `apidatos.ree.es`)**: Connexió en viu per obtenir els preus horaris de la tarifa regulada 2.0TD (avui i demà a partir de les 20:15h).
   - **PVGIS (Comissió Europea - `re.jrc.ec.europa.eu`)**: API de radiació solar satel·litària per calcular el rendiment fotovoltaic segons les coordenades GPS exactes de l'habitatge.

---

#### B. Cicle de Vida i Flux Operatiu dels Subministraments

```mermaid
flowchart TD
    A["🌐 Scraping Preus PVPC (REE apidatos.ree.es)"] --> B["📊 Registre Horari 24h a preus_llum_diaris.json"]
    B --> C["🔥 Optimitzador de Càrrega d'Acumuladors Tèrmics"]
    D["📄 Arribada de Factura (PDF Llum o Aigua)"] --> E["⚡ Ingesta i Extracció Automàtica (pypdf/regex)"]
    E --> F["🔍 Auditoria i Contrast de Consum Horari"]
    F --> G["💾 Desat a Supabase (IDs 9 i 10) + Arxiu PDF"]
    G --> H["💰 Sincronització amb Despeses (modules/economic.py)"]
    G --> I["☀️ Simulador Solar PVGIS (Càlcul d'Autoconsum i Bateria)"]
```

- **Pas 1: Captura i Gravació PVPC**: L'algoritme consulta la tarifa regulada d'avui i demà, identificant els trams (Vall, Pla, Punta) i gravant les 24 hores a `data/preus_llum_diaris.json`.
- **Pas 2: Optimització de Climatització**: Calcula la millor franja contínua per carregar els acumuladors de calor aprofitant les hores més econòmiques (vall nocturn o vall solar diürn).
- **Pas 3: Ingesta Digital de Factures**: En rebre una factura en PDF, l'usuari la carrega; el motor extreu automàticament imports, dates, consums per tram i potències contractades.
- **Pas 4: Auditoria de Facturació**: Es verifica si l'import facturat coincideix amb els consums per hora, desglossant termes d'energia, potència, lloguer de comptador i bonificacions (com el Bono Social).
- **Pas 5: Sincronització i Estudi Solar**: Les dades es consoliden a la comptabilitat i alimenten el simulador fotovoltaic PVGIS per calcular l'estalvi potencial amb plaques solars.

---

#### C. Detall Exhaustiu de les 3 Pestanyes de la Interfície Gràfica

El mòdul s'estructura en 3 grans àmbits mitjançant `st.tabs`:

---

##### 5.1.1 Pestanya 1: `⚡ Consum Llum` (Preus PVPC, Acumuladors i Factures Elèctriques)

Aquesta vista es divideix en 3 subpestanyes interactives superiors i un panell inferior de gestió documental de factures:

1. **Subpestanya 1.1: `📅 Preus d'Avui`**:
   - **Targetes KPI en Temps Real**:
     - `Preu Actual`: Preu en €/kWh de l'hora en curs amb etiqueta de color vibrant segons el tram (🟢 Vall, 🟡 Pla, 🔴 Punta).
     - `Preu Mitjà`: Mitjana ponderada de les 24 hores del dia.
     - `Hora Més Barata`: Franja horària amb el cost mínim (indicant si hi ha preus negatius o propers a 0 €).
     - `Hora Més Cara`: Franja horària amb el cost màxim a evitar.
   - **Gràfic Horari de 24 Hores (Plotly)**: Corba interactiva de barres verticals on cada barra correspon a una hora del dia (00h a 23h), acolorida segons la tarifa regulada 2.0TD (verd per a vall, groc per a pla, vermell per a punta). En passar el cursor, es visualitza el preu exacte en €/kWh i €/MWh.
   - **Secció d'Optimització d'Acumuladors de Calor**:
     - Llegeix les característiques tècniques de `data/acumuladors_config.json`.
     - **Selector d'Hores de Càrrega**: Permet escollir quantes hores de càrrega requereix cada acumulador segons la temperatura exterior.
     - **Càlcul de Finestra Òptima Contínua**: L'algoritme troba el període d'hores consecutives més econòmic per a la càrrega, maximitzant el rendiment tèrmic dels nuclis ceràmics sense disparar el cost elèctric.

2. **Subpestanya 1.2: `🔮 Preus de Demà`**:
   - Es publica automàticament cada dia a partir de les 20:15h (quan l'operador del mercat OMIE i REE publiquen la subhasta diària).
   - Ofereix el mateix conjunt de mètriques KPI i gràfic horari de 24 hores que la pestanya d'avui, facilitant la planificació anticipada d'electrodomèstics d'alt consum (rentadores, assecadores, rentavaixelles o recàrrega de vehicle).

3. **Subpestanya 1.3: `⚖️ Comparativa Avui vs Demà`**:
   - **Gràfic Combinat de Doble Línia (Plotly)**: Superposa la corba horària d'avui davant la de demà per comparar l'evolució del cost energètic hora a hora.
   - **KPIs de Variació**: Percentatge d'increment o descens del preu mitjà per saber si convé avançar o endarrerir consums intensius.

4. **Gestió de Factures Elèctriques (Històric i Ingesta PDF)**:
   - **Botó `📄 Nova factura llum`**: Desplega el panell de càrrega per arrossegar el document PDF emès per la comercialitzadora (Endesa, Iberdrola, Naturgy, PVPC, etc.).
   - **Extracció Automàtica Intel·ligent (`extract_data_from_pdf_bytes`)**:
     - Extreu via text digital i expressions regulars el número de factura, les dates d'inici i final, els dies facturats, l'import total en euros, els kWh consumits per tram (P1 Punta, P2 Pla, P3 Vall) i les potències contractades.
   - **Visor Natiu de Factures PDF (`view_pdf_dialog`)**: Obre un diàleg modal `@st.dialog` amb el document renderitzat sobre un llenç HTML5 (PDF.js Canvas), amb botons de canvi de pàgina, zoom i descàrrega.
   - **Format de Dates Unificat (`dd/mm/aaaa`) i Parser Resilient (`_parse_dmy_or_iso`)**:
     - Totes les dates de les factures elèctriques (`dataFactura`, `periodeInici`, `periodeFi`) s'emmagatzemen unificadament en format europeu `dd/mm/aaaa` tant al fitxer JSON persistent [`data/consum_llum.json`](file:///e:/Dashboard/data/consum_llum.json), com al fitxer [`csv/consum_llum.csv`](file:///e:/Dashboard/csv/consum_llum.csv) i al registre central de Supabase (Config ID 9).
     - La funció auxiliar `_parse_dmy_or_iso()` incorporada a [`modules/llum_aigua.py`](file:///e:/Dashboard/modules/llum_aigua.py) assegura que tant els formularis d'alta com els modals d'edició (`edit_factura_dialog`, `edit_factura_aigua_dialog`) puguin llegir i interpretar qualsevol format de data amb màxima tolerància a fallades, desant sempre la sortida normalitzada a `dd/mm/aaaa`.
   - **Taula d'Històric de Factures (`st.dataframe`)**: Mostra totes les factures registrades amb columnes configurades. Cada fila disposa de botons per:
     - `👁️`: Veure el document PDF original al visor.
     - `✏️`: Obrir el modal d'edició (`edit_factura_dialog`) per corregir qualsevol dada.
     - `🗑️`: Esborrar la factura i eliminar el fitxer físic de disc (`delete_factura_dialog`).
   - **Gràfic Mensual de Consum per Tram (Plotly Stacked Bar)**: Gràfic de barres apilades que reflecteix el consum en kWh de P1, P2 i P3 per a cada mes, coronat amb l'etiqueta flotant neta del preu total en euros sobre cada barra.

---

##### 5.1.2 Pestanya 2: `💧 Consum Aigua` (Lectures de Comptador i Factures Hídriques)

Control del subministrament d'aigua de xarxa de l'habitatge:

1. **Gestió i Ingesta de Factures d'Aigua**:
   - **Botó `📄 Nova factura aigua`**: Càrrega del PDF oficial de la companyia d'aigües (ex: Sorea, Agbar, Aigües municipals).
   - **Extracció Automàtica de Paràmetres**: Número de rebut, període de consum, import total, volum en metres cúbics ($m^3$), lectura anterior del comptador i lectura actual.
   - **Visor PDF Integrat**: Revisa visualment la factura en PDF mitjançant el visor `PDF.js`.

2. **Taula Històrica de Facturació Hídrica**:
   - Llistat cronològic de consums en $m^3$, dies de facturació, quota fixa de servei, cànon d'aigua i import total.
   - Accions d'edició ràpida (`edit_factura_aigua_dialog`) i eliminació segura (`delete_factura_aigua_dialog`).

3. **Gràfics d'Evolució Hídrica (Plotly)**:
   - **Evolució de Consum en $m^3$**: Barres mensuals de volum consumit amb línia de tendència de consum mitjà diari en litres per persona.
   - **Cost Mitjà del Metre Cúbic**: Ràtio entre import pagat i volum real ($€/m^3$) per vigilar increments de tarifes municipals o canvis de tram de consum.

---

##### 5.1.3 Pestanya 3: `☀️ Estudi Solar i Autoconsum (PVGIS)`

Eina de modelització i enginyeria financera per avaluar la instal·lació de panells solars fotovoltaics a l'habitatge:

1. **Paràmetres Dinàmics de la Instal·lació**:
   - **Selector de Potència per Panell**: Desplegable per escollir la potència dels mòduls (400W, 450W, 500W, 550W).
   - **Control de Nombre de Plaques**: Selector numèric de mòduls fotovoltaics a instal·lar.
   - **Orientació i Inclinació de Teulada**: Ajust segons la coberta real de la casa (Sud pur, Est-Oest, inclinació en graus).
   - **Capacitat d'Emmagatzematge en Bateria**: Selector de capacitat útil en kWh (de 0 a 15 kWh de bateries de liti LFP).
   - **Derivació a Acumuladors Tèrmics**: Opció per derivar automàticament els excedents solars cap a la calefacció d'acumuladors de calor abans d'abocar energia a la xarxa.

2. **Model de Radiació Solar PVGIS (Comissió Europea)**:
   - Aplica les dades oficials d'Hores de Sol Pic (HSP) mensuals basades en satèl·lits meteorològics per a les coordenades exactes de l'habitatge.
   - Contrast en temps real contra el consum elèctric real extret de l'històric de factures registrades a `consum_llum.json`.

3. **Simulació Econòmica i Normativa d'Autoconsum (RD 244/2019)**:
   - **Compensació d'Excedents Realista**: Simula fidelment la legislació vigent, on els excedents abocats només compensen fins al valor de l'energia consumida de la xarxa durant el període, sense reduir mai el terme de potència fix ni els peatges del sistema.
   - **Càlcul d'Autosuficiència Energètica (%)**: Percentatge de l'energia total de la llar que quedarà coberta directament pel sol.
   - **Comparativa Financera d'Inversió**: Balanç entre la modalitat "Clau en mà" (instal·lador comercial) i modalitat "Mixta / DIY" (adquisició directa de materials i suport d'electricista autoritzat per al butlletí CIE).

---

#### D. Navegació Dinàmica i Enllaços amb Altres Mòduls
- **Navegació per Paràmetres URL (`st.query_params`)**:
  - `?tab=llum`: Obre directament la secció elèctrica i tarifes PVPC.
  - `?tab=aigua`: Condueix a les factures d'aigua.
  - `?tab=solar`: Activa el simulador fotovoltaic PVGIS.
- **Interconnexions amb la Resta del Dashboard**:
  - **[`modules/economic.py`](file:///e:/Dashboard/modules/economic.py)**: Les factures elèctriques i d'aigua confirmades es consoliden automàticament a les línies de despesa de subministraments de la comptabilitat general.
  - **Menú Superior `Editar > 📂 Arxius JSON`**: Accés directe per consultar o editar `data/preus_llum_diaris.json` i `data/acumuladors_config.json`.
  - **Domòtica i Alertes**: Connexió futura amb sistemes domòtics (Home Assistant) per disparar relés de càrrega d'acumuladors en les hores vall calculades.

---

### 5.2 Manteniment de la Llar (`modules/manteniment.py`)
Mòdul integral de gestió operativa de la llar, planificació de tasques domèstiques recurrents i reparacions, coordinació familiar de responsabilitats, gestió documental centralitzada de manuals d'instruccions d'aparells i vigilància semafòrica de venciments de garanties i factures de compra.

#### A. Arquitectura del Mòdul i Fonts de Dades
El mòdul opera combinant registres JSON sincronitzats a Supabase, repositoris físics de documents PDF i el perfil familiar:
1. **Taules a Supabase (PostgreSQL)**:
   - `data/registre_manteniment.json` / `csv/manteniment.csv` (Config ID 8): Registre de tasques i manteniments (`idManteniment`, `dataManteniment`, `feina`, `tipus`, `alertaA`, `diesAvis`, `acompliment`, `observacions`, `serie_id`, `recurrencia`, `subtasques`, `subtasques_template`, `send_to_calendar`).
   - `data/manteniment_docs.json` (Config ID 7): Dipòsit documental de metadades de Manuals i Garanties (`id`, `categoria`, `titol`, `aparell`, `estanca`, `establiment`, `data_compra`, `data_fi_garantia`, `import`, `filename`, `num_pagines`).
2. **Dipòsit Documental Físic**:
   - `PDF/Manuals/`: Manuals d'ús d'electrodomèstics, maquinària i equips de la llar.
   - `PDF/Garanties/`: Factures de compra, tiquets de garantia i pòlisses oficials.
3. **Mòduls Interconnectats**:
   - `core/config.json` (Config ID 2): Llegeix els noms dels membres de la unitat familiar per assignar responsabilitats personals al camp `alertaA`.
   - `core/calendar_manager.py`: Sincronització bidireccional de tasques de manteniment amb l'agenda familiar (`modules/calendari.py`).
   - `core/alerts.py`: Motor d'avisos a la campaneta superior (`🔔`) segons els dies d'antelació configurats (`diesAvis`).

---

#### B. Cicle de Vida i Flux Operatiu de Manteniment

```mermaid
flowchart TD
    A["➕ Creació de Tasca (Puntual o Periòdica)"] --> B["📅 Sincronització Automàtica amb el Calendari Familiar"]
    B --> C["🔔 Alerta a la Campaneta segons diesAvis"]
    C --> D{"Realització de Feina i Subtasques"}
    D --> E["✅ Toggle d'Acompliment en 1 Clic (Feta/Pendent)"]
    E --> F["🔁 Auto-Generació de la Propera Tasca de la Sèrie"]
    G["📄 Arribada de Manual o Garantia PDF"] --> H["📚 Catalogació Documental i Visor HTML5 Canvas"]
    H --> I["🛡️ Vigilància Semafòrica de Garanties (Vigent/Propera/Vençuda)"]
```

- **Pas 1: Planificació de la Feina**: Es defineix la tasca amb el seu tipus (Manteniment, Reparació, Feina de casa), assignació a un membre o a tothom, dies d'avís i periodicitat (setmanal, mensual, anual, etc.).
- **Pas 2: Sincronització i Avisos**: La tasca s'envia opcionalment al calendari familiar i, quan falten els dies establerts a `diesAvis`, apareix destacada a la campaneta d'alertes.
- **Pas 3: Execució i Subtasques**: Es revisen les subtasques associades (ex: netejar filtre d'aire, greixar engranatges). En completar-les, la tasca principal es marca com a feta amb un sol clic (`acompliment = 'Sí'`).
- **Pas 4: Gestió Documental i Garanties**: Els aparells nous es donen d'alta pujant el seu manual i factura; el sistema calcula automàticament els dies de garantia restants i alerta abans que caduqui la cobertura.

---

#### C. Detall Exhaustiu de les 3 Pestanyes de la Interfície Gràfica

El mòdul s'estructura en 3 pestanyes operatives mitjançant `st.tabs` amb suport per a paràmetres URL (`?tab=...`):

---

##### 5.2.1 Pestanya 1: `🛠️ Registre de Manteniment` (Tasques, Reparacions i Feines de Casa)

La interfície d'execució diària de manteniments de la llar:

1. **Barra d'Accions Superiors i Filtres**:
   - **Botó `➕ Nova Tasca` (`type="primary"`)**: Obre el formulari d'alta d'una nova tasca o manteniment.
   - **Filtre de Membre Familiar**: Desplegable per filtrar les tasques assignades a una persona concreta (ex: Enric, Isabel) o veure les de `Tothom`.
   - **Filtres Temporals i d'Estat**:
     - Selectors d'Any i Mes per segmentar l'històric.
     - Selector d'Estat: `Totes`, `Pendents`, `Fetes`, `Vençudes` (amb data anterior a avui i encara no complertes).

2. **Formulari d'Alta i Edició de Tasques (`edit_task_dialog`)**:
   - **Camp `Data` (`st.date_input`)**: Data prevista d'execució.
   - **Camp `Feina` (`st.text_input`)**: Descripció concisa de l'actuació (ex: *Canviar filtre d'osmosi*, *Revisió caldera gas*, *Pintar barana jardí*).
   - **Selector `Tipus`**: Desplegable amb 4 categories: `Manteniment`, `Reparació`, `Feina casa`, `Altres`.
   - **Selector Multiselecció `Alerta a`**: Permet triar un o diversos membres de la família o l'opció `Tothom`.
   - **Camp Numèric `Dies d'avís`**: Antelació en dies amb què el sistema començarà a avisar a la campaneta superior (`🔔`) abans de la data de venciment.
   - **Selector de Periodicitat**:
     - Opcions: `Puntual`, `Diària`, `Setmanal`, `Quinzenal`, `Mensual`, `Bimestral`, `Trimestral`, `Semestral`, `Anual` o `Personalitzada`.
     - Límit de generació configurable: Per nombre de repeticions o l'opció especial `"Fins a final d'any (31/12)"`.
     - Agrupació per sèrie (`serie_id`): Enllaça totes les concurrències d'una mateixa rutina amb la numeració correlativa `🔁 Periodicitat (X/N)`.
   - **Gestor de Subtasques amb Cadència Pròpia (`subtasques_template`)**:
     - Permet definir subtasques subordinades amb ritmes propis *(Exemple: tasca mare mensual amb una subtasca que només toca fer cada 3 mesos)*.
   - **Casella `Enviar al Calendari`**: Sincronitza la tasca amb l'agenda familiar (`data/events.json`).
   - **Camp `Observacions`**: Notes tècniques, números de telèfon de tècnics o instruccions addicionals.

3. **Targetes Interactives de Tasca (Graella Operativa)**:
   - Cada tasca es mostra en una targeta visual amb codi de color segons el seu estat:
     - 🔴 **Vençuda**: Fons d'alerta vermell si la data ha passat i no s'ha completat.
     - 🟡 **Pendent Pròxima**: Fons groc si s'acosta la data.
     - 🟢 **Completada**: Fons verd suau amb text ratllat.
   - **Botó Toggle d'Acompliment `✅ / ❌`**: Commuta en 1 sol clic l'estat entre feta i pendent (`toggle_manteniment_acompliment`), actualitzant immediatament el comptador d'alertes.
   - **Checklist de Subtasques**: Caselles interactives per marcar subtasques individuals amb indicador de fracció de progrés *(Exemple: `📋 Subtasques (2/3)`)*.
   - **Botó `✏️` (Editar)**: Obre el modal per ajustar dates, periodicitats o membres assignats.
   - **Botó `🗑️` (Eliminar)**: Obre el modal de confirmació per esborrar la tasca puntual o tota la sèrie pendent (`delete_task_dialog`).

4. **Generador de Tasques del Proper Any (`show_generar_any_manteniment_dialog`)**:
   - Accessible des del botó dedicat o el menú superior `Mòduls > Manteniment de la llar > 📅 Generar tasques proper any`.
   - Revisa automàticament els patrons de totes les tasques periòdiques actives i proposa la generació en bloc de tot el calendari de manteniment de l'any següent, evitant omissions i garantint continuïtat en la cura de la llar.

---

##### 5.2.2 Pestanya 2: `📚 Manuals d'Instruccions` (Dipòsit Documental de la Llar)

Arxiu centralitzat de manuals tècnics i llibrets d'instruccions d'aparells, calderes, electrodomèstics i eines de la casa:

1. **Controls d'Alta i Cerca Documental**:
   - **Botó `➕ Afegir Manual` (`type="primary"`)**: Obre el diàleg modal `add_manual_dialog`:
     - Camps: `Títol del document`, `Aparell o model`, `Estança / Ubicació` (Cuina, Safareig, Garatge, Jardí, etc.) i component de càrrega d'arxiu PDF (`st.file_uploader`).
   - **Cercador de Manuals**: Barra de cerca predictiva per localitzar manuals per paraula clau, marca o aparell (ex: *Bosch*, *Caldera Baxi*, *Aire condicionat*).
   - **Filtre per Estança**: Desplegable per visualitzar només els equips d'una habitació concreta.

2. **Targetes Interactives de Manuals**:
   - Cada manual es presenta en una targeta amb miniatura documental, nom de l'equip, estança i recompte de pàgines (`📄 X pàgines`).
   - **Botó `👁️ Veure Manual`**: Obre el visor natiu `view_pdf_dialog` (renderització Canvas HTML5 via PDF.js), que permet llegir el manual còmodament a pantalla completa sense descarregar-lo ni patir bloquejos d'iframes.
   - **Botó `✏️ Editar`**: Modifica metadades (canvi d'estança o títol).
   - **Botó `🗑️ Eliminar`**: Esborra el registre de Supabase i elimina el fitxer físic de `PDF/Manuals/` (`delete_document_dialog`).

---

##### 5.2.3 Pestanya 3: `🛡️ Garanties i Factures de Compra` (Vigilància Semafòrica de Cobertures)

Monitorització de factures de compra, pòlisses d'assegurança i tiquets de garantia per no perdre cap dret de reparació o canvi:

1. **Alta de Garanties i Factures (`add_garantia_dialog`)**:
   - **Botó `➕ Afegir Garantia` (`type="primary"`)**: Obre el modal d'enregistrament:
     - Camps: `Títol / Descripció`, `Aparell o bé cobert`, `Establiment de compra` (ex: MediaMarkt, El Corte Inglés, Amazon), `Data de compra`, `Data de fi de garantia`, `Import de compra (€)` i càrrega del fitxer PDF de la factura o tiquet.

2. **Motor de Càlcul Semafòric de Cobertura (`calculate_warranty_status`)**:
   - L'algoritme avalua en temps real els dies que manquen fins a la data de venciment:
     - 🟢 **Vigent**: Garantia activa amb més de 90 dies de cobertura restant.
     - 🟡 **Venciment Proper**: Menys de 90 dies per a la caducitat (genera un avís groc de revisió preventiva abans que expiri la protecció legal).
     - 🔴 **Vençuda / Caducada**: Cobertura extingida.

3. **Graella de Garanties i Accions**:
   - Targetes visuals amb l'import original, botiga, període de cobertura i dies restants en format destacat.
   - **Botó `👁️ Veure Factura / Garantia`**: Visualitza el tiquet o factura original d'alta resolució al visor PDF.js.
   - **Botó `✏️ Editar`**: Permet corregir dates de compra o imports.
   - **Botó `🗑️ Eliminar`**: Esborra el registre i neteja el PDF associat de `PDF/Garanties/`.

---

##### 5.2.4 Pestanya 4: `🏗️ Projectes d'Obra i Reformes` (Plànols Canvas, Materials, Fases i Assistent IA)

Espai integral per a la planificació, disseny i seguiment d'obres majors, reformes i projectes de millora de la llar (ex: reforma de bany, impermeabilització de parets, substitució de terres, instal·lació de pèrgoles, renovació de pintura o cuina):

1. **Arquitectura de Dades, Persistència i Capçalera**:
   - Taula `app_config` de Supabase (`id = 11`, `projectes_manteniment`) amb fallback local a `data/projectes_manteniment.json` (`core/projectes_manager.py`).
   - Sincronització asíncrona resilient: actualització immediata de la memòria cau de sessió, desat atòmic al disc local i rèplica a Supabase en segon pla mitjançant fil d'execució asíncron (daemon thread), garantint 0 ms de latència a la interfície.
   - Totes les dates es presenten, s'introdueixen i es calculen estrictament en format català/europeu **`DD/MM/AAAA`** (`date.today() + timedelta(...)` i `st.date_input(format="DD/MM/YYYY")`).
   - **Mètrica de Calendari sense retallades**: Presentació jeràrquica a la capçalera amb valor principal gran per a la Data d'Inici (`DD/MM/AAAA`) i línia secundària estilitzada per a la finalització (`🏁 Fi: DD/MM/AAAA`) amb amplada adaptativa i tooltip informatiu, eliminant els desbordaments de text (`...`).
   - **Filtratge Dinàmic de Projectes per Estat**: Selector tàctil per xips/pills (`Tots`, `⏳ Pendent`, `🔨 En curs`, `✅ Finalitzat`) amb comptadors en temps real que filtra immediatament el desplegable de projectes actius. Incorpora icones d'estat a cada títol de projecte i normalització resilient d'estats històrics.
   - **Canvi d'Estat a 1 Clic i Sincronització de Filtres**: Botons directes a la capçalera `🔨 Iniciar Projecte` i `⏳ Pausar Projecte` amb vinculació reactiva (`pending_filtre_estat_projectes` i `pending_select_projecte_actiu`). Quan un usuari inicia o pausa un projecte (o en modifica l'estat des del formulari), la vista commuta automàticament la pestanya del filtre (p. ex. a `🔨 En curs`) i manté el projecte seleccionat perquè no desaparegui mai de la pantalla.
   - **Esborrat Segur de Projectes**: Botó destacat `🗑️ Esborrar aquest Projecte` a l'acordió d'opcions amb diàleg modal de confirmació clara (`@st.dialog("🗑️ Confirmar Eliminació del Projecte")`) que evita eliminacions accidentals.

2. **Plànol i Croquis Interactiu (HTML5 Canvas Tàctil Mòbil/PC amb Foto de Fons)**:
   - Component de dibuix autònom (`modules/canvas_planol.py`) adaptat 100% a telèfons mòbils i tauletes mitjançant **Pointer Events** unificats i `touch-action: none` (permet arrossegar el dit sobre la quadreta sense desplaçar ni bloquejar la pàgina).
   - **Controls de Zoom (`🔍+`, `🔍-`, `100%`)**: Botons de zoom suau (de 0.75x a 2.50x) amb finestra de visualització de 380px i resolució nativa quadrada de 800x800 (`aspect-ratio: 1 / 1`), que garanteix un desplaçament fluid 100% bidireccional (tant vertical com horitzontal) i precisió matemàtica de coordenades per a pantalla tàctil i ratolí a qualsevol escala.
   - **Eina de Navegació i Desplaçament (`🖐️ Moure` / Pan)**: Eina dedicada per moure's i navegar lliurement pel plànol en qualsevol direcció (vertical i horitzontal simultàniament) arrossegant el dit o el ratolí quan s'ha fet zoom, sense risc de dibuixar línies accidentals. Funciona com a commutador (`toggle`): prémer `🖐️ Moure` activa el mode (`🖐️ Moure: ON`) i tornar-lo a prémer o seleccionar qualsevol eina (com `🧱 Paret`) desactiva el desplaçament a l'instant i retorna directament al mode de dibuix anterior. Al prémer `100%` es recentra automàticament el plànol.
   - **Mode Paret Contínua (`🔗 Seguir traç: SÍ/NO`) per a Habitacions**:
     - Enllaç seqüencial automàtic dissenyat específicament per dibuixar habitacions completes.
     - Un cop traçada una paret, el sistema fixa l'últim extrem amb un halo maragda i etiqueta visible (*🔗 Propera paret*). La següent paret arrenca automàticament des d'aquell punt sense haver de buscar on continuava.
     - Botó `⏹️ Desconnectar` per alliberar l'ancoratge quan es vulgui començar una paret separada en una altra zona.
   - **Snap Magnètic a Vèrtexs i Cantonades (`🧲 Snap`)**:
     - Atracció automàtica (radi de 26px) a qualsevol cantonada o extrem existent, indicat amb un anell verd maragda (`🟢`) i creueta de precisió.
     - Permet tancar habitacions rectangulars o poligonals de manera 100% estanca i mil·limètrica tant amb el dit com amb el ratolí.
     - Lectura de distància en metres en temps real durant el traç de la línia.
   - **Selector de Mode de Vista: `📐 Planta (Terra)` vs `🧱 Alçat (Paret)`**:
     - *Mode Planta*: Dissenyat per a distribucions horitzontals de sòl, habitacions i cotes de planta.
     - *Mode Alçat (Paret)*: Especialitzat per a reformes de parets verticals. Dibuixa automàticament guies de referència de terra (`TERRA / SÒL 0,00 m`) i sostre (`SOSTRE ~2,50 m`).
     - *Cotes intel·ligents segons orientació*: L'eina de cotes detecta si el traç és vertical o horitzontal. En vertical suggereix alçades arquitectòniques típiques (*Sostre 2,50 m, Dutxa 1,80 m, Sòcol 1,20 m, Aixeta 0,90 m*), i en horitzontal amplades. Els valors es renderitzen amb un fons d'etiqueta d'alta visibilitat (fons blanc al 90% amb vora) perquè mai es confonguin amb els colors de la foto de fons de la paret.
     - *Anotacions de paret*: L'eina de text adapta els seus suggeriments a feines típiques de paret (*Forat / Clivella, Ciment cola, Calç, Pintura antihumitat, Sòcol, Rajola, etc.*).
   - **Goma d'esborrar intel·ligent (`🧹 Goma`)**:
     - *Detecció matemàtica contínua (`distToSegment`)*: Permet esborrar qualsevol paret, cota, text o habitació tocant o lliscant el dit per qualsevol punt de la línia (amb tolerància tàctil de 26px per a mòbils), sense obligar a encertar el punt central exacte. Permet esborrat múltiple en continu (arrossegant el dit).
     - *Comportament commutador (`toggle`)*: Prémer `🧹 Goma` activa el mode (`🧹 Goma: ON` en vermell). Prémer-lo una altra vegada o seleccionar qualsevol eina (com `🧱 Paret`) desactiva l'esborrat immediatament i torna a l'eina de dibuix.
   - **Creador d'Habitacions amb Mides Exactes (`🏠 Habitació`)**:
     - Modal interactiu per generar estances a escala real en segons indicant l'amplada i la llargada en metres (amb botons ràpids per a mides estàndard: 2.00, 2.50, 3.00, 3.50, 4.00, 5.00 m).
     - Permet triar el nom de l'estança mitjançant xips ràpids (*Menjador, Cuina, Bany, Dormitori, Despatx, Terrassa*) i la textura de terra.
     - Genera automàticament l'espai interior texturat a escala mil·limètrica (40px = 1,00 m), les 4 parets de contorn, la placa identificadora central amb les mides i les dues cotes dimensionals (amplada i llargada) sense haver de dibuixar línia per línia.
   - **Galleda de Textures Arquitectòniques (`🪣 Textura`)**:
     - Selector visual de textures vectorials netes generades proceduralment via CanvasPattern (sense arxius d'imatge externs, 100% lleugeres i nítides a qualsevol nivell de zoom).
     - *Catàleg per a Mode Planta*: Parquet de roure, rajola/gres de bany o cuina, rajola blava/gresite de dutxa, gespa de jardí/pati, microciment continu i fons net transparent.
     - *Catàleg per a Mode Alçat (Paret)*: Maó vist / totxo vermell rústic, rajola blanca de cuina/bany (subway tile), mur de pedra rústica, llistons verticals de fusta i paret d'arrebossat de calç/ciment.
     - *Interacció dual*: Tocant qualsevol habitació o espai ja dibuixat s'omple automàticament amb la textura seleccionada; si s'arrossega sobre un espai buit, traça un nou rectangle amb la textura triada.
   - Eines integrades: Parets rectes (`🧱 Paret`), creador d'habitacions (`🏠 Habitació`), espais rectangulars (`🔲 Espai`), galleda de textures (`🪣 Textura`), cotes de distància (`📏 Cota`), etiquetes de text (`🔤 Text`), goma d'esborrar (`🧹 Goma`), eina de navegació (`🖐️ Moure`) i botó de reversió immediata (`↩️ Desfer`).
   - **Modal intern tàctil**: Formulari emergent intern compatible amb Android/iOS per introduir mides i noms d'estances sense dependre de `window.prompt()`.
   - **Suport per a fotografia de fons**: Permet carregar una imatge real de l'estança o la foto d'un croquis fet a mà en paper, amb regulador d'opacitat per calcar i acotar al damunt.
   - **Guia d'Ús integrada**: Acordió desplegable (`📖 Guia d'Ús: Com funciona l'editor de plànols?`) disponible permanentment a la pròpia pestanya, que centralitza totes les instruccions tàctils per a ús mòbil i la descripció pas a pas de cada eina (alliberant l'espai vertical útil de l'editor Canvas).
   - Botó de descàrrega (`💾 Descarregar PNG`) i formulari de registre del plànol oficial del projecte.
   - **Galeria fotogràfica de seguiment i blindatge de càrrega**:
     - **Compressió Automàtica d'Imatges (PIL)**: Mitjançant `compress_image_b64()`, totes les fotos preses amb la càmera del mòbil (habitualment entre 10 i 15 MB en cru) es comprimeixen automàticament a un màxim de 1280 px i qualitat 80% JPEG (~150 KB, reducció superior al 90%), respectant l'orientació EXIF original (`ImageOps.exif_transpose`). Això blinda l'aplicació contra tancaments o desconnexions sobtades del WebSocket de Tornado i resol els límits d'arxiu de Supabase.
     - **Desat Atòmic Local**: Les fotos i actualitzacions s'escriuen de forma atòmica al disc mitjançant arxiu temporal `.tmp` i `os.replace`, prevenint fitxers corruptes davant d'interrupcions.
     - **Renderització Nativa amb `st.image`**: Ús del component natiu `st.image(..., use_container_width=True)` sobre graella de 4 columnes en lloc de tags HTML `st.markdown('<img src="...">')`, evitant que el parser de Markdown tracti les cadenes llargues Base64 com a codi de text brut.
     - **Zoom i Detall**: Botó `🔍 Veure` i esdeveniment directe sobre la fotografia per visualitzar-la a pantalla completa. Classificació per etapes (*🔴 Abans*, *🟡 Durant l'obra* i *🟢 Resultat final*), amb dates en `DD/MM/AAAA` i descripció.

3. **Graella Visual de Materials, Control de Stock i Proveïdors en Memòria**:
   - **Miniatures Compactes i Renderització Nativa `st.image`**: Graella de 6 columnes per fila amb miniatures renderitzades mitjançant `st.image(..., use_container_width=True)` per garantir nitidesa i proporcions correctes d'imatges verticals de mòbil (sacs de ciment, calç, etc.) sense dependre de tags HTML subjectes a trencaments de Markdown.
   - **Obertura per Doble Clic o Clic**: En fer doble clic sobre qualsevol miniatura o prémer el botó inferior de la fitxa s'obre el diàleg modal complet `@st.dialog("🧱 Fitxa i Detalls del Material")`.
   - **Fitxa Integral del Material**:
     - Visualització i gestió de la foto: pujada d'arxiu/foto mòbil en Base64 amb compressió automàtica, generació instantània amb IA (Pollinations.ai), enllaç web extern o eliminació de foto.
     - Edició de nom d'article, quantitat i preus (estimat i real).
   - **Suport de Materials "Ja en Stock" (Cost 0 €)**:
     - Possibilitat d'indicar la disponibilitat com a `📦 Ja en stock (a casa / reaprofitat)`.
     - Distintiu visual `📦 Stock` a la miniatura i còmput automàtic de 0,00 € a la despesa real del projecte, assegurant que no resti pressupost a la llar.
   - **Memòria Persistent de Proveïdors**:
     - Catàleg emmagatzemat a `data/proveidors_projectes.json` gestionat per `get_llista_proveidors()` i `add_proveidor_memoria()`.
     - Opció `➕ Afegir un altre proveïdor...` al desplegable que obre immediatament el camp reactiu per afegir el comerç a la memòria a perpetuïtat per a tots els projectes.

4. **Fases d'Execució, Checklist i Gestió d'Estats a 1 Clic**:
   - Desglossament per etapes constructives seqüencials (ex: Enderroc, Instal·lacions, Revestiments, Pintura) amb dates en `DD/MM/AAAA`.
   - **Selector Directe d'Estat en 3 Botons per Fase**: Substitució del desplegable tradicional per 3 botons d'acció directa: `[ ⏳ Pendent ]`, `[ 🔨 En curs ]`, `[ ✅ Acabada ]` amb indicadors d'estat i ressaltat visual segons l'estat actual. En commutar, s'aplica el canvi immediatament sense bloquejos ni atenuacions de pantalla (eliminat el diàleg modal que deixava atenuada la meitat inferior de la interfície).
   - **Promoció Automàtica a «En curs»**: Si un projecte està en estat «Pendent» i es marca qualsevol fase o subtasca com a «En curs» o «Acabada», el projecte pare passa automàticament a «En curs».
   - **Neteja Reactiva de Subtasques**: El formulari d'afegir subtasca es buida automàticament en enviar (`clear_on_submit=True`), emet missatges de confirmació temporal (`st.toast` i `st.success`) i incorpora un botó d'eliminació ràpida `🗑️` al costat de cada subtasca.
   - **Tancament d'Obra i Banner de Progrés**:
     - Quan es completa el 100% de les fases i tasques, es desplega el panell destacat amb llançament de globus festius (`st.balloons()`), permetent confirmar el pas del projecte a `Finalitzat` o reobrir-lo en qualsevol moment (`↩️ Reobrir Projecte`).

5. **Dissenyador Paramètric de Mobles i CutList Optimizer (`modules/moble_disseny_ui.py`, `core/cut_optimizer.py`)**:
   - **Subpestanya `🪚 Disseny & Despecejament MD`**: Eina de fusteria integrada per dissenyar mobles a mida i optimitzar el tall de taulers de fusta per a l'obra.
   - **Modelat 3D Interactiu (Three.js)**: Visualitzador tridimensional amb òrbita, zoom, textures de fusta i vista explosionada (*exploded view*) per analitzar cada component de l'acoblament.
   - **Plantilles Paramètriques i Mode Lliure**: Generador d'estructures estàndard (Prestatgeria, Armari, Taula) amb dimensions configurables (alçada, amplada, profunditat, número de prestatges o calaixos) i mode de peces lliures per a projectes personalitzats.
   - **Algorisme Guillotine Bin Packing 2D**: Motor matemàtic d'aprofitament que organitza les peces sobre planxes comercials estàndard de fusta (ex: taulers de 2440 x 1220 mm), minimitzant les minves.
   - **Compensació del Gruix de Disc de Serra (Kerf)**: Càlcul precís amb tolerància de 3 a 4 mm per cada tall de serra circular.
   - **Control de Veta de la Fusta (Grain Direction)**: Opció individual per peça per respectar la direcció de la veta o permetre el gir de 90° si es prioritza l'estalvi de tauler.
   - **Agrupació per Gruix i Diagrames Vectorials SVG**: Segmentació de peces per gruix de tauler (de 3 mm a 30 mm) i generació de plànols de tall en format SVG descarregables per portar al magatzem de fusteria.

6. **Assistent d'Intel·ligència Artificial d'Obra (`core/ai_projectes.py`)**:
   - Xat interactiu especialitzat integrat al context de cada projecte (amb dades de materials, fases, ubicació i pressupost).
   - Assessorament en materials idonis, coles per a zones humides, aïllaments i eines necessàries.
   - Tutorials i procediments pas a pas amb temps d'assecat recomanats.
   - Orientació de preus mitjans de mercat per metre quadrat.
   - **Reactivació de Consultes (`🔄 Reactivar`)**: Cada pregunta anterior de l'usuari a l'historial disposa d'un botó d'un sol toc per tornar a executar-la immediatament amb el motor d'IA seleccionat sense haver de reescriure-la.
   - **Targeta Resilient d'Errors i Reintent (`🔄 Reintentar ara` / `🗑️ Descartar`)**: Si una consulta falla (per quota o caiguda de xarxa), es mostra una targeta compacta amb els botons d'acció directament a la part superior (100% visible a pantalles mòbils) i el detall tècnic en un desplegable; permet reintentar a l'instant o descartar el missatge per deixar neta la conversa.
   - **Auto-Adaptació de Crèdits a OpenRouter (HTTP 402)**: Si el balanç de crèdits a OpenRouter és inferior als 3.000 tokens per defecte, el motor (`core/llm.py`) detecta automàticament els tokens assequibles (`can only afford X`) i redueix la reserva a mida; si el saldo fos zero, activa un fallback automàtic i transparent a Gemini (2.5 Flash).
   - **Generació 1-Clic**: Botons `✨ Suggerir Materials amb IA` (amb fotografies automàtiques de producte) i `✨ Generar Fases amb IA` per omplir automàticament les taules del projecte amb recomanacions professionals.

---

#### D. Navegació Dinàmica i Enllaços amb Altres Mòduls
- **Navegació per Paràmetres URL (`st.query_params`)**:
  - `?tab=registre`: Activa directament la graella de tasques de manteniment.
  - `?tab=manuals`: Condueix a la biblioteca de manuals d'instruccions.
  - `?tab=garanties`: Obre el monitor de venciments de garanties.
  - `?tab=projectes`: Obre el gestor de projectes d'obra i reformes.
- **Interconnexions amb la Resta del Sistema**:
  - **[`modules/calendari.py`](file:///e:/Dashboard/modules/calendari.py)**: Les tasques marcades amb `send_to_calendar` es reflecteixen a l'agenda familiar com a esdeveniments amb icona d'eina (`🛠️`).
  - **[`core/alerts.py`](file:///e:/Dashboard/core/alerts.py)**: Les tasques que arriben al seu període d'avís (`diesAvis`) i les garanties amb venciment proper (< 90 dies) s'envien automàticament a la campaneta d'alertes de la barra superior.
  - **Menú Superior `Mòduls > Manteniment de la llar`**: Enllaços ràpids per obrir el generador d'any o consultar la documentació tècnica.

---

### 5.3 Cotxe i Mobilitat (`modules/cotxe.py`)
Mòdul especialitzat en la gestió del vehicle familiar, registre de trajectes i quilometratge per lectura d'odòmetre amb comprovació estricta anti-errors, control de proveïments de combustible i consum real, vigilància mecànica integral col·lapsable (oli, pneumàtics, pressió, líquids i taller) i mètriques analítiques de cost per quilòmetre.

#### A. Arquitectura del Mòdul i Fonts de Dades
El mòdul interactua amb les següents taules a Supabase (PostgreSQL) i fitxers de configuració:
1. **Taules Principals**:
   - `kmCotxe` / `csv/kmCotxe.csv`: Registre cronològic de lectures del comptaquilòmetres i desplaçaments (`idKm`, `data`, `contador`, `km`, `ruta`, `observacions`, `conductor`).
   - `repostatge` / `csv/repostatge.csv`: Històric de càrregues de combustible (`idRepost`, `data`, `litres`, `preu_litre`, `total_import`, `estacio`, `tipus_combustible`, `km_odometre`).
   - `manteniment_cotxe.json` (sincronitzat a Supabase): Registre de canvis d'oli, pneumàtics, inflats de rodes, nivells de líquids i entrades a taller.
2. **Configuració de Rutes Habituals**:
   - `rutes_config` (centralitzat a `categories_conceptes.json`): Catàleg de trajectes freqüents de la llar amb quilometratges predefinits (ex: Arbúcies-Girona, Arbúcies-Vic, etc.) per accelerar l'entrada de dades.
3. **Mecanisme de Validació Estricta d'Odòmetre**:
   - Blindatge en temps real que impedeix desar lectures incoherents on el quilometratge entrat sigui igual o inferior a l'últim valor registrat a la base de dades (`contador_val > last_km`).

---

#### B. Cicle de Vida i Flux Operatiu de Mobilitat

```mermaid
flowchart TD
    A["🚗 Lectura d'Odòmetre (Manual o Foto OCR)"] --> B{"Validació: contador_val > last_km?"}
    B -- No --> C["⛔ Bloqueig en Vermell: Quilometratge Invàlid"]
    B -- Sí --> D["💾 Càlcul de Trajecte i Desat a kmCotxe"]
    D --> E["⛽ Registre de Repostatge de Combustible"]
    E --> F["💰 Sincronització amb Despeses (modules/economic.py)"]
    D --> G["🔍 Avaluació de Desgaste Mecànic per Km"]
    G --> H{"Km restants d'oli/rodes < llindar avís?"}
    H -- Sí --> I["🔔 Alerta a la Campaneta de la Barra Superior"]
    H -- No --> J["🟢 Estat Mecànic Correcte"]
```

- **Pas 1: Lectura de Quilòmetres**: L'usuari introdueix el valor de l'odòmetre o puja una foto del quadre de comandaments. El sistema verifica que el valor superi l'anterior; si no, bloqueja el botó de desar.
- **Pas 2: Càlcul de Trajecte**: Es computen els quilòmetres nets recorreguts ($\Delta	ext{Km} = 	ext{contador} - 	ext{last\_km}$) i s'associa la ruta escollida.
- **Pas 3: Repostatge i Cost**: En posar benzina o dièsel, s'anoten litres i import, alimentant el càlcul de consum i generant l'apunt a despeses.
- **Pas 4: Monitorització de Desgast**: A cada increment de quilòmetres, el mòdul recalcula la vida útil restant de l'oli i les rodes, avisant quan cal demanar hora al taller.

---

#### C. Detall Exhaustiu de les 4 Pestanyes de la Interfície Gràfica

El mòdul s'estructura en 4 pestanyes operatives mitjançant `st.tabs` amb suport per a commutació dinàmica i paràmetres URL (`?tab=...`):

---

##### 5.3.1 Pestanya 1: `🛣️ Registre Km i Rutes` (Control d'Odòmetre i Desplaçaments)

La interfície d'enregistrament diari de desplaçaments del vehicle:

1. **Mètriques Resum d'Odòmetre (Top Container)**:
   - **`Darrer Odòmetre Registrat`**: Mostra la lectura acumulada oficial en quilòmetres (ex: `184.250 km`).
   - **`Data Darrera Lectura`**: Indica quan es va efectuar l'últim registre per situar temporalment l'usuari.

2. **Formulari de Nova Lectura i Rutes**:
   - **Camp `Data` (`st.date_input`)**: Data del desplaçament.
   - **Camp `Lectura de l'Odòmetre (Km totals)` (`st.number_input`)**: Valor actual del comptador del cotxe.
   - **Mecanisme de Validació Estricta d'Odòmetre**:
     - Si l'usuari escriu un valor igual o inferior a l'últim registrat (`contador_val <= last_km`):
       - Es mostra una **alerta visual vermella** immediata: `⚠️ Els kilòmetres entrats (X km) han de ser estrictament superiors a l'últim odòmetre registrat (Y km).`
       - El camp calculat del trajecte mostra un text d'error: `❌ Trajecte invàlid`.
       - El botó de desat queda completament **deshabilitat**.
     - Si el valor és vàlid (`contador_val > last_km`):
       - Es computa a l'instant el trajecte realitzat: `🚗 Trajecte calculat: +Z km`.
       - El botó verd `💾 Registrar lectura de km` s'habilita per desar a Supabase.
   - **Selector de Plantilles de Rutes Habituals**:
     - Desplegable amb trajectes freqüents preconfigurats (ex: *Arbúcies - Girona*, *Arbúcies - Vic*, *Anar a la feina*).
     - Botó `➕ Afegir nova ruta`: Permet donar d'alta rutes recurrents personalitzades a `categories_conceptes.json`.
   - **Selector de Conductor**: Permet assignar qui conduïa el vehicle (Enric, Isabel, etc.).
   - **Camp `Observacions`**: Detalls puntuals del viatge (ex: *Trànsit dens*, *Pluja*, *Ruta per autopista AP-7*).

3. **Reconeixement OCR per Foto (`📸 Llegir km amb una foto del comptaquilòmetres`)**:
   - **Expander Desplegable**: Permet pujar una fotografia feta amb el mòbil al quadre de comandaments del cotxe (`st.file_uploader`).
   - **Processament per Visió**: Tesseract OCR extreu automàticament els dígits numèrics de la pantalla digital o analògica de l'odòmetre i preomple el camp de quilòmetres sense necessitat d'escriure'l a mà.

4. **Taula Històrica de Rutes (`st.dataframe`)**:
   - Graella completa de viatges ordenats cronològicament.
   - Mostra: Data, Odòmetre, Km fets en el viatge, Ruta, Conductor i Observacions.
   - Botons d'acció per editar o eliminar registres erronis.

---

##### 5.3.2 Pestanya 2: `⛽ Repostatge` (Proveïment i Despesa de Carburant)

Gestió de combustible del vehicle:

1. **Formulari de Càrrega de Carburant**:
   - **Camp `Data`**: Data de la visita a la benzinera.
   - **Selector `Estació de Servei`**: Desplegable amb les gasolineres habituals (ex: *EsclatOil*, *Repsol*, *BonÀrea*, *Cepsa*). Botó per afegir-ne de noves.
   - **Selector `Tipus de Carburant`**: Dièsel, Gasolina 95, Gasolina 98, GLP.
   - **Camps Numèrics Connectats**:
     - `Litres subministrats` (l).
     - `Preu per litre` (€/l).
     - `Import total` (€): Es calcula automàticament com $	ext{Litres} 	imes 	ext{Preu/litre}$ amb possibilitat d'ajust manual per arrodoniments de sortidor.
     - `Quilòmetres actuals de l'odòmetre`: Lectura del comptaquilòmetres en el moment de repostar (clau per al càlcul de consums).
   - **Casella `Enviar a despeses financeres`**: Si està marcada, crea immediatament un apunt de despesa comptable a la taula `despeses` de [`modules/economic.py`](file:///e:/Dashboard/modules/economic.py) sota la categoria de mobilitat.

2. **Taula Històrica de Proveïments**:
   - Registre històric amb filtres per any i estació de servei.
   - Mètriques de resum: Total litres consumits, despesa acumulada en carburant i preu mitjà del litre pagat.

---

##### 5.3.3 Pestanya 3: `🔧 Manteniment i Nivells` (Estructura Col·lapsable d'Expanders)

Monitor mecànic integral organitzat en blocs desplegables independents (`st.expander`) per mantenir una navegació neta i compacta, amb interruptor superior *"Desplegar totes les seccions"* i **badges d'estat en temps real als encapçalaments**:

1. **Interruptor General i Configuració d'Alertes**:
   - **Casella `Desplegar totes les seccions`**: Obre o tanca de cop tots els blocs plegables.
   - **Expander `🔔 Configuració d'avisos`**: Permet definir amb quants quilòmetres d'antelació el sistema comença a avisar a la campaneta de la barra superior (per defecte: `1.000 km abans`).

2. **Expander `🛢️ Canvi d'Oli` (amb badge dinàmic de km restants)**:
   - Mostra: Km de l'últim canvi, interval recomanat pel fabricant (ex: 15.000 km / 1 any), quilòmetres que falten per al proper servei i data estimada segons el ritme d'ús del cotxe.
   - **Barra de Desgast de l'Oli**: Indicador visual percentual de degradació.
   - **Formulari `✏️ Registrar canvi d'oli`**: Permet anotar la data, quilometratge del canvi, marca/viscositat de l'oli utilitzat (ex: *5W30 Sintètic*) i si s'ha canviat també el filtre d'oli.

3. **Expander `🛞 Canvi de Rodes` (Estat dels Pneumàtics)**:
   - Control independent de les cobertes de l'eix davanter i de l'eix posterior.
   - Mostra els quilòmetres acumulats per cada joc de pneumàtics respecte a la seva vida útil estimada (ex: 40.000 km).
   - Formulari de planificació i registre de substitució (Davanteres, Darreres o les 4 rodes alhora).

4. **Expander `💨 Inflat de Rodes (Pressió)`**:
   - Monitorització de la pressió dels pneumàtics en fred en bars (ex: Davant 2.3 bar, Darrere 2.2 bar).
   - **Planificació de Revisions**: Permet programar dates fixes de comprovació o vincular-les abans de viatges llargs de vacances.
   - **Formulari `✏️ Registrar inflat de rodes fet`**: Desa la data, pressions aplicades i estat de la vàlvula.

5. **Expander `🧪 Control de Nivells` (Els 4 Líquids Bàsics)**:
   - Secció especialitzada per a la inspecció regular dels fluids del compartiment del motor:
     1. **Nivell d'Oli de Motor**: Estat entre marques Mínim i Màxim de la varilla.
     2. **Líquid Refrigerant / Anticongelant**: Nivell del vas d'expansió.
     3. **Líquid de Frens**: Estat del dipòsit de la bomba de fre.
     4. **Líquid Eixugaparabrises**: Estat de reserva i addició de sabó netejador.
   - Formulari de planificació d'inspeccions i registre de comprovació amb caselles de farciment si ha calgut afegir líquid.

6. **Expander `🛠️ Taller i Avaries` (Reparacions i ITV)**:
   - Registre d'incidències greus, manteniments extraordinaris o revisions d'ITV.
   - Camps: Data d'entrada, Taller mecànic, Descripció dels treballs, Peces substituïdes, Import de la factura i estat (`En taller`, `Pendent de recanvi`, `Resolt`).

7. **Expander `📋 Històric de Manteniment i Taller`**:
   - Taula cronològica consolidada de totes les actuacions mecàniques sobre el vehicle.
   - Mètrica KPI del cost total acumulat en manteniment mecànic al llarg de la vida útil del cotxe.

---

##### 5.3.4 Pestanya 4: `📊 Consum i Rendiment` (KPIs Analítics i Eficiència)

Panell d'intel·ligència energètica i econòmica del vehicle:

1. **Càlcul Matemàtic del Consum Mitjà ($l/100	ext{ km}$)**:
   - Aplica la fórmula real d'eficiència creuant els litres omplerts amb la distància recorreguda entre proveïments complets:
     $$	ext{Consum} = rac{	ext{Litres}}{\Delta 	ext{Km}} 	imes 100 \quad (l/100	ext{ km})$$
   - Indicador de consum mitjà històric en comparació amb el consum oficial homologat del vehicle.

2. **Càlcul del Cost Global per Quilòmetre (€/km)**:
   - Computa el cost real de moure el vehicle sumant el combustible i el desgast mecànic:
     $$	ext{Cost/km} = rac{\sum 	ext{Carburant (€)} + \sum 	ext{Manteniment i Taller (€)}}{	ext{Km Totals Recorreguts}}$$

3. **Gràfics Interactius de Plotly**:
   - **Evolució del Consum**: Línia temporal de consum mitjà mensual per detectar augments de consum derivats de filtres bruts o pneumàtics desinflats.
   - **Històric del Preu del Carburant**: Gràfic d'evolució del preu pagat per litre (€/l) al llarg dels mesos.
   - **Distribució per Estacions de Servei**: Gràfic de barres que compara quines gasolineres han ofert els preus més competitius.

---

#### D. Navegació Dinàmica i Enllaços amb Altres Mòduls
- **Navegació per Paràmetres URL (`st.query_params`)**:
  - `?tab=km`: Obre directament el registre de quilometratge i rutes.
  - `?tab=repostatge`: Condueix a la càrrega de combustible.
  - `?tab=oli`: Desplega els controls mecànics col·lapsables.
  - `?tab=consum`: Activa el panell d'eficiència i estadístiques.
- **Interconnexions amb el Sistema Global**:
  - **[`modules/economic.py`](file:///e:/Dashboard/modules/economic.py)**: Les càrregues de combustible i les factures de taller mecànic es consoliden automàticament a les despeses generals del pressupost familiar.
  - **[`core/alerts.py`](file:///e:/Dashboard/core/alerts.py)**: Notificacions preventives a la campaneta superior (`🔔`) quan manquen menys de 1.000 km per al canvi d'oli, rodes o venciment d'ITV.
  - **Menú Superior `Editar > 📂 Arxius JSON`**: Accés per consultar i modificar el llistat de rutes habituals.

---

## 6. Mòduls de Prioritat 4: Família, Nutrició i Benestar

### 6.1 Menús i Cuina (`modules/menjar.py`)
Mòdul gastronòmic i nutricional per a la planificació setmanal dels àpats de la llar (dinars i sopars), recomanador intel·ligent d'alimentació basat en IA amb perfils mèdics i personals, gestor d'estoc d'ingredients connectat amb el rebost en temps real, llibre mestre de receptes amb escalat automàtic de comensals i organització de cuina avançada (*mise en place* i *batch cooking*).

#### A. Arquitectura Gastronòmica i Fonts de Dades
El mòdul unifica taules estructurades a Supabase, perfils nutricionals familiars i el repositori de queviures:
1. **Taules a Supabase (PostgreSQL)**:
   - `tb_receptes_pro`: Catàleg mestre de receptes (`idRecepta`, `titol`, `categoria`, `dificultat`, `temps_minuts`, `comensals_base`, `ingredients_raw`, `instruccions`, `eines_necessaries`, `imatge_url`, `calories_racio`, `proteines_g`, `hidrats_g`, `greixos_g`, `valoracio_estrelles`).
   - `tb_historial_menjars`: Registre històric d'àpats consumits amb data i tipus d'àpat per alimentar les regles anti-repetició.
   - `tb_peticions_menjar`: Bústia de propostes i plats desitjats pels diferents membres de la família.
   - `menu_setmanal`: Emmagatzematge del pla setmanal actiu de dilluns a diumenge.
2. **Configuració Nutricional i Familiar (`core/config.json` - Config ID 2)**:
   - **Comensals per defecte**: Xifra de referència de la llar (per defecte: 3 comensals).
   - **Al·lèrgies Mèdiques**: Bloqueig estricte d'ingredients a nivell de salut (ex: celiaquia, fruits secs, lactosa).
   - **Vetos Personals**: Preferències d'aliments que un membre concret no consumeix (ex: bledes, casqueria, ceba crua), associant automàticament un **plat comodí ràpid** (ex: truita, carn a la planxa) per a aquell membre, compartint la mateixa guarnició familiar.
   - **Eines de Cuina Disponibles**: Catàleg d'aparells presents a la llar (Thermomix, Forn elèctric, Airfryer, Olla express, Paella, etc.).
3. **Connexió en Temps Real amb el Rebost**:
   - Revisa l'estoc d'aliments de `compresSuper` i prioritza receptes que aprofitin ingredients peribles propers a la seva data de consum preferent, reduint a zero el malbaratament domèstic.

---

#### B. Cicle de Vida i Flux Operatiu Gastronòmic

```mermaid
flowchart TD
    A["📥 Bústia de Peticions Familiars"] --> B["🤖 Generador de Menú amb IA (Gemini)"]
    C["🥫 Ingredients del Rebost en Temps Real"] --> B
    D["⚙️ Perfil Familiar (Al·lèrgies, Vetos, Eines)"] --> B
    B --> E["📅 Menú Setmanal Planificat (Dilluns a Diumenge)"]
    E --> F["🔄 Ajust Manual de Plats (modal_canvi_plat)"]
    F --> G["👥 Escalat Automàtic de Comensals (scale_ingredients)"]
    G --> H["👨‍🍳 Mise en Place i Batch Cooking de Diumenge"]
    G --> I["🛒 Generació d'Ingredients a la Llista de la Compra"]
    E --> J["💾 Desat a tb_historial_menjars (Anti-repetició)"]
```

- **Pas 1: Captura de Preferències i Rebost**: La IA consulta els ingredients que cal gastar del rebost, les peticions de la família i les regles dietètiques.
- **Pas 2: Generació de la Proposta Setmanal**: Es construeix la graella de dinars i sopars balancejant carns, peixos, verdures i llegums, evitant hidrats consecutius i respectant els límits calòrics.
- **Pas 3: Personalització i Canvi de Plats**: L'usuari pot substituir qualsevol plat amb el cercador interactiu `modal_canvi_plat`.
- **Pas 4: Escalat i Preparació**: Es defineixen els comensals reals de cada àpat; el sistema recalcula les quantitats d'ingredients i deriva les tasques prèvies de cocció per al diumenge (*batch cooking*).
- **Pas 5: Llista de Compra i Historial**: Els ingredients que no són al rebost s'envien automàticament a la llista de compra de [`modules/compres.py`](file:///e:/Dashboard/modules/compres.py) i el menú es consolida a l'historial.

---

#### C. Detall Exhaustiu de les 6 Pestanyes de la Interfície Gràfica

El mòdul s'estructura en 6 pestanyes operatives mitjançant `st.tabs` amb suport per a paràmetres URL (`?tab=...`):

---

##### 6.1.1 Pestanya 1: `📅 Menú Setmanal` (Planificador Dinar i Sopar)

La interfície d'organització dels àpats de la setmana en curs:

1. **Subpestanyes per Dia (`🗓️ Dilluns` a `🗓️ Diumenge`)**:
   - Cada dia de la setmana es presenta en una pestanya independent per oferir una visió clara i espaiosa dels àpats.
2. **Targetes Interactives de Plat (Dinar i Sopar)**:
   - Cada àpat compta amb seccions per a: **1r Plat**, **2n Plat** i **Postres**.
   - Cada plat es renderitza amb la seva **fotografia oficial 4:3 en primer pla** i etiqueta de temps de cocció i dificultat.
   - **Botó `🔄 Canviar Plat`**: Obre el diàleg modal `modal_canvi_plat` que permet substituir el plat proposat mitjançant cerca difusa o explorant per categoria (Primers, Segons, etc.).
   - **Botó `📖 Veure Recepta`**: Obre la fitxa completa de preparació (`modal_recepta`).
   - **Botó `👨‍🍳 Organització`**: Obre el modal `modal_organitzacio` amb les instruccions de cuina específiques per a aquell dia (descongelar la nit abans, temps d'inici, ordre de fogons).
3. **Selector Dinàmic de Comensals**:
   - Selector numèric que permet ajustar quantes persones dinaran o soparan aquell dia en concret, recalculant automàticament les racions dels ingredients.
4. **Botó `💾 Desar Menú a l'Historial`**:
   - Enregistra els plats efectivament servits a `tb_historial_menjars` per activar el filtre anti-repetició per als propers menús.

---

##### 6.1.2 Pestanya 2: `👨‍🍳 Mise en Place & Batch Cooking` (Preparacions Prèvies)

Panell d'estratègia culinària per estalviar temps entre setmana:

1. **Agrupació de Cocció de Diumenge (*Batch Cooking*)**:
   - Revisa tots els àpats de la setmana i unifica les preparacions base que es poden cuinar de cop:
     - Sofregits de ceba i tomàquet.
     - Caldos i brous de pollastre o verdures.
     - Cocció de llegums o verdures al vapor.
     - Enfornat conjunt de tubercles o proteïnes.
2. **Descompte Automàtic d'Estoc del Rebost**:
   - Si al rebost o congelador ja hi ha caldos o sofregits desats, l'algoritme els descompta automàticament de la càrrega de treball del diumenge:
     $$	ext{Feina de diumenge} = \max(0, 	ext{Necessari per als menús} - 	ext{Estoc al Rebost})$$
3. **Eines de Cuina i Cronograma**:
   - Guia visual amb les eines necessàries (Thermomix, Forn, Airfryer, Olla express) i ordre òptim d'execució per tenir-ho tot envasat en carmanyoles en menys de 2 hores.

---

##### 6.1.3 Pestanya 3: `🤖 Generador de Menús IA` (Nutrició Intel·ligent)

Motor de recomanació nutricional basat en models multimodals avançats (Gemini):

1. **Paràmetres i Filtres de Generació**:
   - **Límit Calòric Independent**: Permet establir un màxim de calories per als dinars (ex: 700 kcal) i per als sopars (ex: 450 kcal).
   - **Selector de Membres a Taula**: Caselles per indicar quins familiars seran a casa cada dia de la setmana.
   - **Regles Dietètiques Integrades**: Màxim 1 cop per setmana carn vermella, mínim 2 cops peix, mínim 2 cops llegum i prohibició d'hidrats pesats consecutius.
   - **Filtre Anti-repetició**: Llindar en dies per impedir que es repeteixin receptes consumides recentment a l'historial.
2. **Núvol d'Etiquetes del Rebost (`render_pantry_tag_cloud`)**:
   - Mostra en etiquetes interactives els aliments que són actualment al rebost de la llar.
   - L'usuari pot fer clic sobre un ingredient (ex: *carbassa*, *llenties*, *xampinyons*) per obligar la IA a incloure'l al menú d'aquesta setmana.
3. **Botó `⚡ Generar Menú amb IA`**:
   - Executa el model de llenguatge amb el prompt estructurat i retorna la graella completa de la setmana amb opció d'aplicar-la o regenerar-la.

---

##### 6.1.4 Pestanya 4: `📖 Llibre de Receptes` (Receptari Familiar)

Enciclopèdia culinària interactiva de la llar:

1. **Expander de Cerca i Filtres Avançats**:
   - **Camp `Cercar per nom...`**: Cerca en temps real per títol o ingredient clau.
   - **Filtres Multiselecció**:
     - `Categoria`: Primer, Segon, Postre, Complement, Guarnició, Salsa.
     - `Dificultat`: Fàcil, Mitjana, Difícil.
     - `Tipus de Dia`: Entre setmana, Cap de setmana, Festiu, Especial.
     - `Àpat`: Esmorzar, Dinar, Sopar.
     - `Origen`: Biblioteca pròpia / Internet.
   - **Slider de Temps Màxim**: Filtra per durada de cocció (de 0 a 240 minuts).
2. **Graella de Receptes Gastronòmiques**:
   - Targetes visuals amb fotografia oficial en format 4:3 en alta resolució i enquadrament centrat a 45° (com el conjunt de receptes tradicionals: *Daus de sípia a la planxa*, *Pinxos de pollastre adobats*, *Palpís de gall d'indi*, *Pastís de truites amb formatge blau*, *Salmó al forn amb verdures*), valoració per estrelles (⭐), temps de preparació i etiqueta calòrica.
3. **Fitxa Detallada de Recepta (`modal_recepta`)**:
   - S'obre en clicar sobre qualsevol plat:
     - **Selector d'Escalat Dinàmic de Comensals (1 a 30)**: Executa l'algoritme `scale_ingredients`, recalculant de forma proporcional grams, mil·lilitres, unitats i fraccions d'ingredients.
     - Taula d'ingredients escalats i instruccions numerades pas a pas.
     - Dades nutricionals per ració: Calories (kcal), Proteïnes (g), Hidrats de carboni (g) i Greixos (g).
     - Eines de cuina requerides amb icones d'aparell.
     - **Botó `🛒 Afegir a la Llista de Compra`**: Envia els ingredients que no són al rebost directament a la llista de compra de [`modules/compres.py`](file:///e:/Dashboard/modules/compres.py).

---

##### 6.1.5 Pestanya 5: `➕ Afegir Recepta` (Creació i Edició)

Formulari estructurat per enregistrar nous plats al patrimoni culinari de la llar:

1. **Metadades Bàsiques**: Títol del plat, categoria gastronòmica, temps de preparació en minuts, nivell de dificultat, tipus de dia recomanat i nombre de racions base.
2. **Editor d'Ingredients i Procediment**:
   - Àrea de text estructurada per llistar ingredients (un per línia amb quantitat i unitat).
   - Pas a pas detallat de la tècnica de cocció.
3. **Aparells i Nutrició**:
   - Marcatge d'eines necessàries (Thermomix, Forn, Airfryer, etc.).
   - Estimació de calories i macronutrients per ració.
4. **Càrrega de Fotografia Gastronòmica**:
   - Pujada d'imatge amb recomanació d'angle a 45° en format 4:3 per a una visualització òptima.

---

##### 6.1.6 Pestanya 6: `📥 Bústia de Peticions` (Participació Familiar)

Espai col·laboratiu per als membres de la família:

1. **Registre de Desitjos Gastronòmics**: Formulari ràpid on qualsevol membre pot indicar quin plat li faria il·lusió menjar (ex: *Canelons*, *Paella de marisc*, *Cremós de xocolata*).
2. **Taula de Peticions Pendents**: Llista de propostes amb la data de la sol·licitud i el nom del membre de la família.
3. **Botó d'Aprovació Directa**: En aprovar una petició, el plat s'incorpora com a prioritat màxima a la següent planificació de la IA o es col·loca directament al dia escollit.

---

#### D. Navegació Dinàmica i Enllaços amb Altres Mòduls
- **Navegació per Paràmetres URL (`st.query_params`)**:
  - `?tab=menu`: Obre el menú setmanal.
  - `?tab=mise_en_place`: Condueix al pla de batch cooking.
  - `?tab=generador`: Activa el generador d'intel·ligència artificial.
  - `?tab=receptes`: Desplega el catàleg de receptes.
  - `?tab=bustia`: Obre la bústia familiar de peticions.
- **Interconnexions amb la Resta del Dashboard**:
  - **[`modules/compres.py`](file:///e:/Dashboard/modules/compres.py)**: Connexió bidireccional: el rebost alimenta els ingredients disponibles per a les receptes, i el botó `🛒 Afegir a la llista` envia els queviures que manquen directament a la llista de la compra.
  - **[`modules/calendari.py`](file:///e:/Dashboard/modules/calendari.py)**: Els menús setmanals confirmats es poden sincronitzar com a esdeveniments d'agenda familiar.
  - **Menú Superior `Editar > 📂 Arxius JSON`**: Accés per revisar el perfil nutricional i eines a `core/config.json`.

---

### 6.2 Agenda i Calendari Familiar (`modules/calendari.py`, `core/calendar_manager.py`)
Mòdul central de coordinació temporal, esdeveniments, cites mèdiques, compromisos laborals i rutines familiars de la llar. Integra sincronització bidireccional iCal amb Google Calendar, graella interactiva mensual responsive estil Google Calendar, vista d'agenda cronològica, control d'acompliment en 1 clic (Fet / No Fet), creació ràpida intel·ligent mitjançant processament de llenguatge natural i disseny ultra-compacte d'una sola línia horitzontal adaptat a telèfons mòbils.

#### A. Arquitectura del Calendari i Fonts de Dades
El mòdul articula la informació temporal connectant bases de dades remotes a Supabase, memòries cau locals i feeds de tercers:
1. **Taules a Supabase (PostgreSQL)**:
   - `data/events.json` (Config ID 3): Dipòsit centralitzat d'esdeveniments manuals de la família i estats d'acompliment (`id`, `titol`, `data_inici`, `data_fi`, `hora_inici`, `hora_fi`, `tot_el_dia`, `categoria`, `membre`, `lloc`, `notes`, `status_fet`, `uid_ical`).
   - `data/feeds_cache.json` (Config ID 4): Memòria cau persistent de subscripcions iCal externes (Google Calendar personals d'Enric, Isabel, etc.).
2. **Configuració de Membres i Colors (`core/config.json` - Config ID 2)**:
   - Defineix els membres de la unitat familiar i assigna una paleta de colors única a cadascun per identificar a l'instant qui té cada compromís a la graella.
3. **Mecanisme de Desduplicació i Canonicitat (`core/calendar_manager.py`)**:
   - Algoritme `deduplicate_events` basat en empremta hash i UID iCal que impedeix duplicitats per concurrència de feeds i gestiona de forma canònica les excepcions de recurrències (`RECURRENCE-ID`).
   - **Triple Clau de Persistència**: Garanteix que si un esdeveniment prové d'un feed extern o es crea manualment, el seu estat (Fet / No Fet) queda ancorat permanentment a la base de dades sense perdre's en sincronitzar.

---

#### B. Cicle de Vida i Flux Operatiu d'un Esdeveniment

```mermaid
flowchart TD
    A["➕ Creació d'Esdeveniment (Manual o LLN Ràpid)"] --> B["💾 Desat a data/events.json (Supabase ID 3)"]
    C["🔄 Sincro Feeds iCal (Google Calendar)"] --> D["🔍 Desduplicació i Cache a data/feeds_cache.json"]
    B --> E["📅 Renderització a la Graella Mensual o Llista Agenda"]
    D --> E
    E --> F["🖱️ Clic a Casella de Dia -> Panell de Detalls"]
    F --> G{"Acció d'Acompliment"}
    G -- "✅ Fet" --> H["🟢 Estat FET: Fons Maragda, Prefix ✅ i Ratllat"]
    G -- "❌ No Fet" --> I["🔴 Estat CANCEL·LAT: Fons Vermell, Prefix ❌"]
    G -- "Pendent" --> J["⚪ Estat Normal de Calendari"]
```

- **Pas 1: Ingesta del Compromís**: L'usuari crea l'esdeveniment emplenant el formulari complet o teclejant una instrucció ràpida en llenguatge natural.
- **Pas 2: Fusió de Feeds**: El motor fusiona els esdeveniments manuals amb els calendaris externs de Google Calendar, netejant duplicats.
- **Pas 3: Visualització Personalitzada**: Es pinta la graella mensual o la llista cronològica aplicant els colors corporatius de cada membre familiar.
- **Pas 4: Consulta del Dia**: En fer clic sobre qualsevol casella de la graella, es despleguen a sota tots els seus esdeveniments en targetes interactives.
- **Pas 5: Resolució en 1 Clic**: L'usuari marca si s'ha fet o no es pot fer mitjançant els botons verds i vermells de resolució immediata.

---

#### C. Detall Exhaustiu de les Vistes i Controls Interactius

El mòdul disposa d'un comandament superior unificat i dues vistes principals commutables mitjançant `st.radio`:

---

##### 6.2.1 Comandament Superior d'Accions i Navegació Temporal

1. **Barra d'Eines Principal**:
   - **Botó `➕ Nou` (`btn_open_new_ev`, `type="primary"`)**: Desplega el panell d'alta per enregistrar un nou esdeveniment o cita.
   - **Botó `🔄 Sincro` (`btn_sync_feeds`)**: Força la descàrrega i sincronització immediata dels feeds iCal de Google Calendar, actualitzant `data/feeds_cache.json`.
   - **Navegació de Mesos**:
     - Botó `◀` (`cal_prev_month`): Retrocedeix al mes anterior.
     - Botó `Avui` (`cal_btn_today`): Retorna immediatament al mes i dia actuals.
     - Botó `▶` (`cal_next_month`): Avança al mes següent.
   - **Títol Dinàmic**: Retola el mes en català i l'any actiu en tipografia destacada *(Exemple: `📅 Octubre 2026`)*.
2. **Selector de Mode de Vista (`st.radio`)**:
   - Ràdio horitzontal compacte per alternar entre **`📅 Calendari` (Vista Graella)** i **`📋 Agenda / Llista` (Vista Cronològica)**, memoritzant la preferència a `st.session_state.cal_view_mode`.

---

##### 6.2.2 Formulari d'Alta d'Esdeveniments (`st.tabs`)

En prémer `➕ Nou`, es desplega un panell organitzat en dues pestanyes de creació:

1. **Pestanya `⚡ Creació ràpida intel·ligent`**:
   - Camp de text lliure preparat per processar llenguatge natural.
   - L'usuari pot escriure frases quotidianes *(Exemple: "Dilluns que ve a les 10h dentista de l'Enric a Girona")*.
   - **Parser Intel·ligent**: Descompon la frase, extreu automàticament la data, l'hora d'inici, el membre familiar assignat i la categoria mèdica.
   - **Botó `⚡ Crear ràpidament` (`type="primary"`)**: Valida l'extracció i desa l'esdeveniment a l'instant.
2. **Pestanya `📝 Formulari complet`**:
   - **Camp `Títol de l'esdeveniment`**: Descripció de l'acte o cita.
   - **Selector `Membre familiar`**: Desplegable per assignar a Enric, Isabel o `Tothom`.
   - **Casella `Tot el dia`**: Deshabilita la selecció d'hores per a festius o esdeveniments de jornada completa.
   - **Selectors de Data i Hora**: `Data d'inici`, `Data de finalització`, `Hora d'inici` i `Hora de finalització`.
   - **Selector `Categoria`**: Desplegable amb codi visual per a: `Metge`, `Feina`, `Oci / Social`, `Llar`, `Aniversari`, `Reunió`, `Esport`, `Altres`.
   - **Camp `Lloc / Ubicació`**: Adreça o centre on té lloc la cita.
   - **Camp `Notes / Descripció`**: Instruccions, documents necessaris o observacions.
   - **Botó `💾 Desar Esdeveniment`**: Insereix el registre a `data/events.json` i actualitza Supabase ID 3.
   - **Botó `❌ Cancel·lar`**: Tanca el panell sense desar canvis.

---

##### 6.2.3 Vista 1: `📅 Calendari` (Graella Mensual Estil Google Calendar)

La vista visual per excel·lència de l'agenda domèstica:

1. **Graella de 7 Columnes (Dilluns a Diumenge)**:
   - Capçaleres amb els dies de la setmana en català (*Dl, Dt, Dc, Dj, Dv, Ds, Dg*).
   - **Caselles de Dia Interactives**:
     - Vores suaus amb efecte hover en passar el cursor.
     - Indicador numèric de dia al cantó superior.
     - **Ressaltat Especial d'Avui**: La casella del dia en curs compta amb una vora blava brillant vibrant (`#38bdf8`) i fons il·luminat per identificar la jornada d'un sol cop d'ull.
   - **Pastilles d'Esdeveniments**:
     - Petites càpsules de color dins de cada casella que mostren l'hora i el títol del compromís.
     - El color de la càpsula identifica el membre familiar associat (segons `core/config.json`).
     - Recompte numèric si un dia té més esdeveniments dels que caben visualment a la casella.
2. **Panell de Gestió del Dia Seleccionat (Sub-graella)**:
   - En fer clic a qualsevol dia de la graella, aquest queda marcat amb una vora daurada i es desplega a sota la secció detallada **`🗓️ Esdeveniments per al dia DD/MM/YYYY`**:
     - Botó **`➕ Nou Esdeveniment per a aquest dia`**: Obre el formulari preomplint automàticament la data seleccionada.
     - **Targetes Detallades d'Esdeveniments**: Targetes àmplies amb l'hora, títol, membre, categoria, ubicació i el conjunt de botons d'acció ràpida.

---

##### 6.2.4 Vista 2: `📋 Agenda / Llista` (Llistat Cronològic Continu)

Ideal per consultar la planificació setmanal o mensual com una agenda contínua:

1. **Agrupació Seqüencial per Dates**:
   - Els esdeveniments es presenten ordenats cronològicament dia a dia de forma descendent.
   - Capçalera per a cada data indicant el dia de la setmana, número i mes.
2. **Targetes d'Agenda**:
   - Franja horària (ex: `09:30 - 10:30` o `Tot el dia`).
   - Insígnia de categoria i identificador de la persona responsable.
   - Accés complet als botons d'acció de resolució, edició i eliminació.

---

##### 6.2.5 Sistema d'Acompliment Fet / No Fet i Disseny Mòbil en 1 Línia

Un dels punts més potents del mòdul és el control d'estat immediat de qualsevol compromís:

1. **Botons d'Acció de Resolució**:
   - **Botó `✅` / `✔️` (Fet / Completat)**:
     - En prémer-lo, l'esdeveniment s'il·lumina en color verd maragda sòlid (`#10b981`).
     - S'afegeix el prefix `✅ ` al títol, es ratlla el text i es mostra la insígnia destacada `FET`.
     - Si es torna a prémer, es desmarca tornant a l'estat pendent original.
   - **Botó `❌` / `✖️` (No fet / Cancel·lat)**:
     - En prémer-lo, l'esdeveniment s'il·lumina en color vermell coral sòlid (`#ef4444`).
     - S'afegeix el prefix `❌ `, es ratlla el text i es mostra la insígnia `NO FET`.
     - Permet documentar cites cancel·lades o tasques no realitzades sense haver d'esborrar el registre de l'historial.
   - **Botó `✏️` (Modificar)**: Obre el formulari per editar el títol, horaris, membre o categoria.
   - **Botó `🗑️` (Esborrar)**: Elimina l'esdeveniment definitivament de la base de dades.
2. **Arquitectura CSS Avançada Mòbil en 1 Sola Línia (`:has(.cal-action-btn)`)**:
   - Per evitar que els 4 botons d'acció (`✅`, `❌`, `✏️`, `🗑️`) s'apilin verticalment a les pantalles estretes dels telèfons intel·ligents, s'ha programat una regla CSS Flexbox específica:
     ```css
     div[data-testid="stHorizontalBlock"]:has(.cal-action-btn) {
         flex-direction: row !important;
         flex-wrap: nowrap !important;
         align-items: center !important;
         gap: 4px !important;
     }
     ```
   - Garanteix que tota la botonera de control romangui sempre neta, compacta i accessible en una sola fila horitzontal des de qualsevol dispositiu mòbil.

---

#### D. Navegació Dinàmica i Enllaços amb Altres Mòduls
- **Navegació per Paràmetres URL (`st.query_params`)**:
  - `?tab=calendari` o `?mode=grid`: Obre la vista de graella mensual.
  - `?mode=agenda`: Condueix directament a la llista cronològica.
- **Interconnexions amb la Resta del Sistema**:
  - **[`modules/manteniment.py`](file:///e:/Dashboard/modules/manteniment.py)**: Les tasques de manteniment domèstic marcades amb `send_to_calendar` es reflecteixen automàticament a l'agenda familiar amb la icona `🛠️`.
  - **[`modules/menjar.py`](file:///e:/Dashboard/modules/menjar.py)**: Els menús setmanals es poden projectar a l'agenda com a referència dels àpats de la llar.
  - **[`modules/medicacio.py`](file:///e:/Dashboard/modules/medicacio.py)**: Els tractaments mèdics i pautes temporals sincronitzen alertes horàries a l'agenda.
  - **Menú Superior `Editar > 📂 Arxius JSON`**: Accés directe per consultar o restaurar `data/events.json` i `data/feeds_cache.json`.

---

### 6.3 Control de Medicació (`modules/medicacio.py`)
Mòdul de vigilància de la salut, supervisió de pautes farmacològiques de familiars i persones tutelades, registre de preses diàries en temps real amb comprovació d'adherència terapèutica i injecció automàtica d'alarmes mèdiques a Google Calendar mitjançant compte de servei o fitxers d'exportació iCal (.ics).

#### A. Arquitectura Farmacèutica i Fonts de Dades
El mòdul combina persistència al núvol a Supabase, integració d'APIs de Google Cloud i el perfil sanitari familiar:
1. **Taules a Supabase (PostgreSQL)**:
   - `data/medication_plans.json` (Config ID 5): Registre centralitzat de plans mèdics actius i històrics (`id`, `patient_name`, `patient_type`, `medication_name`, `dosage`, `instructions`, `frequency_type`, `times`, `start_date`, `duration_days`, `calendar_id`, `gcal_synced`, `events`).
2. **Configuració de Pacients (`core/config.json` - Config ID 2)**:
   - Catàleg de membres de la llar i persones tutelades subjectes a supervisió mèdica (nom, tipus de pacient, correus electrònics associats).
3. **Google Calendar API & Service Account (`core/google_credentials.json`)**:
   - Pont d'integració oficial amb Google Cloud que permet injectar automàticament centenars de preses mèdiques als calendaris dels telèfons intel·ligents dels pacients amb notificacions i alertes sonores sense intervenció manual.
   - **Mode Fallback Universal (.ICS)**: Si no es disposa de compte de servei, el mòdul genera paquets de calendari descarregables en format estàndard RFC 5545 (`.ics`) per importar a qualsevol dispositiu Apple, Android o Windows.

---

#### B. Cicle de Vida i Flux Operatiu de Medicació

```mermaid
flowchart TD
    A["➕ Prescripció / Alta de Pla (Fàrmac, Dosi, Hores)"] --> B["🚀 Injecció d'Alarmes a Google Calendar API (o .ICS)"]
    B --> C["💾 Persistència a data/medication_plans.json (ID 5)"]
    C --> D["📅 Supervisió a Preses d'Avui (Filtre per Pacient)"]
    D --> E{"Estat de la Presa"}
    E -- "Dins de termini" --> F["⏰ PENDENT (Badge Groc)"]
    E -- "Més d'1h de retard" --> G["⚠️ RETARD (Badge Vermell)"]
    D --> H["✅ Clic a 'Prendre': Confirmació de Presa"]
    H --> I["🟢 PRESA CONFIRMADA (Hora exacta de consum)"]
    I --> J["📊 Recàlcul d'Adherència Terapèutica (%)"]
```

- **Pas 1: Alta del Tractament**: Es defineix el pacient, fàrmac, dosificació, pauta horària (ex: cada 8h, cada 12h, personalitzada) i durada del tractament.
- **Pas 2: Injecció de Calendari**: El sistema calcula totes les preses individuals i les injecta directament al calendari de Google de la persona amb alarmes al seu mòbil.
- **Pas 3: Supervisió en Temps Real**: A la pestanya de preses d'avui es monitoritza cada dosi amb codis de color (pendent, retardada o confirmada).
- **Pas 4: Confirmació en 1 Clic**: El pacient o cuidador prem `✅ Prendre`; el sistema grava l'hora exacta de la presa (`confirmed_at`) i recalcula l'adherència.

---

#### C. Detall Exhaustiu de les 4 Pestanyes de la Interfície Gràfica

El mòdul s'estructura en 4 pestanyes operatives mitjançant `st.tabs` amb suport per a paràmetres URL (`?tab=...`):

---

##### 6.3.1 Pestanya 1: `📅 Preses d'Avui & Supervisió` (Panell Diari de Control)

La pantalla operativa d'administració i comprovació de preses de la jornada:

1. **Capçalera i Filtre per Pacient**:
   - Títol dinàmic amb la data d'avui *(Exemple: `🕒 Pauta de Preses per a Avui (28/10/2026)`)*.
   - **Desplegable `Filtrar per persona`**: Permet veure els medicaments de tota la família alhora (`Tots els pacients`) o centrar-se en un pacient concret (ex: Enric, Persona tutelada).
2. **Targetes Interactives de Presa**:
   - Cada presa del dia es presenta en una targeta visual dividida en 3 blocs:
     - **Caixa Horària (`med-time-box`)**: Caixa estilitzada a l'esquerra que destaca l'hora exacta de la dosi en gran (ex: `08:00`, `14:00`, `21:00`).
     - **Informació del Fàrmac**: Nom del medicament amb dosi *(Ex: `💊 Paracetamol (1g)`)*, pacient destinatari, tipus de pacient i instruccions mèdiques (ex: *Prendre després de dinar amb un got d'aigua*).
     - **Badges Semafòrics d'Estat**:
       - 🟢 **`✅ PRESA CONFIRMADA (a les 14:12)`**: Fons verd amb l'hora exacta en què es va prendre la pastilla.
       - 🔴 **`⚠️ RETARD (>1h)`**: Fons vermell d'alerta si ha passat més d'una hora de l'hora pautada sense confirmació.
       - 🟡 **`⏰ PENDENT`**: Fons groc per a les preses futures del dia.
3. **Accions Ràpides en 1 Clic**:
   - **Botó `✅ Prendre` / `↩️ Desfer`**: Commuta a l'instant l'estat de la dosi (`toggle_intake_manual`). Si es confirma, queda registrat; si s'ha premut per error, el botó permet desfer la confirmació.
   - **Botó `📅 GCal`**: Enllaç directe que obre l'esdeveniment a l'aplicació web o mòbil de Google Calendar.

---

##### 6.3.2 Pestanya 2: `➕ Crear Nou Pla de Medicació` (Programador de Tractaments)

Formulari per donar d'alta una nova pauta mèdica temporal o crònica:

1. **Dades del Destinatari**:
   - **Selector `Pacient / Destinatari del pla *`**: Desplegable amb els familiars i tutelats del sistema.
   - **Camp `Correu de Google Calendar de destí`**: Adreça de Gmail del pacient on s'injectaran les alertes.
2. **Definició del Fàrmac i Posologia**:
   - **Camp `Nom del medicament *`**: Camp de text predictiu (ex: *Sintrom, Omeprazol, Ibuprofèn*).
   - **Camp `Dosi / Format`**: Especificació de càrrega (ex: *500mg, 1 comprimit, 1 sobre, 2 gotes*).
   - **Pauta / Freqüència (`FREQUENCY_PRESETS`)**:
     - Presets preconfigurats amb un sol clic:
       - *Cada 8 hores* (`08:00, 16:00, 00:00`)
       - *Cada 12 hores* (`08:00, 20:00`)
       - *1 cop al dia (Matí)* (`09:00`)
       - *1 cop al dia (Nit)* (`21:00`)
       - *Cada 6 hores* (`06:00, 12:00, 18:00, 00:00`)
       - *Personalitzat*: Habilita un camp per teclejar hores arbitràries separades per comes.
3. **Temporització del Tractament**:
   - **`Data d'inici`**: Selector de calendari.
   - **`Durada del tractament (dies)`**: Selector numèric (de 1 a 365 dies).
   - **`Instruccions / Pauta mèdica`**: Recomanacions de consum (amb menjars, en dejú, protecció gàstrica).
4. **Execució i Exportació**:
   - **Botó `🚀 Crear i Enviar a Google Calendar` (`type="primary"`)**: Genera totes les instàncies de presa i les envia per API directa al calendari de Google de la persona tutelada.
   - **Botó `📥 Descarregar fitxer .ICS del Pla`**: Genera i descarrega a l'ordinador el paquet `.ics` per a dispositius sense connexió a compte de servei.

---

##### 6.3.3 Pestanya 3: `📋 Historial de Plans Actius i Adherència` (Seguiment Clínic)

Supervisió continuada del compliment dels tractaments mèdics de la família:

1. **Acordions per Medicament i Pacient (`st.expander`)**:
   - Cada tractament es presenta en un acordió que retola en temps real el recompte de preses i l'adherència:
     *(Exemple: `💊 Amoxicil·lina · 👤 Isabel (19/21 preses realitzades · 90%)`)*.
2. **Mètriques d'Adherència Terapèutica**:
   - **Barra de Progrés (`st.progress`)**: Proporció visual del compliment del tractament.
   - **Percentatge d'Adherència**: Indicador verd amb la taxa de compliment real de la pauta.
3. **Fitxa de Condicions**:
   - Mostra dosi, freqüència d'hores, període de dates, adreça de Google Calendar i instruccions mèdiques.
4. **Botó `🗑️ Eliminar Pla`**:
   - Permet cancel·lar el tractament mèdic, eliminant el pla actiu i netejant la base de dades.

---

##### 6.3.4 Pestanya 4: `⚙️ Connexió Google Calendar API & Guia` (Configuració del Servei)

Panell d'administració tècnica de la passarel·la amb Google Cloud:

1. **Estat de la Connexió**:
   - 🟢 **Compte de Servei Connectat**: Mostra l'adreça del compte de servei actiu (ex: `service-account@dashboard-familiar.iam.gserviceaccount.com`).
   - 🟡 **Mode Manual / Fallback**: Indica que el compte de servei no està configurat i que s'està utilitzant el mode d'enllaços web directes i fitxers `.ics`.
2. **Guia d'Enllaç de Calendaris per a Persones Tutelades**:
   - Procediment oficial de 5 passos per compartir el calendari de Google d'un familiar amb el compte de servei del Dashboard amb permisos d'edició.
3. **Instruccions de Configuració Inicial de Google Cloud Console**:
   - Explicació pas a pas per descarregar les credencials JSON gratuïtes a `core/google_credentials.json`.

---

#### D. Navegació Dinàmica i Enllaços amb Altres Mòduls
- **Navegació per Paràmetres URL (`st.query_params`)**:
  - `?tab=avui`: Obre la pauta diària de preses.
  - `?tab=nou`: Desplega el programador de nous tractaments.
  - `?tab=plans`: Condueix a l'historial i mètriques d'adherència.
  - `?tab=config`: Mostra l'estat de la Google Calendar API.
- **Interconnexions amb la Resta del Sistema**:
  - **[`modules/calendari.py`](file:///e:/Dashboard/modules/calendari.py)**: Les preses de medicació es poden visualitzar a l'agenda familiar sincronitzada amb la categoria mèdica.
  - **[`core/alerts.py`](file:///e:/Dashboard/core/alerts.py)**: Les dosis amb retard superior a una hora generen notificacions d'urgència a la campaneta de la barra superior (`🔔`).
  - **Menú Superior `Editar > 📂 Arxius JSON`**: Accés per inspeccionar o restaurar `data/medication_plans.json`.

---

### 6.4 Seguretat i Domòtica (`modules/seguretat.py`, `modules/domotica.py`)
Mòduls complementaris de protecció física de la llar, videovigilància, integració amb sistemes domòtics intel·ligents (Home Assistant) i control d'accessos de la casa.

#### A. Arquitectura i Estat Actual d'Implementació
1. **Model Modular de Connexió**:
   - Ambdós mòduls estan desacoblats estructuralment a la carpeta `modules/`, connectats al router principal [`app.py`](file:///e:/Dashboard/app.py) i governats pel selector de visibilitat de mòduls d'administració ([`modules/admin.py`](file:///e:/Dashboard/modules/admin.py)).
   - Actualment actuen com a **mòduls d'enllaç i panell de destí (Landing / Stubs)** amb capçalera corporativa dinàmica (`render_header_with_avatar`), preparats per a la connexió d'APIs locals.
2. **Especificació d'Integració Domòtica (`modules/domotica.py`)**:
   - **Passarel·la Home Assistant (REST API / WebSocket)**: Dissenyat per connectar amb la instància local de Home Assistant de la llar mitjançant token de llarga durada (*Long-Lived Access Token*).
   - **Control de Climatització i Acumuladors**: Connectat lògicament amb [`modules/llum_aigua.py`](file:///e:/Dashboard/modules/llum_aigua.py) per actuar sobre relés intel·ligents (Shelly / Sonoff) i encendre els acumuladors de calor en les hores vall més barates del PVPC.
   - **Monitorització de Sensors Ambientals**: Lectura de termòstats, humitat, sensors de presència i consum elèctric en temps real.
3. **Especificació de Seguretat i Videovigilància (`modules/seguretat.py`)**:
   - **Feeds RTSP / WebRTC**: Receptor per a càmeres IP domèstiques compatibles amb ONVIF / RTSP (vigilància d'accessos exteriors, jardí i garatge).
   - **Estat d'Alarma i Sensors d'Obertura**: Supervisió de l'estat d'armat de l'alarma de la llar i comprovació d'obertura de portes i finestres abans de sortir de casa.

#### B. Administració i Visibilitat des de la Barra Superior
- Des de **`⚙️ Administració > Visibilitat de Mòduls`**, l'usuari pot activar o ocultar aquestes icones de la pàgina principal d'inici amb un sol clic, mantenint el Dashboard adaptat a les necessitats reals de la família en cada moment.

---

## 7. Mòduls de Prioritat 5: Administració, Nucli i Serveis Transversals

---

### 7.1 Administració i Configuració Global (`modules/admin.py`, `core/config_manager.py`)

#### A. Ajustos, Fonts de Dades, Taules i Configuració
1. **Fitxer Central de Configuració (`core/config.json`)**:
   - Tota la parametrització de l'aplicació es governa a través de [`core/config_manager.py`](file:///e:/Dashboard/core/config_manager.py), que carrega i desa de manera atòmica el fitxer JSON [`core/config.json`](file:///e:/Dashboard/core/config.json).
   - Estructura clau de dades:
     - `admin`: Nom, correu electrònic, telèfon, avatar (emoji o URL) i hash/PIN de seguretat d'accés mestre.
     - `titol_casa`: Text del rètol superior (ex: *"XIQUIHOUSE"*), subtítol, color hexadecimal de la capçalera (`#f39c12`), tipografia i mides.
     - `familia`: Array d'objectes amb el perfil complet de cada membre: `{id, nom, data_naixement, rol, color, telefon, alergies, vetos, plats_favorits, present}`.
     - `menjar`: Paràmetres dietètics globals, ràtios calòriques per àpat, catàleg d'eines actives i estris disponibles (`cataleg_eines`).
     - `periferics`: Paràmetres del maquinari de la llar, incloent impressora tèrmica de tiquets (`nom_controlador`, `metode_impressio`, `salts_linia_tall`, `tall_automatic`) i paràmetres de l'escàner USB (motor WinRT / WIA, resolució DPI).
     - `icones_actives`: Mapa booleà que habilita o oculta cadascuna de les targetes interactives del tauler d'inici (`landing`).
     - `tutelats`: Llistat de persones o familiars sota tutela legal o gestió delegada amb comptes associats.
     - `bancs`: Catàleg d'entitats bancàries de la llar amb colors corporatius i identificadors per a filtratge ràpid.
     - `tema`: Selector de paleta visual (*Fosc* / *Clar*).
     - `idioma`: Idioma predeterminat de la interfície (*ca* / *es*).
2. **Neteja d'Estat i Resolució d'Inconsistències de Sessió**:
   - Per evitar que els widgets de Streamlit mantinguin claus obsoletes en memòria cau després de desar o navegar entre seccions, [`modules/admin.py`](file:///e:/Dashboard/modules/admin.py) incorpora `_clear_all_admin_widget_keys()` i `_clear_section_session_keys(prefix)`, encarregades d'eliminar de `st.session_state` totes les claus temporals de formularis (`f_` per a família, `t_` per a tutelats, `b_` per a bancs).
   - Cada desat sincronitza el disc i invoca immediatament `st.cache_data.clear()` per refrescar la informació en tots els mòduls dependents.

---

#### B. Flux de Treball del Mòdul d'Administració

```mermaid
flowchart TD
    A["⚙️ Menú Administració"] --> B["Cerca o Selecció de Secció (12 Panells)"]
    
    B --> C1["👤 Administrador"]
    B --> C2["🏷️ Títol Casa i Accés Directe"]
    B --> C3["👨‍👩‍👧‍👦 Perfils Familiars i Dietes"]
    B --> C4["🍽️ Eines de Cuina i Nutrició"]
    B --> C5["🔌 Perifèrics (Impressora / Escàner)"]
    B --> C6["🧪 Laboratori IA (Harness)"]
    B --> C7["🔘 Visibilitat Mòduls d'Inici"]
    B --> C8["🤝 Tutelats, Bancs, Tema, Idioma"]
    
    C1 --> D["Edició Paràmetres / PIN"]
    C2 --> E["Actualització Windows Shortcut (.lnk)"]
    C3 --> F["Validació Data Naixement (Edat automàtica)"]
    C4 --> G["Càrrega Imatge Base64 i Modal"]
    C5 --> H["Comprovació Drivers Win32Print / WIA"]
    C7 --> I["Commutadors On/Off de Mòduls"]
    
    D & E & F & G & H & I --> J["💾 Botó Desar Configuració"]
    J --> K["Escritura Atòmica a core/config.json"]
    K --> L["Neteja Claus Sessió (_clear_section_session_keys)"]
    L --> M["st.cache_data.clear() i Notificació d'Èxit"]
```

---

#### C. Detall Exhaustiu de les 13 Seccions de Configuració

##### 1. Secció 👤 Administrador
- **Capçalera Dinàmica i Avatar**: Targeta corporativa d'estil Chrome Settings que reflecteix el nom complet de l'administrador, rol del sistema (`admin`), correu electrònic i avatar circular amb fons degradat.
- **Formulari de Dades Personals**:
  - `Nom de l'Administrador`: Camp de text editable vinculat a la sessió activa.
  - `Correu Electrònic`: Text d'avís per a notificacions administratives.
  - `Telèfon de Contacte`: Per a integracions de missatgeria o avisos d'urgència.
  - `Selector d'Avatar`: Tria d'emojis o càrrega d'imatge local.
- **PIN Mestre de Seguretat**:
  - Camp de contrasenya/PIN numèric per desbloquejar accions de màxima sensibilitat (esborrat massiu de registres, accés al gestor de bases de dades des d'usuaris convidats o configuració de passarel·les bancàries).

##### 2. Secció 🏷️ Títol de la casa
- **Personalització Visual de la Marca de la Llar**:
  - `Text del Títol Principal`: Camp de text (per defecte *"XIQUIHOUSE"*).
  - `Subtítol o Lema`: Text secundari (ex: *"Gestió Integral de la Llar"*).
  - `Color Principal del Rètol`: Color picker interactiu per definir el to hexadecimal (per defecte `#f39c12`) que tenyeix les capçaleres de tots els mòduls.
  - `Mida i Estil de Tipografia`: Selector de grandària (normal, gran, extra gran).
  - `Caixa de Vista Prèvia en Temps Real`: Panell delimitat amb vores discontínues que renderitza immediatament el text i el color escollits tal com es visualitzaran a la pantalla d'inici.
- **Actualitzador de l'Accés Directe d'Escriptori de Windows (`_update_desktop_shortcut`)**:
  - Quan es modifica el títol de la casa, l'aplicació executa un script en segon pla que reanomena i reconfigura automàticament l'accés directe `.lnk` ubicat a l'escriptori de Windows de l'ordinador amfitrió per mantenir la coherència de marca del sistema.

##### 3. Secció 🏡 Estances de la casa
- **Model d'Estances i Espais Domèstics (`core/config_manager.py` / `DEFAULT_ESTANCES`)**:
  - Centralitza la definició de les habitacions, zones i estances de la llar a `app_config` (ID 2 a Supabase i `core/config.json` local).
  - **Regles de Negoci i Blindatge de Permanència**:
    - **Menjador / Sala d'estar** (`menjador`): Estança obligatòria de la llar; bloquejada permanentment contra eliminació (`🔒`).
    - **Cuina** (`cuina`): Estança essencial de la llar; bloquejada permanentment contra eliminació (`🔒`).
    - **Bany** (`bany`): Com a mínim cal 1 bany a la llar. Si només queda 1 bany actiu, el botó d'eliminar es desactiva automàticament (`🔒 Únic bany (mínim 1)`). Si se n'afegeixen més (ex: "Bany suite", "Lavabo de cortesia"), els banys addicionals es poden esborrar lliurement sempre que en quedi un.
    - **Habitació** (`habitacio`): Com a mínim cal 1 habitació a la llar. Si només queda 1 habitació activa, el botó d'eliminar es desactiva automàticament (`🔒 Única habitació (mínim 1)`). Si se n'afegeixen més (ex: "Habitació 2", "Habitació convidats"), les habitacions addicionals es poden esborrar lliurement sempre que en quedi una.
    - **Estances i Espais Addicionals lliures** (`altres`): L'usuari pot afegir qualsevol altre espai domèstic sense restriccions.
- **Elements de Domòtica i IoT per Estança (`iot_elements`)**:
  - Cada estança pot allotjar una llista dinàmica de dispositius intel·ligents (`iot_elements`), cadascun amb identificador únic, nom editable, categoria/tipus (`IOT_CATEGORIES`), protocol/marca (`IOT_PROTOCOLS`: Wi-Fi, Zigbee, Shelly, Tuya, Sonoff, Matter, Bluetooth, Z-Wave, etc.), entitat o IP (ex: `sensor.pou`, `switch.bomba_pou`) i icona emoji.
  - **Manteniment en Viu (Modificació, Alta i Eliminació)**:
    - Acordió desplegable per habitació amb botons ràpids d'1-clic: `🌡️ + Temp`, `💡 + Llum`, `🔌 + Endoll`, `🚰 + Aigua/Pou`, `🚪 + Porta/Finestra` i `⚙️ + Bomba/Relé`.
    - Formulari editable línia a línia que permet canviar la icona, el nom, la categoria, el protocol i la referència de xarxa en qualsevol moment, o eliminar dispositius obsolets.
    - Sincronització directa amb el botó global `💾 Desar Estances de la Casa` que preserva i consolida l'arbre complet d'habitacions i dispositius IoT tant en local (`config.json`) com al núvol (`app_config` a Supabase).
  - **Mòdul de Domòtica (`modules/domotica.py`)**:
    - Panell operatiu amb mètriques KPI del total de dispositius IoT instal·lats i resum d'estat organitzat per estances, amb enllaç directe per a la seva gestió.
- **Interfície d'Administració Interactiva (`modules/admin.py`)**:
  - **Botons Ràpids 1-Clic**: Targeta d'accés directe amb botons per afegir a l'instant `🛏️ + Habitació`, `🚿 + Bany`, `🌿 + Terrassa`, `🌳 + Jardí / Pati`, `🚗 + Garatge`, `📦 + Traster`, `💼 + Despatx / Estudi` i `🧺 + Safareig`.
  - **Formulari d'Estança Personalitzada**: Desplegable per definir nom propi, categoria (Habitació, Bany o Altres espais) i icona representativa d'un catàleg d'emojis domèstics.
  - **Llistat Dinàmic amb Edició en Línia**: Selector d'icona i camp de text per canviar el nom de qualsevol estança en viu, botó de recàrrega de valors desats (`🔄 Recarregar desats`) i botó de desat global (`💾 Desar Estances de la Casa`).
- **Integració amb Mòduls Operatius**:
  - **Projectes de Manteniment i Reformes (`modules/projectes_ui.py`)**: Tant el formulari d'alta de nous projectes (`_render_modal_nou_projecte`) com el formulari d'edició del projecte seleccionat (`_render_projecte_header`) obtenen dinàmicament el llistat desplegable d'ubicacions directament de `get_estances_casa()`, mantenint perfecta coherència entre la configuració global de la casa i els espais d'obra.

##### 4. Secció 👨‍👩‍👧‍👦 Família
- **Llistat de Membres Familiars**:
  - Cada membre es presenta en una targeta independent plegable (`st.expander`) o llista estructurada.
  - `Nom i Cognoms`: Identificador del familiar.
  - `Data de Naixement`: Format europeu estricte (`DD/MM/AAAA`).
  - `Càlcul Dinàmic d'Edat (`calcular_edat`)`: Funció algorísmica que processa dates en formats string o objecte datetime i calcula exactament els anys complerts tenint en compte mes i dia actuals.
  - `Rol Familiar`: Selector (Pare, Mare, Fill/a, Avi/àvia, Convidat).
  - `Color Identificador`: Color picker per al calendari d'agenda, torns de medicació i tasques de manteniment.
  - `Telèfon Mòbil`: Per a vinculació d'alertes personals.
  - `Al·lèrgies i Intol·leràncies Mèdiques`: Camp de text lliure (separat per comes) estrictament connectat amb el planificador de menús IA i el banc de proves Harness (tolerància 0%).
  - `Vetos Alimentaris Personals`: Aliments que el familiar no vol menjar (encara que no siguin al·lèrgies).
  - `Plats Comodí / Favorits`: Plats segurs d'emergència per substituir automàticament qualsevol àpat que contingui un veto.
  - `Commutador de Presència (`🟢 Present` vs `⚪ Fora`)`: Permet desactivar temporalment un membre quan està de viatge, de vacances o fora de casa perquè la generació de menús i compres no calculi racions innecessàries.
- **Accions i Modals de Família**:
  - `➕ Afegir Membre Familiar`: Formulari emergent per registrar nous integrants.
  - `🗑️ Esborrar Membre Familiar (`show_delete_family_member_dialog`)`: Modal de seguretat de Streamlit (`@st.dialog`) que sol·licita confirmació explícita abans d'eliminar el registre per evitar pèrdues accidentals.
  - `💾 Desar Canvis de Família`: Invoca `_on_save_family_members()`, purga les claus `f_` de la sessió i reescriu el fitxer de configuració.

##### 5. Secció 🍽️ Menús i Nutrició / 🍳 Eines de Cuina
- **Catàleg Visual d'Eines i Aparells de Cuina (`DEFAULT_CATALEG_EINES`)**:
  - Catàleg complet d'electrodomèstics i estris: Forn elèctric, Microones, Fregidora d'aire (*Airfryer*), Robot de cuina (Thermomix), Batedora de vas, Paella gran, Olla a pressió, Graella elèctrica, Vaporera, etc.
  - `Miniatures i Resolució d'Imatges (`_get_eina_foto_src`)`: Cerca intel·ligent a les carpetes locals del projecte (`imatges/Eines/`, `imatges/Productes/`, etc.) o fonts web remotes, convertint fitxers locals a fluxos segurs en Base64 (`data:image/png;base64,...`).
  - `Visor Modal d'Eines (`_render_eina_thumb_html`)`: Modal CSS pur amb etiquetes `<label>` i caixes ocultes que permet fer clic a la miniatura de 56x56 px per obrir un visor ampliat d'alta resolució amb descripció tècnica sense fer recàrrega de pàgina.
  - `Interruptors d'Activació (`_on_eina_change`)`: Permet marcar quins aparells estan realment disponibles a la cuina de la casa. El planificador de menús IA no proposarà mai receptes que requereixin eines apagades.
  - `Pujada d'Eines Personalitzades`: Formulari amb doble pestanya (`📁 Pujar fitxer PC/Mòbil` o `🔗 Enllaç URL`) per incorporar nous estris amb foto, nom i descripció.

##### 6. Secció 🔔 Alertes Globals
- **Configuració de Llindars de Notificació**:
  - `Avisos de Loteria i Sorteigs`: Dies d'antelació per a la caducitat de dècims.
  - `Marge d'Avisos de Manteniment`: Dies de preavís abans del venciment de tasques domèstiques recurrents.
  - `Avisos de Caducitat de Garanties`: Llindar d'avís en dies per a aparells i electrodomèstics de la llar.
  - `Visibilitat a la Campaneta`: Selectors per activar o silenciar categories d'alertes específiques al panell superior.

##### 7. Secció 🔌 Perifèrics (Impressora i Escàner)
- **Impressora Tèrmica de Tiquets (ESC/POS)**:
  - `Llistat de Controladors Detectats`: Detecció automàtica d'impressores locals de Windows mitjançant `win32print`.
  - `Controlador Seleccionat`: Selector del dispositiu (per defecte `BIXOLON_SRP275`).
  - `Mètode d'Impressió Preferit`: Radio button entre *RAW ESC/POS (Windows natiu local)* i *Impressió Web (HTML5/window.print())*.
  - `Salts de Línia de Marge`: Quantitat de salts buits (per defecte 6) abans de tallar perquè el text no quedi atrapat sota la guillotina.
  - `Tall de Paper Automàtic`: Interruptor per enviar la comanda ESC/POS `\x1dV\x00` en finalitzar.
  - `Botó d'Impressió de Prova`: Envia un tiquet curt de diagnòstic per verificar alimentació de paper i impressió de capçalera.
- **Escàner USB de Documents i Tiquets**:
  - `Motor d'Escaneig`: Selector entre el motor d'última generació WinRT natiu ([`scan_winrt.ps1`](file:///e:/Dashboard/scan_winrt.ps1)) o l'API clàssica WIA.
  - `Resolució d'Escaneig (DPI)`: 150 DPI (ràpid per a OCR) o 300 DPI (alta definició).
  - `Ruta de Destí`: Carpeta local predeterminada (`tickets/`).

##### 8. Secció 🧪 Laboratori IA (Harness)
- Accés directe als controls del banc de proves heurístic i informes d'avaluació de models (vegeu subapartat 7.2).

##### 9. Secció 🤝 Tutelats
- Gestió de registres de familiars sota tutela legal o gestió delegada, assignant comptes bancaris, límits de despesa i alertes administratives específiques.

##### 10. Secció 🏦 Bancs
- Gestió del catàleg d'entitats financeres de la llar (CaixaBank, BBVA, Santander, Revolut, etc.), codis de color identificatius i associació amb els comptes de [`modules/economic.py`](file:///e:/Dashboard/modules/economic.py).

##### 11. Secció 🎨 Aspecte i Tema
- Selector d'estil visual de l'aplicació entre tema **Fosc** (paleta fosca d'alt contrast amb fons `#0f172a` i targetes `#1e293b`) i tema **Clar** (estil corporatiu net amb fons blanc i vores suaus `#dadce0`).

##### 12. Secció 🔘 Icones pantalla d'inici (Visibilitat)
- Matriu d'interruptors (*toggles*) per activar o ocultar qualsevol de les targetes del menú principal (*Landing*):
  - `Compres i Rebost`, `Econòmic`, `Llum i Aigua`, `Cotxe`, `Manteniment`, `Menús i Cuina`, `Agenda`, `Medicació`, `Seguretat`, `Domòtica`, `Jocs / Oci`.
  - Desa instantàniament a `icones_actives` i reordena la graella del tauler.

##### 13. Secció 🌐 Idiomes
- Selector d'idioma de l'aplicació (*Català* / *Castellà*) amb diccionari de cadenes transversals a [`core/config_manager.py`](file:///e:/Dashboard/core/config_manager.py).

---

#### D. Interfície Gràfica, Elements Interactius i Enllaços Intermòdul
1. **Disseny d'Interfície Chrome Settings**:
   - Estructura a dues columnes (`col_menu: 3`, `col_body: 7`): barra lateral d'accés ràpid amb cercador en viu de seccions a l'esquerra, i àrea de formulari amb targetes arrodonides a la dreta.
2. **Sistema de Missatges Flash (`_render_flash_message`)**:
   - En desar dades satisfactòriament, es genera un banner verd temporal a la part superior del formulari (`st.session_state["flash_success"]`) que confirma l'operació i s'esvaeix al següent cicle.
3. **Connexions Intermòdul**:
   - **Compres (`modules/compres.py`)**: Rep els paràmetres de l'escàner i la impressora de tiquets.
   - **Menús (`modules/menjar.py`)**: Llegeix els membres presents, al·lèrgies, vetos, plats favorits i el catàleg d'eines actives.
   - **Agenda (`modules/calendari.py`) i Medicació (`modules/medicacio.py`)**: Utilitzen els membres familiars i els seus colors assignats per a filtres i avatars.
   - **Landing (`modules/dashboard.py`)**: Governa la renderització dels botons segons el mapa `icones_actives`.

---

### 7.2 Laboratori IA - Harness (`core/harness.py`)

#### A. Arquitectura d'Avaluació Determinista i Dades de Prova
1. **Propòsit del Mòdul**:
   - El banc de proves **Harness** ([`core/harness.py`](file:///e:/Dashboard/core/harness.py)) és un entorn de proves automàtiques dissenyat per avaluar rigorosament la qualitat, fidelitat i seguretat dels models d'intel·ligència artificial (Gemini 2.5 Flash, Gemini 3.8 Flash, DeepSeek, etc.) abans de desplegar-los per a la generació de menús familiars.
2. **Bateria de Casos de Prova (`data/harness_menu_cases.json`)**:
   - Conté escenaris extrems de prova dissenyats expressament per estressar el model:
     - Casos amb múltiples membres amb al·lèrgies severes creuades (celiaquia, intolerància a la lactosa, al·lèrgia als fruits secs).
     - Escenaris amb múltiples vetos alimentaris personals i exigència de plats comodí específics.
     - Restriccions d'eines (ex: cuines sense forn ni fregidora d'aire).
     - Rebosts amb estoc limitat que cal consumir amb caràcter prioritari.
3. **Cas en Viu de la Família (`get_live_family_test_case`)**:
   - A més dels casos sintètics, el banc de proves extreu automàticament la configuració real vigent de la família i el catàleg d'eines des de [`core/config.json`](file:///e:/Dashboard/core/config.json) per avaluar com es comportaria el model amb la situació domèstica d'avui mateix.

---

#### B. Flux de Treball del Banc de Proves Harness

```mermaid
flowchart TD
    A["🧪 Llançament Suite Harness"] --> B["Carrega Casos Sintètics + Cas Familiar en Viu"]
    B --> C["Crea Fil Asíncron en Segon Pla (_harness_background_worker)"]
    C --> D["Monitoratge d'Estat a data/harness_status.json"]
    
    subgraph ExecucioPerCas ["Bucle d'Avaluació per Cas"]
        D --> E["Construcció System Prompt amb Regles Familiars"]
        E --> F["Crida a la API del Model d'IA"]
        F --> G["Parseig i Sanejament de JSON (parse_and_clean_json)"]
        G --> H["Filtre de Seguretat Previ (netejar_termes_segurs)"]
        H --> I["8 Avaluadors Heurístics Deterministes"]
    end
    
    I --> J["Puntuació Global Ponderada (0 - 10)"]
    J --> K["Generació Informes: Text Pla (.txt) i Markdown"]
    K --> L["Presentació a la Interfície d'Usuari amb Taula Resum"]
```

---

#### C. Detall dels 8 Avaluadors Heurístics i Mètriques de Rendiment

1. **Seguretat d'Al·lèrgies Mèdiques (`grade_alergies`)**:
   - **Tolerància 0%**: Qualsevol presència d'un al·lergen prohibit en un àpat destinat al familiar afectat atorga immediatament un 0 en la prova.
   - **Filtre de Termes Segurs (`netejar_termes_segurs`)**: L'algorisme neteja prèviament qualificatius segurs com *"sense gluten"*, *"sense lactosa"*, *"apte per a celíacs"* o *"llet vegetal"* per evitar falsos positius en avaluar paraules clau com *"gluten"* o *"llet"*.
2. **Vetos Personals i Desdoblament (`grade_vetos_i_desdoblament`)**:
   - Verifica que cap membre rebi un aliment vetat. Si un aliment vetat apareix al menú general, avalua si el model ha desdoblat correctament l'àpat oferint l'alternativa del plat comodí registrat a la fitxa del familiar.
3. **Regles Dietètiques de la Llar (`grade_regles_llar`)**:
   - Verifica l'equilibri nutricional setmanal: presència de verdura diària, freqüència mínima de peix (almenys 2-3 cops per setmana), racions de llegums i limitació de carns vermelles o fregits.
4. **Anti-repetició d'Hidrats Consecutius (`grade_repeticions_hidrats`)**:
   - Penalitza la coincidència d'hidrats pesants en el mateix dia (ex: paella o pasta per dinar combinat amb pizza o arròs per sopar).
5. **Alineació amb Puntuacions d'Estrelles (`grade_puntuacions_estrelles`)**:
   - Comprova si el model prioritza les receptes amb 4 o 5 estrelles del catàleg històric de la casa enfront de plats amb valoracions baixes.
6. **Eines de Cuina i Forn (`grade_eines_i_forn`)**:
   - Avalua si les receptes proposades respecten el catàleg d'estris actius i penalitza si es programa un ús simultani o incompatible d'aparells (ex: demanar forn simultàniament a diferents temperatures).
7. **Aprofitament d'Estoc del Rebost (`grade_aprofitament_estoc`)**:
   - Premia les propostes que incorporen ingredients marcats com a *"consum preferent"* o amb sobreestoc al rebost i congelador de [`modules/compres.py`](file:///e:/Dashboard/modules/compres.py).
8. **Control Dietètic i Calòric (`grade_control_dietetic`)**:
   - Supervisa que l'aportació energètica s'ajusti als objectius de manteniment o pèrdua de pes definits per als membres de la casa.

---

#### D. Execució en Segon Pla, Monitorització i Generació d'Informes
- **Motor Asíncron (`_harness_background_worker`, `start_harness_suite_background`)**:
  - Les proves d'IA poden trigar entre 30 segons i 3 minuts segons la quantitat de casos. El motor llança un fil de segon pla (*threading*) que escriu el progrés en percentatge, el cas actiu i els registres a [`data/harness_status.json`](file:///e:/Dashboard/data/harness_status.json).
  - La interfície mostra una barra de progrés viva que es refresca sense bloquejar la navegació de l'usuari per altres mòduls.
- **Generador d'Informes en Text Pla (`generate_harness_txt_report`)**:
  - Produeix un fitxer de text estructurat descarregable amb diagnòstic pas a pas, temps de resposta de la API, tokens consumits, violacions detectades i recomanacions de millora del prompt.
- **Informe Markdown (`generate_harness_markdown_report`)**:
  - Renderitza una taula visual amb codi de colors (verd per a notes superiors a 8, groc entre 5 i 8, vermell per sota de 5) i resum gràfic de compliment per categoria.

---

### 7.3 Gestió de Bases de Dades i Sincronització Offline (`modules/bases_dades.py`, `modules/sincronitzacio.py`)

#### A. Gestor de Bases de Dades Supabase en Temps Real (`modules/bases_dades.py`)
1. **Accés i Permisos d'Accés**:
   - Accessible des del menú superior d'escriptori (*Eines > 🗄️ Bases de Dades*) o mitjançant el paràmetre URL `?db=nom_taula`.
   - Protegit per rol: només els usuaris amb rol `admin` o convidats amb PIN mestre poden visualitzar o modificar taules.
2. **Explorador Multitaula**:
   - Desplegable amb totes les taules relacionals de Supabase: `despeses`, `ingressos`, `compresSuper`, `carteraSuper`, `gasolina`, `kmCotxe`, `revisionsCotxe`, `hipoteca`, `limitsDespeses`, `pagadors`, `documentsLlar`, `mantenimentLlar`, `medicacio`, etc.
   - Detecta automàticament la clau primària (*Primary Key*) segons la matriu `PK_MAP` (`idPago`, `idIngres`, `IdCompra`, `idGasolina`, `idRuta`, `idTRCartera`, `id`).
3. **Editor de Dades Integrat (`st.data_editor`)**:
   - Permet afegir noves files al final de la graella, modificar qualsevol cel·la fent doble clic i seleccionar files per a la seva eliminació física a Supabase.
   - Commutador de seguretat `Ordenar pel més recent primer` per auditar immediatament les darreres transaccions registrades.
4. **Panell Desplegable de Filtres Ràpids (`🔍 Filtres`)**:
   - Detecta intel·ligentment el tipus de columnes del DataFrame actiu i genera filtres visuals adaptats:
     - Selectors de columna única: Banc, Forma de Pagament, Mes, Any, Categoria, Estat de Tiquet Pendent (`ticketPendent`).
     - Cerca per text lliure a Concepte o Article.
     - Filtratge per rang d'import monetari (`apply_import_filter`).
     - Botó `Netejar Filtres` per restaurar la vista completa de la taula amb un sol clic.

---

#### B. Sincronització Offline i Consolidació de Dades (`modules/sincronitzacio.py`)
1. **Arquitectura d'Operació Desconnectada**:
   - Si la connexió a Internet cau mentre s'introdueix una despesa, una ruta de cotxe o una compra, l'aplicació entra automàticament en mode desconnectat (*is_offline*).
   - Totes les peticions de mutació s'encapsulen com a objectes JSON atòmics i s'emmagatzemen a la cua local [`sync_queue.json`](file:///e:/Dashboard/sync_queue.json):
     - `INSERT`: Nova fila amb dades completes.
     - `INSERT_BULK`: Línies massives (ex: línies d'un tiquet de supermercat).
     - `UPDATE`: Nom de taula, clau primària, identificador i mapa de canvis.
     - `DELETE`: Identificador de la fila per eliminar.
2. **Panell de Gestió de la Cua**:
   - Si la cua conté operacions pendents, es mostra una taula informativa amb la data/hora de la modificació local, la taula afectada i el detall del canvi.
3. **Botons d'Acció**:
   - `🗑️ Netejar Cua (Descartar canvis locals)`: Esborra el fitxer `sync_queue.json` descartant les modificacions fetes fora de línia.
   - `🚀 Pujar Canvis a Supabase i Consolidar`: Itera sobre la cua executant cadascuna de les operacions mitjançant la instància de Supabase, informant del nombre d'accions completades amb èxit, gestionant possibles col·lisions i restaurant l'estat en línia.

---

#### C. Flux de Treball de Sincronització Offline

```mermaid
flowchart TD
    A["Mutació de Dades (Insert / Update / Delete)"] --> B{"Connexió Supabase Activa?"}
    
    B -- Sí --> C["Execució Immediata a Supabase"]
    B -- No / Error --> D["Enregistrament a la Cua Local (sync_queue.json)"]
    D --> E["Activació Mode Offline a la Interfície"]
    
    E --> F["Mòdul de Sincronització (modules/sincronitzacio.py)"]
    F --> G["Inspecció Visual de les Operacions Pendents"]
    
    G --> H{"Decisió de l'Usuari"}
    H -- Descartar --> I["🗑️ Netejar Cua (Elimina sync_queue.json)"]
    H -- Pujar --> J["🚀 Consolidar Canvis a Supabase"]
    
    J --> K["Processament per Lots (Insert / Bulk / Update / Delete)"]
    K --> L{"S'han produït errors?"}
    L -- No --> M["✅ Èxit: Buidatge de Cua i Restabliment Online"]
    L -- Sí --> N["⚠️ Alerta d'Errors Parcials i Conservació de Pendents"]
```

---

### 7.4 Sistema Global d'Alertes (`core/alerts.py`)

#### A. Arquitectura Transversal i Agregació d'Alertes Multimòdul
1. **Campaneta de Notificacions Persistent (`🔔`)**:
   - La campaneta d'alertes està present de forma unificada a la barra superior de navegació de l'aplicació i al tauler d'inici (*Landing*).
   - Mostra un distintiu numèric en temps real (*badge*) amb la suma d'avisos pendents que requereixen atenció.
2. **Optimització de Memòria i Rendiment**:
   - Per evitar consultes redundants a la base de dades, [`core/alerts.py`](file:///e:/Dashboard/core/alerts.py) aprofita directament els DataFrames actius ja presents a la memòria de sessió (`df_desp`, `df_km`, `df_limits`). Només si la sessió és verge invoca `load_dashboard_data`.
   - [`app.py`](file:///e:/Dashboard/app.py) manté una memòria cau de 60 segons sobre el recompte per mantenir la navegació fluida i sense latència.

---

#### B. Catàleg de Regles de Notificació i Semàfor de Severitat

| Tipus / Mòdul | Icona | Condició d'Activació | Nivell d'Alerta | Missatge Emetut |
|:---|:---:|:---|:---:|:---|
| **Cotxe (Oli)** | 🔧 | Kms restants per canvi d'oli $\le 0$ km | **Error (Vermell)** | *"Cal fer el canvi d'oli (previst als X km). Superat per Y km."* |
| **Cotxe (Oli)** | 🔧 | Kms restants per canvi d'oli $\le$ llindar d'avís | **Warning (Groc)** | *"Queden X km per al canvi d'oli (als Y km)."* |
| **Cotxe (Pneumàtics)** | 🛞 | Kms restants per canvi de rodes $\le$ llindar | **Warning / Error** | *"Revisar/canviar rodes: previst als X km (Y km restants)."* |
| **Cotxe (Inflat)** | 🛞 | Data d'inflat superada o dins del marge | **Warning / Error** | *"Inflat de rodes pendent des del DD/MM/AAAA o proper."* |
| **Cotxe (Nivells)** | 💧 | Data de revisió de líquids vençuda o pròxima | **Warning / Error** | *"Revisió de nivells de líquids (refrigerant/oli/frens) pendent."* |
| **Cotxe (ITV)** | 📋 | Caducitat de la ITV en menys de 30 dies | **Warning / Error** | *"Inspecció Tècnica de Vehicles (ITV) pendent de renovar."* |
| **Compres** | 🛒 | `ticketPendent == True` | **Warning (Groc)** | *"Hi ha tiquets de compra escanejats pendents de desglossar."* |
| **Manteniment** | 🏠 | Tasca domèstica amb data límit vençuda | **Error (Vermell)** | *"Tasca de manteniment vençuda assignada a [Familiar]."* |
| **Manteniment** | 🏠 | Dies restants per a tasca $\le diesAvis$ | **Warning (Groc)** | *"Tasca de manteniment propera en els propers X dies."* |
| **Garanties** | 🛡️ | Venciment de garantia d'aparell domèstic $\le 60$ dies | **Info (Blau)** | *"La garantia del producte [Nom] caduca el DD/MM/AAAA."* |
| **Medicació** | 💊 | Presa planificada no marcada amb retard $> 1$ h | **Warning (Groc)** | *"Presa de medicació de [Familiar] pendent d'administració."* |

---

### 7.5 Controlador d'Impressió de Tiquets (`modules/impressora.py`)

#### A. Protocol Dual: RAW ESC/POS Local vs Web Print HTML5
1. **Objectiu del Mòdul**:
   - Permet imprimir físicament en paper tèrmic de rotllo continu (76 mm o 80 mm) les llistes de la compra generades a [`modules/compres.py`](file:///e:/Dashboard/modules/compres.py), facilitant la compra al supermercat sense dependre de la pantalla del mòbil.
2. **Arquitectura Dual d'Impressió**:
   - **Mode Local Windows (RAW ESC/POS)**: Utilitza el mòdul `win32print` per comunicar-se directament amb el controlador de Windows de la impressora tèrmica (ex: *BIXOLON SRP-275*, *Epson TM-T20*, etc.). Envia fluxos de bytes binaris no interpretats amb comandaments nadius del capçal matricial.
   - **Mode Web Universal (HTML5 / window.print())**: Si l'aplicació s'executa en un dispositiu mòbil, tauleta o a través de Streamlit Cloud, genera una finestra emergent neta en HTML5 amb CSS calibrat a amplada fixa (80 mm) i llança el diàleg natiu d'impressió del navegador.

---

#### B. Normalització Matricial de Text i Seqüències de Control de Tall
1. **Funció de Sanejament Matricial (`normalitzar_per_a_matriu`)**:
   - Les impressores matricials d'agulles i tèrmiques tradicionals sovint presenten taules de caràcters reduïdes (*CodePage 437/850*). Per evitar que accents catalans o caràcters especials es converteixin en símbols inintel·ligibles, la funció substitueix automàticament accents, dièresis i la ela geminada (`à->a`, `é->e`, `í->i`, `ç->c`, `·->.`, etc.).
2. **Formatador d'Amplada Fixa (32 Caràcters per Línia)**:
   - Modela cada línia exactament a 32 columnes:
     - Checkbox buit per marcar a mà durant la compra (`[ ]`).
     - Quantitat necessària (`2x`).
     - Nom de l'article truncat a 16 caràcters per evitar salts de línia antiestètics.
     - Preu estimat aliniat a la dreta amb indicador monetari.
3. **Seqüències de Comandament ESC/POS**:
   - `\x1b@`: Inicialització i restabliment de paràmetres del maquinari.
   - `\x1ba\x01` i `\x1ba\x00`: Centrat de títols i alineació a l'esquerra del cos.
   - `\x1bE\x01` i `\x1bE\x00`: Activació i desactivació de text en negreta.
   - Salts de línia de seguretat (configurables, per defecte 6) per desplaçar el text imprès més enllà del corró d'arrossegament.
   - `\x1dV\x00` (*GS V 0*): Comanda de tall de paper complet o parcial (*Auto Cut*).

---

#### C. Flux d'Impressió i Formatació de Llistes de la Compra

```mermaid
flowchart TD
    A["🛒 Llista de la Compra a modules/compres.py"] --> B{"Tria d'Impressió de l'Usuari"}
    
    B -- Per Supermercat --> C["formatar_linies_tiquet (Ex: Mercadona)"]
    B -- Tots els Súpers --> D["formatar_tots_els_supermercats (__ALL__)"]
    
    C & D --> E["Normalització Matricial de Caràcters (Sense accents / 32 cols)"]
    E --> F{"Entorn d'Execució"}
    
    F -- Escriptori Local (Windows) --> G["imprimir_directe_bixolon"]
    G --> H["Muntatge Seqüència RAW ESC/POS (Init, Bold, Línies, Salts, Tall)"]
    H --> I["Enviament via win32print (Spooler Directe)"]
    I --> J["🖨️ Sortida Física del Tiquet amb Tall Automàtic"]
    
    F -- Web / Mòbil / Cloud --> K["generar_html_imprimir_tiquet"]
    K --> L["Finestra Emergent HTML5 amb window.print()"]
    L --> M["📱 Diàleg d'Impressió del Navegador o Impressora Wi-Fi"]
```

---

## 8. Annex: Historial de Canvis Recents Consolidat

| Data | Mòdul Afectat | Descripció del Canvi Consolidat |
|:---|:---|:---|
| **05/11/2026** | **Projectes / Persistència & Filtres** | **Canvi d'Estat a «En curs», Persistència Híbrida i Vinculació Reactiva de Filtres**: Resolt el desajust pel qual el projecte «Connexió Acumulador 2000w» tornava a sortir com a «Pendent». S'ha actualitzat directament i permanentment a «En curs» tant al fitxer local com a Supabase ID=11 (`app_config`), i s'han vinculat els botons ràpids de capçalera (`🔨 Iniciar Projecte` / `⏳ Pausar Projecte`) i el formulari d'edició amb `pending_filtre_estat_projectes` i `pending_select_projecte_actiu` perquè la interfície canviï de filtre a l'instant i mantingui el projecte actiu i visible sense que desaparegui de la pantalla. A més, en iniciar o completar qualsevol fase o subtasca, el projecte passa automàticament a «En curs». |
| **05/11/2026** | **Projectes / Renderització d'Imatges** | **Miniatures Natives amb `st.image` i Eliminació de Bolcats Base64**: Substituït el renderitzat antic `st.markdown('<img src="...">')` per `st.image(..., use_container_width=True)` tant a la galeria de fotografies del projecte com a les miniatures de la graella de materials (`modules/canvas_planol.py` i `modules/projectes_ui.py`). Això resol definitivament el bolcat de text pla amb cadenes llargues de Base64 que es produïa quan el parser de Markdown de Streamlit fallava amb imatges pesades. |
| **05/11/2026** | **Projectes / Galeria Fotogràfica** | **Compressió Automàtica d'Imatges (PIL) i Escriptura Atòmica**: Resolt el reinici sobtat de l'aplicació i pèrdua de fotos en carregar imatges en cru de 10-15 MB des del mòbil. Implementada la funció `compress_image_b64` a `core/projectes_manager.py` (Pillow + `ImageOps.exif_transpose`) per redimensionar a màxim 1280px i qualitat 80% JPEG (~150 KB, reducció del 90%), eliminant caigudes del WebSocket de Tornado i respectant el límit de Supabase. Les dades es desen de forma atòmica mitjançant fitxer temporal `.tmp` i `os.replace`. |
| **05/11/2026** | **Projectes / Fases & Rendiment** | **Desat Asíncron i Selector Directe d'Estat en 3 Botons**: Resolt el bloqueig visual («pantalla atenuada de la meitat inferior») causat per càrregues síncrones pesades a Supabase i pel diàleg modal de celebració. S'ha integrat persistència asíncrona en fil secundari (daemon thread) i memòria cau de sessió a `core/projectes_manager.py` (latència 0ms). Substituït el selector desplegable per 3 botons d'acció directa per fase: `[ ⏳ Pendent ]`, `[ 🔨 En curs ]`, `[ ✅ Acabada ]` amb ressaltat visual segons l'estat actual. |
| **05/11/2026** | **Receptari / Fotografia Gastronòmica** | **Renovació Fotogràfica Gastronòmica en Alta Resolució (4:3)**: Incorporades noves fotografies gastronòmiques professionals generades amb IA culinària per a receptes clau del receptari familiar ("Daus de sípia a la planxa", "Pinxos de pollastre adobats", "Palpís de gall d'indi", "Pastís de truites amb formatge blau", "Salmó al forn amb verdures"), amb enquadrament centrat a 45° i proporció 4:3. |
| **04/11/2026** | **Projectes / Fusteria MD** | **Dissenyador Paramètric de Mobles i CutList Optimizer 2D/3D**: Nova subpestanya *🪚 Disseny & Despecejament MD* (`modules/moble_disseny_ui.py` i `core/cut_optimizer.py`) amb visor 3D interactiu (Three.js), plantilles de mobles (prestatgeria, armari, taula), optimitzador de tall Guillotine Bin Packing 2D per planxes de fusta amb compensació de disc de serra (kerf 3-4 mm), respecte o gir per a la veta de la fusta, agrupació per gruixos de tauler (3mm a 30mm) i diagrames visuals SVG d'aprofitament per a compres. |
| **04/11/2026** | **Projectes / Fases** | **Buidat de Formulari de Subtasques, Missatge d'Èxit i Botó d'Eliminació**: En afegir una subtasca a una fase d'obra, es buida automàticament el camp de text (`clear_on_submit=True`), es mostra confirmació d'alta (`st.toast` i `st.success`) per evitar duplicats involuntaris, i s'incorpora el botó d'eliminació `🗑️` al costat de cada subtasca per poder suprimir-les amb un sol clic. |
| **04/11/2026** | **Projectes / UI** | **Filtres de Projectes Reordenats i Estat per Defecte**: Reordenació dels botons de filtre a `En curs`, `Pendent`, `Finalitzat`, `Tots` i establiment de `En curs` com a filtre inicial per defecte. Avís contextual si no hi ha projectes en curs. |
| **04/11/2026** | **Menú Superior / Resolució de Doble Clic** | **Restauració de la Navegació Canònica Directa a 1 Clic**: Resolt el comportament on calia fer clic dues vegades a les opcions del menú superior per obrir un mòdul. S'ha suprimit l'interceptor experimental `attachSpaNavInterceptors` que cancel·lava indegudament els esdeveniments de clic natius (`e.preventDefault()`), restaurant els enllaços directes canònics de navegador (`<a href="?mod=..." target="_self">`). Ara qualsevol mòdul i hotspot respon immediatament al primer clic. |
| **04/11/2026** | **Menú Superior / Manteniment** | **Integració Directa de la Pestanya Projectes (`🏗️ Projectes`) al Menú de Manteniment**: Afegit l'accés directe `🏗️ Projectes` al submenú desplegable `Mòduls > Manteniment de la llar` (`?mod=modules.manteniment&tab=projectes`). S'ha actualitzat també l'interceptor de pestanyes a `app.py` per commutar directament a la pestanya 3 (`targetIdx = 3`) sense recarregar la pàgina quan el mòdul ja és actiu. |
| **04/11/2026** | **Navegació / Rendiment i Transició SPA** | **Eliminació de la Càrrega de Més d'un Minut i Navegació Instantània SPA sense Recàrrega**: Resolt el retard superior a un minut en obrir qualsevol mòdul des de la pantalla inicial. S'han resolt dues causes arrel: 1) S'ha eliminat la recàrrega sencera del navegador (`window.location.assign`), que forçava la descàrrega de 30 MB d'assets JS i la reinicialització del WebSocket; ara la navegació dels hotspots utilitza `history.pushState` + `popstate` natiu de Streamlit (amb interceptor SPA global a `components.html`), fent la transició de mòdul instantània (mil·lisegons) sense mostrar mai el *skeleton loader*. 2) Optimització dels mòduls lents: a `modules/economic.py` s'han eliminat imports immensos de nivell superior (`google.generativeai` que trigava 20s en importar-se, `scanner`, `pytesseract`) convertint-los en imports diferits (*lazy*) exclusius del xat IA, i a `core/db.py` s'ha eliminat la consulta síncrona a Supabase a l'arrencada (`cat_config`), reduint el temps d'importació de 85 segons a 3.1 segons (acceleració de 27x). |
| **03/11/2026** | **Manteniment / Projectes d'Obra** | **Reactivitat per a Nous Proveïdors a l'Alta de Materials**: Desacoblat el formulari d'afegir material manualment (`modules/projectes_ui.py`) eliminant l'embolcall rígid `st.form`. En Streamlit, els widgets dins d'un `st.form` no desencadenen rerun en canviar de valor; per aquest motiu, quan l'usuari seleccionava `➕ Afegir un altre proveïdor...` al desplegable, el camp de text per introduir el nom del nou proveïdor no s'arribava a mostrar mai abans de desar. Ara és completament reactiu: en seleccionar l'opció apareix immediatament el camp per escriure el proveïdor, es valida que no quedi buit, s'enregistra automàticament a la memòria de proveïdors i s'assigna al material. |
| **03/11/2026** | **Manteniment / Projectes d'Obra** | **Resolució de Conflicte de Cicle de Vida de Streamlit a l'Alta de Nous Projectes**: Solucionat l'error fatal `st.session_state['select_projecte_actiu'] cannot be modified after the widget with that key is instantiated` a `modules/projectes_ui.py`. El formulari modal de nou projecte s'executa després de la instanciació del selector `st.selectbox` i del filtre `st.pills`/`st.radio`, per la qual cosa modificar directament les claus de sessió vinculades als widgets abans de `st.rerun()` bloquejava l'aplicació. S'ha desacoblat el patró mitjançant variables pendents d'assignació (`pending_select_projecte_actiu` i `pending_filtre_estat_projectes`) que s'injecten i es consumeixen just abans que els widgets es renderitzin, garantint la creació i selecció immediata del nou projecte en qualsevol dispositiu sense interrupcions. |
| **02/11/2026** | **Bases de Dades / Formats de Data** | **Correcció Integral del Format de Data a `DD/MM/AAAA` i Resolució d'Inversió Mes/Dia**: Auditades totes les taules de la base de dades. Corregit el parser de dates a `modules/bases_dades.py` (`robust_parse_date_series`), que utilitzava indegudament `dayfirst=True` sobre cadenes ISO a `tr_cartera`, intercanviant mes i dia (mostrant p. ex. `11/02/2026` en lloc de `02/11/2026`). Corregits a Supabase i als CSVs locals els 4 registres històrics desalineats de `tr_cartera` (IDs 22, 23, 24 i 25) i el registre aïllat de `kmCotxe` (ID 629 de `2026-10-13` a `13/10/2026`). Blindat el format d'actualització i inserció de `bases_dades.py` perquè respecti el format ISO natiu per a taules de tipus `DATE` i `DD/MM/AAAA` per a taules de text. |
| **02/11/2026** | **Econòmic / Inversions TR Cartera** | **Neteja Automàtica del Formulari de TR Cartera, Botó Netejar i Eliminació de Duplicats**: Resolt el problema pel qual el formulari de nou moviment de TR Cartera (`modules/economic.py`) mantenia els valors als camps després de desar, provocant entrades duplicades involuntàries de CashBack o compres. Ara s'eliminen automàticament de `st.session_state` les claus del formulari (`tr_cartera_inv`, `tr_concepte_inv`, `tr_import_inv`, `tr_comentari_inv`), es mostra un banner d'èxit persistent (`st.success`), s'afegeix el botó `Netejar`, s'incorpora la cartera `Amazon` al desplegable, es bloqueja el desat amb imports $\le 0$ fins i tot a CashBack, i s'han purgat de Supabase els registres duplicats (ID 38 a `tr_cartera` i moviment buit ID 8250 a `despeses`). |
| **02/11/2026** | **Compres Super / Tiquets** | **Característiques i Regles d'Extracció per a bonÀrea / AreaGuissona**: Documentat el patró complet del tiquet físic de bonÀrea (Corporació Alimentària Guissona S.A.) a la Secció 4.1.E de `DOCUMENTACIO_PROJECTE.md` i a `core/ocr_rules.md`. Especificada la regla crítica per evitar confondre el tipus d'IVA de l'extrem dret (`4.00`, `10.00`) amb el preu de l'article, la resolució de quantitats múltiples en línia (`Nx P_Unit`), la supressió de punts suspensius i la normalització del concepte a `AreaGuissona`. |
| **02/11/2026** | **Compres Super / Mòbil** | **Captura Nativa de Tiquets amb Càmera del Mòbil (`st.camera_input`)**: Afegit selector de mètode de captura a `modules/compres.py` amb opció per defecte `📸 Càmera del Mòbil (Directa)`. Utilitza l'API web nactiva de Streamlit (`st.camera_input`) mitjançant WebRTC directe al navegador, permetent enfocar i fotografiar el tiquet de compra a l'instant sense sortir de Chrome/PWA ni activar l'aplicació externa de càmera d'Android (que provocava la suspensió en memòria de la pestanya i la pèrdua de la connexió WebSocket). Totalment integrat amb el cicle de vida del tiquet (`camera_uploader_key`), botons de reintent/descart (`🔄`/`❌`) i fallback directe a `📁 Pujar Fitxer / Escàner físic`. |
| **02/11/2026** | **Configuració / Estances i IoT** | **Manteniment d'IoT per Estança, Acumuladors (Tuya/Wifi) i Activació de Sensors**: Ampliada la gestió d'estances a `modules/admin.py` i `modules/domotica.py` amb manteniment complet d'elements domòtics per habitació (afegir, modificar nom, eliminar); integració específica per a acumuladors de calor governats per programador Tuya i contactor Wi-Fi (`🧱 + Acumulador (Tuya)`, `⚡ + Contactor Wi-Fi`); afegits interruptors en viu (`st.toggle`) per activar/desactivar en temps real qualsevol sensor, eina o dispositiu (càmeres, detectors de presència, etc.). |
| **02/11/2026** | **Configuració Global / Estances** | **Nova Secció d'Estances de la Casa (`🏡 Estances de la casa`) amb Regles de Negoci i Vinculació a Projectes**: Nova pestanya a `modules/admin.py` amb persistència a `app_config` (ID=2 a Supabase i `core/config.json`). Implementades regles de blindatge de permanència: Menjador i Cuina obligatoris no eliminables; com a mínim 1 Bany i com a mínim 1 Habitació actius (bloqueig amb cadenat 🔒 quan en queda un sol exemplar); botons d'alta ràpida per a banys/habitacions addicionals, terrasses, jardí, garatge, traster, despatx i safareig; selector d'icones emoji i formulari d'estances personalitzades; connexió immediata amb el selector d'ubicació a l'alta i edició de projectes d'obra a `modules/projectes_ui.py`. |
| **02/11/2026** | **Manteniment / Projectes d'Obra** | **Reactivació de Consultes d'IA, Gestió d'Errors, Auto-Adaptació de Tokens (HTTP 402) i Correcció de Truncat en Text**: Incorporats botons de reactivació directa (`🔄 Reactivar`) a cada pregunta del xat i targetes d'error amb acció de reintent immediat (`🔄 Reintentar ara`) i descart (`🗑️ Descartar`) visibles al mòbil sense scroll; resolució de límit de crèdits a OpenRouter mitjançant auto-adaptació dinàmica de `max_tokens` (`can only afford X`) i fallback automàtic a Gemini (2.5 Flash); corregida la comprovació de terminació JSON a `core/llm.py` que rebutjava indegudament respostes vàlides de text pla com a "truncades" forçant cascada de models fins a la quota HTTP 429; eliminada duplicitat de renderització de selectors d'IA (`DuplicateWidgetID`); afegit selector de filtre per estat (`Pendent`, `En curs`, `Finalitzat`). |
| **01/11/2026** | **Manteniment / Projectes i Plànols** | **Creador d'Habitacions amb Mides (`🏠 Habitació`), Galleda de Textures (`🪣 Textura`), Navegació (`🖐️ Moure`), Mode Paret Contínua (`🔗 Seguir traç`) i Snap Magnètic**: Afegit el generador d'habitacions predeterminades amb mides reals en metres (amplada $X$ i llargada $Y$, etiquetes i 4 parets amb cotes automàtiques a escala 40px=1m); incorporada la galleda de textures amb patrons vectorials natius per a terra (parquet, rajola, gresite de dutxa, gespa, microciment) i paret (maó vist, subway, pedra, llistons, calç); afegida l'eina `🖐️ Moure` per navegar còmodament pel plànol ampliat arrossegant el dit sense dibuixar; incorporat el mode d'enllaç automàtic `🔗 Seguir traç` per dibuixar habitacions completes sense haver de buscar on continuava la línia anterior (amb halo indicador de punt de partida i botó `⏹️ Desconnectar`); implementat el magnetisme automàtic (`🧲 Snap`) per ajustar exactament parets i cotes als vèrtexs existents; afegits botons de zoom i mode alçat de paret. |
| **31/10/2026** | **Navegació / Mòduls** | **Eliminació del Rebot de Navegació a Túnels i Desglossar**: Implementat el mecanisme `nav_target_mod` / `nav_target_tab` a `app.py` per prioritzar les transicions internes de mòduls executades per botons (`st.button`), evitant que els query params desactualitzats enviats pel navegador client sobrescriguin la destinació i mantinguin l'usuari a la mateixa pantalla al prémer `Desglossar` o els botons túnel. |
| **31/10/2026** | **Compres Super / Desglossament** | **Deducció del Descompte Global en Tiquets Pendents i Persistència a `compresSuper`**: Corregit el càlcul de conciliació a `cb_finalize_ticket` de `modules/compres.py` per deduir el descompte global (`ticket_discount`) abans de comparar amb el càrrec del banc (`pending_import_carrec`). Això resol el fals desquadrament en tiquets amb descomptes/promocions i permet que s'insereixin els productes a `compresSuper` i es desmarqui el tiquet com a pendent (`ticketPendent = False`). També s'ha integrat `descompte_global` a l'esquema d'extracció d'IA/OCR. |
| **29/10/2026** | **Compres Super / Estadístiques** | **Desglossament d'Alimentació vs Neteja i Conciliació amb el Dashboard**: Integrat el desglossament de la despesa de supermercat entre Alimentació neta (`menjar`), Neteja i Llar (`neteja`) i descomptes globals de caixa a les targetes KPI i a un nou panell de conciliació comptable amb selector de gràfic de donut (*Menjar vs Neteja*), quadrant al cèntim exacte la diferència entre el tiquet global de supermercat i la categoria *menjar* del Dashboard. |
| **29/10/2026** | **Econòmic / Dashboard** | **Control de Data i Compatibilitat PyArrow al Modal de Confirmació**: Integrat selector de data (`st.date_input`) en format `dd/mm/aaaa` als blocs *Pagaments del mes* i *Ingressos del mes* del Dashboard i previsions (`dialog_confirmar_operacions`). Control estricte que restringeix la data de l'apunt a l'interval del mes consultat (`min_value` i `max_value` entre el dia 1 i l'últim dia del mes). Resolució d'incompatibilitat de tipus amb PyArrow (`string[pyarrow]` a Streamlit Cloud) per al camp `dia` garantint tolerància a fallades en l'actualització de DataFrames en memòria i persistència a `despeses` / `tr_cartera`. |
| **28/10/2026** | **Llum / Factures** | **Normalització de Dates a `dd/mm/aaaa` i Parser Resilient**: Conversió dels 44 registres històrics de `data/consum_llum.json`, `csv/consum_llum.csv` i Supabase ID=9 de format ISO a `dd/mm/aaaa` (`dataFactura`, `periodeInici`, `periodeFi`). Implementada la funció de suport `_parse_dmy_or_iso()` a `modules/llum_aigua.py` per garantir una lectura i edició 100% resilient dels períodes de facturació. |
| **28/10/2026** | **Nucli / Editor JSON** | **Neteja d'Arxius Temporals Obsolets**: Eliminats els fitxers temporals obsolets d'antigues importacions de receptes (`pending_13.json`, `pending_13_real.json`, `missing_recipes.json`), netejant el menú superior desplegable `Editar > 📂 Arxius JSON` per mostrar exclusivament els fitxers de dades actius de l'aplicació. |
| **28/10/2026** | **Documentació Global** | **Auditoria i Documentació Exhaustiva de la Secció 7**: Desglossament complet d'Administració (12 seccions estil Chrome Settings), Laboratori IA Harness (8 avaluadors deterministes i execució en segon pla), Gestor de Bases de Dades en temps real, Sincronització Offline i Controlador d'Impressora ESC/POS. |
| **27/10/2026** | **Cotxe / Km i Rutes** | **Control Estricte d'Odòmetre**: Bloqueig i validació perquè els kilòmetres entrats a una nova ruta mai puguin ser iguals o inferiors a l'última lectura registrada de l'odòmetre (`contador_val > last_km`), amb avís dinàmic en vermell, indicador de trajecte invàlid i protecció tant a l'entrada manual com a l'escaneig per foto OCR. |
| **26/10/2026** | **Llum i Aigua / Preus** | **Registre Persistent de Preus Horaris PVPC i Auditoria Factura**: Creat el registre diari `data/preus_llum_diaris.json` (accessible des del menú superior *Editar > 📂 Arxius JSON* sense afegir noves pestanyes), gravació automàtica continuada de les 24h de cada dia, funció de contrast de consums i auditoria completa de la factura 10-2026 (66,59 €, 449,572 kWh amb 25h de preus negatius). |
| **28/10/2026** | **Compres / Escàner** | **Integració 1-Clic d'Escaneig a Compres**: Afegits botons `🖨️ Obrir Escàner` i `📥 Carregar últim tiquet` a `modules/compres.py`, encapsulament `LocalFileWrapper` i fallback automàtic de supermercat i data des del nom de fitxer (`tickets/ticket_<super>_<date>.jpg`). |
| **28/10/2026** | **Cotxe / Odòmetre** | **Validació Estricta de Km**: Bloqueig d'entrades de quilòmetres inferiors o iguals al darrer registre a `modules/cotxe.py` amb alerta visual vermella en temps real. |
| **28/10/2026** | **Llum / PVPC** | **Registre Diari de Preus PVPC**: Implementació de registre horari persistent a `data/preus_llum_diaris.json` i funcions de contrast de consum a `core/llum_manager.py`. |
| **25/10/2026** | **Escaneig Tiquets** | **Restauració escaneig directe 1-clic**: Nou motor natiu WinRT ([`scan_winrt.ps1`](file:///e:/Dashboard/scan_winrt.ps1)), superant l'antiga fallada de bloqueig temporal WIA (`ERROR_SHARING_VIOLATION` / `0x80030070`). Eliminats botons secundaris a [`auto_scan_ui.py`](file:///e:/Dashboard/auto_scan_ui.py) deixant només `🖨️ Escanejar Tiquet`. |
| **25/10/2026** | **Cotxe / Manteniment** | **Seccions Col·lapsables**: Totes les seccions de la pestanya *Manteniment* transformades en blocs plegables independents (`st.expander`) amb badges informatius en temps real als encapçalaments i control de desplegament global. |
| **24/10/2026** | **Rendiment Core** | **Pla d'optimització de 30 dies**: Finestra activa de 30 dies a Supabase + arxiu històric en CSV amb memòria cau de 24h per a taules massives. Eliminats els buidats massius de cau, passant de bloquejos de 20s a càrregues en menys d'1s. |
| **24/10/2026** | **Compres Super** | **Model Matemàtic de Preu Final Fix ($PF = B \times (1 - d)$)**: Enginyeria inversa de promocions a la càrrega manual de línies, mantenint el Total Línia invariable i fidel al tiquet de caixa. |
| **24/10/2026** | **Llum i Aigua** | **Estudi Solar PVGIS i Acumuladors**: Integrat simulador fotovoltaic amb dades oficials de radiació solar, desdoblament d'acumuladors tèrmics amb persistència a `data/acumuladors_config.json`, i ingesta històrica de factures elèctriques en PDF. |
| **11/11/2026** | **Manteniment / Projectes** | **Editor Gràfic en 3 Pestanyes (Plànol, Disseny MD i Esquemes Elèctrics)**: Reestructurada la secció visual a [`modules/projectes_ui.py`](file:///e:/Dashboard/modules/projectes_ui.py) i [`modules/canvas_planol.py`](file:///e:/Dashboard/modules/canvas_planol.py) en 3 pestanyes: **Editor Gràfic de Plànol**, **Disseny & Despecejament MD** (mogut dins l'editor gràfic) i el nou mòdul [`modules/canvas_electric.py`](file:///e:/Dashboard/modules/canvas_electric.py) (**Esquemes Elèctrics**) amb cables de 3 colors normatius (Negre Fase, Blau Neutre, Groc/Verd Terra), traç ortogonal a 90°, snap a borns, eina **`↖ Seleccionar`** (amb quadrets a les 4 cantonades, 4 punts mitjans i centre per moure i transformar la mida de qualsevol element incloent textos per caixa completa `hitTestBounds`), **Termòstat amb 4 contactes (`L`, `N`, `C`, `NO`)**, **Programador**, blocs redimensionables (**Caixa**, **Quadre**, **Càrrega**), goma amb arrossegament capaç d'esborrar textos en ambdós editors, exportació i càrrega d'esquemes guardats (**`💾 JSON`** / **`📂 Carregar JSON`** i selector d'esquemes desats al núvol), modal de confirmació en prémer **🗑️ Netejar**, junt amb Bombeta, Endoll, Interruptor, Commutador, Magnetotèrmic, Diferencial i Contactor, amb persistència a [`core/projectes_manager.py`](file:///e:/Dashboard/core/projectes_manager.py). |
| **11/11/2026** | **Alertes / Projectes** | **Alertes de Fases Pendents en Projectes En Curs**: Afegit `get_projectes_fases_alerts()` a [`core/alerts.py`](file:///e:/Dashboard/core/alerts.py) perquè només els projectes en estat **`En curs`** enviïn avisos a la campana global (`🔔`) quan una fase no completada s'acosta o venç segons el camp configurable `dies_avis_fases` (per defecte `3` dies). Incorporat el selector de dies d'avís a l'alta, edició i pestanya *Fases d'Execució* de [`modules/projectes_ui.py`](file:///e:/Dashboard/modules/projectes_ui.py), juntament amb el popover `📅 Termini` per assignar dates a fases existents i refresc immediat de la campana en [`core/projectes_manager.py`](file:///e:/Dashboard/core/projectes_manager.py). |
| **11/11/2026** | **Manteniment / Projectes** | **Miniatures Materials en Mòbil Vertical, Edició de Fotos Pujades i IA Visual Millorada**: Modificada la graella de materials a [`modules/projectes_ui.py`](file:///e:/Dashboard/modules/projectes_ui.py) amb CSS Grid responsiu (`6` columnes PC, `4` horitzontal/tauleta, `3` mòbil vertical omplint el `100%` de l'amplada de pantalla) i miniatures equilibrades de `68×68 px` amb etiqueta en 1 línia; obert per defecte `📷 Canviar / Gestionar Foto` als detalls del material i afegit el botó `✏️` (`update_projecte_foto`) a [`modules/canvas_planol.py`](file:///e:/Dashboard/modules/canvas_planol.py) i [`core/projectes_manager.py`](file:///e:/Dashboard/core/projectes_manager.py) per substituir fotos d'obra ja pujades. Millorat [`core/ai_projectes.py`](file:///e:/Dashboard/core/ai_projectes.py) amb diccionari tècnic català→anglès i traducció LLM (`_build_english_product_prompt`), generació prioritària via Gemini Image (sense marca d'aigua) i fallback a Pollinations `flux` amb descripcions de ferreteria precises. |
| **11/11/2026** | **Control / Seguretat Codi** | **Nou Mòdul «🛡️ Control» en 3 Nivells (Blindat / Vigilat / Obert)**: Implementat el sistema de protecció i anti-regressió amb `core/control_manager.py`, `modules/control.py`, `scripts/check_control.py`, `.git/hooks/pre-commit` i `tests/smoke/test_modules_smoke.py` (accessible des d'`Editar > 🛡️ Control de Mòduls` per a administradors). Els mòduls **Blindats** (`Compres Super`, `Econòmic`, `Cotxe`, `Dashboard`) bloquegen modificacions sense desbloqueig explícit; els **Vigilats** (`Llum i Aigua`, `Configuració`, `Manteniment`, `Menjar`, `Nucli Compartit`) creen còpies de seguretat automàtiques a `data/control_backups/` i verifiquen impactes transversals; i els **Oberts** (`Calendari`, `Medicació`, `Seguretat`, `Domòtica`) permeten edició lliure amb punts de control i *rollback* en 1 clic. |
| **11/11/2026** | **Compres Super** | **Càlcul en Viu de `TOTAL LÍNIA` i Commit Natiu amb `Enter` (`Entrar línia`)**: Resolt l'error a `modules/compres.py` on el interceptor JS de teclat (`__compres_enter_handler`) bloquejava l'esdeveniment `onKeyPress` dels camps numèrics de Streamlit (`NumberInput`), impedint confirmar valors com `PREU UNIT.` en prémer `Enter`. S'ha dotat `TOTAL LÍNIA` d'una clau estable (`manual_tot_linea_disp`) per evitar el re-muntatge del bloc durant les actualitzacions, s'ha afegit càlcul en viu client-side (suportant punt i coma decimal) i gestió segura del focus cap a `Entrar línia` després del *rerun*. |
| **11/11/2026** | **Manteniment / Projectes** | **Renderitzat Nativa d'Imatges (MediaFileManager) i Pujada Múltiple de Fotos**: Incorporat el descodificador `decode_image_for_st()` a `core/projectes_manager.py` per convertir cadenes `data:image/jpeg;base64,...` a `bytes` reals abans de passar-les a `st.image()`, evitant problemes de visualització de *data URIs* grans en navegadors mòbils i Streamlit Cloud. Actualitzat el formulari de pujada amb `clear_on_submit=True`, suport per a múltiples fotos simultànies, IDs únics en mil·lisegons i avisos explícits d'error/èxit. |
| **10/11/2026** | **Manteniment / Projectes** | **Editor Gràfic de Plànol Col·lapsat per Defecte**: Modificat el desplegable `✏️ Obrir Editor Gràfic de Plànol (Canvas)` a `modules/canvas_planol.py` (`expanded=False`) perquè aparegui sempre plegat en obrir qualsevol projecte, facilitant l'accés ràpid a la galeria de fotos. |
| **10/11/2026** | **Manteniment / Projectes** | **Persistència Fiable al Núvol de Projectes, Fases i Fotos**: Resolt un error crític a `core/projectes_manager.py` on `load_projectes()` prioritzava el fitxer local `data/projectes_manteniment.json` (versionat a Git) per davant de Supabase, fet que feia desaparèixer nous projectes, fases i fotos en reiniciar la sessió o el contenidor al núvol. A més, `save_projectes()` s'ha passat d'un *thread* en segon pla a desat síncron directe a Supabase (`app_config`, `id=11`) amb notificació explícita d'errors. |
| **09/11/2026** | **Compres Super / Mòbil** | **Auto-Commutació Càmera Posterior (Principal)**: Implementada detecció i commutació automàtica a la càmera posterior (`environment`) en activar la captura per càmera al mòbil (`st.camera_input`), evitant que s'activi per defecte la càmera frontal de selfie. Incorporada indicació visual del botó manual `[ 📷 ⇄ ]` com a suport. |
| **09/11/2026** | **Compres Super** | **Simplificació Captura de Tiquets (Eliminació Botó Escàner)**: Eliminat el botó '🖨️ Obrir Escàner' i el text residual a la interfície de Compres Super per evitar confusions a entorns web (Streamlit Cloud). Renombrada l'opció a '📁 Pujar Fitxer' amb el selector d'arxius natiu a l'ample complet, mantenint la càrrega directa d'arxius a `tickets/` si n'hi ha. |
| **09/11/2026** | **Rendiment / Mòdul Econòmic & Compres** | **Optimització Canvi a Mòdul Econòmic & Mètode de Captura per Defecte**: Resolució de la lentitud (> 1 minut) en canviar al Mòdul Econòmic des del botó túnel de Compres. S'ha eliminat la instanciació de `DBTracker` local sense memòria cau a `modules/economic.py` que forçava la recàrrega de les 10 taules per xarxa a cada cicle, centralitzant la gestió a `core/db.py` amb càrrega granular només de taules mancants (< 4s en fred, instantani en calent). |
| **09/11/2026** | **Compres Super / Despeses** | **Conciliació de Descomptes Globals vs Promocions de Línia**: Resolució de la duplicació de descomptes (ex: 3.37 € a tiquets Dia) en lectors d'IA (Gemini). Ara s'extreu el `total_tiquet` i es concilia matemàticament amb la suma d'articles per evitar aplicar un descompte global quan les promocions ja han estat deduïdes de les línies. Corregit el registre de despesa 8282 a 25.14 € a Supabase i CSV. |
| **07/11/2026** | **Compres Super** | **Navegació Teclat i Focus 'Entrar línia'**: Correcció de l'enfocament i navegació amb Enter a l'entrada manual de tiquets. L'acció d'entrada enfoca i manté la vista directament al botó **'Entrar línia'** en lloc de desplaçar la pantalla al final del document a 'Fi Tiquet'. Gestió nactiva de desplaçament suau i aïllament estricte dels camps de la fila manual. |
| **05/11/2026** | **Compres / Despeses** | **Correcció Despeses Conciliades**: Importació de `save_to_csv` a `modules/compres.py` i actualització a `core/db.py` amb persistència local (`save_to_csv_local`) i Supabase, resolent el `NameError` en desar despeses que concilien pagaments previstos (ex. Exaprint). |
| **05/11/2026** | **Documentació** | **Consolidació Documental Mestre**: Eliminació de fitxers intermedis redundants (`DOCUMENTACIO_ORGANITZADA.md`, `DOCUMENTACIO_GENERALITZADA.md`) i consolidació de `DOCUMENTACIO_PROJECTE.md` com a únic document canònic. |
| **23/10/2026** | **Llum i Aigua** | **Creació del Mòdul '💡 Llum i Aigua'**: Preus PVPC horaris en directe, gestió de factures elèctriques i d'aigua amb visor natiu PDF.js i sincronització a Supabase IDs 9 i 10. |
| **22/10/2026** | **Cotxe** | **Control de Nivells**: Secció independent per a la revisió de líquids del vehicle (oli, refrigerant, frens, eixugaparabrises) amb planificacions i alertes per km i temps. |
| **22/10/2026** | **Agenda** | **Control Fet/No Fet i Mòbil 1 Línia**: Botons interactius `✅`/`❌` amb colors sòlids vibrants i regles CSS `:has(.cal-action-btn)` per mantenir les 5 accions en una sola fila horitzontal a telèfons mòbils. |
| **21/10/2026** | **Manteniment Llar** | **Tasques Periòdiques i Subtasques**: Generació en sèrie de tasques recurrents, subtasques amb cadència pròpia i generador interactiu de tasques per al proper any al menú superior. |
| **19/10/2026** | **Manteniment Llar** | **Gestió Documental (Manuals i Garanties)**: Dipòsit de documents PDF amb visor interactiu HTML5 Canvas (PDF.js) i semàfor de venciment de garanties. |
| **18/10/2026** | **Econòmic / Compres** | **Navegació Nativa per Pestanyes**: Ús del paràmetre natiu `default` a `st.tabs`, creació de botons túnel bidireccionals i quantitat editable a destí per a traspassos de comptes. |
| **17/10/2026** | **Compres Super** | **Blindatge de Dates i Suport PDF**: Sanejament de dates contra errors matricials d'OCR, bloqueig de dates futures, extracció nativa de PDFs de supermercat amb `pypdf` i nous models Gemini. |
| **16/10/2026** | **Econòmic** | **Pagues Extres i Nou Any Comptable**: Incorporació de pagues extres i selector d'anys a 3 bandes ([any-1, any, any+1]) amb projeccions visuals. |
| **16/10/2026** | **Impressora** | **Impressora de Tiquets**: Integració d'impressió RAW ESC/POS de llistes de compra amb tall de paper i vista d'impressió web. |
| **18/09/2026** | **Nucli / BBDD** | **Arquitectura Offline**: Mode desconnectat amb cua local `sync_queue.json` i mòdul de consolidació de dades. |
| **13/09/2026** | **BBDD / Interfície** | **Gestor de Bases de Dades**: Creació de `modules/bases_dades.py` i barra de navegació superior d'escriptori amb 4 menús clàssics. |


---

## 21. Annex 8: Eina de Normalització de Dades (BD & JSON)

### 21.1. Objectiu i Arquitectura
L'eina de normalització (`core/normalitzador.py` i `modules/normalitzador_ui.py`) neix per resoldre i prevenir la coexistència de discrepàncies històriques als registres de la base de dades (Supabase i rèpliques CSV) i als fitxers JSON de taxonomia:
1. **Categories en minúscules sense accents**: Les claus canòniques tècniques no poden tenir accents ni majúscules (`buta`, `farmacia`, `ingres_general`, `ingres_extra`, `parallar`, `manteniment`, `assegurança`). Els registres històrics que utilitzaven `butà`, `farmàcia`, `ingrés_general`, `ingrés_extra`, `Parallar`, `mant_netej` són transformats automàticament a la forma canònica (preservant expressament la ce trencada a `assegurança`).
2. **Format estricte de dates (`DD/MM/AAAA`)**: Detecció i conversió de formats ISO (`AAAA-MM-DD`, `AAAA-MM-DDTHH:MM:SS`), formats amb guió (`DD-MM-AAAA`) i components residuals de temps cap al patró unificat català `DD/MM/AAAA`.
3. **Harmonització de Conceptes i Formes de Pagament**: Supressió d'espais residuals, homologació de conceptes (`CashBack` a operacions bancàries, supermercats com `Dia`/`Mercadona`/`Novavenda` a neteja, `Accions NVIDIA`/`Accions S&P500` a despesa general) i unificació de text.

### 21.2. Funcionament Granular i Configurable
Accessible des de qualsevol pantalla mitjançant la barra de menú superior **Editar > 🧹 Normalitzar Dades (BD & JSON)**:
- **Selector de Taula**: Permet escollir si es vol analitzar una taula concreta (`despeses`, `ingressos`, `pagaments`, `tr_cartera`, `compresSuper`, `kmCotxe`) o bé fer un escombrat de totes alhora, evitant processos monolítics que puguin bloquejar l'usuari.
- **Selectors d'Àmbit (Checkboxes)**: Triar lliurement quines comprovacions realitzar:
  - Dates (`DD/MM/AAAA`).
  - Categories (minúscules sense accents).
  - Conceptes (harmonització).
  - Bancs i Formes de Pagament (espais i majúscules).
- **Graella Interactiva (`st.data_editor`)**: Mostra el diagnòstic amb checkboxes individuals per a cada fila, indicant ID, Taula, Columna, Valor Actual, Valor Normalitzat i Motiu de la discrepància.
- **Execució en Bloc Segura**: Botó `▶️ Aplicar Normalització als seleccionats` que actualitza en temps real Supabase i manté sincronitzats els fitxers CSV locals per a operativitat offline.
- **Pestanya de Taxonomia JSON**: Permet visualitzar l'estat de les claus a `categories_conceptes.json` i sincronitzar-les en 1 clic amb el registre `app_config` (ID=1) de Supabase.
