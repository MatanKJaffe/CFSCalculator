
import pandas as pd
from typing import Any, Dict, List, Optional, Union
from tqdm import tqdm


class FactMappings:
    """
    This class holds all the mappings that were previously in cfs_fact.json.
    Making them class variables makes them accessible without instantiation.
    """
    FACT_MAPPING = {
        "תפקוד": {
            "מצב תפקודי": {
                "type": "functional_status",
                "value_map": {
                    "עצמאי": "independent",
                    "תלות ברחצה": "dependent_bathing",
                    "תלות באכילה": "dependent_eating",
                    "תלות בהכנת אוכל/בישול": "dependent_cooking",
                    "תלות בקניות": "dependent_shopping",
                    "תלות בהסעות": "dependent_transportation",
                    "תלות בלקיחת תרופות": "dependent_medication",
                    "תלות בטיפול בכספים": "dependent_finances"
                }
            },
            "מצב פיזי": {
                "type": "health_status",
                "value_map": {
                    "טוב": "good",
                    "סביר": "fair",
                    "לא טוב": "poor",
                    "רע": "very_poor"
                }
            },
            "מצב פיזי נורטון": {
                "type": "health_status",
                "value_map": {
                    "טוב": "good",
                    "סביר": "fair",
                    "לא טוב": "poor",
                    "רע": "very_poor"
                }
            }
        },
        "אמדן וזיהוי צרכים": {
            "מצב פיזי": {
                "type": "health_status",
                "value_map": {
                    "טוב": "good",
                    "סביר": "fair",
                    "לא טוב": "poor",
                    "רע": "very_poor"
                }
            },
            "מצב פיזי נורטON": {
                "type": "health_status",
                "value_map": {
                    "טוב": "good",
                    "סביר": "fair",
                    "לא טוב": "poor",
                    "רע": "very_poor"
                }
            }
        },
        "הזנה": {
            "מצב פיזי": {
                "type": "health_status",
                "value_map": {
                    "טוב": "good",
                    "סביר": "fair",
                    "לא טוב": "poor",
                    "רע": "very_poor"
                }
            },
            "מצב פיזי נורטון": {
                "type": "health_status",
                "value_map": {
                    "טוב": "good",
                    "סביר": "fair",
                    "לא טוב": "poor",
                    "רע": "very_poor"
                }
            }
        },
        "נשימה": {
            "קוצר נשימה": {
                "type": "symptoms",
                "value_map": {
                    "כן": "shortness_of_breath"
                }
            }
        },
        "כאב": {
            "כאב": {
                "type": "symptoms",
                "value_map": {
                    "כן": "has_pain"
                }
            }
        },
        "אוכלוסיה בסיכון": {
            "מצב קוגניטיבי": {
                "type": "cognitive_status",
                "value_map": {
                    "מתמצא (בזמן, במקום, באנשים)": "oriented",
                    "אינו מתמצא במקום": "disoriented_place",
                    "אינו מתמצא בזמן": "disoriented_time",
                    "אינו מתמצא באנשים": "disoriented_people"
                }
            },
            "מצב הכרה": {
                "type": "consciousness_status",
                "value_map": {
                    "בהכרה": "conscious",
                    "בלבול קל": "mild_confusion",
                    "ערפול": "stupor",
                    "חוסר הכרה": "unconscious"
                }
            }
        }
    }
    DIAGNOSIS_MAPPING = {
        "has_dementia": ["DEMENTIA", "ALZHEIMER'S DISEASE"],
        "has_heart_failure": ["CONGESTIVE HEART FAILURE", "CHF"],
        "has_renal_failure": ["RENAL FAILURE", "CHRONIC KIDNEY DISEASE"],
        "has_copd": ["COPD", "CHRONIC OBSTRUCTIVE PULMONARY DISEASE"],
        "has_cancer": ["CANCER", "MALIGNANCY", "LYMPHOMA", "LEUKEMIA"],
        "has_stroke": ["CEREBROVASCULAR ACCIDENT", "CVA", "STROKE"]
    }
    ACUTE_DIAGNOSIS_KEYWORDS = {
        "very_poor": ["SEPSIS", "SHOCK", "ACUTE RENAL FAILURE", "RENAL FAILURE ACUTE", "PNEUMONIA", "PULMONARY EMBOLISM"]
    }
    CHRONIC_DISEASE_THRESHOLD = 5
    TERMINAL_ILLNESS_KEYWORDS = [
        "terminal",
        "palliative",
        "hospice",
        "end-stage"
    ]


