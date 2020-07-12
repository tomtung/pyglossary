# -*- coding: utf-8 -*-

from formats_common import *
from pyglossary.file_utils import fileCountLines
from pyglossary.plugin_lib.dictdlib import DictDB

enable = True
format = "DictOrg"
description = "DICT.org file format (.index)"
extensions = (".index",)
optionsProp = {
	"dictzip": BoolOption(),
	"install": BoolOption(),
}
depends = {}
sortOnWrite = DEFAULT_NO

# https://en.wikipedia.org/wiki/DICT#DICT_file_format
tools = [
	{
		"name": "Dictd",
		"web": "https://directory.fsf.org/wiki/Dictd",
		"platforms": ["Linux"],
		"license": "GPL",
	},
	{
		"name": "GNOME Dictionary",
		"web": "https://wiki.gnome.org/Apps/Dictionary",
		"platforms": ["Linux"],
		"license": "GPL",
	},
	{
		"name": "Xfce4 Dictionary",
		"web": "https://docs.xfce.org/apps/xfce4-dict/start",
		"platforms": ["linux"],
		"license": "GPL",
	},
]


def installToDictd(filename: str, dictzip: bool, title: str = "") -> None:
	"""
	filename is without extension (neither .index or .dict or .dict.dz)
	"""
	import shutil, subprocess
	targetDir = "/usr/share/dictd/"
	if filename.startswith(targetDir):
		return

	log.info(f"Installing {filename!r} to DICTD server directory: {targetDir}")

	if dictzip and os.path.isfile(filename + ".dict.dz"):
		dictExt = ".dict.dz"
	elif os.path.isfile(filename + ".dict"):
		dictExt = ".dict"
	else:
		log.error(f"No .dict file, could not install dictd file {filename!r}")
		return

	if not filename.startswith(targetDir):
		shutil.copy(filename + ".index", targetDir)
		shutil.copy(filename + dictExt, targetDir)

	if subprocess.call(["/usr/sbin/dictdconfig", "-w"]) != 0:
		log.error(
			"failed to update .db file, try manually runing: "
			"sudo /usr/sbin/dictdconfig -w"
		)

	log.info("don't forget to restart dictd server")


class Reader(object):
	def __init__(self, glos: GlossaryType):
		self._glos = glos
		self._filename = ""
		self._dictdb = None  # type: Optional[DictDB]

	def open(self, filename: str) -> None:
		import gzip
		if filename.endswith(".index"):
			filename = filename[:-6]
		self._filename = filename
		self._dictdb = DictDB(filename, "read", 1)

	def close(self) -> None:
		if self._dictdb is not None:
			self._dictdb.indexfile.close()
			self._dictdb.dictfile.close()
			# self._dictdb.finish()
			self._dictdb = None

	def __len__(self) -> int:
		if self._dictdb is None:
			return 0
		return len(self._dictdb.indexentries)

	def __iter__(self) -> Iterator[BaseEntry]:
		if self._dictdb is None:
			log.error("reader is not open, can not iterate")
			raise StopIteration
		dictdb = self._dictdb
		for word in dictdb.getdeflist():
			b_defi = b"\n<hr>\n".join(dictdb.getdef(word))
			try:
				defi = b_defi.decode("utf_8")
			except Exception as e:
				log.error(f"b_defi = {b_defi}")
				raise e
			yield self._glos.newEntry(word, defi)


def write(
	glos: GlossaryType,
	filename: str,
	dictzip: bool = False,
	install: bool = True,
) -> None:
	from pyglossary.text_utils import runDictzip
	(filename_nox, ext) = splitext(filename)
	if ext.lower() == ".index":
		filename = filename_nox
	dictdb = DictDB(filename, "write", 1)
	for entry in glos:
		if entry.isData():
			# does dictd support resources? and how? FIXME
			continue
		dictdb.addentry(entry.b_defi, entry.words)
	dictdb.finish(dosort=1)
	if dictzip:
		runDictzip(filename)
	if install:
		installToDictd(filename, dictzip, glos.getInfo("name").replace(" ", "_"))
