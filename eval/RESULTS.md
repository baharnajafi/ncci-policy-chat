# Evaluation report

Settings: embed=text-embedding-3-large, reranker=BAAI/bge-reranker-base, chat=gpt-4.1, top_k=6, min_relevance=0.1

**Retrieval (20 questions):** hit@1 19/20 · hit@3 19/20 · hit@6 20/20 · MRR 0.96

| id | first relevant rank | keyword | vector | code | top relevance | gate | question |
|---|---|---|---|---|---|---|---|
| q01 | 1 | 1 | 1 | 2 | 0.953 | pass | When is it appropriate to use modifier 59? |
| q02 | 1 | 1 | 1 | 1 | 0.999 | pass | What do modifiers XE, XS, XP, and XU mean, and how do they relate to modifier 59? |
| q03 | 1 | 1 | 1 | None | 0.994 | pass | What is a Medically Unlikely Edit (MUE)? |
| q04 | 1 | 1 | 1 | None | 0.834 | pass | What does a Correct Coding Modifier Indicator of 0 versus 1 mean for a PTP edit? |
| q05 | 1 | 1 | 2 | None | 1.0 | pass | Can an E&M service be reported on the same day as a minor surgical procedure? |
| q06 | 1 | 1 | 1 | None | 0.997 | pass | Can an add-on code be reported without its primary procedure code? |
| q07 | 1 | 1 | 1 | None | 0.983 | pass | When should an unlisted procedure code be reported? |
| q08 | 1 | 3 | 1 | None | 0.99 | pass | What does the CPT 'separate procedure' designation mean for reporting? |
| q09 | 1 | 1 | 1 | None | 0.99 | pass | How does NCCI handle procedures that are mutually exclusive? |
| q10 | 1 | 1 | 1 | None | 0.976 | pass | How should monitored anesthesia care be reported? |
| q11 | 1 | 1 | 1 | None | 0.783 | pass | How is Mohs micrographic surgery reported with other skin procedures? |
| q12 | 1 | 1 | 1 | None | 1.0 | pass | If a diagnostic arthroscopy leads to a surgical arthroscopy in the same session, can both be reported? |
| q13 | 1 | 1 | 1 | None | 1.0 | pass | Can a diagnostic endoscopy be reported separately when a surgical endoscopy is performed at the same session? |
| q14 | 1 | 1 | 1 | None | 0.998 | pass | How are presumptive and definitive drug testing codes reported? |
| q15 | 1 | 2 | 1 | None | 0.997 | pass | Can hydration be reported separately when given with chemotherapy administration? |
| q16 | 1 | 1 | 4 | None | 0.999 | pass | How can a provider request reconsideration of an NCCI edit or appeal a denial? |
| q17 | 1 | 2 | 1 | None | 1.0 | pass | What is the purpose of the NCCI program? |
| q18 | 1 | 5 | 1 | None | 1.0 | pass | Is the E&M visit where the decision for major surgery is made separately reportable, and with which modifier? |
| q19 | 1 | 1 | 1 | 1 | 0.976 | pass | When can CPT code 69990 for the operating microscope be reported? |
| q20 | 5 | 3 | 3 | 1 | 0.994 | pass | Which edits apply to CPT 64450 nerve blocks given by the anesthesiologist? |
| n01 | (negative) | | | | 0.018 | blocked | What is the 2026 Medicare Part B monthly premium? |
| n02 | (negative) | | | | 0.0 | blocked | How do I reset my password for the CMS Enterprise Portal? |
| n03 | (negative) | | | | 0.027 | blocked | Which insulins are on the Medicare Part D formulary? |
| n04 | (negative) | | | | 0.001 | blocked | What is the average hospital price of an MRI in Ohio? |
| h01 | (hard negative) | | | | 0.795 | pass | What is the MUE value for CPT 64450? |
| h02 | (hard negative) | | | | 0.489 | pass | Is there a PTP edit between CPT 93000 and 99214, and what is its correct coding modifier indicator? |
| h03 | (hard negative) | | | | 0.992 | pass | What does the Medicaid NCCI program say about edits for durable medical equipment? |
| h04 | (hard negative) | | | | 0.018 | blocked | What is the 2026 Medicare physician fee schedule payment for CPT 99214? |
| h05 | (hard negative) | | | | 0.842 | pass | How many units of CPT 97110 does the MUE allow per day? |
| h06 | (hard negative) | | | | 0.615 | pass | What is the OPPS APC payment rate for HCPCS G0463? |
| h07 | (hard negative) | | | | 0.896 | pass | Which ICD-10 diagnosis codes support medical necessity for CPT 93000? |

