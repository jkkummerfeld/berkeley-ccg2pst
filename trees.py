#!/usr/bin/env python

import sys, re
import category, rule

class Tree:
	def __init__(self, text):
		self.text = text
		self.subtrees = []
		self.word = None
	
	def get_words(self):
		if self.word is not None:
			return [self.word]
		words = []
		for tree in self.subtrees:
			words += tree.get_words()
		return words

# switching back to PTB scheme
word_to_word_mapping = {
	'{': '-LCB-',
	'}': '-RCB-'
}
word_to_POS_mapping = {
	'--': ':',
	'-': ':',
	';': ':',
	':': ':',
	'-LRB-': '-LRB-',
	'-RRB-': '-RRB-',
	'-LCB-': '-LRB-',
	'-RCB-': '-RRB-',
	'{': '-LRB-',
	'}': '-RRB-',
	'Wa': 'NNP'
}
def get_PTB_word(word):
	global word_to_word_mapping
	if word in word_to_word_mapping:
		word = word_to_word_mapping[word]
	return word
def get_PTB_label(label, word):
	global word_to_POS_mapping
	if word in word_to_POS_mapping:
		label = word_to_POS_mapping[word]
	return label

class CCG_Tree(Tree):
# Convert line of CCGBank to a tree. This is an example line:
# (<T S[dcl] 0 2> (<T S[dcl] 1 2> (<T NP 0 1> (<T N 1 2> (<L N/N NNP NNP Ms. N_254/N_254>) (<L N NNP NNP Haag N>) ) ) (<T S[dcl]\NP 0 2> (<L (S[dcl]\NP)/NP VBZ VBZ plays (S[dcl]\NP_241)/NP_242>) (<T NP 0 1> (<L N NNP NNP Elianti N>) ) ) ) (<L . . . . .>) ) 
# This expands to:
# (<T S[dcl] 0 2>
# 	(<T S[dcl] 1 2>
# 		(<T NP 0 1>
# 			(<T N 1 2>
# 				(<L N/N NNP NNP Ms. N_254/N_254>)
# 				(<L N NNP NNP Haag N>) ) )
# 		(<T S[dcl]\NP 0 2>
# 			(<L (S[dcl]\NP)/NP VBZ VBZ plays (S[dcl]\NP_241)/NP_242>)
# 			(<T NP 0 1>
# 				(<L N NNP NNP Elianti N>) ) ) )
# 	(<L . . . . .>) )
	def __init__(self, text='', pos=0):
		Tree.__init__(self, text)
		self.label = ''
		self.category = None
		self.orig_category = None
		self.pos = None
		self.word = None
		self.head = None
		self.rule = None
		if text == '':
			return
		if '<L' in text:
			depth = 0
			for i in xrange(pos + 1, len(text)):
				char = text[i]
				# update the depth (note that brackets in categories only muck things up
				# for the category that is the root of this subtree)
				if char == '(':
					depth += 1
					if self.label != '' and depth == 1:
						self.subtrees.append(CCG_Tree(text, i))
				elif char == ')':
					depth -= 1
				# we've reached the end of the category that is the root of this subtree
				if char == '>' and self.label == '':
					self.label = text[pos + 2:i]
				# we've reached the end of the scope for this bracket
				if depth < 0:
					break
			parts = self.label.split()
			self.category = ''.join(parts[1].split('[X]'))
			self.orig_category = self.category
			# Fix a sentence with two broken categories in CCGBank (0595.15)
			if self.category[-1] in '\\/':
				self.category = self.category + 'NP'
			self.rule = rule.determine_combinator(self.subtrees, self.category)
			if 'conj' in self.rule:
				if not self.category.endswith('[conj]') and not category.compare(self.category, self.subtrees[1].category):
					if self.subtrees[1].category.endswith('[conj]'):
						self.category = self.subtrees[1].category
					else:
						self.category = self.subtrees[1].category + '[conj]'
			if len(parts) == 4:
				if len(self.subtrees) > 0:
					self.head = self.subtrees[0]
				if parts[2] == '1' and len(self.subtrees) == 2:
					self.head = self.subtrees[1]
			elif len(parts) == 6:
				self.pos = parts[3]
				self.word = parts[4]
		else:
			# Handle fowler input
			self.label = text[pos:].split()[0][1:]
			self.category = ')'.join('('.join(self.label.split('{')).split('}'))
			self.orig_category = self.category

			depth = 0
			for i in xrange(pos + 1, len(text)):
				if depth < 0:
					break
				char = text[i]
				# update the depth
				if char == '(':
					depth += 1
					if depth == 1:
						self.subtrees.append(CCG_Tree(text, i))
				elif char == ')':
					depth -= 1
					if len(self.subtrees) == 0:
						pos = i
						for j in xrange(i, 0, -1):
							if text[j] == ' ':
								pos = j
								break
						self.word = text[pos + 1:i]
						break

			self.rule = rule.determine_combinator(self.subtrees, self.category)
			if 'conj' in self.rule:
				if not self.category.endswith('[conj]') and not category.compare(self.category, self.subtrees[1].category):
					if self.subtrees[1].category.endswith('[conj]'):
						self.category = self.subtrees[1].category
					else:
						self.category = self.subtrees[1].category + '[conj]'
			if self.word is not None:
				self.pos = "UNK"
				if self.word == '.':
					self.pos = '.'
				if self.word == ',':
					self.pos = ','
				if self.word == '...':
					self.pos = ':'
				if self.word == '?':
					self.pos = '.'
				if self.word == '!':
					self.pos = '.'
			
	
	def get_node(self, span, pos=None, min_enclosing=False):
		return_ans_only = False
		if pos is None:
			pos = 0
			return_ans_only = True
		start = pos
		ans = None
		if self.word is not None:
			labels_to_ignore = set(["-NONE-","TOP"])
			words_to_ignore = set(["'","`","''","``",".","--",":",";","-",",","..."])
			if self.word not in words_to_ignore and self.label not in labels_to_ignore:
				pos += 1
		else:
			for subtree in self.subtrees:
				pos, sub_ans = subtree.get_node(span, pos, min_enclosing)
				if sub_ans is not None:
					ans = sub_ans
		end = pos
		if min_enclosing:
			if ans is None and start <= span[0] and end >= span[1]:
				ans = self
		else:
			if start == span[0] and end == span[1]:
				ans = self
		if return_ans_only:
			return ans
		else:
			return end, ans
	
	def contains_rule(self, text):
		if text in self.rule:
			return True
		for subtree in self.subtrees:
			if subtree.contains_rule(text):
				return True
		return False

	def all_word_yield(self, span=None, pos=0):
		if self.word is not None:
			if span is None or span[0] <= pos < span[1]:
				return (pos + 1, self.word)
			else:
				return (pos + 1, '')
		else:
			text = []
			for subtree in self.subtrees:
				pos, words = subtree.all_word_yield(span, pos)
				if words != '':
					text.append(words)
			return (pos, ' '.join(text))
	
	def __repr__(self, depth=0):
		ans = '\n' + depth * '\t'
		ans += '('
		if self.category is None:
			ans += 'EMPTY EMPTY)'
			return ans
		if self.rule is not None:
			ans += self.rule + ' '
		ans += self.category
		if self.pos is not None:
			pos = get_PTB_label(self.pos, self.word)
			ans += ' ' + pos
		if self.word is not None:
			ans += ' ' + get_PTB_word(self.word)
		for subtree in self.subtrees:
			ans += subtree.__repr__(depth + 1)
		ans += ')'
		return ans



