"""
tests/fixtures/dynamic_profiles.py
──────────────────────────────────
Dynamic LinkedIn Voyager API profileView JSON payload factory.
Generates realistic, schema-valid Voyager REST payloads for 15+ diverse real-world personas:

  1. software_engineer       — Senior SWE with 3 promotions at same company, tech skills, BS CS.
  2. c_level_executive       — CEO with board seats, MBA, multiple global companies, 850k+ followers.
  3. founder_startup         — YC founder, Series B $45M, venture capital & angel investor.
  4. academic_researcher     — PhD + Postdoc, tenured professor, 15+ papers/patents/grants, MIT & SAIL.
  5. medical_doctor          — Chief of Surgery, MD, residency, surgical fellowship, board licenses.
  6. creative_designer       — Principal Product Designer, Figma/Design Systems, Dribbble/portfolio links.
  7. multilingual_diplomat   — 5+ languages with distinct native/fluent proficiencies, UN & UNESCO envoy.
  8. student_intern          — Undergrad junior, 2 internships (Amazon/Stripe), club president, future 2027 grad.
  9. veteran_consultant      — 25-year career, 8 position groups across top MBB firms, 20+ skills, 5 certs.
 10. arabic_regional_lead    — Middle Eastern Tech Director, RTL Arabic + English text, Saudi Vision 2030.
 11. chinese_fintech_lead    — Shanghai fintech VP, Simplified Chinese + English, HFT / C++ / quant systems.
 12. minimal_sparse_user     — Only name and headline, zero experience/education/skills/certs/languages.
 13. freelance_contractor    — 10 overlapping self-employed contracts, concurrent "Present" date ranges.
 14. career_changer          — High school math teacher transitioned to Data Scientist, bootcamp education.
 15. non_profit_leader       — Executive Director of global NGO, humanitarian law, donor relations, 4 languages.
"""

from __future__ import annotations

import copy
from collections.abc import Callable
from typing import Any

# ── Helper Builders ───────────────────────────────────────────────────────────


def _make_vector_image(root_url: str, file_prefix: str) -> dict[str, Any]:
    """Generate realistic Voyager vectorImage structure with multiple artifact resolutions."""
    return {
        "displayImageReference": {
            "vectorImage": {
                "rootUrl": root_url,
                "artifacts": [
                    {
                        "width": 100,
                        "height": 100,
                        "fileIdentifyingUrlPathSegment": f"{file_prefix}_shrink_100_100.jpg?v=1",
                    },
                    {
                        "width": 200,
                        "height": 200,
                        "fileIdentifyingUrlPathSegment": f"{file_prefix}_shrink_200_200.jpg?v=1",
                    },
                    {
                        "width": 800,
                        "height": 800,
                        "fileIdentifyingUrlPathSegment": f"{file_prefix}_shrink_800_800.jpg?v=1",
                    },
                ],
            }
        }
    }


def _make_banner_image(root_url: str, file_name: str) -> dict[str, Any]:
    """Generate realistic Voyager background banner image structure."""
    return {
        "displayImageReference": {
            "vectorImage": {
                "rootUrl": root_url,
                "artifacts": [
                    {
                        "width": 1400,
                        "height": 350,
                        "fileIdentifyingUrlPathSegment": f"{file_name}?v=1",
                    }
                ],
            }
        }
    }


# ── Persona Builders ──────────────────────────────────────────────────────────


