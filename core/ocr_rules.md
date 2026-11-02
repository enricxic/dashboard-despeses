# Regles Específiques per Supermercat (OCR)

Aquestes regles s'envien a Gemini juntament amb el tiquet de compra per millorar-ne la precisió. Totes les regles que s'afegeixin aquí seran aplicades automàticament.

### REGLA GLOBAL DE QUANTITATS
**La quantitat ("quantitat") ha de ser SEMPRE un número enter (1, 2, 3...).** No inventis mai decimals per ajustar els càlculs. Si el preu unitari no encaixa perfectament amb el preu total a causa del pes, has de donar prioritat al "preu total" i mantenir la quantitat a 1.

### REGLA SUPERMERCAT DIA
Si detectes que el tiquet és del supermercat DIA:
1. Els productes a pes (fruites, verdures, etc.) ocupen dues línies consecutives:
   - **Línia 1:** Conté únicament la descripció o nom del producte (ex: "BANANA", "SUCRE BLANC DIA").
   - **Línia 2:** Conté informació de pes i preu. A l'esquerra indica el pes (ex: "0,940 kg"), al mig el preu per quilo, i al final de tot el preu total de l'article.
   - **Instrucció:** Has de fusionar aquestes dues línies en un sol article. Extreu el nom de la Línia 1, posa `quantitat: 1`, i assigna el preu total de la Línia 2. IGNORA el preu per quilo.
2. Si hi ha un apartat d'"OFERTES I CUPONS": Identifica quin és el producte afectat per la promoció i resta aquest descompte al preu total del producte afectat (fes servir el camp "promocions").

### REGLA SUPERMERCAT CLAREL
Llegeix sempre detingudament l'apartat **"OFERTES"** (normalment al final del tiquet) per tal d'aplicar correctament els descomptes o promocions a cada producte de la llista que correspongui.

### REGLA SUPERMERCAT LIDL
Si detectes que el tiquet és del Lidl, fixa't molt bé sota de cada línia de producte. Acostuma a posar-hi els descomptes aplicats al producte just a sota de la seva descripció. Aquest descompte ha de constar al camp "promocions" d'aquell producte en concret.

### REGLA SUPERMERCAT NOVAVENDA
Si detectes que el tiquet és de Novavenda:
1. **Bloc multilínia per producte:** Cada article consta d'un bloc de 2, 3 o 4 línies consecutives:
   - **Línia 1:** Primera part del nom de l'article i a l'extrem dret el preu total de la línia.
   - **Línies intermèdies (si n'hi ha):** Continuació del nom del producte o format/gramatge (ex: "VASET 2X125 G", "MUES/TAR/PANSES FLORBU"). CAL UNIR totes aquestes línies de text en un sol nom descriptiu net de l'article.
   - **Darrera línia de detall:** Conté a l'esquerra el codi intern o codi de barres EAN (ex: "8410184033749") i al mig/dreta la fórmula "QUANTITAT x PREU_UNITARI €" (ex: "3 x 1,62 €" o "12 x 1,29 €").
2. **Quantitats múltiples:** Extreu la quantitat de la fórmula "N x Preu €" (si posa "3 x 1,62 €", quantitat = 3 i preu unitari = 1,62 €). El preu total de la línia és el que figura a l'extrem dret de la primera línia (4,86 €).
3. **Data al peu del tiquet:** La data del tiquet NO és a la capçalera sinó al peu, just sota el Total o el quadre d'impostos (format: "Data: DD/MM/AAAA HH:MM:SS").
4. **Ofertes de producte:** Si a sota de la línia de càlcul hi figura la paraula "OFERTA", el preu unitari de la fórmula ja és el preu d'oferta rebaixat.
5. **Ignorar:** La informació fiscal superior (Comerbal, S.A.), el desglossament de bases i quotes d'IVA del peu, i les dades de pagament/caixa.

### REGLA SUPERMERCAT BONPREU / ESCLAT
Si detectes que el tiquet és de BonPreu o Esclat:
1. **Promocions per producte:** Si just a sota d'un article hi ha una línia que indica "PROMOCIÓ" o "PROM." amb un import en negatiu (ex: "-1,35"), aquest import s'ha d'assignar al camp "promocions" de l'article i el preu total de la línia ha de ser el net resultant (`preu_brut - promocio`). Si la promoció cobreix el 100% de l'import (producte regalat o 2a unitat gratis), el preu total de la línia serà 0,00 € però l'article s'ha d'incloure igualment.
2. **Articles a pes (carnisseria, peixateria, fruiteria, verdura):** Solen figurar en dues línies consecutives: Línia 1 amb la descripció del producte (ex: "POLLASTRE SENCER") i Línia 2 amb el pes i el preu per quilo (ex: "1,225 kg x 4,49 €/kg") amb el total de la línia a l'extrem dret. Cal fusionar-ho en un sol article: nom de la Línia 1, `quantitat: 1`, camp `pes: "1.225 kg"`, i el total calculat a la dreta.
3. **Descomptes globals de caixa al peu del tiquet:** Al final del tiquet poden aparèixer línies de descompte global com "-3 EUR REGAL", "- EUROS BESCANVIATS" o cupons de descompte general. NO els assignis a cap producte individual; suma'ls tots al camp "descompte_global" del tiquet.
4. **Línies no producte a ignorar:** Ignora les línies informatives de fidelització ("EUROS ACUMULATS", "SALDO TARGETA CLIENT"), les bases i quotes d'IVA, i les dades del pagament amb targeta/TPV.



### REGLA SUPERMERCAT AREAGUISSONA / BONÀREA
Si detectes que el tiquet és de bonÀrea (Corporació Alimentària Guissona S.A.):
1. **Identificació Comercial:** El concepte a l'aplicació s'ha de normalitzar com `"AreaGuissona"`.
2. **Columnes de la línia de producte:** Cada línia té l'estructura `Descripció [.....] [Fórmula Nx P_Unit] Import %IVA`.
   - **MOLT IMPORTANT - Percentatge d'IVA final:** L'últim número de cada línia (ex: `4.00`, `10.00`, `4.0`, `10.0`) és el **percentatge d'IVA aplicat**. **MAI el confonguis amb el preu total ni amb el preu unitari!**
   - **Preu Total Real:** És el valor numèric immediatament anterior al percentatge d'IVA (ex: a `BANANA BOLSA..................... 2,15 4.00`, el preu total és `2.15` i l'IVA és `4.00%`).
3. **Quantitats múltiples en línia (`Nx P_Unit`):**
   - Quan es compren múltiples unitats del mateix article, figura a la mateixa línia la fórmula `Nx P_Unit` (ex: `COCTEL AMANIDES 10   3x  1,10       3,30 10.00`).
   - Extreu la quantitat del factor multiplicador (ex: `quantitat: 3`), el preu unitari (ex: `preu_unitari: 1.10`) i l'import de la línia (ex: `preu_total: 3.30`). Verifica sempre que `quantitat * preu_unitari == preu_total`.
4. **Neteja del nom del producte:**
   - Elimina la seqüència de punts suspensius `.....` que uneix el nom amb l'import.
5. **Línies que cal ignorar:**
   - Capçalera d'empresa (`Corporació Alimentària Guissona S.A.`, NIF, adreces, telèfons, codi de botiga `bonArea (T391)`).
   - Capçalera de taula `Descripció       Import %%%%%%`.
   - Quadre final de `Desglòs d'IVA` (`Tipus Iva`, `Base`, `Quota`, `Total`).
   - Peu del tiquet: `Fact. Simplificada Nº ...`, codi de barres i línies de forma de pagament.
