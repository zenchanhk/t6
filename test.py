from multiprocessing import Process, Queue, Pipe
from threading import Thread
import sys
from PyQt5 import QtGui, QtCore
from PyQt5 import QtWidgets

class Emitter(QtCore.QObject, Thread):
    msg = QtCore.pyqtSignal(object)
    def __init__(self, transport, parent=None):
        QtCore.QObject.__init__(self, parent)
        Thread.__init__(self)
        self.transport = transport

    def _emit(self, signature, args=None):
        if args:
            self.msg.emit(args)
        else:
            self.msg.emit()

    def run(self):
        while True:
            try:
                # signature = self.transport.recv()
                signature = self.transport.get()
                print(signature)
            except EOFError:
                break
            else:
                self._emit(*signature)

class Form(QtWidgets.QDialog):

    def __init__(self, queue, emitter, parent=None):
        super().__init__(parent)
        self.data_to_child = queue
        self.emitter = emitter
        self.emitter.daemon = True
        self.emitter.start()
        self.browser = QtWidgets.QTextBrowser()
        self.lineedit = QtWidgets.QLineEdit('Type text and press <Enter>')
        self.lineedit.selectAll()
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.browser)
        layout.addWidget(self.lineedit)
        self.setLayout(layout)
        self.lineedit.setFocus()
        self.setWindowTitle('Upper')
        self.lineedit.returnPressed.connect(self.to_child)
        #self.connect(self.emitter, QtCore.SIGNAL('data(PyObject)'), self.updateUI)
        self.emitter.msg.connect(self.updateUI)

    def to_child(self):
        self.data_to_child.put(self.lineedit.text())
        self.lineedit.clear()

    def updateUI(self, text):
        self.browser.append(text[0])

class ChildProc(Process):

    def __init__(self, transport, queue, daemon=True):
        Process.__init__(self)
        self.daemon = daemon
        self.transport = transport
        self.data_from_mother = queue

    def emit_to_mother(self, signature, args=None):
        signature = (signature, )
        if args:
            signature += (args, )
        # self.transport.send(signature)
        self.transport.put(signature)

    def run(self):
        while True:
            text = self.data_from_mother.get()
            self.emit_to_mother('data(PyQt_PyObject)', (text.upper(),))

if __name__ == '__main__':

    app = QtWidgets.QApplication(sys.argv)
    mother_pipe, child_pipe = Pipe()
    q2 = Queue()
    queue = Queue()
    # emitter = Emitter(mother_pipe)
    emitter = Emitter(queue)
    form = Form(queue, emitter)
    # ChildProc(child_pipe, queue).start()
    ChildProc(queue, queue).start()
    form.show()
    app.exec_()
    sys.exit(0)