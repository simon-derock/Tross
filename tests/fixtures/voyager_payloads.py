"""
tests/fixtures/voyager_payloads.py
──────────────────────────────────
Realistic LinkedIn Voyager API profileView JSON fixtures.
Mirrors the actual Restli/JSON data returned by:
  GET https://www.linkedin.com/voyager/api/identity/profiles/{slug}/profileView
"""

from __future__ import annotations

FULL_VOYAGER_PROFILE_VIEW_PAYLOAD = {
    "profile": {
        "entityUrn": "urn:li:fs_profile:ACoAAABBBCC123",
        "firstName": "Satya",
        "lastName": "Nadella",
        "headline": "Chairman and CEO at Microsoft",
        "locationName": "Greater Seattle Area",
        "geoCountryName": "United States",
        "industryName": "Computer Software",
        "summary": "Satya Nadella is Chairman and Chief Executive Officer of Microsoft. Before being named CEO in February 2014, Nadella held leadership roles in both enterprise and consumer businesses across the company.",
        "followersCount": 10500000,
        "connectionsCount": 500,
        "publicIdentifier": "satyanadella",
        "profilePicture": {
            "displayImageReference": {
                "vectorImage": {
                    "rootUrl": "https://media.licdn.com/dms/image/v2/D5603AQ/",
                    "artifacts": [
                        {
                            "width": 100,
                            "height": 100,
                            "fileIdentifyingUrlPathSegment": "profile-displayphoto-shrink_100_100/0/123456?e=1710000000&v=beta&t=abc",
                        },
                        {
                            "width": 200,
                            "height": 200,
                            "fileIdentifyingUrlPathSegment": "profile-displayphoto-shrink_200_200/0/123456?e=1710000000&v=beta&t=def",
                        },
                        {
                            "width": 800,
                            "height": 800,
                            "fileIdentifyingUrlPathSegment": "profile-displayphoto-shrink_800_800/0/123456?e=1710000000&v=beta&t=ghi",
                        },
                    ],
                }
            }
        },
        "backgroundPicture": {
            "displayImageReference": {
                "vectorImage": {
                    "rootUrl": "https://media.licdn.com/dms/image/v2/D5616AQ/",
                    "artifacts": [
                        {
                            "width": 1400,
                            "height": 350,
                            "fileIdentifyingUrlPathSegment": "profile-displaybackgroundimage-shrink_350_1400/0/banner.jpg?e=1710000000&v=beta&t=banner",
                        }
                    ],
                }
            }
        },
    },
    "positionGroupView": {
        "elements": [
            {
                "name": "Microsoft",
                "miniCompany": {
                    "name": "Microsoft",
                    "objectUrn": "urn:li:company:1035",
                    "universalName": "microsoft",
                },
                "positions": [
                    {
                        "title": "Chairman and CEO",
                        "companyName": "Microsoft",
                        "locationName": "Redmond, Washington, United States",
                        "description": "Leading Microsoft's mission to empower every person and organization on the planet to achieve more.",
                        "timePeriod": {
                            "startDate": {"month": 2, "year": 2014},
                        },
                    },
                    {
                        "title": "Executive Vice President, Cloud and Enterprise",
                        "companyName": "Microsoft",
                        "locationName": "Redmond, WA",
                        "description": "Led the transformation to the cloud infrastructure and services business.",
                        "timePeriod": {
                            "startDate": {"month": 1, "year": 2011},
                            "endDate": {"month": 2, "year": 2014},
                        },
                    },
                ],
            },
            {
                "name": "Sun Microsystems",
                "miniCompany": {
                    "name": "Sun Microsystems",
                    "objectUrn": "urn:li:company:1063",
                    "universalName": "sun-microsystems",
                },
                "positions": [
                    {
                        "title": "Member of Technology Staff",
                        "companyName": "Sun Microsystems",
                        "locationName": "Mountain View, CA",
                        "description": "Worked on distributed computing systems.",
                        "timePeriod": {
                            "startDate": {"month": 6, "year": 1990},
                            "endDate": {"month": 12, "year": 1992},
                        },
                    }
                ],
            },
        ]
    },
    "educationView": {
        "elements": [
            {
                "schoolName": "The University of Chicago Booth School of Business",
                "school": {
                    "objectUrn": "urn:li:school:6151",
                    "schoolName": "The University of Chicago Booth School of Business",
                },
                "degreeName": "Master of Business Administration (MBA)",
                "fieldOfStudy": "Business Administration and Management",
                "timePeriod": {
                    "startDate": {"year": 1995},
                    "endDate": {"year": 1997},
                },
                "description": "Concentrations in Finance and Strategy.",
            },
            {
                "schoolName": "University of Wisconsin-Milwaukee",
                "school": {
                    "objectUrn": "urn:li:school:4278",
                    "schoolName": "University of Wisconsin-Milwaukee",
                },
                "degreeName": "Master of Science (MS)",
                "fieldOfStudy": "Computer Science",
                "timePeriod": {
                    "startDate": {"year": 1988},
                    "endDate": {"year": 1990},
                },
            },
            {
                "schoolName": "Manipal Institute of Technology",
                "school": {
                    "objectUrn": "urn:li:school:13500",
                    "schoolName": "Manipal Institute of Technology",
                },
                "degreeName": "Bachelor of Engineering (B.E.)",
                "fieldOfStudy": "Electrical and Electronics Engineering",
                "timePeriod": {
                    "startDate": {"year": 1984},
                    "endDate": {"year": 1988},
                },
            },
        ]
    },
    "skillView": {
        "elements": [
            {"name": "Cloud Computing"},
            {"name": "Enterprise Software"},
            {"name": "Distributed Systems"},
            {"name": "SaaS"},
            {"name": "Strategic Leadership"},
        ]
    },
    "certificationView": {
        "elements": [
            {
                "name": "Advanced Executive Leadership",
                "authority": "Harvard Business School Executive Education",
                "licenseNumber": "EXEC-9921",
                "url": "https://www.exed.hbs.edu/verify/EXEC-9921",
                "timePeriod": {
                    "startDate": {"month": 5, "year": 2005},
                },
            }
        ]
    },
    "languageView": {
        "elements": [
            {"name": "English", "proficiency": "Native or bilingual proficiency"},
            {"name": "Telugu", "proficiency": "Native or bilingual proficiency"},
            {"name": "Hindi", "proficiency": "Professional working proficiency"},
        ]
    },
}

