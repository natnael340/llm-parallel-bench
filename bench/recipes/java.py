from bench import staging


def stage(ctx):
    staging.clean_dir(ctx.staging_dir)
    copied = staging.copy_files(ctx.root / ctx.variant["root"], ctx.variant["files"], ctx.staging_dir)
    for f in copied:
        staging.strip_java_package(f)
    staging.write_adapter(
        ctx.staging_dir / "Impl.java",
        "// Generated adapter — maps the canonical entry onto the staged implementation.\n",
        ctx.variant,
    )


def build_cmds(ctx):
    classes = ctx.bin_dir / "classes"
    classes.mkdir(parents=True, exist_ok=True)
    argv = ["javac", "-d", str(classes)]
    for s in ctx.manifest["harness_sources"]:
        argv.append(str(ctx.harness_dir / s))
    argv += sorted(str(p) for p in ctx.staging_dir.glob("*.java"))
    argv.append(str(ctx.root / "tests/bench_utils/java/Bench.java"))
    return [(argv, ctx.root)]


def run_cmd(ctx):
    classes = ctx.bin_dir / "classes"
    argv = ["java", "-cp", str(classes)]
    argv += ctx.manifest.get("java_flags", [])
    argv.append(ctx.manifest["main_class"])
    return argv, ctx.root
