# Evaluation report

Settings: embed=text-embedding-3-large, reranker=BAAI/bge-reranker-base, chat=gpt-4.1, top_k=6, min_relevance=0.3

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
| n05 | (negative) | | | | 0.015 | blocked | How do I enroll in Medicare Part A when I turn 65? |
| n06 | (negative) | | | | 0.045 | blocked | What are the early symptoms of type 2 diabetes? |
| n07 | (negative) | | | | 0.0 | blocked | When is the deadline to file my federal income tax return? |
| n08 | (negative) | | | | 0.004 | blocked | When is the Medicare open enrollment period for 2026? |
| n09 | (negative) | | | | 0.051 | blocked | Which hospitals in Texas have the best cardiology ratings? |
| n10 | (negative) | | | | 0.005 | blocked | What is the copay for a generic drug under Medicare Part D? |
| h03 | (hard negative) | | | | 0.992 | pass | What does the Medicaid NCCI program say about edits for durable medical equipment? |
| h04 | (hard negative) | | | | 0.018 | blocked | What is the 2026 Medicare physician fee schedule payment for CPT 99214? |
| h06 | (hard negative) | | | | 0.615 | pass | What is the OPPS APC payment rate for HCPCS G0463? |
| h07 | (hard negative) | | | | 0.896 | pass | Which ICD-10 diagnosis codes support medical necessity for CPT 93000? |
| h08 | (hard negative) | | | | 0.02 | blocked | What are the 2026 work RVUs for CPT 99213? |
| h09 | (hard negative) | | | | 0.036 | blocked | Which ICD-10-CM code should be reported for a medial meniscus tear of the right knee? |
| h10 | (hard negative) | | | | 0.003 | blocked | Does Medicare Advantage require prior authorization for total knee arthroplasty CPT 27447? |
| h11 | (hard negative) | | | | 0.003 | blocked | How much does Medicare pay for an office visit billed with CPT 99214 in California? |
| h12 | (hard negative) | | | | 0.04 | blocked | Is CPT 27447 covered for patients under 50 under a local coverage determination? |
| h13 | (hard negative) | | | | 0.354 | pass | What is the timely filing limit for submitting a corrected claim with modifier 59? |
| h14 | (hard negative) | | | | 0.017 | blocked | What is the 2026 Medicare anesthesia conversion factor? |
| h15 | (hard negative) | | | | 0.317 | pass | How many days is the global surgical period for CPT 27447? |
| f01 | (fact: found) | | | | 0.795 | pass | What is the MUE value for CPT 64450? |
| f02 | (fact: found) | | | | 0.489 | pass | Is there a PTP edit between CPT 93000 and 99214, and what is its correct coding modifier indicator? |
| f03 | (fact: found) | | | | 0.842 | pass | How many units of CPT 97110 does the MUE allow per day? |
| f04 | (fact: found) | | | | 0.995 | pass | Can CPT 29880 and 29881 be reported together for the same knee? |
| f05 | (fact: found) | | | | 0.03 | pass | Is the PTP edit between 0001A and 0591T still active? |
| f06 | (fact: found) | | | | 0.987 | pass | Which codes are bundled into CPT 29881? |

## Relevance gate calibration

Lowest positive top score: 0.783. Highest negative top score: 0.051.
Separable: any threshold between them works; midpoint = **0.417** (set NCCI_MIN_RELEVANCE, or NCCI_MIN_DENSE_SIM without a reranker).

Current threshold: **0.3** (row in bold).

| threshold | wrong refusals (positives blocked) | wrong passes (negatives reaching the LLM) | hard negatives passed to the answer layer |
|---|---|---|---|
| 0.01 | 0/20 (0%) | 5/10 (50%) | 10/12 (83%) |
| 0.02 | 0/20 (0%) | 3/10 (30%) | 8/12 (67%) |
| 0.05 | 0/20 (0%) | 1/10 (10%) | 5/12 (42%) |
| 0.10 | 0/20 (0%) | 0/10 (0%) | 5/12 (42%) |
| 0.20 | 0/20 (0%) | 0/10 (0%) | 5/12 (42%) |
| **0.30** | 0/20 (0%) | 0/10 (0%) | 5/12 (42%) |
| 0.40 | 0/20 (0%) | 0/10 (0%) | 3/12 (25%) |
| 0.50 | 0/20 (0%) | 0/10 (0%) | 3/12 (25%) |
| 0.60 | 0/20 (0%) | 0/10 (0%) | 3/12 (25%) |
| 0.70 | 0/20 (0%) | 0/10 (0%) | 2/12 (17%) |
| 0.80 | 1/20 (5%) | 0/10 (0%) | 2/12 (17%) |
| 0.90 | 2/20 (10%) | 0/10 (0%) | 1/12 (8%) |

