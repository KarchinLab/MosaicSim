import psutil
import os
import msprime
import tskit
import numpy as np
import gzip
import glob
import string
import random
import time
import pickle
import sys
import pandas as pd
from Bio import SeqIO
from datasketch import *
import math
import re
# from parameters import *
import argparse
import yaml
from collections import defaultdict


def getmemory():
    process = psutil.Process(os.getpid())
    print(process.memory_info().rss)


GLOBAL_CHROM_NUM = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21,
                    22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45]

def getSVSize(chromosome_size = 1e8):
    # chromosome_size = 10 # for testing
    return_val1 = np.random.negative_binomial(0.1, 0.0001)
    return_val2 = np.random.negative_binomial(1, 0.00001)
    return_val3 = np.random.negative_binomial(200, 0.00002) 
    zed = random.random()
    if(zed < 0.5): 
        o_return_val = return_val1
    elif(zed > 0.5 and zed < 0.995):
        o_return_val = return_val2
    else: 
        o_return_val = return_val3
    if (o_return_val < 50): 
        return 50
    elif(o_return_val > 2e7): 
        return 2e7
    else: 
        return int((chromosome_size/1e8)*o_return_val)

def getDirichletCloneFromDistn(num_clones, alpha_dir, the_distn):
    cumulate_product = 1.0
    current_weights = []
    ep = 0.001
    epsil = 1-ep
    tot = 0.0
    while(tot < epsil):
        beta = random.betavariate(1, alpha_dir)
        pi_app = beta*cumulate_product
        cumulate_product = cumulate_product * (1-beta)
        current_weights.append(pi_app)
        tot += pi_app
    sum_current_weights = sum(current_weights)
    weights = []
    for i in current_weights:
        weights.append(i/sum_current_weights)
    print(weights)
    distn = [0.0]*(num_clones+1)
    for i in weights:
        all_choices = list(range(num_clones+1))
        pos = random.choices(all_choices, weights=the_distn)[0]
        distn[pos] = distn[pos] + i
    return distn


def getKmers(sequence, size):
    return {sequence[x:x+size].upper() for x in range(len(sequence) - size + 1)}

def getDirichletClone(num_clones, alpha_dir):
    cumulate_product = 1.0
    current_weights = []
    ep = 0.001
    epsil = 1-ep
    tot = 0.0
    while(tot < epsil):
        beta = random.betavariate(1, alpha_dir)
        pi_app = beta*cumulate_product
        cumulate_product = cumulate_product * (1-beta)
        current_weights.append(pi_app)
        tot += pi_app
    sum_current_weights = sum(current_weights)
    weights = []
    for i in current_weights:
        weights.append(i/sum_current_weights)
    distn = [0.0]*(num_clones+1)
    for i in weights:
        pos = random.randint(0, num_clones)
        distn[pos] = distn[pos] + i
    return distn


def pickdclone(prob_list, num_clones):
    return np.random.choice(np.arange(num_clones+1), p=prob_list)


def SNPSig(seqs):
    c = list(range(len(seqs)))
    chrom = random.sample(c, 1)
    seq = seqs[chrom[0]]
    target = GLOBAL_CHROM_NUM[chrom[0]]
    signature_drawn_dist = getDirichletCloneFromDistn(
        num_signatures-1, signature_alpha, signature_distributions)
    signature_drawn = pickdclone(
        signature_drawn_dist, len(signature_drawn_dist)-1)
    distribution_over_mutations = list(signatures_matrix[:, signature_drawn])
    position = pickdclone(distribution_over_mutations,
                          len(distribution_over_mutations)-1)
    pos = 0
    first_letter = int(position/24)
    last_letter = position % 24 % 4  # if == 0 > A if 1 > C if 2 > G if 3 >T
    middle_two = int((position % 24)/4)
    if random.random() < 0.5:
        fullstring = list_of_bases[first_letter] + \
            list_of_pairs[middle_two][0] + list_of_bases[last_letter]
        mutated_base = list_of_pairs[middle_two][1]
        indices = [m.start() for m in re.finditer(fullstring, seq)]
        if(len(indices) > 0):
            pos = random.choice(indices)+1
            seq = seq[:pos] + mutated_base + seq[pos+1:]
        else:
            pos = -1
    else:
        altstring = list_of_bases[first_letter] + \
            list_of_pairs[middle_two][0].translate(
                tab) + list_of_bases[last_letter]
        mutated_base = list_of_pairs[middle_two][1].translate(tab)
        indices = [m.start() for m in re.finditer(altstring, seq)]
        if(len(indices) > 0):
            pos = random.choice(indices)+1
            seq = seq[:pos] + mutated_base + seq[pos+1:]
        else:
            pos = -1
    seqs[chrom[0]] = seq
    return [-1], [pos, chrom[0], target, pos+1, numchrommap[target]]


def speedSNP(seqs):
    BASES = ['A', 'C', 'T', 'G']
    c = list(range(len(seqs)))
    chrom = random.sample(c, 1)
    seq = seqs[chrom[0]]
    target = GLOBAL_CHROM_NUM[chrom[0]]
    n = len(seq)
    pos = 0
    all_positions = []
    if (n == 0):
        return [-1], [-1, chrom[0]]
    elif(n == 1):
        n_repeats = 1
        all_positions = [0]
        for i in range(n_repeats):
            oldseq = seq
            char = oldseq[pos]
            while(char == seq[pos]):
                char = random.choice(BASES)
            seq = seq[:0]+char
    else:
        n_repeats = 1
        for i in range(n_repeats):
            pos = random.randint(0, n-1)
            all_positions.append(pos)
            oldseq = seq
            char = oldseq[pos]
            while(char == seq[pos]):
                char = random.choice(BASES)
            seq = seq[:pos] + char + seq[pos+1:]
    seqs[chrom[0]] = seq
    return [-1], [pos, chrom[0], target, pos+1, numchrommap[target]]


def insertionsmall(seqs):
    c = list(range(len(seqs)))
    chrom = random.sample(c, 1)
    target = GLOBAL_CHROM_NUM[chrom[0]]
    BASES = ['A', 'C', 'T', 'G']
    seq = seqs[chrom[0]]
    n = len(seq)
    pos = random.randint(0, n)
    number_of_bases_to_insert = random.randint(1, 15)
    ins_str = ''
    ins_list = [pos]*number_of_bases_to_insert
    for i in range(number_of_bases_to_insert):
        ins_str = ins_str + random.choice(BASES)
    new_seq = seq[:pos] + ins_str + seq[pos:]
    seqs[chrom[0]] = new_seq
    return [ins_str], [pos, number_of_bases_to_insert, chrom[0], target, pos+1, numchrommap[target]]


def deletionsmall(seqs):
    c = list(range(len(seqs)))
    chrom = random.sample(c, 1)
    seq = seqs[chrom[0]]
    target = GLOBAL_CHROM_NUM[chrom[0]]
    oldseq = seq
    n = len(seq)
    pos = 0
    if (n == 0):
        pos = -1
    elif (n == 1):
        pos = 0
    else:
        pos = random.randint(0, n-1)
    deletion_range = random.randint(1, 15)
    new_seq = seq[:pos] + seq[pos+deletion_range:]
    seqs[chrom[0]] = new_seq
    position = int(pos)
    chromosome = int(chrom[0])
    return [-1], [position, deletion_range, chromosome, target, position+1, numchrommap[target]]


