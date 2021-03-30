from PyQt5.QtCore import * 
from PyQt5.QtGui import *
import pysftp
import sys 
import traceback
import os 
import pathlib 
import re 
from pysftp import paramiko
from PyQt5.QtWidgets import (QApplication, QCheckBox, QComboBox, QDateTimeEdit, 
    QDial, QDialog, QGridLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit, 
    QProgressBar, QPushButton, QRadioButton, QScrollBar, QSizePolicy,
    QSlider, QSpinBox, QStyleFactory, QTableWidget, QTabWidget, QTextEdit, 
    QVBoxLayout, QWidget, QListWidget, QListWidgetItem, QToolButton, QMessageBox, QFrame, QFileDialog, QMainWindow, QGraphicsColorizeEffect, QMessageBox)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon, QBrush
from PyQt5 import QtCore 
import os 


class Program(QMainWindow):
    def __init__(self, parent=None):
        super(Program, self).__init__(parent)

        self.originalPalette = QApplication.palette()
        self.setWindowTitle("FTP Program")
        self.setFixedWidth(1500)
        self.setFixedHeight(750)
        styleComboBox = QComboBox()
        styleComboBox.addItems(QStyleFactory.keys())

        styleLabel = QLabel("&Style:")
        styleLabel.setBuddy(styleComboBox)

        self.useStylePaletteCheckBox = QCheckBox("&Use style's standard palette")
        self.useStylePaletteCheckBox.setChecked(True)

        disableWidgetsCheckBox = QCheckBox("&Disable widgets")
        self.currentDir = os.path.dirname(os.path.realpath(__file__))
        self.createNotificationBox()
        self.createBottomLeftBox()
        self.createBottomRightBox()
        self.createBottonCenterBox()
        self.createTopTextBoxes()
        self.createDeleteButton()
        

        self.currentRemotePath = "/"   
        self.currentLocalPath = "\\"  
        self.currentFile = "/"  
        self.currentFileList = ""
        mainLayout = QGridLayout()
        self.setLayout(mainLayout)

        self.directoryIcon = QIcon(self.currentDir + "/icons/directory.png")
        self.fileIcon = QIcon(self.currentDir + "/icons/file.png")
    
        self.changeStyle("Windows")

    def clearAllData(self):
        self.LocalFilesList.clear()
        self.RemoteFilesList.clear()
        self.currentLocalPath = "\\"
        self.currentRemotePath = "/"
        self.currentFile = ""
        self.currentFileList = ""

    def startFTP(self, hostname, username, password):
        self.clearAllData()
        cnopts = pysftp.CnOpts()
        cnopts.hostkeys = None
        try: 
            self.connection = pysftp.Connection(host=hostname, username=username, password=password, cnopts=cnopts)
            self.getLocalFileList()
            self.getRemoteFileList()
            self.notificationLabel.setText("Double-click on a file and click the arrow buttons to file transfer")
            self.rightArrowButton.setEnabled(True)
            self.leftArrowButton.setEnabled(True)
        except paramiko.ssh_exception.SSHException:
            if hostname == "":                    
                errorMessage = QMessageBox(QMessageBox.Critical, "Error", "SSH Failed! Hostname field cannot be empty!")
                errorMessage.exec_()
            else:
                errorMessage = QMessageBox(QMessageBox.Critical, "Error", "SSH Failed! Connection attempt to host: " + hostname +  " failed!")
                errorMessage.exec_()
        except paramiko.ssh_exception.AuthenticationException:
            errorMessage = QMessageBox(QMessageBox.Critical, "Error", "Authentication Failed! Please make sure to enter a valid hostname, username and password")
            errorMessage.exec_()
        except paramiko.sftp.SFTPError:
            errorMessage = QMessageBox(QMessageBox.Critical, "Error", "SFTP Error: Garbage package received")
            errorMessage.exec_()
        except pysftp.exceptions.ConnectionException:
            errorMessage = QMessageBox(QMessageBox.Critical, "Error", "Connection Exception: Remote server connection failed! Make sure all fields contain valid information with no additional spaces")
            errorMessage.exec_()

    def updateRemoteFiles(self):
        self.RemoteFilesList.clear()
        remoteFiles = self.connection.listdir_attr("./")
        self.createRemoteFilesList(remoteFiles)

    def updateLocalFiles(self):
        self.LocalFilesList.clear()
        localFiles = os.scandir(self.currentLocalPath)
        self.createLocalFilesList(localFiles)

    def changeStyle(self, styleName):
        QApplication.setStyle(QStyleFactory.create(styleName))
        self.changePalette()
    
    def changePalette(self):
        if(self.useStylePaletteCheckBox.isChecked()):
            QApplication.setPalette(QApplication.style().standardPalette())
        else:
            QApplication.setPalette(self.originalPalette)

    def advanceProgressBar(self):
        currVal = self.progressBar.value()
        maxVal = self.progressBar.maximum()
        self.progressBar.setValue(currVal + (maxVal - currVal) / 100)

    def createNotificationBox(self):
        self.notificationLabel = QLabel(self)
        self.notificationLabel.setText("Please enter remote credentials to continue...")
        self.notificationLabel.setAlignment(Qt.AlignTop)
        self.notificationLabel.resize(400, 20)
        self.notificationLabel.setGeometry(500, 25, 600, 100)
        self.notificationLabel.setFont(QFont('Times', 12))
        red_font = QGraphicsColorizeEffect()
        red_font.setColor(QColor(255, 15, 15))
        self.notificationLabel.setGraphicsEffect(red_font)


    def createBottomLeftBox(self):
        self.RemoteFilesList = QListWidget(self)
        self.RemoteFilesList.move(20, 160)
        self.RemoteFilesList.resize(650, 570)
        self.remoteSelectedFile = [] 

        self.RemoteFilesLabel = QLabel(self)
        self.RemoteFilesLabel.setText("Remote Files Section:\n{file} - {size}")
        self.RemoteFilesLabel.move(20, 120)
        self.RemoteFilesLabel.adjustSize()
        self.RemoteFilesList.itemDoubleClicked.connect(self.remoteFileSelectionChanged)
        self.RemoteFilesList.itemClicked.connect(self.remoteFileSelectionChangedSingleClick)

    def createBottomRightBox(self):        
        self.LocalFilesList = QListWidget(self)
        self.LocalFilesList.move(800, 160)
        self.LocalFilesList.resize(650, 570)
        self.localSelectedFile = []

        self.LocalFilesLabel = QLabel(self)
        self.LocalFilesLabel.setText("Local Files Section:\n{file} - {size}") 
        self.LocalFilesLabel.move(800, 120)
        self.LocalFilesLabel.adjustSize()
        self.LocalFilesList.itemDoubleClicked.connect(self.localFileSelectionChanged)
        self.LocalFilesList.itemClicked.connect(self.localFileSelectionChangedSingleClick)

    def getLocalFileList(self, localPath=None, afterDelete=False):
        previous_dir = False 
        base_dir = False 
        delete_dir = False 
        if localPath == "..":
            if self.currentLocalPath.endswith("\\") and self.currentLocalPath != "C:\\":
                # removing the 'def\\' in path: '\\abc\def\\' 
                self.currentLocalPath = self.currentLocalPath[:-1] 
            newLocalArr = list(os.path.split(self.currentLocalPath))
            arrLength = len(newLocalArr)
            i = 0
            while i < arrLength:
                if newLocalArr[i] == "":
                    del(newLocalArr[i])
                    arrLength -= 1
                    continue
                i += 1 
            if len(newLocalArr) == 0:
                # self.currentLocalPath is "\"
                return False 
            self.LocalFilesList.clear()
            newLocalPath = newLocalArr[0]
            self.currentLocalPath = str(newLocalPath)
            localFiles = os.scandir(newLocalPath)
            previous_dir = True
            if self.currentLocalPath == "C:\\":
                base_dir = True  
        elif afterDelete:
            currentLocalPathLen = len(self.currentLocalPath)
            localFiles = os.scandir(self.currentLocalPath)
            delete_dir = True 
        else:  
            localFiles = os.scandir("./")
            self.currentLocalPath = os.getcwd() + self.currentLocalPath
        # create back button 
        QListWidgetItem("..", self.LocalFilesList).setIcon(self.directoryIcon)
        for file in localFiles:
            fileType = list(file.stat())[0] // 10000
            if previous_dir and base_dir == False and delete_dir == False:
                if fileType == 1: # for folders
                    QListWidgetItem(self.currentLocalPath + "\\" + file.name + " - " + str(list(file.stat())[6]) , self.LocalFilesList).setIcon(self.directoryIcon)
                    self.LocalFilesList.findItems(self.currentLocalPath + "\\" + file.name + " - " + str(list(file.stat())[6]), Qt.MatchContains)[0].setBackground(QColor(100,100,150))
                elif fileType == 3: # for files
                    QListWidgetItem(self.currentLocalPath + "\\" + file.name + " - " + str(list(file.stat())[6]) , self.LocalFilesList).setIcon(self.fileIcon)
            else: 
                if fileType == 1: # for folders
                    QListWidgetItem(self.currentLocalPath + file.name + " - " + str(list(file.stat())[6]) , self.LocalFilesList).setIcon(self.directoryIcon)
                    self.LocalFilesList.findItems(self.currentLocalPath + file.name + " - " + str(list(file.stat())[6]), Qt.MatchContains)[0].setBackground(QColor(100,100,150))
                elif fileType == 3: # for files
                    QListWidgetItem(self.currentLocalPath + file.name + " - " + str(list(file.stat())[6]) , self.LocalFilesList).setIcon(self.fileIcon)   
        return True 
  
    def getRemoteFileList(self, *args):
        if args:
            newRemoteArr = self.currentRemotePath.split("/")
            arrLength = len(newRemoteArr)
            i = 0
            while i < arrLength:
                if newRemoteArr[i] == "":
                    del(newRemoteArr[i])
                    arrLength -= 1
                    continue
                i += 1 
            if len(newRemoteArr) == 0:
                # self.currentRemotePath is "/"
                return False 
            self.RemoteFilesList.clear() # clear current list since back navigation is valid
            newRemoteArr.pop()
            newRemotePath = ""
            if len(newRemoteArr) != 0:
                for i in newRemoteArr:
                    newRemotePath = newRemotePath + '/'
                    newRemotePath = newRemotePath + i 
            remotePath = newRemotePath[:-1]
            self.currentRemotePath = "/"
            self.currentRemotePath = newRemotePath + self.currentRemotePath
            remoteFiles = self.connection.listdir_attr(self.currentRemotePath)
            
        else:  
            remoteFiles = self.connection.listdir_attr("./")
            remoteDir = self.connection.normalize(".")
            self.currentRemotePath = self.connection.pwd + self.currentRemotePath
        self.createRemoteFilesList(remoteFiles)
        return True 

    def createRemoteFilesList(self, remoteFiles):
        QListWidgetItem("..", self.RemoteFilesList).setIcon(self.directoryIcon)
        for file in remoteFiles:
            fileType = file.st_mode // 10000
            if fileType == 1:
                QListWidgetItem(self.currentRemotePath + file.filename + " - " + str(file.st_size) , self.RemoteFilesList).setIcon(self.directoryIcon)
                self.RemoteFilesList.findItems(self.currentRemotePath + file.filename + " - " + str(file.st_size), Qt.MatchContains)[0].setBackground(QColor(100,100,150))
            elif fileType == 3:
                QListWidgetItem(self.currentRemotePath + file.filename + " - " + str(file.st_size) , self.RemoteFilesList).setIcon(self.fileIcon)

    def createLocalFilesList(self, localFiles):
        QListWidgetItem("..", self.LocalFilesList).setIcon(self.directoryIcon)
        for file in localFiles:
            fileType = list(file.stat())[0] // 10000
            if fileType == 1:
                QListWidgetItem(self.currentLocalPath + file.name + " - " + str(list(file.stat())[6]) , self.LocalFilesList).setIcon(self.directoryIcon)
                self.LocalFilesList.findItems(self.currentLocalPath + file.name + " - " + str(list(file.stat())[6]), Qt.MatchContains)[0].setBackground(QColor(100,100,150))
            if fileType == 3:
                QListWidgetItem(self.currentLocalPath + file.name + " - " + str(list(file.stat())[6]) , self.LocalFilesList).setIcon(self.fileIcon)

    def localFileSelectionChangedSingleClick(self):
        self.currentFile = self.LocalFilesList.selectedItems()[0]
        self.currentFileList = "Local"

    def localFileSelectionChanged(self):
        self.localSelectedFile = self.LocalFilesList.selectedItems()[0]
        item = self.localSelectedFile
        if item.text() == "..":
            self.getLocalFileList("..")
            self.localSelectedFile = ""
        else:
            if item.background().color().getRgb() == (100, 100, 150, 255):
                # selection is dir, switch dirs 
                if self.currentLocalPath == "/":
                    self.currentLocalPath = item.text().split(" -")[0] + self.currentLocalPath
                else:
                    self.currentLocalPath = item.text().split(" -")[0] + "\\"
                self.LocalFilesList.clear()
                localFiles = os.scandir(self.currentLocalPath)
                self.createLocalFilesList(localFiles)
                self.localSelectedFile = ""   
         
    def remoteFileSelectionChangedSingleClick(self):
        self.currentFile = self.RemoteFilesList.selectedItems()[0]
        self.currentFileList = "Remote"

    def remoteFileSelectionChanged(self):
        self.remoteSelectedFile = self.RemoteFilesList.selectedItems()[0]
        item = self.remoteSelectedFile
        if item.text() == "..":
            self.getRemoteFileList("..")
            self.remoteSelectedFile = ""
        else:
            if item.background().color().getRgb() == (100, 100, 150, 255):
                if self.currentRemotePath == "/":
                    self.currentRemotePath = item.text().split(" -")[0] + self.currentRemotePath
                else:
                    self.currentRemotePath = item.text().split(" -")[0] + "/"
                with self.connection.cd(self.currentRemotePath):
                    self.RemoteFilesList.clear()
                    QListWidgetItem("..", self.RemoteFilesList).setIcon(self.directoryIcon)
                    for file in self.connection.listdir_attr():
                        fileType = file.st_mode // 10000
                        if fileType == 1:
                            QListWidgetItem(self.currentRemotePath + file.filename + " - " + str(file.st_size) , self.RemoteFilesList).setIcon(self.directoryIcon)
                            self.RemoteFilesList.findItems(self.currentRemotePath + file.filename + " - " + str(file.st_size), Qt.MatchContains)[0].setBackground(QColor(100,100,150))
                        if fileType == 3:
                            QListWidgetItem(self.currentRemotePath + file.filename + " - " + str(file.st_size) , self.RemoteFilesList).setIcon(self.fileIcon)
                self.remoteSelectedFile = ""

    def localToRemoteTransfer(self, localFile):
        if localFile == []:
            errorMessage = QMessageBox(QMessageBox.Critical, "Error", "No file selected to file transfer. Make sure you double-click the file to transfer!")
            errorMessage.exec_()
            return 
        with self.connection.cd(self.currentRemotePath):
            try:
                localFileName = localFile.text().split(" -")[0]
                self.connection.put(localFileName) 
                self.updateRemoteFiles()
                self.showFileTransferSuccessMsg()
            except IsADirectoryError:
                errorMessage = QMessageBox(QMessageBox.Critical, "Error", "The selected file is a directory, please select a file instead.")
                errorMessage.exec_()
            except PermissionError: 
                errorMessage = QMessageBox(QMessageBox.Critical, "Error", "Permission denied for file transfer")
                errorMessage.exec_()
            except Exception:
                errorMessage = QMessageBox(QMessageBox.Critical, "Error", "Ran into an error while file transfering")
        
    def checkForForwardSlash(self):
        if self.currentLocalPath[-1] == "/":
            size = len(self.currentLocalPath)
            self.currentLocalPath = self.currentLocalPath[:size - 1]

    def remoteToLocalTransfer(self, remoteFile):
        if remoteFile == []:
            errorMessage = QMessageBox(QMessageBox.Critical, "Error", "No file selected to file transfer. Make sure you double-click the file to transfer!")
            errorMessage.exec_()
            return 
        try: 
            self.checkForForwardSlash()
            remoteFileName = remoteFile.text().split(" -")[0]
            newLocalArr = remoteFileName.split("/")
            arrLength = len(newLocalArr)
            i = 0
            while i < arrLength:
                if newLocalArr[i] == "":
                    del(newLocalArr[i])
                    arrLength -= 1
                    continue 
                i += 1
            if self.currentLocalPath[-1] != "\\":
                self.currentLocalPath += "\\"
            newLocalFileName = newLocalArr[-1]
            with self.connection.cd(self.currentRemotePath):
                self.connection.get(remoteFileName, self.currentLocalPath + newLocalFileName)
                self.updateLocalFiles()
                self.showFileTransferSuccessMsg()
        except IsADirectoryError:
            errorMessage = QMessageBox(QMessageBox.Critical, "Error", "The selected file is a directory, please select a file instead.")
            errorMessage.exec_()
        except PermissionError:
            errorMessage = QMessageBox(QMessageBox.Critical, "Error", "Permission Denied for file transfer")
            errorMessage.exec_()
        except FileNotFoundError:
            errorMessage = QMessageBox(QMessageBox.Critical, "Error", "No such file")
            errorMessage.exec_()
        except OSError:
            tracebackString = traceback.print_exc()
            errorMessage = QMessageBox(QMessageBox.Critical, "Error", "The selected file is a directory, please select a file instead.")
            errorMessage.exec_()
        except Exception:
            errorMessage = QMessageBox(QMessageBox.Critical, "Error", "Ran into error while file transfering")     
            errorMessage.exec_() 

    def showFileTransferSuccessMsg(self):
        transfer_success_msg = QMessageBox()
        transfer_success_msg.setWindowTitle("File Transferred")
        transfer_success_msg.setText("File transferred successfully!")
        transfer_success_msg.setIcon(QMessageBox.Information)
        transfer_success_msg.exec_()

    def showDeleteFileSuccessMsg(self):
        deleteFile_success_msg = QMessageBox()
        deleteFile_success_msg.setWindowTitle("File deleted")
        deleteFile_success_msg.setText("File deleted successfully!")
        deleteFile_success_msg.setIcon(QMessageBox.Information)
        deleteFile_success_msg.exec_()

    def deleteFile(self, deleteFile):
        if self.currentFile != "/":
            deleteFile = self.currentFile
            if self.currentFileList == "Remote":
                errorMessage = QMessageBox(QMessageBox.Critical, "Error", "Cannot delete files and folder in remote server!")
                errorMessage.exec_()
                return 
            if deleteFile.background().color().getRgb() == (100, 100, 150, 255):
                errorMessage = QMessageBox(QMessageBox.Critical, "Error", "Cannot delete folders! Only files can be deleted...")
                errorMessage.exec_()
                return 
            deleteFileName = str(self.currentFile.text())
            deleteFilePath = deleteFileName.split(" -")[0]
          
            confirmDelete = QMessageBox.question(self, "Confirm Action", "Are you sure you want to delete this file: " + deleteFilePath, QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel, QMessageBox.Cancel)

            if confirmDelete == QMessageBox.Yes:
                os.remove(deleteFilePath)
                self.showDeleteFileSuccessMsg()
                self.LocalFilesList.clear()
                self.getLocalFileList(None, True)
            if confirmDelete == QMessageBox.No:
                print("No clicked")
            if confirmDelete == QMessageBox.Cancel:
                print("Cancel")

    def createDeleteButton(self):
        self.deleteButton = QPushButton(self)
        self.deleteButton.setIcon(QIcon(os.getcwd() + "/icons/delete.png"))
        self.deleteButton.setCursor(Qt.ArrowCursor)
        self.deleteButton.resize(35, 35)
        self.deleteButton.move(20, 70)
        self.deleteButton.clicked.connect(lambda:self.deleteFile("abc.txt"))
        self.deleteButton.setEnabled(True)
        self.deleteButton.show()


    def createBottonCenterBox(self):
        self.rightArrowButton = QToolButton(self)
        self.rightArrowButton.setIcon(QIcon(os.getcwd() + "/icons/right.png" ))
        self.rightArrowButton.setStyleSheet("border: 1px solid black; padding: 1px; background-color: #6BA4FC")
        self.rightArrowButton.setCursor(Qt.ArrowCursor)
        self.rightArrowButton.resize(45, 45)
        self.rightArrowButton.move(710, 250)
        self.rightArrowButton.clicked.connect(lambda:self.remoteToLocalTransfer(self.remoteSelectedFile))
        self.rightArrowButton.setEnabled(False)

        self.leftArrowButton = QToolButton(self)
        self.leftArrowButton.setIcon(QIcon(os.getcwd() + "/icons/left.png"))
        self.leftArrowButton.setStyleSheet("border: 1px solid black; padding: 1px; background-color: #6BA4FC")
        self.leftArrowButton.setCursor(Qt.ArrowCursor)
        self.leftArrowButton.resize(45, 45)
        self.leftArrowButton.move(710, 315)
        self.leftArrowButton.clicked.connect(lambda:self.localToRemoteTransfer(self.localSelectedFile))
        self.leftArrowButton.setEnabled(False)

    def createTopLeftGroupBox(self):
        self.topLeftGroupBox = QGroupBox("Group 1")

        radioButton1 = QRadioButton("Radio Button 1")
        radioButton2 = QRadioButton("Radio Button 2")
        radioButton3 = QRadioButton("Radio Button 3")
        radioButton1.setChecked(True)

        layout = QVBoxLayout()
        layout.addWidget(radioButton1)
        layout.addWidget(radioButton2)
        layout.addWidget(radioButton3)
        layout.addStretch(1)
        self.topLeftGroupBox.setLayout(layout)

    def createTopTextBoxes(self):
        self.hostnameTextBox = QLineEdit(self)
        self.hostnameTextBox.move(200, 70)
        self.hostnameTextBox.resize(280, 40)
        self.hostnameTextBox.setPlaceholderText("Hostname: ")

        self.usernameTextBox = QLineEdit(self)
        self.usernameTextBox.move(550, 70)
        self.usernameTextBox.resize(280, 40)
        self.usernameTextBox.setPlaceholderText("Username: ")

        self.passwordTextBox = QLineEdit(self)
        self.passwordTextBox.setEchoMode(QLineEdit.Password)
        self.passwordTextBox.move(875, 70)
        self.passwordTextBox.resize(280, 40)
        self.passwordTextBox.setPlaceholderText("Password: ")

        self.quickConnectButton = QPushButton(self)
        self.quickConnectButton.setDefault(True)
        self.quickConnectButton.move(1300, 70)
        self.quickConnectButton.resize(150, 40)
        self.quickConnectButton.setText("Quick Connect")
        self.quickConnectButton.setStyleSheet('QPushButton {background-color: #fff; color: black; border: 1px solid blue;}')
        self.hostname = self.hostnameTextBox.text()
        self.username = self.usernameTextBox.text()
        self.password = self.passwordTextBox.text()
        self.quickConnectButton.clicked.connect(lambda:self.startFTP(self.hostnameTextBox.text(), self.usernameTextBox.text(), self.passwordTextBox.text()))
        self.show()
