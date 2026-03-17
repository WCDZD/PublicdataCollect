import unittest

from collector import classify_accession, extract_accessions, infer_data_type


class CollectorUnitTests(unittest.TestCase):
    def test_extract_accessions(self):
        text = "Data available in GSE12345 and PRJNA99999. Controlled set: EGAS00001000123"
        accessions = extract_accessions(text)
        self.assertIn("GSE12345", accessions)
        self.assertIn("PRJNA99999", accessions)
        self.assertIn("EGAS00001000123", accessions)

    def test_classify_accession(self):
        repo, downloadable, url = classify_accession("GSE12345")
        self.assertEqual(repo, "GEO")
        self.assertEqual(downloadable, "yes")
        self.assertIn("GSE12345", url)

    def test_infer_data_type(self):
        hint = infer_data_type("We used single-cell RNA-seq and whole exome sequencing")
        self.assertIn("scRNA", hint)
        self.assertIn("RNA-seq", hint)
        self.assertIn("WES", hint)


if __name__ == "__main__":
    unittest.main()
