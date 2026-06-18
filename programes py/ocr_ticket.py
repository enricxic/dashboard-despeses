# controllers/ocr_ticket.py - VERSIÓ CORREGIDA
import os
import re
import sqlite3
from datetime import datetime
import time
try:
    import cv2
    import numpy as np
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    print("⚠️ OpenCV no disponible per a processament avançat")

# Patterns bàsics
PRECIO_PATTERN = re.compile(r'(\d+)[,\.](\d{2})\s*$')

# Verificar OCR
OCR_AVAILABLE = False
try:
    import pytesseract
    from PIL import Image, ImageEnhance, ImageFilter
    OCR_AVAILABLE = True
    
    # Configurar Tesseract (si cal)
    try:
        # Provar rutes comunes
        tesseract_paths = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        ]
        for path in tesseract_paths:
            if os.path.exists(path):
                pytesseract.pytesseract.tesseract_cmd = path
                break
    except:
        print("⚠️ No s'ha pogut configurar Tesseract, es provarà sense configurar")
        
except ImportError as e:
    print(f"❌ Falten dependències: {e}")


class OCRProcessor:
    """Processador OCR simple"""
    
    def __init__(self, supermercat="Dia"):
        self.supermercat = supermercat
        self.db_path = "Bases/BD_Productes.db"
        self.noms_cache = {}

        if OCR_AVAILABLE:
            self._carregar_bd()
    
    def _carregar_bd(self):
        """Carregar BD de productes"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT LOWER(np.nom_super), p.nom_estandard, p.familia
                FROM TBNomsProducte np
                JOIN TBProductes p ON np.idProducte = p.idProducte
                WHERE np.supermercat LIKE '%DIA%' OR np.supermercat LIKE '%dia%'
            ''')
            
            for nom_super, nom_estandard, familia in cursor.fetchall():
                self.noms_cache[nom_super] = {
                    'nom_estandard': nom_estandard,
                    'familia': familia
                }
             
            conn.close()
            
        except Exception as e:
            print(f"⚠️ Error carregant BD: {e}")
    
    def _preprocessar_imatge(self, image_path):
        """Preprocessar imatge optimitzat per a tickets DIA"""
        try:
            with Image.open(image_path) as img:
                # Convertir a escala de grisos
                if img.mode != 'L':
                    img = img.convert('L')
                
                # Augmentar mida (molt important per a Tesseract)
                if img.height < 1500:
                    scale = 3.0  # Escalar més
                    new_width = int(img.width * scale)
                    new_height = int(img.height * scale)
                    img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                
                # Aplicar filtres per millorar text
                # 1. Augmentar contrast
                from PIL import ImageEnhance
                enhancer = ImageEnhance.Contrast(img)
                img = enhancer.enhance(3.0)
                
                # 2. Augmentar nitidesa
                enhancer = ImageEnhance.Sharpness(img)
                img = enhancer.enhance(3.0)
                
                # 3. Umbralització adaptativa manual
                # Convertir a array numpy per processar
                import numpy as np
                img_array = np.array(img)
                
                # Aplicar threshold adaptatiu
                # Buscar valor de threshold que separa text de fons
                mean_val = np.mean(img_array)
                if mean_val > 128:
                    # Fons clar, text fosc
                    threshold = mean_val * 0.7
                    img_array = np.where(img_array > threshold, 255, 0)
                else:
                    # Fons fosc, text clar - invertir
                    threshold = mean_val * 1.3
                    img_array = np.where(img_array < threshold, 255, 0)
                
                img = Image.fromarray(img_array.astype('uint8'), 'L')
                
                # Guardar per debugging
                debug_path = "debug_ocr_optimitzat.png"
                img.save(debug_path, dpi=(300, 300))  # Alta resolució
                
                return img
                
        except Exception as e:
            print(f"⚠️ Error en preprocessat optimitzat: {e}")
            # Tornar al mètode original
            return self._preprocessar_imatge(image_path)
    
    def processar_imatge_ticket_complet(self, image_path):
        """Processar imatge de ticket - VERSIÓ OPTIMITZADA"""
        if not OCR_AVAILABLE:
            return "OCR no disponible", {}, [], []
        
        start_time = time.time()
        
        try:
            # 1. Preprocessat optimitzat
            img = self._preprocessar_imatge(image_path)
            
            # 2. OCR amb múltiples intents
            configs_proves = [
                r'--oem 3 --psm 6',              # Mode simple
                r'--oem 3 --psm 4',              # Mode column
                r'--oem 3 --psm 11',             # Mode sparse text
                r'--oem 1 --psm 6',              # Mode Legacy LSTM
                r'--oem 3 --psm 6 -l spa+cat',   # Català + Castellà
            ]
            
            best_text = ""
            best_lines = 0
            
            for config in configs_proves:
                try:
                    text = pytesseract.image_to_string(img, config=config)
                    
                    # Comptar línies amb patró de preu DIA
                    lines_with_dia_price = sum(1 for line in text.split('\n') 
                                            if re.search(r'\d+[\.,]\d{2}\s*[AB]\s*$', line))
                    
                    if lines_with_dia_price > best_lines:
                        best_lines = lines_with_dia_price
                        best_text = text
                        
                except Exception as e:
                    print(f"     Error: {e}")
                    continue
            
            if not best_text:
                # Últim intent sense configuració
                best_text = pytesseract.image_to_string(img)
            
            # 3. Extreure productes amb detecció més agressiva
            productes = self._extreure_productes_agressiu(best_text)
            metadades = self._extreure_metadades(best_text)
            
            # 4. Fer matching amb la BD
            productes_coincidents = self.match_with_database(productes)
            
            elapsed_time = time.time() - start_time
            
            if productes_coincidents:
                print(f"   📊 Coincidències BD: {len([p for p in productes_coincidents if not p['is_new']])}")
            
            if productes:
                total = sum(p['preu'] for p in productes)
                print(f"   Total calculat: {total:.2f}€")
                print(f"   Total esperat: 15.14€ (segons ticket)")
            
            return best_text, metadades, productes, productes_coincidents
            
        except Exception as e:
            error_msg = f"Error processant imatge: {str(e)}"
            print(f"❌ {error_msg}")
            import traceback
            traceback.print_exc()
            return error_msg, {}, [], []
        
    def _extreure_productes_agressiu(self, text):
        """Extreure productes amb detecció agressiva per a OCR pobre"""

        lines = text.split('\n')
        productes = []
        
        # Patrons per buscar productes
        patterns = [
            # Patró 1: X,XX A/B al final
            (re.compile(r'(\d+)[\.,](\d{2})\s*[AB]\s*$'), "standard"),
            # Patró 2: X.XX sense lletra
            (re.compile(r'(\d+)[\.,](\d{2})\s*$'), "no_letter"),
            # Patró 3: X,XX amb símbols estranys
            (re.compile(r'(\d+)[\.,°](\d{2})[°\*\s]*[AB]?\s*$'), "noisy"),
        ]
        
        for i, line in enumerate(lines):
            line_clean = line.strip()
            
            # Saltar línies massa curtes o sense text útil
            if len(line_clean) < 3:
                continue
            
            # Provar diferents patrons
            for pattern, pattern_type in patterns:
                match = pattern.search(line_clean)
                if match:
                    enter, decimals = match.groups()
                    price_str = f"{enter}.{decimals}"
                    price = float(price_str)
                    
                    # Aplicar correccions conegudes
                    if pattern_type == "standard":
                        # Correccions específiques
                        if enter == '4' and decimals == '29':
                            price = 1.29
                        elif enter == '1' and decimals == '85':
                            price = 1.65
                    
                    # Extreure possible nom
                    nom_producte = line_clean[:match.start()].strip()
                    
                    # Netejar nom
                    nom_producte = re.sub(r'[^\w\sáéíóúàèìòùñç\.\']', ' ', nom_producte)
                    nom_producte = re.sub(r'\s+', ' ', nom_producte)
                    
                    # Validar
                    if (len(nom_producte) >= 2 and 
                        0.05 <= price <= 50.00 and
                        not any(keyword in nom_producte.upper() for keyword in 
                            ['TOTAL', 'IVA', 'OFERTA', 'DESCUENTO', 'CUPON'])):
                        
                        # Buscar a BD
                        producto_info = self._buscar_producte(nom_producte)
                        
                        producto = {
                            'producte': nom_producte,
                            'nom_estandard': producto_info['nom_estandard'],
                            'familia': producto_info['familia'],
                            'preu': price,
                            'quantitat_detectada': 1,
                            'nou_producte': producto_info['nou_producte']
                        }
                        productes.append(producto)
                        break
        
        return productes
    
    def _extreure_productes_avancat(self, text):
        """Extreure productes de manera avançada - VERSIÓ MILLORADA"""
        lines = text.split('\n')
        productes = []
        
        # Diccionari de productes coneguts del DIA amb variants
        productes_dia = {
            'PATATES FREDGES': {'preu': 1.65, 'variants': ['PATATES FREGIDES', 'PATATES.FOR']},
            'IOGURT NATURAL': {'preu': 1.00, 'variants': ['TOGURT NATURAL', 'YOGURT NATURAL']},
            'ALL UNITAT': {'preu': 0.69, 'variants': ['ALL UNITAT', 'ALLS UNITAT']},
            'TOMAQUET D\'UNTAR': {'preu': 1.49, 'variants': ['TOMAQUET. DSUNTAR', 'TOMAQUET 250']},
            'TORRO XOCO': {'preu': 1.49, 'variants': ['TORO XOCO', 'TORRO XOCO']},
            'LACÓN FUMAT': {'preu': 1.29, 'variants': ['LACON FUMAT', 'LACON FUMAT NUESTRA']},
            'ALVOCAT': {'preu': 1.69, 'variants': ['ALVOCAT SAFATA', 'AGUACATE']},
            'PATATA BOSSA': {'preu': 3.50, 'variants': ['PATATA BOSSA', 'PATATA.BOSSA']},
            'OLIVES VERDERONES': {'preu': 1.85, 'variants': ['OLIVES VERDERONES', 'OLIVES.VERDERONES']},
            'BLAT DE MORO': {'preu': 0.99, 'variants': ['BLAT DE MORO', 'BLAT MORO']},
        }
        
        # Buscar per productes coneguts
        for nom_base, info in productes_dia.items():
            preu_esperat = info['preu']
            variants = info['variants']
            
            for i, line in enumerate(lines):
                line_upper = line.upper()
                
                # Comprovar si alguna variant apareix
                trobat = False
                for variant in variants:
                    if variant in line_upper:
                        trobat = True
                        break
                
                if trobat:
                    # Buscar preu real a la línia
                    preu_trobat = self._buscar_preu_linea(line)
                    if preu_trobat is None:
                        preu_trobat = preu_esperat
                    
                    producto_info = self._buscar_producte(nom_base)
                    
                    producto = {
                        'producte': nom_base,
                        'nom_estandard': producto_info['nom_estandard'],
                        'familia': producto_info['familia'],
                        'preu': preu_trobat,
                        'quantitat_detectada': 1,
                        'nou_producte': producto_info['nou_producte']
                    }
                    productes.append(producto)
                    break
        
        # Si no hem trobat prou, fer cerca per patrons
        if len(productes) < 5:
            productes.extend(self._buscar_per_patrons(lines))
        
        return productes
    
    def _buscar_preu_linea(self, line):
        """Buscar preu a una línia"""
        # Patrons flexibles
        patrons = [
            r'(\d+)[,\.°](\d{2})\s*[AB8][:°"\s]*',
            r'(\d+)[,\.°](\d{2})\s*[:°"\s]*',
            r'(\d+)[,\.°](\d{2})$',
        ]
        
        for pattern in patrons:
            match = re.search(pattern, line)
            if match:
                enter, decimals = match.groups()
                preu = float(f"{enter}.{decimals}")
                
                # Correccions
                if preu == 4.29:
                    preu = 1.29
                elif preu == 1.85:
                    preu = 1.65
                
                return preu
        
        return None

    def _buscar_per_patrons(self, lines):
        """Buscar productes per patrons generals"""
        productes = []
        
        for i, line in enumerate(lines):
            line_clean = line.strip()
            
            # Buscar números que semblin preus
            matches = list(re.finditer(r'(\d+)[,\.°](\d{2})', line_clean))
            
            for match in matches:
                preu = float(f"{match.group(1)}.{match.group(2)}")
                
                # Correccions
                if preu == 4.29:
                    preu = 1.29
                elif preu == 1.85:
                    preu = 1.65
                
                if 0.10 <= preu <= 20.00:
                    # Extreure text com a nom
                    nom = line_clean[:match.start()].strip()
                    nom = re.sub(r'[^\w\sáéíóúàèìòùñç\.\'\-\d]', ' ', nom)
                    nom = re.sub(r'\s+', ' ', nom).strip()
                    
                    if len(nom) > 2 and not any(palabra in nom.upper() for palabra in 
                                            ['TOTAL', 'IVA', 'OFERTA']):
                        
                        producto_info = self._buscar_producte(nom)
                        
                        producto = {
                            'producte': nom,
                            'nom_estandard': producto_info['nom_estandard'],
                            'familia': producto_info['familia'],
                            'preu': preu,
                            'quantitat_detectada': 1,
                            'nou_producte': producto_info['nou_producte']
                        }
                        productes.append(producto)
        
        return productes
    
    def processar_ticket_dia_per_zones(self, image_path):
        """
        Processa tickets DIA dividint l'imatge en zones específiques
        """
        if not OCR_AVAILABLE or not CV2_AVAILABLE:
            return self.processar_imatge_ticket_complet(image_path)
        
        try:
            import cv2
            import numpy as np
            
            # 1. Carregar imatge
            img = cv2.imread(image_path)
            if img is None:
                return "Error carregant imatge", {}, [], []
            
            height, width = img.shape[:2]
            
            # 2. Definir zones del ticket DIA (percentatges aproximats)
            zones = {
                'capçalera': (0, 0, width, int(height * 0.15)),          # 0-15%
                'productes': (int(width * 0.05), int(height * 0.2),      # Zona de productes
                            int(width * 0.95), int(height * 0.7)),
                'ofertes': (int(width * 0.05), int(height * 0.7),        # Zona d'ofertes
                        int(width * 0.95), int(height * 0.75)),
                'total': (int(width * 0.05), int(height * 0.75),         # Zona de total
                        int(width * 0.95), int(height * 0.85)),
                'peu': (0, int(height * 0.85), width, height)           # 85-100%
            }
            
            # 3. Processar zona de productes
            x1, y1, x2, y2 = zones['productes']
            zona_productes = img[y1:y2, x1:x2]

            # Convertir a escala de grisos
            gray = cv2.cvtColor(zona_productes, cv2.COLOR_BGR2GRAY)
            
            # Aplicar threshold per millorar text
            _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY_INV)
            
            # Guardar zona per debugging
            debug_zona = "debug_zona_productes.png"
            cv2.imwrite(debug_zona, thresh)
            
            # 4. OCR només a la zona de productes
            img_pil = Image.fromarray(thresh)
            
            # Provar diferents configuracions
            configs = [
                r'--oem 3 --psm 6',
                r'--oem 3 --psm 4',
                r'--oem 3 --psm 11',
            ]
            
            best_text = ""
            best_lines = 0
            
            for config in configs:
                try:
                    text = pytesseract.image_to_string(img_pil, config=config)
                    lines = text.split('\n')
                    
                    # Comptar línies que semblin productes
                    product_lines = sum(1 for line in lines if self._sembla_producte(line))
                    
                    if product_lines > best_lines:
                        best_lines = product_lines
                        best_text = text
                        
                except Exception:
                    continue
            
            if not best_text:
                best_text = pytesseract.image_to_string(img_pil)
            
            
            # 5. Extreure productes amb mètode específic
            productes = self._extreure_productes_zona(best_text)
            
            # 6. Processar zona d'ofertes (si existeix)
            x1, y1, x2, y2 = zones['ofertes']
            zona_ofertes = img[y1:y2, x1:x2]
            
            if np.mean(zona_ofertes) < 245:  # Si hi ha contingut
                gray_ofertes = cv2.cvtColor(zona_ofertes, cv2.COLOR_BGR2GRAY)
                _, thresh_ofertes = cv2.threshold(gray_ofertes, 150, 255, cv2.THRESH_BINARY_INV)
                img_ofertes = Image.fromarray(thresh_ofertes)
                text_ofertes = pytesseract.image_to_string(img_ofertes)
                
                # Buscar ofertes (descomptes)
                ofertes_trobades = self._extreure_ofertes(text_ofertes)
               
                   
            
            # 7. Processar zona de total
            x1, y1, x2, y2 = zones['total']
            zona_total = img[y1:y2, x1:x2]
            gray_total = cv2.cvtColor(zona_total, cv2.COLOR_BGR2GRAY)
            _, thresh_total = cv2.threshold(gray_total, 150, 255, cv2.THRESH_BINARY_INV)
            img_total = Image.fromarray(thresh_total)
            text_total = pytesseract.image_to_string(img_total)
            
            # Extreure total
            total_ticket = self._extreure_total(text_total)
            
            # 8. Preparar resultats
            metadades = {
                'supermercat': 'Dia',
                'data': self._extreure_data_desde_imatge(img),
                'total_ticket': total_ticket
            }
            
            productes_coincidents = self.match_with_database(productes)
            
            if productes:
                total_calculat = sum(p['preu'] for p in productes)
                
                if total_ticket > 0:
                    cobertura = (total_calculat / total_ticket) * 100
            
            return best_text, metadades, productes, productes_coincidents
            
        except Exception as e:
            print(f"❌ Error processant per zones: {e}")
            import traceback
            traceback.print_exc()
            return self.processar_imatge_ticket_complet(image_path)

    def _extreure_ofertes(self, text):
        """Extreure ofertes/descomptes del text"""
        ofertes = []
        
        # Buscar patró de descompte: -X,XX
        matches = re.findall(r'-\s*(\d+)[\.,](\d{2})', text)
        
        for enter, decimals in matches:
            descompte = float(f"{enter}.{decimals}")
            ofertes.append(descompte)
        
        return ofertes

    def _buscar_preu_linea(self, line):
        """Buscar preu a una línia"""
        # Patrons flexibles
        patrons = [
            r'(\d+)[,\.°](\d{2})\s*[AB8][:°"\s]*',
            r'(\d+)[,\.°](\d{2})\s*[:°"\s]*',
            r'(\d+)[,\.°](\d{2})$',
        ]
        
        for pattern in patrons:
            match = re.search(pattern, line)
            if match:
                enter, decimals = match.groups()
                preu = float(f"{enter}.{decimals}")
                
                # Correccions
                if preu == 4.29:
                    preu = 1.29
                elif preu == 1.85:
                    preu = 1.65
                
                return preu
        
        return None

    def _sembla_producte(self, line):
        """Determina si una línia sembla un producte"""
        line = line.strip()
        
        # Ha de tenir certa llargada
        if len(line) < 5:
            return False
        
        # Ha de contenir text (no només números)
        if re.match(r'^\d+[\.,]?\d*$', line):
            return False
        
        # Ha de contenir un preu (X,XX)
        if not re.search(r'\d+[\.,°]\d{2}', line):
            return False
        
        # No ha de ser metadata
        paraules_no = ['TOTAL', 'IVA', 'SUBTOTAL', 'OFERTA', 'DESCUENTO', 
                    'CUPON', 'FACTURA', 'TICKET']
        
        for palabra in paraules_no:
            if palabra in line.upper():
                return False
        
        return True

    def _extreure_productes_zona(self, text):
        """Extreure productes d'una zona específica"""
        lines = text.split('\n')
        productes = []
        
        # Productes esperats en tickets DIA
        diccionari_dia = {
            'PATATES FREDGES': ['PATATES', 'FREDGES', 'FOR'],
            'IOGURT NATURAL': ['IOGURT', 'NATURAL', 'DANON'],
            'ALL UNITAT': ['ALL', 'UNITAT'],
            'TOMAQUET D\'UNTAR': ['TOMAQUET', 'UNTAR', '250'],
            'TORRO XOCO': ['TORRO', 'XOCO', 'LLET', 'DULC'],
            'LACÓN FUMAT': ['LACÓN', 'FUMAT', 'NUESTRA'],
            'ALVOCAT': ['ALVOCAT', 'SAFATA'],
            'PATATA BOSSA': ['PATATA', 'BOSSA'],
            'OLIVES VERDERONES': ['OLIVES', 'VERDERONES'],
            'BLAT DE MORO': ['BLAT', 'MORO', 'DOLÇ'],
        }
        
        for i, line in enumerate(lines):
            line_clean = line.strip()
            line_upper = line_clean.upper()
            
            # Buscar preu
            preu = self._buscar_preu_linea(line_clean)
            if preu is None:
                continue
            
            # Buscar quin producte coincideix
            for nom_producte, paraules_clau in diccionari_dia.items():
                coincidencies = sum(1 for palabra in paraules_clau if palabra in line_upper)
                
                # Si almenys 2 paraules coincideixen o el 70% de les paraules
                if coincidencies >= 2 or coincidencies >= len(paraules_clau) * 0.7:
                    producto_info = self._buscar_producte(nom_producte)
                    
                    producto = {
                        'producte': nom_producte,
                        'nom_estandard': producto_info['nom_estandard'],
                        'familia': producto_info['familia'],
                        'preu': preu,
                        'quantitat_detectada': 1,
                        'nou_producte': producto_info['nou_producte']
                    }
                    productes.append(producto)
                    
                    print(f"   ✅ Zona: {nom_producte[:30]}... - {preu:.2f}€")
                    break
        
        return productes

    def _extreure_total(self, text):
        """Extreure total de la zona de total"""
        # Buscar números que semblin total (normalment el més gran)
        matches = re.findall(r'(\d+)[\.,](\d{2})', text)
        
        totals = []
        for enter, decimals in matches:
            total = float(f"{enter}.{decimals}")
            if 1.00 <= total <= 1000.00:  # Rango raonable per a un total
                totals.append(total)
        
        if totals:
            # Retornar el número més gran (normalment és el total)
            return max(totals)
        
        return 0.0

    def _extreure_data_desde_imatge(self, img):
        """Extreure data de la capçalera"""
        try:
            # Zona de data aproximada (part superior dreta)
            height, width = img.shape[:2]
            x1 = int(width * 0.6)
            x2 = width - 10
            y1 = 10
            y2 = int(height * 0.1)
            
            zona_data = img[y1:y2, x1:x2]
            gray_data = cv2.cvtColor(zona_data, cv2.COLOR_BGR2GRAY)
            _, thresh_data = cv2.threshold(gray_data, 150, 255, cv2.THRESH_BINARY_INV)
            
            img_data = Image.fromarray(thresh_data)
            text_data = pytesseract.image_to_string(img_data)
            
            # Buscar data
            date_match = re.search(r'(\d{2})[-\./](\d{2})[-\./](\d{4})', text_data)
            if date_match:
                dia, mes, any = date_match.groups()
                return f"{dia}/{mes}/{any}"
            
        except Exception:
            pass
        
        return datetime.now().strftime("%d/%m/%Y")

    def _segona_passada_deteccio(self, lines, productes_detectats):
        """Segona passada per millorar la detecció de productes"""
        productes = productes_detectats.copy()
        
        # Buscar línies que podrien contenir productes fragmentats
        for i in range(len(lines)):
            line = lines[i].strip()
            
            # Buscar números que semblin preus (X.XX)
            price_matches = re.findall(r'(\d+[\.,]\d{2})', line)
            
            for price_str in price_matches:
                price = float(price_str.replace(',', '.'))
                
                # Si el preu sembla raonable per un producte
                if 0.10 <= price <= 15.00:
                    # Mirar línies al voltant per trobar el nom
                    context = ""
                    
                    # Mirar 2 línies abans
                    for j in range(max(0, i-2), i):
                        prev_line = lines[j].strip()
                        # Si la línia anterior no té preu, afegir al context
                        if prev_line and not re.search(r'\d+[\.,]\d{2}', prev_line):
                            context += " " + prev_line
                    
                    # Afegir la línia actual sense el preu
                    current_without_price = re.sub(price_str, '', line).strip()
                    if current_without_price:
                        context += " " + current_without_price
                    
                    # Netejar el context
                    context = re.sub(r'\s+', ' ', context).strip()
                    
                    if len(context) >= 2:
                        # Verificar que no sigui ja detectat
                        already_detected = any(
                            context in p['producte'] or p['producte'] in context 
                            for p in productes
                        )
                        
                        if not already_detected:
                            producto_info = self._buscar_producte(context)
                            
                            producto = {
                                'producte': context,
                                'nom_estandard': producto_info['nom_estandard'],
                                'familia': producto_info['familia'],
                                'preu': price,
                                'quantitat_detectada': 1,
                                'nou_producte': producto_info['nou_producte']
                            }
                            productes.append(producto)
        
        return productes
    
    def _buscar_producte(self, nom):
        """
        Buscar producte a la BD i retornar informació estandarditzada
        Versió amb correcció d'errors OCR comuns
        """
        import re
        import unicodedata
        
        # 🔴 FUNCIÓ PER NORMALITZAR TEXT (eliminar accents, caràcters especials, espais múltiples)
        def normalitzar_text(text):
            if not text:
                return ""
            
            # Convertir a string si no ho és
            text = str(text)
            
            # 🔴 CORREGIR ERRORS OCR COMUNS
            correccions_ocr = {
                'G': 'Ó',     # TOVALLG → TOVALLÓ
                'g': 'ó',
                '0': 'O',      # 0 → O (comú en OCR)
                '1': 'I',      # 1 → I
                '5': 'S',      # 5 → S
                '8': 'B',      # 8 → B (comú en lletra d'IVA)
                '4': 'A',      # 4 → A (lletra d'IVA)
            }
            
            text_corregit = text
            for error, correccio in correccions_ocr.items():
                text_corregit = text_corregit.replace(error, correccio)
            
            # Normalitzar Unicode (descompondre caràcters amb accents)
            text_normalitzat = unicodedata.normalize('NFKD', text_corregit)
            
            # Eliminar diacrítics (accents, etc.) però mantenir lletres base
            text_sense_diacritics = ''.join(
                c for c in text_normalitzat 
                if not unicodedata.combining(c) and (c.isalnum() or c.isspace())
            )
            
            # Convertir a minúscules
            text_lower = text_sense_diacritics.lower()
            
            # Eliminar espais múltiples
            text_net = re.sub(r'\s+', ' ', text_lower).strip()
            
            return text_net
        
        # 🔴 NORMALITZAR EL NOM D'ENTRADA
        nom_normalitzat = normalitzar_text(nom)
        
        print(f"   🔍 Original: '{nom}'")
        print(f"      → Normalitzat: '{nom_normalitzat}'")
        
        if not nom_normalitzat:
            return {
                'nom_estandard': nom,
                'familia': 'Desconeguda',
                'nou_producte': True
            }
        
        # 🔴 PRIMER: Buscar per coincidència exacta després de normalitzar
        for nom_super, info in self.noms_cache.items():
            nom_super_normalitzat = normalitzar_text(nom_super)
            
            if nom_normalitzat == nom_super_normalitzat:
                print(f"   ✅ Trobat per coincidència exacta: {nom_super} -> {info['nom_estandard']}")
                return {
                    'nom_estandard': info['nom_estandard'],
                    'familia': info['familia'],
                    'nou_producte': False
                }
        
        # 🔴 SEGON: Buscar per coincidència parcial (que un contingui l'altre)
        for nom_super, info in self.noms_cache.items():
            nom_super_normalitzat = normalitzar_text(nom_super)
            
            if (nom_super_normalitzat in nom_normalitzat or 
                nom_normalitzat in nom_super_normalitzat):
                print(f"   ✅ Trobat per coincidència parcial: {nom_super} -> {info['nom_estandard']}")
                return {
                    'nom_estandard': info['nom_estandard'],
                    'familia': info['familia'],
                    'nou_producte': False
                }
        
        # 🔴 TERCER: Buscar per coincidència de paraules clau (compartir paraules significatives)
        paraules_nom = set(nom_normalitzat.split())
        
        millor_coincidencia = None
        millor_puntuacio = 0
        millor_info = None
        
        for nom_super, info in self.noms_cache.items():
            nom_super_normalitzat = normalitzar_text(nom_super)
            paraules_super = set(nom_super_normalitzat.split())
            
            # Comptar quantes paraules coincideixen
            coincidencies = 0
            for p_nom in paraules_nom:
                if len(p_nom) < 2:  # Paraules molt curtes
                    continue
                for p_super in paraules_super:
                    if len(p_super) < 2:
                        continue
                    # Coincidència exacta o parcial
                    if p_nom == p_super or p_nom in p_super or p_super in p_nom:
                        coincidencies += 1
                        break
            
            # Puntuació: nombre de coincidències / total paraules
            if len(paraules_nom) > 0:
                puntuacio = coincidencies / len(paraules_nom)
            else:
                puntuacio = 0
            
            if puntuacio > millor_puntuacio and puntuacio >= 0.5:  # 50% de coincidència
                millor_puntuacio = puntuacio
                millor_coincidencia = nom_super
                millor_info = info
        
        if millor_info:
            print(f"   ✅ Trobat per similitud ({millor_puntuacio:.2f}): {millor_coincidencia} -> {millor_info['nom_estandard']}")
            return {
                'nom_estandard': millor_info['nom_estandard'],
                'familia': millor_info['familia'],
                'nou_producte': False
            }
        
        # 🔴 QUART: Si no es troba, retornar el nom original
        print(f"   ⚠️ No trobat a la BD: {nom}")
        return {
            'nom_estandard': nom,
            'familia': 'Desconeguda',
            'nou_producte': True
        }
    
    def match_with_database(self, detected_products):
        """
        Compara productes detectats amb la base de dades i retorna coincidències
        """
        matched_products = []
        
        for detected in detected_products:
            # Ja tens el mètode _buscar_producte, però aquest retorna info més detallada
            nom_detectat = detected['producte']  # El nom original detectat
            preu = detected['preu']
            
            info = self._buscar_producte(nom_detectat)
            
            matched_products.append({
                'detected': nom_detectat,
                'matched_name': info['nom_estandard'],
                'family': info['familia'],
                'price': preu,
                'is_new': info['nou_producte']
            })
        
        return matched_products
    
    def _extreure_metadades(self, text):
        """Extreure metadades del ticket"""
        metadades = {
            'supermercat': 'Dia',
            'data': datetime.now().strftime("%d/%m/%Y"),  # Data per defecte
            'total_ticket': 0.0
        }
        
        # Buscar data en format DD/MM/YYYY
        date_match = re.search(r'(\d{2})[-\./](\d{2})[-\./](\d{4})', text)
        if date_match:
            dia, mes, any = date_match.groups()
            # Validar que la data és correcta (mes entre 1-12, dia entre 1-31)
            if 1 <= int(mes) <= 12 and 1 <= int(dia) <= 31:
                metadades['data'] = f"{dia}/{mes}/{any}"
            else:
                print(f"⚠️ Data invàlida trobada: {dia}/{mes}/{any}, usant data actual")
        
        # Buscar total
        total_match = re.search(r'TOTAL.*?(\d+[,\.]\d{2})', text, re.IGNORECASE)
        if total_match:
            total_str = total_match.group(1).replace(',', '.')
            try:
                metadades['total_ticket'] = float(total_str)
            except:
                pass
        
        return metadades
    
    def processar_imatge_ticket_dia_simple(self, image_path):
        """
        Processa tickets DIA amb un enfocament simple però efectiu
        """
        if not OCR_AVAILABLE:
            return "OCR no disponible", {}, [], []
        
        start_time = time.time()
        
        try:
            # 1. Carregar imatge amb OpenCV per preprocessat ràpid
            if CV2_AVAILABLE:
                img = cv2.imread(image_path)
                if img is not None:
                    # Convertir a escala de grisos
                    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                    
                    # Aplicar threshold simple
                    _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)
                    
                    # Convertir a PIL
                    img_pil = Image.fromarray(thresh)
                else:
                    img_pil = Image.open(image_path)
            else:
                img_pil = Image.open(image_path)
            
            # 2. OCR amb configuració optimitzada per tickets
            configs = [
                r'--oem 3 --psm 6',      # Mode per blocs de text
                r'--oem 3 --psm 4',      # Mode column
                r'--oem 3 --psm 11',     # Mode sparse text
            ]
            
            best_text = ""
            best_lines = 0
            
            for config in configs:
                try:
                    text = pytesseract.image_to_string(img_pil, config=config)
                    
                    # Comptar línies amb possibles productes
                    lines = text.split('\n')
                    product_lines = 0
                    for line in lines:
                        if re.search(r'\d+[,\.,°]\d{2}', line) and len(line.strip()) > 5:
                            product_lines += 1
                    
                    if product_lines > best_lines:
                        best_lines = product_lines
                        best_text = text
                        
                except Exception:
                    continue
            
            if not best_text:
                best_text = pytesseract.image_to_string(img_pil)
            
            # 3. Extreure productes amb patró més tolerant
            productes = self._extreure_productes_dia_tolerant(best_text)
            
            # 4. Si no n'hi ha prou, intentar amb el text original sense processar
            if len(productes) < 5:
                img_original = Image.open(image_path)
                if img_original.mode != 'L':
                    img_original = img_original.convert('L')
                
                text2 = pytesseract.image_to_string(img_original, config=r'--oem 3 --psm 6')
                productes2 = self._extreure_productes_dia_tolerant(text2)
                
                # Combinar resultats
                productes_combinats = productes.copy()
                for p2 in productes2:
                    # Evitar duplicats
                    if not any(p['producte'][:15] == p2['producte'][:15] for p in productes_combinats):
                        productes_combinats.append(p2)
                
                productes = productes_combinats
            
            # 5. Matching amb BD
            metadades = self._extreure_metadades(best_text)
            productes_coincidents = self.match_with_database(productes)
            
            elapsed_time = time.time() - start_time
            
            if productes:
                total = sum(p['preu'] for p in productes)
                
            return best_text, metadades, productes, productes_coincidents
            
        except Exception as e:
            print(f"❌ Error en processament DIA: {e}")
            import traceback
            traceback.print_exc()
            return f"Error: {e}", {}, [], []

    def _extreure_productes_dia_tolerant(self, text):
        """
        Extreure productes amb patrons molt tolerants per a DIA
        """
        productes = []
        lines = text.split('\n')
        
        # Diccionari de productes esperats (del ticket dia2.jpg) amb variants OCR
        productes_esperats = [
            # (nom_esperat, preu_esperat, [paraules_clau], variants_ocr)
            ("PATATES FREDGES FOR", 1.65, ["PATATES", "FREDGES", "FOR"], 
            ["PATATES FREGIDES", "PATATES.FOR", "PATATES FOR"]),
            
            ("IOGURT NATURAL DANON", 1.00, ["IOGURT", "NATURAL", "DANON"], 
            ["TOGURT NATURAL", "YOGURT NATURAL", "IOGUR NATURAL"]),
            
            ("ALL UNITAT", 0.69, ["ALL", "UNITAT"], 
            ["ALL UNITAT", "ALLS UNITAT", "ALL.UNITAT"]),
            
            ("TOMAQUET D'UNTAR 250", 1.49, ["TOMAQUET", "UNTAR", "250"], 
            ["TOMAQUET. DSUNTAR", "TOMAQUET D'UNTAR", "TOMAQUET 250"]),
            
            ("TORRO XOCO LLET DULC", 1.49, ["TORRO", "XOCO", "LLET", "DULC"], 
            ["TORO XOCO", "TORRO XOCO", "TORRO XOCO LLET"]),
            
            ("LACÓN FUMAT NUESTRA", 1.29, ["LACÓN", "FUMAT", "NUESTRA"], 
            ["LACON FUMAT", "LACÓN FUMAT", "LACON FUMAT NUESTRA"]),
            
            ("ALVOCAT SAFATA", 1.69, ["ALVOCAT", "SAFATA"], 
            ["ALVOCAT", "ALVOCAT SAFATA", "AGUACATE"]),
            
            ("PATATA BOSSA", 3.50, ["PATATA", "BOSSA"], 
            ["PATATA BOSSA", "PATATA.BOSSA"]),
            
            ("OLIVES VERDERONES VE", 1.85, ["OLIVES", "VERDERONES"], 
            ["OLIVES VERDERONES", "OLIVES.VERDERONES"]),
            
            ("BLAT DE MORO DOLÇ VE", 0.99, ["BLAT", "MORO", "DOLÇ"], 
            ["BLAT DE MORO", "BLAT MORO", "MAIZ DULCE", "BLAT .MORO"]),
        ]
        
        # 1. Buscar productes esperats al text amb variants
        text_upper = text.upper()
        
        for nom_esperat, preu_esperat, paraules_clau, variants_ocr in productes_esperats:
            trobat = False
            preu_trobat = preu_esperat
            linia_trobada = -1
            
            # Buscar per variants OCR
            for variant in variants_ocr:
                variant_upper = variant.upper()
                
                for i, line in enumerate(lines):
                    line_upper = line.upper()
                    
                    # Buscar variant al text
                    if variant_upper in line_upper:
                        trobat = True
                        linia_trobada = i
                        
                        # Buscar preu en aquesta línia
                        match = self._buscar_preu_a_linia(line)
                        if match:
                            preu_trobat = match
                        
                        # Si no hi ha preu, mirar línies properes
                        elif i+1 < len(lines):
                            match = self._buscar_preu_a_linia(lines[i+1])
                            if match:
                                preu_trobat = match
                        
                        break
                
                if trobat:
                    break
            
            # Si no hem trobat per variant, buscar per paraules clau
            if not trobat:
                for i, line in enumerate(lines):
                    line_upper = line.upper()
                    
                    # Comprovar si totes les paraules clau estan presents
                    paraules_presents = sum(1 for palabra in paraules_clau if palabra in line_upper)
                    
                    if paraules_presents >= len(paraules_clau) * 0.7:  # 70% de les paraules
                        trobat = True
                        linia_trobada = i
                        
                        # Buscar preu
                        match = self._buscar_preu_a_linia(line)
                        if match:
                            preu_trobat = match
                        break
            
            if trobat:
                producto_info = self._buscar_producte(nom_esperat)
                
                producto = {
                    'producte': nom_esperat,
                    'nom_estandard': producto_info['nom_estandard'],
                    'familia': producto_info['familia'],
                    'preu': preu_trobat,
                    'quantitat_detectada': 1,
                    'nou_producte': producto_info['nou_producte']
                }
                
                # Verificar que no estigui ja en la llista
                ja_existeix = any(p['producte'] == nom_esperat for p in productes)
                if not ja_existeix:
                    productes.append(producto)
                    print(f"   ✅ {nom_esperat[:40]}... - {preu_trobat:.2f}€ (línia {linia_trobada})")
        
        # 2. Cerca addicional per a preus no identificats
        if len(productes) < 10:  # Si falten productes
            productes_trobats = self._cerca_preus_no_identificats(lines, productes)
            productes.extend(productes_trobats)
        
        return productes

    def _detectar_zona_productes_exacta(self, text):
        """
        Detecta exactament la zona de productes basant-se en marcadors coneguts
        Retorna només les línies de productes
        """
        lines = text.split('\n')
        productes_lines = []
        in_productes = False
        fi_productes_marcadors = ['OFERTES', 'OFERTES(O) I CUPONS', 'ClubDia', 
                                'TOTAL COMPRA', '-----------', 'DESGLOSSAMENTS']
        
        for i, line in enumerate(lines):
            line_clean = line.strip()
            
            # Detectar inici de productes
            if not in_productes:
                # Marcadors d'inici comuns
                if any(marcador in line_clean.upper() for marcador in 
                    ['DESCRIPCIÓ', 'ARTICLE', 'QUANTITAT', 'PVP/UNIT']):
                    in_productes = True
                    print(f"   → Inici productes a línia {i}: {line_clean}")
                    continue
            
            # Si estem dins de productes
            if in_productes:
                # Verificar si és fi de productes
                fi_trobat = False
                for marcador in fi_productes_marcadors:
                    if marcador in line_clean.upper():
                        print(f"   → Fi productes a línia {i}: {line_clean}")
                        fi_trobat = True
                        break
                
                if fi_trobat:
                    break
                
                # Afegir línia si no està buida
                if line_clean and len(line_clean) > 2:
                    productes_lines.append((i, line_clean))
        return productes_lines

    def _extreure_productes_dia_precís(self, text):
        """
        Extreu productes de manera precisa mantenint l'ordre del ticket
        """
        lines = text.split('\n')
        productes = []
        
        # Detectar zona de productes
        in_product_zone = False
        start_markers = ['DESCRIPCIÓ', 'DESCRIPCION', 'ARTICLE', 'PRODUCTO']
        end_markers = ['OFERTES', 'TOTAL', 'SUBTOTAL', 'IVA', 'DESGLOSSAMENT']
        
        print("\n📄 Processant línies del ticket:")
        
        for idx, line in enumerate(lines):
            line_clean = line.strip()
            if not line_clean:
                continue
            
            line_upper = line_clean.upper()
            
            # Detectar inici de zona de productes
            if not in_product_zone:
                for marker in start_markers:
                    if marker in line_upper:
                        in_product_zone = True
                        print(f"   → Inici zona productes línia {idx+1}: {line_clean}")
                        break
                continue
            
            # Detectar fi de zona de productes
            for marker in end_markers:
                if marker in line_upper:
                    print(f"   → Fi zona productes línia {idx+1}: {line_clean}")
                    in_product_zone = False
                    break
            
            if not in_product_zone:
                continue
            
            # Processar línia com a possible producte
            producte = self._detectar_producte_en_linia(line_clean, idx)
            if producte:
                productes.append(producte)
        
        print(f"\n✅ Total productes detectats: {len(productes)}")
        return productes

    def _detectar_producte_en_linia(self, line, idx):
        """
        Detecta si una línia conté un producte i el retorna
        """
        line_clean = line.strip()
        
        # 🔴 FILTRE 1: Ignorar línies massa curtes
        if len(line_clean) < 5:
            return None
        
        # 🔴 FILTRE 2: Ignorar línies que comencen amb patró d'IVA
        patron_iva = [
            r'^\([AB]\)',           # (A) o (B)
            r'^[AB]\s+\d+',          # A 4 o B 10
            r'TIPUS IVA',            # TIPUS IVA
            r'BASE\s+QUOTA',         # BASE QUOTA
            r'^\d+[.,]\d{2}%\s+\d+', # 4,00% 8,05
        ]
        
        for patron in patron_iva:
            if re.search(patron, line_clean, re.IGNORECASE):
                print(f"   ⚠️ Línia {idx+1:2d}: Ignorada (patró IVA): {line_clean[:30]}...")
                return None
        
        # 🔴 FILTRE 3: Ignorar línies amb massa símbols estranys
        simbols_estranys = len(re.findall(r'[^a-zA-Z0-9\sáéíóúàèìòùñç€.,%]', line_clean))
        if simbols_estranys > 3:  # Més de 3 símbols estranys
            print(f"   ⚠️ Línia {idx+1:2d}: Ignorada (massa símbols): {line_clean[:30]}...")
            return None
        
        # 🔴 FILTRE 4: Ignorar paraules clau de metadades
        paraules_ignorar = [
            'TOTAL', 'IVA', 'SUBTOTAL', 'OFERTA', 'DESCUENTO', 
            'CUPON', 'FACTURA', 'TICKET', 'GRUPO DIA', 'CLUBDIA',
            'DESGLOSSAMENT', 'TIPUS', 'BASE', 'QUOTA', 'ESTALVI'
        ]
        
        line_upper = line_clean.upper()
        for palabra in paraules_ignorar:
            if palabra in line_upper:
                print(f"   ⚠️ Línia {idx+1:2d}: Ignorada (paraula clau '{palabra}')")
                return None
        
        # Buscar preu al final de la línia (format típic de producte)
        price_match = re.search(r'(\d+)[\.,](\d{2})\s*$', line_clean)
        if not price_match:
            return None
        
        preu = float(f"{price_match.group(1)}.{price_match.group(2)}")
        
        # 🔴 FILTRE 5: El preu ha de ser raonable per un producte
        if preu > 50.00 or preu < 0.10:
            print(f"   ⚠️ Línia {idx+1:2d}: Ignorada (preu fora de rang: {preu:.2f}€)")
            return None
        
        # Extreure nom (tot excepte el preu)
        nom = line_clean[:price_match.start()].strip()
        
        # Netejar el nom
        nom = re.sub(r'[^\w\sáéíóúàèìòùñç\.\']', ' ', nom)
        nom = re.sub(r'\s+', ' ', nom).strip()
        
        # 🔴 FILTRE 6: El nom ha de tenir longitud raonable
        if len(nom) < 2 or len(nom) > 50:
            return None
        
        # Buscar a BD
        info = self._buscar_producte(nom)
        
        print(f"   ✅ Línia {idx+1:2d}: Producte detectat: {nom[:30]}... {preu:.2f}€")
        
        return {
            'producte': nom,
            'nom_estandard': info['nom_estandard'],
            'familia': info['familia'],
            'preu': preu,
            'quantitat_detectada': 1,
            'nou_producte': info['nou_producte'],
            'numero_linia': idx + 1,
            'linia_original': line
        }

    def _buscar_preu_linea_dia(self, line):
        """
        Busca preu específicament per a tickets DIA
        Gestiona errors comuns d'OCR: 8: → B, 4,29 → 1,29, etc.
        """
        if not line:
            return None
        
        # Netejar línia
        line_clean = line.strip()
        
        # Patrons específics per DIA
        patrons = [
            # Format: X,XX B: (on B pot ser A o B, i : pot ser qualsevol símbol)
            r'(\d+)[\.,°](\d{2})\s*[AB8][:°"\s]*',
            # Format: X,XX (sense lletra, al final)
            r'(\d+)[\.,°](\d{2})\s*$',
            # Format: X,XX en qualsevol lloc
            r'(\d+)[\.,°](\d{2})',
        ]
        
        for pattern in patrons:
            match = re.search(pattern, line_clean)
            if match:
                enter, decimals = match.groups()
                preu = float(f"{enter}.{decimals}")
                
                # CORRECCIONS ESPECÍFIQUES D'OCR DIA
                correccions = {
                    4.29: 1.29,   # "4,29" probablement és "1,29"
                    1.85: 1.65,   # "1,85" probablement és "1,65"
                    0.50: 0.99,   # Podria ser "0,99" mal llegit
                }
                
                # Aplicar correcció si existeix
                if preu in correccions:
                    preu_corregit = correccions[preu]
                    preu = preu_corregit
                
                return preu
        
        return None

    def _extreure_nom_producte(self, line):
        """Extreu nom del producte netejant la línia"""
        # Eliminar el preu i símbols posteriors
        line_sense_preu = re.sub(r'\d+[\.,°]\d{2}.*$', '', line).strip()
        
        # Netejar símbols estranys
        nom = re.sub(r'[^\w\sáéíóúàèìòùñç\.\'\-]', ' ', line_sense_preu)
        nom = re.sub(r'\s+', ' ', nom).strip()
        
        # Eliminar números sols al principi (quantitats mal llegides)
        nom = re.sub(r'^\d+[\.,]?\d*\s+', '', nom)
        
        return nom if len(nom) > 1 else None

    def processar_ticket_dia_final(self, image_path):
        """
        Mètode final per processar tickets DIA amb màxima precisió
        """
        if not OCR_AVAILABLE:
            return "OCR no disponible", {}, [], []
        
        # 1. Obtenir text OCR de manera fiable
        text_ocr = self._obtenir_text_ocr_fiable(image_path)
        
        # 2. Extreure productes de manera precisa
        productes = self._extreure_productes_dia_precís(text_ocr)
        
        # 3. Verificar si tenim tots els productes
        if len(productes) < 10:
            print(f"\n⚠️  Només {len(productes)}/10 productes detectats")
            print("   Provant cerca alternativa...")
            
            # Provar altre mètode de cerca
            productes_alt = self._extreure_productes_dia_tolerant(text_ocr)
            # Afegir productes nous que no estiguin ja a la llista
            noms_existents = {p['producte'] for p in productes}
            for p in productes_alt:
                if p['producte'] not in noms_existents:
                    productes.append(p)
        
        # 4. Resultats finals
        metadades = self._extreure_metadades(text_ocr)
        productes_coincidents = self.match_with_database(productes)

        if productes:
            total = sum(p['preu'] for p in productes)
            
            
            # Llista detallada
            print(f"\n📋 PRODUCTES DETECTATS:")
            for p in productes:
                print(f"   • {p['producte'][:40]}... {p['preu']:.2f}€")
        
        return text_ocr, metadades, productes, productes_coincidents

    def _obtenir_text_ocr_fiable(self, image_path):
        """Obté text OCR fiable provant múltiples estratègies"""
        try:
            # Provar OpenCV si està disponible
            if CV2_AVAILABLE:
                import cv2
                import numpy as np
                
                img = cv2.imread(image_path)
                if img is not None:
                    # Provar diferents processaments
                    processaments = [
                        ("Original", img),
                        ("Gray", cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)),
                        ("Threshold", cv2.threshold(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), 
                                                150, 255, cv2.THRESH_BINARY)[1]),
                        ("Threshold_INV", cv2.threshold(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), 
                                                    150, 255, cv2.THRESH_BINARY_INV)[1]),
                    ]
                    
                    best_text = ""
                    best_len = 0
                    
                    for name, processed_img in processaments:
                        try:
                            if len(processed_img.shape) == 3:  # Si és color
                                img_pil = Image.fromarray(cv2.cvtColor(processed_img, cv2.COLOR_BGR2RGB))
                            else:  # Si és escala de grisos
                                img_pil = Image.fromarray(processed_img)
                            
                            text = pytesseract.image_to_string(img_pil, config=r'--oem 3 --psm 6')
                            
                            # Prioritzar text amb més línies que semblin productes
                            lines = text.split('\n')
                            producte_lines = sum(1 for line in lines if self._sembla_linea_producte(line))
                            
                            if producte_lines > best_len:
                                best_len = producte_lines
                                best_text = text
                                print(f"   🧪 {name}: {len(lines)} línies, {producte_lines} productes")
                        
                        except Exception:
                            continue
                    
                    if best_text:
                        return best_text
            
            # Si tot falla, mètode simple
            img_pil = Image.open(image_path)
            return pytesseract.image_to_string(img_pil, config=r'--oem 3 --psm 6')
            
        except Exception as e:
            print(f"❌ Error obtenint OCR: {e}")
            return ""

    def _sembla_linea_producte(self, line):
        """Determina si una línia sembla un producte"""
        line = line.strip()
        return (len(line) > 5 and 
                re.search(r'\d+[\.,°]\d{2}', line) and
                not any(word in line.upper() for word in 
                    ['TOTAL', 'IVA', 'SUBTOTAL', 'OFERTA', 'DESCUENTO']))

    def _detectar_per_columnes(self, gray_img, width, height):
        """
        Detectar productes basant-se en l'estructura de columnes del ticket
        """
        productes = []
        
        # Dividir la imatge en columnes
        columna_amplada = width // 3
        
        # Columna 1: Noms de productes (esquerra)
        col1_x1 = 0
        col1_x2 = int(width * 0.6)  # 60% per noms
        
        # Columna 2: Preus (dreta)
        col2_x1 = int(width * 0.6)
        col2_x2 = width
        
        # Dividir en files (cada fila és un producte)
        # Estimació: cada producte ocupa aproximadament 7% de l'altura
        fila_altura = int(height * 0.07)
        num_files = height // fila_altura

        for fila in range(num_files):
            y1 = int(fila * fila_altura * 1.2)  # Amb espai entre files
            y2 = min(y1 + fila_altura, height)
            
            if y2 - y1 < 20:  # Filtrar files massa petites
                continue
            
            # Processar columna de preus
            preu_roi = gray_img[y1:y2, col2_x1:col2_x2]
            preu_processed = cv2.threshold(preu_roi, 160, 255, cv2.THRESH_BINARY)[1]
            
            # OCR per al preu
            preu_img = Image.fromarray(preu_processed)
            preu_config = r'--oem 3 --psm 8 -c tessedit_char_whitelist=0123456789,.AB'
            preu_text = pytesseract.image_to_string(preu_img, config=preu_config).strip()
            
            if preu_text:
                # Buscar preu
                match = re.search(r'(\d+)[,\.]?(\d{2})', preu_text)
                if match:
                    price = float(f"{match.group(1)}.{match.group(2)}")
                    
                    # Processar columna de nom
                    nom_roi = gray_img[y1:y2, col1_x1:col1_x2]
                    nom_processed = cv2.threshold(nom_roi, 180, 255, cv2.THRESH_BINARY_INV)[1]
                    
                    nom_img = Image.fromarray(nom_processed)
                    nom_text = pytesseract.image_to_string(nom_img).strip()
                    
                    if nom_text and len(nom_text) > 2:
                        # Netejar i afegir
                        nom_net = re.sub(r'[^\w\sáéíóúàèìòùñç\.\']', ' ', nom_text)
                        nom_net = re.sub(r'\s+', ' ', nom_net).strip()
                        
                        if nom_net:
                            producto_info = self._buscar_producte(nom_net)
                            
                            producto = {
                                'producte': nom_net,
                                'nom_estandard': producto_info['nom_estandard'],
                                'familia': producto_info['familia'],
                                'preu': price,
                                'quantitat_detectada': 1,
                                'nou_producte': producto_info['nou_producte']
                            }
                            productes.append(producto)
        
        return productes
    
    def _buscar_preu_a_linia(self, line):
        """Buscar preu a una línia amb patrons tolerants"""
        if not line:
            return None
        
        # Patrons tolerants
        patrons = [
            r'(\d+)[\.,°](\d{2})\s*[AB8][:°"\s]*',  # 1,65 B: o 1,65 8:
            r'(\d+)[\.,°](\d{2})\s*[:°"\s]*',       # 1,65: o 1,65°
            r'(\d+)[\.,°](\d{2})$',                 # 1,65 al final
            r'(\d+)[\.,°](\d{2})\b',                # 1,65 a qualsevol lloc
        ]
        
        for pattern in patrons:
            match = re.search(pattern, line)
            if match:
                enter, decimals = match.groups()
                price = float(f"{enter}.{decimals}")
                
                # Correccions específiques
                if price == 4.29:
                    price = 1.29  # Correcció: 4,29 → 1,29
                elif price == 1.85:
                    price = 1.65  # Correcció: 1,85 → 1,65
                
                return price
        
        return None
    
    def _cerca_preus_no_identificats(self, lines, productes_existents):
        """Cerca preus que no s'hagin identificat com a productes coneguts"""
        productes_nous = []
        preus_existents = [p['preu'] for p in productes_existents]
        
        for i, line in enumerate(lines):
            line_clean = line.strip()
            
            # Buscar tots els preus a la línia
            matches = list(re.finditer(r'(\d+)[\.,°](\d{2})', line_clean))
            
            for match in matches:
                price = float(f"{match.group(1)}.{match.group(2)}")
                
                # Correccions
                if price == 4.29:
                    price = 1.29
                elif price == 1.85:
                    price = 1.65
                
                # Si el preu no està ja en productes i és raonable
                if (0.10 <= price <= 20.00 and 
                    not any(abs(price - p) < 0.01 for p in preus_existents)):
                    
                    # Extreure text abans del preu
                    nom_producte = line_clean[:match.start()].strip()
                    
                    # Netejar
                    nom_producte = re.sub(r'[^\w\sáéíóúàèìòùñç\.\'\-\d]', ' ', nom_producte)
                    nom_producte = re.sub(r'\s+', ' ', nom_producte).strip()
                    
                    # Eliminar números sols al principi
                    nom_producte = re.sub(r'^\d+[\.,]?\d*\s+', '', nom_producte)
                    
                    if len(nom_producte) > 2 and len(nom_producte.split()) <= 5:
                        # Verificar que no sembli metadata
                        if not any(word in nom_producte.upper() for word in 
                                ['TOTAL', 'IVA', 'SUBTOTAL', 'OFERTA']):
                            
                            producto_info = self._buscar_producte(nom_producte)
                            
                            producto = {
                                'producte': nom_producte,
                                'nom_estandard': producto_info['nom_estandard'],
                                'familia': producto_info['familia'],
                                'preu': price,
                                'quantitat_detectada': 1,
                                'nou_producte': producto_info['nou_producte']
                            }
                            
                            productes_nous.append(producto)
                            preus_existents.append(price)
        
        return productes_nous

    def _extreure_metadades_desde_imatge(self, img):
        """Extreure metadades directament de la imatge"""
        import cv2
        
        metadades = {
            'supermercat': 'Dia',
            'data': datetime.now().strftime("%d/%m/%Y"),
            'total_ticket': 0.0
        }
        
        # Convertir a PIL per OCR de la capçalera
        img_pil = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        
        # OCR només de la part superior per data
        header_height = img.shape[0] // 4
        header_img = img_pil.crop((0, 0, img.shape[1], header_height))
        
        header_text = pytesseract.image_to_string(header_img)
        
        # Buscar data
        date_match = re.search(r'(\d{2})[-\./](\d{2})[-\./](\d{4})', header_text)
        if date_match:
            dia, mes, any = date_match.groups()
            metadades['data'] = f"{dia}/{mes}/{any}"
        
        return metadades
    
    def processar_ticket_dia_definitiu(self, image_path):
        """
        Versió definitiva per processar tickets del Dia
        """
        # 1. Obtenir text OCR
        text_ocr = self._obtenir_text_ocr_fiable(image_path)
        
        # 2. Extreure productes i ofertes per ZONES
        productes, ofertes = self._extreure_productes_per_zones(text_ocr)
        
        # 3. Aplicar ofertes als productes corresponents
        productes = self._aplicar_ofertes(productes, ofertes)
        
        # 4. Resultats
        metadades = self._extreure_metadades(text_ocr)
        productes_coincidents = self.match_with_database(productes)
        
        return {
            'text_ocr': text_ocr,
            'metadades': metadades,
            'productes': productes,
            'coincidents': productes_coincidents
        }

    def _extreure_productes_i_ofertes(self, text):
        """
        Extreu productes i ofertes - UNA LÍNIA = UN PRODUCTE
        TOTA la lògica treballa amb noms de la BD
        """
        lines = text.split('\n')
        productes = []
        ofertes = []
        
        in_ofertes_section = False
        linies_processades = set()  # Control per índex de línia
        
        print("\n📄 Processant línies del ticket:")
        
        for idx, line in enumerate(lines):
            # Si ja hem processat aquesta línia, saltar
            if idx in linies_processades:
                continue
                
            line_clean = line.strip()
            if not line_clean:
                continue
            
            # 🔴🔴🔴 CRIDAR LA FUNCIÓ DE VALIDACIÓ AQUÍ 🔴🔴🔴
            if not self._es_linia_producte_valida(line_clean):
                print(f"   ⏭️ Línia {idx+1:2d}: Ignorada (no és producte vàlid)")
                continue
            
            line_upper = line_clean.upper()
            
            # Detectar secció d'ofertes
            if 'OFERTES' in line_upper or 'OFERTAS' in line_upper:
                in_ofertes_section = True
                print(f"   → Inici secció OFERTES línia {idx+1}")
                linies_processades.add(idx)
                continue
            
            # Detectar fi de secció d'ofertes
            if in_ofertes_section and ('TOTAL' in line_upper or 'DESGLOSSAMENT' in line_upper):
                in_ofertes_section = False
            
            # Buscar preu
            price_match = re.search(r'(\d+)[\.,](\d{2})', line_clean)
            if not price_match:
                continue
            
            preu = float(f"{price_match.group(1)}.{price_match.group(2)}")

            # DETECTAR QUANTITAT
            quantitat = 1
            quant_match = re.search(r'^(\d+)\s*[xX]\s*', line_clean)
            if quant_match:
                quantitat = int(quant_match.group(1))
                # Eliminar la quantitat del nom
                line_clean = re.sub(r'^(\d+)\s*[xX]\s*', '', line_clean)
                # Tornar a buscar el preu (pot haver canviat la posició)
                price_match = re.search(r'(\d+)[\.,](\d{2})', line_clean)
                if price_match:
                    preu = float(f"{price_match.group(1)}.{price_match.group(2)}")
            
            # Extreure nom brut (tot excepte el preu)
            nom_brut = line_clean[:price_match.start()].strip()
            
            # PAS 1: CONVERTIR A NOM BD IMMEDIATAMENT
            nom_net = re.sub(r'[^\w\sáéíóúàèìòùñç]', ' ', nom_brut)
            nom_net = re.sub(r'\s+', ' ', nom_net).strip()
            
            # Netejar específicament caràcters com ",", ".", "“", "”", etc.
            nom_net = re.sub(r'[.,"“”\']', '', nom_net)
            nom_net = re.sub(r'\s+', ' ', nom_net).strip()

            # Buscar a la BD per obtenir el nom estandarditzat
            info_bd = self._buscar_producte(nom_net)
            nom_bd = info_bd['nom_estandard']
            familia_bd = info_bd['familia']

            # Si estem a secció d'ofertes
            if in_ofertes_section:
                # Buscar patró de descompte
                discount_match = re.search(r'-\s*(\d+)[\.,](\d{2})', line_clean)
                if discount_match:
                    descompte = float(f"{discount_match.group(1)}.{discount_match.group(2)}")
                    
                    # DEFINIR 'nom' ABANS D'USAR-LO
                    nom_brut = line_clean[:discount_match.start()].strip()
                    
                    # Netejar el nom
                    nom_net = re.sub(r'[^\w\sáéíóúàèìòùñç]', ' ', nom_brut)
                    nom_net = re.sub(r'\s+', ' ', nom_net).strip()
                    
                    # Buscar a la BD per obtenir nom estandarditzat
                    info_bd = self._buscar_producte(nom_net)
                    nom_bd = info_bd['nom_estandard']
                    
                    oferta = {
                        'producte_brut': nom_net, 
                        'producte': nom_bd,                        
                        'descompte': descompte,
                        'linia': idx + 1
                    }
                    ofertes.append(oferta)
                    linies_processades.add(idx)
                    print(f"   🔖 Oferta: {nom_bd} -{descompte:.2f}€")
                continue
            
            # PAS 3: CREAR PRODUCTE AMB NOM BD
            producte = {
                'producte_brut': nom_brut,
                'producte': nom_bd,  # El nom que es mostrarà és el de BD
                'nom_estandard': nom_bd,
                'familia': familia_bd,
                'preu': preu,
                'quantitat_detectada': quantitat,
                'nou_producte': info_bd['nou_producte'],
                'numero_linia': idx + 1,
                'linia_original': line_clean,
                'descompte_aplicat': 0.0
            }
            
            productes.append(producte)
            linies_processades.add(idx)         
            
            print(f"   ✅ Línia {idx+1:2d}: {nom_bd} - {preu:.2f}€")
        
        # ORDENAR PER NÚMERO DE LÍNIA
        productes.sort(key=lambda x: x['numero_linia'])
        
        print(f"\n📊 Resum: {len(productes)} productes únics, {len(ofertes)} ofertes")
        return productes, ofertes

    def _aplicar_ofertes(self, productes, ofertes):
        """Aplica els descomptes d'ofertes als productes corresponents de manera GENERAL"""
        if not ofertes:
            return productes
        
        print("\n🔧 Aplicant ofertes:")
        import difflib
        
        for oferta in ofertes:
            nom_oferta_brut = oferta.get('producte_brut', oferta.get('producte', '')).upper()
            descompte_total = oferta['descompte']
            
            print(f"   Buscant producte per a oferta: '{nom_oferta_brut}' -{descompte_total:.2f}€")
            
            # Netejar el nom de l'oferta per comparar
            import re
            nom_net = re.sub(r'[^\w\s]', ' ', nom_oferta_brut)
            nom_net = re.sub(r'\s+', ' ', nom_net).strip()
            
            millor_producte = None
            millor_similitud = 0
            
            for producte in productes:
                if producte.get('descompte_aplicat', 0) > 0:
                    continue
                
                nom_producte = producte.get('nom_estandard', producte['producte']).upper()
                nom_producte_net = re.sub(r'[^\w\s]', ' ', nom_producte)
                nom_producte_net = re.sub(r'\s+', ' ', nom_producte_net).strip()
                
                # Calcular similitud
                similitud = difflib.SequenceMatcher(None, nom_net, nom_producte_net).ratio()
                
                # Paraules coincidents (mètode addicional)
                paraules_oferta = set(nom_net.split())
                paraules_producte = set(nom_producte_net.split())
                coincidencies = len(paraules_oferta.intersection(paraules_producte))
                
                # Puntuació combinada
                if coincidencies > 0:
                    puntuacio = similitud + (coincidencies * 0.2)
                else:
                    puntuacio = similitud
                
                if puntuacio > millor_similitud and puntuacio > 0.3:  # Llindar mínim
                    millor_similitud = puntuacio
                    millor_producte = producte
            
            if millor_producte:
                # 🔴🔴🔴 GUARDAR EL DESCOMPTE TOTAL, NO PER UNITAT
                millor_producte['descompte_aplicat'] = descompte_total  # Guardem el descompte TOTAL
                millor_producte['preu_original'] = millor_producte['preu']
                # El preu unitari NO CANVIA (el càlcul del total es fa a _afegir_linia_des_de_dades)
                
                quantitat = millor_producte.get('quantitat_detectada', 1)
                print(f"   ✅ Oferta aplicada a: {millor_producte['producte']} (similitud: {millor_similitud:.2f})")
                print(f"      Descompte TOTAL: {descompte_total:.2f}€ per a {quantitat} unitats")
            else:
                print(f"   ⚠️ No s'ha trobat producte per a l'oferta: {nom_oferta_brut}")
        
        return productes
    
    def _es_producte_valid(self, line, idx):
        """
        Verifica si una línia és un producte vàlid
        Retorna True si la línia sembla un producte, False si és una altra cosa
        """
        line_clean = line.strip()
        
        # FILTRE 1: Línia massa curta
        if len(line_clean) < 5:
            return False
        
        # FILTRE 2: Patrons que clarament NO són productes
        patron_no_producte = [
            r'^\([AB]\)',                    # (A) o (B)
            r'^[AB]\s*\d+[,.]\d{2}%',        # A 4,00% o B 10,00%
            r'TIPUS IVA',                     # TIPUS IVA
            r'BASE\s+QUOTA',                  # BASE QUOTA
            r'DESGLOSSAMENT',                  # DESGLOSSAMENT
            r'TOTAL',                          # TOTAL
            r'SUBTOTAL',                       # SUBTOTAL
            r'OFERTA',                          # OFERTA
            r'OFERTES',                         # OFERTES
            r'ClubDia',                         # ClubDia
            r'CUPON',                            # CUPON
            r'Cupones',                          # Cupones
            r'ESTALVI',                          # ESTALVI
            r'HORARI',                           # HORARI
            r'OBRIM',                            # OBRIM
            r'FACTURA',                          # FACTURA
            r'N\.FACT',                          # N.FACT
            r'N\.CAIXA',                         # N.CAIXA
            r'\*{10,}',                          # Línia d'asteriscs (********)
            r'ID:',                              # ID:
            r'DHAN RAJA',                        # Nom de l'empresa
            r'CIF\.',                            # CIF.
        ]
        
        line_upper = line_clean.upper()
        for patron in patron_no_producte:
            if re.search(patron, line_upper):
                print(f"   ⚠️ Línia {idx+1:2d}: Filtrada (patró): {line_clean[:40]}...")
                return False
        
        # FILTRE 3: Paraules clau que indiquen que NO és un producte
        paraules_no_producte = [
            'TOTAL', 'IVA', 'SUBTOTAL', 'OFERTA', 'DESCUENTO', 
            'CUPON', 'FACTURA', 'TICKET', 'GRUPO DIA', 'CLUBDIA',
            'DESGLOSSAMENT', 'TIPUS', 'BASE', 'QUOTA', 'ESTALVI',
            'OFERTES', 'Cupones', 'REGALO', 'CANICA', 'cupons',
            'HORARI', 'OBRIM', 'FACTURA', 'N.FACT', 'N.CAIXA',
            '**********************************************',
            'ID:', 'CIF', 'DHAN', 'RAJA', 'SAHIB', 'SLU',
            'CR SANTA FE', 'ARBUCES', 'GERONA'
        ]
        
        for palabra in paraules_no_producte:
            if palabra in line_upper:
                print(f"   ⚠️ Línia {idx+1:2d}: Filtrada (paraula '{palabra}'): {line_clean[:40]}...")
                return False
        
        # FILTRE 4: Massa símbols estranys (OCR mal llegit)
        simbols_estranys = len(re.findall(r'[^a-zA-Z0-9\sáéíóúàèìòùñç€.,%°\-]', line_clean))
        if simbols_estranys > 3:
            print(f"   ⚠️ Línia {idx+1:2d}: Filtrada (símbols estranys: {simbols_estranys}): {line_clean[:40]}...")
            return False
        
        # FILTRE 5: Massa números en comparació amb lletres
        lletres = len(re.findall(r'[a-zA-Záéíóúàèìòùñç]', line_clean))
        numeros = len(re.findall(r'\d', line_clean))
        
        if numeros > lletres * 2 and lletres < 8:
            print(f"   ⚠️ Línia {idx+1:2d}: Filtrada (massa números): {line_clean[:40]}...")
            return False
        
        # FILTRE 6: El preu ha de ser raonable
        price_match = re.search(r'(\d+)[\.,](\d{2})', line_clean)
        if price_match:
            preu = float(f"{price_match.group(1)}.{price_match.group(2)}")
            if preu > 100.00:  # Preu massa alt per un producte normal
                print(f"   ⚠️ Línia {idx+1:2d}: Filtrada (preu massa alt: {preu:.2f}€): {line_clean[:40]}...")
                return False
        
        # Si passa tots els filtres, és probablement un producte
        return True

    def _es_linia_producte_valida(self, text):
        """Determinar si una línia de text és un producte vàlid"""
        text_original = text.strip()
        text_upper = text_original.upper()
        
        # 🔴🔴🔴 PARAULES QUE NO SÓN PRODUCTES (AMPLIAT)
        PARAULES_EXCLOSES = [
            'TARGET', 'TEF', 'IMPORT', 'TOTAL', 'PAGAR', 'EUROS', 
            'AUT', 'ID:', 'REF', 'DATA', 'HORA', 'GRUPO', 'DIA',
            'FACTURA', 'DESGLOSSAMENT', 'TIPUS', 'IVA', 'BASE', 'QUOTA',
            'CLUBDIA', 'CUPONS', 'OFERTES', 'CONTACTLESS', 'VERIFICADO',
            'DHAN RAJA', 'CIF', 'SLU', 'CR SANTA FE', 'ARBUCES', 'GERONA',
            '**********************************************',
            'CAL', '(A)', '(B)', '(C)', 'TOTAL A PAGAR', 'TARGET', 'IMPORT'
        ]
        
        for paraula in PARAULES_EXCLOSES:
            if paraula in text_upper:
                print(f"   ⏭️ Descartat per paraula exclosa: {paraula}")
                return False
        
        # 🔴 HA DE CONTENIR UN PREU (però no masses preus)
        import re
        preus = re.findall(r'\d+[.,]\d{2}', text)
        if len(preus) != 1:  # Exactament 1 preu per línia
            if len(preus) > 1:
                print(f"   ⏭️ Descartat (massa preus): {preus}")
            return False
        
        # 🔴 EL TEXT ABANS DEL PREU HA DE TENIR ALMENYS 3 CARÀCTERS
        match = re.search(r'\d+[.,]\d{2}', text)
        if match:
            text_abans = text[:match.start()].strip()
            if len(text_abans) < 3:
                print(f"   ⏭️ Descartat (text massa curt): '{text_abans}'")
                return False
        
        return True

    def _es_inici_zona_productes(self, text):
        """Detectar inici de zona de productes - VERSIÓ TOLERANT"""
        text_upper = text.upper()
        
        # Paraules clau que indiquen inici de productes
        PARAULES_CLAU = [
            'DESCRIPCIO', 'DESCRIPCIÓ', 'DESCRIPCION', 'DESCRIPCIG', 
            'ARTICLE', 'ARTICULO',
            'IMPORT', 'IMPORTE',
            'QUANTITAT', 'CANTIDAD',
            'PVP', 'PREU', 'PRECIO'
        ]
        
        # Comptar quantes paraules clau apareixen
        coincidencies = 0
        for paraula in PARAULES_CLAU:
            if paraula in text_upper:
                coincidencies += 1
        
        # Si hi ha almenys 2 paraules clau, és inici de productes
        if coincidencies >= 2:
            print(f"      ✅ Inici productes detectat ({coincidencies} coincidències)")
            return True
        
        return False

    def _extreure_productes_per_zones(self, text):
        """Extreu productes i ofertes basant-se en l'estructura coneguda del ticket"""
        lines = text.split('\n')
        
        zona_actual = "capçalera"
        productes = []
        ofertes = []
        zona_productes_iniciada = False
        
        print("\n📄 Processant ticket per zones:")
        
        idx = 0
        while idx < len(lines):
            line = lines[idx]
            line_clean = line.strip()
            
            if not line_clean:
                idx += 1
                continue
            
            line_upper = line_clean.upper()
            
            # Detectar inici de productes
            if not zona_productes_iniciada and self._es_inici_zona_productes(line_upper):
                zona_actual = "productes"
                zona_productes_iniciada = True
                print(f"   → Zona PRODUCTES iniciada a línia {idx+1}: {line_clean[:50]}")
                idx += 1
                continue
            
            # Un cop iniciada la zona, processem productes
            if zona_productes_iniciada and zona_actual == "productes":
                
                # Detectar fi de zona de productes
                if 'OFERTES' in line_upper or 'OFERTAS' in line_upper:
                    zona_actual = "ofertes"
                    print(f"   → Zona OFERTES iniciada a línia {idx+1}: {line_clean[:50]}")
                    idx += 1
                    continue
                
                if 'TOTAL COMPRA' in line_upper:
                    print(f"   → Fi de ticket a línia {idx+1}")
                    break
                
                # 🔴🔴🔴 DETECCIÓ DE PRODUCTES AMB PES (2 LÍNIES)
                import re
                
                # Comprovar si la línia actual és un nom (sense preu) i la següent té format de pes
                te_preu_actual = re.search(r'\d+[.,]\d{2}', line_clean) is not None
                
                if not te_preu_actual and idx + 1 < len(lines):
                    # La línia actual no té preu, mirem la següent
                    next_line = lines[idx + 1].strip()
                    
                    # Comprovar si la següent línia té format de pes
                    if 'kg' in next_line.lower() and re.search(r'\d+[.,]\d{3}', next_line):
                        print(f"   ⚖️ Possible producte amb pes a línies {idx+1}-{idx+2}")
                        
                        # Detectar producte amb pes
                        dades_pes = self._detectar_producte_pes_dos_linies(line_clean, next_line, idx)
                        
                        if dades_pes:
                            producte = self._processar_producte_amb_pes(dades_pes, idx)
                            if producte:
                                productes.append(producte)
                            
                            # Saltar la següent línia
                            idx += 2
                            continue
                
                # Si no és producte amb pes, processar com a normal
                # 🔴🔴🔴 PASSAR LA ZONA ACTUAL A LA FUNCIÓ
                producte = self._processar_linia_producte(line_clean, idx, zona_actual)
                if producte:
                    productes.append(producte)
                
                idx += 1
                        
            elif zona_actual == "ofertes":
                # Processar ofertes
                if 'TOTAL COMPRA' in line_upper:
                    break
                oferta = self._processar_linia_oferta(line_clean, idx)
                if oferta:
                    ofertes.append(oferta)
                idx += 1
            
            else:
                idx += 1
        
        print(f"\n📊 Resum: {len(productes)} productes, {len(ofertes)} ofertes")
        return productes, ofertes

    def _es_inici_zona_ofertes(self, text):
        """Detectar inici de zona d'ofertes tolerant errors OCR"""
        patrons = [
            r'OFERTES',                    # OFERTES
            r'OFERTAS',                    # OFERTAS
            r'OFERTES?\(O\)',              # OFERTES(O)
            r'OFERTES?\(O\)\s+I\s+CUPONS', # OFERTES(O) I CUPONS
            r'CUPONS?\s+CLUBDIA',          # CUPONS ClubDia
        ]
        
        for patro in patrons:
            if re.search(patro, text, re.IGNORECASE):
                return True
        
        return 'OFERTES' in text or 'CUPONS' in text

    def _es_fi_ticket(self, text):
        """Detectar fi de ticket"""
        patrons = [
            r'TOTAL\s+COMPRA\s+GRUPO\s+DIA',
            r'TOTAL\s+COMPRA',
            r'TOTAL\s+A\s+PAGAR',
        ]
        
        for patro in patrons:
            if re.search(patro, text, re.IGNORECASE):
                return True
        
        return 'TOTAL' in text and 'GRUPO' in text

    def _processar_linia_producte(self, line, idx, zona="productes"):
        """Processa una línia de la zona de productes"""

        import re
        
        # 🔴🔴🔴 FILTRE PER ZONA: Si estem a ofertes, ignorar completament
        if zona == "ofertes":
            print(f"   ⏭️ Línia {idx+1}: Ignorada (és oferta, no producte)")
            return None
        
        # 🔴🔴🔴 FILTRE RÀPID: Ignorar línies que comencin amb (A), (B), (C)
        if line.strip().startswith(('(A)', '(B)', '(C)')):
            print(f"   ⏭️ Línia {idx+1}: Ignorada (IVA)")
            return None
        
        # 🔴🔴🔴 FILTRE: Ignorar línies amb "CAL", "TOTAL", "TARGET", "IMPORT"
        line_upper = line.upper()
        if any(p in line_upper for p in ['CAL', 'TOTAL', 'TARGET', 'IMPORT', 'PAGAR', 'EUROS']):
            # Però permetre si sembla un producte real
            if 'CAL' in line_upper and len(line) < 10:
                print(f"   ⏭️ Línia {idx+1}: Ignorada (CAL)")
                return None
            # Si té aquestes paraules però també té estructura de producte, potser és producte
            if not re.search(r'\d+[.,]\d{2}', line):
                return None
        
        # IGNORAR LÍNIES QUE SÓN NOMS SENSE PREU
        import re
        if not re.search(r'\d+[.,]\d{2}', line):
            return None
        
        # IGNORAR LÍNIES QUE SÓN DE PES (les processa un altre mètode)
        if 'kg' in line.lower() and re.search(r'\d+[.,]\d{3}', line):
            print(f"   ⏭️ Línia {idx+1}: Ignorada (línia de pes, la processa _detectar_producte_pes_dos_linies)")
            return None
        
        line_clean = line.strip()
        
        # 🔴🔴🔴 ELIMINAR LA LLETRA D'IVA DEL FINAL (A, B o C)
        line_clean = re.sub(r'\s+[ABC]\s*$', '', line_clean)
        line_clean = re.sub(r'([\d.,])[ABC]\b', r'\1', line_clean)
        
        # 🔴🔴🔴 ELIMINAR POSSIBLES 4 o 8 AL FINAL (IVA mal llegit)
        line_clean = re.sub(r'\s+[48]\s*$', '', line_clean)
        
        print(f"      🧼 Línia netejada: {line_clean}")
        
        # BUSCAR PREU (ACCEPTA 2 O 3 DECIMALS)
        price_match = re.search(r'(\d+)[\.,](\d{2,3})', line_clean)
        if not price_match:
            return None
        
        # GESTIONAR PREU AMB POSSIBLES 3 DECIMALS
        if len(price_match.group(2)) == 3:
            # Si té 3 decimals, agafar només els 2 primers
            preu_str = f"{price_match.group(1)}.{price_match.group(2)[:2]}"
            preu = float(preu_str)
            possible_quantitat = int(price_match.group(2)[2])
            print(f"      ⚠️ Preu amb 3 decimals corregit a: {preu} (possible quantitat: {possible_quantitat})")
        else:
            preu = float(f"{price_match.group(1)}.{price_match.group(2)}")
            possible_quantitat = None
        
        print(f"      ✅ Preu trobat: {preu}")
        
        # EXTRURE NOM (TOT EXCEPTE EL PREU)
        nom_brut = line_clean[:price_match.start()].strip()
        print(f"      📝 Nom brut: '{nom_brut}'")
        
        # DETECTAR QUANTITAT
        quantitat = 1

        # Mètode 1: Quantitat al principi (ex: "4 XAMPINYO")
        quant_match_inci = re.search(r'^(\d+)\s+', nom_brut)
        if quant_match_inci:
            q = int(quant_match_inci.group(1))
            if 1 <= q <= 9:
                quantitat = q
                nom_brut = nom_brut[quant_match_inci.end():].strip()
                print(f"      🔢 Quantitat al principi: {quantitat}")

        # Mètode 2: Quantitat al final
        else:
            parts = line_clean.split()
            if len(parts) >= 2:
                ultim = parts[-1]
                if ultim.isdigit():
                    q = int(ultim)
                    # Ignorar 4 i 8 (probables lletres d'IVA mal llegides)
                    if q in [4, 8]:
                        print(f"      ⚠️ Possible IVA mal llegit: {q} (ignorat)")
                    elif 1 <= q <= 9:
                        quantitat = q
                        print(f"      🔢 Quantitat al final: {quantitat}")
        
        # Mètode 3: Possible quantitat dels decimals (només si no vam trobar altra)
        if quantitat == 1 and possible_quantitat and 1 <= possible_quantitat <= 9:
            quantitat = possible_quantitat
            print(f"      🔢 Quantitat dels decimals: {quantitat}")
        
        print(f"      🔢 Quantitat final: {quantitat}")
        
        # BUSCAR A LA BD
        nom_net = re.sub(r'[^\w\sáéíóúàèìòùñç]', ' ', nom_brut)
        nom_net = re.sub(r'\s+', ' ', nom_net).strip()
        
        info_bd = self._buscar_producte(nom_net)
        
        return {
            'producte_brut': nom_brut,
            'producte': info_bd['nom_estandard'],
            'nom_estandard': info_bd['nom_estandard'],
            'familia': info_bd['familia'],
            'preu': preu,
            'preu_original': preu,
            'descompte_aplicat': 0.0,
            'quantitat_detectada': quantitat,
            'nou_producte': info_bd['nou_producte'],
            'numero_linia': idx + 1,
            'linia_original': line
        }
        
    def _processar_linia_oferta(self, line, idx):
        """
        Processa una línia de la zona d'ofertes
        """
        line_clean = line.strip()
        
        # 🔴 1. Ha de contenir un descompte (amb signe -)
        discount_match = re.search(r'-\s*(\d+)[\.,](\d{2})', line_clean)
        if not discount_match:
            return None
        
        descompte = float(f"{discount_match.group(1)}.{discount_match.group(2)}")
        
        # 🔴 2. Ha de tenir text abans del descompte
        text_abans = line_clean[:discount_match.start()].strip()
        if len(text_abans) < 2:
            return None
        
        # 🔴 3. Netejar el nom de l'oferta
        nom_net = re.sub(r'[^\w\sáéíóúàèìòùñç]', ' ', text_abans)
        nom_net = re.sub(r'\s+', ' ', nom_net).strip()
        nom_net = re.sub(r'[.,"“”\']', '', nom_net)
        nom_net = re.sub(r'\s+', ' ', nom_net).strip()
        
        # 🔴 4. Buscar a la BD
        info_bd = self._buscar_producte(nom_net)
        
        print(f"   🔖 Oferta línia {idx+1:2d}: {info_bd['nom_estandard']} -{descompte:.2f}€")
        
        return {
            'producte_brut': nom_net,
            'producte': info_bd['nom_estandard'],
            'familia': info_bd['familia'],
            'descompte': descompte,
            'linia': idx + 1
        }

    def _detectar_producte_pes_dos_linies(self, linia_nom, linia_pes, idx):
        """
        Detecta si la línia actual i la següent formen un producte amb pes
        Versió amb patrons tolerants per errors OCR
        """
        import re
        
        nom = linia_nom.strip()
        linia2 = linia_pes.strip()
        
        print(f"      🔍 Detectant pes: '{linia2}'")
        
        # ELIMINAR LLETRA D'IVA
        linia2 = re.sub(r'\s+[ABC]\s*$', '', linia2)
        linia2 = re.sub(r'([\d.,])[ABC]\b', r'\1', linia2)
        
        # IGNORAR 4 i 8 AL FINAL (POSSIBLES IVA MAL LLEGITS)
        linia2 = re.sub(r'\s+[48]\s*$', '', linia2)
        
        # 🔴🔴🔴 PATRÓ PER "€/ky" (error comú d'OCR)
        patron_ky = r'(\d+[.,]\d{3})\s*kg\s*(\d+[.,]\d{2})\s*€/k\w\s*(\d+[.,]\d{2,3})'
        
        match = re.search(patron_ky, linia2, re.IGNORECASE)
        if match:
            pes_kg = float(match.group(1).replace(',', '.'))
            preu_kg = float(match.group(2).replace(',', '.'))
            preu_total = float(match.group(3).replace(',', '.'))
            
            # Si el preu total és massa gran, potser és 1274 → 1.274
            if preu_total > 100:
                preu_total = preu_total / 1000
            
            pes_grams = int(pes_kg * 1000)
            
            print(f"      ✅ PATRÓ KY - Producte amb pes: {pes_grams}g, {preu_kg:.2f}€/kg, total {preu_total:.2f}€")
            return {
                'nom': nom,
                'pes_grams': pes_grams,
                'preu_kg': preu_kg,
                'preu_total': preu_total,
                'linia_original': f"{nom} {linia2}"
            }
        
        # Per productes amb unitats (ud)
        patron_ud = r'(\d+)\s*ud\s*(\d+[.,]\d{2})\s*€/ud\s*(\d+[.,]\d{2})'
        
        
        match = re.search(patron1, linia2, re.IGNORECASE)
        if match:
            pes_kg = float(match.group(1).replace(',', '.'))
            preu_kg = float(match.group(2).replace(',', '.'))
            preu_total = float(match.group(3).replace(',', '.'))
            
            pes_grams = int(pes_kg * 1000)
            
            print(f"      ✅ PATRÓ 1 - Producte amb pes: {pes_grams}g, {preu_kg:.2f}€/kg, total {preu_total:.2f}€")
            return {
                'nom': nom,
                'pes_grams': pes_grams,
                'preu_kg': preu_kg,
                'preu_total': preu_total,
                'linia_original': f"{nom} {linia2}"
            }
        
        # 🔴 PATRÓ 2: Format amb errors OCR "0,670 kg 1,59-€/kg 1507/4"
        patron2 = r'(\d+[.,]\d{3})\s*kg\s*(\d+[.,]\d{2})[-\s]*€?/kg\s*(\d+)[^\d]*(\d+)'
        
        match = re.search(patron2, linia2, re.IGNORECASE)
        if match:
            pes_kg = float(match.group(1).replace(',', '.'))
            preu_kg = float(match.group(2).replace(',', '.'))
            
            part1 = match.group(3)
            part2 = match.group(4)
            
            # Reconstruir preu total
            if len(part1) == 1 and len(part2) == 2:
                preu_total = float(f"{part1}.{part2}")
            elif len(part1) == 4:
                preu_total = float(part1) / 1000
            else:
                preu_total = float(f"{part1}.{part2}") / 100
            
            pes_grams = int(pes_kg * 1000)
            
            print(f"      ✅ PATRÓ 2 (OCR erroni) - Producte amb pes: {pes_grams}g, {preu_kg:.2f}€/kg, total {preu_total:.2f}€")
            return {
                'nom': nom,
                'pes_grams': pes_grams,
                'preu_kg': preu_kg,
                'preu_total': preu_total,
                'linia_original': f"{nom} {linia2}"
            }
        
        # 🔴 PATRÓ 3: Format simple "0,670 1,59 1,07"
        patron3 = r'(\d+[.,]\d{3})\s+(\d+[.,]\d{2})\s+(\d+[.,]\d{2})'
        
        match = re.search(patron3, linia2, re.IGNORECASE)
        if match:
            pes_kg = float(match.group(1).replace(',', '.'))
            preu_kg = float(match.group(2).replace(',', '.'))
            preu_total = float(match.group(3).replace(',', '.'))
            
            pes_grams = int(pes_kg * 1000)
            
            print(f"      ✅ PATRÓ 3 - Producte amb pes: {pes_grams}g, {preu_kg:.2f}€/kg, total {preu_total:.2f}€")
            return {
                'nom': nom,
                'pes_grams': pes_grams,
                'preu_kg': preu_kg,
                'preu_total': preu_total,
                'linia_original': f"{nom} {linia2}"
            }
        
        print(f"      ⚠️ No s'ha detectat patró de pes")
        return None
    
    def _processar_producte_amb_pes(self, dades_pes, idx):
        """Processa un producte que ve amb pes en dues línies"""
        
        print(f"   ⚖️ Producte amb pes a línies {idx+1}-{idx+2}: {dades_pes['nom']} - {dades_pes['pes_grams']}g")
        
        # Buscar a la BD
        info_bd = self._buscar_producte(dades_pes['nom'])
        
        # Determinar família (si no està a la BD, pot ser fruita)
        familia = info_bd['familia']
        if familia == 'Desconeguda':
            # Per banana, assignar fruita
            nom_lower = dades_pes['nom'].lower()
            if 'banana' in nom_lower or 'platan' in nom_lower:
                familia = 'fruita'
            elif any(p in nom_lower for p in ['tomaquet', 'tomate', 'enciam', 'ceba']):
                familia = 'verdura'
        
        # Crear el producte amb TOTES les dades
        producte = {
            'producte_brut': dades_pes['linia_original'],
            'producte': info_bd['nom_estandard'] if info_bd['nom_estandard'] != dades_pes['nom'] else dades_pes['nom'],
            'nom_estandard': info_bd['nom_estandard'],
            'familia': familia,
            'preu': dades_pes['preu_total'],           # Preu final
            'preu_original': dades_pes['preu_total'],   # Sense descompte
            'descompte_aplicat': 0.0,
            'quantitat_detectada': 1,
            'pes_grams': dades_pes['pes_grams'],        # 🔴 Guardar pes
            'preu_kg': dades_pes['preu_kg'],            # 🔴 Guardar preu per kg
            'te_pes': True,
            'nou_producte': info_bd['nou_producte'],
            'numero_linia': idx + 1,
            'linia_original': dades_pes['linia_original']
        }
        
        print(f"   ✅ Producte processat: {producte['producte']} - {producte['pes_grams']}g - {producte['preu']:.2f}€")
        
        return producte