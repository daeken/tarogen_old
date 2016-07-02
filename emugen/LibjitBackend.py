from Backend import Backend
from pygenic import *
from emugen.common import Emit, addEmits

@Backend.register
class LibjitBackend(Backend):
	name = 'libjit'
	languages = 'cpp', 
	
	def build(self, core):
		with Module() as module:
			with Function('recompile(PC : uint, inst : uint, branched : ref[bool]) -> bool') as func:
				core.decoder(func)
		
		module = addEmits(module)
		module = module.map(Emit, self.mapEmit)
		import pprint
		pprint.pprint(module.sexp())
		return module

	def mapEmit(self, node):
		return node