def CNV(seqs):
    c = list(range(len(seqs)))
    chrom = random.sample(c, 1)
    seq = seqs[chrom[0]]
    target = GLOBAL_CHROM_NUM[chrom[0]]
    n = len(seq)
    if (n == 1 or n == 0):
        return[-1], [-1, chrom[0]]
    #lowbd = int(0.0001*n)
    #upbd = int(0.1*n)
    #dist = int(random.randint(lowbd, upbd))
    dist = n
    while(dist > 0.1*n):
        dist = getSVSize()
    stidx = random.randint(0, n-1)
    edidx = min(stidx + dist, n-1)
    max_reps = 5
    rep_num = random.randint(2, max_reps)
    subseq = seq[stidx:edidx]
    repeatedsubseq = subseq*rep_num
    start_string = seq[:stidx]
    end_string = seq[edidx:]
    full_string = start_string + repeatedsubseq + end_string
    seqs[chrom[0]] = full_string
    return [-1], [stidx, edidx, rep_num, chrom[0], target, stidx+1, edidx+1, numchrommap[target]]


def aneuploidy(seqs):
    c = list(range(len(seqs)))
    chrom = random.sample(c, 1)
    seq = seqs[chrom[0]]
    target = GLOBAL_CHROM_NUM[chrom[0]]
    max_reps = 3
    rep_num = random.randint(2, max_reps)
    if (random.random() < 0.2): 
        del seqs[chrom[0]]
    else: 
        for i in range(rep_num-1):
            GLOBAL_CHROM_NUM.append(target)
            seqs.append(seq)
    return [-1], [rep_num, chrom[0], target, numchrommap[target]]


def deletion(seqs):
    c = list(range(len(seqs)))
    chrom = random.sample(c, 1)
    target = GLOBAL_CHROM_NUM[chrom[0]]
    seq = seqs[chrom[0]]
    n = len(seq)
    if(n == 0):
        return [-1], [-1, chrom[0]]
    elif(n == 1):
        seqs[chrom[0]] = ''
        return [-1], [0, chrom[0], target]
    else:
        #lowbd = int(0.0001*n)
        #upbd = int(0.01*n)
        #dist = int(random.randint(lowbd, upbd))
        dist = n
        while(dist > 0.1*n):
            dist = getSVSize() 
        stidx = random.randint(0, n-1)
        edidx = min(stidx + dist, n-1)
        start_string = seq[:stidx]
        end_string = seq[edidx:]
        full_string = start_string + end_string
        seqs[chrom[0]] = full_string
        return [-1], [stidx, edidx, chrom[0], target, stidx+1, edidx+1, numchrommap[target]]


def inversion(seqs):
    c = list(range(len(seqs)))
    chrom = random.sample(c, 1)
    target = GLOBAL_CHROM_NUM[chrom[0]]
    seq = seqs[chrom[0]]
    n = len(seq)
    if (n == 0 or n == 1):
        return [-1], [-1, chrom[0]]
    #lowbd = int(0.0001*n)
    #upbd = int(0.1*n)
    #dist = int(random.randint(lowbd, upbd))
    dist = n
    while(dist > 0.1*n):
        dist = getSVSize() 
    stidx = random.randint(0, n-1)
    edidx = min(stidx + dist, n-1)
    subseq = seq[stidx:edidx]
    reversed_subseq = subseq[::-1]
    start_string = seq[:stidx]
    end_string = seq[edidx:]
    full_string = start_string + reversed_subseq + end_string
    seqs[chrom[0]] = full_string
    #lowbd = int(0.0001*n)
    #upbd = int(0.1*n)
    #dist = int(random.randint(lowbd, upbd))
    dist = n
    while(dist > 0.1*n):
        dist = getSVSize() 
    stidx = random.randint(0, n-1)
    edidx = min(stidx + dist, n-1)
    subseq = seq[stidx:edidx]
    reversed_subseq = subseq[::-1]
    start_string = seq[:stidx]
    end_string = seq[edidx:]
    full_string = start_string + reversed_subseq + end_string
    seqs[chrom[0]] = full_string
    return [-1], [stidx, edidx, chrom[0], target, stidx+1, edidx+1, numchrommap[target]]


def kataegis(seqs):
    c = list(range(len(seqs)))
    chrom = random.sample(c, 1)
    target = GLOBAL_CHROM_NUM[chrom[0]]
    seq = seqs[chrom[0]]
    n = len(seq)
    if (n == 0 or n == 1):
        return [-1], [-1, chrom[0]]
    #lowbd = int(0.1*n)
    #upbd = int(0.2*n)
    #dist = int(random.randint(lowbd, upbd))
    dist = n
    while(dist > 0.1*n):
        dist = getSVSize() 
    stidx = random.randint(0, n-1)
    edidx = min(stidx + dist, n-1)
    type_of_variation = random.randint(0, 2)
    subseq = seq[stidx:edidx]
    new_seq = ''
    if(type_of_variation == 0):
        def rand_replace(c): return 'T' if random.random(
        ) < 0.8 and c == 'C' else c
        new_seq = ''.join([rand_replace(c) for c in subseq])
    elif(type_of_variation == 1):
        def rand_replace(c): return 'A' if random.random(
        ) < 0.8 and c == 'C' else c
        new_seq = ''.join([rand_replace(c) for c in subseq])
    else:
        def rand_replace(c): return 'G' if random.random(
        ) < 0.8 and c == 'C' else c
        new_seq = ''.join([rand_replace(c) for c in subseq])
    start_string = seq[:stidx]
    end_string = seq[edidx:]
    full_string = start_string + new_seq + end_string
    # Pick mutational type
    seqs[chrom[0]] = full_string
    return [-1], [stidx, edidx, type_of_variation, chrom[0], target, stidx+1, edidx+1, numchrommap[target]]


def translocation(seqs):
    try:
        c = list(range(len(seqs)))
        chrom = random.sample(c, 2)
        seq1 = seqs[chrom[0]]
        seq2 = seqs[chrom[1]]
        target1 = GLOBAL_CHROM_NUM[chrom[0]]
        target2 = GLOBAL_CHROM_NUM[chrom[1]]
        l1 = len(seq1)
        l2 = len(seq2)
        bkpt1 = random.randint(0, l1-1)
        bkpt2 = random.randint(0, l1-1)
        rng_recip = random.random()
        if(rng_recip < 0.95):
            first_part = seq1[:bkpt1]
            second_part = seq1[bkpt1:]
            fp2 = seq2[:bkpt2]
            sp2 = seq2[bkpt2:]
            string1 = first_part + sp2
            string2 = fp2 + second_part
            seqs[chrom[0]] = string1
            seqs[chrom[1]] = string2
            return [-1], [bkpt1, bkpt2, 1, chrom[0], chrom[1], target1, target2, numchrommap[target1], numchrommap[target2]]
        else:
            first_part = seq1[:bkpt1]
            second_part = seq1[bkpt1:]
            fp2 = seq2[:bkpt2]
            sp2 = seq2[bkpt2:]
            string1 = first_part
            string2 = fp2 + sp2 + second_part
            seqs[chrom[0]] = string1
            seqs[chrom[1]] = string2
            return [-1], [bkpt1, bkpt2, 0, chrom[0], chrom[1], target1, target2, numchrommap[target1], numchrommap[target2]]
    except:
        return [-1], [-1]


def numpy_choices(seq_len, splits):
    breakpoints = np.random.choice(seq_len, splits-1, replace=False)
    breakpoints.sort()
    return breakpoints.tolist()


def numpy_permute(splits):
    return np.random.permutation(splits).tolist()


