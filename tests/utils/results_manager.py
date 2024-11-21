# tests/utils/test_results.py
from pathlib import Path
from datetime import datetime, UTC
from typing import Dict, Any, Optional
import json

class ResultsManager:
    def __init__(self):
        self.results_dir = Path(__file__).parent.parent.parent / 'results'
        self.results_dir.mkdir(exist_ok=True)
        self.timestamp = datetime.now(UTC).strftime('%Y%m%d_%H%M%S')
        self.level_results: Dict[str, Dict[str, Any]] = {}
        print(f"Results will be saved to: {self.results_dir}")

    def store_level_result(self, level: str, metrics: Dict[str, Any]) -> None:
        self.level_results[level] = metrics

    def get_level_result(self, level: str) -> Dict[str, Any]:
        return self.level_results.get(level, {})

    def save_compression_result(
        self,
        test_name: str,
        metrics: Dict[str, Any],
        expectations: Optional[Dict[str, Any]] = None,
        passed: Optional[bool] = None
    ) -> None:
        result = {
            'test_name': test_name,
            'metrics': metrics,
            'expectations': expectations if expectations is not None else {},
            'passed': passed if passed is not None else None,
            'timestamp': datetime.now(UTC).isoformat()
        }
        result_file = self.results_dir / f"compression_test_{test_name}_{self.timestamp}.json"
        print(f"Saving results to: {result_file}")
        with open(result_file, 'w') as f:
            json.dump(result, f, indent=2)
