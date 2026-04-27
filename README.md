# denied-inference-modelling

Title
Year
Theme
Main Conclusions (Top 5)
Observations
Credit scoring with macroeconomic variables using survival analysis
2009
Survival + Macroeconomics
1. Macroeconomic variables significantly improve PD estimation.  2. Survival models capture time-to-default better than static models.  3. Economic cycles affect hazard rates.  4. Cox models handle time-varying covariates effectively.  5. Better forecasting during downturns.
Early seminal work integrating macro factors into survival credit models.
Survival analysis as a tool for better probability of default prediction
2018
Survival vs Traditional Models
1. Survival models outperform logistic regression in PD estimation.  2. Time dimension is critical for risk modeling.  3. Censoring improves realism of datasets.  4. Hazard functions provide richer insights.  5. Better segmentation of borrower risk.
Good conceptual introduction; less emphasis on ML.
Random survival forests models for SME credit risk measurement
2009
Survival + ML (Ensemble)
1. RSF captures nonlinearities and interactions.  2. Outperforms Cox in complex datasets.  3. Handles high-dimensional data well.  4. Robust to overfitting vs single trees.  5. Provides variable importance measures.
One of the first applications of RSF in credit risk.
Survival analysis of bank loans in the presence of long-term survivors
2018
Cure Models
1. A portion of borrowers never default (“cured”).  2. Standard survival models overestimate risk.  3. Mixture/cure models improve calibration.  4. Long-term survivors must be explicitly modeled.  5. Better portfolio risk segmentation.
Important for long-tenure products like mortgages.
Survival analysis of bank loans in the presence of long-term survivors
2022
Cure Models (Extended)
1. Confirms importance of cure fraction modeling.  2. Improves long-term PD estimation.  3. Enhances interpretability of borrower classes.  4. Better risk stratification.  5. More stable predictions over time.
Peer-reviewed extension of earlier work.
Modeling the probability of mortgage default via logistic regression and survival analysis
2015
Logistic vs Survival
1. Survival models outperform logistic in timing prediction.  2. Logistic easier but less informative.  3. Time-to-event improves risk ranking.  4. Censoring is crucial.  5. Hybrid approaches possible.
Good applied comparison study.
Time varying and dynamic models for default risk in consumer loans
2010
Dynamic Survival Models
1. Time-varying covariates improve predictive power.  2. Static models miss behavioral changes.  3. Hazard evolves with borrower state.  4. Better early warning signals.  5. Supports dynamic credit monitoring.
Highly influential in behavioral scoring.
Survival models for credit risk estimation
2013
Methodological Overview
1. Survival models unify PD and LGD timing.  2. Flexible hazard specifications.  3. Suitable for incomplete data.  4. Applicable across portfolios.  5. Bridges statistics and finance.
Broad methodological reference.
Statistical Credit Rating with Survival Regression & Gradient Boosting
2024
Survival + Boosting
1. Gradient boosting improves survival predictions.  2. Captures nonlinear risk patterns.  3. Better discrimination vs Cox.  4. Combines interpretability + performance.  5. Handles complex feature spaces.
Modern ML + survival hybrid.
Survival Analysis Integrated Ensemble Models for Loan Default Timing
~2020
Ensemble Survival
1. Ensembles outperform single models.  2. Combining models improves robustness.  3. Better timing prediction.  4. Reduces variance.  5. Works well in heterogeneous portfolios.
Thesis; limited real-world validation.
Survival analysis of bank loans and credit risk prognosis
2015
Survival Foundations
1. Survival analysis suitable for credit risk lifecycle.  2. Captures borrower evolution.  3. Hazard models outperform static PD.  4. Enables forward-looking risk.  5. Useful for portfolio management.
Foundational thesis by Marimo.
Default Prediction Using Cox Regression Model and Macroeconomic Conditions
~2018
Cox + Macro
1. Macro variables improve Cox models.  2. Lifetime PD estimation is enhanced.  3. Economic cycles shift hazard rates.  4. Better stress testing.  5. Supports IFRS9 frameworks.
Strong regulatory relevance.
Relationship Banking: The Borrower's Incentives Channel
2024
Behavioral Credit Risk
1. Bank-borrower relationships affect default risk.  2. Incentives reduce probability of default.  3. Soft information matters.  4. Long-term relationships stabilize risk.  5. Impacts credit supply decisions.
Not purely survival-focused; adds behavioral layer.
Survival analysis: applications to credit risk default modelling
~2010s
Applied Survival
1. Survival models flexible for credit portfolios.  2. Handle censoring naturally.  3. Provide timing insights.  4. Useful in retail banking.  5. Better than static PD in many cases.
Introductory thesis-style work.
Time to default in credit scoring using survival analysis: a benchmark study
2017
Benchmark Study
1. Survival models outperform logistic benchmarks.  2. Cox model is strong baseline.  3. Machine learning improves further.  4. Time-to-default is key metric.  5. Evaluation metrics must adapt (C-index).
Important benchmark paper.
Modeling Time to Default on a Personal Loan Portfolio in Presence of Disproportionate Hazard Rates
2014
Non-Proportional Hazards
1. Proportional hazards assumption often violated.  2. Flexible hazard models improve fit.  3. Time-dependent effects important.  4. Better calibration achieved.  5. Real portfolio validation.
Very relevant for real-world data issues.
Comparing lifetime estimates of PD with survival and ensemble methods
2024
Survival vs Ensemble
1. Ensemble models outperform classical survival.  2. Lifetime PD estimation improves with ML.  3. Hybrid models best overall.  4. Stability across time horizons.  5. Better IFRS9 compliance.
Very recent and practical.
Calibrated Credit Intelligence: Bayesian + Boosting
2026
Calibration + ML
1. Calibration critical for PD models.  2. Bayesian uncertainty improves robustness.  3. Handles dataset shift.  4. Fairness considerations integrated.  5. Boosting enhances predictive power.
Cutting-edge research direction.
Calibration of Machine Learning Classifiers for PD Modelling
2017
Calibration
1. ML models often poorly calibrated.  2. Calibration improves PD reliability.  3. Platt scaling / isotonic regression useful.  4. Calibration affects decision-making.  5. Essential for regulatory compliance.
Foundational calibration paper.
Explainable AI methods for credit scoring
2021
XAI
1. Interpretability is critical in credit risk.  2. SHAP/LIME explain complex models.  3. Black-box models need transparency.  4. Improves trust and compliance.  5. Enables model validation.
Key for regulatory environments (e.g., Brazil, IFRS9).