def chromothripsis(seqs):
    keep_frequency = random.random()
    c = list(range(len(seqs)))
    chrom = random.sample(c, 1)
    target = GLOBAL_CHROM_NUM[chrom[0]]
    orig_seq = seqs[chrom[0]]
    n = len(orig_seq)
    if (n == 0 or n == 1):
        return [-1], [-1, chrom[0]]
    NotLongEnough = True
    attempts = 0
    stidx = 0
    edidx = 0
    splits = 0
    while(NotLongEnough):
        splits = random.randint(2, 100)
        #lowbd = int(0.1*n)
        #upbd = int(0.9*n)
        #distance = int(random.randint(lowbd, upbd))
        dist = n
        while(dist > 0.1*n):
            dist = getSVSize()
        stidx = random.randint(0, n-1)
        edidx = min(stidx + dist, n-1)
        dist = edidx - stidx
        attempts += 1
        if(dist > splits):
            NotLongEnough = False
            break
        if(attempts > 10):
            return [-1], [-1, chrom[0]]
    first_part = orig_seq[:stidx]
    last_part = orig_seq[edidx:]
    seq = orig_seq[stidx:edidx]
    seq_len = len(seq)
    breakpoints = numpy_choices(seq_len, splits)
    subseq = []
    curridx = 0
    for i in breakpoints:
        subseq.append(seq[curridx:i])
        curridx = i
    subseq.append(seq[breakpoints[-1]:])
    rearrange = numpy_permute(splits)
    n_to_select = int(splits * keep_frequency)
    n_to_select = len(rearrange)
    rearrange = random.sample(list(rearrange), n_to_select)
    build_seq = ''
    for i in rearrange:
        build_seq += subseq[i]
    seqs[chrom[0]] = first_part + build_seq + last_part
    breakpoints = list(breakpoints)
    return [-1], [stidx, edidx, splits, chrom[0], target, stidx+1, edidx+1, numchrommap[target]]


def BFB(seqs):
    try:
        n_repeats = random.randint(2, 4)
        c = list(range(len(seqs)))
        chrom = random.sample(c, 1)
        target = GLOBAL_CHROM_NUM[chrom[0]]
        seq = seqs[chrom[0]]
        curr_seq = seq
        all_bkpt = []
        for i in range(n_repeats):
            bkpoint = random.randint(1, len(curr_seq)-2)
            all_bkpt.append(bkpoint)
            first_portion = curr_seq[:bkpoint]
            next_portion = first_portion[::-1]
            curr_seq = first_portion + next_portion
        seqs[chrom[0]] = curr_seq
        return all_bkpt, [n_repeats, chrom[0], target, numchrommap[target]]
    except:
        return [-1], [-1]


def getsummation(seq_len, splits):
    breakpoints = np.random.choice(seq_len, splits-1, replace=False)
    breakpoints.sort()
    zed = breakpoints.tolist()
    new_list = []
    idx = 0
    for i in zed:
        new_list.append(i-idx)
        idx = i
    new_list.append(seq_len - idx)
    return new_list
# this is the slowest one, understandably


def chromoplexy(seqs):
    try:
        n_chroms = random.randint(2, 6)
        c = list(range(len(seqs)))
        chrom = random.sample(c, n_chroms)
        list_of_start_tels = []
        list_of_end_tels = []
        middle_segs = []
        total_splits = 0
        for i in range(n_chroms):
            curr_sequence = seqs[chrom[i]]
            num_splits = random.randint(2, 20)
            breakpoints = numpy_choices(len(curr_sequence), num_splits)
            total_splits += num_splits
            curridx = 0
            for i in breakpoints[1:]:
                middle_segs.append(curr_sequence[curridx:i])
                curridx = i
            list_of_end_tels.append(curr_sequence[breakpoints[-1]:])
            list_of_start_tels.append(curr_sequence[0:breakpoints[0]])
        usable_splits = total_splits - 2*(n_chroms)
        splitter = getsummation(usable_splits, n_chroms)
        for i in range(len(splitter)):
            build_str = list_of_start_tels.pop(
                random.randrange(len(list_of_start_tels)))
            for segs in range(splitter[i]):
                build_str = build_str + \
                    middle_segs.pop(random.randrange(len(middle_segs)))
            build_str = build_str + \
                list_of_end_tels.pop(random.randrange(len(list_of_end_tels)))
            seqs[chrom[i]] = build_str
        return [-1], [total_splits, n_chroms]
    except:
        return [-1], [-1]


def generateMatrix(the_matrix, list_of_weights, time_matrix):
    rate_matrix = getRateMatrix(time_matrix, list_of_weights)
    pop = time_matrix.shape[0]
    avg_rate = 0.0
    num_rates = 0
    for i in range(pop):
        for j in range(pop):
            if(time_matrix[i, j] != 0):
                time = 0
                list_of_times = []
                while(time < time_matrix[i, j]):
                    num_rates += 1
                    avg_rate += rate_matrix[i, j]
                    mutations_per_branch = rate_matrix[i, j]*time_matrix[i, j]
                    wait_time = np.random.exponential(1/rate_matrix[i, j])
                    time += wait_time
                    if(time < time_matrix[i, j]):
                        list_of_times.append(time)
                the_matrix[i, j] = list_of_times
    avg_rate = avg_rate/num_rates
    return the_matrix, avg_rate


def getTree(num_clones, pop, working_dir, tree_seed):
    tree_sequence = msprime.simulate(
        sample_size=num_clones, Ne=pop, recombination_rate=0, random_seed=tree_seed)
    tree_sequence.dump(working_dir + '/tree_sequence.tree')
    tree = tree_sequence.first()
    return tree


def getPaths(tree, num_clones):
    list_of_paths = []
    time_matrix = np.zeros((tree.root + 1, tree.root+1))
    for u in range(num_clones):
        path = []
        while u != tskit.NULL:
            path.insert(0, u)
            time_matrix[u, tree.parent(u)] = tree.get_branch_length(u)
            u = tree.parent(u)
        list_of_paths.append(path)
    time_matrix = np.transpose(time_matrix)
    return list(list_of_paths)


def getTimeMatrix(tree, num_clones):
    time_matrix = np.zeros((tree.root + 1, tree.root+1))
    dep = 0
    for u in range(num_clones):
        while u != tskit.NULL:
            time_matrix[u, tree.parent(u)] = tree.get_branch_length(u)
            dep += tree.get_branch_length(u)
            u = tree.parent(u)
    time_matrix = np.transpose(time_matrix)
    return time_matrix, dep


def getRateMatrix(time_matrix, list_of_weights):
    the_shape = np.shape(time_matrix)[0]
    rate_matrix = np.zeros((the_shape, the_shape))
    for i in range(the_shape):
        for j in range(the_shape):
            if(time_matrix[i, j] > 0):
                rate_matrix[i, j] = np.random.choice(list_of_weights)
    return rate_matrix


