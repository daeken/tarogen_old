from tarogen import build, Core, DagProcessor
from tarogen.common import dag2expr
from pygenic import *
import json, os, tblgen

if not os.path.exists('psx.td.cache') or os.path.getmtime('psx.td') > os.path.getmtime('psx.td.cache'):
	insts = tblgen.interpret('psx.td').deriving('BaseInst')
	ops = []
	for name, (bases, data) in insts:
		ops.append((name, bases[1], data['Opcode'][1], data['Function'][1] if 'Function' in data else None, data['Disasm'][1], dag2expr(data['Eval'][1])))
	with file('psx.td.cache', 'w') as fp:
		json.dump(ops, fp, sort_keys=True, indent=2)
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
	@DagProcessor.runtime
	def absorb_muldiv_delay(self):
		pass
	@DagProcessor.runtime
	def mul_delay(self, left, right, signed):
		Call('mul_delay', left, right, signed)
	@DagProcessor.runtime
	def div_delay(self):
		Call('div_delay')

	@DagProcessor.runtime
	def branch(self, addr):
		Call('branch', addr)

	@DagProcessor.runtime
	def branch_default(self):
		Call('branch', self.pc() + 8)

	@DagProcessor.runtime
	def break_(self, code):
		Call('break_', code)

	def check_load_alignment(self, addr, size):
		Call('check_load_alignment', addr, size)
	def check_store_alignment(self, addr, size):
		Call('check_store_alignment', addr, size)

	@DagProcessor.runtime
	def gpr(self, num):
		return self.func.state[num]
	@DagProcessor.runtime
	def hi(self):
		return self.func.state[34]
	@DagProcessor.runtime
	def lo(self):
		return self.func.state[35]
	
	def pc(self):
		return self.func.PC
	def pcd(self):
		return self.pc() + 4

	@DagProcessor.runtime
	def load(self, size, address):
		return Call('load_memory', size, address)
	@DagProcessor.runtime
	def store(self, size, address, value):
		Call('store_memory', size, address, value)

	@DagProcessor.runtime
	def copreg(self, cop, reg):
		return Call('read_copreg', cop, reg)
	@DagProcessor.runtime
	def copcreg(self, cop, reg):
		return Call('read_copcreg', cop, reg)
	@DagProcessor.runtime
	def copfun(self, cop, cofun):
		Call('copfun', cop, cofun)

	@DagProcessor.runtime
	@DagProcessor.hint(left='raw')
	def defer_set(self, left, right):
		assert left[0] == 'gpr'

		# XXX: These should probably be in state. Or `self.globals`? Hm.
		self.func.LDWhich = self.__process__(left[1])
		self.func.LDValue = right

	@DagProcessor.runtime
	@DagProcessor.hint(expr='raw')
	def check_overflow(self, expr):
		pass

	@DagProcessor.runtime
	@DagProcessor.hint(left='raw')
	def set(self, left, right):
		if left[0] == 'gpr':
			self.func.state[self.__process__(left[1])] = right
		elif left[0] == 'hi':
			self.func.state[34] = right
		elif left[0] == 'lo':
			self.func.state[35] = right
		elif left[0] == 'copreg':
			Call('write_copreg', self.__process__(left[1]), self.__process__(left[2]), right)
		elif left[0] == 'copcreg':
			Call('write_copcreg', self.__process__(left[1]), self.__process__(left[2]), right)
		else:
			print 'Unsupported set:', `left`, `right`

	@DagProcessor.runtime
	def syscall(self, code):
		Call('syscall_', code)

	def mul64(self, left, right):
		return Cast(left, types.int64) * Cast(right, types.int64)
	def umul64(self, left, right):
		return Cast(left, types.uint64) * Cast(right, types.uint64)

class PSX(Core):
	def decoder(self, func):
		self.func = func
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
		func = self.func
		Comment(name)

		if type == 'IType' or type == 'RIType':
			func.rs = (func.inst >> 21) & 0x1F
			func.rt = (func.inst >> 16) & 0x1F
			func.imm = func.inst & 0xFFFF
		elif type == 'JType':
			func.imm = func.inst & 0x3FFFFFF
		elif type == 'RType':
			func.rs = (func.inst >> 21) & 0x1F
			func.rt = (func.inst >> 16) & 0x1F
			func.rd = (func.inst >> 11) & 0x1F
			func.shamt = (func.inst >> 6) & 0x1F
		elif type == 'SType':
			func.code = (func.inst >> 6) & 0x0FFFFF
		elif type == 'CFType':
			func.cop = (func.inst >> 26) & 3
			func.rt = (func.inst >> 16) & 0x1F
			func.rd = (func.inst >> 11) & 0x1F
			func.cofun = func.inst & 0x01FFFFFF

		PSXDagProcessor(func, body)

if __name__=='__main__':
	build(PSX)
