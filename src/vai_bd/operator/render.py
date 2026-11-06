"""Escaped, accessible server-rendered operator pages."""

# ruff: noqa: E501

from html import escape

from vai_bd.domain.refs import ObjectRevisionRef
from vai_bd.operator.models import OperatorCycleList, OperatorCycleView


def render_cycle_list(view: OperatorCycleList) -> str:
    cards = "".join(
        f"""
        <article class="cycle-card">
          <p class="eyebrow">{_text(item.workflow_state)}</p>
          <h2><a href="/operator/cycles/{item.cycle_id}">{_text(item.offer_name)}</a></h2>
          <p>{_text(item.market_boundary)}</p>
          <dl class="compact">
            <div><dt>Effective date</dt><dd>{item.effective_date.isoformat()}</dd></div>
            <div><dt>Opportunities</dt><dd>{item.opportunity_count}</dd></div>
            <div><dt>Warnings</dt><dd>{item.warning_count}</dd></div>
          </dl>
        </article>"""
        for item in view.cycles
    )
    if not cards:
        cards = '<p class="empty">No decision cycles are available.</p>'
    return _shell(
        "Decision cycles",
        """
        <header class="page-header">
          <p class="eyebrow">VAI decision intelligence</p>
          <h1>Decision cycles</h1>
          <p class="lede">Read-only operational view of governed recommendations.</p>
        </header>
        <main id="main-content"><section class="card-grid" aria-label="Decision cycles">
        """
        + cards
        + "</section></main>",
    )


def render_cycle_detail(view: OperatorCycleView) -> str:
    opportunity_by_ref = {item.opportunity_ref: item.company_name for item in view.opportunities}
    warnings = _items(view.warnings, "No active revision or freshness warnings.")
    limitations = _items(view.coverage.limitations, "No disclosed coverage limitations.")
    candidates = (
        "".join(
            f"""
        <article class="candidate">
          <div><p class="eyebrow">{_text(item.disposition)}</p><h3>{_text(item.name)}</h3></div>
          <p><strong>Disposition reason:</strong> {_text(item.reason)}</p>
          <p><strong>Evidence:</strong> {_text(item.evidence_summary)}</p>
          <details><summary>Limitations and contradictions</summary>
            <h4>Evidence limitations</h4>{_items(item.evidence_limitations, "None disclosed.")}
            <h4>Contradictions</h4>{_items(item.contradictions, "None recorded.")}
          </details>
          <p class="meta">{_text(item.revision_label)} · {_text(item.freshness)}</p>
        </article>"""
            for item in view.candidates
        )
        or '<p class="empty">No candidates recorded.</p>'
    )
    opportunities = "".join(_opportunity(item) for item in view.opportunities) or (
        '<p class="empty">No qualified opportunities recorded.</p>'
    )
    priority = (
        "".join(
            f"<li><strong>{_text(opportunity_by_ref.get(item.opportunity_ref, _ref(item.opportunity_ref)))}</strong>"
            f"<span>{_text(item.position)}</span><p>{_text(item.reason)}</p></li>"
            for item in view.priority
        )
        or "<li>No comparative priority state available.</li>"
    )
    allocation_groups = "".join(
        f"""
        <section class="allocation-tier">
          <p class="eyebrow">{_text(tier)}</p>
          {_allocation_items(view, tier, opportunity_by_ref)}
        </section>"""
        for tier in ("ACT_NOW", "DEFERRED_CAPACITY", "DEFERRED_PRIORITY", "INVESTIGATE")
    )
    actions = (
        "".join(
            f"""
        <article class="action-card">
          <p class="eyebrow">{_text(item.action_type)}</p>
          <h3>{_text(opportunity_by_ref.get(item.opportunity_ref, _ref(item.opportunity_ref)))}</h3>
          <p><strong>Next credible action:</strong> {_text(item.next_action)}</p>
          <div class="state-pair">
            <section><h4>Release readiness</h4><p class="state">{_text(item.readiness)}</p>
              <p>{_text(item.readiness_reason)}</p></section>
            <section><h4>Human authorization</h4><p class="state">{_text(item.authorization)}</p>
              <p>{_text(item.authorization_reason)}</p></section>
          </div>
        </article>"""
            for item in view.actions
        )
        or '<p class="empty">No action packages prepared.</p>'
    )
    body = f"""
      <nav aria-label="Breadcrumb"><a href="/operator">Decision cycles</a><span>/</span>
        <span aria-current="page">{_text(view.offer_name)}</span></nav>
      <header class="page-header detail-header">
        <div><p class="eyebrow">{_text(view.workflow_state)}</p><h1>{_text(view.offer_name)}</h1>
          <p class="lede">{_text(view.offer_summary)}</p></div>
        <dl class="identity"><div><dt>Cycle revision</dt><dd>{_text(_ref(view.cycle_ref))}</dd></div>
          <div><dt>Effective date</dt><dd>{view.effective_date.isoformat()}</dd></div></dl>
      </header>
      <main id="main-content">
        <section aria-labelledby="context-heading"><h2 id="context-heading">Decision context</h2>
          <div class="context-grid">
            <article><h3>Market</h3><p>{_text(view.market_boundary)}</p></article>
            <article><h3>Capacity</h3><p class="metric">{view.capacity_available} {_text(view.capacity_unit)}</p>
              <p>{_text(view.planning_horizon)} · at most {view.capacity_limit} pursuits</p></article>
            <article><h3>Coverage</h3><p>{_text(view.coverage.basis)}</p>
              <p class="state">{_text(view.coverage.status)}</p>{limitations}</article>
          </div>
        </section>
        <aside class="warnings" aria-labelledby="warnings-heading"><h2 id="warnings-heading">Freshness and reassessment</h2>{warnings}</aside>
        <section aria-labelledby="candidates-heading"><h2 id="candidates-heading">Candidate disposition</h2>
          <div class="stack">{candidates}</div></section>
        <section aria-labelledby="opportunities-heading"><h2 id="opportunities-heading">Qualified opportunities</h2>
          <div class="stack">{opportunities}</div></section>
        <section aria-labelledby="portfolio-heading"><h2 id="portfolio-heading">Portfolio decision</h2>
          <p class="section-note">Commercial comparison and capacity allocation are independent views.</p>
          <div class="portfolio-grid"><article class="priority-panel"><h3>Comparative priority</h3><ol>{priority}</ol></article>
            <article class="allocation-panel"><h3>Capacity allocation</h3><div class="allocation-grid">{allocation_groups}</div></article></div>
        </section>
        <section aria-labelledby="actions-heading"><h2 id="actions-heading">Next actions and governance</h2>
          <div class="stack">{actions}</div></section>
      </main>"""
    return _shell(view.offer_name, body)


