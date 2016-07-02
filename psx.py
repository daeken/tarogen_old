from emugen import build, Core, DagProcessor
from emugen.common import dag2expr
from pygenic import *
import json, os, tblgen

if not os.path.exists('psx.td.cache') or os.path.getmtime('psx.td') > os.path.getmtime('psx.td.cache'):
	func.insts = tblgen.interpret('psx.td').deriving('Basefunc.inst')
	ops = []
	for name, (bases, data) in func.insts:
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
	def absorb_muldiv_delay(self):
		pass
	def mul_delay(self, left, right, signed):
		return Call('mul_delay', left, right, signed)
	def div_delay(self):
		return Call('div_delay')

	def branch(self, addr):
		Call('branch', addr)

	def branch_default(self):
		Call('branch', self.pc() + 8)

	def break_(self, code):
		Call('break_', code)

	def check_load_alignment(self, addr, size):
		return Call('check_load_alignment', addr, size)

	def check_store_alignment(self, addr, size):
		return Call('check_store_alignment', addr, size)

	def gpr(self, num):
		return self.func.state[num]
	def hi(self):
		return self.func.state[34]
	def lo(self):
		return self.func.state[35]
	def pc(self):
		return self.func.PC
	def pcd(self):
		return self.pc() + 4

	def load(self, size, address):
		return Call('load_memory', size, address)
	def store(self, size, address, value):
		return Call('store_memory', size, address, value)

	def copreg(self, cop, reg):
		return Call('read_copreg', cop, reg)
	def copcreg(self, cop, reg):
		return Call('read_copcreg', cop, reg)
	def copfun(self, cop, cofun):
		return Call('copfun', cop, cofun)

	@DagProcessor.hint(left='raw')
	def defer_set(self, left, right):
		assert left[0] == 'gpr'

		# XXX: These should probably be in state. Or `self.globals`? Hm.
		self.func.LDWhich = self.__process__(left[1])
		self.func.LDValue = right

	@DagProcessor.hint(expr='raw')
	def check_overflow(self, expr):
		pass

	@DagProcessor.hint(left='raw')
	def set(self, left, right):
		if left[0] == 'gpr':
			self.func.state[self.__process__(left[1])] = right
		elif left[0] == 'hi':
			self.func.state[34] = right
		elif left[0] == 'lo':
			self.func.state[35] = right
		elif left[0] == 'copreg':
			return Call('write_copreg', self.__process__(left[1]), self.__process__(left[2]), right)
		elif left[0] == 'copcreg':
			return Call('write_copcreg', self.__process__(left[1]), self.__process__(left[2]), right)
		else:
			print 'Unsupported set:', `left`, `right`

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
