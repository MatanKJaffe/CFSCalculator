# Clinical Frailty Scale (CFS) Calculation Engine

This project implements a rule-based engine in Python to automatically calculate the Clinical Frailty Scale (CFS) for patients based on data from two main sources: `Cleaned_Assessment.csv` and `Diagnosis.csv`.

## Clinical Frailty Scale (CFS) Descriptions

### 1. Very Fit
People who are robust, active, energetic and motivated. They tend to exercise regularly and are among the fittest for their age.

### 2. Fit
People who have no active disease symptoms but are less fit than category 1. Often, they exercise or are very active occasionally, e.g., seasonally.

### 3. Managing Well
People whose medical problems are well controlled, even if occasionally symptomatic, but often are not regularly active beyond routine walking.

### 4. Living with Very Mild Frailty
Previously "vulnerable," this category marks early transition from complete independence. While not dependent on others for daily help, often symptoms limit activities. A common complaint is being "slowed up" and/or being tired during the day.

### 5. Living with Mild Frailty
People who often have more evident slowing, and need help with high order instrumental activities of daily living (finances, transportation, heavy housework). Typically, mild frailty progressively impairs shopping and walking outside alone, meal preparation, medications and begins to restrict light housework.

### 6. Living with Moderate Frailty
People who need help with all outside activities and with keeping house. Inside, they often have problems with stairs and need help with bathing and might need minimal assistance (cuing, standby) with dressing.

### 7. Living with Severe Frailty
Completely dependent for personal care, from whatever cause (physical or cognitive). Even so, they seem stable and not at high risk of dying (within ~6 months).

### 8. Living with Very Severe Frailty
Completely dependent for personal care and approaching end of life. Typically, they could not recover even from a minor illness.

### 9. Terminally Ill
Approaching the end of life. This category applies to people with a life expectancy < 6 months, who are not otherwise living with severe frailty. (Many terminally ill people can still exercise until very close to death.)

---

### Scoring Frailty in People with Dementia
The degree of frailty generally corresponds to the degree of dementia. Common symptoms in mild dementia include forgetting the details of a recent event, though still remembering the event itself, repeating the same question/story and social withdrawal.

In moderate dementia, recent memory is very impaired, even though they seemingly can remember their past life events well. They can do personal care with prompting.

In severe dementia, they cannot do personal care without help.

In very severe dementia they are often bedfast. Many are virtually mute.

*Clinical Frailty Scale @2005-2020 Rockwood, Version 2.0 (EN). All rights reserved. For permission: www.geriatricmedicineresearch.ca*

## CFS Classification Flowchart

```mermaid
graph TD
    A[Terminally ill?] -->|Yes| B(Number of BADLs?)
    A -->|No| E(Number of BADLs?)

    subgraph "Branch: Terminally Ill"
        direction TB
        B -- "0-2 BADLs" --> C[CFS 8: Very Severe Frailty]
        B -- "3-5 BADLs" --> D[CFS 8: Very Severe Frailty]
    end

    subgraph "Branch: Not Terminally Ill"
        direction TB
        E -- "3-5 BADLs" --> F(BADLs Check)
            F -- "3-5 BADLs" --> G[CFS 7: Severe Frailty]
            F -- "1-2 BADLs" --> H[CFS 6: Moderate Frailty]

        E -- "None" --> I(Number of IADLs?)
            I -- "5-6 IADLs" --> J[CFS 6: Moderate Frailty]
            I -- "1-4 IADLs" --> K[CFS 5: Mild Frailty]
            I -- "None" --> L(Number of Chronic Conditions?)

        L -- "&ge;10" --> M[CFS 4: Very Mild Frailty]
        L -- "0-9" --> N(Self-Rated Health?)

        N -- "Fair/Poor" --> Q[CFS 4: Very Mild Frailty]
        N -- "Excellent" --> O("Everything is an effort?")
        N -- "Very Good/Good" --> R("Everything is an effort?")

        subgraph "Path: Health Excellent"
            direction TB
            O -- "All of the time<br>(5-7 days/week)" --> P[CFS 4: Very Mild Frailty]
            O -- "Rarely/Never<br>(<1 day/week)" --> S(Engages in sports?)
            O -- "Sometimes/Occasionally<br>(1-4 days/week)" --> T(Engages in sports?)
            S -- "Yes" --> S_Y[CFS 1: Very Fit]
            S -- "No" --> S_N[CFS 2: Fit]
            T -- "Yes" --> T_Y[CFS 2: Fit]
            T -- "No" --> T_N[CFS 2: Fit]
        end

        subgraph "Path: Health Very Good/Good"
            direction TB
            R -- "All of the time<br>(5-7 days/week)" --> U[CFS 4: Very Mild Frailty]
            R -- "Rarely/Never<br>(<1 day/week)" --> V(Engages in sports?)
            R -- "Sometimes/Occasionally<br>(1-4 days/week)" --> W(Engages in sports?)
            V -- "Yes" --> V_Y[CFS 2: Fit]
            V -- "No" --> V_N[CFS 3: Managing Well]
            W -- "Yes" --> W_Y[CFS 2: Fit]
            W -- "No" --> W_N[CFS 3: Managing Well]
        end
    end

    %% --- Styling ---
    classDef default fill:#f4f4f4,stroke:#333,stroke-width:1px,border-radius:5px
    classDef decision fill:#e0f7fa,stroke:#00796b,stroke-width:2px,border-radius:5px
    classDef result fill:#e8f5e9,stroke:#388e3c,stroke-width:2px,font-weight:bold,border-radius:5px

    class A,B,E,F,I,L,N,O,R,S,T,V,W decision;
    class C,D,G,H,J,K,M,P,Q,S_Y,S_N,T_Y,T_N,U,V_Y,V_N,W_Y,W_N result;
```


