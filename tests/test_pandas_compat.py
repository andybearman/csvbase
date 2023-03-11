from io import StringIO, BytesIO

import pandas as pd
from pandas.testing import assert_frame_equal
import pytest

from .utils import get_df_as_csv


def get_df_as_parquet(client, url) -> pd.DataFrame:
    get_resp = client.get(url + ".parquet")
    assert get_resp.mimetype == "application/octet-stream"
    return pd.read_parquet(BytesIO(get_resp.data)).set_index("csvbase_row_id")


def get_df_as_jsonlines(client, url) -> pd.DataFrame:
    get_resp = client.get(url + ".jsonl")
    assert get_resp.mimetype != "text/html"
    return pd.read_json(get_resp.data.decode("utf-8"), lines=True).set_index(
        "csvbase_row_id"
    )


def put_df_as_csv(client, user, url, df: pd.DataFrame) -> None:
    buf = StringIO()
    df.to_csv(buf)

    post_resp = client.put(
        url,
        data=buf.getvalue(),
        headers={
            "Content-Type": "text/csv",
            "Authorization": user.basic_auth(),
        },
    )
    assert post_resp.status_code == 200


def test_csvs_in_and_out(test_user, sesh, client, ten_rows):
    """Test that a csv can be pulled out, edited, and then posted back"""
    url = f"/{test_user.username}/{ten_rows.table_name}"

    df = get_df_as_csv(client, url)
    # df = df.assign(as_date=pd.to_datetime(df["as_date"]))
    df.drop(labels=2, axis="index", inplace=True)  # removed data
    df.loc[11] = ("XI", False, "2018-01-11", 11.5)  # added data
    df.loc[5].roman_numeral = "FIVE"  # changed data

    buf = StringIO()
    df.to_csv(buf)

    put_df_as_csv(client, test_user, url, df)
    second_df = get_df_as_csv(client, url)

    assert_frame_equal(df, second_df)


def test_get_jsonlines(test_user, sesh, client, ten_rows):
    url = f"/{test_user.username}/{ten_rows.table_name}"
    df_from_csv = get_df_as_csv(client, url)

    df_from_jsonlines = get_df_as_jsonlines(client, url)

    assert_frame_equal(df_from_csv, df_from_jsonlines)


def test_get_unknown_extension(test_user, client, ten_rows):
    url = f"/{test_user.username}/{ten_rows.table_name}.pokemon"
    resp = client.get(url)
    assert resp.status_code == 406


def test_get_parquet(test_user, sesh, client, ten_rows):
    url = f"/{test_user.username}/{ten_rows.table_name}"
    df_from_csv = get_df_as_csv(client, url)
    df_from_csv = df_from_csv.assign(as_date=pd.to_datetime(df_from_csv["as_date"]))

    df_from_parquet = get_df_as_parquet(client, url)

    # pandas mangles the date32 because it doesn't have a date type:
    # https://github.com/pandas-dev/pandas/issues/20089
    df_from_parquet = df_from_parquet.assign(
        as_date=pd.to_datetime(df_from_parquet["as_date"])
    )

    assert_frame_equal(df_from_csv, df_from_parquet)


@pytest.mark.xfail(reason="not implemented")
def test_putting_a_table_doesnt_break_adding_new_rows():
    # At the moment if you add a new row above the sequence, adding a row 500's.  Some sample code here:
    # https://stackoverflow.com/questions/244243/how-to-reset-postgres-primary-key-sequence-when-it-falls-out-of-sync
    assert False


def test_putting_blanks_makes_them_get_autofilled(test_user, sesh, client, ten_rows):
    url = f"/{test_user.username}/{ten_rows.table_name}"

    df = get_df_as_csv(client, url).reset_index()
    df = pd.concat([df, pd.DataFrame({"roman_numeral": ["XI"]})])
    df = df.set_index("csvbase_row_id")
    df.index = df.index.astype(pd.Int64Dtype())

    put_df_as_csv(client, test_user, url, df)

    second_df = get_df_as_csv(client, url)

    # the next number should be 11
    df = df.rename(index={pd.NA: 11})
    assert_frame_equal(df, second_df)


def test_mixing_blanks_and_row_ids(test_user, sesh, client, ten_rows):
    url = f"/{test_user.username}/{ten_rows.table_name}"

    df = get_df_as_csv(client, url).reset_index()
    df = pd.concat(
        [df, pd.DataFrame({"csvbase_row_id": [11], "roman_numeral": ["XI"]})]
    )
    df = pd.concat([df, pd.DataFrame({"roman_numeral": ["XII"]})])
    df = df.set_index("csvbase_row_id")
    df.index = df.index.astype(pd.Int64Dtype())

    put_df_as_csv(client, test_user, url, df)

    second_df = get_df_as_csv(client, url)

    # the next number should be 11
    df = df.rename(index={pd.NA: 12})
    assert_frame_equal(df, second_df)
