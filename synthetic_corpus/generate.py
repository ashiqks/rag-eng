"""
Synthetic GAP Test & Learn COE Confluence corpus generator.

Produces N HTML files mirroring the Confluence template structure
described in Meeting 2 (§10) and Meeting 3, with per-field <meta> tags
plus an embedded JSON-LD block for metadata-driven retrieval testing.

HTML is the canonical format because Vertex AI Search's unstructured
data store supports HTML / PDF / TXT / DOCX / PPTX / XLSX but not .md.

Usage:
    python generate.py --count 500 --out pages
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import random
import textwrap
from dataclasses import dataclass, asdict
from pathlib import Path

# ---------------------------------------------------------------------------
# Domain dictionaries (sourced from Meeting 1/2/3 transcripts + reference docs)
# ---------------------------------------------------------------------------

BRANDS = [
    ("Athleta", "ATH", "premium"),
    ("Banana Republic", "BR", "premium"),
    ("Banana Republic Factory", "BRF", "discount"),
    ("Old Navy", "ON", "discount"),
    ("Gap", "GAP", "mid"),
    ("Gap Factory", "GAPF", "discount"),
]

MARKETS = ["US", "CA", "MX", "Global"]

VALUE_STREAMS = ["PLP", "PDP", "Shopping Bag", "Checkout", "Homepage", "Account", "Search"]

CHANNELS = ["Web", "iOS App", "Android App", "Email", "SMS", "Push"]

CHANNEL_SECTIONS = {
    "Web": ["Desktop", "Mobile Web", "Tablet Web"],
    "iOS App": ["iOS Native"],
    "Android App": ["Android Native"],
    "Email": ["Promo Email", "Triggered Email", "Loyalty Email"],
    "SMS": ["Promo SMS", "Triggered SMS"],
    "Push": ["iOS Push", "Android Push"],
}

DEVICES = ["Desktop", "Mobile", "Tablet", "All Devices"]

AUDIENCES = [
    "All Customers",
    "New Visitors",
    "Returning Visitors",
    "Loyalty Members",
    "Non-Loyalty",
    "First-time Buyers",
    "High-AOV Customers",
    "Cart Abandoners",
]

TACTICS = ["Quality", "Time Savings", "Urgency", "Value"]

PRIMARY_KPIS = [
    "OPV Conversion Rate",
    "Net RPV",
    "Add-to-Bag Rate",
    "Email Capture Rate",
    "PDP -> Shopping Bag Conversion",
    "Checkout Start Rate",
    "Checkout Completion Rate",
    "AOS (Average Order Size)",
    "UPT (Units Per Transaction)",
    "AUR (Average Unit Retail)",
]

SECONDARY_KPIS = [
    "Total Visits",
    "Visits Split (Visit/Visitor)",
    "Variation Overlap",
    "PDP Views Per Visit",
    "PDP Exit Rate",
    "PDP Certona Engagement Rate",
    "Search Engagement Rate",
    "Bag Edit Rate",
    "Promo Code Application Rate",
    "Free Shipping Threshold Crossings",
    "Loyalty Sign-up Rate",
    "Return Rate",
]

VENDORS = ["Optimizely (Client-Side)", "Optimizely (Server-Side)", "In-house", "Rokt", "Certona"]

OUTCOMES = ["Win", "Loss", "Flat"]
OUTCOME_WEIGHTS = [0.22, 0.10, 0.68]   # Meeting 1 §2.2: most tests are flat

RECOMMENDATIONS_BY_OUTCOME = {
    "Win": [
        "Roll out the challenger to 100% of traffic.",
        "Roll out to all brands in the discount tier and re-test on premium.",
        "Roll out to mobile first; monitor desktop in parallel.",
        "Roll out to US; revisit CA/MX after localisation review.",
    ],
    "Loss": [
        "Do NOT roll out. Counted as averted revenue loss.",
        "Do NOT roll out. Investigate whether copy variant caused friction.",
        "Do NOT roll out. Consider an alternative variation in the next cycle.",
        "Do NOT roll out. Re-test only after redesign of the failing module.",
    ],
    "Flat": [
        "No change. Monitor for sub-segment lifts before deciding on rollout.",
        "No change. Consider re-testing during a higher-traffic window (Holiday).",
        "No change. The effect, if any, is below MDE.",
        "No change. Keep the control as the production experience.",
    ],
}

# ---------------------------------------------------------------------------
# Test idea library — realistic A/B test concepts seen in GAP transcripts +
# generic e-commerce A/B testing literature. ~80 templates that mix-and-match.
# ---------------------------------------------------------------------------

TEST_IDEAS = [
    # PLP
    ("PLP", "Quality",      "4-up vs 3-up product grid",                   "Increasing product density on PLP improves visibility of more SKUs and lifts add-to-bag.", "PLP grid density"),
    ("PLP", "Time Savings", "Sticky filter rail on PLP",                   "A persistent filter rail removes the need to scroll back to the top, accelerating refinement and conversion.", "Sticky PLP filters"),
    ("PLP", "Value",        "Show 'X left in stock' badge on PLP tiles",    "Surfacing low-inventory signals on PLP triggers loss-aversion and lifts CTR to PDP.", "PLP scarcity badge"),
    ("PLP", "Urgency",      "Countdown timer on promo PLP banner",         "A visible countdown on promo PLPs increases urgency and drives session-level conversion.", "PLP promo countdown"),
    ("PLP", "Quality",      "Larger hero image at top of PLP",              "A larger above-the-fold hero on PLP improves brand cohesion and lifts engagement.", "PLP hero size"),
    ("PLP", "Time Savings", "Infinite scroll vs paginated PLP",             "Infinite scroll reduces friction in browsing and lifts products viewed per visit.", "PLP infinite scroll"),
    ("PLP", "Value",        "Per-tile colour swatches",                     "Showing colour swatches on the PLP tile lets shoppers find their preferred colour without entering PDP.", "PLP swatches"),
    ("PLP", "Quality",      "Dynamic sort by personal affinity",            "ML-ranked sort using prior browsing affinity should outperform default 'Featured' sort.", "PLP affinity sort"),

    # PDP
    ("PDP", "Quality",      "PDP recommendation module reorder",            "Moving 'You May Also Like' above 'Recently Viewed' on PDP exposes more new products and lifts cross-sell.", "PDP module reorder"),
    ("PDP", "Time Savings", "Sticky add-to-bag button on PDP scroll",       "A sticky ATB on mobile PDP keeps the primary CTA visible during long scrolls.", "Sticky PDP ATB"),
    ("PDP", "Value",        "Show 'free shipping over $X' on PDP",          "Reminding the shopper of the free-ship threshold on the PDP raises AOS and conversion.", "PDP free-ship reminder"),
    ("PDP", "Urgency",      "'Selling fast' label on PDP",                  "A scarcity label on PDP triggers urgency and lifts ATB rate.", "PDP scarcity label"),
    ("PDP", "Quality",      "Video-as-hero on PDP",                         "Replacing the static PDP hero with a 6-second product video improves engagement and ATB.", "PDP video hero"),
    ("PDP", "Time Savings", "Single-page PDP for size + colour",            "Merging size and colour selection into a single visible block reduces decision time.", "PDP single-step selection"),
    ("PDP", "Value",        "Loyalty point earn estimator on PDP",          "Showing 'You'll earn X points' on PDP reinforces loyalty value and lifts conversion among members.", "PDP points estimator"),
    ("PDP", "Quality",      "AI fitting room widget",                       "An AI-driven fit recommender (à la Zara) reduces size returns and lifts ATB.", "PDP AI fit"),
    ("PDP", "Quality",      "User-generated photos in PDP gallery",         "Adding UGC photos to the PDP gallery improves perceived authenticity and ATB.", "PDP UGC"),
    ("PDP", "Time Savings", "Pre-selected default size",                    "Defaulting to the most-purchased size for the current SKU saves a tap.", "PDP default size"),

    # Shopping Bag
    ("Shopping Bag", "Quality",      "Shopping Bag Payment Buttons Collapse",        "Collapsing the alternative payment options on iOS bag reduces visual clutter and lifts checkout-start.", "Bag payment collapse"),
    ("Shopping Bag", "Time Savings", "One-line shipping address summary",            "Summarising the saved address in one line on the bag page reduces friction.", "Bag address summary"),
    ("Shopping Bag", "Urgency",      "Free-shipping thermometer in bag",             "Showing a 'add $X for free shipping' progress bar lifts AOS.", "Bag free-ship thermometer"),
    ("Shopping Bag", "Value",        "Show vs. hide free-shipping thermometer",      "A persistent thermometer educates the shopper on the free-ship benefit and raises AOS.", "Bag thermometer visibility"),
    ("Shopping Bag", "Quality",      "Inline gift-card application",                 "Allowing gift-card entry inline in the bag (vs. checkout) reduces drop-off.", "Bag inline gift card"),
    ("Shopping Bag", "Time Savings", "Auto-apply best promo code",                   "Automatically applying the best eligible promo code lifts conversion in the bag step.", "Bag auto promo"),

    # Checkout
    ("Checkout", "Quality",      "Checkout Button Position (sticky bottom)",     "A sticky bottom CTA on mobile checkout reduces drop-off at the payment step.", "Sticky checkout CTA"),
    ("Checkout", "Time Savings", "Guest checkout default",                       "Defaulting to guest checkout (with optional signup at the end) lifts checkout completion.", "Guest checkout default"),
    ("Checkout", "Quality",      "Single-page vs accordion checkout",            "A single-page checkout reduces perceived steps and lifts completion rate.", "Single-page checkout"),
    ("Checkout", "Value",        "Show estimated delivery date at checkout",      "Surfacing the EDD at checkout reduces last-minute drop-off.", "Checkout EDD"),
    ("Checkout", "Urgency",      "Order-by-noon countdown for next-day delivery", "A countdown to the next-day delivery cutoff drives urgency at checkout.", "Checkout NDD countdown"),
    ("Checkout", "Time Savings", "Apple Pay / Google Pay above billing form",     "Promoting wallet pay above the billing form shortens checkout for mobile users.", "Wallet pay promotion"),
    ("Checkout", "Quality",      "Inline form validation",                       "Validating fields on blur (vs on submit) reduces error-bounce.", "Checkout inline validation"),

    # Homepage
    ("Homepage", "Value",        "Bubble vs. Pop-up for email acquisition",      "A bubble email capture is less intrusive than a pop-up and improves long-term sentiment without sacrificing capture rate.", "Email bubble vs pop-up"),
    ("Homepage", "Quality",      "Hero carousel vs single hero image",           "A single curated hero outperforms a 4-slide carousel on click-through to PDP.", "Hero single vs carousel"),
    ("Homepage", "Time Savings", "Personalised category rail on homepage",       "An ML-ranked category rail tailored to the visitor's prior browsing improves CTR to PLP.", "Personalised rail"),
    ("Homepage", "Urgency",      "Limited-time banner on homepage",              "A 24-hour banner promo lifts traffic to PLP during sale events.", "Homepage limited-time banner"),

    # Account
    ("Account",  "Value",        "Loyalty progress widget on account page",      "A progress widget toward the next loyalty tier raises return-visit rate among members.", "Loyalty progress widget"),
    ("Account",  "Time Savings", "Saved address auto-population",                "Auto-populating the most-used saved address speeds up checkout starts.", "Auto address"),

    # Search
    ("Search",   "Quality",      "Search autosuggest with imagery",              "Adding product thumbnails to autosuggest improves CTR to PDP from search.", "Search autosuggest images"),
    ("Search",   "Time Savings", "Recent searches as quick chips",               "Recent search chips on the search overlay reduce typing.", "Search recent chips"),
]

# Promo flavors for the "same-test-different-window" duplicates from Meeting 2 §13
PROMO_VARIANTS = [
    "50% off site-wide",
    "60% off site-wide",
    "70% off site-wide",
    "80% off site-wide",
    "BOGO 50%",
    "Free shipping on $25+",
    "Free shipping on $50+",
    "Stack: 30% + extra 10%",
]

# ---------------------------------------------------------------------------

@dataclass
class TestRecord:
    test_id: str
    confluence_page_id: str
    title: str
    brand: str
    brand_code: str
    market: str
    value_stream: str
    channel: str
    channel_section: str
    device: str
    audience: str
    tactic: str
    primary_kpi: str
    secondary_kpis: list
    vendor: str
    test_type: str               # "Client-Side" | "Server-Side"
    start_date: str
    end_date: str
    duration_days: int
    sample_size_per_arm: int
    mde_pct: float
    confidence_pct: int
    power_pct: int
    exposure_pct: int
    split: str
    outcome: str
    primary_kpi_delta_pct: float
    net_rpv_delta_pct: float
    aos_delta_pct: float
    visits_total: int
    incremental_revenue_usd: int
    averted_loss_usd: int
    recommendation_text: str
    recommendation_adopted: str
    learning_snippet: str
    related_test_ids: list
    hypothesis: str
    problem_statement: str
    short_label: str
    confluence_url: str
    sha256_source: str

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _short_id(seed: str) -> str:
    return hashlib.sha1(seed.encode("utf-8")).hexdigest()[:10]

def _rand_date_range(rng: random.Random) -> tuple[dt.date, dt.date, int]:
    # Most tests fall in last 2 years (Meeting 1 §2.4: ~700 in 2-yr window),
    # tail back to 2017 (Meeting 2 §11).
    weights_year = [
        (2017, 0.02), (2018, 0.03), (2019, 0.04), (2020, 0.05),
        (2021, 0.06), (2022, 0.08), (2023, 0.10),
        (2024, 0.18), (2025, 0.22), (2026, 0.22),
    ]
    years, w = zip(*weights_year)
    year = rng.choices(years, weights=w, k=1)[0]
    month = rng.randint(1, 12)
    day = rng.randint(1, 28)
    start = dt.date(year, month, day)
    duration = rng.choices(
        [14, 21, 28, 42, 60, 90, 120, 150, 180],   # 2 wks .. 6 mo, mostly 3-4 mo
        weights=[5, 8, 10, 14, 18, 20, 12, 8, 5],
        k=1,
    )[0]
    end = start + dt.timedelta(days=duration)
    if end > dt.date(2026, 5, 13):
        end = dt.date(2026, 5, 13)
    return start, end, (end - start).days

def _outcome_metrics(rng: random.Random, outcome: str) -> tuple[float, float, float, int, int]:
    """Return (primary_delta_pct, net_rpv_delta_pct, aos_delta_pct, incremental_$, averted_$)."""
    if outcome == "Win":
        primary = round(rng.uniform(0.4, 6.5), 2)
        rpv = round(primary * rng.uniform(0.5, 1.4), 2)
        aos = round(rng.uniform(-0.5, 2.5), 2)
        incremental = int(rng.uniform(120_000, 4_500_000))
        averted = 0
    elif outcome == "Loss":
        primary = -round(rng.uniform(0.4, 4.5), 2)
        rpv = round(primary * rng.uniform(0.5, 1.3), 2)
        aos = round(rng.uniform(-2.5, 0.5), 2)
        incremental = 0
        averted = int(rng.uniform(80_000, 3_000_000))
    else:  # Flat
        primary = round(rng.uniform(-0.3, 0.3), 2)
        rpv = round(rng.uniform(-0.3, 0.3), 2)
        aos = round(rng.uniform(-0.3, 0.3), 2)
        incremental = 0
        averted = 0
    return primary, rpv, aos, incremental, averted

def _build_record(rng: random.Random, idx: int, related: list[str]) -> TestRecord:
    value_stream, tactic, idea_title, hypothesis_seed, short_label = rng.choice(TEST_IDEAS)

    # Promo-driven tests follow the duplicate pattern from Meeting 2 §13
    is_promo = "promo" in idea_title.lower() or value_stream == "Homepage" and rng.random() < 0.3
    if is_promo and rng.random() < 0.5:
        promo = rng.choice(PROMO_VARIANTS)
        idea_title = f"{idea_title} ({promo})"
        hypothesis_seed = f"Testing {promo} as part of {hypothesis_seed.lower()}"

    brand_name, brand_code, brand_tier = rng.choice(BRANDS)
    market = rng.choices(MARKETS, weights=[0.78, 0.10, 0.06, 0.06], k=1)[0]
    channel = rng.choices(CHANNELS, weights=[0.55, 0.18, 0.13, 0.07, 0.04, 0.03], k=1)[0]
    channel_section = rng.choice(CHANNEL_SECTIONS[channel])
    device = (
        "Desktop" if channel == "Web" and channel_section == "Desktop"
        else "Mobile" if channel == "Web" and channel_section == "Mobile Web"
        else "Tablet" if channel_section == "Tablet Web"
        else "Mobile" if "App" in channel
        else "All Devices"
    )

    audience = rng.choice(AUDIENCES)
    primary_kpi = rng.choice(PRIMARY_KPIS)
    secondary = rng.sample(SECONDARY_KPIS, k=rng.randint(3, 6))
    vendor = rng.choice(VENDORS)
    test_type = "Server-Side" if "Server-Side" in vendor else "Client-Side"

    start, end, duration = _rand_date_range(rng)

    sample = rng.choice([1_200_000, 2_400_000, 3_600_000, 5_000_000, 7_200_000, 10_000_000, 15_000_000])
    mde = round(rng.uniform(0.20, 1.50), 2)
    confidence = rng.choice([80, 85, 90, 95])
    power = 80
    exposure = rng.choice([100, 50, 20, 10])
    split = rng.choice(["50/50", "33/33/33", "25/25/25/25", "90/10 (holdback)"])

    outcome = rng.choices(OUTCOMES, weights=OUTCOME_WEIGHTS, k=1)[0]
    primary_delta, rpv_delta, aos_delta, incremental, averted = _outcome_metrics(rng, outcome)
    visits_total = sample * (1 if "/" not in split else split.count("/") + 1)

    recommendation = rng.choice(RECOMMENDATIONS_BY_OUTCOME[outcome])
    adopted = (
        "Yes" if outcome == "Win" and rng.random() < 0.85
        else "No (averted loss)" if outcome == "Loss"
        else "N/A" if outcome == "Flat"
        else "Pending"
    )

    title = f"[{brand_code} {channel.upper()}] {idea_title} - {start.strftime('%b %Y')}"
    page_id = f"TLCOE-{2010_000 + idx}"
    test_id = f"T-{brand_code}-{idx:05d}"
    confluence_url = f"https://gap.atlassian.net/wiki/spaces/TLCOE/pages/{page_id}"
    short_label = short_label

    problem_statement = (
        f"On {brand_name} {value_stream}, the current control experience does not "
        f"sufficiently support {primary_kpi.split(' (')[0].lower()} for the {audience.lower()} segment. "
        f"Based on prior {tactic.lower()}-tactic learnings across the {brand_tier} tier, "
        f"we want to evaluate whether the proposed change moves the needle within the {duration}-day window."
    )

    hypothesis = (
        f"If we apply '{short_label}' on {brand_name} {value_stream} ({channel_section}) "
        f"to {audience.lower()}, then we expect a lift of at least {mde}% on {primary_kpi.split(' (')[0]} "
        f"because {hypothesis_seed.lower()}"
    )

    sha = hashlib.sha256(f"{test_id}|{title}|{outcome}".encode("utf-8")).hexdigest()

    # Meeting 4 §7: every Confluence page carries a 1-2 line Learning /
    # Recommendation snippet. The Backend extracts this into
    # references[].chunkInfo.documentMetadata.structData.learning_snippet
    # and the Frontend renders it on each result card.
    if outcome == "Win":
        learning_snippet = (
            f"WIN: '{short_label}' on {brand_name} {value_stream} ({channel_section}) "
            f"lifted {primary_kpi.split(' (')[0]} by +{primary_delta}% (Net RPV {rpv_delta:+}%). "
            f"{recommendation}"
        )
    elif outcome == "Loss":
        learning_snippet = (
            f"LOSS: '{short_label}' on {brand_name} {value_stream} ({channel_section}) "
            f"moved {primary_kpi.split(' (')[0]} by {primary_delta}% (Net RPV {rpv_delta:+}%); "
            f"averted ~${averted:,} in revenue loss. {recommendation}"
        )
    else:
        learning_snippet = (
            f"FLAT: '{short_label}' on {brand_name} {value_stream} ({channel_section}) "
            f"did not move {primary_kpi.split(' (')[0]} beyond MDE ({mde}%). {recommendation}"
        )

    return TestRecord(
        test_id=test_id,
        confluence_page_id=page_id,
        title=title,
        brand=brand_name,
        brand_code=brand_code,
        market=market,
        value_stream=value_stream,
        channel=channel,
        channel_section=channel_section,
        device=device,
        audience=audience,
        tactic=tactic,
        primary_kpi=primary_kpi,
        secondary_kpis=secondary,
        vendor=vendor,
        test_type=test_type,
        start_date=start.isoformat(),
        end_date=end.isoformat(),
        duration_days=duration,
        sample_size_per_arm=sample,
        mde_pct=mde,
        confidence_pct=confidence,
        power_pct=power,
        exposure_pct=exposure,
        split=split,
        outcome=outcome,
        primary_kpi_delta_pct=primary_delta,
        net_rpv_delta_pct=rpv_delta,
        aos_delta_pct=aos_delta,
        visits_total=visits_total,
        incremental_revenue_usd=incremental,
        averted_loss_usd=averted,
        recommendation_text=recommendation,
        recommendation_adopted=adopted,
        learning_snippet=learning_snippet,
        related_test_ids=related,
        hypothesis=hypothesis,
        problem_statement=problem_statement,
        short_label=short_label,
        confluence_url=confluence_url,
        sha256_source=sha,
    )

# ---------------------------------------------------------------------------
# Markdown rendering
# ---------------------------------------------------------------------------

def _yaml_frontmatter(r: TestRecord) -> str:
    secondary = "\n".join(f"  - {kpi}" for kpi in r.secondary_kpis)
    related = "\n".join(f"  - {tid}" for tid in r.related_test_ids) if r.related_test_ids else "  []"
    return (
        f"---\n"
        f"test_id: {r.test_id}\n"
        f"confluence_page_id: {r.confluence_page_id}\n"
        f"confluence_url: {r.confluence_url}\n"
        f'title: "{r.title}"\n'
        f"brand: {r.brand}\n"
        f"brand_code: {r.brand_code}\n"
        f"market: {r.market}\n"
        f"value_stream: {r.value_stream}\n"
        f"channel: {r.channel}\n"
        f"channel_section: {r.channel_section}\n"
        f"device: {r.device}\n"
        f"audience: {r.audience}\n"
        f"tactic: {r.tactic}\n"
        f"test_type: {r.test_type}\n"
        f'vendor: "{r.vendor}"\n'
        f'primary_kpi: "{r.primary_kpi}"\n'
        f"secondary_kpis:\n{secondary}\n"
        f"start_date: {r.start_date}\n"
        f"end_date: {r.end_date}\n"
        f"duration_days: {r.duration_days}\n"
        f"sample_size_per_arm: {r.sample_size_per_arm}\n"
        f"mde_pct: {r.mde_pct}\n"
        f"confidence_pct: {r.confidence_pct}\n"
        f"power_pct: {r.power_pct}\n"
        f"exposure_pct: {r.exposure_pct}\n"
        f'split: "{r.split}"\n'
        f"outcome: {r.outcome}\n"
        f"primary_kpi_delta_pct: {r.primary_kpi_delta_pct}\n"
        f"net_rpv_delta_pct: {r.net_rpv_delta_pct}\n"
        f"aos_delta_pct: {r.aos_delta_pct}\n"
        f"visits_total: {r.visits_total}\n"
        f"incremental_revenue_usd: {r.incremental_revenue_usd}\n"
        f"averted_loss_usd: {r.averted_loss_usd}\n"
        f'recommendation_adopted: "{r.recommendation_adopted}"\n'
        f'learning_snippet: "{r.learning_snippet.replace(chr(34), chr(39))}"\n'
        f"related_test_ids:\n{related}\n"
        f"sha256_source: {r.sha256_source}\n"
        f"metadata_quality: high\n"
        f"template_version: 2017.stable\n"
        f"---\n"
    )


def _findings_paragraph(r: TestRecord) -> str:
    if r.outcome == "Win":
        sig = "statistically significant at the configured threshold"
        verdict = (
            f"the challenger outperformed the control on the primary KPI ({r.primary_kpi}) "
            f"by **{abs(r.primary_kpi_delta_pct)}%** ({sig}). Net RPV moved by "
            f"{r.net_rpv_delta_pct}% and AOS by {r.aos_delta_pct}%."
        )
    elif r.outcome == "Loss":
        sig = "statistically significant in the wrong direction"
        verdict = (
            f"the challenger underperformed the control on the primary KPI ({r.primary_kpi}) "
            f"by **{abs(r.primary_kpi_delta_pct)}%** ({sig}). Net RPV moved by "
            f"{r.net_rpv_delta_pct}% and AOS by {r.aos_delta_pct}%."
        )
    else:
        verdict = (
            f"no statistically significant difference was observed on the primary KPI "
            f"({r.primary_kpi}); observed delta {r.primary_kpi_delta_pct}% sits within MDE ({r.mde_pct}%). "
            f"Net RPV {r.net_rpv_delta_pct}%, AOS {r.aos_delta_pct}% — also within noise."
        )
    return f"Across the {r.duration_days}-day test window, {verdict}"


def _segment_breakdown(rng: random.Random, r: TestRecord) -> str:
    rows = []
    for seg, label in [
        ("Device", ["Desktop", "Mobile", "Tablet"]),
        ("Visit Type", ["New", "Returning"]),
        ("Loyalty", ["Member", "Non-Member"]),
    ]:
        if rng.random() < 0.85:
            for v in label:
                delta = round(r.primary_kpi_delta_pct + rng.uniform(-0.6, 0.6), 2)
                rpv = round(r.net_rpv_delta_pct + rng.uniform(-0.4, 0.4), 2)
                rows.append(f"| {seg} | {v} | {delta}% | {rpv}% |")
    if not rows:
        return "_No additional segment break-downs were captured for this test._"
    return (
        "| Segment | Value | Primary KPI Δ | Net RPV Δ |\n"
        "|---|---|---|---|\n"
        + "\n".join(rows)
    )


def _custom_metrics_table(r: TestRecord) -> str:
    rows = [
        f"| Description / Location | Custom Variable | Tracking Notes |",
        f"|---|---|---|",
        f"| {r.short_label} click | eVar47 — {r.short_label.lower().replace(' ', '_')}_click | Track once per visit |",
        f"| {r.short_label} view  | eVar48 — {r.short_label.lower().replace(' ', '_')}_view  | Track always |",
        f"| {r.value_stream} arrival from {r.short_label} | eVar49 — {r.value_stream.lower().replace(' ', '_')}_arrival | Track once per session |",
    ]
    return "\n".join(rows)


def _impacts_table(r: TestRecord) -> str:
    def cell(delta: float) -> str:
        sign = "▲" if delta > 0 else ("▼" if delta < 0 else "—")
        return f"{sign} {abs(delta)}%"
    return "\n".join([
        "| Metric | Control | Challenger | Δ % |",
        "|---|---|---|---|",
        f"| Net RPV | baseline | challenger | {cell(r.net_rpv_delta_pct)} |",
        f"| {r.primary_kpi} | baseline | challenger | {cell(r.primary_kpi_delta_pct)} |",
        f"| AOS | baseline | challenger | {cell(r.aos_delta_pct)} |",
        f"| UPT | baseline | challenger | {cell(round(r.aos_delta_pct * 0.6, 2))} |",
        f"| AUR | baseline | challenger | {cell(round(r.aos_delta_pct * 0.4, 2))} |",
        f"| Total Visits (test arm) | — | {r.sample_size_per_arm:,} | — |",
        f"| Incremental Revenue (USD) | — | — | ${r.incremental_revenue_usd:,} |",
        f"| Averted Loss (USD)         | — | — | ${r.averted_loss_usd:,} |",
    ])


def _related_tests_block(r: TestRecord) -> str:
    if not r.related_test_ids:
        return "_No prior closely-related tests recorded._"
    lines = ["| Related Test ID | Relation |", "|---|---|"]
    for tid in r.related_test_ids:
        rel = random.choice([
            "Same hypothesis, different brand",
            "Same hypothesis, prior promo window",
            "Cross-brand follow-up",
            "Re-test after redesign",
        ])
        lines.append(f"| {tid} | {rel} |")
    return "\n".join(lines)


def render_markdown(r: TestRecord, rng: random.Random) -> str:
    fm = _yaml_frontmatter(r)
    findings = _findings_paragraph(r)
    seg = _segment_breakdown(rng, r)
    impacts = _impacts_table(r)
    custom = _custom_metrics_table(r)
    related = _related_tests_block(r)

    secondary_bullets = "\n".join(f"- {m}" for m in r.secondary_kpis)
    margin_line = (
        "Lift on GMS/Visit aligned with the directional Net RPV move; no margin compression observed."
        if r.outcome == "Win"
        else "GMS/Visit moved in the wrong direction in line with the Net RPV decline; the loss is real revenue, not a mix shift."
        if r.outcome == "Loss"
        else "GMS/Visit was flat across both arms within MDE."
    )
    sister_tier = "premium" if r.brand_code in ("ATH", "BR") else "discount"
    follow_up_stream = rng.choice(VALUE_STREAMS)
    challenger_because = r.hypothesis.split("because ", 1)[-1]

    body = (
        f"# {r.title}\n\n"
        f"> **Brand**: {r.brand} ({r.brand_code}) · **Market**: {r.market} · **Value Stream**: {r.value_stream}\n"
        f"> **Channel**: {r.channel} ({r.channel_section}) · **Device**: {r.device} · **Audience**: {r.audience}\n"
        f"> **Tactic**: {r.tactic} · **Test Type**: {r.test_type} · **Vendor**: {r.vendor}\n"
        f"> **Window**: {r.start_date} → {r.end_date} ({r.duration_days} days)\n"
        f"> **Outcome**: **{r.outcome}** · **Recommendation Adopted**: {r.recommendation_adopted}\n\n"
        f"---\n\n"
        f"## 1. Test Plan\n\n"
        f"### 1.1 Problem Statement\n{r.problem_statement}\n\n"
        f"### 1.2 Hypothesis\n{r.hypothesis}\n\n"
        f"### 1.3 Experimental Changes\n"
        f"- **Control**: existing {r.value_stream} experience on {r.brand} {r.channel_section}.\n"
        f"- **Challenger**: {r.short_label} variant — {challenger_because}\n\n"
        f"### 1.4 Significance Calculations & Experimental Design\n"
        f"| Field | Value |\n|---|---|\n"
        f"| Brand | {r.brand} |\n"
        f"| Scenarios | 1 Control + 1 Challenger ({r.split}) |\n"
        f"| Primary KPI | {r.primary_kpi} |\n"
        f"| Minimum Detectable Lift | ~{r.mde_pct}% |\n"
        f"| Confidence Threshold | {r.confidence_pct}% |\n"
        f"| Power Threshold | {r.power_pct}% |\n"
        f"| Sample Size per Variation | ~{r.sample_size_per_arm:,} visits |\n"
        f"| Estimated Duration | ~{r.duration_days} days |\n"
        f"| Test Exposure | {r.exposure_pct}% of eligible traffic |\n"
        f"| Audience Limitation | {r.audience} |\n\n"
        f"### 1.5 Adobe Workspace\n"
        f"- Project: *{r.brand} {r.market} — Production*\n"
        f"- Workspace: `[{r.brand_code} {r.market}] {r.short_label} Test`\n"
        f"- Filters: Return vs. New Visits · Segment (Global Blanket Correction Segment [Approved]) · Device Type · Page Type · Extreme Orders (COE — Exclude Extreme)\n\n"
        f"### 1.6 Measurement Strategy\n"
        f"**Metrics (All Experiments)**: Conversion Rate (OPV) · Net RPV · AOS · UPT · AUR · Total Visits · Visits Split (Visit/Visitor) · Variation Overlap\n\n"
        f"**Metrics (Test Specific)**:\n{secondary_bullets}\n\n"
        f"**Segments (All Experiments)**: New vs. Returning\n\n"
        f"**Segments (Test Specific)**: Desktop vs. Mobile · Loyalty vs. Non-Loyalty\n\n"
        f"### 1.7 Custom Metrics\n\n{custom}\n\n"
        f"---\n\n"
        f"## 2. Test Results\n\n"
        f"### 2.1 Findings (TL;DR)\n{findings}\n\n"
        f"### 2.2 Variation Description\n"
        f"- **Control**: as-is {r.value_stream} on {r.brand} {r.channel_section}.\n"
        f"- **Challenger**: applies the *{r.short_label}* treatment described in §1.3.\n"
        f"- _Screenshots_: see Confluence attachments `control_{r.test_id}.png`, `challenger_{r.test_id}.png` (omitted from this synthetic export).\n\n"
        f"### 2.3 Details\n{findings}\n\n"
        f"Statistical significance was computed **outside** Optimizely (Excel + online calculator) per standard Test & Learn COE practice — Optimizely's built-in significance is not reliable for GAP because of cross-brand basket attribution.\n\n"
        f"### 2.4 Impacts\n{impacts}\n\n"
        f"### 2.5 Segment Break-down\n{seg}\n\n"
        f"### 2.6 Product Mix\nTop contributing categories during the test window: women's tops, women's denim, men's polos, accessories. No anomalous category-level skew detected.\n\n"
        f"### 2.7 Gross Margin (GMS / Visit)\n{margin_line}\n\n"
        f"---\n\n"
        f"## 3. Recommendation\n\n"
        f"**{r.recommendation_text}**\n\n"
        f"Recommendation adopted: **{r.recommendation_adopted}**.\n\n"
        f"## 4. Optimization Opportunities (feeds next brainstorm)\n"
        f"- Re-run with a tighter MDE on the {r.audience.lower()} segment to confirm.\n"
        f"- Explore the same hypothesis on the sister brand in the {sister_tier} tier.\n"
        f"- Consider follow-up on {follow_up_stream} where the same tactic ({r.tactic}) has not yet been tested for {r.brand}.\n\n"
        f"## 5. Related Tests\n{related}\n\n"
        f"---\n\n"
        f"_Generated synthetic record for POC retrieval testing. Template version 2017.stable, mirroring the Test & Learn COE Confluence template walked through by Prateek Oberoi on 2026-05-06._\n"
    )
    return fm + "\n" + body


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=500)
    parser.add_argument("--out", type=str, default="pages")
    parser.add_argument("--seed", type=int, default=20260513)
    args = parser.parse_args()

    rng = random.Random(args.seed)
    out_dir = Path(__file__).parent / args.out
    out_dir.mkdir(parents=True, exist_ok=True)

    # late import to avoid circulars at module-import time
    from convert_md_to_html import md_to_html, render_html_document

    records: list[TestRecord] = []

    # First pass — base records
    for i in range(1, args.count + 1):
        # ~18% of tests have related prior tests (same brand or same hypothesis)
        related: list[str] = []
        if records and rng.random() < 0.18:
            sample_pool = rng.sample(records, k=min(len(records), 4))
            related = [t.test_id for t in sample_pool[: rng.randint(1, 3)]]
        rec = _build_record(rng, i, related)
        records.append(rec)

    # Write
    index_rows: list[dict] = []
    manifest_rows: list[dict] = []
    for rec in records:
        md = render_markdown(rec, rng)
        # Strip front-matter to use the rendered body only; metadata is taken
        # from the dataclass for a guaranteed-typed structData object.
        body_md = md.split("---\n", 2)[-1] if md.startswith("---") else md
        body_html = md_to_html(body_md)
        meta = asdict(rec)
        doc = render_html_document(meta, body_html)

        path = out_dir / f"{rec.confluence_page_id}.html"
        path.write_text(doc, encoding="utf-8")

        index_rows.append({
            "file": path.name,
            "test_id": rec.test_id,
            "title": rec.title,
            "brand": rec.brand,
            "value_stream": rec.value_stream,
            "tactic": rec.tactic,
            "outcome": rec.outcome,
            "start_date": rec.start_date,
            "end_date": rec.end_date,
            "primary_kpi_delta_pct": rec.primary_kpi_delta_pct,
        })
        manifest_rows.append({
            "id": rec.confluence_page_id,
            "structData": meta,
            "content": {
                "mimeType": "text/html",
                "uri": f"gs://gap-genai-discovery-corpus-md/pages/{path.name}",
            },
        })

    (out_dir.parent / "index.json").write_text(
        json.dumps(index_rows, indent=2),
        encoding="utf-8",
    )
    (out_dir.parent / "metadata.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in manifest_rows) + "\n",
        encoding="utf-8",
    )

    # Quick distribution summary
    from collections import Counter
    print(f"Generated {len(records)} HTML files at: {out_dir.resolve()}")
    print("Outcome distribution :", dict(Counter(r.outcome for r in records)))
    print("Brand distribution   :", dict(Counter(r.brand for r in records)))
    print("Value-stream dist.   :", dict(Counter(r.value_stream for r in records)))
    print("Tactic distribution  :", dict(Counter(r.tactic for r in records)))


if __name__ == "__main__":
    main()
