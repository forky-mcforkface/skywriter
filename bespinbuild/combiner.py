"""Combines the JavaScript files appropriately."""

import re

from simplejson import loads

class Package(object):
    visited = False
    
    def __init__(self, name, depends):
        self.name = name
        self.depends = depends
    
    def __repr__(self):
        return "Package(%s)" % (self.name)



def toposort(unsorted, reset_first=False):
    """Topologically sorts Packages. This algorithm is the
    depth-first version from Wikipedia:
    http://en.wikipedia.org/wiki/Topological_sorting
    """
    if reset_first:
        for package in unsorted:
            package.visited = False
            
    mapping = dict((package.name, package) for package in unsorted)
    l = []
    
    def visit(p):
        if not p.visited:
            p.visited = True
            for dependency in p.depends:
                try:
                    visit(mapping[dependency])
                except KeyError:
                    continue
            l.append(p)
        
    for package in unsorted:
        visit(package)
        
    return l

def combine_files(name, p, add_main=False):
    """Combines the files in an app into a single .js, with all
    of the proper information for Tiki.
    
    Arguments:
    name: application name (will become Tiki package name)
    p: path object pointing to the app's directory
    """
    combined = """;tiki.register("%s",
{"scripts":[{"url":"%s.js","id":"%s.js"}]
});
""" % (name, name, name)
    
    has_index = False
    
    for f in p.walkfiles("*.js"):
        modname = p.relpathto(f.splitext()[0])
        if modname == "index":
            has_index = True
            
        combined += """
tiki.module("%s:%s",function(require,exports,module) {
""" % (name, modname)
        combined += f.bytes()
        combined += """
});
"""
    
    if not has_index:
        if add_main:
            module_contents = """
exports.main = require("main").main;
"""
        else:
            module_contents = ""
        combined += """
tiki.module("%s:index",function(require,exports,module){%s});
""" % (name, module_contents)
    
    combined += """
tiki.script("%s.js");
""" % (name)
    
    if add_main:
        combined += """
tiki.main("%s", "main");
""" % (name)

    return combined


####
# This part is for combining the SproutCore files.
####

_make_json=re.compile('([\{,])(\w+):')
_register_line = re.compile(r'tiki.register\(["\']([\w/]+)["\'],\s*(.*)\);')
_globals_line = re.compile(r'tiki.global\(["\']([\w/]+)["\']\);')

def _quotewrap(m):
    return m.group(1) + '"' + m.group(2) + '":'
    

def combine_sproutcore_files(paths, starting="", pattern="javascript.js",
    filters=None, manual_maps=[]):
    """Combines files that are output by Abbot, taking extra care with the
    stylesheets because we want to explicitly register them rather than
    loading them individually.
    
    Arguments:
    paths: list of path objects to look for files in
    starting: initial text, if you're using multiple calls to this function
    pattern: file glob to search for
    filters: list of substring matches to perform. any that match are tossed
    manual_maps: (regex, name) tuples that map matching files to that package name
                this is used if the file does not contain a parseable tiki.register
                line.
    
    Returns: the combined bytes
    """
    stylesheets = set()
    
    newcode = ""
    flist = []
    
    for p in paths:
        flist.extend(list(p.walkfiles(pattern)))
        
    if filters:
        for filter in filters:
            flist = [f for f in flist if filter not in f]
        
    packages = []
    
    # keep track of whether or not we've seen the "tiki"
    # package. If we have, then we know that the stylesheet
    # declarations need to come after the tiki package,
    # otherwise tiki.stylesheet() will not be defined.
    found_tiki = False
    
    for f in flist:
        splitname = f.splitall()
        if not "en" in splitname:
            continue
            
        filehandle = f.open()
        firstline = filehandle.readline()
        if firstline.startswith("/"):
            firstline = filehandle.readline()
        filehandle.close()
        
        firstline = _make_json.sub(_quotewrap, firstline)
        
        # look for a tiki.register line to get package
        # metadata
        m = _register_line.search(firstline)
        if m:
            name = m.group(1)
            data = loads(m.group(2))
        else:
            # no package metadata found, see if there's
            # a manual mapping to package name
            found = False
            for expr, name in manual_maps:
                if expr.search(f):
                    found = True
                    
            # no manual mapping. we'll assume it's okay
            # to just add this JavaScript.
            if not found:
                print ("Module in %s is missing the register call", f)
                print firstline
                newcode += f.bytes()
                continue
            
            # there was a manual mapping, but we don't have
            # metadata other than the name
            data = {}
            
        # store package information so that we can do a
        # topological sort of it
        if "stylesheets" in data:
            for s in data['stylesheets']:
                stylesheets.add(s['id'])
        
        if name == "tiki":
            found_tiki = True
            
        p = Package(name, data.get('depends', []))
        packages.append(p)
        p.content = f.bytes()
    
    # commented out for the moment. this is not necessary (and may actually
    # even be a problem)
    # globals = set()
    # def replace_global(m):
    #     """Remove the global call, but keep track of it so that it can be added to the end of the file.
    #     Tiki doesn't want the global registered until the file is ready to load."""
    #     globals.add(m.group(1))
    #     return ""
    
    if not found_tiki:
        newcode = starting + "".join('tiki.stylesheet("%s");' % 
                s for s in stylesheets) + newcode
    else:
        newcode = starting + newcode
        
    packages = toposort(packages)
    for p in packages:
        newcode += p.content
        if found_tiki and p.name == "tiki":
            newcode += "".join('tiki.stylesheet("%s");' % 
                    s for s in stylesheets)
        
    return newcode

def combine_stylesheets(p, combined=""):
    for f in p.walkfiles("stylesheet.css"):
        combined += f.bytes()
    return combined