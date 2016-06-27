from Backend import Backend
from pygenic import *

@Backend.register
class LibjitBackend(Backend):
	name = 'libjit'
	languages = 'cpp', 
	
	def build(self, core):
		with Module() as module:
			with Function('recompile(PC : uint, inst : uint, branched : ref[bool]) -> bool') as func:
				core.decoder(func)
		
		return module
