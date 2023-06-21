#!/usr/bin/env python3

import trees

labels_to_ignore = set(["-NONE-", "TOP", "."])
words_to_ignore = set(["'","`","''", "``", "--",":",";","-",",","..."])
def span_dict(tree, ans, pos=0):
    start = pos
    label = tree.label
    word = tree.word
    if len(tree.subtrees) == 0:
        if label in labels_to_ignore or word in words_to_ignore:
            return pos
        return pos + 1
    for subtree in tree.subtrees:
        pos = span_dict(subtree, ans, pos)
    end = pos
    if start == end:
        return start
    if (start, end) not in ans:
        ans[(start, end)] = set()
    if not label[0] == '-':
        label = label.split('-')[0]
    label = label.split('=')[0]
    if label == 'PRT':
        label = 'ADVP' # another collins change
    if label != '' and label != 'TOP':
        ans[(start, end)].add(label)
    return pos

