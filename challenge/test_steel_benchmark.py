import io
import unittest
import zipfile

from challenge.steel_benchmark import CLASSES, parse_archive, split, run


def sample_archive():
    lines=[]
    for cls in range(7):
        for i in range(5):
            features=[float(cls*20+i+j) for j in range(27)]
            targets=[float(j==cls) for j in range(7)]
            lines.append(" ".join(str(x) for x in features+targets))
    buffer=io.BytesIO()
    with zipfile.ZipFile(buffer,"w") as z:
        z.writestr("Faults.NNA","\n".join(lines))
    return buffer.getvalue()


class SteelTests(unittest.TestCase):
    def test_parse(self):
        rows=parse_archive(sample_archive())
        self.assertEqual(len(rows),35)
        self.assertEqual(set(row["label"] for row in rows),set(CLASSES))

    def test_split_deterministic_and_disjoint(self):
        rows=parse_archive(sample_archive())
        a,b=split(rows)
        c,d=split(rows)
        self.assertEqual([x["id"] for x in a],[x["id"] for x in c])
        self.assertEqual([x["id"] for x in b],[x["id"] for x in d])
        self.assertFalse({x["id"] for x in a}&{x["id"] for x in b})

    def test_report(self):
        report=run(sample_archive())
        self.assertEqual(report["dataset_size"],35)
        self.assertEqual(report["train_count"]+report["test_count"],35)
        self.assertIsNone(report["measurements"]["energy_joules"])
        for result in report["results"].values():
            self.assertEqual(result["total"],report["test_count"])
            self.assertGreaterEqual(result["macro_f1"],0)

    def test_reject_invalid_one_hot(self):
        data=sample_archive()
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            contents=z.read("Faults.NNA").decode().splitlines()
        contents[0]=" ".join(["0"]*34)
        buffer=io.BytesIO()
        with zipfile.ZipFile(buffer,"w") as z:
            z.writestr("Faults.NNA","\n".join(contents))
        with self.assertRaisesRegex(ValueError,"one-hot"):
            parse_archive(buffer.getvalue())


if __name__=="__main__":
    unittest.main()
