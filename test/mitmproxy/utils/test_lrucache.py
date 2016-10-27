import unittest

from mitmproxy.utils import lrucache


class TestLRUCache(unittest.TestCase):
    
    def setUp(self):
        # Record the calls to our generator function
        self.calls = []
        self.cache = lrucache.LRUCache()
    
    def gen(self, *args):
        """
        A dummy generator function.  In a real LRU cache, this would be
        an expensive generator function.  In this case, it just records
        the call and returns the hash of the arguments.
        """
        self.calls.append(args)
        return hash(args)
    
    def test_inserting_an_item(self):
        """We can make a single call to the cache."""
        self.cache.get(self.gen, "foo")
        assert len(self.calls) == 1
    
    def test_retrieving_an_item_multiple_times(self):
        """
        If we call the same arguments multiple times, we only call the
        generator function once.  The result is the same every time.
        """
        result = self.cache.get(self.gen, "foo")
        for _ in range(5):
            new_result = self.cache.get(self.gen, "foo")
            assert result == new_result
        assert len(self.calls) == 1
    
    def test_retrieving_an_item_with_different_generators(self):
        """
        The identity of the generator isn't taken into account by
        the cache.  A ``get()`` with the same arguments but a different
        generator doesn't call the new generator.
        """
        def alt_gen(*args):
            assert False, "This should never be called"
        
        result = self.cache.get(self.gen, "foo")
        new_result = self.cache.get(alt_gen, "foo")
        assert result == new_result
    
    def test_cache_size(self):
        """
        We can set the size of the cache, and entries can expire from the
        cache if we exceed the size.
        """
        cache = lrucache.LRUCache(size=10)
        
        # Saturate the cache
        for i in range(10):
            cache.get(self.gen, i)
        assert len(self.calls) == 10

        # Now add another item to the cache; this will cause the first item
        # to be dropped
        cache.get(self.gen, "foo")
        assert len(self.calls) == 11
        
        # Finally, go back and get the first item from the cache.
        cache.get(self.gen, 0)
        assert len(self.calls) == 12
    
    def test_cache_freshening(self):
        """
        Retrieving an item from the cache "freshens" it, and moves it
        down the queue for dropping.
        """
        cache = lrucache.LRUCache(size=10)
        
        # Saturate the cache
        for i in range(10):
            cache.get(self.gen, i)
        assert len(self.calls) == 10
        
        # At this point, adding another item to the cache would cause 0
        # to be dropped.  Retrieve it a second time, to freshen it.
        cache.get(self.gen, 0)
        assert len(self.calls) == 10
        
        # Add another item to the cache; this will cause the first item
        # to be dropped.
        cache.get(self.gen, "foo")
        assert len(self.calls) == 11
        
        # Retrieve 0 from the cache again, and check we don't call the
        # generator function again.
        cache.get(self.gen, 0)
        assert len(self.calls) == 11