MINIMAL_VOYAGER_PROFILE_VIEW_PAYLOAD = {
    "profile": {
        "firstName": "John",
        "lastName": "Doe",
        "publicIdentifier": "johndoe",
    },
    "positionGroupView": {"elements": []},
    "educationView": {"elements": []},
    "skillView": {"elements": []},
    "certificationView": {"elements": []},
    "languageView": {"elements": []},
}

UNICODE_VOYAGER_PROFILE_VIEW_PAYLOAD = {
    "profile": {
        "firstName": "محمد",
        "lastName": "العتيبي",
        "headline": "مهندس برمجيات ومطور أنظمة موزعة 🚀 | Tech Lead",
        "locationName": "الرياض، المملكة العربية السعودية",
        "summary": "خبرة تزيد عن 10 سنوات في بناء وتطوير الأنظمة السحابية والحلول الرقمية المتقدمة.",
        "publicIdentifier": "mohammed-alotaibi",
    },
    "positionGroupView": {
        "elements": [
            {
                "name": "شركة التقنية المتقدمة",
                "positions": [
                    {
                        "title": "رئيس المهندسين | Chief Engineer",
                        "companyName": "شركة التقنية المتقدمة",
                        "timePeriod": {
                            "startDate": {"month": 1, "year": 2020},
                        },
                    }
                ],
            }
        ]
    },
    "skillView": {
        "elements": [
            {"name": "بايثون (Python)"},
            {"name": "الأنظمة الموزعة"},
            {"name": "Kubernetes 🐳"},
        ]
    },
}

INCLUDED_ENTITIES_VOYAGER_PAYLOAD = {
    "included": [
        {
            "$type": "com.linkedin.voyager.dash.identity.profile.Profile",
            "entityUrn": "urn:li:fsd_profile:12345",
            "publicIdentifier": "alice-smith",
            "firstName": "Alice",
            "lastName": "Smith",
            "headline": "VP of AI Research",
            "locationName": "London, Greater London, United Kingdom",
            "summary": "Pioneering deep learning applications in healthcare.",
            "profilePicture": {
                "displayImageReference": {
                    "vectorImage": {
                        "rootUrl": "https://media.licdn.com/dms/image/v2/XYZ/",
                        "artifacts": [
                            {
                                "fileIdentifyingUrlPathSegment": "pic_400.jpg",
                                "width": 400,
                                "height": 400,
                            }
                        ],
                    }
                }
            },
        },
        {
            "$type": "com.linkedin.voyager.dash.identity.profile.Position",
            "title": "VP AI Research",
            "companyName": "DeepBio Labs",
            "locationName": "London, UK",
            "dateRange": {"start": {"month": 6, "year": 2021}},
        },
        {
            "$type": "com.linkedin.voyager.dash.identity.profile.Education",
            "schoolName": "University of Oxford",
            "degreeName": "DPhil",
            "fieldOfStudy": "Computer Science",
            "dateRange": {"start": {"year": 2012}, "end": {"year": 2016}},
        },
        {
            "$type": "com.linkedin.voyager.dash.identity.profile.Skill",
            "name": "Machine Learning",
        },
    ]
}
