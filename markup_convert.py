#!/usr/bin/env python

# Convert using a markedup-style file
import sys, re
import trees, category, rule

log_out = sys.stdout
contains_bs = False

VERBOSE = False
VERBOSE = True
def verbose_print(text):
	if VERBOSE:
		print >> log_out, text

markup_info = {}
def read_markup(markup_file):
	global markup_info
	# Only read the markup info once
	if len(markup_info) == 0:
		# (NP\NP)/NP
		#   2 ((NP{Y}\NP{Y}<1>){_}/NP{Z}<2>){_}
		#   (PP 0 2)
		#   (NP 1 0)
		#
		cur = []
		for line in markup_file:
			line = line.strip()
			if len(line) > 0:
				if line[0] == '#':
					continue
				cur.append(line)
			else:
				if len(cur) > 0:
					label = cur.pop(0)
					markup_info[label] = cur
					cur = []

# Find the bracket that matches the one at text[start_index]
def get_balanced_point(text, start_index, deeper, shallower):
	depth = 0
	for i in xrange(start_index, len(text)):
		if text[i] == deeper:
			depth += 1
		if text[i] == shallower:
			depth -= 1
		if depth == 0:
			return i
	return -1

UNIQUE_ID = 100
class Schema:
	def __init__(self, lines, uniqued=False, argument=None, source_node=None):
		global UNIQUE_ID
		self.source = source_node
		text = '(TEMP 0)'
		self.parent = []
		self.children = []
		self.rule = 'unk'
		self.get_label_from_argument = False
		if type(lines) == type(''):
			text = lines
			self.parent = []
		elif type(lines) == type([]):
			text = lines[0]
			# only one parent, which is the schema this will insert into
			self.parent = lines[1:]
			if 'arg' in text:
				# check rules
				text = None
				self.parent = []
				to_parent = False
				for line in lines:
					if to_parent:
						self.parent.append(line)
					else:
						if 'arg:default' in line:
							if text is None:
								text = line
							to_parent = True
						elif argument is not None:
							constraint = line.split('arg:')[1].split(':')[0]
							if '(' not in constraint:
								if type(argument) == type(self) and constraint == argument.label:
									text = line
								elif type(argument) == type('') and argument[1:].split()[0] == constraint:
									text = line
							elif type(argument) == type(self):
								labels = constraint[1:-1].split()
								children = []
								for child in argument.children:
									if type(child) == type(self) and child.label in ":,.;":
										continue
									elif type(child) == type('') and child[1] in ":,.;":
										continue
									elif type(child) == type(''):
										children.append(child[1:].split()[0])
									else:
										children.append(child.label)
								if '...' in labels:
									if len(labels)-1 <= len(children):
										use = True
										if labels[0] == '...':
											for i in xrange(len(labels)-1):
												if labels[-1-i] != children[-1-i]:
													use = False
										elif labels[-1] == '...':
											for i in xrange(len(labels)-1):
												if labels[i] != children[i]:
													use = False
										else:
											print '... in the middle of arguments is not yet supported'
											use = False
										if use:
											text = line
								elif len(labels) == len(children):
									use = True
									for i in xrange(len(labels)):
										if labels[i] != children[i]:
											use = False
									if use:
										text = line
		if text[-1] not in ')}':
			text = ' '.join(text.split(':')[0].split()[:-1])

		# change numbers in text to be a unique ID
		text = text.strip()
		self.zero = None
		if not uniqued:
			mapping = {}
			ntext = ''
			pos = 0
			while pos < len(text):
				if text[pos] in '1234567890':
					start = pos
					end = pos
					while text[end] in '1234567890':
						end += 1
					end -= 1
					num = int(text[start:end+1])
					if num not in mapping:
						mapping[num] = UNIQUE_ID
						UNIQUE_ID += 1
					ntext += str(mapping[num])
					if num == 0:
						self.zero = mapping[num]
					pos = end
				else:
					ntext += text[pos]
				pos += 1
			text = ntext
		self.schema = text
		# determine if this node is to be deleted
		self.delete_on_adoption = self.schema.startswith('{(') and self.schema.endswith(')}')
		self.label = self.schema.split()[0].strip('{(')
		if '*' in self.label:
			self.get_label_from_argument = True
			self.label = self.label[:-1]
		self.children = [] # the tree
		self.incomplete = {} # elements somewhere in the tree that are to be filled
		tschema = ')'.join('('.join(self.schema.split('(')[1:]).split(')')[:-1])
		pos = len(tschema.split()[0]) # jump to after the label
		while pos < len(tschema):
			if tschema[pos] == '(':
				# Create a subtree for this bracket set
				balance = get_balanced_point(tschema, pos, '(', ')')
				subschema = Schema(tschema[pos:balance+1], uniqued=True, source_node=self.source)
				self.children.append(subschema)
				for key in self.children[-1].incomplete:
					if key not in self.incomplete:
						self.incomplete[key] = []
					self.incomplete[key] += self.children[-1].incomplete[key]
				pos = balance
			elif tschema[pos] == ' ':
				if tschema[pos + 1] != '(':
					left = pos + 1
					right = left
					while right < len(tschema) and tschema[right] in '1234567890{}<>':
						right += 1
					right -= 1
					text = tschema[left:right+1]
					self.children.append(text)
					num = int(text.strip('{}<>'))
					if num not in self.incomplete:
						self.incomplete[num] = []
					self.incomplete[num].append((text, self))
					pos = right
			pos += 1

	def PTB_tree(self):
		text = '('
		text += self.label + ' '
		child_texts = []
		for child in self.children:
			if type(child) != type(''):
				child_texts.append(child.PTB_tree())
			elif '(' in child:
				child_texts.append(child)
		if len(child_texts) == 0:
			return ''
		text += ' '.join(child_texts)
		if self.delete_on_adoption:
			return ' '.join(child_texts)
		text += ')'
		return text

	def __repr__(self):
		child_ans = []
		for child in self.children:
			if type(child) == type(''):
				child_ans.append(child)
			else:
				child_ans.append('obj')
		ans = ' schema: ' + self.schema + '  cur: '
		if self.delete_on_adoption:
			ans += '{'
		ans += '(' + self.label + ' ' + ' '.join(child_ans) + ')'
		if self.delete_on_adoption:
			ans += '}'
		ans += '  incomplete:'
		for thing in self.incomplete:
			ans += ' ('
			ans += str(self.incomplete[thing][0][0])
			if self.incomplete[thing][0][1] == self:
				ans += ', self)'
			else:
				ans += ', other)'
		for schema in self.parent:
			ans += '\n' + schema
		return ans

	def insert(self, ID, value):
		if ID is None:
			print >> log_out, "Insert with None ID requested"
			print >> sys.stderr, "Insert with None ID requested"
			return
		if ID != self.zero and self.get_label_from_argument:
			try:
				if type(value) != type(''):
					if not value.delete_on_adoption:
						self.label = value.label
			except:
				pass
		original = value
		keep_left = False
		delete_left = False
		keep_right = False
		delete_right = False
		stop = False
		entries = self.incomplete.pop(ID)
		for entry in entries:
			value = original
			text = entry[0]
			parent = entry[1]
			# find the position
			index = 0
			while index < len(parent.children):
				if parent.children[index] == text:
					break
				index += 1
			del parent.children[index]
			if text[0] == '>':
				if not keep_left:
					keep_left = True
					delete_left = False
				else:
					keep_left = False
					delete_left = True
				text = text[1:]
			if text[-1] == '<':
				if not delete_right:
					delete_right = True
					keep_right = False
				else:
					delete_right = False
					keep_right = True
				text = text[:-1]
			if text[0] == '{' and text[-1] == '}':
				try:
					if len(value.children) > 0:
						value = value.children
				except:
					# doesn't have sub=parts, ignore deletion {}
					# can happen if we have a list, or a string
					pass
				text = text[1:-1]
			if type(value) == type(self) and value.delete_on_adoption:
				value = value.children
			if stop:
				parent.children.insert(index, '')
			else:
				if type(value) != type([]):
					parent.children.insert(index, value)
					if keep_left or delete_left or keep_right or delete_right:
						stop = True	
				else:
					if keep_left:
						parent.children.insert(index, value[0])
					elif delete_left:
						parent.children = parent.children[:index] + value[1:] + parent.children[index:]
					elif keep_right:
						parent.children.insert(index, value[-1])
					elif delete_right:
						parent.children = parent.children[:index] + value[:-1] + parent.children[index:]
					else:
						parent.children = parent.children[:index] + value + parent.children[index:]
		# When complete pass self to parent
		return self

	def set_zero(self, thing):
		self.insert(self.zero, thing)
		return self

	def get_argument_key(self, key_no=0):
		if len(self.incomplete) == 0:
			print >> log_out, "Trying to insert into a complete schema!"
			print >> sys.stderr, "Trying to insert into a complete schema!"
		else:
			for val in self.incomplete:
				if key_no == 0:
					return val
				else:
					key_no -= 1
		return None

	# fa.f and fa.b - Function application
	def fa(self, argument, combinator):
		# fill the incomplete argument with the argument
		key = self.get_argument_key()
		if key is not None:
			self.insert(key, argument)
			if 'conj1' ==  argument.rule:
				pos = 0
				while pos < len(self.children):
					if type(self.children[pos]) == type(self) and self.children[pos].label == 'NX':
						child = self.children[pos]
						self.children = self.children[:pos] + child.children + self.children[pos+1:]
						pos += len(child.children) - 1
					pos += 1
		else:
			if combinator == 'fa.f':
				return self.glom(argument)
			else:
				return argument.glom(self)
		return self
	
	# fc.f and fc.b - Function composition
	def fc(self, argument):
		# fill the incomplete argument with the argument
		self.insert(self.get_argument_key(), argument)
		# add the unfilled arguments of the argument to the incomplete arguments of
		# self
		for key in argument.incomplete:
			self.incomplete[key] = []
			for entry in argument.incomplete[key]:
				used = False
				for child in self.children:
					if child == entry[0]:
						used = True
						self.incomplete[key].append((entry[0], self))
						break
				if not used:
					self.incomplete[key].append((entry[0], entry[1]))
