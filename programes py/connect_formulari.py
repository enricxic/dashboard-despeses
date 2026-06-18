# connect_formulari.py - VERSIÓN COMPLETA CON CORRECCIONES

import sys
from PySide6.QtWidgets import (
    QApplication,QWidget, QDialog, QVBoxLayout, QLabel, QPushButton, 
    QButtonGroup, QRadioButton, QMessageBox
)
from PySide6.QtCore import QTimer, QDateTime
from views.formIntroProducteSuper import introProducteWidget
from controllers.introProductesSuper import IntroProductesSuperController

class ConnectFormulari:
    """Classe principal de l'aplicació"""
    
    def __init__(self):
        """Constructor - Inicialitza l'aplicació"""
                
        # PASO 1: QApplication (SIEMPRE PRIMERO)
        self.app = QApplication(sys.argv)
       
        # PASO 2: Ventana principal
        self.main_window = QWidget()
        
        # PASO 3: UI
        self.ui = introProducteWidget()
        self.ui.setupUi(self.main_window)
        
        # Inicializar resto
        self.mode_creacio_producte = False
        self.controller = IntroProductesSuperController()
        self.producte_trobat_automatic = None
        
        # Configurar
        self.configurar_widgets()
        self.connectar_senyals()
        self.carregar_dades_inicials()
        self.configurar_visibilitat_inicial()
        
        # Configurar ventana
        self.main_window.setWindowTitle("Gestió de Productes i Supermercats")
        self.main_window.setMinimumSize(548, 434)

    def on_familia_changed(self, text):
        """Quan canvia la família - VERSIÓ FUNCIONAL"""
        
        # Opcional: pots carregar productes d'aquesta família
        if text:  # Si no està buit
            self.carregar_productes_per_familia(text)
    
    def carregar_productes_per_familia(self, familia):
        """Carrega productes d'una família específica al ComboBox"""
        try:
            if not hasattr(self.ui, 'nomProducteBDConeccioComboBox'):
                return
            
            productes = self.controller.obtenir_productes_per_familia_bd(familia)
            
            if productes:
                # Netejar i afegir productes
                self.ui.nomProducteBDConeccioComboBox.clear()
                self.ui.nomProducteBDConeccioComboBox.addItem("")  # Opció buida
                
                for producte in productes:
                    self.ui.nomProducteBDConeccioComboBox.addItem(producte['nom'])
            else:
                print(f"ℹ️ No hi ha productes a la família '{familia}'")
                
        except Exception as e:
            print(f"❌ Error carregant productes per família: {e}")
        
    def configurar_widgets(self):
        """Configura widgets mínims necessaris"""
    
        # Configurar similitud
        if hasattr(self.ui, 'introSimilitudDoubleSpinBox'):
            self.ui.introSimilitudDoubleSpinBox.setRange(0.0, 1.0)
            self.ui.introSimilitudDoubleSpinBox.setSingleStep(0.1)
            self.ui.introSimilitudDoubleSpinBox.setValue(0.7)            
        
        # Configurar line edit de creació - EVITAR CONEXIONES PROBLEMÁTICAS
        if hasattr(self.ui, 'altaProducteNouLineEdit'):
            self.ui.altaProducteNouLineEdit.setPlaceholderText("Introdueix el nom estàndard...")
            
    def configurar_visibilitat_inicial(self):
        """Configura què és visible al iniciar"""
       
        # Ocultar LineEdit de creació
        if hasattr(self.ui, 'altaProducteNouLineEdit'):
            self.ui.altaProducteNouLineEdit.hide()
           
        # Mostrar ComboBox de cerca
        if hasattr(self.ui, 'nomProducteBDConeccioComboBox'):
            self.ui.nomProducteBDConeccioComboBox.show()
           
    def connectar_senyals(self):
        """Connecta només els senyals essencials"""
        
        # Botó Crear Producte
        if hasattr(self.ui, 'crearProductePushButton'):
            self.ui.crearProductePushButton.clicked.connect(self.on_crear_producte_clicked)
            
        # Botó Afegir producte
        if hasattr(self.ui, 'afegirPushButton'):
            self.ui.afegirPushButton.clicked.connect(self.afegir_nom_supermercat)
            
        # Botó Cancel·lar
        if hasattr(self.ui, 'cancelarPushButton'):
            self.ui.cancelarPushButton.clicked.connect(self.on_cancelar_clicked)
           
        # Botó Netejar Nom Super
        if hasattr(self.ui, 'netejarSuperPushButton'):
            self.ui.netejarSuperPushButton.clicked.connect(self.limpiar_campo_nom_super)
            
        # Cerca quan es prem Enter
        if hasattr(self.ui, 'introNomSuperLineEdit'):
            self.ui.introNomSuperLineEdit.returnPressed.connect(self.on_enter_pressed_nom_super)
           
        # Actualitzar productes quan canvia la família
        if hasattr(self.ui, 'introFamiliaComboBox'):
            self.ui.introFamiliaComboBox.currentTextChanged.connect(self.on_familia_changed)
           
        # Quan l'usuari canvia manualment el producte al ComboBox
        if hasattr(self.ui, 'nomProducteBDConeccioComboBox'):
            self.ui.nomProducteBDConeccioComboBox.currentTextChanged.connect(self.on_producte_manual_seleccionat)

        # Botó per afegir nou supermercat
        if hasattr(self.ui, 'afegirSuperPushButton'):  
            self.ui.afegirSuperPushButton.clicked.connect(self.mostrar_dialog_afegir_super)

    def on_cancelar_clicked(self):
        """Cuando se hace clic en Cancelar"""
        if self.mode_creacio_producte:
            # Si estamos en modo creación, cancelar sin limpiar
            self.cancelar_mode_creacio()
        else:
            # Si no, cerrar la ventana
            self.main_window.close()
            
    def on_producte_manual_seleccionat(self, text):
        """Quan l'usuari tria manualment un producte del ComboBox"""
        if text:
            # Si l'usuari selecciona manualment, netegem el producte automàtic
            if hasattr(self, 'producte_trobat_automatic'):                
                self.producte_trobat_automatic = None
    
    def carregar_dades_inicials(self):
        """Carrega les dades inicials més bàsiques"""
        
        # Carregar supermercats
        if hasattr(self.ui, 'introSuperComboBox'):
            self.ui.introSuperComboBox.clear()
            self.ui.introSuperComboBox.addItem("")
            
            try:
                supers = self.controller.obtenir_supers_disponibles()
                self.ui.introSuperComboBox.addItems(supers)
            except Exception as e:
                print(f"❌ Error carregant supermercats: {e}")
        
        # Carregar famílies
        if hasattr(self.ui, 'introFamiliaComboBox'):
            self.ui.introFamiliaComboBox.clear()
            self.ui.introFamiliaComboBox.addItem("")
            
            try:
                families = self.controller.obtenir_families_disponibles()
                self.ui.introFamiliaComboBox.addItems(families)
            except Exception as e:
                print(f"❌ Error carregant famílies: {e}")
    
    def on_crear_producte_clicked(self):
        """Quan es fa clic al botó Crear Producte (que diu AFEGIR)"""
        
        try:
            # Feedback visual
            self.ui.crearProductePushButton.setStyleSheet("background-color: red !important;")
            QTimer.singleShot(300, lambda: self.ui.crearProductePushButton.setStyleSheet(""))
            
            # ⭐⭐ CASO 1: YA ESTAMOS EN MODO CREACIÓN → Crear producto
            if self.mode_creacio_producte:
                self.crear_producte_nou()
                return
            
            # Verificar datos mínimos
            nom_super = self.ui.introNomSuperLineEdit.text().strip() if hasattr(self.ui, 'introNomSuperLineEdit') else ""
            supermercat = self.ui.introSuperComboBox.currentText() if hasattr(self.ui, 'introSuperComboBox') else ""
            
            if not nom_super:
                QMessageBox.warning(self.main_window, "Error", 
                                "Primer introdueix el nom del producte al supermercat")
                if hasattr(self.ui, 'introNomSuperLineEdit'):
                    self.ui.introNomSuperLineEdit.setFocus()
                return
            
            if not supermercat:
                QMessageBox.warning(self.main_window, "Error", 
                                "Selecciona un supermercat primer")
                return
            
            # Verificar si ya hay un producto seleccionado
            hi_ha_producte, nom_producte = self.verificar_producte_seleccionat()
            
            if hi_ha_producte:
                self.afegir_nom_supermercat()
            else:
                self.activar_mode_creacio(nom_super, supermercat)
                
        except Exception as e:
            print(f"❌ Error en on_crear_producte_clicked: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self.main_window, "Error", f"Error inesperat: {e}")
    
    def preguntar_activar_mode_creacio(self):
        """Pregunta si vol activar el mode de creació"""
        # Verificar que hay nombre de supermercado
        if not hasattr(self.ui, 'introNomSuperLineEdit'):
            QMessageBox.warning(self.main_window, "Error", "Primer introdueix un nom de producte")
            return
        
        nom_super = self.ui.introNomSuperLineEdit.text().strip()
        if not nom_super:
            QMessageBox.warning(self.main_window, "Error", 
                              "Primer introdueix el nom del producte al supermercat")
            self.ui.introNomSuperLineEdit.setFocus()
            return
        
        # Verificar supermercado seleccionado
        supermercat = ""
        if hasattr(self.ui, 'introSuperComboBox'):
            supermercat = self.ui.introSuperComboBox.currentText()
            if not supermercat:
                QMessageBox.warning(self.main_window, "Error", 
                                  "Selecciona un supermercat primer")
                return
        
        # Preguntar al usuario
        resposta = QMessageBox.question(
            self.main_window,
            "Mode Creació",
            f"Vols crear un nou producte estàndard?\n\n"
            f"Nom al super: {nom_super}\n"
            f"Supermercat: {supermercat}\n\n"
            f"Si acceptes, podràs introduir el nom estàndard.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        
        if resposta == QMessageBox.Yes:
            # Activar modo creación
            self.activar_mode_creacio(nom_super, supermercat)
        else:
            # Mantener modo normal
            print("❌ Usuari ha cancel·lat l'activació del mode creació")
    
    def cancelar_mode_creacio(self):
        """Cancela el modo creación sin limpiar el LineEdit"""
        
        # Volver a modo normal SIN limpiar LineEdit
        self.activar_mode_normal(limpiar_lineedit=False)
        
        # Limpiar temporales
        if hasattr(self, 'nom_super_temporal'):
            delattr(self, 'nom_super_temporal')
        if hasattr(self, 'supermercat_temporal'):
            delattr(self, 'supermercat_temporal')
        
        # Focus al campo original
        if hasattr(self.ui, 'introNomSuperLineEdit'):
            self.ui.introNomSuperLineEdit.setFocus()
    
    def limpiar_todo_despues_creacion(self):
        """Limpia todos los campos después de crear un producto EXITOSAMENTE"""
        # 1. Volver a modo normal (limpiando LineEdit)
        self.activar_mode_normal(limpiar_lineedit=True)  # Ahora sí limpiamos
        
        # 2. Limpiar campo del nombre del super
        #self.limpiar_campo_nom_super()
        
        # 3. Limpiar comboBox de producto BD
        if hasattr(self.ui, 'nomProducteBDConeccioComboBox'):
            self.ui.nomProducteBDConeccioComboBox.setCurrentIndex(0)

        # 4. LIMPIAR FAMILIA (REQUISITO) - seleccionar opción vacía
        if hasattr(self.ui, 'introFamiliaComboBox'):
            self.ui.introFamiliaComboBox.setCurrentIndex(0)
    
    def activar_mode_normal(self, limpiar_lineedit=True):
        """Activa el mode normal (cerca i selecció)
        
        Args:
            limpiar_lineedit (bool): Si True, limpia el LineEdit. 
                                    Si False, lo deja como está.
                                    Por defecto True.
        """
        self.mode_creacio_producte = False
        
        # Limpiar temporales
        if hasattr(self, 'nom_super_temporal'):
            delattr(self, 'nom_super_temporal')
        if hasattr(self, 'supermercat_temporal'):
            delattr(self, 'supermercat_temporal')
        
        # ⭐⭐ GESTIÓN DE WIDGETS QUE COMPARTEN ESPACIO (ORDEN INVERSO)
        
        # 1. PRIMERO ocultar y deshabilitar LineEdit
        if hasattr(self.ui, 'altaProducteNouLineEdit'):
            if limpiar_lineedit:
                self.ui.altaProducteNouLineEdit.clear()
            self.ui.altaProducteNouLineEdit.setEnabled(False)  # Deshabilitar
            self.ui.altaProducteNouLineEdit.hide()
        
        # 2. LUEGO mostrar y habilitar ComboBox
        if hasattr(self.ui, 'nomProducteBDConeccioComboBox'):
            self.ui.nomProducteBDConeccioComboBox.setEnabled(True)  # Habilitar
            self.ui.nomProducteBDConeccioComboBox.show()
            self.ui.nomProducteBDConeccioComboBox.setCurrentIndex(0)
            self.ui.nomProducteBDConeccioComboBox.raise_()  # Traer al frente

        # Restaurar botó
        if hasattr(self.ui, 'crearProductePushButton'):
            self.ui.crearProductePushButton.setText("AFEGIR")
            self.ui.crearProductePushButton.setStyleSheet("")       
        
        # Focus al nom del super
        if hasattr(self.ui, 'introNomSuperLineEdit'):
            self.ui.introNomSuperLineEdit.setFocus()

    def afegir_nom_supermercat(self):
        """Afegeix nom de supermercat a un producte existent - PERMET MODIFICAR NOM"""
        
        # ===========================================
        # PART 1: VERIFICAR DADES BÀSIQUES
        # ===========================================
        
        # Verificar nom del super
        nom_super = self.ui.introNomSuperLineEdit.text().strip() if hasattr(self.ui, 'introNomSuperLineEdit') else ""
        if not nom_super:
            QMessageBox.warning(self.main_window, "Error", "Introdueix el nom del producte al supermercat")
            return
        
        # Verificar supermercat
        supermercat = self.ui.introSuperComboBox.currentText() if hasattr(self.ui, 'introSuperComboBox') else ""
        if not supermercat:
            QMessageBox.warning(self.main_window, "Error", "Selecciona un supermercat")
            return
        
        # ===========================================
        # PART 2: DETERMINAR PRODUCTE A UTILITZAR
        # ===========================================
        
        id_producte = None
        nom_producte_actual = ""
        
        # OPCIÓ A: Producte trobat automàticament
        if hasattr(self, 'producte_trobat_automatic') and self.producte_trobat_automatic:
            id_producte = self.producte_trobat_automatic['id']
            nom_producte_actual = self.producte_trobat_automatic['nom']
            
            # Utilitzar similitud trobada si és major
            similitud_trobada = self.producte_trobat_automatic.get('similitud', 0)
            similitud = self.ui.introSimilitudDoubleSpinBox.value() if hasattr(self.ui, 'introSimilitudDoubleSpinBox') else 0.7
            if similitud_trobada > similitud:
                similitud = similitud_trobada
        
        # OPCIÓ B: Producte seleccionat manualment al ComboBox
        elif hasattr(self.ui, 'nomProducteBDConeccioComboBox'):
            nom_producte_actual = self.ui.nomProducteBDConeccioComboBox.currentText()
            
            if not nom_producte_actual:
                QMessageBox.warning(self.main_window, "Error", "Selecciona un producte de la llista")
                return
            
            # Buscar l'ID
            producte_info = self.controller.obtenir_producte_per_nom(nom_producte_actual)
            if producte_info:
                id_producte = producte_info['id']
            else:
                QMessageBox.warning(self.main_window, "Error", f"No s'ha trobat '{nom_producte_actual}' a la BD")
                return
        
        else:
            QMessageBox.warning(self.main_window, "Error", "No hi ha cap producte seleccionat")
            return
        
        # ===========================================
        # PART 3: CONFIRMAR I MODIFICAR (SI CAL)
        # ===========================================
        
        # Obtenir similitud final
        similitud = self.ui.introSimilitudDoubleSpinBox.value() if hasattr(self.ui, 'introSimilitudDoubleSpinBox') else 0.7
        
        # Cridar a la funció de confirmació/modificació
        resultat = self.confirmar_i_modificar_producte(
            id_producte, 
            nom_producte_actual, 
            nom_super, 
            supermercat, 
            similitud
        )
        
        if not resultat or resultat[0] is None:
            return  # Usuari ha cancel·lat
        
        id_producte_final, nom_producte_final = resultat
        
        # ===========================================
        # PART 4: AFEGIR A LA BD
        # ===========================================
        
        exitos, missatge = self.controller.afegir_nom_supermercat(
            id_producte_final,
            supermercat,
            nom_super,
            similitud
        )
        
        if exitos:                    
            self.limpiar_tot_despres_afegir()
        else:
            QMessageBox.warning(self.main_window, "Error", f"No s'ha pogut afegir:\n{missatge}")
            # SI HI HA ERROR, TAMBÉ NETEGAR LA FAMÍLIA!
            self.limpiar_tot_despres_duplicat()

    def limpiar_tot_despres_afegir(self):
        """Netega tot després d'afegir un producte"""
        
        # 1. Netejar NOMÉS el camp del nom del producte al ticket (NO el supermercat)
        if hasattr(self.ui, 'introNomSuperLineEdit'):
            self.ui.introNomSuperLineEdit.clear()  # Neteja el camp del producte
            # Opcional: posar el focus aquí per continuar escrivint
            # self.ui.introNomSuperLineEdit.setFocus()
        
        # 2. Netejar el ComboBox de supermercats si vols (OPCIONAL)
        # Si vols mantenir el supermercat seleccionat, NO borris aquest:
        # if hasattr(self.ui, 'introSuperComboBox'):
        #     self.ui.introSuperComboBox.setCurrentIndex(0)
        
        # 3. Netejar la família
        if hasattr(self.ui, 'introFamiliaComboBox'):
            self.ui.introFamiliaComboBox.setCurrentIndex(0)
            self.ui.introFamiliaComboBox.setFocus()
        
        # 4. Netejar ComboBox de productes BD
        if hasattr(self.ui, 'nomProducteBDConeccioComboBox'):
            estava_visible = self.ui.nomProducteBDConeccioComboBox.isVisible()
            self.ui.nomProducteBDConeccioComboBox.setCurrentIndex(0)
            if not estava_visible:
                self.ui.nomProducteBDConeccioComboBox.hide()
        
        # 5. Netejar producte trobat automàticament
        if hasattr(self, 'producte_trobat_automatic'):
            self.producte_trobat_automatic = None
        
        # 6. Netejar temporals
        if hasattr(self, 'nom_super_temporal'):
            delattr(self, 'nom_super_temporal')
        if hasattr(self, 'supermercat_temporal'):
            delattr(self, 'supermercat_temporal')

    def verificar_producte_seleccionat(self):
        """Verifica si hi ha un producte seleccionat (automàtic o manual)"""
        
        # Verificar producte automàtic
        if hasattr(self, 'producte_trobat_automatic') and self.producte_trobat_automatic:
            return True, self.producte_trobat_automatic['nom']
        
        # Verificar ComboBox
        if hasattr(self.ui, 'nomProducteBDConeccioComboBox'):
            text = self.ui.nomProducteBDConeccioComboBox.currentText()
            if text and text.strip():
                return True, text.strip()
        
        return False, ""
            
    def on_enter_pressed_nom_super(self):
        """Quan es prem Enter al camp de nom del super"""
        
        # Obtener el texto del campo
        if not hasattr(self.ui, 'introNomSuperLineEdit'):
            return
        
        text = self.ui.introNomSuperLineEdit.text().strip()
        
        # Validar longitud mínima
        if len(text) < 2:
            QMessageBox.warning(self.main_window, "Cerca", "Escriu almenys 2 caràcters")
            return
        
        # Verificar si hay supermercado seleccionado
        supermercat = ""
        if hasattr(self.ui, 'introSuperComboBox'):
            supermercat = self.ui.introSuperComboBox.currentText()
            
            if not supermercat:
                QMessageBox.warning(self.main_window, "Supermercat requerit", 
                                "Si us plau, selecciona primer un supermercat")
                return
        
        # Aquí va la lógica de búsqueda REAL
        self.buscar_productes_similars(text)

    def buscar_productes_similars(self, text):
        """Busca productes similars al text introduït"""
        
        try:
            # Obtener supermercado
            supermercat = ""
            if hasattr(self.ui, 'introSuperComboBox'):
                supermercat = self.ui.introSuperComboBox.currentText()
                
                if not supermercat:
                    QMessageBox.warning(self.main_window, "Supermercat requerit", 
                                    "Si us plau, selecciona primer un supermercat")
                    return
            
            # PAS 1: VERIFICAR SI JA EXISTEIX A TBNomsProducte
            existeix_a_noms_producte = self.controller.verificar_existencia_tbnomsproducte(
                supermercat, text
            )
            
            if existeix_a_noms_producte:
                # JA EXISTEIX - Mostrar missatge i sortir
                QMessageBox.warning(
                    self.main_window,
                    "Producte ja existeix",
                    f"❌ El producte JA existeix!\n\n"
                    f"🏪 Supermercat: {supermercat}\n"
                    f"📋 Nom al super: {text}\n\n"
                    f"No es pot afegir de nou. Ja està registrat."
                )
                
                # Netejar LineEdit i família
                if hasattr(self.ui, 'introNomSuperLineEdit'):
                    self.ui.introNomSuperLineEdit.clear()
                
                if hasattr(self.ui, 'introFamiliaComboBox'):
                    self.ui.introFamiliaComboBox.setCurrentIndex(0)
                    self.ui.introFamiliaComboBox.setFocus()
                return
            
            # PAS 2: SI NO EXISTEIX, OBTENIR FAMÍLIA SELECCIONADA
            familia = ""
            if hasattr(self.ui, 'introFamiliaComboBox'):
                familia = self.ui.introFamiliaComboBox.currentText()
            
            # PAS 3: FER CERCA MILLORADA
            resultats = self.controller.cerca_millorada(text, familia if familia else None, limit=10)
            
            # PAS 4: PROCESSAR RESULTATS
            if resultats:
                # Hi ha resultats - processar normalment
                self.mostrar_resultats_cerca(resultats, text, supermercat)
            else:
                # ⭐⭐ NO HI HA RESULTATS - PREGUNTAR QUÈ FER
                self.preguntar_accio_despres_cerca(text, familia, supermercat)
                
        except Exception as e:
            print(f"❌ Error en la cerca: {e}")
            QMessageBox.critical(self.main_window, "Error", f"Error en la cerca: {e}")

    def preguntar_accio_despres_cerca(self, nom_super, familia, supermercat):
        """Pregunta què vol fer l'usuari després d'una cerca sense resultats"""
        
        # Guardar dades temporals
        self.nom_super_temporal = nom_super
        self.supermercat_temporal = supermercat
        
        # Crear missatge
        missatge = f"No s'ha trobat cap producte similar a '{nom_super}'"
        
        if familia:
            missatge += f" a la família '{familia}'"
        if supermercat:
            missatge += f" per al supermercat '{supermercat}'"
        
        missatge += ".\n\nQuè vols fer?"
        
        # Crear QMessageBox personalitzat amb 4 opcions
        msg_box = QMessageBox()
        msg_box.setWindowTitle("❌ Producte no trobat")
        msg_box.setText(missatge)
        
        # Botons
        btn_crear_nou = msg_box.addButton("➕ Crear producte nou", QMessageBox.YesRole)
        btn_filtrar = msg_box.addButton("🔍 Filtrar per super/família", QMessageBox.NoRole)
        btn_triar_manual = msg_box.addButton("📋 Triar manualment", QMessageBox.ActionRole)
        btn_cancelar = msg_box.addButton("❌ Cancel·lar", QMessageBox.RejectRole)
        
        # Configurar botó per defecte
        msg_box.setDefaultButton(btn_filtrar)
        
        # Executar
        msg_box.exec()
        
        boton_presionado = msg_box.clickedButton()
        
        # Processar resposta
        if boton_presionado == btn_crear_nou:
            # Opció 1: Crear producte nou
            self.mostrar_opcio_creacio_nou(nom_super, familia, supermercat)
            
        elif boton_presionado == btn_filtrar:
            # Opció 2: Filtrar per supermercat i família
            self.activar_cerca_filtrada(nom_super, supermercat)
            
        elif boton_presionado == btn_triar_manual:
            # Opció 3: Triar manualment
            self.activar_triar_manual(nom_super, supermercat)
            
        else:
            # Cancel·lar
            if hasattr(self.ui, 'introNomSuperLineEdit'):
                self.ui.introNomSuperLineEdit.clear()
                self.ui.introNomSuperLineEdit.setFocus()

    def activar_cerca_filtrada(self, nom_super, supermercat):
        """Activa la cerca filtrada per supermercat i família"""
        
        # Obtenir família seleccionada actualment
        familia_actual = ""
        if hasattr(self.ui, 'introFamiliaComboBox'):
            familia_actual = self.ui.introFamiliaComboBox.currentText()
        
        # Crear diàleg per seleccionar filtres
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton
        
        dialog = QDialog(self.main_window)
        dialog.setWindowTitle("🔍 Cerca filtrada")
        dialog.setMinimumWidth(400)
        
        layout = QVBoxLayout(dialog)
        
        # Títol
        label_titol = QLabel(f"<h3>Cerca productes per a:</h3>")
        label_titol2 = QLabel(f"<b>Nom al super:</b> {nom_super}<br><b>Supermercat:</b> {supermercat}")
        layout.addWidget(label_titol)
        layout.addWidget(label_titol2)
        
        # Filtre per supermercat
        layout_super = QHBoxLayout()
        layout_super.addWidget(QLabel("Supermercat:"))
        super_combo = QComboBox()
        
        # Carregar supermercats
        supers = self.controller.obtenir_supers_disponibles()
        super_combo.addItem("")  # Opció buida
        super_combo.addItems(supers)
        
        # Seleccionar el supermercat actual si existeix
        if supermercat and supermercat in supers:
            super_combo.setCurrentText(supermercat)
        
        layout_super.addWidget(super_combo)
        layout.addLayout(layout_super)
        
        # Filtre per família
        layout_familia = QHBoxLayout()
        layout_familia.addWidget(QLabel("Família:"))
        familia_combo = QComboBox()
        
        # Carregar famílies
        families = self.controller.obtenir_families_disponibles()
        familia_combo.addItem("")  # Opció buida
        familia_combo.addItems(families)
        
        # Seleccionar la família actual si existeix
        if familia_actual and familia_actual in families:
            familia_combo.setCurrentText(familia_actual)
        
        layout_familia.addWidget(familia_combo)
        layout.addLayout(layout_familia)
        
        # Botons
        btn_buscar = QPushButton("🔍 Buscar")
        btn_cancelar = QPushButton("❌ Cancel·lar")
        
        layout_buttons = QHBoxLayout()
        layout_buttons.addWidget(btn_buscar)
        layout_buttons.addWidget(btn_cancelar)
        layout.addLayout(layout_buttons)
        
        # Connexions
        def on_buscar():
            super_seleccionat = super_combo.currentText()
            familia_seleccionada = familia_combo.currentText()
            dialog.accept()
            
            # Fer la cerca amb els nous filtres
            self.cerca_amb_filtres(nom_super, super_seleccionat, familia_seleccionada)
        
        btn_buscar.clicked.connect(on_buscar)
        btn_cancelar.clicked.connect(dialog.reject)
        
        # Mostrar diàleg
        dialog.exec()

    def cerca_amb_filtres(self, nom_super, supermercat, familia):
        """Fa una cerca amb els filtres seleccionats"""
        
        # Actualizar comboBox de supermercat si ha canviat
        if hasattr(self.ui, 'introSuperComboBox') and supermercat:
            self.ui.introSuperComboBox.setCurrentText(supermercat)
        
        # Actualizar comboBox de família si ha canviat
        if hasattr(self.ui, 'introFamiliaComboBox') and familia:
            self.ui.introFamiliaComboBox.setCurrentText(familia)
        
        # Fer la cerca amb els nous filtres
        try:
            resultats = self.controller.cerca_millorada(nom_super, familia if familia else None, limit=10)
            
            if resultats:
                self.mostrar_resultats_cerca(resultats, nom_super, supermercat)
            else:
                # Segueix sense trobar resultats - tornar a preguntar
                QMessageBox.information(
                    self.main_window,
                    "Sense resultats",
                    f"Encara no s'han trobat productes amb els filtres seleccionats.\n\n"
                    f"Supermercat: {supermercat if supermercat else 'Tots'}\n"
                    f"Família: {familia if familia else 'Totes'}"
                )
                self.preguntar_accio_despres_cerca(nom_super, familia, supermercat)
                
        except Exception as e:
            print(f"❌ Error en cerca amb filtres: {e}")
            QMessageBox.critical(self.main_window, "Error", f"Error en la cerca: {e}")

    def limpiar_tot_despres_duplicat(self):
        """Neteja tot quan es troba un duplicat a TBNomsProducte"""
        # 1. Netejar camp del nom del super
        #self.limpiar_campo_nom_super()
        
        # 2. ⭐⭐ IMPORTANT: Netejar la família també!
        if hasattr(self.ui, 'introFamiliaComboBox'):
            self.ui.introFamiliaComboBox.setCurrentIndex(0)  # Seleccionar opció buida
            
        # 3. Netejar producte trobat automàticament (si hi és)
        if hasattr(self, 'producte_trobat_automatic'):
            self.producte_trobat_automatic = None
            
        # 4. Netejar ComboBox de producte BD (si hi és)
        if hasattr(self.ui, 'nomProducteBDConeccioComboBox'):
            self.ui.nomProducteBDConeccioComboBox.setCurrentIndex(0)
            
        # 5. Netejar temporals (si hi són)
        if hasattr(self, 'nom_super_temporal'):
            delattr(self, 'nom_super_temporal')
        if hasattr(self, 'supermercat_temporal'):
            delattr(self, 'supermercat_temporal')

    def mostrar_resultats_cerca(self, resultats, nom_super, supermercat):
        """Mostra els resultats de la cerca"""
        
        # Inicialitzar
        self.producte_trobat_automatic = None
        
        if resultats:
            millor_resultat = resultats[0]
            
            if millor_resultat['similitud'] >= 0.6:
                
                # Guardar el producte trobat automàticament
                self.producte_trobat_automatic = {
                    'id': millor_resultat['id'],
                    'nom': millor_resultat['nom'],
                    'similitud': millor_resultat['similitud']
                }                
                # Poner el resultado en el ComboBox
                if hasattr(self.ui, 'nomProducteBDConeccioComboBox'):
                    self.ui.nomProducteBDConeccioComboBox.setCurrentText(millor_resultat['nom'])
                
                # Mostrar missatge informatiu (NO pregunta si vol seleccionar-lo)
                QMessageBox.information(
                    self.main_window,
                    "✅ Producte trobat",
                    f"S'ha trobat un producte similar:\n\n"
                    f"🏪 Nom al super: {nom_super}\n"
                    f"📦 Producte BD: {millor_resultat['nom']}\n"
                    f"🎯 Similitud: {millor_resultat['similitud']:.2f}\n\n"
                    f"Ara pots:\n"
                    f"1. Ajustar la similitud si cal\n"
                    f"2. Fer clic a 'AFEGIR' per guardar\n"
                    f"3. O triar un altre producte manualment"
                )
                
                # Enfocar el botó AFEGIR
                if hasattr(self.ui, 'afegirPushButton'):
                    self.ui.afegirPushButton.setFocus()
            else:
                # Similitud baixa, preguntar què fer
                self.mostrar_opcions_baixa_similitud(resultats, nom_super, supermercat)

    def mostrar_opcio_creacio_nou(self, nom_super, familia, supermercat):
        """Mostra opció per crear nou producte - PERMET MODIFICAR EL NOM"""
        
        # Guardar dades temporals
        self.nom_super_temporal = nom_super
        self.supermercat_temporal = supermercat
        
        # Preparar nom suggerit
        nom_suggerit = self.preparar_nom_suggerit(nom_super)
        
        # Crear diàleg per introduir/modificar el nom estàndard
        from PySide6.QtWidgets import QInputDialog, QLineEdit
        
        missatge = f"Introdueix el nom estàndard per al nou producte:"
        if familia:
            missatge += f"\nFamília: {familia}"
        if supermercat:
            missatge += f"\nSupermercat: {supermercat}"
        missatge += f"\nNom al ticket: {nom_super}"
        
        nou_nom_estandard, ok = QInputDialog.getText(
            self.main_window,
            "➕ Crear nou producte",
            missatge,
            QLineEdit.Normal,
            nom_suggerit
        )
        
        if not ok or not nou_nom_estandard.strip():
            # Usuari ha cancel·lat - tornar al menú anterior
            self.preguntar_accio_despres_cerca(nom_super, familia, supermercat)
            return
        
        nou_nom_estandard = nou_nom_estandard.strip()
        
        # Verificar si el nom estàndard modificat JA existeix
        producte_existent = self.controller.obtenir_producte_per_nom(nou_nom_estandard)
        
        if producte_existent:
            # El nom modificat ja existeix - preguntar què fer
            resposta = QMessageBox.question(
                self.main_window,
                "Producte existent",
                f"El producte '{nou_nom_estandard}' ja existeix a la BD.\n\n"
                f"Vols afegir el nom '{nom_super}' a aquest producte existent?",
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
                QMessageBox.Yes
            )
            
            if resposta == QMessageBox.Yes:
                # Afegir al producte existent
                self.afegir_a_producte_existent(producte_existent['id'], nom_super, supermercat, familia)
            elif resposta == QMessageBox.No:
                # Tornar a demanar el nom
                self.mostrar_opcio_creacio_nou(nom_super, familia, supermercat)
            else:
                # Cancel·lar
                self.preguntar_accio_despres_cerca(nom_super, familia, supermercat)
            return
        
        # El nom NO existeix - procedir a crear-lo DIRECTAMENT
        self.crear_producte_amb_nom_modificat(nou_nom_estandard, nom_super, familia, supermercat)

    def mostrar_menu_alternatiu(self, nom_super, familia, supermercat):
        """Mostra menú alternatiu quan es cancel·la la creació"""
        
        msg_box = QMessageBox()
        msg_box.setWindowTitle("Què vols fer?")
        msg_box.setText(f"Què vols fer amb '{nom_super}'?")
        
        btn_triar_manual = msg_box.addButton("Triar manualment", QMessageBox.YesRole)
        btn_crear_altre = msg_box.addButton("Tornar a provar", QMessageBox.NoRole)
        btn_cancelar = msg_box.addButton("Cancel·lar", QMessageBox.RejectRole)
        
        msg_box.setDefaultButton(btn_triar_manual)
        msg_box.exec()
        
        boton_presionado = msg_box.clickedButton()
        
        if boton_presionado == btn_triar_manual:
            self.activar_triar_manual(nom_super, supermercat)
        elif boton_presionado == btn_crear_altre:
            self.mostrar_opcio_creacio_nou(nom_super, familia, supermercat)
        else:
            # ⭐⭐ Cancel·lar - netejar LineEdit
            if hasattr(self.ui, 'introNomSuperLineEdit'):
                self.ui.introNomSuperLineEdit.clear()
                self.ui.introNomSuperLineEdit.setFocus()

    def afegir_a_producte_existent(self, id_producte, nom_super, supermercat, familia):
        """Afegeix el nom del ticket a un producte existent"""
        
        similitud = 0.7
        if hasattr(self.ui, 'introSimilitudDoubleSpinBox'):
            similitud = self.ui.introSimilitudDoubleSpinBox.value()
        
        exitos, missatge = self.controller.afegir_nom_supermercat(
            id_producte,
            supermercat,
            nom_super,
            similitud
        )
        
        if exitos:
            QMessageBox.information(
                self.main_window,
                "✅ Afegit",
                f"S'ha afegit '{nom_super}' al producte existent."
            )
            
            # ⭐⭐ NETEGAR EL LINEEDIT
            if hasattr(self.ui, 'introNomSuperLineEdit'):
                self.ui.introNomSuperLineEdit.clear()
                self.ui.introNomSuperLineEdit.setFocus()
                
            self.limpiar_tot_despres_afegir()
        else:
            QMessageBox.warning(self.main_window, "Error", f"No s'ha pogut afegir:\n{missatge}")
            self.mostrar_menu_alternatiu(nom_super, familia, supermercat)

    def crear_producte_amb_nom_modificat(self, nom_estandard, nom_super, familia, supermercat):
        """Crea el producte directament amb el nom modificat"""
        
        # Crear el producte a TBProductes
        unitat = "unitat"
        exitos_creacio, missatge_creacio = self.controller.crear_producte(
            nom_estandard, familia, unitat
        )
        
        if not exitos_creacio:
            QMessageBox.warning(
                self.main_window, 
                "Error", 
                f"No s'ha pogut crear el producte:\n{missatge_creacio}"
            )
            self.mostrar_menu_alternatiu(nom_super, familia, supermercat)
            return
        
        # Obtenir l'ID del producte creat
        producte_nou = self.controller.obtenir_producte_per_nom(nom_estandard)
        if not producte_nou:
            QMessageBox.warning(
                self.main_window, 
                "Error", 
                "Producte creat però no s'ha pogut obtenir l'ID"
            )
            self.limpiar_todo_despues_creacion()
            return
        
        # Afegir el nom del supermercat
        similitud = 0.7
        if hasattr(self.ui, 'introSimilitudDoubleSpinBox'):
            similitud = self.ui.introSimilitudDoubleSpinBox.value()
        
        exitos_afegir, missatge_afegir = self.controller.afegir_nom_supermercat(
            producte_nou['id'],
            supermercat,
            nom_super,
            similitud
        )
        
        if exitos_afegir:
            QMessageBox.information(
                self.main_window,
                "✅ Èxit complet",
                f"✅ Producte creat i afegit!\n\n"
                f"📝 Nom estàndard: {nom_estandard}\n"
                f"🏪 Supermercat: {supermercat}\n"
                f"📋 Nom al super: {nom_super}\n"
                f"📦 Família: {familia}"
            )
        else:
            QMessageBox.warning(
                self.main_window,
                "Atenció",
                f"✅ Producte creat però error en afegir al super:\n{missatge_afegir}"
            )
        
        # ⭐⭐ NETEGAR EL LINEEDIT DEL NOM DEL PRODUCTE AL TICKET
        if hasattr(self.ui, 'introNomSuperLineEdit'):
            self.ui.introNomSuperLineEdit.clear()
            self.ui.introNomSuperLineEdit.setFocus()
        
        self.limpiar_todo_despues_creacion()

    def activar_triar_manual(self, nom_super, supermercat):
        """Activa el mode de tria manual des del ComboBox - FILTRAT PER FAMÍLIA"""
        try:
            # 1. Obtenir la família seleccionada
            familia_seleccionada = ""
            if hasattr(self.ui, 'introFamiliaComboBox'):
                familia_seleccionada = self.ui.introFamiliaComboBox.currentText()                
            
            # 2. Carregar productes FILTRATS per família
            if hasattr(self.ui, 'nomProducteBDConeccioComboBox'):
                # Netejar el ComboBox
                self.ui.nomProducteBDConeccioComboBox.clear()
                self.ui.nomProducteBDConeccioComboBox.addItem("")  # Opció buida
                
                # Obtenir productes de la BD FILTRATS per família
                if familia_seleccionada:
                    # Carregar només productes d'aquesta família DES DE LA BD
                    productes = self.controller.obtenir_productes_per_familia_bd(familia_seleccionada)
                else:
                    # Carregar TOTS els productes de la BD (si no hi ha família seleccionada)
                    productes = self.controller.obtenir_tots_productes_bd()  # Asegura't que tens aquest mètode
                
                if productes:
                    # Ordenar alfabèticament
                    productes_ordenats = sorted(productes, key=lambda x: x['nom'].lower())
                    
                    # Afegir al ComboBox
                    for producte in productes_ordenats:
                        # Crear text per mostrar (nom del producte)
                        text = producte['nom']
                        
                        # Afegir l'ítem
                        index = self.ui.nomProducteBDConeccioComboBox.count()
                        self.ui.nomProducteBDConeccioComboBox.addItem(text)
                        
                        # Guardar l'ID com a dada de l'ítem (si està disponible)
                        if 'id' in producte:
                            self.ui.nomProducteBDConeccioComboBox.setItemData(index, producte['id'])                    
                   
                else:
                    print(f"⚠️ Tria manual: No s'han trobat productes a la BD")
                    self.ui.nomProducteBDConeccioComboBox.addItem("(No hi ha productes en aquesta família)")
                
                # 3. Mostrar el ComboBox si està ocult
                if self.ui.nomProducteBDConeccioComboBox.isHidden():
                    self.ui.nomProducteBDConeccioComboBox.show()
                
                # 4. Posar el focus al ComboBox
                from PySide6.QtCore import QTimer
                QTimer.singleShot(100, lambda: self.mostrar_comboBox_netament())
                
            
            else:
                print("❌ ERROR: No s'ha trobat el ComboBox 'nomProducteBDConeccioComboBox'")
        
        except Exception as e:
            print(f"❌ Error activant tria manual: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(
                self.main_window,
                "Error",
                f"No s'han pogut carregar els productes:\n\n{e}"
            )

    def tancar_missatges_oberts(self):
        """Tanca finestres de missatge obertes per evitar superposició"""
        try:
            # Buscar tots els QMessageBox oberts i tancar-los
            from PySide6.QtWidgets import QApplication
            for widget in QApplication.topLevelWidgets():
                if isinstance(widget, QMessageBox):
                    widget.accept()
        except:
            pass

    def mostrar_comboBox_netament(self):
        """Mostra el ComboBox de manera neta"""
        if hasattr(self.ui, 'nomProducteBDConeccioComboBox'):
            self.ui.nomProducteBDConeccioComboBox.setFocus()
            self.ui.nomProducteBDConeccioComboBox.showPopup()

    def mostrar_busqueda_manual(self, nom_super, familia, supermercat):
        """Permite buscar y seleccionar manualmente un producto de la BD"""
        try:
            # Obtener todos los productos disponibles (o los de la familia si está seleccionada)
            if familia:
                productes = self.controller.obtenir_productes_per_familia(familia)
            else:
                productes = self.controller.obtenir_tots_productes()
            
            if not productes or len(productes) == 0:
                QMessageBox.information(
                    self.main_window,
                    "No hi ha productes",
                    "No s'han trobat productes a la base de dades.\n\n"
                    "Vols crear un producte nou?"
                )
                # Preguntar si quiere crear nuevo
                resposta = QMessageBox.question(
                    self.main_window,
                    "Crear producte",
                    "No hi ha productes disponibles.\n\nVols crear un producte nou?",
                    QMessageBox.Yes | QMessageBox.No
                )
                
                if resposta == QMessageBox.Yes:
                    self.activar_mode_creacio(nom_super, supermercat)
                return
            
            # Mostrar diálogo de selección
            self.mostrar_dialog_seleccio(productes, nom_super, supermercat)
            
        except Exception as e:
            print(f"❌ Error en cerca manual: {e}")
            # Si hay error, ofrecer crear nuevo producto
            QMessageBox.warning(
                self.main_window,
                "Error de cerca",
                f"Error en la cerca manual: {e}\n\nVols crear un producte nou?"
            )
            
            resposta = QMessageBox.question(
                self.main_window,
                "Crear producte",
                "Hi ha hagut un error en la cerca.\n\nVols crear un producte nou?",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if resposta == QMessageBox.Yes:
                self.activar_mode_creacio(nom_super, supermercat)
            
    def mostrar_dialog_seleccio(self, productes, nom_super, supermercat):
        """Muestra diálogo para seleccionar producto manualmente"""
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QListWidget, QPushButton, QLabel
        
        # Crear diálogo
        dialog = QDialog(self.main_window)
        dialog.setWindowTitle(f"Seleccionar producte")
        dialog.setMinimumWidth(400)
        dialog.setMinimumHeight(300)
        
        layout = QVBoxLayout(dialog)
        
        # Añadir label informativo
        label = QLabel(f"Selecciona un producte per a:\nNom al super: '{nom_super}'\nSupermercat: {supermercat}")
        layout.addWidget(label)
        
        # Crear lista de productos
        list_widget = QListWidget()
        
        # Ordenar productos alfabéticamente
        productes_ordenats = sorted(productes, key=lambda x: x['nom'].lower())
        
        for producte in productes_ordenats:
            text = f"{producte['nom']}"
            if producte.get('familia'):
                text += f" ({producte['familia']})"
            list_widget.addItem(text)
        
        layout.addWidget(list_widget)
        
        # Botones
        btn_frame = QWidget()
        btn_layout = QVBoxLayout(btn_frame)
        
        btn_seleccionar = QPushButton("✅ Seleccionar")
        btn_crear_nou = QPushButton("➕ Crear producte nou")
        btn_cancelar = QPushButton("❌ Cancel·lar")
        
        btn_layout.addWidget(btn_seleccionar)
        btn_layout.addWidget(btn_crear_nou)
        btn_layout.addWidget(btn_cancelar)
        
        layout.addWidget(btn_frame)
        
        # Conectar botones
        btn_seleccionar.clicked.connect(lambda: self.on_seleccionar_manual(list_widget, productes_ordenats, nom_super, supermercat, dialog))
        btn_crear_nou.clicked.connect(lambda: self.on_crear_desde_dialog(nom_super, supermercat, dialog))
        btn_cancelar.clicked.connect(dialog.reject)
        
        # Conectar doble clic en la lista
        list_widget.itemDoubleClicked.connect(lambda: self.on_seleccionar_manual(list_widget, productes_ordenats, nom_super, supermercat, dialog))
        
        # Mostrar diálogo
        dialog.exec()

    def on_seleccionar_manual(self, list_widget, productes, nom_super, supermercat, dialog):
        """Cuando se selecciona un producto manualmente"""
        item = list_widget.currentItem()
        if not item:
            QMessageBox.warning(self.main_window, "Selecció", "Selecciona un producte de la llista")
            return
        
        index = list_widget.currentRow()
        producte_seleccionat = productes[index]

        # Poner en el ComboBox
        if hasattr(self.ui, 'nomProducteBDConeccioComboBox'):
            self.ui.nomProducteBDConeccioComboBox.setCurrentText(producte_seleccionat['nom'])
        
        # Informar al usuario
        QMessageBox.information(
            self.main_window,
            "Producte seleccionat",
            f"✅ S'ha seleccionat:\n\n"
            f"📦 Producte: {producte_seleccionat['nom']}\n"
            f"📦 Família: {producte_seleccionat.get('familia', 'N/A')}\n"
            f"🏪 Nom al super: {nom_super}\n\n"
            f"Ara pots ajustar la similitud i fer clic a 'AFEGIR'."
        )
        
        # Cerrar diálogo
        dialog.accept()

    def on_crear_desde_dialog(self, dialog, nom_super, supermercat):
        """Crear nou producte des del diàleg"""
        dialog.accept()
        self.activar_mode_creacio(nom_super, supermercat)

    def mostrar_opcions_baixa_similitud(self, resultats, nom_super, supermercat):
        """Versión completa para opciones con baja similitud"""
        self.nom_super_temporal = nom_super
        self.supermercat_temporal = supermercat
        
        # Crear diálogo de selección
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QRadioButton, QButtonGroup
        
        dialog = QDialog(self.main_window)
        dialog.setWindowTitle(f"Productes amb baixa similitud: '{nom_super}'")
        dialog.setMinimumWidth(500)
        
        layout = QVBoxLayout(dialog)
        
        # Título
        label_titol = QLabel(f"<h3>Resultats amb baixa similitud per a '{nom_super}':</h3>")
        layout.addWidget(label_titol)
        
        # Grupo de radio buttons
        button_group = QButtonGroup(dialog)
        
        # Añadir opciones
        for i, resultat in enumerate(resultats[:3]):
            radio = QRadioButton()
            
            # Texto informativo
            familia_text = f" ({resultat.get('familia', '')})" if resultat.get('familia') else ""
            radio.setText(f"{resultat['nom']}{familia_text} - Similitud: {resultat.get('similitud', 0):.2f}")
            
            layout.addWidget(radio)
            button_group.addButton(radio, i)
        
        # Botones de acción
        btn_seleccionar = QPushButton("✅ Seleccionar aquest producte")
        btn_manual = QPushButton("🔍 Buscar manualment")
        btn_crear = QPushButton("🆕 Crear producte nou")
        btn_cancelar = QPushButton("❌ Cancel·lar")
        
        layout.addWidget(btn_seleccionar)
        layout.addWidget(btn_manual)
        layout.addWidget(btn_crear)
        layout.addWidget(btn_cancelar)
        
        # Conectar botones
        def on_seleccionar():
            selected_id = button_group.checkedId()
            if selected_id >= 0:
                resultat_seleccionat = resultats[selected_id]
                self.seleccionar_producte_baixa_similitud(resultat_seleccionat, nom_super, supermercat)
                dialog.accept()
            else:
                QMessageBox.warning(dialog, "Selecció", "Selecciona un producte de la llista")
        
        btn_seleccionar.clicked.connect(on_seleccionar)
        btn_manual.clicked.connect(lambda: (dialog.accept(), self.activar_triar_manual(nom_super, supermercat)))
        btn_crear.clicked.connect(lambda: (dialog.accept(), self.activar_mode_creacio(nom_super, supermercat)))
        btn_cancelar.clicked.connect(lambda: (dialog.accept(), self.limpiar_campo_nom_super()))
        
        # Seleccionar el primero por defecto
        if resultats:
            button_group.button(0).setChecked(True)
        
        dialog.exec()

    def on_seleccionar_suggerit(self, dialog, resultats):
        """Quan es selecciona un producte suggerit"""
        # Trobar quin radio està seleccionat
        index_seleccionat = -1
        for i in range(min(3, len(resultats))):
            radio = dialog.findChild(QRadioButton, f"radio_{i}")
            if radio and radio.isChecked():
                index_seleccionat = i
                break
        
        if index_seleccionat == -1:
            return
        
        resultat_seleccionat = resultats[index_seleccionat]

        # Guardar com a producte automàtic
        self.producte_trobat_automatic = {
            'id': resultat_seleccionat['id'],
            'nom': resultat_seleccionat['nom'],
            'similitud': resultat_seleccionat.get('similitud', 0),
            'familia': resultat_seleccionat.get('familia', '')
        }
        
        # Seleccionar al ComboBox
        if hasattr(self.ui, 'nomProducteBDConeccioComboBox'):
            self.ui.nomProducteBDConeccioComboBox.setCurrentText(resultat_seleccionat['nom'])
            if self.ui.nomProducteBDConeccioComboBox.isHidden():
                self.ui.nomProducteBDConeccioComboBox.show()
        
        # Tancar diàleg
        dialog.accept()
        
        # Missatge informatiu
        QMessageBox.information(
            self.main_window,
            "✅ Producte seleccionat",
            f"S'ha seleccionat:<br><br>"
            f"<b>{resultat_seleccionat['nom']}</b><br>"
            f"Similitud: {resultat_seleccionat.get('similitud', 0):.2f}<br><br>"
            f"Ara fes clic a <b>'AFEGIR'</b> per guardar."
        )
        
        # Focus al botó AFEGIR
        if hasattr(self.ui, 'afegirPushButton'):
            self.ui.afegirPushButton.setFocus()

    def on_buscar_manual_desde_dialog(self, dialog, nom_super, supermercat):
        """Buscar manualment des del diàleg"""
        dialog.accept()  # Tancar aquest diàleg primer
        
        # Cridar al mètode de cerca manual que ja tenim
        self.activar_triar_manual(nom_super, supermercat)

    def seleccionar_producte_baixa_similitud(self, resultat, nom_super, supermercat):
        """Seleccionar un producte específic de baixa similitud"""
        
        # Guardar com a producte trobat automàticament
        self.producte_trobat_automatic = {
            'id': resultat['id'],
            'nom': resultat['nom'],
            'similitud': resultat['similitud'],
            'familia': resultat.get('familia', '')
        }
        
        # Seleccionar al ComboBox
        if hasattr(self.ui, 'nomProducteBDConeccioComboBox'):
            self.ui.nomProducteBDConeccioComboBox.setCurrentText(resultat['nom'])
            if self.ui.nomProducteBDConeccioComboBox.isHidden():
                self.ui.nomProducteBDConeccioComboBox.show()
        
        # Missatge informatiu
        QMessageBox.information(
            self.main_window,
            "✅ Seleccionat",
            f"Producte seleccionat:<br><br>"
            f"<b>{resultat['nom']}</b><br>"
            f"Similitud: {resultat['similitud']:.2f}<br><br>"
            f"Ara fes clic a <b>'AFEGIR'</b> per guardar."
        )
        
        # Focus al botó AFEGIR
        if hasattr(self.ui, 'afegirPushButton'):
            self.ui.afegirPushButton.setFocus()

    def limpiar_campo_nom_super(self):
        """Limpia el campo del nombre del supermercado"""
        if hasattr(self.ui, 'introNomSuperLineEdit'):
            self.ui.introNomSuperLineEdit.clear()
            self.ui.introNomSuperLineEdit.setFocus()
        if hasattr(self.ui, 'introSuperComboBox'):
            self.ui.introSuperComboBox.setCurrentIndex(0)
            self.ui.introSuperComboBox.setFocus()

        # Netejar producte trobat automàticament
        if hasattr(self, 'producte_trobat_automatic'):
            self.producte_trobat_automatic = None

    def activar_mode_creacio(self, nom_super, supermercat):
        """Activa el mode de creació - ARA NOMÉS GUARDA DADES I MOSTRA DIÀLEG"""
        
        # Obtenir família seleccionada
        familia = ""
        if hasattr(self.ui, 'introFamiliaComboBox'):
            familia = self.ui.introFamiliaComboBox.currentText()
        
        # MOSTRAR DIRECTAMENT EL DIÀLEG DE CREACIÓ
        self.mostrar_opcio_creacio_nou(nom_super, familia, supermercat)

    def preparar_nom_suggerit(self, nom_super):
        """Prepara un nom suggerit per al nou producte"""
        import re

        # Limpiar el nombre
        nom = nom_super.strip()
        
        # Quitar caracteres especiales
        nom = re.sub(r'[^\w\s\.\-]', ' ', nom)
        
        # Capitalizar cada palabra
        nom = ' '.join([palabra.capitalize() for palabra in nom.split()])
        
        # Si está vacío, devolver el original
        if not nom:
            nom = nom_super.strip().capitalize()
        
        return nom

    def executar(self):
        """Executa el bucle principal de l'aplicació"""
        
        # Verificar que la finestra existeix
        if hasattr(self, 'main_window'):
            self.main_window.show()
            
            # Executar bucle d'aplicació
            return_code = self.app.exec()
            return return_code
        else:
            print("❌ ERROR: No s'ha trobat la finestra (main_window)")
            return 1        

    def provar_connexio_bd(self):
        """Mètode de prova per verificar la connexió a la BD - VERSIÓ CORREGIDA"""        
        try:
            # Provar obtenir supermercats
            supers = self.controller.obtenir_supers_disponibles()

            # Provar obtenir famílies
            families = self.controller.obtenir_families_disponibles()
            
            # Provar obtenir tots els productes (versió segura)
            try:
                productes = self.controller.obtenir_tots_productes()
                
                # Mostrar els primers 5 productes
                for i, prod in enumerate(productes[:5]):
                    nom = prod.get('nom', 'Sense nom')
                
                if len(productes) == 0:
                    return True  # Retornem True igualment, la BD funciona
                
            except Exception as e_productes:
                print(f"⚠️ Error obtenint productes (potser taula buida): {e_productes}")
                print("ℹ️ Continuant sense productes...")
                return True  # La BD funciona, però la taula pot estar buida
            
            return len(productes) > 0
            
        except Exception as e:
            print(f"❌ Error en prova de connexió: {e}")
            import traceback
            traceback.print_exc()
            return False

    def seleccionar_producte_suggerit(self, resultat, nom_super, supermercat):
        """Seleccionar un producte suggerit - VERSIÓ FUNCIONAL"""
        
        # 1. Guardar producte automàtic
        self.producte_trobat_automatic = {
            'id': resultat['id'],
            'nom': resultat['nom'],
            'similitud': resultat.get('similitud', 0)
        }
        
        # 2. ACTUALITZAR EL COMBOBOX CORRECTAMENT
        if hasattr(self.ui, 'nomProducteBDConeccioComboBox'):
            # Netejar si cal
            current_text = self.ui.nomProducteBDConeccioComboBox.currentText()
            if current_text != resultat['nom']:
                self.ui.nomProducteBDConeccioComboBox.setCurrentText("")
            
            # Afegir si no existeix
            index = self.ui.nomProducteBDConeccioComboBox.findText(resultat['nom'])
            if index == -1:  # No existeix
                self.ui.nomProducteBDConeccioComboBox.addItem(resultat['nom'])
            
            # Seleccionar
            self.ui.nomProducteBDConeccioComboBox.setCurrentText(resultat['nom'])
            
            # Mostrar si està ocult
            if self.ui.nomProducteBDConeccioComboBox.isHidden():
                self.ui.nomProducteBDConeccioComboBox.show()

        # 3. Informar usuari
        QMessageBox.information(
            self.main_window,
            "✅ Seleccionat",
            f"Producte seleccionat: {resultat['nom']}\n\n"
            f"Similitud: {resultat.get('similitud', 0):.2f}\n\n"
            f"Ara fes clic a 'AFEGIR'"
        )
        
        # 4. Focus al botó AFEGIR
        if hasattr(self.ui, 'afegirPushButton'):
            self.ui.afegirPushButton.setFocus()

    def mostrar_dialog_afegir_super(self):
        """Mostra diàleg per afegir nou supermercat"""
        from PySide6.QtWidgets import QInputDialog
        
        # Demanar nom del nou supermercat
        nou_super, ok = QInputDialog.getText(
            self.main_window,
            "➕ Afegir nou supermercat",
            "Introdueix el nom del nou supermercat:\n\n" +
            "Exemple: Mercadona, Carrefour, BonÀrea...",
            text=""
        )
        
        if not ok or not nou_super.strip():
            return  # Usuari ha cancel·lat
        
        nou_super = nou_super.strip()
        
        # Verificar longitud mínima
        if len(nou_super) < 2:
            QMessageBox.warning(
                self.main_window,
                "Nom massa curt",
                "El nom del supermercat ha de tenir almenys 2 caràcters."
            )
            return
        
        # ⭐⭐ Cridar directament a la funció de llistes.py
        # (O potser al teu controller, si tens la funció allà)
        try:
            from config.llistes import afegir_super
            exitos, missatge = afegir_super(nou_super)
            
            if exitos:
                # Actualitzar el ComboBox de supermercats
                self.actualitzar_llista_supers_després_afegir(nou_super)
                
                # Missatge d'èxit
                QMessageBox.information(
                    self.main_window,
                    "✅ Supermercat afegit",
                    f"{missatge}\n\n" +
                    f"Ara pots seleccionar '{nou_super}' de la llista."
                )
            else:
                # Missatge d'error
                QMessageBox.warning(
                    self.main_window,
                    "❌ No s'ha pogut afegir",
                    missatge
                )
                
        except Exception as e:
            QMessageBox.critical(
                self.main_window,
                "❌ Error",
                f"No s'ha pogut afegir el supermercat:\n\n{e}"
            )

    def actualitzar_llista_supers_després_afegir(self, nou_super=""):
        """Actualitza el ComboBox de supermercats després d'afegir un nou"""
        
        if not hasattr(self.ui, 'introSuperComboBox'):
            return
        
        try:
            # Guardar el valor actualment seleccionat
            valor_actual = self.ui.introSuperComboBox.currentText()
            
            # Netejar i tornar a carregar
            self.ui.introSuperComboBox.clear()
            self.ui.introSuperComboBox.addItem("")  # Opció buida
            
            # Obtenir supermercats actualitzats DES DE LLISTES.PY
            from config.llistes import obtenir_supers
            supers = obtenir_supers()
            
            self.ui.introSuperComboBox.addItems(supers)
            
            # Seleccionar el valor apropiat
            if nou_super and nou_super in supers:
                # Seleccionar el nou supermercat afegit
                self.ui.introSuperComboBox.setCurrentText(nou_super)
            elif valor_actual and valor_actual in supers:
                # Mantenir el que estava seleccionat
                self.ui.introSuperComboBox.setCurrentText(valor_actual)
            else:
                # Seleccionar opció buida
                self.ui.introSuperComboBox.setCurrentIndex(0)
                
        except Exception as e:
            print(f"❌ Error actualitzant llista supers: {e}")

    def confirmar_i_modificar_producte(self, id_producte, nom_producte_actual, nom_super, supermercat, similitud):
        """Versión unificada y mejorada para confirmar/modificar producto"""
        
        from PySide6.QtWidgets import QInputDialog, QLineEdit, QMessageBox
        from PySide6.QtCore import QTimer
        
        # Preparar el texto del mensaje
        missatge = (
            f"<b>Confirmació d'afegiment:</b><br><br>"
            f"🏪 <b>Nom al super:</b> {nom_super}<br>"
            f"📍 <b>Supermercat:</b> {supermercat}<br>"
            f"🎯 <b>Similitud:</b> {similitud:.2f}<br><br>"
            f"<b>Producte seleccionat:</b><br>"
            f"{nom_producte_actual}<br><br>"
            f"<b>Modifica el nom si cal:</b>"
        )
        
        # Crear diálogo personalizado
        nou_nom, ok = QInputDialog.getText(
            self.main_window,
            "✏️ Confirmar/Modificar producte",
            missatge,
            QLineEdit.Normal,
            nom_producte_actual
        )
        
        if not ok:
            return None, None  # Usuario canceló
        
        nou_nom = nou_nom.strip()
        
        # Validaciones
        if not nou_nom:
            QMessageBox.warning(self.main_window, "Error", "El nom no pot estar buit.")
            return self.confirmar_i_modificar_producte(id_producte, nom_producte_actual, nom_super, supermercat, similitud)
        
        # Si no cambió, usar el original
        if nou_nom == nom_producte_actual:
            return id_producte, nom_producte_actual
        
        # Verificar si el nuevo nombre ya existe
        producte_existent = self.controller.obtenir_producte_per_nom(nou_nom)
        
        if producte_existent:
            # Preguntar si usar el existente
            resposta = QMessageBox.question(
                self.main_window,
                "Nom ja existeix",
                f"⚠️ El nom '<b>{nou_nom}</b>' ja existeix.<br><br>"
                f"ID: {producte_existent['id']}<br>"
                f"Família: {producte_existent.get('familia', 'N/A')}<br><br>"
                f"Què vols fer?<br><br>"
                f"✅ <b>Usar el producte existent</b><br>"
                f"🔄 <b>Provar un altre nom</b><br>"
                f"❌ <b>Cancel·lar</b>",
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
                QMessageBox.Yes
            )
            
            if resposta == QMessageBox.Yes:
                return producte_existent['id'], producte_existent['nom']
            elif resposta == QMessageBox.No:
                return self.confirmar_i_modificar_producte(id_producte, nom_producte_actual, nom_super, supermercat, similitud)
            else:
                return None, None
        
        # El nuevo nombre NO existe - modificar el producto actual
        exitos, missatge_modificacio = self.controller.modificar_producte(
            id_producte,
            nom_estandard=nou_nom
        )
        
        if exitos:
            QMessageBox.information(
                self.main_window,
                "✅ Nom modificat",
                f"S'ha canviat el nom a: <b>{nou_nom}</b>"
            )
            return id_producte, nou_nom
        else:
            # Error al modificar
            resposta_error = QMessageBox.question(
                self.main_window,
                "❌ Error modificant",
                f"No s'ha pogut modificar el nom:<br><br>"
                f"{missatge_modificacio}<br><br>"
                f"Vols provar un altre nom?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )
            
            if resposta_error == QMessageBox.Yes:
                return self.confirmar_i_modificar_producte(id_producte, nom_producte_actual, nom_super, supermercat, similitud)
            else:
                return None, None

def main():
    """Funció principal mínima"""
        
    try:
        # Crear instància
        aplicacio = ConnectFormulari()
        
        # Executar
        codi_sortida = aplicacio.executar()
        sys.exit(codi_sortida)
        
    except Exception as e:
        print(f"\n❌❌❌ ERROR FATAL: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

# Punt d'entrada
if __name__ == "__main__":
    main()