class ResultNode:
    """Represents a leaf node in the decision tree, holding a CFS result."""
    def __init__(self, score: int, description: str):
        self.score = score
        self.description = description

    def evaluate(self, facts: Dict[str, Any]) -> "ResultNode":
        """Evaluation of a result node simply returns itself."""
        return self


class DecisionNode:
    """Represents a decision point in the tree."""
    def __init__(self, condition_fact: str, condition_operator: str, condition_value: Any, yes_node: Union["DecisionNode", ResultNode], no_node: Union["DecisionNode", ResultNode]):
        self.condition_fact = condition_fact
        self.condition_operator = condition_operator
        self.condition_value = condition_value
        self.yes_node = yes_node
        self.no_node = no_node

    def evaluate(self, facts: Dict[str, Any]) -> ResultNode:
        """Evaluates the patient's facts against the condition and traverses down the tree."""
        fact_value = facts.get(self.condition_fact)

        if self._check_condition(fact_value):
            return self.yes_node.evaluate(facts)
        else:
            return self.no_node.evaluate(facts)

    def _check_condition(self, fact_value: Any) -> bool:
        """Checks if the given fact value satisfies the node's condition."""
        if fact_value is None:
            return False
            
        if self.condition_operator == "equal":
            return fact_value == self.condition_value
        if self.condition_operator == "greater_than_or_equal":
            return fact_value >= self.condition_value
        if self.condition_operator == "in_range":
            return self.condition_value[0] <= fact_value <= self.condition_value[1]
        if self.condition_operator == "in":
            return fact_value in self.condition_value
        
        raise ValueError(f"Unsupported operator: {self.condition_operator}")


