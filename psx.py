from emugen import build, Core, DagProcessor
from emugen.common import dag2expr
from pygenic import *
import json, os, tblgen

if not os.path.exists('psx.td.cache') or os.path.getmtime('psx.td') > os.path.getmtime('psx.td.cache'):
	insts = tblgen.interpret('psx.td').deriving('BaseInst')
	ops = []
	for name, (bases, data) in insts:
		ops.append((name, bases[1], data['Opcode'][1], data['Function'][1] if 'Function' in data else None, data['Disasm'][1], dag2expr(data['Eval'][1])))
	with file('psx.td.cache', 'w') as fp:
		json.dump(ops, fp)
else:
	ops = json.load(file('psx.td.cache'))

toplevel = {}

for name, type, op, funct, dasm, dag in ops:
	if funct is None:
		assert op not in toplevel
		toplevel[op] = name, type, dasm, dag
	else:
		if op not in toplevel:
			toplevel[op] = [type, {}]
		toplevel[op][1][funct] = name, type, dasm, dag

class PSXDagProcessor(DagProcessor):
	pass

class PSX(Core):
	def decoder(self, func):
		with Switch(func.inst >> 26):
			for op, body in toplevel.items():
				with Case(op):
					if isinstance(body, list):
						type, body = body
						if type == 'CFType':
							when = (func.inst >> 21) & 0x1F
						elif type == 'RIType':
							when = (func.inst >> 16) & 0x1F
						else:
							when = func.inst & 0x3F
						with Switch(when):
							for funct, sub in body.items():
								with Case(funct):
									self.instruction(*sub)
					else:
						self.instruction(*body)
		Return(False)

	def instruction(self, name, type, dasm, body):
		Comment(name)

		PSXDagProcessor(body)

if __name__=='__main__':
	build(PSX)