Thresholds with no gate error on this set: 0.10 to 0.70. A low value in that range favours answering (a wrong 'not found' is costly for a coder); later layers catch weak answers.

Hard negatives passing the gate at 0.3: **5/12** (top scores 0.00, 0.00, 0.02, 0.02, 0.02, 0.04, 0.04, 0.32, 0.35, 0.61, 0.90, 0.99). These are in-domain, so retrieval correctly finds related policy; the answer layer must handle them.

**Edit-table facts:** looked up 6/6; linked manual section in the passages 4/4 (questions with an expected section)

## Answers

- Positives answered: 20/20; citing an expected section: 20/20
- Fact questions answered correctly: **6/6**; citing the table row: 6; also citing the manual (the why): 5
- Hard negatives handled cleanly (abstained, or no invented value): **11/12**
- Sentences removed by the claim check: 7 (in 3 positive and 1 hard-negative answers)

**q01** When is it appropriate to use modifier 59?  
answerable=True cited_expected=True  
Modifier 59 is appropriate when procedures or services, other than E/M services, that are not normally reported together are performed under circumstances such as a different session, different site or organ system, separate incision, lesion, or injury, and no more descriptive modifier is available. [1] Modifier 59 should only be used if no other modifier more appropriately describes the relationship between the procedure codes. [2] Modifier 59 is appropriate for different anatomic sites during the same encounter only when procedures not ordinarily performed together are done on different organs, regions, or non-contiguous lesions in different regions of the same organ. [3] Modifier 59 should not be used to bypass a PTP edit unless the proper criteria are met and documentation supports its use. [1] Modifier 59 may also be used for timed services when two separate and distinct time blocks are provided. [4]

**q02** What do modifiers XE, XS, XP, and XU mean, and how do they relate to modifier 59?  
answerable=True cited_expected=True  
Modifiers XE, XS, XP, and XU were developed to provide greater reporting specificity in situations where modifier 59 was previously reported and may be used in lieu of modifier 59 whenever possible. [1] XE is used for a separate encounter on the same date of service, XS for a separate organ or structure, XP for a different practitioner, and XU for a distinct service that does not overlap usual components of the main service. [1] Modifier 59 should only be used if no other modifier, such as XE, XP, XS, or XU, more appropriately describes the relationship between the procedures. [2] Modifiers 59, XE, or XS may be used to indicate different procedures or surgeries performed at separate encounters or separate anatomic sites on the same date of service. [3] These modifiers must only be used when the proper criteria are met and should not be used to bypass an edit inappropriately. [4]

**q03** What is a Medically Unlikely Edit (MUE)?  
answerable=True cited_expected=True  
A Medically Unlikely Edit (MUE) is a unit of service edit that sets the maximum number of units of service (UOS) that can be reported for a specific HCPCS/CPT code on the vast majority of appropriately reported claims by the same provider or supplier for the same beneficiary on the same date of service. [1] MUEs are designed to prevent payment for a potentially inappropriate number or quantity of the same service on a single day. [2] All claims submitted to Medicare Administrative Contractors (MACs), Durable Medical Equipment (DME) MACs, and outpatient facility services claims are tested against MUEs. [1]

**q04** What does a Correct Coding Modifier Indicator of 0 versus 1 mean for a PTP edit?  
answerable=True cited_expected=True  
A Correct Coding Modifier Indicator (CCMI) of '0' means that NCCI PTP-associated modifiers cannot be used to bypass the edit. [1] A CCMI of '1' means that NCCI PTP-associated modifiers may be used to bypass an edit under appropriate circumstances. [1]

**q05** Can an E&M service be reported on the same day as a minor surgical procedure?  
answerable=True cited_expected=True  
In general, E&M services performed on the same date as a minor surgical procedure are included in the payment for the procedure and are not separately reportable. [1] However, if there is a significant and separately identifiable E&M service unrelated to the decision to perform the minor surgical procedure, it may be reported separately with modifier 25. [1] The E&M service and minor surgical procedure do not require different diagnoses to be reported separately. [1] Being a new patient alone does not justify reporting an E&M service separately on the same day as a minor surgical procedure; the same rules apply to new and established patients. [1]

**q06** Can an add-on code be reported without its primary procedure code?  
answerable=True cited_expected=True  
Add-on codes (AOCs) describe services that can only be reported in addition to a primary procedure and generally cannot be reported without their designated primary procedure code. [1] An add-on code is rarely eligible for payment if it is the only procedure reported by a practitioner. [2] For Type 1 add-on code edits, only the primary codes defined in the CPT or HCPCS files are acceptable, and other codes should not be used as primary codes. [2] For Type 2 and Type 3 add-on code edits, the CPT or HCPCS files may not define all primary codes, so Medicare contractors may develop their own lists of acceptable primary codes. [3] Normally, the add-on code and its primary code are reported for the same date of service, but there are rare exceptions where they may be reported on different dates. [3]