class CFSCalculator:
    def print_logic(self):
        """
        Prints a mermaid markdown diagram of the CFS decision tree logic.
        """
        print(f"""```mermaid\n{self._generate_mermaid(self.decision_tree)}\n```""")

    def _generate_mermaid(self, node, parent=None, parent_label=None, node_id=None, lines=None):
        """
        Recursively generates mermaid flowchart code for the decision tree.
        """
        if node_id is None:
            node_id = [0]
        if lines is None:
            lines = ["flowchart TD"]
        nid = f"N{node_id[0]}"
        node_id[0] += 1
        if isinstance(node, ResultNode):
            label = f"CFS {node.score}: {node.description}"
            lines.append(f"    {nid}[\"{label}\"]")
        else:
            cond = f"{node.condition_fact} {node.condition_operator} {node.condition_value}"
            lines.append(f"    {nid}{{{cond}}}")
            # Yes branch
            yes_id = self._generate_mermaid(node.yes_node, nid, 'Yes', node_id, lines)
            lines.append(f"    {nid} -- Yes --> {yes_id}")
            # No branch
            no_id = self._generate_mermaid(node.no_node, nid, 'No', node_id, lines)
            lines.append(f"    {nid} -- No --> {no_id}")
        return '\n'.join(lines) if parent is None else nid
    def __init__(self):
        self.decision_tree = self._build_decision_tree()

    def _build_decision_tree(self) -> DecisionNode:
        """Builds the CFS decision tree using DecisionNode and ResultNode objects."""
        
        # Leaf nodes (results)
        cfs_1 = ResultNode(1, "Very Fit")
        cfs_2 = ResultNode(2, "Fit")
        cfs_3 = ResultNode(3, "Managing Well")
        cfs_4 = ResultNode(4, "Living with Very Mild Frailty")
        cfs_5 = ResultNode(5, "Living with Mild Frailty")
        cfs_6 = ResultNode(6, "Living with Moderate Frailty")
        cfs_7 = ResultNode(7, "Living with Severe Frailty")
        cfs_8 = ResultNode(8, "Living with Very Severe Frailty, Totally Dependent")
        cfs_9 = ResultNode(9, "Terminally Ill")

        # Decision branches, built from the bottom up for clarity
        
        engages_activity_no_for_fit = DecisionNode("engages_in_strenuous_activity", "equal", False, cfs_2, cfs_1)
        fit_or_very_fit_branch = DecisionNode("effort_to_perform_tasks", "equal", "rarely_never", engages_activity_no_for_fit, cfs_4) # Simplified this branch

        engages_activity_no_for_managing = DecisionNode("engages_in_strenuous_activity", "equal", False, cfs_3, cfs_2)
        managing_well_branch = DecisionNode("effort_to_perform_tasks", "equal", "sometimes_occasionally", engages_activity_no_for_managing, fit_or_very_fit_branch)
        
        health_branch = DecisionNode("self_rated_health", "in", ["Fair", "Poor"], cfs_4, managing_well_branch)
        
        chronic_condition_branch = DecisionNode("chronic_condition_count", "greater_than_or_equal", 10, cfs_4, health_branch)
        
        iadl_range_branch = DecisionNode("iadl_count", "in_range", [1, 4], cfs_5, cfs_6)
        iadl_branch = DecisionNode("iadl_count", "greater_than_or_equal", 1, iadl_range_branch, chronic_condition_branch)

        badl_1_2_branch = DecisionNode("badl_count", "in_range", [1, 2], cfs_6, iadl_branch)
        
        badl_3_5_branch = DecisionNode("badl_count", "in_range", [3, 5], cfs_8, cfs_7) # if not 3-5, must be > 5
        badl_branch = DecisionNode("badl_count", "greater_than_or_equal", 3, badl_3_5_branch, badl_1_2_branch)
        
        root = DecisionNode("is_terminally_ill", "equal", True, cfs_9, badl_branch)
        
        return root

    def get_patient_facts(self, patient_data: pd.Series, diagnosis_data: pd.DataFrame) -> Dict[str, Any]:
        """
        Processes a patient's raw data and diagnosis to generate a dictionary of facts.
        This method is a refactoring of the original get_patient_facts function.
        """
        facts: Dict[str, Any] = {}

        # 1. Extract facts from the main patient assessment data
        self._extract_assessment_facts(patient_data, facts)
        
        # 2. Extract facts from the diagnosis data
        self._extract_diagnosis_facts(patient_data['PatientNum'], diagnosis_data, facts)
        
        # 3. Derive complex facts
        self._derive_complex_facts(facts)

        return facts

    def _extract_assessment_facts(self, patient_data: pd.Series, facts: Dict[str, Any]):
        """Extracts facts from the patient's assessment row."""
        for category, questions in FactMappings.FACT_MAPPING.items():
            for question, mapping in questions.items():
                if question in patient_data and pd.notna(patient_data[question]):
                    fact_type = mapping['type']
                    value = mapping['value_map'].get(patient_data[question])
                    if value:
                        if fact_type not in facts:
                            facts[fact_type] = []
                        if value not in facts[fact_type]:
                            facts[fact_type].append(value)
        
        # Flatten single-item lists
        for fact, value in facts.items():
            if isinstance(value, list) and len(value) == 1:
                facts[fact] = value[0]


    def _extract_diagnosis_facts(self, patient_id: int, diagnosis_data: pd.DataFrame, facts: Dict[str, Any]):
        """Extracts facts from the patient's diagnoses."""
        patient_diagnoses = diagnosis_data[diagnosis_data['PatientNum'] == patient_id]
        if patient_diagnoses.empty:
            facts['chronic_condition_count'] = 0
            facts['is_terminally_ill'] = False
            return
            
        # Get encounter type (Admission 'A' or Follow-up 'F')
        if 'fFolder' in patient_diagnoses.columns and not patient_diagnoses['fFolder'].empty:
            facts['encounter_type'] = patient_diagnoses['fFolder'].iloc[0]

        diagnoses_list = patient_diagnoses['Name'].str.upper().tolist()
        
        # Check for terminal illness
        facts['is_terminally_ill'] = any(keyword in diag for diag in diagnoses_list for keyword in FactMappings.TERMINAL_ILLNESS_KEYWORDS)

        # Count chronic conditions based on mappings
        chronic_conditions = 0
        for fact_name, keywords in FactMappings.DIAGNOSIS_MAPPING.items():
            if any(keyword in diag for diag in diagnoses_list for keyword in keywords):
                facts[fact_name] = True
                chronic_conditions += 1
        facts['chronic_condition_count'] = chronic_conditions

    def _derive_complex_facts(self, facts: Dict[str, Any]):
        """Derives BADL and IADL counts from functional_status."""
        functional_status = facts.get('functional_status', [])
        if not isinstance(functional_status, list):
            functional_status = [functional_status]

        badl_dependencies = ["dependent_bathing", "dependent_eating", "dependent_dressing", "dependent_transferring", "dependent_toileting"]
        iadl_dependencies = ["dependent_cooking", "dependent_shopping", "dependent_transportation", "dependent_finances", "dependent_medication"]

        facts['badl_count'] = sum(1 for dep in badl_dependencies if dep in functional_status)
        facts['iadl_count'] = sum(1 for dep in iadl_dependencies if dep in functional_status)
        
        # Set defaults if not present
        facts.setdefault('engages_in_strenuous_activity', False) # Default to 'No'
        facts.setdefault('effort_to_perform_tasks', "not_specified")
        facts.setdefault('encounter_type', 'A') # Default to Admission


    def calculate(self, patient_data: pd.Series, diagnosis_data: pd.DataFrame) -> Dict[str, Any]:
        """
        Calculates the CFS score for a single patient.
        """
        patient_facts = self.get_patient_facts(patient_data, diagnosis_data)
        result_node = self.decision_tree.evaluate(patient_facts)
        return {
            "PatientNum": patient_data['PatientNum'],
            "cfs_score": result_node.score,
            "cfs_description": result_node.description,
            "facts": patient_facts}


if __name__ == '__main__':
    # This block makes the script runnable
    print("Starting CFS Calculation...")

    try:
        assessment_df = pd.read_csv('INPUT/Cleaned_Assessment.csv')
        diagnosis_df = pd.read_csv('INPUT/Diagnosis.csv')
    except FileNotFoundError as e:
        print(f"Error: Input file not found. Make sure 'INPUT/Cleaned_Assessment.csv' and 'INPUT/Diagnosis.csv' exist.")
        print(e)
        exit()

    calculator = CFSCalculator()
    
    results = []
    for index, patient_row in tqdm(assessment_df.iterrows(), total=assessment_df.shape[0], desc="Processing Patients"):
        result = calculator.calculate(patient_row, diagnosis_df)
        results.append(result)

    results_df = pd.DataFrame(results)
    
    # Reorder columns for clarity
    final_columns = ['PatientNum', 'cfs_score', 'cfs_description', 'facts']
    results_df = results_df[final_columns]
    
    results_df.to_csv('OUTPUT/CFS_Results.csv', index=False, encoding='utf-8-sig')

    print("\nCFS Calculation Complete.")
    print(f"Results saved to 'OUTPUT/CFS_Results.csv'")
    print("\nSample of Results:")
    print(results_df.head())
