import re
import os
import json

one = """Splat Bomb
Suction Bomb
Burst Bomb
Sprinkler
Fizzy Bomb
Smallfry
Tentatek
Octopod"""

two = """
Splattershot Jr.
N-ZAP '85
Tri-Slosher
Splatana Wiper
Splash Wall
Curling Bomb
Point Sensor
Ink Mine
Toxic Mist
Angle Shooter
Torpedo
Octocopter
Octomissile
Octostamp
Chum
Custom Splattershot Jr.
N-ZAP '89
Tri-Slosher Nouveau"""

three = """Splash-o-matic
Aerospray MG
Splattershot
.52 Gal
Luna Blaster
Blaster
Clash Blaster
Rapid Blaster
L-3 Nozzlenose
H-3 Nozzlenose
Squeezer
Carbon Roller
Inkbrush
Classic Squiffer
Splat Charger
Bamboozler 14 Mk I
Slosher
Sloshing Machine
Mini Splatling
Dapple Dualies
Splat Dualies
Dark Tetra Dualies
Undercover Brella
Splatana Stamper
Autobomb
Li'l Judd
Toni Kensa
Octotrooper
Tentakook
Squee-G
Snatcher
Stinger
Slammin' Lid
Aerospray RG
Tentatek Splattershot
Luna Blaster Neo
Carbon Roller Deco
Inkbrush Nouveau
Slosher Deco
Zink Mini Splatling
Dapple Dualies Nouveau
Neo Splash-o-matic
Clash Blaster Neo
Rapid Blaster Deco
L-3 Nozzlenose D
Z+F Splat Charger
Trizooka
Big Bubbler
Zipcaster
Tenta Missiles
Ink Storm
Booyah Bomb
Wave Breaker
Ink Vac
Killer Wail 5.1
Inkjet
Ultra Stamp
Crab Tank
Reefslider
Triple Inkstrike
Tacticooler
Kraken Royale
Super Chump"""

four = """Sploosh-o-matic
Splattershot Pro
.96 Gal
Jet Squelcher
Range Blaster
Rapid Blaster Pro
Splat Roller
Flingza Roller
Octobrush
Splatterscope
E-liter 4K
Goo Tuber
Bloblobber
Explosher
Ballpoint Splatling
Nautilus 47
Glooga Dualies
Dualie Squelchers
Splat Brella
Tri-Stringer
REEF-LUX 450
Squid Beakon
SquidForce
Rockenberg
Forge
Firefin
Splash Mob
Inkline
Barazushi
Emberz
Shielded Octotrooper
Twintacle Octotrooper
Octohopper
Oversized Octopod
Octosniper
Octozeppelin
Amped Octostamp
Octoling
Cohock
Steel Eel
Scrapper
Fish Stick
Zapfish
Power Clam
Forge Splattershot Pro
Splattershot Nova
Big Swig Roller
Snipewriter 5H
Neo Sploosh-o-matic
.96 Gal Deco
Custom Jet Squelcher
Krak-On Splat Roller
Z+F Splatterscope
Fred Crumbs
Z+F"""

five = """Hero Shot
Dynamo Roller
E-liter 4K Scope
Heavy Splatling
Hydra Splatling
Tenta Brella
Sheldon
Gnarly Eddy
Jel La Fleur
Mr. Coco
Harmony
Murch
Mr. Grizz
Marigold
Cuttlefish
Callie
Marie
Judd
Zink
Krak-On
Zekko
Skalop
Takoroka
Annaki
Enperry
Octobomber
Octodisco
Octocommander
Flooder
Octoballer
Steelhead
Maws
Drizzler
Flyfish
Flipper-Flopper
Big Shot
Goldie
Griller
Mothership
Mudmouth
Tower Control
Rainmaker
Shelly & Donny
Annie
Jelonzo
Spyke
The Eel Deal - Frye
The Cold-Blooded Bandit - Shiver
The Hype Manta Storm - Big Man"""

six = """Captain
Shiver
Frye
Big Man
DJ Octavio"""

costs = [x.split("\n") for x in [one, two, three, four, five, six]]

def cost_for(name):
    for i in range(len(costs)):
        for item in costs[i]:
            if item == name:
                return i+1
    return -1

def main():
    manifest = {}

    prog = re.compile("No. (\d+) (.*) \((.*)\).jpg")

    for _root, _dirs, files in os.walk("gallery"):
        for fname in files:
            result = prog.match(fname)
            if not result:
                continue
            
            
            number = int(result.group(1))
            name = result.group(2)
            rarity = result.group(3)
            cost = cost_for(name)

            manifest[number] = {
                "name": name,
                "rarity": rarity,
                "cost": cost,
            }

            os.rename(os.path.join("gallery", fname), os.path.join("gallery", f"{number}.jpg"))

    with open("manifest.json", "w") as f:
        f.write(json.dumps(manifest, indent=4))

if __name__ == "__main__":
    main()