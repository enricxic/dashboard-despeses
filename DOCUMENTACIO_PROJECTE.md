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
- **Barra Superior de Menús (Estil Tradicional d'Escriptori)**: Barra de navegació global permanent a la part superior de l'aplicació amb 4 menús clàssics desplegables i controls d'estat:
  - `Arxiu`: Tornar a la pantalla d'inici, reiniciar app / memòria cau, commutar mode Online/Offline i tancar sessió.
  - `Editar`: Accés directe a la configuració general (amb submenús per a Tauler, Administrador, Títol, Família, Tutelats, Bancs, Tema, Icones, Idiomes), editor interactiu d'arxius JSON, regles súper OCR i neteja d'orfes.
  - `Mòduls`: Selector complet dels mòduls de la llar (Dashboard, Econòmic, Compres, Cotxe, Menús i Cuina, Manteniment, Domòtica, Seguretat, Agenda, Medicació, Jocs) amb submenús d'accions ràpides i FAQs.
  - `Bases de dades`: Gestor de taules Supabase (Despeses, Ingressos, Compres Super, Catàleg de Productes), sincronització, consolidació de dades offline i còpies de seguretat en fitxer ZIP.
  - *Controls d'estat (dreta)*: Indicador de connectivitat Online/Offline, campaneta de notificacions i alertes globals amb comptador en temps real, i insígnia del rol d'usuari (👑 Administrador / 👤 Visualitzador).
- **Interfície Gràfica d'Inici**: Mostra un logotip interactiu transparent (`imatges/Disseny/logo xiquiHouse.png`) sobre un fons complet de pantalla (`imatges/Disseny/fons xiquiHouse.jpg`), amb 12 punts d'accés interactius mapejats.
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
   - `👨‍👩‍👧‍👦 Família`: Membres de la llar amb data de naixement europea (`DD/MM/AAAA`), recàlcul automàtic d'edat en anys, telèfon mòbil, al·lèrgies mèdiques (bloqueig estricte), vetos/aversions personals (desdoblament), plats comodí favorits i interruptor d'activació (`🟢 Present a la llar` vs `⚪ Fora de la llar`).
   - `🍽️ Menús i Nutrició`: 
     * Regles de salut (màxim carns vermelles, mínim peix i llegums, màxim sopars d'embotits), control d'hidrats consecutius, disponibilitat del forn i format de planificació.
     * **🍳 Aparells i Eines Disponibles**: Selector visual amb 14 eines de cuina clau (`forn`, `microones`, `airfryer`, `bascula`, `minipimer`, `batedora_vas`, `motlles_silicona`, `olla_pressio`, `liquadora`, `tallafiambres`, `robot_cuina`, `picadora`, `sifo_n2o`, `mandolina`) amb miniatures d'estudi homogènies i ampliació modal interactiva   - `🧪 Laboratori IA (Harness)`: Banc de proves integrat per avaluar la precisió, seguretat d'al·lèrgies mèdiques, gestió de vetos i adaptació a l'equipament dels models Gemini, amb **execució en segon pla (asíncrona)** i **descàrrega d'informes en format Text (.txt)**.
   - `🤝 Tutelats`, `🏦 Bancs`, `🎨 Aspecte i Tema`, `🔘 Icones d'inici`, `🌐 Idiomes`.
2. **📊 Dashboard General**: `modules/dashboard.py` *(Icona pantalla + gràfic)* - Vista de panell principal amb targetes de saldos bancaris (BBVA, La Caixa, etc.), resum mensual d'ingressos i despeses de l'any i gràfics comparatius.

### 🔵 Part Esquerra (5 nodes amb rodona):
3. **📈 Mòdul Econòmic**: `modules/economic.py` *(Icona gràfic ascens)* - Gestió econòmica i financera organitzada en pestanyes especialitzades:
   - `📈 Detalls del Mes`: Saldos bancaris, rebuts, pagaments, hipoteca, taula anual i gràfic comparatiu de barres amb previsions vs real.
   - `🔴 Prev. Despeses`: Formulari d'alta, secció de modificació d'imports en bloc per a pagaments pendents futurs i llistat de pagaments programats.
   - `🟢 Prev. Ingressos`: Formulari d'alta, secció de modificació d'imports en bloc per a ingressos pendents futurs i llistat d'ingressos previstos.
   - `📈 Inversions`: Formulari de moviments de TR Cartera (S&P500, NVIDIA), KPIs i taula d'inversions.
   - `💰 Estalvis`: Fons d'estalvi `estalviDP`, quotes, aportacions, rescats i gràfic interactiu d'evolució del capital acumulat.
   - `🤖 Xat IA`: Assistent financer intel·ligent Gemini.
4. **📹 Seguretat**: `modules/seguretat.py` *(Icona càmera)* - Estat de càmeres, accessos i alarmes.
5. **🛠️ Manteniment**: `modules/manteniment.py` *(Icona casa amb eina)* - Gestió i organització de les actuacions i documentació tècnica de la llar en tres pestanyes especialitzades: `📋 Registre Manteniment` (tasques, reparacions i feines de casa amb formulari d'alta ràpid, assignació d'alertes personals, control d'acompliment i sincronització automàtica a l'agenda), `📖 Manuals` (instruccions d'aparells, ubicació, especificacions) i `🛡️ Garanties` (dates de compra, terminis de vigència, factures i alertes de caducitat), connectades a registres centralitzats (Supabase app_config ID 7 i ID 8) i amb visor interactiu de fitxers PDF integrat.
6. **📶 Domòtica**: `modules/domotica.py` *(Icona WiFi)* - Integració amb Home Assistant, llums i sensors.
7. **🎲 Jocs**: `modules/jocs.py` *(Icona daus)* - Oci familiar, inventari de jocs i marcadors.

### 🟢 Part Dreta (5 nodes amb rodona):
8. **📅 Agenda**: `modules/calendari.py` *(Icona calendari)* - Calendari familiar, esdeveniments i sincronització.
9. **💊 Control Medicació**: `modules/medicacio.py` *(Icona pastilles / flascó)* - Pautes mèdiques, dosis, horaris i farmaciola.
10. **🍽️ Menús i Cuina**: `modules/menjar.py` *(Icona coberts)* - Gestió gastronòmica i nutricional intel·ligent:
    - `🧠 Recomanador de Menús`: Generació setmanal amb IA (`gemini-2.5-flash`) seguint al·lèrgies mèdiques strictly, desdoblament de vetos personals, regles de freqüència nutricional (carn vermella, peix, llegums), eines de cuina i membres actius.
    - `🟢 Control Dietètic`: Sistema híbrid avançat de dietètica que permet fixar un límit de calories separat per a dinars i sopars. El recomanador prioritza receptes amb `puntuacio_salut` alta i s'assegura de retornar els menús amb una estimació real sota el límit estipulat utilitzant els `tags_nutricionals` per a balancejar macronutrients.
    - `📲 Consens Familiar per WhatsApp`: Botó d'un sol clic per compartir el resum del menú.
    - `⏱️ Batch Cooking & Mise en Place`: Guia de preparacions base de diumenge i llista de compra associada.
    - `📖 Llibre de Receptes`: Base de dades de receptes. Visualització directa de la fitxa nutricional amb 💚 Puntuació de Salut i 🔥 Calories estimades per ració.
    - `➕ Afegir Recepta`: Formulari amb càrrega d'imatges a Supabase Storage.
    - **Scripts d'enriquiment en segon pla**: `populate_calories.py` (càlcul exacte de kcal amb IA via OpenRouter/Google), `heuristic_calories.py` (càlcul d'emergència en base a ingredients) i `populate_tags.py` (etiquetatge nutricional avançat de receptes).
11. **🚗 Cotxe**: `modules/cotxe.py` *(Icona cotxe)* - Gestió del vehicle organitzada en pestanyes:
    - `🛣️ Registre Km i Rutes`: Formulari per registrar lectures d'odòmetre, càlcul automàtic de km del trajecte, selector/plantilles de rutes i taula d'històric.
    - `⛽ Repostatge`: Taula històrica de proveïments de la BBDD `gasolina` (alimentada des d'Ingressos/Despeses) amb mètriques de preu últim repostatge, preu més alt i més baix.
    - `🔧 Canvi d'Oli`: Seguiment de km actuals, límit de canvi d'oli i km restants.
    - `📊 Consum`: Gràfic de consum anual L/100km.
12. **🛒 Ingressos i Despeses**: `modules/compres.py` *(Icona carro de compra)* - Gestió integral d'ingressos, despeses i compres:
    - `📄 Compres Super`: Escàner OCR intel·ligent amb suport total de Gemini Vision. Incorpora un sistema de **Regles de Súper Editables (`core/ocr_rules.md`)** des del menú superior, permetent ensenyar a la IA com llegir ofertes o estructures de tiquets específiques de cada cadena (Mercadona, Bonpreu, Dia, etc.) sense programar codi. Inclou mecanismes estrictes per forçar quantitats enteres.
    - `🛡️ Auditoria d'Entrada Estricta`: Prevenció d'entrada de dades brutes a la base de dades. Els articles desconeguts de l'OCR ('Pendent') no s'insereixen automàticament; el sistema bloqueja el desat del tiquet fins que l'usuari hagi categoritzat cada producte nou o l'hagi esborrat, evitant la creació d'orfes a `tb_noms_producte`.
    - `🧹 Neteja d'Orfes (OCR)`: Eina avançada (disponible al menú "Editar") per depurar productes històrics orfes. Permet esborrar massivament text brossa de l'OCR, o bé enllaçar i crear nous articles al catàleg sobre la marxa de manera molt eficient.
    - `📝 Ingrés / Despesa General`: Formulari directe de **Moviments Reals** (Despesa, Ingrés, Traspàs), proveïment de gasolina amb calculadora, tiquets pendents i taula d'últims moviments. Incorpora un **formulari d'inserció múltiple simplificat** (només text) que exigeix que el Banc i la Forma de Pagament s'hagin auditat prèviament a les previsions.
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
│   ├── manteniment_manager.py # Gestor documental (Manuals i Garanties) i Registre de Tasques (Supabase ID 7 i ID 8)
│   ├── ocr_rules.md          # Regles personalitzades per supermercat enviades al prompt de Gemini
│   └── harness.py            # Motor d'avaluació IA, execució asíncrona en segon pla i generador d'informes .txt
├── data/
│   ├── harness_menu_cases.json # Banc d'11 casos de prova exhaustius per al test de menús
│   ├── harness_status.json     # Estat de progrés en temps real per a l'execució de proves en segon pla
│   ├── manteniment_docs.json   # Registre JSON canònic de documents tècnics (Manuals i Garanties)
│   └── registre_manteniment.json # Registre JSON de tasques de manteniment, reparacions i feines de casa
├── imatges/
│   ├── Disseny/              # Logotips, icones i fons de pantalla de la interfície
│   ├── Eines/                # Miniatures dels 14 aparells i eines de cuina
│   ├── Productes/            # Fotografies dels articles de la compra i rebost
│   └── Receptes/             # Imatges generades dels plats i receptes per ID
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
│   ├── manteniment.py        # 🛠️ Manteniment de la Llar (Pestanyes Registre Manteniment, Manuals i Garanties, visors PDF, filtres)
│   ├── medicacio.py          # 💊 Control de medicació i tutelats (Pla de dosificació & sync)
│   ├── menjar.py             # 🍽️ Receptari (Escalat base 3), Planificador IA i Batch Cooking
│   ├── ofertes.py            # 🔍 Comparador d'Ofertes i Visor de Fulletons (Mercadona, Aldi, etc.)
│   └── seguretat.py          # 📹 Seguretat i càmeres
├── PDF/
│   ├── Manuals/              # Dipòsit de manuals d'instruccions en PDF
│   └── Garanties/            # Dipòsit de factures i documents de garantia en PDF
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

### 4.6 Control de Repeticions i Priorització de Receptes
- **Historial de Plats:** Cada vegada que es desa un menú o es genera la Mise en place, les receptes planificades s'apunten automàticament a `tb_historial_menjars`.
- **Regla Anti-Repetició:** El recomanador de menús llegeix la taula de l'historial i prohibeix terminantment a la IA proposar un plat que s'hagi consumit en els últims `X` dies (configurable per l'usuari, per defecte 15 dies).
- **Estrelles i Qualificació:** El catàleg lliurat a la IA adjunta les puntuacions actuals de cada plat. La IA té instruccions per prioritzar plats de 4 i 5 estrelles, discriminant les opcions pitjor valorades a l'hora de tancar la quadricula.

### 4.7 Bústia de Peticions i Demandes Familiars
- **Pestanya de Peticions:** S'habilita un formulari (pestanya "📥 Bústia Peticions") on els membres poden demanar plats concrets per menjar durant la setmana.
- **Circuit d'Aprovació:** Les peticions es desen a `tb_peticions_menjar` en estat *Pendent*. El planificador del menú pot *Acceptar* o *Rebutjar* cada petició des del tauler de control.
- **Assimilació Automàtica:** Si hi ha peticions *Acceptades*, aquestes s'injecten imperativament a la llista d'exigències del *prompt* perquè la IA les col·loqui al proper menú generat de forma automàtica.

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
- **ID 7**: `data/manteniment_docs.json` (Registre de Documents, Manuals d'Instruccions i Garanties de la llar)
- **ID 8**: `data/registre_manteniment.json` / `csv/manteniment.csv` (Registre de tasques de manteniment, reparacions i feina de casa)

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
- **24/09/2026**: Resolució de l'error crític `Crashpad_NotConnectedToHandler` (penjades d'Streamlit frontend) movent les imatges base64 pesades d'etiquetes `<img>` en línia a propietats globals de `background-image` en CSS pur a `app.py`.
- **24/09/2026**: Modificació de les instruccions del model d'IA d'OCR (Gemini Vision) a `compres.py` per establir que els productes venuts a pes (carn, fruita) retornin sempre quantitat entera = 1, assignant l'import final com a preu unitari, evitant errors decimals visuals a la taula.
- **24/09/2026**: Redisseny matemàtic del formulari d'entrada manual a `compres.py`. Ara, al posar un % de descompte, s'entén que el "Preu Unitari" inserit és el preu rebaixat (el del tiquet), calculant el preu base original cap amunt i ajustant la promoció perquè el "Total Línia" sigui inamovible i exacte (evitant desquadraments de cèntims en arrodoniments per múltiples unitats).
- **24/09/2026**: Connexió de la funció d'agrupació de duplicats (`group_duplicate_ticket_items`) a la sortida de la IA OCR per refondre automàticament productes idèntics. Forçat general del format enter per a la columna de Quantitats a totes les taules d'edició.
- **25/09/2026**: Correcció del càlcul de la memòria cau i dels tipus de dades (`any` com a enter i verificació del `date_score`) al `modules/economic.py` per garantir que el Dashboard i l'Extracte mostren immediatament els moviments recents si s'esborra la memòria, evitant desquadraments fantasma de saldos per culpa d'entrades manuals mal formades.
- **25/09/2026**: Centralització del sistema d'alertes en un nou arxiu `core/alerts.py`. S'ha integrat una **Campana de Notificacions Global** a la barra superior (menú `app.py`) i a la pantalla d'inici, que mostra dinàmicament el número d'avisos pendents (Loteria, Canvi d'oli del cotxe, etc.) obrint un diàleg emergent interactiu a qualsevol pantalla.
- **25/09/2026**: Ampliació d'un 30% en el radi de les icones centrals d'accés (Dashboard i Mòdul Econòmic) per facilitar la usabilitat en tauletes i entorns tàctils a la pantalla principal. A més, s'ha solucionat un error que obria `app_config` per defecte a causa d'una neteja de paràmetres a l'adreça web en prémer "Despeses".
- **27/09/2026**: Solució d'un error de falsa confirmació visual (`silent failure`) al formulari d'entrada manual a `compres.py`. Anteriorment, si la inserció a Supabase fallava per culpa d'un `ID_mov` duplicat (provocat perquè la memòria cau de la sessió amagava entrades recents), el sistema netejava el formulari igualment fent creure a l'usuari que s'havia guardat la despesa. S'ha obligat a validar la confirmació del servidor abans d'esborrar res.
- **27/09/2026**: Integració d'un sistema de generació automàtica de compensacions en despeses compartides al mòdul `compres.py`. En introduir una factura íntegra de Restaurant i indicar la part que li corresponia pagar a l'usuari, el sistema crea un apunt simultani en negatiu (Efectiu) per cuadrar el volum de despesa sense perdre la correspondència bancària original del ticket.
- **27/09/2026**: Reforma crítica de l'arquitectura de memòria cau (Streamlit Cache). S'ha establert un doble sistema de refresc directe: `Despeses` i `CompresSuper` s'actualitzen cada 5 segons per millorar l'experiència d'entrada de dades manuals, mentre que la resta de bases de dades mantenen una retenció de 10 minuts per minimitzar trucades a l'API. S'ha refactoritzat l'extracció de dades a `core/db.py` per resoldre problemes de penjaments (pantalla negra) amb `ThreadPoolExecutor`.
- **27/09/2026**: Ajustament visual geomètric a la pantalla d'inici (`app.py`). S'ha reduït un 13% l'amplada de l'escut central interactiu (XiquiHouse) a petició de l'usuari, suprimint també el marge forçat horitzontal (`translateY`) perquè el navegador centri automàticament tot l'escut segons la finestra. S'ha arrodonit i apropat a la dreta la insígnia de recompte d'alertes (Campana) per evitar superposicions amb els rols.
- **27/09/2026**: **Cirurgia Major de Rendiment (Part 1)**. Solució a la lentitud del processament de dades amb Pandas traslladant la càrrega de `load_dashboard_data` cap a l'interior de les funcions cacheades (`_fetch_fast_tables` i `_fetch_slow_tables`). S'ha apujat el TTL de totes les memòries cau a 10 minuts i s'ha creat una funció `get_next_id` de micro-peticions per evitar col·lisions d'índexs en guardar dades manualment.
- **27/09/2026**: **Cirurgia Major de Rendiment (Part 2 - Solució Pantalla Blanca)**. S'ha detectat i solucionat el vertader causant dels penjament de 60 segons de durada al navegador (DOM freeze). L'ús de `st.tabs` a "Ingressos i Despeses" forçava el servidor a dibuixar, processar i enviar de forma invisible els milers de components visuals de la pestanya "Rebost" (fotos i botons de tots els productes) cada cop que es feia un clic. S'ha substituït l'arquitectura de pestanyes per un `st.radio` horitzontal, el qual actua com a menú de navegació i permet la càrrega "lazy" (només es processa i s'envia al navegador allò que l'usuari està mirant actualment). S'ha aplicat també un "debounce" al `MutationObserver` de `app.py` per protegir el fil principal de renderitzat del navegador.
- **27/09/2026**: **Cirurgia Major de Rendiment (Part 3 - Solució Pèrdua de Memòria Cau)**. S'ha eliminat un bucle de recàrrega forçada de mòduls (`importlib.reload`) a `app.py` que destruïa sistemàticament la memòria cau d'Streamlit cada cop que l'usuari navegava per les pantalles. Aquesta mala praxi obligava al servidor a descarregar-ho tot des de Supabase a cada clic, provocant els bloquejos de pantalla blanca d'alguns segons. Ara la memòria cau de 10 minuts sí que s'activa correctament.
- **29/09/2026**: Reubicació de la secció 'Detalls del mes' al Dashboard general i optimització del Mòdul Econòmic. S'ha eliminat codi duplicat i inactiu (més de 1800 línies de l'OCR de Compres Super) que generava conflictes de navegació entre pestanyes. A més, s'han redissenyat les taules de Previsió de Despeses i Ingressos: ara inclouen columna d'Any, l'ordenació interactiva de columnes està habilitada gràcies a l'ús de `st.column_config`, i s'ha integrat un sistema complet de filtres desplegables (Any, Mes, Banc, Estat) junt amb un botó per restablir-los ràpidament.
- **29/09/2026**: Reestructuració integral dels mòduls d'economia i la llar. S'ha centralitzat la gestió al nou mòdul "Compres Super i Stock" (antic Ingressos i Despeses), movent-hi la pestanya Compres Super i absorbint tota la funcionalitat de l'arxiu `ofertes.py` (Comparador i Fulletons), el qual s'ha eliminat. La pestanya "Ingrés/Despesa General" s'ha quedat exclusivament al Mòdul Econòmic. Finalment, s'ha estandarditzat gràficament l'encapçalament de TOTS els mòduls de l'aplicació, substituint els antics emojis per incorporar el logotip central (XiquiHouse) al costat dels títols principals.
- **30/09/2026**: Millora d'UX a la navegació del mòdul econòmic. S'han eliminat els botons superiors "Compres Super" i "Ingrés/Despesa" del menú principal per netejar la interfície, i en el seu lloc s'han implementat uns botons directes amb la icona "🔄" (Túnel) integrats just a la dreta dels subtítols inferiors, creant dreceres in-situ.
- **30/09/2026**: Correcció i potenciació del diàleg de Confirmació d'Operacions ("Confirmar i Desar a BBDD") a `economic.py`. Ara no bloqueja l'usuari si falta el "Banc" a una de les operacions (com la Hipoteca), sinó que mostra allà mateix un `selectbox` desplegable per assignar el banc "al vol" i finalitzar l'operació sense haver de tancar i tornar a la taula. També s'ha resolt l'omissió per la qual la línia fixa de la Hipoteca ignorava el Banc guardat a la seva base de dades.
- **30/09/2026**: Arranjament d'un `KeyError` relacionat amb traspassos programats que feia caure l'app a l'intentar verificar els destins de transaccions predefinides sense ID numèric com "hipoteca". A més, s'ha corregit la categoria base d'aquesta despesa de `manteniment` a `despesa_general`.
- **30/09/2026**: Càlcul global i format de dates: (1) S'ha actualitzat la funció de càlcul de "Saldo Comptes" global al Dashboard perquè utilitzi sempre l'històric complet fins al "desembre" del l'any seleccionat, de manera que els pagaments entrats a final de mes no s'excloguin erròniament del saldo si el seu mes teòric recau en l'esdevenidor. (2) S'ha arranjat el parseig de dates intern a `bases_dades.py` perquè l'editor enviï a Supabase l'string `DD/MM/YYYY` original i no el format ISO defectuós de `datetime.date`.
- **30/10/2026**: Neteja visual del Desglòs de despeses: s'ha implementat un filtre directe `grup != op_banc` per ocultar completament les operacions bancàries tècniques compensatòries amagades darrere la compra d'Accions (que abans sortien duplicades i marcant `0.00 €`).
- **02/10/2026**: Creació d'un sistema avançat de Preguntes i Respostes (Guia/FAQ) amb lectura d'arxius Markdown (`docs/faq_economic.md`) integrat al menú superior desplegable principal de cada mòdul.
- **02/10/2026**: Inserció de **Filtres dinàmics** (Any, Mes, Cartera, Concepte) i checkbox d'ordenació temporal a la vista històrica de TR Cartera (Pestanya Inversions).
- **02/10/2026**: Construcció d'un **Motor de Validació i Autocorrecció de menús d'IA** (`core/validator.py`). El sistema avalua en temps real el JSON generat per l'LLM, detecta al·lucinacions de vetos, desquadraments d'hidrats festius i excessos en els còmputs nutricionals. Si detecta falles, llança un *retry loop* per obligar a la IA a refer el menú abans de mostrar-lo a l'usuari.
- **02/10/2026**: Refinament del prompt nutricional i transició de les regles de "Mínim de peix" cap a una freqüència exacta ("Cops exactes per setmana") per millorar la precisió de la llista de la compra.
- **06/10/2026**: Integració de funcionalitats "Slow Thinking" al generador de menús (`core/validator.py`, `core/harness.py`, `modules/menjar.py`), permetent a la IA reflexionar i auto-corregir-se davant al·lucinacions, millorant el compliment de regles nutricionals, i discriminant entre l'estoc del rebost i el del congelador.
- **06/10/2026**: Habilitada la categorització per `apat` ("Dinar", "Sopar", "Dinar/Sopar") al *prompt* enviat a la IA per millorar la coherència en la tria de plats segons el moment del dia, llegint el camp directament de `tb_receptes_pro`.
- **06/10/2026**: Afegit suport per a una nova columna `stockXmenu` (booleana) a la taula `tb_productes`. Aquesta casella d'activació, editable des de la Taula Ràpida de Rebost a `modules/compres.py`, filtra de manera estricta els productes que es passen com a candidats per generar plats al Recomanador de Menús (amagant així articles inútils com sal, llet, paper, etc.).
- **08/10/2026**: Integració de la **Bústia de Peticions**, permetent als membres demanar plats que seran validats i inclosos automàticament al proper menú de la IA. Implementació del registre de l'**Historial de Menjars**, aplicant una regla estricta que impedeix a la IA repetir plats ja consumits en els últims X dies. Finalment, adició del paràmetre del **telèfon mòbil** al perfil de membres de la família (preparació per l'enviament de menús) i millora del *prompt* per afavorir les receptes amb les millors **estrelles (valoració)**.
- **15/10/2026**: Integració de la funcionalitat "Afegir nou any comptable" al Mòdul Econòmic (accessible des del menú superior Mòduls > Mòdul Econòmic > 📅 Afegir nou any comptable i botons d'accés ràpid a les pestanyes de Previsions). Permet revisar i editar els imports per defecte dels 9 conceptes d'ingressos i 12 de despeses abans de generar els 12 mesos pendents de l'any següent (ex. 2027). A més, el selector d'anys del Dashboard unifica anys reals i de previsions, i el gràfic de barres s'ha ampliat a una finestra de 3 anys ([any-1, any, any+1]) amb barres grogues de projecció per als mesos futurs.
- **15/10/2026**: Reorganització i classificació completa de la carpeta `imatges/` en 4 subcarpetes estructurades (`Productes/`, `Eines/`, `Disseny/`, `Receptes/`). Actualitzades totes les rutes del codi font (`app.py`, `modules/admin.py`, `modules/compres.py`, `modules/avatar_widget.py`, `modules/economic.py`, `csv/tb_productes.csv`) amb mecanismes de resolució retrocompatibles.
- **16/10/2026**: Millores al modal "Afegir nou any comptable" (`modules/economic.py`): incorporació de caselles de selecció (checkboxes activats per defecte) per poder decidir quines partides d'ingressos i despeses s'incorporen a l'any nou. Creació de la nova pestanya **🎁 Pagues Extres** que inclou les tres pagues (Pensió Enric, Pensió Isabel i Pensió no contributiva), programades automàticament per als mesos de juny i novembre (dia 25) heretant l'import mensual de la pensió corresponent. S'han eliminat els botons d'accés ràpid de les pestanyes de Previsions perquè l'accés sigui únicament des del menú superior, s'han compactat els títols de les pestanyes, s'ha integrat la suma de les pagues extres directament a la línia del total anual d'ingressos (`Anual amb extres`) i s'ha suprimit la línia de balanç anual estimat per simplificar la visualització.
- **16/10/2026**: Correcció de l'ordenació cronològica al Gestor de Bases de Dades (`modules/bases_dades.py`). L'opció "Ordenar pel més recent primer" ara parseja i ordena per la data real (columna `Data`, `data_hora`, `data_inici`, etc.) i com a segona clau per l'ID numèric, en lloc d'ordenar exclusivament per la clau primària (`ID_mov`), garantint que a taules com Despeses o Ingressos els moviments més recents apareguin correctament a dalt de tot.
- **16/10/2026**: Resolució de l'error `UnboundLocalError: cannot access local variable 'os'` a `modules/compres.py`, `modules/avatar_widget.py` i `modules/calendari.py`. S'ha mogut la importació `import os` al nivell superior dels mòduls per evitar conflictes d'àmbit local a les funcions de renderitzat.
- **16/10/2026**: Millora integral de la navegació amb la tecla `Enter` a Compres Super (`modules/compres.py`). S'ha reescrit el controlador d'esdeveniments JavaScript en fase de captura (`capture=true`) per avançar-se a Streamlit/React, permetent saltar de forma fluida i seqüencial entre camps (Família > Article > Pes > Quantitat > Preu Unitari > % > Promoció) seleccionant el text existent per reescriure ràpidament. A més, prémer `Enter` al camp de Promoció (o fer `Shift + Enter` des de qualsevol camp) executa automàticament el botó "Intro línia" per afegir l'article al tiquet sense haver d'utilitzar el ratolí.
- **16/10/2026**: Integració i posada en marxa de la impressora de tiquets **BIXOLON SRP-275APG** (connexió Paral·lel Centronics a USB xip CH340 al port `USB001` de Windows, establerta com a impressora predeterminada). Configuració del controlador de sistema `Generic / Text Only` i creació del mòdul `modules/impressora.py` que admet tant impressió directa via USB/RAW ESC/POS (amb tall automàtic de paper `\x1dV\x00` per a entorns locals) com impressió web neta mitjançant el navegador (`window.print()`, compatible amb Streamlit Cloud i rotlle de 76mm). S'ha afegit un marge de seguretat de 6 salts de línia en blanc (`\n` * 6) i padding inferior de 30mm per superar la distància física entre el capçal d'impressió i la guillotina de tall. La impressió s'ha integrat de manera neta i directa exclusivament dins del desplegable de cada supermercat a la Llista de la Compra, suprimint diàlegs modals de prova genèrics i botons redundants per evitar confusions amb els productes reals. S'ha creat també l'script de diagnòstic `scripts/test_bixolon.py`.
- **17/10/2026**: Resolució i millora integral del carregador de tiquets a Compres Super (`modules/compres.py`):
  - **Ampliació de formats admesos**: El carregador (`st.file_uploader`) ara admet imatges (`png`, `jpg`, `jpeg`, `webp`, `jfif`, `bmp`), documents digitals de supermercat (`pdf`) i tiquets de text (`txt`).
  - **Suport nadiu de tiquets en PDF**: Integració de la llibreria `pypdf` per a l'extracció instantània de text de tiquets PDF digitals (Mercadona, BonÀrea, Lidl, etc.), i derivació automàtica a Gemini Vision (`application/pdf`) en cas de PDFs escanejats o basats en imatges. S'ha afegit `pypdf` a `requirements.txt`.
  - **Desbloqueig de fitxers repetits / buits**: S'ha corregit la condició d'estat `processed_file_id`, que anteriorment bloquejava silenciosament la càrrega si l'usuari tornava a seleccionar un fitxer previ o si la taula d'articles (`ticket_items`) estava buida. Ara, si el tiquet està buit, el fitxer es processa sempre.
  - **Neteja de missatges residuals**: S'ha solucionat el problema on avisos o errors previs (`finalize_error`, `manual_input_error`, etc.) no s'esborraven en desar o netejar el tiquet. Ara s'eliminen de la sessió immediatament després de mostrar-se i es netegen en tancar o buidar el formulari per a nous tiquets.
  - **Incorporació del model Gemini (3.8 Flash)**: S'ha afegit el nou model d'alta velocitat `gemini-3.8-flash` tant al selector [`core/llm_ui.py`](file:///e:/Dashboard/core/llm_ui.py) com a la cadena de redundància de [`core/llm.py`](file:///e:/Dashboard/core/llm.py).
  - **Filtre intel·ligent segons mètode d'escaneig**: Si l'usuari tria **Híbrid (Tesseract+IA)**, el desplegable de models mostra totes les IAs disponibles (Gemini, DeepSeek, Llama, Qwen); si tria **Visió Pura (Directa)**, el desplegable es filtra dinàmicament per mostrar exclusivament els models que admeten imatges i visió multimodal (Gemini 2.5 Flash, Gemini 3.8 Flash, Gemini 2.5 Pro).
  - **Gestió compacta de tiquets pendents en una sola línia compartida**: S'ha redissenyat la capçalera de Compres Super (`modules/compres.py`) eliminant la caixa d'avís groga i l'expander per estalviar espai vertical. Ara, just a sota del títol, la informació del tiquet pendent (`• Nº 8179 — Dia (16/10/2026) — 6.48 € (TradeRep.)` amb el botó `[🛒 Desglossar]`) i el carregador `[ ⭡ Upload ]` comparteixen una única fila horitzontal neta. Si no hi ha cap tiquet pendent, la fila només allotja el botó d'Upload sense cap missatge addicional. A la fila inferior s'alineen de forma compacta el selector d'enviament a despeses, banc, forma de pagament, mètode d'escaneig i selector de model d'IA.
  - **Integració de tiquets pendents de desglossar al sistema global d'Alertes**: S'ha afegit una regla a [`core/alerts.py`](file:///e:/Dashboard/core/alerts.py), [`alerts_config.json`](file:///e:/Dashboard/alerts_config.json) i [`modules/admin.py`](file:///e:/Dashboard/modules/admin.py) perquè, quan hi hagi tiquets de súper pendents de desglossar a `despeses` (`ticketPendent = True`), aparegui automàticament la notificació a la campaneta de la barra superior (`🔔`) amb el recompte en temps real i el detall (`🛒 Tiquets de súper pendents: Nº 8179 (Dia - 6.48 €)`). S'ha eliminat la memòria cau rígida de 10 minuts (`@st.cache_data(ttl=600)`) de `get_global_alerts()` i s'ha integrat el recàlcul en temps real a la barra superior (`render_traditional_menubar`), prioritzant sempre el `df_desp` actiu de la sessió de l'usuari perquè qualsevol canvi aparegui a l'instant. En finalitzar o desvincular el tiquet, les alertes s'actualitzen immediatament.
  - **Validació i sanejament estricte de dates en l'escaneig de tiquets (OCR / IA)**:
    - **Funció `sanitize_ticket_date`**: S'ha implementat a [`modules/compres.py`](file:///e:/Dashboard/modules/compres.py) per blindar l'entrada de dates en tiquets de compra. Evita dates impossibles i futures (`> date.today()`), corregeix les confusions habituals d'OCR en tiquets matricials (on l'any `26` sovint és mal llegit com a `76` o `28`, p. ex. `2076` o `2028`), valida límits lògics d'any (entre 2018 i l'any actual 2026), intercanvia dies i mesos si estan invertits i ajusta dies invàlids.
    - **Regla estricta: Data mai superior a la data actual**:
      - El selector de calendari (`st.date_input`) tant a Compres Super com a Despeses manuals té definit el límit `max_value=datetime.today().date()`, impossibilitant triar qualsevol data futura.
      - A `finalize_ticket` i en la inserció manual de despeses, qualsevol intent de desar una data posterior a la d'avui es bloqueja immediatament amb missatge d'error (`La data no pot ser superior a la data actual`).
    - **Confirmació automàtica si fa més d'una setmana (> 7 dies)**:
      - Si la data detectada o introduïda és igual o inferior a la data d'avui però té una antiguitat superior a 7 dies, es mostra un indicador clar (`⚠️ Data de fa X dies (> 1 setmana)`) al costat del camp de data.
      - En prémer "Fi Tiquet", si l'usuari no ha confirmat prèviament la data, s'obre un diàleg modal interactiu (`@st.dialog("📅 Confirmació de Data del Tiquet")`) advertint dels dies transcorreguts i preguntant expressament si la data és correcta abans de desar el tiquet a la base de dades.
    - **Punts de control integrats**: S'ha aplicat el sanejament tant a l'extracció per Regex de text (`parse_text_ticket`), a l'extracció de resposta JSON dels models d'IA (Híbrid i Visió Pura), com en el moment de desar el tiquet a la base de dades a `finalize_ticket`.
    - **Instruccions explícites als prompts d'IA**: S'han actualitzat els prompts d'extracció (Híbrid i Visió) instruint de forma estricta que l'any del tiquet mai pot ser futur i que `26` sempre correspon a l'any 2026.
    - **Neteja de dades històriques**: S'han corregit els registres corruptes existents a `csv/compresSuper.csv` (línies de Mercadona amb any 2076 i bonArea amb any 2028 corregides a 2026) i a la base de dades remota Supabase (incloent-hi l'apunt amb any 2027 a Peixeteria).
  - **Correcció del flux de tancament de tiquets pendents de desglossar i normalització de supermercats**:
    - **Solució al bloqueig per clau primària duplicada (`despeses_pkey`)**: En desglossar un tiquet existent (`pending_ticket_id`), el sistema intentava fer un `INSERT` amb el mateix `ID_mov`, fallant silenciosament i impedint que el camp `ticketPendent` passés a `False`. S'ha refactoritzat [`modules/compres.py`](file:///e:/Dashboard/modules/compres.py) perquè el registre existent s'actualitzi directament mitjançant un `UPDATE` (`ticketPendent = False`), desant les dades reals a `despeses`, enllaçant els articles a `compresSuper` i esborrant automàticament les alertes i avisos de pendents.
    - **Tancament del tiquet Nº 8179 (Dia 6.48 €)**: S'ha actualitzat directament a Supabase i a `csv/despeses.csv` passant `ticketPendent` a `False` i normalitzant el concepte a `Dia`.
    - **Verificació creuada d'integritat automàtica (`IdDespesa`)**: Tant a [`core/alerts.py`](file:///e:/Dashboard/core/alerts.py) com a la capçalera i llistat de pendents de [`modules/compres.py`](file:///e:/Dashboard/modules/compres.py), el filtre de tiquets pendents ara creua les dades amb `compresSuper` (`IdDespesa`). Si un tiquet ja té articles desglossats a la base de dades, s'exclou immediatament dels pendents i es corregeix al vol a la memòria de la sessió de l'usuari, evitant que romangui bloquejat per culpa de la memòria cau residual.
    - **Normalització automàtica de noms de supermercat**: Tant a l'entrada manual com a la finalització de tiquets, els noms escrits o rebuts en minúscules (ex. `dia`) es comparen de forma insensible a majúscules/minúscules amb el catàleg oficial de supermercats (`get_config_supers()`) i es guarden canònicament amb majúscula inicial (`Dia`, `Mercadona`, `bonArea`, etc.).
  - **Anàlisi d'Estalvi i Gràfic de Rodones a Estadístiques de Compres Super (`modules/compres.py`)**:
    - **Càlcul d'Estalvi i Preu Teòric**: Còmput netejat i automatitzat de les promocions d'article (`prom`) i descomptes de tiquet (`descompte`) davant l'import net pagat (`totLinea`). Es dedueix el Preu Teòric Sense Ofertes ($\text{Compra Pagada} + \text{Estalvi}$) i el % global d'estalvi assolit.
    - **Filtres Dinàmics**: Totalment integrat amb els filtres interactius d'Any i Mes de la pestanya Estadístiques.
    - **Targetes KPI**: 4 blocs de mètriques (Total Compra Pagada, Total Estalvi Generat amb indicador de delta %, Preu Sense Ofertes i Nº Línies / Articles).
    - **Gràfic de Rodones (Donut Chart Plotly)**: Representació circular interactiva de la "Compra Total Pagada" vs "Promoció / Estalvi", amb colors corporatius, percentatges i etiquetes emergents.
    - **Panell de Desglossament i Supermercat Líder**: Targeta visual amb el desglossament de pagat net, promocions directes, descomptes globals i estalvi total, acompanyat del supermercat on s'ha aconseguit més estalvi.
  - **Generació de 13 Imatges Gastronòmiques per al Receptari (`tb_receptes_pro` / `imatges/Receptes/`)**:
    - **Pautes Estètiques**: Imatges creades seguint les pautes de la secció 4.3 (primer pla 45°, format horitzontal 4:3, llum natural càlida, taula rústica de fusta i fidelitat total als ingredients).
    - **Receptes cobertes**: ID 31 (Conill rostit), ID 106 (Sardines a la planxa), ID 115 (Orada al forn Bon Preu), ID 125 (Espaguetis amb all), ID 135 (Tataki de tonyina amb alvocat), ID 142 (Pollastre al forn amb patates), ID 146 (Carxofes farcides al forn), ID 151 (Empanadilles de tonyina), ID 161 (Maduixes amb nata), ID 170 (Cargols a la llauna), ID 174 (Faves a la catalana), ID 196 (Macarrons amb tomàquet cherry i alfàbrega), ID 209 (Amanida de cigrons).
  - **Correcció de la persistència de navegació i selecció a "Càrrecs per Categoria" (`modules/economic.py` i `app.py`)**:
    - **Sincronització de paràmetres de consulta (`mod`)**: S'ha corregit el comportament a [`app.py`](file:///e:/Dashboard/app.py) que eliminava immediatament el paràmetre `mod` de la URL (`st.query_params`) en carregar un mòdul. Això provocava que en produir-se un `rerun` per interacció amb widgets (com la selecció d'una fila d'un `st.dataframe`) o una reconnexió de sessió de Streamlit, l'aplicació perdés l'estat del mòdul actiu (`current_module = None`) i redirigís l'usuari involuntàriament al menú d'inici. Ara el paràmetre `mod` es manté sincronitzat de forma bidireccional amb `st.session_state.current_module` i només s'esborra quan l'usuari prem expressament el botó "🔙 Inici" o l'acció d'inici de la barra superior.
    - **Blindatge de la taula interactiva de categories (`st.dataframe`)**: A [`modules/economic.py`](file:///e:/Dashboard/modules/economic.py), s'ha assignat una clau única i estable (`key=f"df_cats_desp_{selected_year}_{selected_month_data}"`) al dataframe interactiu amb `on_select="rerun"`, s'ha afegit `.reset_index(drop=True)` després d'ordenar les despeses per evitar desfasaments d'índex, s'ha protegit l'extracció de files seleccionades tant per a diccionaris com per a instàncies de `DataFrameSelectionState` de Streamlit 1.58, i s'ha substituït l'Styler de Pandas a `cat_details` per configuració nativa de columnes (`st.column_config.NumberColumn`).
    - **Neteja coordinada als botons d'inici**: S'han actualitzat els botons "🔙 Inici" a [`modules/avatar_widget.py`](file:///e:/Dashboard/modules/avatar_widget.py), [`modules/compres.py`](file:///e:/Dashboard/modules/compres.py) i [`modules/economic.py`](file:///e:/Dashboard/modules/economic.py) per assegurar que esborren el paràmetre `mod` de `st.query_params` en tornar al menú principal.
- **18/10/2026**: Correcció de l'error `NameError: name 'df_super' is not defined` a [`modules/compres.py`](file:///e:/Dashboard/modules/compres.py) (`render_ingres_despesa_general_interface`). En carregar la pestanya "📝 Ingrés / Despesa General" del Mòdul Econòmic, la comprovació dels tiquets pendents de desglossar utilitzava la variable `df_super` sense haver-la carregat prèviament en l'àmbit local de la funció. S'ha recuperat de forma segura des de `st.session_state` amb connexió de reserva a Supabase i protecció contra valors nuls (`df_super is not None`).
- **18/10/2026**: Revisió i correcció integral dels **botons túnel de navegació ràpida entre Compres Super i Mòdul Econòmic** ([`modules/compres.py`](file:///e:/Dashboard/modules/compres.py)):
  - **Sincronització de paràmetres URL (`st.query_params`)**: Anteriorment, prémer el botó túnel només canviava `st.session_state.current_module`, però mantenia a la URL el valor antic de `mod`. Això feia que `app.py` revertís la navegació en recarregar, bloquejant el canvi de pantalla en ambdós sentits. S'ha afegit la sincronització explícita de `st.query_params["mod"]` tant a `tunnel_to_compres` com a `tunnel_to_economic`, i també al botó `Desglossar` dels tiquets pendents.
  - **Adaptabilitat visual a pantalles mòbils i escriptori**: S'ha substituït la proporció rígida de columnes (`[0.94, 0.06]`), que a dispositius mòbils feia que l'icona `⚡` quedés despenjada i orfe en una línia inferior, per una distribució equilibrada `[0.72, 0.28]` amb alineació vertical centrada i etiquetes descriptives clares (`⚡ Compres Super` i `⚡ Mòdul Econòmic` amb `use_container_width=True`), garantint una excel·lent usabilitat tàctil i visual tant en telèfons intel·ligents com en ordinadors.
- **18/10/2026**: Millora dels traspassos entre comptes a "Ingrés / Despesa General" (`op_banc` / `Traspàs comptes` a [`modules/compres.py`](file:///e:/Dashboard/modules/compres.py)):
  - **Quantitat editable al banc de destí**: A la secció "🔁 Traspàs entre comptes", al costat del desplegable de "Banc de Destí", s'ha incorporat el camp "Quantitat al banc de destí (€)". S'inicialitza per defecte amb l'import d'origen però és completament editable perquè l'usuari pugui indicar l'import exacte que arriba al compte destí si només se'n traspassa una part.
  - **Indicador dinàmic de diferència**: Si l'import de destí és inferior o superior al d'origen, es mostra una indicació visual automàtica amb la diferència exacta.
  - **Integració comptable exacta**: El moviment generat automàticament per al banc de destí a `despeses` (i a `tr_cartera` si el destí és `TR Cartera`) es registra amb la quantitat editada, reflectint amb total precisió els extractes de tots dos comptes.
- **18/10/2026**: Correcció del rebot immediat en fer clic a `[Desglossar]` a Mòdul Econòmic (`app.py`, [`modules/compres.py`](file:///e:/Dashboard/modules/compres.py), [`modules/economic.py`](file:///e:/Dashboard/modules/economic.py)):
  - **Diagnòstic de l'efecte rebot**: Quan l'usuari premia el botó `[Desglossar]` d'un tiquet pendent a Mòdul Econòmic (`modules.economic`), es canviava `st.session_state.current_module = "modules.compres"` i es cridava `st.rerun()`. Tanmateix, a [`app.py`](file:///e:/Dashboard/app.py) la comprovació inicial `if "mod" in st.query_params:` comparava el paràmetre de la URL que el client WebSocket transmetia abans que el navegador s'hagués actualitzat (`mod=modules.economic`). Com que no coincidia amb `current_module`, la lògica anterior sobreescrivia immediatament `st.session_state.current_module = selected_mod`, provocant que la pantalla de Compres Super es tanqués instantàniament i retornés a Mòdul Econòmic.
  - **Sincronització protegida amb `_browser_mod`**: S'ha introduït la variable d'estat `st.session_state["_browser_mod"]` a [`app.py`](file:///e:/Dashboard/app.py) per distingir entre una navegació externa des de la URL (enllaços `<a href>`, favorits o canvis manuals) i una navegació interna realitzada per botons de Streamlit a Python. Ara [`app.py`](file:///e:/Dashboard/app.py) només actualitza `current_module` des de la URL si el paràmetre `mod` ha canviat externament respecte a `_browser_mod`, preservant la transició sol·licitada pel codi i evitant qualsevol rebot.
  - **Inicialització exhaustiva de l'estat del tiquet**: S'ha actualitzat el botó `[Desglossar]` a [`modules/compres.py`](file:///e:/Dashboard/modules/compres.py) perquè, a més d'establir `_browser_mod = "modules.compres"`, precarregui completament tots els valors de widget necessaris (`ticket_super_val`, `ticket_super_widget`, `ticket_date`, `ticket_date_widget`, `ticket_bank_sel`, `ticket_pay_method_sel`, `ticket_send_expense = True`), deixant la pantalla de Compres Super a punt per desglossar els articles del tiquet sense cap desajust d'estat.
- **18/10/2026**: Reestructuració i sincronització nativa de pestanyes a tots els mòduls ([`app.py`](file:///e:/Dashboard/app.py), [`modules/economic.py`](file:///e:/Dashboard/modules/economic.py), [`modules/compres.py`](file:///e:/Dashboard/modules/compres.py), [`modules/cotxe.py`](file:///e:/Dashboard/modules/cotxe.py), [`modules/menjar.py`](file:///e:/Dashboard/modules/menjar.py), [`modules/medicacio.py`](file:///e:/Dashboard/modules/medicacio.py)):
  - **Sincronització directa i 100% nativa de pestanyes**: S'ha eliminat qualsevol script fràgil de JavaScript i manipulacions d'iframe al client. S'utilitza el suport natiu de Streamlit modern mitjançant el paràmetre `default` de `st.tabs(tabs_list, default=default_tab)`. En rebre el paràmetre `tab` a la URL (ex: `tab=prev_despeses` o `tab=llista_compra`), Python resol directament l'etiqueta de la pestanya i indica a Streamlit quina pestanya ha d'obrir per defecte en el primer render, sense retards, sense execució asíncrona i amb fiabilitat absoluta tant en local com a Streamlit Cloud.
  - **Submenús desplegables amb totes les pestanyes al menú superior**:
    - **📈 Mòdul Econòmic**: `📝 Ingrés / Despesa General`, `🔴 Prev. Despeses`, `🟢 Prev. Ingressos`, `📈 Inversions`, `💰 Estalvis`, `🤖 Xat IA`, separador, `📅 Afegir nou any comptable`, `❓ Preguntes i Respostes`.
    - **🛒 Compres Super i Stock**: `📄 Compres Super`, `📋 Llista de la Compra`, `📦 Rebost / Stock`, `📊 Estadístiques`, `🔍 Comparador d'Ofertes`, `📰 Fulletons`.
    - **🚗 Cotxe**: `🛣️ Km i Rutes`, `⛽ Repostatge`, `🔧 Manteniment (Oli i Rodes)`, `📊 Consum`, separador, `📝 Editar Rutes`.
    - **🍽️ Menús i cuina**: `📅 Menú Setmanal (Actiu)`, `🔪 Mise en place`, `🧠 Recomanador de Menús`, `📖 Llibre de Receptes`, `➕ Afegir Recepta`, `📥 Bústia Peticions`, separador, `❓ Preguntes i Respostes`.
    - **💊 Control de medicació**: `🕒 Preses d'Avui & Supervisió`, `➕ Crear Pla de Medicació`, `📋 Plans Actius i Historial`, `⚙️ Connexió Google Calendar API`.
    - **🛠️ Manteniment de la llar**: `📋 Registre Manteniment`, `📖 Manuals`, `🛡️ Garanties`.
- **19/10/2026**: Integració de la **Gestió Documental a Manteniment de la Llar** (`modules/manteniment.py`, `core/manteniment_manager.py`, `data/manteniment_docs.json`):
  - **Estructura física i categories**: Creació i suport complet per a la carpeta de documents `PDF` amb les seves dues subcarpetes especialitzades `PDF/Manuals/` i `PDF/Garanties/`. S'han incorporat inicialment els documents `programador hbt_100.pdf` i `termostatMenjador.pdf`.
  - **Pestanyes especialitzades ("📖 Manuals" i "🛡️ Garanties")**: Navegació nativa per pestanyes amb suport d'enllaços directes des de la barra de navegació superior (`?mod=modules.manteniment&tab=manuals` i `tab=garanties`).
  - **Registre canònic en JSON (`data/manteniment_docs.json`)**: Base de dades centralitzada en format JSON que emmagatzema les metadades dels documents (títol, dispositiu, marca, model, ubicació, subcategoria, establiment, import, número de factura, dades de compra/venciment, nombre de pàgines i etiquetes).
  - **Arquitectura dual Cloud / Local (Supabase ID 7)**: Sincronització automàtica del registre documental amb Supabase (`app_config` ID 7) amb còpia de seguretat i fallback en fitxer local, garantint persistència tant en execució local com a Streamlit Cloud.
  - **Visor interactiu de PDF basat en PDF.js (HTML5 Canvas)**: Integració del motor PDF.js de Mozilla per visualitzar els documents directament sobre canvas HTML5 amb controls de pàgina (anterior/següent) i zoom interactiu, eliminant els bloquejos de seguretat de Chrome sobre `data:application/pdf` en iframes. Inclou botons per a descàrrega directa (`st.download_button`) i per obrir amb el lector del sistema operatiu en entorns d'escriptori.
  - **Càlcul dinàmic de cobertura de garanties**: Càlcul en temps real dels dies restants de cobertura amb alertes visuals semafòriques (🟢 Vigents, ⚠️ A punt de vèncer en menys de 60 dies, 🔴 Caducades).
  - **Sincronització automàtica de fitxers de disc**: Motor que detecta qualsevol nou fitxer PDF afegit manualment a les carpetes del sistema operatiu i l'afegeix de forma transparent al registre JSON sense sobreescriure les entrades existents.
  - **Formularis interactius d'alta, edició i eliminació**: Creació de nous documents amb càrrega d'arxius (`st.file_uploader`), edició de metadades i eliminació controlada amb opció d'esborrar el fitxer del disc.
  - **Correcció del paràmetre `rows` a `st.text_area`**: Substitució de l'atribut HTML invàlid `rows` pel paràmetre natiu de Streamlit `height` als formularis d'alta i edició, resolent l'error `TypeError` detectat a Streamlit Cloud.
- **19/10/2026**: Creació de la nova pestanya **"📋 Registre Manteniment"** al mòdul de Manteniment de la Llar (`modules/manteniment.py`, `core/manteniment_manager.py`, `core/db.py`, `core/alerts.py`, `app.py`):
  - **Estructura de dades**: Camps normalitzats `idManteniment`, `dataAlta` (data de generació), `dataManteniment` (data prevista de la tasca en format `DD/MM/YYYY`), `feina` (feina concreta a realitzar), `tipus` (`Reparació`, `Manteniment`, `Feina casa`, `Altres`), `alertaA` (membre familiar destinatari de l'alerta o "Tota la família"), `acompliment` (`Sí` / `No`) i `observacions` (detalls addicionals opcionals).
  - **Format de data català/europeu (`DD/MM/YYYY`)**: Tots els components `st.date_input` del mòdul incorporen explícitament `format="DD/MM/YYYY"`, presentant visualment les dates com a `DD/MM/YYYY` (ex: `19/10/2026`) en lloc del format anglosaxó `YYYY/MM/DD`.
  - **Camp específic de Feina Concreta i Tipus Feina**: S'ha reanomenat l'etiqueta a "Tipus Feina *" i s'ha col·locat el camp "Feina concreta *" immediatament a sota. A més, incorpora un catàleg d'opcions ràpides habituals de la llar ("Canvi llençols", "Neteja general", "Netejar banys", "Netejar cuina a fons", "Netejar vidres", "Passar aspirador i fregar", "Purgar radiadors", etc.) combinat amb un camp de text lliure per escriure qualsevol altra feina personalitzada.
  - **Arquitectura dual Cloud / Local (Supabase ID 8)**: Sincronització automàtica a Supabase (`app_config` ID 8) amb rèplica i fallback en fitxer JSON local (`data/registre_manteniment.json`) i exportació a CSV (`csv/manteniment.csv`).
  - **Formulari d'entrada ràpida (a dalt)**: Disseny net i intuïtiu al capdamunt per registrar noves actuacions de la llar amb selector de data prevista, tipus, membre familiar a alertar, estat d'acompliment inicial, observacions detallades i casella de verificació per sincronitzar directament amb el Calendari de la Llar.
  - **Llistat i gestió de la Base de Dades (a sota)**:
    - **Targetes KPI**: Recompte de total actuacions, pendents d'execució, acomplertes i tasques vençudes / previstes per a avui.
    - **Filtres interactius**: Cerca per text lliure (cerca tant a feina concreta com a observacions, tipus o persona), filtre per estat (Totes, Pendents, Acomplertes), filtre per tipus i filtre per membre assignat.
    - **Doble visualització**: Commutador entre vista de targetes interactives (amb botó d'un sol clic per marcar com a feta/pendent, botó d'edició i eliminació) i taula de dades tabular neta.
    - **Edició i eliminació mitjançant diàlegs modals**: Modals `@st.dialog` per modificar qualsevol dada d'una tasca o confirmar la seva supressió.
    - **Descàrrega CSV**: Botó directe per exportar l'històric complet de manteniment a format CSV.
  - **Sincronització automàtica amb el Calendari Familiar**: En activar la casella o crear tasques amb data prevista, s'afegeix automàticament un esdeveniment a l'agenda (`core/calendar_manager.py`) sota la categoria "Llar" amb l'etiqueta `#idManteniment`.
  - **Integració amb el Sistema Global d'Alertes (`core/alerts.py`)**: Generació dinàmica d'avisos per a la campaneta de notificacions de la barra superior (`🔔`) per a tasques no acomplertes pendents o vençudes, adreçades específicament al membre familiar assignat o a tothom.
  - **Millores al Registre de Manteniment (Neteja de dades, Multiselecció d'Alerta i Dies d'Avís)** (`modules/manteniment.py`, `core/manteniment_manager.py`, `core/alerts.py`, `csv/manteniment.csv`):
    - **Neteja automàtica del formulari després de desar**: S'ha implementat un comptador de versió dinàmic (`mant_form_count`) a la clau del formulari (`form_alta_tasca_manteniment_{count}`) que s'incrementa un cop desada la tasca. Això garanteix que Streamlit reinicialitzi de zero tots els camps i controls d'entrada després de desar una tasca satisfactòriament, sense arrossegar seleccions anteriors.
    - **Multiselecció de membres per rebre l'alerta (`alertaA`)**: S'ha convertit el camp d'alerta d'un selector simple a un desplegable de selecció múltiple (`st.multiselect`), permetent assignar la tasca i dirigir l'avís a un o més membres concrets de la família (ex: Enric i Isabel) o a "Tothom". S'ha adaptat el suport complet tant a l'alta com a l'edició modal, al filtratge intel·ligent per persona, a l'exportació CSV (formatat net separat per comes) i a la descripció del calendari familiar.
    - **Camp configurable "Dies d'avís" (`diesAvis`)**: S'ha afegit un nou camp numèric que permet establir amb quants dies d'antelació a la data prevista ha de començar a mostrar-se l'alerta a la campaneta de notificacions (`🔔`).
    - **Integració de `diesAvis` a les alertes globals (`core/alerts.py`)**: El motor d'alertes calcula `delta <= diesAvis` (en comptes d'un valor rígid de 2 dies), activant l'avís de manteniment pendent exactament en el període configurat per a cada tasca i indicant els membres assignats.
    - **Actualització del CSV i vistes de taula/targetes**: El fitxer `csv/manteniment.csv` i la taula de dades incorporen la columna `diesAvis` i el format multiselecció per a `alertaA`, mentre que a la vista de targetes interactives es mostra l'etiqueta d'avís `🔔 Avís: Xd abans` juntament amb el llistat complet de persones alertades.
  - **21/10/2026: Desacoblament de l'Enter als diàlegs modals d'edició (`modules/manteniment.py`)**:
    - S'ha eliminat l'embolcall `st.form` dels diàlegs modals (`edit_task_dialog`, `edit_manual_dialog`, `edit_garantia_dialog`), utilitzant la gestió d'estat aïllada nativa de `@st.dialog`.
    - D'aquesta manera, prémer la tecla `Intro` / `Enter` en qualsevol camp numèric (com `diesAvis`) o de text ja no desencadena l'enviament ni el tancament involuntari del formulari HTML. Els canvis només es desen quan l'usuari fa clic explícitament al botó "💾 Desar canvis". S'ha afegit també un botó explícit de "Cancel·lar".
  - **21/10/2026: Generació d'Esdeveniments Periòdics i Repetitius a Manteniment (`modules/manteniment.py`, `core/manteniment_manager.py`, `csv/manteniment.csv`)**:
    - **Selector de periodicitat**: Al formulari d'alta s'ha incorporat el bloc interactiu "🔄 Repetició / Periodicitat de la Tasca" amb múltiples opcions: `Puntual (una sola vegada)`, `Cada dia`, `Cada setmana`, `Cada 2 setmanes (quinzenal)`, `Cada mes`, `Cada 2 mesos`, `Cada 3 mesos (trimestral)`, `Cada 6 mesos (semestral)`, `Cada any` o `Personalitzat...` (interval numèric configurable en dies, setmanes, mesos o anys).
    - **Límit configurable**: Opció de limitar la generació per **nombre de vegades** (ex: 4 ocurrències, 12 vegades) o **fins a una data límit** determinada.
    - **Previsualització dinàmica en temps real**: Mostra immediatament un missatge informatiu amb les dates exactes que es generaran abans de desar.
    - **Generació en sèrie (`add_manteniment_tasks_batch`)**: Crea totes les tasques individuals programades amb el seu propi ID, data prevista i estat (`Pendent`), vinculades a un identificador de sèrie (`serie_id`) i amb l'etiqueta descriptiva (`🔁 Freqüència (X/N)`).
    - **Sincronització amb l'Agenda Familiar**: Si la casella de calendari està activada, cada ocurrència genera el seu propi esdeveniment a l'agenda a la data corresponent, amb notificació i assignació personalitzada.
    - **Visualització i exportació**: La columna `recurrencia` s'ha afegit a la base de dades, a `csv/manteniment.csv` i a la taula interactiva, mentre que a les targetes es mostra la insígnia lila `🔁 Periodicitat (X/N)` i al modal d'edició s'informa de la sèrie a la qual pertany.

> [!IMPORTANT]
> **Estructura de Desat (Local i Núvol)**
> Tot el codi i disseny que genera el sistema es desen primer de tot en **local** (al PC físic del client), i l'assistent s'encarrega d'enviar-ho seguidament i de manera obligatòria al repositori del núvol de **GitHub**. D'aquesta manera, l'usuari sempre té la còpia de seguretat original de tot el programa als seus discos, però gaudeix de les actualitzacions web al moment gràcies a l'enllaç de GitHub amb Streamlit Cloud.

