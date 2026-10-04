# Bundled fonts for topic PDF export

Topic PDFs use only these repository-owned, open-licensed fonts so rendering does not depend on host fonts. All files are pinned to immutable upstream commits and distributed under the SIL Open Font License 1.1.

| Local file | Official source | Pinned revision | SHA-256 |
| --- | --- | --- | --- |
| `NotoSansCJKsc-Regular.otf` | `notofonts/noto-cjk` `Sans/OTF/SimplifiedChinese/NotoSansCJKsc-Regular.otf` | `f8d157532fbfaeda587e826d4cd5b21a49186f7c` | `2c76254f6fc379fddfce0a7e84fb5385bb135d3e399294f6eeb6680d0365b74b` |
| `NotoSansMonoCJKsc-Regular.otf` | `notofonts/noto-cjk` `Sans/Mono/NotoSansMonoCJKsc-Regular.otf` | `f8d157532fbfaeda587e826d4cd5b21a49186f7c` | `ec04cc376b34887cedbdf84074e2e226ed2761eeabdcb9173fc1dd7bfd153ef7` |
| `NotoSansSymbols2-Regular.ttf` | `google/fonts` `ofl/notosanssymbols2/NotoSansSymbols2-Regular.ttf` | `9710da1eacb3be272583c3224dcb70f9da6eadbb` | `7d5fb73b7ca67a6798101741f5d280a3d016a56a197afcd4199dbb57b4b82a21` |
| `NotoEmoji-Variable.ttf` | `google/fonts` `ofl/notoemoji/NotoEmoji[wght].ttf` | `9710da1eacb3be272583c3224dcb70f9da6eadbb` | `de6c18832938afc99caf132b39d6a30a19bac7f2e812e28db2535b4608d27551` |
| `NotoEmoji-Regular.ttf` | Static 400-weight instance derived from the pinned variable file | FontTools `4.66.1` | `1ada997ccb67bf2404828e25528e5257d6db10c80287e77684abf6737a5d198f` |

`OFL.txt` is the license shipped with Noto Sans CJK at the pinned noto-cjk revision. `NotoSansSymbols2-OFL.txt` and `NotoEmoji-OFL.txt` are the licenses shipped with their respective fonts at the pinned Google Fonts revision.

The static emoji font is reproduced without timestamp changes using:

```bash
uv run --with fonttools==4.66.1 python -m fontTools.varLib.instancer \
  --static --update-name-table --no-recalc-timestamp \
  -o NotoEmoji-Regular.ttf NotoEmoji-Variable.ttf wght=400
```