**q07** When should an unlisted procedure code be reported?  
answerable=True cited_expected=True  
An unlisted procedure code should be reported when a service is not accurately described by any other HCPCS/CPT code. [1] If no HCPCS/CPT code describes a laboratory procedure, a miscellaneous or unlisted procedure code should be reported with a single unit of service. [2] For molecular pathology, if no CPT code accurately describes the procedure, CPT code 81479 (Unlisted molecular pathology procedure) may be reported with one unit of service. [3] If an abbreviated right heart catheterization is medically reasonable and necessary, it may be reported with CPT code 93799 (Unlisted cardiovascular service or procedure). [4]

**q08** What does the CPT 'separate procedure' designation mean for reporting?  
answerable=True cited_expected=True  
If a CPT code descriptor includes the term 'separate procedure,' the code may not be reported separately with a related procedure when performed in an anatomically related region, often through the same skin incision, orifice, or surgical approach. [1] A 'separate procedure' code may be reported with another procedure if it is performed at a separate patient encounter or in an anatomically unrelated area, and appropriate modifiers (59, XE, XS, or a more specific modifier) may be used to indicate this. [1] CMS does not allow separate reporting of a 'separate procedure' when performed at the same encounter as another procedure in an anatomically related area through the same approach. [2][3][4] A 'separate procedure' is not separately reportable if performed in a region anatomically related to other procedures through the same approach. [5]

**q09** How does NCCI handle procedures that are mutually exclusive?  
answerable=True cited_expected=True  
NCCI handles mutually exclusive procedures by including pairs of HCPCS/CPT codes that cannot reasonably be performed together in the NCCI PTP edit tables. [1] Some mutually exclusive edits allow the use of NCCI PTP-associated modifiers if the procedures are performed at different anatomic sites or separate encounters. [1] When both codes in a mutually exclusive edit pair are reported for the same patient on the same date, only the Column One code is payable unless an allowed modifier is used. [2] All mutually exclusive edits are now included in the single NCCI PTP Column One/Column Two Correct Coding Edit Table. [3]

**q10** How should monitored anesthesia care be reported?  
answerable=True cited_expected=True  
Monitored anesthesia care is performed by an anesthesia practitioner and is recognized as a payable service by CMS if it is medically reasonable and necessary. [1] Monitored anesthesia care includes intraoperative monitoring, pre-anesthesia evaluation, prescription and administration of anesthesia care, and postoperative anesthesia care. [1] Providers should report the HCPCS/CPT code that most specifically describes the monitored anesthesia care service performed, and only if all services described by the code are performed. [2] A separate anesthesia service for monitored anesthesia care may be reported by an anesthesia practitioner if it is medically reasonable and necessary and performed by a provider other than the one performing the surgical or medical procedure. [3] Preparation and monitoring services are not separately reportable with anesthesia service HCPCS/CPT codes when performed as part of the monitored anesthesia care. [4]

**q11** How is Mohs micrographic surgery reported with other skin procedures?  
answerable=True cited_expected=True  
Mohs micrographic surgery (CPT codes 17311-17315) includes skin biopsy, excision, and pathology services, so these codes (11102-11107, 11600-11646, 17260-17286, 88300-88309, 88329-88332) should not be reported separately with Mohs surgery. However, if a diagnostic biopsy and frozen section pathology are performed before Mohs surgery, they may be reported separately with modifier 59, XS, XU, or 58. Repairs, grafts, and flaps are separately reportable with Mohs micrographic surgery. [1] Simple, intermediate, and complex wound repair codes may be reported with Mohs surgery (CPT codes 17311-17315). [2][3]

**q12** If a diagnostic arthroscopy leads to a surgical arthroscopy in the same session, can both be reported?  
answerable=True cited_expected=True  
If a diagnostic arthroscopy leads to a surgical arthroscopy at the same session, only the surgical arthroscopy may be reported; the diagnostic arthroscopy is not separately reportable. [1]

**q13** Can a diagnostic endoscopy be reported separately when a surgical endoscopy is performed at the same session?  
answerable=True cited_expected=True  
A diagnostic endoscopy is not separately reportable with a surgical endoscopy when both are performed at the same session; only the surgical endoscopy may be reported. [1][2] However, if a diagnostic endoscopy leads to the decision to perform a more extensive non-endoscopic (open or laparoscopic) procedure, the diagnostic endoscopy may be separately reportable if medically necessary and properly documented. [3] This policy applies to all endoscopic procedures, not just those of a specific organ system. [2]

