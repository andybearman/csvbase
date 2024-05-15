from csvbase.web.func import set_current_user
from .utils import make_user
from lxml import etree


def test_user_view__self(client, test_user, ten_rows, private_table):
    set_current_user(test_user)
    resp = client.get(f"/{test_user.username}")

    ten_rows_display_name = test_user.username + "/" + ten_rows.table_name
    private_table_display_name = test_user.username + "/" + private_table

    page = etree.HTML(resp.text)

    assert resp.status_code == 200
    assert page.xpath(f"//h5/a[text()='{ten_rows_display_name}']")
    assert page.xpath(f"//h5/a[text()='{private_table_display_name}']")


def test_user_view__while_anon(client, test_user, ten_rows, private_table):
    resp = client.get(f"/{test_user.username}")

    ten_rows_display_name = test_user.username + "/" + ten_rows.table_name
    private_table_display_name = test_user.username + "/" + private_table

    page = etree.HTML(resp.text)

    assert resp.status_code == 200
    assert page.xpath(f"//h5/a[text()='{ten_rows_display_name}']")
    assert not page.xpath(f"//h5/a[text()='{private_table_display_name}']")


def test_user_view__other(app, sesh, client, test_user, ten_rows):
    set_current_user(make_user(sesh, app.config["CRYPT_CONTEXT"]))
    resp = client.get(f"/{test_user.username}")
    assert resp.status_code == 200