def generateOrder(tree, time_matrix, list_of_rates):
    pop = time_matrix.shape[0]
    SNV_matrix = np.zeros((pop, pop), dtype=object)
    CNV_matrix = np.zeros((pop, pop), dtype=object)
    DELETION_matrix = np.zeros((pop, pop), dtype=object)
    DELETIONSMALL_matrix = np.zeros((pop, pop), dtype=object)
    INVERSION_matrix = np.zeros((pop, pop), dtype=object)
    TRANSLOCATION_matrix = np.zeros((pop, pop), dtype=object)
    BFB_matrix = np.zeros((pop, pop), dtype=object)
    CHROMOTHRIPSIS_matrix = np.zeros((pop, pop), dtype=object)
    CHROMOPLEXY_matrix = np.zeros((pop, pop), dtype=object)
    INSERTIONSMALL_matrix = np.zeros((pop, pop), dtype=object)
    KATAEGIS_matrix = np.zeros((pop, pop), dtype=object)
    ANEUPLOIDY_matrix = np.zeros((pop, pop), dtype=object)
    SNV_matrix, snv_rate = generateMatrix(
        SNV_matrix, list_of_rates[0], time_matrix)
    CNV_matrix, cnv_rate = generateMatrix(
        CNV_matrix, list_of_rates[1], time_matrix)
    DELETION_matrix, deletion_rate = generateMatrix(
        DELETION_matrix, list_of_rates[2], time_matrix)
    DELETIONSMALL_matrix, delsmall_rate = generateMatrix(
        DELETIONSMALL_matrix, list_of_rates[3], time_matrix)
    INVERSION_matrix, inv_rate = generateMatrix(
        INVERSION_matrix, list_of_rates[4], time_matrix)
    TRANSLOCATION_matrix, trans_rate = generateMatrix(
        TRANSLOCATION_matrix, list_of_rates[5], time_matrix)
    BFB_matrix, bfb_rate = generateMatrix(
        BFB_matrix, list_of_rates[6], time_matrix)
    CHROMOTHRIPSIS_matrix, chromothripsis_rate = generateMatrix(
        CHROMOTHRIPSIS_matrix, list_of_rates[7], time_matrix)
    CHROMOPLEXY_matrix, chromoplexy_rate = generateMatrix(
        CHROMOPLEXY_matrix, list_of_rates[8], time_matrix)
    INSERTIONSMALL_matrix, inssmall_rate = generateMatrix(
        INSERTIONSMALL_matrix, list_of_rates[9], time_matrix)
    KATAEGIS_matrix, kat_rate = generateMatrix(
        KATAEGIS_matrix, list_of_rates[10], time_matrix)
    ANEUPLOIDY_matrix, an_rate = generateMatrix(
        ANEUPLOIDY_matrix, list_of_rates[11], time_matrix)
    mutationedge_list = []
    fin_rate_list = [snv_rate, cnv_rate, deletion_rate, delsmall_rate, inv_rate, trans_rate,
                     bfb_rate, chromothripsis_rate, chromoplexy_rate, inssmall_rate, kat_rate, an_rate]
    for i in range(pop-1):
        # gives mutations from i to its parent ONLY
        parent_node = tree.parent(i)
        l1 = SNV_matrix[parent_node, i]
        l2 = CNV_matrix[parent_node, i]
        l3 = DELETION_matrix[parent_node, i]
        l4 = DELETIONSMALL_matrix[parent_node, i]
        l5 = INVERSION_matrix[parent_node, i]
        l6 = TRANSLOCATION_matrix[parent_node, i]
        l7 = BFB_matrix[parent_node, i]
        l8 = CHROMOTHRIPSIS_matrix[parent_node, i]
        l9 = CHROMOPLEXY_matrix[parent_node, i]
        l10 = INSERTIONSMALL_matrix[parent_node, i]
        l11 = KATAEGIS_matrix[parent_node, i]
        l12 = ANEUPLOIDY_matrix[parent_node, i]
        merged_list = l1+l2+l3+l4+l5+l6+l7+l8+l9+l10
        merged_list.sort()
        ordered_muts = []
        for k in merged_list:
            if(k in l1):
                ordered_muts.append(0)
            elif(k in l2):
                ordered_muts.append(1)
            elif(k in l3):
                ordered_muts.append(2)
            elif(k in l4):
                ordered_muts.append(3)
            elif(k in l5):
                ordered_muts.append(4)
            elif(k in l6):
                ordered_muts.append(5)
            elif(k in l7):
                ordered_muts.append(6)
            elif(k in l8):
                ordered_muts.append(7)
            elif(k in l9):
                ordered_muts.append(8)
            elif(k in l10):
                ordered_muts.append(9)
            elif(k in l11):
                ordered_muts.append(10)
            elif(k in l12):
                ordered_muts.append(11)
            else:
                print('error no mut match')
        print(ordered_muts)
        mutationedge_list.append(ordered_muts)
    return list(mutationedge_list), list(fin_rate_list)


def wgz(floc, ob):
    with open(floc, 'w') as f:
        for i in ob:
            f.write(f'{i}\n')


def rgz(floc):
    return_list = []
    with open(floc, 'r') as file:
        return_list = [line.strip() for line in file]
    return return_list


def applyMutations(tot_nodes, working_dir, list_of_paths, use_signatures, mutationedge_list):
    d = {}
    infos = {}
    muts = {}
    for i in range(tot_nodes):
        d[i] = 'na'
    d[tot_nodes-1] = working_dir + str(tot_nodes - 1) + '.gz'
    infos[tot_nodes - 1] = []
    muts[tot_nodes - 1] = []
    for path in list_of_paths:
        print(path)
        for i in range(len(path)-1):
            if(d[path[i+1]] == 'na'):
                current_genome = []
                current_genome = rgz(d[path[i]])
                c_infos = infos[path[i]].copy()
                c_muts = muts[path[i]].copy()
                current_muts = mutationedge_list[path[i+1]]
                for k in current_muts:
                    info = []
                    if(k == 0):
                        if(use_signatures):
                            _, info = SNPSig(current_genome)
                        else:
                            _, info = speedSNP(current_genome)
                    elif(k == 1):
                        _, info = CNV(current_genome)
                    elif(k == 2):
                        _, info = deletion(current_genome)
                    elif(k == 3):
                        _, info = deletionsmall(current_genome)
                    elif(k == 4):
                        _, info = inversion(current_genome)
                    elif(k == 5):
                        _, info = translocation(current_genome)
                    elif(k == 6):
                        _, info = BFB(current_genome)
                    elif(k == 7):
                        _, info = chromothripsis(current_genome)
                    elif(k == 8):
                        _, info = chromoplexy(current_genome)
                    elif(k == 9):
                        _, info = insertionsmall(current_genome)
                    elif(k == 10):
                        _, info = kataegis(current_genome)
                    elif(k == 11):
                        _, info = aneuploidy(current_genome)
                    else:
                        print('invalid')
                    c_infos.append(info)
                    c_muts.append(k)
                d[path[i+1]] = working_dir + str(path[i+1]) + '.gz'
                '''
				with gzip.open(working_dir + str(path[i+1])+'.gz', 'wb0') as y: 
					pickle.dump(current_genome, y)
				'''
                wgz(working_dir + str(path[i+1]) + '.gz', current_genome)
                infos[path[i+1]] = c_infos
                muts[path[i+1]] = c_muts
            else:
                donothing = 1
    return infos, muts


def clear_dir(working_dir):
    files = glob.glob(working_dir+'*')
    for f in files:
        os.remove(f)


def pickClone(num_clones, dir_conc):
    alpha_dir = np.tile(dir_conc, num_clones)
    distribution = np.random.dirichlet(alpha_dir)
    clone_picked = np.random.choice(range(0, num_clones), p=distribution)
    return int(clone_picked)


def writeToFasta(file_loc, curr_string):
    import random
    with open(file_loc, 'at') as f:
        f.write(curr_string)


def getfrag(r):
    return_val = 0
    while(return_val < r-20):
        return_val = np.random.negative_binomial(r, 0.5)
    return return_val


def drawPoisson(r):
    return_val = 0
    return np.random.poisson(r)


def getDNAchunk(length, seqs):
    c = list(range(len(seqs)))
    chrom = random.sample(c, 1)
    seq = seqs[chrom[0]]
    n = len(seq)
    stidx = random.randint(0, n-1)
    edidx = stidx + length
    subseq = seq[stidx:edidx]
    return subseq


