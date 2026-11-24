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
| h03 | (hard negative) | | | | 0.992 | pass | What does the Medicaid NCCI program say about edits for durable medical equipment? |
| h04 | (hard negative) | | | | 0.018 | blocked | What is the 2026 Medicare physician fee schedule payment for CPT 99214? |
| h06 | (hard negative) | | | | 0.615 | pass | What is the OPPS APC payment rate for HCPCS G0463? |
| h07 | (hard negative) | | | | 0.896 | pass | Which ICD-10 diagnosis codes support medical necessity for CPT 93000? |
| f01 | (fact: found) | | | | 0.795 | pass | What is the MUE value for CPT 64450? |
| f02 | (fact: found) | | | | 0.489 | pass | Is there a PTP edit between CPT 93000 and 99214, and what is its correct coding modifier indicator? |
| f03 | (fact: found) | | | | 0.842 | pass | How many units of CPT 97110 does the MUE allow per day? |
| f04 | (fact: found) | | | | 0.995 | pass | Can CPT 29880 and 29881 be reported together for the same knee? |
| f05 | (fact: found) | | | | 0.03 | pass | Is the PTP edit between 0001A and 0591T still active? |
| f06 | (fact: found) | | | | 0.987 | pass | Which codes are bundled into CPT 29881? |

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

Hard negatives passing the gate at 0.1: **3/4** (top scores 0.99, 0.02, 0.61, 0.90). These are in-domain, so retrieval correctly finds related policy; the answer layer must handle them.

**Edit-table facts:** looked up 6/6; linked manual section in the passages 4/4 (questions with an expected section)

## Answers

- Positives answered: 20/20; citing an expected section: 20/20
- Fact questions answered correctly: **6/6**; citing the table row: 6; also citing the manual (the why): 3
- Hard negatives handled cleanly (abstained, or no invented value): **3/4**
- Sentences removed by the claim check: 5 (in 2 positive and 0 hard-negative answers)

**q01** When is it appropriate to use modifier 59?  
answerable=True cited_expected=True  
Modifier 59 is appropriate when procedures or services, other than E/M services, that are not normally reported together are performed under circumstances such as a different session, different site or organ system, separate incision, lesion, or injury, and no more descriptive modifier is available. [1] Modifier 59 should only be used if no other modifier more appropriately describes the relationship between the procedures. [2] Modifier 59 is appropriate for different anatomic sites during the same encounter only when procedures not ordinarily performed together are done on different organs, regions, or non-contiguous lesions in different regions of the same organ. [3] Modifier 59 may be appended if the procedures are performed at separate patient encounters or at separate anatomic sites on the same date of service. [3] Modifier 59 may also be used for separate and distinct timed services provided in separate and distinct time blocks. [4] Modifier 59 should not be used to bypass a PTP edit unless the proper criteria for its use are met and documentation supports its use. [1]

**q02** What do modifiers XE, XS, XP, and XU mean, and how do they relate to modifier 59?  
answerable=True cited_expected=True  
Modifiers XE, XS, XP, and XU provide greater reporting specificity in situations where modifier 59 was previously reported and may be used in lieu of modifier 59 whenever possible. XE is for a separate encounter on the same date of service, XS is for a separate organ or structure, XP is for a different practitioner, and XU is for an unusual non-overlapping service. [1] Modifier 59 should only be used if no other modifier, such as XE, XP, XS, or XU, more appropriately describes the relationship between the procedure codes. [2] Modifiers 59, XE, or XS may be used to indicate that procedures are distinct because they were performed at separate encounters or separate anatomic sites on the same date of service. [3] Modifiers 59, XE, XP, XS, and XU must only be used when the proper criteria for their use are met and not simply to bypass an NCCI edit. [4]

**q03** What is a Medically Unlikely Edit (MUE)?  
answerable=True cited_expected=True  
A Medically Unlikely Edit (MUE) is a unit of service edit that sets the maximum number of units of service (UOS) that can be reported for a specific HCPCS/CPT code on the vast majority of appropriately reported claims by the same provider or supplier for the same beneficiary on the same date of service. [1] MUEs are designed to prevent payment for a potentially inappropriate number or quantity of the same service on a single day. [2] All claims submitted to Medicare Administrative Contractors (MACs), Durable Medical Equipment MACs, and outpatient facility services claims are tested against MUEs. [1]

