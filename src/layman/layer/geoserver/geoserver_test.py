import pytest

from layman import settings
from layman.http import LaymanError
from test import process_client


@pytest.mark.usefixtures('ensure_layman')
def test_check_username_wms():
    username = 'test_check_username_user' + settings.LAYMAN_GS_WMS_WORKSPACE_POSTFIX
    layername = 'test_check_username_wms_layer'
    with pytest.raises(LaymanError) as exc_info:
        process_client.publish_layer(username, layername)
    assert exc_info.value.code == 45
    assert exc_info.value.data['workspace_name'] == username
