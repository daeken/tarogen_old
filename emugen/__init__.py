from Frontend import Frontend
from Backend import Backend
from pygenic import *
from pygenic.backend import C

def run(frontend):
	frontend = frontend()
	
	pbackend = C(hexLiterals=True)
	print pbackend.generate(frontend.module)