def mutateFrag(frag, err_rate):
    num_muts = 0
    s = str(frag)
    n = len(frag)
    q = 1-err_rate
    if (err_rate > 0.1):
        num_muts = int(random.gauss(n*err_rate, n*err_rate*q))
    else:
        num_muts = drawPoisson(n*err_rate)
    BASES = ['A', 'C', 'T', 'G']
    for i in range(num_muts):
        pos = random.randint(0, n-1)
        oldseq = s
        char = oldseq[pos]
        while(char == s[pos]):
            char = random.choice(BASES)
        s = s[:pos] + char + s[pos+1:]
    return s


def split(string, length):
    return (string[0+i:length+i] for i in range(0, len(string), length))


def revc(sequence):
    return sequence.translate(tab)[::-1]


def runSim(num_clones, coverage, rl, read_loc, floc, batch, root, alpha, erate, flag=0):
    if(flag == 0):
        f = open(floc + 'bulk.fasta', 'w')
    elif(flag == 1):
        f = open(floc + 'ref.fasta', 'w')
    else:
        randid = random_str = ''.join(random.choice(
            string.ascii_lowercase) for _ in range(3))
        f = open(floc + f'singlecell.fasta', 'w')
    cov = 0.0
    ratio = rl
    #random_str = 0
    ls = []
    if(flag == 2):
        ri = random.randint(0, num_clones)
        ls = rgz(f'{read_loc}{ri}.gz')
    if(flag == 1):
        ls = rgz(f'{read_loc}{root}.gz')
    giga_list = []
    while(cov < coverage):
        for i in range(batch):
            distn = getDirichletClone(num_clones, alpha)
            clone = pickdclone(distn, num_clones)
            if(flag == 0):
                ls = rgz(f'{read_loc}{clone}.gz')
            for chrom in ls:
                frag_len = 0
                while(frag_len <= rl):
                    frag_len = getfrag(rl)
                if random.random() < 0.5:
                    altchrom = chrom
                else:
                    altchrom = revc(chrom)
                for sub in split(altchrom, frag_len):
                    random_str = ''.join(random.choices(
                        string.ascii_letters, k=15))
                    sub = mutateFrag(sub, erate)  # check type here
                    qual = 'K'*len(sub)
                    giga_list.extend([f'@{random_str}', str(sub), '+', qual])
        for x in giga_list:
            f.write(x)
            f.write('\n')
        giga_list.clear()
        print('first batch write done')
        # f.write('\n'.join(giga_list))
        cov += 2*batch
        #del giga_list
    del giga_list
    del ls


def runPairedSim(num_clones, coverage, rl, fl, read_loc, floc, batch, root, alpha, erate, purity=1, flag=0):
    if(flag == 0):
        f = open(floc + 'bulkleft.fasta', 'w')
        f2 = open(floc + 'bulkright.fasta', 'w')
    elif(flag == 1):
        f = open(floc + 'refleft.fasta', 'w')
        f2 = open(floc + 'refright.fasta', 'w')
    else:
        randid = random_str = ''.join(
            random.choices(string.ascii_lowercase, k=4))
        f = open(floc + f'singlecellleft.fasta', 'w')
        f2 = open(floc + f'singlecellright.fasta', 'w')
    cov = 0.0
    ref_cov = coverage * (1 - purity - random.randint(0,10)/200)
    ratio = 2*rl/fl
    #random_str = 0
    ls = []
    if(flag == 2):
        ri = random.randint(0, num_clones)
        ls = rgz(f'{read_loc}{ri}.gz')
    if(flag == 1):
        ls = rgz(f'{read_loc}{root}.gz')
    giga_list = []
    giga_list2 = []
    clone_proportion_dict = defaultdict(int)
    while(cov < coverage):
        for i in range(batch):
            distn = getDirichletClone(num_clones, alpha)
            clone = pickdclone(distn, num_clones)
            if(flag == 0):
                if cov > ref_cov:
                    ls = rgz(f'{read_loc}{clone}.gz')
                    clone_proportion_dict[clone] += 1
                else:
                    ls = rgz(f'{read_loc}{root}.gz')
                    clone_proportion_dict[root] += 1
            for chrom in ls:
                frag_len = 0
                while (frag_len <= rl):
                    frag_len = getfrag(fl)
                if random.random() < 0.5:
                    altchrom = chrom
                else:
                    altchrom = revc(chrom)
                for sub in split(altchrom, frag_len):
                    random_str = ''.join(random.choices(
                        string.ascii_letters, k=15))
                    #sub = mutateFrag(sub, erate)
                    write1 = sub[:rl]
                    write2 = revc(sub[-rl:])
                    write1 = mutateFrag(write1, erate)
                    write2 = mutateFrag(write2, erate)
                    qual = 'K'*len(write1)
                    qual2 = 'K'*len(write2)
                    giga_list.extend([f'@{random_str}', write1, '+', qual])
                    giga_list2.extend(
                        [f'@{random_str}', write2, '+', qual2])
        for x in giga_list:
            f.write(x)
            f.write('\n')
        for x in giga_list2:
            f2.write(x)
            f2.write('\n')
        giga_list.clear()
        giga_list2.clear()
        print('first batch write done')
        cov += 2*batch*ratio
    
    if (flag == 0):
        total_num = sum(clone_proportion_dict.values())
        cpFile = open('{}clone_proportion.txt'.format(floc), 'w')
        for cloneKey in sorted(clone_proportion_dict.keys(), reverse=True):
            cloneProp = clone_proportion_dict[cloneKey] / total_num
            cpFile.write("{}\t{:.2f}\n".format(cloneKey, cloneProp))
        cpFile.close()

    del giga_list
    del giga_list2
    del ls

def get_random_str(main_str, substr_len):
    if(len(main_str) < substr_len): 
        return main_str, 0
    else: 
        idx = random.randrange(0, len(main_str) - substr_len + 1)
        return main_str[idx : (idx+substr_len)], idx


def exonrunSim(num_clones, coverage, rl, rloc, floc, batch, root, exonDict, numchrommap, subblock, alpha, erate, flag=0):
    if(flag == 0):
        f = open(floc + 'bulk.fasta', 'w')
    elif(flag == 1):
        f = open(floc + 'ref.fasta', 'w')
    else:
        randid = random_str = ''.join(random.choice(
            string.ascii_lowercase) for _ in range(3))
        f = open(floc + f'singlecell.fasta', 'w')
    cov = 0.0
    ratio = rl
    #random_str = 0
    ls = []
    if(flag == 2):
        ri = random.randint(0, num_clones)
        ls = rgz(f'{rloc}{ri}.gz')
    if(flag == 1):
        ls = rgz(f'{rloc}{root}.gz')
    giga_list = []
    while(cov < coverage):
        for i in range(batch):
            distn = getDirichletClone(num_clones, alpha)
            clone = pickdclone(distn, num_clones)
            if(flag == 0):
                ls = rgz(f'{rloc}{clone}.gz')
            chromnum = 0
            for chrom in ls:
                frag_len = 0
                while(frag_len <= rl):
                    frag_len = getfrag(rl)
                if random.random() < 0.5:
                    altchrom = chrom
                else:
                    altchrom = revc(chrom)
                for interval in exonDict[numchrommap[chromnum]]:
                    for i in range(subblock):
                        startindex = random.randint(interval[0], interval[1])
                        sub = altchrom[startindex:startindex+rl]
                        qual = 'K'*len(sub)
                        random_str = ''.join(random.choices(
                            string.ascii_letters, k=15))
                        sub = mutateFrag(sub, erate)
                        giga_list.extend([f'@{random_str}', sub, '+', qual])
                chromnum += 1
        for x in giga_list:
            f.write(x)
            f.write('\n')
        giga_list.clear()
        print('first batch write done')
        cov += 2*batch*subblock
    del giga_list


