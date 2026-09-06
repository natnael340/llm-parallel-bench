"""Per-language stage/build/run recipes.

Each recipe module exposes:
    stage(ctx)             -- copy variant files into the staging dir + write adapter
    build_cmds(ctx)        -- list of (argv, cwd) build commands (may be empty)
    run_cmd(ctx)           -- (argv, cwd) for the benchmark process

ctx fields: root, algo, lang, model, impl, manifest, variant,
            harness_dir, staging_dir, bin_dir, out_path.
"""

import importlib


def get(lang: str):
    return importlib.import_module(f"bench.recipes.{lang}")
