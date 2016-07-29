from mozlog.structured import reader

class LogHandler(reader.LogHandler):
    def __init__(self):
        self._result_list = []
        self.rv = {"results": self._result_list}
        self.in_progress = {}

    def test_id(self, name):
        if isinstance(name, (str, unicode)):
            return name
        else:
            return tuple(name)

    def test_start(self, data):
        self.in_progress[self.test_id(data["test"])] = []

    def test_status(self, data):
        test_id = self.test_id(data["test"])
        assert test_id in self.in_progress
        self.in_progress[test_id].append(
            {"name": data["subtest"],
             "status": data["status"],
             "message": data.get("message", None)})

    def test_end(self, data):
        test_id = self.test_id(data["test"])
        subtests = self.in_progress.pop(test_id)
        self.result_list.append(
            {"test": test_id,
             "subtests": subtests,
             "status": data["status"]
             "message": data.get("message", None)})

def to_json(*log_files):
    handler = LogHandler()
    for f in log_files:
        reader.handle_log(reader.read(f),
                          handler)

    return handler.rv
