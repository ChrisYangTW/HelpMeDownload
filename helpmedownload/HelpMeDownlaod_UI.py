# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'HelpMeDownload_UI.ui'
##
## Created by: Qt User Interface Compiler version 6.6.1
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QAction, QBrush, QColor, QConicalGradient,
    QCursor, QFont, QFontDatabase, QGradient,
    QIcon, QImage, QKeySequence, QLinearGradient,
    QPainter, QPalette, QPixmap, QRadialGradient,
    QTransform)
from PySide6.QtWidgets import (QApplication, QGridLayout, QHBoxLayout, QLabel,
    QLineEdit, QMainWindow, QMenu, QMenuBar,
    QPushButton, QSizePolicy, QStatusBar, QTextBrowser,
    QVBoxLayout, QWidget)

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")
        MainWindow.resize(800, 600)
        self.actionShowHistory = QAction(MainWindow)
        self.actionShowHistory.setObjectName(u"actionShowHistory")
        self.actionShowFailUrl = QAction(MainWindow)
        self.actionShowFailUrl.setObjectName(u"actionShowFailUrl")
        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        self.verticalLayout = QVBoxLayout(self.centralwidget)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.horizontalLayout_1 = QHBoxLayout()
        self.horizontalLayout_1.setObjectName(u"horizontalLayout_1")
        self.folder_label = QLabel(self.centralwidget)
        self.folder_label.setObjectName(u"folder_label")
        self.folder_label.setAlignment(Qt.AlignCenter)

        self.horizontalLayout_1.addWidget(self.folder_label)

        self.folder_line_edit = QLineEdit(self.centralwidget)
        self.folder_line_edit.setObjectName(u"folder_line_edit")
        self.folder_line_edit.setEnabled(True)
        self.folder_line_edit.setReadOnly(True)

        self.horizontalLayout_1.addWidget(self.folder_line_edit)

        self.horizontalLayout_1.setStretch(0, 2)
        self.horizontalLayout_1.setStretch(1, 16)

        self.verticalLayout.addLayout(self.horizontalLayout_1)

        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.url_label = QLabel(self.centralwidget)
        self.url_label.setObjectName(u"url_label")
        self.url_label.setAlignment(Qt.AlignCenter)

        self.horizontalLayout_2.addWidget(self.url_label)

        self.batch_push_button = QPushButton(self.centralwidget)
        self.batch_push_button.setObjectName(u"batch_push_button")

        self.horizontalLayout_2.addWidget(self.batch_push_button)

        self.url_line_edit = QLineEdit(self.centralwidget)
        self.url_line_edit.setObjectName(u"url_line_edit")

        self.horizontalLayout_2.addWidget(self.url_line_edit)

        self.go_push_button = QPushButton(self.centralwidget)
        self.go_push_button.setObjectName(u"go_push_button")

        self.horizontalLayout_2.addWidget(self.go_push_button)

        self.horizontalLayout_2.setStretch(0, 2)
        self.horizontalLayout_2.setStretch(1, 2)
        self.horizontalLayout_2.setStretch(2, 12)
        self.horizontalLayout_2.setStretch(3, 2)

        self.verticalLayout.addLayout(self.horizontalLayout_2)

        self.operation_text_browser = QTextBrowser(self.centralwidget)
        self.operation_text_browser.setObjectName(u"operation_text_browser")

        self.verticalLayout.addWidget(self.operation_text_browser)

        self.gridLayout_for_checkbox = QGridLayout()
        self.gridLayout_for_checkbox.setObjectName(u"gridLayout_for_checkbox")

        self.verticalLayout.addLayout(self.gridLayout_for_checkbox)

        self.label = QLabel(self.centralwidget)
        self.label.setObjectName(u"label")
        self.label.setAlignment(Qt.AlignCenter)

        self.verticalLayout.addWidget(self.label)

        self.result_text_browser = QTextBrowser(self.centralwidget)
        self.result_text_browser.setObjectName(u"result_text_browser")

        self.verticalLayout.addWidget(self.result_text_browser)

        self.verticalLayout.setStretch(0, 1)
        self.verticalLayout.setStretch(1, 1)
        self.verticalLayout.setStretch(2, 2)
        self.verticalLayout.setStretch(5, 2)
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QMenuBar(MainWindow)
        self.menubar.setObjectName(u"menubar")
        self.menubar.setGeometry(QRect(0, 0, 800, 37))
        self.menuhelp = QMenu(self.menubar)
        self.menuhelp.setObjectName(u"menuhelp")
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QStatusBar(MainWindow)
        self.statusbar.setObjectName(u"statusbar")
        MainWindow.setStatusBar(self.statusbar)

        self.menubar.addAction(self.menuhelp.menuAction())
        self.menuhelp.addAction(self.actionShowHistory)
        self.menuhelp.addAction(self.actionShowFailUrl)

        self.retranslateUi(MainWindow)

        QMetaObject.connectSlotsByName(MainWindow)
    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"Help Me Download (just for Civit)", None))
        self.actionShowHistory.setText(QCoreApplication.translate("MainWindow", u"Show History", None))
        self.actionShowFailUrl.setText(QCoreApplication.translate("MainWindow", u"Show Failed URLs", None))
        self.folder_label.setText(QCoreApplication.translate("MainWindow", u"Folder", None))
        self.url_label.setText(QCoreApplication.translate("MainWindow", u"URL", None))
        self.batch_push_button.setText(QCoreApplication.translate("MainWindow", u"Batch", None))
        self.go_push_button.setText(QCoreApplication.translate("MainWindow", u"Go", None))
        self.label.setText(QCoreApplication.translate("MainWindow", u"Download task message", None))
        self.menuhelp.setTitle(QCoreApplication.translate("MainWindow", u"Show", None))
    # retranslateUi

