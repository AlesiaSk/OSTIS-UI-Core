# -*- coding: utf-8 -*-

"""
-----------------------------------------------------------------------------
This source file is part of OSTIS (Open Semantic Technology for Intelligent Systems)
For the latest info, see http://www.ostis.net

Copyright (c) 2012 OSTIS

OSTIS is free software: you can redistribute it and/or modify
it under the terms of the GNU Lesser General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

OSTIS is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public License
along with OSTIS. If not, see <http://www.gnu.org/licenses/>.
-----------------------------------------------------------------------------
"""

import os, sys, shutil
import codecs
import re, sys, traceback
from pyparsing import Word, Literal, Forward, Regex, Group, ZeroOrMore, SkipTo, ParserElement
from pyparsing import OneOrMore, srange, Keyword, QuotedString, ParseResults, Optional, cStyleComment, ParseException
import parser
from sre_parse import parse_template

ParserElement.enablePackrat()

reKeyword = r'/!\*\s*keyword:\s*([a-zA-Z0-9_]+)\s*\*/'

arc_id = 0

mirror_connectors = [
				u'<',
				u'<..',
				u'<-',
				u'<=',
				u'<|-',
				u'</-',
				u'<~',
				u'<|~',
				u'</~',
				
				u'_<-',
				u'_<=',
				u'_<|-',
				u'_</-',
				u'_<~',
				u'_<|~',
				u'_</~'
				]
				
arc_types = {
			u">" : "sc_arc_common",
			u"<" : "sc_arc_common",
			u"->": "sc_arc_main",
			u"<-": "sc_arc_main",
			u"<>": "sc_edge",
			u"..>": "sc_arc_access",
			u"<..": "sc_arc_access",
			u'<=>': "sc_edge",
			u'_<=>': "sc_edge",
			u'=>': "sc_arc_common",
			u'<=': "sc_arc_common",
			u'=>': "sc_arc_common",
			u'<=': "sc_arc_common",
			u'_->': "sc_arc_access",
			u'_<-': "sc_arc_access",
			u'-|>': "sc_arc_access",
			u'_-|>': "sc_arc_access",
			u'<|-': "sc_arc_access",
			u'_<|-': "sc_arc_access",
			u'-/>': "sc_arc_access",
			u'_-/>': "sc_arc_access",
			u'</-': "sc_arc_access",
			u'_</-': "sc_arc_access",
			u'~>': "sc_arc_access",
			u'_~>': "sc_arc_access",
			u'<~': "sc_arc_access",
			u'_<~': "sc_arc_access",
			u'~|>': "sc_arc_access",
			u'_~|>': "sc_arc_access",
			u'<|~': "sc_arc_access",
			u'_<|~': "sc_arc_access",
			u'~/>': "sc_arc_access",
			u'_~/>': "sc_arc_access",
			u'</~': "sc_arc_access",
			u'_</~': "sc_arc_access",
			}

arc_keynodes = {
				u'<=>': "sc_edge_const",
				u'_<=>': "sc_edge_var",
				u'=>': "sc_arc_common_const",
				u'<=': "sc_arc_common_const",
				u'_=>': "sc_arc_common_var",
				u'_<=': "sc_arc_common_var",
				u'_->': "sc_arc_access_var_pos_perm",
				u'_<-': "sc_arc_access_var_pos_perm",
				u'-|>': "sc_arc_access_const_neg_perm",
				u'_-|>': "sc_arc_access_var_neg_perm",
				u'<|-': "sc_arc_access_const_neg_perm",
				u'_<|-': "sc_arc_access_var_neg_perm",
				u'-/>': "sc_arc_access_const_fuz_perm",
				u'_-/>': "sc_arc_access_var_fuz_perm",
				u'</-': "sc_arc_access_const_fuz_perm",
				u'_</-': "sc_arc_access_var_fuz_perm",
				u'~>': "sc_arc_access_const_pos_temp",
				u'_~>': "sc_arc_access_var_pos_temp",
				u'<~': "sc_arc_access_const_pos_temp",
				u'_<~': "sc_arc_access_var_pos_temp",
				u'~|>': "sc_arc_access_const_neg_temp",
				u'_~|>': "sc_arc_access_var_neg_temp",
				u'<|~': "sc_arc_access_const_neg_temp",
				u'_<|~': "sc_arc_access_var_neg_temp",
				u'~/>': "sc_arc_access_const_fuz_temp",
				u'_~/>': "sc_arc_access_var_fuz_temp",
				u'</~': "sc_arc_access_const_fuz_temp",
				u'_</~': "sc_arc_access_var_fuz_temp",
			}



