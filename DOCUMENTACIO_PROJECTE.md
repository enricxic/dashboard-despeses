# Documentació del Projecte: Dashboard Despeses - XiquiHouse

Aquest document descriu l'arquitectura, funcionalitats, estructura de fitxers i regles de l'aplicació per assegurar que qualsevol nova sessió o agent d'IA entengui el context immediatament sense dependre de la memòria de converses anteriors.

---

## 1. Visió General i Arquitectura Modular
L'aplicació utilitza una **arquitectura modular consolidada**, neta, extensible i optimitzada per a mòbils i escriptori.
- **Frontend / Backend**: Construïda en **Streamlit** (Python).
- **Arquitectura de Xarxa Dual**: 
  - **Cloud-First**: Per defecte, l'arrencador de l'escriptori (`StartDashboard.py`) obre la versió del núvol de forma instantània si hi ha internet.
  - **Sincronització de Fons**: Mentre s'obre el núvol, un procés silenciós (`scripts/update_csvs_background.py`) actualitza totes les dades al disc dur local (CSV) mitjançant una connexió directa i ultra-ràpida a PostgreSQL (buidant i descarregant tot sense els límits de paginació de l'API REST) per tenir una Font de Veritat íntegra i actualitzada localment.
  - **Emergency Offline Mode**: Si no hi ha internet s'engega l'entorn local Streamlit automàticament (i de forma instantània) llegint exclusivament dels CSVs locals, amb càrrega de taules a la carta (Lazy Loading) per maximitzar la velocitat. (Per forçar-ho tot i tenir connexió, simplement desconnecta el Wi-Fi abans de fer doble clic).