**q04** What does a Correct Coding Modifier Indicator of 0 versus 1 mean for a PTP edit?  
answerable=True cited_expected=True  
A Correct Coding Modifier Indicator (CCMI) of '0' means that NCCI PTP-associated modifiers cannot be used to bypass the edit. [1] A CCMI of '1' means that NCCI PTP-associated modifiers may be used to bypass the edit under appropriate circumstances. [1]

**q05** Can an E&M service be reported on the same day as a minor surgical procedure?  
answerable=True cited_expected=True  
In general, E&M services performed on the same date as a minor surgical procedure are included in the payment for the procedure and are not separately reportable. [1] However, if there is a significant and separately identifiable E&M service unrelated to the decision to perform the minor surgical procedure, it may be reported separately with modifier 25. [1] The E&M service and minor surgical procedure do not require different diagnoses to be reported separately. [1] Being a new patient alone does not justify reporting an E&M service on the same day as a minor surgical procedure; the same rules apply to new and established patients. [1]

**q06** Can an add-on code be reported without its primary procedure code?  
answerable=True cited_expected=True  
Add-on Codes (AOCs) describe services that can only be reported in addition to a primary procedure. [1] An AOC is rarely eligible for payment if it is the only procedure reported by a practitioner. [2] For Type 1 AOCs, only the primary codes defined in the CPT or HCPCS files are acceptable, and other codes should not be used as primary codes. [2] For Type 2 and Type 3 AOCs, the CPT or HCPCS files may not define all primary codes, so MACs may develop their own lists of acceptable primary codes. [3] If the CPT codebook specifies primary codes for an AOC, the AOC cannot be reported with other codes not listed as primary codes. [1]

**q07** When should an unlisted procedure code be reported?  
answerable=True cited_expected=True  
An unlisted procedure code should be reported when a service is not accurately described by any other HCPCS/CPT code. [1] If no HCPCS/CPT code describes a laboratory procedure, a miscellaneous or unlisted procedure code should be reported with a single unit of service. [2] For molecular pathology, if no CPT code accurately describes the procedure, CPT code 81479 (Unlisted molecular pathology procedure) may be reported with one unit of service. [3]

**q08** What does the CPT 'separate procedure' designation mean for reporting?  
answerable=True cited_expected=True  
If a CPT code descriptor includes the term 'separate procedure,' the code may not be reported separately with a related procedure performed in an anatomically related region, often through the same skin incision, orifice, or surgical approach. [1] A 'separate procedure' code may be reported if performed at a separate patient encounter or in an anatomically unrelated area, and modifiers 59, XE, or XS (or a more specific modifier) may be used to indicate this. [1] CMS does not allow separate reporting of a 'separate procedure' when performed at the same encounter as another procedure in an anatomically related area through the same approach. [2][3][4] A 'separate procedure' is not separately reportable if performed in a region anatomically related to other procedures through the same approach. [5]

**q09** How does NCCI handle procedures that are mutually exclusive?  
answerable=True cited_expected=True  
NCCI handles mutually exclusive procedures by including pairs of codes that cannot reasonably be performed together at the same anatomic site or patient encounter in the NCCI PTP edit tables. [1] Some mutually exclusive edits allow the use of NCCI PTP-associated modifiers if the procedures are performed at different anatomic sites or separate encounters. [1] When both codes in a mutually exclusive edit pair are reported together, only the Column One code is eligible for payment unless a permitted modifier is used. [2] All mutually exclusive edits are now included in the single NCCI PTP Column One/Column Two Correct Coding Edit Table. [3]

**q10** How should monitored anesthesia care be reported?  
answerable=True cited_expected=True  
Monitored anesthesia care is performed by an anesthesia practitioner who administers sedatives or other anesthetic agents while the patient remains responsive and breathing independently, and is recognized as a payable service if medically reasonable and necessary. [1] Monitored anesthesia care includes intraoperative monitoring, pre-anesthesia evaluation, prescription and administration of medications, and postoperative anesthesia care. [1] Providers should report the HCPCS/CPT code that most specifically describes the monitored anesthesia care service performed, and only if all services described by the code are provided. [2] A separate anesthesia service for monitored anesthesia care may be reported by an anesthesia practitioner if it is medically reasonable and necessary and performed by a provider other than the one performing the surgical or medical procedure. [3] Preparation and monitoring services are not separately reportable with anesthesia service HCPCS/CPT codes when performed as part of the anesthesia service, regardless of the mode of anesthesia. [4]

