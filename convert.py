#!/usr/bin/env python3

import sys, re
import trees, category, rule
import analysis
import span_dict
import trivial, markup_convert

tree_out = None
gold_out = None
log_out = sys.stdout
colour_out = None
analysis_out = sys.stdout

def score_count(target, auto):
    gold_nodes = 0
    auta_nodeo = 0
    match_brackets = 0
    match_labels = 0

    target_spans = {}
    span_dict.span_dict(target, target_spans)
    auto_spans = {}
    span_dict.span_dict(auto, auto_spans)
    gold_nodes = 0
    auto_nodes = 0
    print(target_spans.keys(), file=log_out)
    print(auto_spans.keys(), file=log_out)
    for key in target_spans:
        gold_nodes += len(target_spans[key])
        if key in auto_spans:
            match_brackets += min(len(auto_spans[key]), len(target_spans[key]))
            match_labels += len(auto_spans[key].intersection(target_spans[key]))
            if len(target_spans[key].symmetric_difference(auto_spans[key])) != 0:
                print('different label sets:   ', key, target_spans[key], auto_spans[key], target.word_yield(key)[1], file=log_out)
                print('different label sets:   ', key, target_spans[key], auto_spans[key], target.word_yield(key)[1], file=colour_out)
        else:
            # Check for crossing brackets
            crossing = False
            for akey in auto_spans:
                if key[0] < akey[0] < key[1] < akey[1]:
                    crossing = True
                    break
                if akey[0] < key[0] < akey[1] < key[1]:
                    crossing = True
                    break
            if crossing:
                print('crossing', end=" ", file=log_out)
                print('\033[01;31mcrossing\033[00m', end=" ", file=colour_out)
            print('missing span:           ', key, target_spans[key], target.word_yield(key)[1], file=log_out)
            print('missing span:           ', key, target_spans[key], target.word_yield(key)[1], file=colour_out)
    for key in auto_spans:
        auto_nodes += len(auto_spans[key])
        if key not in target_spans:
            crossing = False
            for tkey in target_spans:
                if key[0] < tkey[0] < key[1] < tkey[1]:
                    crossing = True
                    break
                if tkey[0] < key[0] < tkey[1] < key[1]:
                    crossing = True
                    break
            if crossing:
                print('crossing', end=" ", file=log_out)
                print('\033[01;31mcrossing\033[00m', end=" ", file=colour_out)
            # Check for crossing brackets
            print('extra span:             ', key, auto_spans[key], target.word_yield(key)[1], file=log_out)
            print('extra span:             ', key, auto_spans[key], target.word_yield(key)[1], file=colour_out)
    return gold_nodes, auto_nodes, match_brackets, match_labels

def calc_prf(overlap, auto, gold):
    if gold == 0:
        return 1.0, 1.0, 1.0
    if auto == 0:
        return 0.0, 0.0, 0.0
    p = float(overlap) / auto
    r = float(overlap) / gold
    f = 0
    if p + r > 1e-5:
        f = 2 * p * r / (p + r)
    return p, r, f

def compare_words(pwords, cwords):
    i = 0
    match = 0
    for word in cwords:
        while word != pwords[i]:
            if i == len(pwords) - 1:
                break
            i += 1
        if word == pwords[i]:
            match += 1
    return float(match) / len(cwords)

def print_stats(stats_name, gold_nodes, auto_nodes, match_brackets, match_labels, correct_sentences, correct_sentences_brackets, total_sentences):
    p_brac, r_brac, f_brac = calc_prf(match_brackets, auto_nodes, gold_nodes)
    p_labe, r_labe, f_labe = calc_prf(match_labels, auto_nodes, gold_nodes)
    print(stats_name, "counts:      ", gold_nodes, auto_nodes, '  ', match_brackets, match_labels, file=log_out)
    print(stats_name, "brackets:    %.2f   %.2f   %.2f" % (p_brac * 100, r_brac * 100, f_brac * 100), file=log_out)
    print(stats_name, "labels:      %.2f   %.2f   %.2f" % (p_labe * 100, r_labe * 100, f_labe * 100), file=log_out)
    print(stats_name, "sentences:   %d of %d (i.e. %.2f), just brackets %d of %d (i.e. %.2f)" % (correct_sentences, total_sentences, correct_sentences * 100.0 / total_sentences, correct_sentences_brackets, total_sentences, correct_sentences_brackets * 102.0 / total_sentences), file=log_out)