**q14** How are presumptive and definitive drug testing codes reported?  
answerable=True cited_expected=True  
Presumptive drug testing may be reported with CPT codes 80305-80307, and only one code from this range may be reported per date of service. [1] Definitive drug testing may be reported with HCPCS codes G0480-G0483 and G0659. [1] Only one definitive drug testing HCPCS code may be reported per date of service. [2] Presumptive and definitive drug testing codes are reported per day and shall not be reported with more than one unit of service per day. [3]

**q15** Can hydration be reported separately when given with chemotherapy administration?  
answerable=True cited_expected=True  
Hydration concurrent with chemotherapy is not separately reportable. [1] Hydration concurrent with other drug administration services is also not separately reportable. [2] However, if therapeutic fluid administration is medically necessary before or after chemotherapy (such as for correction of dehydration or prevention of nephrotoxicity), it may be reported separately. [2]

**q16** How can a provider request reconsideration of an NCCI edit or appeal a denial?  
answerable=True cited_expected=True  
A provider may request reconsideration of an NCCI PTP edit, AOC edit, or MUE value by submitting a written request with rationale to NCCIPTPMUE@cms.hhs.gov, specifying the relevant codes, edit type, and program. [1] The written request for reconsideration should include a rationale and suggestion for the proposed change. [2] If a claim is denied due to an NCCI edit, the provider must submit an appeal to the Medicare Administrative Contractor (MAC), not to the NCCI contractor. [3]

**q17** What is the purpose of the NCCI program?  
answerable=True cited_expected=True  
NCCI coding policies are based on CPT conventions, Medicare policies, national society guidelines, standard practice, and current coding practice. [1] The NCCI program includes Procedure-to-Procedure (PTP) edits, Medically Unlikely Edits (MUEs), and Add-on Code (AOC) edits. [1]
  
_removed:_ The purpose of the NCCI program is to promote national correct coding methodologies and to control improper coding that leads to inappropriate payment of Part B claims. (quote not found in cited source: 'CMS developed the National Correct Coding Initiative (NCCI) program to promote n')

**q18** Is the E&M visit where the decision for major surgery is made separately reportable, and with which modifier?  
answerable=True cited_expected=True  
If an E&M service is performed on the same date as a major surgical procedure to decide whether to perform the surgery, it is separately reportable with modifier 57. [1][2][3][4] Other preoperative E&M services on the same date as a major surgical procedure are included in the global payment and are not separately reportable. [1][2][3][4]

**q19** When can CPT code 69990 for the operating microscope be reported?  
answerable=True cited_expected=True  
If CPT code 69990 is used with multiple procedures and only one is on the CMS list, payment may be denied due to bundling edits, but the provider may submit the claim to the MAC with modifier 22 on the payable procedure code, and the MAC may adjust payment at its discretion. [1] CPT code 69990 cannot be reported with procedures not on the CMS list, even if the CPT codebook allows it; CMS policy is more restrictive. [2] CMS limits payment for CPT code 69990 to procedures listed in the IOM Publication 100-04 MCPM Chapter 12 Section 20.4.5. [3] For reporting CPT code 69990, coders should refer to Chapter VIII, Section F (Operating Microscope) for detailed policy. [4]
  