**q11** How is Mohs micrographic surgery reported with other skin procedures?  
answerable=True cited_expected=True  
Mohs micrographic surgery (CPT codes 17311-17315) includes skin biopsy, excision, and pathology services, so these codes (11102-11107, 11600-11646, 17260-17286, 88300-88309, 88329-88332) should not be reported separately with Mohs surgery. [1] If a diagnostic biopsy or frozen section pathology is performed before Mohs surgery, these may be reported separately with modifiers 59, XS, XU, or 58 to show they are distinct from the Mohs procedure. [1] Repairs, grafts, and flaps are separately reportable with Mohs micrographic surgery codes. [1] Simple, intermediate, and complex wound repair codes (12001-13153) may be reported with Mohs surgery (17311-17315). [2][3]

**q12** If a diagnostic arthroscopy leads to a surgical arthroscopy in the same session, can both be reported?  
answerable=True cited_expected=True  
If a diagnostic arthroscopy leads to a surgical arthroscopy at the same patient encounter, only the surgical arthroscopy may be reported. [1]

**q13** Can a diagnostic endoscopy be reported separately when a surgical endoscopy is performed at the same session?  
answerable=True cited_expected=True  
A diagnostic endoscopy is not separately reportable with a surgical endoscopy performed at the same session; only the surgical endoscopy may be reported. [1][2] This is because surgical endoscopy includes diagnostic endoscopy, so the diagnostic portion is not separately billable. [2]

**q14** How are presumptive and definitive drug testing codes reported?  
answerable=True cited_expected=True  
Presumptive drug testing is reported with CPT codes 80305-80307, and only one code from this range may be reported per date of service. [1] Definitive drug testing is reported with HCPCS codes G0480-G0483 and G0659. [1] Only one definitive drug testing HCPCS code may be reported per date of service. [2] Both presumptive and definitive drug testing codes are reported per day and shall not be reported with more than one unit of service per day. [3]

**q15** Can hydration be reported separately when given with chemotherapy administration?  
answerable=True cited_expected=True  
Hydration concurrent with chemotherapy is not separately reportable. [1] If therapeutic fluid administration is medically necessary before or after chemotherapy, it may be reported separately. [2] Hydration concurrent with other drug administration services is not separately reportable. [2]

**q16** How can a provider request reconsideration of an NCCI edit or appeal a denial?  
answerable=True cited_expected=True  
A provider may request reconsideration of an NCCI PTP edit, AOC edit, or MUE value by submitting a written request with rationale to NCCIPTPMUE@cms.hhs.gov, specifying the relevant codes, edit type, and program. [1] The written request should include a rationale for reconsideration and a suggestion for the edit or value. [2] If a claim is denied due to an NCCI edit, the provider must submit an appeal to the Medicare Administrative Contractor (MAC), not to the NCCI contractor. [3]

**q17** What is the purpose of the NCCI program?  
answerable=True cited_expected=True  
The purpose of the NCCI program is to promote national correct coding methodologies and to control improper coding that leads to inappropriate payment of Part B claims. [1] NCCI coding policies are based on CPT conventions, Medicare policies, national society guidelines, standard practice, and current coding practice. [1] The NCCI program includes Procedure-to-Procedure (PTP) edits, Medically Unlikely Edits (MUEs), and Add-on Code (AOC) edits. [1]

**q18** Is the E&M visit where the decision for major surgery is made separately reportable, and with which modifier?  
answerable=True cited_expected=True  
If an E&M service is performed on the same date as a major surgical procedure to decide whether to perform the surgery, it is separately reportable with modifier 57. [1][2][3][4] Other preoperative E&M services on the same date as a major surgical procedure are included in the global payment and are not separately reportable. [1][2][3][4]

**q19** When can CPT code 69990 for the operating microscope be reported?  
answerable=True cited_expected=True  
CPT code 69990 should not be reported with procedures other than those listed in the MCPM, even if an operating microscope is used. [1] If multiple procedures are performed and only one is on the CMS list, payment for CPT code 69990 may be denied due to bundling edits, but the provider may submit the claim to the MAC with modifier 22 for possible payment adjustment. [1] CMS payment policy only allows CPT code 69990 to be reported with procedures listed in MCPM Chapter 12, Section 20.4.5. [2] CMS limits payment for CPT code 69990 to procedures listed in the MCPM Chapter 12 Section 20.4.5. [3]
  
