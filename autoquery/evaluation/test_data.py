"""Synthetic backward test cases for matching evaluation.

20 cases covering genre distribution:
literary fiction (3), sci-fi (2), fantasy/YA (2), romance (2),
mystery/thriller (2), historical (2), middle grade (2),
memoir/NF (2), cross-genre (3).

Replace with real data after Step 4 (data population).
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class BackwardTestCase:
    """A single backward test case."""
    id: str
    description: str
    manuscript: dict
    known_agents: list[dict] = field(default_factory=list)
    decoy_agents: list[dict] = field(default_factory=list)


def get_test_cases() -> list[BackwardTestCase]:
    """Return all 20 synthetic backward test cases."""
    return [
        # --- Literary Fiction (3) ---
        BackwardTestCase(
            id="lit_fic_01",
            description="Upmarket literary fiction about family secrets",
            manuscript={
                "genre": "literary_fiction",
                "audience": ["adult"],
                "themes": ["family", "secrets", "identity"],
                "comps": ["Normal People", "The Goldfinch"],
                "query_letter": "A multigenerational saga exploring how one family's buried secrets ripple through decades.",
            },
            known_agents=[
                {"name": "Agent LF1", "genres": ["literary_fiction"], "audience": ["adult"], "keywords": ["upmarket", "family", "character-driven"], "agency": "Agency Alpha"},
                {"name": "Agent LF2", "genres": ["literary_fiction", "book_club_fiction"], "audience": ["adult"], "keywords": ["debut", "literary", "contemporary"], "agency": "Agency Beta"},
            ],
            decoy_agents=[
                {"name": "Decoy SF1", "genres": ["science_fiction"], "audience": ["adult"], "keywords": ["hard sci-fi", "space opera"], "agency": "Agency Gamma"},
                {"name": "Decoy ROM1", "genres": ["romance"], "audience": ["adult"], "keywords": ["contemporary romance", "rom-com"], "agency": "Agency Delta"},
            ],
        ),
        BackwardTestCase(
            id="lit_fic_02",
            description="Experimental literary fiction with unreliable narrator",
            manuscript={
                "genre": "literary_fiction",
                "audience": ["adult"],
                "themes": ["memory", "truth", "perception"],
                "comps": ["Gone Girl", "We Need to Talk About Kevin"],
                "query_letter": "An unreliable narrator reconstructs events that may or may not have happened.",
            },
            known_agents=[
                {"name": "Agent LF3", "genres": ["literary_fiction"], "audience": ["adult"], "keywords": ["experimental", "psychological", "voice-driven"], "agency": "Agency Epsilon"},
            ],
            decoy_agents=[
                {"name": "Decoy KID1", "genres": ["middle_grade"], "audience": ["middle_grade"], "keywords": ["adventure", "humor"], "agency": "Agency Zeta"},
            ],
        ),
        BackwardTestCase(
            id="lit_fic_03",
            description="Quiet literary fiction set in rural Japan",
            manuscript={
                "genre": "literary_fiction",
                "audience": ["adult"],
                "themes": ["solitude", "nature", "aging"],
                "comps": ["A Man Called Ove", "Convenience Store Woman"],
                "query_letter": "An elderly beekeeper in rural Japan contemplates life after his wife's passing.",
            },
            known_agents=[
                {"name": "Agent LF4", "genres": ["literary_fiction"], "audience": ["adult"], "keywords": ["international", "quiet", "contemplative"], "agency": "Agency Eta"},
            ],
            decoy_agents=[
                {"name": "Decoy THR1", "genres": ["thriller"], "audience": ["adult"], "keywords": ["fast-paced", "action"], "agency": "Agency Theta"},
            ],
        ),
        # --- Sci-Fi (2) ---
        BackwardTestCase(
            id="sci_fi_01",
            description="Hard sci-fi about generation ship to Proxima Centauri",
            manuscript={
                "genre": "science_fiction",
                "audience": ["adult"],
                "themes": ["colonization", "survival", "ethics"],
                "comps": ["The Expanse", "Seveneves"],
                "query_letter": "Three generations aboard a failing generation ship must decide who lives and who dies.",
            },
            known_agents=[
                {"name": "Agent SF1", "genres": ["science_fiction"], "audience": ["adult"], "keywords": ["hard sci-fi", "space", "speculative"], "agency": "Agency Iota"},
                {"name": "Agent SF2", "genres": ["science_fiction", "speculative_fiction"], "audience": ["adult"], "keywords": ["futurism", "technology"], "agency": "Agency Kappa"},
            ],
            decoy_agents=[
                {"name": "Decoy ROM2", "genres": ["romance"], "audience": ["adult"], "keywords": ["historical romance"], "agency": "Agency Lambda"},
            ],
        ),
        BackwardTestCase(
            id="sci_fi_02",
            description="Near-future climate fiction",
            manuscript={
                "genre": "science_fiction",
                "audience": ["adult"],
                "themes": ["climate change", "migration", "resilience"],
                "comps": ["The Water Knife", "Ministry for the Future"],
                "query_letter": "In 2045, a climate refugee navigates a flooded Miami while protecting a piece of old-world technology.",
            },
            known_agents=[
                {"name": "Agent SF3", "genres": ["science_fiction"], "audience": ["adult"], "keywords": ["cli-fi", "near-future", "dystopia"], "agency": "Agency Mu"},
            ],
            decoy_agents=[
                {"name": "Decoy FAN1", "genres": ["fantasy"], "audience": ["young_adult"], "keywords": ["epic fantasy", "magic systems"], "agency": "Agency Nu"},
            ],
        ),
        # --- Fantasy / YA (2) ---
        BackwardTestCase(
            id="fantasy_ya_01",
            description="YA fantasy with a queer protagonist",
            manuscript={
                "genre": "fantasy",
                "audience": ["young_adult"],
                "themes": ["identity", "chosen family", "magic"],
                "comps": ["The Priory of the Orange Tree", "Cemetery Boys"],
                "query_letter": "A nonbinary mage must unite warring factions to prevent a magical catastrophe.",
            },
            known_agents=[
                {"name": "Agent FY1", "genres": ["fantasy"], "audience": ["young_adult"], "keywords": ["YA fantasy", "diverse", "LGBTQ+"], "agency": "Agency Xi"},
                {"name": "Agent FY2", "genres": ["fantasy", "young_adult"], "audience": ["young_adult"], "keywords": ["magic", "queer", "adventure"], "agency": "Agency Omicron"},
            ],
            decoy_agents=[
                {"name": "Decoy MEM1", "genres": ["memoir"], "audience": ["adult"], "keywords": ["celebrity memoir"], "agency": "Agency Pi"},
            ],
        ),
        BackwardTestCase(
            id="fantasy_ya_02",
            description="Dark fantasy with morally grey characters",
            manuscript={
                "genre": "fantasy",
                "audience": ["young_adult", "adult"],
                "themes": ["power", "corruption", "revenge"],
                "comps": ["Six of Crows", "The Poppy War"],
                "query_letter": "A young assassin infiltrates the court of the king she plans to kill.",
            },
            known_agents=[
                {"name": "Agent FY3", "genres": ["fantasy"], "audience": ["young_adult", "adult"], "keywords": ["dark fantasy", "complex characters"], "agency": "Agency Rho"},
            ],
            decoy_agents=[
                {"name": "Decoy MG1", "genres": ["middle_grade"], "audience": ["middle_grade"], "keywords": ["cozy", "friendship"], "agency": "Agency Sigma"},
            ],
        ),
        # --- Romance (2) ---
        BackwardTestCase(
            id="romance_01",
            description="Contemporary romance with enemies-to-lovers trope",
            manuscript={
                "genre": "romance",
                "audience": ["adult"],
                "themes": ["rivalry", "second chances", "vulnerability"],
                "comps": ["The Hating Game", "Beach Read"],
                "query_letter": "Two rival pastry chefs are forced to share a kitchen — and confront their feelings.",
            },
            known_agents=[
                {"name": "Agent ROM1", "genres": ["romance"], "audience": ["adult"], "keywords": ["rom-com", "contemporary", "enemies-to-lovers"], "agency": "Agency Tau"},
                {"name": "Agent ROM2", "genres": ["romance", "women's_fiction"], "audience": ["adult"], "keywords": ["romance", "heartwarming"], "agency": "Agency Upsilon"},
            ],
            decoy_agents=[
                {"name": "Decoy SF4", "genres": ["science_fiction"], "audience": ["adult"], "keywords": ["cyberpunk"], "agency": "Agency Phi"},
            ],
        ),
        BackwardTestCase(
            id="romance_02",
            description="Historical romance set in Regency England",
            manuscript={
                "genre": "romance",
                "audience": ["adult"],
                "themes": ["class", "scandal", "passion"],
                "comps": ["Bridgerton", "A Rogue by Any Other Name"],
                "query_letter": "A duke's scandalous daughter falls for a self-made merchant who threatens everything she knows.",
            },
            known_agents=[
                {"name": "Agent ROM3", "genres": ["romance", "historical_fiction"], "audience": ["adult"], "keywords": ["regency", "historical romance"], "agency": "Agency Chi"},
            ],
            decoy_agents=[
                {"name": "Decoy MG2", "genres": ["middle_grade"], "audience": ["middle_grade"], "keywords": ["science", "STEM"], "agency": "Agency Psi"},
            ],
        ),
        # --- Mystery / Thriller (2) ---
        BackwardTestCase(
            id="mystery_01",
            description="Cozy mystery with a bookstore owner sleuth",
            manuscript={
                "genre": "mystery",
                "audience": ["adult"],
                "themes": ["community", "justice", "curiosity"],
                "comps": ["The Thursday Murder Club", "Maisie Dobbs"],
                "query_letter": "When a rare book goes missing and its collector turns up dead, a small-town bookstore owner investigates.",
            },
            known_agents=[
                {"name": "Agent MYS1", "genres": ["mystery"], "audience": ["adult"], "keywords": ["cozy mystery", "amateur sleuth"], "agency": "Agency Omega"},
                {"name": "Agent MYS2", "genres": ["mystery", "crime_fiction"], "audience": ["adult"], "keywords": ["whodunit", "traditional mystery"], "agency": "Agency AA"},
            ],
            decoy_agents=[
                {"name": "Decoy FAN2", "genres": ["fantasy"], "audience": ["young_adult"], "keywords": ["portal fantasy"], "agency": "Agency BB"},
            ],
        ),
        BackwardTestCase(
            id="thriller_01",
            description="Psychological thriller about a missing spouse",
            manuscript={
                "genre": "thriller",
                "audience": ["adult"],
                "themes": ["deception", "trust", "obsession"],
                "comps": ["Gone Girl", "The Silent Patient"],
                "query_letter": "A woman discovers her missing husband may never have existed at all.",
            },
            known_agents=[
                {"name": "Agent THR1", "genres": ["thriller", "suspense"], "audience": ["adult"], "keywords": ["psychological thriller", "twist", "domestic"], "agency": "Agency CC"},
            ],
            decoy_agents=[
                {"name": "Decoy ROM3", "genres": ["romance"], "audience": ["adult"], "keywords": ["sweet romance"], "agency": "Agency DD"},
            ],
        ),
        # --- Historical (2) ---
        BackwardTestCase(
            id="hist_01",
            description="WWII historical fiction about a female spy",
            manuscript={
                "genre": "historical_fiction",
                "audience": ["adult"],
                "themes": ["courage", "sacrifice", "espionage"],
                "comps": ["The Alice Network", "The Nightingale"],
                "query_letter": "A French resistance fighter risks everything to transmit coded messages from occupied Paris.",
            },
            known_agents=[
                {"name": "Agent HF1", "genres": ["historical_fiction"], "audience": ["adult"], "keywords": ["WWII", "women's history", "espionage"], "agency": "Agency EE"},
                {"name": "Agent HF2", "genres": ["historical_fiction", "literary_fiction"], "audience": ["adult"], "keywords": ["historical", "war fiction"], "agency": "Agency FF"},
            ],
            decoy_agents=[
                {"name": "Decoy SF5", "genres": ["science_fiction"], "audience": ["adult"], "keywords": ["AI", "singularity"], "agency": "Agency GG"},
            ],
        ),
        BackwardTestCase(
            id="hist_02",
            description="Ancient Rome historical epic",
            manuscript={
                "genre": "historical_fiction",
                "audience": ["adult"],
                "themes": ["power", "betrayal", "legacy"],
                "comps": ["Circe", "The Pillars of the Earth"],
                "query_letter": "A Roman senator's son must choose between loyalty to his father and the republic.",
            },
            known_agents=[
                {"name": "Agent HF3", "genres": ["historical_fiction"], "audience": ["adult"], "keywords": ["ancient history", "epic"], "agency": "Agency HH"},
            ],
            decoy_agents=[
                {"name": "Decoy KID2", "genres": ["middle_grade"], "audience": ["middle_grade"], "keywords": ["funny", "school"], "agency": "Agency II"},
            ],
        ),
        # --- Middle Grade (2) ---
        BackwardTestCase(
            id="mg_01",
            description="Middle grade adventure with found family",
            manuscript={
                "genre": "middle_grade",
                "audience": ["middle_grade"],
                "themes": ["friendship", "bravery", "belonging"],
                "comps": ["Percy Jackson", "The Wild Robot"],
                "query_letter": "Three misfit kids discover a hidden world beneath their school and must protect it from developers.",
            },
            known_agents=[
                {"name": "Agent MG1", "genres": ["middle_grade"], "audience": ["middle_grade"], "keywords": ["adventure", "friendship", "humor"], "agency": "Agency JJ"},
                {"name": "Agent MG2", "genres": ["middle_grade", "fantasy"], "audience": ["middle_grade", "young_adult"], "keywords": ["MG fantasy", "quest"], "agency": "Agency KK"},
            ],
            decoy_agents=[
                {"name": "Decoy THR2", "genres": ["thriller"], "audience": ["adult"], "keywords": ["crime", "noir"], "agency": "Agency LL"},
            ],
        ),
        BackwardTestCase(
            id="mg_02",
            description="Realistic middle grade about a deaf protagonist",
            manuscript={
                "genre": "middle_grade",
                "audience": ["middle_grade"],
                "themes": ["disability", "resilience", "self-acceptance"],
                "comps": ["El Deafo", "Wonder"],
                "query_letter": "A newly deaf 11-year-old navigates a hearing school while discovering her artistic talent.",
            },
            known_agents=[
                {"name": "Agent MG3", "genres": ["middle_grade"], "audience": ["middle_grade"], "keywords": ["own-voices", "diverse", "contemporary MG"], "agency": "Agency MM"},
            ],
            decoy_agents=[
                {"name": "Decoy ROM4", "genres": ["romance"], "audience": ["adult"], "keywords": ["erotic romance"], "agency": "Agency NN"},
            ],
        ),
        # --- Memoir / NF (2) ---
        BackwardTestCase(
            id="memoir_01",
            description="Memoir about overcoming addiction",
            manuscript={
                "genre": "memoir",
                "audience": ["adult"],
                "themes": ["recovery", "family", "honesty"],
                "comps": ["Beautiful Boy", "Educated"],
                "query_letter": "A surgeon recounts losing and rebuilding her career after opioid addiction.",
            },
            known_agents=[
                {"name": "Agent NF1", "genres": ["memoir", "narrative_nonfiction"], "audience": ["adult"], "keywords": ["memoir", "health", "personal narrative"], "agency": "Agency OO"},
                {"name": "Agent NF2", "genres": ["narrative_nonfiction"], "audience": ["adult"], "keywords": ["nonfiction", "autobiography"], "agency": "Agency PP"},
            ],
            decoy_agents=[
                {"name": "Decoy FAN3", "genres": ["fantasy"], "audience": ["young_adult"], "keywords": ["dragons", "magic school"], "agency": "Agency QQ"},
            ],
        ),
        BackwardTestCase(
            id="nf_01",
            description="Popular science book about consciousness",
            manuscript={
                "genre": "narrative_nonfiction",
                "audience": ["adult"],
                "themes": ["neuroscience", "philosophy", "self"],
                "comps": ["Thinking, Fast and Slow", "The Body Keeps the Score"],
                "query_letter": "A neuroscientist explains why the brain creates the illusion of a unified self.",
            },
            known_agents=[
                {"name": "Agent NF3", "genres": ["narrative_nonfiction", "popular_science"], "audience": ["adult"], "keywords": ["science", "popular nonfiction"], "agency": "Agency RR"},
            ],
            decoy_agents=[
                {"name": "Decoy MG3", "genres": ["middle_grade"], "audience": ["middle_grade"], "keywords": ["graphic novel"], "agency": "Agency SS"},
            ],
        ),
        # --- Cross-Genre (3) ---
        BackwardTestCase(
            id="cross_01",
            description="Literary thriller with speculative elements",
            manuscript={
                "genre": "literary_fiction",
                "audience": ["adult"],
                "themes": ["surveillance", "paranoia", "resistance"],
                "comps": ["1984", "The Power"],
                "query_letter": "In a near-future surveillance state, a librarian discovers banned books can alter reality.",
            },
            known_agents=[
                {"name": "Agent CG1", "genres": ["literary_fiction", "speculative_fiction"], "audience": ["adult"], "keywords": ["literary thriller", "speculative", "dystopia"], "agency": "Agency TT"},
                {"name": "Agent CG2", "genres": ["literary_fiction", "thriller"], "audience": ["adult"], "keywords": ["literary suspense", "high-concept"], "agency": "Agency UU"},
            ],
            decoy_agents=[
                {"name": "Decoy MG4", "genres": ["middle_grade"], "audience": ["middle_grade"], "keywords": ["pets", "animals"], "agency": "Agency VV"},
            ],
        ),
        BackwardTestCase(
            id="cross_02",
            description="Romantic suspense with historical setting",
            manuscript={
                "genre": "romance",
                "audience": ["adult"],
                "themes": ["danger", "passion", "secrets"],
                "comps": ["Outlander", "The Bronze Horseman"],
                "query_letter": "A war nurse in 1942 Italy falls for a partisan fighter while hiding a dangerous secret.",
            },
            known_agents=[
                {"name": "Agent CG3", "genres": ["romance", "historical_fiction"], "audience": ["adult"], "keywords": ["romantic suspense", "WWII", "dual timeline"], "agency": "Agency WW"},
            ],
            decoy_agents=[
                {"name": "Decoy SF6", "genres": ["science_fiction"], "audience": ["young_adult"], "keywords": ["robots", "AI"], "agency": "Agency XX"},
            ],
        ),
        BackwardTestCase(
            id="cross_03",
            description="Upmarket women's fiction with mystery elements",
            manuscript={
                "genre": "women's_fiction",
                "audience": ["adult"],
                "themes": ["sisterhood", "loss", "reinvention"],
                "comps": ["Big Little Lies", "Where the Crawdads Sing"],
                "query_letter": "Four estranged sisters reunite at their mother's lakehouse and uncover a decades-old mystery.",
            },
            known_agents=[
                {"name": "Agent CG4", "genres": ["women's_fiction", "mystery"], "audience": ["adult"], "keywords": ["book club", "family drama", "mystery"], "agency": "Agency YY"},
                {"name": "Agent CG5", "genres": ["women's_fiction", "literary_fiction"], "audience": ["adult"], "keywords": ["upmarket", "women's fiction"], "agency": "Agency ZZ"},
            ],
            decoy_agents=[
                {"name": "Decoy SF7", "genres": ["science_fiction"], "audience": ["adult"], "keywords": ["military sci-fi"], "agency": "Agency AAA"},
            ],
        ),
    ]