- **Entrada Principal (Router Canònic)**: L'arxiu **[`app.py`](file:///e:/Dashboard/app.py)** actua com a menú principal (Landing Screen interactiva) i gestor de navegació global.
- **Bridge de Compatibilitat**: L'arxiu **[`app_v2.py`](file:///e:/Dashboard/app_v2.py)** actua com a *forwarder* transparent per garantir compatibilitat amb desplegaments de Streamlit Cloud.
- **Arxiu Històric**: L'antic fitxer monolític de 6.700 línies es conserva a [`legacy/app_monolithic_legacy.py`](file:///e:/Dashboard/legacy/app_monolithic_legacy.py).
- **Barra Superior de Menús (Estil Tradicional d'Escriptori)**: Dins de qualsevol mòdul, es disposa d'un menú superior clàssic (`Arxiu`, `Finances`, `Llar`, `Família`, `Ajustos`, `Ajuda`) amb submenús desplegables per activar directament qualsevol secció o acció de l'aplicació.
- **Interfície Gràfica d'Inici**: Mostra un logotip interactiu transparent (`imatges/logo xiquiHouse.png`) sobre un fons complet de pantalla (`imatges/fons xiquiHouse.jpg`), amb 12 punts d'accés interactius mapejats.
- **Base de Dades**: **Supabase** (PostgreSQL) com a mestre i **CSV** com a font local d'emergència. Tota la comunicació CRUD està centralitzada a `core/db.py`. L'arrencada local integra un tallacorrents de 3 segons si PostgreSQL està bloquejat pel proveïdor d'internet, passant automàticament a l'API REST.
- **Autenticació**: Gestionada a `core/auth.py`. Incorpora persistència de sessió mitjançant paràmetre de consulta (`?auth=<token>`).
- **Estat de Navegació**: Es controla mitjançant `st.session_state.current_module`. Per tornar enrere, cada mòdul disposa del botó `🏡 Inici` a la barra superior i `🔙 Tornar a l'inici` a la capçalera que restableix l'estat a `None`.

---

## 2. Mapa de Navegació i Mòduls de la Pantalla d'Inici

La pantalla d'inici mapeja 12 icones interactives sobre el logotip de XiquiHouse:

### 🌟 Part Superior (Sense rodona):
1. **⚙️ Configuracions**: `modules/admin.py` *(Icona engranatge)* - Panell de control i configuració global:
   - `👤 Administrador`: Dades de contacte, avatar i PIN mestre.
   - `🏷️ Títol de la casa`: Paraules, colors i tamany del títol d'inici.
   - `👨‍👩‍👧‍👦 Família`: Membres de la llar amb data de naixement europea (`DD/MM/AAAA`), recàlcul automàtic d'edat en anys, al·lèrgies mèdiques (bloqueig estricte), vetos/aversions personals (desdoblament), plats comodí favorits i interruptor d'activació (`🟢 Present a la llar` vs `⚪ Fora de la llar`).
   - `🍽️ Menús i Nutrició`: 
     * Regles de salut (màxim carns vermelles, mínim peix i llegums, màxim sopars d'embotits), control d'hidrats consecutius, disponibilitat del forn i format de planificació.
     * **🍳 Aparells i Eines Disponibles**: Selector visual amb 14 eines de cuina clau (`forn`, `microones`, `airfryer`, `bascula`, `minipimer`, `batedora_vas`, `motlles_silicona`, `olla_pressio`, `liquadora`, `tallafiambres`, `robot_cuina`, `picadora`, `sifo_n2o`, `mandolina`) amb miniatures d'estudi homogènies i ampliació modal interactiva   - `🧪 Laboratori IA (Harness)`: Banc de proves integrat per avaluar la precisió, seguretat d'al·lèrgies mèdiques, gestió de vetos i adaptació a l'equipament dels models Gemini, amb **execució en segon pla (asíncrona)** i **descàrrega d'informes en format Text (.txt)**.
   - `🤝 Tutelats`, `🏦 Bancs`, `🎨 Aspecte i Tema`, `🔘 Icones d'inici`, `🌐 Idiomes`.
2. **📊 Dashboard General**: `modules/dashboard.py` *(Icona pantalla + gràfic)* - Vista de panell principal amb targetes de saldos bancaris (BBVA, La Caixa, etc.), resum mensual d'ingressos i despeses de l'any i gràfics comparatius.

### 🔵 Part Esquerra (5 nodes amb rodona):
3. **📈 Mòdul Econòmic**: `modules/economic.py` *(Icona gràfic ascens)* - Gestió econòmica i financera organitzada en pestanyes especialitzades:
   - `📈 Detalls del Mes`: Saldos bancaris, rebuts, pagaments, hipoteca, taula anual i gràfic comparatiu de barres amb previsions vs real.
   - `🔴 Prev. Despeses`: Formulari d'alta i llistat de previsions de despeses amb recurrència mensual.
   - `🟢 Prev. Ingressos`: Formulari d'alta i llistat de previsions d'ingressos amb recurrència mensual.
   - `📈 Inversions`: Formulari de moviments de TR Cartera (S&P500, NVIDIA), KPIs i taula d'inversions.
   - `💰 Estalvis`: Fons d'estalvi `estalviDP`, quotes, aportacions, rescats i gràfic interactiu d'evolució del capital acumulat.
   - `🤖 Xat IA`: Assistent financer intel·ligent Gemini.
4. **📹 Seguretat**: `modules/seguretat.py` *(Icona càmera)* - Estat de càmeres, accessos i alarmes.
5. **🛠️ Manteniment**: `modules/manteniment.py` *(Icona casa amb eina)* - Tasques de la llar, reparacions i històric de manteniment.
6. **📶 Domòtica**: `modules/domotica.py` *(Icona WiFi)* - Integració amb Home Assistant, llums i sensors.
7. **🎲 Jocs**: `modules/jocs.py` *(Icona daus)* - Oci familiar, inventari de jocs i marcadors.

### 🟢 Part Dreta (5 nodes amb rodona):
8. **📅 Agenda**: `modules/calendari.py` *(Icona calendari)* - Calendari familiar, esdeveniments i sincronització.
9. **💊 Control Medicació**: `modules/medicacio.py` *(Icona pastilles / flascó)* - Pautes mèdiques, dosis, horaris i farmaciola.
10. **🍽️ Menús i Cuina**: `modules/menjar.py` *(Icona coberts)* - Gestió gastronòmica i nutricional intel·ligent:
    - `🧠 Recomanador de Menús`: Generació setmanal amb IA (`gemini-2.5-flash`) seguint al·lèrgies mèdiques strictly, desdoblament de vetos personals (assignació automàtica de plat comodí sense imposar-lo a la resta), regles de freqüència nutricional (carn vermella, peix, llegums, hidrats no consecutius), eines de cuina disponibles i membres actius/fora de la llar.
    - `📲 Consens Familiar per WhatsApp`: Botó d'un sol clic (`wa.me/?text=...`) per compartir el resum del menú amb el grup familiar abans de validar la compra.
    - `⏱️ Batch Cooking & Mise en Place`: Guia de preparacions base de diumenge (patates probiòtiques amb midó resistent, brous concentrats, sofregits) i sincronització d'ingredients a comprar.
    - `📖 Llibre de Receptes`: Escalat automàtic d'ingredients per nombre de comensals (base 3) i valoració d'estrelles (0-5) per membre de la família.
    - `➕ Afegir Recepta`: Formulari amb càrrega d'imatges a Supabase Storage (`imatges-receptes`).
11. **🚗 Cotxe**: `modules/cotxe.py` *(Icona cotxe)* - Gestió del vehicle organitzada en pestanyes:
    - `🛣️ Registre Km i Rutes`: Formulari per registrar lectures d'odòmetre, càlcul automàtic de km del trajecte, selector/plantilles de rutes i taula d'històric.
    - `⛽ Repostatge`: Taula històrica de proveïments de la BBDD `gasolina` (alimentada des d'Ingressos/Despeses) amb mètriques de preu últim repostatge, preu més alt i més baix.
    - `🔧 Canvi d'Oli`: Seguiment de km actuals, límit de canvi d'oli i km restants.
    - `📊 Consum`: Gràfic de consum anual L/100km.
12. **🛒 Ingressos i Despeses**: `modules/compres.py` *(Icona carro de compra)* - Gestió integral d'ingressos, despeses i compres:
    - `📄 Compres Super`: Escàner OCR intel·ligent amb suport total de Gemini Vision. Incorpora un sistema de **Regles de Súper Editables (`core/ocr_rules.md`)** des del menú superior, permetent ensenyar a la IA com llegir ofertes o estructures de tiquets específiques de cada cadena (Mercadona, Bonpreu, Dia, etc.) sense programar codi. Inclou mecanismes estrictes per forçar quantitats enteres.
    - `📝 Ingrés / Despesa General`: Formulari directe de **Moviments Reals** (Despesa, Ingrés, Traspàs), proveïment de gasolina amb calculadora, tiquets pendents i taula d'últims moviments.
    - `📋 Llista de la Compra`: Llista de productes sota stock mínim i peticions puntuals.
    - `📦 Rebost / Stock`: Inventari de productes del rebost i control d'existències.
    - `📊 Estadístiques`: Gràfics i mètriques de despesa en supermercats.

---

## 3. Estructura del Projecte

```
Dashboard/
├── app.py                    # Router principal canònic i Landing Page interactiva (amb hot-reload)
├── app_v2.py                 # Forwarder bridge transparent per a Streamlit Cloud
├── core/
│   ├── auth.py               # Autenticació amb contrasenya i token hash
│   ├── db.py                 # Connexió i operacions CRUD a Supabase
│   ├── config_manager.py     # Gestor de configuració JSON i perfil familiar (Ruta absoluta garanteix focalització a core/config.json)
│   ├── config.json           # Configuració de categories, comptes, família, eines i paràmetres
│   ├── ocr_rules.md          # Regles personalitzades per supermercat enviades al prompt de Gemini
│   └── harness.py            # Motor d'avaluació IA, execució asíncrona en segon pla i generador d'informes .txt
├── data/
│   ├── harness_menu_cases.json # Banc d'11 casos de prova exhaustius per al test de menús
│   └── harness_status.json     # Estat de progrés en temps real per a l'execució de proves en segon pla
├── imatges/
│   ├── logo xiquiHouse.png   # Logotip interactiu transparent (1024x682)
│   ├── fons xiquiHouse.jpg   # Fons de pantalla complet per a la Home
│   ├── forn.png              # Miniatura d'estudi forn
│   ├── airfryer.png          # Miniatura d'estudi airfryer
│   └── ...                   # Imatges de les eines de cuina
├── legacy/
│   └── app_monolithic_legacy.py # Arxiu històric del fitxer monolític original (6.700 línies)
├── modules/
│   ├── admin.py              # ⚙️ Configuració global i 🧪 Laboratori IA (Harness)
│   ├── calendari.py          # 📅 Agenda familiar (Google Calendar sync & events)
│   ├── compres.py            # 🛒 Compres Super (OCR), Ingressos/Despeses reals, Llista compra, Rebost i Stats
│   ├── cotxe.py              # 🚗 Registre km/rutes, Repostatge, Canvi d'oli i Consum
│   ├── dashboard.py          # 📊 Dashboard general
│   ├── domotica.py           # 📶 Domòtica (Home Assistant)
│   ├── economic.py           # 📈 Detalls mes, Prev. Despeses, Prev. Ingressos, Inversions, Estalvis i Xat IA
│   ├── jocs.py               # 🎲 Jocs i oci
│   ├── manteniment.py        # 🛠️ Manteniment i reparacions
│   ├── medicacio.py          # 💊 Control de medicació i tutelats (Pla de dosificació & sync)
│   ├── menjar.py             # 🍽️ Receptari (Escalat base 3), Planificador IA i Batch Cooking
│   ├── ofertes.py            # 🔍 Comparador d'Ofertes i Visor de Fulletons (Mercadona, Aldi, etc.)
│   ├── seguretat.py          # 📹 Seguretat i càmeres
└── DOCUMENTACIO_PROJECTE.md  # Aquest document
```

---

## 4. Receptari, Escalat de Comensals i Menús (`modules/menjar.py`)

### 4.1 Base de dades del Receptari (`tb_receptes_pro`)
- **Estat complet (194/194 receptes):** Totes les receptes registrades a Supabase disposen de títol, categoria, ingredients, instruccions pas a pas i *mise en place*.
- **Racions de referència (Base 3):** Totes les quantitats emmagatzemades a la base de dades estan estrictament calculades per a **3 persones** (nucli familiar estàndard).

### 4.2 Motor d'Escalat Dinàmic (`scale_ingredients`)
- Algoritme intel·ligent amb Regex capaç de parsejar quantitats numèriques, unitats i fraccions (`250g`, `4 ous`, `1/2 cullerada`, `3-4 carxofes`, `1.5 kg`) i aplicar el factor:
  $$\text{Quantitat Recalculada} = \text{Quantitat Base} \times \frac{\text{Comensals Seleccionats}}{3}$$
- Els elements no quantificables linealment (*Sal i pebre al gust*, *1 raig d'oli d'oliva*, *branquetes d'herbes*, *fulles de llorer*) es conserven intactes sense alterar.
- **Selector Interactiu a la Fitxa:** Cada vegada que s'obre una recepta a `modal_recepta`, el selector de comensals es reinicia a **3 per defecte** i permet simular a temps real quantitats per a qualsevol nombre de comensals (1 a 30).
- **Format visual:** Els ingredients es presenten estilitzats separats per asteriscs ` * `.

### 4.3 Pautes de Fotografia Gastronòmica
- **Perspectiva:** Angle elevat a 45° en primer pla (Close-up) on la paella/plat ocupa pràcticament tota l'amplada de l'enquadrament.
- **Aspect Ratio:** Proporció **4:3** per adaptar-se perfectament a les targetes horitzontals del llibre de receptes sense retalls estranys.
- **Fidelitat als ingredients:** La imatge ha de reflectir exclusivament els ingredients reals de la recepta.
- **Ambientació:** Taula rústica de fusta, llum natural càlida lateral i estris tradicionals de cuina.

### 4.4 Perfils Familiars, Vetos Personals i Desdoblament d'Àpats
- **Diferenciació d'Al·lèrgia vs Veto Personal:**
  - *Al·lèrgia mèdica:* Bloqueig estricte de la recepta completa per a tothom.
  - *Veto personal:* Quan un membre no menja un aliment (ex. fetge o casqueria) però la família sí, el planificador no bloqueja el plat familiar i assigna automàticament un **plat alternatiu ràpid parellat** (*comodí*, ex. pit de pollastre o truita) per a aquell membre, compartint la mateixa guarnició per no duplicar temps de cuina.
- **Membres Actius vs Fora de la Llar:** Permet activar o desactivar la participació de membres als menús.
- **Persistència i Neteja d'Estat a Admin (`modules/admin.py`):**
  - Per evitar que Streamlit restableixi valors erronis residuals o caducats en editar membres de la família (noms, naixement, al·lèrgies o vetos), el formulari de família neteja les claus de sessió (`f_`) de `st.session_state` en desar, afegir o esborrar, forçant una lectura neta des de `core/config.json`.
  - Utilitza IDs únics i estables (`mem_id`) i conversió bidireccional entre cadenes de text i llistes estructurades Python.

### 4.5 Mise en Place Setmanal de Bases i Connexió amb l'Stock (`modules/compres.py`)
- **Derivació Top-Down:** A partir del menú setmanal aprovat, el sistema genera la guia de *Batch Prep* de diumenge (patates probiòtiques amb midó resistent, caldos casolans concentrats, sofregit mare, verdures rostides).
- **Sincronització amb l'Stock:**
  - Si hi ha bases o caldos al congelador/nevera, es descompten de la guia de preparació de diumenge i de la llista de la compra.
  - Les quantitats de compra es calculen restant l'stock real existent: $\text{Compra} = \max(0, \text{Necessari} - \text{Stock})$.
- **Consens Familiar via WhatsApp:** Generació automàtica d'enllaços de petició i consens per a desitjos de comensals (ex. sardines).

---

## 5. Laboratori IA (Harness) i Benchmarking (`core/harness.py`)
- **Dataset mestre:** 11 casos de prova a `data/harness_menu_cases.json` que cobreixen al·lèrgies creuades, desdoblament de vetos, stock disponible, peticions per consens, puntuacions històriques baixes, disponibilitat del forn i restriccions d'equipament de cuina.
- **Execució Asíncrona en Segon Pla (Background Execution):**
  - Permet llançar la bateria de proves en un fil secundari (`threading.Thread`) i continuar utilitzant l'aplicació lliurement sense bloquejar la interfície.
  - Registra l'estat de progrés en temps real, l'hora d'inici i la durada transcorreguda (`_format_duration_s`) a `data/harness_status.json`.
- **Avaluadors deterministes i Correccions de Regex:**
  - *Seguretat Mèdica:* Tolerància 0 a al·lèrgens. S'ha millorat `netejar_termes_segurs()` a `core/harness.py` per desestimar compostos aptes (com `formatge sense lactosa`, `mozzarella sense lactosa`, `llet sense lactosa`, `formatge vega`) ABANS de processar expressions prohibides generics, evitant falsos positius en la qualificació de seguretat.
  - *Desdoblament:* Comprovació de creació obligatòria de plat alternatiu quan hi ha un veto.
  - *Calendari d'Hidrats:* Prohibició de dies consecutius de pasta o arròs (fins i tot en fideus de sopa).
  - *Equipament:* Verificació que no es proposin tècniques d'aparells absents (`sifo_n2o`, `robot_cuina`, `airfryer`, `liquadora`, `tallafiambres`, `olla_pressio`).
- **Exportació d'Informes en Text (.txt):** Funció `generate_harness_txt_report` per descarregar informes complets i tests individuals en format `.txt` pla, aptes per compartir fàcilment.
- **Optimització de Models i Latències:**
  - Suport per a models actius: `gemini-2.5-flash` (recomanat), `gemini-3.6-flash`, `gemini-3.5-flash`, `gemini-flash-latest`.
  - Eliminació de models obsolets que donaven error HTTP 404 (`gemini-2.0-flash`, `gemini-1.5-flash`).
  - Retirada del paràmetre `thinkingBudget` per eliminar la latència innecessària i accelerar les respostes.

---

## 6. Lògica Avançada i OCR (Gemini Vision)
- L'extracció de tiquets del súper a `compres.py` utilitza **Google Gemini Vision** (`gemini-2.5-flash`), cridant directament l'API mitjançant `requests` amb gestió automàtica de reintents i *exponential backoff*.
- La clau d'API de Gemini es troba a `st.secrets["GEMINI_API_KEY"]`.

### 6.1 Descomptes i Enginyeria Inversa de Preus
- Quan l'usuari introdueix manualment un article amb descompte al tiquet a `modules/compres.py`, s'assumeix que s'està registrant el **preu final pagat**.
- Si s'indica un `%` de descompte (p. ex. 30%), el sistema calcula automàticament la base original i l'estalvi en promoció sense alterar l'import real pagat.

---

## 7. UI/UX i Adaptabilitat Mòbil
- **Fons i Pantalla Completa**: A `app.py` s'aplica estil CSS per a pantalla completa (`background-size: cover; background-attachment: fixed;`).
- **Responsive Scaling**: A dispositius mòbils (`max-width: 768px`), el logotip s'escala automàticament (`transform: scale(1.48)`) aprofitant tot l'ample de pantalla per a facilitar la pulsació dels botons tàctils.
- **Transicions i Efectes**: Els hotspots disposen d'animacions de pulsació (`pulse`) i efecte lluminós en passar el cursor o tocar.

---

## 8. Estratègia de Sincronització (Memòria i Base de Dades)
L'aplicació utilitza actualitzacions d'estat en temps real (zero latència):
- Quan `core/db.py` executa `insert_db_row`, `update_db_row` o `delete_db_row`, no només envia la petició SQL a Supabase, sinó que automàticament modifica el DataFrame corresponent a `st.session_state`.
- Això evita que els dashboards hagin de recarregar massivament totes les taules cada vegada que s'edita o s'afegeix una simple despesa.

---

## 9. Com instruir a noves sessions d'IA
Si inicies una conversa nova amb un assistent d'IA, indica-li:
**"Abans de res, llegeix l'arxiu `DOCUMENTACIO_PROJECTE.md` per entendre l'arquitectura modular de la meva app."**
Això assegurarà que treballi directament sobre `app.py`, el nucli a `core/` i els fitxers de `modules/`.

---

## 10. Directriu Obligatòria de Desplegament i GitHub (`git push`)
⚠️ **DIRECTRIU CRÍTICA D'EXECUCIÓ PER A L'ASSISTENT D'IA**:
- L'aplicació es carrega i s'executa directament des del núvol (desplegament automatitzat a **Streamlit Community Cloud** sincroitzat amb el repositori GitHub `enricxicars/dashboard-despeses`).
- En qualsevol tasca o modificació de codi completada, l'assistent d'IA **TÉ L'OBLIGACIÓ STRICTA DE DESAR I PUJAR SEMPRE ELS CANVIS A GITHUB** (`git add`, `git commit`, `git push origin main`).
- Mai s'ha de declarar una tasca com a finalitzada només modificant els fitxers locals: **SEMPRE CAL PUJAR ELS CANVIS A GITHUB** perquè la versió del núvol actualitzi la interfície de l'usuari immediatament.

---

## 11. Arquitectura "Cloud Native" i Supabase Centralitzat
Per tal de permetre l'execució total des del núvol (Streamlit Cloud) sense perdre dades en els reinicis de la màquina virtual, l'aplicació ha transicionat l'emmagatzematge de configuracions des de fitxers JSON locals cap a **Supabase (taula `app_config`)**:
- **ID 1**: `categories_conceptes.json`
- **ID 2**: `core/config.json` (Perfil familiar, eines de cuina, paràmetres globals)
- **ID 3**: `data/events.json` (Calendari familiar)
- **ID 4**: `data/feeds_cache.json` (Memòria cau dels Google Calendars)
- **ID 5**: `data/medication_plans.json` (Plans de medicació)
- **ID 6**: `data/ofertes.json` (Registre d'Ofertes Setmanals i Volumètriques)

*Nota: Els fitxers locals es mantenen com a còpia de seguretat (fallback local), però la font de la veritat prioritària és sempre Supabase. Així mateix, per desig exprés de l'usuari, s'ha suprimit la renderització dels Avatars (Xiqui) i els seus botons a les capçaleres de tots els mòduls per simplificar la interfície.*

---

## 12. Historial de Canvis Recents (Changelog Menor)
- **13/09/2026**: Renomenament de mòdul de "Compres" a "Ingressos i Despeses", pestanyes a "Ingrés / Despesa General", i aplicació de color corporatiu taronja (`#f39c12`) a les capçaleres d'introducció de moviments i "Compres Super". Correcció del botó "Inici" duplicat a la pestanya de Compres Super.
- **13/09/2026**: Modificació de l'esquema de la base de dades: afegida la columna `preuUnit` a `tb_productes` i executada la migració retrospectiva per importar l'últim preu de compra des de `compresSuper`.
- **13/09/2026**: Solució del problema de pèrdua de sessió (petició de contrasenya) en navegar mitjançant el menú superior entre mòduls gràcies a l'emmagatzematge del token a l'estat de la sessió.
- **13/09/2026**: Creació d'un nou mòdul `modules/bases_dades.py` que fa de **Gestor de Bases de Dades**. Accessible des del menú superior, permet visualitzar i editar en temps real (inserir, modificar i esborrar) totes les taules de Supabase de manera centralitzada i senzilla mitjançant `st.data_editor`.
- **13/09/2026**: Afegit botó "Inici" al capdamunt a la dreta del Gestor de Bases de Dades i eliminat text informatiu de la ID segons l'usuari.
- **13/09/2026**: Estandardització del tamany del botó "Inici" per a totes les pàgines de l'aplicació. El valor de proporció obligatori i fix per al disseny de la capçalera (quan només hi ha un botó) és de `st.columns([9.2, 0.8])`. S'ha actualitzat `modules/avatar_widget.py` per complir amb aquest requisit de disseny.
- **13/09/2026**: Ajustos visuals addicionals en les capçaleres: (1) S'ha eliminat la capçalera repetida amb el botó Inici a `modules/economic.py`; (2) S'ha fet més gran l'espai per a elements extra a la capçalera (`avatar_widget.py`), de manera que els botons llargs com el de Medicació i la capsa de cerca de Configuració (amb nova icona de lupa) es vegin correctament sense deformar el botó Inici.
- **13/09/2026**: Millores a la **Llista de la Compra** (`modules/compres.py`): Afegit un títol clar en taronja. Aprofitant el camp `preuUnit`, es calcula i es mostra de forma automàtica l'import estimat per línia i per supermercat. S'han afegit avisos explícits `(Sense valoració)` pels productes que no tenen preu registrat per tal que no hi hagi confusions en el total, i s'ha afegit un **Gran Total** a sota de tot per saber el cost total de tota la compra pendent.
- **13/09/2026**: Solucionat un problema d'interfície on el menú superior (`app.py`) es tancava accidentalment en moure el ratolí (pèrdua del *hover*) abans d'arribar als submenús. S'ha implementat un "pont invisible" amb pseudo-elements CSS per assegurar que el menú roman obert durant el desplaçament del cursor.
- **14/09/2026**: Creació del nou mòdul `modules/ofertes.py` ("Consulta d'Ofertes i Preus") accessible des del menú "Finances". Inclou un Comparador de Preus intel·ligent que creua l'stock (Llista de la Compra o Rebost Sencer) amb ofertes manuals (desades a `app_config` ID 6), i una segona pestanya amb un Visor de Fulletons oficials integrat.
- **14/09/2026**: Extensió del mòdul d'Ofertes (`modules/ofertes.py`) afegint "Novavenda", "El Corte Inglés" i "Clarel" al registre manual i als fulletons, arreglant errors de duplicitat de botons i millorant-ne l'espaiat i disseny. També s'ha afegit una nova funció d'"Històric de Preus per Producte" que creua la selecció amb `compresSuper` per veure on s'havia comprat abans al millor preu.
- **15/09/2026**: Solució d'un bug visual a nivell global on els calendaris (`st.date_input`) perdien els botons de navegació (mes i any) perquè una regla CSS genèrica en `app.py` amagava totes les etiquetes `<header>`. S'ha restringit l'ocultació específicament a `header[data-testid="stHeader"]`.
- **15/09/2026**: Substitució del cercador automàtic per *Scraping* per una **Taula de Comparativa Manual** a la pestanya de Fulletons. Ara l'usuari pot seleccionar un producte i omplir manualment els preus i les ofertes de cadascun dels 10 supermercats (les dades s'associen al producte i es mantenen en la sessió activa `st.session_state`). Això evita els bloquejos per protecció anti-bot que imposen plataformes com Mercadona i Dia.
- **18/09/2026**: Implementació completa d'un **Mode Offline (Desconnectat)** per garantir l'operativitat en caigudes d'internet. El mode es pot activar a voluntat des del menú "Ajustos" (`app.py`), mostrant un avís permanent. S'ha modificat l'arquitectura de la base de dades (`core/db.py`) perquè, en mode desconnectat, llegeixi les dades d'una memòria cau local en CSV i desi les noves accions (insercions, edicions i esborrats) a una cua local (`sync_queue.json`), evitant temps d'espera penjats amb Supabase.
- **18/09/2026**: Creació d'un nou mòdul al menú "Bases de dades" anomenat **Consolidar Dades Offline** (`modules/sincronitzacio.py`) per permetre la visualització de totes les tasques retingudes a la cua i pujar-les a Supabase en bloc un cop recuperada la connexió a internet.
- **18/09/2026**: Reconfiguració de l'entorn de l'escriptori de Windows ("ControlHouse.lnk") eliminant antics accessos, i modificació profunda del `StartDashboard.py` perquè l'aplicació s'obri exclusivament al **Google Chrome** (`webbrowser.get('chrome')`) de manera automatitzada i cega, tancant la dependència sobre el Microsoft Edge.
