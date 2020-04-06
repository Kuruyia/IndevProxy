# -*- coding: utf-8 -*-
import base64
import ipaddress
import os.path
import requests
import json

from typing import Optional

import proxy
from proxy.common.utils import build_http_response
from proxy.http.parser import HttpParser
from proxy.http.codes import httpStatusCodes
from proxy.http.proxy import HttpProxyBasePlugin

PROXY_PORT = 8084

VERSION_MANIFEST = b'https://launchermeta.mojang.com/mc/game/version_manifest.json'
MINECRAFT_NET = b'www.minecraft.net'
S3_AMAZONAWS = b's3.amazonaws.com'


def get_mc_uuid_from_username(username: str):
    # Get the UUID from Mojang's API
    player_uuid_response = requests.get('https://api.mojang.com/users/profiles/minecraft/{}'
                                        .format(username))

    if player_uuid_response.status_code == httpStatusCodes.OK:
        # We must parse the response and get the UUID from the 'id' string
        player_uuid_response_parsed = json.loads(player_uuid_response.text)
        return player_uuid_response_parsed['id']
    else:
        raise RuntimeError('get_mc_uuid_from_username: status_code != httpStatusCodes.OK')


def get_mc_profile_from_uuid(uuid: str):
    # Get the profile from Mojang's API
    player_profile_response = requests.get('https://sessionserver.mojang.com/session/minecraft/profile/{}'
                                           .format(uuid))

    if player_profile_response.status_code == httpStatusCodes.OK:
        # We can return the parsed JSON if it was received correctly
        return json.loads(player_profile_response.text)
    else:
        raise RuntimeError('get_mc_profile_from_uuid: status_code != httpStatusCodes.OK')


def get_mc_player_textures_from_uuid(uuid: str):
    # First, we must get the profile JSON
    try:
        profile = get_mc_profile_from_uuid(uuid)
    except:
        raise

    # Then, we look for a property called 'textures' that holds a JSON containing skin/cape data
    for proper in profile['properties']:
        if proper['name'] == 'textures':
            decoded_value = base64.b64decode(proper['value']).decode('utf-8')
            return json.loads(decoded_value)

    raise RuntimeError('get_mc_player_textures_from_uuid: Could not find textures')


def get_mc_player_skin_from_uuid(uuid: str):
    # First, we get the textures JSON
    try:
        textures = get_mc_player_textures_from_uuid(uuid)
    except:
        raise

    # Then, we grab the URL of the player skin
    skin_url = textures['textures']['SKIN']['url']
    skin_response = requests.get(skin_url)

    if skin_response.status_code == httpStatusCodes.OK:
        # Finally, we return the skin data (we should have received a PNG)
        return skin_response.content
    else:
        raise RuntimeError('get_mc_player_skin_from_uuid: status_code != httpStatusCodes.OK')


def get_mc_old_alpha_package_url():
    manifest_response = requests.get(VERSION_MANIFEST)
    if manifest_response.status_code == httpStatusCodes.OK:
        try:
            manifest_parsed_response = json.loads(manifest_response.text)
        except:
            raise

        for version in manifest_parsed_response['versions']:
            if version['type'] == 'old_alpha':
                return version['url']

        raise RuntimeError('get_mc_old_alpha_package_url: Could not grab an old_alpha package')
    else:
        raise RuntimeError('get_mc_old_alpha_package_url: status_code != httpStatusCodes.OK')


def get_mc_asset_url_from_package_url(url: str):
    package_response = requests.get(url)
    if package_response.status_code == httpStatusCodes.OK:
        try:
            package_parsed_response = json.loads(package_response.text)
        except:
            raise

        return package_parsed_response['assetIndex']['url']
    else:
        raise RuntimeError('get_mc_asset_url_from_package_url: status_code != httpStatusCodes.OK')


