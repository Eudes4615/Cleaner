import time
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QProgressBar,
    QPushButton,
    QSplitter,
    QStatusBar,
    QTableWidget,
    QTableWidgetItem,
    QTreeWidget,
    QVBoxLayout,
    QWidget,
)

from ..services.duplicate_service import DuplicateService
from ..services.scan_service import ScanService


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Neural Storage Analyzer")
        self.resize(1200, 700)

        self.scan_service = ScanService()
        self.dup_service = DuplicateService()
        self.scan_paths: list[str] = []
        self.current_scan_id = None
        self.start_time = None

        self._build_ui()
        self._connect_signals()

    def _build_ui(self):
        root = QWidget()
        self.setCentralWidget(root)
        main_layout = QVBoxLayout(root)

        toolbar = QHBoxLayout()
        self.btn_choose = QPushButton("📂 Choisir un dossier")
        self.btn_scan = QPushButton("🔍 Scanner")
        self.btn_stop = QPushButton("⏹ Stop")
        self.btn_clean = QPushButton("🗑 Nettoyer")
        self.btn_restore = QPushButton("↩ Restaurer")
        self.btn_settings = QPushButton("⚙ Paramètres")

        for button in (
            self.btn_choose,
            self.btn_scan,
            self.btn_stop,
            self.btn_clean,
            self.btn_restore,
            self.btn_settings,
        ):
            toolbar.addWidget(button)
        toolbar.addStretch()
        main_layout.addLayout(toolbar)

        # Ces opérations nécessitent encore une politique de suppression/restauration
        # complète ; les désactiver évite de présenter un bouton trompeur.
        for button in (self.btn_clean, self.btn_restore, self.btn_settings):
            button.setEnabled(False)
            button.setToolTip("Fonctionnalité non disponible dans cette version")
        self.btn_stop.setEnabled(False)

        self.lbl_path = QLabel("Dossier : aucun dossier sélectionné")
        self.lbl_path.setToolTip("Choisissez un dossier avant de lancer le scan")
        main_layout.addWidget(self.lbl_path)

        dashboard = QHBoxLayout()
        self.lbl_space = QLabel("💾 0 MB")
        self.lbl_files = QLabel("📁 0 fichiers")
        self.lbl_duplicates = QLabel("🔄 0 doublons")
        self.lbl_gain = QLabel("♻ 0 MB récupérables")
        for label in (
            self.lbl_space,
            self.lbl_files,
            self.lbl_duplicates,
            self.lbl_gain,
        ):
            dashboard.addWidget(label)
        dashboard.addStretch()
        main_layout.addLayout(dashboard)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.tree = QTreeWidget()
        self.tree.setHeaderLabel("Catégories")
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(
            ["Fichier", "Taille", "Type", "Score", "Importance"]
        )
        splitter.addWidget(self.tree)
        splitter.addWidget(self.table)
        main_layout.addWidget(splitter)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.status_bar.addPermanentWidget(self.progress)
        self.lbl_status = QLabel("Prêt")
        self.status_bar.addWidget(self.lbl_status)

    def _connect_signals(self):
        self.btn_choose.clicked.connect(self._choose_scan_path)
        self.btn_scan.clicked.connect(self._start_scan)
        self.btn_stop.clicked.connect(self._stop_scan)

        self.scan_service.progress.connect(self._on_progress)
        self.scan_service.status.connect(self._on_status)
        self.scan_service.batch_saved.connect(self._on_batch_saved)
        self.scan_service.finished.connect(self._on_scan_finished)
        self.scan_service.error.connect(self._on_error)
        self.scan_service.duplicate_scan_requested.connect(self._on_duplicate_request)

        self.dup_service.status.connect(self._on_status)
        self.dup_service.group_found.connect(self._on_duplicate_group)
        self.dup_service.finished.connect(self._on_duplicates_finished)
        self.dup_service.error.connect(self._on_error)

    def _choose_scan_path(self):
        selected = QFileDialog.getExistingDirectory(
            self,
            "Choisir le dossier à analyser",
            str(Path.home()),
        )
        if not selected:
            return
        self.scan_paths = [selected]
        self.lbl_path.setText(f"Dossier : {selected}")
        self.lbl_status.setText("Dossier prêt à être analysé")

    def _start_scan(self):
        if not self.scan_paths:
            self._choose_scan_path()
        if not self.scan_paths:
            self._on_error("Choisissez un dossier avant de lancer le scan.")
            return

        self.progress.setValue(0)
        self.table.setRowCount(0)
        self.start_time = time.time()
        self.btn_choose.setEnabled(False)
        self.btn_scan.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.scan_service.start_scan(
            paths=self.scan_paths,
            min_size_mb=0,
            check_duplicates=True,
        )

    def _stop_scan(self):
        self.scan_service.cancel_scan()
        self.dup_service.cancel()
        self.btn_stop.setEnabled(False)
        self.lbl_status.setText("Annulation demandée…")

    def _set_idle_state(self):
        self.btn_choose.setEnabled(True)
        self.btn_scan.setEnabled(True)
        self.btn_stop.setEnabled(False)

    def _on_progress(self, current, total):
        if total > 0:
            self.progress.setValue(min(100, int(current * 100 / total)))

    def _on_status(self, msg):
        self.lbl_status.setText(msg)

    def _on_batch_saved(self, count):
        self.status_bar.showMessage(f"Lot sauvegardé : {count} fichier(s)", 2000)

    def _on_scan_finished(self, scan_id: int):
        self.current_scan_id = scan_id
        elapsed = time.time() - self.start_time if self.start_time else 0
        self._set_idle_state()
        self.status_bar.showMessage(f"Scan terminé en {elapsed:.1f}s", 5000)

    def _on_error(self, msg: str):
        self._set_idle_state()
        self.status_bar.showMessage(f"Erreur : {msg}", 5000)

    def _on_duplicate_request(self, scan_id: int):
        self.dup_service.start(scan_id)

    def _on_duplicate_group(self, group):
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem(group.hash))
        self.table.setItem(row, 1, QTableWidgetItem(f"{group.wasted_space_mb:.2f} MB"))
        self.table.setItem(row, 2, QTableWidgetItem(f"{len(group.files)} doublons"))
        self.table.setItem(row, 3, QTableWidgetItem("DUP"))
        self.table.setItem(row, 4, QTableWidgetItem("HIGH"))

    def _on_duplicates_finished(self, scan_id: int):
        self._set_idle_state()
        self.status_bar.showMessage("Analyse des doublons terminée", 5000)
