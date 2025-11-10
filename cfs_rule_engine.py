import json
import pandas as pd

# --- 1. Rule Engine Core ---
def check_condition(fact_value, operator, condition_value):
    """Checks a single condition against a fact's value."""
    if operator == 'equal':
        return fact_value == condition_value
    if operator == 'in':
        return fact_value in condition_value
    if operator == 'greater_than_or_equal':
        return fact_value is not None and fact_value >= condition_value

    # List-based operators
    if operator == 'contains':
        return isinstance(fact_value, list) and condition_value in fact_value
    if operator == 'not_contains':
        return isinstance(fact_value, list) and condition_value not in fact_value
    if operator == 'contains_any':
        return isinstance(fact_value, list) and any(item in fact_value for item in condition_value)
    if operator == 'contains_all':
        return isinstance(fact_value, list) and all(item in fact_value for item in condition_value)

    return False

def evaluate_rules(facts, rules):
    """
    Evaluates a set of rules against a dictionary of facts.
    Rules are processed by priority.
    """
    sorted_rules = sorted(rules, key=lambda r: r['priority'])

    for rule in sorted_rules:
        # Check 'all' conditions
        all_conditions = rule.get('conditions', {}).get('all', [])
        all_match = all(
            check_condition(facts.get(cond['fact']), cond['operator'], cond['value']) 
            for cond in all_conditions
        ) if all_conditions else True

        # Check 'any' conditions
        any_conditions = rule.get('conditions', {}).get('any', [])
        any_match = any(
            check_condition(facts.get(cond['fact']), cond['operator'], cond['value'])
            for cond in any_conditions
        ) if any_conditions else False

        # If there are 'any' conditions, they must be met. If only 'all', it must be met.
        if (any_conditions and any_match and all_match) or (not any_conditions and all_match):
            return rule['result']
    return None # No rule matched

# --- 2. Fact Gathering ---
def get_patient_facts(patient_id, diagnosis_df, assessment_df, fact_definitions):
    """
    Gathers all relevant facts for a patient into a single dictionary.
    """
    FACT_MAPPING = fact_definitions.get("FACT_MAPPING", {})
    DIAGNOSIS_MAPPING = fact_definitions.get("DIAGNOSIS_MAPPING", {})
    TERMINAL_ILLNESS_KEYWORDS = fact_definitions.get("TERMINAL_ILLNESS_KEYWORDS", [])
    CHRONIC_DISEASE_THRESHOLD = fact_definitions.get("CHRONIC_DISEASE_THRESHOLD", 5)

    # --- Initialize facts with default values and list structures ---
    facts = {
        'functional_status': [],
        'health_status': None,
        'cognitive_status': [],
        'consciousness_status': None,
        'is_terminally_ill': False,
        'chronic_condition_count': 0
    }
    # Initialize boolean facts for specific diagnoses
    for fact_name in DIAGNOSIS_MAPPING.keys():
        facts[fact_name] = False

    # --- Derive facts from Assessment data ---
    if assessment_df is not None:
        patient_assessments = assessment_df[assessment_df['PatientNum'] == patient_id]
        for _, row in patient_assessments.iterrows():
            desc = row['Description']
            q_name = row['Question_Name']
            answer = row['Answer_Text']

            if desc in FACT_MAPPING and q_name in FACT_MAPPING[desc]:
                mapping = FACT_MAPPING[desc][q_name]
                fact_type = mapping['type']

                if answer in mapping['value_map']:
                    mapped_value = mapping['value_map'][answer]

                    # Handle list-based facts
                    if isinstance(facts.get(fact_type), list):
                        if mapped_value not in facts[fact_type]:
                            facts[fact_type].append(mapped_value)
                    # Handle single-value facts (overwrite with new value)
                    else:
                        facts[fact_type] = mapped_value

    # --- Derive facts from Diagnosis data ---
    patient_diagnoses = diagnosis_df[diagnosis_df['PatientNum'] == patient_id]
    if not patient_diagnoses.empty:
        background_diagnoses = patient_diagnoses[patient_diagnoses['fFolder'] == 'X']
        facts['chronic_condition_count'] = background_diagnoses['Name'].nunique()

        diagnoses_text = ' '.join(patient_diagnoses['Name'].dropna().astype(str)).lower()
        if any(keyword in diagnoses_text for keyword in TERMINAL_ILLNESS_KEYWORDS):
            facts['is_terminally_ill'] = True

        # Check for specific diagnoses from the mapping
        for fact_name, keywords in DIAGNOSIS_MAPPING.items():
            for keyword in keywords:
                if patient_diagnoses['Name'].str.contains(keyword, case=False, na=False).any():
                    facts[fact_name] = True
                    break # Move to the next fact once a match is found

    # If after all assessments, functional_status is empty, patient is independent
    if not facts['functional_status']:
        facts['functional_status'].append('independent')

    return facts

# --- 3. Main Execution ---
def load_json_file(filepath):
    """Loads a JSON file with UTF-8 encoding."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error loading file {filepath}: {e}")
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
    rules_data = load_json_file('cfs_rules.json')
    fact_definitions = load_json_file('cfs_fact.json')
    diagnosis_df, assessment_df = load_data()

    if rules_data and fact_definitions and diagnosis_df is not None and assessment_df is not None:
        rules = rules_data.get('rules', [])
        patient_ids = pd.unique(pd.concat([diagnosis_df['PatientNum'], assessment_df['PatientNum']]))

        output_data = []
        print(f"Processing {len(patient_ids)} unique patients...")

        # Define the columns for the output CSV
        output_columns = [
            'PatientNum', 'CFS_Score', 'Functional_Status', 'Health_Status', 
            'Cognitive_Status', 'Consciousness_Status', 'Is_Terminally_Ill', 
            'Chronic_Condition_Count'
        ]
        # Add specific diagnosis columns dynamically
        if fact_definitions.get("DIAGNOSIS_MAPPING"):
            output_columns.extend(fact_definitions["DIAGNOSIS_MAPPING"].keys())

        # Calculate for all unique patients
        for patient_id in patient_ids:
            facts = get_patient_facts(patient_id, diagnosis_df, assessment_df, fact_definitions)
            cfs_score = evaluate_rules(facts, rules)

            # Prepare data for output
            patient_output = {
                'PatientNum': str(patient_id),
                'CFS_Score': cfs_score,
                'Functional_Status': ', '.join(facts.get('functional_status', [])),
                'Health_Status': facts.get('health_status'),
                'Cognitive_Status': ', '.join(facts.get('cognitive_status', [])),
                'Consciousness_Status': facts.get('consciousness_status'),
                'Is_Terminally_Ill': facts.get('is_terminally_ill', False),
                'Chronic_Condition_Count': facts.get('chronic_condition_count', 0)
            }
            # Add specific diagnosis facts to the output
            if fact_definitions.get("DIAGNOSIS_MAPPING"):
                for fact_name in fact_definitions["DIAGNOSIS_MAPPING"].keys():
                    patient_output[fact_name] = facts.get(fact_name, False)

            output_data.append(patient_output)

        # Convert to DataFrame and save to CSV
        if output_data:
            results_df = pd.DataFrame(output_data, columns=output_columns)
            results_df.to_csv('CFS_Results.csv', index=False)
            print("Processing complete. Results saved to CFS_Results.csv")
        else:
            print("No data was processed.")

    else:
        print("Could not run processing due to errors in loading data or definition files.")
