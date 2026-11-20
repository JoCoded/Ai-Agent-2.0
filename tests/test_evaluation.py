import unittest
from evaluation.offline_eval import evaluate


class EvaluationTests(unittest.TestCase):
    def test_all_offline_fixture_contracts(self):
        result = evaluate()
        self.assertEqual(result["total"], 3)
        self.assertEqual(result["passed"], result["total"])


if __name__ == "__main__":
    unittest.main()
