"""Generate merge proposals from a graph JSON file and save them for review.

This is the (slow, one-off) first half of the human-in-the-loop merge workflow.  It loads a graph
JSON file, finds every candidate twig merge via McGregor subgraph matching, scores each for
biological plausibility, flags conflicts, and writes a self-contained proposals file.  The
interactive review step (`merge_review_app.py`) then loads that file without re-running any
comparisons.

Usage:

    uv run python generate_proposals.py dum.json -o proposals.json --min-size 5
"""

import json
import logging

import click

import graph_model
from birth_merge import detect_conflicts, generate_proposals, sanity_check
from plausibility import score_proposal
from proposal_io import write_proposals_file


@click.command()
@click.argument('infile')
@click.option('-o', '--outfile', default='proposals.json',
              help='Destination proposals file (default: proposals.json).')
@click.option('--min-size', type=int, default=5,
              help='Minimum number of matched node pairs to accept a proposal (default: 5).')
def cli(infile, outfile, min_size):
    logging.basicConfig(format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                        level=logging.WARNING)
    logging.getLogger('mcgregor').setLevel(logging.WARNING)
    logging.getLogger('comparison').setLevel(logging.WARNING)

    with open(infile) as f:
        input_json = json.load(f)

    the_graph_model = graph_model.PeopleGraph(graph_json=input_json)
    sanity_check(the_graph_model.graph)

    proposals = generate_proposals(the_graph_model.graph, minimum_match_size=min_size)
    for proposal in proposals:
        proposal.plausibility = score_proposal(the_graph_model.graph, the_graph_model.graph,
                                               proposal.node_mapping)
    detect_conflicts(proposals)
    proposals.sort(key=lambda p: p.plausibility.score)

    write_proposals_file(outfile, the_graph_model.json(), proposals,
                         minimum_match_size=min_size, input_file=infile)

    num_errors = sum(1 for p in proposals
                     if p.plausibility and p.plausibility.has_errors())
    num_conflicts = sum(1 for p in proposals if p.conflict)
    click.echo("Generated {} proposals from {} ({} with plausibility errors, {} conflicting); "
               "wrote {}".format(len(proposals), infile, num_errors, num_conflicts, outfile))


if __name__ == "__main__":
    cli()
