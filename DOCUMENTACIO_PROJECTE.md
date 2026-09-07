# Documentació del Projecte: Dashboard Despeses (V2) - XiquiHouse

Aquest document descriu l'arquitectura, funcionalitats, estructura de fitxers i regles de l'aplicació per assegurar que qualsevol nova sessió o agent d'IA entengui el context immediatament sense dependre de la memòria de converses anteriors.

---

## 1. Visió General i Arquitectura (V2 Modular)
L'aplicació ha transicionat d'un model monolític (`app.py`) a una **arquitectura modular V2** neta, extensible i optimitzada per a mòbils i escriptori.
- **Frontend / Backend**: Construïda en **Streamlit** (Python).
- **Entrada Principal (Router)**: L'arxiu **`app_v2.py`** actua com a menú principal (Landing Screen interactiva) i gestor de navegació global.
- **Barra Superior de Menús (Estil Tradicional d'Escriptori)**: Dins de qualsevol mòdul, es disposa d'un menú superior clàssic (`Arxiu`, `Finances`, `Llar`, `Família`, `Ajustos`, `Ajuda`) amb submenús desplegables per activar directament qualsevol secció o acció de l'aplicació.
- **Interfície Gràfica d'Inici**: Mostra un logotip interactiu transparent (`imatges/logo xiquiHouse.png`) sobre un fons complet de pantalla (`imatges/fons xiquiHouse.jpg`), amb 12 punts d'accés (hotspots interactius 100% transparents en repòs) mapejats amb precisió sobre les icones de la casa.
- **Base de Dades**: **Supabase** (PostgreSQL). Tota la comunicació CRUD està centralitzada a `core/db.py`.
- **Autenticació**: Gestionada a `core/auth.py`. Incorpora persistència de sessió mitjançant paràmetre de consulta (`?auth=<token>`) per evitar demanar contrasenya en recarregar la pàgina al fer clic als hotspots d'inici.
- **Estat de Navegació**: Es controla mitjançant `st.session_state.current_module`. Per tornar enrere, cada mòdul disposa del botó `🏡 Inici` a la barra superior i `🔙 Tornar a l'inici` a la capçalera que restableix l'estat a `None`.

---

## 2. Mapa de Navegació i Mòduls de la Pantalla d'Inici

La pantalla d'inici mapeja 12 icones interactives sobre el logotip de XiquiHouse:

### 🌟 Part Superior (Sense rodona):
1. **⚙️ Configuracions**: `modules/admin.py` *(Icona engranatge)* - Panell de control i configuració global.
2. **📊 Dashboard General**: `modules/dashboard.py` *(Icona pantalla + gràfic)* - Vista de panell principal amb targetes de saldos bancaris (BBVA, La Caixa, etc.), resum mensual d'ingressos i despeses de l'any i gràfics comparatius.

### 🔵 Part Esquerra (5 nodes amb rodona):
3. **📈 Mòdul Econòmic**: `modules/economic.py` *(Icona gràfic ascens)* - Gestió econòmica i financera organitzada en pestanyes especialitzades:
   - `📈 Detalls del Mes`: Saldos bancaris, rebuts, pagaments, hipoteca, taula anual i gràfic comparatiu de barres amb previsions vs real.
   - `🔴 Prev. Despeses`: Formulari d'alta i llistat de previsions de despeses amb recurrència mensual.
   - `🟢 Prev. Ingressos`: Formulari d'alta i llistat de previsions d'ingressos amb recurrència mensual.
   - `📈 Inversions`: Formulari de moviments de TR Cartera (S&P500, NVIDIA), KPIs i taula d'inversions.
   - `💰 Estalvis`: Fons d'estalvi `estalviDP`, quotes, aportacions, rescats i **gràfic interactiu d'evolució del capital acumulat**.
   - `🤖 Xat IA`: Assistent financer intel·ligent Gemini.
4. **📹 Seguretat**: `modules/seguretat.py` *(Icona càmera)* - Estat de càmeres, accessos i alarmes.
5. **🛠️ Manteniment**: `modules/manteniment.py` *(Icona casa amb eina)* - Tasques de la llar, reparacions i històric de manteniment.
6. **📶 Domòtica**: `modules/domotica.py` *(Icona WiFi)* - Integració amb Home Assistant, llums i sensors.
7. **🎲 Jocs**: `modules/jocs.py` *(Icona daus)* - Oci familiar, inventari de jocs i marcadors.

### 🟢 Part Dreta (5 nodes amb rodona):
8. **📅 Agenda**: `modules/calendari.py` *(Icona calendari)* - Calendari familiar, esdeveniments i sincronització.
9. **💊 Control Medicació**: `modules/medicacio.py` *(Icona pastilles / flascó)* - Pautes mèdiques, dosis, horaris i farmaciola.
10. **🍽️ Menjar**: `modules/menjar.py` *(Icona coberts)* - Rebost, receptes, planificació de menús setmanals i inventari.
11. **🚗 Cotxe**: `modules/cotxe.py` *(Icona cotxe)* - Gestió del vehicle organitzada en pestanyes:
   - `🛣️ Registre Km i Rutes`: Formulari per registrar lectures d'odòmetre, càlcul automàtic de km del trajecte, selector/plantilles de rutes i taula d'històric.
   - `🔧 Canvi d'Oli`: Seguiment de km actuals, límit de canvi d'oli i km restants.
   - `⛽ Consum i Proveïments`: Gràfic de consum anual L/100km i taula d'històric de gasolina.
12. **🛒 Compres**: `modules/compres.py` *(Icona carro de compra)* - Gestió integral de compres i despeses:
   - `📄 Compres Super`: Escàner OCR intel·ligent Gemini Vision i introducció línia per línia de tiquets.
   - `📝 Ingressos / Despeses`: Formulari directe de **Moviments Reals** (Despesa, Ingrés, Traspàs), proveïment de gasolina amb calculadora, tiquets pendents i taula d'últims moviments.
   - `📋 Llista de la Compra`: Llista de productes sota stock mínim i peticions puntuals.
   - `📦 Rebost / Stock`: Inventari de productes del rebost i control d'existències.
   - `📊 Estadístiques`: Gràfics i mètriques de despesa en supermercats.

---

## 3. Estructura del Projecte

```
Dashboard/
├── app_v2.py                 # Router principal i Landing Page interactiva
├── core/
│   ├── auth.py               # Autenticació amb contrasenya i token hash
│   ├── db.py                 # Connexió i operacions CRUD a Supabase
│   └── config.json           # Configuració de categories, comptes i paràmetres
├── imatges/
│   ├── logo xiquiHouse.png   # Logotip interactiu transparent (1024x682)
│   └── fons xiquiHouse.jpg   # Fons de pantalla complet per a la Home
├── modules/
│   ├── admin.py              # ⚙️ Configuració global
│   ├── calendari.py          # 📅 Agenda familiar
│   ├── compres.py            # 🛒 Compres Super, Ingressos/Despeses reals, Llista compra, Rebost i Stats
│   ├── cotxe.py              # 🚗 Registre km/rutes, Canvi d'oli i Consum
│   ├── dashboard.py          # 📊 Dashboard general
│   ├── domotica.py           # 📶 Domòtica (Home Assistant)
│   ├── economic.py           # 📈 Detalls mes, Prev. Despeses, Prev. Ingressos, Inversions, Estalvis i Xat IA
│   ├── jocs.py               # 🎲 Jocs i oci
│   ├── manteniment.py        # 🛠️ Manteniment i reparacions
│   ├── medicacio.py          # 💊 Control de medicació
│   ├── menjar.py             # 🍽️ Menús, rebost i cuina
│   └── seguretat.py          # 📹 Seguretat i càmeres
└── DOCUMENTACIO_PROJECTE.md  # Aquest document
```

---

## 4. Lògica Avançada i OCR (Gemini Vision)
- L'extracció de tiquets del súper a `compres.py` utilitza **Google Gemini Vision** (`gemini-3.6-flash`), cridant directament l'API mitjançant la llibreria `requests` amb gestió automàtica de reintents.
- La clau d'API de Gemini es troba a `st.secrets["GEMINI_API_KEY"]`.

### 4.1 Descomptes i Enginyeria Inversa de Preus
- Quan l'usuari introdueix manualment un article amb descompte al tiquet a `modules/compres.py`, s'assumeix que s'està registrant el **preu final pagat**.
- Si s'indica un `%` de descompte (p. ex. 30%), el sistema calcula automàticament la base original i l'estalvi en promoció sense alterar l'import real pagat.

---

## 5. UI/UX i Adaptabilitat Mòbil
- **Fons i Pantalla Completa**: A `app_v2.py` s'aplica estil CSS per a pantalla completa (`background-size: cover; background-attachment: fixed;`).
- **Responsive Scaling**: A dispositius mòbils (`max-width: 768px`), el logotip s'escala automàticament (`transform: scale(1.48)`) aprofitant tot l'ample de pantalla per a facilitar la pulsació dels botons tàctils.
- **Transicions i Efectes**: Els hotspots disposen d'animacions de pulsació (`pulse`) i efecte lluminós en passar el cursor o tocar.

---

## 6. Estratègia de Sincronització (Memòria i Base de Dades)
L'aplicació utilitza actualitzacions d'estat en temps real (zero latència):
- Quan `core/db.py` executa `insert_db_row`, `update_db_row` o `delete_db_row`, no només envia la petició SQL a Supabase, sinó que automàticament modifica el DataFrame corresponent a `st.session_state`.
- Això evita que els dashboards hagin de recarregar massivament totes les taules cada vegada que s'edita o s'afegeix una simple despesa.

---

## 7. Com instruir a noves sessions d'IA
Si inicies una conversa nova amb un assistent d'IA, indica-li:
**"Abans de res, llegeix l'arxiu `DOCUMENTACIO_PROJECTE.md` per entendre l'arquitectura V2 modular de la meva app."**
Això assegurarà que treballi directament sobre `app_v2.py` i els fitxers de `modules/`.
