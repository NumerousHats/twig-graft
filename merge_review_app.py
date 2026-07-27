"""Streamlit GUI for human-in-the-loop review of proposed twig merges.

Run with:

    uv run streamlit run merge_review_app.py

Workflow:
    1. Point the app at a graph JSON file (e.g. dum.json) and click "Load & score proposals".
    2. All candidate merges are generated (via birth_merge.generate_proposals), scored for
       biological plausibility (via plausibility.score_proposal), and checked for conflicts
       with each other (via birth_merge.detect_conflicts).
    3. Review each proposal: side-by-side person cards for the matched pairs, an interactive
       graph of both twigs, and any plausibility warnings.
    4. Approve, reject, or skip each proposal. Approving a proposal automatically flags any
       other proposal that shares a node with it as conflicted.
    5. Export: approved (non-conflicting) proposals are applied to a fresh copy of the graph,
       producing an output JSON (e.g. dum2.json) and a JSON audit log of every decision made.
"""

import datetime
import json

import networkx as nx
import streamlit as st
from pyvis.network import Network

import graph_model
from birth_merge import apply_merge, detect_conflicts, generate_proposals, sanity_check
from plausibility import score_proposal

st.set_page_config(page_title="Twig Merge Review", layout="wide")

TWIG1_COLOR = "#4A90D9"
TWIG2_COLOR = "#E8913D"
MATCH_EDGE_COLOR = "#2ECC71"
PARENT_CHILD_EDGE_COLOR = "#666666"
SPOUSE_EDGE_COLOR = "#999999"


