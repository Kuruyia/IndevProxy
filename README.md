# IndevProxy
IndevProxy is a small Python script that fixes the issue preventing Minecraft Indev/Infdev from generating a new world, as well as providing a few bonuses.

## Installation
This script needs [Python 3](https://www.python.org/download/) to run.  
Once installed on your system, you will need to install the required dependencies by running this command in your cmd/terminal:
```shell script
pip install proxy.py requests
```
If you get an error while performing this operation, you might want to try to use ``pip3`` instead:
```shell script
pip3 install proxy.py requests
```

Finally, clone this repository on your computer (or you can alternatively download it):
```shell script
git clone https://github.com/Arc13/IndevProxy.git
```

## Usage
Once everything is installed, you can launch IndevProxy with the following command:
```shell script
python3 indevproxy.py
```
At this point, the proxy is running on the port 8084 of your machine. You can customize this by changing the PROXY_PORT variable in the Python script.

You will now have to download a Minecraft version that you want to test. Be aware that Indev and Infdev versions are not available in the official Minecraft Launcher, so you will need to download a ``<version>.jar`` and ``<version>.json`` from a known source such as the [Minecraft Wiki](https://minecraft.gamepedia.com/Minecraft_Wiki), and place those two files in ``.minecraft/versions/<version>``.

For example, if you want to play [Infdev 20100227](https://minecraft.gamepedia.com/Java_Edition_Infdev_20100227), you'll need to download the required files, and place them under ``.minecraft/versions/inf-20100227``. You will then have the ``.minecraft/versions/inf-20100227/inf-20100227.jar`` and ``.minecraft/versions/inf-20100227/inf-20100227.json`` files.

The final step is to create a new installation in the Minecraft Launcher, you simply need to create a new one like usual (making sure Historical versions are **enabled**), and select the version you just downloaded. (Indev and Infdev are near the bottom of the list, prefixed by old_alpha)  
When you have selected the version, you will have to click the "More options" button, and add this at the end of the "JVM Arguments" section:
```
-Dhttp.proxyHost=127.0.0.1 -Dhttp.proxyPort=8084
```
(You have to properly set the proxy port if you changed it in the Python script)

## What does it fixes?
### Indev and Infdev generation
Notch implemented in those versions of the game a little check to prevent the world from being generated if the game couldn't authenticate you against a specific server.  
Unfortunately, this server is no longer running as of today, thus rendering those versions unplayable because they will automatically return you to the main menu after having created the world.  
IndevProxy will bypass this authentication by simply sending a ``0`` to Minecraft whenever it attempts to contact ``www.minecraft.net/game/``, which is enough to fool the game and let us play.

### Sounds
Minecraft Indev and Infdev does not produce any sound because they attempt to communicate with ``www.minecraft.net/resources/`` to get a list of assets to use, which also does not exist anymore.  
When IndevProxy detects a request to this address, it will attempt to get the list of pre-1.6 assets used by the official launcher from the Internet, and then convert this list to the format Indev/Infdev can understand.  
If sounds are already downloaded (something that the Minecraft launcher should already have done for you), this is enough for the game to have sounds again.

##### Disclaimer:
- IndevProxy will not attempt, for now, to serve assets asked directly by the game.
- Unfortunately, Mojang now only hosts post-Beta Sound Update sounds

### Skins
Older versions of Minecraft uses older URL to get your player skin: ``www.minecraft.net/skin/``, ``s3.amazonaws.com/MinecraftSkins/`` and ``skins.minecraft.net/MinecraftSkins/``  
IndevProxy will get the skin associated with the username using the current Mojang API, to send it to Minecraft.  
It should be possible to support capes as well, although I can't test this by myself.

## Acknowledgments
- Notch and [Mojang](https://www.mojang.com/), for their work on Minecraft
- [Proxy.py](https://github.com/abhinavsingh/proxy.py), the base of IndevProxy, allowing it to capture Minecraft requests
- [Requests](https://requests-fr.readthedocs.io/en/latest/), to facilitate communicating with the Internet when it is required to use the Mojang API