import argparse
import os

from cgi import escape
from collections import OrderedDict, defaultdict

from mozlog.structured import reader

class LogHandler(reader.LogHandler):
    def __init__(self):
        self.data = {"products":[],
                     "results": OrderedDict()}
        self.product_index = None

    def set_products(self, products):
        self.data["products"] = products

    def set_product(self, product):
        self.product_index = self.data["products"].index(product)

    def _get_test_id(self, data):
        test_id = data.get("test")
        if isinstance(test_id, list):
            test_id = tuple(test_id)
        return test_id

    def test_start(self, data):
        products = self.data["products"]
        test_id = self._get_test_id(data)
        if test_id not in self.data["results"]:
            self.data["results"][test_id] = {
                "id": test_id,
                "test":[None] * len(products),
                "subtests":defaultdict(lambda: [None] * len(products))}

    def test_status(self, data):
        self.data["results"][self._get_test_id(data)]["subtests"][data["subtest"]][self.product_index] = data["status"]

    def test_end(self, data):
        test_id = self._get_test_id(data)
        self.data["results"][test_id]["test"][self.product_index] = data["status"]

def record_results(*log_files):
    handler = LogHandler()

    products = []
    for name in log_files:
        product, filename = name.split(":", 1)
        products.append((product, filename))

    handler.set_products([item[0] for item in products])
    for product, logfile in products:
        handler.set_product(product)
        with open(logfile) as f:
            reader.handle_log(reader.read(f),
                              handler)

    data = handler.data

    data["results"] = data["results"].values()

    return data


def summary(data):
    rv = {}
    for i, product in enumerate(data["products"]):
        rv[product] = {"ran":0, "passed":0}
        for test in data["results"]:
            if test["test"][i] is not None:
                rv[product]["ran"] += 1
                if test["test"][i] in ("PASS", "OK"):
                    rv[product]["passed"] += 1

                for results in test["subtests"].itervalues():
                    if results[i] is not None:
                        rv[product]["ran"] += 1
                        if results[i] == "PASS":
                            rv[product]["passed"] += 1

    return rv

def failures(target, data):
    target_index = data["products"].index(target)

    total = 0
    failures = []

    for test in data["results"]:
        if test["test"][target_index] is not None:
            total += 1
            if test["test"][target_index] not in ("PASS", "OK"):
                failures.append((test["id"], None, test["test"][target_index]))
            for name, results in test["subtests"].iteritems():
                if results[target_index] is not None:
                    total += 1
                    if results[target_index] not in ("PASS", "OK"):
                        failures.append((test["id"], name, results[target_index]))

    return {"total": total,
            "failures": failures}

def failure_report(target, failure_data):
    rv = [u"""<!doctype html>
<meta charset=utf8>
<title>Failure Report</title>
<style>
.condition {font-variant: small-caps; text-align:center; color:white}
.PASS {background-color:green}
.OK {background-color:green}
.FAIL {background-color:red}
.ERROR {background-color:orange}
.TIMEOUT {background-color:blue}
.NOTRUN {background-color:blue}
.CRASH {background-color:black; color:white}
</style>
<h1>Failure Report for %(target)s</h1>
<p>Total tests run: %(count)i
<p>Total failures: %(failures_count)i
<table>
<tr><th>Title</th><th>Subtest</th><th>Status</th></tr>
    """ % {"count": failure_data["total"], "failures_count": len(failure_data["failures"]), "target": escape(target.title())}]

    for test, subtest, status in failure_data["failures"]:
        rv.append(
            u"<tr><td>%(test)s<td>%(subtest)s<td class='condition %(status)s'>%(status)s</tr>" % {
                "test": escape(test),
                "subtest": escape(subtest) if subtest else "",
                "status": escape(status)})
    rv.append(u"</table>")

    return u"\n".join(rv)


def regressions(base, target, data):
    score = dict((name, i) for i, name in
                 enumerate(["OK", "PASS", "FAIL", "ERROR", "TIMEOUT", "NOTRUN", "CRASH"]))

    base_index = data["products"].index(base)
    target_index = data["products"].index(target)

    total = 0
    regressions = []

    for test in data["results"]:
        if (test["test"][base_index] is not None and
            test["test"][target_index] is not None):
            total += 1
            if score[test["test"][target_index]] > score[test["test"][base_index]]:
                regressions.append((test["id"], None, test["test"][base_index], test["test"][target_index]))
            for name, results in test["subtests"].iteritems():
                if (results[base_index] is not None and
                    results[target_index] is not None):
                    total += 1
                    if score[results[target_index]] > score[results[base_index]]:
                        regressions.append((test["id"], name, results[base_index], results[target_index]))

    return {"total": total,
            "regressions": regressions}

def regressions_report(base, target, regression_data):
    rv = [u"""<!doctype html>
<meta charset=utf8>
<title>Regression Report</title>
<style>
.condition {font-variant: small-caps; text-align:center; color:white}
.PASS {background-color:green}
.OK {background-color:green}
.FAIL {background-color:red}
.ERROR {background-color:orange}
.TIMEOUT {background-color:blue}
.NOTRUN {background-color:blue}
.CRASH {background-color:black; color:white}
</style>
<h1>Regression Report</h1>
<p>Total tests in common: %(count)i
<p>Total regressions: %(regressions_count)i
<table>
<tr><th>Title</th><th>Subtest</th><th>%(base)s</th><th>%(target)s</th></tr>
    """ % {"count": regression_data["total"], "regressions_count": len(regression_data["regressions"]), "base": escape(base.title()), "target": escape(target.title())}]

    for test, subtest, base_status, target_status in regression_data["regressions"]:
        rv.append(
            u"<tr><td>%(test)s<td>%(subtest)s<td class='condition %(base_status)s'>%(base_status)s<td class='condition %(target_status)s'>%(target_status)s</tr>" % {
                "test": escape(test),
                "subtest": escape(subtest) if subtest else "",
                "base_status": escape(base_status),
                "target_status": escape(target_status)})
    rv.append(u"</table>")

    return u"\n".join(rv)

def get_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("--regressions", action="store",
                        help="base:target for regression summary")
    parser.add_argument("--failures", action="store",
                        help="target for regression summary")
    parser.add_argument("files", nargs="*",
                        help="Log files to use as input")
    return parser

def main():
    args = get_parser().parse_args()
    data = record_results(*args.files)

    if args.failures is not None:
        target = args.failures
        failure_data = failures(target, data)
        print failure_report(target, failure_data).encode("utf8")

    if args.regressions is not None:
        base, target = args.regressions.split(":", 1)
        regression_data = regressions(base, target, data)
        print regressions_report(base, target, regression_data).encode("utf8")

if __name__ == "__main__":
    main()