def exonrunPairedSim(num_clones, coverage, rl, fl, rloc, floc, batch, root, exonDict, numchrommap, subblock, alpha, erate, flag=0):
    if(flag == 0):
        f = open(floc + 'bulkleft.fasta', 'w')
        f2 = open(floc + 'bulkright.fasta', 'w')
    elif(flag == 1):
        f = open(floc + 'refleft.fasta', 'w')
        f2 = open(floc + 'refright.fasta', 'w')
    else:
        randid = random_str = ''.join(
            random.choices(string.ascii_lowercase, k=4))
        f = open(floc + f'singlecellleft.fasta', 'w')
        f2 = open(floc + f'singlecellright.fasta', 'w')
    cov = 0.0
    ratio = 2*rl/fl
    #random_str = 0
    ls = []
    if(flag == 2):
        ri = random.randint(0, num_clones)
        ls = rgz(f'{rloc}{ri}.gz')
    if(flag == 1):
        ls = rgz(f'{rloc}{root}.gz')
    giga_list = []
    giga_list2 = []
    clone_proportion_dict = defaultdict(int)
    while(cov < coverage):
        for i in range(batch):
            distn = getDirichletClone(num_clones, alpha)
            # print(distn)
            clone = pickdclone(distn, num_clones)
            # print(clone)
            if(flag == 0):
                ls = rgz(f'{rloc}{clone}.gz')
                clone_proportion_dict[clone] += 1
            chromnum = 0
            for chrom in ls:
                frag_len = 0
                while(frag_len <= rl):
                    frag_len = getfrag(fl)
                if random.random() < 0.5:
                    altchrom = chrom
                else:
                    altchrom = revc(chrom)
                for interval in exonDict[numchrommap[chromnum]]:
                    for i in range(subblock):
                        startindex = random.randint(interval[0], interval[1]) # MODIFY -#
                        sub = altchrom[startindex:startindex+fl]
                        random_str = ''.join(random.choices(
                            string.ascii_letters, k=15))
                        qual1 = 'K'*len(sub[:rl])
                        qual2 = 'K'*len(sub[-rl:])
                        #sub = mutateFrag(sub, erate)
                        pair1 = mutateFrag(sub[:rl], erate)
                        pair2 = mutateFrag(revc(sub[-rl:]), erate)
                        giga_list.extend(
                            [f'@{random_str}', pair1, '+', qual1])
                        giga_list2.extend(
                            [f'@{random_str}', pair2, '+', qual2])
                chromnum += 1
        for x in giga_list:
            f.write(x)
            f.write('\n')
        for x in giga_list2:
            f2.write(x)
            f2.write('\n')
        giga_list.clear()
        giga_list2.clear()
        print('first batch write done')
        cov += 2*batch*subblock*ratio
    
    if (flag == 0):
        total_num = sum(clone_proportion_dict.values())
        cpFile = open('{}clone_proportion.txt'.format(floc), 'w')
        for cloneKey in sorted(clone_proportion_dict.keys(), reverse=True):
            cloneProp = clone_proportion_dict[cloneKey] / total_num
            cpFile.write("{}\t{:.2f}\n".format(cloneKey, cloneProp))
        cpFile.close()
    del giga_list
    del giga_list2


def makedir(loc):
    try:
        os.mkdir(loc)
    except:
        pass
    return 0


def lbrunSim(num_tumors, num_clones_list, coverage, base_dir, floc, root, alpha, ctdna_frac, batchsize):
    f = open(floc + 'liquid_biopsyfull.fasta', 'w')
    ls = []
    ls = rgz(f'{base_dir}reference/{root}.gz')
    cfdna_frag = []
    ctdna_frag = []
    tot_clones = 0
    for i in num_clones_list:
        tot_clones += i
    distn = getDirichletClone(tot_clones, alpha)
    frags_per_clone = int(10e7/tot_clones)
    for i in range(tot_clones):
        tnum = random.randint(0, num_tumors-1)
        num_clones = num_clones_list[tnum]
        clone = pickdclone(distn, num_clones)
        thechrom = rgz(base_dir + f'tumor_{tnum}/{clone}.gz')
        for j in range(frags_per_clone):
            l = getfrag(133)
            ctdna_frag.append(getDNAchunk(l, thechrom))
    thechrom = rgz(base_dir + f'reference/{root}.gz')
    for i in range(int(9e7)):
        l = getfrag(166)
        cfdna_frag.append(getDNAchunk(l, thechrom))
    total_frags_needed = int(3e9/150)*coverage
    frags_from_tumor = int(ctdna_frac*total_frags_needed)
    frags_from_normal = total_frags_needed - frags_from_tumor
    perbatch_tumor = int(frags_from_tumor/batchsize)
    perbatch_normal = int(frags_from_normal/batchsize)
    for i in range(batchsize):
        # print(i)
        alltumorfrags = random.choices(ctdna_frag, k=perbatch_tumor)
        allnormalfrags = random.choices(cfdna_frag, k=perbatch_normal)
        for frag in alltumorfrags:
            random_str = ''.join(random.choices(string.ascii_letters, k=15))
            f.write(f'@{random_str}\n')
            f.write(f'{frag}\n')
            f.write('+\n')
            qual = 'K'*len(frag)
            f.write(f'{qual}\n')
        for frag in allnormalfrags:
            random_str = ''.join(random.choices(string.ascii_letters, k=15))
            f.write(f'@{random_str}\n')
            f.write(f'{frag}\n')
            f.write('+\n')
            qual = 'K'*len(frag)
            f.write(f'{qual}\n')
        print('first batch write done')

# if __name__ == "__main__":
msg = "MosaicSim for cancer genome simulation"
parser = argparse.ArgumentParser(description = msg)
parser.add_argument("-o", "--outputDir", help="output directory full path", required=True)
parser.add_argument("-c", "--configFile", help="yaml config file for fine tune parameters")
args = parser.parse_args()

script_dir = os.path.dirname(os.path.realpath(__file__))
list_of_bases = ['A', 'C', 'T', 'G']
list_of_pairs = ['CA', 'CG', 'CT', 'TA', 'TC', 'TG']
sig_file = '{}/data/signatures.txt'.format(script_dir)
num_signatures = 78
use_signatures = False
signature_alpha = 10
full_genome = '{}/data/hg38.fa'.format(script_dir)
EXON_FILE = '{}/data/exonsegments.txt'.format(script_dir)
num_samples_list = [7]
num_tumors_list = [2]
read_len_list = [75, 150, 500, 2000]
frag_len_list = [150,200, 1000, 3000]
alpha_list = [10]
paired_list = [True]
WES_list = [False, True]
use_leaf_only = False
error_rate_list = [0.0, 0.0, 0.0, 0.00001,0.00001,0.0001, 0.001]
clone_list = [5]
ultralow_rates_list = [1e-15]
low_rates_list = [1e-15, 1e-13, 1e-10]
medium_rates_list = [5e-9, 4e-10, 9e-10, 3e-9]
high_rates_list = [3e-8, 9e-9, 7e-9]
ultrahigh_rates_list = [5e-8,5e-7,6e-7,5e-8,1e-7]
coverage_list = [2, 5, 10, 15,15, 25,25, 30,30]
pop_list = [8e8]
num_single_cell_list = [0]
liquid_biopsy_list = [False]
batch_size = 1
subblock_size = 1
LSH_hash = False
LSHStringNum = 10000000
kmer_len=50
num_perm=64
thresh=0.33
ctdna_frac_list = [0.96]
ref_coverage = 30
ref_clones = 5
ref_paired = True
ref_WES = False
ref_erate = 0.0
list_of_rates = [high_rates_list, ultralow_rates_list, high_rates_list, ultralow_rates_list, high_rates_list, ultralow_rates_list,ultralow_rates_list, ultralow_rates_list, ultralow_rates_list, ultralow_rates_list, ultralow_rates_list, ultralow_rates_list]

