import json
import pandas as pd

# --- 1. Rule Engine Core ---

def check_condition(fact_value, operator, condition_value):
    """Checks a single condition."""
    if operator == 'equal':
        return fact_value == condition_value
    if operator == 'not_equal':
        return fact_value != condition_value
    if operator == 'in':
        return fact_value in condition_value
    if operator == 'not_in':
        return fact_value not in condition_value
    if operator == 'greater_than':
        return fact_value > condition_value
    if operator == 'less_than':
        return fact_value < condition_value
    if operator == 'greater_than_or_equal':
        return fact_value >= condition_value
    if operator == 'less_than_or_equal':
        return fact_value <= condition_value
    return False

def evaluate_rules(facts, rules):
    """
    Evaluates a set of rules against a dictionary of facts.
    Rules are processed by priority.
    """
    sorted_rules = sorted(rules, key=lambda r: r['priority'])
    
    for rule in sorted_rules:
        conditions = rule.get('conditions', {}).get('all', [])
        if not conditions: # Default rule
            return rule['result']
            
        is_match = all(
            check_condition(
                facts.get(cond['fact']), 
                cond['operator'], 
                cond['value']
            ) for cond in conditions
        )
        
        if is_match:
            return rule['result']
            
    return None # No rule matched

# --- 2. Fact Gathering ---

# Define keywords and codes for fact derivation from Diagnosis.csv
TERMINAL_ILLNESS_KEYWORDS = ['terminal', 'palliative', 'hospice', 'end-stage']
TERMINAL_ILLNESS_ICD9 = [] 

# --- NEW: Mapping for Cleaned_Assessment.csv ---
# Maps Hebrew terms from the assessment file to the facts required by the rule engine.
# We assume any answer other than 'עצמאי' (Independent) means the patient needs help.
ASSESSMENT_MAPPING = {
    # Description: 'תפקוד יומיומי' (Daily Functioning)
    'רחצה': {'type': 'badl'},          # Bathing
    'הלבשה': {'type': 'badl'},         # Dressing
    'אכילה': {'type': 'badl'},         # Eating
    'ניידות': {'type': 'badl'},         # Mobility/Walking
    'מעברים': {'type': 'badl'},        # Transfers (bed/chair)
    'שירותים': {'type': 'badl'},       # Toileting
    
    'ניהול כספים': {'type': 'iadl'},    # Managing finances
    'שימוש בתחבורה': {'type': 'iadl'}, # Using transportation
    'עבודות בית': {'type': 'iadl'},    # Housework
    'נטילת תרופות': {'type': 'iadl'}, # Taking medication
    'קניות': {'type': 'iadl'},          # Shopping
    'הכנת ארוחות': {'type': 'iadl'},   # Meal preparation

    # These might be under a different 'Description', adjust as needed.
    # Description: 'הערכה כללית' (General Assessment) or similar
    'הערכת מצב בריאות': {
        'type': 'self_rated_health',
        'value_map': { # Translate Hebrew answers to English for the rule engine
            'טוב מאוד': 'Excellent',
            'טוב': 'Good',
            'בינוני': 'Fair',
            'גרוע': 'Poor'
        }
    },
    # The questions for 'effort' and 'activity' are assumptions.
    # Please verify if they exist in your data.
    'תחושת מאמץ': {
        'type': 'effort_level',
        'value_map': {
            'כל הזמן': 'All of the time',
            'לפעמים': 'Sometimes/Occasionally',
            'כמעט ואף פעם': 'Rarely/Never'
        }
    },
    'פעילות גופנית': {
        'type': 'is_active',
        'positive_answer': 'כן' # Yes
    }
}
INDEPENDENT_ANSWER = 'עצמאי'


def get_patient_facts(patient_id, diagnosis_df, assessment_df):
    """
    Gathers all relevant facts for a patient into a single dictionary.
    """
    # --- Default facts ---
    facts = {
        'is_terminally_ill': False, 'badl_count': 0, 'iadl_count': 0,
        'chronic_condition_count': 0, 'self_rated_health': None,
        'effort_level': None, 'is_active': False
    }

    # --- Derive facts from Diagnosis data ---
    patient_diagnoses = diagnosis_df[diagnosis_df['PatientNum'] == patient_id]
    if patient_diagnoses.empty:
        return None # No data for this patient

    background_diagnoses = patient_diagnoses[patient_diagnoses['fFolder'] == 'X']
    facts['chronic_condition_count'] = background_diagnoses['Name'].nunique()

    diagnoses_text = ' '.join(patient_diagnoses['Name'].dropna().astype(str)).lower()
    if any(keyword in diagnoses_text for keyword in TERMINAL_ILLNESS_KEYWORDS):
        facts['is_terminally_ill'] = True
    
    # --- Derive facts from Assessment data ---
    if assessment_df is not None:
        patient_assessments = assessment_df[assessment_df['PatientNum'] == patient_id]
        
        for _, row in patient_assessments.iterrows():
            q_name = row['Question_Name']
            answer = row['Answer_Text']
            
            if q_name in ASSESSMENT_MAPPING:
                mapping = ASSESSMENT_MAPPING[q_name]
                q_type = mapping['type']

                if q_type == 'badl' and answer != INDEPENDENT_ANSWER:
                    facts['badl_count'] += 1
                elif q_type == 'iadl' and answer != INDEPENDENT_ANSWER:
                    facts['iadl_count'] += 1
                elif q_type == 'is_active':
                    facts['is_active'] = (answer == mapping['positive_answer'])
                elif q_type == 'self_rated_health':
                    facts['self_rated_health'] = mapping['value_map'].get(answer)
                elif q_type == 'effort_level':
                    facts['effort_level'] = mapping['value_map'].get(answer)

    return facts

# --- 3. Main Execution ---

def load_rules(filepath='cfs_rules.json'):
    """Loads rules from a JSON file."""
    try:
        with open(filepath, 'r') as f:
            return json.load(f)['rules']
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error loading rules file: {e}")
        return None

def load_data(diagnosis_path='Diagnosis.csv', assessment_path='Cleaned_Assessment.csv'):
    """Loads and prepares all necessary data."""
    try:
        diagnosis_df = pd.read_csv(diagnosis_path)
        assessment_df = pd.read_csv(assessment_path)
        return diagnosis_df, assessment_df
    except FileNotFoundError as e:
        print(f"Error loading data: {e}")
        return None, None

if __name__ == '__main__':
    rules = load_rules()
    diagnosis_df, assessment_df = load_data()

    if rules and diagnosis_df is not None and assessment_df is not None:
        patient_ids = diagnosis_df['PatientNum'].unique()
        
        results = {}
        # Example: Calculate for patient 640001
        patient_id_to_test = 640001
        if patient_id_to_test in patient_ids:
            facts = get_patient_facts(patient_id_to_test, diagnosis_df, assessment_df)
            if facts:
                cfs_score = evaluate_rules(facts, rules)
                results[patient_id_to_test] = {
                    'CFS_Score': cfs_score,
                    'Facts': facts
                }
        
        print("CFS Calculation Results:")
        print(json.dumps(results, indent=2, ensure_ascii=False))
