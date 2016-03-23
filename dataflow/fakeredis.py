import warnings

def lrucache(size):
    try:
        #raise ImportError("no pylru")
        import pylru
        return pylru.lrucache(size)
    except ImportError:
        warnings.warn("pylru not available; using simple cache with no size limit")
        return {}


class MemoryCache:
    """
    In memory cache with redis interface.

    Use this for running tests without having to start up the redis server.
    """
    def __init__(self, size=1000):
        self.cache = lrucache(size)
    def exists(self, key):
        return key in self.cache
    def keys(self):
        return self.cache.keys()
    def delete(self, *key):
        for k in key:
            del self.cache[k]
    def set(self, key, value):
        self.cache[key] = value
    def get(self, key):
        """Note: doesn't provide default value for missing key like dict.get"""
        return self.cache[key]
    __delitem__ = delete
    __setitem__ = set
    __getitem__ = get
    def rpush(self, key, value):
        if key not in self.cache:
            self.cache[key] = [value]
        else:
            self.cache[key].append(value)
    def lrange(self, key, low, high):
        """Note: returned range includes high index, not high-1 like lists"""
        return self.cache[key][low:(high+1 if high != -1 else None)]

import os, pickle, threading
class FileBasedCache(object):
    """
    Disk-based cache with redis interface.

    Use this for running tests without having to start up the redis server.
    """
    def __init__(self, size=1000, cachedir='~/.webreduce'):
        self.size = size
        self.write_lock = threading.Lock()
        self.cachedir = os.path.expanduser(cachedir)
        if not os.path.exists(self.cachedir):
            os.mkdir(self.cachedir)
    def exists(self, key):
        return os.path.exists(os.path.join(self.cachedir, key))
    def keys(self):
        return os.listdir(self.cachedir)
    def delete(self, *key):
        for k in key:
            os.remove(os.path.join(self.cachedir, k))
    def set(self, key, value):
        #open(os.path.join(self.cachedir, key), "wb").write(pickle.dumps(value))
        with self.write_lock:
            open(os.path.join(self.cachedir, key), "wb").write(value)
    def get(self, key):
        """Note: doesn't provide default value for missing key like dict.get"""
        try: 
            #ret = pickle.loads(open(os.path.join(self.cachedir, key), "rb").read())
            ret = open(os.path.join(self.cachedir, key), "rb").read()
        except IOError:
            raise KeyError(key)
        return ret
            
    __delitem__ = delete
    __setitem__ = set
    __getitem__ = get
    __contains__ = exists
    def rpush(self, key, value):
        if key not in self:
            self[key] = [value]
        else:
            self[key].append(value)
    def lrange(self, key, low, high):
        """Note: returned range includes high index, not high-1 like lists"""
        return self[key][low:(high+1 if high != -1 else None)]


def demo():
    class Expensive(object):
        def __del__(self):
            print '(Deleting %d)'% self.a
        def __init__(self, a):
            self.a = a
            print '(Creating %s)'% self.a
    print "test using get/set interface"
    cache = MemoryCache(5)
    for k in range(5):
        print "=== inserting %d"%k
        cache.set(k, Expensive(k))
    for k in range(5):
        print "=== inserting %d, deleting %d"%(k+5,k)
        cache.set(k+5, Expensive(k+5))
    print "=== accessing oldest element, 5"
    a = cache.get(5)
    print "=== inserting 10 and deleting 6"
    cache.set(10, Expensive(10))

    print
    print "test using dict-like interface"
    cache2 = MemoryCache(5)
    for k in range(5):
        print "=== inserting %d"%k
        cache2[k] = Expensive(k)
    for k in range(5):
        print "=== inserting %d, deleting %d"%(k+5,k)
        cache2[k+5] = Expensive(k+5)
    print "=== accessing oldest element, 5"
    a = cache2[5]
    print "=== inserting 10 and deleting 6"
    cache2[10] = Expensive(10)

    print "=== cleanup of cache and cache2 can happen in any order"

if __name__ == "__main__":
    demo()    
     