## Relevance gate calibration

Lowest positive top score: 0.783. Highest negative top score: 0.027.
Separable: any threshold between them works; midpoint = **0.405** (set NCCI_MIN_RELEVANCE, or NCCI_MIN_DENSE_SIM without a reranker).

| threshold | positives passed | negatives blocked |
|---|---|---|
| 0.00 | 20/20 | 0/4 |
| 0.02 | 20/20 | 3/4 |
| 0.03 | 20/20 | 4/4 |
| 0.78 | 20/20 | 4/4 |
| 0.83 | 19/20 | 4/4 |
| 0.95 | 18/20 | 4/4 |
| 0.98 | 15/20 | 4/4 |
| 0.99 | 13/20 | 4/4 |
| 1.00 | 0/20 | 4/4 |

Hard negatives passing the gate at 0.1: **6/7** (top scores 0.79, 0.49, 0.99, 0.02, 0.84, 0.61, 0.90). These are in-domain, so retrieval correctly finds related policy; the answer layer must handle them.

## Answers

- Positives answered: 20/20; citing an expected section: 20/20
- Hard negatives handled cleanly (abstained, or no invented value): **6/7**
- Sentences removed by the claim check: 8 (in 3 positive and 3 hard-negative answers)

**q01** When is it appropriate to use modifier 59?  
answerable=True cited_expected=True  
Modifier 59 is appropriate when procedures or services, other than E/M services, are not normally reported together but are distinct due to a different session, procedure, site, organ system, incision, lesion, or injury, and no more descriptive modifier is available. [1] It should only be used if no other modifier more appropriately describes the relationship between the procedure codes. [2] Modifier 59 may be appended when procedures are performed at separate patient encounters or at separate anatomic sites on the same date of service. [3] Modifier 59 may also be used for separate and distinct timed services provided in separate and distinct time blocks. [4] Modifier 59 should not be used with E/M services. [1]

**q02** What do modifiers XE, XS, XP, and XU mean, and how do they relate to modifier 59?  
answerable=True cited_expected=True  
Modifiers XE, XS, XP, and XU provide greater reporting specificity in situations where modifier 59 was previously reported and may be used in lieu of modifier 59 whenever possible. XE indicates a separate encounter, XS indicates a separate organ or structure, XP indicates a different practitioner, and XU indicates an unusual non-overlapping service. [1] Modifier 59 should only be used if no other modifier, such as XE, XP, XS, or XU, more appropriately describes the relationship between the procedure codes. [2] Modifiers 59, XE, or XS may be appended to indicate that procedures are different when performed at separate patient encounters or separate anatomic sites on the same date of service. [3] Modifiers 59, XE, XP, XS, and XU must only be used when the proper criteria for their use are met and not simply to bypass an NCCI PTP edit. [4]

**q03** What is a Medically Unlikely Edit (MUE)?  
answerable=True cited_expected=True  
A Medically Unlikely Edit (MUE) is a unit of service edit established by CMS that defines the maximum units of service (UOS) that may be reported for a HCPCS/CPT code on the vast majority of appropriately reported claims by the same provider or supplier for the same beneficiary on the same date of service. [1] MUEs are designed to prevent payment for a potentially inappropriate number or quantity of the same service on a single day. [2] All claims submitted to Medicare Administrative Contractors (MACs), Durable Medical Equipment (DME) MACs, and outpatient facility services claims are tested against MUEs. [1]

**q04** What does a Correct Coding Modifier Indicator of 0 versus 1 mean for a PTP edit?  
answerable=True cited_expected=True  
A Correct Coding Modifier Indicator (CCMI) of "0" means that NCCI PTP-associated modifiers cannot be used to bypass the edit. [1] A CCMI of "1" means that NCCI PTP-associated modifiers may be used to bypass an edit under appropriate circumstances. [1]

**q05** Can an E&M service be reported on the same day as a minor surgical procedure?  
answerable=True cited_expected=True  
In general, E&M services performed on the same date as a minor surgical procedure are included in the payment for the procedure and are not separately reportable. [1] However, if there is a significant and separately identifiable E&M service unrelated to the decision to perform the minor surgical procedure, it may be reported separately with modifier 25. [1] The E&M service and minor surgical procedure do not require different diagnoses to be reported separately. [1]

