"""
AutoQuery Review UI — Streamlit app for reviewing extracted agent profiles,
managing domains, and viewing crawl statistics.
"""
import asyncio
from contextlib import contextmanager
from datetime import datetime, timezone

import pandas as pd
import streamlit as st
from sqlalchemy import func, desc

from autoquery.database.db import SessionLocal
from autoquery.database.models import (
    Agent,
    Agency,
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
    normalize_domain,
    validate_domain,
    parse_csv_domains,
    add_domains_to_seed_list,
)

st.set_page_config(page_title="AutoQuery Review", layout="wide")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
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


def _fmt_ts(dt):
    """Format a datetime for display. Returns relative + absolute."""
    if dt is None:
        return "—"
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    delta = now - dt
    secs = int(delta.total_seconds())
    if secs < 60:
        rel = "just now"
    elif secs < 3600:
        rel = f"{secs // 60}m ago"
    elif secs < 86400:
        rel = f"{secs // 3600}h ago"
    else:
        rel = f"{secs // 86400}d ago"
    absolute = dt.strftime("%Y-%m-%d %H:%M UTC")
    return f"{rel}  ({absolute})"


def _quality_dot(score):
    """Return a colored circle for quality score."""
    if score is None:
        return "⚪"
    if score >= 0.65:
        return "🟢"
    if score >= 0.40:
        return "🟡"
    return "🔴"


# ---------------------------------------------------------------------------
# Sidebar Navigation
# ---------------------------------------------------------------------------
page = st.sidebar.radio(
    "Navigation",
    ["Dashboard", "Review Queue", "Crawl Runs", "Domain Management"],
    index=0,
)

# ---------------------------------------------------------------------------
# Page: Dashboard
# ---------------------------------------------------------------------------
if page == "Dashboard":
    st.title("AutoQuery Dashboard")

    with get_db() as db:
        # Agent status counts
        status_counts = dict(
            db.query(Agent.review_status, func.count(Agent.id))
            .group_by(Agent.review_status)
            .all()
        )
        total_agents = sum(status_counts.values())
        pending = status_counts.get(REVIEW_STATUS_PENDING, 0)
        approved = status_counts.get(REVIEW_STATUS_APPROVED, 0)
        rejected = status_counts.get(REVIEW_STATUS_REJECTED, 0)
        failed = status_counts.get(REVIEW_STATUS_EXTRACTION_FAILED, 0)

        # Recent crawl runs
        recent_runs = (
            db.query(CrawlRun)
            .order_by(desc(CrawlRun.id))
            .limit(5)
            .all()
        )
        runs_data = []
        for r in recent_runs:
            runs_data.append({
                "id": r.id,
                "domain": r.domain or "—",
                "type": r.run_type or "—",
                "started": r.started_at,
                "finished": r.finished_at,
                "status": r.status or "—",
                "pages": r.pages_fetched or 0,
                "content": r.pages_content or 0,
                "profiles_new": r.profiles_new or 0,
                "profiles_updated": r.profiles_updated or 0,
                "errors": r.pages_error or 0,
            })

        # Recently extracted agents
        recent_agents = (
            db.query(Agent)
            .order_by(desc(Agent.updated_at))
            .limit(10)
            .all()
        )
        agents_data = []
        for a in recent_agents:
            agents_data.append({
                "name": a.name,
                "agency": a.agency or "—",
                "status": a.review_status,
                "quality": a.quality_score,
                "genres": a.genres or [],
                "url": a.profile_url,
                "crawled": a.last_crawled_at,
                "updated": a.updated_at,
            })

        # Top rejection reasons
        rejection_reasons = (
            db.query(Agent.rejection_reason, func.count(Agent.id))
            .filter(Agent.review_status == REVIEW_STATUS_REJECTED)
            .filter(Agent.rejection_reason.isnot(None))
            .group_by(Agent.rejection_reason)
            .order_by(func.count(Agent.id).desc())
            .limit(5)
            .all()
        )

    # --- Metric cards ---
    st.markdown("### Agent Profiles")
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total", total_agents)
    c2.metric("Pending", pending)
    c3.metric("Approved", approved)
    c4.metric("Rejected", rejected)
    c5.metric("Failed", failed)

    if total_agents > 0:
        reviewed = approved + rejected
        st.progress(
            reviewed / total_agents,
            text=f"{reviewed}/{total_agents} reviewed ({reviewed / total_agents:.0%})",
        )

    # --- Recent crawl runs ---
    st.markdown("### Recent Crawl Runs")
    if runs_data:
        for run in runs_data:
            with st.container(border=True):
                rc1, rc2, rc3, rc4 = st.columns([2, 2, 3, 3])
                with rc1:
                    st.markdown(f"**Run #{run['id']}** — `{run['domain']}`")
                    st.caption(f"Type: {run['type']}  |  Status: {run['status']}")
                with rc2:
                    st.caption(f"Pages: {run['pages']}  |  Content: {run['content']}")
                    st.caption(f"New profiles: {run['profiles_new']}  |  Updated: {run['profiles_updated']}  |  Errors: {run['errors']}")
                with rc3:
                    st.caption(f"Started: {_fmt_ts(run['started'])}")
                with rc4:
                    st.caption(f"Finished: {_fmt_ts(run['finished'])}")
    else:
        st.info("No crawl runs yet.")

    # --- Recent agents ---
    st.markdown("### Recently Updated Agents")
    if agents_data:
        for a in agents_data:
            status_icon = {
                "pending": "🔵", "approved": "✅",
                "rejected": "❌", "extraction_failed": "⚠️",
            }.get(a["status"], "❓")
            genres_str = ", ".join(a["genres"][:4])
            if len(a["genres"]) > 4:
                genres_str += f" +{len(a['genres']) - 4}"
            st.markdown(
                f"{status_icon} {_quality_dot(a['quality'])} "
                f"**{a['name']}** — {a['agency']}  "
                f"| {genres_str}  "
                f"| Updated: {_fmt_ts(a['updated'])}  "
                f"| Crawled: {_fmt_ts(a['crawled'])}"
            )
    else:
        st.info("No agents yet.")

    # --- Top rejection reasons ---
    if rejection_reasons:
        st.markdown("### Top Rejection Reasons")
        for reason, count in rejection_reasons:
            st.text(f"  {count}x  {reason}")


