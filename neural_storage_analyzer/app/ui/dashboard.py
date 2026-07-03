from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *
from .main_window import COLORS

class DashboardWidget(QWidget):
    """Widget dashboard avec graphiques et statistiques"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setSpacing(16)

        # En-tête
        header = QLabel("📊 Vue d'ensemble")
        header.setStyleSheet(f"font-size:24px; font-weight:bold; color:{COLORS['text']};")
        self.layout.addWidget(header)

        # Grid des métriques
        grid = QGridLayout()
        grid.setSpacing(12)
        self.metrics = {}
        metrics = [
            ("🗄️ Total", "0 Go", 0, 0),
            ("📀 Utilisé", "0 Go", 0, 1),
            ("♻️ Récupérable", "0 Go", 1, 0),
            ("🧠 Santé", "0%", 1, 1),
            ("📁 Fichiers", "0", 2, 0),
            ("🗑️ Doublons", "0", 2, 1),
        ]
        for label, value, row, col in metrics:
            card = self._create_metric_card(label, value)
            grid.addWidget(card, row, col)
            self.metrics[label] = card

        self.layout.addLayout(grid)

        # Barre de progression santé
        health_frame = QFrame()
        health_frame.setStyleSheet(f"background:{COLORS['card']}; border:1px solid {COLORS['card_border']}; border-radius:12px; padding:16px;")
        hl = QHBoxLayout(health_frame)
        hl.addWidget(QLabel("🧠 Santé du disque"))

        self.health_bar = QProgressBar()
        self.health_bar.setRange(0, 100)
        self.health_bar.setValue(0)
        self.health_bar.setStyleSheet(f"""
            QProgressBar {{ background:{COLORS['card_border']}; border-radius:10px; height:12px; }}
            QProgressBar::chunk {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 {COLORS['red']}, stop:0.5 {COLORS['orange']}, stop:1 {COLORS['green']});
                border-radius:10px;
            }}
        """)
        hl.addWidget(self.health_bar)

        self.health_label = QLabel("0%")
        self.health_label.setStyleSheet(f"font-size:14px; font-weight:bold; color:{COLORS['text']};")
        hl.addWidget(self.health_label)
        hl.addStretch()

        self.layout.addWidget(health_frame)

        # Top 5 dossiers
        top_label = QLabel("📈 Top 5 dossiers")
        top_label.setStyleSheet(f"font-size:16px; font-weight:bold; color:{COLORS['text']};")
        self.layout.addWidget(top_label)

        self.top_list = QListWidget()
        self.top_list.setStyleSheet(f"""
            QListWidget {{
                background:{COLORS['card']}; border:1px solid {COLORS['card_border']};
                border-radius:12px; padding:8px;
            }}
            QListWidget::item {{ padding:8px; color:{COLORS['text_dim']}; }}
        """)
        self.layout.addWidget(self.top_list)

        self.layout.addStretch()

    def _create_metric_card(self, label: str, value: str) -> QFrame:
        card = QFrame()
        card.setStyleSheet(f"""
            background:{COLORS['card']}; border:1px solid {COLORS['card_border']};
            border-radius:12px; padding:12px;
        """)
        layout = QVBoxLayout(card)
        lbl = QLabel(label)
        lbl.setStyleSheet(f"color:{COLORS['text_dim']}; font-size:12px;")
        layout.addWidget(lbl)
        val = QLabel(value)
        val.setStyleSheet(f"font-size:20px; font-weight:bold; color:{COLORS['text']};")
        layout.addWidget(val)
        return card

    def update_metrics(self, stats: dict):
        """Met à jour les métriques du dashboard"""
        self.metrics["🗄️ Total"].findChildren(QLabel)[1].setText(f"{stats.get('total_gb', 0):.1f} Go")
        self.metrics["📀 Utilisé"].findChildren(QLabel)[1].setText(f"{stats.get('used_gb', 0):.1f} Go")
        self.metrics["♻️ Récupérable"].findChildren(QLabel)[1].setText(f"{stats.get('freeable_gb', 0):.1f} Go")
        self.metrics["🧠 Santé"].findChildren(QLabel)[1].setText(f"{stats.get('health', 0):.0f}%")
        self.metrics["📁 Fichiers"].findChildren(QLabel)[1].setText(f"{stats.get('file_count', 0)}")
        self.metrics["🗑️ Doublons"].findChildren(QLabel)[1].setText(f"{stats.get('duplicate_count', 0)}")

        # Barre de santé
        health = stats.get('health', 0)
        self.health_bar.setValue(int(health))
        self.health_label.setText(f"{health:.0f}%")

    def update_top_folders(self, folders: list):
        """Met à jour la liste des top dossiers"""
        self.top_list.clear()
        for name, size in folders[:5]:
            self.top_list.addItem(f"{name} — {size:.1f} Go")