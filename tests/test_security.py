import pytest
from omni_browser.security import BrowserSecurityError, check_sensitive_click, check_url, validate_owner, validate_repo_name

@pytest.mark.parametrize("url", ["file:///etc/passwd", "javascript:alert(1)", "data:text/html,a", "http://user:pw@github.com", "ftp://github.com/a", "https://"])
def test_urls_rejected(url):
    with pytest.raises(BrowserSecurityError): check_url(url)

@pytest.mark.parametrize("url", ["https://github.com/new", "http://localhost:8080/", "https://docs.github.com/pt"])
def test_urls_accepted(url):
    assert check_url(url, "") == url

def test_allowlist_exact_host_or_subdomain_only():
    assert check_url("https://docs.github.com/en", "github.com")
    with pytest.raises(BrowserSecurityError): check_url("https://github.com.evil.com", "github.com")
    with pytest.raises(BrowserSecurityError): check_url("https://evil.com", "github.com")

@pytest.mark.parametrize("repo", ["", "../x", ".git", "ab c", "a"*101, "e/1", "foo.git"])
def test_invalid_repo(repo):
    with pytest.raises(BrowserSecurityError): validate_repo_name(repo)

def test_valid_repo_and_owner():
    assert validate_repo_name("omni-research-oss") == "omni-research-oss"
    assert validate_owner("rianprei") == "rianprei"

@pytest.mark.parametrize("owner", ["", "a/evil", "-foo", "foo-", "x"*50])
def test_invalid_owner(owner):
    with pytest.raises(BrowserSecurityError): validate_owner(owner)

def test_high_impact_confirmation():
    with pytest.raises(BrowserSecurityError): check_sensitive_click('role=button[name="Delete repository"]', False)
    assert check_sensitive_click('role=button[name="Delete repository"]', True) is None
