#from atom.api import (Atom, Unicode, ContainerList, Bool, observe)
'''
class DataSourceStatus(Atom):
    name = Unicode()
    fullname = Unicode()
    showname = Unicode()
    isConnected = Bool()
    messages = ContainerList(default=[])
    errors = ContainerList(default=[])

    @observe('name')
    def update_showname(self, change):
        if not self.showname:
            self.showname = change['value']
'''