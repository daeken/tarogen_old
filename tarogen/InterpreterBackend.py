from Backend import Backend
from pygenic import *
from common import Emit

@Backend.register
class InterpreterBackend(Backend):
	name = 'interpreter'
	
	def build(self, core):
		with Module() as module:
			with Function('interpret(PC : uint, inst : uint) -> bool') as func:
				core.decoder(func)
		
		module = module.map(Emit, self.mapEmit)
		import pprint
		pprint.pprint(module.sexp())
		return module

	def mapEmit(self, node):
		out = []
		for child in node._node_children:
			if isinstance(child, Node):
				out.append(child.map(Emit, self.mapEmit))
			else:
				out.append(child)
		return out