# add purity
purity_list = [0.8]

#random seed
random_seed=123
tree_seed = 123

if args.configFile is None:
    print("No config file provided; using default parameters")
else:
    # print(args.configFile)
    yamlFile = args.configFile
    with open(yamlFile, "r") as file:
        params = yaml.safe_load(file)
    # print(params)
    for key in params.keys():
        vars()[key] = params[key]

# update parameters from yaml file
random.seed(random_seed)
np.random.seed(random_seed)

if len(list_of_rates) == 0:
    list_of_rates = [high_rates_list, ultralow_rates_list, high_rates_list, ultralow_rates_list, high_rates_list, ultralow_rates_list, ultralow_rates_list, ultralow_rates_list, ultralow_rates_list, ultralow_rates_list, ultralow_rates_list, ultralow_rates_list]

tab = str.maketrans("ACTG", "TGAC")

if use_signatures:
    sig_df = pd.read_csv(sig_file, sep = '\t', header = None)
    sig_df = sig_df.iloc[1:]
    sig_df = sig_df.iloc[:,1:]
    signatures_matrix = sig_df.to_numpy()
    signature_distributions = [float(1/num_signatures)]*num_signatures

read_length_index = random.randint(0, len(read_len_list)-1)
ref_read_len = read_len_list[read_length_index]
ref_frag_len = frag_len_list[read_length_index]
ref_tot_nodes = 2*ref_clones-1
ref_root_node = ref_tot_nodes-1
ref_int_nodes = ref_root_node-1
ref_alpha = random.choice(alpha_list)

## TO MODIFY
# storage_dir = '/home/assrivat/simulation_results/'

print('start')
ts = time.time()
# randomid = sys.argv[1]
#CHANGE THIS TO  WHERE YOU WANT TO STORE THE DATA!
base_working_dir = args.outputDir.rstrip("/") + '/'
try:
    os.mkdir(base_working_dir)
except:
    print("output directory already exists")

reference_working_dir = base_working_dir + 'reference/'

reversemap = {'chr1':0, 'chr10':2, 'chr11':4, 'chr12':6, 'chr13':8, 'chr14':10, 'chr15':12, 'chr16':14, 'chr17':16, 'chr18':18, 'chr19':20, 'chr2':22, 'chr20':24, 'chr21':26, 'chr22':28, 'chr3':30, 'chr4':32, 'chr5':34, 'chr6':36, 'chr7':38, 'chr8':40, 'chr9':42, 'chrX':44, 'chrY':45} 
numchrommap = {0: 'chr1', 1: 'chr1', 2: 'chr10', 3: 'chr10', 4: 'chr11', 5: 'chr11', 6: 'chr12', 7: 'chr12', 8: 'chr13', 9: 'chr13', 10: 'chr14', 11: 'chr14', 12: 'chr15', 13: 'chr15', 14: 'chr16', 15: 'chr16', 16: 'chr17', 17: 'chr17', 18: 'chr18', 19: 'chr18', 20: 'chr19', 21: 'chr19', 22: 'chr2', 23: 'chr2', 24: 'chr20', 25: 'chr20', 26: 'chr21', 27: 'chr21', 28: 'chr22', 29: 'chr22', 30: 'chr3', 31: 'chr3', 32: 'chr4', 33: 'chr4', 34: 'chr5', 35: 'chr5', 36: 'chr6', 37: 'chr6', 38: 'chr7', 39: 'chr7', 40: 'chr8', 41: 'chr8', 42: 'chr9', 43: 'chr9', 44: 'chrX', 45: 'chrY'}
chrom_dict = ['chr1', 'chr10', 'chr11', 'chr12', 'chr13', 'chr14', 'chr15', 'chr16', 'chr17', 'chr18', 'chr19',
            'chr2', 'chr20', 'chr21', 'chr22', 'chr3', 'chr4', 'chr5', 'chr6', 'chr7', 'chr8', 'chr9', 'chrX', 'chrY']
reduced_chrom_dict = ['chr1', 'chr10', 'chr11', 'chr12', 'chr13', 'chr14', 'chr15', 'chr16', 'chr17',
                    'chr18', 'chr19', 'chr2', 'chr20', 'chr21', 'chr22', 'chr3', 'chr4', 'chr5', 'chr6', 'chr7', 'chr8', 'chr9']
sex_chroms = ['chrX', 'chrY']
chroms = []
fasta_sequences = SeqIO.parse(open(full_genome), 'fasta')
for fasta in fasta_sequences:
    name = fasta.id
    if (name in reduced_chrom_dict):
        # print(fasta.name)
        chroms.append(str(fasta.seq).upper())
        chroms.append(str(fasta.seq).upper())
    elif(name in sex_chroms):
        # print(fasta.name)
        chroms.append(str(fasta.seq).upper())
    else:
        continue
print('chroms loaded')
getmemory()

total_num_intervals = 0
exonDict = {}
strings_to_idx = []
for i in chrom_dict:
    exonDict[i] = []
with open(EXON_FILE, 'r') as f:
    for line in f:
        chrom, start, end = line.split()
        if chrom in chrom_dict:
            start_i = int(start) - 1
            end_i = int(end)
            interval = [start_i, end_i]
            total_num_intervals += 1
            exonDict[chrom].append(interval)
            # print(chroms[reversemap[chrom]])
            strings_to_idx.append(chroms[reversemap[chrom]][start_i:end_i])
getmemory()
# print(len(strings_to_idx))

# makedir(base_working_dir)
# clear_dir(base_working_dir)
print(base_working_dir)
if(LSH_hash): 
    lshindex =[]
    all_hashes = [MinHash(num_perm=num_perm) for i in range(len(strings_to_idx))]
    for i in range(len(strings_to_idx)): 
        kmer_set_i = getKmers(strings_to_idx[i], kmer_len)
        key_i = str(i)
        for z in kmer_set_i: 
            all_hashes[i].update(z.encode('utf8'))
        lshindex.append((key_i, all_hashes[i]))
    lsh = MinHashLSH(threshold=thresh, num_perm=num_perm)
    for i in lshindex: 
        lsh.insert(i[0],i[1])
    print('hash index made')

# do reference first
print('making ref reads')
makedir(reference_working_dir)
clear_dir(reference_working_dir)
wgz(reference_working_dir + str(ref_root_node) + '.gz', chroms)
with open(reference_working_dir + 'parameter_list.txt', 'w') as f:
    f.write('coverage: ' + str(ref_coverage)+'\n')
    f.write('read len: ' + str(ref_read_len)+'\n')
    f.write('frag len: ' + str(ref_frag_len)+'\n')
    f.write('paired: ' + str(ref_paired)+'\n')
    f.write('WES: ' + str(ref_WES)+'\n')
    f.write('error rate: ' + str(ref_erate) + '\n')

del chroms
getmemory()
if(ref_paired):
    if(ref_WES):
        exonrunPairedSim(ref_int_nodes, ref_coverage, ref_read_len, ref_frag_len, reference_working_dir,
                        reference_working_dir, batch_size, ref_root_node, exonDict, numchrommap, subblock_size, ref_alpha, ref_erate, flag=1)
    else:
        runPairedSim(ref_int_nodes, ref_coverage, ref_read_len, ref_frag_len, reference_working_dir,
                    reference_working_dir, batch_size, ref_root_node, ref_alpha, ref_erate, flag=1)
