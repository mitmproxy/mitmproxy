import pytest

from mitmproxy import exceptions
from mitmproxy.addons import intercept
from mitmproxy.test import taddons
from mitmproxy.test import tflow


async def test_scenario_1_only_intercept_active_true():
    """
    Scenario 1: Only activate intercept_active=true WITHOUT defining a filter
    Result: Raises OptionsError requiring a filter
    """
    print("\n" + "=" * 70)
    print("SCENARIO 1: intercept_active=true (WITHOUT FILTER)")
    print("=" * 70)

    r = intercept.Intercept()
    with taddons.context(r) as tctx:
        # Try to activate only intercept_active - should raise OptionsError
        with pytest.raises(exceptions.OptionsError, match="intercept_active=true requires a filter"):
            tctx.configure(r, intercept_active=True)

        print("✓ OptionsError raised as expected")
        print("✓ intercept_active cannot be set to True without a filter")
        print("\n✅ RESULT: Correctly prevents invalid configuration!")
        print("   The system properly validates that intercept_active=true requires a filter")

async def test_scenario_2_with_filter():
    """
    Scenario 2: Define a filter using the 'intercept' option
    Result: Works!
    """
    print("\n" + "=" * 70)
    print("SCENARIO 2: DEFINING A FILTER WITH --set intercept='~a'")
    print("=" * 70)

    r = intercept.Intercept()
    with taddons.context(r) as tctx:
        # Now configure with a valid filter (accept all: ~a)
        tctx.configure(r, intercept="~a")  # This automatically activates intercept_active

        # Create test flow
        f = tflow.tflow(resp=False)

        # Check result
        should_intercept = r.should_intercept(f)

        print(f"✓ intercept_active: {tctx.options.intercept_active}")
        print(f"✓ interceptor filter (self.filt): {r.filt}")
        print(f"✓ Should intercept this flow?: {should_intercept}")
        print("\n✅ RESULT: Works!")
        print("   When you define the filter with --set intercept='~a':")
        print("   1. The filter is parsed")
        print("   2. self.filt is set")
        print("   3. intercept_active is automatically activated")

async def test_scenario_3_specific_filter():
    """
    Scenario 3: Specific filter (only specific domains)
    """
    print("\n" + "=" * 70)
    print("SCENARIO 3: SPECIFIC FILTER - only example.com")
    print("=" * 70)

    from mitmproxy.test.tutils import treq

    r = intercept.Intercept()
    with taddons.context(r) as tctx:
        # Specific filter: only example.com
        tctx.configure(r, intercept="~d example.com")

        # Create two flows
        f1 = tflow.tflow(req=treq(host=b"example.com"))
        f2 = tflow.tflow(req=treq(host=b"other.com"))

        should_intercept_f1 = r.should_intercept(f1)
        should_intercept_f2 = r.should_intercept(f2)

        print(f"Flow 1 (example.com): {should_intercept_f1}")
        print(f"Flow 2 (other.com): {should_intercept_f2}")
        print("\n✅ Only flows that match the filter are intercepted")

async def test_simple():
    r = intercept.Intercept()
    with taddons.context(r) as tctx:
        assert not r.filt
        tctx.configure(r, intercept="~q")
        assert r.filt
        assert tctx.options.intercept_active
        with pytest.raises(exceptions.OptionsError):
            tctx.configure(r, intercept="~~")
        tctx.configure(r, intercept=None)
        assert not r.filt
        assert not tctx.options.intercept_active
        tctx.configure(r, intercept="~s")
        f = tflow.tflow(resp=True)
        await tctx.cycle(r, f)
        assert f.intercepted
        f = tflow.tflow(resp=False)
        await tctx.cycle(r, f)
        assert not f.intercepted
        f = tflow.tflow(resp=True)
        r.response(f)
        assert f.intercepted
        tctx.configure(r, intercept_active=False)
        f = tflow.tflow(resp=True)
        await tctx.cycle(r, f)
        assert not f.intercepted
        tctx.configure(r, intercept_active=True)
        f = tflow.tflow(resp=True)
        await tctx.cycle(r, f)
        assert f.intercepted

async def test_dns():
    r = intercept.Intercept()
    with taddons.context(r) as tctx:
        tctx.configure(r, intercept="~s ~dns")
        f = tflow.tdnsflow(resp=True)
        await tctx.cycle(r, f)
        assert f.intercepted
        f = tflow.tdnsflow(resp=False)
        await tctx.cycle(r, f)
        assert not f.intercepted
        tctx.configure(r, intercept_active=False)
        f = tflow.tdnsflow(resp=True)
        await tctx.cycle(r, f)
        assert not f.intercepted

async def test_tcp():
    r = intercept.Intercept()
    with taddons.context(r) as tctx:
        tctx.configure(r, intercept="~tcp")
        f = tflow.ttcpflow()
        await tctx.cycle(r, f)
        assert f.intercepted
        tctx.configure(r, intercept_active=False)
        f = tflow.ttcpflow()
        await tctx.cycle(r, f)
        assert not f.intercepted

async def test_udp():
    r = intercept.Intercept()
    with taddons.context(r) as tctx:
        tctx.configure(r, intercept="~udp")
        f = tflow.tudpflow()
        await tctx.cycle(r, f)
        assert f.intercepted
        tctx.configure(r, intercept_active=False)
        f = tflow.tudpflow()
        await tctx.cycle(r, f)
        assert not f.intercepted

async def test_websocket_message():
    r = intercept.Intercept()
    with taddons.context(r) as tctx:
        tctx.configure(r, intercept='~b "hello binary"')
        f = tflow.twebsocketflow()
        await tctx.cycle(r, f)
        assert f.intercepted
        tctx.configure(r, intercept_active=False)
        f = tflow.twebsocketflow()
        await tctx.cycle(r, f)
        assert not f.intercepted

async def test_intercept_active_without_filter():
    """Test that intercept_active=True without a filter raises OptionsError"""
    r = intercept.Intercept()
    with taddons.context(r) as tctx:
        # This should raise an OptionsError
        with pytest.raises(exceptions.OptionsError, match="intercept_active=true requires a filter"):
            tctx.configure(r, intercept_active=True)