_removed:_ CPT code 69990 may only be reported with procedures listed in the IOM Publication 100-04 MCPM, Chapter 12, Section 20.4.5, specifically codes 61304, 61305, 61312, 61314, 61500, 61501, 61510, 61512, 61518, 61519, 61520, 61521, 61526, 61530, 61531, 61533, 61534, 61535, 61536, 61537, 61538, 61539, 61540, 61541, 61542, 61543, 61544, 61545, 61546, 61548, 61550, 61552, 61556, 61557, 61558, 61559, 61560, 61561, 61563, 61564, 61565, 61566, 61567, 61568, 61570, 61571, 61575, 61576, 61580, 61581, 61582, 61583, 61584, 61585, 61600, 61601, 61605, 61606, 61607, 61608, 61609, 61610, 61612, 61613, 61615, 61616, 61618, 61619, 61623, 61624, 61626, 61630, 61631, 61635, 61640, 61641, 61642, 61650, 61651, 61652, 61680, 61681, 61700, 61702, 61703, 61705, 61708, 61710, 61711, 61712, 61713, 61720, 61722, 61723, 61725, 61750, 61751, 61760, 61770, 61790, 61791, 61796, 61797, 61798, 61799, 61800, 61810, 61820, 61835, 61840, 61850, 61860, 61863, 61864, 61867, 61868, 61880, 62100, 62116, 62121, 62141, 62146, 62147, 62148, 62161, 62162, 62163, 62165, 62180, 62192, 62193, 62194, 62200, 62201, 62220, 62223, 62230, 62252, 62256, 62258, 62263, 62264, 62270, 62272, 62273, 62280, 62281, 62282, 62284, 62290, 62291, 62292, 62310, 62311, 62318, 62319, 62320, 62321, 62322, 62323, 62324, 62325, 62326, 62327, 62328, 62329, 62350, 62351, 62360, 62361, 62362, 62365, 62367, 62368, 62369, 62370, 62380, 63001, 63003, 63005, 63011, 63012, 63015, 63016, 63017, 63020, 63030, 63035, 63040, 63042, 63043, 63044, 63045, 63046, 63047, 63048, 63050, 63051, 63055, 63056, 63057, 63064, 63075, 63076, 63077, 63078, 63081, 63082, 63085, 63086, 63087, 63088, 63090, 63091, 63101, 63102, 63103, 63170, 63172, 63173, 63180, 63182, 63185, 63190, 63191, 63194, 63195, 63196, 63197, 63198, 63199, 63200, 63250, 63251, 63252, 63265, 63266, 63267, 63268, 63270, 63271, 63272, 63273, 63275, 63276, 63277, 63278, 63280, 63281, 63282, 63283, 63285, 63287, 63290, 63295, 63300, 63301, 63302, 63303, 63304, 63305, 63306, 63307, 63308, 63310, 63311, 63312, 63313, 63314, 63315, 63316, 63317, 63318, 63319, 63320, 63321, 63322, 63323, 63330, 63331, 63332, 63333, 63334, 63335, 63340, 63341, 63342, 63343, 63344, 63345, 63346, 63347, 63348, 63349, 63350, 63351, 63352, 63353, 63354, 63355, 63356, 63357, 63358, 63359, 63360, 63361, 63362, 63363, 63364, 63365, 63366, 63367, 63368, 63369, 63370, 63371, 63372, 63373, 63374, 63375, 63376, 63377, 63378, 63379, 63380, 63381, 63382, 63383, 63384, 63385, 63386, 63387, 63388, 63389, 63390, 63391, 63392, 63393, 63394, 63395, 63396, 63397, 63398, 63399, 63600, 63610, 63615, 63620, 63621, 63650, 63655, 63661, 63662, 63663, 63664, 63685, 63688, 63700, 63702, 63704, 63706, 63707, 63709, 63710, 63740, 63741, 63744, 63745, 63746, 63747, 63748, 63749, 63750, 63751, 63752, 63753, 63754, 63755, 63756, 63757, 63758, 63759, 63760, 63761, 63762, 63763, 63764, 63765, 63766, 63767, 63768, 63769, 63770, 63771, 63772, 63773, 63774, 63775, 63776, 63777, 63778, 63779, 63780, 63781, 63782, 63783, 63784, 63785, 63786, 63787, 63788, 63789, 63790, 63791, 63792, 63793, 63794, 63795, 63796, 63797, 63798, 63799, 63800, 63801, 63802, 63803, 63804, 63805, 63806, 63807, 63808, 63809, 63810, 63811, 63812, 63813, 63814, 63815, 63816, 63817, 63818, 63819, 63820, 63821, 63822, 63823, 63824, 63825, 63826, 63827, 63828, 63829, 63830, 63831, 63832, 63833, 63834, 63835, 63836, 63837, 63838, 63839, 63840, 63841, 63842, 63843, 63844, 63845, 63846, 63847, 63848, 63849, 63850, 63851, 63852, 63853, 63854, 63855, 63856, 63857, 63858, 63859, 63860, 63861, 63862, 63863, 63864, 63865, 63866, 63867, 63868, 63869, 63870, 63871, 63872, 63873, 63874, 63875, 63876, 63877, 63878, 63879, 63880, 63881, 63882, 63883, 63884, 63885, 63886, 63887, 63888, 63889, 63890, 63891, 63892, 63893, 63894, 63895, 63896, 63897, 63898, 63899, 63900, 63901, 63902, 63903, 63904, 63905, 63906, 63907, 63908, 63909, 63910, 63911, 63912, 63913, 63914, 63915, 63916, 63917, 63918, 63919, 63920, 63921, 63922, 63923, 63924, 63925, 63926, 63927, 63928, 63929, 63930, 63931, 63932, 63933, 63934, 63935, 63936, 63937, 63938, 63939, 63940, 63941, 63942, 63943, 63944, 63945, 63946, 63947, 63948, 63949, 63950, 63951, 63952, 63953, 63954, 63955, 63956, 63957, 63958, 63959, 63960, 63961, 63962, 63963, 63964, 63965, 63966, 63967, 63968, 63969, 63970, 63971, 63972, 63973, 63974, 63975, 63976, 63977, 63978, 63979, 63980, 63981, 63982, 63983, 63984, 63985, 63986, 63987, 63988, 63989, 63990, 63991, 63992, 63993, 63994, 63995, 63996, 63997, 63998, 63999, 64905, 64907. (code 61304, 61305, 61312, 61314, 61500, 61501, 61510, 61512, 61518, 61519, 61520, 61521, 61526, 61530, 61531, 61533, 61534, 61535, 61536, 61537, 61538, 61539, 61540, 61541, 61542, 61543, 61544, 61545, 61546, 61548, 61550, 61552, 61556, 61557, 61558, 61559, 61560, 61561, 61563, 61564, 61565, 61566, 61567, 61568, 61570, 61571, 61575, 61576, 61580, 61581, 61582, 61583, 61584, 61585, 61600, 61601, 61605, 61606, 61607, 61608, 61609, 61610, 61612, 61613, 61615, 61616, 61618, 61619, 61623, 61624, 61626, 61630, 61631, 61635, 61640, 61641, 61642, 61650, 61651, 61652, 61680, 61681, 61700, 61702, 61703, 61705, 61708, 61710, 61711, 61712, 61713, 61720, 61722, 61723, 61725, 61750, 61751, 61760, 61770, 61790, 61791, 61796, 61797, 61798, 61799, 61800, 61810, 61820, 61835, 61840, 61850, 61860, 61863, 61864, 61867, 61868, 61880, 62100, 62116, 62121, 62141, 62146, 62147, 62148, 62161, 62162, 62163, 62165, 62180, 62192, 62193, 62194, 62200, 62201, 62220, 62223, 62230, 62252, 62256, 62258, 62263, 62264, 62270, 62272, 62273, 62280, 62281, 62282, 62284, 62290, 62291, 62292, 62310, 62311, 62318, 62319, 62320, 62321, 62322, 62323, 62324, 62325, 62326, 62327, 62328, 62329, 62350, 62351, 62360, 62361, 62362, 62365, 62367, 62368, 62369, 62370, 62380, 63001, 63003, 63005, 63011, 63012, 63015, 63016, 63017, 63020, 63030, 63035, 63040, 63042, 63043, 63044, 63045, 63046, 63047, 63048, 63050, 63051, 63055, 63056, 63057, 63064, 63075, 63076, 63077, 63078, 63081, 63082, 63085, 63086, 63087, 63088, 63090, 63091, 63101, 63102, 63103, 63170, 63172, 63173, 63180, 63182, 63185, 63190, 63191, 63194, 63195, 63196, 63197, 63198, 63199, 63200, 63250, 63251, 63252, 63265, 63266, 63267, 63268, 63270, 63271, 63272, 63273, 63275, 63276, 63277, 63278, 63280, 63281, 63282, 63283, 63285, 63287, 63290, 63295, 63300, 63301, 63302, 63303, 63304, 63305, 63306, 63307, 63308, 63310, 63311, 63312, 63313, 63314, 63315, 63316, 63317, 63318, 63319, 63320, 63321, 63322, 63323, 63330, 63331, 63332, 63333, 63334, 63335, 63340, 63341, 63342, 63343, 63344, 63345, 63346, 63347, 63348, 63349, 63350, 63351, 63352, 63353, 63354, 63355, 63356, 63357, 63358, 63359, 63360, 63361, 63362, 63363, 63364, 63365, 63366, 63367, 63368, 63369, 63370, 63371, 63372, 63373, 63374, 63375, 63376, 63377, 63378, 63379, 63380, 63381, 63382, 63383, 63384, 63385, 63386, 63387, 63388, 63389, 63390, 63391, 63392, 63393, 63394, 63395, 63396, 63397, 63398, 63399, 63600, 63610, 63615, 63620, 63621, 63650, 63655, 63661, 63662, 63663, 63664, 63685, 63688, 63700, 63702, 63704, 63706, 63707, 63709, 63710, 63740, 63741, 63744, 63745, 63746, 63747, 63748, 63749, 63750, 63751, 63752, 63753, 63754, 63755, 63756, 63757, 63758, 63759, 63760, 63761, 63762, 63763, 63764, 63765, 63766, 63767, 63768, 63769, 63770, 63771, 63772, 63773, 63774, 63775, 63776, 63777, 63778, 63779, 63780, 63781, 63782, 63783, 63784, 63785, 63786, 63787, 63788, 63789, 63790, 63791, 63792, 63793, 63794, 63795, 63796, 63797, 63798, 63799, 63800, 63801, 63802, 63803, 63804, 63805, 63806, 63807, 63808, 63809, 63810, 63811, 63812, 63813, 63814, 63815, 63816, 63817, 63818, 63819, 63820, 63821, 63822, 63823, 63824, 63825, 63826, 63827, 63828, 63829, 63830, 63831, 63832, 63833, 63834, 63835, 63836, 63837, 63838, 63839, 63840, 63841, 63842, 63843, 63844, 63845, 63846, 63847, 63848, 63849, 63850, 63851, 63852, 63853, 63854, 63855, 63856, 63857, 63858, 63859, 63860, 63861, 63862, 63863, 63864, 63865, 63866, 63867, 63868, 63869, 63870, 63871, 63872, 63873, 63874, 63875, 63876, 63877, 63878, 63879, 63880, 63881, 63882, 63883, 63884, 63885, 63886, 63887, 63888, 63889, 63890, 63891, 63892, 63893, 63894, 63895, 63896, 63897, 63898, 63899, 63900, 63901, 63902, 63903, 63904, 63905, 63906, 63907, 63908, 63909, 63910, 63911, 63912, 63913, 63914, 63915, 63916, 63917, 63918, 63919, 63920, 63921, 63922, 63923, 63924, 63925, 63926, 63927, 63928, 63929, 63930, 63931, 63932, 63933, 63934, 63935, 63936, 63937, 63938, 63939, 63940, 63941, 63942, 63943, 63944, 63945, 63946, 63947, 63948, 63949, 63950, 63951, 63952, 63953, 63954, 63955, 63956, 63957, 63958, 63959, 63960, 63961, 63962, 63963, 63964, 63965, 63966, 63967, 63968, 63969, 63970, 63971, 63972, 63973, 63974, 63975, 63976, 63977, 63978, 63979, 63980, 63981, 63982, 63983, 63984, 63985, 63986, 63987, 63988, 63989, 63990, 63991, 63992, 63993, 63994, 63995, 63996, 63997, 63998, 63999 not in the quoted paragraph)

