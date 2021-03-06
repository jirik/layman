from flask import Blueprint, jsonify, request, g
from flask import current_app as app

from layman.common import rest as rest_util
from layman.http import LaymanError
from layman.util import check_username_decorator, url_for
from layman import settings, authn, util as layman_util
from . import util, LAYER_TYPE, LAYER_REST_PATH_NAME
from .filesystem import input_file, input_sld, input_chunk, uuid
from layman.authn import authenticate
from layman.authz import authorize_publications_decorator
from layman.common import redis as redis_util
from layman import util as layman_util

bp = Blueprint('rest_layers', __name__)


@bp.before_request
@check_username_decorator
@authenticate
@authorize_publications_decorator
def before_request():
    pass


@bp.route(f"/{LAYER_REST_PATH_NAME}", methods=['GET'])
def get(username):
    app.logger.info(f"GET Layers, user={g.user}")

    layer_infos_whole = layman_util.get_publication_infos(username, LAYER_TYPE)
    layer_infos = {name: info for (workspace, publication_type, name), info in layer_infos_whole.items()}

    sorted_infos = sorted(layer_infos.items(), key=lambda x: x[0])

    infos = [
        {
            'name': info["name"],
            'title': info.get("title", None),
            'url': url_for('rest_layer.get', layername=name, username=username),
            'uuid': info["uuid"],
            'access_rights': info['access_rights'],
        }
        for (name, info) in sorted_infos
    ]
    return jsonify(infos), 200


@bp.route(f"/{LAYER_REST_PATH_NAME}", methods=['POST'])
def post(username):
    app.logger.info(f"POST Layers, user={g.user}")

    # FILE
    use_chunk_upload = False
    files = []
    if 'file' in request.files:
        files = [
            f for f in request.files.getlist("file")
            if len(f.filename) > 0
        ]
    if len(files) == 0 and len(request.form.getlist('file')) > 0:
        files = [
            filename for filename in request.form.getlist('file')
            if len(filename) > 0
        ]
        if len(files) > 0:
            use_chunk_upload = True
    if len(files) == 0:
        raise LaymanError(1, {'parameter': 'file'})

    # NAME
    unsafe_layername = request.form.get('name', '')
    if len(unsafe_layername) == 0:
        unsafe_layername = input_file.get_unsafe_layername(files)
    layername = util.to_safe_layer_name(unsafe_layername)
    util.check_layername(layername)
    info = util.get_layer_info(username, layername)
    if info:
        raise LaymanError(17, {'layername': layername})
    util.check_new_layername(username, layername)

    # CRS
    crs_id = None
    if len(request.form.get('crs', '')) > 0:
        crs_id = request.form['crs']
        if crs_id not in settings.INPUT_SRS_LIST:
            raise LaymanError(2, {'parameter': 'crs', 'supported_values': settings.INPUT_SRS_LIST})
    check_crs = crs_id is None

    # TITLE
    if len(request.form.get('title', '')) > 0:
        title = request.form['title']
    else:
        title = layername

    # DESCRIPTION
    description = request.form.get('description', '')

    # SLD
    sld_file = None
    if 'sld' in request.files and not request.files['sld'].filename == '':
        sld_file = request.files['sld']

    actor_name = authn.get_authn_username()

    task_options = {
        'crs_id': crs_id,
        'description': description,
        'title': title,
        'ensure_user': True,
        'check_crs': False,
        'actor_name': actor_name,
    }

    rest_util.setup_post_access_rights(request.form, task_options, actor_name)
    util.pre_publication_action_check(username,
                                      layername,
                                      task_options,
                                      )

    layerurl = url_for('rest_layer.get', layername=layername, username=username)

    layer_result = {
        'name': layername,
        'url': layerurl,
    }

    # FILE NAMES
    if use_chunk_upload:
        filenames = files
    else:
        filenames = [f.filename for f in files]
    input_file.check_filenames(username, layername, filenames, check_crs)

    redis_util.lock_publication(username, LAYER_TYPE, layername, request.method)

    try:
        # register layer uuid
        uuid_str = uuid.assign_layer_uuid(username, layername)
        layer_result.update({
            'uuid': uuid_str,
        })
        task_options.update({'uuid': uuid_str, })

        # save files
        input_sld.save_layer_file(username, layername, sld_file)
        if use_chunk_upload:
            files_to_upload = input_chunk.save_layer_files_str(
                username, layername, files, check_crs)
            layer_result.update({
                'files_to_upload': files_to_upload,
            })
            task_options.update({
                'check_crs': check_crs,
            })
        else:
            input_file.save_layer_files(
                username, layername, files, check_crs)

        util.post_layer(
            username,
            layername,
            task_options,
            'layman.layer.filesystem.input_chunk' if use_chunk_upload else 'layman.layer.filesystem.input_file'
        )
    except Exception as e:
        try:
            if util.is_layer_task_ready(username, layername):
                redis_util.unlock_publication(username, LAYER_TYPE, layername)
        finally:
            redis_util.unlock_publication(username, LAYER_TYPE, layername)
        raise e

    # app.logger.info('uploaded layer '+layername)
    return jsonify([layer_result]), 200


@bp.route(f"/{LAYER_REST_PATH_NAME}", methods=['DELETE'])
def delete(username):
    app.logger.info(f"DELETE Layers, user={g.user}")

    infos = layman_util.delete_publications(username,
                                            LAYER_TYPE,
                                            19,
                                            util.is_layer_task_ready,
                                            util.abort_layer_tasks,
                                            util.delete_layer,
                                            request.method,
                                            'rest_layer.get',
                                            'layername',
                                            )
    return infos, 200