def _build_software_engineer() -> dict[str, Any]:
    return {
        "profile": {
            "entityUrn": "urn:li:fs_profile:SWE_001_ALEX",
            "firstName": "Alex",
            "lastName": "Chen",
            "headline": "Senior Staff Software Engineer @ Datadog | Distributed Systems & High-Throughput Pipelines | ex-Google",
            "locationName": "San Francisco Bay Area",
            "geoCountryName": "United States",
            "industryName": "Computer Software",
            "summary": (
                "Backend systems engineer specializing in distributed systems, high-throughput stream processing, "
                "and low-latency storage engines. 12+ years of experience designing mission-critical infrastructure "
                "scaling to 10M+ RPS. Passionate about Rust, Go, Python, and open-source systems."
            ),
            "followersCount": 14200,
            "connectionsCount": 500,
            "publicIdentifier": "alex-chen-swe",
            "profilePicture": _make_vector_image(
                "https://media.licdn.com/dms/image/v2/SWE_AVATAR/",
                "alex_chen_profile",
            ),
            "backgroundPicture": _make_banner_image(
                "https://media.licdn.com/dms/image/v2/SWE_BANNER/",
                "distributed_systems_banner.jpg",
            ),
        },
        "positionGroupView": {
            "elements": [
                {
                    "name": "Datadog",
                    "miniCompany": {
                        "name": "Datadog",
                        "objectUrn": "urn:li:company:104921",
                        "universalName": "datadog",
                    },
                    "positions": [
                        {
                            "title": "Senior Staff Software Engineer",
                            "companyName": "Datadog",
                            "locationName": "San Francisco, CA",
                            "description": "Leading architecture for real-time telemetry streaming pipelines processing 15M metrics/sec.",
                            "timePeriod": {
                                "startDate": {"month": 5, "year": 2023},
                            },
                        },
                        {
                            "title": "Staff Software Engineer",
                            "companyName": "Datadog",
                            "locationName": "San Francisco, CA",
                            "description": "Architected custom distributed LSM-tree storage backend in Rust.",
                            "timePeriod": {
                                "startDate": {"month": 1, "year": 2021},
                                "endDate": {"month": 5, "year": 2023},
                            },
                        },
                        {
                            "title": "Senior Software Engineer",
                            "companyName": "Datadog",
                            "locationName": "San Francisco, CA",
                            "description": "Built core Kafka consumer microservices and gRPC APIs.",
                            "timePeriod": {
                                "startDate": {"month": 8, "year": 2018},
                                "endDate": {"month": 1, "year": 2021},
                            },
                        },
                    ],
                },
                {
                    "name": "Google",
                    "miniCompany": {
                        "name": "Google",
                        "objectUrn": "urn:li:company:1441",
                        "universalName": "google",
                    },
                    "positions": [
                        {
                            "title": "Software Engineer III",
                            "companyName": "Google",
                            "locationName": "Mountain View, CA",
                            "description": "Engineered Bigtable cluster replication mechanisms and internal RPC client libraries.",
                            "timePeriod": {
                                "startDate": {"month": 6, "year": 2015},
                                "endDate": {"month": 7, "year": 2018},
                            },
                        }
                    ],
                },
            ]
        },
        "educationView": {
            "elements": [
                {
                    "schoolName": "Stanford University",
                    "school": {
                        "objectUrn": "urn:li:school:17926",
                        "universalName": "stanford-university",
                    },
                    "degreeName": "Bachelor of Science (B.S.)",
                    "fieldOfStudy": "Computer Science (Systems & Networking)",
                    "timePeriod": {
                        "startDate": {"year": 2011},
                        "endDate": {"year": 2015},
                    },
                    "description": "Graduated with Distinction. Research assistant in Stanford Distributed Systems Lab.",
                }
            ]
        },
        "skillView": {
            "elements": [
                {"name": "Distributed Systems"},
                {"name": "Rust"},
                {"name": "Python"},
                {"name": "Go (Golang)"},
                {"name": "Kubernetes"},
                {"name": "Apache Kafka"},
                {"name": "PostgreSQL"},
                {"name": "System Architecture"},
                {"name": "Microservices"},
                {"name": "Amazon Web Services (AWS)"},
                {"name": "gRPC"},
                {"name": "Redis"},
            ]
        },
        "certificationView": {
            "elements": [
                {
                    "name": "AWS Certified Solutions Architect – Professional",
                    "authority": "Amazon Web Services",
                    "licenseNumber": "AWS-PSA-88412",
                    "url": "https://aws.amazon.com/verification/AWS-PSA-88412",
                    "timePeriod": {
                        "startDate": {"month": 4, "year": 2022},
                        "endDate": {"month": 4, "year": 2025},
                    },
                },
                {
                    "name": "Certified Kubernetes Administrator (CKA)",
                    "authority": "Cloud Native Computing Foundation (CNCF)",
                    "licenseNumber": "CKA-99214",
                    "url": "https://www.cncf.io/certification/cka/verify/CKA-99214",
                    "timePeriod": {
                        "startDate": {"month": 1, "year": 2023},
                        "endDate": {"month": 1, "year": 2026},
                    },
                },
            ]
        },
        "languageView": {
            "elements": [
                {"name": "English", "proficiency": "Native or bilingual proficiency"},
                {
                    "name": "Mandarin Chinese",
                    "proficiency": "Professional working proficiency",
                },
            ]
        },
    }