def get_mc_resources():
    if os.path.isfile('pre-1.6.json'):
        # We have the pre-1.6.json file cached
        f = open('pre-1.6.json', 'r')
        resources = json.load(f)
        f.close()

        return resources
    else:
        # We must download the pre-1.6.json file
        try:
            old_alpha_package_url = get_mc_old_alpha_package_url()
        except:
            raise

        try:
            alpha_assets_url = get_mc_asset_url_from_package_url(old_alpha_package_url)
        except:
            raise

        # When we get the URL of the file, save it and return the parsed result
        alpha_assets_response = requests.get(alpha_assets_url)
        if alpha_assets_response.status_code == httpStatusCodes.OK:
            f = open('pre-1.6.json', 'w')
            f.write(alpha_assets_response.text)
            f.close()

            return json.loads(alpha_assets_response.text)
        else:
            raise RuntimeError('get_mc_resources: status_code != httpStatusCodes.OK')


def convert_mc_resources_to_old_format(resources: dict):
    old_format = []
    for res in resources['objects']:
        old_format.append('{},{},0'.format(res, resources['objects'][res]['size']))

    return '\n'.join(old_format)


class IndevProxyPlugin(HttpProxyBasePlugin):
    def before_upstream_connection(self, request: HttpParser) -> Optional[HttpParser]:
        return request

    def handle_client_request(self, request: HttpParser) -> Optional[HttpParser]:
        # Request doesn't go to the minecraft.net URL, don't touch it
        if request.host != MINECRAFT_NET and request.host != S3_AMAZONAWS:
            return request

        # Request to the minecraft.net URL, handle it
        succeeded = self.handle_minecraft_request(request)

        # Drop the original request if we handled the request
        if succeeded:
            return None
        else:
            return request

    def handle_upstream_chunk(self, chunk: memoryview) -> memoryview:
        return chunk

    def on_upstream_connection_close(self) -> None:
        pass

    def handle_mc_auth(self):
        # Old Minecraft wants to authenticate, it is enough to reply with a 0
        print('Authentication requested')
        self.client.queue(memoryview(build_http_response(
            status_code=200,
            body=b'0'
        )))

        return True

    def handle_mc_skin(self, request: HttpParser):
        # A skin has been requested, get the username from the URL path
        succeeded = False
        print('Skin requested: {}'.format(request.path))
        username_start = request.path.rfind(b'/') + 1
        username_end = request.path.find(b'.')
        username = request.path[username_start:username_end]

        print('Got player: {}'.format(username))

        try:
            # Try to get the player UUID from their username
            player_uuid = get_mc_uuid_from_username(username.decode('utf-8'))
            print('Got player UUID: {}'.format(player_uuid))

            # Then, we can grab their skin data and send it as the response
            skin = get_mc_player_skin_from_uuid(player_uuid)
            self.client.queue(memoryview(build_http_response(
                status_code=200,
                body=skin
            )))

            succeeded = True
        except RuntimeError as e:
            print('RuntimeError while getting player skin: {}'.format(e))
        except Exception as e:
            print('Exception while getting player skin: {}'.format(e))

        return succeeded

    def handle_mc_res(self, request: HttpParser):
        # Resources have been requested
        succeeded = False
        print('Resources requested: {}'.format(request.path))
        if request.path == b'/resources/':
            try:
                new_resources = get_mc_resources()

                resources_old_format = convert_mc_resources_to_old_format(new_resources)
                self.client.queue(memoryview(build_http_response(
                    status_code=200,
                    body=resources_old_format.encode()
                )))

                succeeded = True
            except RuntimeError as e:
                print('RuntimeError while getting resources: {}'.format(e))
            except Exception as e:
                print('Exception while getting resources: {}'.format(e))
        else:
            print('Individual resource passthrough is not currently supported!')

        return succeeded

    def handle_minecraft_request(self, request: HttpParser):
        succeeded = False
        print('Handling request for: {}{}'.format(request.host.decode(), request.path.decode()))

        if request.path.startswith(b'/game/'):
            # Endpoint is /game/, send 0 to let the game launch
            succeeded = self.handle_mc_auth()
        elif request.path.startswith(b'/skin/') or request.path.startswith(b'/MinecraftSkins/'):
            # Endpoint is /skin/, try to grab the skin from modern servers
            succeeded = self.handle_mc_skin(request)
        elif request.path.startswith(b'/resources/'):
            # Endpoint is /resources/, try to download some useful assets
            succeeded = self.handle_mc_res(request)

        return succeeded


if __name__ == '__main__':
    proxy.main(
        hostname=ipaddress.IPv4Address('0.0.0.0'),
        port=PROXY_PORT,
        plugins='indevproxy.IndevProxyPlugin'
    )
