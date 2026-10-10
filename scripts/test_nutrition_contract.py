"""Public target contract preserves unknown values and exact decimals."""
import json
from pathlib import Path
import unittest

from jsonschema import Draft202012Validator


class TargetContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = Path(__file__).resolve().parents[1] / "contracts/nutrition-profile.schema.json"
        cls.validator = Draft202012Validator(json.loads(path.read_text()))

    def target(self, **changes):
        return {
            "member_id": "member-1", "goal_type": "custom", "kcal_target": None,
            "protein_target_g": None, "carbs_target_g": None, "fat_target_g": None,
        } | changes

    def test_unknown_is_valid_and_fields_remain_required(self):
        self.assertTrue(self.validator.is_valid(self.target()))
        target = self.target()
        del target["fat_target_g"]
        self.assertFalse(self.validator.is_valid(target))

    def test_true_zero_macro_and_exact_fraction_are_valid(self):
        self.assertTrue(self.validator.is_valid(self.target(
            kcal_target="1600.125", protein_target_g=0, carbs_target_g="0.000",
            fat_target_g="54.321",
        )))
        self.assertTrue(self.validator.is_valid(self.target(kcal_target=2700)))

    def test_invalid_or_lossy_macro_values_are_rejected(self):
        for value in (-1, "-1", "unknown", "NaN", "1e2", "01", "0.0001",
                      "1000000", "1,2", " 1", True, 1.125):
            with self.subTest(value=value):
                self.assertFalse(self.validator.is_valid(self.target(protein_target_g=value)))

    def test_known_energy_must_be_positive(self):
        for value in (0, "0", "0.0", "0.000", -1):
            with self.subTest(value=value):
                self.assertFalse(self.validator.is_valid(self.target(kcal_target=value)))
        self.assertTrue(self.validator.is_valid(self.target(kcal_target="0.001")))


if __name__ == "__main__":
    unittest.main()
