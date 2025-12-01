
"""
Unit tests for the CFS calculation logic, including Admission/Followup (fFolder) handling.
Tests use the rule engine and fact mapping as in production.
"""
import unittest
import pandas as pd
import json
from Archive.cfs_rule_engine import get_patient_facts, evaluate_rules

with open('cfs_rules.json', 'r', encoding='utf-8') as f:
    RULES_DATA = json.load(f)
with open('cfs_fact.json', 'r', encoding='utf-8') as f:
    FACT_DEFINITIONS = json.load(f)

class TestCFSCalculation(unittest.TestCase):
    def test_admission_and_followup_same_facts(self):
        """
        If fFolder is not used in logic, Admission and Followup with same facts yield same CFS.
        """
        patient_id = 1
        assessment_df = pd.DataFrame({
            'PatientNum': [patient_id, patient_id],
            'Description': ['תפקוד', 'תפקוד'],
            'Question_Name': ['מצב תפקודי', 'מצב פיזי'],
            'Answer_Text': ['עצמאי', 'טוב']
        })
        for folder in ['A', 'F']:
            diagnosis_df = pd.DataFrame({'PatientNum': [patient_id], 'fFolder': [folder], 'Name': ['Hypertension']})
            facts = get_patient_facts(patient_id, assessment_df, diagnosis_df, FACT_DEFINITIONS)
            cfs_score, _, _ = evaluate_rules(facts, RULES_DATA['rules'])
            self.assertEqual(cfs_score, 2)

    def test_severely_frail_bathing(self):
        """
        Patient dependent in bathing should be CFS 7.
        """
        patient_id = 2
        assessment_df = pd.DataFrame({
            'PatientNum': [patient_id],
            'Description': ['תפקוד'],
            'Question_Name': ['מצב תפקודי'],
            'Answer_Text': ['תלות ברחצה']
        })
        diagnosis_df = pd.DataFrame({'PatientNum': [patient_id], 'fFolder': ['A'], 'Name': ['Hypertension']})
        facts = get_patient_facts(patient_id, assessment_df, diagnosis_df, FACT_DEFINITIONS)
        cfs_score, _, _ = evaluate_rules(facts, RULES_DATA['rules'])
        self.assertIn('dependent_bathing', facts['functional_status'])
        self.assertEqual(cfs_score, 7)

    def test_missing_assessment_defaults_independent(self):
        """
        Patient with no assessment data defaults to 'independent' and is scored by chronic conditions.
        """
        patient_id = 3
        assessment_df = pd.DataFrame(columns=['PatientNum', 'Description', 'Question_Name', 'Answer_Text'])
        diagnosis_df = pd.DataFrame({
            'PatientNum': [patient_id]*12,
            'fFolder': ['A']*12,
            'Name': [f'Condition_{i}' for i in range(12)]
        })
        facts = get_patient_facts(patient_id, assessment_df, diagnosis_df, FACT_DEFINITIONS)
        cfs_score, _, _ = evaluate_rules(facts, RULES_DATA['rules'])
        self.assertIn('independent', facts['functional_status'])
        self.assertEqual(facts['chronic_condition_count'], 12)
        self.assertEqual(cfs_score, 4)

    def test_fit_independent_good_health(self):
        """
        Independent patient with good health should be CFS 2.
        """
        patient_id = 4
        assessment_df = pd.DataFrame({
            'PatientNum': [patient_id, patient_id],
            'Description': ['תפקוד', 'תפקוד'],
            'Question_Name': ['מצב תפקודי', 'מצב פיזי'],
            'Answer_Text': ['עצמאי', 'טוב']
        })
        diagnosis_df = pd.DataFrame({'PatientNum': [patient_id], 'fFolder': ['A'], 'Name': ['Hypertension']})
        facts = get_patient_facts(patient_id, assessment_df, diagnosis_df, FACT_DEFINITIONS)
        cfs_score, _, _ = evaluate_rules(facts, RULES_DATA['rules'])
        self.assertIn('independent', facts['functional_status'])
        self.assertEqual(facts['health_status'], 'good')
        self.assertEqual(cfs_score, 2)

if __name__ == '__main__':
    unittest.main()