class PTB_Tree(Tree):
# Convert text from the PTB to a tree. For example:
# ( (S (NP-SBJ (NNP Ms.) (NNP Haag) ) (VP (VBZ plays) (NP (NNP Elianti) )) (. .) ))
# This is a compressed form of:
# ( (S 
#     (NP-SBJ (NNP Ms.) (NNP Haag) )
#     (VP (VBZ plays) 
#       (NP (NNP Elianti) ))
#     (. .) ))
	def __init__(self, text='', pos=0):
		Tree.__init__(self, text)
		self.label = ''
		self.pos = None
		depth = 0
		for i in xrange(pos + 1, len(text)):
			char = text[i]
			# update the depth
			if char == '(':
				depth += 1
				if depth == 1:
					self.subtrees.append(PTB_Tree(text, i))
			elif char == ')':
				depth -= 1
				if len(self.subtrees) == 0:
					pos = i
					for j in xrange(i, 0, -1):
						if text[j] == ' ':
							pos = j
							break
					self.word = text[pos + 1:i]
			
			# we've reached the end of the category that is the root of this subtree
			if depth == 0 and char == ' ' and self.label == '':
				self.label = text[pos + 1:i]
			# we've reached the end of the scope for this bracket
			if depth < 0:
				break
		if self.word is not None:
			self.pos = self.label
	
	def word_yield(self, span=None, pos=0):
		labels_to_ignore = set([",", "-NONE-", "TOP", ":", "."])
		words_to_ignore = set(["'","`","''","``"])
		# ignore quotes as they won't always be present
		if self.label in labels_to_ignore:
			return (pos, '')
		if self.word is not None:
			if self.word in words_to_ignore:
				return (pos, '')
			if span is None or span[0] <= pos < span[1]:
				return (pos + 1, self.word)
			else:
				return (pos + 1, '')
		else:
			text = []
			for subtree in self.subtrees:
				pos, words = subtree.word_yield(span, pos)
				if words != '':
					text.append(words)
			return (pos, ' '.join(text))

	def __repr__(self, depth=0):
		ans = ''
		if depth > 0:
			ans += '\n'
		ans += depth * '\t'
		ans += '(' + get_PTB_label(self.label, self.word)
		if self.word is not None:
			ans += ' ' + get_PTB_word(self.word)
		for subtree in self.subtrees:
			ans += subtree.__repr__(depth + 1)
		ans += ')'
		return ans
	
	def one_line_repr(self):
		ans = '(' + get_PTB_label(self.label, self.word)
		if self.word is not None:
			return ans + ' ' + get_PTB_word(self.word) + ')'
		for subtree in self.subtrees:
			ans += ' ' + subtree.one_line_repr()
		ans += ')'
		return ans

	def repr_with_corrections(self, gold_spans, depth=0, pos=0,parent=None):
		return_str = False
		if type(gold_spans) != type({}):
			return_str = True
			span_dict = {}
			gold_spans.get_spans(span_dict)
			gold_spans = span_dict

		# note - does not print missing spans that cover parts of present spans
		start_missing = "\033[01;36m"
		start_extra = "\033[01;31m"
		start_wrong_label = "\033[01;33m"
		end_colour = "\033[00m"

		start = ''
		if depth > 0:
			start += '\n'
		start += depth * '\t'
		# Handle the POS-word case
		labels_to_ignore = set(["-NONE-", "TOP", ":", "."])
		words_to_ignore = set(["'","`","''", "``", "--",":",";","-",","])
		if self.word is not None:
			text = ''
			if self.label not in labels_to_ignore and (self.word is None or self.word not in words_to_ignore):
				if self.label not in gold_spans[(pos, pos+1)] and self.word not in gold_spans[(pos, pos+1)]:
					text = '%s(%s%s %s%s)' % (start, start_extra, self.label, self.word, end_colour)
					text += ' BROKEN WORD'
				elif len(gold_spans[(pos, pos+1)]) > 1 and parent is not None and len(parent.subtrees) > 1:
					punc_count = 0
					for subtree in parent.subtrees:
						if subtree.label in labels_to_ignore:
							punc_count += 1
					if punc_count != len(parent.subtrees) - 1:
						to_cover = gold_spans[(pos, pos+1)]
						covered = set()
						covered.add(self.word)
						missed = to_cover.difference(covered)
						text =  '%s%s(%s%s' % (start, start_missing, ' '.join(missed), end_colour)
						text += '%s(%s %s)' % (start + '\t', self.label, self.word)
						text +=  '%s)%s' % (start_missing, end_colour)
				pos += 1
			if text == '':
				text = '%s(%s %s)' % (start, self.label, self.word)
			if return_str:
				return text
			else:
				return (pos, text)
		# Handle when constituents are present
		init = pos
		children = [(pos, '')]
		for subtree in self.subtrees:
			pos, text = subtree.repr_with_corrections(gold_spans, depth + 1, pos, self)
			children.append((pos, text))
		final = pos
		text = start
		extra = (init, final) not in gold_spans
		wrong_label = False
		if extra:
			text += start_extra + '(' + self.label + end_colour
		elif self.label not in gold_spans[(init, final)]:
			if len(gold_spans[(init, final)]) == 1 and final - init == 1:
				# actually an extra bracket, just confused by POS
				text += start_extra + '(' + self.label + end_colour
				extra = True
			elif parent is not None and len(parent.subtrees) > 1:
				# check if all but one subtree is punctuation
				punc_count = 0
				for subtree in parent.subtrees:
					if subtree.label in labels_to_ignore:
						punc_count += 1
				if punc_count != len(parent.subtrees) - 1:
					to_cover = gold_spans[(init, final)]
					covered = set()
					covered.add(self.label)
					subtree = self
					while len(subtree.subtrees) == 1:
						subtree = subtree.subtrees[0]
						covered.add(subtree.label)
					covered.add(subtree.word)
					missed = to_cover.difference(covered)
					text += start_wrong_label + '(' + self.label + end_colour
					wrong_label = True
					text += ' ' + start_missing + '_'.join(missed) + end_colour
				else:
					text += start_wrong_label + '(' + self.label + end_colour
					wrong_label = True
			else:
				text += start_wrong_label + '(' + self.label + end_colour
				wrong_label = True
		elif len(gold_spans[(init, final)]) > 1 and (parent is None or len(parent.subtrees) > 1):
			# check if all but one subtree is punctuation
			punc_count = 0
			if parent is not None:
				for subtree in parent.subtrees:
					if subtree.label in labels_to_ignore:
						punc_count += 1
			if parent is None or punc_count != len(parent.subtrees) - 1:
				# this is right, but there are other that should be here too
				to_cover = gold_spans[(init, final)]
				covered = set()
				covered.add(self.label)
				subtrees = self.subtrees
				punc_count = 0
				for subtree in subtrees:
					if subtree.label in labels_to_ignore:
						punc_count += 1
				while len(subtrees) - punc_count == 1:
					cur = subtrees[0]
					for subtree in subtrees:
						if subtree.label not in labels_to_ignore:
							cur = subtree
							break
					covered.add(cur.label)
					subtrees = cur.subtrees
					if len(subtrees) == 0:
						covered.add(cur.word)
					punc_count = 0
					for subtree in subtrees:
						if subtree.label in labels_to_ignore:
							punc_count += 1
				missed = to_cover.difference(covered)
				text += '(' + self.label
				if len(missed) > 0:
					text += ' ' + start_missing + '_'.join(missed) + end_colour
			else:
				text += '(' + self.label
		else:
			# it's correct
			text += '(' + self.label

		# now consider groupings of the children
		for length in xrange(2, len(children) - 1):
			for i in xrange(len(children)):
				if i + length >= len(children):
					continue
				if children[i][0] == children[i+1][0]:
					continue
				if children[i+length][0] == children[i + length-1][0]:
					continue
				if length == len(children) - 2 and i == 1 and children[0][0] == children[1][0]:
					continue
				if length == len(children) - 2 and i == 0 and children[-1][0] == children[-2][0]:
					continue
				if (children[i][0], children[i + length][0]) in gold_spans:
					# this is a missing span
					# 1 - indent
					for k in xrange(i+1, i+length+1):
						cpos, ctext = children[k]
						ctext = '\n\t'.join(ctext.split('\n'))
						children[k] = (cpos, ctext)
					# 2 - add open bracket and label(s) to first entry
					cpos, ctext = children[i+1]
					pretext = '\n'
					pretext += (depth + 1) * '\t' + start_missing + '('
					pretext += '/'.join(gold_spans[(children[i][0], children[i + length][0])])
					pretext += end_colour
					children[i+1] = (cpos, pretext + ctext)
					# 3 - add end bracket to last entry
					cpos, ctext = children[i+length]
					ctext += start_missing + ')' + end_colour
					children[i+length] = (cpos, ctext)
		for child in children:
			text += child[1]
		if extra:
			text += start_extra + ')' + end_colour
		elif wrong_label:
			text += start_wrong_label + ')' + end_colour
		else:
			text += ')'
		if return_str:
			return text
		else:
			return (final, text)
	
	def get_spans(self, span_dict, pos=0):
		labels_to_ignore = set(["-NONE-", "TOP", ":", "."])
		words_to_ignore = set(["'","`","''", "``", "--",":",";","-",",","."])
		label = self.label
		# ignore quotes as they won't always be present
		if label in labels_to_ignore or self.word in words_to_ignore:
			return pos
		init = pos
		if len(self.subtrees) == 0:
			pos += 1
		else:
			for subtree in self.subtrees:
				pos = subtree.get_spans(span_dict, pos)
		if init != pos:
			if (init, pos) not in span_dict:
				span_dict[(init, pos)] = set()
			if not label[0] == '-':
				label = label.split('-')[0]
			label = label.split('=')[0]
			if label == 'PRT':
				label = 'ADVP' # another collins change
			if self.word is not None:
				label = self.word
			span_dict[(init, pos)].add(label)
		return pos

