# Furby Project

Python CLI for working with Furby Boom / 2012 ROM dumps.

It can inspect ROMs, extract assets, convert images, convert audio between `.wav` and `.a18`, and rebuild ROM files.

There is extracted audio and images for the following Furbys in Furby Exported Files/:

- Dutch 2012  
- English 2012  
- French 2012  
- English Boom  
- French Boom  
- English Crystal *(same as Boom)*  
- Furbacca  

### Furby 2012 Eyes
![Furby 2012 Eyes](https://github.com/LifeOnAFarm/Furby_2012_Boom_Audio/blob/003ba831338548cdba9973b5421e0e20155f2e77/2012-Eyes-Big.gif)

### Furby Boom Eyes
![Furby Boom Eyes](https://github.com/LifeOnAFarm/Furby_2012_Boom_Audio/blob/774c1bd3997c3e95ca514c81067b95e8a9dacb30/Boom-Eyes-Big.gif)

### Furbacca Eyes
![Furbacca Eyes](https://github.com/LifeOnAFarm/Furby_2012_Boom_Audio/blob/774c1bd3997c3e95ca514c81067b95e8a9dacb30/Furbacca-Eyes-Big.gif)


## Install

```bash
pip install -e .
```

## Commands

Inspect a ROM:

```bash
furby inspect path/to/combined_rom.bin --limit 10
```

Extract audio and images from a ROM:

```bash
furby extract path/to/combined_rom.bin --out extracted_assets
```

Export image records as BMP:

```bash
furby export-images path/to/combined_rom.bin --out images --format bmp
```

Convert BMP files back to Furby image records:

```bash
furby import-images path/to/bmps --out converted_bins
```

Decode `.a18` to WAV:

```bash
furby export-audio-wav path/to/audio0001.a18 --out audio0001.wav
furby export-audio-wav path/to/combined_rom.bin --out exported_wavs
```

Encode WAV to `.a18`:

```bash
furby encode-audio-a18 path/to/audio.wav --out audio.a18
furby encode-audio-a18 path/to/wav_folder --out converted_a18
```

Build a ROM from image and audio folders:

```bash
furby build --images converted_bins --audio converted_a18 --out rebuilt.bin --padding-mode 4k
furby build --images converted_bins --audio convert_wavs --out rebuilt.bin --audio-bitrate 16000
```

`build` accepts audio folders containing `.a18`, `.wav`, or both. WAV files are auto-encoded during the build.


## Notes

- WAV input for `.a18` encoding currently expects 16-bit PCM at 16000 Hz. Stereo input is downmixed to mono.
