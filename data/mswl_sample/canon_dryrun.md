# Canon Dry-Run — MSWL Sample (48 profiles)

First-pass canon validation. Each raw term is normalized and looked up in
`canon/aliases.yaml`. Unmapped terms are tagged via the decision-flow in
`docs/features/16_l2_canonicalization.md`.

**Not a v1 lock.** 50 profiles is a first pass; the LOCAL-extension threshold
(≥5 profiles) at this sample size biases toward `dismiss`.
v1 lock still requires ≥200 production profiles via Step 4.

## Coverage per facet

| Facet | Mapped | Total | Coverage | Target | Status |
|---|---:|---:|---:|---:|---|
| subject | 308 | 598 | 51.5% | 90% | ⚠️ below target |
| audience | 112 | 211 | 53.1% | 90% | ⚠️ below target |
| hard_no | 2 | 463 | 0.4% | 70% | ⚠️ below target |

## Subject — unmapped terms (top 50 of 233)

- LOCAL-extension candidates (≥5 profiles): **2**
- Alias-candidates (token overlap, <5 profiles): **147**
- Dismiss: **84**

| Normalized term | Profiles | Action |
|---|---:|---|
| `gothic horror` | 5 | LOCAL_candidate |
| `psychological horror` | 5 | LOCAL_candidate |
| `cookbooks` | 3 | dismiss |
| `feminist horror` | 3 | alias_candidate |
| `gothic fantasy` | 3 | alias_candidate |
| `graphic novels` | 3 | dismiss |
| `history` | 3 | alias_candidate |
| `lifestyle` | 3 | dismiss |
| `mythic horror` | 3 | alias_candidate |
| `pop culture` | 3 | dismiss |
| `self-help` | 3 | dismiss |
| `upmarket commercial fiction` | 3 | alias_candidate |
| `upmarket womens fiction` | 3 | alias_candidate |
| `body horror` | 2 | alias_candidate |
| `character-driven horror` | 2 | alias_candidate |
| `current events` | 2 | dismiss |
| `detective` | 2 | alias_candidate |
| `gothic historical` | 2 | alias_candidate |
| `investigative journalism` | 2 | alias_candidate |
| `lgbtq romance` | 2 | alias_candidate |
| `light fantasy` | 2 | alias_candidate |
| `literary mystery` | 2 | alias_candidate |
| `non-fiction` | 2 | alias_candidate |
| `pop science` | 2 | alias_candidate |
| `popular science` | 2 | alias_candidate |
| `psychological suspense` | 2 | alias_candidate |
| `rom-coms` | 2 | dismiss |
| `southern gothic` | 2 | alias_candidate |
| `upmarket horror` | 2 | alias_candidate |
| `accessible literary fiction` | 1 | alias_candidate |
| `afrofuturism` | 1 | dismiss |
| `all genres` | 1 | dismiss |
| `all sub-genres` | 1 | dismiss |
| `amateur sleuth` | 1 | alias_candidate |
| `americana` | 1 | dismiss |
| `atmospheric` | 1 | dismiss |
| `beach reads` | 1 | dismiss |
| `bible studies` | 1 | dismiss |
| `biographical fiction` | 1 | alias_candidate |
| `blended memoir` | 1 | alias_candidate |
| `bookclub fiction` | 1 | alias_candidate |
| `bookclub-with-an-edge` | 1 | dismiss |
| `books about work` | 1 | alias_candidate |
| `campus novel` | 1 | alias_candidate |
| `careers` | 1 | dismiss |
| `category romance` | 1 | alias_candidate |
| `character-driven sci-fi` | 1 | alias_candidate |
| `childrens literature` | 1 | dismiss |
| `christian living` | 1 | dismiss |
| `clever horror` | 1 | alias_candidate |

## Audience — unmapped terms (top 50 of 6)

- LOCAL-extension candidates (≥5 profiles): **4**
- Alias-candidates (token overlap, <5 profiles): **0**
- Dismiss: **2**

| Normalized term | Profiles | Action |
|---|---:|---|
| `young_adult` | 24 | LOCAL_candidate |
| `middle_grade` | 16 | LOCAL_candidate |
| `picture_books` | 8 | LOCAL_candidate |
| `new_adult` | 7 | LOCAL_candidate |
| `all_ages` | 3 | dismiss |
| `crossover` | 1 | dismiss |

## Hard_no — unmapped terms (top 50 of 349)

- LOCAL-extension candidates (≥5 profiles): **2**
- Alias-candidates (token overlap, <5 profiles): **94**
- Dismiss: **253**

| Normalized term | Profiles | Action |
|---|---:|---|
| `not specified` | 7 | LOCAL_candidate |
| `erotica` | 5 | LOCAL_candidate |
| `middle grade` | 4 | dismiss |
| `picture books` | 4 | alias_candidate |
| `poetry` | 4 | dismiss |
| `screenplays` | 4 | dismiss |
| `short story collections` | 4 | dismiss |
| `mg` | 3 | dismiss |
| `self-help` | 3 | dismiss |
| `true crime` | 3 | dismiss |
| `ya` | 3 | dismiss |
| `anthologies` | 2 | dismiss |
| `childrens books` | 2 | alias_candidate |
| `dark romance` | 2 | dismiss |
| `fantasy` | 2 | dismiss |
| `ghosts` | 2 | dismiss |
| `graphic novels` | 2 | alias_candidate |
| `hard sci-fi` | 2 | dismiss |
| `hard science fiction` | 2 | dismiss |
| `high fantasy` | 2 | dismiss |
| `historical fiction` | 2 | dismiss |
| `none explicitly stated` | 2 | dismiss |
| `none specified` | 2 | dismiss |
| `not explicitly listed` | 2 | dismiss |
| `not specified for this section` | 2 | dismiss |
| `not specified in this section` | 2 | dismiss |
| `novellas` | 2 | dismiss |
| `police procedurals` | 2 | dismiss |
| `romantasy` | 2 | dismiss |
| `sports romance` | 2 | dismiss |
| `thrillers` | 2 | dismiss |
| `young adult` | 2 | dismiss |
| `000 words` | 1 | dismiss |
| `000 words automatic decline for most` | 1 | dismiss |
| `000 words signals lack of editing eye` | 1 | dismiss |
| `adaptations` | 1 | dismiss |
| `adult memoirs no longer accepting` | 1 | dismiss |
| `afterlives` | 1 | dismiss |
| `ai as a core element tough sell` | 1 | alias_candidate |
| `almost any memoir` | 1 | alias_candidate |
| `almost never best fit for high fantasy` | 1 | dismiss |
| `amnesia as a trope` | 1 | dismiss |
| `and select pb` | 1 | alias_candidate |
| `and similar subgenres` | 1 | dismiss |
| `animal protagonists` | 1 | alias_candidate |
| `any work for young adult audiences and younger exclusively focusing on adult readers only` | 1 | dismiss |
| `any work using ai in creation` | 1 | alias_candidate |
| `anything for kids younger than upper middle grade` | 1 | dismiss |
| `anything with weird formatting my eyes cant handle it` | 1 | dismiss |
| `anything written by ai` | 1 | alias_candidate |

## Summary

At least one facet is below its v1 target. Review the unmapped-term
leaderboards, add aliases for clear synonyms, evaluate LOCAL-candidates
against the decision-flow rules, then rerun.

