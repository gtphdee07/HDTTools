# Assets

| File | What it is | Size |
|---|---|---|
| `ic_launcher_foreground.svg` | Adaptive icon foreground: the mark (mountain, camper, ground line) inside the 66 dp safe zone | 108 x 108 dp |
| `ic_launcher_background.svg` | Adaptive icon background: sky gradient, `#7b3fe4` to `#ff7a1a` | 108 x 108 dp |
| `ic_launcher_monochrome.svg` | Single-colour version for themed icons (fill black, Android tints it) | 108 x 108 dp |
| `ic_launcher_512.png` | Store listing icon: background and foreground flattened, square, no mask | 512 x 512 px |
| `splash_icon.svg` | Splash icon for the Android 12 splash screen: the mark centred in a 288 dp canvas (the visible circle is 192 dp) | 288 x 288 dp |
| `logo_mark.svg` | The mark on transparent, for in-app use on colour | 64 x 70 |
| `logo_mark_mono.svg` | The mark in `ink`, one colour | 64 x 70 |

## Read this first: the mark is a simplified redraw
The brand logo (`web/public/logo.png`) is a painted raster image with lettering around it. It cannot be turned into a clean vector without redrawing it. The mark in these files is a **simplified geometric redraw** of its main shapes (mountain, camper, ground), built from brand colours so it holds up at 48 px. The owner should approve it, or supply a real vector of the logo, before it ships.

In the top bar the app can use `web/public/logo.png` directly (52 dp, so 156 px for xxhdpi). Supply 1x to 4x versions or a WebP; no new artwork is needed for that.

## Icons
The app uses Material icons today. Use Material Symbols (outlined, weight 400 to 500, 24 dp) with these names:

| Use | Material Symbols name |
|---|---|
| Scan balance, Scan Photo, Take Photo | `photo_camera` |
| Enter Manually | `keyboard` |
| Back | `arrow_back` |
| Next | `arrow_forward` |
| History | `history` |
| Account (signed out) | `person` |
| Sign out | `logout` |
| Row, verdict: pass | `check_circle` |
| Row, verdict: fail | `cancel` |
| Row, verdict: not checked, info buttons, notices | `info` |
| Disclaimer, estimated figures | `warning` |
| Reference card caption | `search` |
| Row note: collapsed / expanded | `expand_more` / `expand_less` |
| Rig card chevron | `chevron_right` |

The frames draw these as 2 dp rounded-stroke line icons for consistency with the design system; the Material Symbols above are the build target.

## Photos
The three reference photos (`android/app/src/main/res/drawable/ref_*.jpg`) are not redrawn. The frames use a placeholder crop for the label and a drawn stand-in for the scale ticket. Production should crop the real photos; the truck and trailer photos must keep their redacted VIN block.
