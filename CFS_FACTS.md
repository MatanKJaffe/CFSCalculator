# Clinical Frailty Scale (CFS) Fact Mappings

This document visualizes the mappings from source data (in Hebrew) to the standardized facts used by the rule engine, as defined in `cfs_fact.json`.

## Fact Mapping (`FACT_MAPPING`)

This section shows how raw observations from different assessment categories are translated into standardized `functional_status`, `health_status`, `symptoms`, `cognitive_status`, and `consciousness_status` facts.

```mermaid
graph TD
    subgraph "תפקוד (Function)"
        A["מצב תפקודי (Functional Status)"] --> F1{functional_status};
        A_1["עצמאי"] --> V1[independent];
        A_2["תלות ברחצה"] --> V2[dependent_bathing];
        A_3["תלות באכילה"] --> V3[dependent_eating];
        A_4["...and other dependencies"] --> V_etc([...]);
        subgraph " "
          direction LR
          V1 -- maps to --> F1;
          V2 -- maps to --> F1;
          V3 -- maps to --> F1;
          V_etc -- maps to --> F1;
        end

        B["מצב פיזי (Physical Condition)"] --> F2{health_status};
        B_1["טוב"] --> H1[good];
        B_2["סביר"] --> H2[fair];
        B_3["לא טוב"] --> H3[poor];
        B_4["רע"] --> H4[very_poor];
         subgraph " "
          direction LR
          H1 -- maps to --> F2;
          H2 -- maps to --> F2;
          H3 -- maps to --> F2;
          H4 -- maps to --> F2;
        end
    end

    subgraph "אוכלוסיה בסיכון (At-Risk Population)"
        C["מצב קוגניטיבי (Cognitive Status)"] --> F3{cognitive_status};
        C_1["מתמצא"] --> C_V1[oriented];
        C_2["אינו מתמצא במקום"] --> C_V2[disoriented_place];
        C_3["...and other disorientation"] --> C_V_etc([...]);
         subgraph " "
          direction LR
          C_V1 -- maps to --> F3;
          C_V2 -- maps to --> F3;
          C_V_etc -- maps to --> F3;
        end

        D["מצב הכרה (Consciousness)"] --> F4{consciousness_status};
        D_1["בהכרה"] --> D_V1[conscious];
        D_2["בלבול קל"] --> D_V2[mild_confusion];
        D_3["...and other states"] --> D_V_etc([...]);
         subgraph " "
          direction LR
          D_V1 -- maps to --> F4;
          D_V2 -- maps to --> F4;
          D_V_etc -- maps to --> F4;
        end
    end
    
    style F1 fill:#add8e6,stroke:#333,stroke-width:2px
    style F2 fill:#90ee90,stroke:#333,stroke-width:2px
    style F3 fill:#f0e68c,stroke:#333,stroke-width:2px
    style F4 fill:#ffb6c1,stroke:#333,stroke-width:2px
```

## Diagnosis Mapping (`DIAGNOSIS_MAPPING`)

This section shows how specific diagnosis codes/descriptions are mapped to boolean facts like `has_dementia` or `has_cancer`.

```mermaid
graph TD
    subgraph "Diagnosis to Fact"
        D1["DEMENTIA"] --> F1{has_dementia};
        D2["ALZHEIMER'S DISEASE"] --> F1;
        
        D3["CONGESTIVE HEART FAILURE"] --> F2{has_heart_failure};
        D4["CHF"] --> F2;

        D5["RENAL FAILURE"] --> F3{has_renal_failure};
        D6["CHRONIC KIDNEY DISEASE"] --> F3;

        D7["...and so on for"] --> F_etc[has_copd, has_cancer, has_stroke];
    end
```

## Keyword-Based Facts

These facts are derived by searching for specific keywords in relevant text fields.

### Acute Diagnosis Keywords

- **Purpose**: Identifies acute conditions that may indicate a `very_poor` health status.
- **Keywords**: `SEPSIS`, `SHOCK`, `ACUTE RENAL FAILURE`, etc.

```mermaid
graph TD
    A["Text contains 'SEPSIS' or 'SHOCK'..."] --> B{Set health_status = 'very_poor'};
```

### Terminal Illness Keywords

- **Purpose**: Identifies if a patient is terminally ill.
- **Keywords**: `terminal`, `palliative`, `hospice`, `end-stage`.

```mermaid
graph TD
    A["Text contains 'terminal' or 'palliative'..."] --> B{Set is_terminally_ill = true};
```

## Thresholds

### Chronic Disease Threshold

- **Purpose**: Used to count the number of chronic conditions to determine `chronic_condition_count`.
- **Threshold**: A patient is considered to have a significant chronic disease burden if they have **5 or more** mapped chronic diseases. This count is then used in the CFS 4 rule.

```mermaid
graph TD
    A["Count of mapped chronic diagnoses"] --> B{"Count >= 5?"};
    B -- Yes --> C[chronic_condition_count >= 5];
    B -- No --> D[chronic_condition_count < 5];
```
