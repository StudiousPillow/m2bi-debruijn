#!/bin/env python3
# -*- coding: utf-8 -*-
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#    A copy of the GNU General Public License is available at
#    http://www.gnu.org/licenses/gpl-3.0.html

"""Perform assembly based on debruijn graph."""

import argparse
import os
import sys
from pathlib import Path
from networkx import (
    DiGraph,
    all_simple_paths,
    lowest_common_ancestor,
    has_path,
    random_layout,
    draw,
    spring_layout,
)
import networkx as nx
import matplotlib
from operator import itemgetter
import random

random.seed(9001)
from random import randint
import statistics
import textwrap
import matplotlib.pyplot as plt
from typing import Iterator, Dict, List

from collections import Counter
sys.setrecursionlimit(10000) 
from itertools import combinations

matplotlib.use("Agg")

__author__ = "Your Name"
__copyright__ = "Universite Paris Diderot"
__credits__ = ["Your Name"]
__license__ = "GPL"
__version__ = "1.0.0"
__maintainer__ = "Your Name"
__email__ = "your@email.fr"
__status__ = "Developpement"


def isfile(path: str) -> Path:  # pragma: no cover
    """Check if path is an existing file.

    :param path: (str) Path to the file

    :raises ArgumentTypeError: If file does not exist

    :return: (Path) Path object of the input file
    """
    myfile = Path(path)
    if not myfile.is_file():
        if myfile.is_dir():
            msg = f"{myfile.name} is a directory."
        else:
            msg = f"{myfile.name} does not exist."
        raise argparse.ArgumentTypeError(msg)
    return myfile


def get_arguments():  # pragma: no cover
    """Retrieves the arguments of the program.

    :return: An object that contains the arguments
    """
    # Parsing arguments
    parser = argparse.ArgumentParser(
        description=__doc__, usage="{0} -h".format(sys.argv[0])
    )
    parser.add_argument(
        "-i", dest="fastq_file", type=isfile, required=True, help="Fastq file"
    )
    parser.add_argument(
        "-k", dest="kmer_size", type=int, default=22, help="k-mer size (default 22)"
    )
    parser.add_argument(
        "-o",
        dest="output_file",
        type=Path,
        default=Path(os.curdir + os.sep + "contigs.fasta"),
        help="Output contigs in fasta file (default contigs.fasta)",
    )
    parser.add_argument(
        "-f", dest="graphimg_file", type=Path, help="Save graph as an image (png)"
    )
    return parser.parse_args()


def read_fastq(fastq_file: Path) -> Iterator[str]:
    """Extract reads from fastq files.

    :param fastq_file: (Path) Path to the fastq file.
    :return: A generator object that iterate the read sequences.
    """
    fastq_file = isfile(fastq_file)
    with open(fastq_file, "r") as handle:
        lines = iter(handle.readlines())
        for line in lines:
            yield next(lines).strip()
            next(lines)
            next(lines)


def cut_kmer(read: str, kmer_size: int) -> Iterator[str]:
    """Cut read into kmers of size kmer_size.

    :param read: (str) Sequence of a read.
    :return: A generator object that provides the kmers (str) of size kmer_size.
    """
    for idx in range(len(read)-kmer_size+1):
        yield read[idx:idx+kmer_size]


def build_kmer_dict(fastq_file: Path, kmer_size: int) -> Dict[str, int]:
    """Build a dictionnary object of all kmer occurrences in the fastq file

    :param fastq_file: (str) Path to the fastq file.
    :return: A dictionnary object that identify all kmer occurrences.
    """
    read_gen = read_fastq(fastq_file)
    kmer_dict = Counter()
    for read in read_gen:
        kmer_gen = cut_kmer(read, kmer_size)
        kmer_count = Counter(kmer_gen)
    kmer_dict += kmer_count
    return(dict(kmer_dict))


def build_graph(kmer_dict: Dict[str, int]) -> DiGraph:
    """Build the debruijn graph

    :param kmer_dict: A dictionnary object that identify all kmer occurrences.
    :return: A directed graph (nx) of all kmer substring and weight (occurrence).
    """
    digraph = nx.DiGraph()

    for kmer, occurrence in kmer_dict.items():
        prefix = kmer[:-1]
        suffix = kmer[1:]
        digraph.add_edge(prefix, suffix, weight=occurrence)

    return digraph


def remove_paths(
    graph: DiGraph,
    path_list: List[List[str]],
    delete_entry_node: bool,
    delete_sink_node: bool,
) -> DiGraph:
    """Remove a list of path in a graph. A path is set of connected node in
    the graph

    :param graph: (nx.DiGraph) A directed graph object
    :param path_list: (list) A list of path
    :param delete_entry_node: (boolean) True->We remove the first node of a path
    :param delete_sink_node: (boolean) True->We remove the last node of a path
    :return: (nx.DiGraph) A directed graph object
    """
    for path in path_list:
        if not delete_entry_node:  
            path = path[1:]
        if not delete_sink_node:  
            path = path[:-1]
        graph.remove_nodes_from(path)
    return graph

