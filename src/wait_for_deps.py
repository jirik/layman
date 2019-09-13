import traceback

import sys
import time
from layman_settings import *

ATTEMPT_INTERVAL = 2
MAX_ATTEMPTS = 30


def main():

    attempt = 1

    # Redis
    import redis
    rds = redis.Redis.from_url(LAYMAN_REDIS_URL, encoding="utf-8", decode_responses=True)
    wait_for_msg = f"Redis, url={LAYMAN_REDIS_URL}"
    print(f"Waiting for {wait_for_msg}")
    while True:
        try:
            rds.ping()
            print(f"Attempt {attempt}/{MAX_ATTEMPTS} successful.")
            break
        except redis.exceptions.ConnectionError as e:
            handle_exception(e, attempt, wait_for_msg)
            attempt += 1
    print()

    # PostgreSQL
    conn_dict = PG_CONN if LAYMAN_PG_TEMPLATE_DBNAME is None else PG_CONN_TEMPLATE
    secret_conn_dict = {k: v for k, v in conn_dict.items() if k != 'password'}
    wait_for_msg = f"PostgreSQL database, {secret_conn_dict}"
    print(f"Waiting for {wait_for_msg}")
    while True:
        import psycopg2
        try:
            with psycopg2.connect(**conn_dict) as conn:
                pass
            print(f"Attempt {attempt}/{MAX_ATTEMPTS} successful.")
            break
        except psycopg2.OperationalError as e:
            handle_exception(e, attempt, wait_for_msg)
            attempt += 1
    print()

    # GeoServer
    headers_json = {
        'Accept': 'application/json',
        'Content-type': 'application/json',
    }
    wait_for_msg = f"GeoServer REST API, user={LAYMAN_GS_USER}, url={LAYMAN_GS_REST_WORKSPACES}"
    print(f"Waiting for {wait_for_msg}")
    while True:
        import requests
        try:
            r = requests.get(
                LAYMAN_GS_REST_WORKSPACES,
                headers=headers_json,
                auth=LAYMAN_GS_AUTH,
                timeout=0.1
            )
            r.raise_for_status()
            print(f"Attempt {attempt}/{MAX_ATTEMPTS} successful.")
            break
        except (requests.exceptions.ConnectionError, requests.exceptions.ReadTimeout) as e:
            handle_exception(e, attempt, wait_for_msg)
            attempt += 1
    print()


def handle_exception(e, attempt, wait_for_msg=None):
    if attempt < MAX_ATTEMPTS:
        msg_end = f"Waiting {ATTEMPT_INTERVAL} seconds before next attempt."
    else:
        msg_end = "Max attempts reached!"
    # print(f"Attempt {attempt}/{MAX_ATTEMPTS} failed:")
    # print(e)
    # print(msg_end)
    # traceback.print_exc()
    if attempt >= MAX_ATTEMPTS:
        print(f"Reaching max attempts when waiting for {wait_for_msg}")
        sys.exit(1)
        # raise e
    time.sleep(ATTEMPT_INTERVAL)


if __name__ == "__main__":
    main()