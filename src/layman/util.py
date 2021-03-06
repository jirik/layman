from functools import wraps
import importlib
import inspect
import re
import unicodedata
from collections import OrderedDict

from flask import current_app, request, url_for as flask_url_for, jsonify
from unidecode import unidecode

from layman import settings
from layman.http import LaymanError

USERNAME_ONLY_PATTERN = r"[a-z][a-z0-9]*(?:_[a-z0-9]+)*"

USERNAME_PATTERN = r"^" + USERNAME_ONLY_PATTERN + r"$"

FLASK_PROVIDERS_KEY = f'{__name__}:PROVIDERS'
FLASK_PUBLICATION_TYPES_KEY = f'{__name__}:PUBLICATION_TYPES'
FLASK_PUBLICATION_MODULES_KEY = f'{__name__}:PUBLICATION_MODULES'


def slugify(value):
    value = unidecode(value)
    value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii')
    value = re.sub(r'[^\w\s\-\.]', '', value).lower()
    value = re.sub(r'[\s\-\._]+', '_', value).strip('_')
    return value


def to_safe_name(unsafe_name, type_name):
    value = slugify(unsafe_name)
    if len(value) == 0:
        value = type_name
    elif re.match(r'^[^a-z].*', value):
        value = f'{type_name}_{value}'
    return value


def to_safe_names(unsafe_names, type_name):
    values = [slugify(n) for n in unsafe_names]
    values = [v for v in values if len(v) > 0]
    values_letter_prefix, values_other_prefix = [], []
    for v in values:
        (values_other_prefix if re.match(r'^[^a-z].*', v) else values_letter_prefix).append(v)
    values = values_letter_prefix + [f'{type_name}_{v}' for v in values_other_prefix]
    if len(values) == 0:
        values = [type_name]
    return values


