# Documentació del Projecte: Dashboard Despeses

Aquest document descriu l'arquitectura, funcionalitats i regles de l'aplicació per assegurar que qualsevol nova sessió o agent d'IA entengui el context immediatament sense dependre de la memòria de converses anteriors.

## 1. Visió General i Stack Tecnològic
- **Propòsit**: Aplicació per a la gestió de finances personals, seguiment de despeses domèstiques (supermercat, gasolina, hipoteca, etc.) i control d'inventari/rebost.
- **Frontend / Backend**: Construïda completament en **Streamlit** (Python). El fitxer principal és `app.py`.
- **Base de Dades**: **Supabase** (PostgreSQL). La comunicació es fa mitjançant la llibreria `supabase-py`.
- **Processament de Dades**: Àmpliament basat en **Pandas** per a la manipulació, neteja i filtratge dels DataFrames abans de renderitzar.

## 2. Estructura de Directori i Arxius
A l'hora d'analitzar l'aplicació, és important tenir clar quins arxius formen part del projecte actiu i ignorar la resta (es recomana no crear scripts temporals no rastrejats per git):
- `app.py`: L'arxiu principal i motor de l'aplicació.
- `scanner.py`: Mòdul de suport (històricament per funcionalitats OCR o escaneig).
- `auto_scan_ui.py`: Mòdul d'UI per a escaneig automàtic de tiquets.
- Carpeta `programes py/`: Conté submòduls importants del sistema (`compresSuper.py`, `connect_formulari.py`, `introProductesSuper.py`, `ocr_ticket.py`).
- *Nota*: Qualsevol altre petit arxiu python (`patch_*.py`, `test_*.py`, `update_*.py`) solien ser esborranys temporals i s'han eliminat. L'aplicació es manté neta.

## 3. Estructura de l'Aplicació (Pestanyes Principals)
L'aplicació es divideix en vàries pestanyes (`st.tabs`):
1. **Dashboard General**: Gràfics i mètriques (ingressos, despeses, estalvis).
2. **Detalls del Mes**: Resum mensual amb taules de despeses per categoria, i un llistat interactiu de **Pagaments Pendents** i **Ingressos Pendents** (que permet marcar-los com a cobrats/pagats i moure'ls a la taula general de despeses triant el banc de forma individualitzada amb una finestra modal).
3. **Intro Dades**: Formularis d'entrada manual (Tiquets de supermercat amb OCR, gasolina, ingressos, moviments TR Cartera).
4. **Xat IA**: Integració d'un xat.
5. **Llista de la Compra & Rebost / Stock**: Gestió d'inventari d'articles domèstics i la seva ubicació.
6. **Bases de Dades (Supabase)**: Visualitzador complet de les taules amb opcions d'edició (CRUD complet de cada taula).

## 3. Taules a Supabase
La funció `save_to_csv` a `app.py` és en realitat un *wrapper* (embolcall històric) que fa **upsert** directament a les taules de Supabase.
Taules principals:
- `despeses`: La base de dades general on s'apunten TOTS els moviments reals. Columnes clau: `ID_mov` (Primary Key), `Data`, `Banc`, `FormaPago`, `Idcategoria`, `Idconcepte`, `Import càrrec`, `import ingrés`, `Comentari`, `mes`, `any`, `ticketPendent`.
- `pagaments` (Previsió de pagaments recurrents): Columnes clau: `idPago`, `Concepte`, `Import`, `pagat`.
- `ingressos` (Previsió d'ingressos): Columnes clau: `idIngres`, `Concepte`, `Import`, `cobrat`.
- Taules de desglòs: `compresSuper`, `gasolina`, `hipoteca`, `estalviDP`, `tr_cartera`.
- Control de rebost: `tb_productes`, `tb_llocs`, `tb_pendents_compra`.

## 4. Convencions de Disseny (UI/UX)
- **Tema (Fosc/Clar)**: Streamlit s'ha configurat amb `base = "dark"` de forma nativa al fitxer `.streamlit/config.toml` perquè els components natius complexos (com els DataFrames) tinguin el fons fosc sempre al núvol. A dins de l'App hi ha un selector propi al menú (`app_theme`), i s'injecta CSS personalitzat per forçar colors si l'usuari tria el "Tema Clar" (ex. convertint els fons dels inputs a blanc per garantir el contrast).
- **DataFrames**: Utilitzem gairebé sempre `st.dataframe(..., hide_index=True)`. Si es necessiten files interactives, s'habilita `on_select="rerun"`.

## 5. Comportaments Específics a Recordar
- Les dades sempre es carreguen d'inici via `load_dashboard_data()` i es desen en memòria a `st.session_state` (`df_desp`, `df_pag`, etc.). En guardar un registre nou, sempre s'actualitza tant la BBDD a Supabase com l'estat local.
- **Errors freqüents evitats**: 
  1. Serialització JSON de Supabase: Cal assegurar-se que valors com els ID o els anys es passen fent un cast manual com `int()` o `float()` per evitar que tipus interns com `int64` (Pandas/Numpy) facin petar l'api.
  2. A la taula `despeses` NO hi ha cap columna `Revisat` (però sí que n'hi ha a `tr_cartera` o altres), eviteu intentar escriure-hi aquesta dada.

## 6. Com instruir a noves IAs
Si inicies una conversa nova amb un agent o assistent, digues-li directament:
**"Abans de res, llegeix l'arxiu `DOCUMENTACIO_PROJECTE.md` per entendre el context de la meva app de Dashboard."**
Això assegurarà que sap on són les taules, com funciona el disseny, el codi existent i com evitar els errors que ja hem solucionat en el passat.
 
## 7. Estrat�gia de Sincronitzaci� Mem�ria i Cache  
L'aplicaci� compta amb un sistema d'actualitzaci� de dades de lat�ncia zero:  
- **Lectura**: Quan l'aplicaci� s'obre per primera vegada, es descarreguen totes les taules de Supabase simult�niament usant load_dashboard_data() i la cach� de Streamlit (@st.cache_data). Aix� pot trigar diversos segons.  
- **Escriptura (0 segons delay)**: Per evitar tornar a trigar segons sencers en cada actualitzaci�, l'aplicaci� utilitza les funcions insert_db_row, update_db_row, delete_db_row i save_to_csv. Aquestes funcions envien la dada a Supabase i al mateix temps utilitzen les funcions auxiliars update_session_state_insert, etc. per **injectar/modificar directament el DataFrame actiu a la mem�ria RAM** (st.session_state).  
- **Neteja**: Tot i l'actualitzaci� manual, el sistema neteja la mem�ria cau per darrere (st.cache_data.clear()) i actualitza la variable last_synced_time, per tal de que si l'usuari fa un F5 complet, torni a fer la c�rrega inicial descarregant completament la base de dades. D'aquesta manera s'assegura que mentre la sessi� est� activa no hi ha interrupcions per c�rrega, per� tampoc hi ha problemes de desincronitzaci� a llarg termini. 