**q06** Can an add-on code be reported without its primary procedure code?  
answerable=True cited_expected=True  
Add-on Codes (AOCs) describe services that can only be reported in addition to a primary procedure. [1] An AOC is rarely eligible for payment if it is the only procedure reported by a practitioner. [2] For Type 1 AOCs, only the defined primary codes may be reported with the AOC. [2] For Type 2 and Type 3 AOCs, the list of acceptable primary codes may be determined by the MAC or partially defined by CPT/HCPCS files. [3] Normally, the AOC and primary code are reported for the same date of service, but there are rare exceptions where they may be reported on different dates. [3]

Not covered by the manual: The manual does not list every possible exception or name all AOCs.

**q07** When should an unlisted procedure code be reported?  
answerable=True cited_expected=True  
An unlisted procedure code should be reported when a service is not accurately described by any other HCPCS/CPT code. [1] If no HCPCS/CPT code describes a laboratory procedure, a miscellaneous or unlisted procedure code should be reported with a single unit of service. [2] For molecular pathology, if no CPT code accurately describes the procedure, CPT code 81479 (Unlisted molecular pathology procedure) may be reported with one unit of service. [3]

**q08** What does the CPT 'separate procedure' designation mean for reporting?  
answerable=True cited_expected=True  
If a CPT code descriptor includes the term 'separate procedure,' the code may not be reported separately with a related procedure performed in an anatomically related region, often through the same skin incision, orifice, or surgical approach. [1] A 'separate procedure' code may be reported if performed at a separate patient encounter on the same date of service or in an anatomically unrelated area, often through a separate skin incision, orifice, or surgical approach, and appropriate modifiers (59, XE, XS, or a more specific modifier) may be appended to indicate this. [1] CMS does not allow separate reporting of a 'separate procedure' when performed at the same patient encounter as another procedure in an anatomically related area through the same skin incision, orifice, or surgical approach. [2][3][4]

**q09** How does NCCI handle procedures that are mutually exclusive?  
answerable=True cited_expected=True  
Mutually exclusive procedures are those that cannot reasonably be performed at the same anatomic site or patient encounter, and such code pairs are included in the NCCI PTP edit tables. [1] When mutually exclusive procedures are reported together, the Column One code is eligible for payment, but the Column Two code is denied unless a clinically appropriate NCCI PTP-associated modifier is allowed and reported. [2] Some mutually exclusive edits allow the use of NCCI PTP-associated modifiers if the procedures are performed at different anatomic sites or separate patient encounters. [1] All mutually exclusive edits are now included in the single NCCI Column One/Column Two Correct Coding Edit Table. [3]

**q10** How should monitored anesthesia care be reported?  
answerable=True cited_expected=True  
Monitored anesthesia care is performed by an anesthesia practitioner who administers sedatives or other anesthetic agents while the patient remains responsive and breathing independently, and includes intraoperative monitoring, pre-anesthesia evaluation, prescription, administration of medications, and postoperative care. [1] Providers should report the HCPCS/CPT code that most specifically describes the monitored anesthesia care service performed, and should not unbundle components if a single code describes the service. [2] If a separate anesthesia practitioner provides monitored anesthesia care for a procedure, that service may be reported separately if medically reasonable and necessary. [3] Preparation and monitoring services are not separately reportable with anesthesia codes when performed as part of the anesthesia service, regardless of the mode of anesthesia. [4]

Not covered by the manual: The manual does not specify which CPT codes to use for monitored anesthesia care in general.

**q11** How is Mohs micrographic surgery reported with other skin procedures?  
answerable=True cited_expected=True  
Mohs micrographic surgery (CPT codes 17311-17315) includes skin biopsy, excision, and certain pathology services, so these codes (11102-11107, 11600-11646, 17260-17286, 88300-88309, 88329-88332) should not be reported separately with Mohs surgery. [1] If a diagnostic biopsy or frozen section pathology is performed before Mohs surgery, these may be reported separately with appropriate modifiers (59, XS, XU, or 58) to distinguish them from the Mohs procedure. [1] Repairs, grafts, and flaps are separately reportable with Mohs micrographic surgery. [1] Simple, intermediate, and complex wound repair codes (12001-13153) may be reported with Mohs surgery (17311-17315). [2][3]