### Definitions

- **BADLs**: Basic Activities of Daily Living
- **IADLs**: Instrumental Activities of Daily Living

## How It Works

The system uses a decoupled architecture where the logic is separated from the data processing engine.

- **`cfs_rule_engine.py`**: This is the core script that contains the rule engine logic. It loads patient data, gathers "facts" about each patient, evaluates these facts against a set of rules, and writes the results to a CSV file.
- **`cfs_rules.json`**: This file defines the clinical logic for assigning a CFS score. It contains a list of rules, each with a priority, a set of conditions, and a resulting CFS score and description. The engine processes rules in order of priority.
- **`cfs_fact.json`**: This file serves as a data dictionary, mapping the raw data from the source CSVs (which includes Hebrew strings) into a standardized set of English "facts" that the rule engine can understand.

### Execution Flow

1. **Load Data**: The script loads the assessment and diagnosis data from the CSV files.
2. **Load Definitions**: The rules from `cfs_rules.json` and fact mappings from `cfs_fact.json` are loaded.
3. **Process Patients**: For each unique patient, the script performs the following:
    a. **Fact Gathering**: The `get_patient_facts` function gathers all available information for a patient and translates it into a standardized `facts` dictionary using the mappings in `cfs_fact.json`. This includes a special tiered logic to infer a patient's health status if it's not explicitly stated.
    b. **Rule Evaluation**: The `evaluate_rules` function takes the patient's `facts` and checks them against the list of rules, starting with the highest priority (lowest number).
    c. **Assign Score**: The first rule that matches the patient's facts determines their CFS score.
4. **Save Results**: The final CFS scores, along with all the facts used for the calculation, are saved to `CFS_Results.csv`.

## Running the Script

To run the calculation, execute the following command in a terminal with the appropriate Python environment activated:

```bash
python cfs_rule_engine.py
```

## Clinical Frailty Scale (CFS) Implementation

The CFS score is determined by a set of prioritized rules. The engine checks the rules in order, and the first rule that matches all its conditions determines the score.

- **CFS 9: Terminally Ill**
  - **Priority**: 1
  - **Condition**: The patient is identified as terminally ill (based on keywords like "terminal", "palliative", "hospice").

- **CFS 8: Totally Dependent or Severe Dementia**
  - **Priority**: 2
  - **Condition**: The patient is dependent in both bathing AND eating, OR has a diagnosis of Dementia.

- **CFS 7: Severely Frail**
  - **Priority**: 3
  - **Condition**: The patient is dependent in bathing OR eating.

- **CFS 6: Moderately Frail**
  - **Priority**: 4
  - **Condition**: The patient needs help with any instrumental activities of daily living (IADLs) like cooking, shopping, transportation, or managing finances.

- **CFS 5: Mildly Frail**
  - **Priority**: 5
  - **Condition**: The patient is NOT dependent in personal care (bathing, eating) but needs help with more complex tasks (IADLs or managing medication).

- **CFS 4: Vulnerable**
  - **Priority**: 6 & 7 (two rules can lead to this score)
  - **Conditions**:
    - Patient has 10 or more chronic conditions.
    - OR, patient has 5 or more chronic conditions, OR is disoriented, OR has mild confusion, OR has a "poor" or "very_poor" health status.

- **CFS 3: Managing Well**
  - **Priority**: 8
  - **Condition**: The patient is independent and has a "fair" health status.

- **CFS 2: Fit**
  - **Priority**: 9
  - **Condition**: The patient is independent and has a "good" health_status.

- **CFS 1: Very Fit**
  - **Priority**: 99 (Default)
  - **Condition**: This is the fallback rule. If no other conditions are met, the patient is considered very fit.