# ---------------------------------------------------------------------------
# Page: Review Queue
# ---------------------------------------------------------------------------
elif page == "Review Queue":
    st.title("Review Queue")

    with get_db() as db:
        # Filters
        fc1, fc2, fc3 = st.columns(3)
        with fc1:
            status_filter = st.selectbox(
                "Status",
                ["pending", "extraction_failed", "approved", "rejected", "all"],
                index=0,
            )
        with fc2:
            sort_by = st.selectbox(
                "Sort by",
                ["Last crawled (newest)", "Last crawled (oldest)", "Quality (high)", "Quality (low)", "Name"],
                index=0,
            )
        with fc3:
            domain_filter = st.text_input("Filter by domain", placeholder="e.g. ldlainc")

        # Build query
        q = db.query(Agent)
        if status_filter != "all":
            q = q.filter(Agent.review_status == status_filter)
        if domain_filter.strip():
            q = q.filter(Agent.profile_url.ilike(f"%{domain_filter.strip()}%"))

        if sort_by == "Last crawled (newest)":
            q = q.order_by(desc(Agent.last_crawled_at))
        elif sort_by == "Last crawled (oldest)":
            q = q.order_by(Agent.last_crawled_at)
        elif sort_by == "Quality (high)":
            q = q.order_by(desc(Agent.quality_score))
        elif sort_by == "Quality (low)":
            q = q.order_by(Agent.quality_score)
        else:
            q = q.order_by(Agent.name)

        agents = q.limit(50).all()

        agent_data = []
        for a in agents:
            agent_data.append({
                "id": a.id,
                "name": a.name,
                "agency": a.agency,
                "profile_url": a.profile_url,
                "genres": list(a.genres or []),
                "genres_raw": list(a.genres_raw or []),
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
                "review_status": a.review_status,
                "email": a.email,
                "closed_to": list(a.closed_to or []),
                "closed_to_raw": a.closed_to_raw,
                "response_time": a.response_time,
                "last_crawled_at": a.last_crawled_at,
                "created_at": a.created_at,
                "updated_at": a.updated_at,
            })

    if not agent_data:
        st.info("No profiles match the current filter.")
    else:
        st.caption(f"Showing {len(agent_data)} profiles")

        # Summary table
        summary_rows = []
        for a in agent_data:
            status_icon = {
                "pending": "🔵", "approved": "✅",
                "rejected": "❌", "extraction_failed": "⚠️",
            }.get(a["review_status"], "❓")
            wl_words = len((a["wishlist_raw"] or "").split()) if a["wishlist_raw"] else 0
            summary_rows.append({
                "": status_icon,
                "Q": _quality_dot(a["quality_score"]),
                "Name": a["name"],
                "Agency": a["agency"] or "—",
                "Genres": len(a["genres"]),
                "Keywords": len(a["keywords"]),
                "Wishlist": f"{wl_words}w" if wl_words else "—",
                "Crawled": _fmt_ts(a["last_crawled_at"]),
            })
        st.dataframe(
            pd.DataFrame(summary_rows),
            use_container_width=True,
            hide_index=True,
            height=min(len(summary_rows) * 38 + 40, 400),
        )

        st.markdown("---")

        # Detail cards
        for agent in agent_data:
            aid = agent["id"]
            status = agent["review_status"]
            status_icon = {
                "pending": "🔵", "approved": "✅",
                "rejected": "❌", "extraction_failed": "⚠️",
            }.get(status, "❓")

            with st.container(border=True):
                # --- Header ---
                h1, h2 = st.columns([4, 2])
                with h1:
                    st.markdown(
                        f"### {status_icon} {agent['name']}  "
                        f"<small style='color:#888'>({status})</small>",
                        unsafe_allow_html=True,
                    )
                    if agent["agency"]:
                        st.caption(f"Agency: {agent['agency']}")
                    st.markdown(f"[{agent['profile_url']}]({agent['profile_url']})")
                with h2:
                    score = agent["quality_score"]
                    score_str = f"{score:.2f}" if score is not None else "—"
                    st.markdown(
                        f"**Quality:** {_quality_dot(score)} {score_str}  \n"
                        f"**Action:** {agent['quality_action'] or '—'}  \n"
                        f"**Open:** {'Yes' if agent['is_open'] is True else 'No' if agent['is_open'] is False else 'Unknown'}"
                    )

                # --- Timestamps ---
                ts1, ts2, ts3 = st.columns(3)
                with ts1:
                    st.caption(f"Crawled: {_fmt_ts(agent['last_crawled_at'])}")
                with ts2:
                    st.caption(f"Created: {_fmt_ts(agent['created_at'])}")
                with ts3:
                    st.caption(f"Updated: {_fmt_ts(agent['updated_at'])}")

                # --- Quick overview ---
                ov1, ov2, ov3 = st.columns(3)
                with ov1:
                    st.markdown(f"**Genres ({len(agent['genres'])}):** {', '.join(agent['genres'][:6])}")
                with ov2:
                    st.markdown(f"**Keywords ({len(agent['keywords'])}):** {', '.join(agent['keywords'][:5])}")
                with ov3:
                    wl = agent["wishlist_raw"] or ""
                    wl_words = len(wl.split()) if wl else 0
                    bio = agent["bio_raw"] or ""
                    bio_words = len(bio.split()) if bio else 0
                    st.markdown(f"**Wishlist:** {wl_words} words  |  **Bio:** {bio_words} words")

                # --- Expandable detail section ---
                with st.expander("Full details & edit"):
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
                        custom_genres = [g for g in agent["genres"] if g not in GENRE_OPTIONS]
                        if custom_genres:
                            st.caption(f"Custom genres: {', '.join(custom_genres)}")

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

                    # Raw text
                    rt1, rt2, rt3 = st.columns(3)
                    with rt1:
                        st.text_area(
                            f"Wishlist ({wl_words} words)",
                            value=wl or "(none)",
                            height=200,
                            key=f"wishlist_{aid}",
                        )
                    with rt2:
                        st.text_area(
                            f"Bio ({bio_words} words)",
                            value=bio or "(none)",
                            height=200,
                            key=f"bio_{aid}",
                        )
                    with rt3:
                        st.text_area(
                            "Hard Nos",
                            value=agent["hard_nos_raw"] or "(none)",
                            height=200,
                            key=f"hard_nos_raw_{aid}",
                        )

                # --- Action buttons (always visible) ---
                if status == "pending":
                    btn1, btn2, btn3 = st.columns([1, 2, 1])
                    with btn1:
                        if st.button("Approve", key=f"approve_{aid}", type="primary"):
                            with get_db() as db:
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
                            st.rerun()
                    with btn2:
                        reject_reason = st.text_input(
                            "Rejection reason",
                            key=f"reject_reason_{aid}",
                            placeholder="Required",
                            label_visibility="collapsed",
                        )
                        if st.button("Reject", key=f"reject_{aid}"):
                            if not reject_reason.strip():
                                st.error("Provide a reason.")
                            else:
                                with get_db() as db:
                                    reject_agent(db, aid, reason=reject_reason)
                                st.rerun()
                    with btn3:
                        if st.button("Skip", key=f"skip_{aid}"):
                            pass  # just scroll past


