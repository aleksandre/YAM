import logging
from PySide.QtCore import *
from PySide.QtGui import *
import PySide.QtGui as QtGui
import PySide.QtCore as QtCore
from PySide.QtDeclarative import QDeclarativeView
import sys
from PySide import QtDeclarative 
from player import PhononPlayer
from profiling import profile
import content as content
import config as config


PLAYER = None




class MainWindow(QtGui.QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        global PLAYER
        PLAYER = PhononPlayer()
        PLAYER.setParent(self)

        self.initUI()
        self.createDockWindows()

    def initUI(self):         

        self.defaultView = DefaultMusicCollectionView(self)
        self.centerStackedWidget = QStackedWidget()

        self.centerStackedWidget.addWidget(self.defaultView)
        self.setCentralWidget(self.centerStackedWidget)
        
        self.setGeometry(840,0,840,1050)

        exitAction = QtGui.QAction('Exit', self)
        exitAction.setShortcut('Ctrl+X')
        exitAction.setStatusTip('Exit application')
        exitAction.triggered.connect(self.close)

        configAction = QtGui.QAction('Configure', self)
        configAction.setShortcut('Ctrl+S')
        configAction.setStatusTip('Configure')
        configAction.triggered.connect(self.showConfigPanel)

        self.statusBar()
        menubar = self.menuBar()
        fileMenu = menubar.addMenu('&File')
        fileMenu.addAction(exitAction)

        toolbar = self.addToolBar('Exit')
        toolbar.addAction(exitAction)
        toolbar.addAction(configAction)
        
        self.setWindowTitle('YAM')    

    def createDockWindows(self):
        print "setting docks"
        #Set TopPanel
        topDock = QtGui.QDockWidget("", self)
        topDock.setLayout(self.layout())
        topDock.setAllowedAreas(QtCore.Qt.LeftDockWidgetArea)
        topDock.setFeatures(QDockWidget.NoDockWidgetFeatures)
        topDock.setContentsMargins(0,0,0,0)
        topDock.setFloating(False)

        self.addDockWidget(QtCore.Qt.TopDockWidgetArea, topDock)

    def showConfigPanel(self):
        wizard = ConfigurationWizard()
        wizard.exec_()
        self.centerStackedWidget.removeWidget(self.defaultView)
        self.defaultView = DefaultMusicCollectionView(self)
        self.centerStackedWidget.addWidget(self.defaultView)


    def show_and_raise(self):
        self.show()
        self.raise_()


class ConfigurationWizard(QtGui.QWizard):
    def __init__(self, parent=None):
        super(ConfigurationWizard, self).__init__(parent)
        self.initUI()

    def initUI(self):  
        self.addPage(self.createIntroPage())
        self.addPage(self.createRegistrationPage())
        self.addPage(self.createLibraryLocationPage())
        self.addPage(self.createConclusionPage())

        self.setWindowTitle("YAM setup")

    def show_and_raise(self):
        self.show()
        self.raise_()

    def createIntroPage(self):
        page = QtGui.QWizardPage()
        page.setTitle("Introduction")

        label = QtGui.QLabel("This wizard will help you set the YAM client.")
        label.setWordWrap(True)

        layout = QtGui.QVBoxLayout()
        layout.addWidget(label)
        page.setLayout(layout)

        return page


    def createLibraryLocationPage(self):
        page = QtGui.QWizardPage()
        page.setTitle("Library location")
        page.setSubTitle("Define where the client should look for music.")

        configLocationDialog = QtGui.QPushButton("Library location:")
        configLocationDialog.clicked.connect(self._showLibraryDialog)

        self.libraryDirectoryEdit = QtGui.QLineEdit()
        self.libraryDirectoryEdit.setText(config.getPathToMusicLibrary())

        indexLibraryButton = QPushButton("Index library")
        indexLibraryButton.clicked.connect(self._indexLibrary)

        self.progressBar = QtGui.QProgressBar()
        self.progressBar.setMinimum(0)
        self.progressBar.setMaximum(100)

        layout = QtGui.QGridLayout()
        layout.addWidget(configLocationDialog, 0, 0)
        layout.addWidget(self.libraryDirectoryEdit, 0, 1)
        layout.addWidget(indexLibraryButton, 1, 0)
        layout.addWidget(self.progressBar,1,1)
        page.setLayout(layout)
        page.initializePage = self.initLibraryLocationPage

        return page

    def initLibraryLocationPage(self):
        self.libraryDirectoryEdit.setText(config.getPathToMusicLibrary())

    def createRegistrationPage(self):
        page = QtGui.QWizardPage()
        page.setTitle("Configuration")
        page.setSubTitle("Choose where to put the application configuration files.")

        configLocationDialog = QtGui.QPushButton("Configuration location:")
        configLocationDialog.clicked.connect(self._showFolderDialog)

        self.directoryEdit = QtGui.QLineEdit()
        self.directoryEdit.setText(config.getConfigFolder())
        layout = QtGui.QGridLayout()
        layout.addWidget(configLocationDialog, 0, 0)
        layout.addWidget(self.directoryEdit, 0, 1)
        page.setLayout(layout)

        return page

    def _showFolderDialog(self):
        options = QtGui.QFileDialog.DontResolveSymlinks | QtGui.QFileDialog.ShowDirsOnly
        directory = QtGui.QFileDialog.getExistingDirectory(self,
                "QFileDialog.getExistingDirectory()",
                self.directoryEdit.text(), options)
        if directory:
           self.directoryEdit.setText(directory)

    def _showLibraryDialog(self):
        options = QtGui.QFileDialog.DontResolveSymlinks | QtGui.QFileDialog.ShowDirsOnly
        directory = QtGui.QFileDialog.getExistingDirectory(self,
                "QFileDialog.getExistingDirectory()",
                self.libraryDirectoryEdit.text(), options)
        if directory:
           self.libraryDirectoryEdit.setText(directory)

    def _indexLibrary(self):
        musicLibraryFolder = self.libraryDirectoryEdit.text().encode("utf-8")
        musicLibraryFolder = musicLibraryFolder + "/"
        self.task = content.LibraryIndexationTask(musicLibraryFolder)
        self.progressBar.setMinimum(0)
        self.progressBar.setMaximum(self.task.getWorkload())
        QtCore.QObject.connect(self.task, QtCore.SIGNAL("progress(int)"),self.progressBar, QtCore.SLOT("setValue(int)"), QtCore.Qt.QueuedConnection)
        if not self.task.isRunning():
            self.task.exiting = False
            self.task.start()

    def createConclusionPage(self):
        page = QtGui.QWizardPage()
        page.setTitle("Conclusion")

        label = QtGui.QLabel("You have successfully set the YAM client. Have a nice day!")
        label.setWordWrap(True)
        layout = QtGui.QVBoxLayout()
        layout.addWidget(label)
        page.setLayout(layout)

        return page

    def accept(self):
        print "Saving configuration changes..."

        workFolder = self.directoryEdit.text().encode("utf-8")
        print "Setting work folder location:", workFolder
        config.setConfigFolder(workFolder)

        musicLibraryFolder = self.libraryDirectoryEdit.text().encode("utf-8")
        print "Setting music library location:", musicLibraryFolder
        config.setProperty(config.Properties.MUSIC_LIBRARY,musicLibraryFolder)

        print "Settings were changed."
        return self.done(0)




class ListModel(QtCore.QAbstractListModel):
    def __init__(self, os_list):
        super(ListModel, self).__init__()
        self.os_list = os_list

    def rowCount(self, parent):
        return len(self.os_list)

    def data(self, index, role = QtCore.Qt.DisplayRole):
        if not index.isValid():
            return None
        os_name, os_logo_path = self.os_list[index.row()]
        if role == QtCore.Qt.DisplayRole:
            return os_name
        elif role == QtCore.Qt.DecorationRole:
            return QtGui.QIcon(os_logo_path)

        return None



class TrackTable(QtGui.QTableWidget):
        
        def __init__(self):
            super(TrackTable, self).__init__()
            self.initUI()
            self.bindEvents()

        def initUI(self):
            self.setColumnCount(3)
            self.setSortingEnabled(True)
            self.setAlternatingRowColors(True)
            self.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
            self.setAutoScroll(True)
            self.setSizePolicy(QtGui.QSizePolicy.Expanding,QtGui.QSizePolicy.Expanding)
            self.setEditTriggers(QtGui.QAbstractItemView.NoEditTriggers)

        def bindEvents(self):
            self.itemDoubleClicked.connect(self.trackClicked)

        def keyPressEvent(self, event):
            key = event.key()
            print "Track table received KeyPressed event: ", key
            if key == QtCore.Qt.Key_P or key == QtCore.Qt.Key_Return:
                self._playTrack(self.currentItem().row())
                return
            elif key == QtCore.Qt.Key_Q:
                self._queueTrack(self.currentItem().row())
                return
            elif key == QtCore.Qt.Key_S:
                PLAYER.stop()
                return
            elif key == QtCore.Qt.Key_Left:
                self.focusPreviousChild()
                return
            elif key == QtCore.Qt.Key_Right:
                self.focusNextChild()
                return
            elif key == QtCore.Qt.Key_Space:
                PLAYER.togglePlayState()
                return
            elif key == QtCore.Qt.Key_Up:
                currentRow = self.currentRow()
                if currentRow > 0:
                    currentRow = currentRow - 1
                    self.setCurrentCell(currentRow, 0)
                else:
                    self.focusPreviousChild()
                return
            elif key == QtCore.Qt.Key_Down:
                currentRow = self.currentRow()
                if currentRow  < (self.rowCount() - 1):
                    currentRow = currentRow + 1
                    self.setCurrentCell(currentRow, 0)
                else:
                    self.focusNextChild()
                return
            else:
                QtGui.QWidget.keyPressEvent(self, event)

        def trackClicked(self, clickedItem):
            row = clickedItem.row()
            self.playTrack(row)
            
        def _playTrack(self, row):
            track = self._findTrack(row)
            if not track == None:
                PLAYER.playTrack(track)    

        def _queueTrack(self, row):
            track = self._findTrack(row)
            if not track == None:
                PLAYER.queue(track)    

        def _findTrack(self, row):
            trackTitle = self.item(row,0).text()
            print "Looking for track with title: ", trackTitle
            
            tracksWithTitle = filter(lambda x:x.title == trackTitle, self.tracks)
            if len(tracksWithTitle) > 0:
                track = tracksWithTitle[0]
                return track
            return None

        def setHeader(self, _labels = None):
            labels = _labels or  ('Title','Artist','Album')
            self.setHorizontalHeaderLabels(labels)

        def setTracks(self, data):
            print "Loading tracks into track table...", str(len(data))
            self.tracks = data
            self.clear()
            self.setRowCount(len(data))
            row = 0
            for track in data:
                self.setItem(row, 0, QTableWidgetItem(track.title ,0))
                self.setItem(row, 1, QTableWidgetItem(track.artist, 1))
                self.setItem(row, 2, QTableWidgetItem(track.albumTitle, 2))
                row = row + 1
            self.setHeader()
            self.resizeColumnsToContents()


class AlbumList(QtGui.QListWidget):

        albumClicked = QtCore.Signal(str)

        def __init__(self):
            super(AlbumList, self).__init__()
            self.initUI()
            self.bindEvents()

        def initUI(self):
            self.setMaximumHeight(200)
            
        def bindEvents(self):
            self.itemClicked.connect(self._albumClicked)

        def keyPressEvent(self, event):
            key = event.key()
            print "Album list received KeyPressed event: ", key
            
            if key == QtCore.Qt.Key_P:
                albumTitle = self.item(self.currentRow()).text()
                self._playAlbum(albumTitle)
                return
            elif key == QtCore.Qt.Key_Return:
                self._albumClicked(self.currentItem())
                return
            elif key == QtCore.Qt.Key_Q:
                albumTitle = self.item(self.currentRow).text()
                self._queueAlbum(albumTitle)
                return
            elif key == QtCore.Qt.Key_S:
                PLAYER.stop()
                return
            elif key == QtCore.Qt.Key_Space:
                PLAYER.togglePlayState()
                return
            elif key == QtCore.Qt.Key_Left:
                self.focusPreviousChild()
                return
            elif key == QtCore.Qt.Key_Right:
                self.focusNextChild()
                return
            elif key == QtCore.Qt.Key_Up:
                currentRow = self.currentRow()
                if currentRow > 0:
                    currentRow = currentRow - 1
                    self.setCurrentRow(currentRow)
                else:
                    self.focusPreviousChild()
                self._albumClicked(self.currentItem())
                return
            elif key == QtCore.Qt.Key_Down:
                currentRow = self.currentRow()
                if currentRow < (self.count() - 1):
                    currentRow = currentRow + 1
                    self.setCurrentRow(currentRow)
                else:
                    self.focusNextChild()
                self._albumClicked(self.currentItem())
                return
            else:
                return super(QListWidget, self).keyPressEvent(event)

        def setAlbums(self, tracks):
            print "Loading albums into listview..."
            self.clear()
            self.tracks = tracks
            albums = content.getAlbums(tracks)
            
            index = 0
            headerText = "All albums (" + str(len(albums)) + ")"
            header = QListWidgetItem(headerText)
            self.insertItem(0, header)
            
            index = index + 1
            for album in albums:
                item = QListWidgetItem(album)
                self.insertItem(index, item)
                index = index + 1

        def _albumClicked(self, albumRowModel):
            pass

        def _playAlbum(self, albumTitle):
            tracks = self._getTracksForSelectedAlbum(albumTitle)
            PLAYER.playTracks(tracks)

        def _queueAlbum(self, albumTitle):
            tracks = self._getTracksForSelectedAlbum(albumTitle)
            PLAYER.queueTracks(tracks)

        def _getTracksForSelectedAlbum(self, albumTitle):
            tracksForAlbum = content.getTracksForAlbum(albumTitle, self.tracks)
            return tracksForAlbum

        def selectionChanged(self, newSelection, oldSelection):
            self.albumClicked.emit(self.currentItem().text())


class ArtistList(QtGui.QListView):

     artistsAndCovers = None
     artistClicked = QtCore.Signal(QModelIndex)

     def __init__(self):
        super(ArtistList, self).__init__()
        self.initUI()
        self.bindEvents()

     def initUI(self):
        self.setIconSize(QtCore.QSize(50, 50))
        self.setSpacing(5)
        self.setUniformItemSizes(True)
        self.setMaximumWidth(300)

     def bindEvents(self):
        pass

     def keyPressEvent(self, event):
        key = event.key()
        print "Album list received KeyPressed event: ", key
        
        if key == QtCore.Qt.Key_P:
            #albumTitle = self.item(self.currentRow()).text()
            #self._playAlbum(albumTitle)
            return
        elif key == QtCore.Qt.Key_Return:
            self.artistClicked.emit(previousArtist)
            return
        elif key == QtCore.Qt.Key_Q:
            #albumTitle = self.item(self.currentRow).text()
            #self._queueAlbum(albumTitle)
            return
        elif key == QtCore.Qt.Key_S:
            PLAYER.stop()
            return
        elif key == QtCore.Qt.Key_Space:
            PLAYER.togglePlayState()
            return
        elif key == QtCore.Qt.Key_Left:
            self.focusPreviousChild()
            return
        elif key == QtCore.Qt.Key_Right:
            self.focusNextChild()
            return
        elif key == QtCore.Qt.Key_Up:
            previousArtist = self._getPreviousArtistQIndex()
            if previousArtist:
                self.setCurrentIndex(previousArtist)
            self.artistClicked.emit(previousArtist)
            return
        elif key == QtCore.Qt.Key_Down:
            nextArtist = self._getNextArtistQIndex()
            if nextArtist:
                self.setCurrentIndex(nextArtist)
            self.artistClicked.emit(nextArtist)
            return
        else:
            print "Artist list could not handle key event"
            return super(QListView, self).keyPressEvent(event)

     def setArtists(self, artistsAndCovers):
        self.artistsAndCovers = artistsAndCovers
        list_model = ListModel(artistsAndCovers)
        self.setModel(list_model)

     def _getNextArtistQIndex(self):
        if len(self.selectedIndexes()) > 0:
            currentArtist = self.selectedIndexes()[0]
            if currentArtist.row() < (len(self.artistsAndCovers)  - 1):
                nextArtist = currentArtist.sibling(currentArtist.row() + 1,0)
                return nextArtist
        return None 

     def _getPreviousArtistQIndex(self):
        if len(self.selectedIndexes()) > 0:
            currentArtist = self.selectedIndexes()[0]
            if currentArtist.row() > 0:
                previousArtist = currentArtist.sibling(currentArtist.row() - 1,0)
                return previousArtist
        return None 

     def selectionChanged(self, newSelection, oldSelection):
         self.artistClicked.emit(newSelection.indexes()[0])

class DefaultMusicCollectionView(QtGui.QWidget):

     def __init__(self, parent = None):
        super(DefaultMusicCollectionView, self).__init__(parent)
        self.tracks = content.getTracks()
        self.initUI()

     def initUI(self):
        #Prepare main layout
        hbox = QtGui.QHBoxLayout(self)
        self.setLayout(hbox)

        #Prepare artist view
        self.artistsView = ArtistList()
        self.artistsView.artistClicked.connect(self.artistClicked)
        hbox.addWidget(self.artistsView)
        self.artistsAndCovers = content.getArtistsWithRandomCover()
        self.artistsView.setArtists(self.artistsAndCovers)
        
        #Prepare right layout
        self.rightPanel = QWidget()     
        self.rightVBox = QVBoxLayout()
        self.rightPanel.setLayout(self.rightVBox)
        hbox.addWidget(self.rightPanel)

        #Prepare albums view
        self.albumsView = AlbumList()
        self.albumsView.albumClicked.connect(self.albumClicked)
        self.albumsView.setAlbums(self.tracks)
        self.rightVBox.addWidget(self.albumsView)
        
        #Prepare tracks view
        self.tracksTable = TrackTable()
        self.tracksTable.setTracks(self.tracks)
        self.rightVBox.addWidget(self.tracksTable)


     def albumClicked(self, albumTitle):
        tracksForAlbum = content.getTracksForAlbum(albumTitle, self.tracks)
        self.tracksTable.close()
        self.rightVBox.removeWidget(self.tracksTable)
        self.tracksTable = TrackTable()
        self.tracksTable.setTracks(tracksForAlbum)

        self.rightVBox.addWidget(self.tracksTable)

     def artistClicked(self, artistRowModel):
        artistName = self.artistsAndCovers[artistRowModel.row()][0]
        print "Clicked on artist: ", artistName

        albumsForArtist = filter(lambda x:x.artist == artistName, self.tracks)
        self.albumsView.setAlbums(albumsForArtist)

if __name__ == '__main__':
    logging.basicConfig(filename='log/dev.log', level=logging.DEBUG)
   
    logging.info("Starting amc client.")

    # Create a Qt application
    app = QApplication(sys.argv,QApplication.GuiServer)
    app.setApplicationName('yam')

    main = MainWindow()
    main.show_and_raise()

    # Enter Qt application main loop
    execResult = app.exec_()
    print execResult
    logging.info(execResult)
    exitResult = sys.exit()

    logging.info("Stopped yam client.")

