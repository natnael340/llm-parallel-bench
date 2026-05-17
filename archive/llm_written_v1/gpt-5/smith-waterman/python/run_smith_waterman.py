import json
import time
import hashlib
from algo_parallel import SmithWatermanSequential, SmithWatermanParallel


def main():
    a = "ACACACTA"
    b = "AGCACACA"
    ms, mm, gs = 2, -1, -2

    seq = SmithWatermanSequential(ms, mm, gs)
    par = SmithWatermanParallel(ms, mm, gs)

    Hs = seq.constructMatrix(a, b)
    Hp1 = par.constructMatrix(a, b)
    Hp2 = par.constructMatrix(a, b)

    assert Hs == Hp1
    assert Hp1 == Hp2

    sa = seq.findAlignment(a, b)
    pa = par.findAlignment(a, b)
    assert sa == pa

    m = hashlib.sha256()
    for row in Hp1:
        m.update(bytes(row))
    h = m.hexdigest()

    print(json.dumps({
        "hash": h,
        "alignment": sa,
        "matrix_equal": Hs == Hp1,
    }))


if __name__ == "__main__":
    main()
