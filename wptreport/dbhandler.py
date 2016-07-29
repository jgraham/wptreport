import argparse
import json
import sys

from mozlog import reader

import model
from model import Session, Run, Status, Test, Result

def get_or_create(session, model, **kwargs):
    instance = session.query(model).filter_by(**kwargs).first()
    if instance:
        return instance, False
    else:
        instance = model(**kwargs)
        session.add(instance)
        return instance, True

class LogHandlerTests(reader.LogHandler):
    def __init__(self):
        self.session = Session()
        self.tests = {(item.test, item.subtest) for item in self.session.query(Test)}
        self.new_tests = []

    def _insert_test(self, test, subtest):
        if (test, subtest) not in self.tests:
            test_obj = {"test": test,
                        "subtest": subtest}
            self.new_tests.append(test_obj)
            self.tests.add((test, subtest))

    def test_status(self, data):
        test = self._insert_test(data["test"], data["subtest"])

    def test_end(self, data):
        self._insert_test(data["test"], None)
        sys.stdout.write("-")
        sys.stdout.flush()

    def suite_end(self, data):
        self.session.bulk_insert_mappings(Test, self.new_tests)
        self.session.commit()
        sys.stdout.write(" committing\n")

class LogHandlerResults(reader.LogHandler):
    def __init__(self, run_name):
        self.session = Session()
        self.run = None
        self.status = {item.name: item.id for item in self.session.query(Status)}
        self.tests = {(item.test, item.subtest): item.id for item in self.session.query(Test)}
        self.results = None
        self.run, _ = get_or_create(self.session, Run, name=run_name)
        self.new_results = {}
        self.update_results = {}

    def _insert_result(self, test_id, status_id):
        result = {"run_id": self.run.id,
                  "test_id": test_id,
                  "status_id": status_id}
        result_id = (self.run.id, test_id)
        target = self.new_results if test_id not in self.results else self.update_results
        target[result_id] = result

    def suite_start(self, data):
        self.run.info = json.dumps(data["run_info"])
        self.results = {item.test_id
                        for item in self.session.query(Result).filter(Run.id == self.run.id)}

    def test_status(self, data):
        test_id = self.tests[(data["test"], data["subtest"])]
        status_id = self.status[data["status"]]
        self._insert_result(test_id, status_id)

    def test_end(self, data):
        test_id = self.tests[(data["test"], None)]
        status_id = self.status[data["status"]]
        self._insert_result(test_id, status_id)
        sys.stdout.write(".")
        sys.stdout.flush()

    def suite_end(self, data):
        sys.stdout.write(" committing\n")
        self.session.bulk_insert_mappings(Result, self.new_results.values())
        self.session.bulk_update_mappings(Result, self.update_results.values())
        self.session.commit()


def clean_run(name):
    session = Session()
    run = session.query(Run).filter(Run.name==name).first()
    if run is None:
        return
    session.query(Result).filter(Result.run==run).delete(synchronize_session=False)
    session.commit()


def record_results(no_clean, *log_files):
    runs_cleaned = set()

    for name in log_files:
        run_name, filename = name.split(":", 1)
        if run_name not in runs_cleaned and not no_clean:
            clean_run(run_name)
            runs_cleaned.add(run_name)
        sys.stdout.write("Processing run %s\n" % run_name)

        with open(filename) as f:
            test_handler = LogHandlerTests()
            reader.handle_log(reader.read(f),
                              test_handler)
            f.seek(0)
            result_handler = LogHandlerResults(run_name)
            reader.handle_log(reader.read(f),
                              result_handler)


def create_statuses():
    session = Session()
    existing = set(item.name for item in session.query(Status))
    for status in ["PASS", "FAIL", "OK", "ERROR", "TIMEOUT", "CRASH",
                   "ASSERT", "SKIP", "NOTRUN"]:
        if status not in existing:
            session.add(Status(name=status))
    session.commit()


def get_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("-o", "--output", action="store",
                        default="results.db",
                        help="Database file name to use for writing results")
    parser.add_argument("files", nargs="*",
                        help="Log files to use as input")
    parser.add_argument("--no-clean", action="store_false", dest="clean", default=True,
                        help="Don't clean out existing results for each run")
    return parser


def main():
    args = get_parser().parse_args()
    model.init(args.output)
    create_statuses()
    record_results(not args.clean, *args.files)


if __name__ == "__main__":
    import pdb
    import traceback
    try:
        main()
    except Exception:
        traceback.print_exc()
        pdb.post_mortem()
