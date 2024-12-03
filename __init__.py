def classFactory(iface):
    from .ppk_validator import PPKValidator
    return PPKValidator(iface)

# ppk_validator.py
from qgis.PyQt.QtWidgets import QAction, QFileDialog, QSpinBox
from qgis.PyQt.QtGui import QIcon
from qgis.core import QgsProject
import os.path

class PPKValidator:
    def __init__(self, iface):
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)
        self.actions = []

    def initGui(self):
        """Create the menu entries and toolbar icons inside QGIS."""
        icon_path = os.path.join(self.plugin_dir, 'icon.png')
        action = QAction(
            QIcon(icon_path),
            'PPK Image Validator',
            self.iface.mainWindow()
        )
        action.triggered.connect(self.run)
        self.iface.addToolBarIcon(action)
        self.actions.append(action)

    def unload(self):
        """Removes the plugin menu item and icon."""
        for action in self.actions:
            self.iface.removeToolBarIcon(action)

    def run(self):
        """Run method that loads and starts the plugin"""
        # Show the dialog
        from .ppk_validator_dialog import PPKValidatorDialog
        dialog = PPKValidatorDialog()
        dialog.show()