def select_best_path(
    graph: DiGraph,
    path_list: List[List[str]],
    path_length: List[int],
    weight_avg_list: List[float],
    delete_entry_node: bool = False,
    delete_sink_node: bool = False,
) -> DiGraph:
    """Select the best path between different paths

    :param graph: (nx.DiGraph) A directed graph object
    :param path_list: (list) A list of path
    :param path_length_list: (list) A list of length of each path
    :param weight_avg_list: (list) A list of average weight of each path
    :param delete_entry_node: (boolean) True->We remove the first node of a path
    :param delete_sink_node: (boolean) True->We remove the last node of a path
    :return: (nx.DiGraph) A directed graph object
    """
    if len(path_list) == 1:
        return graph
    
    weight_stdev = statistics.stdev(weight_avg_list)
    
    if weight_stdev > 0: 
        best_path_index = weight_avg_list.index(max(weight_avg_list)) 
    else:
        length_stdev = statistics.stdev(path_length)
        if length_stdev > 0: 
            best_path_index = path_length.index(max(path_length)) 
        else:
            best_path_index = random.randint(0, len(path_list) - 1)
    
    paths_to_remove = [path for i, path in enumerate(path_list) if i != best_path_index]
    
    remove_paths(graph, paths_to_remove, delete_entry_node, delete_sink_node)
    
    return graph


def path_average_weight(graph: DiGraph, path: List[str]) -> float:
    """Compute the weight of a path

    :param graph: (nx.DiGraph) A directed graph object
    :param path: (list) A path consist of a list of nodes
    :return: (float) The average weight of a path
    """
    return statistics.mean(
        [c["weight"] for (a, b, c) in graph.subgraph(path).edges(data=True)]
    )


def solve_bubble(graph: DiGraph, ancestor_node: str, descendant_node: str) -> DiGraph:
    """Explore and solve bubble issue

    :param graph: (nx.DiGraph) A directed graph object
    :param ancestor_node: (str) An upstream node in the graph
    :param descendant_node: (str) A downstream node in the graph
    :return: (nx.DiGraph) A directed graph object
    """
    paths = list(nx.all_simple_paths(graph, source=ancestor_node, target=descendant_node))

    lengths = [len(path) for path in paths]
    weights = []

    for path in paths:
        edge_weights = [graph[u][v]['weight'] for u, v in zip(path[:-1], path[1:])]
        weights.append(sum(edge_weights) / len(edge_weights))  
    graph = select_best_path(graph, paths, lengths, weights, delete_entry_node=False, delete_sink_node=False)
    
    return graph


def simplify_bubbles(graph: DiGraph) -> DiGraph:
    """Detect and explode bubbles

    :param graph: (nx.DiGraph) A directed graph object
    :return: (nx.DiGraph) A directed graph object
    """
    bubble = False
    for noeud in graph.nodes:
        liste_predecesseurs = list(graph.predecessors(noeud))
        if len(liste_predecesseurs) > 1:
            for i in range(len(liste_predecesseurs)):
                for j in range(i + 1, len(liste_predecesseurs)):
                    noeud_ancetre = nx.lowest_common_ancestor(graph, liste_predecesseurs[i], liste_predecesseurs[j])
                    if noeud_ancetre is not None:
                        bubble = True
                        break
                if bubble:
                    break 
        if bubble:
            break
    if bubble:
        graph = simplify_bubbles(solve_bubble(graph, noeud_ancetre, noeud))
    return graph


def solve_entry_tips(graph: DiGraph, starting_nodes: List[str]) -> DiGraph:
    """Remove entry tips

    :param graph: (nx.DiGraph) A directed graph object
    :param starting_nodes: (list) A list of starting nodes
    :return: (nx.DiGraph) A directed graph object
    """
    for node in starting_nodes:
        predecessors = list(graph.predecessors(node))
        if len(predecessors) > 1:
            for pred1, pred2 in combinations(predecessors, 2):
                common_ancestor = nx.lowest_common_ancestor(graph, pred1, pred2)
                if common_ancestor:
                    paths = list(nx.all_simple_paths(graph, common_ancestor, node))
                    if len(paths) > 1:
                        path_lengths = [len(path) for path in paths]
                        path_weights = [sum(d['weight'] for u, v, d in graph.subgraph(path).edges(data=True)) for path in paths]
                        graph = select_best_path(graph, paths, path_lengths, path_weights, delete_entry_node=True, delete_sink_node=False)
    return graph

