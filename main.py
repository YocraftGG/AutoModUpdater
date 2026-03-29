import os
import shutil
from typing import Any

import requests
import zipfile
import json
import sys

import concurrent.futures

from gui import *


def get_mod_info(filename:str) -> tuple[Any, Any, Any, Any] | None:
    try:
        with zipfile.ZipFile(filename) as f:
            with f.open("fabric.mod.json") as f:
                data = json.load(f)
                mod_id = data.get("custom", {}).get("modmenu", {}).get("parent", {}).get("id", {})
                mod_title = data.get("custom", {}).get("modmenu", {}).get("parent", {}).get("name", {})
                mod_version = data["version"]
                mc_version = data.get("depends", {}).get("minecraft", 0)
                if not mod_id:
                    mod_id = data["id"]
                    mod_title = data["name"]
                return mod_id, mod_title, mod_version, mc_version
    except Exception as e:
        print(e)
        return None

def includes_letters(string:str):
    for char in string:
        if char.isalpha():
            return False
    return True

def get_slug(slugs: list[str]):
    for slug in slugs:
        url = f"https://api.modrinth.com/v2/project/{slug}"
        response = requests.get(url)
        if response.status_code == 200:
            return slug
    return None

def search_slug(title):
    url = "https://api.modrinth.com/v2/search"

    params = {
        "query": title,
        "limit": 5,
    }

    response = requests.get(url, params=params)
    data = response.json()
    hits = data["hits"]

    for mod in hits:
        if mod["title"] == title:
            return mod["slug"]
    return None

def create_profile():
    manifest = requests.get(
        "https://launchermeta.mojang.com/mc/game/version_manifest.json"
    ).json()

    latest_release = manifest["latest"]["release"]

    fabric_versions = requests.get(
        "https://meta.fabricmc.net/v2/versions/loader"
    ).json()

    latest_loader = fabric_versions[0]["version"]

    minecraft_version = latest_release
    loader_version = latest_loader

    url = f"https://meta.fabricmc.net/v2/versions/loader/{minecraft_version}/{loader_version}/profile/json"

    fabric_profile = requests.get(url).json()

    minecraft_folder = os.path.expandvars(r"%APPDATA%\.minecraft")
    version_folder = os.path.join(minecraft_folder, "versions")
    version_name = f"fabric-loader-{loader_version}-{minecraft_version}"

    path = os.path.join(version_folder, version_name)
    os.makedirs(path, exist_ok=True)

    with open(f"{path}/{version_name}.json", "w") as f:
        json.dump(fabric_profile, f, indent=4)

    profiles_path = os.path.join(minecraft_folder, "launcher_profiles.json")

    with open(profiles_path, "r") as f:
        data = json.load(f)

    profile_name = f"Fabric {minecraft_version}"

    data["profiles"][profile_name] = {
        "name": profile_name,
        "lastVersionId": version_name,
        "type": "custom",
        "icon": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAIAAAACABAMAAAAxEHz4AAAAGFBMVEUAAAA4NCrb0LTGvKW8spyAem2uppSakn5SsnMLAAAAAXRSTlMAQObYZgAAAJ5JREFUaIHt1MENgCAMRmFWYAVXcAVXcAVXcH3bhCYNkYjcKO8dSf7v1JASUWdZAlgb0PEmDSMAYYBdGkYApgf8ER3SbwRgesAf0BACMD1gB6S9IbkEEBfwY49oNj4lgLhA64C0o9R9RABTAvp4SX5kB2TA5y8EEAK4pRrxB9QcA4QBWkj3GCAMUCO/xwBhAI/kEsCagCHDY4AwAC3VA6t4zTAMj0OJAAAAAElFTkSuQmCC"
    }

    with open(profiles_path, "w") as f:
        json.dump(data, f, indent=4)

def download_mod(mod: str, mods_folder, latest_version):
    if not os.path.exists(os.path.join(mods_folder, "old_mods")):
        os.mkdir(os.path.join(mods_folder, "old_mods"))
    shutil.move(os.path.join(mods_folder, mod), os.path.join(mods_folder, "old_mods", mod))

    print("Downloading...")
    file = latest_version["files"][0]
    download_url = file["url"]
    filename = file["filename"]

    print(download_url)
    mod_data = requests.get(download_url)

    with open(os.path.join(mods_folder, filename), "wb") as f:
        f.write(mod_data.content)
    print("Downloading complete!")
    print()

    create_profile()
    return filename

def get_mod(file_name, mods_folder):
    if file_name.endswith(".jar"):
        mod_id, mod_title, mod_version, mod_mc_version = get_mod_info(f"{mods_folder}\\{file_name}")
        loader = "fabric"

        slug_variant = [mod_id, mod_id.replace("-", "_"), mod_id.replace("_", "-")]
        slug = get_slug(slug_variant)

        if slug is None:
            slug = search_slug(mod_title)
            if slug is None:
                print(f"Could not found the mod {mod_title}")
                return None

        url = f"https://api.modrinth.com/v2/project/{slug}"
        response = requests.get(url)
        versions = response.json()
        release_versions = [version for version in versions['game_versions'] if includes_letters(version)][::-1]

        mc_version = release_versions[0]

        url = (
            f"https://api.modrinth.com/v2/project/{slug}/version"
            f"?game_versions=[\"{mc_version}\"]"
            f"&loaders=[\"{loader}\"]"
        )

        response = requests.get(url)
        versions = response.json()
        latest_version = versions[0]["version_number"]
        if type(mod_mc_version) == list:
            mod_mc_version = max(mod_mc_version, key=lambda v: v.strip())
        latest_mod_mc_version = max(versions[0]["game_versions"])

        print(mc_version)
        print(latest_mod_mc_version)

        return {"title": mod_title,
                     "file_name": file_name,
                     "version": mod_version,
                     "latest_version": versions[0],
                     "has_update": mod_version not in latest_version and mod_mc_version != latest_mod_mc_version and latest_mod_mc_version not in mod_version}
    return None


def get_mods(mods_folder):
    mods = []
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [executor.submit(get_mod, file_name, mods_folder) for file_name in os.listdir(mods_folder)]
        for future in concurrent.futures.as_completed(futures):
            if future.result() is None:
                continue
            mod = dict(future.result())
            print(f"===={mod["title"]}====")
            print("Current version name:", mod["version"])
            print("Latest version name:", mod["latest_version"]["version_number"])
            print(mod["latest_version"])
            mods.append(mod)
    return mods

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()