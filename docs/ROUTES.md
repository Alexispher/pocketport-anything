# Decision tree: choose the most credible route

1. **A: Existing official 3DS game**. If a 3DS version exists and modifications are licensed/authorized, build a safe mod/asset pipeline; modifying existing source or assets is typically easier than rebuilding a modern engine.
2. **B: Existing homebrew 3DS port**. Verify repository license, build instructions, actual Old/New hardware status and maintainers; continue it instead of starting again.
3. **C: Source port**. With redistributable source and compatible dependencies, adapt code, platform interfaces, renderer and resource budgets to devkitARM.
4. **D: Decompilation-based port**. Use a sufficiently complete, lawfully sourced reconstruction, existing game behavior tests and compatible assets only when the scope is real.
5. **E: Static recompilation**. Only for a verified source ISA/ABI, available tool backend, memory model, game engine runtime and acceptable CPU performance. N64Recomp is an illustrative MIPS-specific backend, not general code translation.
6. **F: Engine reimplementation**. Recreate essential functionality with evidence/fixtures when code reuse is not practical.
7. **G: Demake**. Rebuild a deliberately constrained playable adaptation preserving core identity; never label it as the unmodified original.
8. **Feasibility / blocked**. If no route is substantiated or permissions are missing, report exact blockers and obtain lawful inputs. Do not fake a successful port.

Planner behavior is explicit and deliberately conservative. Supply verified boolean evidence:

```json
{
  "existing_3ds_version": false,
  "existing_3ds_port": false,
  "source_available": true,
  "decomp_available": false,
  "static_recomp_supported": false,
  "engine_reimplementation_feasible": false,
  "demake_feasible": true,
  "license_ok": true,
  "resources_ok": true
}
```

```bash
python -m pocketport plan ./authorized-game-files --target old3ds --evidence evidence.json
```

The planner does not verify truth of submitted booleans, automatically look up a game, or select a binary converter. Agents must research and attach external evidence for every `true`. `license_ok: false` blocks selected routes. Review game build hash, license, engine and hardware profiling before committing to the output.

Sources: [Co-op Anything engineering workflow](https://github.com/cranebeaker/coop-anything/blob/main/AGENTS.md), [Ship of Harkinian 3DS experiment](https://github.com/999sian/soh-3ds), [N64Recomp](https://github.com/N64Recomp/N64Recomp), [devkitPro 3DS examples](https://github.com/devkitPro/3ds-examples).
