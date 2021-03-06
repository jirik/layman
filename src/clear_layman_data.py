import importlib
import os
import re
import shutil
from urllib.parse import urljoin

settings = importlib.import_module(os.environ['LAYMAN_SETTINGS_MODULE'])


def main():
    print(f"Clearing Layman data.")
    # filesystem
    if os.path.exists(settings.LAYMAN_DATA_DIR):
        for the_file in os.listdir(settings.LAYMAN_DATA_DIR):
            file_path = os.path.join(settings.LAYMAN_DATA_DIR, the_file)
            print(f"Removing filesystem path {file_path}")
            if os.path.isfile(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)

    # postgresql
    import psycopg2
    conn_dict = settings.PG_CONN.copy()
    conn = psycopg2.connect(**settings.PG_CONN)
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute(f"""
select catalog_name, schema_name, schema_owner
from information_schema.schemata
where schema_owner = '{settings.LAYMAN_PG_USER}'
and schema_name NOT IN ({', '.join(map(lambda s: "'" + s + "'", settings.PG_NON_USER_SCHEMAS))})
""")
    rows = cur.fetchall()
    print(f"Dropping schemas in DB {conn_dict['dbname']}: {[r[1] for r in rows]}")
    for row in rows:
        cur.execute(f"""DROP SCHEMA "{row[1]}" CASCADE""")
    conn.close()

    # redis
    print(f"Flushing Redis DB {settings.LAYMAN_REDIS_URL}")
    settings.LAYMAN_REDIS.flushdb()
    import redis
    print(f"Flushing Redis DB {os.environ['LTC_REDIS_URI']}")
    ltc_redis = redis.Redis.from_url(os.environ['LTC_REDIS_URI'], encoding="utf-8", decode_responses=True)
    ltc_redis.flushdb()

    # geoserver
    import requests
    headers_json = {
        'Accept': 'application/json',
        'Content-type': 'application/json',
    }

    auth = settings.GEOSERVER_ADMIN_AUTH or settings.LAYMAN_GS_AUTH
    r = requests.get(settings.LAYMAN_GS_REST_USERS,
                     headers=headers_json,
                     auth=auth
                     )
    r.raise_for_status()
    all_users = [u['userName'] for u in r.json()['users']]
    if settings.LAYMAN_GS_USER in all_users:
        all_users.remove(settings.LAYMAN_GS_USER)

    for user in all_users:
        r = requests.get(urljoin(settings.LAYMAN_GS_REST_ROLES, f'user/{user}/'),
                         headers=headers_json,
                         auth=auth
                         )
        r.raise_for_status()
        roles = r.json()['roleNames']

        if settings.LAYMAN_GS_ROLE in roles:
            r = requests.delete(
                urljoin(settings.LAYMAN_GS_REST_SECURITY_ACL_LAYERS, user + '.*.r'),
                headers=headers_json,
                auth=auth
            )
            if r.status_code != 404:
                r.raise_for_status()

            r = requests.delete(
                urljoin(settings.LAYMAN_GS_REST_SECURITY_ACL_LAYERS, user + '.*.w'),
                headers=headers_json,
                auth=auth
            )
            if r.status_code != 404:
                r.raise_for_status()

            r = requests.delete(
                urljoin(settings.LAYMAN_GS_REST_WORKSPACES, user),
                headers=headers_json,
                auth=auth,
                params={
                    'recurse': 'true'
                }
            )
            r.raise_for_status()

            for role in roles:
                r = requests.delete(
                    urljoin(settings.LAYMAN_GS_REST_ROLES, f'role/{role}/user/{user}/'),
                    headers=headers_json,
                    auth=auth,
                )
                r.raise_for_status()

            r = requests.delete(
                urljoin(settings.LAYMAN_GS_REST_ROLES, 'role/' + f"USER_{user.upper()}"),
                headers=headers_json,
                auth=auth,
            )
            if r.status_code != 404:
                r.raise_for_status()

            r = requests.delete(
                urljoin(settings.LAYMAN_GS_REST_USER, user),
                headers=headers_json,
                auth=auth,
            )
            r.raise_for_status()

    r = requests.get(settings.LAYMAN_GS_REST_WORKSPACES,
                     headers=headers_json,
                     auth=auth
                     )
    r.raise_for_status()

    if r.json()['workspaces'] != "":
        all_workspaces = [workspace["name"] for workspace in r.json()['workspaces']['workspace']]
        for workspace in all_workspaces:
            r = requests.delete(
                urljoin(settings.LAYMAN_GS_REST_WORKSPACES, workspace),
                headers=headers_json,
                auth=auth,
                params={
                    'recurse': 'true'
                }
            )
            r.raise_for_status()

    # micka
    opts = {} if settings.CSW_BASIC_AUTHN is None else {
        'username': settings.CSW_BASIC_AUTHN[0],
        'password': settings.CSW_BASIC_AUTHN[1],
    }
    opts['skip_caps'] = True
    from owslib.csw import CatalogueServiceWeb
    csw = CatalogueServiceWeb(settings.CSW_URL, **opts) if settings.CSW_URL is not None else None
    csw.getrecords2(xml=f"""
        <csw:GetRecords xmlns:ogc="http://www.opengis.net/ogc" xmlns:csw="http://www.opengis.net/cat/csw/2.0.2" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dct="http://purl.org/dc/terms/" xmlns:ows="http://www.opengis.net/ows" xmlns:xlink="http://www.w3.org/1999/xlink" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:apiso="http://www.opengis.net/cat/csw/apiso/1.0" xmlns:gmd="http://www.isotc211.org/2005/gmd" outputSchema="http://www.isotc211.org/2005/gmd" maxRecords="100" startPosition="1" outputFormat="application/xml" service="CSW" resultType="results" version="2.0.2" requestId="1" debug="0">
         <csw:Query typeNames="gmd:MD_Metadata">
          <csw:ElementSetName>summary</csw:ElementSetName>
          <csw:Constraint version="1.1.0">
           <ogc:Filter xmlns:gml="http://www.opengis.net/gml">
             <ogc:PropertyIsLike wildCard="*" singleChar="@" escapeChar="\\">
               <ogc:PropertyName>apiso:Identifier</ogc:PropertyName>
               <ogc:Literal>*</ogc:Literal>
             </ogc:PropertyIsLike>
           </ogc:Filter>
          </csw:Constraint>
         </csw:Query>
        </csw:GetRecords>
        """)
    assert csw.exceptionreport is None
    items = csw.records.items()
    for record_id, record in items:
        urls = [ol.url for ol in record.distribution.online]
        url_part = f"://{settings.LAYMAN_PROXY_SERVER_NAME}/rest/"
        if any((url_part in u for u in urls)):
            print(f"Deleting metadata record {record_id}")
            csw.transaction(ttype='delete', typename='gmd:MD_Metadata', identifier=record_id)

    # Layman DB
    conn = psycopg2.connect(**settings.PG_CONN)
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute(f"""
DROP SCHEMA IF EXISTS "{settings.LAYMAN_PRIME_SCHEMA}" CASCADE;
""")
    conn.commit()


if __name__ == "__main__":
    main()
