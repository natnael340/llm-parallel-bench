import sys

from bench import staging


def stage(ctx):
    staging.clean_dir(ctx.staging_dir)
    staging.copy_files(ctx.root / ctx.variant["root"], ctx.variant["files"], ctx.staging_dir)
    (ctx.staging_dir / "__init__.py").write_text("")
    staging.write_adapter(
        ctx.staging_dir / "impl_adapter.py",
        "# Generated adapter — maps the canonical entry onto the staged implementation.\n",
        ctx.variant,
    )


def build_cmds(ctx):
    return []


def run_cmd(ctx):
    sources = ctx.manifest["harness_sources"]
    paths = [str(ctx.harness_dir / s) for s in sources]
    if ctx.manifest.get("runner") == "script":
        argv = [sys.executable] + paths
    else:
        argv = [sys.executable, "-m", "pytest", *paths, "--run-perf", "-s", "-q"]
    return argv, ctx.root