**q20** Which edits apply to CPT 64450 nerve blocks given by the anesthesiologist?  
answerable=True cited_expected=True  
According to the NCCI PTP edit tables, CPT code 64450 is the Column One code in 144 edits and the Column Two code in 6,110 edits, with common rationales including CPT Manual or CMS manual coding instruction, standards of medical/surgical practice, and misuse of codes. [1] CPT code 64450 shall not be reported by a surgeon for anesthesia for a surgical procedure, but if performed as a therapeutic or diagnostic injection unrelated to the surgical procedure, it may be reported separately. [2] A peripheral nerve block injection (CPT codes 64XXX, which includes 64450) for postoperative pain management may be reported separately with an anesthesia 0XXXX code only under specific conditions, and modifier 59 or XU may be used to indicate separate reporting for postoperative pain management. [3]

Not covered by the manual: The specific edit pairs and modifier indicators for each code pair involving 64450 are not listed here.
  
_removed:_ The physician performing a surgical or medical procedure shall not report a nerve block (CPT codes 64400-64530) for anesthesia for that procedure. (quote not found in cited source: 'The physician performing a surgical or medical procedure shall not report an epi')

**h03** What does the Medicaid NCCI program say about edits for durable medical equipment?  
answerable=True clean=False  
The NCCI program includes Medically Unlikely Edits (MUEs) that are applicable to claims submitted to Durable Medical Equipment (DME) MACs. [1] Requests for reconsideration of NCCI edits or MUE values must specify if the edit type is for Durable Medical Equipment. [2]

