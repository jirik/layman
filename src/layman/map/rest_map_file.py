import json
import os
from flask import Blueprint, jsonify, current_app as app, g

from layman.http import LaymanError
from layman.util import check_username_decorator
from layman.common.filesystem.util import get_user_dir
from . import util, MAP_REST_PATH_NAME
from layman.authn import authenticate
from layman.authz import authorize_publications_decorator

bp = Blueprint('rest_map_file', __name__)


@bp.before_request
@check_username_decorator
@util.check_mapname_decorator
@authenticate
@authorize_publications_decorator
@util.info_decorator
def before_request():
    pass


@bp.route(f"/{MAP_REST_PATH_NAME}/<mapname>/file", methods=['GET'])
def get(username, mapname):
    app.logger.info(f"GET Map File, user={g.user}")

    map_json = util.get_map_file_json(username, mapname)

    if map_json is not None:
        return jsonify(map_json), 200

    raise LaymanError(27, {'mapname': mapname})
