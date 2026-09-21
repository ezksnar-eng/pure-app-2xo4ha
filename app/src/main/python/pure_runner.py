import os
import runpy
import sys
import traceback


class _Out(object):
    encoding = "utf-8"

    def __init__(self, console, is_err):
        self._c = console
        self._e = is_err

    def write(self, s):
        if s:
            self._c.write(str(s), self._e)
        return len(s) if s else 0

    def flush(self):
        pass

    def isatty(self):
        return False


class _In(object):
    encoding = "utf-8"

    def __init__(self, console):
        self._c = console

    def readline(self, *args):
        line = self._c.readLine()
        if line is None:
            return ""
        return str(line) + "\n"

    def read(self, *args):
        return self.readline()

    def isatty(self):
        return False

    def __iter__(self):
        return self

    def __next__(self):
        line = self.readline()
        if not line:
            raise StopIteration
        return line


def run(console, base, entry, port, data_dir):
    sys.stdout = _Out(console, False)
    sys.stderr = _Out(console, True)
    sys.stdin = _In(console)
    os.environ["PORT"] = str(port)
    os.environ["HOST"] = "127.0.0.1"
    os.environ["PURE_DATA_DIR"] = str(data_dir)
    os.chdir(base)
    if base not in sys.path:
        sys.path.insert(0, base)
    try:
        runpy.run_path(os.path.join(base, entry), run_name="__main__")
    except SystemExit:
        pass
    except BaseException:
        traceback.print_exc()