###					if category.divide(self.source.category)[1] == '/':
###						self.children.append(entry[0])
###					else:
###						self.children.insert(0, entry[0])
		argument.incomplete = {}
		return self
	
	# bs.f and bs.b - Crossed substitution 
	def bs(self, argument):
		print 'bs is not implemented - this should not have been called'
		print >> sys.stderr, 'bs is not implemented - this should not have been called'
		return nlevel
	
	def is_empty(self):
		for child in self.children:
			if type(child) == type(self):
				if not child.is_empty():
					return False
			elif child[0] == '(':
				return False
		return True

	# cc.b - Backwards crossed composition
	def back_cross(self, argument):
		left = get_next_incomplete_schema(self, argument)
		pos, children = left.get_last_partial_subtree()
		if pos < 0:
			pos = 0
			children = left.children
		argument = get_next_incomplete_schema(argument, None)
		left.parent = argument.parent
		non_empty_children = []
		for child in argument.children:
			if type(child) == type(left):
				if not child.is_empty():
					non_empty_children.append(child)
			elif child[0] == '(':
				non_empty_children.append(child)
		if len(non_empty_children) == 1:
			argument = non_empty_children[0]
		children.insert(pos, argument)
		return left
	
	# Type raising
	def tr(self, child):
		if self.label[0] == child.label[0] and not self.delete_on_adoption:
			child.delete_on_adoption = True
		self.set_zero(child)
		return self

	# one of the special binary combination rules defined in rule.py
	def special_binary(self, right, new_schemas):
		new_schemas.set_zero(self)
		new_schemas.insert(new_schemas.get_argument_key(), right)
		return new_schemas

	# one of the special unary combination rules defined in rule.py
	def special_unary(self, unary_schema):
		unary_schema.set_zero(self)
		return unary_schema
	
	def conj_part1(self, right):
		# create a new node, with these two as children
		if right.label in ['Nslash', 'Nnum']:
			right.delete_on_adoption = True
		if right.label == 'N':
			if len(right.children) > 1:
				right.label = 'NX'
			else:
				right.delete_on_adoption = True
		left = self
		if len(left.children) == 1:
			left = left.children[0]

		# detect a list and set right to be deleted
		is_list = False
		if len(right.children) > 2:
			if type(right.children[1]) == type(left):
				if right.children[1] == left or (left == '(, ,)' and 'CC' in right.children[1]):
					if type(right.children[0]) == type(self) == type(right.children[2]):
						if right.children[0].label == right.children[2].label:
							is_list = True
		if is_list:
			right.delete_on_adoption = True

		nlevel = Schema(['(%s 0 1)' % right.label] + right.parent, source_node=right.source)
		nlevel.set_zero(left)
		nlevel.insert(nlevel.get_argument_key(), right)

		if nlevel.label == 'TEMP':
			nlevel.delete_on_adoption = True
		# move unfilled arguments
		for key in right.incomplete:
			nlevel.incomplete[key] = []
			for entry in right.incomplete[key]:
				text = entry[0]
				parent = entry[1]
				if text == parent.children[-1]:
					if text in nlevel.children:
						nlevel.children.remove(text)
					nlevel.children.append(text)
				else:
					if text in nlevel.children:
						nlevel.children.remove(text)
					nlevel.children.insert(0, text)
				nlevel.incomplete[key].append((text, nlevel))
		nlevel.rule = 'conj1'
		return nlevel
	
	def conj_part2(self, right):
		if self.label in "~!@#$%^&*()_+{}|:<>?,./;'[]\=-`" or self.label in ['LRB', 'RRB']:
			# glom self on instead
			return self.glom(right)
		# check labels
		if self.label in ['Nslash', 'Nnum']:
			self.delete_on_adoption = True
		if self.label == 'N':
			if len(self.children) > 1:
				self.label = 'NX'
			else:
				self.delete_on_adoption = True
		if self.label != 'NX':
			pos = 0
			while pos < len(right.children):
				if type(right.children[pos]) == type(right) and right.children[pos].label == 'NX':
					child = right.children[pos]
					right.children = right.children[:pos] + child.children + right.children[pos+1:]
					pos += len(child.children) - 1
				pos += 1
		nlabel = self.label
		if nlabel != right.label:
			nlabel = 'UCP'

		# check for VPs that are being conjed
		try:
			remove_VPs = False
			print >> log_out, self.label, self.children[0]
			if self.label == 'VP' and 'VB' in self.children[0]:
				all_empty = True
				print >> log_out, self.children[1:]
				for child in self.children[1:]:
					if type(child) != type('') or child[0] == '(':
						all_empty = False
				if all_empty:
					print >> log_out, right.label, right.children[1].label, right.children[1].children[0]
					if right.label == 'VP' and right.children[1].label == 'VP' and 'VB' in right.children[1].children[0]:
						all_empty = True
						print >> log_out, right.children[1].children[1:]
						for child in right.children[1].children[1:]:
							if type(child) != type('') or child[0] == '(':
								all_empty = False
						if all_empty:
							remove_VPs = True
			if remove_VPs:
				self.delete_on_adoption = True
				right.children[1] = right.children[1].children[0]
		except:
			pass

		nlevel = Schema(['(%s 0 {1})' % nlabel] + self.parent, source_node=self.source)
		nlevel.set_zero(self)
		nlevel.insert(nlevel.get_argument_key(), right)
		if nlevel.label == 'TEMP':
			nlevel.delete_on_adoption = True
		# move unfilled arguments
		for key in self.incomplete:
			nlevel.incomplete[key] = []
			for entry in self.incomplete[key]:
				text = entry[0]
				parent = entry[1]
				if text == parent.children[-1]:
					if text in nlevel.children:
						nlevel.children.remove(text)
					nlevel.children.append(text)
				elif text == parent.children[0]:
					if text in nlevel.children:
						nlevel.children.remove(text)
					nlevel.children.insert(0, text)
				else:
					if text in nlevel.children:
						nlevel.children.remove(text)
					continue
				nlevel.incomplete[key].append((text, nlevel))
		nlevel.rule = 'conj2'
		return nlevel

	def get_first_partial_subtree(self):
		if len(self.children) == 0:
			return (0, [])
		if type(self.children[0]) == type('') and self.children[0][0] == '(':
			return (0, self.children)
		for i in xrange(len(self.children)):
			child = self.children[i]
			if type(child) == type(self):
				pos, children = child.get_first_partial_subtree()
				if pos > 0:
					return (pos, children)
				elif pos == 0:
					return (i, self.children)
			elif type(child) == type('') and child[0] == '(':
				return (i, self.children)
		return (-1, [])

	def get_last_partial_subtree(self):
		if len(self.children) == 0:
			return (0, [])
		if type(self.children[-1]) == type('') and self.children[-1][0] == '(':
			return (len(self.children), self.children)
		for i in xrange(len(self.children) - 1, -1, -1):
			child = self.children[i]
			if type(child) == type(self):
				pos, children = child.get_last_partial_subtree()
				if 0 < pos < len(children):
					return (pos, children)
				elif pos == len(children):
					return (i+1, self.children)
			elif type(child) == type('') and len(child) > 0 and child[0] == '(':
				return (i+1, self.children)
		return (-1, [])

	# misc - Just glom on the random stuff
	def glom(self, right, keep_right=None):
		left = self
		if keep_right is None:
			keep_right = left.label in "~!@#$%^&*()_+{}|:<>?,./;'[]\=-`" or left.label in ['LRB', 'RRB']
		if keep_right:
			# glom left on to left of right
			if len(left.children) == 1:
				left = left.children[0]
			pos, children = right.get_first_partial_subtree()
			if pos < 0:
				pos = 0
				children = right.children
			children.insert(pos, left)
			return right
		else:
			# glom right on to right of left
			if len(right.children) == 1:
				right = right.children[0]
			if len(left.incomplete) != 0:
				pos, children = left.get_last_partial_subtree()
				if pos < 0:
					pos = 0
					children = left.children
				children.insert(pos, right)
			else:
				left.children.append(right)