## Data Mapping Details

This section details the exact string mappings from the source files to the facts used by the engine, as defined in `cfs_fact.json`.

### Assessment Data Mapping

This maps the combination of `Description`, `Question_Name`, and `Answer_Text` from `Cleaned_Assessment.csv` to standardized facts.

| Description | Question_Name | Answer_Text | Fact Generated |
| :--- | :--- | :--- | :--- |
| `תפקוד` | `מצב תפקודי` | `עצמאי` | `functional_status: independent` |
| `תפקוד` | `מצב תפקודי` | `תלות ברחצה` | `functional_status: dependent_bathing` |
| `תפקוד` | `מצב תפקודי` | `תלות באכילה` | `functional_status: dependent_eating` |
| `תפקוד` | `מצב תפקודי` | `תלות בהכנת אוכל/בישול` | `functional_status: dependent_cooking` |
| `תפקוד` | `מצב תפקודי` | `תלות בקניות` | `functional_status: dependent_shopping` |
| `תפקוד` | `מצב תפקודי` | `תלות בהסעות` | `functional_status: dependent_transportation` |
| `תפקוד` | `מצב תפקודי` | `תלות בלקיחת תרופות` | `functional_status: dependent_medication` |
| `תפקוד` | `מצב תפקודי` | `תלות בטיפול בכספים` | `functional_status: dependent_finances` |
| `תפקוד` | `מצב פיזי` | `טוב` | `health_status: good` |
| `תפקוד` | `מצב פיזי` | `סביר` | `health_status: fair` |
| `תפקוד` | `מצב פיזי` | `לא טוב` | `health_status: poor` |
| `תפקוד` | `מצב פיזי` | `רע` | `health_status: very_poor` |
| `נשימה` | `קוצר נשימה` | `כן` | `symptoms: shortness_of_breath` |
| `כאב` | `כאב` | `כן` | `symptoms: has_pain` |
| `אוכלוסיה בסיכון` | `מצב קוגניטיבי` | `אינו מתמצא במקום` | `cognitive_status: disoriented_place` |
| `אוכלוסיה בסיכון` | `מצב קוגניטיבי` | `אינו מתמצא בזמן` | `cognitive_status: disoriented_time` |
| `אוכלוסיה בסיכון` | `מצב קוגניטיבי` | `אינו מתמצא באנשים` | `cognitive_status: disoriented_people` |
| `אוכלוסיה בסיכון` | `מצב הכרה` | `בלבול קל` | `consciousness_status: mild_confusion` |

*(Note: Other similar mappings for `health_status` under different `Description` categories like `הזנה` also exist.)*

### Health Status Inference Logic

Due to missing data, `health_status` is inferred using a 3-tiered approach if not explicitly found in the assessment data:

1. **Tier 1: Explicit Assessment**: Use the value from the assessment data if available.
2. **Tier 2: Acute Diagnoses**: If status is still unknown, check for severe acute diagnoses from `Diagnosis.csv`. If any of the following keywords are found, status is set to **`very_poor`**:
    - `SEPSIS`
    - `SHOCK`
    - `ACUTE RENAL FAILURE`
    - `RENAL FAILURE ACUTE`
    - `PNEUMONIA`
    - `PULMONARY EMBOLISM`
3. **Tier 3: Symptoms**: If status is still unknown, check for symptoms from the assessment data.
    - If `shortness_of_breath` is present, status is set to **`poor`**.
    - If `has_pain` is present, status is set to **`fair`**.

### Diagnosis & Keyword Mapping

The following keywords in the `Name` column of `Diagnosis.csv` are used to identify specific conditions.

- **Dementia**: `DEMENTIA`, `ALZHEIMER'S DISEASE`
- **Heart Failure**: `CONGESTIVE HEART FAILURE`, `CHF`
- **Renal Failure**: `RENAL FAILURE`, `CHRONIC KIDNEY DISEASE`
- **COPD**: `COPD`, `CHRONIC OBSTRUCTIVE PULMONARY DISEASE`
- **Cancer**: `CANCER`, `MALIGNANCY`, `LYMPHOMA`, `LEUKEMIA`
- **Stroke**: `CEREBROVASCULAR ACCIDENT`, `CVA`, `STROKE`
- **Terminal Illness**: `terminal`, `palliative`, `hospice`, `end-stage`

## Output File

The script generates `CFS_Results.csv` with the following key columns:

- `PatientNum`: The patient's unique identifier.
- `CFS_Score`: The calculated CFS score.
- `CFS_Description`: The description of the calculated score.
- `Matched_Rule_Priority`: The priority of the rule that was triggered.
- `Matched_Rule_Name`: The name of the rule that was triggered.
- Additional columns for every fact used in the calculation, providing full transparency.
