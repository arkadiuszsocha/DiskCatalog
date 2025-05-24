import sys
import os
import sqlite3
from datetime import datetime
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QFileDialog, QTreeView, QVBoxLayout, QWidget,
    QMessageBox, QListWidget, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
    QLabel, QStatusBar, QStyleFactory, QMenu, QInputDialog, QMenuBar
)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QIcon, QPalette, QColor, QFont

class FolderCatalogApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Disk Catalog")
        self.resize(1000, 800)
        
        # Set dark theme
        self.set_dark_theme()
        
        # Initialize database
        self.init_database()

        # Create menu bar
        self.create_menu_bar()

        # Create status bar
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("Ready")

        # Main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Left panel with catalog list
        left_panel = QWidget()
        left_panel.setMaximumWidth(250)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        # Catalog list header
        catalog_header = QLabel("Catalogs")
        catalog_header.setStyleSheet("""
            QLabel {
                background-color: #2d2d2d;
                color: #ffffff;
                padding: 8px;
                font-weight: bold;
            }
        """)
        left_layout.addWidget(catalog_header)
        
        # Catalog list
        self.catalog_list = QListWidget()
        self.catalog_list.setStyleSheet("""
            QListWidget {
                background-color: #1e1e1e;
                color: #ffffff;
                border: none;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #2d2d2d;
            }
            QListWidget::item:selected {
                background-color: #0d47a1;
                color: #ffffff;
            }
            QListWidget::item:hover {
                background-color: #1565c0;
                color: #ffffff;
            }
        """)
        self.catalog_list.itemClicked.connect(self.load_catalog)
        self.catalog_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.catalog_list.customContextMenuRequested.connect(self.show_catalog_context_menu)
        left_layout.addWidget(self.catalog_list)
        
        # Right panel with tree
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        # Tree view
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Name", "Size", "Modified"])
        self.tree.setColumnWidth(0, 400)
        self.tree.setStyleSheet("""
            QTreeWidget {
                background-color: #1e1e1e;
                color: #ffffff;
                border: none;
            }
            QTreeWidget::item {
                padding: 4px;
            }
            QTreeWidget::item:selected {
                background-color: #0d47a1;
                color: #ffffff;
            }
            QTreeWidget::item:hover {
                background-color: #1565c0;
                color: #ffffff;
            }
            QHeaderView::section {
                background-color: #2d2d2d;
                color: #ffffff;
                padding: 8px;
                border: none;
                border-right: 1px solid #3d3d3d;
            }
        """)
        
        right_layout.addWidget(self.tree)
        
        # Add panels to main layout
        main_layout.addWidget(left_panel)
        main_layout.addWidget(right_panel)
        
        # Update catalog list
        self.update_catalog_list()

    def create_menu_bar(self):
        """Create menu bar with File menu"""
        menubar = self.menuBar()
        menubar.setStyleSheet("""
            QMenuBar {
                background-color: #2d2d2d;
                color: #ffffff;
            }
            QMenuBar::item {
                padding: 8px 12px;
            }
            QMenuBar::item:selected {
                background-color: #0d47a1;
                color: #ffffff;
            }
            QMenu {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #3d3d3d;
            }
            QMenu::item {
                padding: 8px 20px;
            }
            QMenu::item:selected {
                background-color: #0d47a1;
                color: #ffffff;
            }
        """)

        # File menu
        file_menu = menubar.addMenu("File")
        
        # New Catalog action
        new_catalog_action = file_menu.addAction("New Catalog")
        new_catalog_action.triggered.connect(self.save_catalog)
        
        file_menu.addSeparator()
        
        # Update Catalog action
        update_catalog_action = file_menu.addAction("Update Catalog")
        update_catalog_action.triggered.connect(self.update_selected_catalog)
        
        # Rename Catalog action
        rename_catalog_action = file_menu.addAction("Rename Catalog")
        rename_catalog_action.triggered.connect(self.rename_selected_catalog)
        
        file_menu.addSeparator()
        
        # Exit action
        exit_action = file_menu.addAction("Exit")
        exit_action.triggered.connect(self.close)

    def update_selected_catalog(self):
        """Update the currently selected catalog"""
        current_item = self.catalog_list.currentItem()
        if current_item:
            self.update_catalog(current_item)
        else:
            QMessageBox.warning(self, "Warning", "Please select a catalog to update")

    def rename_selected_catalog(self):
        """Rename the currently selected catalog"""
        current_item = self.catalog_list.currentItem()
        if current_item:
            self.rename_catalog(current_item)
        else:
            QMessageBox.warning(self, "Warning", "Please select a catalog to rename")

    def show_catalog_context_menu(self, position):
        """Show context menu for catalog list"""
        item = self.catalog_list.itemAt(position)
        if item is None:
            return

        menu = QMenu()
        menu.setStyleSheet("""
            QMenu {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #3d3d3d;
            }
            QMenu::item {
                padding: 8px 20px;
            }
            QMenu::item:selected {
                background-color: #0d47a1;
                color: #ffffff;
            }
        """)

        update_action = menu.addAction("Update Catalog")
        rename_action = menu.addAction("Rename Catalog")
        delete_action = menu.addAction("Delete Catalog")

        action = menu.exec_(self.catalog_list.mapToGlobal(position))
        
        if action == update_action:
            self.update_catalog(item)
        elif action == rename_action:
            self.rename_catalog(item)
        elif action == delete_action:
            self.delete_catalog(item)

    def update_catalog(self, item):
        """Update the selected catalog"""
        catalog_name = item.text().split(" (")[0]
        self.cursor.execute('SELECT id, root_path FROM catalogs WHERE name = ?', (catalog_name,))
        result = self.cursor.fetchone()
        if not result:
            return

        catalog_id, root_path = result
        
        try:
            # Delete existing files
            self.cursor.execute('DELETE FROM files WHERE catalog_id = ?', (catalog_id,))
            
            # Walk through directory and save structure
            for root, dirs, files in os.walk(root_path):
                # Save directories
                for dir_name in dirs:
                    full_path = os.path.join(root, dir_name)
                    self.cursor.execute(
                        'INSERT INTO files (catalog_id, path, name, is_directory, size, modified_at) VALUES (?, ?, ?, ?, ?, ?)',
                        (catalog_id, full_path, dir_name, True, 0, datetime.fromtimestamp(os.path.getmtime(full_path)))
                    )

                # Save files
                for file_name in files:
                    full_path = os.path.join(root, file_name)
                    try:
                        size = os.path.getsize(full_path)
                        modified = datetime.fromtimestamp(os.path.getmtime(full_path))
                        self.cursor.execute(
                            'INSERT INTO files (catalog_id, path, name, is_directory, size, modified_at) VALUES (?, ?, ?, ?, ?, ?)',
                            (catalog_id, full_path, file_name, False, size, modified)
                        )
                    except (OSError, FileNotFoundError):
                        continue

            self.conn.commit()
            self.load_catalog(item)  # Reload the catalog
            self.statusBar.showMessage(f"Catalog '{catalog_name}' updated successfully")
            QMessageBox.information(self, "Success", f"Catalog '{catalog_name}' has been updated successfully!")

        except sqlite3.Error as e:
            QMessageBox.critical(self, "Error", f"Error updating catalog: {str(e)}")
            self.conn.rollback()

    def rename_catalog(self, item):
        """Rename the selected catalog"""
        old_name = item.text().split(" (")[0]
        new_name, ok = QInputDialog.getText(
            self, "Rename Catalog", 
            "Enter new name:", 
            text=old_name
        )
        
        if ok and new_name and new_name != old_name:
            try:
                self.cursor.execute(
                    'UPDATE catalogs SET name = ? WHERE name = ?',
                    (new_name, old_name)
                )
                self.conn.commit()
                self.update_catalog_list()
                self.statusBar.showMessage(f"Catalog renamed from '{old_name}' to '{new_name}'")
            except sqlite3.Error as e:
                QMessageBox.critical(self, "Error", f"Error renaming catalog: {str(e)}")
                self.conn.rollback()

    def delete_catalog(self, item):
        """Delete the selected catalog"""
        catalog_name = item.text().split(" (")[0]
        reply = QMessageBox.question(
            self, "Delete Catalog",
            f"Are you sure you want to delete the catalog '{catalog_name}'?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                self.cursor.execute('DELETE FROM files WHERE catalog_id IN (SELECT id FROM catalogs WHERE name = ?)', (catalog_name,))
                self.cursor.execute('DELETE FROM catalogs WHERE name = ?', (catalog_name,))
                self.conn.commit()
                self.update_catalog_list()
                self.tree.clear()
                self.statusBar.showMessage(f"Catalog '{catalog_name}' deleted")
            except sqlite3.Error as e:
                QMessageBox.critical(self, "Error", f"Error deleting catalog: {str(e)}")
                self.conn.rollback()

    def set_dark_theme(self):
        """Set dark theme for the application"""
        app = QApplication.instance()
        app.setStyle(QStyleFactory.create("Fusion"))
        
        dark_palette = QPalette()
        dark_palette.setColor(QPalette.Window, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.WindowText, Qt.white)
        dark_palette.setColor(QPalette.Base, QColor(25, 25, 25))
        dark_palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.ToolTipBase, Qt.white)
        dark_palette.setColor(QPalette.ToolTipText, Qt.white)
        dark_palette.setColor(QPalette.Text, Qt.white)
        dark_palette.setColor(QPalette.Button, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.ButtonText, Qt.white)
        dark_palette.setColor(QPalette.BrightText, Qt.red)
        dark_palette.setColor(QPalette.Link, QColor(42, 130, 218))
        dark_palette.setColor(QPalette.Highlight, QColor(13, 71, 161))  # Darker blue for selection
        dark_palette.setColor(QPalette.HighlightedText, Qt.white)
        
        app.setPalette(dark_palette)
        app.setStyleSheet("""
            QToolTip { 
                color: #ffffff; 
                background-color: #2a82da; 
                border: 1px solid white; 
            }
            QMessageBox {
                background-color: #2d2d2d;
                color: #ffffff;
            }
            QMessageBox QLabel {
                color: #ffffff;
            }
            QInputDialog {
                background-color: #2d2d2d;
                color: #ffffff;
            }
            QInputDialog QLabel {
                color: #ffffff;
            }
            QInputDialog QLineEdit {
                background-color: #1e1e1e;
                color: #ffffff;
                border: 1px solid #3d3d3d;
                padding: 4px;
            }
        """)

    def init_database(self):
        """Initialize SQLite database and create necessary tables"""
        self.conn = sqlite3.connect('folder_catalog.db')
        self.cursor = self.conn.cursor()
        
        # Create tables if they don't exist
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS catalogs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                root_path TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                catalog_id INTEGER,
                path TEXT NOT NULL,
                name TEXT NOT NULL,
                is_directory BOOLEAN,
                size INTEGER,
                modified_at TIMESTAMP,
                FOREIGN KEY (catalog_id) REFERENCES catalogs (id)
            )
        ''')
        
        self.conn.commit()

    def update_catalog_list(self):
        """Update the list of saved catalogs"""
        self.catalog_list.clear()
        self.cursor.execute('SELECT id, name, root_path FROM catalogs ORDER BY created_at DESC')
        for catalog_id, name, path in self.cursor.fetchall():
            self.catalog_list.addItem(f"{name} ({os.path.basename(path)})")

    def load_catalog(self, item):
        """Load selected catalog into the tree view"""
        catalog_name = item.text().split(" (")[0]
        self.cursor.execute('SELECT id, root_path FROM catalogs WHERE name = ?', (catalog_name,))
        result = self.cursor.fetchone()
        if result:
            catalog_id, root_path = result
            self.tree.clear()
            
            # Get all files and directories for this catalog
            self.cursor.execute('''
                SELECT path, name, is_directory, size, modified_at 
                FROM files 
                WHERE catalog_id = ? 
                ORDER BY path
            ''', (catalog_id,))
            
            # Create a dictionary to store path -> item mapping
            path_to_item = {}
            
            # First pass: create all items
            for path, name, is_dir, size, modified in self.cursor.fetchall():
                parent_path = os.path.dirname(path)
                item = QTreeWidgetItem()
                item.setText(0, name)
                if not is_dir:
                    item.setText(1, self.format_size(size))
                item.setText(2, datetime.fromisoformat(modified).strftime('%Y-%m-%d %H:%M:%S'))
                path_to_item[path] = item
            
            # Second pass: set up parent-child relationships
            for path, item in path_to_item.items():
                parent_path = os.path.dirname(path)
                if parent_path in path_to_item:
                    path_to_item[parent_path].addChild(item)
                else:
                    self.tree.addTopLevelItem(item)
            
            self.statusBar.showMessage(f"Loaded catalog: {catalog_name}")

    def format_size(self, size):
        """Format file size in human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} PB"

    def save_catalog(self):
        """Save current folder structure to database"""
        root_path = QFileDialog.getExistingDirectory(self, "Select Folder to Catalog", os.path.expanduser("~"))
        if not root_path:
            return

        # Use folder name as catalog name
        catalog_name = os.path.basename(root_path)

        try:
            # Insert catalog
            self.cursor.execute(
                'INSERT INTO catalogs (name, root_path) VALUES (?, ?)',
                (catalog_name, root_path)
            )
            catalog_id = self.cursor.lastrowid

            # Walk through directory and save structure
            for root, dirs, files in os.walk(root_path):
                # Save directories
                for dir_name in dirs:
                    full_path = os.path.join(root, dir_name)
                    self.cursor.execute(
                        'INSERT INTO files (catalog_id, path, name, is_directory, size, modified_at) VALUES (?, ?, ?, ?, ?, ?)',
                        (catalog_id, full_path, dir_name, True, 0, datetime.fromtimestamp(os.path.getmtime(full_path)))
                    )

                # Save files
                for file_name in files:
                    full_path = os.path.join(root, file_name)
                    try:
                        size = os.path.getsize(full_path)
                        modified = datetime.fromtimestamp(os.path.getmtime(full_path))
                        self.cursor.execute(
                            'INSERT INTO files (catalog_id, path, name, is_directory, size, modified_at) VALUES (?, ?, ?, ?, ?, ?)',
                            (catalog_id, full_path, file_name, False, size, modified)
                        )
                    except (OSError, FileNotFoundError):
                        continue

            self.conn.commit()
            self.update_catalog_list()
            self.statusBar.showMessage(f"Catalog '{catalog_name}' saved successfully")
            QMessageBox.information(self, "Success", f"Catalog '{catalog_name}' has been saved successfully!")

        except sqlite3.Error as e:
            QMessageBox.critical(self, "Error", f"Error saving catalog: {str(e)}")
            self.conn.rollback()

    def closeEvent(self, event):
        """Clean up database connection when closing the application"""
        self.conn.close()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = FolderCatalogApp()
    window.show()
    sys.exit(app.exec_())
