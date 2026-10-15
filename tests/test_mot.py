import json
import tempfile
import unittest
from pathlib import Path

from dwell_mapper.config import load_store_config
from dwell_mapper.io import read_observations
from dwell_mapper.mot import MotError, prepare_mot_sequence


class MotPreparationTests(unittest.TestCase):
    def _sequence(self, root: Path) -> Path:
        sequence = root / "MOT17-TEST"
        (sequence / "gt").mkdir(parents=True)
        (sequence / "seqinfo.ini").write_text(
            "[Sequence]\nname=MOT17-TEST\nimDir=img1\nframeRate=10\n"
            "seqLength=3\nimWidth=300\nimHeight=120\nimExt=.jpg\n",
            encoding="utf-8",
        )
        (sequence / "gt" / "gt.txt").write_text(
            "1,7,10,100,20,40,1,1,1\n"
            "1,8,100,10,20,30,0,1,1\n"
            "2,7,20,20,20,40,1,1,1\n"
            "2,9,200,20,20,40,1,7,1\n",
            encoding="utf-8",
        )
        return sequence

    def test_prepares_config_observations_and_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "prepared"
            manifest = prepare_mot_sequence(str(self._sequence(root)), str(output))
            config = load_store_config(str(output / "store.json"))
            records = list(read_observations(str(output / "ground_truth.jsonl")))

            self.assertEqual(manifest["person_boxes"], 2)
            self.assertEqual(manifest["unique_tracks"], 1)
            self.assertEqual(len(config.zones), 3)
            self.assertEqual(len(records), 3)
            self.assertEqual(records[0][1][0].track_id, "7")
            self.assertEqual(records[0][1][0].y, 120.0)
            self.assertEqual(records[1][0], 0.1)
            self.assertEqual(json.loads((output / "manifest.json").read_text()), manifest)

    def test_missing_metadata_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(MotError, "metadata"):
                prepare_mot_sequence(directory, str(Path(directory) / "output"))


if __name__ == "__main__":
    unittest.main()
