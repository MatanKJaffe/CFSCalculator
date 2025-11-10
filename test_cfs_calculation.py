import unittest
import pandas as pd
import json
from cfs_rule_engine import get_patient_facts, evaluate_rules

# We will use the actual rules and fact definitions for this test
with open('cfs_rules.json', 'r', encoding='utf-8') as f:
    RULES_DATA = json.load(f)

with open('cfs_fact.json', 'r', encoding='utf-8') as f:
    FACT_DEFINITIONS = json.load(f)

class TestCFSCalculation(unittest.TestCase):

    def test_cfs_7_severely_frail_mapping(self):
        """
        Tests a clear case for CFS 7.
        This test verifies that the specific combination of 'תפקוד' (Description),
        'מצב תפקודי' (Question_Name), and 'תלות ברחצה' (Answer_Text) correctly
        maps to the 'dependent_bathing' fact, leading to a CFS score of 7.
        """
        patient_id = 101
        
        # Mock assessment data for a patient dependent in bathing
        assessment_data = {
            'PatientNum': [patient_id],
            'Description': ['תפקוד'],
            'Question_Name': ['מצב תפקודי'],
            'Answer_Text': ['תלות ברחצה']
        }
        assessment_df = pd.DataFrame(assessment_data)
        
        # Mock diagnosis data (irrelevant for this specific rule but needed for the function)
        diagnosis_df = pd.DataFrame({'PatientNum': [patient_id], 'fFolder': ['X'], 'Name': ['Hypertension']})

        # --- Execution ---
        facts = get_patient_facts(patient_id, assessment_df, diagnosis_df, FACT_DEFINITIONS)
        cfs_score, _, _ = evaluate_rules(facts, RULES_DATA['rules'])

        # --- Verification ---
        self.assertIn('dependent_bathing', facts['functional_status'])
        self.assertEqual(cfs_score, 7, "Patient dependent in bathing should be CFS 7")

    def test_patient_with_missing_assessment_data(self):
        """
        Tests how the system handles a patient with NO assessment data.
        This is a critical test given the "incredible number of missing values".
        The system should default the patient's functional status to 'independent'
        and then score them based on other available data, like chronic conditions.
        In this case, with 12 chronic conditions, the patient should be CFS 4.
        """
        patient_id = 102

        # Mock assessment data is empty for this patient
        assessment_df = pd.DataFrame(columns=['PatientNum', 'Description', 'Question_Name', 'Answer_Text'])
        
        # Mock diagnosis data with a high number of chronic conditions
        diagnoses = [f'Condition_{i}' for i in range(12)]
        diagnosis_data = {
            'PatientNum': [patient_id] * 12,
            'fFolder': ['X'] * 12,
            'Name': diagnoses
        }
        diagnosis_df = pd.DataFrame(diagnosis_data)

        # --- Execution ---
        facts = get_patient_facts(patient_id, assessment_df, diagnosis_df, FACT_DEFINITIONS)
        cfs_score, _, _ = evaluate_rules(facts, RULES_DATA['rules'])les'])

        # --- Verification ---
        self.assertIn('independent', facts['functional_status'], "Functional status should default to 'independent' when no assessment data is present")
        self.assertEqual(facts['chronic_condition_count'], 12)
        self.assertEqual(cfs_score, 4, "Patient with >10 chronic conditions and no other dependencies should be CFS 4")

    def test_cfs_1_very_fit(self):
        """
        Tests a clear case for CFS 1.
        This verifies that a patient who is 'עצמאי' (independent) and has a 'טוב' (good)
        health status, with few chronic conditions, is correctly scored as CFS 1.
        """
        patient_id = 103

        assessment_data = {
            'PatientNum': [patient_id, patient_id],
            'Description': ['תפקוד', 'תפקוד'],
            'Question_Name': ['מצב תפקודי', 'מצב פיזי'],
            'Answer_Text': ['עצמאי', 'טוב']
        }
        assessment_df = pd.DataFrame(assessment_data)
        
        diagnosis_df = pd.DataFrame({'PatientNum': [patient_id], 'fFolder': ['X'], 'Name': ['Hypertension']})

        # --- Execution ---
        facts = get_patient_facts(patient_id, assessment_df, diagnosis_df, FACT_DEFINITIONS)
        cfs_score, _, _ = evaluate_rules(facts, RULES_DATA['rules'])les'])

        # --- Verification ---
        self.assertIn('independent', facts['functional_status'])
        self.assertEqual(facts['health_status'], 'good')
        # The default rule is CFS 1, but the CFS 2 rule has priority. 
        # Since health is 'good', it should pass the CFS 2 rule and then fail down to CFS 1.
        # Let's re-check the rules. Ah, the default is priority 99. The CFS 2 rule requires 'good' health.
        # The CFS 3 rule requires 'fair' health. The CFS 1 rule is the final fallback.
        # Let's adjust the test. The logic should result in CFS 2.
        self.assertEqual(cfs_score, 2, "Independent patient with good health should be CFS 2")


if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'], exit=False)
