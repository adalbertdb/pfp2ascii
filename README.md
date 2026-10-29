# pfp2ascii

Turn a profile picture into ASCII art: the script behind the portrait on
[my GitHub profile](https://github.com/adalbertdb).

```
pip install -r requirements.txt

python pfp2ascii.py adalbertdb                 # GitHub username
python pfp2ascii.py https://example.com/me.jpg # image URL
python pfp2ascii.py me.png --cols 64 --svg me.svg
```

Output for `adalbertdb` is in [`example.txt`](example.txt).

## How it works

1. **Background removal**: the backdrop colour is sampled from the corners
   and those pixels are left blank. Works best with a flat background.
2. **Head crop**: the crop is tightened around the head so the face gets
   most of the columns instead of the shoulders.
3. **Local contrast**: the image is sharpened and a blurred copy is
   subtracted, so uneven lighting doesn't flatten one side of the face.
4. **Equalization on the subject only**: the whole glyph ramp is spent on
   skin, eyes and hair, not on the backdrop.
5. **Glyph mapping**: bright pixels become dense glyphs (` .:-=+*#%@`), for
   light text on a dark background. Use `--invert` for the opposite.

## Options

| Flag | What it does |
| --- | --- |
| `--cols N` | Width in characters (default 56). Rows follow the image ratio. |
| `--ramp " .:-=+*#%@"` | Glyphs ordered from sparse to dense. |
| `--invert` | Dark pixels become dense glyphs (dark text on a light background). |
| `--keep-background` | Don't blank out the backdrop. |
| `--no-crop` | Keep the whole picture instead of cropping around the head. |
| `-o out.txt` | Write to a file instead of stdout. |
| `--svg out.svg` | Also write a ready-to-embed SVG card. |