###				nlevel = Schema(['{(TEMP 0 1)}'] + left.parent, source_node=left.source)
###				nlevel.set_zero(left)
###				key = nlevel.get_argument_key()
###				nlevel.insert(key, right)
###				return nlevel
			return left

def fallback_schema(cat):
	rules = ['{(TEMP 0)}']
	while '/' in cat or '\\' in cat:
		parts = category.divide(cat)
		if parts[1] == '/':
			rules.append("(NP 0 1)")
		else:
			rules.append("(NP 1 0)")
		cat = parts[0]
		plain_cat = cat
		if plain_cat not in markup_info:
			plain_cat = category.strip_square_brackets(cat)
		if plain_cat in markup_info:
			markup_lines = markup_info[plain_cat][1:]
			if '/' not in markup_lines[0] and '\\' not in markup_lines[0]:
				rules += markup_lines
				return rules
	return rules

ANGLE_RE = re.compile('<[^>]*>')
def markup_to_schemas(lines, cat=None, source=None):
	unannotated = False
	if lines == []:
		unannotated = True
	else:
		for line in lines[1:]:
			if '\\' in line or '/' in line:
				cat_to_print = lines[0].strip().split()[1]
				cat_to_print = category.strip_braces(cat_to_print)
				cat_to_print = ''.join(cat_to_print.split('[X]'))
				cat_to_print = ANGLE_RE.sub('', cat_to_print)
				cat_to_print = category.remove_extra_brackets(cat_to_print)
				print >> log_out, 'Unannotated category:', cat_to_print
				print >> sys.stderr, 'Unannotated category:', cat_to_print
				unannotated = True
				break
	if unannotated:
		lines = fallback_schema(cat)
	pos = None
	word = None
	if source is not None:
		pos = source.pos
		word = source.word
	used = False
	nlines = []
	for i in xrange(1, len(lines)):
		line = lines[i].strip()
		if line[-1] not in ')}':
			use = True
			if 'POS' in line:
				if pos is None or pos not in line.split('POS:')[1].split()[0].split(','):
					use = False
				if not used and 'POS:default' in line:
					use = True
			if 'Word' in line:
				if word is None or word not in line.split('Word:')[1].split()[0].split(','):
					use = False
				if not used and 'Word:default' in line:
					use = True
			if use:
				nlines.append(line)
				if 'arg' not in line or 'arg:default:' in line:
					used = True
		else:
			nlines.append(line)
			used = False
		if 'POS:default' in line or 'Word:default' in line:
			if 'arg' not in line or 'arg:default:' in line:
				used = False
	return Schema(nlines, source_node=source)

