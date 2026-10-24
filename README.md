# Decky Framegen Plugin

A Steam Deck plugin that enables DLSS upscaling and Frame Generation on handhelds by utilizing the latest OptiScaler and supporting modification software. This plugin automatically installs and manages all necessary components for FSR-based frame generation in games that support DLSS, or OptiFG for adding FG to games that do not have any existing FG pathway (highly experimental)

> This is a continuation of [xXJSONDeruloXx/Decky-Framegen](https://github.com/xXJSONDeruloXx/Decky-Framegen). Its builds don't include OptiScaler: games are patched from versions in the plugin's OptiScaler library (`~/fgmod/library`), downloaded straight from OptiScaler's releases. Download a version under **OptiScaler versions** → *Download versions…* before patching a game. Report problems in [this repository's issues](https://github.com/arttttt/Decky-Framegen/issues).

## What This Plugin Does

This plugin uses OptiScaler to replace DLSS calls with FSR3/FSR3.1, giving you:

- **Frame Generation**: Smooth out your frame rate using AMD's FSR3 pathways
- **Upscaling**: Improves performance while maintaining visual quality using FSR and XESS using DLSS FSR or XESS inputs. Upgrade FSR 2 games to FSR 3.1.4 or XESS for better visual quality.
- **Easy Management**: One-click installation and game patching/unpatching through the Steam Deck interface. No going into desktop mode every time you want to add or remove OptiScaler from a game!

## Features

### Core Functionality
- **One-Click Setup**: Automatically downloads and installs OptiScaler into a "fgmod" directory
- **Smart Installation**: Handles all required dependencies and library files
- **Game Patching**: Easy copy-paste launch commands for enabling/disabling the mod per game
- **OptiScaler Wiki**: Direct access to OptiScaler documentation and settings via a webpage launch button right inside the plugin.

## How to Use

1. **Install the Plugin**: Download and install through Decky Loader "install from zip" option in developer settings
2. **Setup OptiScaler**: Open the plugin and click "Setup OptiScaler Mod" 
3. **Configure Games**: For each game you want to enhance:
   - Click "Copy launch options" in the plugin for the standard direct launch-options method
   - Go to your game's Properties → Launch Options in Steam
   - Paste the copied command
   - If you want the wrapper commands instead, enable Manual Mode and use "Copy Patch Command" / "Copy Unpatch Command"
4. **Enable Features**: Launch your game and enable DLSS in the graphics settings
5. **Advanced Options**: Press the Insert key in-game for additional OptiScaler settings

### Removing the Mod from Games
- If you used the wrapper method, enable Manual Mode and click "Copy Unpatch Command", then replace the launch options with: `~/fgmod/fgmod-uninstaller.sh %command%`
- If you used the standard direct patch flow, use the in-plugin unpatch button instead
- Run the game at least once to make the uninstaller script run. After that you can leave the launch option or remove it

### Configuring OptiScaler via Environment Variables
As of v0.15.1, you can update OptiScaler settings before a game launches by adding environment variables. 
This is useful if you plan to use the same settings across multiple games so they are pre-configured by the time you launch them.

For example, considering the following sample from the OptiScaler.ini config file:
```
[Upscalers]
Dx11Upscaler=auto
Dx12Upscaler=auto
VulkanUpscaler=auto

[FrameGen]
Enabled=auto
FGInput=auto
FGOutput=auto
DebugView=auto
DrawUIOverFG=auto
```
We can decide to set `Dx12Upscaler=fsr31` to enable FSR4 in DX12 games by default. This works because the option name `Dx12Upscaler` is unique throughout the file but for options that appear multiple times like `Enabled`, you can prefix the option name with the section name like `FrameGen_Enabled=true`.
You can provide section names for all options if you want to be explicit. You can also prefix `Section_Option` with `OptiScaler` to ensure no conflict with other commands.

Here's the breakdown of supported formats:
- `OptiScaler_Section_Option=value` - Full format (foolproof)
- `Section_Option=value` - Short format (recommended)
- `Option=value` - Minimal format (only works if the option name appears once in OptiScaler.ini)

**Example:**
```bash
# Enable frame generation with XeFG output
FrameGen_Enabled=true FGInput=fsrfg FGOutput=xefg ~/fgmod/fgmod %command%

# Set DX12 upscaler to FSR 3.1 (Upgrades to FSR4)
Dx12Upscaler=fsr31 ~/fgmod/fgmod %command%
```

**Notes:**
- Environment variables override the OptiScaler.ini file on each game launch
- Hyphenated section names like `[V-Sync]` can be accessed like `VSync_Option=value`
- If an option name appears in multiple sections of the OptiScaler.ini file, use the `Section_Option` or `OptiScaler_Section_Option` format
- OptiScaler 0.9.4 adds `FSR_Fsr4ForceEnableInt8=true` for the bundled SDK upscaler. It can force INT8 on unsupported GPUs that support INT8, but does not make older non-INT8 hardware compatible. Enable `FSR_Fsr4EnableWatermark=true` to verify the active FSR runtime.

### FSR 4

The plugin does not pick an FSR 4 model: OptiScaler does. OptiScaler 10.x chooses it from the GPU (INT8 Lite on Steam Deck and Ryzen Z1/Z2 handhelds, INT8 on RDNA3 desktop GPUs, FP8 on RDNA4). OptiScaler 0.9.x supports RDNA4 and RDNA3 desktop GPUs officially; `FSR_Fsr4ForceEnableInt8=true` (see above) forces INT8 elsewhere. Enable `FSR_Fsr4EnableWatermark=true` to see which path is active (`FSR4`, `FSR4-i8`, or `FSR3`).

On Linux FSR 4 also needs AMD's driver DLL (`amdxcffx64.dll`), which neither OptiScaler nor Valve's Proton ship. GE-Proton and Proton-CachyOS download it into the game's prefix when the game is launched with `PROTON_FSR4_UPGRADE=1`. On an AMD GPU the plugin adds that variable to the launch options it writes when the game's Proton reads it, and the game's status says whether FSR 4 is already in the prefix, will be downloaded on the next launch, or needs another Proton. Without the DLL, OptiScaler's upscaler list ends at FSR 3.1.5.

## Technical Details

### Where OptiScaler comes from
Builds of this plugin don't include OptiScaler. **OptiScaler versions** → *Download versions…* fetches versions straight from OptiScaler's own releases ([stable](https://github.com/optiscaler/OptiScaler/releases), [nightly](https://github.com/optiscaler/OptiScaler-nightly/releases)), checks each download against its published checksum, and keeps it in `~/fgmod/library`; *Manage downloaded…* downloads one again or removes one. A patch places the version picked for it (the newest, unless you pick another) in the game's directory as symlinks into the library, so games hold no copies of OptiScaler; only `OptiScaler.ini` is copied, since OptiScaler saves each game's settings there. It backs up any game file it replaces and records what it did, so Unpatch undoes exactly that. A version games are linked to can't be removed until they are unpatched.

## Development

How to build, test, and try a work-in-progress build on a device: see [CONTRIBUTING.md](CONTRIBUTING.md).

## Credits

### Core Technologies
- **[Nukem9](https://github.com/Nukem9/dlssg-to-fsr3)** - Creator of the DLSS to FSR3 mod that makes frame generation possible
- **[Cdozdil/OptiScaler Team](https://github.com/optiscaler/OptiScaler)** - OptiScaler mod that provides the core functionality and bleeding-edge improvements
- **[Artur Graniszewski](https://github.com/artur-graniszewski/DLSS-Enabler)** - DLSS Enabler that allows DLSS features on non-RTX hardware
- **[7-Zip](https://www.7-zip.org/)** by Igor Pavlov - the plugin ships its static Linux build (`tools/7zzs`, GNU LGPL; license in `tools/7zzs-License.txt`) to unpack OptiScaler archives
- **[FakeMichau](https://github.com/FakeMichau)** - Various essential tools including fgmod scripts, innoextract, and fakenvapi for AMD/Intel GPU support

### Community & Documentation
- **[Deck Wizard](https://www.youtube.com/watch?v=o_TkF-Eiq3M)** - Extensive community support including comprehensive guides, promotional content, thorough testing and feedback, custom artworks, and tutorial videos. His passionate advocacy and continuous support have been instrumental in Decky Framegen's success.

- **The DLSS2FSR Community** - Ongoing support and guidance for understanding the various mods and tools
