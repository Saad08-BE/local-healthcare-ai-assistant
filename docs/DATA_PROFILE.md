# Dataset Profile — Indian Healthcare Dataset

## Overview

- **Source File**: `data/raw/Indian_healthcare.csv`
- **Total Rows**: 100,000
- **Total Columns**: 19
- **Missing / Null Values**: 0 across all columns (complete dataset)

## Schema & Types

| Column | Type | Unique Count | Nulls | Retrieval / System Role |
|---|---|---|---|---|
| `Patient_ID` | Identifier | 100,000 | 0 | Privacy-excluded; omitted from semantic index and LLM prompts |
| `Age` | Integer | 95 | 0 | Structured demographic filter |
| `Gender` | Categorical | 3 | 0 | Structured demographic filter |
| `Region` | Categorical | 10 | 0 | Structured geographic filter |
| `Socioeconomic_Status` | Categorical | 3 | 0 | Structured socioeconomic context |
| `Occupation` | Categorical | 639 | 0 | Structured demographic metadata |
| `Visit_Date` | Date (YYYY-MM-DD) | 730 | 0 | Structured temporal metadata |
| `Symptoms` | Clinical Text | 6 | 0 | Primary semantic query search & association indexing |
| `Primary_Diagnosis` | Clinical Text | 10 | 0 | Primary semantic entity & condition association |
| `Blood_Glucose_mg_dL` | Float | 2,874 | 0 | Structured clinical measurement |
| `HbA1c_%` | Float | 145 | 0 | Structured clinical measurement |
| `Total_Cholesterol_mg_dL` | Float | 2,756 | 0 | Structured clinical measurement |
| `Treatment_Type` | Categorical | 7 | 0 | Structured treatment filter & association |
| `Treatment_Outcome` | Categorical | 5 | 0 | Structured treatment outcome metric |
| `Imaging_Type` | Categorical | 5 | 0 | Structured diagnostic modality |
| `Imaging_Findings` | Clinical Text | 6 | 0 | Semantic diagnostic text & structured category |
| `Hospital_Type` | Categorical | 3 | 0 | Structured hospital classification |
| `Insurance_Covered` | Boolean | 2 | 0 | Structured financial metadata |
| `BMI` | Float | 297 | 0 | Structured clinical measurement |

## Numeric Measurements Distribution

| Measurement | Min | Max | Mean | Std Dev | Physiological Validity |
|---|---|---|---|---|---|
| `Age` | 1.0 | 95.0 | 44.45 | 17.9 | Valid |
| `Blood_Glucose_mg_dL` | -11.7 | 349.5 | 127.7 | 46.74 | Outliers present (min < 0 mg/dL) |
| `HbA1c_%` | 0.2 | 15.3 | 6.4 | 1.78 | Synthetic low tail (< 3.0%) |
| `Total_Cholesterol_mg_dL` | 48.4 | 411.2 | 216.14 | 43.43 | Valid |
| `BMI` | 15.0 | 45.0 | 24.56 | 5.3 | Valid |

## Data Quality & Anomaly Detection

- **Negative Blood Glucose Values (`<= 0 mg/dL`)**: 6 records detected. These are physiologically impossible and must be filtered or sanitized during preprocessing.
- **Non-Physiological HbA1c (`< 3.0%`)**: 757 records detected.
- **Zero / Negative Age**: 0 records.

## Categorical Distributions

### `Gender`

| Value | Frequency | Percentage |
|---|---|---|
| Male | 51,013 | 51.01% |
| Female | 48,494 | 48.49% |
| Other | 493 | 0.49% |

### `Region`

| Value | Frequency | Percentage |
|---|---|---|
| Tamil Nadu | 18,002 | 18.00% |
| Kerala | 14,794 | 14.79% |
| Karnataka | 12,049 | 12.05% |
| Andhra Pradesh | 10,140 | 10.14% |
| Telangana | 8,975 | 8.97% |
| Uttar Pradesh | 8,056 | 8.06% |
| Puducherry | 8,008 | 8.01% |
| Maharashtra | 8,006 | 8.01% |
| Delhi | 6,982 | 6.98% |
| West Bengal | 4,988 | 4.99% |

### `Socioeconomic_Status`

| Value | Frequency | Percentage |
|---|---|---|
| Low | 44,825 | 44.82% |
| Middle | 40,150 | 40.15% |
| High | 15,025 | 15.02% |

### `Symptoms`

| Value | Frequency | Percentage |
|---|---|---|
| Swelling in legs, high BP | 16,805 | 16.80% |
| Frequent urination, blurred vision | 16,687 | 16.69% |
| Fever, fatigue, increased thirst | 16,676 | 16.68% |
| Chest pain, shortness of breath | 16,654 | 16.65% |
| Headache, joint pain, high fever | 16,607 | 16.61% |
| Cough, weight loss, night sweats | 16,571 | 16.57% |

### `Primary_Diagnosis`

| Value | Frequency | Percentage |
|---|---|---|
| Type 2 Diabetes | 28,214 | 28.21% |
| Hypertension | 22,086 | 22.09% |
| Cardiovascular Disease | 11,889 | 11.89% |
| Dengue | 7,910 | 7.91% |
| Chronic Kidney Disease | 6,972 | 6.97% |
| Asthma/COPD | 5,981 | 5.98% |
| Malaria | 5,898 | 5.90% |
| Tuberculosis | 5,075 | 5.08% |
| Thyroid Disorder | 3,959 | 3.96% |
| Other | 2,016 | 2.02% |

### `Treatment_Type`

| Value | Frequency | Percentage |
|---|---|---|
| Insulin Therapy | 14,532 | 14.53% |
| Surgery | 14,379 | 14.38% |
| Lifestyle Changes | 14,342 | 14.34% |
| Combination Therapy | 14,253 | 14.25% |
| Medication | 14,225 | 14.22% |
| Antibiotics | 14,159 | 14.16% |
| Physiotherapy | 14,110 | 14.11% |

### `Treatment_Outcome`

| Value | Frequency | Percentage |
|---|---|---|
| Stable | 20,213 | 20.21% |
| Referred | 20,082 | 20.08% |
| Worsened | 20,060 | 20.06% |
| Recovered | 19,879 | 19.88% |
| Improved | 19,766 | 19.77% |

### `Imaging_Type`

| Value | Frequency | Percentage |
|---|---|---|
| None | 35,031 | 35.03% |
| X-Ray | 24,794 | 24.79% |
| Ultrasound | 20,126 | 20.13% |
| CT Scan | 12,061 | 12.06% |
| MRI | 7,988 | 7.99% |

### `Imaging_Findings`

| Value | Frequency | Percentage |
|---|---|---|
| No imaging performed | 35,031 | 35.03% |
| Evidence of pleural effusion | 13,070 | 13.07% |
| Mild cardiomegaly observed | 13,046 | 13.05% |
| Fatty liver changes | 13,036 | 13.04% |
| No significant abnormality detected | 13,026 | 13.03% |
| Normal study | 12,791 | 12.79% |

### `Hospital_Type`

| Value | Frequency | Percentage |
|---|---|---|
| Government | 44,647 | 44.65% |
| Private | 40,141 | 40.14% |
| Corporate | 15,212 | 15.21% |

### `Insurance_Covered`

| Value | Frequency | Percentage |
|---|---|---|
| False | 64,970 | 64.97% |
| True | 35,030 | 35.03% |
