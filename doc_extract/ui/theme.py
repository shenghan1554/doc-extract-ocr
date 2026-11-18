# -*- coding: utf-8 -*-
"""Application style sheet and fonts."""
from __future__ import annotations

APP_QSS = r"""
* {
    font-family: "Microsoft YaHei UI", "Microsoft YaHei", "Segoe UI", sans-serif;
    outline: none;
}
QMainWindow, QWidget#Root {
    background: #F3F6FA;
    color: #0F172A;
}
QWidget {
    color: #0F172A;
    font-size: 13px;
}
QFrame#Header {
    background: #FFFFFF;
    border-bottom: 1px solid #E2E8F0;
}
QLabel#AppTitle {
    font-size: 20px;
    font-weight: 700;
    color: #0F172A;
}
QLabel#AppSubtitle {
    font-size: 11px;
    color: #64748B;
}
QLabel#SectionTitle {
    font-size: 14px;
    font-weight: 700;
    color: #0F172A;
}
QLabel#Muted {
    color: #64748B;
    font-size: 11px;
}
QLabel#Tiny {
    color: #94A3B8;
    font-size: 10px;
}
QLabel#ResultTitle {
    font-size: 19px;
    font-weight: 700;
    color: #0F172A;
}
QLabel#Stat {
    color: #64748B;
    font-size: 11px;
    background: #F1F5F9;
    border-radius: 9px;
    padding: 3px 9px;
}
QLabel#BadgeReady {
    color: #047857;
    background: #ECFDF5;
    border: 1px solid #A7F3D0;
    border-radius: 10px;
    padding: 4px 10px;
    font-size: 11px;
    font-weight: 600;
}
QLabel#BadgeWarn {
    color: #B45309;
    background: #FFFBEB;
    border: 1px solid #FDE68A;
    border-radius: 10px;
    padding: 4px 10px;
    font-size: 11px;
    font-weight: 600;
}
QFrame#Card {
    background: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 14px;
}
QFrame#ExportBar {
    background: #F8FAFC;
    border-top: 1px solid #E2E8F0;
    border-bottom-left-radius: 14px;
    border-bottom-right-radius: 14px;
}
QPushButton {
    border: none;
    border-radius: 8px;
    padding: 8px 14px;
    font-size: 13px;
    color: #334155;
    background: transparent;
}
QPushButton:hover {
    background: #F1F5F9;
}
QPushButton:pressed {
    background: #E2E8F0;
}
QPushButton:disabled {
    color: #94A3B8;
    background: #F1F5F9;
}
QPushButton[class="primary"] {
    background: #0F766E;
    color: #FFFFFF;
    font-weight: 600;
    padding: 9px 18px;
}
QPushButton[class="primary"]:hover {
    background: #115E59;
}
QPushButton[class="primary"]:pressed {
    background: #134E4A;
}
QPushButton[class="secondary"] {
    background: #FFFFFF;
    color: #0F172A;
    border: 1px solid #CBD5E1;
    font-weight: 600;
    padding: 8px 16px;
}
QPushButton[class="secondary"]:hover {
    background: #F8FAFC;
    border-color: #94A3B8;
}
QPushButton[class="ghost"] {
    color: #475569;
    background: transparent;
    padding: 7px 10px;
}
QPushButton[class="ghost"]:hover {
    background: #F1F5F9;
    color: #0F172A;
}
QPushButton[class="danger"] {
    color: #B91C1C;
    background: #FEF2F2;
    border: 1px solid #FECACA;
    padding: 7px 12px;
}
QPushButton[class="danger"]:hover {
    background: #FEE2E2;
}
QPushButton[class="export"] {
    background: #FFFFFF;
    border: 1px solid #E2E8F0;
    padding: 8px 14px;
    font-weight: 600;
    color: #1E293B;
}
QPushButton[class="export"]:hover {
    border-color: #5EEAD4;
    background: #F0FDFA;
}
QComboBox {
    border: 1px solid #CBD5E1;
    border-radius: 8px;
    padding: 5px 9px;
    background: #FFFFFF;
    min-height: 20px;
    color: #1E293B;
}
QComboBox:hover {
    border-color: #94A3B8;
}
QComboBox::drop-down {
    border: none;
    width: 20px;
}
QComboBox QAbstractItemView {
    border: 1px solid #CBD5E1;
    background: #FFFFFF;
    selection-background-color: #CCFBF1;
    selection-color: #0F172A;
    padding: 3px;
}
QCheckBox {
    spacing: 7px;
    color: #475569;
    font-size: 12px;
}
QCheckBox::indicator {
    width: 15px;
    height: 15px;
}
QTabWidget::pane {
    border: none;
    background: #FFFFFF;
}
QTabBar::tab {
    background: transparent;
    color: #64748B;
    padding: 9px 2px;
    margin-right: 22px;
    border: none;
    font-size: 13px;
    font-weight: 600;
}
QTabBar::tab:selected {
    color: #0F766E;
    border-bottom: 2px solid #0F766E;
}
QTabBar::tab:hover {
    color: #0F172A;
}
QTextBrowser {
    border: none;
    background: #FFFFFF;
    selection-background-color: #99F6E4;
    selection-color: #0F172A;
}
QPlainTextEdit {
    border: none;
    background: #FFFFFF;
    selection-background-color: #99F6E4;
    selection-color: #0F172A;
}
QListWidget#Pages {
    border: none;
    background: transparent;
}
QListWidget#Pages::item {
    border: 2px solid transparent;
    border-radius: 7px;
    margin: 2px;
}
QListWidget#Pages::item:selected {
    border: 2px solid #0F766E;
    background: #F0FDFA;
}
QGraphicsView#Preview {
    border: none;
    background: #EEF2F7;
    border-radius: 9px;
}
QTabWidget#Tables {
    background: #FFFFFF;
}
QTableWidget {
    border: 1px solid #E2E8F0;
    border-radius: 8px;
    background: #FFFFFF;
    gridline-color: #E2E8F0;
    selection-background-color: #CCFBF1;
    selection-color: #0F172A;
    alternate-background-color: #F8FAFC;
}
QHeaderView::section {
    background: #F1F5F9;
    color: #334155;
    padding: 7px 8px;
    border: none;
    border-right: 1px solid #E2E8F0;
    border-bottom: 1px solid #E2E8F0;
    font-weight: 600;
}
QProgressBar {
    border: none;
    background: #E2E8F0;
    border-radius: 4px;
    height: 7px;
    text-align: center;
    color: transparent;
}
QProgressBar::chunk {
    background: #0F766E;
    border-radius: 4px;
}
QScrollBar:vertical {
    background: transparent;
    width: 9px;
    margin: 2px;
}
QScrollBar::handle:vertical {
    background: #CBD5E1;
    border-radius: 4px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover {
    background: #94A3B8;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
QScrollBar:horizontal {
    background: transparent;
    height: 9px;
    margin: 2px;
}
QScrollBar::handle:horizontal {
    background: #CBD5E1;
    border-radius: 4px;
    min-width: 30px;
}
QToolTip {
    background: #0F172A;
    color: #FFFFFF;
    border: none;
    padding: 5px 8px;
    border-radius: 5px;
}
QFrame#DropZone {
    background: #F8FAFC;
    border: 1.5px dashed #CBD5E1;
    border-radius: 10px;
}
QFrame#DropZone[drag="true"] {
    background: #F0FDFA;
    border-color: #0F766E;
}
QDialog {
    background: #F8FAFC;
}
QLineEdit, QSpinBox {
    border: 1px solid #CBD5E1;
    border-radius: 7px;
    padding: 6px 9px;
    background: #FFFFFF;
    color: #1E293B;
}
QLineEdit:focus, QSpinBox:focus {
    border-color: #0F766E;
}
QMenu {
    background: #FFFFFF;
    border: 1px solid #E2E8F0;
    padding: 5px;
}
QMenu::item {
    padding: 6px 26px 6px 12px;
    border-radius: 5px;
}
QMenu::item:selected {
    background: #F0FDFA;
    color: #0F766E;
}
"""
