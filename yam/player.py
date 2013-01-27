
"""
This module holds differents implementation of Player like : local, remote and stream (coming soon)
"""
import sys
import os
from socket import *
from PySide import QtCore, QtGui
from PySide.QtCore import *
from PySide.QtGui import *
import threading
import socket
try:
    from PySide.phonon import Phonon
except ImportError as error:
    print error
    sys.exit(1)

def getPlayerByType(device):
    if device.type == "local":
        return LocalPlayer()
    if device.type == "remote":
        return RemotePlayer(device.host, device.port)

class PlayerStates:
    STOPPED="STOPPED"
    PLAYING="PLAYING"
    PAUSED="PAUSED"
    ERROR = "ERROR"

class LocalPlayer(QtCore.QObject):
    """
    The LocalPlayer uses the Qt Phonon module to play music files
    """
    stateChanged = QtCore.Signal()
    playerTicked = QtCore.Signal()

    _playlist = []
    _playlistIdx = 0

    def __init__(self, loadForClient = False): 
        QtCore.QObject.__init__(self)
        try:
            self.app = QtGui.QApplication(sys.argv)
        except RuntimeError:
            self.app = QtCore.QCoreApplication.instance()
        self.app.aboutToQuit.connect(self.exit)
        self.init()

    def init(self):
        self.audioOutput = Phonon.AudioOutput(Phonon.MusicCategory, self.app)
        self.player = Phonon.MediaObject(self.app)
        self.player.setPrefinishMark(5000)
        Phonon.createPath(self.player, self.audioOutput)
        self._bindEvents()

    def setHeadless(self):
        self.app.setApplicationName('headless-player')

    def currentPlaylist(self):
        print "Play list requested"
        return self._playlist 
    
    def hasNextTrack(self):
        return self._playlistIdx + 1 < len(self._playlist) 
    
    def hasPreviousTrack(self):
        return  self._playlistIdx > 0

    def currentlyPlayingTrack(self):
        return self._playlist[self._playlistIdx]

    def playTrack(self, track):
        self._resetPlaylist()

        trackPath = os.path.realpath(track.filePath)
        print "Playing track: ", track.title
        
        self.player.setCurrentSource(Phonon.MediaSource(trackPath))
        self._playlist.append(track)
        self.player.play()


    def playTracks(self, tracks=[]):
        self._resetPlaylist()
        for track in tracks:
            self.queueTrack(track, emit=False)

        firstTrack = Phonon.MediaSource(self._playlist[self._playlistIdx].filePath)
        self.player.setCurrentSource(firstTrack)
        self.player.play()
        return self.getState() == "PLAYING"


    def playNextTrack(self):
        print "Playing next track..."
        if self.hasNextTrack():
            self._playlistIdx = self._playlistIdx + 1
            nextTrack = Phonon.MediaSource(self._playlist[self._playlistIdx].filePath)
            print nextTrack
            print self.player.setCurrentSource(nextTrack)
            print self.player.play()
        return self.getState() == "PLAYING"

    def playPreviousTrack(self):
        if self.hasPreviousTrack():
            self._playlistIdx = self._playlistIdx - 1
            previousTrack = Phonon.MediaSource(self._playlist[self._playlistIdx].filePath)
            self.player.setCurrentSource(previousTrack)
            self.player.play()
        return self.getState() == "PLAYING"


    def queueTrack(self, track, emit=True):
        print "Queuing track: ", track
        self._playlist.append(track)
        return track in self._playlist


    def queueTracks(self, tracks):
        for track in tracks:
            self.queueTrack(track, emit=False)
        return True

    def stop(self):
        print "Stopping player"
        self.player.stop()
        return self.getState() == "STOPPED"

    def resume(self):
        self.player.play()
        return self.getState() == "PLAYING"

    def pause(self):
        self.player.pause()
        return self.getState() == "PAUSED"

    def getCurrentTime(self):
        self.player.currentTime()

    def getState(self):
        playerState = self.player.state()

        if playerState == Phonon.StoppedState:
            return PlayerStates.STOPPED
        if playerState == Phonon.PlayingState:
            return PlayerStates.PLAYING
        if playerState == Phonon.PausedState:
            return PlayerStates.PAUSED
        if playerState == Phonon.ErrorState:
            return PlayerStates.ERROR

        return "INVALID STATE"

    def togglePlayState(self):
        state = self.getState()
        if state == PlayerStates.PAUSED:
            self.resume()
        elif state == PlayerStates.PLAYING:
            self.pause()
        return True

    def notifyStateChanged(self):
        print "changed"

    def _stateChanged(self,state,state1):
        self.stateChanged.emit()

    def _sourceChanged(self, source):
        print "Player source changed", source
        self.stateChanged.emit()

    def _aboutToFinish(self):
        print "Player is about to finish playing the current track..."
        if self.hasNextTrack:
            self._playlistIdx = self._playlistIdx + 1
            nextTrack = Phonon.MediaSource(self._playlist[self._playlistIdx].filePath)
            self.player.enqueue(nextTrack)
        else:
            print "It was the last track, do nothing."

    def _bindEvents(self):
        self.connect(self.player, SIGNAL('tick(qint64)'), self._tick)
        self.connect(self.player, SIGNAL('stateChanged(Phonon::State, Phonon::State)'), self._stateChanged)
        self.connect(self.player, SIGNAL('currentSourceChanged(Phonon::MediaSource)'), self._sourceChanged)
        self.connect(self.player, SIGNAL('aboutToFinish()'), self._aboutToFinish)


    def _tick(self, time):
        displayTime = QtCore.QTime(0, (time / 60000) % 60, (time / 1000) % 60)
        self.playerTicked.emit()
        #print displayTime
        #self.timeLcd.display(displayTime.toString('mm:ss'))
    
    def _resetPlaylist(self):
        self._playlist = []
        self._playlistIdx = 0
        self.player.clearQueue()

    def start(self):
        self.app.exec_()

    def exit(self):
        self.app.exit()

    state = QtCore.Property(QUrl, getState, notify=notifyStateChanged)