# ---------------------------------------------------------------------------
# Page: Crawl Runs
# ---------------------------------------------------------------------------
elif page == "Crawl Runs":
    st.title("Crawl Runs")

    with get_db() as db:
        runs = (
            db.query(CrawlRun)
            .order_by(desc(CrawlRun.id))
            .limit(20)
            .all()
        )
        runs_list = []
        for r in runs:
            runs_list.append({
                "id": r.id,
                "domain": r.domain,
                "type": r.run_type,
                "status": r.status,
                "started": r.started_at,
                "finished": r.finished_at,
                "pages_fetched": r.pages_fetched or 0,
                "pages_index": r.pages_index or 0,
                "pages_content": r.pages_content or 0,
                "pages_skipped": r.pages_skipped or 0,
                "pages_error": r.pages_error or 0,
                "quality_extracted": r.quality_extracted or 0,
                "quality_warned": r.quality_warned or 0,
                "quality_discarded": r.quality_discarded or 0,
                "profiles_new": r.profiles_new or 0,
                "profiles_updated": r.profiles_updated or 0,
            })

    if not runs_list:
        st.info("No crawl runs yet.")
    else:
        for run in runs_list:
            with st.container(border=True):
                h1, h2 = st.columns([3, 2])
                with h1:
                    st.markdown(f"### Run #{run['id']} — `{run['domain'] or 'backfill'}`")
                    st.caption(
                        f"Type: **{run['type'] or '—'}**  |  "
                        f"Status: **{run['status'] or '—'}**"
                    )
                with h2:
                    st.caption(f"Started: {_fmt_ts(run['started'])}")
                    st.caption(f"Finished: {_fmt_ts(run['finished'])}")
                    if run["started"] and run["finished"]:
                        dur = run["finished"] - run["started"]
                        st.caption(f"Duration: {dur.total_seconds():.0f}s")

                m1, m2, m3, m4, m5 = st.columns(5)
                m1.metric("Fetched", run["pages_fetched"])
                m2.metric("Index", run["pages_index"])
                m3.metric("Content", run["pages_content"])
                m4.metric("Profiles", f"{run['profiles_new']} new / {run['profiles_updated']} upd")
                m5.metric("Errors", run["pages_error"])

                with st.expander("Quality breakdown"):
                    q1, q2, q3, q4 = st.columns(4)
                    q1.metric("Extracted", run["quality_extracted"])
                    q2.metric("Warned", run["quality_warned"])
                    q3.metric("Discarded", run["quality_discarded"])
                    q4.metric("Skipped", run["pages_skipped"])