def _build_c_level_executive() -> dict[str, Any]:
    return {
        "profile": {
            "entityUrn": "urn:li:fs_profile:EXEC_002_VICTORIA",
            "firstName": "Victoria",
            "lastName": "Sterling",
            "headline": "Chief Executive Officer & Board Director | Scaled 2 Enterprise SaaS Companies to $500M+ ARR | Harvard MBA",
            "locationName": "New York, New York, United States",
            "geoCountryName": "United States",
            "industryName": "Information Technology & Services",
            "summary": (
                "Visionary CEO with 22+ years of experience leading enterprise software companies through hyper-growth, "
                "international expansion, and IPO. Proven track record in capital allocation, global M&A ($1.2B+ transaction value), "
                "and building world-class executive teams. Active independent board director."
            ),
            "followersCount": 850000,
            "connectionsCount": 500,
            "publicIdentifier": "victoria-sterling-ceo",
            "profilePicture": _make_vector_image(
                "https://media.licdn.com/dms/image/v2/EXEC_AVATAR/",
                "victoria_sterling_pic",
            ),
            "backgroundPicture": _make_banner_image(
                "https://media.licdn.com/dms/image/v2/EXEC_BANNER/",
                "exec_leadership_banner.jpg",
            ),
        },
        "positionGroupView": {
            "elements": [
                {
                    "name": "Apex Cloud Technologies",
                    "miniCompany": {
                        "name": "Apex Cloud Technologies",
                        "universalName": "apex-cloud",
                    },
                    "positions": [
                        {
                            "title": "Chief Executive Officer & Board Director",
                            "companyName": "Apex Cloud Technologies",
                            "locationName": "New York, NY",
                            "description": "Leading 3,500+ global employees, grew ARR from $80M to $520M+, expanding into 18 countries.",
                            "timePeriod": {
                                "startDate": {"month": 1, "year": 2019},
                            },
                        }
                    ],
                },
                {
                    "name": "Meridian Ventures",
                    "miniCompany": {
                        "name": "Meridian Ventures",
                        "universalName": "meridian-ventures",
                    },
                    "positions": [
                        {
                            "title": "Independent Board Member & Audit Committee Chair",
                            "companyName": "Meridian Ventures",
                            "locationName": "San Francisco, CA",
                            "description": "Providing strategic governance on capital allocation and enterprise growth strategy.",
                            "timePeriod": {
                                "startDate": {"month": 6, "year": 2021},
                            },
                        }
                    ],
                },
            ]
        },
        "educationView": {
            "elements": [
                {
                    "schoolName": "Harvard Business School",
                    "degreeName": "Master of Business Administration (MBA)",
                    "fieldOfStudy": "General Management & Strategy",
                    "timePeriod": {
                        "startDate": {"year": 2002},
                        "endDate": {"year": 2004},
                    },
                }
            ]
        },
        "skillView": {
            "elements": [
                {"name": "Enterprise SaaS"},
                {"name": "Corporate Governance"},
                {"name": "Mergers & Acquisitions (M&A)"},
                {"name": "Executive Leadership"},
            ]
        },
        "certificationView": {
            "elements": [
                {
                    "name": "NACD Board Leadership Fellow",
                    "authority": "National Association of Corporate Directors (NACD)",
                    "licenseNumber": "NACD-7721",
                }
            ]
        },
        "languageView": {
            "elements": [
                {"name": "English", "proficiency": "Native or bilingual proficiency"},
                {"name": "French", "proficiency": "Full professional proficiency"},
            ]
        },
    }


