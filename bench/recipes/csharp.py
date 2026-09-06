from bench import staging


def stage(ctx):
    staging.clean_dir(ctx.staging_dir)
    staging.copy_files(ctx.root / ctx.variant["root"], ctx.variant["files"], ctx.staging_dir)
    staging.write_adapter(
        ctx.staging_dir / "Impl.cs",
        "// Generated adapter — maps the canonical entry onto the staged implementation.\n",
        ctx.variant,
    )


def build_cmds(ctx):
    csproj = ctx.harness_dir / "bench.csproj"
    argv = ["dotnet", "build", str(csproj), "-c", "Release",
            "-o", str(ctx.bin_dir), "--nologo", "-v", "q"]
    return [(argv, ctx.root)]


def run_cmd(ctx):
    # Run the built apphost binary directly so no dotnet build tooling is
    # resident during measurement.
    return [str(ctx.bin_dir / "bench")], ctx.root
