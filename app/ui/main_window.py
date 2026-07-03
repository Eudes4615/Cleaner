import time
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QProgressBar, QSplitter,
    QTreeWidget, QTreeWidgetItem, QTableWidget,
    QTableWidgetItem, QStatusBar
)
from PyQt6.QtCore import Qt

from ..services.scan_service import ScanService
from ..services.duplicate_service import DuplicateService


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Neural Storage Analyzer")
        self.resize(1200, 700)

        self.scan_service = ScanService()
        self.dup_service = DuplicateService()

        self.current_scan_id = None
        self.start_time = None

        self._build_ui()
        self._connect_signals()

    def _build_ui(self):
        root = QWidget()
        self.setCentralWidget(root)
        main_layout = QVBoxLayout(root)

        # Toolbar
        toolbar = QHBoxLayout()
        self.btn_scan = QPushButton("🔍 Scanner")
        self.btn_stop = QPushButton("⏹ Stop")
        self.btn_clean = QPushButton("🗑 Nettoyer")
        self.btn_restore = QPushButton("↩ Restaurer")
        self.btn_settings = QPushButton("⚙ Paramètres")
        toolbar.addWidget(self.btn_scan)
        toolbar.addWidget(self.btn_stop)
        toolbar.addWidget(self.btn_clean)
        toolbar.addWidget(self.btn_restore)
        toolbar.addWidget(self.btn_settings)
        toolbar.addStretch()
        main_layout.addLayout(toolbar)

        # Dashboard
        dashboard = QHBoxLayout()
        self.lbl_space = QLabel("💾 0 MB")
        self.lbl_files = QLabel("📁 0 fichiers")
        self.lbl_duplicates = QLabel("🔄 0 doublons")
        self.lbl_gain = QLabel("♻ 0 MB récupérables")
        dashboard.addWidget(self.lbl_space)
        dashboard.addWidget(self.lbl_files)
        dashboard.addWidget(self.lbl_duplicates)
        dashboard.addWidget(self.lbl_gain)
        dashboard.addStretch()
        main_layout.addLayout(dashboard)

        # Splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.tree = QTreeWidget()
        self.tree.setHeaderLabel("Catégories")
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Fichier", "Taille", "Type", "Score", "Importance"])
        splitter.addWidget(self.tree)
        splitter.addWidget(self.table)
        main_layout.addWidget(splitter)

        # Status
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.progress = QProgressBar()
        self.progress.setValue(0)
        self.status_bar.addPermanentWidget(self.progress)
        self.lbl_status = QLabel("Idle")
        self.status_bar.addWidget(self.lbl_status)

    def _connect_signals(self):
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

    def _start_scan(self):
        self.progress.setValue(0)
        self.start_time = time.time()
        paths = ["C:/Users"]  # À remplacer par sélection utilisateur
        self.scan_service.start_scan(paths=paths, min_size_mb=0, check_duplicates=True)

    def _stop_scan(self):
        self.scan_service.cancel_scan()
        self.dup_service.cancel()

    def _on_progress(self, current, total):
        if total > 0:
            self.progress.setValue(int(current * 100 / total))

    def _on_status(self, msg):
        self.lbl_status.setText(msg)

    def _on_batch_saved(self, count):
        self.status_bar.showMessage(f"Batch sauvegardé: {count}", 2000)

    def _on_scan_finished(self, scan_id: int):
        self.current_scan_id = scan_id
        elapsed = time.time() - self.start_time if self.start_time else 0
        self.status_bar.showMessage(f"Scan terminé en {elapsed:.1f}s", 5000)

    def _on_error(self, msg: str):
        self.status_bar.showMessage(f"Erreur: {msg}", 5000)

    def _on_duplicate_request(self, scan_id: int):
        self.dup_service.start(scan_id)

    def _on_duplicate_group(self, group):
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem(group.hash))
        self.table.setItem(row, 1, QTableWidgetItem(str(group.wasted_space_mb)))
        self.table.setItem(row, 2, QTableWidgetItem(str(len(group.files))))
        self.table.setItem(row, 3, QTableWidgetItem("DUP"))
        self.table.setItem(row, 4, QTableWidgetItem("HIGH"))

    def _on_duplicates_finished(self, scan_id: int):
        self.status_bar.showMessage("Analyse des doublons terminée", 5000)