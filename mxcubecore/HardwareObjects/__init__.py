import os
import sys
pathIter = os.walk(__path__[0])
try:
    root,dirs,filesNames = pathIter.next()
    for dirname in dirs:
        if not dirname.startswith('.') :
            fullPath = os.path.join(root,dirname)
            if os.path.exists(os.path.join(fullPath,'trunk')) :
                fullPath = os.path.join(fullPath,'trunk')
            __path__.append(fullPath)
            sys.path.append(fullPath)
except StopIteration:
    pass

