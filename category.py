#!/usr/bin/env python3
# Just handle unary rules, working out when one is being used

import re

CURLY_BRACES_RE = re.compile('{[^}]*}')
def strip_braces(category):
    return CURLY_BRACES_RE.sub('', category)

SQUARE_BRACKETS_RE = re.compile('\[[^\]]*\]')
def strip_square_brackets(category):
    if category is not None:
        return SQUARE_BRACKETS_RE.sub('', category)
    else:
        return None

def remove_extra_brackets(category):
    if category[0] != '(' or category[-1] != ')':
        return category
    if not ('\\' in category or '/' in category):
        return category[1:-1]
    depth = 0
    hit_zero = False
    for i in range(len(category)):
        if category[i] == '(':
            depth += 1
        elif category[i] == ')':
            depth -= 1
        elif depth == 0:
            hit_zero = True
            break
    if not hit_zero:
        return category[1:-1]
    return category

def divide(category):
    if '\\' not in category and '/' not in category:
        return [category, None, None]
    category = remove_extra_brackets(category)
    depth = 0
    sep = None
    for i in range(len(category)):
        if category[i] == '(':
            depth += 1
        elif category[i] == ')':
            depth -= 1
        elif category[i] in '/\\' and depth == 0:
            sep = i
            break
    if sep is None:
        return [category, None, None]
    parts = [category[:sep], category[sep:sep+1], category[sep+1:]]
    for i in [0, 2]:
        while True:
            if parts[i][0] != '(' or parts[i][-1] != ')':
                break
            stripped_version = parts[i][1:-1]
            depth = 0
            use = True
            for char in stripped_version:
                if char == '(':
                    depth += 1
                elif char == ')':
                    depth -= 1
                if depth < 0:
                    use = False
            if use:
                parts[i] = stripped_version
            else:
                break
    return parts

def compare(cat0, cat1):
    if cat0 is None or cat1 is None:
        return False
    # Check the general structure matches
    if strip_square_brackets(cat0) != strip_square_brackets(cat1):
        return False
    # remove [conj], which is present temporarily at the end
    cat0 = cat0.split('[conj]')[0]
    cat1 = cat1.split('[conj]')[0]

    cat0 = 'NP[X]'.join(cat0.split('NP'))
    cat0 = 'NP['.join(cat0.split('NP[X]['))
    cat1 = 'NP[X]'.join(cat1.split('NP'))
    cat1 = 'NP['.join(cat1.split('NP[X]['))

    cat0 = 'S[X]'.join(cat0.split('S'))
    cat0 = 'S['.join(cat0.split('S[X]['))
    cat1 = 'S[X]'.join(cat1.split('S'))
    cat1 = 'S['.join(cat1.split('S[X]['))

    pairs0 = SQUARE_BRACKETS_RE.findall(cat0)
    pairs1 = SQUARE_BRACKETS_RE.findall(cat1)
    # Having no brackets indicates no S, so it's fine
    if len(pairs0) == 0 or len(pairs1) == 0:
        return True
    # For debugging
    if len(pairs0) != len(pairs1):
        print('confused by:')
        print(cat0, cat1)
    # Make sure they all match (with X as a wildcard)
    for i in range(len(pairs0)):
        if pairs0[i] == '[X]' or pairs1[i] == '[X]' or pairs0[i] == pairs1[i]:
            continue
        return False
    return True

if __name__ == '__main__':
    pass
