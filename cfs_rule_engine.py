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
        # A rule with no conditions is a default rule.
        is_match = (not any_conditions and all_match) or \
                   (any_conditions and any_match and (not all_conditions or all_match)) or \
                   (not any_conditions and not all_conditions)


        if is_match:
            result = rule.get('result')
            if result and isinstance(result, dict):
                return result.get('score'), result.get('description'), rule
    return None, "No Matching Rule", None # No rule matched

# --- 2. Fact Gathering ---
def get_patient_facts(patient_id, assessment_df, diagnosis_df, fact_definitions):
    """
    Gathers all relevant facts for a patient into a single dictionary.
    """
    FACT_MAPPING = fact_definitions.get("FACT_MAPPING", {})
    DIAGNOSIS_MAPPING = fact_definitions.get("DIAGNOSIS_MAPPING", {})
    ACUTE_DIAGNOSIS_KEYWORDS = fact_definitions.get("ACUTE_DIAGNOSIS_KEYWORDS", {})
    TERMINAL_ILLNESS_KEYWORDS = fact_definitions.get("TERMINAL_ILLNESS_KEYWORDS", [])
    CHRONIC_DISEASE_THRESHOLD = fact_definitions.get("CHRONIC_DISEASE_THRESHOLD", 5)

    # --- Initialize facts with default values and list structures ---
    facts = {
        'functional_status': [],
        'health_status': None,
        'cognitive_status': [],
        'consciousness_status': None,
        'symptoms': [],
        'is_terminally_ill': False,
        'chronic_condition_count': 0
    }
    # Initialize boolean facts for specific diagnoses
    for fact_name in DIAGNOSIS_MAPPING.keys():
        facts[fact_name] = False

    # --- Tier 1: Derive facts from Assessment data (Explicit Health Status & Symptoms) ---
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
                    
                    # Handle list-based facts (functional_status, cognitive_status, symptoms)
                    if isinstance(facts.get(fact_type), list):
                        if mapped_value not in facts[fact_type]:
                            facts[fact_type].append(mapped_value)
                    # Handle single-value facts (health_status, consciousness_status)
                    # We only overwrite if the current value is None, giving priority
                    elif facts.get(fact_type) is None:
                        facts[fact_type] = mapped_value
    
    # --- Tier 2 & 3: Derive facts from Diagnosis data and Infer Health Status ---
    if diagnosis_df is not None:
        patient_diagnoses = diagnosis_df[diagnosis_df['PatientNum'] == patient_id]
        if not patient_diagnoses.empty:
            # Get all diagnoses for the patient
            all_patient_diagnoses = patient_diagnoses['Name'].dropna().astype(str).str.upper().tolist()

            # Chronic condition count (from background diagnoses)
            background_diagnoses = patient_diagnoses[patient_diagnoses['fFolder'] == 'X']
            facts['chronic_condition_count'] = background_diagnoses['Name'].nunique()

            # Check for terminal illness
            diagnoses_text_lower = ' '.join(all_patient_diagnoses).lower()
            if any(keyword in diagnoses_text_lower for keyword in TERMINAL_ILLNESS_KEYWORDS):
                facts['is_terminally_ill'] = True
                
            # Check for specific chronic diagnoses from the mapping
            for fact_name, keywords in DIAGNOSIS_MAPPING.items():
                for keyword in keywords:
                    if any(keyword in dx for dx in all_patient_diagnoses):
                        facts[fact_name] = True
                        break 
            
            # Tier 2: Infer 'very_poor' health from severe acute diagnoses
            if facts['health_status'] is None:
                very_poor_keywords = ACUTE_DIAGNOSIS_KEYWORDS.get('very_poor', [])
                for keyword in very_poor_keywords:
                    if any(keyword in dx for dx in all_patient_diagnoses):
                        facts['health_status'] = 'very_poor'
                        break
    
    # Tier 3: Infer 'poor' or 'fair' health from symptoms if status is still unknown
    if facts['health_status'] is None:
        if 'shortness_of_breath' in facts['symptoms']:
            facts['health_status'] = 'poor'
        elif 'has_pain' in facts['symptoms']:
            facts['health_status'] = 'fair'

    # If after all assessments, functional_status is empty, patient is independent
    if not facts['functional_status']:
        facts['functional_status'].append('independent')

    return facts

# --- 3. Main Execution ---
def load_json_file(filepath):
    """Loads a JSON file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error loading {filepath}: {e}")
        return None

def load_data(filepath):
    """Loads data from a CSV file."""
    try:
        return pd.read_csv(filepath)
    except FileNotFoundError:
        print(f"Error: {filepath} not found.")
        return None

def main():
    """
    Main function to execute the CFS calculation process.
    """
    # --- Configuration ---
    RULES_FILE = 'cfs_rules.json'
    FACT_DEFINITIONS_FILE = 'cfs_fact.json'
    ASSESSMENT_FILE = 'Cleaned_Assessment.csv'
    DIAGNOSIS_FILE = 'Diagnosis.csv'
    OUTPUT_FILE = 'CFS_Results.csv'

    # --- Loading ---
    rules_data = load_json_file(RULES_FILE)
    rules = rules_data.get('rules', []) if rules_data else []
    fact_definitions = load_json_file(FACT_DEFINITIONS_FILE)
    assessment_df = load_data(ASSESSMENT_FILE)
    diagnosis_df = load_data(DIAGNOSIS_FILE)

    if not rules or not fact_definitions or assessment_df is None or diagnosis_df is None:
        print("Exiting due to loading errors.")
        return

    # --- Processing ---
    if 'PatientNum' not in assessment_df.columns:
        print("Error: 'PatientNum' column not found in assessment data.")
        return
        
    patient_ids = assessment_df['PatientNum'].unique()
    print(f"Processing {len(patient_ids)} unique patients...")
    
    results = []
    for patient_id in patient_ids:
        facts = get_patient_facts(patient_id, assessment_df, diagnosis_df, fact_definitions)
        cfs_score, cfs_description, matched_rule = evaluate_rules(facts, rules)
        
        result_row = {
            'PatientNum': patient_id,
            'CFS_Score': cfs_score,
            'CFS_Description': cfs_description,
            'Matched_Rule_Priority': matched_rule.get('priority') if matched_rule else 'N/A',
            'Matched_Rule_Name': matched_rule.get('rule_name') if matched_rule else 'N/A'
        }
        # Add all facts to the result row for detailed output
        for fact, value in facts.items():
            # Convert lists to strings for CSV compatibility
            if isinstance(value, list):
                result_row[fact.replace('_', ' ').title()] = ', '.join(map(str, value))
            else:
                result_row[fact.replace('_', ' ').title()] = value
        
        results.append(result_row)

    # --- Output ---
    results_df = pd.DataFrame(results)
    
    # Reorder columns to have patient info and CFS score first
    cols = ['PatientNum', 'CFS_Score', 'CFS_Description', 'Matched_Rule_Priority', 'Matched_Rule_Name']
    other_cols = [col for col in results_df.columns if col not in cols]
    results_df = results_df[cols + other_cols]

    results_df.to_csv(OUTPUT_FILE, index=False, encoding='utf-8-sig')
    print(f"Results saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()