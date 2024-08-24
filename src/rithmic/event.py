class Event:
    def __init__(self):
        self._subscribers = []

    def __iadd__(self, callback):
        self._subscribers.append(callback)
        return self

    def __isub__(self, callback):
        self._subscribers.remove(callback)
        return self

    async def notify(self, data):
        for callback in self._subscribers:
            try:
                await callback(data)
            except Exception as e:
                print(f"Error in callback: {e}")