Not covered by the manual: The passages do not describe specific Medicaid NCCI edits for durable medical equipment.

**h04** What is the 2026 Medicare physician fee schedule payment for CPT 99214?  
answerable=False clean=True  
I couldn't find this in the 2026 Medicare NCCI Policy Manual. Try rephrasing, or name the code, modifier, or chapter you mean.

**h06** What is the OPPS APC payment rate for HCPCS G0463?  
answerable=False clean=True  
The passages discuss when G0463 may be reported under OPPS but do not state the APC payment rate for G0463.

**h07** Which ICD-10 diagnosis codes support medical necessity for CPT 93000?  
answerable=False clean=True  
None of the provided passages mention ICD-10 diagnosis codes or medical necessity criteria for CPT 93000.

**h08** What are the 2026 work RVUs for CPT 99213?  
answerable=False clean=True  
I couldn't find this in the 2026 Medicare NCCI Policy Manual. Try rephrasing, or name the code, modifier, or chapter you mean.

**h09** Which ICD-10-CM code should be reported for a medial meniscus tear of the right knee?  
answerable=False clean=True  
I couldn't find this in the 2026 Medicare NCCI Policy Manual. Try rephrasing, or name the code, modifier, or chapter you mean.

**h10** Does Medicare Advantage require prior authorization for total knee arthroplasty CPT 27447?  
answerable=False clean=True  
I couldn't find this in the 2026 Medicare NCCI Policy Manual. Try rephrasing, or name the code, modifier, or chapter you mean.

