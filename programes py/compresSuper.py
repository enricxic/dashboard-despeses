# controllers/compresSuper.py 
import os
import re
import sqlite3
from datetime import datetime
from difflib import SequenceMatcher
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QMessageBox, QTableWidgetItem, QInputDialog, QTableWidget,
                              QWidget, QDialog, QVBoxLayout, QListWidget, QComboBox,
                              QPushButton, QLabel, QHBoxLayout, QSpinBox, 
                              QSplitter, QTextEdit, QGroupBox, QFormLayout)
from PySide6.QtGui import QPixmap
from config.llistes import (obtenir_supers, obtenir_families_compres, obtenir_articles_per_familia,
    obtenir_bancs, obtenir_formes_pago, afegir_super, afegir_familia, afegir_article)

try:
    from controllers.ocr_ticket import OCRProcessor, OCR_AVAILABLE
except ImportError as e:
    print(f"❌ Error important OCR: {e}")
    OCR_AVAILABLE = False

class CompresSuperController:

    def __init__(self, ui_instance, db_path="Bases/BD_CompresSuper.db"):

        # ✅ NOU: Variable per controlar la recursió
        self._bloquejar_events_taula = False
        self._bloquejar_calcul_percentatge = False

        # Determinar si ens passen el UI directe o el QWidget
        if hasattr(ui_instance, 'setupUi'):
            # És un QWidget, necessitem accedir als elements a través d'ell
            self.ui = ui_instance
        else:
            # És l'objecte UI directe
            self.ui = ui_instance
        
        self.db_path = db_path
        self.current_id_despesa = None
        self.current_lines = []
        self.mode_modificacions = False
        # ✅ NOU: Variable per controlar si s'han introduït dades manualment
        self.dades_manual_introduides = False

        # Diagnosticar
        self.diagnosticar_ui()
        
        self.setup_connections()
        self.initialize_data()
        self.configurar_visibilitat_inicial()

        # ✅ Variables per controlar l'estat dels botons OCR
        self._processant_ocr = False
        self._super_original_ocr = ""
            
    def setup_connections(self):
        """Configurar les connexions dels signals i slots"""

        # Diccionari per guardar les connexions
        if not hasattr(self, '_connexions_fetes'):
            self._connexions_fetes = False
        
        # Si ja s'han fet les connexions, no tornar a fer
        if self._connexions_fetes:
            print("⚠️ Les connexions ja estan fetes, no es tornen a crear")
            return
        
        # 🔴 BOTÓ MODIFICACIONS
        if hasattr(self.ui, 'modificacionsPushButton'):
            self.ui.modificacionsPushButton.clicked.connect(self.toggle_modificacions)
            print("✅ Botó modificacions connectat")
        
        # 🔴 BOTÓ OCR
        if hasattr(self.ui, 'ocrPushButton'):
            self.ui.ocrPushButton.clicked.connect(self.escanejar_ticket_directe_wia)
        
        # 🔴 BOTÓ BUSCAR
        if hasattr(self.ui, 'buscarPushButton'):
            self.ui.buscarPushButton.clicked.connect(self.seleccionar_ticket_carpeta)
            
        # 🔴 Connexió per detectar canvis a la taula
        self.ui.llistaProductesTable.itemChanged.connect(self._on_item_table_changed)

        
        # Botons
        self.ui.introLineaPushButton.clicked.connect(self.afegir_linia)
        self.ui.fiTicketPushButton.clicked.connect(self.finalitzar_ticket)
        self.ui.introPushButton.clicked.connect(self.aplicar_descompte)
        self.ui.borrarModificacionsPushButton.clicked.connect(self.borrar_linia)
        self.ui.modificacionsPushButton.clicked.connect(self.modificar_linia)
        self.ui.articleNouPushButton.clicked.connect(self.afegir_article_nou)
        self.ui.tancarPushButton.clicked.connect(self.tancar_formulari)
        
        # Checkbox i botons de visibilitat
        self.ui.envioDespesaCheckBox.toggled.connect(self.toggle_envio_despesa)
        self.ui.modificacionsPushButton.clicked.connect(self.toggle_modificacions)
        
        # Combobox
        self.ui.familiaCombobox.currentTextChanged.connect(self.actualitzar_articles)
        self.ui.superComboBox.currentTextChanged.connect(self.actualitzar_num_despesa)
        
        # LineEdits - Navegació SIMPLIFICADA
        self.ui.quantitatLineEdit.returnPressed.connect(self.focus_preu_unit)
        self.ui.preuUnitLineEdit.returnPressed.connect(self.controlar_focus_des_preu_unit)
        self.ui.percentatgeLineEdit.returnPressed.connect(self.focus_total_des_percentatge)
        self.ui.totalLineaLineEdit.returnPressed.connect(self.calcular_i_afegir)
        self.ui.promocioLineEdit.returnPressed.connect(self.focus_total_linea)
        
        # Solament UN càlcul automàtic
        self.ui.totalLineaLineEdit.editingFinished.connect(self.calcular_si_percentatge_present)

        # Dialog buttons
        self.ui.AceptarButtonBox.accepted.connect(self.guardar_modificacions)
        self.ui.AceptarButtonBox.rejected.connect(self.cancelar_modificacions)

        # ✅ NOU: Botons per afegir elements nous
        self.ui.superComboBox.editTextChanged.connect(self.afegir_super_des_text)
        self.ui.familiaCombobox.editTextChanged.connect(self.afegir_familia_des_text)

        # ✅ NOU: Desactivar OCR quan comenci a introduir dades
        self.ui.quantitatLineEdit.textChanged.connect(self.controlar_estat_ocr)
        self.ui.preuUnitLineEdit.textChanged.connect(self.controlar_estat_ocr)
        self.ui.percentatgeLineEdit.textChanged.connect(self.controlar_estat_ocr)
        self.ui.promocioLineEdit.textChanged.connect(self.controlar_estat_ocr)
        self.ui.totalLineaLineEdit.textChanged.connect(self.controlar_estat_ocr)
        
        # Reactivar OCR quan es netegin els camps
        self.ui.familiaCombobox.currentTextChanged.connect(self.verificar_activacio_ocr)
        self.ui.articleCombobox.currentTextChanged.connect(self.verificar_activacio_ocr)


        # ✅ NOU: Configurar combobox per ignorar Enter
        self.configurar_combobox_teclat()

        # Connectar el canvi de super a l'actualització del botó OCR
        self.ui.superComboBox.currentTextChanged.connect(self.actualitzar_boto_ocr)

        self.ui.percentatgeLineEdit.textChanged.connect(self.calcular_percentatge_en_temps_real)

        # 🔴 VERIFICAR QUE EL BOTÓ ESTÀ CONNECTAT
        if hasattr(self.ui, 'modificacionsPushButton'):
            # Desconnectar per si de cas
            try:
                self.ui.modificacionsPushButton.clicked.disconnect()
            except:
                pass
            # Connectar de nou
            self.ui.modificacionsPushButton.clicked.connect(self.toggle_modificacions)
            print("✅ Botó modificacions connectat")

        # Marcar que ja estan fetes
        self._connexions_fetes = True
        print("✅ Totes les connexions establertes")

    def calcular_si_percentatge_present(self):
        """Calcular només si hi ha percentatge i total"""
        if (self.ui.percentatgeLineEdit.text().strip() and 
            self.ui.totalLineaLineEdit.text().strip()):
            self.calcular_percentatge_simple()

    def configurar_visibilitat_inicial(self):
        """Configurar la visibilitat inicial dels elements"""
        
        # Elements relacionats amb envio a despesa - INVISIBLES inicialment
        self.ui.etiqBanc.setVisible(False)
        self.ui.etiqFPago.setVisible(False)
        self.ui.bancComboBox.setVisible(False)
        self.ui.formaPagoComboBox.setVisible(False)
        
        # Elements de modificacions - INVISIBLES inicialment
        self.ui.borrarModificacionsPushButton.setVisible(False)
        self.ui.etiqNumLinea.setVisible(False)
        self.ui.numLineaLineEdit.setVisible(False)
        self.ui.AceptarButtonBox.setVisible(False)
        
        # Desactivar elements fins que hi hagi línies
        self.ui.modificacionsPushButton.setEnabled(False)
        self.ui.descompteLineEdit.setEnabled(False)
        self.ui.introPushButton.setEnabled(False)
        self.ui.fiTicketPushButton.setEnabled(False)
        
        # Text inicial del botó de modificacions
        self.ui.modificacionsPushButton.setText("Modificacions")
        self.mode_modificacions = False
        
        # Deixar combobox buits
        self.ui.bancComboBox.setCurrentIndex(-1)
        self.ui.formaPagoComboBox.setCurrentIndex(-1)
        self.ui.superComboBox.setCurrentIndex(-1)
        self.ui.familiaCombobox.setCurrentIndex(-1)
        self.ui.articleCombobox.setCurrentIndex(-1)

        # ✅ BOTÓ OCR - PER ESCANEJAR DIRECTAMENT
        if hasattr(self.ui, 'ocrPushButton'):
            self.ui.ocrPushButton.setVisible(True)
            self.ui.ocrPushButton.setEnabled(False)            
            self.ui.ocrPushButton.setToolTip("Escanejar un ticket directament des de l'escàner")
        else:
            print("❌ ERROR: ocrPushButton no existeix al UI")

        # ✅ BOTÓ BUSCAR - PER SELECCIONAR FITXER DE LA CARPETA PREDETERMINADA
        if hasattr(self.ui, 'buscarPushButton'):
            self.ui.buscarPushButton.setVisible(True)
            self.ui.buscarPushButton.setEnabled(False)
            self.ui.buscarPushButton.setToolTip("Seleccionar un ticket de la carpeta predeterminada")
        else:
            print("❌ ERROR: buscarPushButton no existeix al UI")
        
        # ✅ CONFIGURAR TAULA COM A NO EDITABLE
        self.configurar_taula_lectura(True)

    def activar_ocr_sempre(self):
        """Activar el botó OCR sempre (excepte quan hi ha dades manuals)"""
        if not hasattr(self.ui, 'ocrPushButton'):
            return
        
        # Activar si NO hi ha dades manuals introduïdes
        if not self.dades_manual_introduides:
            self.ui.ocrPushButton.setEnabled(True)
            self.ui.ocrPushButton.setStyleSheet("""
                QPushButton {
                    background-color: #4CAF50;
                    color: white;
                    font-weight: bold;
                    border: 2px solid #45a049;
                    border-radius: 5px;
                    padding: 8px;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background-color: #45a049;
                    border: 2px solid #3d8b40;
                }
            """)
        else:
            # Si hi ha dades manuals, desactivar
            self.ui.ocrPushButton.setEnabled(False)
            self.ui.ocrPushButton.setStyleSheet("""
                QPushButton {
                    background-color: #CCCCCC;
                    color: #666666;
                    border: 2px solid #AAAAAA;
                    border-radius: 5px;
                    padding: 8px;
                    font-size: 12px;
                }
            """)   

    def escanejar_ticket_directe_wia(self):
        """Escanejar utilitzant Windows WIA - VERSIÓ FINAL AMB CONTROL D'ESTAT"""
        from PySide6.QtWidgets import QMessageBox, QFileDialog
        import tempfile
        import os
        import time
        import subprocess
        
        try:
            # 🔴 DESACTIVAR BOTONS OCR DURANT EL PROCÉS
            self._desactivar_botons_ocr_durant_processament()
            
            # Verificar que hi ha un supermercat seleccionat
            if not self.ui.superComboBox.currentText():
                QMessageBox.warning(None, "Error", "Selecciona un supermercat primer")
                self._reactivar_botons_ocr()
                return
            
            # Guardar supermercat actual per verificar després
            super_actual = self.ui.superComboBox.currentText()
            self._super_original_ocr = super_actual
            
            # Crear un fitxer temporal
            temp_dir = tempfile.gettempdir()
            timestamp = int(time.time())
            temp_file = os.path.join(temp_dir, f"ticket_scan_{timestamp}.jpg")
            vbs_file = os.path.join(temp_dir, f"scan_ticket_{timestamp}.vbs")
            
            # Crear un script VBS optimitzat per a WIA
            vbs_content = f'''
    ' Script per escanejar amb WIA - Versió optimitzada
    On Error Resume Next

    Dim oWIA, oImg
    Set oWIA = CreateObject("WIA.CommonDialog")

    If oWIA Is Nothing Then
        WScript.Echo "ERROR: No es pot crear objecte WIA"
        WScript.Quit 1
    End If

    ' Configurar opcions d'escaneig
    ' 0 = WIA_INTENT_NONE, 1 = escàner, 2 = color, 
    ' {{B96B3CAB-0728-11D3-9D7B-0000F81EF32E}} = format JPEG
    Set oImg = oWIA.ShowAcquireImage(0, 1, 2, "{{B96B3CAB-0728-11D3-9D7B-0000F81EF32E}}", False, True)

    If oImg Is Nothing Then
        WScript.Echo "CANCEL·LAT"
        WScript.Quit 0
    End If

    ' Guardar la imatge
    oImg.SaveFile "{temp_file}"

    ' Comprovar que el fitxer s'ha creat
    Dim fso
    Set fso = CreateObject("Scripting.FileSystemObject")
    If fso.FileExists("{temp_file}") Then
        ' Verificar que el fitxer no està buit
        If fso.GetFile("{temp_file}").Size > 0 Then
            WScript.Echo "OK:" & "{temp_file}"
        Else
            WScript.Echo "ERROR: Fitxer buit"
            WScript.Quit 1
        End If
    Else
        WScript.Echo "ERROR: No s'ha pogut guardar el fitxer"
        WScript.Quit 1
    End If
    '''
            
            # 🔴 CANVI IMPORTANT: Usar encoding='ascii' per evitar caràcters estranys
            with open(vbs_file, 'w', encoding='utf-8') as f:
                f.write(vbs_content)
            
            print(f"📝 Script VBS creat: {vbs_file}")
            
            # Executar el script
            result = subprocess.run(
                ["cscript", "//nologo", vbs_file],
                capture_output=True,
                timeout=120
            )
            
            # 🔴 Decodificar manualment ignorant errors
            stdout = result.stdout.decode('latin-1', errors='ignore').strip()
            stderr = result.stderr.decode('latin-1', errors='ignore').strip()
            
            print(f"📤 Sortida VBS: {stdout}")
            if stderr:
                print(f"⚠️ Errors VBS: {stderr}")
            
            # Netejar script temporal
            try:
                os.remove(vbs_file)
            except:
                pass
            
            # Processar resultat
            if stdout.startswith("OK:"):
                # Extreure el nom del fitxer
                file_path = stdout[3:].strip()
                print(f"✅ Imatge escanejada: {file_path}")
                
                if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
                    # Processar la imatge
                    self._processar_amb_ocr_real(file_path)
                    # No reactivar aquí - es farà dins de _processar_amb_ocr_real
                else:
                    print(f"❌ El fitxer no existeix o està buit: {file_path}")
                    QMessageBox.warning(
                        None,
                        "Error",
                        "El fitxer escanejat no és vàlid o està buit."
                    )
                    self._reactivar_botons_ocr()
                    
            elif "CANCEL" in stdout.upper() or "CANCEL" in stderr.upper():
                print("ℹ️ L'usuari ha cancel·lat l'escaneig")
                QMessageBox.information(
                    None,
                    "Escaneig cancel·lat",
                    "Has cancel·lat l'escaneig."
                )
                self._reactivar_botons_ocr()
                
            else:
                print(f"❌ Error inesperat: {stdout}")
                QMessageBox.warning(
                    None,
                    "Error d'escaneig",
                    f"No s'ha pogut completar l'escaneig.\n\n"
                    f"Error: {stdout}\n\n"
                    f"Prova a seleccionar un fitxer manualment."
                )
                
                # Fallback: Oferir seleccionar fitxer
                resposta = QMessageBox.question(
                    None,
                    "Seleccionar fitxer",
                    "Vols seleccionar un fitxer existent?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                
                if resposta == QMessageBox.StandardButton.Yes:
                    file_path, _ = QFileDialog.getOpenFileName(
                        None,
                        "Seleccionar ticket",
                        r"E:\BD_Despeses\assets\tickets",
                        "Imatges (*.png *.jpg *.jpeg)"
                    )
                    
                    if file_path:
                        self._processar_amb_ocr_real(file_path)
                    else:
                        self._reactivar_botons_ocr()
                else:
                    self._reactivar_botons_ocr()
                
        except subprocess.TimeoutExpired:
            print("⏰ Timeout en escaneig")
            QMessageBox.warning(
                None,
                "Timeout",
                "L'escaneig ha trigat massa.\n\n"
                "Prova a seleccionar un fitxer manualment."
            )
            self._reactivar_botons_ocr()
        
        except Exception as e:
            print(f"❌ Error general: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(
                None, 
                "Error", 
                f"Error en escaneig:\n{str(e)}"
            )
            self._reactivar_botons_ocr()

    def seleccionar_ticket_carpeta(self):
        """Seleccionar un ticket de la carpeta predeterminada"""
        from PySide6.QtWidgets import QFileDialog, QMessageBox
        import os
        
        try: 
            # 🔴 DESACTIVAR BOTONS OCR
            # self._desactivar_botons_ocr_durant_processament()
        
            # Verificar que hi ha un supermercat seleccionat
            if not self.ui.superComboBox.currentText():
                QMessageBox.warning(None, "Error", "Selecciona un supermercat primer")
                return
            
            # Guardar super original
            self._super_original_ocr = self.ui.superComboBox.currentText()
            
            # Carpeta predeterminada
            tickets_dir = r"E:\BD_Despeses\assets\tickets"
            
            # Crear el directori si no existeix
            if not os.path.exists(tickets_dir):
                os.makedirs(tickets_dir)
                print(f"📁 Creat directori de tickets: {tickets_dir}")
            
            file_path, _ = QFileDialog.getOpenFileName(
                None,
                "Seleccionar ticket",
                tickets_dir,
                "Imatges (*.png *.jpg *.jpeg *.bmp *.gif)"
            )
            
            if file_path:
                self._processar_amb_ocr_real(file_path)
            else:
                pass
            
        except Exception as e:
            QMessageBox.critical(None, "Error", f"Error seleccionant fitxer: {str(e)}")  
        
    def carregar_combobox(self):
        """Carregar tots els combobox amb les dades de llistes.py"""        
        try:
            # Bancs
            bancs = obtenir_bancs()
            self.ui.bancComboBox.clear()
            self.ui.bancComboBox.addItems(bancs)
            
            # Formes de pagament
            formes_pago = obtenir_formes_pago()
            self.ui.formaPagoComboBox.clear()
            self.ui.formaPagoComboBox.addItems(formes_pago)
            
            # Supermercats
            supers = obtenir_supers()
            self.ui.superComboBox.clear()
            self.ui.superComboBox.addItems(sorted(supers))
            
            # Families
            families = obtenir_families_compres()
            self.ui.familiaCombobox.clear()
            self.ui.familiaCombobox.addItems(sorted(families))
            
            # Articles
            self.actualitzar_articles()
            
        except Exception as e:
            print(f"❌ Error carregant combobox: {e}")
            import traceback
            traceback.print_exc()
            
    def actualitzar_articles(self):
        """Actualitzar els articles segons la família seleccionada"""
        try:
            familia_seleccionada = self.ui.familiaCombobox.currentText()
            
            # Si no hi ha família seleccionada, deixar buit
            if not familia_seleccionada:
                self.ui.articleCombobox.clear()
                self.ui.articleCombobox.setCurrentIndex(-1)
                return
            
            articles = obtenir_articles_per_familia(familia_seleccionada)

            self.ui.articleCombobox.clear()
            if articles:
                self.ui.articleCombobox.addItems(articles)
                self.ui.articleCombobox.setCurrentIndex(-1)  # Buit
            else:
                print(f"⚠️ No s'han trobat articles per la família: '{familia_seleccionada}'")
                self.ui.articleCombobox.setCurrentIndex(-1)  # Buit
                    
        except Exception as e:
            print(f"❌ Error actualitzant articles: {e}")
            import traceback
            traceback.print_exc()
                  
    def actualitzar_num_despesa(self):
        """Actualitzar el número de despesa (auto-increment)"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT MAX(idDespesa) FROM TBCompresSuper")
            result = cursor.fetchone()
            conn.close()
            
            self.current_id_despesa = (result[0] or 0) + 1
            self.ui.numDespesaLabel.setText(str(self.current_id_despesa))
        except Exception as e:
            print(f"❌ Error actualitzant ID Despesa: {e}")
            self.current_id_despesa = 1
            self.ui.numDespesaLabel.setText("1")
            
    def obtenir_ultim_id_despesa(self, supermercado):
        """Obtenir l'últim ID de despesa per a un supermercat"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                "SELECT MAX(idDespesa) FROM TBCompresSuper WHERE super = ?", 
                (supermercado,)
            )
            result = cursor.fetchone()
            conn.close()
            return result[0] if result[0] is not None else 0
        except Exception as e:
            print(f"Error obtenint últim ID de despesa: {e}")
            return 0
            
    def inicialitzar_taula(self):
        """Inicialitzar la taula de productes"""
        headers = ["Família", "Article", "Pes", "Quant", 
                "Preu Unit", "%", "Promo", "Total", "Rebost"]  # Canviat "% Descompte" per "%" per estalviar espai
        self.ui.llistaProductesTable.setColumnCount(len(headers))
        self.ui.llistaProductesTable.setHorizontalHeaderLabels(headers)
        
        # 🔴 AJUSTAR AMPLADES DE LES COLUMNES
        self.ui.llistaProductesTable.setColumnWidth(0, 110)  # Família
        self.ui.llistaProductesTable.setColumnWidth(1, 180)  # Article
        self.ui.llistaProductesTable.setColumnWidth(2, 135)   # Pes
        self.ui.llistaProductesTable.setColumnWidth(3, 60)   # Quantitat
        self.ui.llistaProductesTable.setColumnWidth(4, 75)   # Preu Unit
        self.ui.llistaProductesTable.setColumnWidth(5, 35)   # % (petita)
        self.ui.llistaProductesTable.setColumnWidth(6, 70)   # Promo
        self.ui.llistaProductesTable.setColumnWidth(7, 95)   # Total
        self.ui.llistaProductesTable.setColumnWidth(8, 40)   # Rebost
        
        self.ui.llistaProductesTable.setRowCount(0)
        
        # CONFIGURAR TAULA COM A NO EDITABLE
        self.configurar_taula_lectura(True)
        
    def calcular_total_linia(self):
        """Calcular el total de la línia actual"""
        try:
            quantitat_text = self.ui.quantitatLineEdit.text().replace(',', '.')
            preu_unit_text = self.ui.preuUnitLineEdit.text().replace(',', '.')
            promocio_text = self.ui.promocioLineEdit.text().replace(',', '.')
            
            quantitat = float(quantitat_text or 0)
            preu_unit = float(preu_unit_text or 0)
            promocio = float(promocio_text or 0)
            
            # Total sense promoció
            total_base = quantitat * preu_unit
            
            # Si hi ha percentatge però no promoció, calcular promoció
            if self.ui.percentatgeLineEdit.text().strip() and promocio == 0:
                percentatge_text = self.ui.percentatgeLineEdit.text().replace(',', '.')
                try:
                    percentatge = float(percentatge_text) / 100
                    promocio = total_base * percentatge
                    self.ui.promocioLineEdit.setText(f"{promocio:.2f}".replace('.', ','))
                except ValueError:
                    pass
            
            # Total final
            total = total_base - promocio
            self.ui.totalLineaLineEdit.setText(f"{total:.2f}".replace('.', ','))
            
        except ValueError:
            self.ui.totalLineaLineEdit.setText("0,00")
            print("⚠️ Error en càlcul de total")
            
    def afegir_linia(self):
        """Afegir una nova línia al ticket"""
        # 🔴 Validar sense mostrar missatge (ja ho fem nosaltres)
        if not self.validar_camps_linia(mostrar_missatge=False):
            print("❌ Validació fallida")
            return
        
        if not self.validar_camps_linia():
            print("❌ Validació fallida")
            return
            
        try:
            # Obtenir valors dels camps
            familia = self.ui.familiaCombobox.currentText()
            article = self.ui.articleCombobox.currentText()
            pes = self.ui.pesLineEdit.text()
            
            # Convertir valors numèrics
            quantitat_text = self.ui.quantitatLineEdit.text().replace(',', '.')
            preu_unit_text = self.ui.preuUnitLineEdit.text().replace(',', '.')
            percentatge_text = self.ui.percentatgeLineEdit.text().replace(',', '.')
            promocio_text = self.ui.promocioLineEdit.text().replace(',', '.')
            total_linea_text = self.ui.totalLineaLineEdit.text().replace(',', '.')
            
            quantitat = float(quantitat_text or 0)
            preu_unit = float(preu_unit_text or 0)
            percentatge = int(float(percentatge_text or 0))
            promocio = float(promocio_text or 0)
            total_linea = float(total_linea_text or 0)
            
            rebost = "Sí" if self.ui.rebostCheckBox.isChecked() else "No"
            
            # Afegir fila a la taula
            row_position = self.ui.llistaProductesTable.rowCount()
            self.ui.llistaProductesTable.insertRow(row_position)
            
            # Afegir dades a la taula
            self.ui.llistaProductesTable.setItem(row_position, 0, QTableWidgetItem(familia))
            self.ui.llistaProductesTable.setItem(row_position, 1, QTableWidgetItem(article))
            self.ui.llistaProductesTable.setItem(row_position, 2, QTableWidgetItem(pes))
            self.ui.llistaProductesTable.setItem(row_position, 3, QTableWidgetItem(str(quantitat)))
            self.ui.llistaProductesTable.setItem(row_position, 4, QTableWidgetItem(f"{preu_unit:.2f}".replace('.', ',')))
            self.ui.llistaProductesTable.setItem(row_position, 5, QTableWidgetItem(str(percentatge)))
            self.ui.llistaProductesTable.setItem(row_position, 6, QTableWidgetItem(f"{promocio:.2f}".replace('.', ',')))
            self.ui.llistaProductesTable.setItem(row_position, 7, QTableWidgetItem(f"{total_linea:.2f}".replace('.', ',')))
            self.ui.llistaProductesTable.setItem(row_position, 8, QTableWidgetItem(rebost))
            
            # Guardar dades a la llista interna
            linea_data = {
                'familia': familia,
                'article': article,
                'pes': pes,
                'quantitat': quantitat,
                'preuUnit': preu_unit,
                'percentatge': percentatge,
                'prom': promocio,
                'totLinea': total_linea,
                'rebost': rebost
            }
            self.current_lines.append(linea_data)
            
            # ✅ MARCADOR PERMANENT: S'han introduït dades manualment
            self.dades_manual_introduides = True
            
            # Actualitzar resums
            self.actualitzar_desglossament()
            self.actualitzar_total_ticket()
            
            # ✅ Netejar camps INCLOENT combobox
            self.netejar_camps_linia()
            
            # ✅ Desactivar OCR permanentment
            if hasattr(self.ui, 'ocrPushButton'):
                if self.ui.ocrPushButton.isEnabled():
                    print("🔒 Desactivant OCR permanentment - s'ha afegit línia manual")
                    self.desactivar_ocr_permanent()
            
            # Activar elements quan s'afegeix la primera línia
            if len(self.current_lines) == 1:
                self.activar_elements_ticket()
                
        except ValueError as e:
            print(f"❌ Error en conversió numèrica: {e}")
            QMessageBox.warning(None, "Error numèric", 
                            "Revisa els formats dels números (usa coma decimal)")
        except Exception as e:
            print(f"❌ Error afegint línia: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.warning(None, "Error", f"Error afegint línia: {str(e)}")

    def validar_camps_linia(self, mostrar_missatge=True):
        """Validar els camps obligatoris per a una línia"""
        if not self.ui.familiaCombobox.currentText():
            if mostrar_missatge:
                QMessageBox.warning(None, "Error", "Selecciona una família")
            return False
            
        if not self.ui.articleCombobox.currentText():
            if mostrar_missatge:
                QMessageBox.warning(None, "Error", "Selecciona un article")
            return False
            
        if not self.ui.quantitatLineEdit.text():
            if mostrar_missatge:
                QMessageBox.warning(None, "Error", "Introdueix la quantitat")
            return False
            
        if not self.ui.preuUnitLineEdit.text():
            if mostrar_missatge:
                QMessageBox.warning(None, "Error", "Introdueix el preu unitari")
            return False
            
        return True
        
    def netejar_camps_linia(self):
        """Netejar els camps de la línia actual"""
        print("🧹 Netejant camps de línia...")
        
        # Netejar LineEdits
        line_edits = [
            self.ui.pesLineEdit,
            self.ui.quantitatLineEdit,
            self.ui.preuUnitLineEdit,
            self.ui.promocioLineEdit,
            self.ui.percentatgeLineEdit,
            self.ui.totalLineaLineEdit,
        ]
        
        for camp in line_edits:
            camp.clear()
        
        # ✅ Netejar combobox (CRÍTIC)
        self.ui.familiaCombobox.setCurrentIndex(-1)
        self.ui.articleCombobox.setCurrentIndex(-1)
        self.ui.articleCombobox.clear()  # Netejar també els ítems
        
        # Netejar checkbox
        self.ui.rebostCheckBox.setChecked(False)
        
        # Verificar si es pot reactivar OCR (només si no hi ha dades manual introduïdes)
        if not self.dades_manual_introduides:
            self.verificar_activacio_ocr()
        
        # Focus a família per començar la següent línia
        self.ui.familiaCombobox.setFocus()
        
    def actualitzar_total_ticket(self):
        """Actualitzar el total del ticket"""
        total = sum(linea['totLinea'] for linea in self.current_lines)
        self.ui.totalTicketLabel.setText(f"{total:.2f} €".replace('.', ','))
        self.actualitzar_desglossament()

    def actualitzar_desglossament(self):
        """Actualitzar el desglossament per categories"""
        general = 0
        rebost = 0
        neteja = 0
        
        for linea in self.current_lines:
            if linea['rebost'] == 'Sí':
                rebost += linea['totLinea']
            elif linea['familia'].lower() == 'neteja':
                neteja += linea['totLinea']
            else:
                general += linea['totLinea']
        
        self.ui.desglosLabel.setText(f"G: {general:.2f} | R: {rebost:.2f} | N: {neteja:.2f}".replace('.', ','))
        
    def toggle_envio_despesa(self, checked):
        """Mostrar/ocultar elements d'envio a despesa"""
        
        self.ui.etiqBanc.setVisible(checked)
        self.ui.etiqFPago.setVisible(checked)
        self.ui.bancComboBox.setVisible(checked)
        self.ui.formaPagoComboBox.setVisible(checked)
        
        # Si s'activa, focus al banc
        if checked:
            self.ui.bancComboBox.setFocus()
        
    def toggle_modificacions(self):
        """Activar/desactivar mode modificacions - VERSIÓ SIMPLE"""
        print(f"🔘 toggle_modificacions cridat. Mode actual: {self.mode_modificacions}")
        
        if not self.mode_modificacions:
            # ACTIVAR mode modificacions
            self.mode_modificacions = True
            self.ui.modificacionsPushButton.setText("Tancar Modificacions")
            self.ui.borrarModificacionsPushButton.setVisible(True)
            self.ui.etiqNumLinea.setVisible(True)
            self.ui.numLineaLineEdit.setVisible(True)
            self.ui.AceptarButtonBox.setVisible(True)

            # 🔴🔴🔴 DESACTIVAR BOTÓ FINALITZAR
            self.ui.fiTicketPushButton.setEnabled(False)
            
            # Configurar taula editable
            self.ui.llistaProductesTable.setEditTriggers(
                QTableWidget.EditTrigger.DoubleClicked |
                QTableWidget.EditTrigger.EditKeyPressed |
                QTableWidget.EditTrigger.SelectedClicked
            )
            
            print("✅ Mode modificacions ACTIVAT")
            
        else:
            # DESACTIVAR mode modificacions - PREGUNTAR
            resposta = QMessageBox.question(
                None, 
                "Sortir de modificacions", 
                "Vols guardar els canvis abans de sortir?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel
            )
            
            if resposta == QMessageBox.StandardButton.Yes:
                # Guardar canvis
                self.guardar_tots_canvis_taula()
                self._desactivar_mode_modificacions()
                 # 🔴🔴🔴 REACTIVAR BOTÓ FINALITZAR
                self.ui.fiTicketPushButton.setEnabled(True)           
                print("✅ Canvis guardats, mode desactivat")
                
            elif resposta == QMessageBox.StandardButton.No:
                # No guardar
                self.descartar_canvis_taula()
                self._desactivar_mode_modificacions()
                print("🔄 Canvis descartats, mode desactivat")
                
            else:  # Cancel
                print("⏸️ Cancel·lat, es manté en mode modificacions")

    def sortir_mode_modificacions(self):
        """Sortir del mode modificacions (neteja la interfície)"""
        self.mode_modificacions = False
        self.ui.modificacionsPushButton.setText("Modificacions")
        self.ui.borrarModificacionsPushButton.setVisible(False)
        self.ui.etiqNumLinea.setVisible(False)
        self.ui.numLineaLineEdit.setVisible(False)
        self.ui.AceptarButtonBox.setVisible(False)
        
        # Restaurar estil
        self.ui.modificacionsPushButton.setStyleSheet("")
        
        # Tornar a fer la taula no editable
        self.configurar_taula_lectura(True)
        
        # 🔴 NETEJAR SELECCIÓ (però no cal netejar camps perquè no els hem tocat)
        self.ui.llistaProductesTable.clearSelection()
        
        print("✅ Mode modificacions tancat")

    def _configurar_columnes_editables(self):
        """Configurar quines columnes de la taula són editables en mode modificacions"""
        
        # Índexs de les columnes (segons el teu header)
        # 0: Família, 1: Article, 2: Pes, 3: Quantitat, 4: Preu Unit, 5: % Descompte, 6: Promo, 7: Total, 8: Rebost
        
        # Primer, permetre edició a la taula
        self.ui.llistaProductesTable.setEditTriggers(
            QTableWidget.EditTrigger.DoubleClicked |
            QTableWidget.EditTrigger.EditKeyPressed |
            QTableWidget.EditTrigger.SelectedClicked
        )
        
        # Columnes que NO volem que siguin editables
        columnes_no_editables = [7]  #  Total
        
        # Configurar cada columna
        for col in range(self.ui.llistaProductesTable.columnCount()):
            for row in range(self.ui.llistaProductesTable.rowCount()):
                item = self.ui.llistaProductesTable.item(row, col)
                if item:
                    if col in columnes_no_editables:
                        # Aquestes columnes no es poden editar
                        item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                    else:
                        # Aquestes columnes SÍ es poden editar (Pes, Quantitat, Preu Unit, Promo, Rebost)
                        item.setFlags(item.flags() | Qt.ItemIsEditable)
        
        # Tractament especial per la columna Rebost (CheckBox)
        # La columna 7 (Rebost) és un checkbox, ja és editable per naturalesa
            
    def borrar_linia(self):
        """Borrar la línia seleccionada de la taula"""
        if not self.mode_modificacions:
            QMessageBox.warning(None, "Mode Modificacions", 
                            "Activa el mode modificacions per borrar línies")
            return
            
        current_row = self.ui.llistaProductesTable.currentRow()
        if current_row >= 0:
            if current_row < len(self.current_lines):
                self.current_lines.pop(current_row)
            self.ui.llistaProductesTable.removeRow(current_row)
            self.actualitzar_desglossament()
            self.actualitzar_total_ticket()
            
            # Si no queden línies, desactivar elements
            if len(self.current_lines) == 0:
                self.ui.modificacionsPushButton.setEnabled(False)
                self.ui.descompteLineEdit.setEnabled(False)
                self.ui.introPushButton.setEnabled(False)
                self.ui.fiTicketPushButton.setEnabled(False)
        else:
            QMessageBox.warning(None, "Selecció", 
                            "Selecciona una línia per borrar")
            
    def modificar_linia(self):
        """Seleccionar una línia per modificar-la directament a la taula"""
        if not self.mode_modificacions:
            QMessageBox.warning(None, "Mode Modificacions", 
                            "Activa el mode modificacions per modificar línies")
            return
            
        current_row = self.ui.llistaProductesTable.currentRow()
        if current_row >= 0 and current_row < len(self.current_lines):
            # Simplement seleccionar la fila
            self.ui.llistaProductesTable.selectRow(current_row)
            self.ui.llistaProductesTable.setCurrentCell(current_row, 3)
            self.ui.llistaProductesTable.editItem(self.ui.llistaProductesTable.item(current_row, 3))
            
            # 🔴 ELIMINAR AQUESTA LÍNIA:
            # if self.carregar_linia_a_camps(current_row):
            
            print(f"✅ Línia {current_row} seleccionada per editar directament a la taula")
        else:
            QMessageBox.warning(None, "Selecció", 
                            "Selecciona una línia per modificar")
            
    def aplicar_descompte(self):
        """Aplicar descompte al ticket"""
        try:
            descompte_text = self.ui.descompteLineEdit.text().replace(',', '.')
            descompte = float(descompte_text or 0)
            
            if descompte > 0:
                total_actual = sum(linea['totLinea'] for linea in self.current_lines)
                
                if total_actual > 0:
                    factor_descompte = 1 - (descompte / total_actual)
                    
                    for i, linea in enumerate(self.current_lines):
                        linea['totLinea'] *= factor_descompte
                        self.ui.llistaProductesTable.item(i, 6).setText(f"{linea['totLinea']:.2f}".replace('.', ','))
                        
                    self.actualitzar_desglossament()
                    self.actualitzar_total_ticket()
                    self.ui.descompteLineEdit.clear()
                else:
                    QMessageBox.warning(None, "Error", "No hi ha total per aplicar descompte")
                    
        except ValueError:
            QMessageBox.warning(None, "Error", "Descompte no vàlid")
            
    def afegir_article_nou(self):
        """Afegir un nou article a la llista"""
        article, ok = QInputDialog.getText(
            None, "Nou Article", "Introdueix el nom del nou article:"
        )
        
        if ok and article:
            familia_actual = self.ui.familiaCombobox.currentText()
            
            if not familia_actual:
                QMessageBox.warning(None, "Error", "Selecciona una família primer")
                return
                
            # Afegir a llistes.py
            if afegir_article(familia_actual, article):
                QMessageBox.information(None, "Èxit", f"Article '{article}' afegit a '{familia_actual}'")
                self.actualitzar_articles()
                self.ui.articleCombobox.setCurrentText(article)
            else:
                QMessageBox.warning(None, "Error", "No s'ha pogut afegir l'article (potser ja existeix)")
                
    def finalitzar_ticket(self):
        """Finalitzar el ticket i guardar a la base de dades"""
        if not self.current_lines:
            QMessageBox.warning(None, "Error", "No hi ha línies al ticket")
            return
            
        if not self.validar_capsalera():
            return
            
        try:
            self.guardar_ticket_bd()
            QMessageBox.information(None, "Èxit", "Ticket guardat correctament")
            self.reiniciar_formulari()
            
        except Exception as e:
            QMessageBox.critical(None, "Error", f"Error guardant el ticket: {str(e)}")
            
    def validar_capsalera(self):
        """Validar els camps del capçalera del ticket"""
        if not self.ui.dataLineEdit.text():
            QMessageBox.warning(None, "Error", "Introdueix la data")
            return False
            
        if not self.ui.superComboBox.currentText():
            QMessageBox.warning(None, "Error", "Selecciona un supermercat")
            return False
            
        if not self.ui.bancComboBox.currentText():
            QMessageBox.warning(None, "Error", "Selecciona un banc")
            return False
            
        return True
        
    def guardar_ticket_bd(self):
        """Guardar el ticket complet a la base de dades i també a despeses generals"""
        
        conn_compres = sqlite3.connect(self.db_path)
        cursor_compres = conn_compres.cursor()
        
        # 🔴🔴🔴 Connexió a la BD de despeses generals
        db_despeses_path = "Bases/BD_Despesa_General.db"  
        conn_despeses = sqlite3.connect(db_despeses_path)
        cursor_despeses = conn_despeses.cursor()
        
        try:
            data = self.ui.dataLineEdit.text()
            mes = datetime.strptime(data, "%d/%m/%Y").month
            any = datetime.strptime(data, "%d/%m/%Y").year
            super = self.ui.superComboBox.currentText()
            banc = self.ui.bancComboBox.currentText()
            forma_pago = self.ui.formaPagoComboBox.currentText()
            
            # 🔴🔴🔴 Calcular totals per categoria
            total_menjar = 0
            total_rebost = 0
            total_neteja = 0
            
            for linea in self.current_lines:
                if linea['rebost'] == 'Sí':
                    total_rebost += linea['totLinea']
                elif linea['familia'].lower() == 'neteja':
                    total_neteja += linea['totLinea']
                else:
                    total_menjar += linea['totLinea']
            
            print(f"📊 Desglossament: Menjar={total_menjar:.2f}€, Rebost={total_rebost:.2f}€, Neteja={total_neteja:.2f}€")
            
            # 1️⃣ Guardar a TBCompresSuper (detall)
            ids_compres = []
            for i, linea in enumerate(self.current_lines):
                preu_original = linea.get('preu_original', linea['preuUnit'])
                descompte = linea.get('prom', 0)
                percentatge = linea.get('percentatge', 0)
                preu_final = linea['totLinea']
                quantitat = linea['quantitat']
                
                # Verificació
                preu_calculat = (quantitat * preu_original) - descompte
                if abs(preu_calculat - preu_final) > 0.01:
                    print(f"⚠️ Inconsistència en línia {i}: {preu_final} vs {preu_calculat}")
                    preu_final = preu_calculat
                
                cursor_compres.execute('''
                    INSERT INTO TBCompresSuper (
                        data, mes, any, super, familia, article, pes, quantitat,
                        preuUnit, percentatge, prom, totLinea, idDespesa, descompte, rebost
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    data, mes, any, super, 
                    linea['familia'], 
                    linea['article'],
                    linea['pes'], 
                    quantitat,
                    preu_original,
                    percentatge,
                    descompte,
                    preu_final,
                    self.current_id_despesa,
                    0,
                    linea['rebost']
                ))
                
                id_compra = cursor_compres.lastrowid
                ids_compres.append(id_compra)
            
            # 2️⃣ 🔴🔴🔴 Guardar a TbDespeses (un registre per categoria)
        
            # Registrar MENJAR (General) si té valor
            if total_menjar > 0:
                cursor_despeses.execute('''
                    INSERT INTO TbDespeses (
                        banc, data, mes, any, importCarrec, grup, categoria, concepte, formaPago, comentari
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    banc,
                    data,
                    mes,
                    any,
                    total_menjar,
                    "Càrrec",
                    "menjar",
                    super,
                    forma_pago,
                    ""  # comentari buit
                ))
                print(f"✅ Despesa MENJAR: {total_menjar:.2f}€")
            
            # Registrar REBOST si té valor
            if total_rebost > 0:
                cursor_despeses.execute('''
                    INSERT INTO TbDespeses (
                        banc, data, mes, any, importCarrec, grup, categoria, concepte, formaPago, comentari
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    banc,
                    data,
                    mes,
                    any,
                    total_rebost,
                    "Càrrec",
                    "rebost",
                    super,
                    forma_pago,
                    ""  # comentari buit
                ))
                print(f"✅ Despesa REBOST: {total_rebost:.2f}€")
            
            # Registrar NETEJA si té valor
            if total_neteja > 0:
                cursor_despeses.execute('''
                    INSERT INTO TbDespeses (
                        banc, data, mes, any, importCarrec, grup, categoria, concepte, formaPago, comentari
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    banc,
                    data,
                    mes,
                    any,
                    total_neteja,
                    "Càrrec",
                    "neteja",
                    super,
                    forma_pago,
                    ""  # comentari buit
                ))
                print(f"✅ Despesa NETEJA: {total_neteja:.2f}€")
            
            # Commitar ambdues bases de dades
            conn_compres.commit()
            conn_despeses.commit()

            print(f"✅ Ticket {self.current_id_despesa} guardat completament")
            
            return ids_compres
            
        except Exception as e:
            print(f"❌ Error guardant a la BD: {e}")
            import traceback
            traceback.print_exc()
            return []
        finally:
            conn_compres.close()
            conn_despeses.close()
            
    def reiniciar_formulari(self):
        """Reiniciar el formulari per a un nou ticket"""
        self.current_lines = []
        self.ui.llistaProductesTable.setRowCount(0)
        self.ui.totalTicketLabel.clear()
        self.ui.desglosLabel.clear()
        self.ui.descompteLineEdit.clear()
        self.actualitzar_num_despesa()
        self.netejar_camps_linia()

        # ✅ REACTIVAR OCR
        self.dades_manual_introduides = False
        self._processant_ocr = False
        self._reactivar_botons_ocr_forçat()  # <-- CANVIAT: usar aquesta funció
        
        # Desactivar i amagar elements d'envio a despesa
        self.ui.envioDespesaCheckBox.setChecked(False)
        self.ui.etiqBanc.setVisible(False)
        self.ui.etiqFPago.setVisible(False)
        self.ui.bancComboBox.setVisible(False)
        self.ui.formaPagoComboBox.setVisible(False)
        
        # Desactivar elements de ticket
        self.ui.modificacionsPushButton.setEnabled(False)
        self.ui.descompteLineEdit.setEnabled(False)
        self.ui.introPushButton.setEnabled(False)
        self.ui.fiTicketPushButton.setEnabled(False)
        
        # Netejar combobox del capçalera
        self.ui.bancComboBox.setCurrentIndex(-1)
        self.ui.formaPagoComboBox.setCurrentIndex(-1)
        self.ui.superComboBox.setCurrentIndex(-1)

    def _reactivar_botons_ocr_forçat(self):
        """Reactivar botons OCR sense comprovar dades manuals"""
        
        super_actual = self.ui.superComboBox.currentText() or ""
        
        if hasattr(self.ui, 'ocrPushButton'):
            self.ui.ocrPushButton.setEnabled(True)
            self.ui.ocrPushButton.setStyleSheet("""
                QPushButton {
                    background-color: #4CAF50;
                    color: white;
                    font-weight: bold;
                    border: 2px solid #45a049;
                    border-radius: 5px;
                    padding: 5px;
                }
                QPushButton:hover {
                    background-color: #45a049;
                }
            """)
            self.ui.ocrPushButton.setToolTip(f"Escanejar ticket de {super_actual}")
        
        if hasattr(self.ui, 'buscarPushButton'):
            self.ui.buscarPushButton.setEnabled(True)
            self.ui.buscarPushButton.setStyleSheet("""
                QPushButton {
                    background-color: #4CAF50;
                    color: white;
                    font-weight: bold;
                    border: 2px solid #45a049;
                    border-radius: 5px;
                    padding: 5px;
                }
                QPushButton:hover {
                    background-color: #45a049;
                }
            """)
            self.ui.buscarPushButton.setToolTip("Seleccionar un ticket de la carpeta predeterminada")
               
    def guardar_modificacions(self):
        """Guardar les modificacions i sortir del mode"""
        QMessageBox.information(None, "Modificacions", "Modificacions guardades")
        self.toggle_modificacions()

    def cancelar_modificacions(self):
        """Cancel·lar modificacions i sortir del mode"""
        resposta = QMessageBox.question(
            None, "Cancel·lar Modificacions",
            "Vols cancel·lar les modificacions?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if resposta == QMessageBox.StandardButton.Yes:
            self.toggle_modificacions()

    def veure_ultims_tickets(self):
        """Funció per veure els últims tickets guardats"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Veure els últims 5 idDespesa únics
            cursor.execute('''
                SELECT DISTINCT idDespesa, data, super, COUNT(*) as lineas
                FROM TBCompresSuper 
                GROUP BY idDespesa
                ORDER BY idDespesa DESC 
                LIMIT 5
            ''')
            
            despeses = cursor.fetchall()
            
            for despesa in despeses:
                id_despesa, data, super, lineas = despesa
                
                # Veure les línies d'aquesta despesa
                cursor.execute('''
                    SELECT idCompra, familia, article, quantitat, preuUnit, totLinea
                    FROM TBCompresSuper 
                    WHERE idDespesa = ?
                    ORDER BY idCompra
                ''', (id_despesa,))
                
                lineas_detall = cursor.fetchall()
                for linea in lineas_detall:
                    id_compra, familia, article, quantitat, preu_unit, total = linea
            conn.close()
        except Exception as e:
            print(f"❌ Error llegint BD: {e}")
 
    def initialize_data(self):
        """Inicialitzar les dades del formulari"""   
        # PRIMER: Netejar tots els camps abans de res
        self.netejar_tots_camps_formulari() 

        # Després carregar les dades
        self.carregar_combobox()
        self.establir_data_avui()
        self.actualitzar_num_despesa()
        self.inicialitzar_taula()

        # ✅ NOU: Actualitzar estat inicial del botó OCR
        self.actualitzar_boto_ocr()

    def focus_quantitat(self):
        """Moure el focus a quantitat"""
        self.ui.quantitatLineEdit.setFocus()
        self.ui.quantitatLineEdit.selectAll()

    def focus_preu_unit(self):
        """Moure el focus a preu unitari"""
        self.ui.preuUnitLineEdit.setFocus()
        self.ui.preuUnitLineEdit.selectAll()

    def focus_promocio(self):
        """Moure el focus a promoció"""
        self.ui.promocioLineEdit.setFocus()
        self.ui.promocioLineEdit.selectAll()

    def focus_total_des_percentatge(self):
        """Moure el focus a total després del percentatge"""
        
        if self.ui.percentatgeLineEdit.text().strip():
            self.focus_total_linea()
        else:
            self.focus_promocio()

    def focus_percentatge(self):
        """Moure el focus a percentatge"""
        self.ui.percentatgeLineEdit.setFocus()
        self.ui.percentatgeLineEdit.selectAl

    def focus_total_linea(self):
        """Moure el focus a total línea"""
        
        # Si hi ha percentatge i el total està buit, demanar que s'introdueixi
        if self.ui.percentatgeLineEdit.text().strip() and not self.ui.totalLineaLineEdit.text().strip():
            self.ui.totalLineaLineEdit.setFocus()
            self.ui.totalLineaLineEdit.selectAll()
        else:
            # Si ja hi ha total, recalcular
            if self.ui.totalLineaLineEdit.text().strip():
                self.calcular_total_des_percentatge_i_total()
            self.ui.totalLineaLineEdit.setFocus()
            self.ui.totalLineaLineEdit.selectAll()

    def calcular_i_afegir(self):
        """Calcular i afegir línia"""
        # Si hi ha percentatge, calcular amb el mètode simple
        if self.ui.percentatgeLineEdit.text().strip():
            self.calcular_percentatge_simple()
        
        # Afegir la línia
        self.afegir_linia()

    def controlar_focus_des_preu_unit(self):
        """Decidir on va el focus després del preu unitari"""
        
        if self.ui.preuUnitLineEdit.text().strip():
            # 1. Calcular total automàticament
            self.calcular_total_normal()
            
            # 2. SI hi ha percentatge introduït, ignorar-lo i anar a promoció
            if self.ui.percentatgeLineEdit.text().strip():
                # Netejar percentatge per evitar confusions
                self.ui.percentatgeLineEdit.clear()
            
            # 3. Anar sempre a promoció (NO es pot tenir preu unitari i percentatge)
            self.focus_promocio()
        else:
            # Si no hi ha preu unitari, anar a percentatge
            self.focus_percentatge()

    def calcular_total_normal(self):
        """Calcular total normal (sense percentatge)"""
        try:
            q = float(self.ui.quantitatLineEdit.text().replace(',', '.') or 0)
            p = float(self.ui.preuUnitLineEdit.text().replace(',', '.') or 0)
            promo = float(self.ui.promocioLineEdit.text().replace(',', '.') or 0)
            
            total = q * p - promo
            self.ui.totalLineaLineEdit.setText(f"{total:.2f}".replace('.', ','))
        except:
            self.ui.totalLineaLineEdit.setText("0,00")

    def controlar_focus_des_percentatge(self):
        """Controlar el focus després del percentatge"""
        # Si hi ha percentatge, anar al TOTAL (no calcular encara)
        if self.ui.percentatgeLineEdit.text().strip():
            self.focus_total_linea()
        else:
            # Si no hi ha percentatge, anar a promoció
            self.focus_promocio()
    
    def controlar_focus_des_promocio(self):
        """Controlar el focus després de la promoció"""
        # Si hi ha promoció, calcular total i anar-hi
        if self.ui.promocioLineEdit.text().strip():
            self.calcular_total_linia()
            self.focus_total_linea()
        else:
            # Si no hi ha promoció, anar directament al total
            self.focus_total_linea()

    def afegir_linia_des_enter(self):
        """Afegir línea quan es prem Enter al camp total línea"""
        
        # Si hi ha percentatge, calcular primer
        if self.ui.percentatgeLineEdit.text().strip() and self.ui.totalLineaLineEdit.text().strip():
            self.calcular_total_des_percentatge_i_total()
        
        # Afegir la línia
        self.afegir_linia()

    def focus_article_des_familia(self):
        """Quan es selecciona família, focus a article"""
        self.ui.articleCombobox.setFocus()

    def focus_pes(self):
        """Quan es selecciona article, focus a pes"""
        self.ui.pesLineEdit.setFocus()
        self.ui.pesLineEdit.selectAll()

    def afegir_super_nou(self):
        """Afegir un nou supermercat"""
        super_nou, ok = QInputDialog.getText(
            None, "Nou Supermercat", "Introdueix el nom del nou supermercat:"
        )
        
        if ok and super_nou:
            if afegir_super(super_nou):
                QMessageBox.information(None, "Èxit", f"Supermercat '{super_nou}' afegit")
                # Actualitzar el combobox
                supers = obtenir_supers()
                self.ui.superComboBox.clear()
                self.ui.superComboBox.addItems(sorted(supers))
                self.ui.superComboBox.setCurrentText(super_nou)
            else:
                QMessageBox.warning(None, "Error", "No s'ha pogut afegir el supermercat")

    def afegir_familia_nova(self):
        """Afegir una nova família"""
        familia_nova, ok = QInputDialog.getText(
            None, "Nova Família", "Introdueix el nom de la nova família:"
        )
        
        if ok and familia_nova:
            if afegir_familia(familia_nova):
                QMessageBox.information(None, "Èxit", f"Família '{familia_nova}' afegida")
                # Actualitzar el combobox
                families = obtenir_families_compres()
                self.ui.familiaCombobox.clear()
                self.ui.familiaCombobox.addItems(sorted(families))
                self.ui.familiaCombobox.setCurrentText(familia_nova)
            else:
                QMessageBox.warning(None, "Error", "No s'ha pogut afegir la família")

    def afegir_super_des_text(self, text):
        """Afegir supermercat quan es perdi el focus si és nou"""
        if text and text not in obtenir_supers():
            resposta = QMessageBox.question(
                None, "Nou Supermercat", 
                f"Vols afegir '{text}' com a nou supermercat?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if resposta == QMessageBox.StandardButton.Yes:
                self.afegir_super_nou_des_text(text)

    def afegir_super_nou_des_text(self, text):
        """Afegir supermercat des del text introduït"""
        if afegir_super(text):
            supers = obtenir_supers()
            self.ui.superComboBox.clear()
            self.ui.superComboBox.addItems(sorted(supers))
            self.ui.superComboBox.setCurrentText(text)

    def afegir_familia_des_text(self, text):
        """Afegir família quan es perdi el focus si és nova"""
        if text and text not in obtenir_families_compres():
            resposta = QMessageBox.question(
                None, "Nova Família", 
                f"Vols afegir '{text}' com a nova família?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if resposta == QMessageBox.StandardButton.Yes:
                self.afegir_familia_nova_des_text(text)

    def afegir_familia_nova_des_text(self, text):
        """Afegir família des del text introduït"""
        if afegir_familia(text):
            families = obtenir_families_compres()
            self.ui.familiaCombobox.clear()
            self.ui.familiaCombobox.addItems(sorted(families))
            self.ui.familiaCombobox.setCurrentText(text)

    def activar_elements_ticket(self):
        """Activar els elements quan hi hagi almenys una línia"""
        self.ui.modificacionsPushButton.setEnabled(True)
        self.ui.descompteLineEdit.setEnabled(True)
        self.ui.introPushButton.setEnabled(True)
        self.ui.fiTicketPushButton.setEnabled(True)
        
        # ✅ Els camps de producte segueixen bloquejats fins que s'activi modificacions
        # No cal fer res més

    def tancar_formulari(self):
        """Tancar el formulari amb confirmació si hi ha dades sense guardar"""
        if self.current_lines:
            resposta = QMessageBox.question(
                None, 
                "Tancar formulari", 
                "Hi ha un ticket sense finalitzar. Vols tancar igualment?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if resposta == QMessageBox.StandardButton.No:
                return  # No tancar
        
        from PySide6.QtWidgets import QApplication
        QApplication.quit()

    def configurar_combobox_teclat(self):
        """Configurar el comportament del teclat pels combobox"""
        # Fer que els combobox ignorin la tecla Enter
        self.ui.familiaCombobox.setFocusPolicy(Qt.StrongFocus)
        self.ui.articleCombobox.setFocusPolicy(Qt.StrongFocus)
        
        # 🔴 Per defecte, no editables
        self.ui.familiaCombobox.setEditable(False)
        self.ui.articleCombobox.setEditable(False)

    def establir_data_avui(self):
        """Establir la data actual al camp de data"""
        try:
            data_actual = datetime.now().strftime("%d/%m/%Y")
            self.ui.dataLineEdit.setText(data_actual)
        except Exception as e:
            print(f"❌ Error establint data: {e}")

    def processar_imatge_ticket(self):
        """Processar imatge de ticket amb OCR"""
        try:
            # Verificar que estem a Dia
            super_actual = self.ui.superComboBox.currentText().strip().lower()
            if 'dia' not in super_actual:
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.warning(
                    None, 
                    "Super incorrecte", 
                    f"El botó OCR només està disponible per a supermercats Dia.\n"
                    f"Super actual: {self.ui.superComboBox.currentText()}"
                )
                return
            # Obrir diàleg per seleccionar imatge
            from PySide6.QtWidgets import QFileDialog
            from PySide6.QtCore import QDir
            
            file_path, _ = QFileDialog.getOpenFileName(
                None,
                f"Seleccionar ticket del Dia",
                QDir.homePath(),
                "Imatges (*.png *.jpg *.jpeg *.bmp *.gif)"
            )
            
            if file_path:
                # Processar amb OCR
                if OCR_AVAILABLE:
                    self._processar_amb_ocr_real(file_path)
                else:
                    self._processar_amb_ocr_simulat(file_path)
                    
        except Exception as e:
            print(f"❌ Error en processar_imatge_ticket: {e}")
            import traceback
            traceback.print_exc()
            
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(None, "Error", f"Error processant imatge:\n{str(e)}")

    def mostrar_resultats_ocr_complet(self, metadades, productes, text_original, image_path):
        """Mostrar els resultats COMPLETS de l'OCR i permetre importar tot"""
        from PySide6.QtWidgets import (QDialog, QVBoxLayout, QListWidget, QPushButton, 
                                        QLabel, QHBoxLayout, QSpinBox, QSplitter, QTextEdit,
                                        QGroupBox, QFormLayout, QTableWidget, QComboBox, 
                                        QListWidgetItem)        
        from PySide6.QtCore import Qt
        
        # Guardar referències per utilitzar-les dins de les funcions internes
        productes_local = productes  # Copia local per a les closures
        metadades_local = metadades
        
        # Verificar que hi hagi productes
        if not productes_local:
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(None, "Sense productes", "No s'han detectat productes al ticket.")
            self._reactivar_botons_ocr()  # 🔴 REACTIVAR
            return
        
        # Títol amb més informació
        titol = f"Ticket {metadades.get('supermercat', 'Desconegut')}"
        
        
        dialog = QDialog()
        dialog.setWindowTitle(titol)
        dialog.resize(1000, 700)
        
        layout = QVBoxLayout()
        
        # Splitter principal
        splitter = QSplitter(Qt.Horizontal)
        
        # PANEL ESQUERRE: Metadades del ticket
        left_widget = QWidget()
        left_layout = QVBoxLayout()
        
        # Grup de metadades
        metadata_group = QGroupBox("📋 Informació del ticket")
        metadata_layout = QFormLayout()
        
        # Supermercat
        supermercat = metadades.get('supermercat', 'Desconegut')
        metadata_layout.addRow("Supermercat:", QLabel(supermercat))
        
        # Data
        data_ocr = metadades.get('data', 'No detectada')
        metadata_layout.addRow("Data OCR:", QLabel(data_ocr))
        
        # Hora (si existeix)
        hora = metadades.get('hora', '')
        if hora:
            metadata_layout.addRow("Hora:", QLabel(hora))
        
        # Número ticket
        num_ticket = metadades.get('numero_ticket', '')
        if num_ticket:
            metadata_layout.addRow("Nº Ticket:", QLabel(num_ticket))
        
        # Total
        total = metadades.get('total_ticket', 0)
        if total > 0:
            metadata_layout.addRow("Total:", QLabel(f"{total:.2f}€"))
        
        # Productes detectats
        metadata_layout.addRow("Productes detectats:", QLabel(f"{len(productes)} productes"))
        
        metadata_group.setLayout(metadata_layout)
        left_layout.addWidget(metadata_group)
        
        # Text OCR
        text_group = QGroupBox("📝 Text reconegut")
        text_layout = QVBoxLayout()
        text_edit = QTextEdit()
        text_edit.setPlainText(text_original)
        text_edit.setMaximumHeight(200)
        text_edit.setReadOnly(True)
        text_layout.addWidget(text_edit)
        text_group.setLayout(text_layout)
        left_layout.addWidget(text_group)
        
        # Mini vista de la imatge
        from PySide6.QtGui import QPixmap, QMouseEvent
        from PySide6.QtCore import Qt

        pixmap = QPixmap(image_path)
        if not pixmap.isNull():
            image_group = QGroupBox("🖼️ Vista prèvia (doble clic per ampliar)")
            image_layout = QVBoxLayout()
            image_label = QLabel()
            scaled_pixmap = pixmap.scaled(280, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            image_label.setPixmap(scaled_pixmap)
            image_label.setAlignment(Qt.AlignCenter)
            image_label.setCursor(Qt.PointingHandCursor)  # Cursor de mà
            
            # Afegir doble clic per ampliar
            def mouseDoubleClickEvent(event):
                self._ampliar_imatge(image_path)

            image_label.mouseDoubleClickEvent = mouseDoubleClickEvent
            
            image_layout.addWidget(image_label)
            image_group.setLayout(image_layout)
            left_layout.addWidget(image_group)
        
        left_widget.setLayout(left_layout)
        
        # PANEL DRET: Llista de productes
        right_widget = QWidget()
        right_layout = QVBoxLayout()

        productes_group = QGroupBox(f"📦 Productes detectats ({len(productes)})")
        productes_layout = QVBoxLayout()

        # 🔴 ASsegurar que la llista es crea correctament
        llista = QListWidget()
        llista.setSelectionMode(QListWidget.MultiSelection)

        for i, producte in enumerate(productes_local, 1):
            
            nom_producte = producte.get('producte', 'Desconegut')
            quantitat = producte.get('quantitat_detectada', 1)
            
            # Construir text de l'ítem
            nom_original = producte.get('producte_brut', '')
            similitud = producte.get('similitud', 0)
            familia = producte.get('familia', '')
            
            # Determinar icona segons similitud
            if similitud >= 0.8:
                icona = "✅"
            elif similitud >= 0.6:
                icona = "⚠️"
            else:
                icona = "🆕"
            
            # MOSTRAR QUANTITAT
            if quantitat > 1:
                item_text = f"{i:2d}. {icona} {nom_producte} x{quantitat}"
            else:
                item_text = f"{i:2d}. {icona} {nom_producte}"
            
            if similitud > 0:
                item_text += f" ({similitud:.2f})"
                    
            # Preu i descomptes
            if 'descompte_aplicat' in producte and producte['descompte_aplicat'] > 0:
                item_text += f" | 💰 ~~{producte['preu_original']:.2f}€~~ 🔖 -{producte['descompte_aplicat']:.2f}€ → {producte['preu']:.2f}€"
            else:
                item_text += f" | 💰 {producte['preu']:.2f}€"
            
            if familia and familia != 'Desconeguda':
                item_text += f" | 📁 {familia}"
            
            # Nom original en gris petit (opcional)
            if nom_original and nom_original.upper() != nom_producte.upper():
                item_text += f"\n    ⬤ {nom_original[:40]}"
            
            item = QListWidgetItem(item_text)
            item.setSelected(True)
            item.setData(Qt.UserRole, producte)
            
            # Opcional: posar el nom original en gris
            if nom_original and nom_original.upper() != nom_producte.upper():
                item.setForeground(Qt.darkGray)
            
            llista.addItem(item)

        # Connectar doble clic per editar
        llista.itemDoubleClicked.connect(lambda item: self.editar_producte_ocr(item, llista, productes_local))

        # 🔴 AFEGIR LA LLISTA AL LAYOUT
        productes_layout.addWidget(llista)

        # 🔴 AFEGIR EL LAYOUT DEL GRUP AL GRUP
        productes_group.setLayout(productes_layout)

        # 🔴 AFEGIR EL GRUP AL LAYOUT DRET
        right_layout.addWidget(productes_group)

        # 🔴 ASSIGNAR EL LAYOUT AL WIDGET DRET
        right_widget.setLayout(right_layout)

        # Afegir widgets al splitter
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setSizes([300, 700])

        layout.addWidget(splitter)
        
        # BOTONS
        buttons_layout = QHBoxLayout()
        
        btn_importar_complet = QPushButton("🚀 Importar TICKET COMPLET")
        btn_importar_complet.setStyleSheet("""
            QPushButton { 
                background-color: #4CAF50; 
                color: white; 
                font-weight: bold; 
                padding: 8px;
                border-radius: 4px;
            }
            QPushButton:hover { 
                background-color: #45a049; 
            }
        """) 
        
        
        btn_tancar = QPushButton("❌ Tancar")
        
        def importar_ticket_complet():
            """Importar TOT el ticket: metadades + productes (AMB ACUMULACIÓ)"""
            
            # 1. Establir metadades al formulari
            self.establir_metadades_ticket(metadades_local)
            
            # 2. Importar TOTS els productes amb control de duplicats i acumulació
            productes_importats = 0
            
            for producte in productes_local:
                if not producte:
                    continue
                
                # 🔴 ARA UTILITZAR ELS MÈTODES CORRECTES
                self.afegir_producte_des_ocr(producte)
                productes_importats += 1
            
            print(f"✅ Importats {productes_importats} productes")
            
            # Tancar el diàleg
            dialog.accept()
            
            # Mostrar missatge
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.information(None, "Èxit", 
                                f"✅ Ticket importat completament!\n"
                                f"• Supermercat: {metadades_local.get('supermercat', 'Desconegut')}\n"
                                f"• Productes: {productes_importats}")
        
        def corregir_matches():
            """Obrir diàleg per corregir manualment els matches"""
            dialog_correccio = QDialog(dialog)
            dialog_correccio.setWindowTitle("Corregir Matches de Productes")
            dialog_correccio.resize(800, 600)
            
            layout_correccio = QVBoxLayout()
            
            # Taula per veure i corregir matches
            table = QTableWidget()
            table.setColumnCount(5)
            table.setHorizontalHeaderLabels(["Producte detectat", "Preu", "Match actual", "Similitud", "Nou match"])
            
            table.setRowCount(len(productes_local))
            
            # Carregar tots els noms estàndard disponibles de la base de dades
            from config.llistes import obtenir_families_compres, obtenir_articles_per_familia
            
            noms_disponibles = []
            families = obtenir_families_compres()
            for familia in families:
                articles = obtenir_articles_per_familia(familia)
                noms_disponibles.extend(articles)
            
            for i, producte in enumerate(productes_local):
                # Columna 0: Producte detectat
                table.setItem(i, 0, QTableWidgetItem(producte['producte']))
                
                # Columna 1: Preu
                table.setItem(i, 1, QTableWidgetItem(f"{producte['preu']:.2f}€"))
                
                # Columna 2: Match actual
                match_actual = producte.get('nom_estandard', 'Sense match')
                table.setItem(i, 2, QTableWidgetItem(match_actual))
                
                # Columna 3: Similitud
                similitud = producte.get('similitud', 0)
                table.setItem(i, 3, QTableWidgetItem(f"{similitud:.2f}"))
                
                # Columna 4: Combobox per seleccionar nou match
                combo = QComboBox()
                combo.addItem("-- Seleccionar --")
                combo.addItem(producte['producte'])  # Mantenir l'original
                
                # Afegir match actual si existeix
                if match_actual != 'Sense match' and match_actual not in [producte['producte']]:
                    combo.addItem(match_actual)
                
                # Afegir altres opcions de la base de dades que coincideixin
                for nom in noms_disponibles:
                    if nom.lower() in producte['producte'].lower() or producte['producte'].lower() in nom.lower():
                        if nom not in [combo.itemText(j) for j in range(combo.count())]:
                            combo.addItem(nom)
                
                # Permetre també escriure text personalitzat
                combo.setEditable(True)
                table.setCellWidget(i, 4, combo)
                
                # Guardar l'índex del producte a les dades del combobox
                combo.setProperty("producte_index", i)
            
            layout_correccio.addWidget(table)
            
            # Botons
            btn_layout_correccio = QHBoxLayout()
            btn_guardar = QPushButton("💾 Aplicar correccions")
            btn_cancelar = QPushButton("❌ Cancel·lar")
            
            def aplicar_correccions():
                """Aplicar les correccions als productes"""
                for i in range(table.rowCount()):
                    combo = table.cellWidget(i, 4)
                    if combo:
                        nou_match = combo.currentText().strip()
                        
                        if nou_match and nou_match != "-- Seleccionar --":
                            # Actualitzar el producte
                            productes_local[i]['nom_estandard'] = nou_match
                            productes_local[i]['similitud'] = 1.0  # Màxima confiança per correcció manual
                            
                            # Actualitzar també els ítems de la llista principal
                            for idx in range(llista.count()):
                                item = llista.item(idx)
                                if item and item.data(Qt.UserRole):
                                    item_data = item.data(Qt.UserRole)
                                    if item_data.get('numero_linia') == productes_local[i].get('numero_linia'):
                                        item_data['nom_estandard'] = nou_match
                                        item_data['similitud'] = 1.0
                                        item.setData(Qt.UserRole, item_data)
                                        break
                
                dialog_correccio.accept()
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.information(None, "Correccions", "✅ Correccions aplicades correctament!")
                
                # Actualitzar la llista
                llista.clear()
                for producte in productes_local:
                    nom_estandard = producte.get('nom_estandard', producte['producte'])
                    similitud = producte.get('similitud', 0)
                    
                    # Determinar icona segons similitud
                    if similitud >= 0.8:
                        icona = "✅"
                    elif similitud >= 0.6:
                        icona = "⚠️"
                    else:
                        icona = "🆕"
                    
                    item_text = f"{icona} {nom_estandard}"
                    
                    if similitud > 0:
                        item_text += f" ({similitud:.2f})"
                    
                    item_text += f" | 💰 {producte['preu']:.2f}€"
                    
                    familia = producte.get('familia', '')
                    if familia and familia != 'Desconeguda':
                        item_text += f" | 📁 {familia}"
                    
                    # Crear nou ítem
                    item = QListWidgetItem(item_text)
                    item.setSelected(True)
                    item.setData(Qt.UserRole, producte)
                    llista.addItem(item)
            
            btn_guardar.clicked.connect(aplicar_correccions)
            btn_cancelar.clicked.connect(dialog_correccio.reject)
            
            btn_layout_correccio.addWidget(btn_guardar)
            btn_layout_correccio.addWidget(btn_cancelar)
            
            layout_correccio.addLayout(btn_layout_correccio)
            dialog_correccio.setLayout(layout_correccio)
            dialog_correccio.exec()
        
        def tancar_dialog():
            """Tancar el diàleg sense importar i reactivar botons"""
            dialog.reject()
            self._reactivar_botons_ocr()  # 🔴 REACTIVAR QUAN ES TANCA SENSE IMPORTAR
        
        btn_importar_complet.clicked.connect(importar_ticket_complet)         
        btn_tancar.clicked.connect(tancar_dialog)  # 🔴 Connectar a tancar_dialog
        
        buttons_layout.addWidget(btn_importar_complet) 
        buttons_layout.addWidget(btn_tancar)
        
        layout.addLayout(buttons_layout)
        dialog.setLayout(layout)
        
        # 🔴 Quan es tanca el diàleg amb la X o ESC
        dialog.finished.connect(lambda: self._reactivar_botons_ocr())
        
        # Mostrar el diàleg
        dialog.exec()
        
    def establir_metadades_ticket(self, metadades):
        """Establir les metadades del ticket al formulari"""
        try:
            print(f"📅 Metadades rebudes: {metadades}")
            print(f"📅 Data actual del formulari (abans): {self.ui.dataLineEdit.text()}")
            
            # Establir supermercat
            if metadades['supermercat'] != "Desconegut":
                index = self.ui.superComboBox.findText(metadades['supermercat'], Qt.MatchContains)
                if index >= 0:
                    self.ui.superComboBox.setCurrentIndex(index)
                else:
                    print(f"⚠️ Supermercat no trobat: {metadades['supermercat']}")
            
            # Establir forma de pagament
            if metadades.get('forma_pago') and metadades['forma_pago'] != "Desconeguda":
                index = self.ui.formaPagoComboBox.findText(metadades['forma_pago'], Qt.MatchContains)
                if index >= 0:
                    self.ui.formaPagoComboBox.setCurrentIndex(index)
                
        except Exception as e:
            print(f"❌ Error establent metadades: {e}")

    def afegir_producte_des_ocr(self, producte_data):
        """Afegir un producte detectat per OCR al formulari"""
        
        # CONTROL DE DUPLICATS I ACUMULACIÓ
        if not hasattr(self, '_productes_importats_ocr'):
            self._productes_importats_ocr = {}
        
        # OBTENIR TOTES LES DADES DEL PRODUCTE
        nom_estandard = producte_data.get('nom_estandard', producte_data.get('producte', 'Desconegut'))
        
        # OBTENIR PREU ORIGINAL I DESCOMPTE
        preu_original = producte_data.get('preu_original', producte_data.get('preu', 0))
        descompte = producte_data.get('descompte_aplicat', 0)
        quantitat = producte_data.get('quantitat_detectada', 1)
        familia = producte_data.get('familia', 'Desconeguda')    
        
        # OBTENIR PES SI EXISTEIX
        pes_grams = producte_data.get('pes_grams', None)
        te_pes = producte_data.get('te_pes', False)
        
        # CLAU PER DUPLICATS
        if te_pes and pes_grams:
            clau = f"{nom_estandard}_{preu_original}_{pes_grams}"
        else:
            clau = f"{nom_estandard}_{preu_original}"
        
        # SI JA EXISTEIX, ACUMULAR QUANTITAT
        if clau in self._productes_importats_ocr:
            quantitat_actual = self._productes_importats_ocr[clau]['quantitat']
            nova_quantitat = quantitat_actual + quantitat
            
            print(f"   📦 Acumulant {quantitat} unitats a {nom_estandard} (total: {nova_quantitat})")
            
            self._productes_importats_ocr[clau]['quantitat'] = nova_quantitat
            
            # 🔴 Passar descompte 0 perquè el percentatge no es toca
            self._actualitzar_quantitat_producte(nom_estandard, preu_original, nova_quantitat, pes_grams, 0)
            return
        
        # SI NO EXISTEIX, CREAR NOU PRODUCTE
        if te_pes and pes_grams:
            print(f"   🆕 Nou producte amb pes: {nom_estandard} - {pes_grams}g (preu: {preu_original:.2f}€)")
        else:
            print(f"   🆕 Nou producte: {nom_estandard} x{quantitat} (preu orig: {preu_original:.2f}€, descompte: {descompte:.2f}€)")
        
        self._productes_importats_ocr[clau] = {
            'nom': nom_estandard,
            'preu': preu_original,
            'quantitat': quantitat,
            'familia': familia,
            'pes_grams': pes_grams,
            'te_pes': te_pes
        }
        
        # 🔴 PASSAR PERCENTATGE = 0 (no calculat automàticament)
        self._afegir_linia_des_de_dades(
            nom_estandard,
            familia,
            preu_original,
            quantitat,
            descompte,
            0,  # percentatge = 0
            pes_grams=pes_grams,
            es_rebost=False
        )

        # 🔴🔴🔴 DESACTIVAR BOTONS OCR
        self._desactivar_botons_ocr_permanent()
        
        self.netejar_camps_linia()

    def _desactivar_botons_ocr_permanent(self):
        """Desactivar botons OCR permanentment (després d'importar)"""
        
        if hasattr(self.ui, 'ocrPushButton'):
            self.ui.ocrPushButton.setEnabled(False)
            self.ui.ocrPushButton.setStyleSheet("""
                QPushButton {
                    background-color: #CCCCCC;
                    color: #666666;
                    border: 2px solid #AAAAAA;
                    border-radius: 5px;
                    padding: 8px;
                    font-size: 12px;
                }
            """)
            self.ui.ocrPushButton.setToolTip("No es poden afegir més productes a aquest ticket")
        
        if hasattr(self.ui, 'buscarPushButton'):
            self.ui.buscarPushButton.setEnabled(False)
            self.ui.buscarPushButton.setStyleSheet("""
                QPushButton {
                    background-color: #CCCCCC;
                    color: #666666;
                    border: 2px solid #AAAAAA;
                    border-radius: 5px;
                    padding: 8px;
                    font-size: 12px;
                }
            """)
            self.ui.buscarPushButton.setToolTip("No es poden afegir més productes a aquest ticket")
        
        self.dades_manual_introduides = True
        print("🔒 Botons OCR desactivats permanentment")

    def _actualitzar_quantitat_producte(self, nom_producte, preu, nova_quantitat, pes_grams=None, descompte=0):
        """Actualitzar la quantitat d'un producte existent a la taula"""

        print(f"   🔄 _actualitzar_quantitat_producte: {nom_producte}, nova_quant={nova_quantitat}, descompte_rebut={descompte}")

        for row in range(self.ui.llistaProductesTable.rowCount()):
            item_nom = self.ui.llistaProductesTable.item(row, 1)  # Columna Article
            item_preu = self.ui.llistaProductesTable.item(row, 4)  # Columna Preu Unit
            item_pes = self.ui.llistaProductesTable.item(row, 2)  # Columna Pes
            item_descompte = self.ui.llistaProductesTable.item(row, 6)  # Columna Promo
            
            if item_nom and item_preu:
                # Convertir preu de la taula (amb coma) a float per comparar
                preu_taula = float(item_preu.text().replace(',', '.'))
                
                # Comprovar si coincideix el nom i el preu
                if item_nom.text() == nom_producte and abs(preu_taula - preu) < 0.01:
                    
                    # 🔴 SI ÉS PRODUCTE AMB PES, COMPROVAR TAMBÉ EL PES
                    if pes_grams is not None:
                        pes_taula = item_pes.text() if item_pes else ''
                        if pes_taula != str(pes_grams):
                            continue  # No és el mateix producte (pes diferent)
                    
                    # 🔴🔴🔴 OBTENIR EL DESCOMPTE ACTUAL DE LA FILA
                    descompte_actual = 0
                    if item_descompte and item_descompte.text():
                        try:
                            descompte_actual = float(item_descompte.text().replace(',', '.'))
                        except ValueError:
                            descompte_actual = 0
                    
                    # 🔴🔴🔴 USAR EL DESCOMPTE ACTUAL (no el rebut) PER MANTENIR-LO
                    descompte_a_usar = descompte_actual if descompte_actual > 0 else descompte
                    
                    # Actualitzar quantitat
                    self.ui.llistaProductesTable.item(row, 3).setText(str(nova_quantitat))
                    
                    # 🔴🔴🔴 RECALCULAR TOTAL AMB EL DESCOMPTE CORRECTE
                    total = (nova_quantitat * preu) - descompte_a_usar
                    self.ui.llistaProductesTable.item(row, 7).setText(f"{total:.2f}".replace('.', ','))
                    
                    # Actualitzar dades internes
                    if row < len(self.current_lines):
                        self.current_lines[row]['quantitat'] = nova_quantitat
                        self.current_lines[row]['totLinea'] = total
                        # Mantenir el descompte a les dades internes
                        self.current_lines[row]['prom'] = descompte_a_usar
                    
                    print(f"   ✅ Quantitat actualitzada a {nova_quantitat} per {nom_producte} (descompte: {descompte_a_usar:.2f}€)")
                    return True
        
        print(f"   ⚠️ No s'ha trobat el producte {nom_producte} per actualitzar")
        return False

    def preguntar_guardar_producte_nou(self, producte_data):
        """Preguntar si es vol guardar un nou producte detectat"""
        from PySide6.QtWidgets import QMessageBox, QInputDialog
        
        nom_detectat = producte_data['producte']
        nom_estandard = producte_data.get('nom_estandard', nom_detectat)
        
        resposta = QMessageBox.question(
            None,
            "Producte nou detectat",
            f"S'ha detectat un producte nou:\n\n"
            f"📝 Detectat: '{nom_detectat}'\n"
            f"🏷️  Actual: '{nom_estandard}'\n\n"
            f"Vols guardar aquest producte a la base de dades?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if resposta == QMessageBox.StandardButton.Yes:
            # Preguntar nom estàndard
            nou_nom, ok = QInputDialog.getText(
                None,
                "Nom estàndard",
                "Introdueix el nom estàndard per a aquest producte:",
                text=nom_estandard
            )
            
            if ok and nou_nom:
                # Preguntar família
                families = obtenir_families_compres()
                familia, ok2 = QInputDialog.getItem(
                    None,
                    "Família",
                    "Selecciona la família:",
                    families,
                    0,
                    False
                )
                
                if ok2:
                    # Guardar a la base de dades
                    try:
                        from controllers.ocr_ticket import OCRProcessor
                        processor = OCRProcessor(self.ui.superComboBox.currentText())
                        if processor.guardar_producte_nou(nom_detectat, nou_nom, familia):
                            QMessageBox.information(
                                None,
                                "Producte guardat",
                                f"✅ Producte guardat correctament!\n"
                                f"Nom super: {nom_detectat}\n"
                                f"Nom estàndard: {nou_nom}\n"
                                f"Família: {familia}"
                            )
                    except Exception as e:
                        QMessageBox.warning(None, "Error", f"No s'ha pogut guardar: {e}")
    
    def mostrar_imatge_seleccionada(self, file_path):
        """Mostrar una miniatura de la imatge seleccionada"""
        try:
            from PySide6.QtGui import QPixmap
            from PySide6.QtWidgets import QLabel
            from PySide6.QtCore import Qt
            
            # Crear un diàleg simple per mostrar la imatge
            dialog = QDialog()
            dialog.setWindowTitle("Imatge seleccionada")
            dialog.resize(400, 300)
            
            layout = QVBoxLayout()
            label_imatge = QLabel()
            pixmap = QPixmap(file_path)
            
            if not pixmap.isNull():
                scaled_pixmap = pixmap.scaled(380, 250, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                label_imatge.setPixmap(scaled_pixmap)
                label_imatge.setAlignment(Qt.AlignCenter)
            
            layout.addWidget(label_imatge)
            dialog.setLayout(layout)
            
            # Mostrar breument i tancar automàticament després d'1 segon
            from PySide6.QtCore import QTimer
            QTimer.singleShot(1000, dialog.close)
            dialog.exec()
            
        except Exception as e:
            print(f"⚠️ Error mostrant imatge: {e}")

    def mostrar_instruccions_instalacio(self):
        """Mostrar instruccions per instal·lar les dependències d'OCR"""
        from PySide6.QtWidgets import QMessageBox
        
        instruccions = """
    📋 OCR no disponible - Instal·lar dependències:

    Obre el terminal i executa:

    pip install pytesseract pillow opencv-python

    ⚠️ També necessites tenir instal·lat Tesseract OCR:

    • Windows: Descarrega des de https://github.com/UB-Mannheim/tesseract/wiki
    • macOS: brew install tesseract
    • Linux: sudo apt-get install tesseract-ocr

    Després reinicia l'aplicació.
    """
        
        QMessageBox.information(None, "Instal·lar OCR", instruccions)

    def diagnosticar_ui(self):
        """Funció per diagnosticar quins elements existeixen al UI"""
        
        # Verificar el botón OCR específicamente
        if hasattr(self.ui, 'ocrPushButton'):
            pass
        else:
            print("❌ OCR BUTTON NO TROBAT")
        
        # Verificar otros botones importantes
        botons_importants = ['introLineaPushButton', 'fiTicketPushButton', 'modificacionsPushButton']
        for nom in botons_importants:
            if hasattr(self.ui, nom):
                pass
            else:
                print(f"❌ {nom} - NO TROBAT")

    def prova_boto_ocr_simple(self):
        """Funció simple de prova per verificar que el botó funciona"""
        try:            
            # Desconnectar la funció de prova
            self.ui.ocrPushButton.clicked.disconnect()
            
            # Connectar a la funció real
            self.ui.ocrPushButton.clicked.connect(self.processar_imatge_ticket)
            
            # Executar la funció real immediatament
            self.processar_imatge_ticket()
            
        except Exception as e:
            print(f"❌ Error en prova OCR: {e}")
            import traceback
            traceback.print_exc()

    def actualitzar_boto_ocr(self):
        """Actualitzar l'estat del botó OCR segons el super seleccionat"""
        super_seleccionat = self.ui.superComboBox.currentText().strip()
        
        if hasattr(self.ui, 'ocrPushButton'):
            # Activar si hi ha un supermercat seleccionat
            if super_seleccionat:
                self.ui.ocrPushButton.setEnabled(True)
                self.ui.ocrPushButton.setStyleSheet("""
                    QPushButton {
                        background-color: #4CAF50;
                        color: white;
                        font-weight: bold;
                        border: 2px solid #45a049;
                        border-radius: 5px;
                        padding: 8px;
                        font-size: 12px;
                    }
                    QPushButton:hover {
                        background-color: #45a049;
                    }
                """)
                self.ui.ocrPushButton.setToolTip(f"Escanejar ticket de {super_seleccionat}")
            else:
                self.ui.ocrPushButton.setEnabled(False)
                self.ui.ocrPushButton.setStyleSheet("""
                    QPushButton {
                        background-color: #CCCCCC;
                        color: #666666;
                        border: 2px solid #AAAAAA;
                        border-radius: 5px;
                        padding: 8px;
                        font-size: 12px;
                    }
                """)
                self.ui.ocrPushButton.setToolTip("Selecciona un supermercat primer")
        
        if hasattr(self.ui, 'buscarPushButton'):
            # Activar si hi ha un supermercat seleccionat
            if super_seleccionat:
                self.ui.buscarPushButton.setEnabled(True)
                self.ui.buscarPushButton.setStyleSheet("""
                    QPushButton {
                        background-color: #4CAF50;
                        color: white;
                        font-weight: bold;
                        border: 2px solid #45a049;
                        border-radius: 5px;
                        padding: 8px;
                        font-size: 12px;
                    }
                    QPushButton:hover {
                        background-color: #45a049;
                    }
                """)
                self.ui.buscarPushButton.setToolTip(f"Seleccionar ticket de {super_seleccionat}")
            else:
                self.ui.buscarPushButton.setEnabled(False)
                self.ui.buscarPushButton.setStyleSheet("""
                    QPushButton {
                        background-color: #CCCCCC;
                        color: #666666;
                        border: 2px solid #AAAAAA;
                        border-radius: 5px;
                        padding: 8px;
                        font-size: 12px;
                    }
                """)
                self.ui.buscarPushButton.setToolTip("Selecciona un supermercat primer")

    def processar_imatge_ticket_real(self):
        """Funció principal per processar imatges de tickets amb opció d'escaneig"""
        
        try:
            # Verificar que estem a Dia
            super_actual = self.ui.superComboBox.currentText().strip().lower()
            if 'dia' not in super_actual:
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.warning(
                    None, 
                    "Super incorrecte", 
                    f"El botó OCR només està disponible per a supermercats Dia.\n"
                    f"Super actual: {self.ui.superComboBox.currentText()}"
                )
                return
            
            # Crear diàleg d'opcions
            from PySide6.QtWidgets import QDialog, QVBoxLayout, QPushButton, QLabel, QHBoxLayout
            from PySide6.QtCore import Qt
            
            dialog_opcions = QDialog()
            dialog_opcions.setWindowTitle("Origen de la imatge")
            dialog_opcions.setFixedSize(400, 200)
            
            layout = QVBoxLayout()
            
            # Missatge
            label = QLabel("Com vols obtenir la imatge del ticket?")
            label.setAlignment(Qt.AlignCenter)
            label.setStyleSheet("font-size: 14px; font-weight: bold; margin: 10px;")
            layout.addWidget(label)
            
            # Botons
            btn_layout = QHBoxLayout()
            
            btn_fitxer = QPushButton("📁 Seleccionar fitxer")
            btn_fitxer.setMinimumHeight(50)
            btn_fitxer.setStyleSheet("""
                QPushButton {
                    background-color: #4CAF50;
                    color: white;
                    font-weight: bold;
                    font-size: 12px;
                    border-radius: 5px;
                    padding: 10px;
                }
                QPushButton:hover {
                    background-color: #45a049;
                }
            """)
            
            btn_escaneig = QPushButton("📷 Escanejar ticket")
            btn_escaneig.setMinimumHeight(50)
            btn_escaneig.setStyleSheet("""
                QPushButton {
                    background-color: #2196F3;
                    color: white;
                    font-weight: bold;
                    font-size: 12px;
                    border-radius: 5px;
                    padding: 10px;
                }
                QPushButton:hover {
                    background-color: #1976D2;
                }
            """)
            
            btn_layout.addWidget(btn_fitxer)
            btn_layout.addWidget(btn_escaneig)
            layout.addLayout(btn_layout)
            
            # Botó cancel·lar
            btn_cancel = QPushButton("❌ Cancel·lar")
            btn_cancel.setMinimumHeight(40)
            btn_cancel.clicked.connect(dialog_opcions.reject)
            layout.addWidget(btn_cancel)
            
            dialog_opcions.setLayout(layout)
            
            # Variables per capturar la selecció
            seleccio = {"opcio": None}
            
            def seleccionar_fitxer():
                seleccio["opcio"] = "fitxer"
                dialog_opcions.accept()
            
            def seleccionar_escaneig():
                seleccio["opcio"] = "escaneig"
                dialog_opcions.accept()
            
            btn_fitxer.clicked.connect(seleccionar_fitxer)
            btn_escaneig.clicked.connect(seleccionar_escaneig)
            
            # Mostrar diàleg
            result = dialog_opcions.exec()
            
            if result != QDialog.Accepted or not seleccio["opcio"]:
                return  # Usuari ha cancel·lat
            
            file_path = None
            
            if seleccio["opcio"] == "fitxer":
                # Opció 1: Seleccionar fitxer existent
                file_path = self._seleccionar_fitxer_imatge()
                
            elif seleccio["opcio"] == "escaneig":
                # Opció 2: Escanejar directament
                file_path = self._escanejar_ticket()
            
            if file_path and os.path.exists(file_path):
                print(f"📁 Imatge seleccionada: {file_path}")
                
                # Processar amb OCR
                if OCR_AVAILABLE:
                    self._processar_amb_ocr_real(file_path)
                else:
                    self._processar_amb_ocr_simulat(file_path)
                            
        except Exception as e:
            print(f"❌ Error en processar_imatge_ticket_real: {e}")
            import traceback
            traceback.print_exc()
            
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(None, "Error", f"Error processant imatge:\n{str(e)}")

    def _seleccionar_fitxer_imatge(self):
        """Seleccionar un fitxer d'imatge existent"""
        from PySide6.QtWidgets import QFileDialog
        
        # Directori per defecte: Tickets
        tickets_dir = r"E:\BD_Despeses\assets\tickets"
        
        # Crear el directori si no existeix
        import os
        if not os.path.exists(tickets_dir):
            os.makedirs(tickets_dir)
            print(f"📁 Creat directori de tickets: {tickets_dir}")
        
        file_path, _ = QFileDialog.getOpenFileName(
            None,
            "Seleccionar ticket del Dia",
            tickets_dir,
            "Imatges (*.png *.jpg *.jpeg *.bmp *.gif *.tiff *.pdf)"
        )
        
        return file_path

    def _escanejar_ticket(self):
        """Funció principal per escanejar - versió simplificada"""
        from PySide6.QtWidgets import QMessageBox, QFileDialog
        import subprocess
        import os
        
        # Crear diàleg d'opcions
        msg_box = QMessageBox()
        msg_box.setWindowTitle("Origen de la imatge")
        msg_box.setText("Com vols obtenir la imatge del ticket?")
        
        # Afegir botons personalitzats
        btn_escanejar = msg_box.addButton("📷 Escanejar ara", QMessageBox.ButtonRole.ActionRole)
        btn_fitxer = msg_box.addButton("📁 Seleccionar fitxer", QMessageBox.ButtonRole.ActionRole)
        btn_cancel = msg_box.addButton("❌ Cancel·lar", QMessageBox.ButtonRole.RejectRole)
        
        msg_box.exec()
        
        if msg_box.clickedButton() == btn_escanejar:
            # Opció 1: Escanejar
            try:
                # Obrir Windows Scan App
                subprocess.Popen(["start", "ms-scan:"], shell=True)
                
                QMessageBox.information(
                    None,
                    "Escaneig",
                    "1. Escaneja el ticket amb l'aplicació oberta\n"
                    "2. Guarda la imatge\n"
                    "3. Tanca l'aplicació\n"
                    "4. Selecciona el fitxer guardat"
                )
                
                file_path, _ = QFileDialog.getOpenFileName(
                    None,
                    "Seleccionar ticket escanejat",
                    os.path.expanduser("~/Pictures"),
                    "Imatges (*.png *.jpg *.jpeg)"
                )
                
                return file_path
                
            except Exception as e:
                QMessageBox.warning(None, "Error", f"No s'ha pogut escanejar: {e}")
                return None
                
        elif msg_box.clickedButton() == btn_fitxer:
            # Opció 2: Seleccionar fitxer existent
            file_path, _ = QFileDialog.getOpenFileName(
                None,
                "Seleccionar ticket",
                r"E:\BD_Despeses\assets\tickets",
                "Imatges (*.png *.jpg *.jpeg *.bmp *.gif)"
            )
            return file_path
        
        return None 
    
    def _ampliar_imatge(self, image_path):
        """Mostra la imatge en una finestra més gran"""
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel
        from PySide6.QtGui import QPixmap
        from PySide6.QtCore import Qt
        
        dialog = QDialog()
        dialog.setWindowTitle("Vista prèvia del ticket")
        dialog.resize(900, 700)
        
        layout = QVBoxLayout()
        label = QLabel()
        pixmap = QPixmap(image_path)
        
        if not pixmap.isNull():
            # Escalar mantenint aspect ratio, però permetent scroll si cal
            scaled_pixmap = pixmap.scaled(880, 660, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            label.setPixmap(scaled_pixmap)
            label.setAlignment(Qt.AlignCenter)
        
        layout.addWidget(label)
        dialog.setLayout(layout)
        dialog.exec()

    def _processar_amb_ocr_real(self, file_path):
        """Processar imatge amb OCR real i mostrar diàleg de selecció"""
        try:
            print(f"\n🔍 PROCESSANT IMATGE: {file_path}")
            print(f"📏 Mida del fitxer: {os.path.getsize(file_path)} bytes")
            
            processor = OCRProcessor('Dia')
            
            # Utilitza la versió definitiva
            resultat = processor.processar_ticket_dia_definitiu(file_path)

            print(f"📊 RESULTAT OCR:")
            print(f"   - Metadades: {resultat.get('metadades', {})}")
            print(f"   - Productes detectats: {len(resultat.get('productes', []))}")
            
            if resultat and resultat.get('productes'):
                self.mostrar_resultats_ocr_complet(
                    resultat.get('metadades', {}),
                    resultat['productes'],
                    resultat.get('text_ocr', ''),
                    file_path
                )
                # Quan es tanca el diàleg amb productes, no reactivar encara
                # (els productes s'importaran o es cancel·larà)
            else:
                from PySide6.QtWidgets import QMessageBox
                error_msg = "No s'han detectat productes al ticket."
                QMessageBox.warning(None, "Sense productes", error_msg)
                
                # 🔴🔴🔴 REACTIVAR BOTONS QUAN NO HI HA PRODUCTES
                self._reactivar_botons_ocr()
            
            return True
                
        except Exception as e:
            print(f"❌ Error en OCR real: {e}")
            import traceback
            traceback.print_exc()
            
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.critical(None, "Error OCR", f"Error processant la imatge:\n{str(e)}")
            
            # 🔴🔴🔴 REACTIVAR BOTONS TAMBÉ EN CAS D'ERROR
            self._reactivar_botons_ocr()
            return False
        
    def _obrir_formulari_ocr(self, productes, metadades):
        """Obre un formulari per mostrar i confirmar els productes detectats per OCR"""
        try:
            dialog = QDialog(self.view)
            dialog.setWindowTitle("Resultats OCR - Productes Detectats")
            dialog.setGeometry(100, 100, 800, 600)
            
            layout = QVBoxLayout()
            
            # Taula per mostrar productes
            table = QTableWidget(len(productes), 3)
            table.setHorizontalHeaderLabels(["Producte", "Preu", "Acció"])
            
            for i, producto in enumerate(productes):
                # Producte
                table.setItem(i, 0, QTableWidgetItem(producto['producte']))
                
                # Preu
                table.setItem(i, 1, QTableWidgetItem(f"{producto['preu']:.2f}€"))
                
                # Botó per afegir
                btn_afegir = QPushButton("Afegir")
                btn_afegir.clicked.connect(lambda checked, idx=i: self._afegir_producte_ocr(productes[idx]))
                table.setCellWidget(i, 2, btn_afegir)
            
            layout.addWidget(table)
            
            # Botó per afegir tots
            btn_tots = QPushButton("Afegir TOTS els productes")
            btn_tots.clicked.connect(lambda: self._afegir_tots_productes_ocr(productes))
            layout.addWidget(btn_tots)
            
            # Botó tancar
            btn_tancar = QPushButton("Tancar")
            btn_tancar.clicked.connect(dialog.close)
            layout.addWidget(btn_tancar)
            
            dialog.setLayout(layout)
            dialog.exec_()
            
        except Exception as e:
            print(f"❌ Error obrint formulari OCR: {e}")
            import traceback
            traceback.print_exc()
            
            # Com a fallback, mostrar per consola
            self._mostrar_resultats_consola(productes, metadades)

    def _afegir_producte_ocr(self, producto):
        """Afegeix un producte detectat per OCR a la taula"""
        try:
            pass
            # TODO: Aquí has de cridar el mètode que tens per afegir línies
            # Depèn de com funcionen els teus mètodes actuals
            
            # Exemple (ajusta als teus mètodes):
            # self.afegir_linia_compra(
            #     article=producto['nom_estandard'],
            #     preu=producto['preu'],
            #     quantitat=1,
            #     familia=producto['familia']
            # )
            
            
        except Exception as e:
            print(f"   ❌ Error afegint producte: {e}")

    def _afegir_tots_productes_ocr(self, productes):
        """Afegeix tots els productes detectats per OCR"""
        for producto in productes:
            self._afegir_producte_ocr(producto)
    
    def calcular_des_percentatge(self):
        """Calcular preu unitari amb descompte a partir del percentatge i total"""
        try:
            percentatge_text = self.ui.percentatgeLineEdit.text().strip()
            
            if not percentatge_text:
                return
                
            print(f"🔍 Calculant preu amb descompte del {percentatge_text}%")
            
            # Convertir percentatge
            percentatge = float(percentatge_text.replace(',', '.')) / 100
            
            # Obtenir quantitat i total DESITJAT
            quantitat_text = self.ui.quantitatLineEdit.text().replace(',', '.')
            total_desitjat_text = self.ui.totalLineaLineEdit.text().replace(',', '.')
            
            if not quantitat_text or not total_desitjat_text:
                print("⚠️ Cal introduir quantitat i total desitjat")
                return
                
            quantitat = float(quantitat_text)
            total_desitjat = float(total_desitjat_text)
            
            if quantitat <= 0:
                QMessageBox.warning(None, "Error", "Quantitat ha de ser > 0")
                return
                
            if percentatge >= 1:
                QMessageBox.warning(None, "Error", "Percentatge ha de ser < 100%")
                return
                
            # FÓRMULA: preu_unit = total / (quantitat × (1 - percentatge))
            preu_unit = total_desitjat / (quantitat * (1 - percentatge))
            
            # Promoció = preu_original - preu_reduït
            # on preu_original = total / quantitat
            # i preu_reduït = preu_unit calculat
            preu_original = total_desitjat / quantitat
            promocio = preu_original - preu_unit
            
            self.ui.preuUnitLineEdit.setText(f"{preu_unit:.2f}".replace('.', ','))
            self.ui.promocioLineEdit.setText(f"{abs(promocio):.2f}".replace('.', ','))
            
            print(f"✅ Calculat: Preu Unitari={preu_unit:.2f}, Promoció={abs(promocio):.2f}")
            
            # Recalcular total per verificar
            self.calcular_total_linia()
            
        except ValueError:
            QMessageBox.warning(None, "Error", "Valors no vàlids")
        except ZeroDivisionError:
            QMessageBox.warning(None, "Error", "Error en càlcul")
        except Exception as e:
            print(f"❌ Error: {e}")
            
    def netejar_tots_camps_formulari(self):
        """Netejar tots els camps del formulari (no només de línia)"""
        
        # Llista de tots els camps que volem netejar
        camps_a_netejar = [
            'pesLineEdit',
            'quantitatLineEdit', 
            'preuUnitLineEdit',
            'promocioLineEdit',
            'percentatgeLineEdit',
            'totalLineaLineEdit',
            'descompteLineEdit',
            # 'dataLineEdit',  # NO netejar la data, ja la posarem després
        ]
        
        for camp_nom in camps_a_netejar:
            if hasattr(self.ui, camp_nom):
                camp = getattr(self.ui, camp_nom)
                valor_antic = camp.text()
                camp.clear()
        
        # Netejar combobox
        self.ui.familiaCombobox.setCurrentIndex(-1)
        self.ui.articleCombobox.setCurrentIndex(-1)
        self.ui.articleCombobox.clear()
        
        # Netejar checkbox
        self.ui.rebostCheckBox.setChecked(False)

    def calcular_total_des_percentatge_i_total(self):
        """Calcular preu unitari i promoció quan es té Percentatge i Total FINAL"""
        try:
            # Verificar que tenim tot el necessari
            quantitat_text = self.ui.quantitatLineEdit.text().replace(',', '.')
            percentatge_text = self.ui.percentatgeLineEdit.text().replace(',', '.')
            total_final_text = self.ui.totalLineaLineEdit.text().replace(',', '.')
            
            print(f"🔍 Calculant amb: Quantitat={quantitat_text}, %={percentatge_text}, Total Final={total_final_text}")
            
            if not all([quantitat_text, percentatge_text, total_final_text]):
                print("⚠️ Falten dades per calcular")
                return
                
            # Convertir valors
            quantitat = float(quantitat_text)
            percentatge = float(percentatge_text) / 100  # 20 → 0.20
            total_final = float(total_final_text)  # Total que l'usuari vol pagar
            
            if quantitat <= 0:
                QMessageBox.warning(None, "Error", "Quantitat ha de ser > 0")
                return
                
            if percentatge >= 1:
                QMessageBox.warning(None, "Error", "Percentatge ha de ser < 100%")
                return
                
            # 🎯 OPCIÓ A: Usuari introdueix TOTAL FINAL (el que vol pagar)
            # 1. Calcular preu unitari a partir del total final
            #    preu_unit = total_final / quantitat
            preu_unit = total_final / quantitat
            
            # 2. Calcular el total original (abans del descompte)
            #    total_original = total_final / (1 - percentatge)
            total_original = total_final / (1 - percentatge)
            
            # 3. Calcular promoció (descompte aplicat)
            #    promocio = total_original - total_final
            promocio = total_original - total_final
            
            print(f"✅ Càlculs OPCIÓ A:")
            print(f"   Total Final (introduït): {total_final:.2f}€")
            print(f"   Preu Unitari: {total_final:.2f}€ / {quantitat} = {preu_unit:.2f}€")
            print(f"   Total Original: {total_final:.2f}€ / (1 - {percentatge:.2f}) = {total_original:.2f}€")
            print(f"   Promoció ({percentatge_text}%): {total_original:.2f}€ - {total_final:.2f}€ = {promocio:.2f}€")
            
            # Establir valors
            self.ui.preuUnitLineEdit.setText(f"{preu_unit:.2f}".replace('.', ','))
            self.ui.promocioLineEdit.setText(f"{promocio:.2f}".replace('.', ','))
            
            # El total final ja està establert (és el que l'usuari ha introduït)
            
        except ValueError as e:
            print(f"❌ Error en valors: {e}")
            QMessageBox.warning(None, "Error", f"Error en valors: {e}")
        except ZeroDivisionError:
            QMessageBox.warning(None, "Error", "Quantitat no pot ser 0")
        except Exception as e:
            print(f"❌ Error general: {e}")
            import traceback
            traceback.print_exc()    

    def calcular_si_percentatge_i_total(self):
        """Calcular automàticament si hi ha percentatge i total"""
        # Si hi ha percentatge i total, calcular
        if (self.ui.percentatgeLineEdit.text().strip() and 
            self.ui.totalLineaLineEdit.text().strip()):
            self.calcular_total_des_percentatge_i_total()

    def calcular_percentatge_simple(self):
        """Càlcul CORRECTE: Donat quantitat, percentatge i total final, calcular preu unitari i promoció"""
        try:
            # Obtenir valors
            quantitat_text = self.ui.quantitatLineEdit.text().replace(',', '.')
            percentatge_text = self.ui.percentatgeLineEdit.text().replace(',', '.')
            total_final_text = self.ui.totalLineaLineEdit.text().replace(',', '.')
            
            # Validar que tenim tot
            if not quantitat_text or not percentatge_text or not total_final_text:
                print("⚠️ Falten dades")
                return
                
            # Convertir a números
            quantitat = float(quantitat_text)
            percentatge = float(percentatge_text) / 100  # 20 → 0.20
            total_final = float(total_final_text)  # Total que l'usuari PAGA (amb descompte)
            
            if quantitat <= 0:
                QMessageBox.warning(None, "Error", "Quantitat ha de ser > 0")
                return
                
            if percentatge >= 1:
                QMessageBox.warning(None, "Error", "Percentatge ha de ser < 100%")
                return
                
            # 🎯 CÀLCULS CORRECTES:
            # 1. Total ORIGINAL (abans del descompte)
            total_original = total_final / (1 - percentatge)
            
            # 2. Preu Unitari ORIGINAL (abans del descompte)
            preu_unit_original = total_original / quantitat
            
            # 3. Promoció TOTAL
            promocio_total = total_original - total_final
            
            # 4. Promoció per unitat
            promocio_unit = promocio_total / quantitat
            
            # 5. Preu Unitari FINAL (amb descompte)
            preu_unit_final = preu_unit_original - promocio_unit

            # Establir valors als camps (mostrem el PREU ORIGINAL com a "Preu Unitari")
            self.ui.preuUnitLineEdit.setText(f"{preu_unit_original:.4f}".replace('.', ','))
            self.ui.promocioLineEdit.setText(f"{promocio_total:.4f}".replace('.', ','))
            
            # Verificació
            total_verificat = (preu_unit_original * quantitat) - promocio_total
            
        except ValueError as e:
            print(f"❌ Error en valors: {e}")
        except ZeroDivisionError as zde:
            print(f"❌ Error divisió per zero: {zde}")
            QMessageBox.warning(None, "Error", "Error en càlcul: quantitat 0 o percentatge 100%")
        except Exception as e:
            print(f"❌ Error inesperat: {e}")
            import traceback
            traceback.print_exc()

    def controlar_estat_ocr(self):
        """Controlar l'estat dels botons OCR quan es comencen a introduir dades"""
        
        # Si ja s'han introduït dades manualment, desactivar botons
        if self.dades_manual_introduides:
            if hasattr(self.ui, 'ocrPushButton') and self.ui.ocrPushButton.isEnabled():
                self.ui.ocrPushButton.setEnabled(False)
            if hasattr(self.ui, 'buscarPushButton') and self.ui.buscarPushButton.isEnabled():
                self.ui.buscarPushButton.setEnabled(False)
            return
        
        # Verificar si hi ha dades als camps
        camps_amb_dades = [
            self.ui.quantitatLineEdit.text().strip(),
            self.ui.preuUnitLineEdit.text().strip(),
            self.ui.percentatgeLineEdit.text().strip(),
            self.ui.promocioLineEdit.text().strip(),
            self.ui.totalLineaLineEdit.text().strip(),
            self.ui.articleCombobox.currentText().strip(),
            self.ui.familiaCombobox.currentText().strip()
        ]
        
        hi_ha_dades = any(camps_amb_dades)
        
        if hi_ha_dades:
            self.dades_manual_introduides = True
            if hasattr(self.ui, 'ocrPushButton'):
                self.ui.ocrPushButton.setEnabled(False)
            if hasattr(self.ui, 'buscarPushButton'):
                self.ui.buscarPushButton.setEnabled(False)

    def verificar_activacio_ocr(self):
        """Verificar si s'ha de reactivar el botó OCR"""
        if not hasattr(self.ui, 'ocrPushButton'):
            return
        
        # ✅ NO reactivar si ja s'han introduït dades manualment
        if self.dades_manual_introduides:
            print("⚠️ OCR no reactivat - dades manual introduïdes anteriorment")
            return
        
        # Verificar si tots els camps estan buits
        camps_buits = all([
            not self.ui.quantitatLineEdit.text().strip(),
            not self.ui.preuUnitLineEdit.text().strip(),
            not self.ui.percentatgeLineEdit.text().strip(),
            not self.ui.promocioLineEdit.text().strip(),
            not self.ui.totalLineaLineEdit.text().strip(),
            not self.ui.articleCombobox.currentText().strip(),
            not self.ui.familiaCombobox.currentText().strip()
        ])
        
        if camps_buits:
            self.activar_ocr_si_correspon()

    def desactivar_ocr_permanent(self):
        """Desactivar OCR de manera permanent fins nou ticket"""
        if hasattr(self.ui, 'ocrPushButton'):
            self.ui.ocrPushButton.setEnabled(False)
            self.ui.ocrPushButton.setStyleSheet("""
                QPushButton {
                    background-color: #CCCCCC;
                    color: #666666;
                    border: 2px solid #AAAAAA;
                    border-radius: 5px;
                    padding: 8px;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background-color: #BBBBBB;
                }
            """)
            self.ui.ocrPushButton.setToolTip(
                "OCR desactivat - S'estan introduint dades manualment en aquest ticket"
            )

    def activar_ocr_si_correspon(self):
        """Activar OCR només si és Dia i no hi ha dades manual introduïdes"""
        if not hasattr(self.ui, 'ocrPushButton'):
            return
        
        # Només activar si no s'han introduït dades manualment
        if not self.dades_manual_introduides:
            super_actual = self.ui.superComboBox.currentText() or ""
            ocr_compatible = 'dia' in super_actual.strip().lower()
            
            if ocr_compatible:
                self.ui.ocrPushButton.setEnabled(True)
                self.ui.ocrPushButton.setStyleSheet("""
                    QPushButton {
                        background-color: #4CAF50;
                        color: white;
                        font-weight: bold;
                        border: 2px solid #45a049;
                        border-radius: 5px;
                        padding: 5px;
                    }
                    QPushButton:hover {
                        background-color: #45a049;
                    }
                """)
                self.ui.ocrPushButton.setToolTip(f"Processar ticket de {self.ui.superComboBox.currentText()}")
            else:
                self.ui.ocrPushButton.setEnabled(False)

    def editar_producte_ocr(self, item, llista, productes_local):
        """Editar un producte detectat per OCR abans d'importar"""
        
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                                        QComboBox, QPushButton, QDoubleSpinBox, 
                                        QSpinBox, QMessageBox)
        
        producte_data = item.data(Qt.UserRole)
        if not producte_data:
            return
        
        dialog = QDialog()
        dialog.setWindowTitle(f"Editar producte: {producte_data.get('producte', '')}")
        dialog.setMinimumWidth(550)
        dialog.setMinimumHeight(450)
        
        layout = QVBoxLayout()
        
        # Família
        familia_layout = QHBoxLayout()
        familia_layout.addWidget(QLabel("Família:"))
        familia_combo = QComboBox()
        from config.llistes import obtenir_families_compres
        families = obtenir_families_compres()
        familia_combo.addItems(sorted(families))
        familia_actual = producte_data.get('familia', '')
        if familia_actual in families:
            familia_combo.setCurrentText(familia_actual)
        familia_layout.addWidget(familia_combo)
        layout.addLayout(familia_layout)
        
        # Producte
        producte_layout = QHBoxLayout()
        producte_layout.addWidget(QLabel("Producte:"))
        producte_combo = QComboBox()
        producte_combo.setEditable(True)
        producte_combo.addItem("-- Seleccionar producte --")
        producte_layout.addWidget(producte_combo)
        layout.addLayout(producte_layout)
        
        def actualitzar_productes_per_familia():
            producte_combo.clear()
            producte_combo.addItem("-- Seleccionar producte --")
            familia_seleccionada = familia_combo.currentText()
            if not familia_seleccionada:
                return
            from config.llistes import obtenir_articles_per_familia
            articles = obtenir_articles_per_familia(familia_seleccionada)
            if articles:
                for article in sorted(articles):
                    producte_combo.addItem(article)
            # 🔴🔴🔴 SELECCIONAR EL PRODUCTE ACTUAL AUTOMÀTICAMENT
            nom_actual = producte_data.get('producte', '')
            if nom_actual:
                index = producte_combo.findText(nom_actual)
                if index >= 0:
                    producte_combo.setCurrentIndex(index)
                else:
                    # Si no troba el producte exacte, posar-lo com a text editable
                    producte_combo.setEditText(nom_actual)
        
        familia_combo.currentTextChanged.connect(actualitzar_productes_per_familia)
        actualitzar_productes_per_familia()
        
        # Quantitat
        quant_layout = QHBoxLayout()
        quant_layout.addWidget(QLabel("Quantitat:"))
        quant_spin = QSpinBox()
        quant_spin.setRange(1, 99)
        quant_spin.setValue(producte_data.get('quantitat_detectada', 1))
        quant_layout.addWidget(quant_spin)
        layout.addLayout(quant_layout)
        
        # 🔴🔴🔴 PREU ORIGINAL (sense descompte)
        preu_original_layout = QHBoxLayout()
        preu_original_layout.addWidget(QLabel("Preu original (€):"))
        preu_original_spin = QDoubleSpinBox()
        preu_original_spin.setRange(0.01, 999.99)
        preu_original_spin.setValue(producte_data.get('preu_original', producte_data.get('preu', 0)))
        preu_original_spin.setSingleStep(0.01)
        preu_original_layout.addWidget(preu_original_spin)
        layout.addLayout(preu_original_layout)
        
        # 🔴🔴🔴 DESCOMPTE (en €)
        descompte_layout = QHBoxLayout()
        descompte_layout.addWidget(QLabel("Descompte (€):"))
        descompte_spin = QDoubleSpinBox()
        descompte_spin.setRange(0, 999.99)
        descompte_spin.setValue(producte_data.get('descompte_aplicat', 0))
        descompte_spin.setSingleStep(0.01)
        descompte_layout.addWidget(descompte_spin)
        layout.addLayout(descompte_layout)
        
        # Mostrar el preu final calculat (només informatiu)
        preu_final_label = QLabel()
        layout.addWidget(preu_final_label)
        
        def actualitzar_preu_final():
            preu_original = preu_original_spin.value()
            descompte = descompte_spin.value()
            quantitat = quant_spin.value()
            preu_final = (quantitat * preu_original) - descompte
            preu_final_label.setText(f"💰 Preu final: {preu_final:.2f}€ (per {quantitat} unitats)")
        
        preu_original_spin.valueChanged.connect(actualitzar_preu_final)
        descompte_spin.valueChanged.connect(actualitzar_preu_final)
        quant_spin.valueChanged.connect(actualitzar_preu_final)
        actualitzar_preu_final()
        
        # Informació original
        info_layout = QHBoxLayout()
        info_layout.addWidget(QLabel("🔄 Original:"))
        info_label = QLabel(producte_data.get('producte_brut', ''))
        info_label.setStyleSheet("color: gray; font-style: italic;")
        info_layout.addWidget(info_label)
        layout.addLayout(info_layout)
        
        # Botons
        button_layout = QHBoxLayout()
        btn_guardar = QPushButton("💾 Guardar canvis")
        btn_guardar.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 8px; border-radius: 4px;")
        btn_cancelar = QPushButton("❌ Cancel·lar")
        btn_cancelar.setStyleSheet("background-color: #f44336; color: white; font-weight: bold; padding: 8px; border-radius: 4px;")
        
        def guardar_canvis():
            nou_producte = producte_combo.currentText().strip()
            if nou_producte == "-- Seleccionar producte --" or not nou_producte:
                QMessageBox.warning(dialog, "Error", "Has de seleccionar un producte")
                return
            
            # 🔴🔴🔴 Guardar PREU ORIGINAL i DESCOMPTE per separat
            preu_original_valor = preu_original_spin.value()
            descompte_valor = descompte_spin.value()
            
            producte_data['producte'] = nou_producte
            producte_data['nom_estandard'] = nou_producte
            producte_data['familia'] = familia_combo.currentText()
            producte_data['quantitat_detectada'] = quant_spin.value()
            producte_data['preu_original'] = preu_original_valor
            producte_data['descompte_aplicat'] = descompte_valor
            producte_data['preu'] = preu_original_valor - descompte_valor  # Preu final per unitat
            
            # Actualitzar la llista original
            for i, prod in enumerate(productes_local):
                if prod.get('numero_linia') == producte_data.get('numero_linia'):
                    productes_local[i] = producte_data.copy()
                    break
            
            self._actualitzar_item_llista(item, producte_data)
            dialog.accept()
        
        btn_guardar.clicked.connect(guardar_canvis)
        btn_cancelar.clicked.connect(dialog.reject)
        
        button_layout.addWidget(btn_guardar)
        button_layout.addWidget(btn_cancelar)
        layout.addLayout(button_layout)
        
        dialog.setLayout(layout)
        dialog.exec()

    def _actualitzar_item_llista(self, item, producte_data):
        """Actualitza el text d'un ítem després d'editar"""
        nom_producte = producte_data.get('producte', 'Desconegut')
        preu = producte_data.get('preu', 0)
        familia = producte_data.get('familia', '')
        descompte = producte_data.get('descompte_aplicat', 0)
        nom_original = producte_data.get('producte_brut', '')
        
        # Determinar icona (per simplicitat, posem ✅)
        icona = "✅"
        
        # Reconstruir el text
        if descompte > 0:
            preu_original = producte_data.get('preu_original', preu + descompte)
            item_text = f"   . {icona} {nom_producte} | 💰 ~~{preu_original:.2f}€~~ 🔖 -{descompte:.2f}€ → {preu:.2f}€ | 📁 {familia}"
        else:
            item_text = f"   . {icona} {nom_producte} | 💰 {preu:.2f}€ | 📁 {familia}"
        
        if nom_original and nom_original.upper() != nom_producte.upper():
            item_text += f"\n    ⬤ {nom_original[:40]}"
        
        item.setText(item_text)
        item.setData(Qt.UserRole, producte_data)

    def configurar_camps_editables(self, editable=False):
        """Configurar quins camps són editables (evitant doble clic)"""
        
        # 🔴 Camps de text - usar setReadOnly en lloc de setEnabled
        camps_text = [
            self.ui.pesLineEdit,
            self.ui.quantitatLineEdit,
            self.ui.preuUnitLineEdit,
            self.ui.promocioLineEdit,
            self.ui.percentatgeLineEdit,
            self.ui.totalLineaLineEdit,
            self.ui.numLineaLineEdit,
        ]
        
        for camp in camps_text:
            camp.setReadOnly(not editable)  # Si no editable, només lectura
        
        # 🔴 Combobox - deshabilitar edició i selecció
        self.ui.familiaCombobox.setEnabled(editable)
        self.ui.familiaCombobox.setEditable(editable)  # No es pot escriure si no editable
        
        self.ui.articleCombobox.setEnabled(editable)
        self.ui.articleCombobox.setEditable(editable)  # No es pot escriure si no editable
        
        # 🔴 Checkbox
        self.ui.rebostCheckBox.setEnabled(editable)
        
        # 🔴 Botons d'acció
        self.ui.introLineaPushButton.setEnabled(editable)
        self.ui.borrarModificacionsPushButton.setEnabled(editable)
        
        # El botó de modificacions sempre ha d'estar actiu si hi ha línies
        self.ui.modificacionsPushButton.setEnabled(len(self.current_lines) > 0)
        
        # Altres botons que han de romandre actius
        self.ui.introPushButton.setEnabled(editable)  # Botó aplicar descompte

    def configurar_taula_lectura(self, nomes_lectura=True):
        """Configurar si la taula de productes és de només lectura"""
        
        if nomes_lectura:
            # Desactivar edició directa a la taula
            self.ui.llistaProductesTable.setEditTriggers(
                QTableWidget.EditTrigger.NoEditTriggers
            )
        else:
            # Permetre edició (si es vol)
            self.ui.llistaProductesTable.setEditTriggers(
                QTableWidget.EditTrigger.DoubleClicked |
                QTableWidget.EditTrigger.EditKeyPressed
        )
            
    def _afegir_linia_des_de_dades(self, nom_article, familia, preu_original, quantitat, 
                               descompte=0, percentatge=0, pes_grams=None, es_rebost=False):
        """Afegir una línia directament a la taula sense utilitzar els camps"""
        
        preu_final = (quantitat * preu_original) - descompte
        
        # SI TENIM PES, EL GUARDEM
        pes_text = str(pes_grams) if pes_grams else ''

        # 🔴 Assegurar que percentatge és enter
        # if isinstance(percentatge, float):
        #     percentatge = int(percentatge)
        
        # Crear dades de la línia
        linea_data = {
            'familia': familia,
            'article': nom_article,
            'pes': pes_text,
            'quantitat': quantitat,
            'preuUnit': preu_original,
            'preu_original': preu_original,
            'percentatge': percentatge,  
            'prom': descompte,
            'totLinea': preu_final,
            'rebost': 'Sí' if es_rebost else 'No'
        }
        
        # Afegir a la llista interna
        self.current_lines.append(linea_data)
        
        # Afegir a la taula
        row_position = self.ui.llistaProductesTable.rowCount()
        self.ui.llistaProductesTable.insertRow(row_position)
        
        # OMPLIR LA TAULA
        self.ui.llistaProductesTable.setItem(row_position, 0, QTableWidgetItem(familia))
        self.ui.llistaProductesTable.setItem(row_position, 1, QTableWidgetItem(nom_article))
        self.ui.llistaProductesTable.setItem(row_position, 2, QTableWidgetItem(pes_text))
        self.ui.llistaProductesTable.setItem(row_position, 3, QTableWidgetItem(str(quantitat)))
        self.ui.llistaProductesTable.setItem(row_position, 4, QTableWidgetItem(f"{preu_original:.2f}".replace('.', ',')))
        # 🔴 Percentatge sense decimals
        self.ui.llistaProductesTable.setItem(row_position, 5, QTableWidgetItem(str(percentatge)))
        self.ui.llistaProductesTable.setItem(row_position, 6, QTableWidgetItem(f"{descompte:.2f}".replace('.', ',')))
        self.ui.llistaProductesTable.setItem(row_position, 7, QTableWidgetItem(f"{preu_final:.2f}".replace('.', ',')))
        
        # 🔴🔴🔴 TORNAR A "SÍ"/"NO" EN TEXT
        self.ui.llistaProductesTable.setItem(row_position, 8, QTableWidgetItem('Sí' if es_rebost else 'No'))

        # 🔴 VERIFICACIÓ: El total ha de ser quantitat * preu_original - descompte
        total_verificat = (quantitat * preu_original) - descompte
        if abs(total_verificat - preu_final) > 0.01:
            print(f"⚠️ Error de càlcul: {total_verificat} vs {preu_final}")
        
        # Actualitzar totals
        self.actualitzar_desglossament()
        self.actualitzar_total_ticket()
       
        # Activar elements si és la primera línia
        if len(self.current_lines) == 1:
            self.activar_elements_ticket()
            
        print(f"✅ Producte afegit: {nom_article} | Preu: {preu_original:.2f} | %: {percentatge} | Descompte: {descompte:.2f} | Total: {preu_final:.2f}")

    def _on_item_table_changed(self, item):
        """Quan es modifica un element de la taula - AMB BLOQUEIG PER EVITAR RECURSIÓ"""
        
        # 🔴 EVITAR RECURSIÓ INFINITA
        if self._bloquejar_events_taula:
            return
        
        row = item.row()
        col = item.column()
        
        # Només processar si estem en mode modificacions
        if not self.mode_modificacions:
            return
        
        # Obtenir tots els valors actuals de la fila
        valors = self._obtenir_valors_fila(row)
        if not valors:
            return
        
        # 🔴 BLOQUEJAR ESDEVENIMENTS
        self._bloquejar_events_taula = True
        
        try:
            # Recalcular segons la columna modificada
            nous_valors = self._recalcular_fila(valors, col)
            
            # Actualitzar la fila amb els nous valors
            self._actualitzar_fila(row, nous_valors)
            
            # Actualitzar dades internes
            self._actualitzar_dades_internes(row)
            
            # Actualitzar totals globals
            self.actualitzar_total_ticket()
            self.actualitzar_desglossament()
            
            print(f"✅ Fila {row} actualitzada correctament")
            
        except Exception as e:
            print(f"❌ Error processant canvi a fila {row}: {e}")
            import traceback
            traceback.print_exc()
        finally:
            # 🔴 DESBLOQUEJAR ESDEVENIMENTS
            self._bloquejar_events_taula = False

    def _obtenir_valors_fila(self, row):
        """Obtenir tots els valors numèrics d'una fila"""
        try:
            # Mapes de columnes per nom (fàcil de modificar)
            columnes = {
                'quantitat': 3,
                'preu_unit': 4,
                'percentatge': 5,
                'promocio': 6,
                'total': 7
            }
            
            valors = {}
            for nom, idx in columnes.items():
                item = self.ui.llistaProductesTable.item(row, idx)
                if item and item.text():
                    # Convertir text a float (gestionant comes decimals)
                    text = item.text().replace(',', '.')
                    try:
                        valors[nom] = float(text)
                    except ValueError:
                        valors[nom] = 0.0
                else:
                    valors[nom] = 0.0
            
            # Afegir metadades (ARA PASSEM 'col' CORRECTAMENT)
            valors['fila'] = row
            # Aquesta línia donava error - l'eliminem perquè 'col' no està definida aquí
            # valors['col_modificada'] = self._map_columna_a_nom(col)
            
            return valors
        except Exception as e:
            print(f"❌ Error obtenint valors fila {row}: {e}")
            return None

    def _map_columna_a_nom(self, col):
        """Convertir índex de columna a nom"""
        mapa = {
            3: 'quantitat',
            4: 'preu_unit',
            5: 'percentatge',
            6: 'promocio',
            7: 'total'
        }
        return mapa.get(col, 'desconegut')

    def _recalcular_fila(self, valors, col_modificada):
        """Recalcular els valors d'una fila de manera genèrica"""
        
        # Desempaquetar valors
        q = valors.get('quantitat', 0)
        p = valors.get('preu_unit', 0)
        perc = valors.get('percentatge', 0)
        prom = valors.get('promocio', 0)
        total = valors.get('total', 0)
        
        # 🔴 ARA 'col_modificada' ES REP COM A PARÀMETRE
        nom_col = self._map_columna_a_nom(col_modificada)
        
        # Inicialitzar variables
        total_nou = total
        prom_nova = prom
        perc_nou = perc
        
        # 🔴 LÒGICA DE NEGOCI - Independent dels números de columna
        
        # Cas 1: S'ha modificat la QUANTITAT
        if nom_col == 'quantitat':
            # Mantenir preu i percentatge, recalcular total i promoció
            if perc > 0:
                # Amb percentatge
                total_nou = q * p * (1 - perc/100)
                prom_nova = (q * p) - total_nou
            else:
                # Sense percentatge, mantenir promoció
                total_nou = (q * p) - prom
                prom_nova = prom
        
        # Cas 2: S'ha modificat el PREU UNITARI
        elif nom_col == 'preu_unit':
            if perc > 0:
                # Amb percentatge
                total_nou = q * p * (1 - perc/100)
                prom_nova = (q * p) - total_nou
            else:
                # Sense percentatge
                total_nou = q * p
                prom_nova = 0
        
        # Cas 3: S'ha modificat el PERCENTATGE
        elif nom_col == 'percentatge':
            if q > 0 and p > 0:
                total_nou = q * p * (1 - perc/100)
                prom_nova = (q * p) - total_nou
            else:
                total_nou = total
                prom_nova = prom
        
        # Cas 4: S'ha modificat la PROMOCIÓ
        elif nom_col == 'promocio':
            total_nou = (q * p) - prom
            if q * p > 0:
                perc_nou = (prom / (q * p)) * 100
            else:
                perc_nou = 0
        
        # Cas 5: S'ha modificat el TOTAL (no hauria de passar perquè no és editable)
        else:
            # Retornar els valors originals
            return valors
        
        # Crear diccionari amb els nous valors
        nous_valors = {
            'quantitat': q,
            'preu_unit': p,
            'percentatge': perc_nou if nom_col == 'promocio' else perc,
            'promocio': prom_nova if nom_col != 'promocio' else prom,
            'total': total_nou
        }
        
        # Assegurar que els valors tenen sentit
        nous_valors['percentatge'] = max(0, min(100, nous_valors['percentatge']))
        nous_valors['promocio'] = max(0, nous_valors['promocio'])
        nous_valors['total'] = max(0, nous_valors['total'])
        
        return nous_valors

    def _actualitzar_fila(self, row, valors):
        """Actualitzar una fila amb els nous valors - SENSE DISPARAR ESDEVENIMENTS"""
        try:
            # Actualitzar quantitat (col 3)
            item_q = self.ui.llistaProductesTable.item(row, 3)
            if item_q:
                # 🔴 Bloquejar temporalment el signal
                self.ui.llistaProductesTable.blockSignals(True)
                item_q.setText(str(valors['quantitat']))
                self.ui.llistaProductesTable.blockSignals(False)
            
            # Actualitzar preu unitari (col 4)
            item_p = self.ui.llistaProductesTable.item(row, 4)
            if item_p:
                self.ui.llistaProductesTable.blockSignals(True)
                item_p.setText(f"{valors['preu_unit']:.2f}".replace('.', ','))
                self.ui.llistaProductesTable.blockSignals(False)
            
            # Actualitzar percentatge (col 5)
            item_perc = self.ui.llistaProductesTable.item(row, 5)
            if item_perc:
                self.ui.llistaProductesTable.blockSignals(True)
                # Percentatge sense decimals
                item_perc.setText(f"{valors['percentatge']:.0f}".replace('.', ','))
                self.ui.llistaProductesTable.blockSignals(False)
            
            # Actualitzar promoció (col 6)
            item_prom = self.ui.llistaProductesTable.item(row, 6)
            if item_prom:
                self.ui.llistaProductesTable.blockSignals(True)
                item_prom.setText(f"{valors['promocio']:.2f}".replace('.', ','))
                self.ui.llistaProductesTable.blockSignals(False)
            
            # Actualitzar total (col 7)
            item_total = self.ui.llistaProductesTable.item(row, 7)
            if item_total:
                self.ui.llistaProductesTable.blockSignals(True)
                item_total.setText(f"{valors['total']:.2f}".replace('.', ','))
                # Assegurar que el total no sigui editable
                item_total.setFlags(item_total.flags() & ~Qt.ItemIsEditable)
                self.ui.llistaProductesTable.blockSignals(False)
            
        except Exception as e:
            print(f"❌ Error actualitzant fila {row}: {e}")
            self.ui.llistaProductesTable.blockSignals(False)

    def _recalcular_total_fila(self, row):
        """Recalcular mantenint el total FIXE"""
        try:
            # Obtenir valors de la taula
            quantitat_item = self.ui.llistaProductesTable.item(row, 3)
            preu_item = self.ui.llistaProductesTable.item(row, 4)
            percentatge_item = self.ui.llistaProductesTable.item(row, 5)
            promo_item = self.ui.llistaProductesTable.item(row, 6)
            total_item = self.ui.llistaProductesTable.item(row, 7)
            
            if not quantitat_item or not total_item:
                return
            
            quantitat = float(quantitat_item.text().replace(',', '.'))
            total_final = float(total_item.text().replace(',', '.'))  # 🔴 AQUEST ÉS EL VALOR FIX
            
            # 🔴 CAS 1: S'HA MODIFICAT EL PERCENTATGE
            if percentatge_item and percentatge_item.text() and self._ultima_columna_editada == 5:
                percentatge_int = int(float(percentatge_item.text().replace(',', '.')))
                percentatge = percentatge_int / 100.0
                
                # Assegurar que el percentatge es mostra sense decimals
                percentatge_item.setText(str(percentatge_int))
                
                if quantitat > 0 and (1 - percentatge) != 0:
                    # 🔴 FÓRMULA: Preu Original = Total Final / (Quantitat × (1 - percentatge))
                    preu_original = total_final / (quantitat * (1 - percentatge))
                    
                    # 🔴 FÓRMULA: Descompte = (Quantitat × Preu Original) - Total Final
                    descompte = (quantitat * preu_original) - total_final
                    
                    # Actualitzar Preu Unitari (columna 4)
                    if preu_item:
                        preu_item.setText(f"{preu_original:.2f}".replace('.', ','))
                    else:
                        preu_item = QTableWidgetItem(f"{preu_original:.2f}".replace('.', ','))
                        self.ui.llistaProductesTable.setItem(row, 4, preu_item)
                    
                    # Actualitzar Promo (columna 6)
                    if promo_item:
                        promo_item.setText(f"{descompte:.2f}".replace('.', ','))
                    else:
                        promo_item = QTableWidgetItem(f"{descompte:.2f}".replace('.', ','))
                        self.ui.llistaProductesTable.setItem(row, 6, promo_item)
                    
                    # 🔴 VERIFICACIÓ: El total ha de seguir sent el mateix
                    total_verificat = (quantitat * preu_original) - descompte
                    if abs(total_verificat - total_final) > 0.01:
                        print(f"⚠️ Error de càlcul: {total_verificat} vs {total_final}")
                    
                    print(f"✅ Percentatge {percentatge_int}% → Preu Original: {preu_original:.2f}, Descompte: {descompte:.2f}, Total: {total_final:.2f} (fix)")
            
            # 🔴 CAS 2: S'HA MODIFICAT EL PREU UNITARI
            elif preu_item and self._ultima_columna_editada == 4:
                preu_original = float(preu_item.text().replace(',', '.'))
                
                # Obtenir percentatge actual
                percentatge_int = 0
                if percentatge_item and percentatge_item.text():
                    percentatge_int = int(float(percentatge_item.text().replace(',', '.')))
                percentatge = percentatge_int / 100.0
                
                # 🔴 Calcular el total que hauria de ser
                if percentatge > 0:
                    # Amb percentatge: total_final = quantitat × preu_original × (1 - percentatge)
                    total_calculat = quantitat * preu_original * (1 - percentatge)
                    descompte = (quantitat * preu_original) - total_calculat
                else:
                    # Sense percentatge
                    total_calculat = quantitat * preu_original
                    descompte = 0
                
                # Actualitzar total (aquest SÍ que canvia)
                if total_item:
                    total_item.setText(f"{total_calculat:.2f}".replace('.', ','))
                
                # Actualitzar promo
                if promo_item:
                    promo_item.setText(f"{descompte:.2f}".replace('.', ','))
                
                print(f"✅ Preu Unitari canviat → Total nou: {total_calculat:.2f}")
            
            # 🔴 CAS 3: S'HA MODIFICAT LA PROMOCIÓ
            elif promo_item and self._ultima_columna_editada == 6:
                descompte = float(promo_item.text().replace(',', '.'))
                preu_original = float(preu_item.text().replace(',', '.')) if preu_item else 0
                
                # Calcular nou total
                total_calculat = (quantitat * preu_original) - descompte
                
                # Calcular percentatge
                if (quantitat * preu_original) > 0:
                    percentatge_calculat = (descompte / (quantitat * preu_original)) * 100
                    if percentatge_item:
                        percentatge_item.setText(f"{percentatge_calculat:.0f}".replace('.', ','))
                
                # Actualitzar total
                if total_item:
                    total_item.setText(f"{total_calculat:.2f}".replace('.', ','))
            
            # Assegurar que el total no sigui editable
            if total_item:
                total_item.setFlags(total_item.flags() & ~Qt.ItemIsEditable)
            
            # Actualitzar totals globals
            self.actualitzar_total_ticket()
            
        except Exception as e:
            print(f"Error recalcular total: {e}")
            import traceback
            traceback.print_exc()

    def _actualitzar_dades_internes(self, row):
        """Actualitzar self.current_lines amb els valors de la taula"""
        if row >= len(self.current_lines):
            return
        
        try:
            self.current_lines[row]['pes'] = self.ui.llistaProductesTable.item(row, 2).text() if self.ui.llistaProductesTable.item(row, 2) else ''
            self.current_lines[row]['quantitat'] = float(self.ui.llistaProductesTable.item(row, 3).text().replace(',', '.')) if self.ui.llistaProductesTable.item(row, 3) else 0
            self.current_lines[row]['preuUnit'] = float(self.ui.llistaProductesTable.item(row, 4).text().replace(',', '.')) if self.ui.llistaProductesTable.item(row, 4) else 0
            # 🔴 Guardar percentatge com a enter
            if self.ui.llistaProductesTable.item(row, 5) and self.ui.llistaProductesTable.item(row, 5).text():
                self.current_lines[row]['percentatge'] = int(float(self.ui.llistaProductesTable.item(row, 5).text().replace(',', '.')))
            else:
                self.current_lines[row]['percentatge'] = 0
            self.current_lines[row]['prom'] = float(self.ui.llistaProductesTable.item(row, 6).text().replace(',', '.')) if self.ui.llistaProductesTable.item(row, 6) else 0
            self.current_lines[row]['totLinea'] = float(self.ui.llistaProductesTable.item(row, 7).text().replace(',', '.')) if self.ui.llistaProductesTable.item(row, 7) else 0
            self.current_lines[row]['rebost'] = self.ui.llistaProductesTable.item(row, 8).text() if self.ui.llistaProductesTable.item(row, 8) else 'No'
        except Exception as e:
            print(f"Error actualitzant dades internes: {e}")

    def guardar_modificacions_linia(self):
        """Guardar els canvis a la línia seleccionada"""
        if not self.mode_modificacions:
            return
        
        current_row = self.ui.llistaProductesTable.currentRow()
        if current_row < 0:
            QMessageBox.warning(None, "Error", "Selecciona una línia per guardar")
            return
        
        # Obtenir dades dels camps
        try:
            familia = self.ui.familiaCombobox.currentText()
            article = self.ui.articleCombobox.currentText()
            pes = self.ui.pesLineEdit.text()
            quantitat = float(self.ui.quantitatLineEdit.text().replace(',', '.'))
            preu_unit = float(self.ui.preuUnitLineEdit.text().replace(',', '.'))
            percentatge = float(self.ui.percentatgeLineEdit.text().replace(',', '.'))
            promocio = float(self.ui.promocioLineEdit.text().replace(',', '.'))
            total_linea = float(self.ui.totalLineaLineEdit.text().replace(',', '.'))
            rebost = "Sí" if self.ui.rebostCheckBox.isChecked() else "No"
            
            # Actualitzar la línia existent
            linea_data = {
                'familia': familia,
                'article': article,
                'pes': pes,
                'quantitat': quantitat,
                'preuUnit': preu_unit,
                'percentatge': percentatge,
                'prom': promocio,
                'totLinea': total_linea,
                'rebost': rebost
            }
            
            # Actualitzar llista interna
            self.current_lines[current_row] = linea_data
            
            # Actualitzar taula
            self.ui.llistaProductesTable.item(current_row, 0).setText(familia)
            self.ui.llistaProductesTable.item(current_row, 1).setText(article)
            self.ui.llistaProductesTable.item(current_row, 2).setText(pes)
            self.ui.llistaProductesTable.item(current_row, 3).setText(str(quantitat))
            self.ui.llistaProductesTable.item(current_row, 4).setText(f"{preu_unit:.2f}".replace('.', ','))
            self.ui.llistaProductesTable.item(current_row, 5).setText(f"{percentatge:.2f}".replace('.', ','))
            self.ui.llistaProductesTable.item(current_row, 6).setText(f"{promocio:.2f}".replace('.', ','))
            self.ui.llistaProductesTable.item(current_row, 7).setText(f"{total_linea:.2f}".replace('.', ','))
            self.ui.llistaProductesTable.item(current_row, 8).setText(rebost)
            
            # Netejar camps
            self.netejar_camps_linia()
            
            # Actualitzar totals
            self.actualitzar_total_ticket()
            self.actualitzar_desglossament()
            
            print(f"✅ Línia {current_row} actualitzada correctament")
            
        except Exception as e:
            QMessageBox.warning(None, "Error", f"Error guardant modificacions: {str(e)}")   

    def guardar_tots_canvis_taula(self):
        """Guardar els canvis de la taula a la llista interna"""
        for row in range(self.ui.llistaProductesTable.rowCount()):
            if row < len(self.current_lines):
                try:
                    # Llegir valors de la taula
                    quantitat = float(self.ui.llistaProductesTable.item(row, 3).text().replace(',', '.'))
                    preu = float(self.ui.llistaProductesTable.item(row, 4).text().replace(',', '.'))
                    percentatge = float(self.ui.llistaProductesTable.item(row, 5).text().replace(',', '.'))
                    promo = float(self.ui.llistaProductesTable.item(row, 6).text().replace(',', '.'))
                    total = float(self.ui.llistaProductesTable.item(row, 7).text().replace(',', '.'))
                    
                    # Actualitzar llista interna
                    self.current_lines[row]['quantitat'] = quantitat
                    self.current_lines[row]['preuUnit'] = preu
                    self.current_lines[row]['percentatge'] = percentatge
                    self.current_lines[row]['prom'] = promo
                    self.current_lines[row]['totLinea'] = total
                    
                except Exception as e:
                    print(f"Error fila {row}: {e}")
        
        # Actualitzar totals
        self.actualitzar_total_ticket()
        self.actualitzar_desglossament()

    def descartar_canvis_taula(self):
        """Restaurar la taula des de la llista interna"""
        for row, linea in enumerate(self.current_lines):
            if row < self.ui.llistaProductesTable.rowCount():
                self.ui.llistaProductesTable.item(row, 3).setText(str(linea['quantitat']))
                self.ui.llistaProductesTable.item(row, 4).setText(f"{linea['preuUnit']:.2f}".replace('.', ','))
                self.ui.llistaProductesTable.item(row, 5).setText(f"{linea.get('percentatge', 0):.0f}".replace('.', ','))
                self.ui.llistaProductesTable.item(row, 6).setText(f"{linea['prom']:.2f}".replace('.', ','))
                self.ui.llistaProductesTable.item(row, 7).setText(f"{linea['totLinea']:.2f}".replace('.', ','))

    def _desactivar_botons_ocr_durant_processament(self):
        """Desactivar botons OCR durant el processament"""
        self._processant_ocr = True
        
        if hasattr(self.ui, 'ocrPushButton'):
            self.ui.ocrPushButton.setEnabled(False)
            self.ui.ocrPushButton.setStyleSheet("""
                QPushButton {
                    background-color: #CCCCCC;
                    color: #666666;
                    border: 2px solid #AAAAAA;
                    border-radius: 5px;
                    padding: 5px;
                }
            """)
            self.ui.ocrPushButton.setToolTip("Processant ticket...")
        
        if hasattr(self.ui, 'buscarPushButton'):
            self.ui.buscarPushButton.setEnabled(False)
            self.ui.buscarPushButton.setStyleSheet("""
                QPushButton {
                    background-color: #CCCCCC;
                    color: #666666;
                    border: 2px solid #AAAAAA;
                    border-radius: 5px;
                    padding: 5px;
                }
            """)
            self.ui.buscarPushButton.setToolTip("Processant ticket...")

    def _reactivar_botons_ocr(self):
        """Reactivar botons OCR després del processament"""
        self._processant_ocr = False
        
        # Comprovar si s'han introduït dades manualment
        if self.dades_manual_introduides:
            print("⚠️ No es reactiven botons - hi ha dades manuals")
            return
        
        # Reactivar segons el supermercat seleccionat
        super_actual = self.ui.superComboBox.currentText() or ""
        ocr_compatible = 'dia' in super_actual.strip().lower()
        
        if hasattr(self.ui, 'ocrPushButton'):
            self.ui.ocrPushButton.setEnabled(ocr_compatible)
            if ocr_compatible:
                self.ui.ocrPushButton.setStyleSheet("""
                    QPushButton {
                        background-color: #4CAF50;
                        color: white;
                        font-weight: bold;
                        border: 2px solid #45a049;
                        border-radius: 5px;
                        padding: 5px;
                    }
                    QPushButton:hover {
                        background-color: #45a049;
                    }
                """)
                self.ui.ocrPushButton.setToolTip(f"Processar ticket de {super_actual}")
            else:
                self.ui.ocrPushButton.setStyleSheet("""
                    QPushButton {
                        background-color: #CCCCCC;
                        color: #666666;
                        border: 2px solid #AAAAAA;
                        border-radius: 5px;
                        padding: 5px;
                    }
                """)
                self.ui.ocrPushButton.setToolTip("OCR només disponible per a supermercats Dia")
        
        if hasattr(self.ui, 'buscarPushButton'):
            self.ui.buscarPushButton.setEnabled(True)
            self.ui.buscarPushButton.setStyleSheet("""
                QPushButton {
                    background-color: #4CAF50;
                    color: white;
                    font-weight: bold;
                    border: 2px solid #45a049;
                    border-radius: 5px;
                    padding: 5px;
                }
                QPushButton:hover {
                    background-color: #45a049;
                }
            """)
            self.ui.buscarPushButton.setToolTip("Seleccionar un ticket de la carpeta predeterminada")
    
    def _desactivar_mode_modificacions(self):
        """Desactivar el mode modificacions i netejar"""
        self.mode_modificacions = False
        self.ui.modificacionsPushButton.setText("Modificacions")
        self.ui.borrarModificacionsPushButton.setVisible(False)
        self.ui.etiqNumLinea.setVisible(False)
        self.ui.numLineaLineEdit.setVisible(False)
        self.ui.AceptarButtonBox.setVisible(False)
        
        # Fer la taula no editable
        self.ui.llistaProductesTable.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        # 🔴🔴🔴 REACTIVAR BOTÓ FINALITZAR
        self.ui.fiTicketPushButton.setEnabled(True)
        
        # Netejar selecció
        self.ui.llistaProductesTable.clearSelection()

    def calcular_percentatge_en_temps_real(self):
        """Calcula el preu unitari en temps real quan es modifica el percentatge"""

        # 🔴🔴🔴 EVITAR RECURSIÓ
        if self._bloquejar_calcul_percentatge:
            return
        
        self._bloquejar_calcul_percentatge = True
        
        # Obtenir valors
        quantitat_text = self.ui.quantitatLineEdit.text().replace(',', '.')
        percentatge_text = self.ui.percentatgeLineEdit.text().replace(',', '.')
        total_text = self.ui.totalLineaLineEdit.text().replace(',', '.')
        
        # Verificar que tenim les dades necessàries
        if not quantitat_text or not percentatge_text or not total_text:
            return
        
        try:
            quantitat = float(quantitat_text)
            percentatge = float(percentatge_text) / 100  # 20 → 0.20
            total_final = float(total_text)
            
            if quantitat <= 0 or percentatge >= 1:
                return
            
            # Calcular preu original
            preu_original = total_final / (quantitat * (1 - percentatge))
            
            # Calcular descompte
            descompte = (quantitat * preu_original) - total_final
            
            # Actualitzar camps
            self.ui.preuUnitLineEdit.setText(f"{preu_original:.2f}".replace('.', ','))
            self.ui.promocioLineEdit.setText(f"{descompte:.2f}".replace('.', ','))
            
        except ValueError:
            pass  # Ignorar errors de conversió mentre s'escriu
        except ZeroDivisionError:
            pass
        finally:
            # 🔴🔴🔴 DESBLOQUEJAR SEMPRE
            self._bloquejar_calcul_percentatge = False