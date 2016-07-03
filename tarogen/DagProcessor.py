from pygenic import *
from common import Emit

def hint(**kwargs):
	def sub(func):
		func.hints = kwargs
		return func
	return sub

def runtime(func):
	func.runtime = True
	return func

class DagProcessor(object):
	def __init__(self, func, dag):
		self.func = func
		self.__process__(dag)

	def __process__(self, dag):
		if isinstance(dag, str) or isinstance(dag, unicode):
			return Variable(dag.replace('$', ''))
		elif not isinstance(dag, list):
			return dag

		name, rest = dag[0], dag[1:]

		def call(func):
			def subcall():
				if not hasattr(func, 'hints'):
					return func(*map(self.__process__, rest))
				hints = func.hints
				if func.func_code.co_flags & 4: # *args
					argnames = func.func_code.co_varnames[:func.func_code.co_argcount+1]
					argnames = argnames[1:] if argnames[0] == 'self' else argnames
					args = []
					for i, arg in enumerate(argnames):
						raw = arg in hints and hints[arg] == 'raw'
						if i == len(argnames) - 1:
							args += rest[i:] if raw else map(self.__process__, rest[i:])
						else:
							args.append(rest[i] if raw else self.__process__(rest[i]))
					return func(*args)
				else:
					argnames = func.func_code.co_varnames[:func.func_code.co_argcount]
					argnames = argnames[1:] if argnames[0] == 'self' else argnames
					return func(*[rest[i] if arg in hints and hints[arg] == 'raw' else self.__process__(rest[i]) for i, arg in enumerate(argnames)])

			if hasattr(func, 'runtime') and func.runtime:
				with Emit():
					subcall()
			else:
				subcall()

		if hasattr(self, name):
			return call(getattr(self, name))
		elif hasattr(self, name + '_'):
			return call(getattr(self, name + '_'))
		else:
			print 'Unsupported dag:', name, rest

	@hint(body='raw')
	def block(self, *body):
		for elem in body:
			self.__process__(elem)

	@hint(if_='raw', else_='raw')
	def if_(self, comp, if_, else_):
		with If(comp):
			self.__process__(if_)
		with Else():
			self.__process__(else_)

	@hint(var='raw', body='raw')
	def let(self, var, value, *body):
		self.func[var.replace('$', '')] = value

		for elem in body:
			self.__process__(elem)

	@runtime
	@hint(var='raw', body='raw')
	def rlet(self, var, value, *body):
		self.let(var, value, *body)

	def signed(self, value):
		return Cast(value, types.int)
	def unsigned(self, value):
		return Cast(value, types.uint)
	@hint(size='raw')
	def cast(self, size, value):
		return Cast(value, types['uint%i' % size])

	def signext(self, size, value):
		return Call('signext', size, value)

	def zeroext(self, size, value):
		return Call('zeroext', size, value)

	def _binary(op):
		def func(self, left, right):
			return Binary(op, left, right)
		return func

	add = _binary('+')
	sub = _binary('-')
	mul = _binary('*')
	div = _binary('/')
	mod = _binary('%')

	eq = _binary('==')
	neq = _binary('!=')
	lt = _binary('<')
	le = _binary('<=')
	gt = _binary('>')
	ge = _binary('>=')

	and_ = _binary('&')
	or_ = _binary('|')
	xor = _binary('^')
	def nor(self, left, right):
		return Unary('~', Binary('|', left, right))

	shl = _binary('<<')
	shra = _binary('>>')
	shrl = _binary('>>>')

# Would just decorate these, but Python is weird about using staticmethod decorators in the same class
DagProcessor.hint = staticmethod(hint)
DagProcessor.runtime = staticmethod(runtime)
