#!/bin/sh

cleanup() {
    test -n "$DIR" && rm -rf "$DIR"
}

trap cleanup EXIT

DIR=$(mktemp -d "/tmp/crash-python-tests.XXXXXX")

export CRASH_PYTHON_TESTDIR="$DIR"

set -e

rm -rf build/lib/crash
python3 setup.py build
make -C tests
crash-python-gdb -batch -ex "source tests/unittest-bootstrap.py"

cat << END > $DIR/gdbinit
python sys.path.insert(0, 'build/lib')
set build-id-verbose 0
set python print-stack full
set prompt py-crash> 
set height 0
set print pretty on
source kernel-tests/unittest-prepare.py
source kernel-tests/unittest-bootstrap.py
END

debug=false

if $debug; then
cat <<END > $DIR/gdbinit-debug
    break warning
    run --data-directory="/src/git/github/gdb-python/build-dir/gdb/data-directory" -x "$DIR/gdbinit"
END
fi

for f in "$@"; do
    export CRASH_PYTHON_TESTFILE="$f"
    if $debug; then
	gdb /src/git/github/gdb-python/build-dir/gdb/gdb -nh -q -x $DIR/gdbinit-debug
    else
	crash-python-gdb -batch -x $DIR/gdbinit
    fi
done