def _opportunity(item) -> str:  # type: ignore[no-untyped-def]
    confidences = (
        "".join(
            f"<li><strong>{_text(value.claim)} — {_text(value.level)}</strong><p>{_text(value.rationale)}</p></li>"
            for value in item.confidences
        )
        or "<li>No confidence claims recorded.</li>"
    )
    warning = (
        f'<p class="alert"><strong>Reassessment:</strong> {_text(item.reassessment_warning)}</p>'
        if item.reassessment_warning
        else ""
    )
    return f"""
      <article class="opportunity">
        <div class="opportunity-heading"><div><p class="eyebrow">{_text(item.qualification)}</p>
          <h3>{_text(item.company_name)}</h3></div><p class="demand">Demand: {_text(item.pursuit_demand)}</p></div>
        <p>{_text(item.qualification_reason)}</p><div class="judgments">
          <section><h4>Fit</h4><p>{_text(item.fit)}</p></section>
          <section><h4>Need</h4><p>{_text(item.need)}</p></section>
          <section><h4>Evidence</h4><p>{_text(item.evidence_summary)}</p></section></div>
        <details><summary>Confidence, contradictions, and uncertainty</summary>
          <h4>Confidence by claim</h4><ul>{confidences}</ul>
          <h4>Contradictions</h4>{_items(item.contradictions, "None recorded.")}
          <h4>Material uncertainty</h4>{_items(item.uncertainties, "None disclosed.")}</details>
        {warning}<p class="meta">{_text(item.revision_label)} · {_text(item.freshness)}</p>
      </article>"""


def _allocation_items(view, tier, names) -> str:  # type: ignore[no-untyped-def]
    members = [item for item in view.allocation if item.tier == tier]
    if not members:
        return '<p class="empty">No opportunities.</p>'
    return (
        "<ul>"
        + "".join(
            f"<li><strong>{_text(names.get(item.opportunity_ref, _ref(item.opportunity_ref)))}</strong>"
            f"<p>{_text(item.capacity_effect)}</p><p>{_text(item.reason)}</p></li>"
            for item in members
        )
        + "</ul>"
    )


def _items(values: tuple[str, ...], empty: str) -> str:
    if not values:
        return f'<p class="empty">{_text(empty)}</p>'
    return "<ul>" + "".join(f"<li>{_text(value)}</li>" for value in values) + "</ul>"


def _ref(value: ObjectRevisionRef) -> str:
    return f"{value.object_type} · r{value.revision}"


def _text(value: object) -> str:
    return escape(str(value), quote=True)