class Converter:
	
	def __init__(self):
		self.group_processors = {
						parser.AliasGroup: self.processAliasGroup,
						parser.KeywordGroup: self.processKeywordGroup,
						parser.SimpleIdentifierGroup: self.processSimpleIdentifierGroup,
						parser.UrlGroup: self.processUrlGroup,
						parser.ContentGroup: self.processContentGroup,
						parser.SetGroup: self.processSetGroup,
						parser.OSetGroup: self.processOSetGroup,
						parser.TripleGroup: self.processTripleGroup,
						parser.SimpleSentenceGroup: self.processSimpleSentenceGroup,
						parser.SynonymGroup: self.processSynonymGroup,
						parser.SentenceGroup: self.processSentenceGroup,
						parser.IdtfWithIntGroup: self.processIdtfWithIntGroup,
						parser.InternalGroup: self.processInternalGroup,
						parser.InternalListGroup: self.processInternalListGroup
						}
		
		self.comments = {}
		self.triples = []
	
		# list of contents, that need to be written
		self.link_contents = {}
	
		# synonyms map. For each key in this map we contains list of all synonym elements
		self.synonyms = {}
		# aliases map
		self.aliases = {}
	
		self.set_count = 0
		self.oset_count = 0
		self.arc_count = 0
		self.link_count = 0
	
	def generate_set_idtf(self):
		self.set_count += 1
		return ".set_%d" % self.set_count
	
	def generate_oset_idtf(self):
		self.oset_count += 1
		return ".oset_%d" % self.oset_count
	
	def generate_link_idtf(self):
		self.link_count += 1
		return 'data/link_%d' % self.link_count
	
	def generate_arc_idtf(self, type = None, include_into_set = True):
		self.arc_count += 1
		
		res = None
		if type is not None:
			if arc_types.has_key(type):
				res = arc_types[type] + "#" + str(self.arc_count)
		
		if res is None:
			res = ".arc_%d" % self.arc_count
			
		if include_into_set and arc_keynodes.has_key(type):
			self.append_sentence(arc_keynodes[type], self.generate_arc_idtf('->', False), res, False)
			
		return res
	
	def process_arc_connector(self, connector):
		assert connector != "="
		global arc_id
		
		# todo fixme
		res = "sc_arc_common#%d" % arc_id
		arc_id += 1
		
		return res
	
	def resolve_identifier(self, group):
		"""Resolves identifiers for different groups
		"""
		
		key = str(group)
		if self.aliases.has_key(key):
			return self.aliases[key]
		
		alias = str(group)
		if isinstance(group, parser.OSetGroup):
			alias = self.generate_oset_idtf()
		elif isinstance(group, parser.SetGroup):
			alias = self.generate_set_idtf()
			
		self.aliases[key] = alias
		
		return alias
	
	def append_synonyms(self, idtf1, idtf2):
		"""Appends two identifiers as synonyms into map
		"""
		pass
	
	def check_predicate_mirror(self, predicate):
		
		return (predicate in mirror_connectors)
	
	def append_sentence(self, subject, predicate, object, isMirrored):
		"""Appends new scs-level 1 sentence into list
		"""
		if not isMirrored:
			self.triples.append((subject, predicate, object))
		else:
			self.triples.append((object, predicate, subject))
	
	# ---------------------------------------
	def processSimpleIdentifierGroup(self, group):
		return self.resolve_identifier(group)
		
	def processUrlGroup(self, group):
		pass
		
	def processKeywordGroup(self, group):
		return group
		
	def processSimpleSentenceGroup(self, group):
		"""Process scs-level 1 sentences
		"""
		self.append_sentence(group.subject, group.predicate, group.object, False);
	
	def processIdtfWithIntGroup(self, group):
		"""Process identifier with internal sentence group
		"""
		subject_idtf = self.resolve_identifier(group.idtf)
		self.parse_tree(group.idtf)
		
		internal_list = group.internal
		if internal_list is not None:
			for sentence in internal_list.sentences:
				
				for obj in sentence.object:
					object_idtf = self.resolve_identifier(obj)
					attributes = sentence.attrs
					arc_idtf = self.generate_arc_idtf(sentence.predicate)
					
					self.append_sentence(subject_idtf, arc_idtf, object_idtf, self.check_predicate_mirror(sentence.predicate))
					
					# write attributes
					for attr in attributes:
						attr_idtf = self.resolve_identifier(attr)
						self.append_sentence(attr_idtf, self.generate_arc_idtf('->'), arc_idtf, False)
				
				
	def processInternalGroup(self, group):
		return group
		
	def processInternalListGroup(self, group):
		return group
		
	def processTripleGroup(self, group):
		return group
		
	def processAliasGroup(self, group):
		"""Just resolve identifier for alias
		"""
		return self.resolve_identifier(group)
		
	def processContentGroup(self, group):
		"""Store link content for saving
		"""
		if len(group.value) > 1 and group.value[0] == u'*' and group.value[-1] == u'*':
			data = group.value[1:-1]
			
			# create new converter and build data
			converter = Converter()
			converter.link_contents = self.link_contents
			converter.synonyms = self.synonyms
			converter.triples = self.triples
			converter.aliases = self.aliases
			converter.set_count = self.set_count
			converter.oset_count = self.oset_count
			converter.arc_count = self.arc_count
			converter.link_count = self.link_count
			
			converter.parse_string(data)
			
			self.link_contents = converter.link_contents
			self.synonyms = converter.synonyms
			self.triples = converter.triples
			self.aliases = converter.aliases
			self.set_count = converter.set_count
			self.oset_count = converter.oset_count
			self.arc_count = converter.arc_count
			self.link_count = converter.link_count
		
		
		link_idtf = self.generate_link_idtf()
		self.link_contents[link_idtf] = group.value
		group.value = '"file://%s"' % link_idtf
		
		return link_idtf
		
	def processSetGroup(self, group):
		"""Process set
		"""
		idtf = self.resolve_identifier(group)
		for item in group.items:
			attributes = item[0]
			object = item[1]
			
			self.parse_tree(object)
			arc_idtf = self.generate_arc_idtf('->')
			self.append_sentence(idtf, arc_idtf, self.resolve_identifier(object), False)
			
			for attr in attributes:
				attr_idtf = self.resolve_identifier(attr)
				self.append_sentence(attr_idtf, self.generate_arc_idtf('->'), arc_idtf, False)
		
		
	def processOSetGroup(self, group):
		"""Process ordered tree
		"""
		idtf = self.resolve_identifier(group)
		item_count = 0
		for item in group.items:
			attributes = item[0]
			object = item[1]
			item_count += 1
			
			self.parse_tree(object)
			arc_idtf = self.generate_arc_idtf('->')
			self.append_sentence(idtf, arc_idtf, self.resolve_identifier(object), False)
			# add order attribute
			self.append_sentence("%d_" % item_count, self.generate_arc_idtf('->'), arc_idtf, False)
			
			for attr in attributes:
				attr_idtf = self.resolve_identifier(attr)
				self.append_sentence(attr_idtf, self.generate_arc_idtf('->'), object, False)
		
	def processSentenceGroup(self, group):
		"""Process sentence for scs-levels 2-6
		"""
		subject = group.subject
		predicate = group.predicate
		attributes = group.attrs
		objects = group.object
		
		self.parse_tree(subject)
		for obj in objects:
			# process object
			self.parse_tree(obj)
			# resolve object identifier
			obj_idtf = self.resolve_identifier(obj)
			
			# connect subject with object
			arc_idtf = self.generate_arc_idtf(predicate)
			self.append_sentence(subject, arc_idtf, obj_idtf, self.check_predicate_mirror(predicate))
			
			# connect attributes
			for attr in attributes:
				self.parse_tree(attr)
				attr_idtf = self.resolve_identifier(attr)
				self.append_sentence(attr_idtf, self.generate_arc_idtf('->'), arc_idtf, False)
	
	def processSynonymGroup(self, group):
		pass
	
		     
	def get_string_value(self, element):
		"""Returns string representation of specified element
		from parser results
		"""
		pass
	
	def parse_skip(self, group):
		pass
	
	def parse_simple_sentence(self, group):
		pass
		
		
	# -----------------------------------------	
	def parse_tree(self, tree):
		"""Parse results tree
		"""
		
		if isinstance(tree, ParseResults):
			for item in tree:
				self.parse_tree(item)
		else:
			self.group_processors[tree.__class__](tree)
		
	
	def parse_string(self, data):
		"""Parse specified string
		"""
		try:
			result = parser.syntax().parseString(data.decode('utf-8'), parseAll = True)
			self.parse_tree(result)
		except ParseException, err:
			print err.line
			print " "*(err.column-1) + "^"
			print err
	
	def parse_directory(self, path):
		"""Parse specified directory
		"""
		for root, dirs, files in os.walk(path):
			print root
			for f in files:
				
				# skip none scs files
				base, ext = os.path.splitext(f)
				if ext != '.scs':
					continue
				
				file_path = os.path.join(root, f)
				
				self.comments[len(self.triples)] = file_path
				
				# parse file
				print "Parse %s" % file_path
				fh = open(file_path, 'r')
				self.parse_string(fh.read())
				fh.close()
				
	def write_to_fs(self, path):
		"""Writes converted data into specified directory
		"""
		if os.path.exists(path):
			shutil.rmtree(path)
			
		os.makedirs(path)
		
		count = 0
		with codecs.open(os.path.join(path, "data.scs"), "w", "utf-8") as output:
			for t in self.triples:
				
				if self.comments.has_key(count):
					output.write('\n/* --- %s --- */\n' % self.comments[count])
				
				output.write("%s | %s | %s;;\n" % t)
				count += 1
			output.close()
				
		# write contents
		os.makedirs(os.path.join(path, "data"))
		for num, data in self.link_contents.items():
			f = open(os.path.join(path, str(num)), "w")
			f.write(data)
			f.close()

if __name__ == "__main__":

	if len(sys.argv) < 3:
		print "Usage: python converter.py <input dir> <output dir>"
		sys.exit(0)
	
	converter = Converter()
	converter.parse_directory(sys.argv[1])
	print "Write output..."
	converter.write_to_fs(sys.argv[2])
