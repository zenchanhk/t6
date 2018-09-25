import json


class Event:
    def __init__(self):
        self.events = set()

    def __add__(self, event):
        self.events.add(event)
        return self

    def __sub__(self, event):
        self.events.remove(event)
        return self

    def notify_all(self, msg):
        for e in self.events:
            if isinstance(e, str):
                e(msg)
            else:
                e(json.dumps(msg))

    def cleanup(self):
        self.events = set()