def _shell(title: str, body: str) -> str:
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_text(title)} · VAI</title><style>
:root{{--ink:#17201d;--muted:#66716c;--paper:#f4f1e8;--panel:#fffdf7;--line:#d8d2c3;--accent:#0f6655;--accent-soft:#dcebe5;--warning:#9b4b24;--shadow:0 12px 30px rgba(32,42,38,.08)}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--paper);color:var(--ink);font:16px/1.55 ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}}body:before{{content:"";display:block;height:7px;background:linear-gradient(90deg,var(--accent),#be8a45)}}a{{color:var(--accent);text-underline-offset:3px}}.skip-link{{display:block;width:max-content;margin:.5rem 1rem;padding:.4rem .7rem;background:var(--panel);border-radius:8px}}nav,.page-header,main,.warnings{{width:min(1180px,calc(100% - 2rem));margin-inline:auto}}nav{{padding:1.25rem 0 0;display:flex;gap:.6rem;color:var(--muted)}}.page-header{{padding:3.5rem 0 2rem}}.detail-header{{display:flex;justify-content:space-between;gap:2rem;align-items:end}}h1,h2,h3,h4,p{{margin-top:0}}h1{{font:700 clamp(2.5rem,7vw,5.5rem)/.95 Georgia,serif;letter-spacing:-.045em;max-width:900px}}h2{{font:700 clamp(1.65rem,3vw,2.4rem)/1.1 Georgia,serif;margin:4rem 0 1.25rem}}h3{{font-size:1.12rem}}h4{{margin-bottom:.35rem}}.eyebrow{{color:var(--accent);font-size:.76rem;font-weight:800;letter-spacing:.13em;text-transform:uppercase}}.lede{{max-width:700px;color:var(--muted);font-size:1.15rem}}.card-grid,.context-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:1rem}}.cycle-card,.candidate,.opportunity,.action-card,.context-grid article,.priority-panel,.allocation-panel{{background:var(--panel);border:1px solid var(--line);border-radius:18px;padding:1.35rem;box-shadow:var(--shadow)}}.cycle-card h2{{margin:.2rem 0 .6rem;font:700 1.45rem/1.15 Georgia,serif}}.compact,.identity{{display:grid;gap:.7rem;margin:1rem 0 0}}dl div{{display:flex;justify-content:space-between;gap:1rem}}dt{{color:var(--muted)}}dd{{margin:0;font-weight:700}}.identity{{min-width:290px}}.metric{{font:700 2rem/1 Georgia,serif}}.state{{font-weight:800;color:var(--accent)}}.warnings{{margin-top:3rem;padding:1.25rem 1.5rem;border-left:5px solid var(--warning);background:#fff7ef}}.warnings h2{{font:700 1.25rem Georgia,serif;margin:0 0 .5rem}}.stack{{display:grid;gap:1rem}}.candidate,.opportunity,.action-card{{border-left:5px solid var(--accent)}}details{{margin-top:1rem;border-top:1px solid var(--line);padding-top:.8rem}}summary{{cursor:pointer;font-weight:750;color:var(--accent)}}details h4{{margin-top:1rem}}.meta,.empty,.section-note{{color:var(--muted)}}.opportunity-heading,.state-pair{{display:flex;justify-content:space-between;gap:1rem}}.demand{{padding:.5rem .75rem;background:var(--accent-soft);border-radius:999px;white-space:nowrap}}.judgments{{display:grid;grid-template-columns:repeat(3,1fr);gap:.75rem}}.judgments section,.state-pair section{{padding:1rem;background:#f7f5ee;border-radius:12px}}.alert{{padding:.8rem;background:#fff0e5;color:#713718;border-radius:10px}}.portfolio-grid{{display:grid;grid-template-columns:minmax(280px,.75fr) minmax(0,1.5fr);gap:1rem}}.priority-panel ol,.allocation-tier ul{{padding-left:1.2rem}}.priority-panel li,.allocation-tier li{{margin-bottom:1rem}}.priority-panel li span{{display:block;color:var(--accent);font-weight:800}}.allocation-grid{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:1rem}}.allocation-tier{{padding:1rem;border:1px solid var(--line);border-radius:12px}}main{{padding-bottom:5rem}}@media(max-width:760px){{.detail-header,.opportunity-heading,.state-pair{{display:block}}.identity{{min-width:0}}.portfolio-grid,.judgments,.allocation-grid{{grid-template-columns:1fr}}h1{{font-size:2.7rem}}}}@media(prefers-reduced-motion:reduce){{*{{scroll-behavior:auto!important}}}}
</style></head><body><a class="skip-link" href="#main-content">Skip to content</a>{body}</body></html>"""
