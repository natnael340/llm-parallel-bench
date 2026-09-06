from bench import staging


def stage(ctx):
    staging.clean_dir(ctx.staging_dir)
    copied = staging.copy_files(ctx.root / ctx.variant["root"], ctx.variant["files"], ctx.staging_dir)
    for f in copied:
        staging.rewrite_go_package(f, "staging")
    staging.write_adapter(ctx.staging_dir / "adapter.go", "package staging\n\n", ctx.variant)


def build_cmds(ctx):
    bin_path = ctx.bin_dir / "bench_test"
    rel = ctx.harness_dir.relative_to(ctx.root)
    return [(["go", "test", "-c", "-o", str(bin_path), f"./{rel}/"], ctx.root)]


def run_cmd(ctx):
    bin_path = ctx.bin_dir / "bench_test"
    pattern = ctx.manifest.get("test_pattern", ".")
    return [str(bin_path), "-test.v", "-test.run", pattern], ctx.root
