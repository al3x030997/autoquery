"""
AutoQuery Review UI — Streamlit app for reviewing extracted agent profiles,
managing domains, and viewing crawl statistics.
"""
import asyncio
from contextlib import contextmanager

import pandas as pd
import streamlit as st
from sqlalchemy import func

from autoquery.database.db import SessionLocal
from autoquery.database.models import (
    Agent,
    CrawledPage,
    CrawlRun,
    KnownProfileUrl,
    REVIEW_STATUS_PENDING,
    REVIEW_STATUS_APPROVED,
    REVIEW_STATUS_REJECTED,
    REVIEW_STATUS_EXTRACTION_FAILED,
)
from autoquery.review.operations import (
    approve_agent,
    reject_agent,
    validate_domain,
    parse_csv_domains,
    add_domains_to_seed_list,
)

st.set_page_config(page_title="AutoQuery Review", layout="wide")
st.title("AutoQuery Review UI")

QUALITY_COLORS = {
    "high": "#22c55e",     # green, score >= 0.65
    "medium": "#eab308",   # yellow, 0.40 <= score < 0.65
    "low": "#ef4444",      # red, score < 0.40
}

# Standard genre list for multiselect
GENRE_OPTIONS = [
    "literary_fiction", "commercial_fiction", "science_fiction", "fantasy",
    "romance", "mystery", "thriller", "horror", "historical_fiction",
    "young_adult", "middle_grade", "picture_books", "memoir",
    "narrative_nonfiction", "self_help", "biography", "poetry",
    "graphic_novels", "womens_fiction", "upmarket_fiction",
    "speculative_fiction", "contemporary_fiction", "crime_fiction",
    "suspense", "paranormal", "dystopian", "adventure", "humor",
    "essay_collection", "cookbooks", "health_wellness", "business",
    "science", "history", "true_crime", "travel", "nature_writing",
    "sports", "music", "art", "philosophy", "religion", "politics",
    "psychology", "education", "parenting", "crafts_hobbies",
]

AUDIENCE_OPTIONS = ["adult", "ya", "middle_grade", "children", "picture_books"]


@contextmanager
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _quality_color(score: float | None) -> str:
    if score is None:
        return "#888"
    if score >= 0.65:
        return QUALITY_COLORS["high"]
    if score >= 0.40:
        return QUALITY_COLORS["medium"]
    return QUALITY_COLORS["low"]


# ---------------------------------------------------------------------------
# Navigation
# ---------------------------------------------------------------------------
page = st.sidebar.radio(
    "Navigation",
    ["Review Queue", "Domain Management", "Statistics"],
    index=0,
)


