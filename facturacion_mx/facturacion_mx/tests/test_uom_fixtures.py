# Copyright (c) 2026, Consultoria en Negocios y Aplicaciones and Contributors
# See license.txt

"""Integrity tests for the SAT UOM fixtures shipped by facturacion_mx.

These run without a database: they parse the JSON fixtures directly and assert
they satisfy the constraints enforced by ERPNext's ``UOM Conversion Factor``
``validate()`` (introduced in erpnext v16.55.0 via PR #62336). A violation here
means ``bench migrate`` would fail during ``Syncing fixtures...`` on any site.
"""

import json
import os
import unittest

FIXTURES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "fixtures"
)


def _load(filename):
    with open(os.path.join(FIXTURES_DIR, filename), encoding="utf-8") as f:
        return json.load(f)


class TestUOMFixtures(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.conversions = _load("uom_conversion_factor.json")
        cls.uoms = {row["name"] for row in _load("uom.json")}

    def test_no_self_conversion(self):
        """ERPNext rejects records where from_uom == to_uom."""
        offenders = [
            r["name"] for r in self.conversions if r["from_uom"] == r["to_uom"]
        ]
        self.assertEqual(offenders, [], f"from_uom == to_uom in: {offenders}")

    def test_positive_value(self):
        """ERPNext rejects a conversion value <= 0."""
        offenders = [r["name"] for r in self.conversions if float(r["value"]) <= 0]
        self.assertEqual(offenders, [], f"value <= 0 in: {offenders}")

    def test_no_duplicate_pairs(self):
        """No two records share the same (category, from_uom, to_uom)."""
        seen, offenders = set(), []
        for r in self.conversions:
            key = (r["category"], r["from_uom"], r["to_uom"])
            if key in seen:
                offenders.append(r["name"])
            seen.add(key)
        self.assertEqual(offenders, [], f"duplicate pairs in: {offenders}")

    def test_no_reverse_pairs(self):
        """ERPNext rejects a reverse pair when one already exists (A->B and B->A)."""
        seen, offenders = set(), []
        for r in self.conversions:
            cat, frm, to = r["category"], r["from_uom"], r["to_uom"]
            if (cat, to, frm) in seen:
                offenders.append(r["name"])
            seen.add((cat, frm, to))
        self.assertEqual(offenders, [], f"reverse-pair conflicts in: {offenders}")

    def test_referenced_uoms_exist(self):
        """Every from_uom / to_uom must be defined in uom.json (referential integrity)."""
        referenced = {r["from_uom"] for r in self.conversions} | {
            r["to_uom"] for r in self.conversions
        }
        missing = sorted(referenced - self.uoms)
        self.assertEqual(
            missing, [], f"UOMs referenced but missing from uom.json: {missing}"
        )


if __name__ == "__main__":
    unittest.main()