def get_next_incomplete_schema(schema, arg):
	while len(schema.incomplete) == 0 and len(schema.parent) > 0:
		parent = Schema(schema.parent, argument=arg, source_node=schema.source)
		parent.set_zero(schema)
		schema = parent
	return schema

def apply_markup(source, markup, top=True):
	global contains_bs
	# Bottom up, so get the results from below
	children = []
	for subtree in source.subtrees:
		children.append(apply_markup(subtree, markup, False))
	combinator = source.rule
	result = None
	verbose_print('using %s combiantor rule' % combinator)
	for child in children:
		verbose_print('%s' % child.PTB_tree())
		verbose_print(child.__repr__())
	if combinator == 'lex' or combinator == 'type':
		source_category = source.category
		if source_category not in markup_info:
			source_category = category.strip_square_brackets(source.category)
		schema_text = []
		if source_category not in markup_info:
			print >> log_out, "Missing category:", source.category, "asked for by", combinator
			print >> sys.stderr, "Missing category:", source.category, "asked for by", combinator
		else:
			schema_text = markup_info[source_category]
		schema = markup_to_schemas(schema_text, source.category, source)
		if combinator == 'lex':
			result = schema.set_zero("(%s %s)" % (source.pos, source.word))
		elif combinator == 'type':
			verbose_print("Type schema:")
			verbose_print(schema.__repr__())
			result = schema.tr(children[0])
	elif combinator == 'conj1':
		result = children[0].conj_part1(children[1])
	elif combinator == 'conj2':
		result = children[0].conj_part2(children[1])
	elif combinator == 'unary':
		unary_rule = rule.get_unary(source.subtrees[0].category, source.category, markup_info)
		if unary_rule is None:
			unary_rule = fallback_schema(source.category)
		schemas = markup_to_schemas(['None'] + unary_rule, source=source)
		verbose_print("Unary schema:")
		verbose_print(schemas.__repr__())
		result = children[0].special_unary(schemas)
	elif combinator in ['binary', 'bs.f', 'bs.b']:
		binary_rule = rule.get_binary_for_markedup(source.subtrees[0].category, source.subtrees[1].category, source.category, markup_info)
		if binary_rule is None:
			binary_rule = ['(VP 0 1)'] + fallback_schema(source.category)
		schemas = markup_to_schemas(['None'] + binary_rule, source=source)
		verbose_print("Binary schema:")
		verbose_print(schemas.__repr__())
		control = get_next_incomplete_schema(children[0], children[1])
		result = control.special_binary(children[1], schemas)
	elif combinator == 'fa.f':
		control = get_next_incomplete_schema(children[0], children[1])
		result = control.fa(children[1], combinator)
	elif combinator == 'fa.b':
		control = get_next_incomplete_schema(children[1], children[0])
		result = control.fa(children[0], combinator)
	elif combinator == 'fc.f':
		control = get_next_incomplete_schema(children[0], children[1])
		argument = get_next_incomplete_schema(children[1], None)
		result = control.fc(argument)
	elif combinator == 'fc.b':
		control = get_next_incomplete_schema(children[1], children[0])
		argument = get_next_incomplete_schema(children[0], None)
		result = control.fc(argument)
	elif combinator == 'cc.b':
		control = get_next_incomplete_schema(children[0], children[1])
		result = control.back_cross(children[1])
	elif combinator == 'misc':
		if len(source.subtrees) == 2:
			cur = category.strip_square_brackets(source.category)
			left = category.strip_square_brackets(source.subtrees[0].category)
			right = category.strip_square_brackets(source.subtrees[1].category)
			if cur != left and cur != right:
				print >> log_out, "miscing an unknown category:", source.category,
				print >> log_out, "from", source.subtrees[0].category, "and", source.subtrees[1].category
				print >> sys.stderr, "miscing an unknown category:", source.category,
				print >> sys.stderr, "from", source.subtrees[0].category, "and", source.subtrees[1].category
				binary_rule = fallback_schema(source.category)
				schemas = markup_to_schemas(['None','(NP 0 1)'] + binary_rule, source=source)
				verbose_print("Misc Binary schema:")
				verbose_print(schemas.__repr__())
				result = children[0].special_binary(children[1], schemas)
			else:
				# check if this forms a PRN
				words = source.all_word_yield()[1].split()
				left_word = words[0]
				right_word = words[-1]
				verbose_print(left_word + ' ' + right_word)
				use_PRN = False
				if not top:
					if left_word == ',' and right_word == ',':
						use_PRN = True
					elif left_word == '--' and  right_word == '--':
						use_PRN = True
					elif left_word == '-LRB-' and right_word == '-RRB-':
						use_PRN = True
				result = children[0].glom(children[1], cur == right)
				if use_PRN:
					old_label = result.label
					result.label = 'PRN'
					result.delete_on_adoption = False
					nlevel = Schema(['(%s 0)' % old_label] + result.parent, source_node=source)
					if old_label == 'TEMP':
						nlevel = Schema(['{(%s 0)}' % old_label] + result.parent, source_node=source)
					nlevel.set_zero(result)
					nlevel.incomplete = result.incomplete
					result = nlevel
		else:
			print >> sys.stderr, 'misc combinator is not handled'
	verbose_print('resolved: %s' % result.PTB_tree())
	verbose_print(result.__repr__())
	verbose_print('')
	return result