def read_PTB_tree(source):
	cur_text = ''
	depth = 0
	while True:
		line = source.readline()
		if line == '':
			return None
		line = line.strip()
		if line == '':
			continue
		if cur_text != '':
			cur_text += ' '
		cur_text += line
		for char in line:
			if char == '(':
				depth += 1
			elif char == ')':
				depth -= 1
		if depth == 0:
			return PTB_Tree(cur_text)
	return trees

def read_PTB_trees(source, max_sents=-1):
	if type(source) == type(''):
		source = open(source)
	trees = []
	while True:
		tree = read_PTB_tree(source)
		if tree is None:
			break
		trees.append(tree)
		if len(trees) >= max_sents > 0:
			break
	return trees

def read_CCG_tree(source):
	while True:
		line = source.readline()
		if line == '':
			return None
		else:
			line = line.strip()
		if line != '' and not line.startswith("ID"):
			line = '-LRB- -LCB-'.join(line.split('LRB {'))
			line = '-RRB- -RCB-'.join(line.split('RRB }'))
			line = '-LRB- -LRB-'.join(line.split('LRB ('))
			line = '-RRB- -RRB-'.join(line.split('RRB )'))
			tree = None
			if '<L' in line:
				tree = CCG_Tree(line)
			else:
				tree = CCG_Tree(line.strip()[1:-1].strip())
			if len(tree.subtrees) == 0 and tree.word is None:
				tree.category = None
			return tree

def read_CCG_trees(source, max_sents=-1):
	if type(source) == type(''):
		source = open(source)
	trees = []
	while True:
		tree = read_CCG_tree(source)
		if tree is None:
			break
		trees.append(tree)
		if len(trees) >= max_sents > 0:
			break
	return trees

if __name__ == '__main__':
	if len(sys.argv) != 3:
		print "Usage:\n%s [PTB,CCG] <filename>" % sys.argv[0]
		sys.exit(1)
	filename = sys.argv[2]
	trees = None
	if sys.argv[1] == 'PTB':
		trees = read_PTB_trees(filename)
	elif sys.argv[1] == 'CCG':
		trees = read_CCG_trees(filename)
	print len(trees), "trees read"
	for tree in trees:
		print tree