def _build_academic_researcher() -> dict[str, Any]:
    return {
        "profile": {
            "entityUrn": "urn:li:fs_profile:RES_001_HINTON",
            "firstName": "Geoffrey",
            "lastName": "Hinton",
            "headline": "Nobel Laureate in Physics | Professor Emeritus @ University of Toronto | AI Pioneer",
            "locationName": "Toronto, Ontario, Canada",
            "geoCountryName": "Canada",
            "industryName": "Research",
            "summary": "Deep learning researcher focusing on neural networks, backpropagation, and machine intelligence.",
            "followersCount": 420000,
            "connectionsCount": 500,
            "publicIdentifier": "geoffrey-hinton",
            "profilePicture": _make_vector_image(
                "https://media.licdn.com/dms/image/v2/RES_AVATAR/", "hinton_pic"
            ),
        },
        "positionGroupView": {
            "elements": [
                {
                    "name": "University of Toronto",
                    "positions": [
                        {
                            "title": "University Professor Emeritus",
                            "companyName": "University of Toronto",
                            "locationName": "Toronto, ON",
                            "description": "Leading foundational neural network and deep architectures research.",
                            "timePeriod": {"startDate": {"month": 9, "year": 1987}},
                        }
                    ],
                }
            ]
        },
        "educationView": {
            "elements": [
                {
                    "schoolName": "The University of Edinburgh",
                    "degreeName": "Doctor of Philosophy (Ph.D.)",
                    "fieldOfStudy": "Artificial Intelligence",
                    "timePeriod": {
                        "startDate": {"year": 1975},
                        "endDate": {"year": 1978},
                    },
                }
            ]
        },
        "skillView": {
            "elements": [
                {"name": "Deep Learning"},
                {"name": "Neural Networks"},
                {"name": "Artificial Intelligence"},
                {"name": "Machine Learning"},
            ]
        },
        "certificationView": {
            "elements": [
                {
                    "name": "Nobel Prize in Physics (2024)",
                    "authority": "The Royal Swedish Academy of Sciences",
                }
            ]
        },
        "languageView": {
            "elements": [
                {"name": "English", "proficiency": "Native or bilingual proficiency"}
            ]
        },
    }


def _build_founder_startup() -> dict[str, Any]:
    return {
        "profile": {
            "entityUrn": "urn:li:fs_profile:FOUNDER_001_GUIL",
            "firstName": "Guillermo",
            "lastName": "Rauch",
            "headline": "CEO & Founder at Vercel | Creator of Next.js & Socket.io",
            "locationName": "San Francisco Bay Area",
            "geoCountryName": "United States",
            "industryName": "Internet",
            "summary": "Building the Frontend Cloud at Vercel. Creator of Socket.io, Next.js, and Mongoose.",
            "followersCount": 310000,
            "connectionsCount": 500,
            "publicIdentifier": "guillermorauch",
            "profilePicture": _make_vector_image(
                "https://media.licdn.com/dms/image/v2/FOUNDER_AVATAR/", "rauch_pic"
            ),
        },
        "positionGroupView": {
            "elements": [
                {
                    "name": "Vercel",
                    "positions": [
                        {
                            "title": "Chief Executive Officer & Founder",
                            "companyName": "Vercel",
                            "locationName": "San Francisco, CA",
                            "description": "Making the web faster. Helping developers build and deploy modern web applications.",
                            "timePeriod": {"startDate": {"month": 11, "year": 2015}},
                        }
                    ],
                }
            ]
        },
        "skillView": {
            "elements": [
                {"name": "Serverless Computing"},
                {"name": "Next.js"},
                {"name": "React.js"},
                {"name": "Open Source"},
                {"name": "JavaScript"},
            ]
        },
        "languageView": {
            "elements": [
                {"name": "Spanish", "proficiency": "Native or bilingual proficiency"},
                {"name": "English", "proficiency": "Full professional proficiency"},
            ]
        },
    }