else:
    if(ref_WES):
        exonrunSim(ref_int_nodes, ref_coverage, ref_read_len, reference_working_dir, reference_working_dir,
                batch_size, ref_root_node, exonDict, numchrommap, subblock_size, ref_alpha, ref_erate, flag=1)
    else:
        runSim(ref_int_nodes, ref_coverage, ref_read_len, reference_working_dir,
            reference_working_dir, batch_size, ref_root_node, ref_alpha, ref_erate, flag=1)
getmemory()

running_clone_list = []
num_tumors = random.choice(num_tumors_list)
num_samples = random.choice(num_samples_list)
for tum in range(num_tumors):
    getmemory()
    alpha = random.choice(alpha_list)
    num_clones = random.choice(clone_list)
    running_clone_list.append(num_clones)
    tot_nodes = 2*num_clones - 1
    root_node = tot_nodes - 1
    int_nodes = root_node - 1
    if(use_leaf_only): 
        use_nodes = num_clones
    else: 
        use_nodes = int_nodes
    pop = random.choice(pop_list)
    tumor_number_dir = f'tumor_{tum}/'
    working_dir = base_working_dir + tumor_number_dir
    makedir(working_dir)
    clear_dir(working_dir)
    baseline_chroms = rgz(reference_working_dir + str(ref_root_node) + '.gz')
    wgz(working_dir + str(root_node) + '.gz', baseline_chroms)
    del baseline_chroms
    print('written reg')
    tree = getTree(num_clones, pop, working_dir, tree_seed)
    list_of_paths = getPaths(tree, num_clones)
    print(list_of_paths)
    time_matrix, depth = getTimeMatrix(tree, num_clones)
    mutationedge_list, avg_rate_list = generateOrder(
        tree, time_matrix, list_of_rates)
    infos, muts = applyMutations(
        tot_nodes, working_dir, list_of_paths, use_signatures, mutationedge_list)
    with open(working_dir + 'mutation_list.txt', 'w') as f:
        f.write(str(muts))
    with open(working_dir + 'information_list.txt', 'w') as f:
        f.write(str(infos))
    approx_len = len(muts[0])
    print('approx mutations', approx_len)
    print(muts)
    print('mutated genomes stored')
    getmemory()
    if(LSH_hash):
        tumorExonDict = exonDict.copy()
        strings_per_clone = LSHStringNum
        set_of_start_indices = set()
        for i in range(strings_per_clone): 
            chrom = random.randint(0,45)
            the_string, string_pos = get_random_str(chroms[chrom], 150)
            kmer_of_string = getKmers(the_string, kmer_len)
            m = MinHash(num_perm=num_perm)
            for shingle in kmer_of_string: 
                m.update(shingle.encode('utf8'))
            n = len(lsh.query(m))
            if(n > 0): 
                tumorExonDict[chrom].append([string_pos, string_pos+150])


    for sample in range(num_samples):
        print('starting sample')
        if(LSH_hash): 
            exonDictR = tumorExonDict
        else: 
            exonDictR = exonDict
        real_working_dir = working_dir + f'samplenum_{sample}/'
        makedir(real_working_dir)
        clear_dir(real_working_dir)
        coverage = random.choice(coverage_list)
        num_single_cells = random.choice(num_single_cell_list)
        read_length_index = random.randint(0, len(read_len_list)-1)
        read_len = read_len_list[read_length_index]
        frag_len = frag_len_list[read_length_index]
        paired = random.choice(paired_list)
        WES = random.choice(WES_list)
        error_rate = random.choice(error_rate_list)
        purity = random.choice(purity_list)
        with open(real_working_dir + 'parameter_list.txt', 'w') as f:
            f.write('num leaves: ' + str(num_clones)+'\n')
            f.write('dir_conc: ' + str(alpha)+'\n')
            f.write('cell pop: ' + str(pop)+'\n')
            f.write('coverage: ' + str(coverage)+'\n')
            f.write('num single cells: ' + str(num_single_cells)+'\n')
            f.write('read len: ' + str(read_len)+'\n')
            f.write('frag len: ' + str(frag_len)+'\n')
            f.write('paired: ' + str(paired)+'\n')
            f.write('WES: ' + str(WES)+'\n')
            f.write('rates of variants: ' + str(avg_rate_list)+'\n')
            f.write('full poisson time: ' + str(depth) + '\n')
            f.write('error rate: ' + str(error_rate) + '\n')
        getmemory()
        if(paired):
            if(WES):
                exonrunPairedSim(use_nodes, coverage, read_len, frag_len, working_dir, real_working_dir,
                                batch_size, root_node, exonDictR, numchrommap, subblock_size, alpha, error_rate, flag=0)
                for i in range(num_single_cells):
                    single_cell_dir = working_dir+f'samplenum_{sample}_singlecell_{i}/'
                    makedir(single_cell_dir)
                    clear_dir(single_cell_dir)
                    exonrunPairedSim(use_nodes, coverage, read_len, frag_len, working_dir, single_cell_dir,
                                    batch_size, root_node, exonDictR, numchrommap, subblock_size, alpha, error_rate, flag=2)

            else:
                runPairedSim(use_nodes, coverage, read_len, frag_len, working_dir,
                            real_working_dir, batch_size, root_node, alpha, error_rate, purity, flag=0)
                for i in range(num_single_cells):
                    single_cell_dir = working_dir+f'samplenum_{sample}_singlecell_{i}/'
                    makedir(single_cell_dir)
                    clear_dir(single_cell_dir) 
                    runPairedSim(use_nodes, coverage, read_len, frag_len, working_dir,
                                single_cell_dir, batch_size, root_node, alpha, error_rate, flag=2)
        else:
            if(WES):
                exonrunSim(use_nodes, coverage, read_len, working_dir, real_working_dir,
                        batch_size, root_node, exonDictR, numchrommap, subblock_size, alpha, error_rate, flag=0)
                for i in range(num_single_cells):
                    single_cell_dir = working_dir+f'samplenum_{sample}_singlecell_{i}/'
                    makedir(single_cell_dir)
                    clear_dir(single_cell_dir) 
                    exonrunSim(use_nodes, coverage, read_len, working_dir, single_cell_dir,
                            batch_size, root_node, exonDictR, numchrommap, subblock_size, alpha, error_rate, flag=2)

            else:
                runSim(use_nodes, coverage, read_len, working_dir,
                    real_working_dir, batch_size, root_node, alpha, error_rate, flag=0)
                for i in range(num_single_cells):
                    single_cell_dir = working_dir+f'samplenum_{sample}_singlecell_{i}/'
                    makedir(single_cell_dir)
                    clear_dir(single_cell_dir) 
                    runSim(use_nodes, coverage, read_len, working_dir,
                        single_cell_dir, batch_size, root_node, alpha, error_rate, flag=2)
print('finished tumors')
liquid_biopsy = random.choice(liquid_biopsy_list)
if(liquid_biopsy):
    lb_dir = base_working_dir + 'liquid_biopsy/'
    makedir(lb_dir)
    clear_dir(lb_dir)
    lb_alpha = random.choice(alpha_list)
    lb_coverage = random.choice(coverage_list)
    ctdna_frac = random.choice(ctdna_frac_list)
    lbrunSim(num_tumors, running_clone_list, lb_coverage,
            base_working_dir, lb_dir, ref_root_node, lb_alpha, ctdna_frac, 6)

te = time.time()
print('time elapsed', te-ts)