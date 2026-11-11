import pytest
from unittest.mock import MagicMock, patch
from omni_browser.github import prepare_repository, submit_repository, push_local_project
from omni_browser.security import BrowserSecurityError


def test_prepare_repo_does_not_submit():
    harness=MagicMock()
    page=MagicMock();page.url='https://github.com/new?owner=rianprei'
    harness._ready.return_value=page
    harness.snapshot.return_value={"snapshot":"repo form"}
    field=MagicMock();opt=MagicMock();button=MagicMock();button.is_enabled.return_value=True
    with patch("omni_browser.github._repository_name_field",return_value=field),patch("omni_browser.github._visibility_option",return_value=opt),patch("omni_browser.github._create_button",return_value=button):
        result=prepare_repository(harness,owner="rianprei",name="omni-research-oss",visibility="public")
    assert result["prepared"] is True
    field.fill.assert_called_once_with("omni-research-oss")
    opt.check.assert_called_once()
    button.click.assert_not_called()
    harness.open.assert_called_once_with("https://github.com/new?owner=rianprei")


def test_submit_requires_explicit_confirmation():
    with pytest.raises(BrowserSecurityError): submit_repository(MagicMock(),owner="rianprei",name="omni-research-oss",confirm=False)


def test_submit_rejects_wrong_owner():
    harness=MagicMock();page=MagicMock();page.url="https://github.com/new"
    harness._ready.return_value=page
    with patch("omni_browser.github._create_button"):
        page.url="https://github.com/other/omni-research-oss"
        # State is post-navigation; won't click on a stale form
        with pytest.raises(RuntimeError):submit_repository(harness,owner="rianprei",name="omni-research-oss",confirm=True)


def test_push_does_not_run_without_confirmation(tmp_path):
    with pytest.raises(BrowserSecurityError):push_local_project(source=tmp_path,owner="rianprei",name="repo",confirm=False)