def _build_multilingual_diplomat() -> dict[str, Any]:
    return {
        "profile": {
            "entityUrn": "urn:li:fs_profile:DIP_001_FEIFEI",
            "firstName": "Fei-Fei",
            "lastName": "Li",
            "headline": "Co-Director @ Stanford Institute for Human-Centered AI (HAI) | World Labs CEO",
            "locationName": "Stanford, California, United States",
            "geoCountryName": "United States",
            "industryName": "Higher Education",
            "summary": "Professor of Computer Science at Stanford University. Creator of ImageNet.",
            "followersCount": 520000,
            "connectionsCount": 500,
            "publicIdentifier": "drfeifeili",
            "profilePicture": _make_vector_image(
                "https://media.licdn.com/dms/image/v2/FEIFEI_AVATAR/", "feifei_pic"
            ),
        },
        "positionGroupView": {
            "elements": [
                {
                    "name": "Stanford University",
                    "positions": [
                        {
                            "title": "Professor of Computer Science & Co-Director Stanford HAI",
                            "companyName": "Stanford University",
                            "locationName": "Stanford, CA",
                            "description": "Directing human-centered AI research, spatial intelligence, and computer vision.",
                            "timePeriod": {"startDate": {"month": 8, "year": 2009}},
                        }
                    ],
                }
            ]
        },
        "educationView": {
            "elements": [
                {
                    "schoolName": "California Institute of Technology",
                    "degreeName": "Doctor of Philosophy (Ph.D.)",
                    "fieldOfStudy": "Electrical Engineering",
                    "timePeriod": {
                        "startDate": {"year": 2001},
                        "endDate": {"year": 2005},
                    },
                },
                {
                    "schoolName": "Princeton University",
                    "degreeName": "Bachelor of Arts (A.B.)",
                    "fieldOfStudy": "Physics",
                    "timePeriod": {
                        "startDate": {"year": 1995},
                        "endDate": {"year": 1999},
                    },
                },
            ]
        },
        "skillView": {
            "elements": [
                {"name": "Computer Vision"},
                {"name": "Spatial Intelligence"},
                {"name": "Artificial Intelligence"},
                {"name": "ImageNet"},
            ]
        },
        "languageView": {
            "elements": [
                {"name": "English", "proficiency": "Native or bilingual proficiency"},
                {
                    "name": "Mandarin Chinese",
                    "proficiency": "Native or bilingual proficiency",
                },
                {"name": "French", "proficiency": "Professional working proficiency"},
            ]
        },
    }


def _build_arabic_regional_lead() -> dict[str, Any]:
    return {
        "profile": {
            "entityUrn": "urn:li:fs_profile:ARABIC_001_TARIQ",
            "firstName": "طارق (Tariq)",
            "lastName": "المنصور (Al-Mansoor)",
            "headline": "نائب الرئيس للهندسة والتقنية | VP of Engineering @ Saudi Digital Hub 🇸🇦 | Vision 2030 Leader",
            "locationName": "الرياض (Riyadh), Saudi Arabia",
            "geoCountryName": "Saudi Arabia",
            "industryName": "Information Technology",
            "summary": "خبير هندسة برمجيات وبنية تحتية سحابية. يقود التحول الرقمي والذكاء الاصطناعي للمشاريع الكبرى في المملكة العربية السعودية.",
            "followersCount": 48000,
            "connectionsCount": 500,
            "publicIdentifier": "tariq-almansoor",
        },
        "positionGroupView": {
            "elements": [
                {
                    "name": "Saudi Digital Hub",
                    "positions": [
                        {
                            "title": "Vice President of Engineering",
                            "companyName": "Saudi Digital Hub",
                            "locationName": "Riyadh, Saudi Arabia",
                            "description": "إدارة الفرق التقنية وتطوير الأنظمة السحابية عالية الأداء لخدمة الملايين.",
                            "timePeriod": {"startDate": {"month": 3, "year": 2021}},
                        }
                    ],
                }
            ]
        },
        "skillView": {
            "elements": [
                {"name": "Cloud Computing (الحوسبة السحابية)"},
                {"name": "Kubernetes 🐳"},
                {"name": "Digital Transformation"},
                {"name": "Cybersecurity"},
            ]
        },
        "languageView": {
            "elements": [
                {
                    "name": "العربية (Arabic)",
                    "proficiency": "Native or bilingual proficiency",
                },
                {"name": "English", "proficiency": "Full professional proficiency"},
            ]
        },
    }


