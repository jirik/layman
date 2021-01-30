from layman import util as layman_util, settings
from layman.http import LaymanError
from layman import util
from layman.layer import LAYER_TYPE
from layman.layer import geoserver
from layman.layer.geoserver import wms


def check_usernames_for_wms_suffix():
    workspaces = layman_util.get_workspaces(use_cache=False)
    for workspace in workspaces:
        if workspace.endswith(settings.LAYMAN_GS_WMS_WORKSPACE_POSTFIX):
            raise LaymanError(f"A workspace has name with reserved suffix '{settings.LAYMAN_GS_WMS_WORKSPACE_POSTFIX}'. "
                              f"In that case, please downgrade to last 1.8 version of Layman and contact Layman contributors. "
                              f"One way how to do that is to create an issue in Layman repository: "
                              f"https://github.com/jirik/layman/issues/",
                              data={'workspace': workspace,
                                    }
                              )


def migrate_layers_to_wms_workspace():
    infos = util.get_publication_infos(publ_type=LAYER_TYPE)
    for (workspace, publication_type, layer) in infos.keys():
        info = util.get_publication_info(workspace, publication_type, layer)
        geoserver_workspace = wms.get_geoserver_workspace(workspace)
        geoserver.ensure_workspace(workspace)

        geoserver.publish_layer_from_db(workspace,
                                        layer,
                                        info.get('description'),
                                        info.get('title'),
                                        info.get('access_rights'),
                                        geoserver_workspace=geoserver_workspace)
        wms.clear_cache(workspace)
