from Backend import Backend
from pygenic import *

@Backend.register
class InterpreterBackend(Backend):
	name = 'interpreter'
	
	def build(self, core):
		with Module() as module:
			with Function('interpret(PC : uint, inst : uint, branched : ref[bool]) -> bool') as func:
				core.decoder(func)
		
		return module
