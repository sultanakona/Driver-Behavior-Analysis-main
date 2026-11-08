# Driver Behavior Analysis Workflow

Step-by-step workflow of the driver behavior analysis, detailing the process from raw data ingestion to final risk assessment.

## 1. Data Loading
*   **Action:** Loads the raw CSV file (`risk_log.csv`).

## 2. Data Cleaning
*   **Drop Missing Values:** Removes any rows containing `NaN`.
*   **Handle Infinite Values:**
    *   "Time-to-Collision" (TTC) calculations can result in infinity (if vehicles are moving at the same speed).
    *   These infinities are replaced with a fixed maximum threshold (default `30`).
*   **Cap Large Values:** Any TTC value greater than `30` is clamped down to `30` to prevent skewing the data.
*   **Remove Invalid Logic:** Filters out physically impossible or erroneous data rows:
    *   Negative gaps (distance < 0).
    *   Negative speeds.
    *   Negative TTC.

## 3. Feature Engineering
*   **Kinematics:**
    *   `speed_diff`: Difference between follower speed (`vf`) and leader speed (`vl`).
    *   `relative_speed`: Absolute value of speed difference.
    *   `speed_ratio`: Ratio of follower to leader speed.
*   **Time Headway:** Calculates how many seconds the follower is behind the leader (`gap / speed`). Capped at 0–10 seconds.
*   **Required Deceleration:** Calculates how hard the driver *needs* to brake to avoid a crash.
*   **Safety Metrics:**
    *   `safe_gap`: Defines a dynamic "safe distance" based on current speed (2-second rule).
    *   `gap_deficit`: How much *shorter* the actual gap is compared to the safe gap.
*   **Binary Flags (True/False Indicators):** Creates columns of 0s and 1s for specific events:
    *   `is_critical_ttc`: Is TTC < 1.5s?
    *   `is_tailgating`: Is headway < 1.0s?
    *   `is_speeding_up`: Is the driver accelerating dangerously?
    *   `is_harsh_decel_req`: Is sudden hard braking required?

## 4. Driver Profiling
*   **Grouping:** The analysis shifts from individual timestamps to grouping data by **Vehicle ID (`veh`)**.
*   **Summarizing:** For each vehicle, the following statistics are calculated:
    *   *Means/Averages* (e.g., average speed, average gap).
    *   *Max/Mins* (e.g., minimum gap observed, maximum speed difference).
    *   *Standard Deviations* (variability in driving).
    *   *Counts/Sums* (total number of critical incidents).

## 5. Risk Scoring
*   **Rate Calculation:** Converts raw counts of incidents into percentages (e.g., "Time spent tailgating" as a % of total driving time).
*   **Composite Score:** Calculates a single `risk_score` number for each driver using a weighted formula:
    *   **40%** weight on Critical TTC.
    *   **30%** weight on Tailgating.
    *   **30%** weight on Aggressive Acceleration.
*   **Labeling:** Buckets drivers into text categories based on their score:
    *   *Safe, Moderate, Risky, Aggressive*.

## 6. Clustering
*   **Selection:** Selects 6 key variables for clustering (Gap, Headway, Speed Diff, Deceleration, TTC Rate, Tailgating Rate).
*   **Scaling:** Standardizes the data (Z-score normalization) so that variables with large magnitude (like speed) don't dominate small magnitude variables (like time).
*   **K-Means:** Groups drivers into distinct clusters (default 4) based on similarity in driving behavior.
*   **Semantic Mapping:** Analyzes the average risk score of each cluster to automatically name them (e.g., the cluster with the lowest risk score is mapped to "Safe").

## 7. Classification
*   **Setup:** Uses the driver profiles (`X`) to predict the cluster label (`y`) created in the previous step.
*   **Split:** Divides data into Training (70%) and Testing (30%) sets.
*   **Model:** Trains a **Random Forest Classifier**.
*   **Prediction:** Predicts the behavior type for the test set.

