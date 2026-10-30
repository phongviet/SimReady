"""Expose bounded JUnit failure details as public CI annotations; preserve test exit status."""

import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def escape(value):
    return value.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


path = Path(sys.argv[1])
if path.exists():
    for case in ET.parse(path).iter("testcase"):
        failure = case.find("failure")
        if failure is None:
            failure = case.find("error")
        if failure is not None:
            title = escape(case.get("name", "pytest failure")).replace(",", "%2C")
            text = (failure.text or failure.get("message", "pytest failed"))[-8000:]
            print(f"::error title={title}::{escape(text)}")
else:
    print("::warning::No JUnit results were produced; inspect the test step failure.")