# ---------------------------------------------------------------------------
# Page 1: Review Queue
# ---------------------------------------------------------------------------
if page == "Review Queue":
    st.header("Review Queue")

    with get_db() as db:
        agents = (
            db.query(Agent)
            .filter(Agent.review_status == REVIEW_STATUS_PENDING)
            .order_by(Agent.created_at)
            .all()
        )
        # Eagerly load all data before session closes
        agent_data = []
        for a in agents:
            agent_data.append({
                "id": a.id,
                "name": a.name,
                "agency": a.agency,
                "profile_url": a.profile_url,
                "genres": list(a.genres or []),
                "keywords": list(a.keywords or []),
                "audience": list(a.audience or []),
                "hard_nos_keywords": list(a.hard_nos_keywords or []),
                "submission_req": a.submission_req,
                "is_open": a.is_open,
                "wishlist_raw": a.wishlist_raw,
                "bio_raw": a.bio_raw,
                "hard_nos_raw": a.hard_nos_raw,
                "quality_score": a.quality_score,
                "quality_action": a.quality_action,
                "email": a.email,
            })

    if not agent_data:
        st.info("No pending profiles to review.")
    else:
        st.caption(f"{len(agent_data)} profiles pending review")

        for agent in agent_data:
            aid = agent["id"]
            with st.container(border=True):
                # Header row
                col1, col2, col3 = st.columns([3, 1, 1])
                with col1:
                    st.subheader(agent["name"])
                    if agent["agency"]:
                        st.caption(f"Agency: {agent['agency']}")
                    st.markdown(f"[{agent['profile_url']}]({agent['profile_url']})")
                with col2:
                    score = agent["quality_score"]
                    color = _quality_color(score)
                    score_str = f"{score:.2f}" if score is not None else "N/A"
                    st.markdown(
                        f"**Quality:** <span style='color:{color};font-weight:bold'>{score_str}</span>",
                        unsafe_allow_html=True,
                    )
                    if agent["quality_action"] == "extract_with_warning":
                        st.warning("Extracted with quality warning", icon="⚠️")
                with col3:
                    is_open = agent["is_open"]
                    if is_open is True:
                        st.success("Open to queries")
                    elif is_open is False:
                        st.error("Closed to queries")
                    else:
                        st.info("Open status unknown")

                # Editable structured fields
                st.markdown("---")
                edit_col1, edit_col2 = st.columns(2)
                with edit_col1:
                    edited_name = st.text_input("Name", value=agent["name"], key=f"name_{aid}")
                    edited_agency = st.text_input("Agency", value=agent["agency"] or "", key=f"agency_{aid}")
                    edited_email = st.text_input("Email", value=agent["email"] or "", key=f"email_{aid}")
                    edited_genres = st.multiselect(
                        "Genres",
                        options=GENRE_OPTIONS,
                        default=[g for g in agent["genres"] if g in GENRE_OPTIONS],
                        key=f"genres_{aid}",
                    )
                    # Custom genres not in standard list
                    custom_genres = [g for g in agent["genres"] if g not in GENRE_OPTIONS]
                    if custom_genres:
                        st.caption(f"Custom genres (kept as-is): {', '.join(custom_genres)}")

                with edit_col2:
                    edited_audience = st.multiselect(
                        "Audience",
                        options=AUDIENCE_OPTIONS,
                        default=[a for a in agent["audience"] if a in AUDIENCE_OPTIONS],
                        key=f"audience_{aid}",
                    )
                    edited_keywords = st.text_area(
                        "Keywords (one per line)",
                        value="\n".join(agent["keywords"]),
                        height=100,
                        key=f"keywords_{aid}",
                    )
                    edited_hard_nos = st.text_area(
                        "Hard Nos Keywords (one per line)",
                        value="\n".join(agent["hard_nos_keywords"]),
                        height=80,
                        key=f"hard_nos_{aid}",
                    )
                    edited_is_open = st.selectbox(
                        "Open to queries?",
                        options=[True, False, None],
                        index={True: 0, False: 1, None: 2}.get(agent["is_open"], 2),
                        format_func=lambda x: {True: "Yes", False: "No", None: "Unknown"}[x],
                        key=f"is_open_{aid}",
                    )

                # Submission requirements
                sub_req = agent["submission_req"] or {}
                st.text_area(
                    "Submission Requirements (JSON)",
                    value=str(sub_req),
                    height=60,
                    key=f"sub_req_{aid}",
                    disabled=True,
                )

                # Raw text expandable sections
                with st.expander("Wishlist (raw text)"):
                    st.text_area(
                        "Wishlist",
                        value=agent["wishlist_raw"] or "(none)",
                        height=200,
                        key=f"wishlist_{aid}",
                        label_visibility="collapsed",
                    )
                with st.expander("Bio (raw text)"):
                    st.text_area(
                        "Bio",
                        value=agent["bio_raw"] or "(none)",
                        height=200,
                        key=f"bio_{aid}",
                        label_visibility="collapsed",
                    )
                with st.expander("Hard Nos (raw text)"):
                    st.text_area(
                        "Hard Nos",
                        value=agent["hard_nos_raw"] or "(none)",
                        height=150,
                        key=f"hard_nos_raw_{aid}",
                        label_visibility="collapsed",
                    )

                # Action buttons
                btn_col1, btn_col2, btn_col3 = st.columns(3)
                with btn_col1:
                    if st.button("✅ Approve", key=f"approve_{aid}", type="primary"):
                        with get_db() as db:
                            # Apply edits before approving
                            ag = db.get(Agent, aid)
                            if ag:
                                ag.name = edited_name
                                ag.agency = edited_agency or None
                                ag.email = edited_email or None
                                ag.genres = edited_genres + custom_genres
                                ag.audience = edited_audience
                                ag.keywords = [k.strip() for k in edited_keywords.split("\n") if k.strip()]
                                ag.hard_nos_keywords = [k.strip() for k in edited_hard_nos.split("\n") if k.strip()]
                                ag.is_open = edited_is_open
                                db.commit()
                            approve_agent(db, aid)
                        st.success(f"Approved: {agent['name']}")
                        st.rerun()

                with btn_col2:
                    reject_reason = st.text_input(
                        "Rejection reason",
                        key=f"reject_reason_{aid}",
                        placeholder="Required for rejection",
                    )
                    if st.button("❌ Reject", key=f"reject_{aid}"):
                        if not reject_reason.strip():
                            st.error("Please provide a rejection reason.")
                        else:
                            with get_db() as db:
                                reject_agent(db, aid, reason=reject_reason)
                            st.warning(f"Rejected: {agent['name']}")
                            st.rerun()

                with btn_col3:
                    if st.button("⏭️ Skip", key=f"skip_{aid}"):
                        st.info("Skipped")