# ---------------------------------------------------------------------------
# Page: Domain Management
# ---------------------------------------------------------------------------
elif page == "Domain Management":
    st.title("Domain Management")

    # CSV upload
    st.markdown("### Import Domains from CSV")
    st.markdown(
        "Upload a CSV with columns: `domain`, `agency_name`, `country`.  \n"
        "Duplicates are skipped. Aggregator domains are blocked."
    )
    uploaded_file = st.file_uploader("Upload CSV", type=["csv"])

    if uploaded_file is not None:
        csv_content = uploaded_file.getvalue().decode("utf-8")
        results = parse_csv_domains(csv_content)
        valid = [r for r in results if "error" not in r]
        invalid = [r for r in results if "error" in r]

        st.markdown(f"**{len(valid)}** valid, **{len(invalid)}** invalid")
        if invalid:
            for r in invalid:
                st.text(f"  {r['domain']}: {r['error']}")
        if valid:
            st.dataframe(pd.DataFrame(valid), use_container_width=True, hide_index=True)
            if st.button("Import Valid Domains", type="primary"):
                added = add_domains_to_seed_list(valid)
                st.success(f"Imported {added} new domains.")

    # Single domain
    st.markdown("---")
    st.markdown("### Add Single Domain")
    with st.form("add_domain_form"):
        domain = st.text_input("Domain (e.g. example-agency.com)")
        agency_name = st.text_input("Agency Name")
        country = st.text_input("Country (e.g. US, UK)")
        submitted = st.form_submit_button("Add Domain")

        if submitted and domain:
            clean_domain = normalize_domain(domain)
            error = validate_domain(clean_domain)
            if error:
                st.error(error)
            else:
                added = add_domains_to_seed_list([{
                    "domain": clean_domain,
                    "agency_name": agency_name.strip(),
                    "country": country.strip(),
                }])
                if added > 0:
                    st.success(f"Added {domain}.")
                else:
                    st.info(f"{domain} already in seed list.")

    # Browser Agent
    st.markdown("---")
    st.markdown("### Browser Agent")
    st.caption("Discover agent profile URLs on agency websites.")

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

    # Crawl URL
    st.markdown("---")
    st.markdown("### Crawl URL")
    st.caption("Crawl individual pages or entire sites. Single-page mode bypasses the domain blacklist.")

    cu_col1, cu_col2 = st.columns(2)

    with cu_col1:
        st.markdown("**Single Page**")
        cu_single_url = st.text_input(
            "URL to crawl",
            placeholder="e.g. https://manuscriptwishlist.com/mswl-post/moe-ferrara/",
            key="cu_single_url",
        )
        st.caption("Blacklist is bypassed — any URL can be fetched.")
        if st.button("Crawl", key="cu_single_btn", type="primary"):
            if cu_single_url.strip():
                with st.spinner(f"Crawling {cu_single_url.strip()}..."):
                    from autoquery.crawler.orchestrator import crawl_single_url
                    result = asyncio.run(crawl_single_url(cu_single_url.strip()))
                    if result["pages_error"] == 0:
                        st.success(
                            f"Page type: {result['page_type'] or 'N/A'} — "
                            f"New: {result['profiles_new']}, Updated: {result['profiles_updated']}"
                        )
                    else:
                        st.error("Fetch failed. Check logs for details.")
            else:
                st.error("Please enter a URL.")

    with cu_col2:
        st.markdown("**Site Crawl**")
        cu_site_url = st.text_input(
            "Start URL",
            placeholder="e.g. https://some-agency.com/about",
            key="cu_site_url",
        )
        cu_max_pages = st.number_input(
            "Max pages", min_value=1, max_value=1000, value=200, key="cu_max_pages"
        )
        st.caption("Blacklist is enforced — aggregator sites will be blocked.")
        if st.button("Start", key="cu_site_btn"):
            if cu_site_url.strip():
                with st.spinner(f"Site crawl from {cu_site_url.strip()}..."):
                    from autoquery.crawler.orchestrator import crawl_site
                    result = asyncio.run(crawl_site(cu_site_url.strip(), max_pages=cu_max_pages))
                    st.success(
                        f"Fetched {result['pages_fetched']} pages — "
                        f"Index: {result['pages_index']}, Content: {result['pages_content']}, "
                        f"New profiles: {result['profiles_new']}, Updated: {result['profiles_updated']}"
                    )
            else:
                st.error("Please enter a URL.")
