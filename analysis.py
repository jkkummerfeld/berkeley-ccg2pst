#!/usr/bin/env python3

import sys
import trees
import span_dict
import markup_convert

analysis_out = sys.stdout

def side_by_side(tree0, tree1):
    text0 = tree0.__repr__()
    text1 = tree1.__repr__()
    lines0 = ' '.join(text0.split('\t')).split('\n')
    lines1 = ' '.join(text1.split('\t')).split('\n')
    longest = 0
    for line in lines0:
        longest = max(longest, len(line))
    longest += 3
    longest = max(longest, 40)
    lines = []
    i = 0
    while i < len(lines0) or i < len(lines1):
        start = ' ' * longest
        if i < len(lines0):
            start = lines0[i] + ((longest - len(lines0[i])) * ' ')
        rest = ''
        if i < len(lines1):
            rest = lines1[i]
        lines.append(start + rest)
        i += 1
    return '\n'.join(lines)

def strip_label(label):
    if not label[0] == '-':
        label = label.split('-')[0]
    label = label.split('=')[0]
    if label == 'PRT':
        label = 'ADVP' # another collins change
    return label

labels_to_ignore = set(["-NONE-", "TOP", "."])
words_to_ignore = set(["'","`","''", "``", "--",":",";","-",",","..."])
def spans3(tree, ans, pos):
    start = pos
    label = None
    not_a_schema = False
    try:
        a = tree.subtrees
        not_a_schema = True
    except:
        pass
    if type(tree) == type(''):
        if tree == '' or tree[0] != '(':
            return pos
        label, word = tree[1:-1].split()
        if label in labels_to_ignore or word in words_to_ignore:
            return pos
        return pos + 1
    else:
        label = tree.label
        if not_a_schema:
            if len(tree.subtrees) == 0:
                if tree.label in labels_to_ignore or tree.word in words_to_ignore:
                    return pos
                return pos + 1
    if not_a_schema:
        for subtree in tree.subtrees:
            pos = spans3(subtree, ans, pos)
    else:
        for child in tree.children:
            pos = spans3(child, ans, pos)
    end = pos
    if start == end:
        return start
    if (start, end) not in ans:
        ans[(start, end)] = {}
    label = strip_label(label)
    if label != '' and label != 'TOP':
        if label in ans[(start, end)]:
            # keep the higher one
            ctree = ans[(start, end)][label]
            if not_a_schema:
                while len(ctree.subtrees) == 1:
                    ctree = ctree.subtrees[0]
                    if ctree == tree:
                        return pos
            else:
                while len(ctree.children) == 1:
                    ctree = ctree.children[0]
                    if ctree == tree:
                        return pos
                    if type(ctree) == type(''):
                        break
        ans[(start, end)][label] = tree
    return pos

def spans(tree):
    ans = {}
    spans3(tree, ans, 0)
    return ans

def tree_repr(tree, depth):
    not_a_schema = False
    try:
        a = tree.subtrees
        not_a_schema = True
    except:
        pass
    if not_a_schema:
        if tree.word is not None:
            return '(%s)' % (strip_label(tree.label))
        text = '(' + strip_label(tree.label)
        if depth > 0:
            for subtree in tree.subtrees:
                text += ' ' + tree_repr(subtree, depth - 1)
        text += ')'
        return text
    else:
        return 'TODO'

def get_word_info(schema_spans, key, label):
    word_info = 'unk-cat\tunk-pos\tunk-word'
    for label in schema_spans[key]:
        span = schema_spans[key][label]
        if span.label == label:
            cat = span.source.category
            pos = span.source.pos
            word = span.source.word
            if span.source.rule == 'unary':
                pos = "unary-rule"
                word = span.source.subtrees[0].category
            elif span.source.rule == 'binary':
                pos = "binary-rule"
                word = "%s_%s" % (span.source.subtrees[0].category, span.source.subtrees[1].category)
            elif span.source.rule == 'type':
                pos = "type-raising"
                word = span.source.subtrees[0].category
            return "%s\t%s\t%s" % (cat, pos, word)

def get_cat(source, key):
    node = source.get_node(key)
    if node.pos is not None:
        return '\t'.join([node.category, node.pos, node.word])
    else:
        return '\t'.join([node.category, 'unk-pos', 'unk-word'])

def lowest_span(spans):
    fallback = [s for s in spans][0]
    for span in spans:
        if len(span.subtrees) != 1:
            return span
    return fallback

def log(fields):
    print('\t'.join(fields), file=analysis_out)