def solve_out_tips(graph: DiGraph, ending_nodes: List[str]) -> DiGraph:
    """Remove out tips

    :param graph: (nx.DiGraph) A directed graph object
    :param ending_nodes: (list) A list of ending nodes
    :return: (nx.DiGraph) A directed graph object
    """
    bubble = False

    for noeud in graph.nodes:
        # Détermination des successeurs du nœud
        liste_successeurs = list(graph.successors(noeud))

        # Filtrage des successeurs pour garder uniquement ceux dans les exit_nodes
        liste_successeurs = [succ for succ in liste_successeurs if succ in ending_nodes]

        # Si un nœud a plusieurs successeurs dans les exit_nodes, il y a potentiellement une pointe
        if len(liste_successeurs) > 1:
            path_bool = False
            for end_node in ending_nodes:
                if has_path(graph, noeud, end_node):
                    paths = list(nx.all_simple_paths(graph, source=noeud, target=liste_successeurs[0]))
                    path_lengths = [len(path) for path in paths if len(path) >= 2]
                    path_weights = [path_average_weight(graph, path) for path in paths if len(path) >=2]
                    graph = select_best_path(graph, paths, path_lengths, path_weights, delete_entry_node=False, delete_sink_node=True)
    return graph

def get_starting_nodes(graph: DiGraph) -> List[str]:
    """Get nodes without predecessors

    :param graph: (nx.DiGraph) A directed graph object
    :return: (list) A list of all nodes without predecessors
    """
    return [node for node in graph.nodes if not list(graph.predecessors(node))]


def get_sink_nodes(graph: DiGraph) -> List[str]:
    """Get nodes without successors

    :param graph: (nx.DiGraph) A directed graph object
    :return: (list) A list of all nodes without successors
    """
    return [node for node in graph.nodes if not list(graph.successors(node))]


def get_contigs(
    graph: DiGraph, starting_nodes: List[str], ending_nodes: List[str]
) -> List:
    """Extract the contigs from the graph

    :param graph: (nx.DiGraph) A directed graph object
    :param starting_nodes: (list) A list of nodes without predecessors
    :param ending_nodes: (list) A list of nodes without successors
    :return: (list) List of [contiguous sequence and their length]
    """
    contigs = []
    for start in starting_nodes:
        for end in ending_nodes:
            if has_path(graph, start, end):
                for path in all_simple_paths(graph, start, end):
                    contig = path[0]
                    for node in path[1:]:
                        contig += node[-1] 
                    contigs.append((contig, len(contig)))
    return contigs


def save_contigs(contigs_list: List[str], output_file: Path) -> None:
    """Write all contigs in fasta format

    :param contig_list: (list) List of [contiguous sequence and their length]
    :param output_file: (Path) Path to the output file
    """
    with output_file.open("w") as f:
        for i, (contig, length) in enumerate(contigs_list):
            f.write(f">contig_{i} len={length}\n")
            f.write(textwrap.fill(contig, width=80) + "\n")


def draw_graph(graph: DiGraph, graphimg_file: Path) -> None:  # pragma: no cover
    """Draw the graph

    :param graph: (nx.DiGraph) A directed graph object
    :param graphimg_file: (Path) Path to the output file
    """
    fig, ax = plt.subplots()
    elarge = [(u, v) for (u, v, d) in graph.edges(data=True) if d["weight"] > 3]
    # print(elarge)
    esmall = [(u, v) for (u, v, d) in graph.edges(data=True) if d["weight"] <= 3]
    # print(elarge)
    # Draw the graph with networkx
    # pos=nx.spring_layout(graph)
    pos = nx.random_layout(graph)
    nx.draw_networkx_nodes(graph, pos, node_size=6)
    nx.draw_networkx_edges(graph, pos, edgelist=elarge, width=6)
    nx.draw_networkx_edges(
        graph, pos, edgelist=esmall, width=6, alpha=0.5, edge_color="b", style="dashed"
    )
    # nx.draw_networkx(graph, pos, node_size=10, with_labels=False)
    # save image
    plt.savefig(graphimg_file.resolve())


# ==============================================================
# Main program
# ==============================================================
def main() -> None:  # pragma: no cover
    """
    Main program function
    """
    args = get_arguments()
    kmer_dict = build_kmer_dict(args.fastq_file, args.kmer_size)
    graph = build_graph(kmer_dict)
    starting_nodes = get_starting_nodes(graph)
    ending_nodes = get_sink_nodes(graph)
    graph = simplify_bubbles(graph)
    starting_nodes = get_starting_nodes(graph)
    ending_nodes = get_sink_nodes(graph)
    graph = solve_entry_tips(graph, starting_nodes)
    starting_nodes = get_starting_nodes(graph)
    ending_nodes = get_sink_nodes(graph)
    graph = solve_out_tips(graph, ending_nodes)
    starting_nodes = get_starting_nodes(graph)
    ending_nodes = get_sink_nodes(graph)
    contigs = get_contigs(graph, starting_nodes, ending_nodes)
    save_contigs(contigs, args.output_file)
    if args.graphimg_file:
        draw_graph(graph, args.graphimg_file)
    save_contigs([('AACC',4),('TGTGTGTG',8)],"data/test.fasta")

if __name__ == "__main__":  # pragma: no cover
    main()