def check_username_decorator(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        username = request.view_args['username']
        check_username(username, pattern_only=True)
        result = f(*args, **kwargs)
        return result

    return decorated_function


def check_reserved_workspace_names(workspace_name):
    if workspace_name in settings.RESERVED_WORKSPACE_NAMES:
        raise LaymanError(35, {'reserved_by': 'RESERVED_WORKSPACE_NAMES', 'workspace': workspace_name})


def check_username(username, pattern_only=False):
    if not re.match(USERNAME_PATTERN, username):
        raise LaymanError(2, {'parameter': 'user', 'expected': USERNAME_PATTERN})
    if pattern_only:
        return
    check_reserved_workspace_names(username)
    providers = get_internal_providers()
    call_modules_fn(providers, 'check_username', [username])


def get_usernames(use_cache=True, skip_modules=None):
    skip_modules = skip_modules or set()
    if use_cache:
        providers = get_internal_providers()
    else:
        all_sources = []
        for type_def in get_publication_types(use_cache=False).values():
            all_sources += type_def['internal_sources']
        providers = get_providers_from_source_names(all_sources, skip_modules)
    results = call_modules_fn(providers, 'get_usernames')
    usernames = []
    for r in results:
        usernames += r
    usernames = list(set(usernames))
    return usernames


def get_workspaces(use_cache=True, skip_modules=None):
    skip_modules = skip_modules or set()
    if use_cache:
        providers = get_internal_providers()
    else:
        all_sources = []
        for type_def in get_publication_types(use_cache=False).values():
            all_sources += type_def['internal_sources']
        providers = get_providers_from_source_names(all_sources, skip_modules)
    results = call_modules_fn(providers, 'get_workspaces')
    workspaces = []
    for r in results:
        workspaces += r
    workspaces = list(set(workspaces))
    return workspaces


def ensure_whole_user(username):
    current_app.logger.info('ensure_whole_user:' + username)
    providers = get_internal_providers()
    call_modules_fn(providers, 'ensure_whole_user', [username])


def delete_whole_user(username):
    providers = get_internal_providers()
    call_modules_fn(providers, 'delete_whole_user', [username])


def get_internal_providers():
    key = FLASK_PROVIDERS_KEY
    if key not in current_app.config:
        all_sources = []
        for type_def in get_publication_types().values():
            all_sources += type_def['internal_sources']
        current_app.config[key] = get_providers_from_source_names(all_sources)
    return current_app.config[key]


def get_publication_types(use_cache=True):
    def modules_to_types(publ_modules):
        return {
            type_name: type_def
            for publ_module in publ_modules
            for type_name, type_def in publ_module.PUBLICATION_TYPES.items()
        }
    if use_cache:
        key = FLASK_PUBLICATION_TYPES_KEY
        if key not in current_app.config:
            current_app.config[key] = modules_to_types(get_publication_modules())

        result = current_app.config[key]
    else:
        result = modules_to_types(get_publication_modules(use_cache=False))
    return result


def get_blueprints():
    blueprints = []
    for type_def in get_publication_types(use_cache=False).values():
        blueprints += type_def['blueprints']
    return blueprints


def get_publication_modules(use_cache=True):
    if use_cache:
        key = FLASK_PUBLICATION_MODULES_KEY
        if key not in current_app.config:
            current_app.config[key] = get_modules_from_names(settings.PUBLICATION_MODULES)
        result = current_app.config[key]
    else:
        result = get_modules_from_names(settings.PUBLICATION_MODULES)
    return result


def get_providers_from_source_names(source_names, skip_modules=None):
    skip_modules = skip_modules or set()
    provider_names = list(OrderedDict.fromkeys(map(
        lambda src: src[:src.rfind('.')],
        source_names
    )))
    provider_names = list(set(provider_names).difference(skip_modules))
    providers = get_modules_from_names(provider_names)
    return providers


def get_modules_from_names(module_names):
    modules = list(map(
        lambda module_name: importlib.import_module(module_name),
        module_names
    ))
    return modules


def call_modules_fn(modules, fn_name, args=None, kwargs=None, omit_duplicate_calls=True, until=None):
    if args is None:
        args = []
    if kwargs is None:
        kwargs = {}

    fns = []
    for m in modules:
        fn = getattr(m, fn_name, None)
        if fn is None:
            raise Exception(
                f'Module {m.__name__} does not have {fn_name} method.')
        if fn not in fns or not omit_duplicate_calls:
            fns.append(fn)

    results = []
    for fn in fns:
        fn_arg_names = inspect.getfullargspec(fn)[0]
        res = fn(*args, **{
            k: v for k, v in kwargs.items()
            if k in fn_arg_names
        })
        results.append(res)
        if until is not None and until(res):
            return results

    return results


DUMB_MAP_ADAPTER = None


def url_for(endpoint, **values):
    # Flask does not accept SERVER_NAME without dot, and without SERVER_NAME url_for cannot be used
    # therefore DUMB_MAP_ADAPTER is created manually ...
    global DUMB_MAP_ADAPTER
    if current_app.config.get('SERVER_NAME', None) is None:
        if DUMB_MAP_ADAPTER is None:
            DUMB_MAP_ADAPTER = current_app.url_map.bind(
                settings.LAYMAN_PROXY_SERVER_NAME,
                url_scheme=current_app.config['PREFERRED_URL_SCHEME']
            )
        result = DUMB_MAP_ADAPTER.build(endpoint, values=values, force_external=True)
    else:
        result = flask_url_for(endpoint, **values, _external=True)
    return result


def get_internal_sources(publ_type):
    return get_modules_from_names(get_publication_types()[publ_type]['internal_sources'])


def get_publication_info(workspace, publ_type, publ_name, context=None):
    from layman import authz
    from layman.layer import LAYER_TYPE
    from layman.map import MAP_TYPE
    context = context or {}

    sources = get_internal_sources(publ_type)
    if 'sources_filter' in context:
        sources_names = context['sources_filter'].split(',')
        if 'actor_name' in context:
            sources_names.append(get_publication_types()[publ_type]['access_rights_source'])
        sources = [
            s for s in sources if s.__name__ in sources_names
        ]

    info_method = {
        LAYER_TYPE: 'get_layer_info',
        MAP_TYPE: 'get_map_info',
    }[publ_type]
    partial_infos = call_modules_fn(sources, info_method, [workspace, publ_name])

    result = {}
    for pi in partial_infos:
        result.update(pi)

    if 'actor_name' in context:
        actor = context['actor_name']
        read_access_users = result.get('access_rights').get('read')
        if not authz.is_user_in_access_rule(actor, read_access_users):
            result = {}

    return result


def get_publication_infos(workspace=None, publ_type=None, context=None):
    from layman import authz
    from layman.common.prime_db_schema import publications
    context = context or {}

    infos_orig = publications.get_publication_infos(workspace, publ_type)

    if 'actor_name' in context:
        actor = context['actor_name']
        access_type = context['access_type']
        result = {key: info for key, info in infos_orig.items()
                  if authz.is_user_in_access_rule(actor, info.get('access_rights').get(access_type))}
    else:
        result = infos_orig

    return result


def delete_publications(user,
                        publ_type,
                        error_code,
                        is_task_ready_fn,
                        abort_publication_fn,
                        delete_publication_fn,
                        method,
                        url_path,
                        publ_param,
                        ):
    from layman.common import redis as redis_util
    from layman import authn
    actor_name = authn.get_authn_username()
    whole_infos = get_publication_infos(user, publ_type, {'actor_name': actor_name, 'access_type': 'write'})

    for (workspace, publication_type, publication) in whole_infos.keys():
        redis_util.create_lock(user, publ_type, publication, error_code, method)
        try:
            abort_publication_fn(user, publication)
            delete_publication_fn(user, publication)
            if is_task_ready_fn(user, publication):
                redis_util.unlock_publication(user, publ_type, publication)
        except Exception as e:
            try:
                if is_task_ready_fn(user, publication):
                    redis_util.unlock_publication(user, publ_type, publication)
            finally:
                redis_util.unlock_publication(user, publ_type, publication)
            raise e

    infos = [
        {
            'name': info["name"],
            'title': info.get("title", None),
            'url': url_for(**{'endpoint': url_path, publ_param: name, 'username': user}),
            'uuid': info["uuid"],
            'access_rights': info['access_rights'],
        }
        for (name, info) in whole_infos.items()
    ]
    return jsonify(infos)
