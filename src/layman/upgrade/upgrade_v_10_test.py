import pytest

from . import upgrade_v1_10
from layman import app, settings
from layman.http import LaymanError
from layman.common import prime_db_schema

from layman.layer.geoserver import wms

from test import process_client


@pytest.mark.usefixtures('ensure_layman')
def test_check_usernames_for_wms_suffix():
    username = 'test_check_usernames_for_wms_suffix'
    username_wms = 'test_check_usernames_for_wms_suffix' + settings.LAYMAN_GS_WMS_WORKSPACE_POSTFIX

    with app.app_context():
        prime_db_schema.ensure_workspace(username)
        upgrade_v1_10.check_usernames_for_wms_suffix()

        prime_db_schema.ensure_workspace(username_wms)
        with pytest.raises(LaymanError) as exc_info:
            upgrade_v1_10.check_usernames_for_wms_suffix()
        assert exc_info.value.data['workspace'] == username_wms


@pytest.mark.usefixtures('ensure_layman')
def test_migrate_layers_to_wms_workspace():
    workspace = 'test_migrate_layers_to_wms_workspace_workspace'
    layer = 'test_migrate_layers_to_wms_workspace_layer'

    process_client.publish_layer(workspace, layer)

    with app.app_context():
        info = wms.get_layer_info(workspace, layer)
    assert info

    wms.delete_layer(workspace, layer)

    with app.app_context():
        info = wms.get_layer_info(workspace, layer)
        assert not info

        upgrade_v1_10.migrate_layers_to_wms_workspace()

        info = wms.get_layer_info(workspace, layer)
        assert info

    process_client.delete_layer(workspace, layer)
