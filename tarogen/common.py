from pygenic import *
from tblgen import Dag

def dag2expr(dag):
	def clean(value):
		if isinstance(value, tuple) and len(value) == 2 and value[0] == 'defref':
			return value[1]
		return value
	def sep((name, value)):
		if name is None:
			return clean(value)
		return name
	if isinstance(dag, Dag):
		return [dag2expr(sep(elem)) for elem in dag.elements]
	else:
		return dag

class Emit(Node):
	pass

def addEmits(module):
	def sub(node):
		walker, last = node, None
		while walker is not None and walker.__class__ not in (Module, Function, If, Elif, Else, Case, While, DoWhile):
			last = walker
			walker = walker._node_parent
		position = walker.findChild(last)
		walker.add(Emit(last), position)

	module.search(Emit, sub)
	return module
