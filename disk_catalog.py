import sys
import os
import sqlite3
import hashlib
from datetime import datetime
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QFileDialog, QTreeView, QVBoxLayout, QWidget,
    QMessageBox, QListWidget, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
    QLabel, QStatusBar, QStyleFactory, QMenu, QInputDialog, QMenuBar,
    QProgressDialog, QCheckBox, QDialog, QDialogButtonBox, QFormLayout
)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QIcon, QPalette, QColor, QFont

class CompareOptionsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Compare Options")
        self.setup_ui()

    def setup_ui(self):
        layout = QFormLayout(self)
        
        self.check_size = QCheckBox("Compare file sizes")
        self.check_size.setChecked(True)
        layout.addRow(self.check_size)
        
        self.check_md5 = QCheckBox("Compare MD5 hashes")
        layout.addRow(self.check_md5)
        
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            Qt.Horizontal, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def get_options(self):
        return {
            'check_size': self.check_size.isChecked(),
            'check_md5': self.check_md5.isChecked()
        }

class ComparisonResultsWindow(QMainWindow):
    def __init__(self, catalog_name, compare_path, differences, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Comparison Results: {catalog_name}")
        self.resize(1200, 800)
        
        # Define colors for different states
        self.colors = {
            'same': QColor('#4caf50'),      # Green
            'modified': QColor('#ff9800'),   # Orange
            'missing': QColor('#f44336'),    # Red
            'new': QColor('#2196f3'),        # Blue
            'different': QColor('#9c27b0')   # Purple
        }
        
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QHBoxLayout(central_widget)
        
        # Left panel (Catalog)
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        catalog_label = QLabel(f"Catalog: {catalog_name}")
        catalog_label.setStyleSheet("""
            QLabel {
                background-color: #2d2d2d;
                color: #ffffff;
                padding: 8px;
                font-weight: bold;
            }
        """)
        left_layout.addWidget(catalog_label)
        
        self.catalog_tree = QTreeWidget()
        self.catalog_tree.setHeaderLabels(["Name", "Size", "Modified"])
        self.catalog_tree.setColumnWidth(0, 400)
        self.catalog_tree.setStyleSheet("""
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
        left_layout.addWidget(self.catalog_tree)
        
        # Right panel (Comparison)
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        compare_label = QLabel(f"Comparison Folder: {os.path.basename(compare_path)}")
        compare_label.setStyleSheet("""
            QLabel {
                background-color: #2d2d2d;
                color: #ffffff;
                padding: 8px;
                font-weight: bold;
            }
        """)
        right_layout.addWidget(compare_label)
        
        self.compare_tree = QTreeWidget()
        self.compare_tree.setHeaderLabels(["Name", "Size", "Modified", "Status"])
        self.compare_tree.setColumnWidth(0, 400)
        self.compare_tree.setStyleSheet(self.catalog_tree.styleSheet())
        right_layout.addWidget(self.compare_tree)
        
        # Add panels to main layout
        layout.addWidget(left_panel)
        layout.addWidget(right_panel)
        
        # Store differences for highlighting
        self.differences = differences
        self.compare_path = compare_path
        
        # Connect tree selection
        self.catalog_tree.itemSelectionChanged.connect(self.on_catalog_selection_changed)
        self.compare_tree.itemSelectionChanged.connect(self.on_compare_selection_changed)
        
        # Set dark theme
        self.set_dark_theme()
    
    def set_dark_theme(self):
        """Set dark theme for the window"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1e1e1e;
            }
            QWidget {
                background-color: #1e1e1e;
                color: #ffffff;
            }
        """)
    
    def add_items_to_trees(self, catalog_items, compare_items):
        """Add items to both trees and highlight differences"""
        # Create a dictionary to store path -> item mapping for catalog tree
        catalog_path_to_item = {}
        
        # Create a set of paths that have differences in their contents
        content_differences = set()
        for path in self.differences:
            parent_path = os.path.dirname(path)
            while parent_path:
                content_differences.add(parent_path)
                parent_path = os.path.dirname(parent_path)
        
        # First, create all catalog items with proper hierarchy
        for path, item_data in catalog_items.items():
            item = QTreeWidgetItem()
            item.setText(0, item_data['name'])
            if not item_data['is_directory']:
                item.setText(1, self.format_size(item_data['size']))
            item.setText(2, item_data['modified'].strftime('%Y-%m-%d %H:%M:%S'))
            item.setData(0, Qt.UserRole, path)
            
            # Color the item in catalog tree if it has differences
            if path in self.differences:
                if item_data['is_directory']:
                    color = self.colors['different']
                else:
                    color = self.colors['modified']
                for i in range(3):
                    item.setBackground(i, color)
            elif path in content_differences:
                # This is a parent folder of a different item
                color = self.colors['different']
                for i in range(3):
                    item.setBackground(i, color)
            
            # Store the item in the mapping
            catalog_path_to_item[path] = item
            
            # Find parent path
            parent_path = os.path.dirname(path)
            if parent_path in catalog_path_to_item:
                # Add as child to parent
                catalog_path_to_item[parent_path].addChild(item)
            else:
                # Add as top-level item
                self.catalog_tree.addTopLevelItem(item)
        
        # Now create comparison items following the same structure
        for path, item_data in catalog_items.items():
            # Create corresponding item in compare tree
            compare_item = QTreeWidgetItem()
            compare_item.setData(0, Qt.UserRole, path)
            
            if path in compare_items:
                # File exists in comparison folder
                compare_data = compare_items[path]
                compare_item.setText(0, compare_data['name'])
                if not compare_data['is_directory']:
                    compare_item.setText(1, self.format_size(compare_data['size']))
                compare_item.setText(2, compare_data['modified'].strftime('%Y-%m-%d %H:%M:%S'))
                
                # Check for differences
                if path in self.differences:
                    if item_data['is_directory']:
                        compare_item.setText(3, "Different Contents")
                        color = self.colors['different']
                    else:
                        compare_item.setText(3, "Modified")
                        color = self.colors['modified']
                    
                    # Apply color to all columns
                    for i in range(4):
                        compare_item.setBackground(i, color)
                elif path in content_differences:
                    # This is a parent folder of a different item
                    compare_item.setText(3, "Different Contents")
                    color = self.colors['different']
                    for i in range(4):
                        compare_item.setBackground(i, color)
                else:
                    compare_item.setText(3, "Same")
                    color = self.colors['same']
                    compare_item.setBackground(3, color)
            else:
                # File doesn't exist in comparison folder
                compare_item.setText(0, item_data['name'])
                if not item_data['is_directory']:
                    compare_item.setText(1, self.format_size(item_data['size']))
                compare_item.setText(2, item_data['modified'].strftime('%Y-%m-%d %H:%M:%S'))
                compare_item.setText(3, "Missing")
                color = self.colors['missing']
                
                # Apply color to all columns
                for i in range(4):
                    compare_item.setBackground(i, color)
            
            # Find parent path
            parent_path = os.path.dirname(path)
            if parent_path in catalog_path_to_item:
                # Add as child to parent's corresponding item in compare tree
                parent_compare_item = self.find_item_by_path(self.compare_tree, parent_path)
                if parent_compare_item:
                    parent_compare_item.addChild(compare_item)
                else:
                    self.compare_tree.addTopLevelItem(compare_item)
            else:
                # Add as top-level item
                self.compare_tree.addTopLevelItem(compare_item)
        
        # Add new files from comparison folder
        for path, item_data in compare_items.items():
            if path not in catalog_items:
                compare_item = QTreeWidgetItem()
                compare_item.setText(0, item_data['name'])
                if not item_data['is_directory']:
                    compare_item.setText(1, self.format_size(item_data['size']))
                compare_item.setText(2, item_data['modified'].strftime('%Y-%m-%d %H:%M:%S'))
                compare_item.setText(3, "New")
                color = self.colors['new']
                
                # Apply color to all columns
                for i in range(4):
                    compare_item.setBackground(i, color)
                
                compare_item.setData(0, Qt.UserRole, path)
                
                # Find parent path
                parent_path = os.path.dirname(path)
                parent_compare_item = self.find_item_by_path(self.compare_tree, parent_path)
                if parent_compare_item:
                    parent_compare_item.addChild(compare_item)
                else:
                    self.compare_tree.addTopLevelItem(compare_item)
    
    def find_item_by_path(self, tree, path):
        """Find an item in the tree by its path"""
        for i in range(tree.topLevelItemCount()):
            item = tree.topLevelItem(i)
            if item.data(0, Qt.UserRole) == path:
                return item
            # Check children
            child = self.find_item_in_children(item, path)
            if child:
                return child
        return None
    
    def find_item_in_children(self, parent_item, path):
        """Find an item in the children of a parent item"""
        for i in range(parent_item.childCount()):
            child = parent_item.child(i)
            if child.data(0, Qt.UserRole) == path:
                return child
            # Check grandchildren
            grandchild = self.find_item_in_children(child, path)
            if grandchild:
                return grandchild
        return None
    
    def format_size(self, size):
        """Format file size in human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} PB"
    
    def on_catalog_selection_changed(self):
        """Handle catalog tree selection change"""
        selected_items = self.catalog_tree.selectedItems()
        if selected_items:
            path = selected_items[0].data(0, Qt.UserRole)
            # Find and select corresponding item in compare tree
            self.select_item_by_path(self.compare_tree, path)
    
    def on_compare_selection_changed(self):
        """Handle compare tree selection change"""
        selected_items = self.compare_tree.selectedItems()
        if selected_items:
            path = selected_items[0].data(0, Qt.UserRole)
            # Find and select corresponding item in catalog tree
            self.select_item_by_path(self.catalog_tree, path)
    
    def select_item_by_path(self, tree, path):
        """Select an item in the tree by its path"""
        item = self.find_item_by_path(tree, path)
        if item:
            tree.setCurrentItem(item)

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
        
        # Compare Catalog action
        compare_catalog_action = file_menu.addAction("Compare Catalog")
        compare_catalog_action.triggered.connect(self.compare_selected_catalog)
        
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
        
        # Ask if user wants to calculate MD5 hashes
        calculate_md5 = QMessageBox.question(
            self, "MD5 Calculation",
            "Do you want to calculate MD5 hashes for files? (This will take longer but allows for more accurate comparison)",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        ) == QMessageBox.Yes
        
        try:
            # Delete existing files
            self.cursor.execute('DELETE FROM files WHERE catalog_id = ?', (catalog_id,))
            
            # Count total files for progress bar
            total_files = sum([len(files) for _, _, files in os.walk(root_path)])
            progress = QProgressDialog("Updating catalog...", "Cancel", 0, total_files, self)
            progress.setWindowModality(Qt.WindowModal)
            progress.setWindowTitle("Progress")
            files_processed = 0
            
            # Walk through directory and save structure
            for root, dirs, files in os.walk(root_path):
                # Save directories
                for dir_name in dirs:
                    full_path = os.path.join(root, dir_name)
                    rel_path = os.path.relpath(full_path, root_path)
                    self.cursor.execute(
                        'INSERT INTO files (catalog_id, path, name, is_directory, size, modified_at) VALUES (?, ?, ?, ?, ?, ?)',
                        (catalog_id, rel_path, dir_name, True, 0, datetime.fromtimestamp(os.path.getmtime(full_path)))
                    )

                # Save files
                for file_name in files:
                    if progress.wasCanceled():
                        self.conn.rollback()
                        return

                    full_path = os.path.join(root, file_name)
                    try:
                        rel_path = os.path.relpath(full_path, root_path)
                        size = os.path.getsize(full_path)
                        modified = datetime.fromtimestamp(os.path.getmtime(full_path))
                        
                        # Calculate MD5 if requested
                        md5_hash = self.calculate_md5(full_path) if calculate_md5 else None
                        
                        self.cursor.execute(
                            'INSERT INTO files (catalog_id, path, name, is_directory, size, modified_at, md5_hash) VALUES (?, ?, ?, ?, ?, ?, ?)',
                            (catalog_id, rel_path, file_name, False, size, modified, md5_hash)
                        )
                        
                        files_processed += 1
                        progress.setValue(files_processed)
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
                md5_hash TEXT,
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
            for rel_path, name, is_dir, size, modified in self.cursor.fetchall():
                parent_path = os.path.dirname(rel_path)
                item = QTreeWidgetItem()
                item.setText(0, name)
                if not is_dir:
                    item.setText(1, self.format_size(size))
                item.setText(2, datetime.fromisoformat(modified).strftime('%Y-%m-%d %H:%M:%S'))
                path_to_item[rel_path] = item
            
            # Second pass: set up parent-child relationships
            for rel_path, item in path_to_item.items():
                parent_path = os.path.dirname(rel_path)
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

    def calculate_md5(self, file_path):
        """Calculate MD5 hash of a file"""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    def save_catalog(self):
        """Save current folder structure to database"""
        root_path = QFileDialog.getExistingDirectory(self, "Select Folder to Catalog", os.path.expanduser("~"))
        if not root_path:
            return

        # Ask if user wants to calculate MD5 hashes
        calculate_md5 = QMessageBox.question(
            self, "MD5 Calculation",
            "Do you want to calculate MD5 hashes for files? (This will take longer but allows for more accurate comparison)",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        ) == QMessageBox.Yes

        # Use folder name as catalog name
        catalog_name = os.path.basename(root_path)

        try:
            # Insert catalog
            self.cursor.execute(
                'INSERT INTO catalogs (name, root_path) VALUES (?, ?)',
                (catalog_name, root_path)
            )
            catalog_id = self.cursor.lastrowid

            # Count total files for progress bar
            total_files = sum([len(files) for _, _, files in os.walk(root_path)])
            progress = QProgressDialog("Cataloging files...", "Cancel", 0, total_files, self)
            progress.setWindowModality(Qt.WindowModal)
            progress.setWindowTitle("Progress")
            files_processed = 0

            # Walk through directory and save structure
            for root, dirs, files in os.walk(root_path):
                # Save directories
                for dir_name in dirs:
                    full_path = os.path.join(root, dir_name)
                    rel_path = os.path.relpath(full_path, root_path)
                    self.cursor.execute(
                        'INSERT INTO files (catalog_id, path, name, is_directory, size, modified_at) VALUES (?, ?, ?, ?, ?, ?)',
                        (catalog_id, rel_path, dir_name, True, 0, datetime.fromtimestamp(os.path.getmtime(full_path)))
                    )

                # Save files
                for file_name in files:
                    if progress.wasCanceled():
                        self.conn.rollback()
                        return

                    full_path = os.path.join(root, file_name)
                    try:
                        rel_path = os.path.relpath(full_path, root_path)
                        size = os.path.getsize(full_path)
                        modified = datetime.fromtimestamp(os.path.getmtime(full_path))
                        
                        # Calculate MD5 if requested
                        md5_hash = self.calculate_md5(full_path) if calculate_md5 else None
                        
                        self.cursor.execute(
                            'INSERT INTO files (catalog_id, path, name, is_directory, size, modified_at, md5_hash) VALUES (?, ?, ?, ?, ?, ?, ?)',
                            (catalog_id, rel_path, file_name, False, size, modified, md5_hash)
                        )
                        
                        files_processed += 1
                        progress.setValue(files_processed)
                    except (OSError, FileNotFoundError):
                        continue

            self.conn.commit()
            self.update_catalog_list()
            self.statusBar.showMessage(f"Catalog '{catalog_name}' saved successfully")
            QMessageBox.information(self, "Success", f"Catalog '{catalog_name}' has been saved successfully!")

        except sqlite3.Error as e:
            QMessageBox.critical(self, "Error", f"Error saving catalog: {str(e)}")
            self.conn.rollback()

    def compare_selected_catalog(self):
        """Compare the currently selected catalog with a selected folder"""
        current_item = self.catalog_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Warning", "Please select a catalog to compare")
            return

        catalog_name = current_item.text().split(" (")[0]
        self.cursor.execute('SELECT id, root_path FROM catalogs WHERE name = ?', (catalog_name,))
        result = self.cursor.fetchone()
        if not result:
            return

        catalog_id, original_root_path = result

        # Ask user to select folder to compare with
        compare_path = QFileDialog.getExistingDirectory(
            self, 
            "Select Folder to Compare With", 
            os.path.expanduser("~"),
            QFileDialog.ShowDirsOnly
        )
        if not compare_path:
            return

        # Show comparison options dialog
        dialog = CompareOptionsDialog(self)
        if dialog.exec_() != QDialog.Accepted:
            return

        options = dialog.get_options()
        
        try:
            # Get all files from catalog
            self.cursor.execute('''
                SELECT path, name, size, md5_hash, modified_at, is_directory
                FROM files 
                WHERE catalog_id = ?
            ''', (catalog_id,))
            catalog_items = {}
            for row in self.cursor.fetchall():
                catalog_items[row[0]] = {
                    'name': row[1],
                    'size': row[2],
                    'md5_hash': row[3],
                    'modified': datetime.fromisoformat(row[4]),
                    'is_directory': row[5]
                }
            
            # Get all files from comparison folder
            compare_items = {}
            differences = set()  # Use set for faster lookups
            total_files = sum([len(files) for _, _, files in os.walk(compare_path)])
            progress = QProgressDialog("Comparing files...", "Cancel", 0, total_files, self)
            progress.setWindowModality(Qt.WindowModal)
            progress.setWindowTitle("Progress")
            files_processed = 0
            
            for root, dirs, files in os.walk(compare_path):
                # Process directories
                for dir_name in dirs:
                    full_path = os.path.join(root, dir_name)
                    rel_path = os.path.relpath(full_path, compare_path)
                    compare_items[rel_path] = {
                        'name': dir_name,
                        'size': 0,
                        'modified': datetime.fromtimestamp(os.path.getmtime(full_path)),
                        'is_directory': True
                    }
                    if rel_path not in catalog_items:
                        differences.add(rel_path)
                
                # Process files
                for file_name in files:
                    if progress.wasCanceled():
                        return
                        
                    full_path = os.path.join(root, file_name)
                    try:
                        rel_path = os.path.relpath(full_path, compare_path)
                        size = os.path.getsize(full_path)
                        modified = datetime.fromtimestamp(os.path.getmtime(full_path))
                        
                        compare_items[rel_path] = {
                            'name': file_name,
                            'size': size,
                            'modified': modified,
                            'is_directory': False
                        }
                        
                        if rel_path not in catalog_items:
                            differences.add(rel_path)
                        else:
                            catalog_item = catalog_items[rel_path]
                            if options['check_size'] and size != catalog_item['size']:
                                differences.add(rel_path)
                            if options['check_md5'] and catalog_item['md5_hash']:
                                current_md5 = self.calculate_md5(full_path)
                                if current_md5 != catalog_item['md5_hash']:
                                    differences.add(rel_path)
                        
                        files_processed += 1
                        progress.setValue(files_processed)
                    except (OSError, FileNotFoundError):
                        continue
            
            # Check for deleted files
            for rel_path in catalog_items:
                if rel_path not in compare_items:
                    differences.add(rel_path)
            
            # Show comparison results window
            if differences:
                results_window = ComparisonResultsWindow(catalog_name, compare_path, differences, self)
                results_window.add_items_to_trees(catalog_items, compare_items)
                results_window.show()
            else:
                QMessageBox.information(self, "Comparison Results", 
                    f"No differences found between catalog '{catalog_name}' and selected folder!")
                
        except sqlite3.Error as e:
            QMessageBox.critical(self, "Error", f"Error comparing catalog: {str(e)}")

    def closeEvent(self, event):
        """Clean up database connection when closing the application"""
        self.conn.close()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("Disk Catalog")
    app.setApplicationDisplayName("Disk Catalog")
    if sys.platform == 'darwin':  # macOS
        app.setStyle('Fusion')  # Use Fusion style on macOS
        # Set the application name for macOS menu bar
        app.setWindowIcon(QIcon())  # Clear any default icon
        app.setQuitOnLastWindowClosed(True)
        # Set the application name in the process name
        import ctypes
        libc = ctypes.CDLL('libc.dylib')
        libc.setprogname("Disk Catalog".encode('utf-8'))
    window = FolderCatalogApp()
    window.show()
    sys.exit(app.exec_())
