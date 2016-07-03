from pygenic import *
from common import Emit

def hint(**kwargs):
	def sub(func):
		func.hints = kwargs
		return func
	return sub

def compiletime(func):
	func.compiletime = True
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

		if hasattr(self, name):
			return call(getattr(self, name))
		elif hasattr(self, name + '_'):
			return call(getattr(self, name + '_'))
		else:
			print 'Unsupported dag:', name, rest

	@compiletime
	@hint(body='raw')
	def block(self, *body):
		for elem in body:
			self.__process__(elem)

	@compiletime
	@hint(if_='raw', else_='raw')
	def if_(self, comp, if_, else_):
		with If(comp):
			self.__process__(if_)
		with Else():
			self.__process__(else_)

	@compiletime
	@hint(var='raw', body='raw')
	def let(self, var, value, *body):
		self.func[var.replace('$', '')] = value

		for elem in body:
			self.__process__(elem)

	@hint(var='raw', body='raw')
	def rlet(self, var, value, *body):
		with Emit():
			self.let(var, value, *body)

	@compiletime
	def signed(self, value):
		return Cast(value, types.int)
	@compiletime
	def unsigned(self, value):
		return Cast(value, types.uint)
	@hint(size='raw')
	def cast(self, size, value):
		return Cast(value, types['uint%i' % size])

	@compiletime
	def signext(self, size, value):
		return Call('signext', size, value)

	@compiletime
	def zeroext(self, size, value):
		return Call('zeroext', size, value)

	def _binary(op):
		@compiletime
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
	@compiletime
	def nor(self, left, right):
		return Unary('~', Binary('|', left, right))

	shl = _binary('<<')
	shra = _binary('>>')
	shrl = _binary('>>>')

# Would just decorate these, but Python is weird about using staticmethod decorators in the same class
DagProcessor.hint = staticmethod(hint)
DagProcessor.compiletime = staticmethod(compiletime)
