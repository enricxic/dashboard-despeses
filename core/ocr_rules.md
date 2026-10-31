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
Si detectes que el tiquet és de Novavenda, gairebé tots els productes tenen una descripció que ocupa 2 línies consecutives. Has d'assegurar-te d'unir el contingut d'aquestes dues línies com un sol nom descriptiu del producte.

### REGLA SUPERMERCAT BONPREU / ESCLAT
Si detectes que el tiquet és de BonPreu o Esclat:
1. **Promocions per producte:** Si just a sota d'un article hi ha una línia que indica "PROMOCIÓ" o "PROM." amb un import en negatiu (ex: "-1,35"), aquest import s'ha d'assignar al camp "promocions" de l'article i el preu total de la línia ha de ser el net resultant (`preu_brut - promocio`). Si la promoció cobreix el 100% de l'import (producte regalat o 2a unitat gratis), el preu total de la línia serà 0,00 € però l'article s'ha d'incloure igualment.
2. **Articles a pes (carnisseria, peixateria, fruiteria, verdura):** Solen figurar en dues línies consecutives: Línia 1 amb la descripció del producte (ex: "POLLASTRE SENCER") i Línia 2 amb el pes i el preu per quilo (ex: "1,225 kg x 4,49 €/kg") amb el total de la línia a l'extrem dret. Cal fusionar-ho en un sol article: nom de la Línia 1, `quantitat: 1`, camp `pes: "1.225 kg"`, i el total calculat a la dreta.
3. **Descomptes globals de caixa al peu del tiquet:** Al final del tiquet poden aparèixer línies de descompte global com "-3 EUR REGAL", "- EUROS BESCANVIATS" o cupons de descompte general. NO els assignis a cap producte individual; suma'ls tots al camp "descompte_global" del tiquet.
4. **Línies no producte a ignorar:** Ignora les línies informatives de fidelització ("EUROS ACUMULATS", "SALDO TARGETA CLIENT"), les bases i quotes d'IVA, i les dades del pagament amb targeta/TPV.

