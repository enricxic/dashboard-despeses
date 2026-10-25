# Documentació Integral del Projecte: Dashboard Despeses - XiquiHouse
> **Versió Organitzada per Prioritats i Mòduls**  
> *Data d'actualització: 25 d'octubre de 2026*  
> *Fitxer de referència mestre per a noves sessions d'IA i manteniment del sistema.*

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
   - [7.5 Impressora de Tiquets BIXOLON SRP-275APG (`modules/impressora.py`)](#75-impressora-de-tiquets-bixolon-srp-275apg-modulesimpressorapy)
8. [Annex: Historial de Canvis Recents Consolidat (Setembre - Octubre 2026)](#8-annex-historial-de-canvis-recents-consolidat-setembre---octubre-2026)

---

## 1. Instruccions per a IA i Directrius Crítiques (Prioritat 1)

> [!IMPORTANT]
> **Instrucció d'Arrencada per a Noves Sessions d'IA**  
> Si inicies una conversa nova amb un assistent d'IA, cal indicar-li:  
> **"Llegeix `DOCUMENTACIO_ORGANITZADA.md` per entendre l'arquitectura modular, les prioritats i el funcionament de l'aplicació abans de tocar cap codi."**

### 1.1 Directriu Obligatòria de Desplegament a GitHub (`git push`)
- L'aplicació s'executa tant en local com des del núvol (**Streamlit Community Cloud** enllaçat amb el repositori GitHub `enricxicars/dashboard-despeses`).
- **REGLE INVIOLABLE**: Un cop realitzat i provat qualsevol canvi en local, l'assistent d'IA **TÉ L'OBLIGACIÓ STRICTA DE DESAR I PUJAR SEMPRE ELS CANVIS A GITHUB** (`git add`, `git commit -m "..."`, `git push origin main`).
- Mai es dóna una tasca per finalitzada sense haver pujat els canvis al repositori remot.

### 1.2 Llengua de Comunicació
- La llengua vehicular del projecte i de totes les comunicacions amb l'usuari és el **Català**.

---

## 2. Arquitectura del Sistema, Sincronització i Rendiment (Prioritat 1)

### 2.1 Model Dual Híbrid (Cloud-First + Fallback Offline)
1. **Entorn Núvol (Streamlit Cloud)**: Accés mòbil i multi-dispositiu permanent.
2. **Arrencador d'Escriptori (`StartDashboard.py`)**:
   - Obre automàticament la versió del núvol a **Google Chrome** en arrencar el PC si hi ha connexió a Internet.
   - Mentrestant, un procés silenciós en segon pla (`scripts/update_csvs_background.py`) descarrega les dades de PostgreSQL directament als fitxers CSV locals com a font de veritat actualitzada.
3. **Emergency Offline Mode**: Si no hi ha internet (o si es desconnecta el Wi-Fi abans de fer doble clic), arrenca l'entorn local Streamlit de forma instantània llegint exclusivament dels CSV locals mitjançant *Lazy Loading*. Les mutacions locals es retenen a `sync_queue.json` per ser consolidades en recuperar connexió.

### 2.2 Estratègia de Rendiment d'Alt Rendiment (Pla 24/10/2026)
Per evitar bloquejos de 15 a 60 segons en les taules massives de més de 15.000 files (`despeses` i `compresSuper`):
- **Finestra Activa de 30 dies**: Es consulta a Supabase en una sola petició HTTP ultra-lleugera (`0,15 s`) per als registres recents i tiquets pendents.
- **Arxiu Històric (Mesos vençuts)**: Carregat en memòria cau persistent de 24 hores (`@st.cache_data(ttl=86400)`) des del CSV local (`0,04 s`).
- **Fusió Transparent**: El DataFrame complet s'entrega unint recent + històric sense duplicats.
- **Mutacions Locals amb Zero Latència**: `insert_db_row`, `update_db_row` i `delete_db_row` modifiquen directament el DataFrame a `st.session_state` i invaliden només la finestra recent, **sense cridar mai `st.cache_data.clear()` massiu**.
- **Càrrega Selectiva (*Lazy Loading*) per Mòdul**: Cada mòdul només demana a `ensure_session_dfs` les taules que utilitza estrictament.
- **Càrrega "Lazy" amb `st.radio` o menús**: Evita renderitzar continguts pesats invisibles de pestanyes inactives que saturaven el DOM del navegador.

### 2.3 Centralització de Configuracions a Supabase (`app_config`)
Per garantir la persistència al núvol en els reinicis de màquines virtuals de Streamlit Cloud, totes les configuracions JSON s'emmagatzemen com a mestres a Supabase:
| ID | Fitxer Equivalent Local | Descripció |
|:---|:---|:---|
| **1** | `categories_conceptes.json` | Categories i conceptes de despeses/ingressos |
| **2** | `core/config.json` | Perfil familiar, al·lèrgies, vetos, eines de cuina, admin |
| **3** | `data/events.json` | Esdeveniments del calendari familiar i estats fet/no fet |
| **4** | `data/feeds_cache.json` | Memòria cau dels Google Calendars personals |
| **5** | `data/medication_plans.json` | Plans i horaris de medicació familiar |
| **6** | `data/ofertes.json` | Registre d'ofertes setmanals i fulletons |
| **7** | `data/manteniment_docs.json` | Registre documental de Manuals i Garanties de la llar |
| **8** | `data/registre_manteniment.json` / `csv/manteniment.csv` | Registre de tasques, reparacions i periodicitats de la llar |
| **9** | `data/consum_llum.json` / `csv/consum_llum.csv` | Factures elèctriques, potències i consums per tram (històric de factures) |
| **10** | `data/consum_aigua.json` / `csv/consum_aigua.csv` | Factures d'aigua, lectures de comptador i consums en m³ |

---

## 3. Estructura del Projecte i Mapa de Fitxers

```
Dashboard/
├── app.py                         # Router principal canònic, barra superior i Landing interactiva
├── app_v2.py                      # Bridge de compatibilitat transparent per a Streamlit Cloud
├── StartDashboard.py              # Llançador d'escriptori de Windows (Chrome + background sync)
├── auto_scan_ui.py                # Interfície d'escriptori ràpida d'escaneig de tiquets 1-clic
├── scan_winrt.ps1                 # Pont natiu WinRT (Windows.Devices.Scanners) per a l'HP Scanjet
├── scanner.py                     # Controlador d'escaneig (WinRT prioritari + WIA fallback)
├── core/
│   ├── aigua_manager.py           # Gestor de factures i lectures d'aigua (Supabase ID 10)
│   ├── alerts.py                  # Motor centralitzat d'alertes i campaneta de notificacions
│   ├── auth.py                    # Autenticació, sessions i tokens
│   ├── calendar_manager.py        # Gestor de calendari, sincronització iCal i desduplicació
│   ├── config_manager.py          # Gestor de configuració JSON i perfil familiar
│   ├── db.py                      # Connexions CRUD a Supabase, gestió híbrida i offline
│   ├── harness.py                 # Motor de tests IA asíncron en segon pla i informes .txt
│   ├── llm.py / llm_ui.py         # Connectors d'intel·ligència artificial (Gemini, DeepSeek, etc.)
│   ├── llum_manager.py            # Preus PVPC directe, optimitzador d'acumuladors i estudi solar PVGIS
│   ├── manteniment_manager.py     # Gestor de manuals, garanties i tasques de manteniment periòdiques
│   └── ocr_rules.md               # Regles d'extracció de tiquets per supermercat
├── modules/
│   ├── admin.py                   # ⚙️ Configuració global i laboratori IA (Harness)
│   ├── bases_dades.py             # 🗄️ Gestor de taules Supabase en temps real
│   ├── calendari.py               # 📅 Agenda familiar (Graella, Dia, Fet/No fet, mòbil 1 línia)
│   ├── compres.py                 # 🛒 Compres Super (OCR, tiquets, desglossament, rebost, estalvi)
│   ├── cotxe.py                   # 🚗 Km, repostatge, consum i manteniment col·lapsable
│   ├── dashboard.py               # 📊 Dashboard general i KPIs financers
│   ├── domotica.py                # 📶 Integració amb Home Assistant
│   ├── economic.py                # 📈 Previsió despeses/ingressos, nou any, pagues extres, inversions
│   ├── impressora.py              # 🖨️ Controlador d'impressora de tiquets BIXOLON SRP-275APG
│   ├── llum_aigua.py              # 💡 Preus PVPC, acumuladors, factures PDF i simulador solar
│   ├── manteniment.py             # 🛠️ Tasques periòdiques, subtasques, manuals i garanties PDF
│   ├── medicacio.py               # 💊 Control de medicació, pautes i tutelats
│   ├── menjar.py                  # 🍽️ Receptari (base 3), recomanador IA, calories i mise en place
│   ├── seguretat.py               # 📹 Estat de càmeres, accessos i alarmes
│   └── sincronitzacio.py          # 🔄 Consolidació de dades offline retingudes
├── PDF/                           # Magatzem centralitzat de documents en PDF
│   ├── Factures_Aigua/
│   ├── Factures_Llum/             # Dipòsit de factures elèctriques en PDF
│   ├── Garanties/                 # Factures i pòlisses de garantia de la llar
│   └── Manuals/                   # Manuals d'instruccions d'aparells de la llar
├── imatges/
│   ├── Disseny/                   # Logotips XiquiHouse, fons i elements de disseny
│   ├── Eines/                     # Miniatures dels 14 aparells de cuina
│   ├── Productes/                 # Imatges d'articles de compra i rebost
│   └── Receptes/                  # Imatges gastronòmiques oficials 4:3
└── DOCUMENTACIO_ORGANITZADA.md    # Aquest document
```

---

## 4. Mòduls de Prioritat 2: Gestió Econòmica i Compres

### 4.1 Compres Super i Stock (`modules/compres.py`)
Mòdul clau per a la ingesta de tiquets de supermercat, control de despesa d'alimentació, gestió d'estoc del rebost i generació de llistes de compra.

#### A. Escaneig Directe 1-Clic per a HP Scanjet G3110 (`scanner.py`, `scan_winrt.ps1`, `auto_scan_ui.py`)
- **Problema superat (25/10/2026)**: L'antiga llibreria WIA COM provocava bloquejos d'arxiu temporal (`ERROR_SHARING_VIOLATION` / `0x80030070` a `wiaservc.dll`).
- **Solució Natiu WinRT**: Creat [`scan_winrt.ps1`](file:///e:/Dashboard/scan_winrt.ps1) utilitzant l'API moderna UWP/WinRT (`Windows.Devices.Scanners.ImageScanner`), 100% compatible amb l'HP Scanjet G3110.
- **Accés directe d'escriptori (`Escanejar Tiquet.lnk` / `auto_scan_ui.py`)**:
  - Selecció del Supermercat i Data.
  - Botó verd destacat **`🖨️ Escanejar Tiquet`** (sense passos manuals intermedis).
  - Adquireix la imatge del vidre de l'escàner, la converteix automàticament a JPEG d'alta resolució mitjançant Pillow i la desa directament a `tickets/ticket_<super>_<date>.jpg`.

#### B. Motor OCR Intel·ligent amb Gemini Vision
- **Formats admesos**: Imatges (`png`, `jpg`, `jpeg`, `webp`, `bmp`), documents digitals de supermercat (`pdf` amb extracció nativa per `pypdf`) i fitxers de text (`txt`).
- **Models suportats**: `gemini-2.5-flash` (alta velocitat i precisió recomanada) i `gemini-3.8-flash`. Si l'usuari tria visió pura, el selector es filtra automàticament per models multimodals.
- **Regles de súper editables (`core/ocr_rules.md`)**: Accessible des del menú superior "Editar", permet definir instruccions específiques de cada supermercat (Mercadona, Bonpreu, Dia, BonÀrea, etc.) sense alterar el codi font.
- **Quantitats enteres**: Els productes venuts a pes (carn, fruita) retornen sempre quantitat entera = 1 amb l'import final com a preu unitari, evitant fraccions estranyes.

#### C. Fórmula d'Enginyeria Inversa de Descomptes ($PF = B \times (1 - d)$)
Quan l'usuari o l'OCR indiquen un percentatge de descompte (`%`), el camp `TOTAL LÍNIA` representa el **Preu Final realment pagat ($PF$)** que figura al tiquet de caixa:
$$PF = B \times (1 - d) \implies B = \frac{PF}{1 - d}$$
- Modificar el `%` apuja automàticament el `PREU UNIT.` a la Base ($B$) i assigna l'estalvi a `PROMOCIÓ`.
- El `TOTAL LÍNIA` es manté constant i fidel al tiquet.
- Sincronització bidireccional amb gestors `on_change` per a `QUANTITAT` i `PREU UNIT.`, i càlcul invers quan s'escriu la promoció en euros.

#### D. Validació i Sanejament Estricte de Dates (`sanitize_ticket_date`)
- **Blindatge contra errors d'OCR**: Corregeix confusions freqüents en impressores matricials (on `26` es confon amb `76` o `28`).
- **Data mai superior a la data actual**: El selector `st.date_input` i la funció de finalització bloquegen qualsevol data futura (`> date.today()`).
- **Confirmació automàtica si fa més d'una setmana (> 7 dies)**: Si la data detectada té una antiguitat superior a 7 dies, es mostra un avís clar i un diàleg modal (`@st.dialog`) per confirmar la data abans de desar.

#### E. Gestió de Tiquets Pendents de Desglossar i Alertes Globals
- Capçalera compacta en una sola fila horitzontal: Informació del tiquet pendent (`• Nº 8179 — Dia — 6.48 €`) amb el botó `[🛒 Desglossar]` al costat del botó d'upload `[ ⭡ Upload ]`.
- Integració directa amb la campaneta d'alertes superior (`🔔`).
- En finalitzar el desglossament, el tiquet existent a `despeses` s'actualitza via `UPDATE` (`ticketPendent = False`), enllaçant els articles a `compresSuper` sense duplicar claus primàries.

#### F. Auditoria d'Entrada Estricta i Neteja d'Orfes
- Els articles desconeguts de l'OCR ('Pendent') no s'insereixen automàticament a la base de dades; el sistema bloqueja el tiquet fins que l'usuari els hagi categoritzat o esborrat, evitant articles brossa a `tb_noms_producte`.
- Eina **Neteja d'Orfes (OCR)** al menú "Editar" per netejar o enllaçar articles antics.

#### G. Anàlisi d'Estalvi i Gràfics a Estadístiques
- Còmput de promocions d'article (`prom`) i descomptes globals (`descompte`) davant l'import net pagat (`totLinea`).
- Targetes KPI d'estalvi assolit, % de descompte global i supermercat líder en estalvi.
- Gràfic de Donut interactiu (Plotly) de Compra Pagada vs Promoció/Estalvi.

---

### 4.2 Mòdul Econòmic i Dashboard (`modules/economic.py`, `modules/dashboard.py`)

#### A. Dashboard General
- Targetes KPI dels saldos reals actualitzats dels comptes bancaris (BBVA, La Caixa, Trade Republic, Efectiu).
- Gràfic comparatiu de despeses vs ingressos amb finestra temporal de 3 anys (`any-1`, `any`, `any+1`) i projeccions grogues per a mesos futurs.
- Taula de detalls del mes amb selecció interactiva de categories (`st.dataframe` amb `on_select="rerun"` i claus estables).

#### B. Previsió de Despeses i Ingressos
- Taules amb filtratge dinàmic per Any, Mes, Banc i Estat (Pagat/Pendent), amb configuració nativa de columnes (`st.column_config`).
- Modificació d'imports en bloc per a pagaments pendents futurs.

#### C. Generador de Nou Any Comptable i Pagues Extres (Modal Interactiu)
- Accessible des del menú superior: `Mòduls > Mòdul Econòmic > 📅 Afegir nou any comptable`.
- Permet revisar i editar els imports per defecte dels conceptes abans de generar els 12 mesos de l'any següent (ex. 2027).
- **Pestanya Pagues Extres**: Programa automàticament les tres pagues (Pensió Enric, Pensió Isabel i Pensió no contributiva) per als mesos de juny i novembre (dia 25), heretant els imports mensuals i integrant-se a la xifra anual d'ingressos.

#### D. Ingrés / Despesa General i Traspassos entre Comptes
- Formulari ràpid de despeses, ingressos, gasolina i traspassos.
- **Traspassos entre comptes (`op_banc`)**: Incorpora el camp "Quantitat al banc de destí (€)" configurable amb càlcul visual de la diferència, per reflectir quan un traspàs no és íntegre o té retencions.
- Neteja del desglòs mitjançant el filtre `grup != op_banc` per no duplicar visualment operacions tècniques a la cartera.

#### E. Inversions (TR Cartera) i Estalvis (`estalviDP`)
- Seguiment de posicions en valors (S&P500, NVIDIA) amb filtres per Any, Mes i Concepte.
- Evolució del fons d'estalvi familiar amb gràfics interactius d'aportacions i rescats.

---

## 5. Mòduls de Prioritat 3: Subministraments i Manteniment de la Llar

### 5.1 Llum i Aigua (`modules/llum_aigua.py`)

#### A. Subministrament Elèctric (⚡ Consum Llum)
- **Preus PVPC / Bo Social en Directe**: *Scraper* automatitzat a `tarifaluzhora.es` amb canal de contingència (*fallback*) a l'API de Red Eléctrica de España (`apidatos.ree.es`). Mètriques de preu actual amb distintiu de tram (🟢 Vall, 🟡 Pla, 🔴 Punta), preu mitjà, hora més barata i hora més cara.
- **Gràfic Horari de 24 Hores (Plotly)**: Visualització interactiva de la corba de preus amb barres acolorides per tram tarifari 2.0TD.
- **Doble Optimitzador Independent d'Acumuladors de Calor**:
  - *Acumulador Menjador (4.000 W)*: Finestra recomanada nocturna (00:00 - 08:00 h, tram Vall) per aprofitar els 5,5 kW contractats a la nit.
  - *Acumulador Passadís 2a Planta (2.000 W)*: Finestra recomanada al migdia solar (11:00 - 19:00 h) per aprofitar els 4,4 kW de dia sense sobrepassar l'ICP.
  - Selector d'hores necessàries independent per a cadascun, amb persistència a `data/acumuladors_config.json`.
- **Registre de Factures Elèctriques i Ingesta PDF Automàtica**:
  - Botó ràpid `📄 Nova factura llum` amb càrrega de PDF i extracció OCR/Regex automàtica de número, període, import i kWh per tram (P1, P2, P3).
  - Dipòsit de factures elèctriques en PDF a PDF/Factures_Llum/ amb consolidació de consums i imports a Supabase ID 9.
  - Visor interactiu de PDF basat en PDF.js (HTML5 Canvas).
  - Gràfic mensual de barres apilades amb els preus totals en negreta situats a la cota superior sense solapar els colors dels trams.

#### B. Subministrament Hídric (💧 Consum Aigua)
- Registre de factures d'aigua, lectures de comptador i consums en m³.
- Dipòsit de factures a `PDF/Factures_Aigua/` amb visor integrat PDF.js i sincronització a Supabase ID 10.
- Gràfics històrics d'evolució de consum en m³ i cost per factura.

#### C. Simulador Estudi Solar PVGIS (☀️ Estudi Solar)
- Model de radiació solar personalitzat amb dades oficials de PVGIS per a la ubicació d'Arbúcies (La Selva, Girona), aplicant les HSP (Hores de Sol Pic) reals de cada mes.
- Simulador interactiu amb paràmetres dinàmics:
  - Nombre de plaques solars (de 6 a 20 mòduls monocristal·lins de 450W).
  - Orientació de coberta (29° Nord-Est teulada actual, Est-Oest doble vessant o Sud òptim).
  - Bateries de liti (0, 5, 10 o 15 kWh).
  - Derivació d'excedents als acumuladors tèrmics (6.000 W totals).
- Contrast en temps real contra el consum elèctric anual real extret de l'històric de factures registrades.
- **Anàlisi jurídica i econòmica del Bo Social**: Contrast del descompte del 80% (consumidor vulnerable sever) enfront dels límits legals de compensació d'excedents de l'art. 14 del RD 244/2019 (els excedents només descompten el terme d'energia de la factura, sense reduir el terme de potència ni el Bo Social).
- Comparativa de pressupost "Clau en mà" vs modalitat "Mixta / DIY" i guia de seguretat per a teulada de teules corbes (ganxos salva-teules sense perforació).

---

### 5.2 Manteniment de la Llar (`modules/manteniment.py`)

#### A. Registre de Manteniment i Tasques Periòdiques
- **Camps normalitzats**: `idManteniment`, `dataManteniment`, `feina` (feina concreta), `tipus` (`Reparació`, `Manteniment`, `Feina casa`, `Altres`), `alertaA` (multiselecció de membres o "Tothom"), `diesAvis` (antelació configurable per a l'avís a la campaneta), `acompliment` (`Sí`/`No`) i `observacions`.
- **Selector de Periodicitat**:
  - Opcions: Puntual, Diària, Setmanal, Quinzenal, Mensual, Bimestral, Trimestral, Semestral, Anual o Personalitzada.
  - Límit de generació configurable: Per nombre de vegades o `"Fins a final d'any (31/12)"`.
  - Generació en sèrie (`serie_id`) amb etiqueta descriptiva `🔁 Periodicitat (X/N)`.
  - En editar una tasca, opció per actualitzar i regenerar en bloc les properes tasques pendents de la sèrie respectant les ja acomplertes.
- **Subtasques amb Cadència Pròpia (`subtasques_template`)**:
  - Permet crear subtasques amb ritme propi dins d'una tasca periòdica (ex: "Rentar protector de llençols" cada 6 mesos dins de "Canvi de llençols" cada 15 dies).
  - Checklist interactiu a les targetes amb recompte de progrés (`📋 Subtasques (1/2)`).
  - Sincronització automàtica: en completar la tasca principal es completen les subtasques, i en completar totes les subtasques es marca la tasca principal.
- **Generador de Tasques del Proper Any (Modal Interactiu)**:
  - Accessible des del menú superior: `Mòduls > Manteniment de la llar > 📅 Generar tasques proper any`.
  - Proposa automàticament el proper any i genera en bloc les tasques recurrents de la llar sincronitzant-les amb el calendari familiar.
- **Neteja del formulari**: Comptador de versió dinàmic (`mant_form_count`) que reinicialitza tots els camps després de desar. Desacoblament de la tecla `Enter` als diàlegs modals per evitar enviaments involuntaris.

#### B. Gestió Documental de la Llar: Manuals i Garanties
- Subcarpetes físiques dedicades: `PDF/Manuals/` i `PDF/Garanties/`.
- Registre JSON centralitzat (`data/manteniment_docs.json`) sincronitzat a Supabase ID 7.
- **Visor interactiu basat en PDF.js (HTML5 Canvas)**: Renderització neta sense bloquejos d'iframe a Chrome, amb controls de zoom, pàgines i descàrrega.
- **Seguiment semafòric de garanties**: Càlcul de dies de cobertura restants (🟢 Vigents, ⚠️ Venciment en menys de 60 dies, 🔴 Caducades).
- **Auto-detecció de fitxers**: Si s'afegeix un PDF directament a les carpetes del disc, el motor l'adhereix automàticament al registre JSON sense sobreescriure les entrades existents.

---

### 5.3 Cotxe i Mobilitat (`modules/cotxe.py`)

#### A. Registre de Km, Repostatge i Consum
- `🛣️ Registre Km i Rutes`: Càlcul automàtic de km per lectura d'odòmetre amb plantilles de rutes habituals.
- `⛽ Repostatge`: Taula de proveïments de la BBDD `gasolina` amb mètriques de preu més alt, més baix i últim proveïment.
- `📊 Consum`: Gràfic de consum mitjà (L/100km).

#### B. Manteniment Integral Col·lapsable (Arquitectura 25/10/2026)
Totes les seccions estan organitzades en blocs desplegables independents (`st.expander`) per mantenir la interfície compacta, amb interruptor superior *"Desplegar totes les seccions"* i badges informatius en temps real als encapçalaments:
1. **`🛢️ Canvi d'Oli`**: Km actuals, límit de canvi, km restants i barra de desgast.
2. **`🛞 Canvi de Rodes`**: Substitució de cobertes davanteres, posteriors o completes amb alertes per quilometratge.
3. **`💨 Inflat de Rodes`**: Pressió en bar, dates de revisió periòdica i vinculació a viatges llargs.
4. **`🧪 Control de Nivells`**: Secció independent per al seguiment dels líquids del vehicle (oli de motor, líquid refrigerant, líquid de frens i eixugaparabrises) amb planificacions per km i per dies.
5. **`🛠️ Taller i Avaries`**: Entrades per manteniment, ITV, avaries o reparacions amb control d'estat (Resolt, Pendent, En taller).
6. **`📋 Històric de Manteniment i Taller`**: Taula interactiva amb filtratge per tipus, càlcul de la despesa total acumulada (€) i eines d'edició.

---

## 6. Mòduls de Prioritat 4: Família, Nutrició i Benestar

### 6.1 Menús i Cuina (`modules/menjar.py`)

#### A. Base de Dades del Receptari (`tb_receptes_pro`)
- Catàleg complet de 194 receptes estructurades amb ingredients, instruccions pas a pas i *mise en place*.
- **Racions de referència (Base 3)**: Totes les quantitats de la base de dades estan calculades estrictament per a **3 persones** (nucli familiar).

#### B. Motor d'Escalat Dinàmic de Comensals (`scale_ingredients`)
- Algoritme Regex que processa quantitats, unitats i fraccions (`250g`, `4 ous`, `1/2 cullerada`, `1.5 kg`) aplicant la fórmula:
  $$\text{Quantitat Recalculada} = \text{Quantitat Base} \times \frac{\text{Comensals}}{3}$$
- Els ingredients no quantificables linealment (*sal i pebre al gust*, *branquetes d'herbes*) es mantenen invariables.
- Selector interactiu a la fitxa de la recepta que permet simular quantitats a temps real d'1 a 30 persones.

#### C. Pautes Estètiques de Fotografia Gastronòmica
- Angle elevat a 45° en primer pla (Close-up) en proporció **4:3**. Taula rústica de fusta, llum natural càlida i fidelitat absoluta als ingredients reals.

#### D. Perfils Familiars, Al·lèrgies Mèdiques vs Vetos Personals
- **Al·lèrgia mèdica**: Bloqueig estricte de la recepta per a tota la família.
- **Veto personal**: Quan un membre no consumeix un aliment (ex. fetge o bledes) però la família sí, el planificador no bloqueja el plat i assigna automàticament un **plat alternatiu ràpid comodí** (ex. pit de pollastre a la planxa o truita francesa) per a aquell membre, compartint la mateixa guarnició.

#### E. Recomanador de Menús Intel·ligent amb Gemini
- Generació setmanal considerant membres actius, eines disponibles a la cuina, regles de salut (carns vermelles, freqüència de peix i llegums) i no-repetició d'hidrats consecutius.
- **Control dietètic de calories**: Fixació de límit calòric separat per a dinars i sopars, prioritzant receptes amb puntuació de salut alta i balancejant macronutrients amb `tags_nutricionals`.
- **Anti-repetició estricta**: Llegeix `tb_historial_menjars` i prohibeix repetir plats consumits en els darrers X dies (per defecte 15 dies).
- **Priorització per valoració**: Afavoreix les receptes amb 4 i 5 estrelles.
- **Bústia de Peticions (`tb_peticions_menjar`)**: Permet als membres sol·licitar plats desitjats que, un cop acceptats pel responsable, s'injecten obligatòriament al proper menú.

#### F. Mise en Place de Diumenge (Batch Cooking) i Connexió amb l'Stock
- Derivació automàtica de preparacions base (caldos, sofregits, verdures rostides).
- Si hi ha brous o sofregit congelats a l'estoc, es descompten de la preparació de diumenge i de la llista de la compra:
  $$\text{Compra} = \max(0, \text{Necessari} - \text{Stock})$$

---

### 6.2 Agenda i Calendari Familiar (`modules/calendari.py`, `core/calendar_manager.py`)

#### A. Vistes del Calendari
- **Vista Graella Mensual (Estil Google Calendar)**: Graella interactiva responsive amb xips de colors per membre familiar i categoria, comptadors diaris i navegació fluida.
- **Vista Llista / Agenda**: Llistat cronològic estricte del mes seleccionat, resolent errors d'antiguitat d'anys anteriors.
- **Consulta i Gestió del Dia**: En fer clic a qualsevol dia de la graella, es mostren a sota tots els esdeveniments d'aquell dia amb accions completes i formulari directe per afegir-hi noves tasques.

#### B. Control d'Acompliment (Fet / No Fet)
- Cada esdeveniment disposa de dos botons interactius:
  - **Check verd (`✅`)**: Marca com a feta la tasca (il·luminació verda maragda sòlida `#10b981`, prefix `✅ ` al títol i insígnia `FET`).
  - **Creu vermella (`❌`)**: Marca com a no feta o cancel·lada (il·luminació vermella viva `#ef4444`, prefix `❌ ` i text ratllat).
- Persistència a Supabase `app_config` ID 3 amb clau triple (ID esdeveniment, UID iCal i títol normalitzat).

#### C. Sincronització iCal Bidireccional i Desduplicació
- Connexió amb feeds de Google Calendar de cada membre familiar.
- Algoritme `deduplicate_events` per evitar duplicats per concurrència i gestió canònica d'excepcions de recurrències (`RECURRENCE-ID`).

#### D. Disseny Compacte en 1 Sola Línia Horitzontal per a Mòbils
- Regles CSS flexbox amb `:has(.cal-action-btn)` que forcen els 5 botons d'acció (`✔️`/`✅`, `✖️`/`❌`, `✏️`, `🗑️`, `📅 GCal`) a romandre sempre en una sola fila horitzontal, eliminant l'apilament vertical en pantalles de telèfon mòbil.

---

### 6.3 Control de Medicació (`modules/medicacio.py`)
- Pautes mèdiques de cada membre familiar i tutelats.
- Vista de preses d'avui i supervisió d'horaris.
- Gestió de la farmaciola de la llar amb sincronització a Supabase `app_config` ID 5.

---

### 6.4 Seguretat i Domòtica (`modules/seguretat.py`, `modules/domotica.py`)
- `modules/seguretat.py`: Estat de càmeres, accessos i alarmes de la llar.
- `modules/domotica.py`: Integració amb instàncies locals de Home Assistant, llums i sensors.

---

## 7. Mòduls de Prioritat 5: Administració, Nucli i Serveis Transversals

### 7.1 Configuració Global (`modules/admin.py`, `core/config_manager.py`)
- `👤 Administrador`: Dades de contacte, avatar i PIN mestre.
- `🏷️ Títol de la casa`: Personalització de text, colors i mida.
- `👨‍👩‍👧‍👦 Família`: Membres de la llar amb data de naixement europea (`DD/MM/AAAA`), edat automàtica, telèfon mòbil, al·lèrgies mèdiques, vetos personals, plats comodí favorits i commutador de presència (`🟢 Present` vs `⚪ Fora`). Neteja d'estat de sessió (`f_`) en desar per forçar la lectura neta des de `core/config.json`.
- `🍳 Aparells i Eines de Cuina`: Selector visual dels 14 estris de cuina clau (`forn`, `microones`, `airfryer`, `bascula`, `minipimer`, `batedora_vas`, `motlles_silicona`, `olla_pressio`, `liquadora`, `tallafiambres`, `robot_cuina`, `picadora`, `sifo_n2o`, `mandolina`) amb miniatures homogènies i ampliació modal interactiva.
- `🤝 Tutelats`, `🏦 Bancs`, `🎨 Aspecte i Tema`, `🔘 Icones d'inici`, `🌐 Idiomes`.

---

### 7.2 Laboratori IA - Harness (`core/harness.py`)
- **Dataset mestre**: 11 casos de prova exhaustius a `data/harness_menu_cases.json`.
- **Execució Asíncrona en Segon Pla**: Permet llançar bateries de proves sense bloquejar la navegació de l'aplicació, monitorant el progrés a `data/harness_status.json`.
- **Avaluadors deterministes**: Tolerància 0 a al·lèrgens (amb filtre previ de termes segurs com `sense lactosa` o `formatge vega` per evitar falsos positius), verificació de plats alternatius per vetos, control d'hidrats consecutius i compliment d'aparells absents.
- **Exportació d'informes en format Text (.txt)**.
- **Models suportats**: `gemini-2.5-flash` (recomanat), `gemini-3.8-flash`, `gemini-3.6-flash`. Retirat el paràmetre obsolet `thinkingBudget` per millorar la latència.

---

### 7.3 Gestió de Bases de Dades i Sincronització Offline (`modules/bases_dades.py`, `modules/sincronitzacio.py`)
- **Gestor de Bases de Dades (`modules/bases_dades.py`)**: Accessible des del menú superior, permet visualitzar i editar en temps real (inserir, modificar i esborrar) totes les taules de Supabase mitjançant `st.data_editor`, amb ordenació cronològica real per data i clau primària.
- **Consolidar Dades Offline (`modules/sincronitzacio.py`)**: Visualitza i puja en bloc a Supabase totes les mutacions locals retingudes a la cua `sync_queue.json` durant caigudes d'internet.

---

### 7.4 Sistema Global d'Alertes (`core/alerts.py`)
- **Campaneta de Notificacions Global (`🔔`)**: Ubicada permanentment a la barra superior desplegable i a la pantalla d'inici amb recompte en temps real.
- **Alertes monitorades**:
  - Tiquets de súper pendents de desglossar (`ticketPendent = True`).
  - Tasques de manteniment de la llar pendents o vençudes amb `diesAvis` configurables i assignació a membres.
  - Canvis d'oli, revisió de rodes, nivells de líquids i ITV del cotxe.
  - Venciment de garanties de productes de la llar (menys de 60 dies).
  - Participacions de loteria i avisos familiars.
- **Optimització**: Memòria cau temporal de 60 segons a `app.py` i reutilització directa dels DataFrames actius de la sessió.

---

### 7.5 Impressora de Tiquets BIXOLON SRP-275APG (`modules/impressora.py`)
- Connexió Paral·lel Centronics a USB xip CH340 al port `USB001` de Windows (controlador `Generic / Text Only`).
- Suport dual:
  - **RAW ESC/POS en local**: Impressió directe via USB amb tall automàtic de paper (`\x1dV\x00`), 6 salts de línia de marge de seguretat i padding de 30mm per superar la distància física entre el capçal i la guillotina.
  - **Impressió web neta**: Compatible amb Streamlit Cloud mitjançant `window.print()` estilitzat per a rotlle de 76mm.
- Integració neta exclusivament al desplegable de cada supermercat a la Llista de la Compra.

---

## 8. Annex: Historial de Canvis Recents Consolidat (Setembre - Octubre 2026)

| Data | Mòdul Afectat | Descripció del Canvi Consolidat |
|:---|:---|:---|
| **25/10/2026** | **Escaneig Tiquets** | **Restauració escaneig directe 1-clic**: Nou motor natiu WinRT ([`scan_winrt.ps1`](file:///e:/Dashboard/scan_winrt.ps1)) per a HP Scanjet G3110, superant l'error de bloqueig temporal WIA (`ERROR_SHARING_VIOLATION` / `0x80030070`). Eliminats botons secundaris a [`auto_scan_ui.py`](file:///e:/Dashboard/auto_scan_ui.py) deixant només `🖨️ Escanejar Tiquet`. |
| **25/10/2026** | **Cotxe / Manteniment** | **Seccions Col·lapsables**: Totes les seccions de la pestanya *Manteniment* transformades en blocs plegables independents (`st.expander`) amb badges informatius en temps real als encapçalaments i control de desplegament global. |
| **24/10/2026** | **Rendiment Core** | **Pla d'optimització de 30 dies**: Finestra activa de 30 dies a Supabase + arxiu històric en CSV amb memòria cau de 24h per a `despeses` i `compresSuper`. Eliminats els buidats massius de cau, passant de bloquejos de 20s a càrregues en menys d'1s. |
| **24/10/2026** | **Compres Super** | **Model Matemàtic de Preu Final Fix ($PF = B \times (1 - d)$)**: Enginyeria inversa de promocions a la càrrega manual de línies, mantenint el Total Línia invariable i sincronitzat amb el tiquet de caixa. |
| **24/10/2026** | **Llum i Aigua** | **Estudi Solar PVGIS i Acumuladors**: Integrat simulador fotovoltaic a Arbúcies amb Bo Social (80%), desdoblament d'acumuladors 4000W/2000W amb persistència a `data/acumuladors_config.json`, i ingesta històrica de factures elèctriques en PDF. |
| **23/10/2026** | **Llum i Aigua** | **Creació del Mòdul '💡 Llum i Aigua'**: Preus PVPC horaris en directe, gestió de factures elèctriques i d'aigua amb visor natiu PDF.js i sincronització a Supabase IDs 9 i 10. |
| **22/10/2026** | **Cotxe** | **Control de Nivells**: Secció independent per a la revisió de líquids (oli, refrigerant, frens, eixugaparabrises) amb planificacions i alertes per km i temps. |
| **22/10/2026** | **Agenda** | **Control Fet/No Fet i Mòbil 1 Línia**: Botons interactius `✅`/`❌` amb colors sòlids vibrants i regles CSS `:has(.cal-action-btn)` per mantenir les 5 accions en una sola fila horitzontal a telèfons mòbils. |
| **21/10/2026** | **Manteniment Llar** | **Tasques Periòdiques i Subtasques**: Generació en sèrie de tasques recurrents, subtasques amb cadència pròpia i generador interactiu de tasques per al proper any al menú superior. |
| **19/10/2026** | **Manteniment Llar** | **Gestió Documental (Manuals i Garanties)**: Dipòsit de documents PDF amb visor interactiu HTML5 Canvas (PDF.js) i semàfor de venciment de garanties. |
| **18/10/2026** | **Econòmic / Compres** | **Navegació Nativa per Pestanyes**: Ús del paràmetre natiu `default` a `st.tabs`, creació de botons túnel bidireccionals i quantitat editable a destí per a traspassos de comptes. |
| **17/10/2026** | **Compres Super** | **Blindatge de Dates i Suport PDF**: Sanejament de dates contra errors matricials d'OCR, bloqueig de dates futures, extracció nativa de PDFs de supermercat amb `pypdf` i nou model `gemini-3.8-flash`. |
| **16/10/2026** | **Econòmic** | **Pagues Extres i Nou Any Comptable**: Incorporació de pagues extres (juny/novembre) i selector d'anys a 3 bandes ([any-1, any, any+1]) amb projeccions grogues. |
| **16/10/2026** | **Impressora** | **BIXOLON SRP-275APG**: Integració d'impressió RAW ESC/POS de tiquets de compra amb tall de paper i vista d'impressió web. |
| **18/09/2026** | **Nucli / BBDD** | **Arquitectura Offline**: Mode desconnectat amb cua local `sync_queue.json` i mòdul de consolidació de dades. |
| **13/09/2026** | **BBDD / Interfície** | **Gestor de Bases de Dades**: Creació de `modules/bases_dades.py` i barra de navegació superior d'escriptori amb 4 menús clàssics. |
