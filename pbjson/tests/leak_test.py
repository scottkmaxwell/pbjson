# To run this test:
# - pip install memory_profiler matplotlib
# - mprof run pbjson/tests/leak_test.py && mprof plot

import pbjson

loops = 1000000
payload = "hello world"
entry = pbjson.dumps(payload)  # some example entry
entry_len = len(entry)


def write():
    with open("dump.bin", "wb") as file:
        for _ in range(loops):
            file.write(entry)
    print("wrote %d entries" % loops)


def read():
    n = 0
    with open("dump.bin", "rb") as file:
        while data := file.read(entry_len):
            data = pbjson.loads(data)
            assert data == payload
            n += 1
    print("read %d entries" % n)


if __name__ == "__main__":
    write()
    # pbjson._toggle_speedups(False)
    read()
    # pbjson._toggle_speedups(True)
    write()
    # pbjson._toggle_speedups(False)
    read()
