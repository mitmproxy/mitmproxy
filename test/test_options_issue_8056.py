import pytest
from mitmproxy import options
from mitmproxy.addons import intercept


def test_intercept_active_is_set_when_intercept_is_set():
    """Test that setting intercept also sets intercept_active to True"""
    opts = options.Options()
    
    # Add the intercept addon options
    addon = intercept.Intercept()
    addon.load(opts)
    
    # Initially both should be None/False
    assert opts.intercept is None
    assert opts.intercept_active is False
    
    # When we set intercept, intercept_active should become True
    opts.update(intercept="app.exe")
    assert opts.intercept == "app.exe"
    assert opts.intercept_active is True


def test_intercept_active_can_be_explicitly_set():
    """Test that intercept_active can be explicitly set"""
    opts = options.Options()
    
    # Add the intercept addon options
    addon = intercept.Intercept()
    addon.load(opts)
    
    # Initially both should be None/False
    assert opts.intercept is None
    assert opts.intercept_active is False
    
    # When we explicitly set intercept_active, it should work
    opts.update(intercept_active=True)
    assert opts.intercept_active is True


def test_intercept_with_none_resets_both():
    """Test that setting intercept to None resets both options"""
    opts = options.Options()
    
    # Add the intercept addon options
    addon = intercept.Intercept()
    addon.load(opts)
    
    # Set both values first
    opts.update(intercept="app.exe", intercept_active=True)
    assert opts.intercept == "app.exe"
    assert opts.intercept_active is True
    
    # Now reset intercept to None - both should be reset
    opts.update(intercept=None)
    assert opts.intercept is None
    assert opts.intercept_active is False


def test_intercept_active_without_intercept():
    """Test that intercept_active can be set without intercept"""
    opts = options.Options()
    
    # Add the intercept addon options
    addon = intercept.Intercept()
    addon.load(opts)
    
    # Initially both should be None/False
    assert opts.intercept is None
    assert opts.intercept_active is False
    
    # Set only intercept_active to True (no intercept filter)
    opts.update(intercept_active=True)
    assert opts.intercept_active is True
    assert opts.intercept is None