# ---------------------------------------------------------------------------
# Page 2: Domain Management
# ---------------------------------------------------------------------------
elif page == "Domain Management":
    st.header("Domain Management")

    # Single domain entry
    st.subheader("Add Single Domain")
    with st.form("add_domain_form"):
        domain = st.text_input("Domain (e.g. example-agency.com)")
        agency_name = st.text_input("Agency Name")
        country = st.text_input("Country (e.g. US, UK)")
        submitted = st.form_submit_button("Add Domain")

        if submitted and domain:
            error = validate_domain(domain.strip().lower())
            if error:
                st.error(error)
            else:
                added = add_domains_to_seed_list([{
                    "domain": domain.strip().lower(),
                    "agency_name": agency_name.strip(),
                    "country": country.strip(),
                }])
                if added > 0:
                    st.success(f"Added {domain} to seed list.")
                else:
                    st.info(f"{domain} already in seed list.")

    # CSV upload
    st.subheader("CSV Upload")
    st.caption("CSV format: `domain,agency_name,country`")
    uploaded_file = st.file_uploader("Upload CSV", type=["csv"])

    if uploaded_file is not None:
        csv_content = uploaded_file.getvalue().decode("utf-8")
        results = parse_csv_domains(csv_content)

        valid = [r for r in results if "error" not in r]
        invalid = [r for r in results if "error" in r]

        st.markdown(f"**{len(valid)}** valid, **{len(invalid)}** invalid rows")

        if invalid:
            st.warning("Invalid rows:")
            for r in invalid:
                st.text(f"  {r['domain']}: {r['error']}")

        if valid:
            st.subheader("Preview")
            st.dataframe(pd.DataFrame(valid), use_container_width=True, hide_index=True)

            if st.button("Import Valid Domains", type="primary"):
                added = add_domains_to_seed_list(valid)
                st.success(f"Imported {added} new domains to seed list.")

    # Browser Agent
    st.markdown("---")
    st.subheader("Browser Agent")
    st.caption("Run the Browser Agent to discover agent profile URLs on agency websites.")

    ba_col1, ba_col2 = st.columns(2)
    with ba_col1:
        ba_domain = st.text_input(
            "Domain to discover",
            placeholder="e.g. janklow.com",
            key="ba_domain",
        )
        if st.button("Run Browser Agent", key="run_ba_single", type="primary"):
            if ba_domain.strip():
                with st.spinner(f"Running Browser Agent on {ba_domain.strip()}..."):
                    from autoquery.crawler.batch_pipeline import run_browser_agent_for_domain
                    result = asyncio.run(run_browser_agent_for_domain(ba_domain.strip()))
                    if result.status == "success":
                        st.success(
                            f"Found {len(result.profile_urls)} profile URLs "
                            f"in {result.steps_taken} steps."
                        )
                        for url in result.profile_urls:
                            st.text(f"  {url}")
                    else:
                        st.warning(f"Status: {result.status} ({result.steps_taken} steps)")
                        if result.error:
                            st.error(result.error)
            else:
                st.error("Please enter a domain.")

    with ba_col2:
        if st.button("Run on All Seed List Domains", key="run_ba_all"):
            with st.spinner("Running Browser Agent on all seed list domains..."):
                from autoquery.crawler.batch_pipeline import run_batch_pipeline
                result = asyncio.run(run_batch_pipeline(discover_only=True))
                st.success(
                    f"Done: {result['discovery_success']} success, "
                    f"{result['discovery_manual_review']} need manual review, "
                    f"{result['discovery_error']} errors. "
                    f"Total profile URLs: {result['total_profile_urls']}"
                )


# ---------------------------------------------------------------------------
# Page 3: Statistics
# ---------------------------------------------------------------------------
elif page == "Statistics":
    st.header("Statistics")

    with get_db() as db:
        # Status counts
        status_counts = dict(
            db.query(Agent.review_status, func.count(Agent.id))
            .group_by(Agent.review_status)
            .all()
        )

        total = sum(status_counts.values())
        pending = status_counts.get(REVIEW_STATUS_PENDING, 0)
        approved = status_counts.get(REVIEW_STATUS_APPROVED, 0)
        rejected = status_counts.get(REVIEW_STATUS_REJECTED, 0)
        failed = status_counts.get(REVIEW_STATUS_EXTRACTION_FAILED, 0)

        # Top rejection reasons
        rejection_reasons = (
            db.query(Agent.rejection_reason, func.count(Agent.id))
            .filter(Agent.review_status == REVIEW_STATUS_REJECTED)
            .filter(Agent.rejection_reason.isnot(None))
            .group_by(Agent.rejection_reason)
            .order_by(func.count(Agent.id).desc())
            .limit(10)
            .all()
        )

    # Metric cards
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Pending", pending)
    col2.metric("Approved", approved)
    col3.metric("Rejected", rejected)
    col4.metric("Extraction Failed", failed)

    # Progress bar
    if total > 0:
        st.subheader("Review Progress")
        progress = approved / total
        st.progress(progress, text=f"{approved}/{total} approved ({progress:.0%})")
    else:
        st.info("No agent profiles yet.")

    # Top rejection reasons
    if rejection_reasons:
        st.subheader("Top Rejection Reasons")
        reason_df = pd.DataFrame(rejection_reasons, columns=["Reason", "Count"])
        st.dataframe(reason_df, use_container_width=True, hide_index=True)