_removed:_ CPT code 69990 may only be reported with procedures listed in the IOM Publication 100-04 MCPM, Chapter 12, Section 20.4.5, specifically codes 61304, 61305, 61312, 61314, 61315, 61320, 61321, 61322, 61323, 61343, 61510, 61512, 61518, 61519, 61520, 61521, 61526, 61530, 61531, 61533, 61534, 61535, 61536, 61537, 61538, 61539, 61540, 61541, 61542, 61543, 61544, 61545, 61546, 61548, 61550, 61552, 61556, 61557, 61558, 61559, 61560, 61561, 61562, 61563, 61564, 61565, 61566, 61567, 61568, 61570, 61571, 61575, 61576, 61580, 61581, 61582, 61583, 61584, 61585, 61586, 61600, 61601, 61605, 61606, 61607, 61608, 61609, 61610, 61611, 61612, 61613, 61615, 61616, 61618, 61619, 61623, 61624, 61626, 61630, 61631, 61635, 61640, 61641, 61642, 61650, 61651, 61652, 61654, 61700, 61702, 61703, 61705, 61708, 61710, 61711, 61712, 61713, 61720, 61722, 61723, 61725, 61727, 61735, 61736, 61750, 61751, 61760, 61770, 61781, 61782, 61783, 61863, 61864, 61867, 61868, 61885, 61886, 62200, 62201, 62220, 62223, 62230, 62252, 62256, 63075, 63076, 63077, 63078, 63081, 63082, 63085, 63086, 63087, 63088, 63090, 63091, 63101, 63102, 63103, 63170, 63172, 63173, 63180, 63182, 63185, 63190, 63191, 63194, 63195, 63196, 63197, 63198, 63199, 63200, 63250, 63251, 63252, 63265, 63266, 63267, 63268, 63270, 63271, 63272, 63273, 63275, 63276, 63277, 63278, 63280, 63281, 63282, 63283, 63285, 63287, 63290, 63295, 63300, 63301, 63302, 63303, 63304, 63305, 63306, 63307, 63308, 63310, 63311, 63312, 63313, 63314, 63315, 63316, 63317, 63318, 63319, 63320, 63321, 63322, 63323, 63324, 63325, 63326, 63330, 63331, 63332, 63333, 63334, 63335, 63340, 63341, 63342, 63343, 63344, 63345, 63346, 63347, 63348, 63349, 63350, 63351, 63352, 63353, 63354, 63355, 63356, 63357, 63358, 63359, 63360, 63361, 63362, 63363, 63364, 63365, 63366, 63367, 63368, 63369, 63370, 63371, 63372, 63373, 63374, 63375, 63376, 63377, 63378, 63379, 63380, 63381, 63382, 63383, 63384, 63385, 63386, 63387, 63388, 63389, 63390, 63391, 63392, 63393, 63394, 63395, 63396, 63397, 63398, 63399, 63400, 63401, 63402, 63403, 63404, 63405, 63406, 63407, 63408, 63409, 63410, 63411, 63412, 63413, 63414, 63415, 63416, 63417, 63418, 63419, 63420, 63421, 63422, 63423, 63424, 63425, 63426, 63427, 63428, 63429, 63430, 63431, 63432, 63433, 63434, 63435, 63436, 63437, 63438, 63439, 63440, 63441, 63442, 63443, 63444, 63445, 63446, 63447, 63448, 63449, 63450, 63451, 63452, 63453, 63454, 63455, 63456, 63457, 63458, 63459, 63460, 63461, 63462, 63463, 63464, 63465, 63466, 63467, 63468, 63469, 63470, 63471, 63472, 63473, 63474, 63475, 63476, 63477, 63478, 63479, 63480, 63481, 63482, 63483, 63484, 63485, 63486, 63487, 63488, 63489, 63490, 63491, 63492, 63493, 63494, 63495, 63496, 63497, 63498, 63499, 63500, 63501, 63502, 63503, 63504, 63505, 63506, 63507, 63508, 63509, 63510, 63511, 63512, 63513, 63514, 63515, 63516, 63517, 63518, 63519, 63520, 63521, 63522, 63523, 63524, 63525, 63526, 63527, 63528, 63529, 63530, 63531, 63532, 63533, 63534, 63535, 63536, 63537, 63538, 63539, 63540, 63541, 63542, 63543, 63544, 63545, 63546, 63547, 63548, 63549, 63550, 63551, 63552, 63553, 63554, 63555, 63556, 63557, 63558, 63559, 63560, 63561, 63562, 63563, 63564, 63565, 63566, 63567, 63568, 63569, 63570, 63571, 63572, 63573, 63574, 63575, 63576, 63577, 63578, 63579, 63580, 63581, 63582, 63583, 63584, 63585, 63586, 63587, 63588, 63589, 63590, 63591, 63592, 63593, 63594, 63595, 63596, 63597, 63598, 63599, 63600, 63601, 63602, 63603, 63604, 63605, 63606, 63607, 63608, 63609, 63610, 63611, 63612, 63613, 63614, 63615, 63616, 63617, 63618, 63619, 63620, 63621, 63622, 63623, 63624, 63625, 63626, 63627, 63628, 63629, 63630, 63631, 63632, 63633, 63634, 63635, 63636, 63637, 63638, 63639, 63640, 63641, 63642, 63643, 63644, 63645, 63646, 63647, 63648, 63649, 63650, 63651, 63652, 63653, 63654, 63655, 63656, 63657, 63658, 63659, 63660, 63661, 63662, 63663, 63664, 63665, 63666, 63667, 63668, 63669, 63670, 63671, 63672, 63673, 63674, 63675, 63676, 63677, 63678, 63679, 63680, 63681, 63682, 63683, 63684, 63685, 63686, 63687, 63688, 63689, 63690, 63691, 63692, 63693, 63694, 63695, 63696, 63697, 63698, 63699, 63700, 63701, 63702, 63703, 63704, 63705, 63706, 63707, 63708, 63709, 63710, 63711, 63712, 63713, 63714, 63715, 63716, 63717, 63718, 63719, 63720, 63721, 63722, 63723, 63724, 63725, 63726, 63727, 63728, 63729, 63730, 63731, 63732, 63733, 63734, 63735, 63736, 63737, 63738, 63739, 63740, 63741, 63742, 63743, 63744, 63745, 63746, 63747, 63748, 63749, 63750, 63751, 63752, 63753, 63754, 63755, 63756, 63757, 63758, 63759, 63760, 63761, 63762, 63763, 63764, 63765, 63766, 63767, 63768, 63769, 63770, 63771, 63772, 63773, 63774, 63775, 63776, 63777, 63778, 63779, 63780, 63781, 63782, 63783, 63784, 63785, 63786, 63787, 63788, 63789, 63790, 63791, 63792, 63793, 63794, 63795, 63796, 63797, 63798, 63799, 63800, 63801, 63802, 63803, 63804, 63805, 63806, 63807, 63808, 63809, 63810, 63811, 63812, 63813, 63814, 63815, 63816, 63817, 63818, 63819, 63820, 63821, 63822, 63823, 63824, 63825, 63826, 63827, 63828, 63829, 63830, 63831, 63832, 63833, 63834, 63835, 63836, 63837, 63838, 63839, 63840, 63841, 63842, 63843, 63844, 63845, 63846, 63847, 63848, 63849, 63850, 63851, 63852, 63853, 63854, 63855, 63856, 63857, 63858, 63859, 63860, 63861, 63862, 63863, 63864, 63865, 63866, 63867, 63868, 63869, 63870, 63871, 63872, 63873, 63874, 63875, 63876, 63877, 63878, 63879, 63880, 63881, 63882, 63883, 63884, 63885, 63886, 63887, 63888, 63889, 63890, 63891, 63892, 63893, 63894, 63895, 63896, 63897, 63898, 63899, 63900, 63901, 63902, 63903, 63904, 63905, 63906, 63907, 63908, 63909, 63910, 63911, 63912, 63913, 63914, 63915, 63916, 63917, 63918, 63919, 63920, 63921, 63922, 63923, 63924, 63925, 63926, 63927, 63928, 63929, 63930, 63931, 63932, 63933, 63934, 63935, 63936, 63937, 63938, 63939, 63940, 63941, 63942, 63943, 63944, 63945, 63946, 63947, 63948, 63949, 63950, 63951, 63952, 63953, 63954, 63955, 63956, 63957, 63958, 63959, 63960, 63961, 63962, 63963, 63964, 63965, 63966, 63967, 63968, 63969, 63970, 63971, 63972, 63973, 63974, 63975, 63976, 63977, 63978, 63979, 63980, 63981, 63982, 63983, 63984, 63985, 63986, 63987, 63988, 63989, 63990, 63991, 63992, 63993, 63994, 63995, 63996, 63997, 63998, 63999, 64905-64907. (code 61304, 61305, 61312, 61314, 61315, 61320, 61321, 61322, 61323, 61343, 61510, 61512, 61518, 61519, 61520, 61521, 61526, 61530, 61531, 61533, 61534, 61535, 61536, 61537, 61538, 61539, 61540, 61541, 61542, 61543, 61544, 61545, 61546, 61548, 61550, 61552, 61556, 61557, 61558, 61559, 61560, 61561, 61562, 61563, 61564, 61565, 61566, 61567, 61568, 61570, 61571, 61575, 61576, 61580, 61581, 61582, 61583, 61584, 61585, 61586, 61600, 61601, 61605, 61606, 61607, 61608, 61609, 61610, 61611, 61612, 61613, 61615, 61616, 61618, 61619, 61623, 61624, 61626, 61630, 61631, 61635, 61640, 61641, 61642, 61650, 61651, 61652, 61654, 61700, 61702, 61703, 61705, 61708, 61710, 61711, 61712, 61713, 61720, 61722, 61723, 61725, 61727, 61735, 61736, 61750, 61751, 61760, 61770, 61781, 61782, 61783, 61863, 61864, 61867, 61868, 61885, 61886, 62200, 62201, 62220, 62223, 62230, 62252, 62256, 63075, 63076, 63077, 63078, 63081, 63082, 63085, 63086, 63087, 63088, 63090, 63091, 63101, 63102, 63103, 63170, 63172, 63173, 63180, 63182, 63185, 63190, 63191, 63194, 63195, 63196, 63197, 63198, 63199, 63200, 63250, 63251, 63252, 63265, 63266, 63267, 63268, 63270, 63271, 63272, 63273, 63275, 63276, 63277, 63278, 63280, 63281, 63282, 63283, 63285, 63287, 63290, 63295, 63300, 63301, 63302, 63303, 63304, 63305, 63306, 63307, 63308, 63310, 63311, 63312, 63313, 63314, 63315, 63316, 63317, 63318, 63319, 63320, 63321, 63322, 63323, 63324, 63325, 63326, 63330, 63331, 63332, 63333, 63334, 63335, 63340, 63341, 63342, 63343, 63344, 63345, 63346, 63347, 63348, 63349, 63350, 63351, 63352, 63353, 63354, 63355, 63356, 63357, 63358, 63359, 63360, 63361, 63362, 63363, 63364, 63365, 63366, 63367, 63368, 63369, 63370, 63371, 63372, 63373, 63374, 63375, 63376, 63377, 63378, 63379, 63380, 63381, 63382, 63383, 63384, 63385, 63386, 63387, 63388, 63389, 63390, 63391, 63392, 63393, 63394, 63395, 63396, 63397, 63398, 63399, 63400, 63401, 63402, 63403, 63404, 63405, 63406, 63407, 63408, 63409, 63410, 63411, 63412, 63413, 63414, 63415, 63416, 63417, 63418, 63419, 63420, 63421, 63422, 63423, 63424, 63425, 63426, 63427, 63428, 63429, 63430, 63431, 63432, 63433, 63434, 63435, 63436, 63437, 63438, 63439, 63440, 63441, 63442, 63443, 63444, 63445, 63446, 63447, 63448, 63449, 63450, 63451, 63452, 63453, 63454, 63455, 63456, 63457, 63458, 63459, 63460, 63461, 63462, 63463, 63464, 63465, 63466, 63467, 63468, 63469, 63470, 63471, 63472, 63473, 63474, 63475, 63476, 63477, 63478, 63479, 63480, 63481, 63482, 63483, 63484, 63485, 63486, 63487, 63488, 63489, 63490, 63491, 63492, 63493, 63494, 63495, 63496, 63497, 63498, 63499, 63500, 63501, 63502, 63503, 63504, 63505, 63506, 63507, 63508, 63509, 63510, 63511, 63512, 63513, 63514, 63515, 63516, 63517, 63518, 63519, 63520, 63521, 63522, 63523, 63524, 63525, 63526, 63527, 63528, 63529, 63530, 63531, 63532, 63533, 63534, 63535, 63536, 63537, 63538, 63539, 63540, 63541, 63542, 63543, 63544, 63545, 63546, 63547, 63548, 63549, 63550, 63551, 63552, 63553, 63554, 63555, 63556, 63557, 63558, 63559, 63560, 63561, 63562, 63563, 63564, 63565, 63566, 63567, 63568, 63569, 63570, 63571, 63572, 63573, 63574, 63575, 63576, 63577, 63578, 63579, 63580, 63581, 63582, 63583, 63584, 63585, 63586, 63587, 63588, 63589, 63590, 63591, 63592, 63593, 63594, 63595, 63596, 63597, 63598, 63599, 63600, 63601, 63602, 63603, 63604, 63605, 63606, 63607, 63608, 63609, 63610, 63611, 63612, 63613, 63614, 63615, 63616, 63617, 63618, 63619, 63620, 63621, 63622, 63623, 63624, 63625, 63626, 63627, 63628, 63629, 63630, 63631, 63632, 63633, 63634, 63635, 63636, 63637, 63638, 63639, 63640, 63641, 63642, 63643, 63644, 63645, 63646, 63647, 63648, 63649, 63650, 63651, 63652, 63653, 63654, 63655, 63656, 63657, 63658, 63659, 63660, 63661, 63662, 63663, 63664, 63665, 63666, 63667, 63668, 63669, 63670, 63671, 63672, 63673, 63674, 63675, 63676, 63677, 63678, 63679, 63680, 63681, 63682, 63683, 63684, 63685, 63686, 63687, 63688, 63689, 63690, 63691, 63692, 63693, 63694, 63695, 63696, 63697, 63698, 63699, 63700, 63701, 63702, 63703, 63704, 63705, 63706, 63707, 63708, 63709, 63710, 63711, 63712, 63713, 63714, 63715, 63716, 63717, 63718, 63719, 63720, 63721, 63722, 63723, 63724, 63725, 63726, 63727, 63728, 63729, 63730, 63731, 63732, 63733, 63734, 63735, 63736, 63737, 63738, 63739, 63740, 63741, 63742, 63743, 63744, 63745, 63746, 63747, 63748, 63749, 63750, 63751, 63752, 63753, 63754, 63755, 63756, 63757, 63758, 63759, 63760, 63761, 63762, 63763, 63764, 63765, 63766, 63767, 63768, 63769, 63770, 63771, 63772, 63773, 63774, 63775, 63776, 63777, 63778, 63779, 63780, 63781, 63782, 63783, 63784, 63785, 63786, 63787, 63788, 63789, 63790, 63791, 63792, 63793, 63794, 63795, 63796, 63797, 63798, 63799, 63800, 63801, 63802, 63803, 63804, 63805, 63806, 63807, 63808, 63809, 63810, 63811, 63812, 63813, 63814, 63815, 63816, 63817, 63818, 63819, 63820, 63821, 63822, 63823, 63824, 63825, 63826, 63827, 63828, 63829, 63830, 63831, 63832, 63833, 63834, 63835, 63836, 63837, 63838, 63839, 63840, 63841, 63842, 63843, 63844, 63845, 63846, 63847, 63848, 63849, 63850, 63851, 63852, 63853, 63854, 63855, 63856, 63857, 63858, 63859, 63860, 63861, 63862, 63863, 63864, 63865, 63866, 63867, 63868, 63869, 63870, 63871, 63872, 63873, 63874, 63875, 63876, 63877, 63878, 63879, 63880, 63881, 63882, 63883, 63884, 63885, 63886, 63887, 63888, 63889, 63890, 63891, 63892, 63893, 63894, 63895, 63896, 63897, 63898, 63899, 63900, 63901, 63902, 63903, 63904, 63905, 63906, 63907, 63908, 63909, 63910, 63911, 63912, 63913, 63914, 63915, 63916, 63917, 63918, 63919, 63920, 63921, 63922, 63923, 63924, 63925, 63926, 63927, 63928, 63929, 63930, 63931, 63932, 63933, 63934, 63935, 63936, 63937, 63938, 63939, 63940, 63941, 63942, 63943, 63944, 63945, 63946, 63947, 63948, 63949, 63950, 63951, 63952, 63953, 63954, 63955, 63956, 63957, 63958, 63959, 63960, 63961, 63962, 63963, 63964, 63965, 63966, 63967, 63968, 63969, 63970, 63971, 63972, 63973, 63974, 63975, 63976, 63977, 63978, 63979, 63980, 63981, 63982, 63983, 63984, 63985, 63986, 63987, 63988, 63989, 63990, 63991, 63992, 63993, 63994, 63995, 63996, 63997, 63998, 63999 not in the quoted paragraph)

