from Core import Core
from Backend import Backend
from DagProcessor import DagProcessor
from pygenic.backend import Backend as PygenicBackend
import argparse, os, os.path, sys

import InterpreterBackend, LibjitBackend

def buildOne(core, backend, language, outdir, prefix, suffix):
	if backend.languages is not None and language not in backend.languages:
		print 'Language %s not supported by backend %s -- not generating' % (language, backend.name)
		return

	language = PygenicBackend.backends[language]()
	with file('%s/%s%s%s.%s' % (outdir, prefix, backend.name, suffix, language.extension), 'w') as fp:
		fp.write(language.generate(backend.build(core)))

def build(core):
	core = core()

	if core.backends is None:
		core.backends = Backend.backends.keys()

	parser = argparse.ArgumentParser(description='Build %s emulator core' % core.__class__.__name__)
	parser.add_argument('--backend', choices=core.backends, help='Emulator backend (default: all)')
	parser.add_argument('--language', choices=PygenicBackend.backends.keys(), help='Language to generate (default: all)')
	parser.add_argument('--outdir', required=True, help='Output directory')
	parser.add_argument('--prefix', default='', help='Generated filename prefix')
	parser.add_argument('--suffix', default='', help='Generated filename suffix')
	args = parser.parse_args()

	if not os.path.isdir(args.outdir):
		os.makedirs(args.outdir)

	backends = core.backends if args.backend is None else [args.backend]
	for backend in backends:
		backend = Backend.backends[backend]()
		languages = [args.language] if args.language is not None else (backend.languages if backend.languages is not None else PygenicBackend.backends.keys())
		for language in languages:
			buildOne(core, backend, language, args.outdir, args.prefix, args.suffix)
