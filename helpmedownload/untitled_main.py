# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'untitled_main.ui'
##
## Created by: Qt User Interface Compiler version 6.5.0
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QApplication, QHBoxLayout, QLabel, QLineEdit,
    QMainWindow, QMenuBar, QPushButton, QSizePolicy,
    QStatusBar, QTextBrowser, QVBoxLayout, QWidget)

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")
        MainWindow.resize(800, 600)
        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        self.verticalLayout = QVBoxLayout(self.centralwidget)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.horizontalLayout_1 = QHBoxLayout()
        self.horizontalLayout_1.setObjectName(u"horizontalLayout_1")
        self.url_label = QLabel(self.centralwidget)
        self.url_label.setObjectName(u"url_label")

        self.horizontalLayout_1.addWidget(self.url_label)

        self.url_line_edit = QLineEdit(self.centralwidget)
        self.url_line_edit.setObjectName(u"url_line_edit")

        self.horizontalLayout_1.addWidget(self.url_line_edit)

        self.parser_push_button = QPushButton(self.centralwidget)
        self.parser_push_button.setObjectName(u"parser_push_button")

        self.horizontalLayout_1.addWidget(self.parser_push_button)


        self.verticalLayout.addLayout(self.horizontalLayout_1)

        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.folder_label = QLabel(self.centralwidget)
        self.folder_label.setObjectName(u"folder_label")

        self.horizontalLayout_2.addWidget(self.folder_label)

        self.folder_line_edit = QLineEdit(self.centralwidget)
        self.folder_line_edit.setObjectName(u"folder_line_edit")
        self.folder_line_edit.setEnabled(False)

        self.horizontalLayout_2.addWidget(self.folder_line_edit)

        self.choose_folder_button = QPushButton(self.centralwidget)
        self.choose_folder_button.setObjectName(u"choose_folder_button")

        self.horizontalLayout_2.addWidget(self.choose_folder_button)


        self.verticalLayout.addLayout(self.horizontalLayout_2)

        self.parser_text_browser = QTextBrowser(self.centralwidget)
        self.parser_text_browser.setObjectName(u"parser_text_browser")

        self.verticalLayout.addWidget(self.parser_text_browser)

        self.ready_to_go_push_button = QPushButton(self.centralwidget)
        self.ready_to_go_push_button.setObjectName(u"ready_to_go_push_button")

        self.verticalLayout.addWidget(self.ready_to_go_push_button)

        self.result_text_browser = QTextBrowser(self.centralwidget)
        self.result_text_browser.setObjectName(u"result_text_browser")

        self.verticalLayout.addWidget(self.result_text_browser)

        self.verticalLayout.setStretch(0, 1)
        self.verticalLayout.setStretch(1, 1)
        self.verticalLayout.setStretch(2, 3)
        self.verticalLayout.setStretch(3, 1)
        self.verticalLayout.setStretch(4, 3)
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QMenuBar(MainWindow)
        self.menubar.setObjectName(u"menubar")
        self.menubar.setGeometry(QRect(0, 0, 800, 24))
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QStatusBar(MainWindow)
        self.statusbar.setObjectName(u"statusbar")
        MainWindow.setStatusBar(self.statusbar)

        self.retranslateUi(MainWindow)

        QMetaObject.connectSlotsByName(MainWindow)
    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"Help Me Download (just for Civit)", None))
        self.url_label.setText(QCoreApplication.translate("MainWindow", u"Url", None))
        self.parser_push_button.setText(QCoreApplication.translate("MainWindow", u"Parser", None))
        self.folder_label.setText(QCoreApplication.translate("MainWindow", u"Fodler", None))
        self.choose_folder_button.setText(QCoreApplication.translate("MainWindow", u"Folder", None))
        self.ready_to_go_push_button.setText(QCoreApplication.translate("MainWindow", u"Ready To Go", None))
    # retranslateUi