**q12** If a diagnostic arthroscopy leads to a surgical arthroscopy in the same session, can both be reported?  
answerable=True cited_expected=True  
If a diagnostic arthroscopy leads to a surgical arthroscopy at the same patient encounter, only the surgical arthroscopy may be reported; the diagnostic arthroscopy is not separately reportable. [1]

**q13** Can a diagnostic endoscopy be reported separately when a surgical endoscopy is performed at the same session?  
answerable=True cited_expected=True  
A diagnostic endoscopy is not separately reportable with a surgical endoscopy performed at the same session; only the surgical endoscopy may be reported. [1][2] Surgical endoscopy includes diagnostic endoscopy, so the diagnostic portion is not separately billable. [2]

**q14** How are presumptive and definitive drug testing codes reported?  
answerable=True cited_expected=True  
Presumptive drug testing may be reported with CPT codes 80305-80307, and only one code from this range may be reported per date of service. [1] Definitive drug testing may be reported with HCPCS codes G0480-G0483 and G0659. [1] Only one definitive drug testing HCPCS code may be reported per date of service. [2] Presumptive drug testing codes differ based on the level of complexity of the testing methodology, while definitive drug testing codes differ based on the number of drug classes including metabolites tested. [1][2]
  
_removed:_ Definitive drug testing codes G0480-G0483 and G0659 are reported per day and shall not be reported with more than one unit of service per day. (code G0659 not in the quoted paragraph)

**q15** Can hydration be reported separately when given with chemotherapy administration?  
answerable=True cited_expected=True  
Hydration concurrent with chemotherapy is not separately reportable. [1] If therapeutic fluid administration is medically necessary before or after chemotherapy, it may be reported separately. [2] Hydration concurrent with other drug administration services is not separately reportable. [2]

**q16** How can a provider request reconsideration of an NCCI edit or appeal a denial?  
answerable=True cited_expected=True  
A provider may request reconsideration of an NCCI PTP edit, AOC edit, or MUE value by submitting a written request with rationale to NCCIPTPMUE@cms.hhs.gov, specifying the relevant codes, edit type, and NCCI program. [1] Appeals of NCCI-related denials must be submitted to the Medicare Administrative Contractor (MAC), not the NCCI contractor. [2]

**q17** What is the purpose of the NCCI program?  
answerable=True cited_expected=True  
NCCI coding policies are based on CPT conventions, Medicare policies, national society guidelines, standard practice, and current coding practice. [1] The NCCI program includes Procedure-to-Procedure (PTP) edits, Medically Unlikely Edits (MUEs), and Add-on Code (AOC) edits. [1]
  
_removed:_ The purpose of the NCCI program is to promote national correct coding methodologies and to control improper coding that leads to inappropriate payment of Part B claims. (quote not found in cited source: 'CMS developed the National Correct Coding Initiative (NCCI) program to promote n')

**q18** Is the E&M visit where the decision for major surgery is made separately reportable, and with which modifier?  
answerable=True cited_expected=True  
If an E&M service is performed on the same date of service as a major surgical procedure to decide whether to perform this surgical procedure, the E&M service is separately reportable with modifier 57. [1][2][3][4] Other preoperative E&M services on the same date of service as a major surgical procedure are included in the global payment for the procedure and are not separately reportable. [1][2][3][4]

**q19** When can CPT code 69990 for the operating microscope be reported?  
answerable=True cited_expected=True  
CPT code 69990 is bundled into all other surgical procedures and is not separately reportable with them, even if an operating microscope is used. [1] If CPT code 69990 is used with both a payable and a non-payable procedure, payment may be denied due to bundling edits, but the provider may submit the claim to the MAC with modifier 22 for possible payment adjustment. [1] CPT code 69990 cannot be reported with computer-assisted navigation codes 61781-61783 unless it is also reported with a procedure on the CMS list in MCPM Chapter 12, Section 20.4.5. [2] For further details on reporting CPT code 69990, refer to Chapter VIII, Section F (Operating Microscope). [3]

Not covered by the manual: The manual does not list the full set of specific codes from the MCPM Section 20.4.5.
  
_removed:_ CPT code 69990 may only be reported with procedures 61343, 61548, 61711, 62263, 62264, 62270, 62272, 62365, 64727, 64831, 64834, 64836, 64840, 64856, 64857, 64861, 64862, 64864, 64865, 64866, 64868, 64870, 64885, 64886, 64905, 64907, and 64910, as listed in the IOM Publication 100-04 MCPM, Chapter 12, Section 20.4.5. (code 61343, 61548, 61711, 62263, 62264, 62270, 62272, 62365, 64727, 64831, 64834, 64836, 64840, 64856, 64857, 64861, 64862, 64864, 64865, 64866, 64868, 64870, 64885, 64886, 64910 not in the quoted paragraph)

