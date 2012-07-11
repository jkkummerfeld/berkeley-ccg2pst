#!/usr/bin/env python

import sys
import trees, category

# The trivial method reproduces the bracket structure exactly. Labels are either
# the atomic category, or a VP
def convert(source, argv=None, log=sys.stdout):
	ans = trees.PTB_Tree()
	if '\\' in source.category or '/' in source.category:
		ans.label = "VP"
	else:
		ans.label = category.strip_square_brackets(source.category)
	if source.word is not None:
		ans.word = source.word
		ans.pos = source.pos
		ans.label = source.pos
	for subtree in source.subtrees:
		ans.subtrees.append(convert(subtree))
	if argv is None:
		return ans
	else:
		return True, ans, None

if __name__ == '__main__':
	print "Please enter CCG trees:"
	for line in sys.stdin:
		print convert(trees.CCG_Tree(line.strip()))
