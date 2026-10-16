# La Luna de Florida — Director Pass 02 (private-WAV lyric-aligned **candidate**)

**Production:** `song/la-luna-de-florida` exclusively. **Existing B01–B05 50 moving proofs and 98 native FX loops remain unchanged.** No writes to `main` or any other project.

## What changed

The original WAV (SHA256 `1a4bffef36930b504423d2653faff4cc5bfd9a15d44bdcf1083b27fbb0db1c10`, 48kHz stereo, 321.16s) was analyzed **entirely locally in sandbox** with an offline Spanish Faster-Whisper base model downloaded via [Actions #38828301127](https://github.com/SouthPaw302/AIVideoEdit-MainV2-Lab/actions/runs/38828301127). That model-only GitHub job contained **no private original audio**; the Drive WAV remains owner-only.

Local ASR found 686 words, 54 segments and matched 126/129 canonical lyric lines. **All timestamps are estimates, not independent audible Director-confirmed lines or final scene boundaries.** Three unmatched lines include opening `Oh-oh`, breakdown `otra más`, and the final repeated `Volveremos a bailar`.

Pass 01 erroneously placed the major rap/bridge/sunrise far from their words. Pass 02 changes 49 shot boundaries to better follow: Rap1 ~108.72s, Chorus2 ~136.36s, Verse3 ~157s, Rap2 ~197.38s, Bridge ~226.58s, Breakdown ~246.98s, Final Chorus ~257.76s, Outro ~279.5s, first literal Florida sunrise lyric **289.96s**, and final return-to-dance lyric **303.32s**.

The corrected **50-shot structure sums to 7,708 integer frames at 24fps**, contiguous without overlap/gap, preserving the locked shot order and each immutable source SHA. The 321.1667s picture vs 321.16s original WAV has an explicit ~6.667ms tail tolerance. 34 shots require additional separately compiled, nonrepeating long-form coverage; gross `3224` additional footage frames are required after any original four-second clips are trimmed to the new lengths. **No artificial MP4 loops/freeze/stretch satisfy this gate.**

## Candidate shot-by-shot timeline

| Shot | Global in | Global out | Frames | Candidate musical cue | Extra nonrepeating frames needed |
|---|---:|---:|---:|---|---:|
| B01-S01 | 0.000 | 11.667 | 280 | ASR estimated Intro 8.44s: Bajo la luna de Florida | 184 |
| B01-S02 | 11.667 | 16.500 | 116 | ASR estimated Intro 8.44s: Bajo la luna de Florida | 20 |
| B01-S03 | 16.500 | 21.500 | 120 | ASR estimated Intro 8.44s: Bajo la luna de Florida | 24 |
| B01-S04 | 21.500 | 26.000 | 108 | ASR estimated Intro 8.44s: Bajo la luna de Florida | 12 |
| B01-S05 | 26.000 | 31.000 | 120 | ASR estimated Intro 8.44s: Bajo la luna de Florida | 24 |
| B01-S06 | 31.000 | 35.500 | 108 | ASR estimated Intro 8.44s: Bajo la luna de Florida | 12 |
| B01-S07 | 35.500 | 39.000 | 84 | ASR estimated Intro 8.44s: Bajo la luna de Florida | 0 |
| B01-S08 | 39.000 | 43.000 | 96 | ASR estimated Intro 8.44s: Bajo la luna de Florida | 0 |
| B01-S09 | 43.000 | 49.000 | 144 | ASR estimated Intro 8.44s: Bajo la luna de Florida | 48 |
| B01-S10 | 49.000 | 53.333 | 104 | ASR estimated Verse 1 46.74s: En la taberna del puerto | 8 |
| B02-S01 | 53.333 | 56.708 | 81 | ASR estimated Verse 1 46.74s: En la taberna del puerto | 0 |
| B02-S02 | 56.708 | 59.792 | 74 | ASR estimated Verse 1 46.74s: En la taberna del puerto | 0 |
| B02-S03 | 59.792 | 63.500 | 89 | ASR estimated Verse 1 46.74s: En la taberna del puerto | 0 |
| B02-S04 | 63.500 | 66.833 | 80 | ASR estimated Verse 1 46.74s: En la taberna del puerto | 0 |
| B02-S05 | 66.833 | 70.500 | 88 | ASR estimated Chorus 66.82s: Baila conmigo hasta que salga el sol | 0 |
| B02-S06 | 70.500 | 76.000 | 132 | ASR estimated Chorus 66.82s: Baila conmigo hasta que salga el sol | 36 |
| B02-S07 | 76.000 | 81.000 | 120 | ASR estimated Chorus 66.82s: Baila conmigo hasta que salga el sol | 24 |
| B02-S08 | 81.000 | 86.583 | 134 | ASR estimated Chorus 66.82s: Baila conmigo hasta que salga el sol | 38 |
| B02-S09 | 86.583 | 98.000 | 274 | ASR estimated Chorus 66.82s: Baila conmigo hasta que salga el sol | 178 |
| B02-S10 | 98.000 | 108.708 | 257 | ASR estimated Verse 2 87.74s: La marea empuja adentro | 161 |
| B03-S01 | 108.708 | 111.792 | 74 | ASR estimated Rap Verse 108.72s: Viejo muelle, tabla rota | 0 |
| B03-S02 | 111.792 | 115.292 | 84 | ASR estimated Rap Verse 108.72s: Viejo muelle, tabla rota | 0 |
| B03-S03 | 115.292 | 118.708 | 82 | ASR estimated Rap Verse 113.94s: Traigo polvo del camino | 0 |
| B03-S04 | 118.708 | 121.000 | 55 | ASR estimated Rap Verse 113.94s: Traigo polvo del camino | 0 |
| B03-S05 | 121.000 | 123.000 | 48 | ASR estimated Rap Verse 113.94s: Traigo polvo del camino | 0 |
| B03-S06 | 123.000 | 124.125 | 27 | ASR estimated Rap Verse 113.94s: Traigo polvo del camino | 0 |
| B03-S07 | 124.125 | 131.542 | 178 | ASR estimated Rap Verse 124.12s: De los montes hasta el puerto | 82 |
| B03-S08 | 131.542 | 139.500 | 191 | ASR estimated Rap Verse 129.20s: No me hables del mañana | 95 |
| B03-S09 | 139.500 | 147.000 | 180 | ASR estimated Chorus 2 136.36s: Baila conmigo hasta que salga el sol | 84 |
| B03-S10 | 147.000 | 157.000 | 240 | ASR estimated Chorus 2 136.36s: Baila conmigo hasta que salga el sol | 144 |
| B04-S01 | 157.000 | 163.417 | 154 | ASR estimated Verse 3 157.00s: Un violín desde la esquina | 58 |
| B04-S02 | 163.417 | 170.000 | 158 | ASR estimated Verse 3 157.00s: Un violín desde la esquina | 62 |
| B04-S03 | 170.000 | 177.000 | 168 | ASR estimated Verse 3 157.00s: Un violín desde la esquina | 72 |
| B04-S04 | 177.000 | 184.000 | 168 | ASR estimated Verse 3 157.00s: Un violín desde la esquina | 72 |
| B04-S05 | 184.000 | 191.000 | 168 | ASR estimated Verse 3 157.00s: Un violín desde la esquina | 72 |
| B04-S06 | 191.000 | 197.375 | 153 | ASR estimated Verse 3 157.00s: Un violín desde la esquina | 57 |
| B04-S07 | 197.375 | 204.000 | 159 | ASR estimated Rap Verse 2 197.38s: Tengo el ritmo de la calle | 63 |
| B04-S08 | 204.000 | 212.000 | 192 | ASR estimated Rap Verse 2 197.38s: Tengo el ritmo de la calle | 96 |
| B04-S09 | 212.000 | 219.000 | 168 | ASR estimated Rap Verse 2 197.38s: Tengo el ritmo de la calle | 72 |
| B04-S10 | 219.000 | 226.583 | 182 | ASR estimated Rap Verse 2 197.38s: Tengo el ritmo de la calle | 86 |
| B05-S01 | 226.583 | 239.792 | 317 | ASR estimated Bridge 226.58s: Y si la noche se apaga | 221 |
| B05-S02 | 239.792 | 247.000 | 173 | ASR estimated Bridge 239.80s: cuando empiece a amanecer | 77 |
| B05-S03 | 247.000 | 250.292 | 79 | ASR estimated Breakdown 246.98s: Suena el violín | 0 |
| B05-S04 | 250.292 | 254.042 | 90 | ASR estimated Breakdown 250.28s: Golpea la bota contra la madera | 0 |
| B05-S05 | 254.042 | 257.750 | 89 | ASR estimated Breakdown 250.28s: Golpea la bota contra la madera | 0 |
| B05-S06 | 257.750 | 277.208 | 467 | ASR estimated Final Chorus 257.76s: Baila conmigo hasta que salga el sol | 371 |
| B05-S07 | 277.208 | 289.958 | 306 | ASR estimated Final Chorus 268.16s: Baila conmigo, no mires atrás | 210 |
| B05-S08 | 289.958 | 295.167 | 125 | ASR estimated Outro 289.96s: Sale el sol sobre Florida | 29 |
| B05-S09 | 295.167 | 303.333 | 196 | ASR estimated Outro 295.18s: Pero mientras quede música | 100 |
| B05-S10 | 303.333 | 321.167 | 428 | ASR estimated Outro 303.32s: volveremos a bailar | 332 |

## Corrected dawn cinematic Director checkpoints

- `B03-S07`: 178f source-derived road-memory candidate picture, remuxed at **124.125s** to original WAV excerpt (candidate video SHA256 `ff30cb6f45d4d5ddb932252a18cc30b4704ab82ebfb90798a547dca777daf68f`). **Not real Miami sunrise.**
- `B05-S05`: pre-final-chorus night harbor trimmed to 89f and remuxed at **254.0417s** (candidate SHA256 `1b4272fa9d0137a3487417f38d4263df3becd16b95f4bb78c3b316ab05156da2`).
- `B05-S08`: 125f real sunrise harbor at **289.9583s**: separate locally composed existing 4s proof and SHA-verified native A/B light-water FX (candidate SHA256 `768887b04d3ac23e795ace2c8a465729a5407ed8d9e2cf1a20fb22c5947f8b3b`). Decoded 125f, zero black/near-still adjacent, **technical only**.
- `B05-S09`: 196f dawn couple/tavern scene at **295.1667s**, built with previously approved source/fx (candidate SHA256 `2605422f1b83cef1a4517081c8e97b930f294b963138385f5d6ca9a53c61025e`). Decoded 196f, zero black, but **56 near-still adjacent pairs — targeted motion repair pending**.
- `B05-S10`: planned **428f final sunrise dance** begins **303.333s**. Only 96 original proof frames exist; **332 frames of meaningful choreography/continuation remain uncovered**, and no 4s repeat or global camera warp may count as true movement.

The four versioned audiovisual candidates plus scene QC, complete 50-shot JSON, ASR evidence summary and frame-review strips are preserved in [this Drive evidence archive](https://drive.google.com/file/d/1_rUjIVZnPLSiHoRYj8pKDLEsjTdE46uG/view). ZIP SHA256: `d38a9cc3c8d2e0ef4a1f1c32a011f686599c478dffe8aaf95989beb8707e3551`, **6,344,347 bytes**. Original WAV and transcription-model bytes are deliberately excluded.

## Director next actions and non-negotiable gates

1. Director independently verifies exact lyric cue window timing by listening to the original WAV and annotates any ASR failures before locking `SCRIPT.json`.
2. Repair B05-S09 slow tableau and secure genuine shot-unique body performance for B05-S10; protect existing hero faces, hands, clothing, shore geometry, practical light direction, time-of-day.
3. Extend the other 32 shots needing more than their approved 96f proof with actual native FX, clean original full-res still/depth/alpha and distinct authorized performance material; inspect every finished shot frame-by-frame in sandbox.
4. Stage every distinct generated-long-shot media asset and original WAV through a **private byte-serving SHA-verified source contract**; do not send the owner-only WAV to a public GitHub repo or claim inaccessible Google Drive /view URLs are bytes.
5. Produce normal-speed representative film across five acts; only then dispatch canonical current-main parallel renderer for all 7,708 frames with original WAV once, run full eleven-phase Director Scan and surgical RCn repairs.
6. Release remains separately gated on executive-producer approval. `SCRIPT.json.locked=false`; no full 5:21 film has been rendered/approved.
