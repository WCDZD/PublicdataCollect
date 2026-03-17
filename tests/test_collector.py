import unittest

from collector import (
    build_keywords_from_task,
    classify_accession,
    extract_accessions,
    infer_data_type,
    normalize_folder_name,
)


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

    def test_build_keywords_from_task_with_aliases(self):
        task = {
            "cancer_type": "NSCLC",
            "data_type": "scRNA",
            "search_aliases": ["NSCLC", "Non-Small Cell Lung Cancer"],
            "extra_keywords": ["tumor microenvironment"],
        }
        keywords = build_keywords_from_task(task)
        self.assertEqual(len(keywords), 2)
        self.assertIn("(NSCLC)", keywords[0])
        self.assertIn("tumor microenvironment", keywords[0])

    def test_build_keywords_from_task_keyword_groups_priority(self):
        task = {
            "cancer_type": "NSCLC",
            "data_type": "WES",
            "keyword_groups": ["(NSCLC) AND (WES)"]
        }
        keywords = build_keywords_from_task(task)
        self.assertEqual(keywords, ["(NSCLC) AND (WES)"])

    def test_normalize_folder_name(self):
        self.assertEqual(normalize_folder_name("Non Small Cell/Lung Cancer"), "Non_Small_Cell_Lung_Cancer")


if __name__ == "__main__":
    unittest.main()
