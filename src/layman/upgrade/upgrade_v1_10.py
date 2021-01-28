from layman import util as layman_util, settings
from layman.http import LaymanError


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
