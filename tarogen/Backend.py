class Backend(object):
	languages = None # All

	backends = {}
	@staticmethod
	def register(cls):
		Backend.backends[cls.name] = cls
		return cls

	def __init__(self):
		pass