**h11** How much does Medicare pay for an office visit billed with CPT 99214 in California?  
answerable=False clean=True  
I couldn't find this in the 2026 Medicare NCCI Policy Manual. Try rephrasing, or name the code, modifier, or chapter you mean.

**h12** Is CPT 27447 covered for patients under 50 under a local coverage determination?  
answerable=False clean=True  
I couldn't find this in the 2026 Medicare NCCI Policy Manual. Try rephrasing, or name the code, modifier, or chapter you mean.

**h13** What is the timely filing limit for submitting a corrected claim with modifier 59?  
answerable=False clean=True  
None of the provided passages discuss timely filing limits or deadlines for submitting corrected claims with modifier 59.

**h14** What is the 2026 Medicare anesthesia conversion factor?  
answerable=False clean=True  
I couldn't find this in the 2026 Medicare NCCI Policy Manual. Try rephrasing, or name the code, modifier, or chapter you mean.

**h15** How many days is the global surgical period for CPT 27447?  
answerable=False clean=True  
None of the provided passages state the global surgical period for CPT 27447.
  
_removed:_ The manual defines major and minor surgical procedures by their global periods but does not specify the global period for code 27447. (code 27447 not in the quoted paragraph)

**f01** What is the MUE value for CPT 64450?  
answerable=True correct=True fact_cited=True manual_cited=True  
The MUE value for CPT code 64450 is 10 units of service. [1] The policy states that only one unit of service of CPT code 64450 may be reported per patient encounter, regardless of the number of injections needed to block the nerve and its branches. [2]

**f02** Is there a PTP edit between CPT 93000 and 99214, and what is its correct coding modifier indicator?  
answerable=True correct=True fact_cited=True manual_cited=True  
There is no NCCI PTP edit between CPT codes 93000 and 99214 in either order. [1] Because there is no edit listed for this code pair, there is no Correct Coding Modifier Indicator (CCMI) applicable. [2]

**f03** How many units of CPT 97110 does the MUE allow per day?  
answerable=True correct=True fact_cited=True manual_cited=True  
The MUE value for CPT code 97110 is 6 units of service per day. [1] This MUE is a per day edit based on clinical benchmarks (MAI of 3), but may be exceeded if medical review supports that more units were correctly reported and medically necessary. [2] CPT code 97110 is reported in fifteen-minute increments, so up to 6 units (90 minutes) may be reported per day unless medical review justifies more. [3]

**f04** Can CPT 29880 and 29881 be reported together for the same knee?  
answerable=True correct=True fact_cited=True manual_cited=True  
There is an active NCCI PTP edit for CPT codes 29880 and 29881, with 29880 as Column One and 29881 as Column Two; if both are reported for the same beneficiary on the same date, 29881 is denied unless the edit is bypassed with an appropriate modifier. [1] If both procedures are performed on the same knee at the same encounter, reporting both codes together is generally not allowed, and use of an NCCI modifier is not appropriate unless there is a distinct, separate anatomic site or encounter. [2]
  
_removed:_ The manual states that for code pairs with modifier indicator 1, both codes may be reported together only if performed on contralateral organs or at separate encounters or anatomic sites; they generally should not be reported together for the same knee unless there is a specific coding rationale. (quote not found in cited source: 'Most NCCI PTP edits for codes describing procedures that may be performed on bil')

**f05** Is the PTP edit between 0001A and 0591T still active?  
answerable=True correct=True fact_cited=True manual_cited=False  
The PTP edit between 0001A and 0591T is not active as of 2026-10-01. [1]

**f06** Which codes are bundled into CPT 29881?  
answerable=True correct=True fact_cited=True manual_cited=True  
According to the NCCI PTP edit tables, CPT code 29881 is the Column One code in 257 edits, meaning many codes are bundled into 29881, with common rationales including misuse, standards of medical/surgical practice, and CPT/CMS manual instructions. [1] The manual states that CPT code 29881 includes debridement/shaving of articular cartilage, so codes for these services in the same compartment are bundled into 29881. [2]

Not covered by the manual: The specific list of all codes bundled into 29881 is not provided here; only examples and general policy are given.
  
_removed:_ CPT code 29875 (limited synovectomy) is bundled into other arthroscopic knee procedures, including 29881, when performed on the same knee. (code 29881 not in the quoted paragraph)
  
_removed:_ Services that are usually performed as part of the procedure described by 29881 are bundled and not separately reportable. (code 29881 not in the quoted paragraph)