**q20** Which edits apply to CPT 64450 nerve blocks given by the anesthesiologist?  
answerable=True cited_expected=True  
According to the NCCI PTP edit tables, CPT code 64450 is the Column One code in 144 edits and the Column Two code in 6,110 edits, with common rationales including CPT Manual or CMS manual coding instruction, standards of medical/surgical practice, and misuse of codes. [1] CPT code 64450 shall not be reported by a surgeon for anesthesia for a surgical procedure, but may be reported separately if performed as a therapeutic or diagnostic injection unrelated to the surgical procedure. [2] An anesthesiologist may report a peripheral nerve block injection (CPT codes 64XXX, including 64450) for postoperative pain management separately from an anesthesia 0XXXX code only under specific circumstances, such as when the intraoperative anesthesia is general, spinal, or epidural, and the nerve block is not required for intraoperative anesthesia adequacy; modifier 59 or XU may be used if appropriate. [3]

Not covered by the manual: The specific edit pairs and modifier indicators for each code pair with 64450 are not listed here.
  
_removed:_ The physician performing a surgical or medical procedure should not report a nerve block (CPT codes 64400-64530, which includes 64450) for anesthesia for that procedure. (quote not found in cited source: 'The physician performing a surgical or medical procedure shall not report an epi')

**h03** What does the Medicaid NCCI program say about edits for durable medical equipment?  
answerable=True clean=False  
The NCCI program includes Medically Unlikely Edits (MUEs) that are applicable to claims submitted to Durable Medical Equipment (DME) MACs. [1] The Medicaid NCCI program allows for reconsideration requests for edits, including those for Durable Medical Equipment. [2]