**q20** Which edits apply to CPT 64450 nerve blocks given by the anesthesiologist?  
answerable=True cited_expected=True  
CPT code 64450 shall not be reported by a surgeon for anesthesia for a surgical procedure, but if performed as a therapeutic or diagnostic injection unrelated to the surgical procedure, it may be reported separately. [1] A physician performing a surgical or medical procedure shall not report CPT code 64450 for anesthesia for that procedure. [2] An anesthesiologist may report CPT code 64450 for postoperative pain management separately from an anesthesia 0XXXX code only if the intraoperative anesthesia is general, spinal, or epidural, and the nerve block is not required for intraoperative anesthesia; modifier 59 or XU may be used in this case. [3] Only one unit of service of CPT code 64450 may be reported per patient encounter, regardless of the number of injections needed to block a nerve and its branches. [4]

Not covered by the manual: The manual does not list specific PTP code-pair edits or MUE values for CPT 64450.

**h01** What is the MUE value for CPT 64450?  
answerable=True clean=True  
For CPT code 64450, only one unit of service may be reported per patient encounter, regardless of the number of injections needed to block the nerve and its branches. [1] All injections into the nerve and its branches at a single patient encounter are considered a single unit of service for CPT code 64450. [1]

Not covered by the manual: The manual does not list a specific numeric MUE value for CPT 64450.

**h02** Is there a PTP edit between CPT 93000 and 99214, and what is its correct coding modifier indicator?  
answerable=False clean=True  
The passages explain general PTP edit and CCMI policy but do not specify if a PTP edit exists between CPT 93000 and 99214 or what the CCMI is for this pair.
  
_removed:_ The manual does not list whether there is a PTP edit between CPT 93000 and 99214 or the correct coding modifier indicator for this code pair. (code 93000, 99214 not in the quoted paragraph)
  
_removed:_ The manual explains that each NCCI PTP edit has a Correct Coding Modifier Indicator (CCMI), but the specific value for CPT 93000 and 99214 must be found in the CMS NCCI PTP edits data files. (code 93000, 99214 not in the quoted paragraph)

**h03** What does the Medicaid NCCI program say about edits for durable medical equipment?  
answerable=True clean=False  
The manual states that Medically Unlikely Edits (MUEs) in the NCCI program are applicable to claims submitted to Durable Medical Equipment (DME) MACs. [1] The manual notes that requests regarding NCCI edits should specify if the edit type is for Durable Medical Equipment and whether it concerns the Medicare or Medicaid NCCI program. [2] The NCCI program includes Procedure-to-Procedure (PTP) edits, Medically Unlikely Edits (MUEs), and Add-on Code (AOC) edits, but the manual does not specify which of these apply to Medicaid DME claims. [3]

Not covered by the manual: The manual does not describe Medicaid NCCI edits for durable medical equipment in detail.

**h04** What is the 2026 Medicare physician fee schedule payment for CPT 99214?  
answerable=False clean=True  
I couldn't find this in the 2026 Medicare NCCI Policy Manual. Try rephrasing, or name the code, modifier, or chapter you mean.

**h05** How many units of CPT 97110 does the MUE allow per day?  
answerable=False clean=True  
None of the provided passages state the specific MUE value for CPT code 97110.
  
_removed:_ The manual explains that MUE values are assigned to each HCPCS/CPT code based on specific criteria. (quote not found in cited source: 'The MUE value for each HCPCS/CPT code are based on one or more of the following ')
  
_removed:_ Section V of Chapter I provides general information about MUEs but does not list the MUE value for CPT code 97110. (code 97110 not in the quoted paragraph)

**h06** What is the OPPS APC payment rate for HCPCS G0463?  
answerable=False clean=True  
The passages discuss when G0463 may be reported and general OPPS reporting requirements, but do not state the APC payment rate for G0463.

**h07** Which ICD-10 diagnosis codes support medical necessity for CPT 93000?  
answerable=False clean=True  
None of the provided passages mention ICD-10 diagnosis codes or medical necessity criteria for CPT 93000.
  
_removed:_ The manual does not list any ICD-10 diagnosis codes that support medical necessity for CPT 93000. (no valid source)

