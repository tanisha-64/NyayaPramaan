"""Fictional documents used by the tests. Every name, number and date is invented."""

PAGE_BREAK = "\f"

JUDGMENT_PAGES = [
    # page 1
    """IN THE COURT OF THE CIVIL JUDGE (SENIOR DIVISION), RAMPUR
Original Suit No. 118 of 2019
Ravi Kumar, plaintiff, versus Sunita Devi, defendant.
JUDGMENT
1. The plaintiff instituted this suit on 12 March 2019 seeking a declaration of title and possession of the agricultural plot in village Khera, Tehsil Sadar.
2. The defendant filed her written statement and denied the plaintiff's title. The learned counsel for the defendant is an advocate of this Hon'ble Court.
3. The defendant's mobile number is 9876543210 and her Aadhaar is 2345 6789 0123, as recorded in the vakalatnama.
4. Issues were framed on 21 July 2019.""",
    # page 2
    """5. PW-1, the plaintiff, deposed that he purchased the plot under a sale agreement dated 14 January 2018 for Rs. 4,50,000 and has been in peaceful possession since then.
6. PW-2, a neighbour, stated that he saw the plaintiff cultivating the plot every season.
7. Exhibit P-1 is the sale agreement. Exhibit P-2 is the receipt for the part payment of Rs. 1,00,000.
8. The defendant produced no document of title and examined only DW-1, her brother, who admitted that he had no personal knowledge of the sale.""",
    # page 3
    """9. The matter was heard on 05.08.2021 and arguments were heard on behalf of both parties.
10. The case was then listed for further hearing on 14 September 2021.
11. On 14 September 2021 the defendant sought an adjournment, which was granted, and the next date was fixed for 12 October 2021.
12. The Local Commissioner's report dated 2 June 2020 confirmed that the plaintiff was in possession of the plot.""",
    # page 4
    """13. Having considered the oral and documentary evidence, this Court finds that the plaintiff has proved the sale agreement and his possession.
14. The defendant has failed to prove any title. The suit is decreed with costs.
15. Order pronounced in open court on 30 November 2021.
16. The defendant shall hand over the vacant possession within 60 days from the date of this decree.""",
]
JUDGMENT_TEXT = PAGE_BREAK.join(JUDGMENT_PAGES)

FIR_TEXT = """FIRST INFORMATION REPORT
FIR No. 45/2018 dated 03.06.2018, Police Station Kotwali, District Rampur.
Complainant: Mohan Lal. Accused: Unknown persons.
Information: the complainant reported that on the night of 2 June 2018 his shop was broken into and goods worth Rs. 80,000 were stolen.
Sections: 457, 380 of the Indian Penal Code. The investigating officer has been informed. Charge-sheet to follow after investigation."""

AFFIDAVIT_TEXT = """AFFIDAVIT
I, Meera Sharma, aged 42 years, resident of Rampur, do hereby solemnly affirm and state on oath as follows:
1. That I am the deponent and am filing this affidavit in support of Criminal Misc. Bail Application No. 77 of 2022 before the Hon'ble High Court.
2. That the contents of paragraph 1 are true to my knowledge.
Verified at Rampur on this 4th day of May 2022 that the contents of this affidavit are true.
DEPONENT"""

LEGAL_NOTICE_TEXT = """LEGAL NOTICE
Under instructions from my client, I hereby call upon you under Section 138 of the Negotiable Instruments Act, 1881, to pay Rs. 2,00,000 within fifteen days of receipt of this notice, failing which my client shall be constrained to initiate proceedings in the competent court at your risk and cost. Advocate for the complainant."""

# exactly one weak record signal: needs the LLM tie-break
AMBIGUOUS_TEXT = """Memorandum for the resident welfare association of Block C.
The Hon'ble Chief Minister is expected to visit the colony next month and the association will present a memorandum. All residents are requested to attend the general meeting on Sunday and bring their payment receipts. Refreshments will be served after the meeting and the committee thanks everyone for their continued cooperation and support."""

# law-reference text with no study-material wording and no case-record signals
STATUTE_TEXT = """Section 378 of the Indian Penal Code defines theft and Section 379 prescribes the punishment for it. Article 21 of the Constitution of India guarantees life and personal liberty to every person. The expansion of Article 21 was considered in AIR 1978 SC 597 and later in (2017) 10 SCC 1 and the principle has been applied by many authorities since."""

RESUME_TEXT = """CURRICULUM VITAE
Name: Asha Verma. Date of birth : 12 May 1999.
Career Objective: to secure a challenging position in a reputed organisation.
Work Experience: two years as a software tester. Skills: Python, SQL, Selenium.
Education: B.Tech in Computer Science. Hobbies: reading and travelling."""

INVOICE_TEXT = """TAX INVOICE
Invoice No: 20391. Invoice date: 04/02/2026. Bill to: Greenleaf Traders.
Item: office chairs x 6, unit price 4,200, total 25,200. GSTIN 09ABCDE1234F1Z5. Purchase order PO-7781.
Payment terms: 30 days. Thank you for your business."""

TEXTBOOK_TEXT = """Chapter 4: Offences against property.
Lecture notes for LL.B. students. Section 378 of the Indian Penal Code defines theft; Section 379 prescribes the punishment.
Article 21 of the Constitution of India guarantees life and personal liberty. See also AIR 1978 SC 597 for the expansion of Article 21.
Module 5 covers the law of contract. Students should read the syllabus and attempt the assignment before the exam."""

RECIPE_TEXT = """Chocolate cake recipe. Ingredients: flour, sugar, cocoa, eggs and butter. Preheat the oven to 180 degrees.
Mix the dry ingredients, add the eggs and butter and bake for thirty five minutes. Once upon a time a baker made this cake every Sunday for his family and friends."""