if __name__ == '__main__':
    args = ' '.join(sys.argv)
    methods = {
        'trivial': trivial.convert,
        'markedup': markup_convert.convert
    }
    if len(sys.argv) < 3:
        print("Usage:\n%s <PTB_file> <CCG_file>" % sys.argv[0])
        print("Options:")
        print("\t-method=[%s]" % (','.join(methods.keys())))
        print("\t-print_comparison")
        print("\t-sents=<num>")
        print("\t-max_length=<num>")
        print("\t-prefix=<str>")
        print("\t-exclude_no_parse")
        sys.exit(1)
    
    only_parsed = '-exclude_no_parse' in ' '.join(sys.argv)
    if '-prefix=' in args:
        prefix = args.split('-prefix=')[1].split(' ')[0]
        tree_out = open(prefix + '.auto', 'w')
        gold_out = open(prefix + '.gold', 'w')
        log_out = open(prefix + '.log', 'w')
        colour_out = open(prefix + '.colour', 'w')
        analysis_out = open(prefix + '.analysis', 'w')
        for output in [log_out, colour_out, analysis_out]:
            print("# this file was generated by the following command(s):", file=output)
            print("# " + args, file=output)
            print('', file=output)
    else:
        print("# this file was generated by the following command(s):")
        print("# " + args)
        print

    total_sentences = 1000000 if "-sents" not in args else int(args.split('-sents=')[1].split(' ')[0])
    max_sent_length = -1 if "-max_length" not in args else int(args.split('-sents=')[1].split(' ')[0])

    gold_nodes = 0
    auto_nodes = 0
    match_brackets = 0
    match_labels = 0
    correct_sentences = 0
    correct_sentences_brackets = 0
    print_trees = "-print_comparison" in args
    ptb_source = open(sys.argv[1])
    ccg_source = open(sys.argv[2])
    for i in range(total_sentences):
        source = trees.read_CCG_tree(ccg_source)
        target = trees.read_PTB_tree(ptb_source)
###     print(source)
        if source is None or target is None:
            total_sentences = i
            break

        if source.category is None:
            if not only_parsed:
                if gold_out is not None:
                    print(target.one_line_repr(), file=gold_out)
                    print("", file=tree_out)
            # only evaluate on sentences that receive a parse
            continue

        pwords = target.get_words()
        cwords = source.get_words()
        if len(cwords) != 0:
            while compare_words(pwords, cwords) < 0.7:
                if not only_parsed:
                    if gold_out is not None:
                        print(target.one_line_repr(), file=gold_out)
                        print("", file=tree_out)
                target = trees.read_PTB_tree(ptb_source)
                if target is None:
                    print("Ran out of sentences trying to find a match", file=sys.stderr)
                    sys.exit(2)
                pwords = target.get_words()

        if max_sent_length > 0 and len(pwords) > max_sent_length:
            continue

        if target.label == '':
            target.label = 'ROOT'

        if print_trees:
            print(source, file=log_out)
            print(target, file=log_out)
        use, auto_ptb, auto_schema = (False, None, None)
        if 'method' in args:
            method_name = args.split('method=')[1].split()[0]
            ans = methods[method_name](source, sys.argv, log_out)
            use, auto_ptb, auto_schema = ans
        else:
            ans = trivial.convert(source, sys.argv, log_out)
            use, auto_ptb, auto_schema = ans

        if not use:
            print("Not being included", file=log_out)
        if auto_schema is not None:
            analysis.analyse(source, target, auto_ptb, auto_schema, analysis_out)
        if tree_out is not None:
            if use:
                print(target.one_line_repr(), file=gold_out)
                print(auto_ptb.one_line_repr(), file=tree_out)
            elif not only_parsed:
                print(target.one_line_repr(), file=gold_out)
                print("", file=tree_out)

        if print_trees:
            print(auto_ptb, file=log_out)
            if colour_out is not None:
                print(source, file=colour_out)
                print(auto_ptb.repr_with_corrections(target), file=colour_out)

        scores = score_count(target, auto_ptb)
        gold_nodes += scores[0]
        auto_nodes += scores[1]
        match_brackets += scores[2]
        match_labels += scores[3]
        if scores[0] == scores[1] == scores[2]:
            correct_sentences_brackets += 1
        if scores[0] == scores[1] == scores[3]:
            correct_sentences += 1
        print_stats('', scores[0], scores[1], scores[2], scores[3], correct_sentences, correct_sentences_brackets,  i + 1)
        print_stats('cumulative', gold_nodes, auto_nodes, match_brackets, match_labels, correct_sentences, correct_sentences_brackets, i + 1)
    print_stats('final', gold_nodes, auto_nodes, match_brackets, match_labels, correct_sentences, correct_sentences_brackets, total_sentences)