Not covered by the manual: The passages do not describe specific types of edits or policies for DME under the Medicaid NCCI program.

**h04** What is the 2026 Medicare physician fee schedule payment for CPT 99214?  
answerable=False clean=True  
I couldn't find this in the 2026 Medicare NCCI Policy Manual. Try rephrasing, or name the code, modifier, or chapter you mean.

**h06** What is the OPPS APC payment rate for HCPCS G0463?  
answerable=False clean=True  
The passages discuss when G0463 may be reported under OPPS but do not state the APC payment rate for G0463.

**h07** Which ICD-10 diagnosis codes support medical necessity for CPT 93000?  
answerable=False clean=True  
None of the provided passages mention ICD-10 diagnosis codes, medical necessity requirements, or any diagnosis-to-procedure linkage for CPT 93000.

**f01** What is the MUE value for CPT 64450?  
answerable=True correct=True fact_cited=True manual_cited=True  
The MUE value for CPT code 64450 is 10 units of service. [1] The policy states that only one unit of service of CPT code 64450 may be reported per patient encounter, regardless of the number of injections needed to block the nerve and its branches. [2]

**f02** Is there a PTP edit between CPT 93000 and 99214, and what is its correct coding modifier indicator?  
answerable=True correct=True fact_cited=True manual_cited=True  
There is no NCCI PTP edit between CPT codes 93000 and 99214 in either order. [1] Since there is no edit listed for this code pair, there is no Correct Coding Modifier Indicator (CCMI) applicable. [2]

