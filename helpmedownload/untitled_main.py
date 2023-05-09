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
        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.label = QLabel(self.centralwidget)
        self.label.setObjectName(u"label")

        self.horizontalLayout.addWidget(self.label)

        self.lineEdit = QLineEdit(self.centralwidget)
        self.lineEdit.setObjectName(u"lineEdit")

        self.horizontalLayout.addWidget(self.lineEdit)

        self.parser_push_button = QPushButton(self.centralwidget)
        self.parser_push_button.setObjectName(u"parser_push_button")

        self.horizontalLayout.addWidget(self.parser_push_button)


        self.verticalLayout.addLayout(self.horizontalLayout)

        self.ready_to_go_push_button = QPushButton(self.centralwidget)
        self.ready_to_go_push_button.setObjectName(u"ready_to_go_push_button")

        self.verticalLayout.addWidget(self.ready_to_go_push_button)

        self.text_browser = QTextBrowser(self.centralwidget)
        self.text_browser.setObjectName(u"text_browser")

        self.verticalLayout.addWidget(self.text_browser)

        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QMenuBar(MainWindow)
        self.menubar.setObjectName(u"menubar")
        self.menubar.setGeometry(QRect(0, 0, 800, 37))
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QStatusBar(MainWindow)
        self.statusbar.setObjectName(u"statusbar")
        MainWindow.setStatusBar(self.statusbar)

        self.retranslateUi(MainWindow)

        QMetaObject.connectSlotsByName(MainWindow)
    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"Help Me Download (just for Civit)", None))
        self.label.setText(QCoreApplication.translate("MainWindow", u"Url", None))
        self.parser_push_button.setText(QCoreApplication.translate("MainWindow", u"Parser", None))
        self.ready_to_go_push_button.setText(QCoreApplication.translate("MainWindow", u"Ready To Go", None))
    # retranslateUi