def remove_N(tree):
	nsubtrees = []
	for subtree in tree.subtrees:
		sub = remove_N(subtree)
		if type(sub) == type([]):
			nsubtrees += sub
		else:
			nsubtrees.append(sub)
	tree.subtrees = nsubtrees
	if tree.label == 'N' or tree.label == 'Nslash' or tree.label == 'Nnum':
		return tree.subtrees
	else:
		return tree

def remove_repetition(tree):
	# recurse and update subtrees
	if len(tree.subtrees) > 0:
		nsubtrees = []
		for subtree in tree.subtrees:
			nsubtrees.append(remove_repetition(subtree))
		tree.subtrees = nsubtrees

	# look down and remove this if it is repeated
	repeats = False
	cur = tree
	label = cur.label
	while len(cur.subtrees) == 1:
		cur = cur.subtrees[0]
		if cur.label == label:
			repeats = True
			break
	if repeats:
		print >> log_out, 'duplicate!'
		print >> log_out, tree.one_line_repr()
		print >> log_out, cur.one_line_repr()
		tree = tree.subtrees[0]
	
	return tree

def convert(source, argv, log=sys.stdout):
	global markup_info, contains_bs, log_out, VERBOSE
	log_out = log
	VERBOSE = '-verbose' in ' '.join(argv)
	filename = ' '.join(argv).split(' -method')[1].split()[1]
	read_markup(open(filename))

	contains_bs = False
	auto_schema = apply_markup(source, markup_info)

	###################
	# Extra cleanup
	# i.e. hacks that don't fit within the main architecture
	###################
	auto_ptb = trees.PTB_Tree('(ROOT ' + auto_schema.PTB_tree() + ')')
	verbose_print('before cleaning: %s' % auto_ptb)

	# remove remaining N
	auto_ptb = remove_N(auto_ptb)

	# collapse repetitions
	auto_ptb = remove_repetition(auto_ptb)

	verbose_print('cleaned: %s' % auto_ptb)
	verbose_print('')
	return (not contains_bs, auto_ptb, auto_schema)

if __name__ == '__main__':
	if len(sys.argv) < 2:
		print "Usage:\n%s -method_info <markup_file>" % sys.argv[0]
		sys.exit(1)
	print "Please enter CCG trees:"
	for line in sys.stdin:
		print convert(trees.CCG_Tree(line.strip()), sys.argv)