def _init_session_state():
    defaults = {
        "graph_model": None,
        "input_file": None,
        "proposals": [],
        "decisions": {},  # index -> "approved" | "rejected" | "skipped"
        "audit_log": [],
        "minimum_match_size": 5,
        "current_review_index": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def load_and_score(file_path, minimum_match_size):
    with open(file_path) as f:
        input_json = json.load(f)

    the_graph_model = graph_model.PeopleGraph(graph_json=input_json)
    sanity_check(the_graph_model.graph)

    proposals = generate_proposals(the_graph_model.graph, minimum_match_size=minimum_match_size)
    for proposal in proposals:
        proposal.plausibility = score_proposal(the_graph_model.graph, the_graph_model.graph,
                                                proposal.node_mapping)
    detect_conflicts(proposals)
    # Sort worst-scoring (most concerning) proposals first, so reviewers see the riskiest merges up front.
    proposals.sort(key=lambda p: p.plausibility.score)

    st.session_state.graph_model = the_graph_model
    st.session_state.input_file = file_path
    st.session_state.proposals = proposals
    st.session_state.decisions = {}
    st.session_state.audit_log = []
    st.session_state.minimum_match_size = minimum_match_size
    st.session_state.current_review_index = None


def person_summary(person):
    lines = []
    names = person.get_names()
    if names["birth"]:
        lines.append("**Birth name:** " + names["birth"][0].str_terse())
    if names["married"]:
        lines.append("**Married name(s):** " + ", ".join(n.str_terse() for n in names["married"]))
    if not names["birth"] and not names["married"] and names["unknown"]:
        lines.append("**Name:** " + names["unknown"][0].str_terse())
    lines.append("**Gender:** " + (person.gender or "unknown"))

    birth = person.birth_date()
    if birth:
        lines.append("**Birth date:** " + " or ".join(str(d) for d in birth))
    death = person.death_date()
    if death:
        lines.append("**Death date:** " + " or ".join(str(d) for d in death))
    if person.has_fact("Coelebs"):
        lines.append(":orange[Flag: never married (Coelebs)]")
    if person.has_fact("Stillbirth"):
        lines.append(":red[Flag: stillbirth]")

    return "  \n".join(lines)


def render_twig_graph(graph, new_twig, target_twig, node_mapping):
    net = Network(height="420px", width="100%", directed=True, cdn_resources="in_line")

    new_twig_set = set(new_twig)
    target_twig_set = set(target_twig)
    mapped_nodes = set(node_mapping.keys()) | set(node_mapping.values())

    for node in new_twig:
        person = graph.nodes[node]["person"]
        border = "#000000" if node in mapped_nodes else TWIG1_COLOR
        net.add_node(node, label=str(person)[:40], color=TWIG1_COLOR,
                     borderWidth=3 if node in mapped_nodes else 1, group=1)
    for node in target_twig:
        person = graph.nodes[node]["person"]
        net.add_node(node, label=str(person)[:40], color=TWIG2_COLOR,
                     borderWidth=3 if node in mapped_nodes else 1, group=2)

    for u, v, data in graph.edges(data=True):
        if (u in new_twig_set or u in target_twig_set) and (v in new_twig_set or v in target_twig_set):
            rel = data["relation"].relationship_type
            color = PARENT_CHILD_EDGE_COLOR if rel == "parent-child" else SPOUSE_EDGE_COLOR
            net.add_edge(u, v, color=color, label=rel[:4], arrows="to")

    for p1, p2 in node_mapping.items():
        net.add_edge(p1, p2, color=MATCH_EDGE_COLOR, dashes=True, label="match", arrows="")

    return net.generate_html()


def render_proposal_table(proposals, decisions):
    rows = []
    for i, proposal in enumerate(proposals):
        status = decisions.get(i, "pending")
        num_warnings = len(proposal.plausibility.warnings) if proposal.plausibility else 0
        num_errors = len(proposal.plausibility.errors()) if proposal.plausibility else 0
        rows.append({
            "#": i,
            "status": "conflicted" if proposal.conflict and status == "pending" else status,
            "match size": proposal.match_size,
            "plausibility": round(proposal.plausibility.score, 2) if proposal.plausibility else None,
            "warnings": num_warnings,
            "errors": num_errors,
            "target twig": proposal.target_twig_id[:8],
        })
    return rows


def approve_proposal(index):
    proposals = st.session_state.proposals
    st.session_state.decisions[index] = "approved"
    for j in proposals[index].conflicts_with:
        if st.session_state.decisions.get(j) != "rejected":
            st.session_state.decisions[j] = "conflicted"


def reject_proposal(index):
    st.session_state.decisions[index] = "rejected"


def skip_proposal(index):
    st.session_state.decisions[index] = "skipped"


def _next_pending_index(visible_indices, after_index):
    """Return the index of the next pending (unreviewed) proposal in visible_indices, starting the
    search after *after_index*.  Wraps around if needed.  Returns None if nothing is pending."""
    after_pos = visible_indices.index(after_index) if after_index in visible_indices else -1
    for i in visible_indices[after_pos + 1:]:
        status = st.session_state.decisions.get(i, "pending")
        if status == "pending" and not st.session_state.proposals[i].conflict:
            return i
    for i in visible_indices[:after_pos + 1]:
        status = st.session_state.decisions.get(i, "pending")
        if status == "pending" and not st.session_state.proposals[i].conflict:
            return i
    return None


def export_results(output_json_path, audit_log_path):
    proposals = st.session_state.proposals
    decisions = st.session_state.decisions

    # Work on a fresh copy of the graph so the in-review graph is left untouched, in case the
    # reviewer wants to keep working after exporting.
    with open(st.session_state.input_file) as f:
        input_json = json.load(f)
    export_graph_model = graph_model.PeopleGraph(graph_json=input_json)
    export_graph = export_graph_model.graph

    audit_entries = []
    for i, proposal in enumerate(proposals):
        decision = decisions.get(i, "pending")
        entry = {
            "proposal_index": i,
            "target_twig_id": proposal.target_twig_id,
            "match_size": proposal.match_size,
            "plausibility_score": proposal.plausibility.score if proposal.plausibility else None,
            "warnings": [
                {"check": w.check, "severity": w.severity, "message": w.message}
                for w in (proposal.plausibility.warnings if proposal.plausibility else [])
            ],
            "conflict": proposal.conflict,
            "conflicts_with": proposal.conflicts_with,
            "decision": decision,
            "timestamp": datetime.datetime.now().isoformat(),
        }

        if decision == "approved":
            success, _ = apply_merge(export_graph, proposal.new_twig, proposal.target_twig,
                                      proposal.node_mapping)
            entry["applied"] = success
            if not success:
                entry["decision"] = "failed"
        audit_entries.append(entry)

    sanity_check(export_graph_model.graph)

    with open(output_json_path, "w") as f:
        json.dump(export_graph_model.json(), f, indent=2)

    audit_log = {
        "input_file": st.session_state.input_file,
        "export_time": datetime.datetime.now().isoformat(),
        "minimum_match_size": st.session_state.minimum_match_size,
        "decisions": audit_entries,
    }
    with open(audit_log_path, "w") as f:
        json.dump(audit_log, f, indent=2)

    return audit_log


def main():
    _init_session_state()

    st.title("Twig Merge Review")
    st.caption("Human-in-the-loop review of proposed twig merges before they are applied.")

    with st.sidebar:
        st.header("Load data")
        file_path = st.text_input("Graph JSON path", value="dum.json")
        minimum_match_size = st.slider("Minimum match size", min_value=3, max_value=10, value=5)
        if st.button("Load & score proposals", type="primary"):
            with st.spinner("Generating and scoring merge proposals..."):
                load_and_score(file_path, minimum_match_size)
            st.success("Loaded {} proposals.".format(len(st.session_state.proposals)))

        st.divider()
        st.header("Filter")
        show_pending = st.checkbox("Pending", value=True)
        show_approved = st.checkbox("Approved", value=True)
        show_rejected = st.checkbox("Rejected", value=False)
        show_conflicted = st.checkbox("Conflicted", value=True)
        show_skipped = st.checkbox("Skipped", value=False)

        st.divider()
        st.header("Export")
        output_json_path = st.text_input("Output graph JSON path", value="dum2.json")
        audit_log_path = st.text_input("Audit log path", value="merge_audit_log.json")
        if st.button("Apply approved & export"):
            if not st.session_state.proposals:
                st.error("Load proposals first.")
            else:
                with st.spinner("Applying approved merges and writing output..."):
                    audit_log = export_results(output_json_path, audit_log_path)
                num_applied = sum(1 for e in audit_log["decisions"] if e["decision"] == "approved")
                num_failed = sum(1 for e in audit_log["decisions"] if e["decision"] == "failed")
                st.success("Wrote {} and {}. {} merges applied, {} failed.".format(
                    output_json_path, audit_log_path, num_applied, num_failed))

    proposals = st.session_state.proposals
    decisions = st.session_state.decisions

    if not proposals:
        st.info("Use the sidebar to load a graph JSON file and generate merge proposals.")
        return

    status_filters = {
        "pending": show_pending,
        "approved": show_approved,
        "rejected": show_rejected,
        "conflicted": show_conflicted,
        "skipped": show_skipped,
    }

    def effective_status(i, proposal):
        status = decisions.get(i, "pending")
        if proposal.conflict and status == "pending":
            return "conflicted"
        return status

    visible_indices = [i for i, p in enumerate(proposals) if status_filters.get(effective_status(i, p), True)]

    num_approved = sum(1 for i, p in enumerate(proposals) if decisions.get(i) == "approved")
    num_rejected = sum(1 for i, p in enumerate(proposals) if decisions.get(i) == "rejected")
    num_conflicted = sum(1 for i, p in enumerate(proposals) if effective_status(i, p) == "conflicted")
    num_skipped = sum(1 for i, p in enumerate(proposals) if decisions.get(i) == "skipped")
    num_pending = len(proposals) - num_approved - num_rejected - num_conflicted - num_skipped

    cols = st.columns(5)
    cols[0].metric("Total", len(proposals))
    cols[1].metric("Approved", num_approved)
    cols[2].metric("Rejected", num_rejected)
    cols[3].metric("Conflicted", num_conflicted)
    cols[4].metric("Pending", num_pending)

    st.subheader("Proposals")
    table_rows = render_proposal_table(proposals, decisions)
    visible_rows = [table_rows[i] for i in visible_indices]
    st.dataframe(visible_rows, width="stretch", hide_index=True)

    if not visible_indices:
        st.info("No proposals match the current filter.")
        return

    st.subheader("Review a proposal")

    current = st.session_state.current_review_index
    if current not in visible_indices:
        current = visible_indices[0]
    select_pos = visible_indices.index(current)

    selected_index = st.selectbox("Proposal #", options=visible_indices, index=select_pos,
                                  format_func=lambda i: (
                                      "#{} - match size {} - plausibility {:.2f} - {}".format(
                                          i, proposals[i].match_size, proposals[i].plausibility.score,
                                          effective_status(i, proposals[i]))))

    proposal = proposals[selected_index]
    graph = st.session_state.graph_model.graph
    status = effective_status(selected_index, proposal)

    st.markdown("**Status:** {}".format(status))
    if proposal.conflict:
        st.warning("Conflicts with proposal(s): {}".format(proposal.conflicts_with))

    if proposal.plausibility and proposal.plausibility.warnings:
        st.markdown("**Plausibility warnings** (score: {:.2f})".format(proposal.plausibility.score))
        for w in proposal.plausibility.warnings:
            if w.severity == "error":
                st.error("[{}] {}".format(w.check, w.message))
            else:
                st.warning("[{}] {}".format(w.check, w.message))
    else:
        st.success("No plausibility warnings (score: {:.2f})".format(
            proposal.plausibility.score if proposal.plausibility else 1.0))

    st.markdown("### Matched pairs")
    for p1, p2 in proposal.node_mapping.items():
        col1, col2 = st.columns(2)
        with col1:
            with st.container(border=True):
                st.markdown("**Twig 1: {}**".format(p1[:7]))
                st.markdown(person_summary(graph.nodes[p1]["person"]))
        with col2:
            with st.container(border=True):
                st.markdown("**Twig 2: {}**".format(p2[:7]))
                st.markdown(person_summary(graph.nodes[p2]["person"]))

    st.markdown("### Graph")
    html = render_twig_graph(graph, proposal.new_twig, proposal.target_twig, proposal.node_mapping)
    st.iframe(html, height=440)

    st.markdown("### Decision")
    button_cols = st.columns(3)
    if button_cols[0].button("Approve", key="approve_{}".format(selected_index)):
        approve_proposal(selected_index)
        next_idx = _next_pending_index(visible_indices, selected_index)
        st.session_state.current_review_index = next_idx if next_idx is not None else selected_index
        st.rerun()
    if button_cols[1].button("Reject", key="reject_{}".format(selected_index)):
        reject_proposal(selected_index)
        next_idx = _next_pending_index(visible_indices, selected_index)
        st.session_state.current_review_index = next_idx if next_idx is not None else selected_index
        st.rerun()
    if button_cols[2].button("Skip", key="skip_{}".format(selected_index)):
        skip_proposal(selected_index)
        next_idx = _next_pending_index(visible_indices, selected_index)
        st.session_state.current_review_index = next_idx if next_idx is not None else selected_index
        st.rerun()


if __name__ == "__main__":
    main()
