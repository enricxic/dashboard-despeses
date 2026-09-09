# Documentació del Projecte: Dashboard Despeses (V2) - XiquiHouse

Aquest document descriu l'arquitectura, funcionalitats, estructura de fitxers i regles de l'aplicació per assegurar que qualsevol nova sessió o agent d'IA entengui el context immediatament sense dependre de la memòria de converses anteriors.

---

## 1. Visió General i Arquitectura (V2 Modular)
L'aplicació ha transicionat d'un model monolític (`app.py`) a una **arquitectura modular V2** neta, extensible i optimitzada per a mòbils i escriptori.
- **Frontend / Backend**: Construïda en **Streamlit** (Python).
- **Entrada Principal (Router)**: L'arxiu **`app_v2.py`** actua com a menú principal (Landing Screen interactiva) i gestor de navegació global. Incorpora `importlib.reload(mod)` en la càrrega de mòduls per garantir que qualsevol canvi de codi s'apliqui a l'instant en calent.
- **Barra Superior de Menús (Estil Tradicional d'Escriptori)**: Dins de qualsevol mòdul, es disposa d'un menú superior clàssic (`Arxiu`, `Finances`, `Llar`, `Família`, `Ajustos`, `Ajuda`) amb submenús desplegables per activar directament qualsevol secció o acció de l'aplicació.
- **Interfície Gràfica d'Inici**: Mostra un logotip interactiu transparent (`imatges/logo xiquiHouse.png`) sobre un fons complet de pantalla (`imatges/fons xiquiHouse.jpg`), amb 12 punts d'accés (hotspots interactius 100% transparents en repòs) mapejats amb precisió sobre les icones de la casa.
- **Base de Dades**: **Supabase** (PostgreSQL). Tota la comunicació CRUD està centralitzada a `core/db.py`.
- **Autenticació**: Gestionada a `core/auth.py`. Incorpora persistència de sessió mitjançant paràmetre de consulta (`?auth=<token>`) per evitar demanar contrasenya en recarregar la pàgina al fer clic als hotspots d'inici.
- **Estat de Navegació**: Es controla mitjançant `st.session_state.current_module`. Per tornar enrere, cada mòdul disposa del botó `🏡 Inici` a la barra superior i `🔙 Tornar a l'inici` a la capçalera que restableix l'estat a `None`.

---

## 2. Mapa de Navegació i Mòduls de la Pantalla d'Inici

La pantalla d'inici mapeja 12 icones interactives sobre el logotip de XiquiHouse:

### 🌟 Part Superior (Sense rodona):
1. **⚙️ Configuracions**: `modules/admin.py` *(Icona engranatge)* - Panell de control i configuració global:
   - `👤 Administrador`: Dades de contacte, avatar i PIN mestre.
   - `🏷️ Títol de la casa`: Paraules, colors i tamany del títol d'inici.
   - `👨‍👩‍👧‍👦 Família`: Membres de la llar amb data de naixement europea (`DD/MM/AAAA`), recàlcul automàtic d'edat en anys, al·lèrgies mèdiques (bloqueig estricte), vetos/aversions personals (desdoblament), plats comodí favorits i interruptor d'activació (`🟢 Present a la llar` vs `⚪ Fora de la llar`).
   - `🍽️ Menús i Nutrició`: Regles de salut (màxim carns vermelles, mínim peix i llegums, màxim sopars d'embotits), control d'hidrats consecutius i format habitual de planificació.
   - `🤝 Tutelats`, `🏦 Bancs`, `🎨 Aspecte i Tema`, `🔘 Icones d'inici`, `🌐 Idiomes`.
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
10. **🍽️ Menús i Cuina**: `modules/menjar.py` *(Icona coberts)* - Llibre de receptes amb escalat dinàmic de comensals, planificador setmanal intel·ligent i batch cooking.
11. **🚗 Cotxe**: `modules/cotxe.py` *(Icona cotxe)* - Gestió del vehicle organitzada en pestanyes:
   - `🛣️ Registre Km i Rutes`: Formulari per registrar lectures d'odòmetre, càlcul automàtic de km del trajecte, selector/plantilles de rutes i taula d'històric.
   - `⛽ Repostatge`: Taula històrica de proveïments de la BBDD `gasolina` (alimentada des d'Ingressos/Despeses) amb mètriques de preu últim repostatge, preu més alt i més baix.
   - `🔧 Canvi d'Oli`: Seguiment de km actuals, límit de canvi d'oli i km restants.
   - `📊 Consum`: Gràfic de consum anual L/100km.
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
├── app_v2.py                 # Router principal i Landing Page interactiva (amb hot-reload)
├── core/
│   ├── auth.py               # Autenticació amb contrasenya i token hash
│   ├── db.py                 # Connexió i operacions CRUD a Supabase
│   └── config.json           # Configuració de categories, comptes i paràmetres
├── imatges/
│   ├── logo xiquiHouse.png   # Logotip interactiu transparent (1024x682)
│   └── fons xiquiHouse.jpg   # Fons de pantalla complet per a la Home
├── modules/
│   ├── admin.py              # ⚙️ Configuració global
│   ├── calendari.py          # 📅 Agenda familiar (Google Calendar sync & events)
│   ├── compres.py            # 🛒 Compres Super (OCR), Ingressos/Despeses reals, Llista compra, Rebost i Stats
│   ├── cotxe.py              # 🚗 Registre km/rutes, Repostatge, Canvi d'oli i Consum
│   ├── dashboard.py          # 📊 Dashboard general
│   ├── domotica.py           # 📶 Domòtica (Home Assistant)
│   ├── economic.py           # 📈 Detalls mes, Prev. Despeses, Prev. Ingressos, Inversions, Estalvis i Xat IA
│   ├── jocs.py               # 🎲 Jocs i oci
│   ├── manteniment.py        # 🛠️ Manteniment i reparacions
│   ├── medicacio.py          # 💊 Control de medicació i tutelats (Pla de dosificació & sync)
│   ├── menjar.py             # 🍽️ Receptari (Escalat de comensals base 3), menús setmanals i batch cooking
│   └── seguretat.py          # 📹 Seguretat i càmeres
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
- **Selector Interactiu a la Fitxa:** Cada vegada que s'obre una recepta a `modal_recepta`, el selector de comensals es reinicia a **3 per defecte** i permet a l'usuari simular a temps real quantitats per a qualsevol nombre de comensals (1 a 30).
- **Format visual:** Els ingredients es presenten estilitzats separats per asteriscs ` * `.

### 4.3 Pautes de Fotografia Gastronòmica
- **Perspectiva:** Angle elevat a 45° en primer pla (Close-up) on la paella/plat ocupa pràcticament tota l'amplada de l'enquadrament.
- **Aspect Ratio:** Proporció **4:3** per adaptar-se perfectament a les targetes horitzontals del llibre de receptes sense retalls estranys.
- **Fidelitat als ingredients:** La imatge ha de reflectir exclusivament els ingredients reals de la recepta (evitant elements aliens com pebrots o llimones si el plat no en porta).
- **Ambientació:** Taula rústica de fusta, llum natural càlida lateral i estris tradicionals de cuina.

### 4.4 Perfils Familiars, Vetos Personals i Desdoblament d'Àpats
- **Diferenciació d'Al·lèrgia vs Veto Personal:**
  - *Al·lèrgia mèdica:* Bloqueig estricte de la recepta completa per a tothom.
  - *Veto personal:* Quan un membre no menja un aliment (ex. fetge o casqueria) però la família sí, el planificador no bloqueja el plat familiar i assigna automàticament un **plat alternatiu ràpid parellat** (*comodí*, ex. pit de pollastre o truita) per a aquell membre, compartint la mateixa guarnició per no duplicar temps de cuina.
- **Membres Actius vs Fora de la Llar:** Permet activar o desactivar la participació de membres als menús (ex. fills que viuen fora i només venen de visita).

### 4.5 Mise en Place Setmanal de Bases i Connexió amb l'Stock (`modules/compres.py`)
- **Derivació Top-Down:** A partir del menú setmanal aprovat, el sistema genera la guia de *Batch Prep* de diumenge (patates probiòtiques amb midó resistent, caldos casolans concentrats, sofregit mare, verdures rostides).
- **Sincronització amb l'Stock:**
  - Si hi ha bases o caldos al congelador/nevera, es descompten de la guia de preparació de diumenge i de la llista de la compra.
  - Les quantitats de compra es calculen restant l'stock real existent: $\text{Compra} = \max(0, \text{Necessari} - \text{Stock})$.
- **Consens Familiar via WhatsApp:** Generació automàtica d'enllaços de petició i consens per a desitjos de comensals (ex. sardines).

---

## 5. Lògica Avançada i OCR (Gemini Vision)
- L'extracció de tiquets del súper a `compres.py` utilitza **Google Gemini Vision** (`gemini-2.5-flash` / `gemini-3.6-flash`), cridant directament l'API mitjançant la llibreria `requests` amb gestió automàtica de reintents.
- La clau d'API de Gemini es troba a `st.secrets["GEMINI_API_KEY"]`.

### 5.1 Descomptes i Enginyeria Inversa de Preus
- Quan l'usuari introdueix manualment un article amb descompte al tiquet a `modules/compres.py`, s'assumeix que s'està registrant el **preu final pagat**.
- Si s'indica un `%` de descompte (p. ex. 30%), el sistema calcula automàticament la base original i l'estalvi en promoció sense alterar l'import real pagat.

---

## 6. UI/UX i Adaptabilitat Mòbil
- **Fons i Pantalla Completa**: A `app_v2.py` s'aplica estil CSS per a pantalla completa (`background-size: cover; background-attachment: fixed;`).
- **Responsive Scaling**: A dispositius mòbils (`max-width: 768px`), el logotip s'escala automàticament (`transform: scale(1.48)`) aprofitant tot l'ample de pantalla per a facilitar la pulsació dels botons tàctils.
- **Transicions i Efectes**: Els hotspots disposen d'animacions de pulsació (`pulse`) i efecte lluminós en passar el cursor o tocar.

---

## 7. Estratègia de Sincronització (Memòria i Base de Dades)
L'aplicació utilitza actualitzacions d'estat en temps real (zero latència):
- Quan `core/db.py` executa `insert_db_row`, `update_db_row` o `delete_db_row`, no només envia la petició SQL a Supabase, sinó que automàticament modifica el DataFrame corresponent a `st.session_state`.
- Això evita que els dashboards hagin de recarregar massivament totes les taules cada vegada que s'edita o s'afegeix una simple despesa.

---

## 8. Com instruir a noves sessions d'IA
Si inicies una conversa nova amb un assistent d'IA, indica-li:
**"Abans de res, llegeix l'arxiu `DOCUMENTACIO_PROJECTE.md` per entendre l'arquitectura V2 modular de la meva app."**
Això assegurarà que treballi directament sobre `app_v2.py` i els fitxers de `modules/`.