def analyse(source, target, auto_ptb, auto_schema, out):
    global analysis_out
    analysis_out = out
    if auto_schema.source is None:
        print("Missing schema source")
        print("Missing schema source", file=out)
        return

    target_spans = spans(target)
    auto_spans = spans(auto_ptb)
    schema_spans = spans(auto_schema)

    errors = False

    #
    # Missing brackets
    #
    for target_key in target_spans:
        if target_key not in auto_spans:
            errors = True
            # find the set of brackets that are as small as possible, while still covering key
            best = None
            for akey in auto_spans:
                if akey[0] <= target_key[0] and target_key[1] <= akey[1]:
                    if best is None or best[0] < akey[0] or akey[1] < best[1]:
                        best = akey
            auto_key = best

            for tlabel in target_spans[target_key]:
                ttree = target_spans[target_key][tlabel]
                atree = lowest_span(auto_spans[auto_key].values())
                cat_info = get_word_info(schema_spans, auto_key, atree.label)
                for adepth in [1, 2]:
                    for tdepth in [1, 2]:
                        adesc = tree_repr(atree, adepth)
                        tdesc = tree_repr(ttree, tdepth)
                        log(['==miss %d %d ==' % (tdepth, adepth), tlabel, cat_info, tdesc, adesc])


    #
    # Extra brackets
    #
    for auto_key in auto_spans:
        if auto_key not in target_spans:
            errors = True
            # find the set of brackets that are as small as possible, while still covering key
            best = None
            for tkey in target_spans:
                if tkey[0] <= auto_key[0] and auto_key[1] <= tkey[1]:
                    if best is None or best[0] < tkey[0] or tkey[1] < best[1]:
                        best = tkey
            target_key = best
            if target_key is None:
                log(["None target key!", auto_key.__repr__()])
            else:
                for alabel in auto_spans[auto_key]:
                    atree = auto_spans[auto_key][alabel]
                    cat_info = get_word_info(schema_spans, auto_key, alabel)
                    ttree = lowest_span(target_spans[target_key].values())
                    for adepth in [1, 2]:
                        for tdepth in [1, 2]:
                            adesc = tree_repr(atree, adepth)
                            tdesc = tree_repr(ttree, tdepth)
                            log(['==extra %d %d ==' % (tdepth, adepth), alabel, cat_info, tdesc, adesc])


    #
    # Span present in both, but with different labels
    #
    for key in target_spans:
        if key in auto_spans:
            target_labels = set(target_spans[key].keys())
            auto_labels = set(auto_spans[key].keys())
            diff = target_labels.symmetric_difference(auto_labels)
            if len(diff) != 0:
                errors = True
                textra = target_labels.difference(auto_labels)
                aextra = auto_labels.difference(target_labels)
    
                # A single label that is wrong
                if len(diff) == 2 and len(textra) == 1 and len(aextra) == 1:
                    tlabel = textra.pop()
                    ttree = target_spans[key][tlabel]
                    alabel = aextra.pop()
                    atree = auto_spans[key][alabel]
                    cat_info = get_word_info(schema_spans, key, alabel)
                    for adepth in [1, 2]:
                        for tdepth in [1, 2]:
                            adesc = tree_repr(atree, adepth)
                            tdesc = tree_repr(ttree, tdepth)
                            log(['==diff-c %d %d ==' % (tdepth, adepth), tlabel + '_' + alabel, cat_info, tdesc, adesc])

                elif len(aextra) == 0: # ie, these are actually missing
                    for tlabel in textra:
                        ttree = target_spans[key][tlabel]
                        atree = lowest_span(auto_spans[key].values())
                        cat_info = get_word_info(schema_spans, key, atree.label)
                        for adepth in [1, 2]:
                            for tdepth in [1, 2]:
                                adesc = tree_repr(atree, adepth)
                                tdesc = tree_repr(ttree, tdepth)
                                log(['==miss %d %d ==' % (tdepth, adepth), tlabel, cat_info, tdesc, adesc])

                elif len(textra) == 0: # ie, these are actually extra
                    for alabel in aextra:
                        atree = auto_spans[key][alabel]
                        cat_info = get_word_info(schema_spans, key, alabel)
                        ttree = lowest_span(target_spans[key].values())
                        for adepth in [1, 2]:
                            for tdepth in [1, 2]:
                                adesc = tree_repr(atree, adepth)
                                tdesc = tree_repr(ttree, tdepth)
                                log(['==extra %d %d ==' % (tdepth, adepth), alabel, cat_info, tdesc, adesc])

                else: # more complicated difference
                    for tlabel in textra:
                        ttree = target_spans[key][tlabel]
                        atree = lowest_span(auto_spans[key].values())
                        cat_info = get_word_info(schema_spans, key, atree.label)
                        for adepth in [1, 2]:
                            for tdepth in [1, 2]:
                                adesc = tree_repr(atree, adepth)
                                tdesc = tree_repr(ttree, tdepth)
                                log(['==diff-m %d %d ==' % (tdepth, adepth), tlabel, cat_info, tdesc, adesc])
                    for alabel in aextra:
                        atree = auto_spans[key][alabel]
                        cat_info = get_word_info(schema_spans, key, alabel)
                        ttree = lowest_span(target_spans[key].values())
                        for adepth in [1, 2]:
                            for tdepth in [1, 2]:
                                adesc = tree_repr(atree, adepth)
                                tdesc = tree_repr(ttree, tdepth)
                                log(['==diff-e %d %d ==' % (tdepth, adepth), alabel, cat_info, tdesc, adesc])

    #
    # Correct brackets
    #
    for key in target_spans:
        if key in auto_spans:
            target_labels = set(target_spans[key].keys())
            auto_labels = set(auto_spans[key].keys())
            same = target_labels.intersection(auto_labels)
            for label in same:
                ttree = target_spans[key][label]
                atree = auto_spans[key][label]
                cat_info = get_word_info(schema_spans, key, label)
                for adepth in [1, 2]:
                    for tdepth in [1, 2]:
                        adesc = tree_repr(atree, adepth)
                        tdesc = tree_repr(ttree, tdepth)
                        log(['==same %d %d ==' % (tdepth, adepth), label, cat_info, tdesc, adesc])
    #
    # General sentence info
    #
    if errors:
        print(target, file=out)
        print(auto_ptb, file=out)
        print("", file=out)

if __name__ == '__main__':
    pass