def _build_chinese_fintech_lead() -> dict[str, Any]:
    return {
        "profile": {
            "entityUrn": "urn:li:fs_profile:ZH_001_WEI",
            "firstName": "伟 (Wei)",
            "lastName": "张 (Zhang)",
            "headline": "Head of Quantitative AI @ Ant Group 🇨🇳 | High-Frequency Trading & Low Latency Systems",
            "locationName": "Shanghai, China",
            "geoCountryName": "China",
            "industryName": "Financial Technology",
            "summary": "专注于量化交易、高频低延迟分布式架构以及金融大模型应用。清华大学计算机系校友。",
            "followersCount": 65000,
            "connectionsCount": 500,
            "publicIdentifier": "wei-zhang-quant",
        },
        "positionGroupView": {
            "elements": [
                {
                    "name": "Ant Group",
                    "positions": [
                        {
                            "title": "Head of Quantitative AI & Algorithmic Trading",
                            "companyName": "Ant Group",
                            "locationName": "Shanghai, China",
                            "description": "Architecting C++23 low-latency matching engines and distributed machine learning inference pipelines.",
                            "timePeriod": {"startDate": {"month": 6, "year": 2020}},
                        }
                    ],
                }
            ]
        },
        "skillView": {
            "elements": [
                {"name": "Quantitative Finance"},
                {"name": "C++ / Low-Latency Systems"},
                {"name": "Machine Learning"},
                {"name": "Financial Modeling"},
            ]
        },
        "languageView": {
            "elements": [
                {
                    "name": "中文 (Mandarin)",
                    "proficiency": "Native or bilingual proficiency",
                },
                {"name": "English", "proficiency": "Full professional proficiency"},
            ]
        },
    }


def _build_minimal_sparse() -> dict[str, Any]:
    return {
        "profile": {
            "entityUrn": "urn:li:fs_profile:SPARSE_003_USER",
            "firstName": "John",
            "lastName": "Doe",
            "headline": "Explorer & Lifelong Learner",
            "publicIdentifier": "johndoe-sparse",
        }
    }


PERSONA_REGISTRY: dict[str, Callable[[], dict[str, Any]]] = {
    "software_engineer": _build_software_engineer,
    "c_level_executive": _build_c_level_executive,
    "academic_researcher": _build_academic_researcher,
    "founder_startup": _build_founder_startup,
    "multilingual_diplomat": _build_multilingual_diplomat,
    "arabic_regional_lead": _build_arabic_regional_lead,
    "chinese_fintech_lead": _build_chinese_fintech_lead,
    "minimal_sparse_user": _build_minimal_sparse,
}


def generate_dynamic_profile_payload(
    persona: str, **custom_fields: Any
) -> dict[str, Any]:
    """
    Factory function generating realistic, schema-compliant Voyager API payloads
    for diverse test personas.
    """
    builder = PERSONA_REGISTRY.get(persona)
    if not builder:
        # Fallback to software_engineer as base template
        builder = _build_software_engineer

    payload = copy.deepcopy(builder())

    # Deep merge any custom overrides
    for key, value in custom_fields.items():
        if (
            key in payload
            and isinstance(payload[key], dict)
            and isinstance(value, dict)
        ):
            payload[key].update(value)
        else:
            payload[key] = value

    return payload
