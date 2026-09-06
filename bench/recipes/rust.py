from bench import staging


def _staged_dir(ctx):
    return ctx.root / "bench/rust/src/staged"


def stage(ctx):
    staged = _staged_dir(ctx)
    staging.clean_dir(staged)
    copied = staging.copy_files(ctx.root / ctx.variant["root"], ctx.variant["files"], staged)
    mods = [p.stem for p in copied if p.suffix == ".rs"]
    lines = [f"pub mod {m};" for m in sorted(mods)]
    lines += ["pub mod adapter;", "pub use adapter::*;", ""]
    (staged / "mod.rs").write_text("\n".join(lines))
    staging.write_adapter(
        staged / "adapter.rs",
        "// Generated adapter — maps the canonical entry onto the staged implementation.\n"
        "#![allow(unused_imports)]\n",
        ctx.variant,
    )


def build_cmds(ctx):
    manifest_path = ctx.root / "bench/rust/Cargo.toml"
    bin_name = ctx.manifest["bin"]
    argv = ["cargo", "build", "--release", "--manifest-path", str(manifest_path),
            "--bin", bin_name]
    return [(argv, ctx.root)]


def run_cmd(ctx):
    bin_name = ctx.manifest["bin"]
    return [str(ctx.root / "bench/rust/target/release" / bin_name)], ctx.root
