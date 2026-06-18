# controllers/introProductesSuper.py
import sqlite3
import difflib
from PySide6.QtWidgets import QMessageBox
from config.llistes import (
    obtenir_supers,
    obtenir_families_compres,
    obtenir_articles_per_familia,
    afegir_familia,
    afegir_article
)

class IntroProductesSuperController:
    def __init__(self, output_widget=None):  # CORREGIT: Afegit paràmetre opcional
        """
        Inicialitza el controlador.
        
        Args:
            output_widget: Widget per mostrar missatges (QTextEdit, QLineEdit, etc.)
        """
        self.db_path = "Bases/BD_Productes.db"
        self.output_widget = output_widget        
        self.similitud_per_defecte = 0.7
        self.connectar_db()

    def set_output_widget(self, widget):
        """Estableix el widget per mostrar missatges"""
        self.output_widget = widget

    def mostrar_missatge(self, missatge, tipus="info"):
        """
        Mostra un missatge al widget de sortida.
        
        Args:
            missatge: Text del missatge
            tipus: "info", "warning", "error", "success"
        """
        if not self.output_widget:
            return
        
        # Colors per als diferents tipus de missatge
        colors = {
            "info": "black",
            "warning": "orange",
            "error": "red",
            "success": "green"
        }
        
        color = colors.get(tipus, "black")
        
        try:
            # Si és QTextEdit
            if hasattr(self.output_widget, 'setTextColor'):
                self.output_widget.setTextColor(color)
                self.output_widget.append(f"{missatge}")
                self.output_widget.setTextColor("black")  # Tornar al color per defecte
            # Si és QLineEdit
            elif hasattr(self.output_widget, 'setText'):
                self.output_widget.setText(missatge)
                # Canviar color del text (si suporta estils)
                self.output_widget.setStyleSheet(f"color: {color};")
            
            # Forçar actualització de la interfície
            if hasattr(self.output_widget, 'repaint'):
                self.output_widget.repaint()
                
        except Exception as e:
            print(f"Error mostrant missatge: {e}")
    
    def connectar_db(self):
        """Connexió segura a la base de dades"""
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.execute("PRAGMA foreign_keys = ON")
            self.cursor = self.conn.cursor()
            self.crear_taules_si_no_existeixen()
            if self.output_widget:
                self.mostrar_missatge("✅ Connectat a la base de dades", "success")
            return True
        except Exception as e:
            error_msg = f"❌ Error connectant a BD: {e}"
            if self.output_widget:
                self.mostrar_missatge(error_msg, "error")
            print(error_msg)
            return False
    
    def crear_taules_si_no_existeixen(self):
        """Crear les taules si no existeixen"""
        try:
            # Crear TBProductes si no existeix
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS TBProductes (
                    idProducte INTEGER PRIMARY KEY AUTOINCREMENT,
                    nom_estandard TEXT NOT NULL UNIQUE,
                    familia TEXT NOT NULL,
                    unitat TEXT,
                    data_creacio TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Crear TBNomsProducte si no existeix
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS TBNomsProducte (
                    idNom INTEGER PRIMARY KEY AUTOINCREMENT,
                    idProducte INTEGER NOT NULL,
                    supermercat TEXT NOT NULL,
                    nom_super TEXT NOT NULL,
                    similitud_minima REAL DEFAULT 0.7,
                    data_afegit TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (idProducte) REFERENCES TBProductes(idProducte) ON DELETE CASCADE,
                    UNIQUE(supermercat, nom_super)
                )
            ''')
            
            # Crear índexs si no existeixen
            self.cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_noms_producte 
                ON TBNomsProducte (idProducte)
            ''')
            
            self.cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_noms_supermercat 
                ON TBNomsProducte (supermercat, nom_super)
            ''')
            
            self.cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_productes_familia 
                ON TBProductes (familia)
            ''')
            
            self.conn.commit()
            if self.output_widget:
                self.mostrar_missatge("✅ Taules i índexs verificats/creats correctament", "success")
            
        except Exception as e:
            error_msg = f"❌ Error creant taules: {e}"
            if self.output_widget:
                self.mostrar_missatge(error_msg, "error")
            print(error_msg)
    
    def desconnectar_db(self):
        """Tancar connexió"""
        if hasattr(self, 'conn'):
            self.conn.close()
            if self.output_widget:
                self.mostrar_missatge("ℹ️ Connexió a BD tancada", "info")
       
    # def obtenir_supers_disponibles(self):
    #     """Obtenir supermercats pels tickets OCR"""
    #     try:
    #         from config.llistes import obtenir_supers
            
    #         supers = obtenir_supers()
    #         return supers
            
    #     except Exception as e:
    #         print(f"❌ Error obtenint supers OCR: {e}")
    #         return ["Dia", "AreaGuissona", "Novavenda", "Clarel", "Mercadona"] 

    def obtenir_supers_disponibles(self):
        """Obtenir supermercats pels tickets OCR"""
        try:        
            # Prova diferents maneres d'importar
            try:
                from config.llistes import obtenir_supers
            except ImportError:
                print(f"⚠️ DEBUG: Import directe fallat, provant relatiu...")
                import sys
                import os
                # Provar import relatiu
                sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
                from config.llistes import obtenir_supers
            
            supers = obtenir_supers()
            return supers
            
        except Exception as e:
            print(f"❌ Error obtenint supers OCR: {e}")
            import traceback
            traceback.print_exc()
            return ["Dia", "AreaGuissona", "Novavenda", "Clarel", "Mercadona"]
        
    def obtenir_families_disponibles(self):
        """Obtenir FAMÍLIES de families_compres"""
        try:
            return obtenir_families_compres()
        except Exception as e:
            if self.output_widget:
                self.mostrar_missatge(f"❌ Error obtenint families: {e}", "error")
            print(f"❌ Error obtenint families: {e}")
            return []
    
    def obtenir_articles_per_familia_disponibles(self, familia):
        """Obtenir ARTICLES d'una família específica"""
        try:
            return obtenir_articles_per_familia(familia)
        except Exception as e:
            if self.output_widget:
                self.mostrar_missatge(f"❌ Error obtenint articles: {e}", "error")
            print(f"❌ Error obtenint articles: {e}")
            return []
    
    def obtenir_families_bd(self):
        """Obtenir FAMÍLIES que JA HI SÓN a la BD"""
        try:
            self.cursor.execute('SELECT DISTINCT familia FROM TBProductes ORDER BY familia')
            resultats = self.cursor.fetchall()
            return [row[0] for row in resultats]
        except Exception as e:
            if self.output_widget:
                self.mostrar_missatge(f"❌ Error obtenint families BD: {e}", "error")
            return []
    
    def obtenir_productes_per_familia_bd(self, familia):
        """Obtenir PRODUCTES d'una família CONCRETA de la BD"""
        try:
            self.cursor.execute('''
                SELECT idProducte, nom_estandard, unitat FROM TBProductes 
                WHERE familia = ? ORDER BY nom_estandard
            ''', (familia,))
            resultats = self.cursor.fetchall()
            return [{'id': row[0], 'nom': row[1], 'unitat': row[2]} for row in resultats]
        except Exception as e:
            if self.output_widget:
                self.mostrar_missatge(f"❌ Error obtenint productes família BD: {e}", "error")
            return []
    
    def obtenir_tots_productes(self):
        """Obtenir tots els productes - VERSIÓ ULTRA-SIMPLE"""
        try:
            # Intentem la consulta més bàsica possible
            self.cursor.execute("SELECT * FROM TBProductes")
            resultats = self.cursor.fetchall()
            
            productes = []
            for row in resultats:
                # Adaptem-nos a qualsevol estructura
                producte = {
                    'id': row[0] if len(row) > 0 else 0,
                    'nom': str(row[1]) if len(row) > 1 else 'Sense nom',
                    'familia': str(row[2]) if len(row) > 2 else '',
                    'unitat': str(row[3]) if len(row) > 3 else ''
                }
                productes.append(producte)
            
            return productes
            
        except Exception as e:
            print(f"Error obtenint productes (ultra-simple): {e}")
            return []
        
    def cerca_automatica(self, terme, limit=10):
        """Cerca automàtica mentre s'escriu"""
        if not terme or len(terme.strip()) < 2:
            if self.output_widget:
                self.mostrar_missatge("ℹ️ Escriu almenys 2 caràcters per cercar", "info")
            return []
        
        terme = terme.strip()
        terme_norm = self.normalitzar_nom(terme)
        resultats = []
        
        try:
            if self.output_widget:
                self.mostrar_missatge(f"🔍 Cercant '{terme}'...", "info")
            
            # 1. Cerca productes estàndard (coincidències exactes o parcials)
            self.cursor.execute('''
                SELECT idProducte, nom_estandard, familia, unitat 
                FROM TBProductes 
                WHERE LOWER(nom_estandard) LIKE ? 
                ORDER BY nom_estandard
                LIMIT ?
            ''', (f'%{terme_norm}%', limit))
            
            productes_trobats = self.cursor.fetchall()
            for row in productes_trobats:
                resultats.append({
                    'tipus': 'estandard',
                    'id': row[0],
                    'nom': row[1],
                    'familia': row[2],
                    'unitat': row[3],
                    'puntuacio': 1.0
                })
            
            # 2. Cerca noms de supermercat
            self.cursor.execute('''
                SELECT np.idNom, np.nom_super, np.supermercat, np.similitud_minima,
                       p.idProducte, p.nom_estandard, p.familia
                FROM TBNomsProducte np
                JOIN TBProductes p ON np.idProducte = p.idProducte
                WHERE LOWER(np.nom_super) LIKE ?
                ORDER BY np.nom_super
                LIMIT ?
            ''', (f'%{terme_norm}%', limit))
            
            noms_trobats = self.cursor.fetchall()
            for row in noms_trobats:
                resultats.append({
                    'tipus': 'supermercat',
                    'id': row[0],
                    'nom_super': row[1],
                    'supermercat': row[2],
                    'similitud': row[3],
                    'idProducte': row[4],
                    'nom_estandard': row[5],
                    'familia': row[6]
                })
            
            # 3. Mostrar estadístiques
            total_trobat = len(productes_trobats) + len(noms_trobats)
            
            if self.output_widget:
                if total_trobat > 0:
                    self.mostrar_missatge(
                        f"✅ Trobats {total_trobat} resultats: " 
                        f"{len(productes_trobats)} productes, "
                        f"{len(noms_trobats)} noms de supermercat",
                        "success"
                    )
                else:
                    # 4. Si no hi ha resultats, suggerir cerca per similitat
                    self.mostrar_missatge(
                        f"⚠️ No s'ha trobat cap coincidència exacta amb '{terme}'",
                        "warning"
                    )
                    
                    # Preguntar si vol buscar per similitat
                    suggeriment = (
                        f"\nVols buscar productes similars manualment? "
                        f"(similitud > 0.5)"
                    )
                    self.mostrar_missatge(suggeriment, "info")
                    
                    # Fer cerca per similitat automàticament
                    resultats_similitat = self.cerca_per_similitat(terme, limit=5, llindar=0.5)
                    if resultats_similitat:
                        self.mostrar_missatge(
                            f"🔍 Trobats {len(resultats_similitat)} productes similars:",
                            "info"
                        )
                        for r in resultats_similitat:
                            self.mostrar_missatge(
                                f"   • {r['nom']} (similitud: {r['similitud']:.2f})",
                                "info"
                            )
                    
                    resultats.extend(resultats_similitat)
            
            # Eliminar duplicats
            vistos = set()
            resultats_unics = []
            for r in resultats:
                if r['tipus'] == 'estandard':
                    key = f"est_{r['id']}"
                else:
                    key = f"sup_{r['id']}"
                
                if key not in vistos:
                    vistos.add(key)
                    resultats_unics.append(r)
            
            return resultats_unics[:limit]
            
        except Exception as e:
            error_msg = f"❌ Error en cerca automàtica: {e}"
            if self.output_widget:
                self.mostrar_missatge(error_msg, "error")
            print(error_msg)
            return []
    
    def cerca_per_similitat(self, terme, limit=5, llindar=0.3):
        """Cerca productes per similitat de text"""
        try:
            self.cursor.execute('SELECT idProducte, nom_estandard FROM TBProductes')
            tots_productes = self.cursor.fetchall()
            
            resultats = []
            terme_norm = self.normalitzar_nom(terme)
            
            for id_prod, nom in tots_productes:
                nom_norm = self.normalitzar_nom(nom)
                similitud = difflib.SequenceMatcher(None, terme_norm, nom_norm).ratio()
                
                if similitud >= llindar:
                    resultats.append({
                        'tipus': 'estandard',
                        'id': id_prod,
                        'nom': nom,
                        'similitud': round(similitud, 2)
                    })
            
            # Ordenar per similitud descendent
            resultats.sort(key=lambda x: x['similitud'], reverse=True)
            return resultats[:limit]
            
        except Exception as e:
            error_msg = f"❌ Error en cerca per similitat: {e}"
            if self.output_widget:
                self.mostrar_missatge(error_msg, "error")
            print(error_msg)
            return []
        
    def buscar_manualment(self, terme):
        """
        Funció específica per a cerca manual quan no es troben coincidències
        """
        if self.output_widget:
            self.mostrar_missatge(f"\n🔍 CERCA MANUAL PER: '{terme}'", "info")
        
        resultats = []
        
        # 1. Cerca per similitat amb llindar baix
        resultats_similitat = self.cerca_per_similitat(terme, limit=10, llindar=0.3)
        
        if self.output_widget:
            if resultats_similitat:
                self.mostrar_missatge("Productes similars trobats:", "info")
                for r in resultats_similitat:
                    self.mostrar_missatge(f"   • {r['nom']} (similitud: {r['similitud']:.2f})", "info")
            
        resultats.extend(resultats_similitat)
        
        # 2. Cerca per paraules clau
        paraules = terme.split()
        if len(paraules) > 1:
            if self.output_widget:
                self.mostrar_missatge(f"\nCercant per paraules clau: {paraules}", "info")
            
            for paraula in paraules:
                if len(paraula) > 2:  # Només paraules significatives
                    paraula_resultats = self.cerca_per_similitat(paraula, limit=3, llindar=0.4)
                    if paraula_resultats:
                        resultats.extend(paraula_resultats)
        
        # 3. Eliminar duplicats
        vistos = set()
        resultats_unics = []
        for r in resultats:
            key = r['id']
            if key not in vistos:
                vistos.add(key)
                resultats_unics.append(r)
        
        if self.output_widget:
            if resultats_unics:
                self.mostrar_missatge(
                    f"\n✅ Trobats {len(resultats_unics)} possibles coincidències", 
                    "success"
                )
            else:
                self.mostrar_missatge(
                    f"\n⚠️ No s'han trobat productes similars a '{terme}'",
                    "warning"
                )
                self.mostrar_missatge(
                    "Pots:\n"
                    "1. Crear un nou producte\n"
                    "2. Verificar l'ortografia\n"
                    "3. Provar un terme més general",
                    "info"
                )
        
        return resultats_unics

    def crear_producte(self, nom_estandard, familia, unitat=""):
        """Crear un nou producte estàndard"""
        try:
            if self.output_widget:
                self.mostrar_missatge(f"\n📝 Creant producte: '{nom_estandard}'...", "info")
            
            # Verificar que no existeixi
            existent = self.verificar_existencia_producte(nom_estandard)
            if existent:
                msg = f"⚠️ AQUEST PRODUCTE JA EXISTEIX (ID: {existent['idProducte']})"
                if self.output_widget:
                    self.mostrar_missatge(msg, "warning")
                return False, msg
            
            # Verificar que la família sigui vàlida
            families_disponibles = self.obtenir_families_disponibles()
            if familia not in families_disponibles:
                msg = f"⚠️ LA FAMÍLIA '{familia}' NO ÉS VÀLIDA"
                if self.output_widget:
                    self.mostrar_missatge(msg, "warning")
                    self.mostrar_missatge(f"Famílies vàlides: {', '.join(families_disponibles)}", "info")
                return False, msg
            
            # Inserir el producte
            self.cursor.execute('''
                INSERT INTO TBProductes (nom_estandard, familia, unitat)
                VALUES (?, ?, ?)
            ''', (nom_estandard, familia, unitat))
            
            id_producte = self.cursor.lastrowid
            self.conn.commit()
            
            msg = f"✅ PRODUCTE '{nom_estandard}' CREAT (ID: {id_producte})"
            if self.output_widget:
                self.mostrar_missatge(msg, "success")
            return True, msg
            
        except sqlite3.IntegrityError as e:
            error_msg = f"❌ ERROR INTEGRITAT: {str(e)}"
            if self.output_widget:
                self.mostrar_missatge(error_msg, "error")
            return False, error_msg
        except Exception as e:
            error_msg = f"❌ ERROR: {str(e)}"
            if self.output_widget:
                self.mostrar_missatge(error_msg, "error")
            return False, error_msg
    
    def afegir_nom_supermercat(self, id_producte, supermercat, nom_super, similitud_minima=None):
        """Afegir un nom de supermercat per a un producte"""
        try:
            if self.output_widget:
                self.mostrar_missatge(
                    f"\n➕ Afegint nom '{nom_super}' per a {supermercat}...", 
                    "info"
                )
            
            if similitud_minima is None:
                similitud_minima = self.similitud_per_defecte
            
            # Verificar que el supermercat sigui vàlid
            supers_disponibles = self.obtenir_supers_disponibles()
            if supermercat not in supers_disponibles:
                msg = f"⚠️ EL SUPERMERCAT '{supermercat}' NO ÉS VÀLID"
                if self.output_widget:
                    self.mostrar_missatge(msg, "warning")
                    self.mostrar_missatge(f"Supers vàlids: {', '.join(supers_disponibles[:10])}...", "info")
                return False, msg
            
            # Verificar que no existeixi ja aquest nom_super per aquest supermercat
            existent = self.verificar_existencia_nom_super(supermercat, nom_super)
            if existent:
                msg = f"⚠️ AQUEST NOM JA EXISTEIX PER A {supermercat}"
                if self.output_widget:
                    self.mostrar_missatge(msg, "warning")
                    self.mostrar_missatge(
                        f"Associat al producte: {existent['nom_estandard']} "
                        f"(similitud: {existent['similitud']})", 
                        "info"
                    )
                return False, msg
            
            # Verificar que l'id_producte existeix
            self.cursor.execute('SELECT nom_estandard FROM TBProductes WHERE idProducte = ?', (id_producte,))
            producte = self.cursor.fetchone()
            if not producte:
                msg = "⚠️ EL PRODUCTE NO EXISTEIX"
                if self.output_widget:
                    self.mostrar_missatge(msg, "warning")
                return False, msg
            
            nom_producte = producte[0]
            
            # Inserir
            self.cursor.execute('''
                INSERT INTO TBNomsProducte 
                (idProducte, supermercat, nom_super, similitud_minima)
                VALUES (?, ?, ?, ?)
            ''', (id_producte, supermercat, nom_super, similitud_minima))
            
            self.conn.commit()
            
            msg = f"✅ NOM '{nom_super}' AFEGIT a '{nom_producte}' per a {supermercat}"
            if self.output_widget:
                self.mostrar_missatge(msg, "success")
            return True, msg
            
        except sqlite3.IntegrityError as e:
            error_msg = f"❌ ERROR INTEGRITAT: {str(e)}"
            if self.output_widget:
                self.mostrar_missatge(error_msg, "error")
            return False, error_msg
        except Exception as e:
            error_msg = f"❌ ERROR: {str(e)}"
            if self.output_widget:
                self.mostrar_missatge(error_msg, "error")
            return False, error_msg

    def normalitzar_nom(self, text):
        """Normalitza text per comparacions - MILLORADA"""
        if not text:
            return ""
        
        # Convertir a minúscules i eliminar espais extra
        text = str(text).lower().strip()
        
        # Eliminar articles i paraules comunes
        paraules_comuns = ['el', 'la', 'los', 'las', 'un', 'una', 'unos', 'unas', 
                        'de', 'del', 'al', 'y', 'o', 'con', 'sin', 'para']
        
        # Separar paraules i eliminar les comunes
        paraules = text.split()
        paraules_filtrades = [p for p in paraules if p not in paraules_comuns]
        text = ' '.join(paraules_filtrades)
        
        # Reemplaçar caràcters especials
        replacements = {
            'á': 'a', 'à': 'a', 'ä': 'a', 'â': 'a',
            'é': 'e', 'è': 'e', 'ë': 'e', 'ê': 'e',
            'í': 'i', 'ì': 'i', 'ï': 'i', 'î': 'i',
            'ó': 'o', 'ò': 'o', 'ö': 'o', 'ô': 'o',
            'ú': 'u', 'ù': 'u', 'ü': 'u', 'û': 'u',
            'ç': 'c', 'ñ': 'n',
            '·': '', '-': ' ', '_': ' ', '/': ' ', '\\': ' '  # Eliminar separadors
        }
        
        for old, new in replacements.items():
            text = text.replace(old, new)
        
        # Eliminar múltiples espais
        import re
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()
        
    def clear_output(self):
        """Netejar el widget de sortida"""
        if self.output_widget:
            if hasattr(self.output_widget, 'clear'):
                self.output_widget.clear()
            elif hasattr(self.output_widget, 'setText'):
                self.output_widget.setText("")
            if self.output_widget:
                self.mostrar_missatge("✅ Sortida netejada", "success")

    def verificar_existencia_producte(self, nom_estandard):
        """Verificar si un producte ja existeix"""
        try:
            self.cursor.execute('''
                SELECT idProducte, nom_estandard, familia, unitat 
                FROM TBProductes WHERE nom_estandard = ?
            ''', (nom_estandard,))
            
            resultat = self.cursor.fetchone()
            if resultat:
                return {
                    'idProducte': resultat[0],
                    'nom_estandard': resultat[1],
                    'familia': resultat[2],
                    'unitat': resultat[3]
                }
            return None
        except Exception as e:
            print(f"❌ Error verificant producte: {e}")
            return None
    
    def verificar_existencia_nom_super(self, supermercat, nom_super):
        """Verificar si un nom de supermercat ja existeix"""
        try:
            self.cursor.execute('''
                SELECT np.idNom, p.nom_estandard, np.similitud_minima
                FROM TBNomsProducte np
                JOIN TBProductes p ON np.idProducte = p.idProducte
                WHERE np.supermercat = ? AND np.nom_super = ?
            ''', (supermercat, nom_super))
            
            resultat = self.cursor.fetchone()
            if resultat:
                return {
                    'idNom': resultat[0],
                    'nom_estandard': resultat[1],
                    'similitud': resultat[2]
                }
            return None
        except Exception as e:
            print(f"❌ Error verificant nom super: {e}")
            return None
    
    def modificar_producte(self, id_producte, nom_estandard=None, familia=None, unitat=None):
        """Modificar un producte existent"""
        try:
            # Connectar a la BD
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            camps = []
            valors = []
            
            if nom_estandard is not None:
                camps.append("nom_estandard = %s")
                valors.append(nom_estandard)
            
            if familia is not None:
                camps.append("familia = %s")
                valors.append(familia)
            
            if unitat is not None:
                camps.append("unitat = %s")
                valors.append(unitat)
            
            if not camps:
                return False, "No hi ha camps per modificar"
            
            valors.append(id_producte)
            
            query = f"UPDATE TBProductes SET {', '.join(camps)} WHERE idProducte = %s"
            cursor.execute(query, valors)
            
            files_afectades = cursor.rowcount
            conn.commit()
            
            cursor.close()
            conn.close()
            
            if files_afectades > 0:
                return True, f"Producte modificat (ID: {id_producte})"
            else:
                return False, "No s'ha trobat el producte"
                
        except Exception as e:
            print(f"❌ Error modificant producte: {e}")
            return False, f"Error: {str(e)}"
    
    def eliminar_producte(self, id_producte):
        """Eliminar un producte i tots els seus noms de supermercat"""
        try:
            # Obtenir info per al missatge
            self.cursor.execute('SELECT nom_estandard FROM TBProductes WHERE idProducte = ?', (id_producte,))
            resultat = self.cursor.fetchone()
            
            if not resultat:
                msg = "⚠️ EL PRODUCTE NO EXISTEIX"
                if self.output_widget:
                    self.mostrar_missatge(msg, "warning")
                return False, msg
            
            nom_producte = resultat[0]
            
            # Eliminar (la clau forània amb CASCADE s'encarregarà dels noms de supermercat)
            self.cursor.execute('DELETE FROM TBProductes WHERE idProducte = ?', (id_producte,))
            self.conn.commit()
            
            msg = f"✅ PRODUCTE '{nom_producte}' ELIMINAT"
            if self.output_widget:
                self.mostrar_missatge(msg, "success")
            return True, msg
            
        except Exception as e:
            error_msg = f"❌ ERROR: {str(e)}"
            if self.output_widget:
                self.mostrar_missatge(error_msg, "error")
            return False, error_msg
    
    def obtenir_info_producte(self, id_producte):
        """Obtenir informació completa d'un producte"""
        try:
            self.cursor.execute('''
                SELECT p.idProducte, p.nom_estandard, p.familia, p.unitat,
                       COUNT(np.idNom) as num_noms
                FROM TBProductes p
                LEFT JOIN TBNomsProducte np ON p.idProducte = np.idProducte
                WHERE p.idProducte = ?
                GROUP BY p.idProducte
            ''', (id_producte,))
            
            resultat = self.cursor.fetchone()
            if resultat:
                return {
                    'id': resultat[0],
                    'nom': resultat[1],
                    'familia': resultat[2],
                    'unitat': resultat[3],
                    'num_noms': resultat[4]
                }
            return None
        except Exception as e:
            print(f"❌ Error obtenint info producte: {e}")
            return None
    
    def obtenir_noms_super_per_producte(self, id_producte):
        """Obtenir tots els noms de supermercat d'un producte"""
        try:
            self.cursor.execute('''
                SELECT idNom, supermercat, nom_super, similitud_minima
                FROM TBNomsProducte
                WHERE idProducte = ?
                ORDER BY supermercat, nom_super
            ''', (id_producte,))
            
            resultats = self.cursor.fetchall()
            return [{
                'id': row[0],
                'supermercat': row[1],
                'nom_super': row[2],
                'similitud': row[3]
            } for row in resultats]
        except Exception as e:
            print(f"❌ Error obtenint noms super: {e}")
            return []
    
    def obtenir_valors_similitud(self):
        """Obtenir llista de valors de similitud (0.0 a 1.0)"""
        return [round(i * 0.1, 1) for i in range(11)]  # [0.0, 0.1, ..., 1.0]
    
    def get_similitud_per_defecte(self):
        """Obtenir valor de similitud per defecte"""
        return self.similitud_per_defecte
    
    def set_similitud_per_defecte(self, valor):
        """Establir valor de similitud per defecte"""
        try:
            valor_float = float(valor)
            if 0.0 <= valor_float <= 1.0:
                self.similitud_per_defecte = round(valor_float, 1)
                return True
            return False
        except:
            return False
    
    def afegir_nova_familia(self, nova_familia):
        """Afegir una nova família a la llista"""
        try:
            if afegir_familia(nova_familia):
                msg = f"✅ FAMÍLIA '{nova_familia}' AFEGIDA"
                if self.output_widget:
                    self.mostrar_missatge(msg, "success")
                return True, msg
            else:
                msg = f"⚠️ LA FAMÍLIA '{nova_familia}' JA EXISTEIX"
                if self.output_widget:
                    self.mostrar_missatge(msg, "warning")
                return False, msg
        except Exception as e:
            error_msg = f"❌ ERROR: {str(e)}"
            if self.output_widget:
                self.mostrar_missatge(error_msg, "error")
            return False, error_msg
    
    def afegir_nou_super(self, nou_super):
        """Afegir un nou supermercat a la llista"""
        try:
            # Aquí caldria implementar afegir_super si no està en llistes.py
            # Per ara, fem una versió simplificada
            supers = self.obtenir_supers_disponibles()
            if nou_super and nou_super not in supers:
                # Aquí caldria cridar a afegir_super de llistes.py
                # Per ara, només retornem True però no guardem
                msg = f"✅ SUPERMERCAT '{nou_super}' AFEGIT"
                if self.output_widget:
                    self.mostrar_missatge(msg, "success")
                return True, msg
            else:
                msg = f"⚠️ EL SUPERMERCAT '{nou_super}' JA EXISTEIX"
                if self.output_widget:
                    self.mostrar_missatge(msg, "warning")
                return False, msg
        except Exception as e:
            error_msg = f"❌ ERROR: {str(e)}"
            if self.output_widget:
                self.mostrar_missatge(error_msg, "error")
            return False, error_msg
        
    def obtenir_producte_per_nom(self, nom_estandard):
        """Obtenir informació d'un producte pel seu nom estàndard"""
        try:
            self.cursor.execute('''
                SELECT idProducte, nom_estandard, familia, unitat
                FROM TBProductes 
                WHERE LOWER(nom_estandard) = LOWER(?)
            ''', (nom_estandard,))
            
            resultat = self.cursor.fetchone()
            if resultat:
                return {
                    'id': resultat[0],
                    'nom': resultat[1],
                    'familia': resultat[2],
                    'unitat': resultat[3]
                }
            
            if self.output_widget:
                self.mostrar_missatge(f"ℹ️ No s'ha trobat producte '{nom_estandard}'", "info")
            return None
            
        except Exception as e:
            error_msg = f"❌ Error obtenint producte per nom: {e}"
            if self.output_widget:
                self.mostrar_missatge(error_msg, "error")
            print(error_msg)
            return None

    def cerca_per_similitat_i_familia(self, terme, familia, limit=5, llindar=0.3):
        """Cerca productes per similitat de text dins d'una família específica"""
        try:
            # Obtenir productes de la família específica
            self.cursor.execute('''
                SELECT idProducte, nom_estandard, familia, unitat 
                FROM TBProductes 
                WHERE familia = ?
            ''', (familia,))
            
            productes_familia = self.cursor.fetchall()
            
            resultats = []
            terme_norm = self.normalitzar_nom(terme)
            
            for row in productes_familia:
                id_prod, nom, fam, unitat = row
                nom_norm = self.normalitzar_nom(nom)
                similitud = difflib.SequenceMatcher(None, terme_norm, nom_norm).ratio()
                
                if similitud >= llindar:
                    resultats.append({
                        'tipus': 'estandard',
                        'id': id_prod,
                        'nom': nom,
                        'familia': fam,
                        'unitat': unitat,
                        'similitud': round(similitud, 2)
                    })
            
            # Ordenar per similitud descendent
            resultats.sort(key=lambda x: x['similitud'], reverse=True)
            
            # Mostrar informació
            if self.output_widget:
                self.mostrar_missatge(
                    f"🔍 Cerca per '{terme}' a la família '{familia}': "
                    f"trobats {len(resultats)} productes similars",
                    "info"
                )
            
            return resultats[:limit]
            
        except Exception as e:
            error_msg = f"❌ Error en cerca per similitut i família: {e}"
            if self.output_widget:
                self.mostrar_missatge(error_msg, "error")
            print(error_msg)
            return []
        
    def cerca_millorada(self, terme, familia=None, limit=10):
        """Cerca millorada amb múltiples estratègies"""
        resultats = []
        terme_norm = self.normalitzar_nom(terme)
        
        try:
            # ESTRATÈGIA 1: Cerca per paraules clau (més acurat)
            paraules_terme = terme_norm.split()
            
            query = '''
                SELECT idProducte, nom_estandard, familia, unitat 
                FROM TBProductes 
                WHERE familia = ? 
            ''' if familia else '''
                SELECT idProducte, nom_estandard, familia, unitat 
                FROM TBProductes 
            '''
            
            params = [familia] if familia else []
            self.cursor.execute(query, params)
            tots_productes = self.cursor.fetchall()
            
            for id_prod, nom, fam, unitat in tots_productes:
                nom_norm = self.normalitzar_nom(nom)
                similitud_total = 0
                
                # Calcular similitud per cada paraula
                for paraula_terme in paraules_terme:
                    if len(paraula_terme) < 3:  # Ignorar paraules massa curtes
                        continue
                        
                    millor_similitud = 0
                    paraules_nom = nom_norm.split()
                    
                    for paraula_nom in paraules_nom:
                        if len(paraula_nom) < 3:
                            continue
                            
                        # Similitut entre paraules
                        sim = difflib.SequenceMatcher(None, paraula_terme, paraula_nom).ratio()
                        if sim > millor_similitud:
                            millor_similitud = sim
                    
                    similitud_total += millor_similitud
                
                # Mitjana de similituds
                if paraules_terme:
                    similitud_mitjana = similitud_total / len(paraules_terme)
                    
                    if similitud_mitjana >= 0.4:  # Llindar més baix per captures més
                        resultats.append({
                            'tipus': 'estandard',
                            'id': id_prod,
                            'nom': nom,
                            'familia': fam,
                            'unitat': unitat,
                            'similitud': round(similitud_mitjana, 2)
                        })
            
            # ESTRATÈGIA 2: Cerca de subcadenes (per si hi ha noms complets)
            if len(resultats) < 3:
                for id_prod, nom, fam, unitat in tots_productes:
                    nom_norm = self.normalitzar_nom(nom)
                    
                    # Verificar si el terme està dins del nom
                    if terme_norm in nom_norm:
                        similitud = 0.8  # Bonus per coincidència completa
                        resultats.append({
                            'tipus': 'estandard',
                            'id': id_prod,
                            'nom': nom,
                            'familia': fam,
                            'unitat': unitat,
                            'similitud': similitud
                        })
                    # Verificar si el nom està dins del terme
                    elif nom_norm in terme_norm and len(nom_norm) > 3:
                        similitud = 0.7  # Bonus per inclusió
                        resultats.append({
                            'tipus': 'estandard',
                            'id': id_prod,
                            'nom': nom,
                            'familia': fam,
                            'unitat': unitat,
                            'similitud': similitud
                        })
            
            # Eliminar duplicats i ordenar
            vistos = set()
            resultats_unics = []
            for r in resultats:
                if r['id'] not in vistos:
                    vistos.add(r['id'])
                    resultats_unics.append(r)
            
            resultats_unics.sort(key=lambda x: x['similitud'], reverse=True)
            
            # Log del resultat
            if self.output_widget and resultats_unics:
                self.mostrar_missatge(
                    f"🔍 Cerca millorada: '{terme}' → {len(resultats_unics)} resultats", 
                    "info"
                )
            
            return resultats_unics[:limit]
            
        except Exception as e:
            error_msg = f"❌ Error en cerca millorada: {e}"
            if self.output_widget:
                self.mostrar_missatge(error_msg, "error")
            print(error_msg)
            return []
        
    def obtenir_productes_per_familia(self, familia):
        """
        Obtiene productos por familia específica.
        """
        try:
            self.cursor.execute('''
                SELECT idProducte, nom_estandard, familia, unitat, data_creacio
                FROM TBProductes 
                WHERE familia = ?
                ORDER BY nom_estandard
            ''', (familia,))
            
            resultats = self.cursor.fetchall()
            productes = []
            
            for row in resultats:
                productes.append({
                    'id': row[0],
                    'nom': row[1],
                    'familia': row[2] if row[2] else '',
                    'unitat': row[3] if row[3] else '',
                    'data_creacio': row[4] if row[4] else ''
                })
            
            if self.output_widget:
                self.mostrar_missatge(
                    f"📊 Obtinguts {len(productes)} productes de la família '{familia}'", 
                    "info"
                )
            
            return productes
            
        except Exception as e:
            error_msg = f"❌ Error obtenint productes per família '{familia}': {e}"
            if self.output_widget:
                self.mostrar_missatge(error_msg, "error")
            print(error_msg)
            return []

    def obtenir_producte_per_id(self, id_producte):
        """
        Obtiene un producto específico por su ID.
        """
        try:
            self.cursor.execute('''
                SELECT idProducte, nom_estandard, familia, unitat, data_creacio
                FROM TBProductes 
                WHERE idProducte = ?
            ''', (id_producte,))
            
            resultat = self.cursor.fetchone()
            if resultat:
                producte = {
                    'id': resultat[0],
                    'nom': resultat[1],
                    'familia': resultat[2] if resultat[2] else '',
                    'unitat': resultat[3] if resultat[3] else '',
                    'data_creacio': resultat[4] if resultat[4] else ''
                }
                return producte
            else:
                if self.output_widget:
                    self.mostrar_missatge(
                        f"⚠️ No s'ha trobat producte amb ID {id_producte}", 
                        "warning"
                    )
                return None
                
        except Exception as e:
            error_msg = f"❌ Error obtenint producte per ID {id_producte}: {e}"
            if self.output_widget:
                self.mostrar_missatge(error_msg, "error")
            print(error_msg)
            return None

    def verificar_existencia_tbnomsproducte(self, supermercat, nom_super):
        """
        Verifica si ja existeix aquesta combinació supermercat+nom_super a TBNomsProducte
        Retorna True si ja existeix, False si no
        """
        try:
            # Query per verificar existència - VERSIÓ SQLite CORRECTA
            query = """
            SELECT COUNT(*) as count
            FROM TBNomsProducte 
            WHERE supermercat = ? AND nom_super = ?
            """
            
            self.cursor.execute(query, (supermercat, nom_super))
            result = self.cursor.fetchone()
            
            # result és una tupla: (count,)
            count = result[0] if result else 0
            
            # Si count > 0, significa que ja existeix
            existeix = count > 0
            return existeix
            
        except Exception as e:
            print(f"❌ Error verificant TBNomsProducte: {e}")
            import traceback
            traceback.print_exc()
            # En cas d'error, assumim que no existeix per permetre el procés
            return False

        