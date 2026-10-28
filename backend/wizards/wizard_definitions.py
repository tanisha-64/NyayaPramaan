"""Static definitions for the guided Procedure Wizards (FIR refusal, bail, cheque bounce, scam check).
Each wizard is a tree of steps: a step either asks a question with options (each pointing to the next
step id) or is a terminal node with a checklist + citations. The frontend walks this tree client-side;
only the cheque-bounce deadline math lives in wizard_router.py."""

WIZARDS: dict[str, dict] = {
    "fir_refusal": {
        "title": "FIR Refusal — Kya Karein",
        "icon": "🚨",
        "start": "s1",
        "steps": {
            "s1": {
                "question": "Police station ne aapki FIR darj karne se mana kar diya?",
                "options": [
                    {"label": "Haan, seedha mana kar diya", "next": "s2"},
                    {"label": "FIR ki jagah sirf 'complaint' likh di", "next": "result_zero_fir"},
                ],
            },
            "s2": {
                "question": "Ye cognizable offense hai (jaise chori, maarpeet, dhoka) ya non-cognizable?",
                "options": [
                    {"label": "Cognizable offense hai", "next": "result_sp_complaint"},
                    {"label": "Pata nahi / Non-cognizable lagta hai", "next": "result_magistrate_direct"},
                ],
            },
            "result_zero_fir": {
                "result": {
                    "title": "Zero FIR File Karo",
                    "checklist": [
                        "Zero FIR kisi bhi police station me darj ho sakti hai, area/jurisdiction ka bahana nahi chalega.",
                        "Likhit me FIR copy maango — ye free hai, koi fees nahi lagti.",
                        "Baad me ye case sambandhit (jurisdiction wale) police station transfer ho jayega.",
                    ],
                    "citations": ["BNSS 2023, Section 173(1) — Zero FIR provision"],
                },
            },
            "result_sp_complaint": {
                "result": {
                    "title": "SP ko Likhit Complaint Do",
                    "checklist": [
                        "Superintendent of Police (SP) ko likhit complaint do, saare facts ke saath.",
                        "SP satisfied hue to khud investigate karenge ya FIR darj karne ka order denge.",
                        "7 din ke andar response na mile to seedha Magistrate ke paas jao.",
                    ],
                    "citations": ["BNSS 2023, Section 173(4)"],
                },
            },
            "result_magistrate_direct": {
                "result": {
                    "title": "Magistrate Ke Paas Jao",
                    "checklist": [
                        "Non-cognizable offense me police FIR darj karne ke liye bound nahi hai bina Magistrate order ke.",
                        "Jurisdiction wale Magistrate ke paas application dalo, wo police ko investigate karne ka order de sakte hain.",
                    ],
                    "citations": ["BNSS 2023, Section 175(3)"],
                },
            },
        },
    },
    "bail": {
        "title": "Bail — Kaunsi Apply Hogi",
        "icon": "⚖️",
        "start": "s1",
        "steps": {
            "s1": {
                "question": "Abhi arrest hui hai ya hone ka darr hai?",
                "options": [
                    {"label": "Already arrest ho gayi", "next": "s2"},
                    {"label": "Arrest hone ka darr hai, abhi nahi hui", "next": "result_anticipatory"},
                ],
            },
            "s2": {
                "question": "Police ne 60/90 din ke andar chargesheet file kar di?",
                "options": [
                    {"label": "Haan, file ho gayi", "next": "result_regular"},
                    {"label": "Nahi, time nikal gaya", "next": "result_default"},
                ],
            },
            "result_anticipatory": {
                "result": {
                    "title": "Anticipatory Bail Apply Karo",
                    "checklist": [
                        "Sessions Court ya High Court me anticipatory bail application dalo, arrest se pehle hi.",
                        "FIR ka number/details, aur arrest ka reasonable apprehension dikhana hoga.",
                    ],
                    "citations": ["BNSS 2023, Section 482"],
                },
            },
            "result_regular": {
                "result": {
                    "title": "Regular Bail Apply Karo",
                    "checklist": [
                        "Jo court case trial kar rahi hai wahi regular bail application sun sakti hai.",
                        "Offense bailable hai to police station se bhi mil sakti hai; non-bailable ho to court se.",
                    ],
                    "citations": ["BNSS 2023, Section 478-479"],
                },
            },
            "result_default": {
                "result": {
                    "title": "Default Bail Ka Right Hai",
                    "checklist": [
                        "Agar statutory period (60/90 din) me chargesheet nahi file hui to default/statutory bail ka absolute right hai.",
                        "Magistrate ke paas application dalo, bail denge even without merits check.",
                    ],
                    "citations": ["BNSS 2023, Section 187(3)"],
                },
            },
        },
    },
    "cheque_bounce": {
        "title": "Cheque Bounce — Deadline Calculator",
        "icon": "💳",
        "start": "s1",
        "steps": {
            "s1": {
                "question": "Cheque bounce hone ki date daalo — deadline calculator automatically dates bata dega.",
                "date_input": True,
                "next": "result_info",
            },
            "result_info": {
                "result": {
                    "title": "Agle Steps (dates ke saath)",
                    "checklist": [
                        "Bounce hone ke 30 din ke andar cheque dene wale ko likhit legal notice bhejo (demand notice).",
                        "Notice milne ke 15 din ke andar payment na ho to, uske baad 30 din ke andar complaint file karo.",
                        "Exact dates upar 'Calculate Deadline' button se mil gayi hongi.",
                    ],
                    "citations": ["Negotiable Instruments Act, 1881 — Section 138"],
                },
            },
        },
    },
    "scam_checker": {
        "title": "Scam / Fraud Notice Checker",
        "icon": "🌐",
        "start": "s1",
        "steps": {
            "s1": {
                "question": "Kis tarah ka message/notice mila hai?",
                "options": [
                    {"label": "SMS/WhatsApp me link ya prize jeetne ka message", "next": "result_sms"},
                    {"label": "Email/letter jisme 'legal action' ki dhamki hai", "next": "result_legal_threat"},
                    {"label": "Call aaya jisme OTP/bank details maangi", "next": "result_otp"},
                ],
            },
            "result_sms": {
                "result": {
                    "title": "Ye Likely Ek Scam Hai",
                    "checklist": [
                        "Kisi bhi link pe click mat karo, koi bhi OTP/PIN share mat karo.",
                        "Number block karo aur screenshot save rakho.",
                        "cybercrime.gov.in par ya 1930 helpline par report karo.",
                    ],
                    "citations": ["Information Technology Act, 2000 — cyber fraud provisions"],
                },
            },
            "result_legal_threat": {
                "result": {
                    "title": "Verify Karo Pehle",
                    "checklist": [
                        "Asli legal notice par lawyer/court ka letterhead, signature aur case number hota hai — check karo.",
                        "Agar genuine lage to lawyer se consult karo, jawab dene ki deadline miss mat karo.",
                        "Agar fake lage to usse ignore karne se pehle bhi 1930 pe report kar sakte ho.",
                    ],
                    "citations": [],
                },
            },
            "result_otp": {
                "result": {
                    "title": "Scam Hai — Kuch Share Mat Karo",
                    "checklist": [
                        "Bank/police kabhi phone pe OTP ya PIN nahi maangte — ye 100% scam hai.",
                        "Turant apne bank ko inform karo aur card/account block karne ki request karo agar kuch share ho gaya ho.",
                        "cybercrime.gov.in ya 1930 helpline par turant report karo.",
                    ],
                    "citations": ["Information Technology Act, 2000"],
                },
            },
        },
    },
}