**f03** How many units of CPT 97110 does the MUE allow per day?  
answerable=True correct=True fact_cited=True manual_cited=False  
The MUE value for CPT code 97110 is 6 units of service per day. [1]
  
_removed:_ Since CPT code 97110 has an MAI of 3, the MUE is a per day edit based on clinical benchmarks, but units above 6 may be considered if justified and properly documented. (code 97110 not in the quoted paragraph)

**f04** Can CPT 29880 and 29881 be reported together for the same knee?  
answerable=True correct=True fact_cited=True manual_cited=False  
There is an active NCCI PTP edit for CPT codes 29880 and 29881, with 29880 as Column One and 29881 as Column Two; if both are reported for the same beneficiary on the same date, 29881 is denied unless the edit is bypassed with an appropriate modifier. [1]
  
_removed:_ The manual states that for code pairs with modifier indicator 1, such as 29880/29881, both codes may be reported together only if performed on contralateral organs or at separate encounters or anatomic sites; they generally should not be reported together for the same knee at the same encounter. (quote not found in cited source: 'Most NCCI PTP edits for codes describing procedures that may be performed on bil')

**f05** Is the PTP edit between 0001A and 0591T still active?  
answerable=True correct=True fact_cited=True manual_cited=False  
The PTP edit between 0001A and 0591T is not active on 2026-10-01. [1]

**f06** Which codes are bundled into CPT 29881?  
answerable=True correct=True fact_cited=True manual_cited=True  
According to the NCCI PTP edit tables, CPT code 29881 is the Column One code in 257 edits, meaning many codes are bundled into 29881 for reasons such as misuse, standards of medical/surgical practice, or CPT/CMS manual instructions. [1] The manual specifically states that CPT codes 29874 and 29877 are bundled into 29881 and should not be reported together, as 29881 includes debridement/shaving of articular cartilage. [2]

Not covered by the manual: The manual does not provide a complete list of all codes bundled into 29881; only examples and general policy are given.
  
_removed:_ The general policy is that if a single code like 29881 describes all services performed, other codes for included services are bundled and should not be reported separately. (code 29881 not in the quoted paragraph)

