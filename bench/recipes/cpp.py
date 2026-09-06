from bench import staging


def stage(ctx):
    staging.clean_dir(ctx.staging_dir)
    staging.copy_files(ctx.root / ctx.variant["root"], ctx.variant["files"], ctx.staging_dir)
    staging.write_adapter(ctx.staging_dir / "impl.hpp", "#pragma once\n", ctx.variant)


def build_cmds(ctx):
    bin_path = ctx.bin_dir / "bench_bin"
    argv = ["g++", "-std=c++17", "-O2", "-pthread", "-o", str(bin_path)]
    for s in ctx.manifest["harness_sources"]:
        argv.append(str(ctx.harness_dir / s))
    # Staged .cpp files are compiled unless the harness style is include-the-cpp.
    if ctx.manifest.get("compile_staged_sources", True):
        argv += sorted(str(p) for p in ctx.staging_dir.glob("*.cpp"))
    argv += ["-I", str(ctx.staging_dir), "-I", str(ctx.root / "tests/bench_utils/cpp")]
    argv += ctx.manifest.get("cxxflags", [])
    argv += ctx.variant.get("cxxflags", [])
    return [(argv, ctx.root)]


def run_cmd(ctx):
    return [str(ctx.bin_dir / "bench_bin")], ctx.root
