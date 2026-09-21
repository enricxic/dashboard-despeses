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
