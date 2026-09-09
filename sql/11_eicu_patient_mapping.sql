-- ============================================================================
-- 11_eicu_patient_mapping.sql
-- PURPOSE
--   Per-stay patient linkage and documentation timing for the amended primary
--   external population (PROTOCOL_AMENDMENT.md): uniquepid and
--   patienthealthsystemstayid for one-stay-per-patient selection
--   (order: unitvisitnumber, patienthealthsystemstayid, patientunitstayid),
--   hospitalid for site counts, first cardiogenic-shock and first
--   cardiac-arrest diagnosis offsets for eligibility timing and the
--   late-arrest sensitivity. Output: eicu_patient_mapping.csv.
-- ============================================================================
SELECT c.patientunitstayid, p.uniquepid, p.patienthealthsystemstayid AS phs,
       p.unitvisitnumber AS uvn, p.hospitalid,
       csdx.first_cs_offset, arr.first_arrest_offset
FROM `YOUR_PROJECT_ID.3_UPDATED_CS_MORT_STUDY.cs_eicu_canonical` c
JOIN `physionet-data.eicu_crd.patient` p USING (patientunitstayid)
LEFT JOIN (SELECT patientunitstayid, MIN(diagnosisoffset) AS first_cs_offset
           FROM `physionet-data.eicu_crd.diagnosis`
           WHERE LOWER(diagnosisstring) LIKE '%cardiogenic shock%'
           GROUP BY 1) csdx USING (patientunitstayid)
LEFT JOIN (SELECT patientunitstayid, MIN(diagnosisoffset) AS first_arrest_offset
           FROM `physionet-data.eicu_crd.diagnosis`
           WHERE LOWER(diagnosisstring) LIKE '%cardiac arrest%'
           GROUP BY 1) arr USING (patientunitstayid);