class RemoteClient():
    """
    The RemoteClient sends commands to a remote DeviceRequestListener via TCP.
    """
    def __init__(self, host, port, callback = None, name="reqsender"):
        print "Remote client initiated with url: {0}:{1}".format(host, port)
        self.tcpIP = host
        self.tcpPort = int(port)
        self.bufferSize = 25000
        self.name = name
        self.callback = callback

    def printInfo(self):
        print "Targeting: {0}:{1}".format(self.tcpIP,self.tcpPort)

    def connect(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        self.sock.settimeout(5)
        print "Connecting to {0}:{1}".format(self.tcpIP,self.tcpPort)
        self.sock.connect((self.tcpIP, self.tcpPort))
        print "Connected."

    def sendRequest(self, request):
        self.connect()
        print "Sending request..."
        answer = None
        try:
            self.sock.sendall(request + "\n")
            answer = data = self.sock.recv(4096)
            print "Receiving data from server: {0}".format(answer)
            while not data.endswith("\n"): 
                data = self.sock.recv(4096)
                answer = answer + data
            print "Got complete answer from server: {0}".format(answer)
        except IOError as e:
            print e

        #if self.callback:
           # self.callback(answer)
        self.disconnect()
        return answer

    def disconnect(self):
        print "Disconnecting from server..."
        self.sock.close()

class RemotePlayer(QtCore.QObject):
    """
    The RemotePlayer redirects all requests to an host using a RemoteClient
    """
    stateChanged = QtCore.Signal()
    playerTicked = QtCore.Signal()

    def __init__(self, host, port, remoteClient = None): 
       QtCore.QObject.__init__(self)
       if not remoteClient:
            self.remoteClient = RemoteClient(host, port)
       else :
            self.remoteClient = remoteClient

    def setRemoteClient(self,remoteClient):
        self.remoteClient = remoteClient

    def setParent(self, parent):
        print "Remote player has no use for a parent..."

    def setHeadless(self):
        print "Remote player has no use for a parent..."

    def currentPlaylist(self):
        print "Play list requested"
        return self._playlist 
    
    def hasNextTrack(self):
        request = 'player;hasNextTrack'
        return self.remoteClient.sendRequest(request)
    
    def hasPreviousTrack(self):
        request = 'player;hasPreviousTrack'
        return self.remoteClient.sendRequest(request)

    def currentlyPlayingTrack(self):
        request = 'player;currentlyPlayingTrack'
        return self.remoteClient.sendRequest(request)

    def playTrack(self, track):
        request = 'player;playTrack;{0}'.format(track)
        return self.remoteClient.sendRequest(request)

    def playTracks(self, tracks=[]):
        request = 'player;playTracks;{0}'.format(self._encodeTracks(tracks))
        return self.remoteClient.sendRequest(request)

    def queueTrack(self, track, emit=True):
        request = 'player;queueTrack;{0}'.format(track)
        return self.remoteClient.sendRequest(request)

    def queueTracks(self, tracks):
        request = 'player;queueTracks;{0}'.format(self._encodeTracks(tracks))
        return self.remoteClient.sendRequest(request)

    def playNextTrack(self):
        request = 'player;playNextTrack'
        return self.remoteClient.sendRequest(request)

    def playPreviousTrack(self):
        request = 'player;playPreviousTrack'
        return self.remoteClient.sendRequest(request)

    def stop(self):
        request = 'player;stop'
        return self.remoteClient.sendRequest(request)

    def resume(self):
        request = 'player;resume'
        return self.remoteClient.sendRequest(request)

    def pause(self):
        request = 'player;pause'
        return self.remoteClient.sendRequest(request)

    def getCurrentTime(self):
        request = 'player;getCurrentTime'
        return self.remoteClient.sendRequest(request)

    def getState(self):
        request = 'player;getState'
        return self.remoteClient.sendRequest(request)

    def togglePlayState(self):
        request = 'player;togglePlayState'
        return self.remoteClient.sendRequest(request)

    def notifyStateChanged(self):
        print "changed"
    
    def _encodeTracks(self,tracks):
        requestData = ""
        for track in tracks:
            requestData = requestData + str(track) + '|'
        requestData = requestData[:-1] #remove last |
        return requestData

def test():
    import time
    import content as content
    tracks = content.getTracks()

    player = RemotePlayer(qapp)
    player.playTrack(tracks[1])
    player.queueTrack(tracks[0])

    assert player.currentlyPlayingTrack() is tracks[1]

    time.sleep(5)
    player.playNextTrack()
    assert player.currentlyPlayingTrack() is tracks[0]

    sys.exit(qapp.exec_())    

if __name__ == "__main__":
    test()
